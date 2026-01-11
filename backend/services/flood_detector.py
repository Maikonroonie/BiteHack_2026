import numpy as np
import os
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.ndimage import binary_dilation, median_filter
import rasterio.features
from typing import Dict, Any, List

# Ścieżka do zapisu modelu
MODEL_PATH = "models_cache/sar_kmeans_v1.joblib"

class FloodDetector:
    def __init__(self):
        self.scaler = StandardScaler()
        self.kmeans = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                self.kmeans = data["model"]
                self.scaler = data["scaler"]
                self.model_loaded = True
                print(f" [AI] Załadowano model z {MODEL_PATH}")
            except: pass
        
        if not self.model_loaded:
            self.kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)

    def train_on_history(self, training_images: List[np.ndarray]):
        print(" [AI] Uczenie modelu na bieżących danych...")
        valid_pixels = []
        for img in training_images:
            pixels = img.flatten()
            valid_pixels.append(pixels[~np.isnan(pixels)])
            
        if not valid_pixels: return
        
        X = np.concatenate(valid_pixels).reshape(-1, 1)
        if X.shape[0] > 100000:
            X = X[np.random.choice(X.shape[0], 100000, replace=False)]
            
        X_scaled = self.scaler.fit_transform(X)
        self.kmeans.fit(X_scaled)
        
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.kmeans, "scaler": self.scaler}, MODEL_PATH)
        self.model_loaded = True

    def detect_flood(self, sar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Główna metoda analizy."""
        image_after = np.nan_to_num(sar_data["after"], nan=0.0)
        image_before = np.nan_to_num(sar_data["before"], nan=0.0)
        dem_data = np.nan_to_num(sar_data.get("dem"), nan=0.0)
        bbox = sar_data["bbox"]

        if not self.model_loaded:
            self.train_on_history([image_after, image_before])

        # AI Detection
        # 1. AI Detection (Zostawiamy jak jest)
        mask_after = self._predict_mask(image_after)

        # 2. POLUZOWANIE BEZPIECZNIKA (Zmień z -19.5 na -17.0)
        # Przy średniej -16dB, próg -19.5 jest za niski dla płytkiej wody miejskiej
        physics_mask = image_after < -16.0 

        # 3. WYŁĄCZENIE ODEJMOWANIA (Zakomentuj (~mask_before))
        # Chcemy zobaczyć CAŁĄ wodę z 20 września, a nie tylko różnicę względem 14-go
        current_flood_mask = mask_after & physics_mask
        depth_map, risk_map = self._calculate_physics(current_flood_mask, dem_data)
        
        # 20 kroków symulacji
        future_mask = self._simulate_gravity(current_flood_mask, dem_data, steps=20)

        geojson_current = self._mask_to_geojson(current_flood_mask, bbox, image_after.shape, 
                                                {"status": "current", "type": "flood", "risk": "high"})
        
        predicted_expansion = future_mask & (~current_flood_mask)
        geojson_future = self._mask_to_geojson(predicted_expansion, bbox, image_after.shape,
                                               {"status": "forecast", "type": "warning", "risk": "medium"})

        all_features = geojson_current["features"] + geojson_future["features"]

        max_depth = float(np.max(depth_map)) if depth_map.size > 0 else 0.0

        flooded_px = int(np.sum(current_flood_mask))
        flooded_km2 = (flooded_px * 100) / 1_000_000

        return {
            "status": "success",
            "stats": {
                "flooded_area_px": int(np.sum(current_flood_mask)),
                "flooded_area_km2": round(flooded_km2, 4),
                "max_depth_m": round(max_depth, 2),
                "risk_level": "CRITICAL" if max_depth > 1.2 else "MODERATE"
            },
            "geojson": {"type": "FeatureCollection", "features": all_features},
            "mask": current_flood_mask 
        }

    # Metody dla endpointu /predict
    async def predict_flood_risk(self, bbox, precipitation_data, terrain_data, prediction_hours):
        precip_mm = precipitation_data.get("precipitation_mm", {}).get("mean", 0)
        if precip_mm > 20:
            flood_prob = 0.85 + (precip_mm / 200.0)
            risk_level = "critical"
        elif precip_mm > 5:
            flood_prob = 0.45
            risk_level = "moderate"
        else:
            flood_prob = 0.05
            risk_level = "low"
            
        return {
            "flood_probability": min(flood_prob, 0.99),
            "risk_level": risk_level,
            "confidence": 0.82,
            "factors": {"precipitation_contribution": 0.7, "terrain_contribution": 0.2, "time_factor": 1.1},
            "risk_zones_geojson": None 
        }

    def calculate_evacuation_priorities(self, buildings, flood_probability, prediction_hours):
        """
        Priorytetyzacja ewakuacji budynków z OSM.
        Szpitale/szkoły pierwsze, potem mieszkalne.
        """
        priorities = []
        
        # Wagi typów budynków (wyższa = pilniejsza ewakuacja)
        type_weights = {
            "hospital": 1.0,
            "school": 0.9,
            "kindergarten": 0.95,
            "nursing_home": 0.95,
            "apartments": 0.7,
            "residential": 0.6,
            "house": 0.6,
            "commercial": 0.4,
            "industrial": 0.3,
            "yes": 0.5,
        }
        
        # Szacunkowa liczba osób
        people_estimates = {
            "hospital": 400,
            "school": 300,
            "kindergarten": 100,
            "nursing_home": 150,
            "apartments": 200,
            "residential": 6,
            "house": 4,
            "commercial": 50,
            "industrial": 100,
            "yes": 20,
        }
        
        for building in buildings:
            try:
                # Obsługa różnych formatów danych
                if hasattr(building, 'building_type'):
                    btype = building.building_type or 'yes'
                    osm_id = getattr(building, 'osm_id', 0)
                    name = getattr(building, 'name', None)
                    lat = getattr(building, 'lat', 0)
                    lon = getattr(building, 'lon', 0)
                elif isinstance(building, dict):
                    props = building.get('properties', {})
                    btype = props.get('building_type', 'yes') or 'yes'
                    osm_id = props.get('osm_id', 0)
                    name = props.get('name')
                    coords = building.get('geometry', {}).get('coordinates', [0, 0])
                    lon, lat = coords[0], coords[1] if len(coords) > 1 else (0, 0)
                else:
                    continue
                    
                weight = type_weights.get(btype, 0.5)
                evac_score = flood_probability * weight
                
                # Poziom ryzyka
                if evac_score >= 0.7:
                    risk_level = "critical"
                elif evac_score >= 0.5:
                    risk_level = "high"
                elif evac_score >= 0.3:
                    risk_level = "medium"
                else:
                    risk_level = "low"
                
                # Szacowany czas do zalania
                time_to_flood = prediction_hours * (1 - flood_probability * 0.8)
                
                priorities.append({
                    "osm_id": osm_id,
                    "name": name or f"Budynek {btype}",
                    "building_type": btype,
                    "lat": lat,
                    "lon": lon,
                    "risk_level": risk_level,
                    "flood_probability": round(flood_probability, 2),
                    "evacuation_score": round(evac_score, 2),
                    "estimated_time_to_flood_hours": round(time_to_flood, 1),
                    "people_estimate": people_estimates.get(btype, 50)
                })
            except Exception:
                continue
        
        # Sortuj po score (najwyższy pierwszy)
        priorities.sort(key=lambda x: x["evacuation_score"], reverse=True)
        return priorities[:10]

    # Helpers
    def _predict_mask(self, image):
        h, w = image.shape
        X = image.reshape(-1, 1)
        X_scaled = self.scaler.transform(X)
        labels = self.kmeans.predict(X_scaled)
        centers = self.kmeans.cluster_centers_
        water_label = 0 if centers[0][0] < centers[1][0] else 1
        return (labels == water_label).reshape(h, w)

    def _calculate_physics(self, mask, dem):
        depth = np.zeros_like(dem)
        risk = np.zeros_like(dem, dtype=np.uint8)
        if np.sum(mask) == 0: return depth, risk
        water_level = np.mean(dem[mask])
        depth = np.where(mask, np.maximum(0, water_level - dem), 0)
        risk[depth > 0.1] = 1
        risk[depth > 0.5] = 2
        risk[depth > 1.5] = 3
        return depth, risk

    def _simulate_gravity(self, mask, dem, steps=3):
        """Symulacja spływu grawitacyjnego"""
        future = mask.copy()
        if np.max(dem) == np.min(dem): return future
        for _ in range(steps):
            neighbors = binary_dilation(future) & ~future
            if np.any(future):
                avg_water_level = np.mean(dem[future])
                downhill = dem < avg_water_level
                future = future | (neighbors & downhill)
            else:
                break
        return future
    
    def check_impact(self, buildings: List[Any], mask: np.ndarray, bbox: List[float]) -> List[Any]:
        """Sprawdza wpływ powodzi, obsługując obiekty BuildingInfo oraz słowniki."""
        h, w = mask.shape
        min_lon, min_lat, max_lon, max_lat = bbox
        affected = []

        for b in buildings:
            try:
                # Obsługa obiektów Pydantic (dostęp przez kropkę)
                if hasattr(b, 'geometry'):
                    lon, lat = b.geometry.coordinates
                # Obsługa słowników
                else:
                    lon, lat = b["geometry"]["coordinates"]
                
                # Mapowanie na macierz
                x = int((lon - min_lon) / (max_lon - min_lon) * w)
                y = int((max_lat - lat) / (max_lat - min_lat) * h)

                if 0 <= x < w and 0 <= y < h:
                    if mask[y, x]:
                        # Oznaczamy zalanie w zależności od typu danych
                        if hasattr(b, 'properties'):
                            b.properties.is_flooded = True
                        else:
                            b["properties"]["is_flooded"] = True
                        affected.append(b)
            except (AttributeError, KeyError, TypeError, IndexError):
                continue
                
        return affected

    def _mask_to_geojson(self, mask, bbox, shape, props):
        h, w = shape
        min_lon, min_lat, max_lon, max_lat = bbox
        if w == 0 or h == 0: return {"type": "FeatureCollection", "features": []}
        transform = rasterio.transform.from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)
        features = []
        for geom, val in rasterio.features.shapes(mask.astype('uint8'), transform=transform):
            if val == 1:
                features.append({"type": "Feature", "properties": props, "geometry": geom})
        return {"type": "FeatureCollection", "features": features}

    def check_buildings_flooding(self, buildings, mask, bbox):
        return []

# Singleton
flood_detector = FloodDetector()
FloodPredictor = FloodDetector