import os
import xarray as xr
import rioxarray
import pandas as pd

out_dir = os.path.join(os.getcwd(), 'data', 'raw')
out_hcho = os.path.join(out_dir, 'hcho_india_spike.tif')
out_era5 = os.path.join(out_dir, 'era5_india_spike.tif')

if not os.path.exists(out_hcho) or not os.path.exists(out_era5):
    print("Error: TIFF files not found. Did you run phase0_gee_spike.py first?")
    exit(1)

print("Loading HCHO TIFF...")
hcho_da = rioxarray.open_rasterio(out_hcho)
# S5P exported image usually has 1 band if we select 1 variable
hcho_da = hcho_da.isel(band=0) # select the single band
hcho_da.name = 'tropospheric_HCHO'

print("Loading ERA5 TIFF...")
era5_da = rioxarray.open_rasterio(out_era5)
# era5 has 3 bands because we selected 3 variables: temperature_2m, u_wind, v_wind
era5_ds = xr.Dataset({
    'temperature_2m': era5_da.isel(band=0),
    'u_component_of_wind_10m': era5_da.isel(band=1),
    'v_component_of_wind_10m': era5_da.isel(band=2)
})

print("Merging datasets...")
# Combine them. Because they were exported with the same scale and region from GEE, 
# their spatial dimensions (x, y) should match perfectly.
ds = xr.merge([hcho_da.to_dataset(), era5_ds])

# Add the correct time dimension
target_date = '2023-11-01'
ds = ds.expand_dims(time=pd.to_datetime([target_date]))

# Clean up coordinates
if 'band' in ds.coords:
    ds = ds.drop_vars('band')

zarr_out = os.path.join(os.getcwd(), 'data', 'ard', 'datacube_spike.zarr')
os.makedirs(os.path.dirname(zarr_out), exist_ok=True)

print(f"Saving combined datacube to Zarr at {zarr_out}...")
ds.to_zarr(zarr_out, mode='w')
print("Phase 0 stacking complete! We have a multi-variable Zarr datacube ready for ML ingestion.")
