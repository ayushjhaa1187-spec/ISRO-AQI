"""
main.py
-------
FastAPI application entry point for the ISRO AQI & HCHO Hotspot Platform.

Features:
- Versioned API router mounted at /api/v1
- TiTiler dynamic tile router mounted at /tiles
- CORS middleware with configurable origins
- Full OpenAPI metadata
- /health liveness endpoint
- Structured logging
- Async lifespan context manager
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from core.config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Startup:  initialise DB connection pool, warm up COG index cache.
    Shutdown: gracefully close all connections.
    """
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   DEV_MODE  : %s", settings.DEV_MODE)
    logger.info("   DEBUG     : %s", settings.DEBUG)
    logger.info("   CORS      : %s", settings.CORS_ORIGINS)

    # --- Startup tasks ---
    if not settings.DEV_MODE:
        # Real DB pool initialisation would go here
        # e.g. await database.connect()
        logger.info("Production mode: connecting to database …")
    else:
        logger.info("DEV_MODE active — skipping real DB / COG initialisation.")

    yield  # App is running

    # --- Shutdown tasks ---
    logger.info("🛑 Shutting down %s …", settings.APP_NAME)
    if not settings.DEV_MODE:
        # await database.disconnect()
        pass
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "# ISRO Surface AQI & HCHO Hotspot Platform\n\n"
        "REST API powering the satellite-based air-quality and formaldehyde "
        "hotspot monitoring dashboard for India.\n\n"
        "## Data Sources\n"
        "- **Sentinel-5P TROPOMI** — HCHO vertical column density\n"
        "- **CPCB Ground Stations** — Observed AQI / pollutant concentrations\n"
        "- **FIRMS (VIIRS + MODIS)** — Active-fire detections\n\n"
        "## Key Features\n"
        "- Cloud-Optimised GeoTIFF (COG) raster serving via TiTiler\n"
        "- CPCB-compliant AQI computation for 6 regulated pollutants\n"
        "- Async export jobs (GeoTIFF / CSV / PDF)\n"
        "- Real-time & ML-predicted AQI time-series\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "ISRO / SAC AQI Platform Team",
        "url": "https://www.isro.gov.in",
        "email": "aqi-platform@isro.gov.in",
    },
    license_info={
        "name": "Government Open Data License – India (GODL)",
        "url": "https://data.gov.in/government-open-data-license-india",
    },
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for large GeoJSON responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ---------------------------------------------------------------------------
# Request timing middleware (lightweight)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Attach X-Process-Time header to every response (ms)."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    return response


# ---------------------------------------------------------------------------
# API v1 routers
# ---------------------------------------------------------------------------

from api.v1 import aqi, hcho, stations, fire, meta, export  # noqa: E402

api_v1_prefix = "/api/v1"

app.include_router(aqi.router,      prefix=api_v1_prefix)
app.include_router(hcho.router,     prefix=api_v1_prefix)
app.include_router(stations.router, prefix=api_v1_prefix)
app.include_router(fire.router,     prefix=api_v1_prefix)
app.include_router(meta.router,     prefix=api_v1_prefix)
app.include_router(export.router,   prefix=api_v1_prefix)


# ---------------------------------------------------------------------------
# TiTiler tile router
# ---------------------------------------------------------------------------

try:
    from titiler.core.factory import TilerFactory
    from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers

    cog_tiler = TilerFactory(router_prefix="/tiles")
    app.include_router(cog_tiler.router, prefix="/tiles", tags=["Tiles (TiTiler)"])
    add_exception_handlers(app, DEFAULT_STATUS_CODES)
    logger.info("TiTiler COG tiler mounted at /tiles")
except ImportError:
    logger.warning(
        "titiler not installed — tile endpoint (/tiles) will not be available. "
        "Install with: pip install titiler.core"
    )


# ---------------------------------------------------------------------------
# Root & Health endpoints
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root():
    """Redirect hint for the API root."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": "/api/v1",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Liveness probe",
    description="Returns 200 OK with service status. Used by load-balancers and k8s probes.",
    response_model=None,
)
async def health_check():
    """
    Liveness / readiness probe endpoint.

    Returns HTTP 200 with a JSON body containing service status and version.
    In production, this would also check DB connectivity.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "dev_mode": settings.DEV_MODE,
        },
    )


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "path": str(request.url.path)},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.exception("Unhandled error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Dev-server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
