"""
services/db_init.py
------------------
Database schema initialization script for the ISRO AQI & HCHO platform.
Creates the tables for spatial grid cells, stations, daily features, model predictions,
daily maps, validation metrics, and the model registry.
"""

import asyncio
import logging
import sys
from typing import List

try:
    import asyncpg
except ImportError:
    print("Warning: asyncpg is not installed. PostgreSQL schema creation requires asyncpg.")
    asyncpg = None

from core.config import settings

logger = logging.getLogger(__name__)

# DDL statements for creating the PostgreSQL and PostGIS tables
DDL_STATEMENTS: List[str] = [
    # Enable PostGIS extension
    "CREATE EXTENSION IF NOT EXISTS postgis;",

    # 1. Grid Cells table
    """
    CREATE TABLE IF NOT EXISTS grid_cells (
        grid_id VARCHAR(20) PRIMARY KEY,
        geom GEOMETRY(Polygon, 4326),
        centroid GEOMETRY(Point, 4326),
        elevation DOUBLE PRECISION,
        land_use VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_grid_cells_geom ON grid_cells USING GIST(geom);",

    # 2. CPCB Stations table
    """
    CREATE TABLE IF NOT EXISTS stations (
        station_id VARCHAR(20) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        city VARCHAR(50),
        state VARCHAR(50),
        geom GEOMETRY(Point, 4326),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stations_geom ON stations USING GIST(geom);",

    # 3. Station Observations table
    """
    CREATE TABLE IF NOT EXISTS station_obs (
        obs_id SERIAL PRIMARY KEY,
        station_id VARCHAR(20) REFERENCES stations(station_id) ON DELETE CASCADE,
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        pm25 DOUBLE PRECISION,
        pm10 DOUBLE PRECISION,
        no2 DOUBLE PRECISION,
        so2 DOUBLE PRECISION,
        o3 DOUBLE PRECISION,
        co DOUBLE PRECISION,
        aqi DOUBLE PRECISION,
        dominant_pollutant VARCHAR(10),
        UNIQUE(station_id, timestamp)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_station_obs_timestamp ON station_obs(timestamp);",

    # 4. Daily Features table (51-feature matrix per grid cell)
    """
    CREATE TABLE IF NOT EXISTS daily_features (
        feature_id SERIAL PRIMARY KEY,
        grid_id VARCHAR(20) REFERENCES grid_cells(grid_id) ON DELETE CASCADE,
        date DATE NOT NULL,
        hcho_vcd DOUBLE PRECISION,
        no2_vcd DOUBLE PRECISION,
        so2_vcd DOUBLE PRECISION,
        o3_column DOUBLE PRECISION,
        co_column DOUBLE PRECISION,
        aod DOUBLE PRECISION,
        temp_2m DOUBLE PRECISION,
        relative_humidity DOUBLE PRECISION,
        wind_u DOUBLE PRECISION,
        wind_v DOUBLE PRECISION,
        boundary_layer_height DOUBLE PRECISION,
        surface_pressure DOUBLE PRECISION,
        precipitation DOUBLE PRECISION,
        ndvi DOUBLE PRECISION,
        road_density DOUBLE PRECISION,
        population_density DOUBLE PRECISION,
        UNIQUE(grid_id, date)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_daily_features_date ON daily_features(date);",

    # 5. Model Predictions table
    """
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id SERIAL PRIMARY KEY,
        grid_id VARCHAR(20) REFERENCES grid_cells(grid_id) ON DELETE CASCADE,
        date DATE NOT NULL,
        predicted_aqi DOUBLE PRECISION NOT NULL,
        confidence_lower DOUBLE PRECISION,
        confidence_upper DOUBLE PRECISION,
        model_version VARCHAR(20),
        UNIQUE(grid_id, date, model_version)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(date);",

    # 6. Daily Maps Metadata table
    """
    CREATE TABLE IF NOT EXISTS aqi_daily_maps (
        map_id SERIAL PRIMARY KEY,
        date DATE UNIQUE NOT NULL,
        raster_path VARCHAR(255) NOT NULL,
        mean_aqi DOUBLE PRECISION,
        max_aqi DOUBLE PRECISION,
        min_aqi DOUBLE PRECISION,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # 7. Validation Runs table (Dual Validation Protocol)
    """
    CREATE TABLE IF NOT EXISTS validation_runs (
        run_id SERIAL PRIMARY KEY,
        model_version VARCHAR(20) NOT NULL,
        run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        rmse DOUBLE PRECISION,
        mae DOUBLE PRECISION,
        r_squared DOUBLE PRECISION,
        pearson_r DOUBLE PRECISION,
        spatial_holdout_rmse DOUBLE PRECISION,
        temporal_holdout_rmse DOUBLE PRECISION,
        n_points INTEGER
    );
    """,

    # 8. Model Registry table
    """
    CREATE TABLE IF NOT EXISTS model_registry (
        model_name VARCHAR(50) NOT NULL,
        version VARCHAR(20) PRIMARY KEY,
        framework VARCHAR(30),
        hyperparameters JSONB,
        metrics JSONB,
        status VARCHAR(20) DEFAULT 'candidate',
        registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
]

async def init_db(connection_url: str = None) -> bool:
    """Connect to PostgreSQL and create the database schema tables."""
    if not asyncpg:
        print("Error: asyncpg library is missing. Cannot initialize database.")
        return False

    url = connection_url or settings.DATABASE_URL
    # Normalise connection scheme for asyncpg
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to database at: {url.split('@')[-1]} (password masked)")
    
    try:
        conn = await asyncpg.connect(url, timeout=5.0)
        print("Connected successfully to PostgreSQL database!")
        
        async with conn.transaction():
            for stmt in DDL_STATEMENTS:
                stmt_stripped = stmt.strip()
                first_line = stmt_stripped.split('\n')[0] if '\n' in stmt_stripped else stmt_stripped
                print(f"Executing DDL: {first_line} ...")
                await conn.execute(stmt)
                
        await conn.close()
        print("Database schema initialization completed successfully.")
        return True
    except Exception as e:
        print(f"Database Initialization Failed: {e}", file=sys.stderr)
        print("Continuing program in DEV_MODE...", file=sys.stderr)
        return False

if __name__ == "__main__":
    # If run as script, perform initialization
    asyncio.run(init_db())
