"""
services/raster.py
------------------
COG (Cloud-Optimised GeoTIFF) querying utilities.

Key responsibilities:
- Resolve the file-system path of a COG given a layer name and date.
- Sample a COG at an arbitrary (lat, lon) point, handling CRS reprojection.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import of rasterio so the rest of the app can start even when
# rasterio is not installed (useful in minimal test environments).
# ---------------------------------------------------------------------------
try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import rowcol
    from pyproj import Transformer

    _RASTERIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RASTERIO_AVAILABLE = False
    logger.warning(
        "rasterio / pyproj not installed. COG querying will return None."
    )


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# Canonical layer → sub-directory mapping
LAYER_DIR_MAP: dict[str, str] = {
    "aqi":  "aqi",
    "hcho": "hcho",
    "fire": "fire",
    "pm25": "aqi",   # alias
    "pm10": "aqi",   # alias
}

# Expected COG filename pattern: {layer}_{YYYY-MM-DD}.tif
COG_FILENAME_TEMPLATE = "{layer}_{date}.tif"


def get_cog_path(layer: str, query_date: date, base_path: Optional[str] = None) -> str:
    """
    Resolve the absolute file-system path of a COG for a given layer and date.

    Args:
        layer:      Data layer identifier (e.g. 'aqi', 'hcho', 'fire').
        query_date: The date whose COG is requested.
        base_path:  Root directory containing layer sub-directories.
                    Defaults to the value from application settings.

    Returns:
        Absolute path to the expected COG file.

    Raises:
        ValueError: If the layer name is not recognised.
        FileNotFoundError: If the COG file does not exist on disk.
    """
    from core.config import settings  # deferred to avoid circular import

    if base_path is None:
        base_path = settings.cog_base_path_abs

    sub_dir = LAYER_DIR_MAP.get(layer.lower())
    if sub_dir is None:
        raise ValueError(
            f"Unknown layer '{layer}'. Known layers: {list(LAYER_DIR_MAP.keys())}"
        )

    filename = COG_FILENAME_TEMPLATE.format(
        layer=layer.lower(),
        date=query_date.isoformat(),
    )
    full_path = os.path.normpath(os.path.join(base_path, sub_dir, filename))

    if not os.path.isfile(full_path):
        raise FileNotFoundError(
            f"COG not found for layer='{layer}', date='{query_date}': {full_path}"
        )

    return full_path


def list_available_dates(layer: str, base_path: Optional[str] = None) -> list[date]:
    """
    Scan the COG directory for a layer and return all available dates sorted
    in ascending order.

    Args:
        layer:     Data layer identifier.
        base_path: COG root directory (defaults to settings value).

    Returns:
        Sorted list of date objects for which a COG file exists.
    """
    from core.config import settings

    if base_path is None:
        base_path = settings.cog_base_path_abs

    sub_dir = LAYER_DIR_MAP.get(layer.lower())
    if sub_dir is None:
        return []

    layer_dir = os.path.join(base_path, sub_dir)
    if not os.path.isdir(layer_dir):
        return []

    dates: list[date] = []
    prefix = f"{layer.lower()}_"
    for fname in os.listdir(layer_dir):
        if fname.startswith(prefix) and fname.endswith(".tif"):
            date_str = fname[len(prefix):-4]  # strip prefix and .tif
            try:
                dates.append(date.fromisoformat(date_str))
            except ValueError:
                continue

    return sorted(dates)


# ---------------------------------------------------------------------------
# Point sampling
# ---------------------------------------------------------------------------


def query_cog_point(
    cog_path: str,
    lat: float,
    lon: float,
    band: int = 1,
    nodata_sentinel: float = -9999.0,
) -> Optional[float]:
    """
    Sample the value of a COG raster at a single geographic point (lat/lon WGS-84).

    Args:
        cog_path:         Absolute path to the COG file.
        lat:              Latitude in WGS-84 decimal degrees.
        lon:              Longitude in WGS-84 decimal degrees.
        band:             Raster band index (1-based). Defaults to 1.
        nodata_sentinel:  Value to treat as nodata when the file has no nodata
                          metadata set. Defaults to -9999.

    Returns:
        The raster value at the requested point as a Python float, or None if
        the point falls outside the raster extent or on a nodata cell.

    Raises:
        RuntimeError: If rasterio is not available.
        FileNotFoundError: If the COG file does not exist.
    """
    if not _RASTERIO_AVAILABLE:
        raise RuntimeError(
            "rasterio is not installed. Cannot query COG files."
        )

    if not os.path.isfile(cog_path):
        raise FileNotFoundError(f"COG file not found: {cog_path}")

    with rasterio.open(cog_path) as src:
        # ------------------------------------------------------------------
        # Reproject the query point to the raster's native CRS if needed
        # ------------------------------------------------------------------
        raster_crs = src.crs
        if raster_crs is None:
            logger.warning(
                "COG '%s' has no CRS defined. Assuming WGS-84.", cog_path
            )
            query_x, query_y = lon, lat
        elif raster_crs.to_epsg() == 4326:
            query_x, query_y = lon, lat
        else:
            transformer = Transformer.from_crs(
                "EPSG:4326", raster_crs, always_xy=True
            )
            query_x, query_y = transformer.transform(lon, lat)

        # ------------------------------------------------------------------
        # Convert projected coordinates to pixel (row, col)
        # ------------------------------------------------------------------
        try:
            row, col = src.index(query_x, query_y)
        except Exception:
            logger.debug(
                "Point (%.6f, %.6f) is outside raster extent of '%s'.",
                lat,
                lon,
                cog_path,
            )
            return None

        # Bounds check
        if not (0 <= row < src.height and 0 <= col < src.width):
            logger.debug(
                "Computed pixel (%d, %d) out of raster bounds (%d x %d).",
                row,
                col,
                src.height,
                src.width,
            )
            return None

        # ------------------------------------------------------------------
        # Read the single pixel
        # ------------------------------------------------------------------
        window = rasterio.windows.Window(col, row, 1, 1)
        data = src.read(band, window=window)

        if data.size == 0:
            return None

        value = float(data[0, 0])

        # Treat nodata
        nodata = src.nodata if src.nodata is not None else nodata_sentinel
        if value == nodata:
            return None

        return value


def query_cog_point_safe(
    cog_path: str,
    lat: float,
    lon: float,
    band: int = 1,
) -> Optional[float]:
    """
    Wrapper around query_cog_point that catches all exceptions and returns
    None instead of raising, for use in non-critical code paths.
    """
    try:
        return query_cog_point(cog_path, lat, lon, band)
    except Exception as exc:
        logger.warning(
            "query_cog_point failed for path='%s', lat=%.6f, lon=%.6f: %s",
            cog_path,
            lat,
            lon,
            exc,
        )
        return None
