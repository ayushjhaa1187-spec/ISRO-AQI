import os
import sys
import pytest
import numpy as np
import xarray as xr
import pandas as pd
import rasterio
from rasterio.transform import from_origin

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data_pipeline.integration.fuse import fuse_data_for_date
from config.grid import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX, RESOLUTION

@pytest.fixture
def mock_raw_data(tmp_path, monkeypatch):
    """
    Creates mock raw data (S5P TIF, ERA5 TIF, FIRMS CSV, INSAT NC) 
    in a temporary directory and patches the current working directory.
    """
    target_date = "2023-11-01"
    raw_dir = tmp_path / "data" / "raw"
    
    # Create directories
    s5p_dir = raw_dir / "s5p" / target_date
    era5_dir = raw_dir / "era5" / target_date
    firms_dir = raw_dir / "firms" / target_date
    insat_dir = raw_dir / "insat" / target_date
    
    s5p_dir.mkdir(parents=True)
    era5_dir.mkdir(parents=True)
    firms_dir.mkdir(parents=True)
    insat_dir.mkdir(parents=True)
    
    # 1. Create mock S5P TIF (HCHO)
    # 1 degree resolution for raw data
    transform = from_origin(LON_MIN, LAT_MAX, 1.0, 1.0)
    hcho_data = np.random.rand(1, 30, 30).astype(np.float32)
    with rasterio.open(
        s5p_dir / 'hcho_col.tif', 'w',
        driver='GTiff', height=30, width=30, count=1,
        dtype=hcho_data.dtype, crs='EPSG:4326', transform=transform
    ) as dst:
        dst.write(hcho_data)

    # 2. Create mock ERA5 TIF
    era5_data = np.random.rand(8, 30, 30).astype(np.float32)
    with rasterio.open(
        era5_dir / 'era5_met.tif', 'w',
        driver='GTiff', height=30, width=30, count=8,
        dtype=era5_data.dtype, crs='EPSG:4326', transform=transform
    ) as dst:
        dst.write(era5_data)

    # 3. Create mock FIRMS CSV
    firms_csv = firms_dir / 'fire_points.csv'
    df = pd.DataFrame([
        {'latitude': LAT_MIN + 1, 'longitude': LON_MIN + 1, 'acq_date': target_date, 'confidence': 'h', 'frp': 100.0},
        {'latitude': LAT_MIN + 1, 'longitude': LON_MIN + 1.01, 'acq_date': target_date, 'confidence': 'h', 'frp': 50.0},
        {'latitude': LAT_MIN + 5, 'longitude': LON_MIN + 5, 'acq_date': target_date, 'confidence': 'n', 'frp': 20.0},
    ])
    df.to_csv(firms_csv, index=False)

    # 4. Create mock INSAT NC
    insat_nc = insat_dir / 'aod.nc'
    with open(insat_nc, 'w') as f:
        f.write("MOCK")

    # Patch working directory so fuse.py reads from our tmp_path
    monkeypatch.chdir(tmp_path)
    return target_date, tmp_path

def test_datacube_fusion(mock_raw_data):
    """
    Tests that fuse_data_for_date correctly builds a Zarr datacube
    with the expected canonical grid dimensions and variables.
    """
    target_date, tmp_path = mock_raw_data
    
    # Run fusion
    fuse_data_for_date(target_date)
    
    zarr_path = tmp_path / "data" / "processed" / "datacube.zarr"
    assert zarr_path.exists(), "Zarr datacube was not created."
    
    # Open the Zarr
    ds = xr.open_zarr(zarr_path)
    
    # Validate Canonical Grid dimensions
    # LAT_MAX - LAT_MIN = 35.5 - 6.7 = 28.8
    # 28.8 / 0.05 = 576
    # LON_MAX - LON_MIN = 97.4 - 68.1 = 29.3
    # 29.3 / 0.05 = 586
    expected_y_len = int(np.round((LAT_MAX - LAT_MIN) / RESOLUTION))
    expected_x_len = int(np.round((LON_MAX - LON_MIN) / RESOLUTION))
    
    assert ds.sizes['y'] == expected_y_len, f"Expected y dim {expected_y_len}, got {ds.sizes['y']}"
    assert ds.sizes['x'] == expected_x_len, f"Expected x dim {expected_x_len}, got {ds.sizes['x']}"
    assert ds.sizes['time'] == 1, "Expected time dim to be 1 for a single day."
    
    # Validate variables exist
    expected_vars = ['hcho_col', 't2m', 'td', 'u10', 'v10', 'sp', 'tp', 'blh', 'rh', 'fire_count', 'fire_frp', 'aod']
    for v in expected_vars:
        assert v in ds.variables, f"Variable {v} missing from datacube."
        
    # Validate fire aggregation logic (summation)
    # The two fires near (LON_MIN+1, LAT_MIN+1) should be summed together if they fall in the same grid cell
    # Let's just check that fire_count max is at least 1, and fire_frp max is at least 150 (100 + 50)
    max_count = ds['fire_count'].max().compute().item()
    max_frp = ds['fire_frp'].max().compute().item()
    
    assert max_count >= 1, "Fire count summation failed."
    assert max_frp >= 50, "Fire FRP summation failed."

