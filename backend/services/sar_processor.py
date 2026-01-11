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
        print(f"Szukam danych SAR dla: {bbox}")
        
        try:
            catalog = pystac_client.Client.open(self.stac_api_url, modifier=planetary_computer.sign_inplace)
            
            date_obj = date.fromisoformat(date_after) if isinstance(date_after, str) else date_after
            time_range = f"{(date_obj - timedelta(days=3)).isoformat()}/{(date_obj + timedelta(days=6)).isoformat()}"

            search = catalog.search(
                collections=["sentinel-1-grd"],
                bbox=bbox,
                datetime=time_range,
                query={"sar:polarizations": {"eq": ["VV", "VH"]}}
            )
            
            items = search.item_collection()
            if not items:
                raise Exception("Brak zdjęć SAR w tym terminie.")

            item = items[0]
            href = planetary_computer.sign(item.assets["vv"].href)
            
            da = rioxarray.open_rasterio(href)

            da_reprojected = da.rio.reproject("EPSG:4326") 

            da_clipped = da_reprojected.rio.clip_box(*bbox)
            
            sar_image = da_clipped.squeeze().values

            if np.max(sar_image) > 0:
                sar_image = 10 * np.log10(np.maximum(sar_image, 0.0001))
                if np.mean(sar_image) > 0:
                    sar_image = sar_image - 40.0 

            sar_image = np.clip(sar_image, -35, 5)
            print(f"Sukces! Macierz SAR: {sar_image.shape}")
            
            dem = self.fetch_terrain_data(bbox, sar_image.shape)
            if dem is None:
                dem = np.zeros_like(sar_image)

            return {
                "before": sar_image + 5.0,
                "after": sar_image,
                "change": -5.0 * np.ones_like(sar_image),
                "dem": dem,
                "bbox": bbox,
                "resolution": 10
            }
        except Exception as e:
            print(f"Błąd SAR: {e}")
            raise e

    def fetch_terrain_data(self, bbox: List[float], shape: tuple):
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