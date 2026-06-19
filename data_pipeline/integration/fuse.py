import os
import sys
import argparse
import xarray as xr
import pandas as pd
from datetime import datetime
import numpy as np
import rioxarray

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.grid import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX, RESOLUTION, LON, LAT
from data_pipeline.regrid import get_canonical_grid, regrid_to_canonical

def regrid_points_to_grid(df, target_ds, value_col, agg_func='sum'):
    # Simple 2D histogram regridding for points
    lon_bins = np.append(LON - RESOLUTION/2, [LON[-1] + RESOLUTION/2])
    lat_bins = np.append(LAT - RESOLUTION/2, [LAT[-1] + RESOLUTION/2])
    
    ret, _, _ = np.histogram2d(
        df['latitude'].values, df['longitude'].values,
        bins=[lat_bins, lon_bins],
        weights=df[value_col].values if value_col else None
    )
    # The result shape is (len(lat_bins)-1, len(lon_bins)-1)
    # xarray coordinates need to match the center
    da = xr.DataArray(ret, coords=[('y', LAT), ('x', LON)])
    return da

def fuse_data_for_date(target_date: str):
    raw_dir = os.path.join(os.getcwd(), 'data', 'raw')
    processed_dir = os.path.join(os.getcwd(), 'data', 'processed')
    os.makedirs(processed_dir, exist_ok=True)
    
    zarr_path = os.path.join(processed_dir, 'datacube.zarr')
    print(f"Fusing data for {target_date}...")
    
    target_ds = get_canonical_grid()
    daily_ds = target_ds.copy()
    
    time_val = pd.to_datetime(target_date)
    daily_ds = daily_ds.expand_dims(time=[time_val])
    
    # 2. Process S5P
    s5p_dir = os.path.join(raw_dir, 's5p', target_date)
    if os.path.exists(s5p_dir):
        for f in os.listdir(s5p_dir):
            if f.endswith('.tif'):
                var_name = f.replace('.tif', '')
                tif_path = os.path.join(s5p_dir, f)
                try:
                    da = rioxarray.open_rasterio(tif_path)
                    # Use rioxarray directly if there's no rule in RESAMPLING_RULES, 
                    # but S5P columns usually use 'conservative'. We pass 'hcho_col' etc.
                    # Actually config/resampling.py might only define 'hcho', 'no2', etc.
                    regridded = regrid_to_canonical(da.isel(band=0), var_name)
                    daily_ds[var_name] = (('time', 'y', 'x'), [regridded.values])
                    print(f"  Merged S5P {var_name}")
                except Exception as e:
                    print(f"  Error regridding {f}: {e}")
                    
    # 3. Process ERA5
    era5_tif = os.path.join(raw_dir, 'era5', target_date, 'era5_met.tif')
    if os.path.exists(era5_tif):
        try:
            da = rioxarray.open_rasterio(era5_tif)
            band_names = ['t2m', 'td', 'u10', 'v10', 'sp', 'tp', 'blh', 'rh']
            for i in range(min(len(band_names), da.sizes.get('band', 0))):
                b_name = band_names[i]
                try:
                    regridded = regrid_to_canonical(da.isel(band=i), b_name)
                    daily_ds[b_name] = (('time', 'y', 'x'), [regridded.values])
                except Exception:
                    # fallback if no rule defined
                    regridded = da.isel(band=i).rio.reproject_match(target_ds)
                    daily_ds[b_name] = (('time', 'y', 'x'), [regridded.values])
            print(f"  Merged ERA5 meteorology")
        except Exception as e:
            print(f"  Error regridding ERA5: {e}")

    # 4. Process FIRMS
    firms_csv = os.path.join(raw_dir, 'firms', target_date, 'fire_points.csv')
    if os.path.exists(firms_csv):
        try:
            df = pd.read_csv(firms_csv)
            if len(df) > 0:
                df['count'] = 1
                fire_count = regrid_points_to_grid(df, target_ds, value_col='count', agg_func='sum')
                daily_ds['fire_count'] = (('time', 'y', 'x'), [fire_count.values])
                if 'frp' in df.columns:
                    fire_frp = regrid_points_to_grid(df, target_ds, value_col='frp', agg_func='sum')
                    daily_ds['fire_frp'] = (('time', 'y', 'x'), [fire_frp.values])
                print(f"  Merged FIRMS fire data")
        except Exception as e:
            print(f"  Error regridding FIRMS: {e}")

    # 5. Process INSAT
    insat_nc = os.path.join(raw_dir, 'insat', target_date, 'aod.nc')
    if os.path.exists(insat_nc):
        daily_ds['aod'] = (('time', 'y', 'x'), [np.full((target_ds.sizes['y'], target_ds.sizes['x']), np.nan)])

    # Ensure chunking matches zarr logic
    daily_ds = daily_ds.chunk({'time': 1, 'y': -1, 'x': -1})

    if os.path.exists(zarr_path):
        daily_ds.to_zarr(zarr_path, append_dim='time')
    else:
        daily_ds.to_zarr(zarr_path, mode='w')
    print(f"Fusion complete for {target_date}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    fuse_data_for_date(args.date)
