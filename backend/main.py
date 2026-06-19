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
from fastapi import FastAPI, Request, Response
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
# Mock Spatial Tile Server (DEV_MODE fallback for dynamic maps)
# ---------------------------------------------------------------------------

import math
import io
from PIL import Image
import numpy as np
from typing import Optional

def tile_bounds(z: int, x: int, y: int):
    """Get the bounding box of a tile in latitude and longitude."""
    n = 2.0 ** z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    
    lat_min_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    lat_max_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    
    lat_min = math.degrees(lat_min_rad)
    lat_max = math.degrees(lat_max_rad)
    
    return lon_min, lat_min, lon_max, lat_max

@app.get("/tiles/{layer}/{z}/{x}/{y}.png", tags=["Tiles (TiTiler)"])
async def serve_mock_tile(layer: str, z: int, x: int, y: int, date: Optional[str] = None):
    # Only run mock spatial overlays if in DEV_MODE and files are absent
    if not settings.DEV_MODE:
        # Let default FastAPI / TiTiler handle it or raise 404
        return Response(status_code=404, content="Tile not found")

    lon_min, lat_min, lon_max, lat_max = tile_bounds(z, x, y)
    
    # Check intersection with India bounding box (approximate)
    if lon_max < 65.0 or lon_min > 98.0 or lat_max < 5.0 or lat_min > 38.0:
        # Return transparent tile
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
        
    grid_size = 32
    lats = np.linspace(lat_max, lat_min, grid_size)
    lons = np.linspace(lon_min, lon_max, grid_size)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # Generate spatial layers representing India's air quality, HCHO, and fire zones
    if layer in ("aqi", "pm25", "pm10"):
        # Indo-Gangetic Plain pollution zone (Delhi hotspot)
        d_igp = np.exp(-((lat_grid - 27.5)/3.5)**2 - ((lon_grid - 81.0)/7.0)**2)
        # Central-Eastern forest fires & industrial belt (Odisha/Jharkhand)
        d_east = np.exp(-((lat_grid - 22.0)/3.0)**2 - ((lon_grid - 84.5)/3.0)**2)
        # Western industrial zone (Gujarat/Mumbai)
        d_west = np.exp(-((lat_grid - 20.0)/3.0)**2 - ((lon_grid - 73.0)/3.0)**2)
        # Southern cleaner zone (Bangalore/Chennai)
        d_south = np.exp(-((lat_grid - 13.0)/4.0)**2 - ((lon_grid - 78.5)/4.0)**2)
        
        val_grid = 45.0 + 240.0 * d_igp + 110.0 * d_east + 60.0 * d_west + 35.0 * d_south
        
        rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)
        for r in range(grid_size):
            for c in range(grid_size):
                v = val_grid[r, c]
                lat_val = lat_grid[r, c]
                lon_val = lon_grid[r, c]
                
                # Exclude pixels clearly outside land boundaries
                if (lat_val < 20 and lon_val < 71.5) or (lat_val < 15 and lon_val > 81) or (lat_val < 20 and lon_val > 86):
                    rgba[r, c] = [0, 0, 0, 0]
                    continue
                    
                if v <= 50:
                    rgba[r, c] = [0, 228, 0, 80]
                elif v <= 100:
                    rgba[r, c] = [255, 255, 0, 80]
                elif v <= 200:
                    rgba[r, c] = [255, 126, 0, 120]
                elif v <= 300:
                    rgba[r, c] = [255, 0, 0, 150]
                elif v <= 400:
                    rgba[r, c] = [143, 63, 151, 160]
                else:
                    rgba[r, c] = [126, 0, 35, 170]
                    
    elif layer == "hcho":
        # HCHO satellite columns (Sentinel-5P TROPOMI)
        # Stubble burning in Punjab/Haryana (lat 30.5, lon 75.8)
        h_punjab = np.exp(-((lat_grid - 30.5)/1.5)**2 - ((lon_grid - 75.8)/1.5)**2)
        # Forest fire / agricultural burnings in Central/Eastern India (Odisha/Jharkhand)
        h_central = np.exp(-((lat_grid - 22.0)/2.5)**2 - ((lon_grid - 84.5)/2.5)**2)
        # IGP secondary HCHO source
        h_igp = np.exp(-((lat_grid - 26.5)/3.0)**2 - ((lon_grid - 82.0)/6.0)**2)
        
        val_grid = 1.5 + 9.5 * h_punjab + 5.5 * h_central + 3.0 * h_igp
        rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)
        for r in range(grid_size):
            for c in range(grid_size):
                v = val_grid[r, c]
                lat_val = lat_grid[r, c]
                lon_val = lon_grid[r, c]
                if (lat_val < 20 and lon_val < 71.5) or (lat_val < 15 and lon_val > 81) or (lat_val < 20 and lon_val > 86):
                    rgba[r, c] = [0, 0, 0, 0]
                    continue
                
                norm = min(1.0, max(0.0, (v - 1.5) / 10.0))
                if norm < 0.1:
                    rgba[r, c] = [0, 0, 0, 0]
                else:
                    red = int(80 + norm * 175)
                    green = int(20 + norm * 180)
                    blue = int(140 - norm * 80)
                    alpha = int(30 + norm * 140)
                    rgba[r, c] = [red, green, blue, alpha]
                    
    else: # fire density or other
        # FIRMS active fires (VIIRS/MODIS)
        f_punjab = np.exp(-((lat_grid - 30.5)/1.2)**2 - ((lon_grid - 75.8)/1.2)**2)
        f_central = np.exp(-((lat_grid - 22.0)/2.2)**2 - ((lon_grid - 84.5)/2.2)**2)
        f_east = np.exp(-((lat_grid - 26.0)/2.0)**2 - ((lon_grid - 92.5)/2.0)**2)
        
        val_grid = f_punjab * 10.0 + f_central * 6.0 + f_east * 5.0
        rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)
        for r in range(grid_size):
            for c in range(grid_size):
                v = val_grid[r, c]
                lat_val = lat_grid[r, c]
                lon_val = lon_grid[r, c]
                if (lat_val < 20 and lon_val < 71.5) or (lat_val < 15 and lon_val > 81) or (lat_val < 20 and lon_val > 86):
                    rgba[r, c] = [0, 0, 0, 0]
                    continue
                
                if v < 0.5:
                    rgba[r, c] = [0, 0, 0, 0]
                else:
                    norm = min(1.0, v / 8.0)
                    red = 255
                    green = int(220 - norm * 200)
                    blue = int(50 - norm * 50)
                    alpha = int(40 + norm * 140)
                    rgba[r, c] = [red, green, blue, alpha]
                    
    img = Image.fromarray(rgba, "RGBA")
    img = img.resize((256, 256), Image.Resampling.BILINEAR)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


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
