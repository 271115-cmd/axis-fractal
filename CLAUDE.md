# CLAUDE.md — Fractal Analysis of Beijing's Central Axis (+ Hong Kong comparison)

> **Environment as actually built (Phase 0):** Python **3.12.13** (installed via Homebrew as
> `/opt/homebrew/bin/python3.12`), virtual environment at `.venv/`. The brief below asked for
> "3.11+"; 3.12 satisfies that and has the broadest wheel coverage for the geospatial stack.
> Exact package versions are frozen in `requirements.lock.txt`. See `parameters.md` for the
> full log of every setup decision.
>
> **Comparison city: Hong Kong** (changed from Seoul on 2026-07-14). Hong Kong has *no*
> imperial ceremonial axis — which is the point: it tests whether human-scale texture comes
> from heritage protection or from morphology. See the research question and Phase 8 below.
>
> **Output framing: a documentary VIDEO SERIES** (changed from a research paper on 2026-07-15).
> Same Beijing/Hong Kong research; the pipeline now also emits broadcast-quality visual assets
> (Phase 9) and 3D-bridge exports for Rhino/Grasshopper + Blender (Phase 10). The paper draft in
> `paper/` becomes the narration/script basis, not the primary deliverable.

## Who I am and how to work with me
I am a high school student with minimal coding experience learning Python through this project. This research supports my undergraduate architecture applications, so **I must genuinely understand everything built here**.

Working rules for you (Claude Code):
1. **Teach as you build.** Before writing each module, explain in plain language what it does and why. After writing it, walk me through the key lines. Prefer readable code over clever code.
2. **Never fabricate results.** All numbers must come from actual computation on actual data. If data is missing or a computation fails, say so and log it — do not fill gaps with plausible values.
3. **Log every parameter choice** (buffer widths, resolutions, scale ranges, thresholds) in a `parameters.md` file with a one-line justification each, so I can defend every decision in an interview.
4. **Reproducibility first.** Anyone should be able to clone the repo and regenerate every figure with one command per phase.
5. Build in **small phases**; stop after each phase so I can run it, inspect outputs, and ask questions before continuing.

## Research question
Do the imperial core (Central Axis / Forbidden City zone) and the vernacular hutong fabric of Beijing share a similar spatial texture — measured by fractal dimension (box-counting) and lacunarity (gliding-box) — while the modern CBD diverges? Secondary (Hong Kong): can fine-grain texture exist *without* a protected heritage axis? Compare hyper-dense vernacular fabric (Sham Shui Po / Mong Kok) against podium-tower megastructure zones (Union Square, Central reclamation, or Tseung Kwan O) — testing whether human-scale grain is a product of heritage or of morphology.

## Environment
- Python 3.11+ (built with 3.12), venv, `requirements.txt`
- Core libraries: `osmnx`, `geopandas`, `shapely`, `rasterio`, `numpy`, `scipy`, `matplotlib`, `scikit-image`
- Jupyter notebooks for exploration, importable `.py` modules in `src/` for the pipeline

## Repo structure to create
```
axis-fractal/
  CLAUDE.md            (this file)
  README.md            (reproducibility instructions)
  parameters.md        (every parameter + justification)
  requirements.txt
  data/
    raw/               (downloaded OSM extracts, footprints — gitignored if large)
    processed/         (rasters, tile grids)
    manual/            (hand-digitized tiles, if needed)
  src/
    acquire.py         (data download)
    audit.py           (data completeness checks)
    rasterize.py       (vector → binary raster)
    boxcount.py        (fractal dimension)
    lacunarity.py      (gliding-box)
    sampling.py        (tiling + statistics)
    viz.py             (all figures)
  notebooks/
    01_data_audit.ipynb
    02_beijing_pipeline.ipynb
    03_sensitivity.ipynb
    04_hongkong_comparison.ipynb
  results/
    figures/
    tables/
    results.md         (auto-appended findings with parameters used)
```

## Pipeline phases

### Phase 0 — Setup
Create venv, requirements, repo skeleton, .gitignore. Verify osmnx can download a small test area.

