import ee
import geemap
import os

# To avoid interactive prompt hanging during execution by an agent, 
# we rely on the user having authenticated, or we'll print a message.
try:
    ee.Initialize()
except Exception as e:
    print(f"Failed to initialize Earth Engine: {e}")
    print("Please run the following command in your terminal to authenticate:")
    print("earthengine authenticate")
    exit(1)

# Define India bounding box roughly (min_lon, min_lat, max_lon, max_lat)
india_roi = ee.Geometry.Rectangle([68.1, 6.7, 97.4, 35.5])

# Define target date
target_date = '2023-11-01'
next_date = '2023-11-02'

print(f"Fetching Sentinel-5P HCHO data for {target_date}...")

# Sentinel-5P HCHO
collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_HCHO') \
    .select('tropospheric_HCHO_column_number_density') \
    .filterDate(target_date, next_date) \
    .filterBounds(india_roi)

# Mosaic the daily images and clip to India
hcho_image = collection.mosaic().clip(india_roi)

out_dir = os.path.join(os.getcwd(), 'data', 'raw')
os.makedirs(out_dir, exist_ok=True)
out_hcho = os.path.join(out_dir, 'hcho_india_spike.tif')

print("Downloading HCHO image via GEE...")
# 0.1 degree is roughly 11132 meters.
geemap.ee_export_image(hcho_image, filename=out_hcho, scale=11132, region=india_roi, file_per_band=False)
print(f"Saved HCHO to {out_hcho}")

print(f"Fetching ERA5 meteorological data for {target_date}...")
era5 = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
    .filterDate(target_date, next_date) \
    .filterBounds(india_roi) \
    .select(['temperature_2m', 'u_component_of_wind_10m', 'v_component_of_wind_10m']) \
    .first().clip(india_roi)

out_era5 = os.path.join(out_dir, 'era5_india_spike.tif')
print("Downloading ERA5 image via GEE...")
geemap.ee_export_image(era5, filename=out_era5, scale=11132, region=india_roi, file_per_band=False)
print(f"Saved ERA5 to {out_era5}")

print("Phase 0 data download complete!")
