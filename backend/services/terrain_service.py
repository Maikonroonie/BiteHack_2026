import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

class TerrainService:
    def __init__(self):
        self.initialized = False
        self.project_id = os.getenv("GEE_PROJECT_ID", "")
        self.dem_collection = "USGS/SRTMGL1_003"
        
    async def initialize(self) -> bool:
        """Połączenie z Google Earth Engine."""
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
            print("Terrain Service (DEM) initialized")
            return True
            
        except ImportError:
            print("Earthengine-api not installed - using simulated terrain")
            return False
        except Exception as e:
            print(f"GEE initialization failed: {e} - using simulated terrain")
            return False
    
    async def get_elevation(
        self,
        bbox: List[float],
        resolution: int = 100
    ) -> Dict[str, Any]:
        if await self.initialize():
            return await self._get_dem_data(bbox, resolution)
        else:
            return self._get_simulated_elevation(bbox, resolution)
    
    async def _get_dem_data(
        self,
        bbox: List[float],
        resolution: int
    ) -> Dict[str, Any]:
        """Pobiera prawdziwe dane DEM z GEE."""
        try:
            import ee
            
            region = ee.Geometry.Rectangle(bbox)
            
            dem = ee.Image(self.dem_collection)
            elevation = dem.select('elevation')

            stats = elevation.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.max(), sharedInputs=True
                ).combine(
                    ee.Reducer.min(), sharedInputs=True
                ).combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=region,
                scale=30,
                maxPixels=1e9
            ).getInfo()

            slope = ee.Terrain.slope(elevation)
            slope_stats = slope.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            return {
                "source": "SRTM_30m",
                "bbox": bbox,
                "elevation_m": {
                    "mean": round(stats.get("elevation_mean", 0), 1),
                    "max": round(stats.get("elevation_max", 0), 1),
                    "min": round(stats.get("elevation_min", 0), 1),
                    "std": round(stats.get("elevation_stdDev", 0), 1)
                },
                "slope_degrees": {
                    "mean": round(slope_stats.get("slope", 0), 1)
                },
                "is_simulated": False
            }
            
        except Exception as e:
            print(f"DEM query failed: {e}")
            return self._get_simulated_elevation(bbox, resolution)
    
    def _get_simulated_elevation(
        self,
        bbox: List[float],
        resolution: int
    ) -> Dict[str, Any]:
        np.random.seed(42)

        x = np.linspace(0, 1, resolution)
        y = np.linspace(0, 1, resolution)
        X, Y = np.meshgrid(x, y)

        base_elevation = 150
        valley = 30 * np.exp(-((X - 0.5)**2 + (Y - 0.5)**2) / 0.1)
        hills = 50 * (np.sin(X * 4 * np.pi) * np.cos(Y * 3 * np.pi) + 1) / 2
        noise = np.random.normal(0, 5, (resolution, resolution))
        
        terrain = base_elevation + hills - valley + noise
        
        return {
            "source": "SIMULATED",
            "bbox": bbox,
            "elevation_m": {
                "mean": round(float(np.mean(terrain)), 1),
                "max": round(float(np.max(terrain)), 1),
                "min": round(float(np.min(terrain)), 1),
                "std": round(float(np.std(terrain)), 1)
            },
            "slope_degrees": {
                "mean": round(np.random.uniform(2, 8), 1)
            },
            "grid": terrain.tolist(),
            "resolution": resolution,
            "is_simulated": True
        }
    
    async def get_flow_accumulation(
        self,
        bbox: List[float]
    ) -> Dict[str, Any]:
        elevation_data = await self.get_elevation(bbox, resolution=50)
        
        if elevation_data.get("grid"):
            grid = np.array(elevation_data["grid"])
            
            accumulation = self._simple_flow_accumulation(grid)

            threshold = np.percentile(accumulation, 90)
            high_accumulation_mask = accumulation > threshold
            
            return {
                "bbox": bbox,
                "flow_accumulation": accumulation.tolist(),
                "high_risk_percentage": round(
                    100 * np.sum(high_accumulation_mask) / accumulation.size, 
                    2
                ),
                "max_accumulation": float(np.max(accumulation)),
                "is_simulated": True
            }
        else:
            return {
                "bbox": bbox,
                "high_risk_percentage": np.random.uniform(5, 15),
                "note": "Flow accumulation requires grid data"
            }
    
    def _simple_flow_accumulation(self, elevation: np.ndarray) -> np.ndarray:

        rows, cols = elevation.shape
        accumulation = np.ones_like(elevation)
        
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        flat_indices = np.argsort(elevation, axis=None)[::-1]
        
        for flat_idx in flat_indices:
            i, j = flat_idx // cols, flat_idx % cols
            current_elev = elevation[i, j]
            
            min_elev = current_elev
            min_neighbor = None
            
            for di, dj in directions:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols:
                    if elevation[ni, nj] < min_elev:
                        min_elev = elevation[ni, nj]
                        min_neighbor = (ni, nj)
            
            if min_neighbor:
                accumulation[min_neighbor] += accumulation[i, j]
        
        return accumulation
    
    def identify_low_lying_areas(
        self,
        elevation_data: Dict[str, Any],
        threshold_percentile: int = 20
    ) -> Dict[str, Any]:
        if "grid" in elevation_data:
            grid = np.array(elevation_data["grid"])
            threshold = np.percentile(grid, threshold_percentile)
            
            low_areas = grid < threshold
            low_area_percentage = 100 * np.sum(low_areas) / grid.size

            if np.any(low_areas):
                low_indices = np.where(low_areas)
                center_y = np.mean(low_indices[0]) / grid.shape[0]
                center_x = np.mean(low_indices[1]) / grid.shape[1]
                
                bbox = elevation_data["bbox"]
                center_lon = bbox[0] + center_x * (bbox[2] - bbox[0])
                center_lat = bbox[1] + center_y * (bbox[3] - bbox[1])
            else:
                center_lon, center_lat = None, None
            
            return {
                "low_area_percentage": round(low_area_percentage, 2),
                "threshold_elevation_m": round(threshold, 1),
                "center_of_low_areas": {
                    "lat": round(center_lat, 6) if center_lat else None,
                    "lon": round(center_lon, 6) if center_lon else None
                }
            }
        else:
            return {
                "low_area_percentage": threshold_percentile,
                "note": "Estimation based on percentile"
            }

terrain_service = TerrainService()
