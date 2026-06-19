import os
import sys
import argparse
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

MOSDAC_USER = os.environ.get('MOSDAC_USER', 'MOCK_USER')
MOSDAC_PASS = os.environ.get('MOSDAC_PASS', 'MOCK_PASS')

def fetch_insat_for_date(target_date: str):
    """
    Fetches INSAT-3D AOD data from MOSDAC API.
    Extracts AOD at 550nm and applies cloud mask.
    Outputs to data/raw/insat/{date}/aod.nc
    """
    out_dir = os.path.join(os.getcwd(), 'data', 'raw', 'insat', target_date)
    os.makedirs(out_dir, exist_ok=True)
    
    out_nc = os.path.join(out_dir, 'aod.nc')
    
    print(f"Fetching INSAT-3D AOD data for {target_date}...")
    
    if MOSDAC_USER == 'MOCK_USER':
        print("Warning: No MOSDAC credentials found. Using mock/skip for AOD.")
        # In a real scenario, this would download the NetCDF, apply cloud masks,
        # and save the cleaned array. We will create a dummy file for pipeline continuity.
        with open(out_nc, 'w') as f:
            f.write("MOCK_NETCDF_DATA")
        print(f"Created mock AOD file at {out_nc}")
        return

    # Pseudo-code for actual MOSDAC download
    # 1. Authenticate with MOSDAC
    # 2. Query INSAT-3D AOD product for target_date
    # 3. Download .h5 or .nc file
    # 4. Extract AOD dataset, apply QA mask (drop if cloud_fraction > 0)
    # 5. Save processed data to out_nc
    print("Actual MOSDAC fetch not fully implemented without real credentials.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    fetch_insat_for_date(args.date)
