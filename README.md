# axis-fractal

**Measuring the spatial texture of Beijing's Central Axis — and comparing it to Hong Kong — with fractal dimension and lacunarity.**

> This is an **exploratory, reproducible study**, not a finished proof. Every number here
> comes from real computation on real OpenStreetMap data. Where the method breaks down, or
> the data is incomplete, that is reported openly. All code, parameters, and limitations are
> published in this repository.

## The question

Do the imperial core (the Central Axis / Forbidden City zone) and the vernacular **hutong**
fabric of Beijing share a similar spatial texture — measured by **box-counting fractal
dimension (Dᵦ)** and **gliding-box lacunarity (Λ(r))** — while the modern CBD diverges?

**Secondary (Hong Kong):** can fine-grain texture exist *without* a protected heritage axis?
Hong Kong has no imperial ceremonial spine, so it is the honest stress-test of the Beijing
hypothesis: we compare hyper-dense vernacular fabric (Sham Shui Po / Mong Kok) against
podium-tower megastructure zones — asking whether human-scale grain is a product of
**heritage protection or of morphology**.

Lacunarity is scale-dependent, so we report a **curve Λ(r)**, never a single "magic number."

## Requirements

- **Python 3.11+** (built and tested on 3.12).
- macOS/Linux/Windows. Core libraries: `osmnx`, `geopandas`, `shapely`, `rasterio`,
  `numpy`, `scipy`, `matplotlib`, `scikit-image` (see `requirements.txt`).

## Setup (one time)

```bash
# 1. Get the code
git clone <your-repo-url> axis-fractal
cd axis-fractal

# 2. Create an isolated environment with Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install the exact dependencies
pip install --upgrade pip
pip install -r requirements.txt    # or: pip install -r requirements.lock.txt  (exact pins)
```

## Verify the setup (Phase 0)

Confirms every library imports and that `osmnx` can actually download a small area:

```bash
python src/verify_setup.py
```

You should see version numbers for each library and a short report showing a tiny test
download succeeded. If it prints `PHASE 0 OK`, you're ready for Phase 1.

## How the project runs (one command per phase)

The project is built in **small, inspectable phases**. Each phase has one documented entry
point and writes its outputs to `results/`. (Commands are added here as each phase is built.)

| Phase | What it does | Command |
|---|---|---|
| 0 | Environment + osmnx sanity check | `python src/verify_setup.py` |
| 1 | Download data + completeness audit | *(added in Phase 1)* |
| 2 | Rasterize streets/footprints | *(added in Phase 2)* |
| 3 | Box-counting dimension | *(added in Phase 3)* |
| 4 | Gliding-box lacunarity | *(added in Phase 4)* |
| 5 | Per-tile sampling + statistics | *(added in Phase 5)* |
| 6 | Sensitivity analysis | *(added in Phase 6)* |
| 7 | Figures for paper + portfolio | *(added in Phase 7)* |
| 8 | Hong Kong comparison | *(added in Phase 8)* |

## Repository layout

```
axis-fractal/
  CLAUDE.md         governing directive (how this project must be built)
  README.md         you are here (reproducibility)
  parameters.md     every parameter choice + its justification
  requirements.txt  dependencies (lower bounds)  + requirements.lock.txt (exact pins)
  data/             raw/ (OSM downloads), processed/ (rasters), manual/ (hand-traced tiles)
  src/              acquire, audit, rasterize, boxcount, lacunarity, sampling, viz
  notebooks/        01 audit · 02 beijing pipeline · 03 sensitivity · 04 hong kong
  results/          figures/ · tables/ · results.md (findings log)
```

## Data & coordinates

- OpenStreetMap data is **WGS-84 (EPSG:4326) worldwide, including China.** We do **not**
  apply any GCJ-02 ("Mars coordinate") correction to OSM data — that would corrupt it.
- All measurement happens in a **metric CRS** (UTM 50N / EPSG:32650 for Beijing;
  Hong Kong 1980 Grid / EPSG:2326 for Hong Kong — UTM 50N also covers HK), so buffers and
  tiles are in true metres.

## Integrity & AI assistance

Code in this repository was developed with **AI pair-programming assistance (Claude Code)**.
All analysis decisions, parameter choices, and interpretations are the author's own, and the
author can explain every line and every parameter. AI use is disclosed here and in the paper's
methods/acknowledgments. Using AI tooling is normal; hiding it would not be.
