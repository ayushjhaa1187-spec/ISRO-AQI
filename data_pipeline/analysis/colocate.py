import os
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import argparse

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def classify_hotspots(hotspots_geojson, firms_csv, out_geojson, distance_threshold_km=50.0):
    """
    Reads the detected HCHO hotspots and FIRMS fire points for the same date.
    Calculates the distance to the nearest fire for each hotspot.
    Classifies as 'Biomass Burning' if within threshold, else 'Anthropogenic'.
    """
    print(f"Running Fire Colocation Test...")
    
    if not os.path.exists(hotspots_geojson):
        print(f"Hotspots file not found: {hotspots_geojson}")
        return
        
    hotspots_gdf = gpd.read_file(hotspots_geojson)
    
    if len(hotspots_gdf) == 0:
        print("No hotspots to classify.")
        # Just copy the empty geojson
        os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
        hotspots_gdf.to_file(out_geojson, driver='GeoJSON')
        return

    # If no fires, everything is anthropogenic
    if not os.path.exists(firms_csv):
        print("No FIRMS fire data found for this date. Classifying all as Anthropogenic.")
        hotspots_gdf['source_region'] = 'Anthropogenic'
        hotspots_gdf['nearest_fire_km'] = None
        os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
        hotspots_gdf.to_file(out_geojson, driver='GeoJSON')
        return
        
    fires_df = pd.read_csv(firms_csv)
    if len(fires_df) == 0:
        print("Empty FIRMS fire data. Classifying all as Anthropogenic.")
        hotspots_gdf['source_region'] = 'Anthropogenic'
        hotspots_gdf['nearest_fire_km'] = None
        os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
        hotspots_gdf.to_file(out_geojson, driver='GeoJSON')
        return

    # Convert fires to GeoDataFrame
    # FIRMS has 'latitude' and 'longitude'
    geometry = [Point(xy) for xy in zip(fires_df.longitude, fires_df.latitude)]
    fires_gdf = gpd.GeoDataFrame(fires_df, geometry=geometry, crs="EPSG:4326")
    
    # Reproject to a metric CRS for accurate distance calculation (e.g., EPSG:3857 or India local EPSG:32643)
    # Using EPSG:3857 (Web Mercator) is a decent approximation for distances, but let's use a local one or just EPSG:3857
    hotspots_metric = hotspots_gdf.to_crs(epsg=3857)
    fires_metric = fires_gdf.to_crs(epsg=3857)
    
    threshold_meters = distance_threshold_km * 1000.0
    
    classifications = []
    distances = []
    
    for idx, hotspot in hotspots_metric.iterrows():
        # distance from polygon to all fire points
        dist_array = fires_metric.distance(hotspot.geometry)
        min_dist = dist_array.min()
        
        distances.append(min_dist / 1000.0) # Store in km
        
        if min_dist <= threshold_meters:
            classifications.append('Biomass Burning')
        else:
            classifications.append('Anthropogenic')
            
    hotspots_gdf['nearest_fire_km'] = distances
    hotspots_gdf['source_region'] = classifications
    
    num_bb = classifications.count('Biomass Burning')
    num_anthro = classifications.count('Anthropogenic')
    
    print(f"Classification Complete: {num_bb} Biomass Burning, {num_anthro} Anthropogenic.")
    
    os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
    hotspots_gdf.to_file(out_geojson, driver='GeoJSON')
    print(f"Saved classified hotspots to {out_geojson}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    hotspots_geojson = os.path.join(os.getcwd(), 'data', 'processed', 'hotspots', f'{args.date}.geojson')
    firms_csv = os.path.join(os.getcwd(), 'data', 'raw', 'firms', args.date, 'fire_points.csv')
    out_geojson = os.path.join(os.getcwd(), 'data', 'processed', 'hotspots', f'{args.date}_classified.geojson')
    
    classify_hotspots(hotspots_geojson, firms_csv, out_geojson)
