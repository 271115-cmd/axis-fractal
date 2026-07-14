"""
config.py — the single source of truth for paths, coordinate systems, and study areas.

Every other module imports these values instead of hard-coding its own copy. That way there
is exactly ONE place to change a parameter, and it always matches parameters.md. (This file
is not in the original CLAUDE.md file list; it was added in Phase 1 because acquire.py and
audit.py both need the same boxes and CRS, and duplicating them would invite mistakes.)
"""
from __future__ import annotations

import warnings
from pathlib import Path

# Harmless: rasterio's array read triggers a NumPy 2.5 deprecation notice. It does not affect
# results; we silence just that one message so the pipeline output stays readable.
warnings.filterwarnings("ignore", message="Setting the shape on a NumPy array")

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

# --- Phase 2 rasterization parameters -----------------------------------------------------
RASTER_RES_M = 2.0        # metres per pixel. 2 m resolves a 4 m alley as ~2 px wide.
RASTER_ALL_TOUCHED = False  # burn a pixel only if its CENTRE is inside the shape (area-true)

# Street WIDTH (metres, full carriageway) by OSM highway class. We buffer each street
# centreline by width/2 to give it real width before rasterizing. Provisional — the brief
# anchors primary=20, residential=8, alley≈4; refine from field measurements later.
STREET_WIDTHS = {
    "motorway": 25.0, "motorway_link": 12.0,
    "trunk": 22.0,    "trunk_link": 11.0,
    "primary": 20.0,  "primary_link": 10.0,
    "secondary": 15.0, "secondary_link": 8.0,
    "tertiary": 12.0,  "tertiary_link": 7.0,
    "residential": 8.0, "unclassified": 8.0,
    "living_street": 6.0, "pedestrian": 6.0,
    "service": 4.0,     # hutong alleys are often tagged 'service' -> matches brief's ~4 m alley
    "footway": 4.0, "path": 4.0, "steps": 4.0, "track": 4.0,
    "cycleway": 3.0, "corridor": 3.0,
    "_default": 6.0,    # anything unrecognised
}

# --- Phase 3 box-counting parameters ------------------------------------------------------
# Box sizes in pixels, powers of 2. At 2 m/px these are 2 m .. 1 km.
BOX_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
# We FIT the slope only over a middle "scaling range": exclude the smallest boxes (pixel-scale
# rendering noise) and the largest (too few boxes across the ~830 px-wide transect to be stable).
BOXCOUNT_FIT_MIN_PX = 4     # 8 m — above pixel noise
BOXCOUNT_FIT_MAX_PX = 128   # 256 m — still >=6 boxes across the transect width
BOXCOUNT_R2_FLAG = 0.99     # below this over the chosen range, flag and inspect the plot by eye

# --- Phase 4 lacunarity parameters --------------------------------------------------------
# Gliding-box radii (box side) in pixels. At 2 m/px this spans 16 m .. 1 km
# (alley scale up to district scale). From the brief.
LAC_RADII = [8, 16, 32, 64, 128, 256, 512]

# --- Phase 5 per-tile sampling parameters -------------------------------------------------
TILE_PX = int(round(TILE_M / RASTER_RES_M))    # 500 m / 2 m = 250 px per tile
# Per-TILE box-counting needs a smaller scaling range than the whole transect (a 250 px tile
# cannot hold a 128 px box more than ~twice). Fit 2-32 px within a tile.
TILE_BOX_SIZES = [1, 2, 4, 8, 16, 32, 64]
TILE_BOX_FIT_MIN_PX = 2
TILE_BOX_FIT_MAX_PX = 32
TILE_LAC_RADII = [4, 8, 16, 32, 64]            # lacunarity scales inside a tile (8 m .. 128 m)
# A tile with almost no structure is not "fabric" (it is a void: lake, plaza, palace grounds).
# Exclude it from the fractal metrics rather than report a meaningless dimension.
TILE_MIN_BUILT_FRAC = 0.02

