# axis-fractal

**Measuring the spatial texture of Beijing's Central Axis — and comparing it to Hong Kong — with fractal dimension and lacunarity.**

> An **exploratory, reproducible study**, not a finished proof. Every number here comes from
> real computation on real open data. Where the method breaks down, or the data is incomplete,
> that is reported openly. All code, parameters, and limitations are in this repository, and
> the analysis was built in small, inspectable phases (see `CLAUDE.md`).

---

## What it found (honest summary)

1. **Box-counting fractal dimension (Dᵦ) does not tell urban fabrics apart.** Hutong, imperial
   Axis, commercial Beijing, Hong Kong tong-lau and podium towers all sit near **Dᵦ ≈ 1.6**.
   A single dimension is too blunt an instrument — reporting "they converge!" would be dishonest.
2. **Lacunarity Λ(r) — the measure of *gappiness* — is the real discriminator.**
3. **Beijing:** the differences are *weak*. At the neighbourhood scale the **Axis is slightly
   the gappiest** (the Forbidden City's monumental blocks + voids) and the **hutong the most
   uniform** — but the effect is small and does not survive strict multiple-comparison correction.
   The tidy "hutong ≈ Axis, modern CBD ruptures" story is **not** supported.
4. **Hong Kong:** the same contrast is *dramatic*. Fine tong-lau (Sham Shui Po) Λ(64 m) ≈ **1.54**
   vs. podium-megastructure (Tseung Kwan O) ≈ **2.92** — **p = 0.001, large effect (r = 0.66)**.
5. **The cross-city answer.** Fine vernacular fabric is similar across both cities (HK Sham Shui
   Po ≈ Beijing hutong). Hong Kong has **no protected ceremonial axis**, yet its fine grain
   persists — while its megastructures are far coarser than anything in old Beijing. So
   human-scale grain is a product of **morphology, not heritage protection**.

The robust cross-city reading is the **comparison of contrasts** (the fine-vs-coarse *gap* is far
larger in Hong Kong than Beijing), **not** absolute lacunarity levels between cities, which are
confounded by terrain and data. See `results/results.md` for every number and `parameters.md`
for every choice.

## The question

Do the imperial core (Central Axis / Forbidden City) and the vernacular **hutong** fabric of
Beijing share a spatial texture — via **box-counting dimension (Dᵦ)** and **gliding-box
lacunarity (Λ(r))** — while the modern CBD diverges? **Secondary (Hong Kong):** can fine-grain
texture exist *without* a protected heritage axis? Lacunarity is scale-dependent, so we report a
**curve Λ(r)**, never a single "magic number."

---

## Requirements

- **Python 3.11+** (built and tested on **3.12**). macOS/Linux/Windows.
- Core libraries: `osmnx`, `geopandas`, `shapely`, `rasterio`, `numpy`, `scipy`, `matplotlib`,
  `scikit-image`, `contextily`, plus the `overturemaps` CLI (all in `requirements.txt`).

## Setup (once)

```bash
git clone <your-repo-url> axis-fractal && cd axis-fractal
make setup          # creates .venv (Python 3.12) and installs requirements.txt
# equivalently, by hand:
#   python3.12 -m venv .venv && source .venv/bin/activate
#   pip install --upgrade pip && pip install -r requirements.txt
```

`requirements.lock.txt` holds exact version pins for a byte-identical environment.

## Reproduce it — one command per phase

The whole study regenerates from these commands (a `Makefile` wraps each phase). Data phases
(**1** and **8**) need internet; every other phase runs offline on the saved data.

```bash
make verify     # Phase 0: check the environment + that osmnx can download
make all        # Phases 1–8 end to end
# ...or one phase at a time:
make phase3
```

| Phase | Command | What it does | Key outputs |
|---|---|---|---|
| 0 | `make verify` | env + osmnx sanity check | console report |
| 1 | `make phase1` | download OSM, audit coverage, swap in Overture footprints, re-audit | `phase1_*` figures/tables; `data/raw/` |
| 2 | `make phase2` | rasterize streets + footprints to 2 m/px binary GeoTIFFs | `data/processed/*.tif`, `phase2_rasters_overview.png` |
| 3 | `make phase3` | box-counting dimension Dᵦ (+95% CI, R², a log-log plot each) | `phase3_boxcount_*` |
| 4 | `make phase4` | gliding-box lacunarity Λ(r) via summed-area table | `phase4_lacunarity_*` |
| 5 | `make phase5` | per-500 m-tile Dᵦ/Λ(r), distributions, Mann-Whitney | `phase5_*` |
| 6 | `make phase6` | sensitivity: resolution 1/2/4 m, buffers ±50%, streets vs footprints | `phase6_sensitivity.*` |
| 7 | `make phase7` | portfolio figures (colourblind-safe, minimal ink) | `phase7_*` |
| 8 | `make phase8` | Hong Kong acquisition + measurement + cross-city comparison | `phase8_*` |

**Note on `results/results.md`:** it is a *curated findings log* — the committed copy is the
canonical record. Figures (`.png`) and tables (`.csv`) overwrite deterministically on re-run;
`results.md` is appended to, so re-running the pipeline on top of the committed file will add
duplicate sections. Treat the committed `results.md` as the record and the figures/tables as the
regenerable outputs.

## Repository layout

```
axis-fractal/
  CLAUDE.md          governing directive (how this project must be built)
  README.md          you are here
  parameters.md      every parameter choice + its one-line justification
  Makefile           one target per phase
  requirements.txt   dependencies (+ requirements.lock.txt = exact pins)
  data/
    raw/             OSM + Overture downloads (gitignored — regenerate with make phase1/phase8)
    processed/       binary GeoTIFF rasters (gitignored — make phase2)
    manual/          QGIS hand-digitizing template for flagged tiles
  src/
    config.py        single source of truth: paths, CRS, study boxes, all parameters
    acquire.py       Phase 1  OSM streets + footprints (Beijing)
    audit.py         Phase 1  completeness audit + satellite ground-truth
    acquire_footprints.py  Phase 1  Overture footprints (fixes Beijing's sparse OSM buildings)
    audit_footprints.py    Phase 1  OSM-vs-Overture coverage check
    rasterize.py     Phase 2  vector -> binary raster
    boxcount.py      Phase 3  fractal dimension
    lacunarity.py    Phase 4  gliding-box lacunarity
    sampling.py      Phase 5  per-tile metrics + statistics
    sensitivity.py   Phase 6  robustness sweep
    viz.py           Phase 7  portfolio figures
    acquire_hk.py    Phase 8  Hong Kong acquisition + coverage check
    compare_hk.py    Phase 8  Hong Kong measurement + cross-city comparison
  notebooks/         01 audit · 02 beijing pipeline · 03 sensitivity · 04 hong kong
  results/           figures/ · tables/ · results.md (findings log)
```

## Data, coordinates & sources

- **Streets:** OpenStreetMap via `osmnx` (© OpenStreetMap contributors, ODbL).
- **Building footprints:** Overture Maps buildings — chosen because OSM footprints are severely
  incomplete for Beijing's hutongs (see the Phase 1 audit). Overture aggregates open sources
  including a China rooftop dataset (Zenodo `10.5281/zenodo.8174931`). The **same** source is
  used for both cities so the comparison is fair.
- **Satellite imagery (visual ground-truth only, not measured):** Esri World Imagery.
- **Coordinates:** OSM is **WGS-84 (EPSG:4326) worldwide, including China** — we apply **no
  GCJ-02 correction** to OSM (that would corrupt it; GCJ-02 only matters for Chinese-provider
  basemaps). All measurement is done in a **metric CRS**: **EPSG:32650** (UTM 50N) for Beijing,
  **EPSG:2326** (Hong Kong 1980 Grid) for Hong Kong.

## Limitations (read these)

- **2D plan analysis only.** Building *height* is not captured — a real limitation for Hong Kong,
  which is intensely vertical. The footprint/street plan texture we measure is valid; verticality
  is out of scope.
- **Cross-city absolute lacunarity is confounded** (terrain, water, reclamation). Trust the
  *contrast-of-contrasts*, not absolute levels between cities.
- **Small samples** for some Hong Kong sites (Tseung Kwan O n≈14; Kat Hing Wai walled village is a
  qualitative reference only, not a distribution).
- **Multiple comparisons:** many pairwise tests were run; nominal p<0.05 results are reported as
  *suggestive* and weighted by effect size, not treated as proof.
- **Footprints are machine-derived** (Overture/ML rooftops) — a big improvement over empty OSM,
  but not survey-grade.

## Integrity & AI assistance

Code in this repository was developed with **AI pair-programming assistance (Claude Code)**. All
analysis decisions, parameter choices, and interpretations are the author's own, and the author
can explain every line and every parameter. Nothing in `results/results.md` is written by hand
from imagination — if a number is there, a script computed it from real data. AI use is disclosed
here and in the paper's methods/acknowledgments; using AI tooling is normal, hiding it would not be.
