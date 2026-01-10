"""
CrisisEye - Google Earth Engine Service
Integracja z GEE do pobierania danych Sentinel-1.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import date
import asyncio


class GEEService:
    """
    Serwis do integracji z Google Earth Engine.
    
    Pobiera dane Sentinel-1 SAR dla analizy powodzi.
    Wymaga skonfigurowanego konta GEE i credentials.
    """
    
    def __init__(self):
        self.initialized = False
        self.project_id = os.getenv("GEE_PROJECT_ID", "")
        
    async def initialize(self) -> bool:
        """
        Inicjalizuje połączenie z Google Earth Engine.
        
        Returns:
            True jeśli inicjalizacja się powiodła
        """
        if self.initialized:
            return True
            
        try:
            import ee
            
            # Spróbuj uwierzytelnić
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if credentials_path and os.path.exists(credentials_path):
                credentials = ee.ServiceAccountCredentials(
                    email=None,
                    key_file=credentials_path
                )
                ee.Initialize(credentials, project=self.project_id)
            else:
                # Fallback do domyślnej autentykacji
                ee.Initialize(project=self.project_id)
            
            self.initialized = True
            print("✅ Google Earth Engine initialized")
            return True
            
        except ImportError:
            print("⚠️ earthengine-api not installed")
            return False
        except Exception as e:
            print(f"⚠️ GEE initialization failed: {e}")
            return False
    
    async def get_sentinel1_data(
        self,
        bbox: List[float],
        date_start: date,
        date_end: date,
        polarization: str = "VV"
    ) -> Optional[Dict[str, Any]]:
        """
        Pobiera dane Sentinel-1 z GEE.
        
        Args:
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            date_start: Data początkowa
            date_end: Data końcowa
            polarization: Polaryzacja (VV lub VH)
            
        Returns:
            Dict z danymi SAR lub None jeśli błąd
        """
        if not await self.initialize():
            return None
            
        try:
            import ee
            
            # Definiuj region
            region = ee.Geometry.Rectangle(bbox)
            
            # Filtruj kolekcję Sentinel-1
            collection = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(region)
                .filterDate(str(date_start), str(date_end))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
                .select(polarization)
            )
            
            # Sprawdź czy są dostępne obrazy
            count = collection.size().getInfo()
            
            if count == 0:
                print(f"⚠️ No Sentinel-1 images found for {date_start} to {date_end}")
                return None
            
            # Weź medianę dla redukcji szumu
            composite = collection.median()
            
            # Pobierz dane jako numpy array
            # (uproszczone - w produkcji użylibyśmy ee.batch.Export)
            scale = 10  # metry
            
            # Dla hackathonu - zwróć metadane
            return {
                "collection_id": "COPERNICUS/S1_GRD",
                "image_count": count,
                "polarization": polarization,
                "bbox": bbox,
                "date_range": [str(date_start), str(date_end)],
                "scale": scale
            }
            
        except Exception as e:
            print(f"⚠️ GEE query failed: {e}")
            return None
    
    async def get_flood_difference(
        self,
        bbox: List[float],
        date_before: date,
        date_after: date,
        polarization: str = "VV"
    ) -> Optional[Dict[str, Any]]:
        """
        Oblicza różnicę SAR między dwoma datami dla detekcji powodzi.
        
        Args:
            bbox: Bounding box
            date_before: Data przed powodzią
            date_after: Data po powodzi
            polarization: Polaryzacja SAR
            
        Returns:
            Dict z danymi różnicowymi
        """
        if not await self.initialize():
            return None
            
        try:
            import ee
            
            region = ee.Geometry.Rectangle(bbox)
            
            # Obraz przed
            before = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(region)
                .filterDate(str(date_before), str(date_before))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .select(polarization)
                .median()
            )
            
            # Obraz po
            after = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(region)
                .filterDate(str(date_after), str(date_after))
                .filter(ee.Filter.eq('instrumentMode', 'IW'))
                .select(polarization)
                .median()
            )
            
            # Różnica
            difference = after.subtract(before)
            
            return {
                "before_date": str(date_before),
                "after_date": str(date_after),
                "difference_computed": True,
                "bbox": bbox
            }
            
        except Exception as e:
            print(f"⚠️ Flood difference calculation failed: {e}")
            return None


# Singleton instance
gee_service = GEEService()
