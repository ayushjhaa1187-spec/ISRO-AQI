import numpy as np
import xarray as xr
import os

# Definition from Phase 0: Canonical spatial grid
# CRS: EPSG:4326 (regular lat/lon)
# Bounding box: lon 67E-98E, lat 6N-38N
# Resolution: 0.05 degrees

print("Defining canonical grid...")
LON = np.arange(67.0, 98.0, 0.05)
LAT = np.arange(6.0, 38.0, 0.05)

GRID = xr.Dataset(coords={"lat": LAT, "lon": LON})

out_dir = os.path.join(os.getcwd(), 'config')
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, 'canonical_grid.nc')

GRID.to_netcdf(out_file)
print(f"Successfully saved canonical grid to {out_file}")
print("This template grid will be used for all subsequent data regridding steps.")
