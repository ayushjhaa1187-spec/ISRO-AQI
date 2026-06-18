import os
import xarray as xr
import pandas as pd
import numpy as np

zarr_in = os.path.join(os.getcwd(), 'data', 'ard', 'datacube_spike.zarr')

if not os.path.exists(zarr_in):
    print(f"Datacube not found at {zarr_in}. Run Phase 0 first.")
    exit(1)

print("Loading Zarr Datacube...")
ds = xr.open_zarr(zarr_in)

# For Phase 1, we need CPCB station locations. 
# Since we don't have the live CPCB database yet, we'll mock a few major stations.
stations = pd.DataFrame([
    {'station_id': 'DEL01', 'city': 'Delhi', 'lat': 28.6139, 'lon': 77.2090, 'pm25_obs': 150.5},
    {'station_id': 'MUM01', 'city': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777, 'pm25_obs': 65.2},
    {'station_id': 'BLR01', 'city': 'Bangalore', 'lat': 12.9716, 'lon': 77.5946, 'pm25_obs': 35.8},
    {'station_id': 'KOL01', 'city': 'Kolkata', 'lat': 22.5726, 'lon': 88.3639, 'pm25_obs': 85.0},
    {'station_id': 'CHE01', 'city': 'Chennai', 'lat': 13.0827, 'lon': 80.2707, 'pm25_obs': 45.3}
])

print("Matching satellite/meteorology data to station locations...")
matched_data = []

target_date = '2023-11-01'

for idx, row in stations.iterrows():
    # Nearest neighbor interpolation to get the grid cell value for the station
    try:
        cell_data = ds.sel(x=row['lon'], y=row['lat'], method='nearest').sel(time=target_date)
        
        # Extract features
        hcho = float(cell_data['tropospheric_HCHO'].values)
        temp = float(cell_data['temperature_2m'].values)
        u_wind = float(cell_data['u_component_of_wind_10m'].values)
        v_wind = float(cell_data['v_component_of_wind_10m'].values)
        
        matched_data.append({
            'station_id': row['station_id'],
            'city': row['city'],
            'lat': row['lat'],
            'lon': row['lon'],
            'pm25_obs': row['pm25_obs'], # Ground truth target
            's5p_hcho': hcho,
            'era5_temp_2m': temp,
            'era5_u_wind': u_wind,
            'era5_v_wind': v_wind
        })
    except Exception as e:
        print(f"Could not match data for {row['city']}: {e}")

df_matched = pd.DataFrame(matched_data)

out_dir = os.path.join(os.getcwd(), 'data', 'processed')
os.makedirs(out_dir, exist_ok=True)
out_csv = os.path.join(out_dir, 'station_matched_features.csv')

df_matched.to_csv(out_csv, index=False)
print(f"Extracted features saved to {out_csv}")
print("\nSample of matched data:")
print(df_matched.head())
