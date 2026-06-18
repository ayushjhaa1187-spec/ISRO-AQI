"""
models/schemas.py
-----------------
Pydantic v2 response schemas for the ISRO AQI & HCHO Hotspot Platform.

All models use strict typing and include field descriptions (used in the
auto-generated OpenAPI docs).
"""

from __future__ import annotations

from datetime import date as DateType, datetime as DatetimeType
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AQICategory(str, Enum):
    GOOD = "Good"
    SATISFACTORY = "Satisfactory"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very Poor"
    SEVERE = "Severe"


class ExportFormat(str, Enum):
    GEOTIFF = "geotiff"
    CSV = "csv"
    PDF = "pdf"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SignificanceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


# ---------------------------------------------------------------------------
# AQI
# ---------------------------------------------------------------------------


class AQIResponse(BaseModel):
    """Full AQI assessment for a specific location and date."""

    value: float = Field(..., ge=0, description="AQI value (0–500+)")
    category: AQICategory = Field(..., description="CPCB AQI category")
    color_hex: str = Field(..., description="Display colour as hex, e.g. '#00B050'")
    dominant_pollutant: str = Field(
        ..., description="Pollutant driving the AQI value, e.g. 'PM2.5'"
    )
    health_advice: str = Field(..., description="Public health guidance for this AQI level")
    lat: float = Field(..., ge=-90, le=90, description="Query latitude")
    lon: float = Field(..., ge=-180, le=180, description="Query longitude")
    date: DateType = Field(..., description="Observation / prediction date")
    is_predicted: bool = Field(
        False,
        description="True when the value comes from an ML forecast rather than observation",
    )
    tile_url_template: Optional[str] = Field(
        None,
        description="TiTiler XYZ tile URL template for this layer/date, e.g. /tiles/aqi/{z}/{x}/{y}.png?date=…",
    )

    model_config = {"json_schema_extra": {"example": {
        "value": 187,
        "category": "Poor",
        "color_hex": "#FE0000",
        "dominant_pollutant": "PM2.5",
        "health_advice": "Avoid prolonged outdoor activity. Sensitive groups must stay indoors.",
        "lat": 28.6139,
        "lon": 77.2090,
        "date": "2024-01-15",
        "is_predicted": False,
        "tile_url_template": "/tiles/aqi/{z}/{x}/{y}.png?date=2024-01-15",
    }}}


# ---------------------------------------------------------------------------
# HCHO / Hotspots
# ---------------------------------------------------------------------------


class HotspotProperties(BaseModel):
    """Properties attached to a HCHO hotspot GeoJSON feature."""

    date: DateType = Field(..., description="Date of the hotspot observation")
    mean_hcho: float = Field(..., description="Mean HCHO column density (mol/cm²)")
    significance: SignificanceLevel = Field(..., description="Statistical significance tier")
    fire_count: int = Field(0, ge=0, description="FIRMS active-fire count within the hotspot polygon")
    source_region: str = Field(..., description="Administrative region name")


class HotspotFeature(BaseModel):
    """GeoJSON Feature representing a single HCHO hotspot."""

    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON geometry (Polygon or Point)",
    )
    properties: HotspotProperties

    model_config = {"json_schema_extra": {"example": {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[77.0, 28.5], [77.5, 28.5], [77.5, 29.0], [77.0, 29.0], [77.0, 28.5]]],
        },
        "properties": {
            "date": "2024-01-15",
            "mean_hcho": 8.3e-16,
            "significance": "high",
            "fire_count": 12,
            "source_region": "Haryana",
        },
    }}}


class HotspotFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection of HCHO hotspots."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[HotspotFeature]
    total: int = Field(..., description="Total number of features")
    start_date: Optional[DateType] = None
    end_date: Optional[DateType] = None


# ---------------------------------------------------------------------------
# Stations (CPCB)
# ---------------------------------------------------------------------------


class StationSummary(BaseModel):
    """Summary of a CPCB air-quality monitoring station."""

    id: str = Field(..., description="Unique station identifier")
    name: str = Field(..., description="Station display name")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    city: str
    state: str = Field("", description="State / UT")
    has_timeseries: bool = Field(
        True, description="Whether historical time-series data is available"
    )
    last_aqi: Optional[float] = Field(None, description="Most recent AQI reading")
    last_updated: Optional[DatetimeType] = Field(None, description="Timestamp of last data update")


