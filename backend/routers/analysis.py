"""
CrisisEye - Analysis Router
Główne endpointy do analizy powodzi
"""

import time
from fastapi import APIRouter, HTTPException
from typing import Optional

from models.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    AnalysisStatus,
    BuildingsRequest,
    BuildingsResponse,
    FloodMaskResponse,
    FloodPixelStats
)
from services.flood_detector import FloodDetector
from services.osm_service import OSMService
from services.sar_processor import SARProcessor

router = APIRouter()

# Inicjalizacja serwisów
flood_detector = FloodDetector()
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
