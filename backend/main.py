"""
CrisisEye - FastAPI Main Entry Point
Hackathon "AI między orbitami" 2026

System do wykrywania powodzi z danych radarowych SAR.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routers import analysis, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management - inicjalizacja przy starcie"""
    print(f"🛰️  Starting {settings.app_name} v{settings.app_version}")
    print(f"📡 SAR Polarization: {settings.sar_default_polarization}")
    print(f"🌊 Flood Threshold: {settings.flood_threshold} dB")
    
    # Tutaj można zainicjalizować połączenie z GEE
    # await initialize_gee()
    
    yield
    
    # Cleanup przy zamknięciu
    print("👋 Shutting down CrisisEye...")


# Inicjalizacja FastAPI
app = FastAPI(
    title=settings.app_name,
    description="System wykrywania powodzi z danych SAR - Hackathon 'AI między orbitami'",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(analysis.router, prefix=settings.api_prefix, tags=["Analysis"])


@app.get("/")
async def root():
    """Root endpoint z informacjami o API"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Flood detection from SAR data",
        "docs": "/docs",
        "health": "/health"
    }
