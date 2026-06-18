"""
tests/conftest.py
─────────────────
Shared fixtures for the entire test suite.
Provides synthetic canonical grids, mock datacubes,
sample station data, and the FastAPI test client.
"""

import pytest
import numpy as np
import pandas as pd
import xarray as xr


# ── Canonical Grid Fixture ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def canonical_grid():
    """Returns a small canonical grid over India for fast tests."""
    lon = np.arange(67.0, 98.0, 0.1)   # coarser for speed
    lat = np.arange(6.0,  38.0, 0.1)
    return xr.Dataset(coords={"lat": lat, "lon": lon})


# ── Synthetic Datacube Fixture ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def synthetic_datacube(canonical_grid):
    """
    A 10-day synthetic multi-variable datacube on the canonical grid.
    Values are physically plausible random draws.
    """
    rng = np.random.default_rng(42)
    times = pd.date_range("2023-11-01", periods=10, freq="D")
    lat = canonical_grid.lat.values
    lon = canonical_grid.lon.values

    shape = (len(times), len(lat), len(lon))

    ds = xr.Dataset(
        {
            "tropospheric_HCHO": (["time", "lat", "lon"],
                                   rng.uniform(1e-5, 2e-4, shape).astype("float32")),
            "tropospheric_NO2": (["time", "lat", "lon"],
                                  rng.uniform(1e-6, 1e-4, shape).astype("float32")),
            "temperature_2m": (["time", "lat", "lon"],
                                rng.uniform(280.0, 315.0, shape).astype("float32")),
            "u_component_of_wind_10m": (["time", "lat", "lon"],
                                         rng.uniform(-15.0, 15.0, shape).astype("float32")),
            "v_component_of_wind_10m": (["time", "lat", "lon"],
                                         rng.uniform(-15.0, 15.0, shape).astype("float32")),
            "fire_count": (["time", "lat", "lon"],
                            rng.integers(0, 20, shape).astype("int16")),
            "fire_frp": (["time", "lat", "lon"],
                          rng.uniform(0.0, 500.0, shape).astype("float32")),
        },
        coords={
            "time": times,
            "lat": lat,
            "lon": lon,
        },
    )
    ds["time"].attrs["timezone"] = "UTC"
    return ds


# ── Planted Hotspot Datacube ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def datacube_with_hotspot(synthetic_datacube):
    """
    Inject a known HCHO hotspot over Punjab (75–77°E, 29–32°N)
    on days 3–5 (Nov 4–6), to validate hotspot detection methods.
    """
    ds = synthetic_datacube.copy(deep=True)
    hcho = ds["tropospheric_HCHO"].values.copy()
    fire = ds["fire_count"].values.copy()

    lon_vals = ds.lon.values
    lat_vals = ds.lat.values

    # Get index arrays
    lon_idx = np.where((lon_vals >= 75.0) & (lon_vals <= 77.0))[0]
    lat_idx = np.where((lat_vals >= 29.0) & (lat_vals <= 32.0))[0]

    # Use proper 3D indexing with np.ix_ per time step
    for t in [3, 4, 5]:
        hcho[np.ix_([t], lat_idx, lon_idx)] *= 5.0
        fire_slice = fire[np.ix_([t], lat_idx, lon_idx)]
        fire[np.ix_([t], lat_idx, lon_idx)] = np.clip(fire_slice + 15, 0, 50).astype("int16")

    ds["tropospheric_HCHO"].values[:] = hcho
    ds["fire_count"].values[:] = fire
    return ds


# ── CPCB Station Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_stations():
    """Representative major CPCB monitoring stations."""
    return pd.DataFrame([
        {"station_id": "DEL01", "city": "Delhi",     "lat": 28.6139, "lon": 77.2090},
        {"station_id": "MUM01", "city": "Mumbai",    "lat": 19.0760, "lon": 72.8777},
        {"station_id": "BLR01", "city": "Bangalore", "lat": 12.9716, "lon": 77.5946},
        {"station_id": "KOL01", "city": "Kolkata",   "lat": 22.5726, "lon": 88.3639},
        {"station_id": "CHE01", "city": "Chennai",   "lat": 13.0827, "lon": 80.2707},
        {"station_id": "LDH01", "city": "Ludhiana",  "lat": 30.9009, "lon": 75.8573},
        {"station_id": "AMR01", "city": "Amritsar",  "lat": 31.6340, "lon": 74.8723},
    ])


# ── FastAPI Test Client Fixture ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def api_client():
    """Returns an httpx test client for the FastAPI backend."""
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)
    except ImportError:
        pytest.skip("Backend not yet implemented — skipping API tests")
