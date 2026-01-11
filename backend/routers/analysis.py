"""
CrisisEye - Analysis Router
Główne endpointy do analizy i PREDYKCJI powodzi - Wersja Hackathon MVP
"""

import time
from datetime import datetime
from services.flood_detector import flood_detector
from fastapi import APIRouter, HTTPException
from typing import Optional

from models.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    AnalysisStatus,
    BuildingsRequest,
    BuildingsResponse,
    FloodMaskResponse,
    FloodPixelStats,
    # Nowe schematy predykcji
    PredictionRequest,
    PredictionResponse,
    EvacuationPriority,
    PrecipitationInfo,
    RiskFactors
)
from services.flood_detector import FloodPredictor
from services.osm_service import OSMService
from services.sar_processor import SARProcessor
#from services.damage import DamageService
from services.gee_service import gee_service
from services.precipitation_service import precipitation_service
from services.terrain_service import terrain_service

router = APIRouter()

# Inicjalizacja serwisów
flood_predictor = FloodPredictor()
osm_service = OSMService()
sar_processor = SARProcessor()
#damage_service = DamageService()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_flood(request: AnalysisRequest):
    """
    Main flood analysis endpoint (Pipeline v2.1).
    
    Pipeline:
    1. Fetch SAR data (before and after) + DEM
    2. Run change detection with K-Means classifier
    3. Fetch infrastructure from OSM
    4. Perform spatial join (buildings vs flood mask)
    5. Calculate financial losses
    """
    start_time = time.time()
    
    try:
        # 1. Process SAR data (satellite imagery)
        sar_data = await sar_processor.process_sar(
            bbox=request.bbox.to_list(),
            date_after=request.date_after,
            date_before=request.date_before  # Now using real before date!
        )
        
        # Get additional terrain/rain data from GEE
        gee_data = await gee_service.get_terrain_and_rain(request.bbox.to_list())
        
        # 2. Flood detection (AI model)
        flood_result = await flood_detector.detect_flood(sar_data)
        
        # 3. Fetch buildings from OSM
        buildings = await osm_service.get_buildings(request.bbox.to_list())
        
        # 4. Check which buildings are flooded (spatial analysis)
        flooded_buildings = flood_detector.check_buildings_flooding(
            buildings, 
            flood_result["mask"],
            request.bbox.to_list()
        )
        
        # 5. Calculate financial losses (inline, no separate service)
        estimated_loss = calculate_damage_inline(len(flooded_buildings), flood_result["stats"].get("flooded_area_km2", 0))
        
        processing_time = time.time() - start_time
        
        # Build stats object
        raw_stats = flood_result["stats"]
        stats = FloodPixelStats(
            total_pixels=raw_stats.get("total_pixels", 0),
            flooded_pixels=raw_stats.get("flooded_pixels", 0),
            flood_percentage=raw_stats.get("flood_percentage", 0),
            area_km2=raw_stats.get("area_km2", 0),
            flooded_area_km2=raw_stats.get("flooded_area_km2", 0),
            avg_elevation_m=gee_data.get("avg_elevation", 0),
            current_rainfall_mm_h=gee_data.get("current_rainfall", 0)
        )
        
        return AnalysisResponse(
            status=AnalysisStatus.COMPLETED,
            message="Analiza zakonczona pomyslnie",
            stats=stats,
            flood_geojson=flood_result["geojson"],
            buildings_affected=len(flooded_buildings),
            estimated_loss_pln=estimated_loss,
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AnalysisResponse(
            status=AnalysisStatus.FAILED,
            message=f"Blad analizy: {str(e)}",
            processing_time_seconds=time.time() - start_time
        )


def calculate_damage_inline(buildings_affected: int, flooded_area_km2: float) -> float:
    """Simple inline damage calculation."""
    # Average costs (PLN)
    AVG_BUILDING_DAMAGE = 150000
    INFRASTRUCTURE_PER_KM2 = 300000
    AGRICULTURAL_PER_KM2 = 50000
    
    building_damage = buildings_affected * AVG_BUILDING_DAMAGE
    infrastructure_damage = flooded_area_km2 * INFRASTRUCTURE_PER_KM2
    agricultural_damage = flooded_area_km2 * 0.3 * AGRICULTURAL_PER_KM2
    
    return building_damage + infrastructure_damage + agricultural_damage


@router.post("/buildings", response_model=BuildingsResponse)
async def get_buildings_only(request: BuildingsRequest):
    """Szybki podgląd infrastruktury bez pełnej analizy SAR."""
    try:
        buildings = await osm_service.get_buildings(request.bbox.to_list())
        return BuildingsResponse(
            total_count=len(buildings),
            flooded_count=0, # Wymaga pełnej analizy do wypełnienia
            buildings=buildings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd OSM: {str(e)}")


@router.post("/flood-mask", response_model=FloodMaskResponse)
async def get_flood_mask_only(request: AnalysisRequest):
    """Endpoint dedykowany dla warstw mapy (Tiles/GeoJSON)."""
    try:
        sar_data = await sar_processor.process_sar(
            bbox=request.bbox.to_list(),
            date_after=request.date_after
        )
        flood_result = await flood_detector.detect_flood(sar_data)
        
        return FloodMaskResponse(
            type="FeatureCollection",
            features=flood_result["geojson"].get("features", []),
            stats=flood_result["stats"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo")
async def get_demo_data():
    """Demo endpoint (Wrocław 1997) do testów Frontendu."""
    demo_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"flood_probability": 0.95, "type": "residential"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[17.02, 51.10], [17.04, 51.10], [17.04, 51.12], [17.02, 51.12], [17.02, 51.10]]]
                }
            }
        ]
    }
    
    return AnalysisResponse(
        status=AnalysisStatus.COMPLETED,
        message="Demo data - Wrocław Simulation",
        stats=FloodPixelStats(
            total_pixels=500000,
            flooded_pixels=75000,
            flood_percentage=15.0,
            area_km2=50.0,
            flooded_area_km2=7.5
        ),
        flood_geojson=demo_geojson,
        buildings_affected=12,
        estimated_loss_pln=450000.0,
        processing_time_seconds=0.1
    )


