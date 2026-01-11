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

    async def process_sar(self, bbox: List[float], date_after: Any, date_before: Any = None, **kwargs) -> Dict[str, Any]:
        """Pobiera PRAWDZIWE dane Sentinel-1 przed i po powodzi"""
        print(f"[SAR] Szukam danych dla: {bbox}")
        
        try:
            catalog = pystac_client.Client.open(self.stac_api_url, modifier=planetary_computer.sign_inplace)
            
            # Parsowanie dat
            date_after_obj = date.fromisoformat(date_after) if isinstance(date_after, str) else date_after
            
            if date_before is None:
                date_before_obj = date_after_obj - timedelta(days=14)
            else:
                date_before_obj = date.fromisoformat(date_before) if isinstance(date_before, str) else date_before
            
            print(f"[SAR] BEFORE: {date_before_obj}, AFTER: {date_after_obj}")
            
            # Pobierz AFTER (po powodzi)
            sar_after = await self._fetch_single_sar(catalog, bbox, date_after_obj)
            
            # Pobierz BEFORE (przed powodzią) - PRAWDZIWE DANE!
            sar_before = await self._fetch_single_sar(catalog, bbox, date_before_obj)
            
            # Dopasuj rozmiary
            if sar_before.shape != sar_after.shape:
                sar_before = resize(sar_before, sar_after.shape, mode='reflect', preserve_range=True)
            
            # Pobierz DEM
            dem = self.fetch_terrain_data(bbox, sar_after.shape)
            if dem is None:
                dem = np.zeros_like(sar_after)

            print(f"[SAR] OK! Shape: {sar_after.shape}, Before mean: {np.mean(sar_before):.1f}dB, After mean: {np.mean(sar_after):.1f}dB")
            
            return {
                "before": sar_before,  # PRAWDZIWE dane przed powodzią!
                "after": sar_after,
                "change": sar_after - sar_before,
                "dem": dem,
                "bbox": bbox,
                "resolution": 10
            }
        except Exception as e:
            print(f"[SAR] Blad: {e}")
            raise e

    async def _fetch_single_sar(self, catalog, bbox: List[float], target_date: date) -> np.ndarray:
        """Pobiera pojedynczy obraz SAR dla daty"""
        time_range = f"{(target_date - timedelta(days=7)).isoformat()}/{(target_date + timedelta(days=7)).isoformat()}"
        
        search = catalog.search(
            collections=["sentinel-1-grd"],
            bbox=bbox,
            datetime=time_range,
            query={"sar:polarizations": {"eq": ["VV", "VH"]}}
        )
        
        items = search.item_collection()
        if not items:
            raise Exception(f"Brak SAR dla {target_date}")
        
        # Wybierz najbliższy do target_date
        items_sorted = sorted(items, key=lambda x: abs((date.fromisoformat(x.datetime.strftime('%Y-%m-%d')) - target_date).days))
        item = items_sorted[0]
        
        print(f"[SAR] Znaleziono: {item.datetime.strftime('%Y-%m-%d')}")
        
        href = planetary_computer.sign(item.assets["vv"].href)
        da = rioxarray.open_rasterio(href)
        da_reprojected = da.rio.reproject("EPSG:4326")
        da_clipped = da_reprojected.rio.clip_box(*bbox)
        sar_image = da_clipped.squeeze().values

        if np.max(sar_image) > 0:
            sar_image = 10 * np.log10(np.maximum(sar_image, 0.0001))
            if np.mean(sar_image) > 0:
                sar_image = sar_image - 40.0

        return np.clip(sar_image, -35, 5)

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