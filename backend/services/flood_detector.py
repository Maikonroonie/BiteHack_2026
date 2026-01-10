"""
CrisisEye - Flood Predictor Service
AI-powered flood prediction using precipitation, terrain, and ML.

NOWCASTING: Predykcja powodzi w czasie rzeczywistym na podstawie:
- Aktualnych opadów (GPM satellite)
- Ukształtowania terenu (DEM)
- Historycznych wzorców powodzi
"""

import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os
from pathlib import Path
from datetime import datetime

from models.schemas import FloodPixelStats, BuildingInfo


class FloodPredictor:
    """
    Serwis do PREDYKCJI powodzi z wykorzystaniem ML.
    
    Różnica vs stary FloodDetector:
    - Stary: "Czy piksel jest zalany?" (detekcja)
    - Nowy: "Jaka jest szansa zalania za X godzin?" (predykcja)
    
    Features dla modelu:
    1. Akumulacja opadów (1h, 3h, 6h, 24h)
    2. Wysokość terenu (m n.p.m.)
    3. Nachylenie terenu (stopnie)
    4. Odległość od rzeki (km)
    5. Przepuszczalność gleby (0-1)
    6. Flow accumulation (ile wody spływa do punktu)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.prediction_model: Optional[GradientBoostingRegressor] = None
        self.scaler = StandardScaler()
        self.model_path = model_path or "./models_cache/flood_predictor.joblib"
        
        # Feature names dla interpretacji
        self.feature_names = [
            "precipitation_1h",
            "precipitation_3h", 
            "precipitation_6h",
            "precipitation_24h",
            "elevation_m",
            "slope_deg",
            "distance_to_river_km",
            "soil_permeability",
            "flow_accumulation",
            "soil_saturation"
        ]
        
        # Wagi dla różnych typów budynków (priorytet ewakuacji)
        self.building_priority = {
            "hospital": 1.0,
            "school": 0.95,
            "kindergarten": 0.95,
            "nursing_home": 0.9,
            "apartments": 0.7,
            "residential": 0.6,
            "commercial": 0.4,
            "industrial": 0.3,
            "warehouse": 0.2,
        }
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Ładuje model lub tworzy nowy z fizycznie realistycznymi danymi."""
        if os.path.exists(self.model_path):
            try:
                saved = joblib.load(self.model_path)
                self.prediction_model = saved["model"]
                self.scaler = saved["scaler"]
                print(f"✅ Loaded flood predictor from {self.model_path}")
                return
            except Exception as e:
                print(f"⚠️ Could not load model: {e}")
        
        self._train_physics_based_model()
    
    def _train_physics_based_model(self):
        """
        Trenuje model na danych opartych na fizyce spływu wody.
        
        W przeciwieństwie do czystych losowych danych, ten model
        uczy się prawdziwych zależności:
        - Więcej opadów = większe ryzyko
        - Niżej położony teren = większe ryzyko
        - Większy flow accumulation = większe ryzyko
        """
        print("🔧 Training physics-based flood prediction model...")
        
        n_samples = 20000
        np.random.seed(42)
        
        # Generuj realistyczne features
        # Opady (mm) - różne intensywności
        precip_1h = np.abs(np.random.exponential(5, n_samples))
        precip_3h = precip_1h * np.random.uniform(1.5, 3.0, n_samples)
        precip_6h = precip_3h * np.random.uniform(1.2, 2.0, n_samples)
        precip_24h = precip_6h * np.random.uniform(1.5, 4.0, n_samples)
        
        # Teren
        elevation = np.random.uniform(100, 500, n_samples)  # m n.p.m.
        slope = np.random.exponential(3, n_samples)  # stopnie
        distance_river = np.random.exponential(2, n_samples)  # km
        soil_permeability = np.random.uniform(0.1, 0.9, n_samples)
        flow_accumulation = np.random.exponential(100, n_samples)
        soil_saturation = np.random.uniform(0.2, 0.95, n_samples)
        
        # Target: Prawdopodobieństwo zalania (0-1)
        # Fizyczny model:
        # P(flood) = f(precipitation, terrain, soil)
        
        # Efektywne opady (uwzględniając nasycenie gleby)
        effective_precip = precip_6h * (0.3 + 0.7 * soil_saturation) * (1 - soil_permeability)
        
        # Podatność terenu (niżej + płasko = gorzej)
        terrain_risk = (1 - elevation / 500) * (1 - slope / 30) * (1 / (1 + distance_river))
        
        # Flow accumulation factor
        flow_factor = np.log1p(flow_accumulation) / 10
        
        # Combine factors into flood probability
        raw_probability = (
            0.3 * (effective_precip / 50) +  # Opady
            0.3 * terrain_risk +              # Teren
            0.2 * flow_factor +               # Spływ
            0.2 * soil_saturation             # Wilgotność
        )
        
        # Dodaj szum i ogranicz do [0, 1]
        flood_probability = np.clip(
            raw_probability + np.random.normal(0, 0.05, n_samples),
            0, 1
        )
        
        # Przygotuj features
        X = np.column_stack([
            precip_1h, precip_3h, precip_6h, precip_24h,
            elevation, slope, distance_river,
            soil_permeability, flow_accumulation, soil_saturation
        ])
        
        # Normalizacja
        X_scaled = self.scaler.fit_transform(X)
        
        # Trenuj model regresji (nie klasyfikacji!)
        self.prediction_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.prediction_model.fit(X_scaled, flood_probability)
        
        # Zapisz
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.prediction_model,
            "scaler": self.scaler
        }, self.model_path)
        
        print(f"✅ Physics-based model trained and saved to {self.model_path}")
        
        # Wypisz ważność cech
        importances = self.prediction_model.feature_importances_
        for name, imp in sorted(zip(self.feature_names, importances), key=lambda x: -x[1]):
            print(f"   {name}: {imp:.3f}")
    
    async def predict_flood_risk(
        self,
        bbox: List[float],
        precipitation_data: Dict[str, Any],
        terrain_data: Dict[str, Any],
        prediction_hours: int = 6
    ) -> Dict[str, Any]:
        """
        Przewiduje ryzyko powodzi dla obszaru.
        
        Args:
            bbox: Bounding box
            precipitation_data: Dane z PrecipitationService
            terrain_data: Dane z TerrainService
            prediction_hours: Za ile godzin przewidywać
            
        Returns:
            Dict z predykcją i mapą ryzyka
        """
        # Przygotuj features
        precip = precipitation_data.get("precipitation_mm", {})
        elev = terrain_data.get("elevation_m", {})
        
        # Symuluj dodatkowe features (w produkcji z prawdziwych danych)
        np.random.seed(int(bbox[0] * 1000) % 10000)
        
        features = np.array([[
            precip.get("mean", 0) * 0.3,  # 1h estimate
            precip.get("mean", 0),         # 3h
            precip.get("mean", 0) * 2,     # 6h projection
            precip.get("mean", 0) * 6,     # 24h projection
            elev.get("mean", 200),
            terrain_data.get("slope_degrees", {}).get("mean", 3),
            np.random.uniform(0.5, 5),     # distance_river_km
            np.random.uniform(0.3, 0.7),   # soil_permeability
            np.random.uniform(50, 500),    # flow_accumulation
            np.random.uniform(0.4, 0.8),   # soil_saturation
        ]])
        
        # Predykcja
        X_scaled = self.scaler.transform(features)
        base_probability = float(self.prediction_model.predict(X_scaled)[0])
        
        # Adjust for prediction horizon (dalej = więcej niepewności)
        time_factor = 1 + (prediction_hours / 24) * 0.2
        adjusted_probability = min(base_probability * time_factor, 0.99)
        
        # Determine risk level
        if adjusted_probability < 0.2:
            risk_level = "low"
        elif adjusted_probability < 0.4:
            risk_level = "moderate"
        elif adjusted_probability < 0.7:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        # Generate risk zones GeoJSON
        risk_zones = self._generate_risk_zones(bbox, adjusted_probability)
        
        return {
            "bbox": bbox,
            "prediction_hours": prediction_hours,
            "timestamp": datetime.utcnow().isoformat(),
            "flood_probability": round(adjusted_probability, 3),
            "risk_level": risk_level,
            "confidence": round(0.85 - prediction_hours * 0.02, 2),
            "risk_zones_geojson": risk_zones,
            "factors": {
                "precipitation_contribution": round(precip.get("mean", 0) / 50, 2),
                "terrain_contribution": round((500 - elev.get("mean", 200)) / 500, 2),
                "time_factor": round(time_factor, 2)
            }
        }
    
    def _generate_risk_zones(
        self,
        bbox: List[float],
        base_probability: float
    ) -> Dict[str, Any]:
        """Generuje GeoJSON z zonami ryzyka."""
        features = []
        
        # Podziel obszar na komórki
        n_cells = 5
        lon_step = (bbox[2] - bbox[0]) / n_cells
        lat_step = (bbox[3] - bbox[1]) / n_cells
        
        np.random.seed(int(base_probability * 1000))
        
        for i in range(n_cells):
            for j in range(n_cells):
                # Losowa wariacja wokół bazowego prawdopodobieństwa
                local_prob = base_probability * np.random.uniform(0.6, 1.4)
                local_prob = np.clip(local_prob, 0, 1)
                
                if local_prob > 0.2:  # Tylko znaczące ryzyka
                    lon = bbox[0] + j * lon_step
                    lat = bbox[1] + i * lat_step
                    
                    if local_prob < 0.4:
                        risk = "moderate"
                    elif local_prob < 0.7:
                        risk = "high"
                    else:
                        risk = "critical"
                    
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "flood_probability": round(local_prob, 2),
                            "risk_level": risk
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon, lat],
                                [lon + lon_step, lat],
                                [lon + lon_step, lat + lat_step],
                                [lon, lat + lat_step],
                                [lon, lat]
                            ]]
                        }
                    })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def calculate_evacuation_priorities(
        self,
        buildings: List[BuildingInfo],
        flood_probability: float,
        prediction_hours: int
    ) -> List[Dict[str, Any]]:
        """
        Oblicza priorytety ewakuacji dla budynków.
        
        Ranking oparty na:
        1. Typ budynku (szpital > szkoła > mieszkania > magazyn)
        2. Prawdopodobieństwo zalania
        3. Szacunkowa liczba osób
        """
        priorities = []
        
        for building in buildings:
            building_type = building.building_type.lower()
            type_priority = self.building_priority.get(building_type, 0.5)
            
            # Lokalne prawdopodobieństwo (symulacja pozycji)
            np.random.seed(building.osm_id % 10000)
            local_flood_prob = flood_probability * np.random.uniform(0.5, 1.5)
            local_flood_prob = np.clip(local_flood_prob, 0, 1)
            
            # Tylko budynki z realnym ryzykiem
            if local_flood_prob < 0.3:
                continue
            
            # Score = ryzyko * priorytet typu budynku
            evacuation_score = local_flood_prob * type_priority
            
            # Szacunkowa liczba osób
            people_estimates = {
                "hospital": np.random.randint(100, 500),
                "school": np.random.randint(200, 800),
                "kindergarten": np.random.randint(30, 100),
                "apartments": np.random.randint(50, 200),
                "residential": np.random.randint(2, 6),
                "commercial": np.random.randint(10, 50),
            }
            people = people_estimates.get(building_type, np.random.randint(5, 20))
            
            # Szacowany czas do zalania
            time_to_flood = prediction_hours * (1 - local_flood_prob) + 0.5
            
            # Określ poziom ryzyka
            if evacuation_score > 0.7:
                risk_level = "critical"
            elif evacuation_score > 0.5:
                risk_level = "high"
            elif evacuation_score > 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            priorities.append({
                "osm_id": building.osm_id,
                "name": building.name or f"Budynek {building_type}",
                "building_type": building_type,
                "lat": building.lat,
                "lon": building.lon,
                "risk_level": risk_level,
                "flood_probability": round(local_flood_prob, 2),
                "evacuation_score": round(evacuation_score, 3),
                "estimated_time_to_flood_hours": round(time_to_flood, 1),
                "people_estimate": people
            })
        
        # Sortuj według evacuation_score (malejąco)
        priorities.sort(key=lambda x: -x["evacuation_score"])
        
        return priorities[:20]  # Top 20 priorytetów


# Legacy compatibility - map old name to new
FloodDetector = FloodPredictor

# Singleton instance
flood_predictor = FloodPredictor()
