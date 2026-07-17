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
| Box sizes | 1,2,4,…,512 px (powers of 2) | IN USE | Standard for box-counting; evenly spaced on the log-log axis. |
| Scaling (fit) range | 4–128 px (8–256 m) | IN USE | Excludes 1–2 px (pixel-scale saturation, visible curving up at the right of each plot) and 256–512 px (too few boxes across the ~830 px width, curving down at the left). Verified by eye on every plot. All 6 Beijing fits gave R² ≥ 0.996, so the middle range is genuinely linear. |
| Fit | least squares, report slope + 95% CI + R² | LOCKED | Brief requirement: a dimension without an R² and confidence interval is not a defensible measurement. |
| R² flag threshold | 0.99 | IN USE | Below this over the chosen range, stop and inspect the log-log plot to pick the linear range by eye. (Not triggered for Beijing — all fits cleared it.) |

---

## Phase 4 — Gliding-box lacunarity  (PROVISIONAL)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Box radii r | 8, 16, 32, 64, 128, 256, 512 px | IN USE | At 2 m/px this spans 16 m–1 km — from alley scale to district scale. |
| Implementation | integral image / summed-area table | LOCKED | A naive sliding window on a ~4096² array exhausts RAM; the summed-area table computes every box sum in O(1). Brief requirement. |
| Output | full Λ(r) curve per sample (+ normalized) | LOCKED | Lacunarity is scale-dependent; a single number is meaningless without the curve. Brief anti-goal forbids single-number claims. |
| Normalization | Λ(r) / Λ(8) (anchor at smallest r) | IN USE | Removes the absolute (density-driven) level so different-density zones' curve SHAPES are comparable. Note Λ(1)=1/p exactly (pure density). Alternative normalizations are a Phase 6 sensitivity consideration. |

---

## Phase 5 — Sampling & statistics

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Sampling tile | 500 m × 500 m (250 px), non-overlapping full tiles | IN USE | Independent samples per zone → distributions, not one number per zone. 48 tiles/zone (partial edge tiles dropped). |
| Per-tile Dᵦ fit range | 2–32 px | IN USE | A 250 px tile cannot hold a 128 px box; the whole-transect 4–128 px range doesn't apply. Median per-tile fit R² ≈ 0.998. |
| Per-tile Λ(r) scales | r = 4,8,16,32,64 px (tested 8,16,32) | IN USE | Within a 250 px tile, probes 8 m–128 m. Note: this is FINER than the 1 km scale where whole-transect zones diverged — per-tile stats test within-neighbourhood texture only. |
| Void exclusion | tiles < 2% built dropped from fractal metrics | IN USE | A lake/plaza/palace void is not fabric; its dimension is meaningless. 0–2 tiles/zone dropped; reported in results.md. |
| Between-zone test | Mann-Whitney U + rank-biserial effect size | LOCKED | Non-parametric (no normality assumption), fine for ~48 tiles/zone; effect size shows practical, not just statistical, significance. |
| Multiple comparisons | 24 tests (4 metrics × 2 reps × 3 pairs) | NOTE | Bonferroni-style threshold ≈ 0.05/24 ≈ 0.0021. No result clears strict correction; nominal p<0.05 findings reported as *suggestive*, weighted by effect size. |

---

## Phase 6 — Sensitivity analysis

| Parameter | Values swept | Status | Justification |
|---|---|---|---|
| Design | one-factor-at-a-time around 2 m / ×1.0 baseline | IN USE | Isolates the effect of each knob; simpler to read than a full 18-cell cross-product. |
| Raster resolution | 1 / 2 / 4 m | IN USE | Result: footprint Λ(64 m) zone ordering (Center>East>West) is resolution-INVARIANT; Dᵦ zone-indistinguishability also holds (absolute Dᵦ drifts down with coarser pixels, an expected artifact). |
| Buffer widths | ×0.5 / ×1.0 / ×1.5 | IN USE | Result: the streets Λ signal weakens as buffers widen (p 0.04→0.09 at ×1.5) — flagged as fragile. |
| Representation | streets vs footprints | IN USE | The robust signal is in footprints; streets give the opposite West-vs-Center direction and are buffer-sensitive. |
| Scale handling | scales fixed in METRES, converted to px per resolution | LOCKED | A "64 m" box must be 64 m at every resolution; comparing fixed pixel counts across resolutions would be an arithmetic artifact, not a finding. |

