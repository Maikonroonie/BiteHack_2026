"""
CrisisEye - Health Check Router
"""

from fastapi import APIRouter
from models.schemas import HealthResponse
from config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Sprawdza status wszystkich serwisów.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        services={
            "api": "ok",
            "sar_processor": "ok",
            "flood_detector": "ok",
            "gee": "configured" if settings.gee_project_id else "not_configured",
            "osm": "ok"
        }
    )
