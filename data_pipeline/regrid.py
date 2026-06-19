import os
import sys
import xarray as xr
import rioxarray
import numpy as np
from rasterio.enums import Resampling

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.grid import LON, LAT, CRS, RESOLUTION, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX
from config.resampling import RESAMPLING_RULES

def get_canonical_grid() -> xr.Dataset:
    """Returns an empty xarray Dataset representing the canonical grid."""
    ds = xr.Dataset(
        coords={
            "y": (["y"], LAT),
            "x": (["x"], LON),
        }
    )
    ds.rio.write_crs(CRS, inplace=True)
    # Note: rioxarray typically expects coordinates to be named 'y' and 'x' or 'lat' and 'lon'.
    return ds

def get_rasterio_resampling_method(method_name: str) -> Resampling:
    """Map string method name to rasterio Resampling enum."""
    mapping = {
        'conservative': Resampling.average, # average is conservative when downsampling
        'bilinear': Resampling.bilinear,
        'sum': Resampling.sum
    }
    if method_name not in mapping:
        raise ValueError(f"Unknown resampling method: {method_name}")
    return mapping[method_name]

def regrid_to_canonical(da: xr.DataArray, var_name: str) -> xr.DataArray:
    """
    Regrids an xarray DataArray to the canonical spatial grid using the rule for `var_name`.
    
    Args:
        da: xarray DataArray with spatial dimensions (y, x) or (lat, lon) and a valid CRS.
        var_name: The variable name matching a key in config.resampling.RESAMPLING_RULES.
        
    Returns:
        Regridded xarray DataArray aligned with the canonical grid.
    """
    if var_name not in RESAMPLING_RULES:
        raise ValueError(f"No resampling rule defined for variable: {var_name}")
        
    rule = RESAMPLING_RULES[var_name]
    resampling_enum = get_rasterio_resampling_method(rule['method'])
    
    # Ensure dimensions are standard for rioxarray
    if 'lat' in da.dims and 'lon' in da.dims:
        da = da.rename({'lat': 'y', 'lon': 'x'})
        
    if not da.rio.crs:
        da.rio.write_crs(CRS, inplace=True)
        
    # Get the target grid
    target_grid = get_canonical_grid()
    
    # Reproject using rioxarray
    regridded = da.rio.reproject_match(
        target_grid,
        resampling=resampling_enum,
        nodata=np.nan
    )
    
    return regridded