---

## Phase 8 — Hong Kong comparison

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Sampling design | compact per-district sample boxes (NOT transects) | IN USE | HK has no ceremonial axis; its comparison units are different *kinds of place*, so parallel transects don't apply. Honest consequence of comparing a planned imperial city to an unplanned port. |
| Metric CRS | EPSG:2326 (Hong Kong 1980 Grid) | IN USE | HK's official local metric grid; 2 m/px etc. carry over unchanged. |
| Sites | Sham Shui Po (tong lau), Tseung Kwan O (podium towers), Kat Hing Wai (walled village) | PROVISIONAL | Fine-grain vernacular / megastructure / heritage — the three contrasts the brief names. Megastructure = TKO (a podium-tower new town); alternatives were Kowloon Station / Central reclamation. |
| Sources | streets = OSM, footprints = Overture | LOCKED | SAME sources as Beijing so the cross-city comparison is fair. HK Overture coverage verified excellent vs satellite (SSP 52%, TKO 47% in ground-truth windows) — unlike Beijing OSM. |
| Kat Hing Wai caveat | small-sample qualitative reference | NOTE | A ~1 ha walled village yields few dense tiles; not a full distribution. Reported honestly. |
| 2D limitation | verticality not captured | NOTE | HK is extremely vertical; this is 2D plan analysis. Podium/street-level texture is valid; building height is out of scope. State explicitly (brief). |

---

## Phase 9 — Video assets

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Frame size | 1920×1080 px, dpi 100 | IN USE | Standard 1080p broadcast frame for the video series. |
| Background | dark (`#0b0b10`) | IN USE | Brief requirement; footprints render as warm off-white on near-black. |
| Box-counting box sizes | 256,128,64,32,16,8,4,2 px (descending) | IN USE | 128–4 px = the fitted range (accent); 256 & 2 px = excluded scale-ends (grey) — mirrors the Phase 3 methodology so the video shows the *real* fit. |
| Forbidden City crop | 760 px (~1.52 km) centred on 39.9175 N, 116.3960 E | PROVISIONAL | Fits the 833 px-wide Center raster; frames the palace mass + surrounding hutong grain. Adjust centre/size for a different shot. |
| Running dimension | least-squares slope over fitted points *so far* | IN USE | The video shows D emerging and settling (1.92 → 1.76) as finer boxes are added — pedagogical, and the final value matches the Phase 3 Center measurement. |
| Attribution burn-in | "© OpenStreetMap contributors · Overture Maps" | LOCKED | Accurate to our data (streets OSM, footprints Overture) — not OSM-only, per honesty. |
| Gliding-box: box size | 32 px = 64 m (step 20 px) | IN USE | Matches the Phase 5/paper headline scale (Λ(64 m)); 121 sweep frames per clip. |
| Gliding-box: demo tiles | Beijing west tile (14,1) Λ≈1.21; HK TKO tile (2,3) Λ≈3.05 | IN USE | Chosen to be REPRESENTATIVE of each zone's reported median Λ(64 m) — not cherry-picked extremes. Selected by scanning all tiles for the closest-to-median value. |
| Map renders | dark figure-ground, dpi 150, long side 12 in | IN USE | High-res per-transect/site footprint maps with title, 500 m scale bar, attribution burned in. |
| Frame determinism | one PNG per box size / sweep step; editor sets hold time | LOCKED | Deterministic + re-renderable (`make phase9`); frames gitignored (regenerable). |

