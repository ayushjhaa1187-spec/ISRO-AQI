"""
tests/stage3_hcho/test_hotspot_detection.py
────────────────────────────────────────────
Stage 3 — HCHO Hotspot Detection Verification

Validates that hotspot detection methods correctly identify
planted hotspots (synthetic ground truth) and are stable
across parameter variations.

Exit criteria:
  ✓ Statistical threshold detects planted Punjab hotspot (Nov 3–5)
  ✓ DBSCAN clustering recovers known cluster coordinates
  ✓ Fire–HCHO correlation is significant (p < 0.05) during burning period
  ✓ HCHO enhancement lags fire by 0–2 days (physically expected)
  ✓ Detection is stable across ±20% threshold variation
"""

import numpy as np
import pytest
from scipy import stats


# ── Helper: Statistical Threshold Hotspot Detection ─────────────────────────

def detect_hotspots_threshold(hcho_array: np.ndarray, k: float = 2.0) -> np.ndarray:
    """
    Flag cells where HCHO > mean + k * std (climatological anomaly method).
    Returns a boolean mask of same shape.
    """
    mean = np.nanmean(hcho_array)
    std  = np.nanstd(hcho_array)
    return hcho_array > (mean + k * std)


def detect_hotspots_dbscan(lats, lons, hcho_values, threshold_quantile=0.90,
                            eps=1.5, min_samples=3):
    """
    DBSCAN clustering on high-HCHO cells.
    Returns cluster labels (-1 = noise).
    """
    from sklearn.cluster import DBSCAN

    # Select above-threshold pixels
    thresh = np.nanquantile(hcho_values, threshold_quantile)
    mask = hcho_values >= thresh

    if mask.sum() < min_samples:
        return np.full(mask.sum(), -1, dtype=int), mask

    pts = np.column_stack([lats[mask], lons[mask]])
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(pts)
    return labels, mask


# ── Test 1: Statistical Threshold Recovers Planted Hotspot ───────────────────

class TestStatisticalThresholdDetection:

    def test_detects_planted_punjab_hotspot(self, datacube_with_hotspot):
        """
        The planted hotspot (75–77°E, 29–32°N, days 3–5) must be
        flagged by the 2-sigma threshold on each of the 3 hotspot days.
        """
        ds = datacube_with_hotspot
        lon_vals = ds.lon.values
        lat_vals = ds.lat.values

        hotspot_lon_mask = (lon_vals >= 75.0) & (lon_vals <= 77.0)
        hotspot_lat_mask = (lat_vals >= 29.0) & (lat_vals <= 32.0)

        hotspot_days = [3, 4, 5]
        for t in hotspot_days:
            hcho_slice = ds["tropospheric_HCHO"].isel(time=t).values
            detected = detect_hotspots_threshold(hcho_slice, k=2.0)

            # At least one hotspot cell must be detected in the planted region
            detected_in_region = detected[np.ix_(hotspot_lat_mask, hotspot_lon_mask)]
            assert detected_in_region.any(), (
                f"Hotspot NOT detected on day {t} in Punjab region. "
                "Spatial alignment or detection threshold may be broken."
            )

    def test_no_false_positives_outside_hotspot_on_clean_days(self, synthetic_datacube):
        """
        On background days (no planted signal), detection rate should be low —
        only ~2.3% of cells should exceed 2-sigma by chance (Gaussian tail).
        """
        hcho_day0 = synthetic_datacube["tropospheric_HCHO"].isel(time=0).values
        detected = detect_hotspots_threshold(hcho_day0, k=2.0)
        false_positive_rate = detected.mean()
        # For a Gaussian, P(X > mu + 2*sigma) ≈ 2.3%
        assert false_positive_rate < 0.10, (
            f"False positive rate {false_positive_rate:.1%} is too high for background data"
        )

    def test_stable_across_threshold_variation(self, datacube_with_hotspot):
        """
        Hotspot detection must be stable across ±20% variation in k.
        If a hotspot disappears with a small k change, it's likely an artifact.
        """
        ds = datacube_with_hotspot
        hcho_day4 = ds["tropospheric_HCHO"].isel(time=4).values

        lon_vals = ds.lon.values
        lat_vals = ds.lat.values
        hotspot_lon_mask = (lon_vals >= 75.0) & (lon_vals <= 77.0)
        hotspot_lat_mask = (lat_vals >= 29.0) & (lat_vals <= 32.0)

        for k in [1.6, 2.0, 2.4]:  # ±20% variation
            detected = detect_hotspots_threshold(hcho_day4, k=k)
            in_region = detected[np.ix_(hotspot_lat_mask, hotspot_lon_mask)]
            assert in_region.any(), (
                f"Hotspot lost at k={k} — detection is not robust"
            )


# ── Test 2: DBSCAN Clustering ─────────────────────────────────────────────────