# ============== NOWCASTING / PREDICTION ENDPOINTS ==============

@router.post("/predict", response_model=PredictionResponse)
async def predict_flood(request: PredictionRequest):
    """
    🎯 GŁÓWNY ENDPOINT AI - Predykcja powodzi w czasie rzeczywistym.
    
    Pipeline:
    1. Pobierz aktualne opady z GPM (satelita)
    2. Pobierz dane terenu z DEM
    3. Uruchom model ML do predykcji ryzyka
    4. Pobierz budynki i oblicz priorytety ewakuacji
    
    Args:
        request: PredictionRequest z bbox i horyzontem czasowym
        
    Returns:
        PredictionResponse z mapą ryzyka i priorytetami ewakuacji
    """
    start_time = time.time()
    
    try:
        bbox = request.bbox.to_list()
        
        # 1. Pobierz aktualne opady (GPM satellite)
        precip_data = await precipitation_service.get_current_precipitation(
            bbox=bbox,
            hours_back=3
        )
        
        # 2. Pobierz dane terenu (DEM)
        terrain_data = await terrain_service.get_elevation(
            bbox=bbox,
            resolution=50
        )
        
        # 3. Uruchom model predykcji AI
        prediction = await flood_predictor.predict_flood_risk(
            bbox=bbox,
            precipitation_data=precip_data,
            terrain_data=terrain_data,
            prediction_hours=request.prediction_hours
        )
        
        # 4. Pobierz budynki i oblicz priorytety ewakuacji
        buildings = await osm_service.get_buildings(bbox)
        evacuation_priorities = flood_predictor.calculate_evacuation_priorities(
            buildings=buildings,
            flood_probability=prediction["flood_probability"],
            prediction_hours=request.prediction_hours
        )
        
        # 5. Przygotuj response
        processing_time = time.time() - start_time
        
        precip_mm = precip_data.get("precipitation_mm", {})
        
        return PredictionResponse(
            status=AnalysisStatus.COMPLETED,
            message=f"Predykcja za {request.prediction_hours}h zakończona",
            timestamp=datetime.utcnow().isoformat(),
            prediction_hours=request.prediction_hours,
            flood_probability=prediction["flood_probability"],
            risk_level=prediction["risk_level"],
            confidence=prediction["confidence"],
            precipitation=PrecipitationInfo(
                mean_mm=precip_mm.get("mean", 0),
                max_mm=precip_mm.get("max", 0),
                source=precip_data.get("source", "unknown"),
                hours_analyzed=precip_data.get("hours_analyzed", 3),
                is_simulated=precip_data.get("is_simulated", True)
            ),
            risk_factors=RiskFactors(
                precipitation_contribution=prediction["factors"]["precipitation_contribution"],
                terrain_contribution=prediction["factors"]["terrain_contribution"],
                time_factor=prediction["factors"]["time_factor"]
            ),
            risk_zones_geojson=prediction["risk_zones_geojson"],
            evacuation_priorities=[
                EvacuationPriority(**ep) for ep in evacuation_priorities
            ],
            processing_time_seconds=round(processing_time, 2),
            next_update_minutes=30
        )
        
    except Exception as e:
        return PredictionResponse(
            status=AnalysisStatus.FAILED,
            message=f"Błąd predykcji: {str(e)}",
            timestamp=datetime.utcnow().isoformat(),
            prediction_hours=request.prediction_hours,
            flood_probability=0,
            risk_level="unknown",
            confidence=0,
            processing_time_seconds=time.time() - start_time
        )


