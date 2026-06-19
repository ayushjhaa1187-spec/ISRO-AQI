"""
api/v1/aqi.py
-------------
AQI-related API endpoints.

Routes:
    GET /aqi                  → raster metadata + tile URL template for a date
    GET /aqi/point            → full AQI assessment for a specific lat/lon/date
"""

from __future__ import annotations

import logging
import requests
import time
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from models.schemas import AQIResponse
from services.aqi_calc import compute_aqi, aqi_to_category

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aqi", tags=["AQI"])


# ---------------------------------------------------------------------------
# Mock data helpers (used when DEV_MODE=True or COG files are absent)
# ---------------------------------------------------------------------------

_MOCK_STATIONS = [
    # (lat, lon, PM2.5, PM10, NO2)
    (28.6139, 77.2090, 95.0,  180.0, 72.0),   # Delhi
    (19.0760, 72.8777, 42.0,  90.0,  50.0),   # Mumbai
    (13.0827, 80.2707, 28.0,  60.0,  35.0),   # Chennai
    (22.5726, 88.3639, 60.0,  140.0, 65.0),   # Kolkata
    (17.3850, 78.4867, 35.0,  80.0,  40.0),   # Hyderabad
]


def _live_aqi_for_point(lat: float, lon: float) -> Optional[dict]:
    try:
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token=demo"
        r = requests.get(url, timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                feed_data = data["data"]
                aqi_val = float(feed_data["aqi"])
                
                # Fetch dominant pollutant
                dom = str(feed_data.get("dominentpol", "PM2.5")).upper()
                if dom == "PM25":
                    dom = "PM2.5"
                elif not dom:
                    dom = "PM2.5"
                
                # Compute category & advice
                category, color_hex, health_advice = aqi_to_category(aqi_val)
                
                return {
                    "value": aqi_val,
                    "category": category,
                    "color_hex": color_hex,
                    "dominant_pollutant": dom,
                    "health_advice": health_advice,
                }
    except Exception as e:
        logger.warning(f"Failed to query live geolocated AQI for {lat},{lon}: {e}")
    return None


def _mock_aqi_for_point(lat: float, lon: float, query_date: date) -> dict:
    """Generate a deterministic mock AQI response for a lat/lon/date triple."""
    # Pick the "closest" mock station (very rough – just for demo purposes)
    best = min(
        _MOCK_STATIONS,
        key=lambda s: abs(s[0] - lat) + abs(s[1] - lon),
    )
    concs = {"PM2.5": best[2], "PM10": best[3], "NO2": best[4]}
    result = compute_aqi(concs)
    return result


def _build_tile_url_template(layer: str, query_date: date) -> str:
    return f"/tiles/{layer}/{{z}}/{{x}}/{{y}}.png?date={query_date.isoformat()}&colormap=rdylgn_r"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="AQI raster metadata",
    description=(
        "Returns metadata for the AQI raster layer on a given date, including "
        "the TiTiler XYZ tile URL template that can be consumed directly by "
        "Leaflet / MapLibre."
    ),
    response_model=None,
)
async def get_aqi_metadata(
    date: date = Query(
        default=None,
        description="Date to query (YYYY-MM-DD). Defaults to yesterday.",
        example="2024-01-15",
    ),
):
    """
    Return AQI raster metadata and tile URL template for the requested date.

    In DEV_MODE the response is mocked; real mode checks for a COG file and
    raises 404 if the date is not available.
    """
    if date is None:
        date = (date or _yesterday())

    query_date = date

    if not settings.DEV_MODE:
        from services.raster import list_available_dates, get_cog_path
        available = list_available_dates("aqi")
        if query_date not in available:
            raise HTTPException(
                status_code=404,
                detail=f"AQI raster not available for date {query_date.isoformat()}. "
                       f"Use GET /meta/dates?layer=aqi to see available dates.",
            )

    tile_url = _build_tile_url_template("aqi", query_date)

    return {
        "layer": "aqi",
        "date": query_date.isoformat(),
        "tile_url_template": tile_url,
        "description": "Surface AQI derived from Sentinel-5P TROPOMI + CPCB ground stations",
        "units": "AQI index (0–500+)",
        "crs": "EPSG:4326",
        "is_mock": settings.DEV_MODE,
    }


@router.get(
    "/point",
    summary="AQI at a geographic point",
    description=(
        "Queries the AQI COG at the supplied latitude/longitude for the given date "
        "and returns a full CPCB AQI assessment including category, colour, dominant "
        "pollutant and health advice."
    ),
    response_model=AQIResponse,
    responses={
        404: {"description": "AQI data not available for the requested date"},
        422: {"description": "Validation error (invalid lat/lon/date)"},
    },
)
async def get_aqi_point(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
    date: Optional[date] = Query(
        None,
        description="Date (YYYY-MM-DD). Defaults to yesterday.",
    ),
    predicted: bool = Query(
        False,
        description="If True, return ML-predicted AQI instead of observed.",
    ),
):
    """
    Return a full AQI assessment for a specific point and date.

    In DEV_MODE a mock value is computed from the nearest sample station.
    In production mode the COG is sampled at the requested coordinates.
    """
    query_date = date if date is not None else _yesterday()

    if settings.DEV_MODE:
        live_result = _live_aqi_for_point(lat, lon)
        if live_result is not None:
            result = live_result
        else:
            result = _mock_aqi_for_point(lat, lon, query_date)
    else:
        from services.raster import get_cog_path, query_cog_point_safe

        layer = "hcho" if predicted else "aqi"
        try:
            cog_path = get_cog_path("aqi", query_date)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"AQI COG not found for date {query_date.isoformat()}.",
            )

        raw_aqi = query_cog_point_safe(cog_path, lat, lon)
        if raw_aqi is None:
            raise HTTPException(
                status_code=404,
                detail="No AQI data at the specified coordinates for this date.",
            )

        category, color_hex, health_advice = aqi_to_category(raw_aqi)
        result = {
            "value": raw_aqi,
            "category": category,
            "color_hex": color_hex,
            "dominant_pollutant": "PM2.5",  # placeholder; real impl reads per-pollutant COGs
            "health_advice": health_advice,
        }

    tile_url = _build_tile_url_template("aqi", query_date)

    return AQIResponse(
        value=result["value"],
        category=result["category"],
        color_hex=result["color_hex"],
        dominant_pollutant=result["dominant_pollutant"],
        health_advice=result["health_advice"],
        lat=lat,
        lon=lon,
        date=query_date,
        is_predicted=predicted,
        tile_url_template=tile_url,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _yesterday() -> date:
    from datetime import datetime
    return (datetime.utcnow() - timedelta(days=1)).date()
