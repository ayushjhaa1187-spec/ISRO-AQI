import ee
import geemap
import os
import sys
import argparse
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.grid import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX

from config.grid import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX

def init_gee():
    service_account_key = os.path.join(os.path.dirname(__file__), '..', 'gee_service_account.json')
    try:
        credentials = ee.ServiceAccountCredentials(
            email='earth-engine-agent@divine-display-475706-u3.iam.gserviceaccount.com',
            key_file=service_account_key
        )
        ee.Initialize(credentials=credentials, project='divine-display-475706-u3')
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        sys.exit(1)

def fetch_era5_for_date(target_date: str):
    """
    Fetches ERA5 and ERA5-Land data for a given date.
    Exports to data/raw/era5/{date}/era5_met.tif
    """
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    next_date_obj = date_obj + timedelta(days=1)
    next_date = next_date_obj.strftime("%Y-%m-%d")
    
    out_dir = os.path.join(os.getcwd(), 'data', 'raw', 'era5', target_date)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Fetching ERA5 meteorological data for {target_date}...")
    
    # Define ROI after ee.Initialize()
    INDIA_ROI = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])
    
    # ERA5-Land Daily
    era5_land = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(target_date, next_date) \
        .filterBounds(INDIA_ROI)
        
    if era5_land.size().getInfo() == 0:
        print(f"No ERA5-Land data found for {target_date}.")
        return
        
    img_land = era5_land.first().select([
        'temperature_2m', 
        'dewpoint_temperature_2m',
        'u_component_of_wind_10m', 
        'v_component_of_wind_10m',
        'surface_pressure',
        'total_precipitation_sum'
    ])
    
    # ERA5 Daily for Boundary Layer Height (BLH)
    # GEE has ECMWF/ERA5/DAILY but sometimes it's slightly delayed.
    try:
        era5_base = ee.ImageCollection("ECMWF/ERA5/DAILY") \
            .filterDate(target_date, next_date) \
            .filterBounds(INDIA_ROI)
            
        if era5_base.size().getInfo() > 0:
            blh = era5_base.first().select('boundary_layer_height')
            # Resample BLH to match ERA5-Land scale and add as band
            img_combined = img_land.addBands(blh)
        else:
            print("No ERA5 BLH found. Exporting without BLH.")
            img_combined = img_land
    except Exception as e:
        print(f"Failed to fetch BLH: {e}. Exporting without BLH.")
        img_combined = img_land

    # Compute Relative Humidity (RH) from t2m and dewpoint
    # RH = 100 * (exp((17.625 * td)/(243.04 + td)) / exp((17.625 * t)/(243.04 + t)))
    # Note: t and td in Celsius. ERA5 gives Kelvin.
    t2m = img_combined.select('temperature_2m').subtract(273.15)
    td = img_combined.select('dewpoint_temperature_2m').subtract(273.15)
    
    # August-Roche-Magnus approximation
    num = td.multiply(17.625).divide(td.add(243.04)).exp()
    den = t2m.multiply(17.625).divide(t2m.add(243.04)).exp()
    rh = num.divide(den).multiply(100).rename('rh')
    
    img_final = img_combined.addBands(rh).clip(INDIA_ROI)
    
    out_tif = os.path.join(out_dir, "era5_met.tif")
    print(f"Downloading ERA5 combined to {out_tif}...")
    
    # Export at 11132m (~0.1 deg) scale
    geemap.ee_export_image(
        img_final,
        filename=out_tif,
        scale=11132,
        region=INDIA_ROI,
        file_per_band=False
    )
    print(f"Success: {out_tif}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    init_gee()
    fetch_era5_for_date(args.date)