### Phase 1 — Data acquisition & completeness audit (critical)
- Download OSM street network AND building footprints for a Beijing bounding box covering three north–south transects (~1.6 km wide each): West (hutong fabric west of the Axis), Center (the Axis: Drum Tower → Yongdingmen corridor), East (Wangfujing/CBD).
- **Coordinate note:** OSM is WGS-84 worldwide, including China. Do NOT apply GCJ-02 correction to OSM data. GCJ-02 only matters if we ever ingest Amap/Baidu data or overlay Chinese basemap tiles. Document this in parameters.md.
- Project everything to a metric CRS before any measurement (UTM zone 50N works for both Beijing and Hong Kong; alternatively use Hong Kong 1980 Grid / EPSG:2326 for the HK arm).
- **Audit:** compute street segment density and building footprint counts per 500 m tile; render quick-look maps; compare visually against satellite imagery for 3 known hutong tiles. Output an honest assessment: is OSM alley/footprint coverage adequate per zone? If hutong coverage is poor, flag which sample tiles I should hand-digitize (produce a template GeoJSON + instructions for tracing over imagery in QGIS).

### Phase 2 — Rasterization
- Two parallel representations, kept separate throughout: (a) **street network**, buffered by highway class (document widths, e.g., primary 20 m, residential 8 m, alley/pedestrian 4 m — I will refine from field measurements), and (b) **building footprints** where coverage allows.
- Rasterize to binary matrices at a fixed metric resolution (start 2 m/pixel; make it a parameter). 1 = structure, 0 = void. Save GeoTIFFs + PNG quick-looks.

### Phase 3 — Box-counting dimension
- Implement box-counting over box sizes in powers of 2 within a justified range (exclude the smallest scales near pixel size and the largest near image size).
- Fit log N vs log(1/ε) by least squares; **report slope, 95% CI, and R²; save the log-log plot for every computation.** If R² < 0.99 over the chosen range, flag it and show the plot so we choose the linear range explicitly.

### Phase 4 — Gliding-box lacunarity
- Gliding-box over r = 8, 16, 32, 64, 128, 256, 512 px (i.e., 16 m–1 km at 2 m/px). Use memory-safe implementation (integral image / summed-area table, NOT a naive sliding_window_view on a 4096² array — that will exhaust RAM).
- Output the **full Λ(r) curve** per sample, plus normalized lacunarity for cross-density comparison. Never reduce to a single number without also saving the curve.

### Phase 5 — Sampling & statistics
- Tile each transect into non-overlapping 500 m × 500 m tiles; compute Db and Λ(r) per tile.
- Per zone: distributions (boxplots), medians, IQRs. Between zones: Mann-Whitney U tests with effect sizes. State results plainly in results.md — including any that contradict the hypothesis.

### Phase 6 — Sensitivity analysis
Re-run the full pipeline varying: raster resolution (1/2/4 m), buffer widths (±50%), representation (streets vs footprints). Produce a table showing how zone rankings hold or change. This section is as important as the main result.

### Phase 7 — Figures for paper & portfolio
- Binary transect maps, log-log fit plots, Λ(r) curve families by zone, per-tile boxplots, lacunarity heatmap over the study area, and clean labeled versions suitable for a portfolio spread (light background, minimal ink, consistent typography).

### Phase 8 — Hong Kong comparison
Same pipeline on four sample zones: (1) Sham Shui Po / Mong Kok fine-grain tong lau fabric, (2) a podium-tower megastructure zone (Union Square/Kowloon Station, Central reclamation, or Tseung Kwan O), (3) a New Territories walled village tile (e.g., Kat Hing Wai) as the Chinese-vernacular heritage sample, (4) optionally a mixed transitional zone (Wan Chai). Reuse all modules; only acquisition bounding boxes and CRS change. Note in results.md that Hong Kong OSM building-footprint coverage is generally strong — prefer the footprint representation here, and use the HK arm to cross-validate the street-vs-footprint sensitivity found in Phase 6. Document the 2D limitation: verticality is not captured.

### Phase 9 — Video asset generation (for the YouTube series)
The research now feeds a documentary series, so the pipeline must also output broadcast-quality visuals:
- **Box-counting animation:** render frame sequences (PNG, 1920×1080, dark background) of the grid overlay shrinking over the Forbidden City raster, with live box-count numbers — exportable as image sequence for video editing.
- **Gliding-box animation:** the box sweeping across a hutong tile vs. a CBD tile side by side, with a live Λ readout.
- **Map renders:** clean styled figure-ground maps of each transect/tile (matplotlib or QGIS-ready exports), high-res, with data attribution burned into a corner of every frame (accurately: "© OpenStreetMap contributors · Overture Maps" — streets are OSM, footprints are Overture).
- **Chart templates:** consistent typography/color across all result charts (define once in viz.py) so every episode's graphics look like one series.
- All animation scripts live in `src/animate.py`; frames output to `results/video_assets/<episode>/`. Keep frames deterministic and re-renderable — episode edits will demand regenerations.

