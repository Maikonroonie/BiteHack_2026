"""
CrisisEye - Flood Detector Service
RandomForest do detekcji powodzi z danych SAR.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from pathlib import Path

from models.schemas import FloodPixelStats, BuildingInfo


class FloodDetector:
    """
    Serwis do wykrywania powodzi z wykorzystaniem RandomForest.
    
    Dla hackathonu używamy prostego modelu zamiast U-Net:
    - Szybsze trenowanie
    - Mniej zależności
    - Wystarczające dla demonstracji
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[RandomForestClassifier] = None
        self.scaler = StandardScaler()
        self.model_path = model_path or "./models_cache/flood_rf_model.joblib"
        
        # Parametry modelu
        self.n_estimators = 100
        self.max_depth = 10
        self.flood_threshold_db = -15.0
        
        # Spróbuj załadować istniejący model
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Ładuje model z dysku lub tworzy nowy z syntetycznymi danymi."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"✅ Loaded flood detection model from {self.model_path}")
                return
            except Exception as e:
                print(f"⚠️ Could not load model: {e}")
        
        # Stwórz model z syntetycznymi danymi (dla hackathonu)
        self._train_synthetic_model()
    
    def _train_synthetic_model(self):
        """
        Trenuje model na syntetycznych danych.
        W prawdziwej aplikacji użylibyśmy prawdziwych danych SAR z labelami.
        """
        print("🔧 Training synthetic flood detection model...")
        
        # Generuj syntetyczne dane treningowe
        n_samples = 10000
        np.random.seed(42)
        
        # Features: [sar_value, change_value, local_variance]
        # Klasa 0: nie-woda, Klasa 1: woda/powódź
        
        # Dane nie-woda (wyższe wartości dB)
        X_land = np.column_stack([
            np.random.normal(-8, 4, n_samples // 2),      # SAR dB
            np.random.normal(0, 2, n_samples // 2),        # change
            np.random.uniform(1, 5, n_samples // 2)        # variance
        ])
        y_land = np.zeros(n_samples // 2)
        
        # Dane woda (niższe wartości dB)
        X_water = np.column_stack([
            np.random.normal(-20, 3, n_samples // 2),     # SAR dB (niższe)
            np.random.normal(-8, 3, n_samples // 2),      # change (spadek)
            np.random.uniform(0.5, 2, n_samples // 2)     # variance (mniejsza)
        ])
        y_water = np.ones(n_samples // 2)
        
        # Połącz
        X = np.vstack([X_land, X_water])
        y = np.hstack([y_land, y_water])
        
        # Przemieszaj
        shuffle_idx = np.random.permutation(len(y))
        X, y = X[shuffle_idx], y[shuffle_idx]
        
        # Normalizacja
        X = self.scaler.fit_transform(X)
        
        # Trenuj model
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X, y)
        
        # Zapisz model
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"✅ Model trained and saved to {self.model_path}")
    
    async def detect_flood(self, sar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wykrywa powódź na podstawie danych SAR.
        
        Args:
            sar_data: Dict z danymi SAR (przed, po, zmiana)
            
        Returns:
            Dict z maską powodzi, GeoJSON i statystykami
        """
        before = sar_data["before"]
        after = sar_data["after"]
        change = sar_data["change"]
        bbox = sar_data["bbox"]
        
        height, width = after.shape
        
        # Przygotuj features dla każdego piksela
        # [sar_value, change_value, local_variance]
        sar_flat = after.flatten()
        change_flat = change.flatten()
        
        # Lokalna wariancja (3x3 okno) - uproszczona
        from scipy.ndimage import generic_filter
        variance = generic_filter(after, np.var, size=3)
        variance_flat = variance.flatten()
        
        X = np.column_stack([sar_flat, change_flat, variance_flat])
        X = self.scaler.transform(X)
        
        # Predykcja
        if self.model:
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]
        else:
            # Fallback - prosta metoda progowa
            predictions = (sar_flat < self.flood_threshold_db).astype(int)
            probabilities = 1 - (sar_flat - (-25)) / 15  # crude probability
            probabilities = np.clip(probabilities, 0, 1)
        
        # Reshape do obrazu
        flood_mask = predictions.reshape((height, width))
        prob_mask = probabilities.reshape((height, width))
        
        # Statystyki
        total_pixels = height * width
        flooded_pixels = int(np.sum(flood_mask))
        flood_percentage = (flooded_pixels / total_pixels) * 100
        
        # Oblicz obszar (przybliżenie)
        pixel_size_km = (sar_data["resolution"] / 1000) ** 2
        area_km2 = total_pixels * pixel_size_km
        flooded_area_km2 = flooded_pixels * pixel_size_km
        
        stats = FloodPixelStats(
            total_pixels=total_pixels,
            flooded_pixels=flooded_pixels,
            flood_percentage=round(flood_percentage, 2),
            area_km2=round(area_km2, 2),
            flooded_area_km2=round(flooded_area_km2, 2)
        )
        
        # Konwertuj do GeoJSON
        geojson = self._mask_to_geojson(flood_mask, prob_mask, bbox)
        
        return {
            "mask": flood_mask,
            "probabilities": prob_mask,
            "stats": stats,
            "geojson": geojson
        }
    
    def _mask_to_geojson(
        self, 
        mask: np.ndarray, 
        prob_mask: np.ndarray,
        bbox: List[float]
    ) -> Dict:
        """
        Konwertuje maskę powodzi do formatu GeoJSON.
        
        Uproszczona wersja - tworzy grid komórek zamiast poligonów.
        """
        features = []
        height, width = mask.shape
        
        # Rozmiar komórki w stopniach
        lon_step = (bbox[2] - bbox[0]) / width
        lat_step = (bbox[3] - bbox[1]) / height
        
        # Próbkuj co N pikseli dla wydajności
        sample_rate = max(1, min(width, height) // 50)
        
        for i in range(0, height, sample_rate):
            for j in range(0, width, sample_rate):
                if mask[i, j]:
                    # Oblicz współrzędne
                    lon = bbox[0] + j * lon_step
                    lat = bbox[3] - i * lat_step  # Y jest odwrócone
                    
                    # Średnia prawdopodobieństwo dla regionu
                    region = prob_mask[i:i+sample_rate, j:j+sample_rate]
                    avg_prob = float(np.mean(region))
                    
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "flood_probability": round(avg_prob, 2),
                            "cell_size_deg": sample_rate * lon_step
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon, lat],
                                [lon + sample_rate * lon_step, lat],
                                [lon + sample_rate * lon_step, lat - sample_rate * lat_step],
                                [lon, lat - sample_rate * lat_step],
                                [lon, lat]
                            ]]
                        }
                    })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def check_buildings_flooding(self, buildings: List[BuildingInfo], flood_mask: np.ndarray, bbox: List[float]) -> List[BuildingInfo]:
        """Sprawdza zalanie budynków na podstawie realnej maski z modelu AI."""
        flooded = []
        rows, cols = flood_mask.shape
        min_lon, min_lat, max_lon, max_lat = bbox

        for b in buildings:
            # Mapowanie współrzędnych lat/lon na indeksy macierzy maski
            col = int((b.lon - min_lon) / (max_lon - min_lon) * cols)
            row = int((max_lat - b.lat) / (max_lat - min_lat) * rows)

            if 0 <= row < rows and 0 <= col < cols:
                if flood_mask[row, col] > 0:  # Jeśli piksel w masce to woda
                    b.is_flooded = True
                    b.flood_probability = float(flood_mask[row, col])
                    flooded.append(b)
        return flooded
