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
    """
    AI + Physics Engine.
    Wersja dostosowana do danych z Microsoft Planetary Computer.
    """
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
                print(f"✅ [AI] Załadowano model z {MODEL_PATH}")
            except: pass
        
        if not self.model_loaded:
            self.kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)

    def train_on_history(self, training_images: List[np.ndarray]):
        print("🔄 [AI] Uczenie modelu na bieżących danych...")
        # Spłaszczamy dane i usuwamy NaNy
        valid_pixels = []
        for img in training_images:
            pixels = img.flatten()
            valid_pixels.append(pixels[~np.isnan(pixels)])
            
        if not valid_pixels: return # Puste dane
        
        X = np.concatenate(valid_pixels).reshape(-1, 1)
        # Trenujemy na próbce (żeby było szybko), max 100k pikseli
        if X.shape[0] > 100000:
            X = X[np.random.choice(X.shape[0], 100000, replace=False)]
            
        X_scaled = self.scaler.fit_transform(X)
        self.kmeans.fit(X_scaled)
        
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.kmeans, "scaler": self.scaler}, MODEL_PATH)
        self.model_loaded = True

    def detect_flood(self, sar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Główna metoda analizy.
        Teraz DEM wyciągamy bezpośrednio z sar_data.
        """
        # 1. Rozpakowanie danych
        image_after = np.nan_to_num(sar_data["after"], nan=0.0)
        image_before = np.nan_to_num(sar_data["before"], nan=0.0)
        dem_data = np.nan_to_num(sar_data.get("dem"), nan=0.0)
        bbox = sar_data["bbox"]

        # 2. Trening online (jeśli trzeba)
        if not self.model_loaded:
            self.train_on_history([image_after, image_before])

        # 3. Detekcja (K-Means)
        mask_after = self._predict_mask(image_after)
        mask_before = self._predict_mask(image_before)

        # Jeśli piksel jest jaśniejszy niż -15 dB, to nie jest głęboka woda.
        # To eliminuje fałszywe alarmy na polach i budynkach.
        physics_mask = image_after < -15.0

        # 4. Change Detection (AI + Fizyka + Brak wody wcześniej)
        current_flood_mask = mask_after & (~mask_before) & physics_mask
        current_flood_mask = median_filter(current_flood_mask, size=3) # Usuwanie szumu

        # 5. Fizyka (Grawitacja + Głębokość)
        depth_map, risk_map = self._calculate_physics(current_flood_mask, dem_data)
        future_mask = self._simulate_gravity(current_flood_mask, dem_data)

        # 6. Generowanie GeoJSON
        geojson_current = self._mask_to_geojson(current_flood_mask, bbox, image_after.shape, 
                                                {"status": "current", "type": "flood", "risk": "high"})
        
        predicted_expansion = future_mask & (~current_flood_mask)
        geojson_future = self._mask_to_geojson(predicted_expansion, bbox, image_after.shape,
                                               {"status": "forecast", "type": "warning", "risk": "medium"})

        all_features = geojson_current["features"] + geojson_future["features"]

        # Zabezpieczenie statystyk (gdyby mapa była pusta)
        max_depth = float(np.max(depth_map)) if depth_map.size > 0 else 0.0

        return {
            "status": "success",
            "stats": {
                "flooded_area_px": int(np.sum(current_flood_mask)),
                "max_depth_m": round(max_depth, 2),
                "risk_level": "CRITICAL" if max_depth > 1.2 else "MODERATE"
            },
            "geojson": {"type": "FeatureCollection", "features": all_features},
            # Kompatybilność z frontendem
            "mask": current_flood_mask 
        }

    def _predict_mask(self, image):
        h, w = image.shape
        X = image.reshape(-1, 1)
        X_scaled = self.scaler.transform(X)
        labels = self.kmeans.predict(X_scaled)
        # Woda = niższy klaster (ciemniejszy, mniej dB)
        centers = self.kmeans.cluster_centers_
        water_label = 0 if centers[0][0] < centers[1][0] else 1
        return (labels == water_label).reshape(h, w)

    def _calculate_physics(self, mask, dem):
        # Obliczanie głębokości
        depth = np.zeros_like(dem)
        risk = np.zeros_like(dem, dtype=np.uint8)
        if np.sum(mask) == 0: return depth, risk
        
        # Proste założenie: poziom wody to średnia wysokość zalanych pikseli
        water_level = np.mean(dem[mask])
        depth = np.where(mask, np.maximum(0, water_level - dem), 0)
        
        risk[depth > 0.1] = 1
        risk[depth > 0.5] = 2
        risk[depth > 1.5] = 3
        return depth, risk

    def _simulate_gravity(self, mask, dem, steps=3):
        # Automat komórkowy: woda płynie w dół
        future = mask.copy()
        if np.max(dem) == np.min(dem): return future # Płaski teren, brak przepływu
        
        for _ in range(steps):
            neighbors = binary_dilation(future) & ~future
            # Warunek: teren sąsiada musi być niższy niż średni poziom wody obok
            avg_water_level = np.mean(dem[future])
            downhill = dem < avg_water_level
            future = future | (neighbors & downhill)
        return future

    def _mask_to_geojson(self, mask, bbox, shape, props):
        h, w = shape
        min_lon, min_lat, max_lon, max_lat = bbox
        transform = rasterio.transform.from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)
        features = []
        # Optymalizacja: upraszczamy kształty, żeby nie zabić przeglądarki
        for geom, val in rasterio.features.shapes(mask.astype('uint8'), transform=transform):
            if val == 1:
                features.append({"type": "Feature", "properties": props, "geometry": geom})
        return {"type": "FeatureCollection", "features": features}

    # Metoda kompatybilności dla Routera
    def check_buildings_flooding(self, buildings, mask, bbox):
        # Szybka weryfikacja czy budynek jest na zalanym pikselu
        flooded = []
        h, w = mask.shape
        min_lon, min_lat, max_lon, max_lat = bbox
        
        for b in buildings:
            # Mapowanie Lat/Lon -> X/Y
            x = int((b.lon - min_lon) / (max_lon - min_lon) * w)
            y = int((max_lat - b.lat) / (max_lat - min_lat) * h) # Y odwrócone
            
            if 0 <= x < w and 0 <= y < h:
                if mask[y, x]:
                    b.is_flooded = True
                    flooded.append(b)
        return flooded

# Singleton
flood_detector = FloodDetector()

FloodPredictor = FloodDetector