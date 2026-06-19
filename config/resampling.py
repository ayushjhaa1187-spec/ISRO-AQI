# Per-variable resampling rules
# Rule of thumb: counts and fluxes are summed; concentrations and meteorology are averaged/interpolated; 
# wind is split into u/v and averaged separately.

RESAMPLING_RULES = {
    'no2_col': {'method': 'conservative', 'temporal': 'qa_weighted_mean'},
    'so2_col': {'method': 'conservative', 'temporal': 'qa_weighted_mean'},
    'co_col': {'method': 'conservative', 'temporal': 'qa_weighted_mean'},
    'o3_col': {'method': 'conservative', 'temporal': 'qa_weighted_mean'},
    'hcho_col': {'method': 'conservative', 'temporal': 'qa_weighted_mean'},
    'aod': {'method': 'bilinear', 'temporal': 'mean'},
    'u10': {'method': 'bilinear', 'temporal': 'mean'},
    'v10': {'method': 'bilinear', 'temporal': 'mean'},
    'blh': {'method': 'bilinear', 'temporal': 'mean'},
    't2m': {'method': 'bilinear', 'temporal': 'mean'},
    'rh': {'method': 'bilinear', 'temporal': 'mean'},
    'sp': {'method': 'bilinear', 'temporal': 'mean'},
    'precip': {'method': 'bilinear', 'temporal': 'mean'},
    'fire_count': {'method': 'sum', 'temporal': 'sum'},
    'frp_sum': {'method': 'sum', 'temporal': 'sum'},
}
