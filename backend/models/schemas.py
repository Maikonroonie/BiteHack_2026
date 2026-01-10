"""
CrisisEye - Pydantic Schemas
Modele request/response dla API
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


class AnalysisStatus(str, Enum):
    """Status analizy"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BoundingBox(BaseModel):
    """Bounding box dla obszaru analizy [minLon, minLat, maxLon, maxLat]"""
    min_lon: float = Field(..., ge=-180, le=180, description="Minimalna długość geograficzna")
    min_lat: float = Field(..., ge=-90, le=90, description="Minimalna szerokość geograficzna")
    max_lon: float = Field(..., ge=-180, le=180, description="Maksymalna długość geograficzna")
    max_lat: float = Field(..., ge=-90, le=90, description="Maksymalna szerokość geograficzna")
    
    def to_list(self) -> List[float]:
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class AnalysisRequest(BaseModel):
    """Request do analizy powodzi"""
    bbox: BoundingBox
    date_before: date = Field(..., description="Data przed powodzią")
    date_after: date = Field(..., description="Data po powodzi")
    polarization: str = Field(default="VV", description="Polaryzacja SAR (VV/VH)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bbox": {
                    "min_lon": 18.5,
                    "min_lat": 50.0,
                    "max_lon": 19.0,
                    "max_lat": 50.5
                },
                "date_before": "2024-01-01",
                "date_after": "2024-01-15",
                "polarization": "VV"
            }
        }


class FloodPixelStats(BaseModel):
    """Statystyki pikseli powodzi"""
    total_pixels: int
    flooded_pixels: int
    flood_percentage: float
    area_km2: float
    flooded_area_km2: float


class BuildingInfo(BaseModel):
    """Informacje o budynku z OSM"""
    osm_id: int
    name: Optional[str] = None
    building_type: str = "building"
    lat: float
    lon: float
    is_flooded: bool = False
    flood_probability: float = 0.0


class BuildingsRequest(BaseModel):
    """Request do pobrania budynków"""
    bbox: BoundingBox


class BuildingsResponse(BaseModel):
    """Response z listą budynków"""
    total_count: int
    flooded_count: int
    buildings: List[BuildingInfo]


class FloodMaskResponse(BaseModel):
    """Response z maską powodzi w formacie GeoJSON"""
    type: str = "FeatureCollection"
    features: List[dict]
    stats: FloodPixelStats


class AnalysisResponse(BaseModel):
    """Główna odpowiedź z analizy"""
    status: AnalysisStatus
    message: str
    stats: Optional[FloodPixelStats] = None
    flood_geojson: Optional[dict] = None
    buildings_affected: int = 0
    processing_time_seconds: float = 0.0
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "message": "Analiza zakończona pomyślnie",
                "stats": {
                    "total_pixels": 100000,
                    "flooded_pixels": 5000,
                    "flood_percentage": 5.0,
                    "area_km2": 100.0,
                    "flooded_area_km2": 5.0
                },
                "buildings_affected": 42,
                "processing_time_seconds": 2.5
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    services: dict
