# The Axis and the Tower
### Measuring fractal dimension and lacunarity of human-scale fabric in Beijing and Hong Kong

**Author:** [YOUR NAME] · **Draft:** {fill date} · Independent research

> **How to use this file.** This is an *honest scaffold*, not a finished paper. Every number
> below was computed by the code in this repository and is traceable to `results/results.md`
> and `results/tables/`. Blocks marked `[AUTHOR: …]` are where **you** must add your own voice,
> motivation, or judgement — do not submit them as-is. Every citation is marked **⚠ VERIFY** and
> must be checked on Google Scholar before use (the project's credibility depends on this).
> You should be able to explain every sentence and every parameter out loud.

---

## Abstract

Two claims are commonly made about historic urban fabric: that vernacular and monumental cores
share a "grammar," and that modern development ruptures it. I test these quantitatively by
measuring the **box-counting fractal dimension (Dᵦ)** and **gliding-box lacunarity (Λ(r))** of
building-footprint and street-network fabric along three transects across Beijing's Central Axis
(hutong / imperial Axis / commercial), and across three district types in Hong Kong (fine tong-lau
/ podium-tower megastructure / walled-village heritage). The central finding is negative and then
positive: **fractal dimension does not distinguish these fabrics** (all Dᵦ ≈ 1.6), but
**lacunarity does**. In Beijing the lacunarity differences are weak and do not survive strict
correction; in Hong Kong they are large — fine tong-lau (Sham Shui Po) is far more texturally
uniform than podium megastructure (Tseung Kwan O) (Λ(64 m) 1.54 vs 2.92; Mann–Whitney p = 0.001,
rank-biserial r = 0.66). Because Hong Kong protects no ceremonial axis yet retains fine grain, the
result suggests human-scale texture is a product of **morphology, not heritage protection**.

> [AUTHOR: tighten the abstract to ~150 words in your own voice once the rest is settled.]

---

## 1. Introduction

[AUTHOR: 2–4 paragraphs in your own words. Why *you* care about the Central Axis; the UNESCO 2024
inscription hook; what first made you wonder whether the hutongs and the imperial core "feel" alike.
Keep it personal and specific — admissions readers distrust generic openings.]

The intuition that cities have a measurable "texture" is old. Jacobs argued that fine-grained,
mixed fabric supports urban life ⚠ VERIFY (Jacobs, 1961); Lynch that legible cities are built from
repeated elements at multiple scales ⚠ VERIFY (Lynch, 1960); Alexander that living structure recurs
across scales ⚠ VERIFY (Alexander). Mandelbrot formalised scale-invariance as fractal geometry
⚠ VERIFY (Mandelbrot, 1982), and Batty & Longley applied it to cities ⚠ VERIFY (Batty & Longley,
1994). This project asks a narrow, testable version of the question:

**Do the imperial core and the vernacular hutong fabric of Beijing share a spatial texture — while
the modern city diverges? And can fine-grain texture exist *without* a protected heritage axis, as
in Hong Kong?**

I frame this as **measurement, not proof**. Lacunarity is scale-dependent, so I report a *curve*
Λ(r), never a single number, and I report results that contradict the hypothesis as plainly as
those that support it.

## 2. Data and methods

All code, parameters, and outputs are in the repository; each phase regenerates with one command
(`make phaseN`). Parameters and their justifications are logged in `parameters.md`.

**2.1 Study areas.** Beijing: three ~1.6 km-wide north–south transects spanning the Drum Tower →
Yongdingmen corridor — **West** (hutong fabric), **Center** (the Central Axis / Forbidden City),
**East** (Wangfujing / commercial). Hong Kong, which has *no* ceremonial axis, is sampled instead
as four compact districts of distinct type: **Sham Shui Po** (fine tong-lau), **Tseung Kwan O**
(podium-tower new town), **Kat Hing Wai** (New Territories walled village), and **Wan Chai** (mixed
transitional). Using districts rather than transects is the honest consequence of comparing a
planned imperial city to an unplanned port.

**2.2 Data and coordinates.** Street networks are from OpenStreetMap (© OpenStreetMap contributors,
ODbL). Building footprints are from **Overture Maps** — chosen after an audit (§2.3) showed OSM
footprints are severely incomplete for Beijing's hutongs; the same source is used for both cities
for fairness. OSM is WGS-84 worldwide, including China, so **no GCJ-02 correction** is applied.
All measurement is performed in a metric CRS: EPSG:32650 (UTM 50N) for Beijing, EPSG:2326 (Hong
Kong 1980 Grid) for Hong Kong.

**2.3 A data-completeness audit (and a correction).** Before measuring, I tiled each Beijing
transect into 500 m cells and compared OSM coverage against Esri satellite imagery at three known
hutong sites. OSM footprints captured only a fraction of the built fabric — Shichahai 5 %,
Nanluoguxiang 9 % of tile area, where imagery shows ~60–70 %. OSM *streets*, by contrast, were
complete. I therefore replaced Beijing footprints with Overture's (which aggregates a China
rooftop dataset, Zenodo 10.5281/zenodo.8174931), raising median tile coverage from ~8 % to ~20 %
and restoring the missing hutong houses (see `results/figures/phase1_footprint_osm_vs_overture.png`).
Hong Kong's Overture coverage was verified excellent against imagery (Sham Shui Po 52 %, Tseung
Kwan O 47 % built in ground-truth windows), so the street-vs-footprint comparison is valid there.

