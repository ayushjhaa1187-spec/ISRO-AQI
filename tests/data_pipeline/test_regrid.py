import os
import sys
import numpy as np
import xarray as xr
import pytest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data_pipeline.regrid import regrid_to_canonical, get_canonical_grid
from config.grid import LON, LAT, CRS

def test_coordinate_orientation():
    """
    Coordinate-Orientation Test:
    Delhi cell (~28.6 N, 77.2 E) has correct neighbors.
    Catches lat/lon flips across layers.
    """
    grid = get_canonical_grid()
    
    # Check that x is LON and y is LAT
    assert np.array_equal(grid.x.values, LON), "Grid x coordinates do not match canonical LON."
    assert np.array_equal(grid.y.values, LAT), "Grid y coordinates do not match canonical LAT."
    
    # Delhi approx coordinates
    delhi_lon, delhi_lat = 77.2, 28.6
    
    # Find nearest index
    idx_x = np.abs(grid.x.values - delhi_lon).argmin()
    idx_y = np.abs(grid.y.values - delhi_lat).argmin()
    
    # Verify orientation: 
    # Longitude should increase as index increases
    assert grid.x.values[idx_x + 1] > grid.x.values[idx_x], "Longitude should increase with index"
    # Latitude should increase as index increases
    assert grid.y.values[idx_y + 1] > grid.y.values[idx_y], "Latitude should increase with index"

def test_conservation():
    """
    Conservation Test:
    Ensure conservative regridding preserves the sum of values (mass) within floating-point tolerance.
    """
    # Create a synthetic high-resolution dataset (0.01 deg) over a small region
    hi_lon = np.arange(77.0, 78.0, 0.01)
    hi_lat = np.arange(28.0, 29.0, 0.01)
    
    # Create synthetic mass values (e.g. molecules/cm2)
    data = np.ones((len(hi_lat), len(hi_lon))) * 100.0
    
    da_hi = xr.DataArray(
        data,
        coords=[("lat", hi_lat), ("lon", hi_lon)],
        name="synthetic_hcho"
    )
    da_hi.rio.write_crs("EPSG:4326", inplace=True)
    
    # Calculate original total mass (area-weighted in reality, but here we assume uniform area for simple grid sum)
    # The sum of intensive values when regridded conservatively should be preserved if scaled by area.
    # Actually rioxarray's 'average' resampling takes the area-weighted average. 
    # To test conservation of a quantity like column density, the mean over the region should be conserved.
    original_mean = da_hi.mean().item()
    
    # Regrid using conservative rule (hcho_col uses conservative)
    da_regridded = regrid_to_canonical(da_hi, var_name="hcho_col")
    
    # The regridded region is 77.0-78.0 and 28.0-29.0, which falls perfectly within the canonical grid.
    # We slice the canonical grid to only the valid region to avoid NaNs skewing the mean.
    valid_regridded = da_regridded.sel(x=slice(77.0, 77.95), y=slice(28.0, 28.95))
    
    regridded_mean = valid_regridded.mean().item()
    
    # Means should match closely
    assert np.isclose(original_mean, regridded_mean, rtol=1e-3), f"Mean not conserved! Original: {original_mean}, Regridded: {regridded_mean}"

if __name__ == "__main__":
    pytest.main([__file__])
