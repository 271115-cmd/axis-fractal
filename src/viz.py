"""
viz.py — clean paper / portfolio figures.  [PHASE 7]

Diagnostic plots (Phases 3-6) were for us; these are for a reader. One consistent house
style, minimal ink, a colourblind-safe zone palette (validated with the dataviz skill's
checker: Okabe-Ito blue/vermillion/green, CVD ΔE ≈ 37, contrast ≥ 3:1), a single-hue
sequential ramp for the heatmap (never a rainbow), and text in ink — never the series colour.

Builds, into results/figures/:
    phase7_transect_maps.png       binary footprint maps of the three transects (the hero)
    phase7_loglog_fit.png          one clean box-counting fit (method, honestly shown)
    phase7_lacunarity_family.png   footprint Λ(r) curves by zone (the finding)
    phase7_boxplots.png            per-tile Λ(64 m) distributions by zone (the robust result)
    phase7_lacunarity_heatmap.png  Λ(64 m) per tile across the whole study area

    Run it with:  python src/viz.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio  # noqa: F401  (documents raster dependency; load_binary uses it)
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from boxcount import load_binary, box_counts, fit_dimension

# --- house style --------------------------------------------------------------------------
INK, MUTED, FAINT = "#1a1a1a", "#6b6b6b", "#b9b9b4"
SURFACE, GRID = "#fcfcfb", "#ecece8"
ZONE = {"west": "#0072B2", "center": "#D55E00", "east": "#009E73"}   # CVD-safe (validated)
ZONE_LABEL = {"west": "West · hutong", "center": "Center · Axis", "east": "East · commercial"}
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#eef4fa", "#9cc4e0", "#0072B2", "#044a73"])


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.size": 11,
        "text.color": INK, "axes.labelcolor": INK, "axes.titlecolor": INK,
        "axes.edgecolor": FAINT, "axes.linewidth": 0.8,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": MUTED, "ytick.labelcolor": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlepad": 12,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "legend.frameon": False, "figure.dpi": 140,
    })


def _caption(fig, text: str) -> None:
    fig.text(0.5, -0.01, text, ha="center", va="top", color=MUTED, fontsize=9)


# --- 1. binary transect maps (the hero) ---------------------------------------------------

def transect_maps() -> None:
    binmap = ListedColormap([SURFACE, INK])   # 0 = surface, 1 = ink structure
    fig, axes = plt.subplots(1, 3, figsize=(9, 11))
    for ax, zone in zip(axes, config.BEIJING_TRANSECTS):
        arr = load_binary(config.DATA_PROCESSED / f"beijing_{zone}_footprints_2m.tif")
        ax.imshow(arr, cmap=binmap, interpolation="nearest")
        ax.set_title(ZONE_LABEL[zone], color=ZONE[zone], fontsize=12)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.grid(False)
    # a 1 km scale bar on the first panel (2 m/px -> 500 px)
    ax0 = axes[0]
    y = load_binary(config.DATA_PROCESSED / "beijing_west_footprints_2m.tif").shape[0] - 120
    ax0.plot([40, 40 + 500], [y, y], color=INK, lw=2.5)
    ax0.text(40, y - 40, "1 km", color=INK, fontsize=9)
    fig.suptitle("Building fabric of three transects across Beijing's Central Axis",
                 y=0.98, fontsize=15, fontweight="semibold")
    _caption(fig, "Overture footprints, 2 m/pixel. The Forbidden City's monumental blocks sit "
                  "in the Center strip amid the finer hutong grain of West and East.")
    fig.savefig(config.FIGURES / "phase7_transect_maps.png", bbox_inches="tight")
    plt.close(fig)
    print("  phase7_transect_maps.png")


# --- 2. one clean log-log fit -------------------------------------------------------------

def loglog_fit(zone: str = "center") -> None:
    arr = load_binary(config.DATA_PROCESSED / f"beijing_{zone}_footprints_2m.tif")
    sizes = np.array(config.BOX_SIZES)
    counts = box_counts(arr, config.BOX_SIZES)
    fit = fit_dimension(sizes, counts, config.BOXCOUNT_FIT_MIN_PX, config.BOXCOUNT_FIT_MAX_PX)
    x, y, m = -np.log(sizes), np.log(counts), fit["mask"]
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(x[~m], y[~m], s=46, color=FAINT, zorder=3, label="excluded (scale ends)")
    ax.scatter(x[m], y[m], s=52, color=ZONE[zone], zorder=4, label="fitted range")
    xs = np.array([x[m].min(), x[m].max()])
    ax.plot(xs, fit["D"] * xs + fit["intercept"], color=INK, lw=1.8, ls="--", zorder=2)
    ax.set_xlabel("log (1 / box size)"); ax.set_ylabel("log (occupied boxes)")
    ax.set_title(f"Box-counting fit — {ZONE_LABEL[zone]}, footprints")
    ax.text(0.03, 0.97, f"Dᵦ = {fit['D']:.3f}\n95% CI  {fit['ci_low']:.3f}–{fit['ci_high']:.3f}\n"
            f"R² = {fit['r2']:.4f}", transform=ax.transAxes, va="top", ha="left",
            fontsize=11, color=INK,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=GRID))
    ax.legend(loc="lower right")
    _caption(fig, "The straight middle range is the fractal signature; the grey ends "
                  "(pixel-scale and image-scale) are excluded by design.")
    fig.savefig(config.FIGURES / "phase7_loglog_fit.png", bbox_inches="tight")
    plt.close(fig)
    print("  phase7_loglog_fit.png")


# --- 3. lacunarity curve family -----------------------------------------------------------

def lacunarity_family() -> None:
    df = pd.read_csv(config.TABLES / "phase4_lacunarity.csv")
    fp = df[df.rep == "footprints"]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for zone in config.BEIJING_TRANSECTS:
        d = fp[fp.zone == zone].sort_values("r")
        ax.plot(d["r"], d["lambda"], "-o", color=ZONE[zone], lw=2, ms=6, zorder=3)
        last = d.iloc[-1]
        ax.text(last["r"] * 1.06, last["lambda"], ZONE_LABEL[zone].split(" · ")[1],
                color=INK, va="center", fontsize=10)
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_xlabel("gliding-box size  r  (m, at 2 m/px)")
    ax.set_ylabel("lacunarity  Λ(r)")
    ax.set_xticks([8, 32, 128, 512])
    ax.set_xticklabels(["16", "64", "256", "1024"])   # r px * 2 m
    ax.set_title("Building-footprint lacunarity across scale")
    ax.set_xlim(right=512 * 3.0)
    _caption(fig, "Curves converge at fine scale but the Center (Axis) stays gappier than "
                  "West (hutong) at the district scale — the divergence Dᵦ could not see.")
    fig.savefig(config.FIGURES / "phase7_lacunarity_family.png", bbox_inches="tight")
    plt.close(fig)
    print("  phase7_lacunarity_family.png")


# --- 4. per-tile boxplots (the robust finding) --------------------------------------------

def boxplots() -> None:
    df = pd.read_csv(config.TABLES / "phase5_tile_metrics.csv")
    fp = df[df.rep == "footprints"]
    zones = list(config.BEIJING_TRANSECTS)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    data = [fp[fp.zone == z]["lam32"].dropna() for z in zones]
    bp = ax.boxplot(data, tick_labels=[ZONE_LABEL[z].split(" · ")[1] for z in zones],
                    patch_artist=True, widths=0.55, showfliers=True,
                    flierprops=dict(marker="o", ms=3, mfc=FAINT, mec="none"),
                    medianprops=dict(color=INK, lw=2),
                    whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED))
    for patch, z in zip(bp["boxes"], zones):
        patch.set_facecolor(ZONE[z]); patch.set_alpha(0.35); patch.set_edgecolor(ZONE[z])
    for i, d in enumerate(data):
        ax.text(i + 1.32, d.median(), f"{d.median():.2f}", va="center", ha="left",
                fontsize=10, color=INK)
    ax.set_ylabel("Λ(64 m) per 500 m tile")
    ax.set_ylim(0.9, min(4.0, ax.get_ylim()[1]))   # clip extreme void-edge outliers for legibility
    ax.set_title("Neighbourhood-scale gappiness by zone")
    ax.grid(axis="x", visible=False)
    _caption(fig, "West (hutong) is the most uniform; Center (Axis) the gappiest. "
                  "West vs Center: p ≈ 0.008, medium effect, resolution-invariant. "
                  "(A few extreme void-edge outliers clipped for legibility.)")
    fig.savefig(config.FIGURES / "phase7_boxplots.png", bbox_inches="tight")
    plt.close(fig)
    print("  phase7_boxplots.png")


# --- 5. lacunarity heatmap over the study area --------------------------------------------

def lacunarity_heatmap() -> None:
    df = pd.read_csv(config.TABLES / "phase5_tile_metrics.csv")
    fp = df[df.rep == "footprints"]
    offset = {"west": 0, "center": 3, "east": 6}
    nrows = int(fp["row"].max()) + 1
    grid = np.full((nrows, 9), np.nan)
    for _, r in fp.iterrows():
        grid[int(r["row"]), offset[r["zone"]] + int(r["col"])] = r["lam32"]
    SEQ.set_bad(GRID)
    fig, ax = plt.subplots(figsize=(6.5, 9))
    im = ax.imshow(np.ma.masked_invalid(grid), cmap=SEQ, aspect="auto",
                   interpolation="nearest", vmin=1.0, vmax=np.nanpercentile(grid, 95))
    for x in (2.5, 5.5):                       # zone dividers
        ax.axvline(x, color=SURFACE, lw=3)
    ax.set_xticks([1, 4, 7])
    ax.set_xticklabels([ZONE_LABEL[z].split(" · ")[0] for z in config.BEIJING_TRANSECTS])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(False)
    ax.set_title("Where the fabric is gappy — Λ(64 m) per 500 m tile")
    cb = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
    cb.set_label("Λ(64 m)  (higher = gappier)", color=MUTED)
    cb.ax.tick_params(colors=MUTED)
    ax.text(-0.4, -0.6, "▲ north", color=MUTED, fontsize=9)
    _caption(fig, "Each cell is one 500 m tile (voids left blank). The gappiest cells cluster "
                  "in the Center strip — the Forbidden City's monumental scale.")
    fig.savefig(config.FIGURES / "phase7_lacunarity_heatmap.png", bbox_inches="tight")
    plt.close(fig)
    print("  phase7_lacunarity_heatmap.png")


def main() -> None:
    print("=" * 60)
    print("axis-fractal — Phase 7 portfolio figures")
    print("=" * 60)
    apply_style()
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    transect_maps()
    loglog_fit()
    lacunarity_family()
    boxplots()
    lacunarity_heatmap()
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write(
        "\n## Phase 7 — portfolio figures (2026-07-14)\n\n"
        "Clean, colourblind-safe (Okabe-Ito, validated), minimal-ink versions of the key "
        "results in `results/figures/phase7_*`: transect maps, one log-log fit, the footprint "
        "Λ(r) family, per-tile Λ(64 m) boxplots, and a study-area lacunarity heatmap. Same "
        "numbers as the diagnostic figures — restyled for a reader, telling the honest "
        "'Center (Axis) gappiest, West (hutong) most uniform' story.\n")
    print("\nPhase 7 done. Figures written to results/figures/phase7_*.png")


if __name__ == "__main__":
    main()
