# axis-fractal — reproducibility runner.  One target per phase.
#
# Quick start:
#   make setup      # once: create .venv (Python 3.12) and install dependencies
#   make all        # run the whole Beijing + Hong Kong pipeline, phases 1-8
#   make phase3     # ...or run a single phase
#
# Notes:
#   * Data phases (phase1, phase8) need INTERNET — they download from OpenStreetMap
#     and Overture Maps. Every other phase runs offline on the saved data.
#   * Override the interpreter if your venv is elsewhere:  make PYTHON=python3 phase3
#   * Windows users without `make`: run the same commands from the table in README.md.

PYTHON ?= ./.venv/bin/python

.PHONY: help setup verify phase1 phase2 phase3 phase4 phase5 phase6 phase7 phase8 all clean

help:
	@echo "Targets:"
	@echo "  setup      create .venv + install requirements"
	@echo "  verify     Phase 0 — check env + osmnx download works"
	@echo "  phase1..8  run one phase (see README for what each produces)"
	@echo "  phase9     render video-asset frames to results/video_assets/"
	@echo "  all        phase1 -> phase8"
	@echo "  clean      delete generated rasters/figures/tables (keeps raw downloads)"

setup:
	python3.12 -m venv .venv
	./.venv/bin/python -m pip install --upgrade pip
	./.venv/bin/python -m pip install -r requirements.txt

# Phase 0 — environment + osmnx sanity check
verify:
	$(PYTHON) src/verify_setup.py

# Phase 1 — download OSM, audit coverage, swap in Overture footprints, re-audit (needs internet)
phase1:
	$(PYTHON) src/acquire.py
	$(PYTHON) src/audit.py
	$(PYTHON) src/acquire_footprints.py
	$(PYTHON) src/audit_footprints.py

# Phase 2 — rasterize streets + footprints to 2 m/px binary GeoTIFFs
phase2:
	$(PYTHON) src/rasterize.py

# Phase 3 — box-counting fractal dimension
phase3:
	$(PYTHON) src/boxcount.py

# Phase 4 — gliding-box lacunarity
phase4:
	$(PYTHON) src/lacunarity.py

# Phase 5 — per-tile metrics + zone statistics
phase5:
	$(PYTHON) src/sampling.py

# Phase 6 — sensitivity analysis
phase6:
	$(PYTHON) src/sensitivity.py

# Phase 7 — portfolio figures
phase7:
	$(PYTHON) src/viz.py

# Phase 8 — Hong Kong acquisition + measurement/comparison (needs internet for acquire_hk)
phase8:
	$(PYTHON) src/acquire_hk.py
	$(PYTHON) src/compare_hk.py

# Phase 9 — render video-asset frame sequences (offline; needs data/processed rasters)
phase9:
	$(PYTHON) src/animate.py

all: phase1 phase2 phase3 phase4 phase5 phase6 phase7 phase8

clean:
	rm -f data/processed/*.tif results/figures/*.png results/tables/*.csv
	@echo "Cleaned generated rasters, figures, tables. Raw downloads in data/raw/ kept."
