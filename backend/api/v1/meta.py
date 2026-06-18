"""
api/v1/meta.py
--------------
Metadata endpoints for the ISRO AQI & HCHO Hotspot Platform.

Routes:
    GET /meta/dates     → Available raster dates for a given layer
    GET /meta/layers    → List of all available data layers
    GET /meta/health    → Lightweight liveness probe (same as /health on root)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from models.schemas import MetaDates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta", tags=["Metadata"])


# ---------------------------------------------------------------------------
# Supported layers
# ---------------------------------------------------------------------------

_LAYER_DESCRIPTIONS = {
    "aqi":  "Surface AQI (composite CPCB index)",
    "hcho": "HCHO column density (Sentinel-5P TROPOMI)",
    "fire": "FIRMS active-fire detections (VIIRS + MODIS)",
    "pm25": "PM2.5 concentration (µg/m³)",
    "pm10": "PM10 concentration (µg/m³)",
}


def _mock_dates(layer: str, n: int = 60) -> List[date]:
    """
    Generate a list of n consecutive daily dates ending yesterday.
    Skips weekends for 'hcho' to simulate satellite orbit gaps.
    """
    from datetime import datetime
    end = (datetime.utcnow() - timedelta(days=1)).date()
    all_dates: List[date] = []
    cursor = end - timedelta(days=n - 1)
    while cursor <= end:
        # Simulate that HCHO composites may have 2-day gaps (orbit repeat)
        if layer == "hcho" and cursor.weekday() == 6:  # skip Sundays
            cursor += timedelta(days=1)
            continue
        all_dates.append(cursor)
        cursor += timedelta(days=1)
    return sorted(all_dates)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/dates",
    summary="Available raster dates",
    description=(
        "Returns the list of dates for which a COG raster is available for "
        "the specified layer. Use this to populate date-picker widgets in the UI."
    ),
    response_model=MetaDates,
    responses={
        404: {"description": "Unknown layer"},
    },
)
async def get_available_dates(
    layer: str = Query(
        "aqi",
        description="Layer identifier: aqi | hcho | fire | pm25 | pm10",
    ),
    limit: int = Query(
        365,
        ge=1,
        le=1000,
        description="Maximum number of dates to return (most recent first).",
    ),
):
    """
    Return the list of available raster dates for a layer.

    In DEV_MODE returns a synthetic list covering the last 60 days.
    In production mode scans the COG directory for real files.
    """
    if layer not in _LAYER_DESCRIPTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown layer '{layer}'. Supported layers: {list(_LAYER_DESCRIPTIONS.keys())}",
        )

    if settings.DEV_MODE:
        available = _mock_dates(layer, n=min(60, limit))
    else:
        from services.raster import list_available_dates
        available = list_available_dates(layer)

    # Apply limit (most recent first)
    available_sorted = sorted(available, reverse=True)[:limit]
    available_sorted.reverse()  # back to ascending for the response

    latest = available_sorted[-1] if available_sorted else None
    earliest = available_sorted[0] if available_sorted else None

    return MetaDates(
        layer=layer,
        available_dates=available_sorted,
        latest=latest,
        earliest=earliest,
        total_count=len(available_sorted),
    )


@router.get(
    "/layers",
    summary="Available data layers",
    description="Returns a list of all supported data layers with their descriptions.",
    response_model=None,
)
async def get_layers():
    """Return all available data layers and their descriptions."""
    return {
        "layers": [
            {"id": k, "description": v}
            for k, v in _LAYER_DESCRIPTIONS.items()
        ]
    }