### Phase 9b — Blender rendered animations

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Renderer / look | EEVEE; clay 0.85 white fabric, ground 0.05, world 0.02 dark | IN USE | Brief: stylized (not photoreal), one consistent look; EEVEE for speed (~1 s/frame at 1080p, 64 samples). |
| Reproducibility | final shots are headless `bpy` scripts in `src/blender/`; MCP only for interactive preview | LOCKED | Renders must rebuild from the repo (`blender -b -P <script>.py`), like every other output. |
| Local-origin export | `export_context.py` crops + offsets footprints to a 0,0 origin | LOCKED | Absolute UTM/HK coords sit ~4.4e6 m from origin → Blender float precision fails; must offset. |
| Zoom camera (shot 1) | 35 mm, TrackTo scene centre; street (c,−90,5 m) → plan (c,c,1150 m); clip_end 5000 m | IN USE | ~8 s descent/ascent, 480 f @ 60 fps, 1920×1080. clip_end raised because the plan view sits >1000 m up (default far-clip). |
| Crowd seed (match-cut) | 42 (`render_anim.py`) | IN USE | Deterministic crowds (reproducibility). Shot length ≤ BVH clip length → no looping/retargeting. |
| Mocap source | CMU Graphics Lab (mocap.cs.cmu.edu), BVH | NOTE | Free to use; credit "Motion data from mocap.cs.cmu.edu" in video descriptions. BVH files go in `data/raw/mocap/` (gitignored). |

### Central Axis landmark heights (`src/landmarks.py`) — published facts, cited

Height is this project's weakest data: only ~3% of Beijing footprints carry a real Overture height;
the rest get a 7 m zone-median default, which flattens the Axis. These published figures restore its
vertical rhythm. Positions geocoded from OpenStreetMap; heights from official/primary sources.

| Landmark | Height | Source |
|---|--:|---|
| 钟楼 Bell Tower | 47.9 m | zh.wikipedia.org/zh-cn/北京中轴线 |
| 鼓楼 Drum Tower | 46.7 m | (same) |
| 正阳门 Zhengyangmen (Qianmen) | 43.65 m — tallest old city gate | beijing.gov.cn/shipin/bjfq/18938.html |
| 太和殿 Hall of Supreme Harmony | 35.05 m (incl. 台基 terrace) | dpm.org.cn/explore/building/236465.html |
| 天安门 Tiananmen | 34.7 m | news.qq.com/rain/a/20240910A000UN00 |
| 永定门 Yongdingmen | 26.0 m | bjdch.gov.cn/mldc/bglj/whgj/202008/t20200827_2975733.html |
| 万春亭 Wanchun Pavilion | 15.38 m (pavilion only) | gygl.beijing.gov.cn/mlgy/mlgy_gyjg01/201912/t20191211_1048536.html |

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Application radius | 70 m from landmark centroid | PROVISIONAL | Footprints under a landmark take its published height and are tagged `height_src='landmark_published'` — never silently overwritten. |
| Jingshan hill | **unused** (`JINGSHAN_HILL_M = None`) | NOTE | The 万春亭 figure is the pavilion only; it stands on an artificial hill that is TERRAIN we don't model. Commonly cited ~45–48 m but **unverified**, so deliberately not used rather than guessed. |
| 云上中轴 (Tencent × Beijing CHB) | **reference only, no assets taken** | LOCKED | Excellent for proportion/colour/relation. Its 3D assets are proprietary (~15 TB, in-app) — we read published facts and build our own geometry. Facts (heights/positions) aren't copyrightable; the scan meshes are. |
| PanoCity (HF, CC-BY-4.0) | **rejected after inspection** | NOTE | Aerial panos + depth + poses, Beijing 20 blocks — but poses are arbitrary LOCAL coords (e.g. 768.0, −9.0, 728.0): no lat/lon, CRS, or origin, so nothing can be tied to our footprints. Camera grid at fixed altitude + the PanoVGGT training-set citation indicate RENDERED/synthetic imagery, so heights would be a model's, not measurements (violates rule #2). Also: window recesses (~0.2 m) are far below aerial depth noise — windows are an RGB-periodicity signal, not a depth one. |

