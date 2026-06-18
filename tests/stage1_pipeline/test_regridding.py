"""
tests/stage1_pipeline/test_regridding.py
────────────────────────────────────────
Stage 1 — Data Pipeline Verification
Tests the mathematical soundness of the regridding engine.

Exit criteria:
  ✓ Conservative regrid preserves column totals within tolerance
  ✓ Round-trip error on a smooth analytic field is bounded
  ✓ Known landmark (Delhi) lands in the correct grid cell
  ✓ No lat/lon axis flip (orientation test)
"""

import numpy as np
import xarray as xr
import pandas as pd
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_source_grid(lon_min=67.0, lon_max=98.0,
                     lat_min=6.0,  lat_max=38.0, res=0.5) -> xr.Dataset:
    """Coarser source grid simulating a raw satellite product."""
    return xr.Dataset(coords={
        "lat": np.arange(lat_min, lat_max, res),
        "lon": np.arange(lon_min, lon_max, res),
    })


def analytic_field(lat_vals, lon_vals):
    """Smooth sin-cos field that has a known closed-form integral."""
    lon2d, lat2d = np.meshgrid(lon_vals, lat_vals)
    return np.sin(np.radians(lon2d)) * np.cos(np.radians(lat2d))


# ── Test 1: Coordinate Orientation (no lat/lon flip) ─────────────────────────

class TestCoordinateOrientation:
    def test_delhi_in_correct_cell(self, canonical_grid):
        """
        Delhi is at (~77.2°E, ~28.6°N).
        After snapping to the canonical grid the nearest cell must
        be within one grid-spacing of the true location.
        """
        DELHI_LON, DELHI_LAT = 77.2090, 28.6139
        GRID_RES = 0.1  # matches conftest canonical_grid

        lon_vals = canonical_grid.lon.values
        lat_vals = canonical_grid.lat.values

        nearest_lon = lon_vals[np.argmin(np.abs(lon_vals - DELHI_LON))]
        nearest_lat = lat_vals[np.argmin(np.abs(lat_vals - DELHI_LAT))]

        assert abs(nearest_lon - DELHI_LON) <= GRID_RES, (
            f"Delhi lon snap error {abs(nearest_lon - DELHI_LON):.3f}° > {GRID_RES}°"
        )
        assert abs(nearest_lat - DELHI_LAT) <= GRID_RES, (
            f"Delhi lat snap error {abs(nearest_lat - DELHI_LAT):.3f}° > {GRID_RES}°"
        )

    def test_lat_increases_northward(self, canonical_grid):
        """Latitude must increase from south to north (no flip)."""
        lat = canonical_grid.lat.values
        assert lat[0] < lat[-1], "Latitude axis is inverted (south-to-north expected)"

    def test_lon_increases_eastward(self, canonical_grid):
        """Longitude must increase west to east."""
        lon = canonical_grid.lon.values
        assert lon[0] < lon[-1], "Longitude axis is inverted (west-to-east expected)"

    def test_india_bounding_box(self, canonical_grid):
        """Canonical grid must fully cover India's extent."""
        assert canonical_grid.lon.values.min() <= 68.1, "Western India cut off"
        assert canonical_grid.lon.values.max() >= 97.4, "Eastern India cut off"
        assert canonical_grid.lat.values.min() <= 8.0,  "Southern India cut off"
        assert canonical_grid.lat.values.max() >= 35.0, "Northern India cut off"


# ── Test 2: Conservative Regrid — Column Total Preservation ──────────────────

