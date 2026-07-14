"""
sampling.py — per-tile metrics + zone statistics.  [PHASE 5]

WHAT THIS MODULE DOES  (this is the actual hypothesis test)
    Everything before this was one number per whole transect, which proves nothing. Here we
    cut each zone's raster into non-overlapping 500 m (250 px) tiles, compute Dᵦ and Λ(r) for
    EVERY tile, and then:
      * summarise each zone as a distribution (median, IQR, boxplots),
      * compare zones pairwise with the Mann-Whitney U test + a rank-biserial effect size.
    We exclude near-empty tiles (a lake/plaza/palace void is not "fabric" and its dimension is
    meaningless) and report how many. We state results plainly, including any that contradict
    the hypothesis.

    Run it with:  python src/sampling.py

WHY MANN-WHITNEY (not a t-test)
    Dᵦ and Λ per tile are not guaranteed bell-shaped and samples are smallish, so we use a
    rank-based test that makes no normality assumption. Effect size (rank-biserial r) tells us
    whether a "significant" difference is actually LARGE or just detectable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from boxcount import box_counts, fit_dimension
from lacunarity import lacunarity_at

ZONES = list(config.BEIJING_TRANSECTS)
REPS = ["streets", "footprints"]
PAIRS = [("west", "center"), ("west", "east"), ("center", "east")]
# the lacunarity scales we compare across zones (within a 250 px tile: 16 m .. 64 m)
LAC_TEST_RADII = [8, 16, 32]


def load_binary(path) -> np.ndarray:
    with rasterio.open(path) as src:
        return (src.read(1) > 0).astype(np.uint8)


def iter_full_tiles(arr: np.ndarray, tpx: int):
    """Yield (row, col, sub-array) for every complete tpx x tpx tile (partial edges dropped)."""
    H, W = arr.shape
    for r in range(H // tpx):
        for c in range(W // tpx):
            yield r, c, arr[r * tpx:(r + 1) * tpx, c * tpx:(c + 1) * tpx]


def tile_metrics(sub: np.ndarray) -> dict:
    """Built fraction, box-counting Dᵦ (+R²), and lacunarity at several scales for one tile."""
    p = float(sub.mean())
    out = {"p": p}
    if p < config.TILE_MIN_BUILT_FRAC:
        # not fabric — leave fractal metrics undefined (NaN), excluded from stats
        out["Db"] = np.nan
        out["Db_r2"] = np.nan
        for r in config.TILE_LAC_RADII:
            out[f"lam{r}"] = np.nan
        return out
    sizes = np.array(config.TILE_BOX_SIZES)
    counts = box_counts(sub, config.TILE_BOX_SIZES)
    fit = fit_dimension(sizes, counts, config.TILE_BOX_FIT_MIN_PX, config.TILE_BOX_FIT_MAX_PX)
    out["Db"] = fit["D"]
    out["Db_r2"] = fit["r2"]
    for r in config.TILE_LAC_RADII:
        out[f"lam{r}"] = lacunarity_at(sub, r)
    return out


def collect() -> pd.DataFrame:
    rows = []
    for zone in ZONES:
        for rep in REPS:
            suffix = "streets_2m" if rep == "streets" else "footprints_2m"
            arr = load_binary(config.DATA_PROCESSED / f"beijing_{zone}_{suffix}.tif")
            for r, c, sub in iter_full_tiles(arr, config.TILE_PX):
                m = tile_metrics(sub)
                m.update({"zone": zone, "rep": rep, "row": r, "col": c})
                rows.append(m)
    return pd.DataFrame(rows)


def rank_biserial(x, y) -> tuple[float, float, float]:
    """Mann-Whitney U (two-sided) -> (U, p, rank-biserial effect size r)."""
    x, y = np.asarray(x), np.asarray(y)
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    r = 1.0 - 2.0 * res.statistic / (len(x) * len(y))   # in [-1, 1]
    return float(res.statistic), float(res.pvalue), float(r)


def _mag(r: float) -> str:
    a = abs(r)
    return "negligible" if a < 0.1 else "small" if a < 0.3 else "medium" if a < 0.5 else "large"


def zone_stats(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Per rep+zone median/IQR/n for one metric (NaN tiles dropped)."""
    rows = []
    for rep in REPS:
        for zone in ZONES:
            v = df[(df.rep == rep) & (df.zone == zone)][metric].dropna()
            rows.append({"rep": rep, "zone": zone, "n": len(v),
                         "median": v.median(), "q1": v.quantile(.25), "q3": v.quantile(.75)})
    return pd.DataFrame(rows)


