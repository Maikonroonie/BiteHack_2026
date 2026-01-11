"""
CrisisEye - Flood Detector & Predictor
AI + Physics-based flood detection and prediction engine.
"""

import numpy as np
import os
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.ndimage import binary_dilation, median_filter
import rasterio.features
import rasterio.transform
from typing import Dict, Any, List, Optional

# Model cache path
MODEL_PATH = "models_cache/sar_kmeans_v1.joblib"


class FloodDetector:
    """
    AI + Physics Engine for flood detection and prediction.
    Adapted for Microsoft Planetary Computer data.
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.kmeans = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Load pre-trained model if available."""
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                self.kmeans = data["model"]
                self.scaler = data["scaler"]
                self.model_loaded = True
                print(f"[AI] Loaded model from {MODEL_PATH}")
            except Exception as e:
                print(f"[AI] Failed to load model: {e}")
        
        if not self.model_loaded:
            self.kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)

    def train_on_history(self, training_images: List[np.ndarray]):
        """Train model on provided SAR images."""
        print("[AI] Training model on current data...")
        valid_pixels = []
        for img in training_images:
            pixels = img.flatten()
            valid_pixels.append(pixels[~np.isnan(pixels)])
            
        if not valid_pixels:
            return
        
        X = np.concatenate(valid_pixels).reshape(-1, 1)
        # Train on sample for speed (max 100k pixels)
        if X.shape[0] > 100000:
            X = X[np.random.choice(X.shape[0], 100000, replace=False)]
            
        X_scaled = self.scaler.fit_transform(X)
        self.kmeans.fit(X_scaled)
        
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.kmeans, "scaler": self.scaler}, MODEL_PATH)
        self.model_loaded = True
        print("[AI] Model trained and saved")

    async def detect_flood(self, sar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main flood detection method using SAR change detection.
        
        Args:
            sar_data: Dict with 'before', 'after', 'dem', 'bbox' keys
            
        Returns:
            Dict with 'status', 'stats', 'geojson', 'mask'
        """
        # 1. Unpack data
        image_after = np.nan_to_num(sar_data["after"], nan=0.0)
        image_before = np.nan_to_num(sar_data["before"], nan=0.0)
        dem_data = sar_data.get("dem")
        if dem_data is not None:
            dem_data = np.nan_to_num(dem_data, nan=0.0)
        else:
            dem_data = np.zeros_like(image_after)
        bbox = sar_data["bbox"]

        # 2. Train online if needed
        if not self.model_loaded:
            self.train_on_history([image_after, image_before])

        # 3. K-Means detection
        mask_after = self._predict_mask(image_after)
        mask_before = self._predict_mask(image_before)

        # 4. Change Detection (only NEW water)
        current_flood_mask = mask_after & (~mask_before)
        current_flood_mask = median_filter(current_flood_mask, size=3)

        # 5. Physics (Gravity + Depth)
        depth_map, risk_map = self._calculate_physics(current_flood_mask, dem_data)
        future_mask = self._simulate_gravity(current_flood_mask, dem_data)

        # 6. Generate GeoJSON
        geojson_current = self._mask_to_geojson(
            current_flood_mask, bbox, image_after.shape,
            {"status": "current", "type": "flood", "risk": "high", "flood_probability": 0.9}
        )
        
        predicted_expansion = future_mask & (~current_flood_mask)
        geojson_future = self._mask_to_geojson(
            predicted_expansion, bbox, image_after.shape,
            {"status": "forecast", "type": "warning", "risk": "medium", "flood_probability": 0.6}
        )

        all_features = geojson_current["features"] + geojson_future["features"]

        # Calculate stats matching FloodPixelStats schema
        h, w = image_after.shape
        total_pixels = h * w
        flooded_pixels = int(np.sum(current_flood_mask))
        # Approximate: 10m resolution = 0.0001 km^2 per pixel
        pixel_area_km2 = 0.0001
        
        stats = {
            "total_pixels": total_pixels,
            "flooded_pixels": flooded_pixels,
            "flood_percentage": round(100 * flooded_pixels / max(total_pixels, 1), 2),
            "area_km2": round(total_pixels * pixel_area_km2, 2),
            "flooded_area_km2": round(flooded_pixels * pixel_area_km2, 2),
            "max_depth_m": round(float(np.max(depth_map)), 2),
            "risk_level": "CRITICAL" if np.max(depth_map) > 1.2 else "MODERATE"
        }

        return {
            "status": "success",
            "stats": stats,
            "geojson": {"type": "FeatureCollection", "features": all_features},
            "mask": current_flood_mask 
        }

    async def predict_flood_risk(
        self,
        bbox: List[float],
        precipitation_data: Dict[str, Any],
        terrain_data: Dict[str, Any],
        prediction_hours: int
    ) -> Dict[str, Any]:
        """
        Predict flood risk based on precipitation and terrain data.
        Uses physics-informed model combining rainfall and topography.
        
        Args:
            bbox: Bounding box
            precipitation_data: Data from precipitation_service
            terrain_data: Data from terrain_service
            prediction_hours: Hours into future to predict
            
        Returns:
            Dict with flood_probability, risk_level, confidence, factors, risk_zones_geojson
        """
        # Extract precipitation stats
        precip_mm = precipitation_data.get("precipitation_mm", {})
        mean_precip = precip_mm.get("mean", 0)
        max_precip = precip_mm.get("max", 0)
        
        # Extract terrain stats
        elev = terrain_data.get("elevation_m", {})
        mean_elev = elev.get("mean", 100)
        min_elev = elev.get("min", 50)
        slope = terrain_data.get("slope_degrees", {}).get("mean", 5)
        
        # Calculate flood probability components
        # Precipitation factor: higher rainfall = higher risk
        precip_factor = min(1.0, mean_precip / 50.0)
        
        # Terrain factor: lower elevation = higher risk
        terrain_factor = max(0, (150 - min_elev) / 150)
        
        # Slope factor: flatter terrain = higher risk (water accumulates)
        slope_factor = max(0, (10 - slope) / 10)
        
        # Time factor: longer prediction = more uncertainty
        time_factor = min(1.2, 1.0 + prediction_hours * 0.02)
        
        # Combined probability
        flood_probability = (
            0.5 * precip_factor + 
            0.3 * terrain_factor + 
            0.2 * slope_factor
        ) * time_factor
        
        flood_probability = min(0.95, max(0.05, flood_probability))
        
        # Determine risk level
        if flood_probability >= 0.75:
            risk_level = "critical"
        elif flood_probability >= 0.55:
            risk_level = "high"
        elif flood_probability >= 0.35:
            risk_level = "moderate"
        else:
            risk_level = "low"
        
        # Confidence based on data quality
        is_simulated = precipitation_data.get("is_simulated", True)
        confidence = 0.70 if is_simulated else 0.85
        
        # Generate risk zones GeoJSON
        risk_zones = self._generate_risk_zones(bbox, flood_probability, terrain_data)
        
        return {
            "flood_probability": round(flood_probability, 2),
            "risk_level": risk_level,
            "confidence": round(confidence, 2),
            "factors": {
                "precipitation_contribution": round(precip_factor, 2),
                "terrain_contribution": round(terrain_factor, 2),
                "time_factor": round(time_factor, 2)
            },
            "risk_zones_geojson": risk_zones
        }

    def calculate_evacuation_priorities(
        self,
        buildings: List[Any],
        flood_probability: float,
        prediction_hours: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate evacuation priorities for buildings at risk.
        
        Args:
            buildings: List of building objects from OSM
            flood_probability: Overall flood probability
            prediction_hours: Hours until potential flood
            
        Returns:
            List of evacuation priority dicts, sorted by urgency
        """
        priorities = []
        
        # Building type weights (higher = more urgent to evacuate)
        type_weights = {
            "hospital": 1.0,
            "school": 0.9,
            "kindergarten": 0.95,
            "nursing_home": 0.95,
            "apartments": 0.7,
            "residential": 0.6,
            "commercial": 0.4,
            "industrial": 0.3,
            "yes": 0.5,  # Generic building
        }
        
        # People estimates by building type
        people_estimates = {
            "hospital": 400,
            "school": 300,
            "kindergarten": 100,
            "nursing_home": 150,
            "apartments": 200,
            "residential": 6,
            "commercial": 50,
            "industrial": 100,
            "yes": 20,
        }
        
        for building in buildings:
            btype = getattr(building, 'building_type', 'yes') or 'yes'
            weight = type_weights.get(btype, 0.5)
            
            # Calculate evacuation score
            evac_score = flood_probability * weight
            
            # Determine risk level for this building
            if evac_score >= 0.7:
                risk_level = "critical"
            elif evac_score >= 0.5:
                risk_level = "high"
            elif evac_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Estimate time to flood (inverse of risk)
            time_to_flood = prediction_hours * (1 - flood_probability * 0.8)
            
            priorities.append({
                "osm_id": getattr(building, 'osm_id', 0),
                "name": getattr(building, 'name', None),
                "building_type": btype,
                "lat": getattr(building, 'lat', 0),
                "lon": getattr(building, 'lon', 0),
                "risk_level": risk_level,
                "flood_probability": round(flood_probability, 2),
                "evacuation_score": round(evac_score, 2),
                "estimated_time_to_flood_hours": round(time_to_flood, 1),
                "people_estimate": people_estimates.get(btype, 50)
            })
        
        # Sort by evacuation score (highest first)
        priorities.sort(key=lambda x: x["evacuation_score"], reverse=True)
        
        # Return top 10 most critical
        return priorities[:10]

    def _generate_risk_zones(
        self, 
        bbox: List[float], 
        flood_probability: float,
        terrain_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate GeoJSON risk zones based on probability and terrain."""
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Create zones based on probability levels
        features = []
        
        # High risk zone (center, lower elevation)
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
        
        # Create concentric risk zones
        zone_configs = [
            (0.3, "critical" if flood_probability > 0.6 else "high", flood_probability),
            (0.6, "high" if flood_probability > 0.5 else "moderate", flood_probability * 0.8),
            (1.0, "moderate" if flood_probability > 0.4 else "low", flood_probability * 0.5),
        ]
        
        for size_factor, risk_level, prob in zone_configs:
            w = (max_lon - min_lon) * size_factor / 2
            h = (max_lat - min_lat) * size_factor / 2
            
            coords = [[
                [center_lon - w, center_lat - h],
                [center_lon + w, center_lat - h],
                [center_lon + w, center_lat + h],
                [center_lon - w, center_lat + h],
                [center_lon - w, center_lat - h]
            ]]
            
            features.append({
                "type": "Feature",
                "properties": {
                    "flood_probability": round(prob, 2),
                    "risk_level": risk_level
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords
                }
            })
        
        return {"type": "FeatureCollection", "features": features}

    def _predict_mask(self, image: np.ndarray) -> np.ndarray:
        """Predict water mask using K-Means clustering."""
        h, w = image.shape
        X = image.reshape(-1, 1)
        X_scaled = self.scaler.transform(X)
        labels = self.kmeans.predict(X_scaled)
        
        # Water = lower cluster (darker, lower dB)
        centers = self.kmeans.cluster_centers_
        water_label = 0 if centers[0][0] < centers[1][0] else 1
        return (labels == water_label).reshape(h, w)

    def _calculate_physics(self, mask: np.ndarray, dem: np.ndarray):
        """Calculate water depth based on DEM and flooded mask."""
        depth = np.zeros_like(dem, dtype=float)
        risk = np.zeros_like(dem, dtype=np.uint8)
        
        if np.sum(mask) == 0:
            return depth, risk
        
        # Water level = mean elevation of flooded pixels
        water_level = np.mean(dem[mask])
        depth = np.where(mask, np.maximum(0, water_level - dem), 0)
        
        # Risk levels
        risk[depth > 0.1] = 1
        risk[depth > 0.5] = 2
        risk[depth > 1.5] = 3
        
        return depth, risk

    def _simulate_gravity(self, mask: np.ndarray, dem: np.ndarray, steps: int = 3) -> np.ndarray:
        """Simulate water flow using cellular automata."""
        future = mask.copy()
        
        if dem is None or np.max(dem) == np.min(dem):
            return future
        
        for _ in range(steps):
            if np.sum(future) == 0:
                break
            neighbors = binary_dilation(future) & ~future
            avg_water_level = np.mean(dem[future])
            downhill = dem < avg_water_level
            future = future | (neighbors & downhill)
        
        return future

    def _mask_to_geojson(
        self, 
        mask: np.ndarray, 
        bbox: List[float], 
        shape: tuple, 
        props: Dict
    ) -> Dict[str, Any]:
        """Convert binary mask to GeoJSON polygons."""
        h, w = shape
        min_lon, min_lat, max_lon, max_lat = bbox
        transform = rasterio.transform.from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)
        
        features = []
        mask_uint8 = mask.astype('uint8')
        
        for geom, val in rasterio.features.shapes(mask_uint8, transform=transform):
            if val == 1:
                features.append({
                    "type": "Feature",
                    "properties": props.copy(),
                    "geometry": geom
                })
        
        return {"type": "FeatureCollection", "features": features}

    def check_buildings_flooding(
        self, 
        buildings: List[Any], 
        mask: np.ndarray, 
        bbox: List[float]
    ) -> List[Any]:
        """Check which buildings are on flooded pixels."""
        flooded = []
        h, w = mask.shape
        min_lon, min_lat, max_lon, max_lat = bbox
        
        for b in buildings:
            lon = getattr(b, 'lon', 0)
            lat = getattr(b, 'lat', 0)
            
            x = int((lon - min_lon) / (max_lon - min_lon) * w)
            y = int((max_lat - lat) / (max_lat - min_lat) * h)
            
            if 0 <= x < w and 0 <= y < h:
                if mask[y, x]:
                    b.is_flooded = True
                    flooded.append(b)
        
        return flooded


# Singleton instance
flood_detector = FloodDetector()

# Alias for compatibility with router
FloodPredictor = FloodDetector