> [AUTHOR: this audit is one of your strongest talking points — it is direct evidence you did real
> work and caught a real problem. Consider expanding it with the before/after figure.]

**2.4 Rasterization.** Each representation is rasterized to a binary image at **2 m/pixel**
(1 = structure, 0 = void). Streets are buffered to real width by highway class (primary 20 m,
residential 8 m, service/alley 4 m; full table in `config.STREET_WIDTHS`); footprints are painted
directly. Streets and footprints are kept as **separate** representations throughout.

**2.5 Fractal dimension.** Box-counting counts occupied boxes N(ε) for ε = 2ᵏ pixels and fits
log N vs log(1/ε) by least squares over a justified linear range (4–128 px for whole transects;
2–32 px per tile), reporting the slope Dᵦ with a 95 % confidence interval and R². A log-log plot is
saved for every computation; all whole-transect fits had R² ≥ 0.996.

**2.6 Lacunarity.** Gliding-box lacunarity Λ(r) = ⟨m²⟩/⟨m⟩² is computed for r = 8–512 px
(16 m–1 km) using a summed-area table (memory-safe; a naïve sliding window would exhaust RAM). The
full Λ(r) curve is reported per sample.

**2.7 Sampling and statistics.** Each area is tiled into non-overlapping 500 m tiles; Dᵦ and Λ(r)
are computed per tile (tiles < 2 % built are excluded as voids). Zones are compared with the
**Mann–Whitney U test** (no normality assumption) and a **rank-biserial effect size**. With many
pairwise tests, nominal p < 0.05 results are reported as *suggestive* and weighted by effect size,
not treated as proof.

**2.8 Sensitivity.** The pipeline is re-run at resolution 1/2/4 m and street buffers ±50 %, with
scales held fixed in metres so resolutions compare fairly, to test whether any difference survives
the modelling choices.

## 3. Results

**3.1 Fractal dimension does not separate the fabrics.** Whole-transect Beijing footprint Dᵦ is
1.77 (West), 1.75 (Center), 1.75 (East) — near-identical, R² ≥ 0.998 (Table/`phase3_boxcount.csv`).
Per-tile footprint Dᵦ medians are 1.61 / 1.60 / 1.62; every pairwise Mann–Whitney is negligible.
The same holds in Hong Kong (Sham Shui Po 1.63, Tseung Kwan O 1.59). A single fractal dimension
cannot tell hutong, Axis, commercial, tong-lau, or podium fabric apart.

**3.2 In Beijing, lacunarity differences are weak.** Per-tile footprint Λ(64 m) medians are West
1.21, Center 1.38, East 1.28. The clearest contrast is West vs Center (p = 0.008, medium effect),
i.e. the imperial **Axis is the *gappiest*** at neighbourhood scale (its monumental blocks and
voids) and the **hutong the most uniform** — the opposite of a "modern-CBD-ruptures" story, and no
result survives strict multiple-comparison correction. The sensitivity analysis shows this
West < Center footprint ordering is **resolution-invariant** (p ≈ 0.008 at 1, 2, and 4 m), while
the street-based signal is fragile (weakens as buffers widen).

**3.3 In Hong Kong, the contrast is large.** Per-tile footprint Λ(64 m) medians: Sham Shui Po
**1.54**, Tseung Kwan O **2.92**, Kat Hing Wai 2.65 (small sample), Wan Chai 2.00. Fine tong-lau vs
podium megastructure is a large, significant difference (Mann–Whitney p = 0.001, r = 0.66; see
`results/figures/phase8_cross_city_lacunarity.png`).

