"""
services/aqi_calc.py
--------------------
CPCB (Central Pollution Control Board) AQI calculation engine.

Reference: CPCB AQI Technical Document, 2014
           https://cpcb.nic.in/National-Air-Quality-Index/

The AQI is computed as:
    AQI = max(sub_index(pollutant) for pollutant in measured_pollutants)

Each sub-index is computed by linear interpolation within a breakpoint table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Breakpoint:
    """A single row in the AQI breakpoint table."""

    c_lo: float  # Concentration low  (µg/m³ or ppm)
    c_hi: float  # Concentration high
    i_lo: int    # AQI sub-index low
    i_hi: int    # AQI sub-index high


# ---------------------------------------------------------------------------
# CPCB Breakpoint Tables
# All concentrations are 24-hour averages unless noted.
# ---------------------------------------------------------------------------

# PM2.5 (µg/m³) — 24-hour average
PM25_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0,    30,   0,   50),
    Breakpoint(31,   60,   51,  100),
    Breakpoint(61,   90,   101, 200),
    Breakpoint(91,   120,  201, 300),
    Breakpoint(121,  250,  301, 400),
    Breakpoint(251,  500,  401, 500),
]

# PM10 (µg/m³) — 24-hour average
PM10_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0,    50,   0,   50),
    Breakpoint(51,   100,  51,  100),
    Breakpoint(101,  250,  101, 200),
    Breakpoint(251,  350,  201, 300),
    Breakpoint(351,  430,  301, 400),
    Breakpoint(431,  600,  401, 500),
]

# NO2 (µg/m³) — 24-hour average
NO2_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0,    40,   0,   50),
    Breakpoint(41,   80,   51,  100),
    Breakpoint(81,   180,  101, 200),
    Breakpoint(181,  280,  201, 300),
    Breakpoint(281,  400,  301, 400),
    Breakpoint(401,  800,  401, 500),
]

# SO2 (µg/m³) — 24-hour average
SO2_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0,    40,   0,   50),
    Breakpoint(41,   80,   51,  100),
    Breakpoint(81,   380,  101, 200),
    Breakpoint(381,  800,  201, 300),
    Breakpoint(801,  1600, 301, 400),
    Breakpoint(1601, 2100, 401, 500),
]

# O3 (µg/m³) — 8-hour average
O3_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0,    50,   0,   50),
    Breakpoint(51,   100,  51,  100),
    Breakpoint(101,  168,  101, 200),
    Breakpoint(169,  208,  201, 300),
    Breakpoint(209,  748,  301, 400),
    Breakpoint(749,  1000, 401, 500),
]

# CO (mg/m³) — 8-hour average
CO_BREAKPOINTS: List[Breakpoint] = [
    Breakpoint(0.0,  1.0,  0,   50),
    Breakpoint(1.1,  2.0,  51,  100),
    Breakpoint(2.1,  10.0, 101, 200),
    Breakpoint(10.1, 17.0, 201, 300),
    Breakpoint(17.1, 34.0, 301, 400),
    Breakpoint(34.1, 50.0, 401, 500),
]

# ---------------------------------------------------------------------------
# AQI category thresholds & metadata
# ---------------------------------------------------------------------------

AQI_CATEGORIES: List[Tuple[int, int, str, str, str]] = [
    # (lo, hi, category, color_hex, health_advice)
    (0,   50,  "Good",        "#00B050",
     "Air quality is satisfactory and poses little or no risk."),
    (51,  100, "Satisfactory","#92D050",
     "Air quality is acceptable. Unusually sensitive individuals may experience minor issues."),
    (101, 200, "Moderate",    "#FFFF00",
     "Members of sensitive groups may experience health effects. General public is unlikely to be affected."),
    (201, 300, "Poor",        "#FF7F00",
     "Everyone may begin to experience health effects. Limit prolonged outdoor exertion."),
    (301, 400, "Very Poor",   "#FE0000",
     "Health warnings of emergency conditions. Avoid prolonged outdoor activity."),
    (401, 500, "Severe",      "#7030A0",
     "Health alert: everyone may experience more serious health effects. Stay indoors."),
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _find_breakpoint(value: float, table: List[Breakpoint]) -> Optional[Breakpoint]:
    """Return the breakpoint row that contains *value*, or None if out of range."""
    for bp in table:
        if bp.c_lo <= value <= bp.c_hi:
            return bp
    # Clamp to the highest tier when concentration exceeds table maximum
    if value > table[-1].c_hi:
        return table[-1]
    return None


def _sub_index(concentration: float, table: List[Breakpoint]) -> float:
    """
    Compute the AQI sub-index for a single pollutant using linear interpolation.

    Formula:
        I = ((I_hi - I_lo) / (C_hi - C_lo)) * (C - C_lo) + I_lo
    """
    if concentration < 0:
        raise ValueError(f"Concentration must be non-negative, got {concentration}")

    bp = _find_breakpoint(concentration, table)
    if bp is None:
        return 0.0  # No valid breakpoint → sub-index is 0

    # Avoid division-by-zero when breakpoint range is a single point
    if bp.c_hi == bp.c_lo:
        return float(bp.i_hi)

    sub_idx = (
        (bp.i_hi - bp.i_lo) / (bp.c_hi - bp.c_lo)
    ) * (concentration - bp.c_lo) + bp.i_lo

    return round(sub_idx, 2)


def _get_category_meta(aqi_value: float) -> Tuple[str, str, str]:
    """Return (category, color_hex, health_advice) for a given AQI value."""
    for lo, hi, cat, color, advice in AQI_CATEGORIES:
        if lo <= aqi_value <= hi:
            return cat, color, advice
    # If value is above 500, treat as Severe
    return AQI_CATEGORIES[-1][2], AQI_CATEGORIES[-1][3], AQI_CATEGORIES[-1][4]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Mapping from pollutant key (as supplied by callers) to its breakpoint table
POLLUTANT_TABLES: Dict[str, List[Breakpoint]] = {
    "PM2.5": PM25_BREAKPOINTS,
    "PM10":  PM10_BREAKPOINTS,
    "NO2":   NO2_BREAKPOINTS,
    "SO2":   SO2_BREAKPOINTS,
    "O3":    O3_BREAKPOINTS,
    "CO":    CO_BREAKPOINTS,
}


def compute_sub_indices(pollutant_concs: Dict[str, float]) -> Dict[str, float]:
    """
    Compute the AQI sub-index for every supplied pollutant.

    Args:
        pollutant_concs: dict mapping pollutant name → concentration.
            Accepted keys: PM2.5, PM10, NO2, SO2, O3, CO.
            Missing pollutants are silently skipped.

    Returns:
        dict mapping pollutant name → sub-index value.
    """
    sub_indices: Dict[str, float] = {}
    for pollutant, conc in pollutant_concs.items():
        table = POLLUTANT_TABLES.get(pollutant)
        if table is None:
            continue  # Unknown pollutant — skip
        sub_indices[pollutant] = _sub_index(conc, table)
    return sub_indices


def compute_aqi(pollutant_concs: Dict[str, float]) -> Dict[str, object]:
    """
    Compute the composite CPCB AQI from a set of pollutant concentrations.

    Args:
        pollutant_concs: dict mapping pollutant name → 24-hr (or 8-hr for O3/CO)
            average concentration in the units specified by the CPCB breakpoint
            tables (µg/m³ for PM2.5, PM10, NO2, SO2, O3 and mg/m³ for CO).

    Returns:
        dict with keys:
            - value (float)          : composite AQI (max of all sub-indices)
            - category (str)         : AQI category label
            - color_hex (str)        : HTML colour code
            - dominant_pollutant (str): pollutant driving the AQI
            - health_advice (str)    : public health message
            - sub_indices (dict)     : per-pollutant sub-index breakdown

    Raises:
        ValueError: if pollutant_concs is empty or no known pollutants are found.

    Example:
        >>> result = compute_aqi({"PM2.5": 95, "PM10": 180, "NO2": 75})
        >>> result["value"]
        200.0
        >>> result["dominant_pollutant"]
        'PM2.5'
    """
    if not pollutant_concs:
        raise ValueError("pollutant_concs must contain at least one entry.")

    sub_indices = compute_sub_indices(pollutant_concs)

    if not sub_indices:
        raise ValueError(
            f"No recognised pollutants found. Accepted keys: {list(POLLUTANT_TABLES.keys())}"
        )

    # Composite AQI = maximum of all sub-indices
    dominant = max(sub_indices, key=lambda k: sub_indices[k])
    aqi_value = sub_indices[dominant]

    category, color_hex, health_advice = _get_category_meta(aqi_value)

    return {
        "value": aqi_value,
        "category": category,
        "color_hex": color_hex,
        "dominant_pollutant": dominant,
        "health_advice": health_advice,
        "sub_indices": sub_indices,
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def aqi_to_category(aqi_value: float) -> Tuple[str, str, str]:
    """
    Convert a raw AQI value to (category, color_hex, health_advice).
    Convenience wrapper around _get_category_meta.
    """
    return _get_category_meta(aqi_value)