def pairwise(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = []
    for rep in REPS:
        for a, b in PAIRS:
            xa = df[(df.rep == rep) & (df.zone == a)][metric].dropna()
            xb = df[(df.rep == rep) & (df.zone == b)][metric].dropna()
            if len(xa) < 3 or len(xb) < 3:
                continue
            U, p, r = rank_biserial(xa, xb)
            rows.append({"rep": rep, "metric": metric, "pair": f"{a} vs {b}",
                         "median_a": round(xa.median(), 3), "median_b": round(xb.median(), 3),
                         "U": U, "p": round(p, 4), "effect_r": round(r, 3),
                         "effect": _mag(r), "sig_.05": p < 0.05})
    return pd.DataFrame(rows)


def boxplots(df: pd.DataFrame) -> None:
    metrics = [("Db", "Dᵦ (box-counting dimension)"),
               ("lam16", "Λ(16)  ·  32 m lacunarity"),
               ("lam32", "Λ(32)  ·  64 m lacunarity")]
    colors = {"west": "#2b8cbe", "center": "#e34a33", "east": "#31a354"}
    fig, axes = plt.subplots(len(metrics), 2, figsize=(12, 12))
    for row, (metric, mlabel) in enumerate(metrics):
        for col, rep in enumerate(REPS):
            ax = axes[row][col]
            data = [df[(df.rep == rep) & (df.zone == z)][metric].dropna() for z in ZONES]
            bp = ax.boxplot(data, tick_labels=ZONES, patch_artist=True, widths=0.6)
            for patch, z in zip(bp["boxes"], ZONES):
                patch.set_facecolor(colors[z]); patch.set_alpha(0.55)
            for med in bp["medians"]:
                med.set_color("black")
            ax.set_title(f"{rep} — {mlabel}", fontsize=10)
            ax.grid(alpha=0.2, axis="y")
    fig.suptitle("Phase 5 — per-500 m-tile distributions by zone", y=0.995)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase5_tile_distributions.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Boxplots saved -> {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 70)
    print("axis-fractal — Phase 5 per-tile metrics + zone statistics")
    print("=" * 70)
    df = collect()

    # how many tiles, and how many used for fractal metrics after excluding voids
    print("\nTile counts (total / used after excluding voids):")
    for rep in REPS:
        for zone in ZONES:
            sub = df[(df.rep == rep) & (df.zone == zone)]
            print(f"  {rep:>10} / {zone:>6}: {len(sub):>2} tiles, "
                  f"{sub['Db'].notna().sum():>2} used "
                  f"(median fit R² = {sub['Db_r2'].median():.3f})")

    config.TABLES.mkdir(parents=True, exist_ok=True)
    df.round(5).to_csv(config.TABLES / "phase5_tile_metrics.csv", index=False)

    # distributions + tests for the headline metrics
    test_metrics = ["Db"] + [f"lam{r}" for r in LAC_TEST_RADII]
    all_stats = pd.concat([zone_stats(df, m).assign(metric=m) for m in test_metrics],
                          ignore_index=True)
    all_pairs = pd.concat([pairwise(df, m) for m in test_metrics], ignore_index=True)
    all_stats.round(3).to_csv(config.TABLES / "phase5_zone_summary.csv", index=False)
    all_pairs.to_csv(config.TABLES / "phase5_mannwhitney.csv", index=False)

    print("\nPer-zone medians (Dᵦ):")
    print(zone_stats(df, "Db").round(3).to_string(index=False))
    print("\nPairwise Mann-Whitney (all metrics):")
    print(all_pairs.to_string(index=False))

    boxplots(df)
    _write_results(df, all_stats, all_pairs, test_metrics)
    print("\nPhase 5 done.")


def _write_results(df, all_stats, all_pairs, test_metrics) -> None:
    n_by = df.groupby(["rep", "zone"])["Db"].agg(lambda s: s.notna().sum())
    lines = ["\n## Phase 5 — per-tile distributions + statistics (2026-07-14)\n",
             f"Each transect cut into non-overlapping {config.TILE_M:.0f} m tiles "
             f"({config.TILE_PX}×{config.TILE_PX} px). Dᵦ (fit {config.TILE_BOX_FIT_MIN_PX}-"
             f"{config.TILE_BOX_FIT_MAX_PX} px) and Λ(r) computed per tile; tiles below "
             f"{config.TILE_MIN_BUILT_FRAC:.0%} built excluded as voids. Full data in "
             "`results/tables/phase5_tile_metrics.csv`; boxplots "
             "`results/figures/phase5_tile_distributions.png`.\n",
             "**Tiles used per zone (after excluding voids):** "
             + ", ".join(f"{r}/{z}={int(n)}" for (r, z), n in n_by.items()) + ".\n",
             "**Per-zone medians:**\n",
             "| rep | metric | west | center | east |", "|---|---|--:|--:|--:|"]
    for m in test_metrics:
        zs = all_stats[all_stats.metric == m]
        for rep in REPS:
            vals = {z: zs[(zs.rep == rep) & (zs.zone == z)]["median"].iloc[0] for z in ZONES}
            lines.append(f"| {rep} | {m} | {vals['west']:.3f} | {vals['center']:.3f} | {vals['east']:.3f} |")
    lines += ["", "**Significant pairwise differences (Mann-Whitney, p<0.05):**", ""]
    sig = all_pairs[all_pairs["sig_.05"]]
    if len(sig):
        lines.append("| rep | metric | pair | medians | p | effect (r) |")
        lines.append("|---|---|---|---|--:|---|")
        for _, r in sig.iterrows():
            lines.append(f"| {r['rep']} | {r['metric']} | {r['pair']} | "
                         f"{r['median_a']} vs {r['median_b']} | {r['p']} | {r['effect_r']} ({r['effect']}) |")
    else:
        lines.append("_None._")
    lines += ["",
              f"Ran {len(all_pairs)} pairwise tests across {len(test_metrics)} metrics × 2 "
              "representations × 3 pairs — treat single p-values with multiple-comparison caution "
              f"(a Bonferroni-style threshold would be ~0.05/{len(all_pairs)} ≈ "
              f"{0.05/max(len(all_pairs),1):.4f}). Effect sizes matter as much as significance. "
              "Interpretation written up honestly, including non-differences."]
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("Appended to results/results.md.")


if __name__ == "__main__":
    main()
