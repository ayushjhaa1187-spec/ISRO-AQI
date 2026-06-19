"""
api/v1/fire.py
--------------
FIRMS (Fire Information for Resource Management System) fire detection endpoints.

Routes:
    GET /fire   → GeoJSON FeatureCollection of active fire points for a date
"""

from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from models.schemas import FireFeature, FireFeatureCollection, FirePoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fire", tags=["FIRMS Fire"])


# ---------------------------------------------------------------------------
# Mock fire data — representative stubble-burning / industrial fire locations
# ---------------------------------------------------------------------------

_BASE_FIRE_POINTS = [
    # Punjab / Haryana stubble burning belt
    {"lat": 30.45, "lon": 74.80, "frp": 42.3, "confidence": "high",    "satellite": "VIIRS"},
    {"lat": 30.62, "lon": 75.30, "frp": 31.7, "confidence": "high",    "satellite": "VIIRS"},
    {"lat": 30.12, "lon": 76.10, "frp": 18.2, "confidence": "nominal", "satellite": "MODIS"},
    {"lat": 29.98, "lon": 76.85, "frp": 55.1, "confidence": "high",    "satellite": "VIIRS"},
    {"lat": 30.78, "lon": 74.20, "frp": 22.4, "confidence": "nominal", "satellite": "VIIRS"},
    # Odisha / Jharkhand forest fires
    {"lat": 22.10, "lon": 84.50, "frp": 12.5, "confidence": "nominal", "satellite": "MODIS"},
    {"lat": 21.80, "lon": 85.20, "frp":  9.8, "confidence": "low",     "satellite": "MODIS"},
    {"lat": 23.50, "lon": 84.80, "frp": 16.3, "confidence": "nominal", "satellite": "VIIRS"},
    # North-east India
    {"lat": 26.30, "lon": 92.10, "frp": 28.6, "confidence": "high",    "satellite": "VIIRS"},
    {"lat": 25.70, "lon": 93.40, "frp": 19.4, "confidence": "nominal", "satellite": "VIIRS"},
    # Andhra / Telangana
    {"lat": 16.50, "lon": 79.80, "frp":  8.2, "confidence": "low",     "satellite": "MODIS"},
    {"lat": 17.20, "lon": 80.30, "frp": 11.1, "confidence": "nominal", "satellite": "MODIS"},
]


def _jitter(value: float, rng: random.Random, scale: float = 0.05) -> float:
    """Add small random jitter to avoid exact duplicate coordinates."""
    return round(value + rng.uniform(-scale, scale), 6)


def _generate_fire_points(ref_date: date) -> List[FirePoint]:
    """
    Generate a slightly-randomised set of fire points for a given date.
    Uses the date as a seed so results are reproducible.
    Also dynamically incorporates real-time CPCB station AQI observations:
    if station AQI > 100, adds correlated agricultural fire detections.
    """
    from api.v1.stations import _fetch_live_aqi

    rng = random.Random(ref_date.toordinal())
    points: List[FirePoint] = []

    # 1. Base fire points (climatology/historical mock)
    for bp in _BASE_FIRE_POINTS:
        # Randomly skip ~20% of points to simulate daily variation
        if rng.random() < 0.2:
            continue
        frp_jitter = round(bp["frp"] * rng.uniform(0.85, 1.15), 1)
        points.append(
            FirePoint(
                lat=_jitter(bp["lat"], rng),
                lon=_jitter(bp["lon"], rng),
                frp=frp_jitter,
                confidence=bp["confidence"],
                date=ref_date,
                satellite=bp["satellite"],
            )
        )

    # 2. Dynamic correlated fire points based on live AQI
    # We will check key cities and add agricultural/biomass burning fires around them
    # if the live AQI is elevated (>100).
    regions = [
        # (station_id, fallback_aqi, name, lat_min, lat_max, lon_min, lon_max)
        ("DL001", 278.0, "Punjab/Haryana", 29.8, 31.5, 74.0, 76.8),
        ("UP001", 230.0, "Uttar Pradesh", 26.2, 28.2, 79.5, 82.0),
        ("GJ001", 120.0, "Gujarat", 21.8, 23.8, 71.0, 73.2),
        ("KA001", 107.0, "Karnataka", 13.5, 15.5, 74.5, 76.5),
        ("MH001", 98.0, "Maharashtra", 18.0, 20.0, 74.0, 76.0),
    ]

    for station_id, fallback, region_name, lat_min, lat_max, lon_min, lon_max in regions:
        # Get live AQI
        live_aqi = _fetch_live_aqi(station_id, fallback)
        if live_aqi > 100:
            # Scale count of fires: e.g. 1 fire per 15 AQI points above 100 (cap at 20)
            extra_count = min(20, int((live_aqi - 100) / 15) + 2)
            for _ in range(extra_count):
                lat = round(rng.uniform(lat_min, lat_max), 6)
                lon = round(rng.uniform(lon_min, lon_max), 6)
                # Scale FRP with AQI: higher AQI = higher fire radiative power
                frp = round(15.0 + (live_aqi - 100) * rng.uniform(0.15, 0.4), 1)
                confidence = "high" if frp > 40 else "nominal"
                points.append(
                    FirePoint(
                        lat=lat,
                        lon=lon,
                        frp=frp,
                        confidence=confidence,
                        date=ref_date,
                        satellite=rng.choice(["VIIRS", "MODIS"]),
                    )
                )

    return points


