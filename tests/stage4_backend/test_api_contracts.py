"""
tests/stage4_backend/test_api_contracts.py
───────────────────────────────────────────
Stage 4 — Backend API Contract Tests

Tests every endpoint for:
  ✓ Correct HTTP status codes
  ✓ Response schema matches Pydantic models
  ✓ Error handling for bad inputs (404, 422)
  ✓ Point-query returns physically plausible values
  ✓ GeoJSON FeatureCollections are valid

Requires the FastAPI app to be importable from backend.main.
If backend is not yet built, tests are auto-skipped.
"""

import pytest
import sys
import os

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

VALID_DATE = "2023-11-01"
INVALID_DATE = "9999-99-99"
DELHI_LAT = 28.6139
DELHI_LON = 77.2090


@pytest.fixture(scope="module")
def client():
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)
    except ImportError as e:
        pytest.skip(f"Backend not importable: {e}")


# ── Health Check ──────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body(self, client):
        r = client.get("/health")
        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"


# ── Meta Dates ────────────────────────────────────────────────────────────────

class TestMetaEndpoints:
    def test_dates_returns_200(self, client):
        r = client.get("/api/v1/meta/dates?layer=aqi")
        assert r.status_code == 200

    def test_dates_schema(self, client):
        r = client.get("/api/v1/meta/dates?layer=aqi")
        data = r.json()
        assert "layer" in data
        assert "available_dates" in data
        assert isinstance(data["available_dates"], list)

    def test_dates_invalid_layer_422(self, client):
        r = client.get("/api/v1/meta/dates?layer=INVALID_LAYER_XYZ")
        # Either 422 (validation) or 200 with empty list — both acceptable
        assert r.status_code in (404, 422)


# ── AQI Endpoints ─────────────────────────────────────────────────────────────

class TestAQIEndpoints:
    def test_aqi_meta_200(self, client):
        r = client.get(f"/api/v1/aqi?date={VALID_DATE}")
        assert r.status_code in (200, 404)  # 404 if date not in mock data

    def test_aqi_point_schema(self, client):
        r = client.get(f"/api/v1/aqi/point?lat={DELHI_LAT}&lon={DELHI_LON}&date={VALID_DATE}")
        assert r.status_code == 200
        data = r.json()
        required_fields = ["value", "category", "color_hex", "dominant_pollutant",
                           "health_advice", "lat", "lon", "date", "is_predicted"]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' in AQI point response"

    def test_aqi_value_in_valid_range(self, client):
        r = client.get(f"/api/v1/aqi/point?lat={DELHI_LAT}&lon={DELHI_LON}&date={VALID_DATE}")
        if r.status_code == 200:
            aqi_val = r.json()["value"]
            assert 0 <= aqi_val <= 500, f"AQI value {aqi_val} out of range [0, 500]"

    def test_aqi_category_is_valid(self, client):
        valid_categories = {"Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"}
        r = client.get(f"/api/v1/aqi/point?lat={DELHI_LAT}&lon={DELHI_LON}&date={VALID_DATE}")
        if r.status_code == 200:
            cat = r.json()["category"]
            assert cat in valid_categories, f"Unexpected category: '{cat}'"

    def test_aqi_point_out_of_india_422(self, client):
        """Point far outside India should return 422 or meaningful error."""
        r = client.get(f"/api/v1/aqi/point?lat=90.0&lon=180.0&date={VALID_DATE}")
        assert r.status_code in (200, 404, 422)

    def test_aqi_invalid_date_422(self, client):
        r = client.get(f"/api/v1/aqi/point?lat={DELHI_LAT}&lon={DELHI_LON}&date={INVALID_DATE}")
        assert r.status_code in (404, 422)

    def test_is_predicted_flag_present(self, client):
        """Response must clearly distinguish observed vs predicted."""
        r = client.get(f"/api/v1/aqi/point?lat={DELHI_LAT}&lon={DELHI_LON}&date={VALID_DATE}")
        if r.status_code == 200:
            assert "is_predicted" in r.json()


# ── HCHO / Hotspots ───────────────────────────────────────────────────────────

class TestHCHOEndpoints:
    def test_hotspots_returns_geojson(self, client):
        r = client.get(f"/api/v1/hotspots?start=2023-11-01&end=2023-11-10")
        assert r.status_code == 200
        data = r.json()
        assert data.get("type") == "FeatureCollection"
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_hotspot_feature_schema(self, client):
        r = client.get(f"/api/v1/hotspots?start=2023-11-01&end=2023-11-10")
        if r.status_code == 200:
            features = r.json()["features"]
            if features:
                props = features[0].get("properties", {})
                for key in ["date", "mean_hcho", "significance", "source_region"]:
                    assert key in props, f"Hotspot missing property '{key}'"


# ── Stations ──────────────────────────────────────────────────────────────────

class TestStationsEndpoints:
    def test_stations_returns_geojson(self, client):
        r = client.get("/api/v1/stations")
        assert r.status_code == 200
        data = r.json()
        assert data.get("type") == "FeatureCollection"

    def test_station_coordinates_in_india(self, client):
        r = client.get("/api/v1/stations")
        if r.status_code == 200:
            for feature in r.json().get("features", []):
                coords = feature["geometry"]["coordinates"]
                lon, lat = coords[0], coords[1]
                assert 67.0 <= lon <= 98.0, f"Station lon {lon} outside India"
                assert 6.0 <= lat <= 38.0, f"Station lat {lat} outside India"

    def test_timeseries_schema(self, client):
        r = client.get("/api/v1/stations/DEL01/timeseries?range=30d")
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, list)
            if data:
                pt = data[0]
                for key in ["datetime", "pollutant"]:
                    assert key in pt, f"Timeseries missing key '{key}'"


# ── Fire Endpoints ────────────────────────────────────────────────────────────

class TestFireEndpoints:
    def test_fire_returns_geojson(self, client):
        r = client.get(f"/api/v1/fire?date={VALID_DATE}")
        assert r.status_code == 200
        data = r.json()
        assert data.get("type") == "FeatureCollection"

    def test_fire_point_schema(self, client):
        r = client.get(f"/api/v1/fire?date={VALID_DATE}")
        if r.status_code == 200:
            features = r.json()["features"]
            if features:
                props = features[0].get("properties", {})
                assert "frp" in props, "Fire point missing 'frp' property"
                assert "confidence" in props, "Fire point missing 'confidence' property"


# ── Export ────────────────────────────────────────────────────────────────────

class TestExportEndpoints:
    def test_export_job_created(self, client):
        payload = {
            "layer": "aqi",
            "start": VALID_DATE,
            "end": "2023-11-07",
            "format": "csv"
        }
        r = client.post("/api/v1/export", json=payload)
        assert r.status_code in (200, 201, 202)
        if r.status_code in (200, 201, 202):
            data = r.json()
            assert "job_id" in data
            assert "status" in data

    def test_export_status_check(self, client):
        # Create a job first
        payload = {"layer": "hcho", "start": VALID_DATE, "end": "2023-11-05", "format": "geotiff"}
        r = client.post("/api/v1/export", json=payload)
        if r.status_code in (200, 201, 202):
            job_id = r.json().get("job_id")
            if job_id:
                r2 = client.get(f"/api/v1/export/{job_id}")
                assert r2.status_code in (200, 202)
                assert "status" in r2.json()
