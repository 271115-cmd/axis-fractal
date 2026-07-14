# parameters.md — every parameter choice, with a one-line justification

This is the project's decision log. **Rule:** nothing in the analysis uses a "magic number"
that isn't recorded here with a reason. If you can't justify it out loud, it doesn't belong in
the code. Each entry notes whether it is **LOCKED** (decided and in use) or **PROVISIONAL**
(a starting default from the brief, to be confirmed or refined with data / field measurements).

---

## Phase 0 — Environment & setup  (decided 2026-07-14)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Python version | 3.12.13 | LOCKED | Brief asked for 3.11+. 3.12 is modern and has the widest pre-built ("wheel") coverage for the geospatial stack (osmnx/geopandas/rasterio wrap C libs); avoids source-compile failures. |
| Environment isolation | `venv` at `.venv/` | LOCKED | A virtual environment keeps this project's exact library versions separate from the system Python, so results are reproducible and nothing else on the machine is disturbed. |
| Dependency pinning | `requirements.txt` (lower bounds) + `requirements.lock.txt` (exact freeze) | LOCKED | Lower bounds document intent and stay readable; the lock file records the exact versions actually used so anyone can rebuild the identical environment (reproducibility, brief rule #4). |
| OSM coordinate system | WGS-84 (EPSG:4326), **no GCJ-02 correction** | LOCKED | OpenStreetMap stores WGS-84 globally, including China. GCJ-02 ("Mars coordinates") only applies to Chinese providers (Amap/Baidu) or Chinese basemap tiles. Applying `eviltransform` to OSM data would *introduce* a ~500 m error, not remove one. (This corrects a real error in the earlier AI draft.) |

---

## Phase 1 — Data acquisition & audit  (PROVISIONAL until we run it)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Comparison city | **Hong Kong** (changed from Seoul, 2026-07-14) | LOCKED | Hong Kong has no imperial ceremonial axis — so it tests whether human-scale texture comes from *heritage protection* or from *morphology*. Bonus: HK OSM coverage is far more complete than Beijing's, and there is no GCJ-02 issue. |
| Metric CRS — Beijing | UTM zone 50N, EPSG:32650 | PROVISIONAL | Beijing (~116.4°E) falls in UTM zone 50N; a metric CRS is required so buffers/tiles are in true metres, not degrees. Confirmed working in Phase 0 verify. |
| Metric CRS — Hong Kong | Hong Kong 1980 Grid, EPSG:2326 (UTM 50N / EPSG:32650 also valid) | PROVISIONAL | EPSG:2326 is HK's official local metric grid (metres), the most defensible choice for the HK arm. UTM 50N also covers HK (~114.15°E), so a single CRS could be used across both cities if we want strict consistency. Confirm at first use. |
| Transect width | ~1.6 km each (West / Center / East) | PROVISIONAL | From the brief; wide enough to hold several 500 m tiles across, narrow enough to isolate one urban fabric type. Exact bounding boxes to be fixed in Phase 1. |
| Audit tile size | 500 m × 500 m | PROVISIONAL | Matches the sampling tile size (Phase 5) so the completeness audit describes the same units we later measure. |
| Ground-truth check tiles | 3 known hutong tiles | PROVISIONAL | Brief requirement: visually compare OSM coverage against satellite imagery before trusting the data. |
| Transect band (N–S) | lat 39.868 → 39.944 | PROVISIONAL | Drum Tower (~39.942 N) down to Yongdingmen (~39.870 N) — the Central Axis corridor named in the brief, with small margins. |
| West transect bbox (W,S,E,N) | 116.3619, 39.868, 116.3806, 39.944 | PROVISIONAL | 1.6 km slice west of the Axis (hutong fabric: Xisi / Xinjiekou). Width 0.0187° ≈ 1.6 km at 39.9 N. |
| Center transect bbox | 116.3806, 39.868, 116.3994, 39.944 | PROVISIONAL | 1.6 km slice centred on the Axis (Drum Tower → Forbidden City → Yongdingmen). |
| East transect bbox | 116.3994, 39.868, 116.4181, 39.944 | PROVISIONAL | 1.6 km slice east of the Axis (Wangfujing / commercial). |
| OSM network_type | `"all"` | PROVISIONAL | Retrieves every public way incl. service/residential/pedestrian — the classes hutong alleys are usually tagged as. `"all_private"` reserved as a Phase 6 sensitivity option. |
| Audit low-coverage flag | building coverage < 0.10 | PROVISIONAL | Tiles below 10% built area are flagged for a human to check vs. satellite — could be a genuine void (park/lake/plaza) or a data gap. Not an automatic verdict. |
| Ground-truth basemap | Esri World Imagery | LOCKED | Western provider → WGS-84 aligned with our OSM data (a Chinese basemap would be GCJ-02, shifted ~500 m). |
| Ground-truth hutong points | Xisi / Shichahai / Nanluoguxiang | PROVISIONAL | One dense-hutong location per transect, in the preserved northern core, for the OSM-vs-satellite visual check. |

### Phase 1+ — Beijing footprint data source  (decided 2026-07-14)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Beijing footprint source | **Overture Maps** buildings | LOCKED | OSM footprints failed the hutong audit; Overture aggregates a China rooftop dataset (Zenodo DOI 10.5281/zenodo.8174931) that captures the fine-grain courtyard houses. Verified: median tile coverage roughly doubled and the ground-truth hutong sites went 5%→23% (Shichahai) and 9%→28% (Nanluoguxiang). |
| Microsoft Global ML Buildings | REJECTED | LOCKED | Empirically checked — the Microsoft dataset index has **0 tiles for mainland China** (only Japan/Mongolia in the region). Verifying this before use is the reason we didn't waste effort on it. |
| Street source (unchanged) | OSM | LOCKED | The Phase 1 audit found OSM streets complete and coherent; only footprints are replaced. Streets and footprints remain SEPARATE representations, per the brief. |
| Overture footprint caveat | machine-derived rooftops | NOTE | Overture's China footprints are ML-derived and may merge adjacent roofs or miss small structures; a big improvement over near-empty OSM, but not survey-grade. Treat as a distinct representation and cross-check in Hong Kong (Phase 8). |

---

## Phase 2 — Rasterization  (PROVISIONAL)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Raster resolution | 2 m / pixel | IN USE | Fine enough to resolve ~4 m alleys as ~2 px wide; a ~1.6 km transect is ~830×4224 px (manageable). Varied to 1/2/4 m in the Phase 6 sensitivity test. |
| Street widths (full table) | see `config.STREET_WIDTHS` | PROVISIONAL | Full carriageway width by highway class; buffer = width/2. Brief anchors honoured: primary 20 m, residential 8 m, alley≈4 m (service=4). Widest class wins for multi-tagged ways. Refine from field measurements. |
| Street buffer — primary | 20 m width (buffer 10 m) | PROVISIONAL | From the brief. |
| Street buffer — residential | 8 m width (buffer 4 m) | PROVISIONAL | From the brief. |
| Street buffer — service/footway (alleys) | 4 m width (buffer 2 m) | PROVISIONAL | Hutong alleys are usually tagged service/footway; 4 m = 2 px, the minimum to stay connected at 2 m/px. Matches the brief's ~4 m alley. |
| Rasterize all_touched | False | LOCKED | Burn a pixel only if its centre is inside the shape (area-true), so built fractions are meaningful. Alternative (True) reserved as a sensitivity check. |
| Beijing footprint layer rasterized | Overture (not OSM) | LOCKED | Per the Phase 1+ footprint fix; streets rasterized from OSM. Kept as two separate rasters per zone. |
| Binary encoding | 1 = structure, 0 = void | LOCKED | Convention fixed now so every raster in the project means the same thing. |

---

## Phase 3 — Box-counting dimension  (PROVISIONAL)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Box sizes | powers of 2 | PROVISIONAL | Standard for box-counting; gives evenly spaced points on the log-log axis. |
| Scaling range | exclude smallest (near pixel size) and largest (near image size) boxes | PROVISIONAL | The log-log relation is only linear over a middle range; the ends are artefacts of resolution and image extent. Exact range chosen per-plot and recorded. |
| Fit | least squares, report slope + 95% CI + R² | LOCKED | Brief requirement: a dimension without an R² and confidence interval is not a defensible measurement. |
| R² flag threshold | 0.99 | PROVISIONAL | Below this over the chosen range, we stop and inspect the log-log plot to pick the linear range explicitly rather than trusting an automatic fit. |

---

## Phase 4 — Gliding-box lacunarity  (PROVISIONAL)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Box radii r | 8, 16, 32, 64, 128, 256, 512 px | PROVISIONAL | At 2 m/px this spans 16 m–1 km — from alley scale to district scale. |
| Implementation | integral image / summed-area table | LOCKED | A naive sliding window on a ~4096² array exhausts RAM; the summed-area table computes every box sum in O(1). Brief requirement. |
| Output | full Λ(r) curve per sample (+ normalized) | LOCKED | Lacunarity is scale-dependent; a single number is meaningless without the curve. Brief anti-goal forbids single-number claims. |

---

## Phase 5 — Sampling & statistics  (PROVISIONAL)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Sampling tile | 500 m × 500 m, non-overlapping | PROVISIONAL | Independent samples per zone → distributions, not one number per zone. |
| Between-zone test | Mann-Whitney U + effect size | LOCKED | Non-parametric (doesn't assume normal distributions), appropriate for small tile counts; effect size shows practical, not just statistical, significance. |

---

## Phase 6 — Sensitivity analysis  (PROVISIONAL)

| Parameter | Values swept | Status | Justification |
|---|---|---|---|
| Raster resolution | 1 / 2 / 4 m | PROVISIONAL | Shows whether zone rankings survive changes in resolution. |
| Buffer widths | ±50% | PROVISIONAL | Shows whether conclusions depend on the (uncertain) road-width assumptions. |
| Representation | streets vs footprints | PROVISIONAL | Two independent views of the same fabric; agreement strengthens any claim. |

---

*Add a row here the moment any new parameter enters the code. An unlogged number is a bug.*
