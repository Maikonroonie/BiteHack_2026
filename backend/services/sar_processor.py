import numpy as np
import pystac_client
import planetary_computer
import rioxarray
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from skimage.transform import resize

class SARProcessor:
    """
    SAR data processor using Microsoft Planetary Computer.
    Fetches real Sentinel-1 GRD data for before/after flood analysis.
    """
    def __init__(self):
        self.stac_api_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    async def process_sar(
        self, 
        bbox: List[float], 
        date_after: Any,
        date_before: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetches real Sentinel-1 SAR data for before and after dates.
        
        Args:
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            date_after: Date of potential flood (string or date object)
            date_before: Date before flood (optional, defaults to 14 days before)
            
        Returns:
            Dict with 'before', 'after', 'change', 'dem', 'bbox', 'resolution'
        """
        print(f"[SAR] Processing SAR for bbox: {bbox}")
        
        # Parse dates
        date_after_obj = date.fromisoformat(date_after) if isinstance(date_after, str) else date_after
        
        if date_before is None:
            date_before_obj = date_after_obj - timedelta(days=14)
        else:
            date_before_obj = date.fromisoformat(date_before) if isinstance(date_before, str) else date_before
        
        print(f"[SAR] Fetching BEFORE image: {date_before_obj}")
        print(f"[SAR] Fetching AFTER image: {date_after_obj}")
        
        try:
            # Fetch AFTER image (post-flood)
            sar_after = await self._fetch_sar_image(bbox, date_after_obj)
            
            # Fetch BEFORE image (pre-flood) - REAL DATA, not simulated!
            sar_before = await self._fetch_sar_image(bbox, date_before_obj)
            
            # Ensure shapes match
            if sar_before.shape != sar_after.shape:
                print(f"[SAR] Resizing before image from {sar_before.shape} to {sar_after.shape}")
                sar_before = resize(sar_before, sar_after.shape, mode='reflect', preserve_range=True)
            
            # Calculate change detection
            sar_change = sar_after - sar_before
            
            # Fetch DEM for the same area
            dem = self.fetch_terrain_data(bbox, sar_after.shape)
            
            print(f"[SAR] Success! Shape: {sar_after.shape}, Before mean: {np.mean(sar_before):.2f}, After mean: {np.mean(sar_after):.2f}")
            
            return {
                "before": sar_before,
                "after": sar_after,
                "change": sar_change,
                "dem": dem,
                "bbox": bbox,
                "resolution": 10
            }
            
        except Exception as e:
            print(f"[SAR] Error: {e}")
            raise e

    async def _fetch_sar_image(self, bbox: List[float], target_date: date, window_days: int = 7) -> np.ndarray:
        """
        Fetches a single SAR image for the given date.
        Searches within a window of +/- window_days to find available data.
        """
        catalog = pystac_client.Client.open(
            self.stac_api_url, 
            modifier=planetary_computer.sign_inplace
        )
        
        # Create time range window
        start_date = target_date - timedelta(days=window_days)
        end_date = target_date + timedelta(days=window_days)
        time_range = f"{start_date.isoformat()}/{end_date.isoformat()}"
        
        print(f"[SAR] Searching for images in range: {time_range}")
        
        search = catalog.search(
            collections=["sentinel-1-grd"],
            bbox=bbox,
            datetime=time_range,
            query={"sar:polarizations": {"eq": ["VV", "VH"]}}
        )
        
        items = search.item_collection()
        
        if not items:
            raise Exception(f"No SAR images found for date range {time_range}")
        
        # Sort by date closest to target
        items_sorted = sorted(
            items, 
            key=lambda x: abs((date.fromisoformat(x.datetime.strftime('%Y-%m-%d')) - target_date).days)
        )
        item = items_sorted[0]
        
        print(f"[SAR] Found image from: {item.datetime}")
        
        # Download and process
        href = planetary_computer.sign(item.assets["vv"].href)
        da = rioxarray.open_rasterio(href)
        
        # Reproject to EPSG:4326 (degrees) before clipping
        da_reprojected = da.rio.reproject("EPSG:4326")
        da_clipped = da_reprojected.rio.clip_box(*bbox, allow_one_dimensional_raster=True)
        
        # Squeeze to remove channel dimension
        sar_image = da_clipped.squeeze().values
        
        # Convert to dB
        if np.max(sar_image) > 0:
            sar_image = 10 * np.log10(np.maximum(sar_image, 0.0001))
            # Calibration offset
            if np.mean(sar_image) > 0:
                sar_image = sar_image - 40.0
        
        # Clip to reasonable dB range
        sar_image = np.clip(sar_image, -35, 5)
        
        return sar_image

    def fetch_terrain_data(self, bbox: List[float], shape: tuple) -> Optional[np.ndarray]:
        """Fetches elevation data (Copernicus DEM) for the area."""
        try:
            catalog = pystac_client.Client.open(
                self.stac_api_url, 
                modifier=planetary_computer.sign_inplace
            )
            search = catalog.search(collections=["copernicus-dem-glo-30"], bbox=bbox)
            items = search.item_collection()
            
            if items:
                href = planetary_computer.sign(items[0].assets["data"].href)
                dem_da = rioxarray.open_rasterio(href).rio.clip_box(*bbox)
                return resize(dem_da.squeeze().values, shape, mode='reflect', preserve_range=True)
        except Exception as e:
            print(f"[SAR] DEM fetch failed: {e}")
            return None
        return None