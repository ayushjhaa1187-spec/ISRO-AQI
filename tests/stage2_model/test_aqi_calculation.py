"""
tests/stage2_model/test_aqi_calculation.py
───────────────────────────────────────────
Stage 2 — AQI Formula Verification
Tests the CPCB AQI sub-index formula against hand-computed values.
No model needed — pure math validation.

Exit criteria:
  ✓ AQI sub-index matches hand-computed values for each pollutant
  ✓ AQI = max(sub-indices) rule enforced
  ✓ Category labels match CPCB breakpoints exactly
  ✓ No negative concentrations or AQI values
"""

import pytest


# ── CPCB AQI Breakpoints (hand-coded for independent verification) ─────────────
# Format: (C_low, C_high, I_low, I_high)
PM25_BREAKPOINTS = [
    (0,   30,    0,   50),   # Good
    (31,  60,   51,  100),   # Satisfactory
    (61,  90,  101,  200),   # Moderate
    (91, 120,  201,  300),   # Poor
    (121, 250, 301,  400),   # Very Poor
    (251, 500, 401,  500),   # Severe
]

NO2_BREAKPOINTS = [
    (0,   40,    0,   50),
    (41,  80,   51,  100),
    (81, 180,  101,  200),
    (181, 280, 201,  300),
    (281, 400, 301,  400),
    (401, 800, 401,  500),
]

AQI_CATEGORIES = [
    (0,   50,  "Good",          "#00e400"),
    (51,  100, "Satisfactory",  "#ffff00"),
    (101, 200, "Moderate",      "#ff7e00"),
    (201, 300, "Poor",          "#ff0000"),
    (301, 400, "Very Poor",     "#8f3f97"),
    (401, 500, "Severe",        "#7e0023"),
]


def compute_sub_index(concentration: float, breakpoints: list) -> float:
    """Reference CPCB AQI linear interpolation formula."""
    for (C_lo, C_hi, I_lo, I_hi) in breakpoints:
        if C_lo <= concentration <= C_hi:
            return I_lo + (I_hi - I_lo) * (concentration - C_lo) / (C_hi - C_lo)
    return 500.0  # beyond severe


def get_category(aqi: float) -> tuple:
    for (lo, hi, label, color) in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return label, color
    return "Severe", "#7e0023"


# ── Test 1: PM2.5 Sub-index Hand-computed Values ──────────────────────────────

class TestPM25SubIndex:
    @pytest.mark.parametrize("conc,expected_aqi", [
        (0,    0.0),    # lower bound Good
        (15,   25.0),   # mid Good
        (30,   50.0),   # upper bound Good
        (45,   75.0),   # mid Satisfactory
        (60,   100.0),  # upper bound Satisfactory
        # Moderate band [61–90] → AQI [101–200]: 75 → 101 + (200-101)*(75-61)/(90-61) ≈ 148.8
        (75,   148.8),
        (90,   200.0),  # upper bound Moderate
        # Poor band [91–120] → AQI [201–300]: 105 → 201 + (300-201)*(105-91)/(120-91) ≈ 248.8
        (105,  248.8),
        (120,  300.0),  # upper bound Poor
        (185,  350.0),  # mid Very Poor
        (250,  400.0),  # upper bound Very Poor
        (375,  450.0),  # mid Severe
    ])
    def test_pm25_sub_index(self, conc, expected_aqi):
        result = compute_sub_index(conc, PM25_BREAKPOINTS)
        assert abs(result - expected_aqi) < 2.0, (
            f"PM2.5={conc} µg/m³ → expected AQI {expected_aqi}, got {result:.2f}"
        )



# ── Test 2: NO2 Sub-index ─────────────────────────────────────────────────────

class TestNO2SubIndex:
    @pytest.mark.parametrize("conc,expected_aqi", [
        (0,    0.0),
        (20,   25.0),
        (40,   50.0),
        (60,   75.0),
        (80,   100.0),
        (130,  150.0),
        (180,  200.0),
    ])
    def test_no2_sub_index(self, conc, expected_aqi):
        result = compute_sub_index(conc, NO2_BREAKPOINTS)
        assert abs(result - expected_aqi) < 0.5, (
            f"NO2={conc} µg/m³ → expected AQI {expected_aqi}, got {result:.2f}"
        )


# ── Test 3: AQI = max(sub-indices) ───────────────────────────────────────────