class StationFeature(BaseModel):
    """GeoJSON Feature wrapping a StationSummary."""

    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any]
    properties: StationSummary


class StationFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection of CPCB stations."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[StationFeature]
    total: int


# ---------------------------------------------------------------------------
# Timeseries
# ---------------------------------------------------------------------------


class TimeseriesPoint(BaseModel):
    """Single point in a station's AQI time-series."""

    datetime: DatetimeType = Field(..., description="Observation timestamp (UTC)")
    observed: Optional[float] = Field(None, description="Observed AQI value")
    predicted: Optional[float] = Field(None, description="ML-predicted AQI value")
    pollutant: str = Field("AQI", description="Pollutant or composite AQI label")

    @field_validator("observed", "predicted", mode="before")
    @classmethod
    def _round_value(cls, v: object) -> Optional[float]:
        if v is None:
            return None
        return round(float(v), 2)  # type: ignore[arg-type]


class TimeseriesResponse(BaseModel):
    """Complete time-series response for a station."""

    station_id: str
    station_name: str
    range_days: int
    data: List[TimeseriesPoint]


# ---------------------------------------------------------------------------
# Fire (FIRMS)
# ---------------------------------------------------------------------------


class FirePoint(BaseModel):
    """A single FIRMS active-fire detection point."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    frp: float = Field(..., ge=0, description="Fire Radiative Power (MW)")
    confidence: str = Field(..., description="Detection confidence: low | nominal | high")
    date: DateType
    satellite: str = Field("VIIRS", description="Detecting satellite (MODIS / VIIRS)")


class FireFeature(BaseModel):
    """GeoJSON Feature for a fire point."""

    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any]
    properties: FirePoint


class FireFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection of FIRMS fire detections."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[FireFeature]
    total: int
    query_date: DateType


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


class CorrelationStats(BaseModel):
    """Statistical correlation between AQI and HCHO for a region/period."""

    pearson_r: float = Field(..., ge=-1, le=1, description="Pearson correlation coefficient")
    lag_days: int = Field(0, description="Temporal lag (days) at peak correlation")
    n_points: int = Field(..., ge=0, description="Number of paired observations used")
    region: str
    p_value: Optional[float] = Field(None, description="Two-tailed p-value")
    significant: bool = Field(False, description="True if p-value < 0.05")


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class MetaDates(BaseModel):
    """Available raster dates for a given data layer."""

    layer: str = Field(..., description="Layer identifier, e.g. 'aqi', 'hcho', 'fire'")
    available_dates: List[DateType] = Field(..., description="Sorted list of available dates")
    latest: Optional[DateType] = Field(None, description="Most recent available date")
    earliest: Optional[DateType] = Field(None, description="Oldest available date")
    total_count: int = Field(0, description="Total number of available dates")


# ---------------------------------------------------------------------------
# Export Jobs
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    """Request body for creating an async export job."""

    layer: str = Field(..., description="Layer to export: 'aqi', 'hcho', 'fire'")
    start: DateType = Field(..., description="Start date (inclusive)")
    end: DateType = Field(..., description="End date (inclusive)")
    format: ExportFormat = Field(ExportFormat.GEOTIFF, description="Output file format")
    bbox: Optional[List[float]] = Field(
        None,
        description="Optional bounding box [min_lon, min_lat, max_lon, max_lat]",
        min_length=4,
        max_length=4,
    )

    model_config = {"json_schema_extra": {"example": {
        "layer": "aqi",
        "start": "2024-01-01",
        "end": "2024-01-31",
        "format": "geotiff",
    }}}


class ExportJob(BaseModel):
    """Status and result of an async export job."""

    job_id: str = Field(..., description="Unique job identifier (UUID)")
    status: ExportStatus = Field(..., description="Current job status")
    layer: str
    start: DateType
    end: DateType
    format: ExportFormat
    created_at: DatetimeType = Field(..., description="Job creation timestamp (UTC)")
    completed_at: Optional[DatetimeType] = Field(None, description="Completion timestamp (UTC)")
    download_url: Optional[str] = Field(None, description="Signed URL to download the export file")
    error_message: Optional[str] = Field(None, description="Error detail if status is 'failed'")
    progress_pct: int = Field(0, ge=0, le=100, description="Completion percentage (0–100)")
