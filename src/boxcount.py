"""
boxcount.py — fractal (box-counting) dimension.  [PHASE 3]

WHAT THIS MODULE DOES
    For each binary raster it covers the image with boxes of side ε (in pixels), counts how
    many boxes contain any structure, N(ε), for ε = 1,2,4,...,512, and fits the straight line
        log N(ε)  =  D * log(1/ε)  +  c
    over a justified middle range. The slope D is the box-counting dimension. It reports D, a
    95% confidence interval, and R², and SAVES a log-log plot for every computation.

    Run it with:  python src/boxcount.py

HOW THE COUNT IS DONE (efficiently)
    To count boxes of side s that contain structure, we shrink the image by taking the MAX of
    each s x s block (skimage.block_reduce). A block becomes 1 if ANY pixel in it was 1. Summing
    the shrunk image = number of occupied boxes = N(s). Fast and exact.

READING THE RESULT
    D near 1 = line-like/sparse; D near 2 = area-filling. A HIGH R² means the pattern really is
    scale-invariant over that range (a true fractal signature); a low R² is a warning that a
    single dimension does not describe the pattern and we must pick the linear range by eye.
"""
from __future__ import annotations

import numpy as np
import rasterio
from scipy import stats
from skimage.measure import block_reduce
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config


def load_binary(path) -> np.ndarray:
    with rasterio.open(path) as src:
        return (src.read(1) > 0).astype(np.uint8)


def box_counts(arr: np.ndarray, sizes: list[int]) -> np.ndarray:
    """N(ε) for each box size: number of ε x ε boxes containing any structure."""
    counts = []
    for s in sizes:
        if s == 1:
            counts.append(int(arr.sum()))
        else:
            reduced = block_reduce(arr, (s, s), func=np.max, cval=0)
            counts.append(int(reduced.sum()))
    return np.array(counts, dtype=float)


def fit_dimension(sizes: np.ndarray, counts: np.ndarray,
                  lo: int, hi: int) -> dict:
    """Least-squares fit of log N vs log(1/ε) over [lo, hi]. Returns D, 95% CI, R²."""
    m = (sizes >= lo) & (sizes <= hi) & (counts > 0)
    x = -np.log(sizes[m])          # log(1/ε)
    y = np.log(counts[m])          # log N
    res = stats.linregress(x, y)
    n = int(m.sum())
    tcrit = stats.t.ppf(0.975, n - 2) if n > 2 else np.nan
    ci = tcrit * res.stderr
    return {
        "D": res.slope, "ci": ci, "ci_low": res.slope - ci, "ci_high": res.slope + ci,
        "r2": res.rvalue ** 2, "n_points": n, "lo": lo, "hi": hi,
        "intercept": res.intercept, "mask": m,
    }


def plot_loglog(sizes, counts, fit, title, out) -> None:
    """log N vs log(1/ε): all points, the fitted range highlighted, the fit line, D and R²."""
    x_all = -np.log(sizes)
    y_all = np.log(counts)
    m = fit["mask"]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(x_all[~m], y_all[~m], c="0.7", s=40, label="excluded (scale ends)", zorder=3)
    ax.scatter(x_all[m], y_all[m], c="#e34a33", s=45, label="fitted range", zorder=4)
    xs = np.array([x_all[m].min(), x_all[m].max()])
    ax.plot(xs, fit["D"] * xs + fit["intercept"], "k--", lw=1.5,
            label=f"fit: D = {fit['D']:.3f} ± {fit['ci']:.3f}", zorder=2)
    # secondary axis labels in metres for intuition
    ax.set_xlabel("log(1 / ε)   →  finer boxes to the right")
    ax.set_ylabel("log N(ε)   (occupied boxes)")
    flag = "" if fit["r2"] >= config.BOXCOUNT_R2_FLAG else "   ⚠ R² below flag — inspect range"
    ax.set_title(f"{title}\nD = {fit['D']:.3f}  (95% CI {fit['ci_low']:.3f}–{fit['ci_high']:.3f}),  "
                 f"R² = {fit['r2']:.4f}{flag}", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.2)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def analyze(zone: str, rep: str) -> dict:
    """Box-count one raster (zone x representation) and save its log-log plot."""
    suffix = "streets_2m" if rep == "streets" else "footprints_2m"
    path = config.DATA_PROCESSED / f"beijing_{zone}_{suffix}.tif"
    arr = load_binary(path)
    sizes = np.array(config.BOX_SIZES, dtype=int)
    counts = box_counts(arr, config.BOX_SIZES)
    fit = fit_dimension(sizes, counts, config.BOXCOUNT_FIT_MIN_PX, config.BOXCOUNT_FIT_MAX_PX)
    out = config.FIGURES / f"phase3_boxcount_{zone}_{rep}.png"
    plot_loglog(sizes, counts, fit, f"Box-counting — {zone} / {rep}", out)
    flag = "" if fit["r2"] >= config.BOXCOUNT_R2_FLAG else "  <-- R² LOW, inspect"
    print(f"[{zone:>6} / {rep:>10}]  D = {fit['D']:.3f}  "
          f"(95% CI {fit['ci_low']:.3f}-{fit['ci_high']:.3f})  R² = {fit['r2']:.4f}{flag}")
    return {"zone": zone, "rep": rep, "D": fit["D"], "ci_low": fit["ci_low"],
            "ci_high": fit["ci_high"], "r2": fit["r2"],
            "sizes": sizes, "counts": counts, "fit": fit}


