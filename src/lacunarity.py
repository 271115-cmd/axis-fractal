"""
lacunarity.py — gliding-box lacunarity.  [PHASE 4]

WHAT THIS MODULE DOES
    For each binary raster it computes the lacunarity curve Λ(r) for r = 8..512 px using the
    classic Allain & Cloitre gliding-box method, made memory-safe with a summed-area table.
    It outputs the FULL curve per raster (never a single number), a density-independent
    normalized curve, plots, and a table.

    Run it with:  python src/lacunarity.py

THE MATH, SIMPLY
    For box side r, slide it over every position and record the mass m (number of built pixels
    inside). Then  Λ(r) = mean(m²) / mean(m)²  = 1 + Var(m)/Mean(m)².
      Λ = 1        -> every box holds the same amount (perfectly even texture)
      Λ large      -> some boxes full, some empty (clumpy, gappy texture)
    At r = 1, Λ = 1/p exactly (p = built fraction), i.e. pure density. So the curve starts high
    (density) and falls toward 1 as boxes grow and average out the gaps.

MEMORY-SAFE COUNTING (summed-area table / integral image)
    Precompute I, the cumulative sum of the image. Then the sum inside ANY r x r box is just
    four lookups: I[a+r,b+r] - I[a,b+r] - I[a+r,b] + I[a,b]. We get every box's mass with pure
    array arithmetic — no giant stack of windows (which would exhaust RAM).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config


def load_binary(path) -> np.ndarray:
    with rasterio.open(path) as src:
        return (src.read(1) > 0).astype(np.float64)


def gliding_box_masses(arr: np.ndarray, r: int) -> np.ndarray:
    """All r x r box masses via a summed-area table. Returns a 2D array of masses."""
    H, W = arr.shape
    if r > H or r > W:
        return np.array([])  # box bigger than image; skip
    integral = np.zeros((H + 1, W + 1), dtype=np.float64)
    integral[1:, 1:] = arr.cumsum(axis=0).cumsum(axis=1)
    # sum over every box whose top-left is (i, j), i in 0..H-r, j in 0..W-r
    masses = (integral[r:, r:] - integral[:-r, r:]
              - integral[r:, :-r] + integral[:-r, :-r])
    return masses


def lacunarity_at(arr: np.ndarray, r: int) -> float:
    masses = gliding_box_masses(arr, r)
    if masses.size == 0:
        return np.nan
    mean = masses.mean()
    if mean == 0:
        return np.nan
    return float((masses ** 2).mean() / mean ** 2)


def lacunarity_curve(arr: np.ndarray, radii) -> pd.DataFrame:
    p = float(arr.mean())  # built fraction (density)
    rows = [{"r": r, "lambda": lacunarity_at(arr, r)} for r in radii]
    df = pd.DataFrame(rows)
    # normalized for cross-density comparison: anchor each curve to 1 at the smallest r,
    # so we compare the SHAPE / decay of gappiness independent of absolute (density-driven) level
    base = df["lambda"].iloc[0]
    df["lambda_norm"] = df["lambda"] / base
    df["p"] = p
    df["lambda_r1_density"] = 1.0 / p if p > 0 else np.nan  # Λ(1) = 1/p, for reference
    return df


def analyze(zone: str, rep: str) -> pd.DataFrame:
    suffix = "streets_2m" if rep == "streets" else "footprints_2m"
    arr = load_binary(config.DATA_PROCESSED / f"beijing_{zone}_{suffix}.tif")
    df = lacunarity_curve(arr, config.LAC_RADII)
    df.insert(0, "zone", zone)
    df.insert(1, "rep", rep)
    lam8 = df["lambda"].iloc[0]
    lam512 = df["lambda"].iloc[-1]
    print(f"[{zone:>6} / {rep:>10}]  p={df['p'].iloc[0]:.3f}  "
          f"Λ(8)={lam8:.3f}  Λ(512)={lam512:.3f}  (curve of {len(df)} points)")
    return df


def plot_curves(all_df: pd.DataFrame) -> None:
    """2 rows (raw / normalized) x 2 cols (streets / footprints), 3 zone curves each."""
    colors = {"west": "#2b8cbe", "center": "#e34a33", "east": "#31a354"}
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    for col, rep in enumerate(["streets", "footprints"]):
        for row, (ycol, ylabel) in enumerate([
            ("lambda", "Λ(r)  (raw lacunarity)"),
            ("lambda_norm", "Λ(r) / Λ(8)  (normalized, shape)"),
        ]):
            ax = axes[row][col]
            for zone in config.BEIJING_TRANSECTS:
                d = all_df[(all_df["zone"] == zone) & (all_df["rep"] == rep)]
                ax.plot(d["r"], d[ycol], "o-", color=colors[zone], label=zone, lw=1.6, ms=5)
            ax.set_xscale("log", base=2)
            if row == 0:
                ax.set_yscale("log")
            ax.set_xlabel("box size r (pixels; 2 m each)")
            ax.set_ylabel(ylabel)
            ax.set_title(f"{rep}", fontsize=11)
            ax.grid(alpha=0.25, which="both")
            ax.legend(frameon=False, fontsize=9)
    fig.suptitle("Phase 4 — gliding-box lacunarity Λ(r) by zone", y=0.995)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase4_lacunarity_curves.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nCurves saved -> {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 68)
    print("axis-fractal — Phase 4 gliding-box lacunarity Λ(r)")
    print("=" * 68)
    frames = [analyze(z, rep) for z in config.BEIJING_TRANSECTS
              for rep in ("streets", "footprints")]
    all_df = pd.concat(frames, ignore_index=True)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    all_df.round(5).to_csv(config.TABLES / "phase4_lacunarity.csv", index=False)
    plot_curves(all_df)

    # record — the full curves live in the CSV; results.md gets the endpoints + reading
    lines = ["\n## Phase 4 — gliding-box lacunarity (2026-07-14)\n",
             f"Λ(r) for r = {config.LAC_RADII} px (16 m–1 km) via summed-area table. "
             "Full curves in `results/tables/phase4_lacunarity.csv`; plot "
             "`results/figures/phase4_lacunarity_curves.png`. Endpoints below "
             "(Λ(8)=fine-scale gappiness, Λ(512)=district-scale):\n",
             "| zone | rep | density p | Λ(8) | Λ(512) |", "|---|---|--:|--:|--:|"]
    for (zone, rep), d in all_df.groupby(["zone", "rep"]):
        lines.append(f"| {zone} | {rep} | {d['p'].iloc[0]:.3f} | "
                     f"{d['lambda'].iloc[0]:.3f} | {d['lambda'].iloc[-1]:.3f} |")
    lines += ["", "Reminder: lacunarity is scale-dependent — the CURVE is the result, not any "
              "single value (brief anti-goal). Per-tile Λ(r) distributions + the zone comparison "
              "come in Phase 5."]
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("Appended to results/results.md. Phase 4 done.")


if __name__ == "__main__":
    main()
