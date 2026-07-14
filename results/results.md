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

### Footprint fix — Overture vs OSM (2026-07-14)

Applied the Overture footprint dataset and re-ran the coverage audit. Per-zone median 500 m-tile built fraction:

| zone | OSM footprints | Overture footprints | OSM median cov | Overture median cov |
|---|--:|--:|--:|--:|
| west | 3536 | 18996 | 9.9% | 20.4% |
| center | 4607 | 20027 | 7.5% | 20.0% |
| east | 2722 | 17494 | 6.1% | 14.6% |

Before/after overlay: `results/figures/phase1_footprint_osm_vs_overture.png`. Overture (source: Zenodo China rooftop dataset via Overture) captures the fine-grain hutong courtyard houses OSM missed. Beijing footprint representation now usable — still to be treated as a separate representation from streets, per the brief.


## Phase 2 — rasterization (2026-07-14)

Built two separate binary rasters per zone at 2 m/pixel (streets buffered by road class;
Overture footprints painted directly). 1 = structure, 0 = void. GeoTIFFs in
`data/processed/`; overview `results/figures/phase2_rasters_overview.png`.

| zone | grid (px) | streets: % pixels built | footprints: % pixels built |
|---|---|--:|--:|
| west   | 830×4224 | 14.3% | 25.7% |
| center | 833×4224 | 12.6% | 23.4% |
| east   | 828×4224 | 13.8% | 24.3% |

The two representations are visibly different textures (streets = sparse/linear;
footprints = denser/areal), and the Center footprints raster clearly shows the Forbidden
City's coarse monumental blocks amid fine hutong grain. These 0/1 grids are the exact input
to box-counting (Phase 3) and lacunarity (Phase 4). Still no fractal numbers — that is next.

## Phase 3 — box-counting dimension (2026-07-14)

Box sizes [1, 2, 4, 8, 16, 32, 64, 128, 256, 512] px; slope fitted over 4-128 px (= 8-256 m). Every log-log plot saved to `results/figures/phase3_boxcount_*`.

| zone | representation | Dᵦ | 95% CI | R² |
|---|---|--:|---|--:|
| west | streets | 1.546 | 1.432–1.661 | 0.9972 |
| west | footprints | 1.767 | 1.667–1.867 | 0.9983 |
| center | streets | 1.559 | 1.426–1.691 | 0.9962 |
| center | footprints | 1.746 | 1.664–1.827 | 0.9989 |
| east | streets | 1.538 | 1.415–1.661 | 0.9967 |
| east | footprints | 1.752 | 1.658–1.846 | 0.9985 |

**R² check:** all fits ≥ 0.99.
These are whole-transect dimensions (one per zone × representation). The statistically meaningful per-tile distributions + zone comparison come in Phase 5.

## Phase 4 — gliding-box lacunarity (2026-07-14)

Λ(r) for r = [8, 16, 32, 64, 128, 256, 512] px (16 m–1 km) via summed-area table. Full curves in `results/tables/phase4_lacunarity.csv`; plot `results/figures/phase4_lacunarity_curves.png`. Endpoints below (Λ(8)=fine-scale gappiness, Λ(512)=district-scale):

| zone | rep | density p | Λ(8) | Λ(512) |
|---|---|--:|--:|--:|
| center | footprints | 0.234 | 2.424 | 1.034 |
| center | streets | 0.126 | 4.208 | 1.047 |
| east | footprints | 0.243 | 2.416 | 1.118 |
| east | streets | 0.138 | 4.408 | 1.062 |
| west | footprints | 0.257 | 2.251 | 1.025 |
| west | streets | 0.143 | 4.410 | 1.041 |

Reminder: lacunarity is scale-dependent — the CURVE is the result, not any single value (brief anti-goal). Per-tile Λ(r) distributions + the zone comparison come in Phase 5.

## Phase 5 — per-tile distributions + statistics (2026-07-14)

Each transect cut into non-overlapping 500 m tiles (250×250 px). Dᵦ (fit 2-32 px) and Λ(r) computed per tile; tiles below 2% built excluded as voids. Full data in `results/tables/phase5_tile_metrics.csv`; boxplots `results/figures/phase5_tile_distributions.png`.

**Tiles used per zone (after excluding voids):** footprints/center=48, footprints/east=46, footprints/west=48, streets/center=48, streets/east=48, streets/west=48.

**Per-zone medians:**

