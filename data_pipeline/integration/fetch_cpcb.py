import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import requests

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

CPCB_API_KEY = os.environ.get('CPCB_API_KEY', 'MOCK_KEY')

def fetch_cpcb_for_date(target_date: str):
    """
    Fetches daily average PM2.5, PM10, and AQI from CPCB stations.
    Stores as a tabular CSV: station_id, lat, lon, date, pm25, pm10, aqi.
    """
    out_dir = os.path.join(os.getcwd(), 'data', 'raw', 'cpcb', target_date)
    os.makedirs(out_dir, exist_ok=True)
    
    out_csv = os.path.join(out_dir, 'ground_truth.csv')
    
    print(f"Fetching CPCB ground truth data for {target_date}...")
    
    if CPCB_API_KEY == 'MOCK_KEY':
        print("Warning: No CPCB_API_KEY found. Using mock data.")
        # Create a mock dataframe representing CPCB stations
        df = pd.DataFrame([
            {'station_id': 'DL001', 'lat': 28.6139, 'lon': 77.2090, 'date': target_date, 'pm25': 150.2, 'pm10': 210.5, 'aqi': 310},
            {'station_id': 'MH012', 'lat': 19.0760, 'lon': 72.8777, 'date': target_date, 'pm25': 65.4, 'pm10': 95.1, 'aqi': 120},
            {'station_id': 'PB005', 'lat': 30.9010, 'lon': 75.8573, 'date': target_date, 'pm25': 240.1, 'pm10': 310.2, 'aqi': 420},
        ])
    else:
        # Pseudo-code for actual Data.gov.in / CPCB API fetch
        # URL depends on the exact dataset ID on data.gov.in
        url = f"https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?api-key={CPCB_API_KEY}&format=json&limit=2000"
        print(f"Fetching from {url} ...")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching CPCB data: {response.text}")
            sys.exit(1)
            
        data = response.json()
        records = data.get('records', [])
        
        # Parse records into required format.
        # This is highly dependent on the exact API response structure.
        parsed = []
        for r in records:
            # Assumes mapping of fields exists
            parsed.append({
                'station_id': r.get('station', 'UNKNOWN'),
                'lat': float(r.get('latitude', 0)),
                'lon': float(r.get('longitude', 0)),
                'date': target_date,
                'pm25': float(r.get('pm2_5', 0) or 0),
                'pm10': float(r.get('pm10', 0) or 0),
                'aqi': float(r.get('aqi', 0) or 0)
            })
        df = pd.DataFrame(parsed)

    # Save to CSV without rasterizing
    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} CPCB records to {out_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    fetch_cpcb_for_date(args.date)