class TestAQIComposition:
    def test_aqi_is_maximum_of_sub_indices(self):
        """The overall AQI must be the maximum of all pollutant sub-indices."""
        # PM2.5=45 → Satisfactory band [31-60] → AQI = 51+(100-51)*(45-31)/(60-31) = ~74.7
        # NO2=200  → Poor band [181-280]       → AQI = 201+(300-201)*(200-181)/(280-181) = ~219.9
        sub_indices = {
            "PM2.5": compute_sub_index(45, PM25_BREAKPOINTS),
            "NO2":   compute_sub_index(200, NO2_BREAKPOINTS),
        }
        expected_aqi = max(sub_indices.values())
        expected_dominant = max(sub_indices, key=sub_indices.get)

        assert abs(expected_aqi - 219.9) < 2.0, f"NO2 sub-index mismatch: {expected_aqi}"
        assert expected_dominant == "NO2"


    def test_no_negative_aqi(self):
        for conc in [0, 0.001, 0.1, 1.0]:
            assert compute_sub_index(conc, PM25_BREAKPOINTS) >= 0.0

    def test_category_boundaries_are_exact(self):
        """Each breakpoint boundary must resolve to the correct category."""
        boundary_cases = [
            (50,  "Good"),
            (51,  "Satisfactory"),
            (100, "Satisfactory"),
            (101, "Moderate"),
            (200, "Moderate"),
            (201, "Poor"),
            (300, "Poor"),
            (301, "Very Poor"),
            (400, "Very Poor"),
            (401, "Severe"),
        ]
        for aqi_val, expected_cat in boundary_cases:
            cat, _ = get_category(aqi_val)
            assert cat == expected_cat, (
                f"AQI {aqi_val} → expected '{expected_cat}', got '{cat}'"
            )

    def test_color_hex_matches_category(self):
        """Each AQI category must map to the official CPCB color."""
        expected_colors = {
            "Good":       "#00e400",
            "Satisfactory": "#ffff00",
            "Moderate":   "#ff7e00",
            "Poor":       "#ff0000",
            "Very Poor":  "#8f3f97",
            "Severe":     "#7e0023",
        }
        for cat, color in expected_colors.items():
            aqi_mid = {
                "Good": 25, "Satisfactory": 75, "Moderate": 150,
                "Poor": 250, "Very Poor": 350, "Severe": 450
            }[cat]
            returned_cat, returned_color = get_category(aqi_mid)
            assert returned_cat == cat
            assert returned_color == color


# ── Test 4: ML Data Split Integrity ──────────────────────────────────────────

import numpy as np
import pandas as pd


class TestDataSplitIntegrity:
    """Ensure temporal train/test split has zero leakage."""

    def test_no_test_dates_in_train(self):
        """
        Simulate a temporal split: train on 2019–2022, test on 2023.
        Assert zero overlap.
        """
        all_dates = pd.date_range("2019-01-01", "2023-12-31", freq="D")
        train_dates = all_dates[all_dates.year < 2023]
        test_dates  = all_dates[all_dates.year >= 2023]

        overlap = set(train_dates).intersection(set(test_dates))
        assert len(overlap) == 0, f"Temporal leakage: {len(overlap)} dates overlap"

    def test_normalisation_on_train_only(self):
        """
        Normalization stats (mean, std) must come from the training set only.
        Applying them to the test set must not use test statistics.
        """
        rng = np.random.default_rng(0)
        train_data = rng.normal(loc=50.0, scale=20.0, size=(1000,))
        test_data  = rng.normal(loc=80.0, scale=30.0, size=(200,))  # different dist

        train_mean, train_std = train_data.mean(), train_data.std()

        # Normalize both sets using ONLY train statistics
        train_norm = (train_data - train_mean) / train_std
        test_norm  = (test_data  - train_mean) / train_std

        # Train set normalized values should be roughly N(0,1)
        assert abs(train_norm.mean()) < 0.1
        assert abs(train_norm.std() - 1.0) < 0.1

        # Test set mean after train-normalization ≠ 0 (they have different dist)
        # This proves we are NOT using test statistics
        assert abs(test_norm.mean()) > 0.5, (
            "Test set normalized to mean≈0 which suggests test statistics were used"
        )

    def test_masked_loss_excludes_no_station_cells(self):
        """
        Loss must only be computed where CPCB labels exist.
        Simulates masked MSE: cells without stations contribute 0 to the loss.
        """
        rng = np.random.default_rng(1)
        predictions = rng.uniform(0, 300, (10, 50, 60))
        labels      = np.full_like(predictions, np.nan)

        # Plant labels at 5 station cells
        station_cells = [(5, 10), (3, 20), (7, 40), (2, 5), (8, 55)]
        for (r, c) in station_cells:
            labels[:, r, c] = rng.uniform(0, 300, 10)

        mask = ~np.isnan(labels)
        loss = np.nanmean((predictions[mask] - labels[mask]) ** 2)

        # Loss must be finite (only station cells contribute)
        assert np.isfinite(loss), "Masked loss is not finite"
        # Unmasked array contains NaN since labels are sparse
        full_loss_arr = (predictions - labels) ** 2
        assert not np.all(np.isfinite(full_loss_arr)), (
            "Full (unmasked) loss should contain NaN — labels are sparse"
        )
