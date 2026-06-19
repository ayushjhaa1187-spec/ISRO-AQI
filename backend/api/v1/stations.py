"""
api/v1/stations.py
------------------
CPCB monitoring station endpoints.

Routes:
    GET /stations                           → GeoJSON FeatureCollection of all stations
    GET /stations/{station_id}/timeseries   → AQI time-series for a specific station
"""

from __future__ import annotations

import logging
import random
import requests
import time
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from models.schemas import (
    StationFeature,
    StationFeatureCollection,
    StationSummary,
    TimeseriesPoint,
    TimeseriesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["CPCB Stations"])


# ---------------------------------------------------------------------------
# Mock CPCB station database
# ---------------------------------------------------------------------------

_MOCK_STATIONS: List[dict] = [
    {"id": "DL001", "name": "Anand Vihar",            "lat": 28.6477, "lon": 77.3152, "city": "Delhi",     "state": "Delhi",       "last_aqi": 278.0},
    {"id": "DL002", "name": "ITO",                    "lat": 28.6289, "lon": 77.2408, "city": "Delhi",     "state": "Delhi",       "last_aqi": 201.0},
    {"id": "DL003", "name": "R K Puram",              "lat": 28.5641, "lon": 77.1872, "city": "Delhi",     "state": "Delhi",       "last_aqi": 245.0},
    {"id": "DL004", "name": "Punjabi Bagh",           "lat": 28.6733, "lon": 77.1350, "city": "Delhi",     "state": "Delhi",       "last_aqi": 263.0},
    {"id": "MH001", "name": "Bandra",                 "lat": 19.0596, "lon": 72.8295, "city": "Mumbai",    "state": "Maharashtra", "last_aqi": 98.0},
    {"id": "MH002", "name": "Chembur",                "lat": 19.0624, "lon": 72.8995, "city": "Mumbai",    "state": "Maharashtra", "last_aqi": 115.0},
    {"id": "MH003", "name": "Pune Katraj",            "lat": 18.4529, "lon": 73.8567, "city": "Pune",      "state": "Maharashtra", "last_aqi": 88.0},
    {"id": "TN001", "name": "Chennai Alandur",        "lat": 13.0012, "lon": 80.2058, "city": "Chennai",   "state": "Tamil Nadu",  "last_aqi": 75.0},
    {"id": "TN002", "name": "Chennai Manali",         "lat": 13.1688, "lon": 80.2642, "city": "Chennai",   "state": "Tamil Nadu",  "last_aqi": 142.0},
    {"id": "WB001", "name": "Kolkata Jadavpur",       "lat": 22.4996, "lon": 88.3696, "city": "Kolkata",   "state": "West Bengal", "last_aqi": 168.0},
    {"id": "WB002", "name": "Kolkata Rabindra Sarani","lat": 22.5951, "lon": 88.3638, "city": "Kolkata",   "state": "West Bengal", "last_aqi": 185.0},
    {"id": "TS001", "name": "Hyderabad Bollaram",     "lat": 17.5400, "lon": 78.3640, "city": "Hyderabad", "state": "Telangana",   "last_aqi": 91.0},
    {"id": "KA001", "name": "Bengaluru BTM Layout",   "lat": 12.9166, "lon": 77.6101, "city": "Bengaluru", "state": "Karnataka",   "last_aqi": 107.0},
    {"id": "UP001", "name": "Lucknow Talkatora",      "lat": 26.8522, "lon": 80.9189, "city": "Lucknow",   "state": "Uttar Pradesh","last_aqi": 230.0},
    {"id": "GJ001", "name": "Ahmedabad Maninagar",    "lat": 23.0173, "lon": 72.6069, "city": "Ahmedabad", "state": "Gujarat",     "last_aqi": 120.0},
]

_STATION_MAP = {s["id"]: s for s in _MOCK_STATIONS}


# ---------------------------------------------------------------------------
# Live WAQI Fetcher with Cache
# ---------------------------------------------------------------------------
_STATION_AQI_CACHE = {}
_CACHE_TTL = 300  # 5 minutes

_STATION_FEED_MAP = {
    "DL001": "delhi/anand-vihar",
    "DL002": "delhi/ito",
    "DL003": "delhi/r.-k.-puram",
    "DL004": "delhi/punjabi-bagh",
    "MH001": "mumbai/bandra",
    "MH002": "mumbai/chembur",
    "MH003": "pune",
    "TN001": "chennai/alandur",
    "TN002": "chennai/manali",
    "WB001": "kolkata/jadavpur",
    "WB002": "kolkata/rabindra-sarani",
    "TS001": "hyderabad",
    "KA001": "bangalore",
    "UP001": "lucknow",
    "GJ001": "ahmedabad",
}

