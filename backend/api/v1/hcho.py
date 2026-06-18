"""
api/v1/hcho.py
--------------
HCHO (formaldehyde) and hotspot API endpoints.

Routes:
    GET /hcho               → raster metadata for a date / composite
    GET /hotspots           → GeoJSON FeatureCollection of HCHO hotspots
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from models.schemas import (
    HotspotFeature,
    HotspotFeatureCollection,
    HotspotProperties,
    SignificanceLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["HCHO & Hotspots"])


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_HOTSPOTS: List[dict] = [
    {
        "lat": 30.25, "lon": 76.80,
        "width": 0.5,
        "mean_hcho": 9.1e-16,
        "significance": "extreme",
        "fire_count": 22,
        "source_region": "Punjab",
    },
    {
        "lat": 28.90, "lon": 77.50,
        "width": 0.4,
        "mean_hcho": 7.5e-16,
        "significance": "high",
        "fire_count": 14,
        "source_region": "Haryana",
    },
    {
        "lat": 25.60, "lon": 85.10,
        "width": 0.3,
        "mean_hcho": 6.2e-16,
        "significance": "high",
        "fire_count": 8,
        "source_region": "Bihar",
    },
    {
        "lat": 22.30, "lon": 73.20,
        "width": 0.35,
        "mean_hcho": 5.8e-16,
        "significance": "moderate",
        "fire_count": 5,
        "source_region": "Gujarat",
    },
    {
        "lat": 15.50, "lon": 75.00,
        "width": 0.25,
        "mean_hcho": 4.3e-16,
        "significance": "low",
        "fire_count": 2,
        "source_region": "Karnataka",
    },
]


def _build_polygon(lat: float, lon: float, half: float) -> dict:
    """Build a simple square GeoJSON polygon centred at (lat, lon)."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half, lat - half],
            [lon + half, lat - half],
            [lon + half, lat + half],
            [lon - half, lat + half],
            [lon - half, lat - half],
        ]],
    }


def _make_mock_hotspot_feature(h: dict, ref_date: date) -> HotspotFeature:
    return HotspotFeature(
        type="Feature",
        geometry=_build_polygon(h["lat"], h["lon"], h["width"] / 2),
        properties=HotspotProperties(
            date=ref_date,
            mean_hcho=h["mean_hcho"],
            significance=SignificanceLevel(h["significance"]),
            fire_count=h["fire_count"],
            source_region=h["source_region"],
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/hcho",
    summary="HCHO raster metadata",
    description=(
        "Returns metadata for the HCHO (formaldehyde) column-density raster "
        "on a given date. Supports daily and multi-day composite modes."
    ),
    response_model=None,
)
async def get_hcho_metadata(
    date: Optional[date] = Query(
        None,
        description="Date (YYYY-MM-DD). Defaults to yesterday.",
    ),
    composite: Literal["daily", "8day", "monthly"] = Query(
        "daily",
        description="Temporal composite type.",
    ),
):
    """
    Return metadata for the HCHO raster layer.

    In DEV_MODE returns a mock response. In production the COG is checked
    for existence and 404 is raised if not found.
    """
    query_date = date if date is not None else _yesterday()

    if not settings.DEV_MODE:
        from services.raster import list_available_dates
        available = list_available_dates("hcho")
        if query_date not in available:
            raise HTTPException(
                status_code=404,
                detail=f"HCHO raster not available for date {query_date.isoformat()}.",
            )

    tile_url = f"/tiles/hcho/{{z}}/{{x}}/{{y}}.png?date={query_date.isoformat()}&composite={composite}&colormap=plasma"

    return {
        "layer": "hcho",
        "date": query_date.isoformat(),
        "composite": composite,
        "tile_url_template": tile_url,
        "description": "HCHO vertical column density from Sentinel-5P TROPOMI",
        "units": "mol/cm²",
        "crs": "EPSG:4326",
        "sensor": "Sentinel-5P TROPOMI",
        "is_mock": settings.DEV_MODE,
    }


@router.get(
    "/hotspots",
    summary="HCHO hotspot features",
    description=(
        "Returns a GeoJSON FeatureCollection of HCHO hotspot polygons detected "
        "within the specified date range. Each feature carries significance level, "
        "mean HCHO value, co-located FIRMS fire count, and the administrative region."
    ),
    response_model=HotspotFeatureCollection,
    responses={
        404: {"description": "No hotspot data available for the requested range"},
        422: {"description": "Validation error (invalid date range)"},
    },
)
async def get_hotspots(
    start: Optional[date] = Query(
        None,
        description="Start date (YYYY-MM-DD). Defaults to 7 days ago.",
    ),
    end: Optional[date] = Query(
        None,
        description="End date (YYYY-MM-DD). Defaults to yesterday.",
    ),
    min_significance: SignificanceLevel = Query(
        SignificanceLevel.LOW,
        description="Minimum significance level to include in results.",
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of features to return."),
):
    """
    Return HCHO hotspot GeoJSON features for the specified date range.

    In DEV_MODE returns a curated mock dataset. In production mode the
    database / derived products are queried.
    """
    end_date = end if end is not None else _yesterday()
    start_date = start if start is not None else (end_date - timedelta(days=7))

    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail=f"start ({start_date}) must be ≤ end ({end_date}).",
        )

    _sig_order = {
        SignificanceLevel.LOW: 0,
        SignificanceLevel.MODERATE: 1,
        SignificanceLevel.HIGH: 2,
        SignificanceLevel.EXTREME: 3,
    }
    min_level = _sig_order[min_significance]

    if settings.DEV_MODE:
        # Filter by significance and limit
        filtered = [
            h for h in _MOCK_HOTSPOTS
            if _sig_order[SignificanceLevel(h["significance"])] >= min_level
        ][:limit]

        features = [
            _make_mock_hotspot_feature(h, end_date)
            for h in filtered
        ]
    else:
        # Production: query from database / geoparquet / derived products
        # Placeholder — replace with real DB query
        raise HTTPException(
            status_code=503,
            detail="Production hotspot database not yet connected. Set DEV_MODE=true.",
        )

    return HotspotFeatureCollection(
        type="FeatureCollection",
        features=features,
        total=len(features),
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _yesterday() -> date:
    from datetime import datetime
    return (datetime.utcnow() - timedelta(days=1)).date()
