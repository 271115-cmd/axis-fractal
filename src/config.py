"""
config.py — the single source of truth for paths, coordinate systems, and study areas.

Every other module imports these values instead of hard-coding its own copy. That way there
is exactly ONE place to change a parameter, and it always matches parameters.md. (This file
is not in the original CLAUDE.md file list; it was added in Phase 1 because acquire.py and
audit.py both need the same boxes and CRS, and duplicating them would invite mistakes.)
"""
from __future__ import annotations

from pathlib import Path

# --- Folders (all relative to the repo root, computed from this file's location) ---
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"

# --- Coordinate reference systems (CRS) ---
WGS84 = "EPSG:4326"          # what OpenStreetMap gives us: latitude/longitude in degrees
BEIJING_CRS = "EPSG:32650"   # UTM zone 50N — metres — used for ALL Beijing measurement
HONGKONG_CRS = "EPSG:2326"   # Hong Kong 1980 Grid — metres — for the Phase 8 HK arm

# --- Beijing study area: three ~1.6 km-wide N-S transects ---------------------------------
# The band runs north->south from the Drum Tower (~39.942 N) to Yongdingmen (~39.870 N),
# i.e. the Central Axis corridor. Each transect is one 1.6 km-wide longitude slice.
# 1.6 km at latitude 39.9 N  ==  1.6 / (111.32 * cos(39.9 deg)) degrees  ==  ~0.0187 deg lon.
#
# Each box is (west, south, east, north) in WGS-84 degrees — the tuple order osmnx 2.x wants.
# STATUS: provisional (logged in parameters.md); refine after the audit + visual check.
_LAT_SOUTH = 39.868   # just below Yongdingmen
_LAT_NORTH = 39.944   # just above the Drum Tower

BEIJING_TRANSECTS = {
    "west":   (116.3619, _LAT_SOUTH, 116.3806, _LAT_NORTH),  # hutong fabric west of the Axis
    "center": (116.3806, _LAT_SOUTH, 116.3994, _LAT_NORTH),  # the Central Axis corridor
    "east":   (116.3994, _LAT_SOUTH, 116.4181, _LAT_NORTH),  # Wangfujing / commercial east
}

# How we ask OSM for the street network. "all" = every public way including the small
# service/residential/pedestrian ways that hutong alleys are usually tagged as.
NETWORK_TYPE = "all"

# --- Phase 1 audit parameters ------------------------------------------------------------
TILE_M = 500.0            # audit/sampling tile size in metres (matches Phase 5)

# A tile whose building coverage falls below this fraction is FLAGGED for a human to check
# against satellite imagery — it may be a genuine void (park, lake, plaza) or a data gap.
LOW_COVERAGE_FLAG = 0.10  # 10% built area

# Three known dense-hutong locations, one drawn from each transect, used as ground-truth
# checks: we overlay OSM on satellite imagery here and see whether the alleys are mapped.
# (lat, lon) in WGS-84. These sit in the northern, historically preserved half of the core.
HUTONG_GROUNDTRUTH = {
    "Xisi (west)":          (39.9245, 116.3720),   # west transect
    "Shichahai (center)":   (39.9385, 116.3860),   # center transect, NW of the Forbidden City
    "Nanluoguxiang (east)": (39.9330, 116.4030),   # east transect (hutong north of Wangfujing)
}

# Satellite basemap for the ground-truth overlay. Esri World Imagery is a Western provider,
# so it is WGS-84 aligned and matches our OSM data. (A *Chinese* basemap would be GCJ-02 and
# would appear shifted ~500 m — the same coordinate issue documented in parameters.md.)
BASEMAP_PROVIDER = "Esri.WorldImagery"

