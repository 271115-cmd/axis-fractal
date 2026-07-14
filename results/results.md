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

## Phase 1 — completeness audit (2026-07-14)

Tiled the three transects into 288 tiles of 500 m. Per-tile metrics in `results/tables/phase1_audit_tiles.csv`; maps in `results/figures/phase1_audit_*`.

| zone | tiles | median coverage | median street km/km² | median bldg count | tiles < 10% |
|---|--:|--:|--:|--:|--:|
| center | 90 | 7.5% | 15.0 | 22 | 52 |
| east | 108 | 6.1% | 7.5 | 18 | 69 |
| west | 90 | 9.9% | 14.1 | 14 | 46 |

**Ground-truth check:** OSM overlaid on Esri satellite imagery at three known hutong spots (`phase1_audit_groundtruth_hutong.png`).
**Flagged:** 167 tiles below 10% built coverage. These are *candidates to inspect*, not confirmed gaps — many will be genuine voids (lakes, plazas, the Forbidden City grounds). Template for tracing real gaps written to `data/manual/` if any were flagged.

**Preliminary read (to be confirmed by eye against the imagery):** compare the median coverage across zones and check whether the hutong ground-truth tiles look fully mapped. No fractal claims until this is settled.

### Phase 1 audit — CONFIRMED VERDICT (after viewing the satellite overlay)

**Streets: reliable.** The OSM street network is well-mapped and spatially coherent across
all three transects (median 7.5–15 km/km²; the Center's zero tiles are the real Forbidden
City void). The street representation is trustworthy for Beijing.

**Building footprints: severely incomplete for hutong fabric.** The ground-truth overlay is
decisive — at dense, unambiguously built hutong sites OSM footprints capture only a fraction
of what the imagery shows:

| ground-truth site | OSM says built | imagery shows | verdict |
|---|--:|---|---|
| Xisi (west) | 34% | ~60–70% | partial — big blocks yes, fine houses missing |
| Shichahai (center) | 5% | dense fabric round the lake | **footprints almost entirely absent** |
| Nanluoguxiang (east) | 9% | famous ~60–70% hutong grid | **most courtyard houses unmapped** |

**Therefore:** the *footprint* representation cannot be trusted for Beijing as-is. The 167/288
"low-coverage" flag OVER-selects — it cannot tell a genuine void (lake, plaza, Forbidden City)
from a data gap, so it is a screening aid, not a gap list. The satellite overlay is the real
evidence.

**Consequences for the pipeline (honest, and consistent with the brief keeping two
representations):**
- Lead the Beijing analysis with the **street network** (Phases 2–5); it is complete enough.
- For Beijing **footprints**, choose a mitigation before trusting them: (a) substitute an
  external footprint dataset that covers China, or (b) hand-digitize a few representative
  hutong tiles (template ready in `data/manual/`), or (c) restrict footprint claims to
  verified tiles only.
- **Hong Kong (Phase 8)** OSM footprints are reportedly strong — so HK is where the
  street-vs-footprint cross-check is valid. This makes the HK arm more useful, not less.

No fractal dimension or lacunarity numbers yet — that begins in Phase 2, on the street
representation first.