### Phase 9b — Tier 2 production plate (`render_plate.py`, Qianmen)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Facade pool (req 2) | PolyHaven PBR: `brick_wall_003`, `brick_wall_001`, `brick_moss_001`, `brick_4` × 5 tints = 20 variants | IN USE | Real diffuse+normal+rough maps replaced flat procedural colour — the single biggest fix for "bland". CC0; curl'd to `data/raw/assets/tex/` (gitignored). |
| Texture projection | **BOX** projection on **Object** coords, uv_scale 0.40–0.50 | LOCKED | The box geometry has no UVs; box-projection in object space (metres) maps brick correctly on every face. An earlier UV-less brick node produced vertical "barcode" stripes — the classic generic tell. |
| Street paving | `brick_pavement_02`, uv_scale 0.22 | IN USE | Real paving under raking light gives the ground depth and scale cues. |
| Emission levels | windows 1.6 · lanterns/gate 4.0–4.5 · signs 3.0 | IN USE | **AgX clips hot emission to flat white "paper".** First pass at 6–18 blew out; these values glow warm without clipping. |
| Renderer (final) | Cycles, **64 samples** + denoising, max_bounces 6 | IN USE | 64+denoise is ample for motion and ~⅓ faster than 96 over 300 frames. GI bounce is what makes the brick/lantern light read. |
| **GPU gotcha** | run `src/blender/gpu_prefs.py` before `-a` | LOCKED | `scene.cycles.device='GPU'` is saved in the .blend but the **device selection lives in user preferences**, which headless `-b file.blend -a` does NOT load → silent CPU fallback. Measured: **CPU ~168 s/frame vs GPU (M1 Metal) ~77 s/frame**. |
| Figure scale | BVH `global_scale=0.0675` | LOCKED | Verified: yields 1.76 m armature (brief noted 0.0564 → ~1.42 m). Checked every build via a printed height. |
| Figure pose (still) | frame 60 | IN USE | BVH frame 1 is the calibration **T-pose**; frame 60 is mid-walk. |
| Crowd de-sync | NLA strip started at −5…−90 frames | IN USE | Figures sharing a clip would otherwise march in lockstep; a negative-offset strip puts each at a different gait phase from frame 1. |
| Shot length / seed | 300 frames @ 30 fps (10 s), SEED 7 | IN USE | ≤ mocap clip length so no looping/retargeting; seed keeps crowds + clutter deterministic. |

---

## Phase 10 — 3D bridge (exports + design feedback)

| Parameter | Value | Status | Justification |
|---|---|---|---|
| Export formats | GeoJSON + DXF, per area | IN USE | GeoJSON (with attributes) for Rhino Heron / Blender GIS; DXF (2D polylines) as a CAD fallback. Footprints + buffered streets + extent. |
| Export CRS | metric (EPSG:32650 Beijing, EPSG:2326 HK) | LOCKED | Geometry must be in metres for 3D massing; a `CRS.txt` in each folder states the EPSG (GeoJSON here is NOT WGS-84). |
| Building height default | median of the SAME zone's Overture-tagged heights | IN USE | Only 3–6% of buildings carry a height; rather than invent, the untagged majority gets the data-driven zone median (TKO 82 m, SSP 30 m, BJ-center 7 m). `height_src` flags each as 'overture' or 'zone_median_default'. |
| Height fallback | literature value (`FALLBACK_H`) when <5 tagged | IN USE | Where a zone has too few tagged buildings for a median (e.g. BJ west/east): hutong 6 m, commercial 18 m, etc. — documented, not silent. |
| Design check — resolution | 2 m/px (same as the study) | LOCKED | A design must be measured on the SAME grid as the benchmarks or Dᵦ/Λ aren't comparable. |
| Design check — benchmarks | per-tile medians loaded live from `results/tables/` | LOCKED | Benchmarks always match the study; nothing hard-coded. Headline compare scale = Λ(64 m). |
| Design check — target advice | Λ(64 m) Δ vs target: >+0.15 "too gappy", <−0.15 "too uniform" | PROVISIONAL | A simple, honest tuning signal; the ±0.15 band is a soft tolerance, refine with use. |

---

*Add a row here the moment any new parameter enters the code. An unlogged number is a bug.*
