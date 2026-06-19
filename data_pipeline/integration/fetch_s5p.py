import ee
import geemap
import os
import sys
import argparse
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.grid import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX
from config.thresholds import S5P_BANDS

from config.thresholds import S5P_BANDS

def init_gee():
    """Initializes Earth Engine using the service account key."""
    service_account_key = os.path.join(os.path.dirname(__file__), '..', 'gee_service_account.json')
    try:
        credentials = ee.ServiceAccountCredentials(
            email='earth-engine-agent@divine-display-475706-u3.iam.gserviceaccount.com',
            key_file=service_account_key
        )
        ee.Initialize(credentials=credentials, project='divine-display-475706-u3')
        print("Earth Engine initialized via Service Account ✓")
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        sys.exit(1)

def fetch_s5p_for_date(target_date: str):
    """
    Fetches S5P data for a given date.
    Applies per-pixel qa_value mask before compositing.
    Exports to data/raw/s5p/{date}/
    """
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    next_date_obj = date_obj + timedelta(days=1)
    next_date = next_date_obj.strftime("%Y-%m-%d")
    
    out_dir = os.path.join(os.getcwd(), 'data', 'raw', 's5p', target_date)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Fetching Sentinel-5P data for {target_date}...")
    
    # Define ROI after ee.Initialize()
    INDIA_ROI = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])
    
    for pollutant, config in S5P_BANDS.items():
        collection_id = config['collection']
        band_name = config['band']
        qa_thresh = config['qa_threshold']
        
        print(f"  -> Processing {pollutant} ({collection_id})...")
        
        collection = ee.ImageCollection(collection_id) \
            .filterDate(target_date, next_date) \
            .filterBounds(INDIA_ROI)
            
        # Check if collection is empty
        size = collection.size().getInfo()
        if size == 0:
            print(f"     No data found for {pollutant} on {target_date}.")
            continue
            
        def process_image(img):
            # 1. Extract qa_value
            qa = img.select('qa_value')
            # 2. Create binary mask based on threshold
            valid_mask = qa.gte(qa_thresh)
            # 3. Apply mask to the actual data band
            data_band = img.select(band_name).updateMask(valid_mask)
            # 4. Also return the mask itself to compute valid fraction
            return data_band.addBands(valid_mask.rename('valid_fraction'))
            
        processed_collection = collection.map(process_image)
        
        # Take the daily mean. Invalid pixels were masked, so they are excluded from the mean.
        # The mean of 'valid_fraction' (which is 1 or 0) gives the fraction of overpasses that were valid.
        daily_mean = processed_collection.mean().clip(INDIA_ROI)
        
        out_tif = os.path.join(out_dir, f"{pollutant.lower()}_col.tif")
        
        print(f"     Downloading {pollutant} to {out_tif}...")
        try:
            # Export at 5000m scale as per plan
            geemap.ee_export_image(
                daily_mean,
                filename=out_tif,
                scale=5000,
                region=INDIA_ROI,
                file_per_band=False
            )
            print(f"     Success: {out_tif}")
        except Exception as e:
            print(f"     Error downloading {pollutant}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    init_gee()
    fetch_s5p_for_date(args.date)
