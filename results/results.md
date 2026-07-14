# results.md — findings log

Every measurement this project produces is appended here, **with the parameters that
produced it**, exactly as computed. Results that contradict the hypothesis are recorded
the same as any other. Nothing is written here by hand from imagination — if a number is
in this file, a script put it here from real data.

---

## Phase 0 complete (2026-07-14)

Environment set up; `osmnx` verified able to download data. No measurements yet.

## Phase 1 — data acquired (2026-07-14)  *(audit verdict still pending)*

Downloaded OSM streets + building footprints for the three Beijing transects and projected
to EPSG:32650. Counts below are **real** (from `src/acquire.py`), saved to
`data/raw/beijing_<zone>_{streets,buildings}.gpkg` and
`results/tables/phase1_acquire_summary.csv`. Overview map:
`results/figures/phase1_transects_overview.png`.

| zone   | street segments (undirected) | street length (km) | building footprints | roof area (km²) |
|--------|------:|------:|------:|------:|
| west   | 3826 | 277.8 | 3536 | 2.229 |
| center | 4492 | 295.3 | 4607 | 1.949 |
| east   | 3778 | 265.2 | 2722 | 2.234 |

**Method note (integrity):** street length is measured on the *undirected* graph. An earlier
run counted the directed graph and reported ~2× the length (466 km for west vs. the correct
277.8 km) because two-way streets are stored as two directed edges. Fixed in `acquire.py`.

**Not yet a finding.** Whether this OSM coverage is *adequate* (especially hutong alleys and
footprints) is the job of the Phase 1 audit (`audit.py`), which is the next step. Early
observation only: the East (commercial) zone has the fewest, largest footprints (2722 covering
2.23 km²) while Center has the most, smaller ones (4607 covering 1.95 km²) — consistent with
coarser vs. finer grain, but this must be quantified per-tile before any claim.

<!--
  Template for future entries (filled by the pipeline, not by hand):

  ## <Phase / analysis> — <date>
  - Zone / tile: ...
  - Parameters: resolution=__ m/px, buffers=__, box-range=__, r=__  (must match parameters.md)
  - Result: D_b = __ (95% CI __–__, R² = __);  Λ(r) curve saved to results/figures/____.png
  - Notes / caveats: ...
-->