def _fire_point_to_feature(fp: FirePoint) -> FireFeature:
    return FireFeature(
        type="Feature",
        geometry={"type": "Point", "coordinates": [fp.lon, fp.lat]},
        properties=fp,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="FIRMS active fire detections",
    description=(
        "Returns a GeoJSON FeatureCollection of FIRMS active-fire detection points "
        "(VIIRS / MODIS) for the specified date. Each feature includes Fire Radiative "
        "Power (FRP), detection confidence, and the detecting satellite."
    ),
    response_model=FireFeatureCollection,
    responses={
        404: {"description": "Fire data not available for the requested date"},
        422: {"description": "Invalid date format"},
    },
)
async def get_fire_points(
    date: Optional[date] = Query(
        None,
        description="Date (YYYY-MM-DD). Defaults to yesterday.",
    ),
    min_frp: Optional[float] = Query(
        None,
        ge=0,
        description="Minimum Fire Radiative Power (MW) threshold.",
    ),
    confidence: Optional[str] = Query(
        None,
        description="Filter by confidence: low | nominal | high",
    ),
    satellite: Optional[str] = Query(
        None,
        description="Filter by satellite: VIIRS | MODIS",
    ),
):
    """
    Return FIRMS active-fire detection points for the given date.

    In DEV_MODE a synthetic dataset is returned. In production mode
    the FIRMS data parquet / PostGIS table is queried.
    """
    from datetime import datetime
    query_date = date if date is not None else (datetime.utcnow() - timedelta(days=1)).date()

    # Sanity: don't allow future dates
    today = datetime.utcnow().date()
    if query_date > today:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot query future date {query_date.isoformat()}.",
        )

    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=503,
            detail="Production FIRMS database not connected. Use DEV_MODE=true.",
        )

    fire_points = _generate_fire_points(query_date)

    # Apply optional filters
    if min_frp is not None:
        fire_points = [fp for fp in fire_points if fp.frp >= min_frp]
    if confidence:
        fire_points = [fp for fp in fire_points if fp.confidence == confidence.lower()]
    if satellite:
        fire_points = [fp for fp in fire_points if fp.satellite.upper() == satellite.upper()]

    if not fire_points and not settings.DEV_MODE:
        raise HTTPException(
            status_code=404,
            detail=f"No fire detections found for date {query_date.isoformat()}.",
        )

    features = [_fire_point_to_feature(fp) for fp in fire_points]

    return FireFeatureCollection(
        type="FeatureCollection",
        features=features,
        total=len(features),
        query_date=query_date,
    )
