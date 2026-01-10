"""
CrisisEye - Konfiguracja aplikacji
Hackathon "AI między orbitami" 2026
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Główna konfiguracja aplikacji"""
    
    # App
    app_name: str = "CrisisEye"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Google Earth Engine
    gee_project_id: str = "natural-cistern-305412"
    google_application_credentials: str = ""
    
    # API Settings
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # SAR Processing
    sar_default_polarization: str = "VV"
    flood_threshold: float = -15.0  # dB threshold dla detekcji wody
    
    # Model paths
    app_model_cache_dir: str = "./models_cache"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Singleton dla ustawień"""
    return Settings()


settings = get_settings()