| rep | metric | west | center | east |
|---|---|--:|--:|--:|
| streets | Db | 1.431 | 1.407 | 1.433 |
| footprints | Db | 1.614 | 1.604 | 1.618 |
| streets | lam8 | 4.006 | 3.866 | 3.799 |
| footprints | lam8 | 2.018 | 2.238 | 2.157 |
| streets | lam16 | 2.817 | 2.635 | 2.698 |
| footprints | lam16 | 1.522 | 1.750 | 1.639 |
| streets | lam32 | 2.079 | 1.812 | 1.875 |
| footprints | lam32 | 1.211 | 1.382 | 1.282 |

**Significant pairwise differences (Mann-Whitney, p<0.05):**

| rep | metric | pair | medians | p | effect (r) |
|---|---|---|---|--:|---|
| footprints | lam16 | west vs center | 1.522 vs 1.75 | 0.0351 | 0.25 (small) |
| streets | lam32 | west vs center | 2.079 vs 1.812 | 0.042 | -0.241 (small) |
| footprints | lam32 | west vs center | 1.211 vs 1.382 | 0.0076 | 0.317 (medium) |

Ran 24 pairwise tests across 4 metrics × 2 representations × 3 pairs — treat single p-values with multiple-comparison caution (a Bonferroni-style threshold would be ~0.05/24 ≈ 0.0021). Effect sizes matter as much as significance. Interpretation written up honestly, including non-differences.

## Phase 6 — sensitivity analysis (2026-07-14)

One knob at a time around the 2 m / ×1.0 baseline (resolution 1/2/4 m, street buffers ×0.5/×1.0/×1.5, both representations). Scales held fixed in METRES so resolutions compare fairly. Full table `results/tables/phase6_sensitivity.csv`; figure `results/figures/phase6_sensitivity.png`.

| config | rep | Dᵦ W/C/E | Λ(64 m) W/C/E | W-vs-C Λ p | effect | dir |
|---|---|---|---|--:|--:|---|
| baseline | streets | 1.431/1.407/1.433 | 2.079/1.812/1.875 | 0.042 | -0.241 | W>=C |
| res 1 m | streets | 1.465/1.445/1.459 | 2.073/1.811/1.873 | 0.0384 | -0.246 | W>=C |
| res 4 m | streets | 1.355/1.319/1.344 | 2.082/1.817/1.887 | 0.0582 | -0.225 | W>=C |
| buffer ×0.5 | streets | 1.322/1.276/1.315 | 2.196/1.962/2.044 | 0.0451 | -0.24 | W>=C |
| buffer ×1.5 | streets | 1.516/1.5/1.521 | 1.86/1.673/1.725 | 0.0912 | -0.201 | W>=C |
| baseline | footprints | 1.614/1.604/1.618 | 1.211/1.382/1.282 | 0.0076 | 0.317 | W<C |
| res 1 m | footprints | 1.65/1.638/1.642 | 1.21/1.386/1.28 | 0.0081 | 0.314 | W<C |
| res 4 m | footprints | 1.587/1.575/1.593 | 1.223/1.399/1.284 | 0.0079 | 0.315 | W<C |

**Robustness of Phase 5's signal (footprints West < Center in Λ(64 m)):** direction held in ALL footprint configs; nominally significant (p<0.05) in 3 of 3. Dᵦ remained indistinguishable across zones in every configuration. Interpretation written up honestly in the response.

## Phase 7 — portfolio figures (2026-07-14)

Clean, colourblind-safe (Okabe-Ito, validated), minimal-ink versions of the key results in `results/figures/phase7_*`: transect maps, one log-log fit, the footprint Λ(r) family, per-tile Λ(64 m) boxplots, and a study-area lacunarity heatmap. Same numbers as the diagnostic figures — restyled for a reader, telling the honest 'Center (Axis) gappiest, West (hutong) most uniform' story.

## Phase 8 — Hong Kong data acquired + coverage check (2026-07-14)

Three district sample boxes (NOT transects — HK has no axis): Sham Shui Po tong-lau, Tseung Kwan O podium towers, Kat Hing Wai walled village. Streets = OSM, footprints = Overture (same sources as Beijing), projected to EPSG:2326. Real counts in `results/tables/phase8_hk_acquire_summary.csv`; overview `results/figures/phase8_hk_sites_overview.png`; satellite ground-truth `results/figures/phase8_hk_groundtruth.png`.

| site | streets (km) | footprints | roof km² | box km² | % built |
|---|--:|--:|--:|--:|--:|
| shamshuipo | 394.6 | 5841 | 2.368 | 7.53 | 31.4 |
| tseungkwano | 166.1 | 917 | 0.866 | 5.02 | 17.2 |
| kathingwai | 91.2 | 3567 | 0.413 | 5.63 | 7.3 |

Caveat: Kat Hing Wai is a ~1 ha walled village; its box is mostly village+field, so it yields few dense tiles — a small-sample qualitative reference, not a full distribution.
