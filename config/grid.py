import numpy as np

# Canonical spatial grid
CRS = "EPSG:4326"
LON_MIN, LON_MAX = 67.0, 98.0
LAT_MIN, LAT_MAX = 6.0, 38.0
RESOLUTION = 0.05

LON = np.arange(LON_MIN, LON_MAX, RESOLUTION)   # length 620
LAT = np.arange(LAT_MIN, LAT_MAX, RESOLUTION)    # length 640
GRID_VERSION = "v1"
