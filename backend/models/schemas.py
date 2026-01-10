"""
CrisisEye - Pydantic Schemas
Modele request/response dla API
"""

from pydantic import BaseModel, Field
from typing import Optional, List,Dict
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
    total_pixels: int
    flooded_pixels: int
    flood_percentage: float
    area_km2: float
    flooded_area_km2: float
    current_rainfall_mm_h: Optional[float] = 0.0  # Dane z GPM
    avg_elevation_m: Optional[float] = 0.0        # Dane z SRTM

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
    status: AnalysisStatus
    message: str
    stats: Optional[FloodPixelStats] = None
    flood_geojson: Optional[dict] = None
    buildings_affected: int = 0
    estimated_loss_pln: float = 0.0 
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




#NOWCASTING / PREDICTION SCHEMAS 

class PredictionRequest(BaseModel):
    """Request do predykcji powodzi w czasie rzeczywistym"""
    bbox: BoundingBox
    prediction_hours: int = Field(
        default=6, 
        ge=1, 
        le=24, 
        description="Za ile godzin przewidywać (1-24)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "bbox": {
                    "min_lon": 17.0,
                    "min_lat": 51.0,
                    "max_lon": 17.1,
                    "max_lat": 51.1
                },
                "prediction_hours": 6
            }
        }


class EvacuationPriority(BaseModel):
    """Priorytet ewakuacji dla budynku"""
    osm_id: int
    name: Optional[str] = None
    building_type: str
    lat: float
    lon: float
    risk_level: str = Field(description="critical / high / medium / low")
    flood_probability: float = Field(ge=0, le=1)
    evacuation_score: float = Field(ge=0, le=1, description="Wyższy = pilniejsza ewakuacja")
    estimated_time_to_flood_hours: float
    people_estimate: int = Field(description="Szacunkowa liczba osób do ewakuacji")


class PrecipitationInfo(BaseModel):
    """Informacje o opadach"""
    mean_mm: float
    max_mm: float
    source: str
    hours_analyzed: int
    is_simulated: bool = False


class RiskFactors(BaseModel):
    """Czynniki wpływające na ryzyko"""
    precipitation_contribution: float
    terrain_contribution: float
    time_factor: float


class PredictionResponse(BaseModel):
    """Response z predykcją powodzi"""
    status: AnalysisStatus
    message: str
    timestamp: str
    prediction_hours: int
    
    # Główne wyniki
    flood_probability: float = Field(ge=0, le=1, description="0-1 prawdopodobieństwo zalania")
    risk_level: str = Field(description="low / moderate / high / critical")
    confidence: float = Field(ge=0, le=1, description="Pewność predykcji")
    
    # Dane wejściowe
    precipitation: Optional[PrecipitationInfo] = None
    risk_factors: Optional[RiskFactors] = None
    
    # Wyniki przestrzenne
    risk_zones_geojson: Optional[dict] = None
    evacuation_priorities: List[EvacuationPriority] = []
    
    # Meta
    processing_time_seconds: float = 0.0
    next_update_minutes: int = 30
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "message": "Predykcja zakończona",
                "timestamp": "2026-01-10T17:00:00Z",
                "prediction_hours": 6,
                "flood_probability": 0.65,
                "risk_level": "high",
                "confidence": 0.82,
                "evacuation_priorities": [
                    {
                        "osm_id": 12345,
                        "name": "Szpital Miejski",
                        "building_type": "hospital",
                        "lat": 51.1,
                        "lon": 17.05,
                        "risk_level": "critical",
                        "flood_probability": 0.78,
                        "evacuation_score": 0.78,
                        "estimated_time_to_flood_hours": 4.5,
                        "people_estimate": 350
                    }
                ],
                "processing_time_seconds": 1.2,
                "next_update_minutes": 30
            }
        }

