"""
CrisisEye - Precipitation Service (GPM)
Pobieranie danych opadowych z NASA GPM przez Google Earth Engine.

GPM (Global Precipitation Measurement) dostarcza dane opadowe co 30 minut,
co pozwala na nowcasting powodzi bez czekania na zdjęcia SAR.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np


class PrecipitationService:
    """
    Serwis do pobierania danych opadowych z NASA GPM.
    
    Dane używane do:
    - Aktualnych opadów (co 30 min)
    - Akumulacji opadów (3h, 6h, 24h)
    - Predykcji ryzyka powodzi
    """
    
    def __init__(self):
        self.initialized = False
        self.project_id = os.getenv("GEE_PROJECT_ID", "")
        # GPM IMERG collection ID
        self.gpm_collection = "NASA/GPM_L3/IMERG_V06"
        
    async def initialize(self) -> bool:
        """Inicjalizuje połączenie z Google Earth Engine."""
        if self.initialized:
            return True
            
        try:
            import ee
            
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if credentials_path and os.path.exists(credentials_path):
                credentials = ee.ServiceAccountCredentials(
                    email=None,
                    key_file=credentials_path
                )
                ee.Initialize(credentials, project=self.project_id)
            else:
                ee.Initialize(project=self.project_id)
            
            self.initialized = True
            print("✅ Precipitation Service (GPM) initialized")
            return True
            
        except ImportError:
            print("⚠️ earthengine-api not installed - using simulated data")
            return False
        except Exception as e:
            print(f"⚠️ GEE initialization failed: {e} - using simulated data")
            return False
    
    async def get_current_precipitation(
        self,
        bbox: List[float],
        hours_back: int = 3
    ) -> Dict[str, Any]:
        """
        Pobiera aktualne dane opadowe dla obszaru.
        
        Args:
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            hours_back: Ile godzin wstecz analizować
            
        Returns:
            Dict z danymi opadowymi
        """
        if await self.initialize():
            return await self._get_gpm_data(bbox, hours_back)
        else:
            return self._get_simulated_data(bbox, hours_back)
    
    async def _get_gpm_data(
        self,
        bbox: List[float],
        hours_back: int
    ) -> Dict[str, Any]:
        """Pobiera prawdziwe dane z GPM przez GEE."""
        try:
            import ee
            
            region = ee.Geometry.Rectangle(bbox)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=hours_back)
            
            # Pobierz kolekcję GPM IMERG
            collection = (ee.ImageCollection(self.gpm_collection)
                .filterBounds(region)
                .filterDate(start_date.isoformat(), end_date.isoformat())
                .select('precipitationCal')  # Skalibrowane opady
            )
            
            count = collection.size().getInfo()
            
            if count == 0:
                print(f"⚠️ No GPM data for last {hours_back}h - using simulation")
                return self._get_simulated_data(bbox, hours_back)
            
            # Suma opadów w okresie (mm)
            total_precip = collection.sum()
            
            # Oblicz statystyki dla regionu
            stats = total_precip.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.max(), sharedInputs=True
                ).combine(
                    ee.Reducer.min(), sharedInputs=True
                ),
                geometry=region,
                scale=10000,  # 10km resolution
                maxPixels=1e9
            ).getInfo()
            
            return {
                "source": "NASA_GPM_IMERG",
                "bbox": bbox,
                "hours_analyzed": hours_back,
                "timestamp": datetime.utcnow().isoformat(),
                "precipitation_mm": {
                    "mean": round(stats.get("precipitationCal_mean", 0), 2),
                    "max": round(stats.get("precipitationCal_max", 0), 2),
                    "min": round(stats.get("precipitationCal_min", 0), 2)
                },
                "image_count": count,
                "is_simulated": False
            }
            
        except Exception as e:
            print(f"⚠️ GPM query failed: {e}")
            return self._get_simulated_data(bbox, hours_back)
    
    def _get_simulated_data(
        self,
        bbox: List[float],
        hours_back: int
    ) -> Dict[str, Any]:
        """
        Generuje symulowane dane opadowe.
        
        Dla hackathonu - realistyczna symulacja gdy brak dostępu do GEE.
        Model oparty na typowych wzorcach opadów w Polsce.
        """
        # Deterministyczny seed oparty na lokalizacji (nie na czasie!)
        seed = int(abs(bbox[0] * 1000 + bbox[1] * 10000 + bbox[2] * 100 + bbox[3] * 1)) % 10000
        np.random.seed(seed)
        
        # Symulacja realistycznych opadów (mm)
        # Lekkie: 0-5mm, Umiarkowane: 5-20mm, Silne: 20-50mm, Intensywne: >50mm
        intensity = np.random.choice(
            ["light", "moderate", "heavy", "intense"],
            p=[0.5, 0.3, 0.15, 0.05]
        )
        
        intensity_ranges = {
            "light": (0, 5),
            "moderate": (5, 20),
            "heavy": (20, 50),
            "intense": (50, 100)
        }
        
        low, high = intensity_ranges[intensity]
        mean_precip = np.random.uniform(low, high)
        max_precip = mean_precip * np.random.uniform(1.2, 2.0)
        min_precip = mean_precip * np.random.uniform(0.3, 0.8)
        
        return {
            "source": "SIMULATED",
            "bbox": bbox,
            "hours_analyzed": hours_back,
            "timestamp": datetime.utcnow().isoformat(),
            "precipitation_mm": {
                "mean": round(mean_precip, 2),
                "max": round(max_precip, 2),
                "min": round(min_precip, 2)
            },
            "intensity": intensity,
            "is_simulated": True,
            "note": "Simulated data - GEE not available"
        }
    
    async def get_precipitation_accumulation(
        self,
        bbox: List[float]
    ) -> Dict[str, float]:
        """
        Oblicza akumulację opadów dla różnych okresów.
        
        Returns:
            Dict z akumulacją: 1h, 3h, 6h, 12h, 24h
        """
        accumulation = {}
        
        for hours in [1, 3, 6, 12, 24]:
            data = await self.get_current_precipitation(bbox, hours)
            accumulation[f"{hours}h"] = data["precipitation_mm"]["mean"]
        
        return accumulation
    
    def calculate_flood_risk_from_precipitation(
        self,
        precipitation_mm: float,
        soil_saturation: float = 0.5
    ) -> Dict[str, Any]:
        """
        Oblicza ryzyko powodzi na podstawie opadów.
        
        Args:
            precipitation_mm: Opady w mm (suma z ostatnich godzin)
            soil_saturation: Nasycenie gleby (0-1), 1 = całkowicie mokra
            
        Returns:
            Dict z poziomem ryzyka i prawdopodobieństwem
        """
        # Efektywne opady uwzględniające nasycenie gleby
        # Mokra gleba = mniejsza infiltracja = większy spływ
        effective_precip = precipitation_mm * (0.5 + 0.5 * soil_saturation)
        
        # Progi ryzyka (mm efektywnych opadów)
        if effective_precip < 10:
            risk_level = "low"
            probability = 0.05 + effective_precip * 0.01
        elif effective_precip < 30:
            risk_level = "moderate"
            probability = 0.15 + (effective_precip - 10) * 0.02
        elif effective_precip < 60:
            risk_level = "high"
            probability = 0.55 + (effective_precip - 30) * 0.01
        else:
            risk_level = "critical"
            probability = min(0.95, 0.85 + (effective_precip - 60) * 0.005)
        
        return {
            "risk_level": risk_level,
            "flood_probability": round(probability, 2),
            "effective_precipitation_mm": round(effective_precip, 2),
            "soil_saturation": soil_saturation,
            "recommendation": self._get_recommendation(risk_level)
        }
    
    def _get_recommendation(self, risk_level: str) -> str:
        """Zwraca rekomendację dla Szefa Sztabu."""
        recommendations = {
            "low": "Monitorowanie sytuacji. Brak bezpośredniego zagrożenia.",
            "moderate": "Zwiększona uwaga. Przygotować plany ewakuacyjne.",
            "high": "OSTRZEŻENIE. Rozpocząć ewakuację terenów nisko położonych.",
            "critical": "ALARM! Natychmiastowa ewakuacja zagrożonych obszarów."
        }
        return recommendations.get(risk_level, "Brak danych")


# Singleton instance
precipitation_service = PrecipitationService()