### Phase 9b — Blender rendered animations (priority asset batch)
Blender is connected via the BlenderMCP addon (socket server on localhost:9876). **Workflow rule:** use the live MCP connection for interactive scene setup and previews, but commit every final animation as a standalone `bpy` script in `src/blender/` runnable headless (`blender --background --python <script>.py`) — renders must be reproducible from the repo like everything else. Log camera paths, seeds, and palette in parameters.md.

**Look:** stylized, not photoreal. White/clay extruded fabric on a dark ground plane, data overlays in the series palette, EEVEE renderer for speed. One consistent look across all shots.

Build these, in order:
1. **The Descent/Ascent ("The Zoom" 3D leg):** one continuous camera move from street level up over the extruded Zone B fabric, easing into a top-down plan view that match-frames the figure-ground raster (and the reverse). Deliver at 1080p60, ~8 s each direction. This template is reused in every episode — build it first and parameterize the target tile.
2. **Transect orbits:** slow 20 s orbit of each extruded transect (Beijing A/B/C, HK zones) at a consistent height and speed.
3. **3D grid descent:** the box-counting grid rendered as a translucent 3D lattice lowering onto the Forbidden City fabric, boxes lighting up as they register structure.
4. **Gliding-box in 3D:** a glowing box sweeping across hutong vs. podium fabric side by side, gap encounters visibly registering.
5. **Fabric comparison dolly:** one continuous lateral dolly that crosses from Zone A fabric into Zone C — the grain change reads instantly, no narration needed.
6. **Populated match-cut plates (high-effort signature shots):** stylized street scenes with crowds of clay-figure pedestrians driven by real CMU mocap walk cycles (mocap.cs.cmu.edu — free to copy/modify/redistribute; credit "Motion data from mocap.cs.cmu.edu" in video descriptions). Built from `src/blender/render_anim.py` (template in repo): capsule-limb figures bone-parented to imported BVH armatures (stylized on purpose — realistic humans risk uncanny valley and break the cut), deterministic crowd seed, shot length ≤ clip length so no looping/retargeting is needed. **Match-cut protocol:** the real plate is shot on site FIRST; log camera position, height (~1.6 m eye level), and focal length (or solve from a still with fSpy) and copy into the script's camera config. First target: Qianmen/Dashilan street. Two-step render flow: `blender -b -P render_anim.py` to build and save the .blend, then `blender -b output/<shot>.blend -a` for the long headless render.
7. **(Later, A5)** proposal turntable + eye-level walkthrough on the real site context.

Import geometry from the Phase 10 GeoJSON/DXF exports (meters). Frames to `results/video_assets/blender/<shot>/`. NOTE (project-specific): our exports live in `data/exports/`; Blender needs a LOCAL-ORIGIN metres GeoJSON (absolute UTM coords are too far from origin) — `src/to_rhino.py`/a small exporter provides the cropped, offset geometry.

### Phase 10 — 3D bridge (Rhino/Grasshopper + Blender)
The user has live MCP plugins for Rhino/Grasshopper and Blender. The pipeline must export geometry they can ingest:
- **Footprint exports:** per-transect and per-tile building footprints as GeoJSON (and DXF) in the metric CRS, with height attributes where OSM/Overture provides them (default heights by zone where absent — document the assumption).
- **Street/void exports:** buffered street polygons and the binary raster extents as vectors, for figure-ground modeling.
- **Design-feedback utility:** a small CLI (`src/check_design.py`) that takes any plan image or exported curve set from Grasshopper, rasterizes it at the standard resolution, and returns its Db and Λ(r) curve against the measured zone benchmarks — enabling a live loop: GH design → export → check → re-tune toward target Λ.
- Keep all exports deterministic and documented in parameters.md so 3D scenes can be rebuilt.

## Explicit anti-goals
- No invented or interpolated metrics, ever.
- No single-number lacunarity claims without the underlying curve.
- No comparisons to Washington D.C. / Paris unless Phases 1–7 are complete and I ask for it.
- Don't optimize prematurely; correctness and legibility first.

## Definition of done (per phase)
Code runs end-to-end from raw data via one documented command; outputs land in results/; parameters.md updated; and I can explain the phase back to you in my own words (quiz me briefly at the end of each phase).