@router.get("/predict/demo")
async def get_prediction_demo():
    """
    Demo predykcji dla Wrocławia.
    Pokazuje jak wygląda output dla Szefa Sztabu.
    """
    return PredictionResponse(
        status=AnalysisStatus.COMPLETED,
        message="Demo predykcji - Wrocław za 6 godzin",
        timestamp=datetime.utcnow().isoformat(),
        prediction_hours=6,
        flood_probability=0.72,
        risk_level="high",
        confidence=0.85,
        precipitation=PrecipitationInfo(
            mean_mm=45.2,
            max_mm=78.5,
            source="NASA_GPM_IMERG",
            hours_analyzed=3,
            is_simulated=False
        ),
        risk_factors=RiskFactors(
            precipitation_contribution=0.68,
            terrain_contribution=0.45,
            time_factor=1.05
        ),
        risk_zones_geojson={
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"flood_probability": 0.85, "risk_level": "critical"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[17.02, 51.10], [17.04, 51.10], [17.04, 51.12], [17.02, 51.12], [17.02, 51.10]]]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {"flood_probability": 0.65, "risk_level": "high"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[17.04, 51.10], [17.06, 51.10], [17.06, 51.12], [17.04, 51.12], [17.04, 51.10]]]
                    }
                }
            ]
        },
        evacuation_priorities=[
            EvacuationPriority(
                osm_id=12345,
                name="Szpital Uniwersytecki",
                building_type="hospital",
                lat=51.11,
                lon=17.03,
                risk_level="critical",
                flood_probability=0.88,
                evacuation_score=0.88,
                estimated_time_to_flood_hours=3.5,
                people_estimate=450
            ),
            EvacuationPriority(
                osm_id=23456,
                name="Szkoła Podstawowa nr 12",
                building_type="school",
                lat=51.105,
                lon=17.025,
                risk_level="high",
                flood_probability=0.72,
                evacuation_score=0.68,
                estimated_time_to_flood_hours=4.8,
                people_estimate=320
            ),
            EvacuationPriority(
                osm_id=34567,
                name="Blok mieszkalny",
                building_type="apartments",
                lat=51.108,
                lon=17.035,
                risk_level="high",
                flood_probability=0.65,
                evacuation_score=0.46,
                estimated_time_to_flood_hours=5.2,
                people_estimate=180
            )
        ],
        processing_time_seconds=0.15,
        next_update_minutes=30
    )

