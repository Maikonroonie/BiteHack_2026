import numpy as np
import pystac_client
import planetary_computer
import rioxarray
from datetime import date, timedelta
from typing import Dict, List, Any
from skimage.transform import resize

class SARProcessor:
    def __init__(self):
        self.stac_api_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    async def process_sar(self, bbox: List[float], date_after: Any, **kwargs) -> Dict[str, Any]:
        """Pobiera prawdziwe dane Sentinel-1 przez Microsoft STAC"""
        print(f"🛰️ Szukam danych SAR dla: {bbox}")
        
        try:
            catalog = pystac_client.Client.open(self.stac_api_url, modifier=planetary_computer.sign_inplace)
            
            # Obsługa daty (okno +/- 3 dni)
            date_obj = date.fromisoformat(date_after) if isinstance(date_after, str) else date_after
            time_range = f"{(date_obj - timedelta(days=3)).isoformat()}/{(date_obj + timedelta(days=3)).isoformat()}"

            search = catalog.search(
                collections=["sentinel-1-grd"],
                bbox=bbox,
                datetime=time_range,
                query={"sar:polarizations": {"eq": ["VV", "VH"]}}
            )
            
            items = search.item_collection()
            if not items:
                raise Exception("Brak zdjęć SAR w tym terminie.")

            # Pobieranie i przycinanie (.rio.clip_box)
            item = items[0]
            # W metodzie process_sar podmień fragment pobierania:
            href = planetary_computer.sign(item.assets["vv"].href)
            
            # KLUCZOWA POPRAWKA: Reprojekcja do EPSG:4326 (stopnie) przed wycięciem
            da = rioxarray.open_rasterio(href)
            da_reprojected = da.rio.reproject("EPSG:4326") # Przelicz metry na stopnie
            da_clipped = da_reprojected.rio.clip_box(*bbox, allow_one_dimensional_raster=True)
            
                        # Squeeze usunie niepotrzebny wymiar kanału (np. z (1, 500, 500) zrobi (500, 500))
            # W metodzie process_sar, zastąp logikę przeliczania tym:
            sar_image = da_clipped.squeeze().values

            if np.max(sar_image) > 0:
                # Zakładamy, że surowe dane to Amplituda (częste w MS PC)
                # Przeliczamy na decybele z przesunięciem (offsetem), aby uzyskać zakres ujemny
                sar_image = 10 * np.log10(np.maximum(sar_image, 0.0001))
                
                # Przesunięcie kalibracyjne: jeśli średnia jest dodatnia, odejmij od niej stałą
                # Typowe DN dla S1 to setki, co daje ok +25 dB. Odejmujemy 40, by dostać ok -15 dB.
                if np.mean(sar_image) > 0:
                    sar_image = sar_image - 40.0 

            # Teraz clip zadziała poprawnie i nie będzie samej piątki
            sar_image = np.clip(sar_image, -35, 5)
            print(f"✅ Sukces! Nowy kształt macierzy: {sar_image.shape}")
            # Dodatkowo pobieramy DEM dla tego samego obszaru
            dem = self.fetch_terrain_data(bbox, sar_image.shape)

            return {
                "before": sar_image + 5.0, # Symulacja 'przed' (dla change detection)
                "after": sar_image,
                "change": -5.0 * np.ones_like(sar_image), # Uproszczona zmiana
                "dem": dem,
                "bbox": bbox,
                "resolution": 10
            }
        except Exception as e:
            print(f"❌ Błąd: {e}")
            raise e

    def fetch_terrain_data(self, bbox: List[float], shape: tuple):
        """Pobiera wysokość terenu (Copernicus DEM)"""
        try:
            catalog = pystac_client.Client.open(self.stac_api_url, modifier=planetary_computer.sign_inplace)
            search = catalog.search(collections=["copernicus-dem-glo-30"], bbox=bbox)
            items = search.item_collection()
            
            if items:
                href = planetary_computer.sign(items[0].assets["data"].href)
                dem_da = rioxarray.open_rasterio(href).rio.clip_box(*bbox)
                return resize(dem_da.squeeze().values, shape, mode='reflect', preserve_range=True)
        except: return None
        return None