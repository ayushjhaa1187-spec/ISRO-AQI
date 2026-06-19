import os
import sys
import argparse
import pandas as pd
import geopandas as gpd
from datetime import datetime
import requests
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

FIRMS_API_KEY = os.environ.get('FIRMS_API_KEY', 'MOCK_KEY')

def fetch_firms_for_date(target_date: str):
    """
    Fetches FIRMS active fire data (VIIRS SNPP) for India.
    Filters by confidence and outputs GeoJSON.
    """
    out_dir = os.path.join(os.getcwd(), 'data', 'raw', 'firms', target_date)
    os.makedirs(out_dir, exist_ok=True)
    
    out_csv = os.path.join(out_dir, 'fire_points.csv')
    out_geojson = os.path.join(out_dir, 'fire_points.geojson')
    
    if FIRMS_API_KEY == 'MOCK_KEY':
        print("Warning: No FIRMS_API_KEY found in environment. Using mock data.")
        # Create a mock dataframe for the tests
        df = pd.DataFrame([
            # Punjab burning region
            {'latitude': 30.5, 'longitude': 75.0, 'acq_date': target_date, 'confidence': 'n', 'frp': 15.2},
            {'latitude': 30.6, 'longitude': 75.2, 'acq_date': target_date, 'confidence': 'h', 'frp': 25.4},
            {'latitude': 30.55, 'longitude': 75.1, 'acq_date': target_date, 'confidence': 'h', 'frp': 45.1},
        ])
    else:
        # Fetch from FIRMS API
        url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{FIRMS_API_KEY}/VIIRS_SNPP_NRT/IND/1/{target_date}"
        print(f"Fetching FIRMS data from {url} ...")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching FIRMS data: {response.text}")
            sys.exit(1)
            
        with open(out_csv, 'w') as f:
            f.write(response.text)
            
        df = pd.read_csv(out_csv)

    if len(df) == 0:
        print(f"No fire data found for {target_date}.")
        return

    # Filter confidence (VIIRS uses 'l', 'n', 'h' for low, nominal, high)
    # Drop low confidence
    if 'confidence' in df.columns:
        df = df[df['confidence'].isin(['n', 'h', 'nominal', 'high'])]
        
    print(f"Retained {len(df)} nominal/high confidence fire points.")

    # Convert to GeoJSON
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )
    
    gdf.to_file(out_geojson, driver='GeoJSON')
    print(f"Saved FIRMS GeoJSON to {out_geojson}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    fetch_firms_for_date(args.date)
