"""
CrisisEye - SAR Processor Service
Przetwarzanie danych radarowych SAR z wykorzystaniem rasterio i xarray.
NIE używamy snappy - za skomplikowane dla hackathonu!
"""

import numpy as np
from datetime import date
from typing import Dict, List, Optional, Any
import asyncio


class SARProcessor:
    """
    Serwis do przetwarzania danych SAR.
    
    W pełnej wersji:
    - Pobiera dane Sentinel-1 z Google Earth Engine
    - Przetwarza z rasterio/xarray
    - Wykonuje korekcję radiometryczną
    
    Dla hackathonu:
    - Symuluje przetwarzanie z przykładowymi danymi
    - Generuje syntetyczne obrazy SAR
    """
    
    def __init__(self):
        self.default_resolution = 10  # metry
        self.polarizations = ["VV", "VH"]
        
    async def process_sar(
        self,
        bbox: List[float],
        date_before: date,
        date_after: date,
        polarization: str = "VV"
    ) -> Dict[str, Any]:
        """
        Przetwarza dane SAR dla zadanego obszaru i dat.
        
        Args:
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            date_before: Data przed wydarzeniem (powodzią)
            date_after: Data po wydarzeniu
            polarization: Polaryzacja SAR (VV lub VH)
            
        Returns:
            Dict z danymi SAR (przed, po) i różnicą
        """
        # Symulacja opóźnienia przetwarzania
        await asyncio.sleep(0.1)
        
        # Oblicz rozmiar siatki na podstawie bbox
        lon_diff = bbox[2] - bbox[0]
        lat_diff = bbox[3] - bbox[1]
        
        # Przybliżona liczba pikseli (10m rozdzielczość)
        # 1 stopień ≈ 111km
        width = int(lon_diff * 111000 / self.default_resolution)
        height = int(lat_diff * 111000 / self.default_resolution)
        
        # Ogranicz dla hackathonu
        width = min(width, 500)
        height = min(height, 500)
        
        # Generuj syntetyczne dane SAR (w dB)
        # Typowe wartości: woda ~-20 do -25 dB, ląd ~-5 do -15 dB
        sar_before = self._generate_synthetic_sar(width, height, seed=42)
        sar_after = self._generate_synthetic_sar(width, height, seed=43, flood_ratio=0.15)
        
        # Change detection - różnica w dB
        change = sar_after - sar_before
        
        return {
            "before": sar_before,
            "after": sar_after,
            "change": change,
            "bbox": bbox,
            "width": width,
            "height": height,
            "resolution": self.default_resolution,
            "polarization": polarization,
            "date_before": str(date_before),
            "date_after": str(date_after)
        }
    
    def _generate_synthetic_sar(
        self, 
        width: int, 
        height: int, 
        seed: int = 42,
        flood_ratio: float = 0.0
    ) -> np.ndarray:
        """
        Generuje syntetyczne dane SAR dla celów demonstracyjnych.
        
        Args:
            width: Szerokość obrazu
            height: Wysokość obrazu
            seed: Seed dla powtarzalności
            flood_ratio: Procent pikseli do "zalania" (0.0-1.0)
            
        Returns:
            numpy array z wartościami w dB
        """
        np.random.seed(seed)
        
        # Bazowy obraz - ląd (średnio -10 dB z szumem)
        sar = np.random.normal(-10, 3, (height, width))
        
        # Dodaj naturalne wzorce (symulacja terenu)
        x = np.linspace(0, 4*np.pi, width)
        y = np.linspace(0, 4*np.pi, height)
        X, Y = np.meshgrid(x, y)
        pattern = 2 * np.sin(X) * np.cos(Y)
        sar += pattern
        
        if flood_ratio > 0:
            # Symuluj obszar zalany (niższe wartości = woda)
            flood_mask = np.random.random((height, width)) < flood_ratio
            
            # Dodaj spójne obszary powodzi (nie losowe piksele)
            from scipy import ndimage
            flood_mask = ndimage.binary_dilation(flood_mask, iterations=3)
            
            # Woda ma wartości około -20 do -25 dB
            sar[flood_mask] = np.random.normal(-22, 2, np.sum(flood_mask))
        
        return sar
    
    def calculate_water_mask(
        self, 
        sar_data: np.ndarray, 
        threshold_db: float = -15.0
    ) -> np.ndarray:
        """
        Tworzy binarną maskę wody na podstawie progu.
        
        Prosta metoda progowa - dla hackathonu.
        Niskie wartości dB (< threshold) = woda.
        
        Args:
            sar_data: Dane SAR w dB
            threshold_db: Próg w dB (domyślnie -15)
            
        Returns:
            Binarna maska (True = woda)
        """
        return sar_data < threshold_db
    
    def calculate_change_mask(
        self,
        sar_before: np.ndarray,
        sar_after: np.ndarray,
        change_threshold: float = -5.0
    ) -> np.ndarray:
        """
        Wykrywa zmiany między dwoma obrazami SAR.
        
        Spadek o więcej niż threshold = prawdopodobnie zalanie.
        
        Args:
            sar_before: SAR przed wydarzeniem
            sar_after: SAR po wydarzeniu
            change_threshold: Próg zmiany w dB
            
        Returns:
            Binarna maska zmian
        """
        change = sar_after - sar_before
        return change < change_threshold
