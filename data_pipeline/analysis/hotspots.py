import os
import sys
import numpy as np
import pandas as pd
import xarray as xr
import json
from sklearn.cluster import DBSCAN
import geopandas as gpd
from shapely.geometry import Polygon, MultiPoint
import argparse

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.grid import LON, LAT, RESOLUTION

def compute_hcho_anomalies(zarr_path, target_date_str, lookback_days=30, sigma_threshold=2.0):
    """
    Computes HCHO anomalies for a specific date using a trailing mean and std dev.
    """
    ds = xr.open_zarr(zarr_path)
    
    target_date = pd.to_datetime(target_date_str)
    start_date = target_date - pd.Timedelta(days=lookback_days)
    
    # Extract the historical window
    try:
        historical_ds = ds.sel(time=slice(start_date, target_date - pd.Timedelta(days=1)))
        current_ds = ds.sel(time=target_date_str)
    except KeyError:
        raise ValueError(f"Data for date {target_date_str} or its 30-day window is not fully available in the datacube.")
        
    if len(historical_ds.time) == 0:
        raise ValueError("No historical data found in the 30-day trailing window.")
        
    # Calculate pixel-wise mean and std for HCHO
    hcho_mean = historical_ds['hcho_col'].mean(dim='time')
    hcho_std = historical_ds['hcho_col'].std(dim='time')
    current_hcho = current_ds['hcho_col']
    
    # Identify anomalies: current > mean + threshold * std
    anomaly_mask = current_hcho > (hcho_mean + sigma_threshold * hcho_std)
    
    # For zero-variance pixels (std=0), avoid false positives if current_hcho is also low
    # We enforce a minimum HCHO absolute value to be considered a hotspot (e.g., > 0.0001 mol/m2)
    # This value might need tuning based on actual S5P TROPOMI units
    min_absolute_threshold = 0.00005 
    anomaly_mask = anomaly_mask & (current_hcho > min_absolute_threshold)
    
    return anomaly_mask.values, current_hcho.values, hcho_mean.values, hcho_std.values

def cluster_anomalies_to_polygons(anomaly_mask, current_hcho, hcho_mean, target_date_str):
    """
    Takes a 2D boolean mask of anomalies, clusters adjacent pixels using DBSCAN,
    and returns a GeoDataFrame of polygons representing the hotspots.
    """
    # Get y, x indices of anomalous pixels
    y_idx, x_idx = np.where(anomaly_mask)
    
    if len(y_idx) == 0:
        return gpd.GeoDataFrame()
        
    # Convert to physical coordinates
    lon_vals = LON[x_idx]
    lat_vals = LAT[y_idx]
    points = np.column_stack((lon_vals, lat_vals))
    
    # Cluster using DBSCAN
    # eps is in degrees. Diagonal of a 0.05 cell is ~0.07. 
    # Let's use eps=0.08 to connect adjacent and diagonal cells.
    # min_samples=3 to filter out single isolated noisy pixels
    db = DBSCAN(eps=0.08, min_samples=3).fit(points)
    labels = db.labels_
    
    features = []
    unique_labels = set(labels)
    
    for label in unique_labels:
        if label == -1:
            continue # Noise
            
        cluster_mask = (labels == label)
        cluster_points = points[cluster_mask]
        cluster_y = y_idx[cluster_mask]
        cluster_x = x_idx[cluster_mask]
        
        # Create a polygon (convex hull of the grid cell centers + buffer to cover the cell)
        # For a more exact grid representation, we would union square polygons.
        # For simplicity and performance, a convex hull of buffered points is standard for hotspots.
        mp = MultiPoint(cluster_points)
        # Buffer by half the resolution so the polygon fully covers the border cells
        poly = mp.convex_hull.buffer(RESOLUTION / 2.0, cap_style=3) 
        
        # Calculate significance score (mean z-score of the cluster)
        # Actually, let's just calculate the mean HCHO of the cluster
        mean_hcho_cluster = float(np.mean(current_hcho[cluster_y, cluster_x]))
        baseline_hcho_cluster = float(np.mean(hcho_mean[cluster_y, cluster_x]))
        
        # Significance = percentage over baseline
        if baseline_hcho_cluster > 0:
            significance = ((mean_hcho_cluster - baseline_hcho_cluster) / baseline_hcho_cluster) * 100.0
        else:
            significance = 0.0
            
        features.append({
            'geometry': poly,
            'date': target_date_str,
            'mean_hcho': mean_hcho_cluster,
            'baseline_hcho': baseline_hcho_cluster,
            'significance': significance,
            'pixel_count': int(np.sum(cluster_mask))
        })
        
    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    return gdf

def detect_hotspots(zarr_path, target_date_str, out_geojson):
    print(f"Detecting HCHO Hotspots for {target_date_str}...")
    try:
        anomaly_mask, current, mean, std = compute_hcho_anomalies(zarr_path, target_date_str)
        gdf = cluster_anomalies_to_polygons(anomaly_mask, current, mean, target_date_str)
        
        out_dir = os.path.dirname(out_geojson)
        os.makedirs(out_dir, exist_ok=True)
        
        if len(gdf) > 0:
            gdf.to_file(out_geojson, driver='GeoJSON')
            print(f"Found {len(gdf)} hotspot clusters. Saved to {out_geojson}")
        else:
            # Save empty geojson
            empty_fc = {"type": "FeatureCollection", "features": []}
            with open(out_geojson, 'w') as f:
                json.dump(empty_fc, f)
            print("No hotspots detected. Saved empty GeoJSON.")
            
    except Exception as e:
        print(f"Error detecting hotspots: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    zarr_path = os.path.join(os.getcwd(), 'data', 'processed', 'datacube.zarr')
    out_path = os.path.join(os.getcwd(), 'data', 'processed', 'hotspots', f'{args.date}.geojson')
    
    detect_hotspots(zarr_path, args.date, out_path)
