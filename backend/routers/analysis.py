"""
CrisisEye - Analysis Router
Główne endpointy do analizy powodzi - Wersja Hackathon MVP
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
from services.damage import DamageService
from services.gee_service import gee_service

router = APIRouter()

# Inicjalizacja serwisów
flood_detector = FloodDetector()
osm_service = OSMService()
sar_processor = SARProcessor()
damage_service = DamageService()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_flood(request: AnalysisRequest):
    """
    Główny endpoint analizy powodzi (Pipeline v2.1).
    
    Pipeline:
    1. Pobierz dane SAR (przed i po) oraz DEM (wysokość terenu)
    2. Wykonaj change detection i klasyfikację RandomForest
    3. Pobierz infrastrukturę z OSM i Microsoft Footprints
    4. Wykonaj Spatial Join (budynki vs maska powodzi)
    5. Oblicz straty finansowe na podstawie głębokości i stawek
    """
    start_time = time.time()
    
    try:
        # 1. Przetwarzanie SAR (Dane satelitarne)
        sar_data = await sar_processor.process_sar(
            bbox=request.bbox.to_list(),
            date_before=request.date_before,
            date_after=request.date_after,
            polarization=request.polarization
        )
        
        # Opcjonalnie: Pobranie DEM z GEE dla dokładnej głębokości
        # terrain_dem = await gee_service.get_terrain_elevation(request.bbox.to_list())
        
        # 2. Detekcja powodzi (Model AI - RandomForest)
        flood_result = await flood_detector.detect_flood(sar_data)
        
        # 3. Pobierz budynki (OSM Service)
        buildings = await osm_service.get_buildings(request.bbox.to_list())
        
        # 4. Sprawdź które budynki są zalane (Analiza przestrzenna zamiast losowania)
        # Wykorzystuje mapowanie współrzędnych na piksele maski
        flooded_buildings = flood_detector.check_buildings_flooding(
            buildings, 
            flood_result["mask"],
            request.bbox.to_list()
        )
        
        # 5. Oblicz realne straty finansowe
        # Formuła: powierzchnia * wartość_m2 * współczynnik_zniszczenia
        economic_stats = damage_service.calculate_losses(flooded_buildings)
        
        processing_time = time.time() - start_time
        
        # Budowanie finalnej odpowiedzi
        return AnalysisResponse(
            status=AnalysisStatus.COMPLETED,
            message="Analiza zakończona pomyślnie",
            stats=flood_result["stats"],
            flood_geojson=flood_result["geojson"],
            buildings_affected=len(flooded_buildings),
            estimated_loss_pln=economic_stats["total_loss_pln"], # Dodane pole finansowe
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        return AnalysisResponse(
            status=AnalysisStatus.FAILED,
            message=f"Błąd analizy: {str(e)}",
            processing_time_seconds=time.time() - start_time
        )


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
            date_before=request.date_before,
            date_after=request.date_after,
            polarization=request.polarization
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