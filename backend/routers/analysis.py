"""
CrisisEye - Analysis Router
Główne endpointy do analizy i PREDYKCJI powodzi
"""

import time
from datetime import datetime
from backend.services import flood_detector
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
from services.precipitation_service import precipitation_service
from services.terrain_service import terrain_service

router = APIRouter()

# Inicjalizacja serwisów
flood_predictor = FloodPredictor()
osm_service = OSMService()
sar_processor = SARProcessor()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_flood(request: AnalysisRequest):
    """
    Główny endpoint analizy powodzi.
    
    Pipeline:
    1. Pobierz dane SAR (przed i po powodzi)
    2. Wykonaj change detection
    3. Zastosuj RandomForest do klasyfikacji
    4. Wygeneruj maskę powodzi
    5. Pobierz budynki z OSM i sprawdź które są zalane
    
    Args:
        request: AnalysisRequest z bbox, datami i polaryzacją
        
    Returns:
        AnalysisResponse z statystykami i GeoJSON maski
    """
    start_time = time.time()
    
    try:
        # 1. Przetwarzanie SAR (symulacja dla hackathonu)
        sar_data = await sar_processor.process_sar(
            bbox=request.bbox.to_list(),
            date_before=request.date_before,
            date_after=request.date_after,
            polarization=request.polarization
        )
        
        # 2. Detekcja powodzi
        flood_result = await flood_detector.detect_flood(sar_data)
        
        # 3. Pobierz budynki i sprawdź które są zalane
        buildings = await osm_service.get_buildings(request.bbox.to_list())
        flooded_buildings = flood_detector.check_buildings_flooding(
            buildings, 
            flood_result["mask"]
        )
        
        # 4. Przygotuj response
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            status=AnalysisStatus.COMPLETED,
            message="Analiza zakończona pomyślnie",
            stats=flood_result["stats"],
            flood_geojson=flood_result["geojson"],
            buildings_affected=len(flooded_buildings),
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        return AnalysisResponse(
            status=AnalysisStatus.FAILED,
            message=f"Błąd analizy: {str(e)}",
            processing_time_seconds=time.time() - start_time
        )


@router.post("/buildings", response_model=BuildingsResponse)
async def get_buildings(request: BuildingsRequest):
    """
    Pobierz budynki z OpenStreetMap dla zadanego obszaru.
    
    Args:
        request: BuildingsRequest z bounding box
        
    Returns:
        BuildingsResponse z listą budynków
    """
    try:
        buildings = await osm_service.get_buildings(request.bbox.to_list())
        
        return BuildingsResponse(
            total_count=len(buildings),
            flooded_count=sum(1 for b in buildings if b.is_flooded),
            buildings=buildings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd pobierania budynków: {str(e)}")


@router.post("/flood-mask", response_model=FloodMaskResponse)
async def get_flood_mask(request: AnalysisRequest):
    """
    Generuj maskę powodzi w formacie GeoJSON.
    
    Uproszczona wersja /analyze - zwraca tylko maskę bez analizy budynków.
    """
    try:
        # Przetwarzanie SAR
        sar_data = await sar_processor.process_sar(
            bbox=request.bbox.to_list(),
            date_before=request.date_before,
            date_after=request.date_after,
            polarization=request.polarization
        )
        
        # Detekcja
        flood_result = await flood_detector.detect_flood(sar_data)
        
        return FloodMaskResponse(
            type="FeatureCollection",
            features=flood_result["geojson"].get("features", []),
            stats=flood_result["stats"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd generowania maski: {str(e)}")


@router.get("/demo")
async def get_demo_data():
    """
    Demo endpoint z przykładowymi danymi powodzi.
    Używany do testowania frontendu bez prawdziwych danych SAR.
    """
    # Przykładowe dane dla Wrocławia (powódź 1997)
    demo_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "flood_probability": 0.85,
                    "area_km2": 2.5
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [17.02, 51.10],
                        [17.04, 51.10],
                        [17.04, 51.12],
                        [17.02, 51.12],
                        [17.02, 51.10]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "flood_probability": 0.72,
                    "area_km2": 1.8
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [17.05, 51.08],
                        [17.08, 51.08],
                        [17.08, 51.10],
                        [17.05, 51.10],
                        [17.05, 51.08]
                    ]]
                }
            }
        ]
    }
    
    return AnalysisResponse(
        status=AnalysisStatus.COMPLETED,
        message="Demo data - Wrocław 1997 flood simulation",
        stats=FloodPixelStats(
            total_pixels=500000,
            flooded_pixels=75000,
            flood_percentage=15.0,
            area_km2=50.0,
            flooded_area_km2=7.5
        ),
        flood_geojson=demo_geojson,
        buildings_affected=1247,
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

