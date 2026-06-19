import os
import sys
import pytest
import numpy as np
import xarray as xr
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from data_pipeline.analysis.hotspots import compute_hcho_anomalies, cluster_anomalies_to_polygons
from data_pipeline.analysis.colocate import classify_hotspots
from config.grid import LAT, LON

@pytest.fixture
def mock_anomaly_data(tmp_path):
    zarr_path = tmp_path / "mock_hcho_datacube.zarr"
    
    # Create 31 days of data
    dates = pd.date_range("2023-10-01", periods=31, freq="D")
    
    ds = xr.Dataset(
        coords={
            "time": dates,
            "y": LAT,
            "x": LON,
        }
    )
    
    # Baseline HCHO: exactly 0.0001
    hcho_data = np.full((31, len(LAT), len(LON)), 0.0001)
    
    # On the target day (last day), inject an anomaly at specific coordinates
    # Let's say indices y=50, x=50 (cluster 1) and y=100, x=100 (cluster 2)
    target_idx = 30
    hcho_data[target_idx, 50:53, 50:53] = 0.0005  # Highly anomalous cluster 1
    hcho_data[target_idx, 100:102, 100:102] = 0.0004 # Anomalous cluster 2
    
    ds['hcho_col'] = (('time', 'y', 'x'), hcho_data)
    ds.to_zarr(zarr_path, mode='w')
    
    target_date_str = "2023-10-31"
    
    # Mock FIRMS data
    firms_csv = tmp_path / "fire_points.csv"
    # Put a fire right next to cluster 1 (LON[51], LAT[51])
    # Cluster 2 (LON[101], LAT[101]) has NO fire nearby
    fires_df = pd.DataFrame([
        {'latitude': LAT[51], 'longitude': LON[51], 'acq_date': target_date_str, 'confidence': 'h', 'frp': 100.0}
    ])
    fires_df.to_csv(firms_csv, index=False)
    
    return str(zarr_path), target_date_str, str(firms_csv), tmp_path

def test_anomaly_detection_and_clustering(mock_anomaly_data):
    zarr_path, target_date_str, _, _ = mock_anomaly_data
    
    # 1. Test anomaly detection
    anomaly_mask, current, mean, std = compute_hcho_anomalies(zarr_path, target_date_str)
    
    # We should detect anomalies around y=50, x=50 and y=100, x=100
    assert anomaly_mask[51, 51] == True, "Failed to detect injected anomaly (Cluster 1)"
    assert anomaly_mask[101, 101] == True, "Failed to detect injected anomaly (Cluster 2)"
    assert anomaly_mask[10, 10] == False, "False positive detected"
    
    # 2. Test clustering
    gdf = cluster_anomalies_to_polygons(anomaly_mask, current, mean, target_date_str)
    
    # Should have found exactly 2 clusters
    assert len(gdf) == 2, f"Expected 2 clusters, found {len(gdf)}"
    
    # Check that both polygons are valid
    assert all(gdf.is_valid), "Generated polygons are invalid"
    assert all(gdf['significance'] > 0), "Significance score is not positive"

def test_hotspot_colocation(mock_anomaly_data):
    zarr_path, target_date_str, firms_csv, tmp_path = mock_anomaly_data
    
    # First generate the hotspots
    anomaly_mask, current, mean, std = compute_hcho_anomalies(zarr_path, target_date_str)
    gdf = cluster_anomalies_to_polygons(anomaly_mask, current, mean, target_date_str)
    
    hotspots_geojson = tmp_path / "hotspots.geojson"
    gdf.to_file(hotspots_geojson, driver='GeoJSON')
    
    out_geojson = tmp_path / "classified_hotspots.geojson"
    
    # Run colocation
    classify_hotspots(str(hotspots_geojson), str(firms_csv), str(out_geojson), distance_threshold_km=50.0)
    
    assert out_geojson.exists(), "Classified GeoJSON was not created"
    
    classified_gdf = gpd.read_file(out_geojson)
    
    assert len(classified_gdf) == 2, "Lost hotspots during classification"
    assert 'source_region' in classified_gdf.columns, "source_region column missing"
    assert 'nearest_fire_km' in classified_gdf.columns, "nearest_fire_km column missing"
    
    # Cluster 1 is near the fire, Cluster 2 is not
    # Since DBSCAN assigns labels arbitrarily, let's sort by nearest_fire_km
    classified_gdf = classified_gdf.sort_values('nearest_fire_km').reset_index(drop=True)
    
    # Closest cluster should be Biomass Burning (dist < 50km)
    assert classified_gdf.loc[0, 'source_region'] == 'Biomass Burning', "Failed to classify Biomass Burning"
    assert classified_gdf.loc[0, 'nearest_fire_km'] < 50.0, "Distance calculation is wrong"
    
    # Farthest cluster should be Anthropogenic (dist > 50km)
    assert classified_gdf.loc[1, 'source_region'] == 'Anthropogenic', "Failed to classify Anthropogenic"
    assert classified_gdf.loc[1, 'nearest_fire_km'] > 50.0, "Distance calculation is wrong"