def main() -> None:
    print("=" * 70)
    print(f"axis-fractal — Phase 3 box-counting dimension  "
          f"(fit {config.BOXCOUNT_FIT_MIN_PX}-{config.BOXCOUNT_FIT_MAX_PX} px)")
    print("=" * 70)
    results = []
    for zone in config.BEIJING_TRANSECTS:
        for rep in ("streets", "footprints"):
            results.append(analyze(zone, rep))

    # combined 3x2 log-log overview
    fig, axes = plt.subplots(3, 2, figsize=(11, 13))
    for ax, r in zip(axes.flat, results):
        s, c, fit = r["sizes"], r["counts"], r["fit"]
        x, y, m = -np.log(s), np.log(c), r["fit"]["mask"]
        ax.scatter(x[~m], y[~m], c="0.75", s=25)
        ax.scatter(x[m], y[m], c="#e34a33", s=30)
        xs = np.array([x[m].min(), x[m].max()])
        ax.plot(xs, fit["D"] * xs + fit["intercept"], "k--", lw=1.3)
        ax.set_title(f"{r['zone']}/{r['rep']}: D={r['D']:.3f}, R²={r['r2']:.4f}", fontsize=9)
        ax.grid(alpha=0.2)
    fig.suptitle("Phase 3 — box-counting log-log fits (log N vs log 1/ε)", y=0.995)
    fig.savefig(config.FIGURES / "phase3_boxcount_overview.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # save + record table
    import pandas as pd
    tbl = pd.DataFrame([{k: r[k] for k in ("zone", "rep", "D", "ci_low", "ci_high", "r2")}
                        for r in results]).round(4)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(config.TABLES / "phase3_boxcount.csv", index=False)
    print("\n" + tbl.to_string(index=False))

    lo, hi = config.BOXCOUNT_FIT_MIN_PX, config.BOXCOUNT_FIT_MAX_PX
    lines = ["\n## Phase 3 — box-counting dimension (2026-07-14)\n",
             f"Box sizes {config.BOX_SIZES} px; slope fitted over {lo}-{hi} px "
             f"(= {lo*2}-{hi*2} m). Every log-log plot saved to `results/figures/phase3_boxcount_*`.\n",
             "| zone | representation | Dᵦ | 95% CI | R² |", "|---|---|--:|---|--:|"]
    for r in results:
        lines.append(f"| {r['zone']} | {r['rep']} | {r['D']:.3f} | "
                     f"{r['ci_low']:.3f}–{r['ci_high']:.3f} | {r['r2']:.4f} |")
    any_low = [r for r in results if r["r2"] < config.BOXCOUNT_R2_FLAG]
    lines.append("")
    lines.append(f"**R² check:** {'all fits ≥ ' + str(config.BOXCOUNT_R2_FLAG) if not any_low else str(len(any_low)) + ' fit(s) below ' + str(config.BOXCOUNT_R2_FLAG) + ' — scaling range needs a by-eye check (see plots)'}.")
    lines.append("These are whole-transect dimensions (one per zone × representation). The "
                 "statistically meaningful per-tile distributions + zone comparison come in Phase 5.")
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\nSaved plots + table; appended to results/results.md. Phase 3 done.")


if __name__ == "__main__":
    main()
