"""
CrisisEye - Google Earth Engine Service
Integracja z GEE do pobierania realnych danych Sentinel-1 SAR i DEM.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import date
import numpy as np
import ee

class GEEService:
    """
    Serwis do integracji z Google Earth Engine.
    Pobiera realne macierze pikseli dla modelu RandomForest[cite: 755, 757].
    """
    
    def __init__(self):
        self.initialized = False
        self.project_id = os.getenv("GEE_PROJECT_ID", "natural-cistern-305412") # Wpisz swój projekt
        
    async def initialize(self) -> bool:
        """Inicjalizuje połączenie z GEE przy użyciu poświadczeń systemowych."""
        if self.initialized:
            return True
            
        try:
            # Próba inicjalizacji (zakłada wykonane 'earthengine authenticate')
            ee.Initialize(project=self.project_id)
            self.initialized = True
            print("✅ Google Earth Engine initialized")
            return True
        except Exception as e:
            print(f"⚠️ GEE initialization failed: {e}. Run 'earthengine authenticate'.")
            return False

    async def get_sar_pixels(
        self,
        bbox: List[float],
        target_date: date,
        polarization: str = "VV"
    ) -> Optional[np.ndarray]:
        """
        Pobiera realne wartości dB dla zadanego obszaru.
        Konwertuje obiekt ee.Image na macierz NumPy.
        """
        if not await self.initialize():
            return None

        try:
            region = ee.Geometry.Rectangle(bbox)
            
            # Pobieranie najbliższej dostępnej sceny S1 [cite: 754, 1107]
            img = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(region)
                .filterDate(str(target_date.replace(day=1)), str(target_date))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .select(polarization)
                .median()
                .clip(region))

            # Pobieranie danych jako macierz (limit dla getInfo to ~10MB)
            # Przy skali 10m i małym BBOX (hackathon) zadziała idealnie [cite: 978]
            data = img.sampleRectangle(region=region, defaultValue=0).get(polarization).getInfo()
            return np.array(data)
            
        except Exception as e:
            print(f"⚠️ Failed to fetch SAR pixels: {e}")
            return None

    async def get_terrain_elevation(self, bbox: List[float]) -> Optional[np.ndarray]:
        """
        Pobiera dane wysokościowe DEM (SRTM) dla obliczenia głębokości wody[cite: 1095].
        """
        if not await self.initialize():
            return None

        try:
            region = ee.Geometry.Rectangle(bbox)
            # Pobieramy dane SRTM 30m [cite: 1109]
            dem = ee.Image("USGS/SRTMGL1_003").clip(region)
            
            # Konwersja do macierzy NumPy
            data = dem.sampleRectangle(region=region, defaultValue=0).get('elevation').getInfo()
            return np.array(data)
        except Exception as e:
            print(f"⚠️ Failed to fetch DEM: {e}")
            return None

    async def get_flood_analysis_data(
        self,
        bbox: List[float],
        date_before: date,
        date_after: date,
        polarization: str = "VV"
    ) -> Optional[Dict[str, Any]]:
        """
        Kompletny zestaw danych dla FloodDetector.
        Zwraca realne macierze przed i po powodzi [cite: 764-765].
        """
        before_pixels = await self.get_sar_pixels(bbox, date_before, polarization)
        after_pixels = await self.get_sar_pixels(bbox, date_after, polarization)
        
        if before_pixels is None or after_pixels is None:
            return None

        # Obliczanie log-ratio (różnica dB) zgodnie z PRD [cite: 631-633]
        change_pixels = after_pixels - before_pixels
        
        return {
            "before": before_pixels,
            "after": after_pixels,
            "change": change_pixels,
            "bbox": bbox,
            "resolution": 10 # Sentinel-1 resolution [cite: 756]
        }
    
    async def get_terrain_and_rain(self, bbox: List[float]) -> dict:
        """Pobiera dane wysokościowe i opady z GEE."""
        if not await self.initialize():
            return {}
        try:
            import ee
            region = ee.Geometry.Rectangle(bbox)
            
            # Pobieramy DEM (SRTM)
            dem = ee.Image("USGS/SRTMGL1_003").clip(region)
            elev_stats = dem.reduceRegion(ee.Reducer.mean(), region, 30).getInfo()
            
            # Pobieramy Opady (GPM)
            rain = (ee.ImageCollection("NASA/GPM_L3/IMERG_V06")
                    .filterBounds(region)
                    .sort('system:time_start', False).first()
                    .select('precipitationCal'))
            rain_stats = rain.reduceRegion(ee.Reducer.mean(), region, 11132).getInfo()
            
            return {
                "avg_elevation": elev_stats.get('elevation', 0),
                "current_rainfall": rain_stats.get('precipitationCal', 0)
            }
        except Exception as e:
            print(f"⚠️ GEE data fetch failed: {e}")
            return {}

# Singleton instance
gee_service = GEEService()