**3.4 Cross-city.** Fine vernacular fabric is similar across cities (Beijing hutong Λ 1.21 ≈ Hong
Kong Sham Shui Po 1.54; Dᵦ ~1.6 in both). But the fine-vs-coarse *gap* is far larger in Hong Kong
(1.54→2.92) than in Beijing (1.21→1.28). The robust reading is this **contrast of contrasts**, not
absolute lacunarity between cities (which is confounded — §5).

## 4. Discussion

**Lacunarity succeeds where dimension fails** because Dᵦ measures how completely a pattern fills
space, while Λ(r) measures how that mass is *distributed* — clumped vs. even. Two fabrics can fill
space to the same degree (same Dᵦ ≈ 1.6) yet differ entirely in whether the built mass is spread
finely or concentrated into a few large masses with large gaps. That distinction — grain — is
exactly what separates a hutong from a podium megastructure, and it is invisible to dimension alone.

**Morphology, not heritage.** Hong Kong protects no ceremonial axis, yet Sham Shui Po's tong-lau
fabric is as fine and uniform as Beijing's imperial-adjacent hutongs, while Tseung Kwan O's podia
are coarser than anything in the old city. Fine human-scale grain therefore does not require a
protected axis to survive; coarseness arrives with a specific building *form* — the podium
megastructure. [AUTHOR: connect this to your design argument — what does it imply for infill design
near the Axis, or for how new fabric could be grained more finely?]

**The honest complication.** The tidy hypothesis (vernacular ≈ monumental; modern ruptures) is not
what the data show for Beijing: dimension is uniform, lacunarity differences are weak, and it is the
*Axis* — not the CBD — that reads as the neighbourhood-scale outlier. Reporting that, rather than a
suspiciously clean p < 0.001, is the point.

## 5. Limitations

- **2D plan analysis only.** Building height is not captured — a genuine limitation for Hong Kong.
- **Cross-city absolute lacunarity is confounded** by terrain, water, and reclamation; only the
  contrast-of-contrasts is trustworthy.
- **Small samples** (Tseung Kwan O n ≈ 14; Kat Hing Wai is a qualitative reference, not a
  distribution).
- **Multiple comparisons**; no Beijing result clears a strict Bonferroni threshold.
- **Footprints are machine-derived** (Overture/ML rooftops) — better than empty OSM, not
  survey-grade.
- **Box-counting scaling range** is short on 500 m tiles, limiting per-tile Dᵦ precision.

## 6. Conclusion

Fractal dimension is too blunt to distinguish urban fabrics; lacunarity is not. The measurable
story is that fine vernacular grain is shared between two very different East Asian cities and
persists in Hong Kong without any protected axis, while coarseness is a property of megastructure
morphology. [AUTHOR: 2–3 sentences on where you'd take this next — the design translation, a Beijing
field trip, or a third city.]

---

## References — ⚠ VERIFY EACH ON GOOGLE SCHOLAR BEFORE USE

> Do not cite anything you have not opened and confirmed. These foundational works are believed
> genuine; confirm exact author/year/title/venue and add page numbers. **Delete any you do not
> actually use.** Do not add citations you cannot verify.

- Mandelbrot, B. *The Fractal Geometry of Nature*. (1982). — fractal geometry ⚠ VERIFY
- Batty, M. & Longley, P. *Fractal Cities*. (1994). — fractal analysis of urban form ⚠ VERIFY
- Allain, C. & Cloitre, M. "Characterizing the lacunarity of random and deterministic fractal
  sets." *Phys. Rev. A* (1991). — the gliding-box method used here ⚠ VERIFY
- Plotnick, R. E., Gardner, R. H., et al. — lacunarity analysis method ⚠ VERIFY (confirm exact
  paper/year)
- Jacobs, J. *The Death and Life of Great American Cities*. (1961). ⚠ VERIFY
- Lynch, K. *The Image of the City*. (1960). ⚠ VERIFY
- Alexander, C. — *A Pattern Language* / *The Nature of Order* (confirm which, and year) ⚠ VERIFY

## Reproducibility & AI assistance

All figures and tables regenerate from the code (`make all`); see `README.md`. Analysis code was
developed with AI pair-programming assistance (Claude Code); all decisions, parameters, and
interpretations are the author's own, and the author can explain each. This is disclosed here and
must be disclosed in any submission's methods/acknowledgements.
