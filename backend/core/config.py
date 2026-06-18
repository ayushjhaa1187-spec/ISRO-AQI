"""
core/config.py
--------------
Centralised application configuration using pydantic-settings.
All values can be overridden via environment variables or a .env file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    APP_NAME: str = "ISRO AQI & HCHO Hotspot Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # DEV_MODE → return rich mock data when real DB / COG files are absent
    DEV_MODE: bool = True

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> List[str]:
        """Allow a comma-separated string as well as a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://aqi_user:aqi_pass@localhost:5432/aqi_hcho_db"

    # ------------------------------------------------------------------
    # COG (Cloud-Optimised GeoTIFF) storage
    # ------------------------------------------------------------------
    # Root directory that contains sub-folders: aqi/, hcho/, fire/ etc.
    COG_BASE_PATH: str = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cogs")

    # ------------------------------------------------------------------
    # Redis (used for async export job queuing)
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # TiTiler
    # ------------------------------------------------------------------
    TITILER_ENDPOINT: str = "/tiles"

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @property
    def cog_base_path_abs(self) -> str:
        """Return the absolute, normalised COG base path."""
        return os.path.normpath(os.path.abspath(self.COG_BASE_PATH))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Module-level convenience alias so callers can do:
#   from core.config import settings
settings: Settings = get_settings()