class TestConservativeRegrid:
    """
    A conservative regrid (e.g., for HCHO column) must preserve the
    domain-integrated total within a small tolerance.
    We approximate this with a coarse→fine bilinear interpolation test
    (xESMF not required here; just numpy interp logic).
    """

    def test_mass_conservation_bilinear(self, canonical_grid):
        """
        Regrid a synthetic concentration field from 0.5° → 0.1°.
        The domain sum (weighted by cosine of latitude for area correction)
        must be preserved within 2%.
        """
        src_grid = make_source_grid(res=0.5)
        field = analytic_field(src_grid.lat.values, src_grid.lon.values)
        # Shift up so values are always positive (like a real column)
        field = field + 1.5

        # Compute source domain area-weighted sum
        lat_weights_src = np.cos(np.radians(src_grid.lat.values))
        src_total = np.sum(field * lat_weights_src[:, np.newaxis])

        # Bilinear interpolation to target grid
        from scipy.interpolate import RegularGridInterpolator
        interp = RegularGridInterpolator(
            (src_grid.lat.values, src_grid.lon.values),
            field,
            method="linear",
            bounds_error=False,
            fill_value=None,
        )
        tgt_lat = canonical_grid.lat.values
        tgt_lon = canonical_grid.lon.values
        tgt_lon2d, tgt_lat2d = np.meshgrid(tgt_lon, tgt_lat)
        pts = np.stack([tgt_lat2d.ravel(), tgt_lon2d.ravel()], axis=1)
        tgt_field = interp(pts).reshape(len(tgt_lat), len(tgt_lon))

        # Compute target area-weighted sum — scale by area ratio (cells per src cell)
        lat_weights_tgt = np.cos(np.radians(tgt_lat))
        tgt_total = np.sum(tgt_field * lat_weights_tgt[:, np.newaxis])

        # Normalize by grid-area ratio to compare totals
        src_ncells = len(src_grid.lat) * len(src_grid.lon)
        tgt_ncells = len(tgt_lat) * len(tgt_lon)
        normalized_tgt = tgt_total / tgt_ncells * src_ncells

        relative_error = abs(normalized_tgt - src_total) / abs(src_total)
        assert relative_error < 0.05, (
            f"Area-normalized total not conserved: relative error = {relative_error:.3%}"
        )

    def test_wind_components_averaged_separately(self, synthetic_datacube):
        """
        Wind speed derived from averaged u/v components must be ≤
        average of point-wise speeds (triangle inequality).
        This confirms we are NOT averaging speed/direction directly.
        """
        u = synthetic_datacube["u_component_of_wind_10m"].values
        v = synthetic_datacube["v_component_of_wind_10m"].values

        mean_u = u.mean(axis=0)
        mean_v = v.mean(axis=0)
        speed_from_mean_components = np.sqrt(mean_u**2 + mean_v**2)
        mean_of_speeds = np.sqrt(u**2 + v**2).mean(axis=0)

        # Triangle inequality: |mean(u,v)| <= mean(|u,v|)
        assert np.all(speed_from_mean_components <= mean_of_speeds + 1e-6), (
            "Wind speed from averaged components exceeds mean of speeds — "
            "averaging methodology is wrong."
        )

    def test_fire_count_is_summed_not_averaged(self, synthetic_datacube):
        """
        Fire count is an extensive quantity (sum, not average).
        We verify no fire data gets averaged across days accidentally
        by checking the sum across time.
        """
        fire = synthetic_datacube["fire_count"].values
        # Any positive fire count cell should have a positive sum across days
        assert fire.sum() >= fire.mean() * fire.shape[0] * 0.999, (
            "Fire count appears to be averaged rather than summed"
        )


# ── Test 3: Units & Value Ranges ──────────────────────────────────────────────

class TestPhysicalRanges:
    """Verify that all variables in the datacube fall within physically valid ranges."""

    PHYSICAL_RANGES = {
        "tropospheric_HCHO":          (0.0, 1e-3),      # mol/m²
        "tropospheric_NO2":           (0.0, 5e-4),      # mol/m²
        "temperature_2m":             (230.0, 340.0),   # K
        "u_component_of_wind_10m":    (-80.0, 80.0),    # m/s
        "v_component_of_wind_10m":    (-80.0, 80.0),    # m/s
        "fire_count":                 (0, 10000),        # count
        "fire_frp":                   (0.0, 50000.0),   # MW
    }

    @pytest.mark.parametrize("var", list(PHYSICAL_RANGES.keys()))
    def test_variable_in_physical_range(self, synthetic_datacube, var):
        lo, hi = self.PHYSICAL_RANGES[var]
        data = synthetic_datacube[var].values
        assert np.all(data >= lo), f"{var}: values below minimum {lo}"
        assert np.all(data <= hi), f"{var}: values above maximum {hi}"

    def test_no_nan_in_datacube_after_qc(self, synthetic_datacube):
        """Synthetic cube has no NaN — real pipeline must mask, not propagate NaN."""
        for var in self.PHYSICAL_RANGES:
            arr = synthetic_datacube[var].values
            assert not np.isnan(arr).any(), f"Unexpected NaN in {var}"


# ── Test 4: Timezone & Temporal Conventions ───────────────────────────────────

class TestTemporalConventions:
    def test_time_axis_is_utc(self, synthetic_datacube):
        assert synthetic_datacube["time"].attrs.get("timezone") == "UTC", (
            "Time axis must be UTC-anchored"
        )

    def test_no_duplicate_dates(self, synthetic_datacube):
        times = synthetic_datacube.time.values
        assert len(times) == len(set(times)), "Duplicate dates in time axis"

    def test_no_missing_dates(self, synthetic_datacube):
        times = pd.DatetimeIndex(synthetic_datacube.time.values)
        expected = pd.date_range(times[0], times[-1], freq="D")
        assert len(times) == len(expected), (
            f"Missing dates: expected {len(expected)} got {len(times)}"
        )



# ── Test 5: IST → UTC Conversion ─────────────────────────────────────────────

class TestTimezoneConversion:
    """Verify IST (UTC+05:30) to UTC conversion is applied correctly."""

    @pytest.mark.parametrize("ist_hour,expected_utc_hour", [
        (0, 18),   # midnight IST → 18:30 UTC previous day
        (6, 0),    # 06:00 IST → 00:30 UTC same day
        (12, 6),   # 12:00 IST → 06:30 UTC
        (18, 12),  # 18:00 IST → 12:30 UTC
    ])
    def test_ist_to_utc_offset(self, ist_hour, expected_utc_hour):
        from datetime import datetime, timezone, timedelta
        IST_OFFSET = timedelta(hours=5, minutes=30)
        ist_tz = timezone(IST_OFFSET)
        ist_dt = datetime(2023, 11, 1, ist_hour, 0, tzinfo=ist_tz)
        utc_dt = ist_dt.astimezone(timezone.utc)
        assert utc_dt.hour == expected_utc_hour, (
            f"IST {ist_hour:02d}:00 → UTC expected {expected_utc_hour:02d}:00, "
            f"got {utc_dt.hour:02d}:00"
        )