def _fetch_live_aqi(station_id: str, fallback_aqi: float) -> float:
    now = time.time()
    cache_entry = _STATION_AQI_CACHE.get(station_id)
    if cache_entry and (now - cache_entry["timestamp"] < _CACHE_TTL):
        return cache_entry["aqi"]
    
    feed_path = _STATION_FEED_MAP.get(station_id)
    if not feed_path:
        return fallback_aqi
        
    try:
        url = f"https://api.waqi.info/feed/{feed_path}/?token=demo"
        r = requests.get(url, timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                aqi = float(data["data"]["aqi"])
                _STATION_AQI_CACHE[station_id] = {"aqi": aqi, "timestamp": now}
                return aqi
    except Exception as e:
        logger.warning(f"Failed to fetch live AQI for station {station_id}: {e}")
        
    return fallback_aqi


def _station_to_feature(s: dict) -> StationFeature:
    now = datetime.now(tz=timezone.utc)
    live_aqi = _fetch_live_aqi(s["id"], s["last_aqi"])
    return StationFeature(
        type="Feature",
        geometry={"type": "Point", "coordinates": [s["lon"], s["lat"]]},
        properties=StationSummary(
            id=s["id"],
            name=s["name"],
            lat=s["lat"],
            lon=s["lon"],
            city=s["city"],
            state=s["state"],
            has_timeseries=True,
            last_aqi=live_aqi,
            last_updated=now - timedelta(hours=random.randint(1, 6)),
        ),
    )


# ---------------------------------------------------------------------------
# Mock time-series generator (anchored to live AQI)
# ---------------------------------------------------------------------------

def _generate_timeseries(
    station: dict,
    days: int,
    pollutant: str = "AQI",
) -> List[TimeseriesPoint]:
    """
    Generate synthetic AQI time-series data with realistic diurnal variation
    and a random-walk trend, anchored to current live values.
    """
    rng = random.Random(hash(station["id"]))
    base_aqi = _fetch_live_aqi(station["id"], station["last_aqi"])
    points: List[TimeseriesPoint] = []
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)

    for hour_offset in range(days * 24, 0, -1):
        ts = now - timedelta(hours=hour_offset)
        hour = ts.hour

        # Diurnal pattern: peak at 08:00 and 20:00 (rush hours)
        diurnal = 1.0 + 0.3 * (
            max(0, 1 - abs(hour - 8) / 4) + max(0, 1 - abs(hour - 20) / 4)
        )
        noise = rng.gauss(0, base_aqi * 0.05)
        observed = max(10, round(base_aqi * diurnal + noise, 1))

        # Predicted: slight smooth offset
        predicted = max(10, round(observed * rng.uniform(0.92, 1.08), 1))

        points.append(
            TimeseriesPoint(
                datetime=ts,
                observed=observed,
                predicted=predicted,
                pollutant=pollutant,
            )
        )

    return points


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="All CPCB monitoring stations",
    description=(
        "Returns a GeoJSON FeatureCollection of all CPCB ambient air-quality "
        "monitoring stations with their latest AQI reading."
    ),
    response_model=StationFeatureCollection,
)
async def get_stations(
    state: Optional[str] = Query(None, description="Filter by state/UT name (case-insensitive)."),
    city: Optional[str] = Query(None, description="Filter by city name (case-insensitive)."),
    min_aqi: Optional[float] = Query(None, ge=0, description="Return only stations with AQI ≥ min_aqi."),
    max_aqi: Optional[float] = Query(None, ge=0, description="Return only stations with AQI ≤ max_aqi."),
):
    """
    Return all CPCB monitoring stations as a GeoJSON FeatureCollection.

    Supports optional filtering by state, city, and AQI range.
    """
    if not settings.DEV_MODE:
        # Production: query from PostGIS / database
        raise HTTPException(status_code=503, detail="Database not connected. Use DEV_MODE=true.")

    stations = list(_MOCK_STATIONS)

    if state:
        stations = [s for s in stations if state.lower() in s["state"].lower()]
    if city:
        stations = [s for s in stations if city.lower() in s["city"].lower()]

    features = []
    for s in stations:
        feature = _station_to_feature(s)
        live_aqi = feature.properties.last_aqi
        if min_aqi is not None and (live_aqi is None or live_aqi < min_aqi):
            continue
        if max_aqi is not None and (live_aqi is None or live_aqi > max_aqi):
            continue
        features.append(feature)
    return StationFeatureCollection(
        type="FeatureCollection",
        features=features,
        total=len(features),
    )


@router.get(
    "/{station_id}/timeseries",
    summary="Station AQI time-series",
    description=(
        "Returns hourly AQI time-series (observed + ML-predicted) for a specific "
        "CPCB station. The range parameter controls how many past days to include."
    ),
    response_model=TimeseriesResponse,
    responses={
        404: {"description": "Station not found"},
        422: {"description": "Invalid range format"},
    },
)
async def get_station_timeseries(
    station_id: str,
    range: str = Query(
        "30d",
        description="Time range, e.g. '7d', '30d', '90d'. Max 365d.",
        pattern=r"^\d+d$",
    ),
    pollutant: str = Query("AQI", description="Pollutant or 'AQI' for composite index."),
):
    """
    Return an hourly AQI time-series for the requested station.

    Range format: '<N>d' where N is 1–365.
    In DEV_MODE, synthetic data is generated.
    """
    station = _STATION_MAP.get(station_id.upper())
    if station is None:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{station_id}' not found. Use GET /stations to list available IDs.",
        )

    days = int(range.rstrip("d"))
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=422,
            detail="Range must be between 1d and 365d.",
        )

    if settings.DEV_MODE:
        data = _generate_timeseries(station, days, pollutant)
    else:
        raise HTTPException(status_code=503, detail="Database not connected. Use DEV_MODE=true.")

    return TimeseriesResponse(
        station_id=station_id.upper(),
        station_name=station["name"],
        range_days=days,
        data=data,
    )