class TestDBSCANClustering:
    """Verify DBSCAN recovers known planted hotspot cluster."""

    def test_dbscan_recovers_planted_cluster(self, datacube_with_hotspot):
        """
        DBSCAN applied to the hotspot day must return at least one cluster
        centered in the Punjab region (75–77°E, 29–32°N).
        """
        from sklearn.cluster import DBSCAN

        ds = datacube_with_hotspot
        lat_vals = ds.lat.values
        lon_vals = ds.lon.values
        hcho = ds["tropospheric_HCHO"].isel(time=4).values

        thresh = np.nanquantile(hcho, 0.90)
        mask = hcho >= thresh

        lats_2d, lons_2d = np.meshgrid(lat_vals, lon_vals, indexing="ij")
        high_lats = lats_2d[mask]
        high_lons = lons_2d[mask]

        if len(high_lats) < 3:
            pytest.skip("Not enough high-HCHO cells for DBSCAN")

        pts = np.column_stack([high_lats, high_lons])
        labels = DBSCAN(eps=2.0, min_samples=3).fit_predict(pts)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        assert n_clusters >= 1, "DBSCAN found no clusters on hotspot day"

        # Check if any cluster centroid is in the Punjab region
        found_punjab = False
        for cl_id in set(labels):
            if cl_id == -1:
                continue
            cl_mask = labels == cl_id
            cl_lat = high_lats[cl_mask].mean()
            cl_lon = high_lons[cl_mask].mean()
            if 29.0 <= cl_lat <= 33.0 and 74.0 <= cl_lon <= 78.0:
                found_punjab = True
                break

        assert found_punjab, (
            "No DBSCAN cluster centroid found in Punjab/Haryana region on hotspot day"
        )


# ── Test 3: Fire–HCHO Correlation ─────────────────────────────────────────────

class TestFireHCHOCorrelation:
    """
    Verify that elevated fire counts are statistically correlated
    with elevated HCHO during the burning period.
    """

    def test_correlation_significant_during_burning(self, datacube_with_hotspot):
        """
        Domain-mean HCHO and domain-mean fire count over 10 days
        must have a significant Pearson correlation (p < 0.05).
        """
        ds = datacube_with_hotspot
        hcho_ts = ds["tropospheric_HCHO"].mean(dim=["lat", "lon"]).values
        fire_ts = ds["fire_count"].mean(dim=["lat", "lon"]).values

        r, p = stats.pearsonr(fire_ts, hcho_ts)
        assert p < 0.05, (
            f"Fire–HCHO correlation not significant: r={r:.3f}, p={p:.3f}. "
            "Check spatial alignment — signal may not be co-located."
        )
        assert r > 0, f"Negative correlation (r={r:.3f}) — fire reducing HCHO is unphysical"

    def test_hcho_lag_behind_fire(self, datacube_with_hotspot):
        """
        HCHO should be elevated 0–2 days after peak fire.
        Test that max cross-correlation occurs at lag 0 or 1.
        (Biomass-burning HCHO accumulates same-day to next-day.)
        """
        ds = datacube_with_hotspot
        hcho_ts = ds["tropospheric_HCHO"].mean(dim=["lat", "lon"]).values
        fire_ts = ds["fire_count"].mean(dim=["lat", "lon"]).values

        # Compute cross-correlation for lags 0, 1, 2 days
        n = len(fire_ts)
        max_lag = 3
        best_lag = 0
        best_corr = -np.inf

        for lag in range(0, max_lag + 1):
            if lag == 0:
                r, _ = stats.pearsonr(fire_ts, hcho_ts)
            else:
                r, _ = stats.pearsonr(fire_ts[:-lag], hcho_ts[lag:])
            if r > best_corr:
                best_corr = r
                best_lag = lag

        assert 0 <= best_lag <= 2, (
            f"Peak fire–HCHO cross-correlation at lag={best_lag} days, "
            "expected 0–2. May indicate transport issue."
        )


# ── Test 4: Source Region Identification ──────────────────────────────────────

class TestSourceRegionIdentification:
    """
    The IGP (Indo-Gangetic Plain) must show elevated HCHO
    during the planted hotspot days.
    IGP is roughly: lat 24–32°N, lon 74–88°E.
    """

    def test_igp_elevated_hcho_during_hotspot(self, datacube_with_hotspot):
        ds = datacube_with_hotspot
        lat_vals = ds.lat.values
        lon_vals = ds.lon.values

        igp_lat = (lat_vals >= 24.0) & (lat_vals <= 32.0)
        igp_lon = (lon_vals >= 74.0) & (lon_vals <= 88.0)

        # Mean HCHO over IGP on hotspot days vs background days
        hotspot_days = [3, 4, 5]
        background_days = [0, 1, 2, 6, 7, 8, 9]

        hcho = ds["tropospheric_HCHO"].values
        igp_hcho = hcho[:, np.ix_(igp_lat, igp_lon)[0], :][:, :, np.ix_(igp_lon)[0]]

        hot_mean = hcho[hotspot_days][:, np.ix_(igp_lat, igp_lon)[0], :][:, :, :].mean()
        bg_mean  = hcho[background_days][:, np.ix_(igp_lat, igp_lon)[0], :][:, :, :].mean()

        assert hot_mean > bg_mean * 1.5, (
            f"IGP HCHO not elevated during hotspot days: "
            f"hotspot={hot_mean:.2e}, background={bg_mean:.2e}"
        )
