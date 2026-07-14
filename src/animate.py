"""
animate.py — broadcast-quality animation frames for the video series.  [PHASE 9]

Renders deterministic PNG frame sequences (1920×1080, dark background) to
`results/video_assets/<episode>/`. Frames use the SAME computations as the analysis modules,
so the video shows real numbers, not decoration. One frame per box size / sweep step; the
video editor sets how long to hold each.

    Run it with:  python src/animate.py

Episodes built here:
    ep1_boxcount_forbidden_city/   the box-counting grid shrinking over the Forbidden City,
                                   with a live box count and the dimension emerging in a
                                   log-log plot that accumulates one point per frame.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import rasterio
from scipy import stats
from shapely.geometry import Point
from skimage.measure import block_reduce
from matplotlib.colors import ListedColormap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

# --- broadcast dark palette ---------------------------------------------------------------
BG = "#0b0b10"          # near-black background
STRUCT = "#e9e4d6"      # warm off-white for built structure
GRID = "#393b47"        # subtle grid lines
ACCENT = "#ff7a45"      # occupied boxes + fitted points (warm)
EXCLUDED = "#6b6c78"    # excluded scale-end points
INK = "#ece8dc"         # primary light text
MUTED = "#9a9ba6"       # secondary text
ATTRIB = "© OpenStreetMap contributors · Overture Maps"

FORBIDDEN_CITY = (39.9175, 116.3960)   # lat, lon — main palace mass in the Center transect
CROP_PX = 760                          # ~1.52 km window at 2 m/px (fits the 833 px-wide raster)


def video_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
        "font.family": "sans-serif", "text.color": INK,
        "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def load_fc_crop(size_px: int = CROP_PX) -> np.ndarray:
    """Read the Center footprint raster and crop a square window around the Forbidden City."""
    path = config.DATA_PROCESSED / "beijing_center_footprints_2m.tif"
    with rasterio.open(path) as src:
        arr = (src.read(1) > 0).astype(np.uint8)
        px = gpd.GeoSeries([Point(FORBIDDEN_CITY[1], FORBIDDEN_CITY[0])], crs=config.WGS84) \
            .to_crs(config.BEIJING_CRS)
        row, col = src.index(px.x.iloc[0], px.y.iloc[0])
    H, W = arr.shape
    half = size_px // 2
    r0 = int(np.clip(row - half, 0, max(0, H - size_px)))
    c0 = int(np.clip(col - half, 0, max(0, W - size_px)))
    return arr[r0:r0 + size_px, c0:c0 + size_px]


def occupied_overlay(arr: np.ndarray, s: int) -> tuple[np.ndarray, int]:
    """Occupied-box mask upsampled back to pixel size, and the box count N(s)."""
    reduced = block_reduce(arr, (s, s), func=np.max, cval=0)
    N = int(reduced.sum())
    full = np.repeat(np.repeat(reduced, s, axis=0), s, axis=1)[:arr.shape[0], :arr.shape[1]]
    return full.astype(bool), N


def render_boxcount(episode: str = "ep1_boxcount_forbidden_city") -> None:
    arr = load_fc_crop()
    H, W = arr.shape
    res = config.RASTER_RES_M
    # descending box sizes; 256 & 2 px are the excluded scale-ends, 128..4 the fitted range
    sizes = [256, 128, 64, 32, 16, 8, 4, 2]
    fit_lo, fit_hi = config.BOXCOUNT_FIT_MIN_PX, config.BOXCOUNT_FIT_MAX_PX
    struct_cmap = ListedColormap([BG, STRUCT])
    occ_cmap = ListedColormap([(0, 0, 0, 0), ACCENT])  # transparent where not occupied

    out_dir = config.RESULTS / "video_assets" / episode
    out_dir.mkdir(parents=True, exist_ok=True)

    pts = []  # (size, N) accumulated for the log-log
    for i, s in enumerate(sizes):
        mask, N = occupied_overlay(arr, s)
        pts.append((s, N))

        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        # ---- left: the raster with grid + highlighted occupied boxes ----
        axL = fig.add_axes([0.03, 0.08, 0.52, 0.84])
        axL.imshow(arr, cmap=struct_cmap, interpolation="nearest")
        axL.imshow(np.where(mask, 1, 0), cmap=occ_cmap, alpha=0.42, interpolation="nearest")
        # grid lines (skip when a grid would be too dense to read)
        if W / s <= 96:
            for x in range(0, W + 1, s):
                axL.axvline(x - 0.5, color=GRID, lw=0.6)
            for y in range(0, H + 1, s):
                axL.axhline(y - 0.5, color=GRID, lw=0.6)
        axL.set_xlim(-0.5, W - 0.5); axL.set_ylim(H - 0.5, -0.5)
        axL.set_xticks([]); axL.set_yticks([])
        axL.set_title("Beijing Central Axis — Forbidden City (building footprints)",
                      color=INK, fontsize=15, pad=12)
        # 500 m scale bar (250 px)
        axL.plot([20, 20 + 250], [H - 30, H - 30], color=INK, lw=3)
        axL.text(20, H - 45, "500 m", color=INK, fontsize=11)

        # ---- right: the emerging log-log fit + big readout ----
        axR = fig.add_axes([0.62, 0.30, 0.34, 0.50])
        ps = np.array(pts, float)
        x_all, y_all = -np.log(ps[:, 0]), np.log(ps[:, 1])
        infit = (ps[:, 0] >= fit_lo) & (ps[:, 0] <= fit_hi)
        axR.scatter(x_all[~infit], y_all[~infit], s=70, color=EXCLUDED, zorder=3)
        axR.scatter(x_all[infit], y_all[infit], s=90, color=ACCENT, zorder=4)
        D_txt = "—"
        if infit.sum() >= 2:
            res_fit = stats.linregress(x_all[infit], y_all[infit])
            xs = np.array([x_all[infit].min(), x_all[infit].max()])
            axR.plot(xs, res_fit.slope * xs + res_fit.intercept, "--", color=INK, lw=1.6, zorder=2)
            D_txt = f"{res_fit.slope:.3f}"
        axR.set_xlabel("log (1 / box size)"); axR.set_ylabel("log (occupied boxes)")
        axR.grid(alpha=0.15)

        # big live readout
        fig.text(0.62, 0.90, "BOX-COUNTING DIMENSION", color=MUTED, fontsize=14, family="monospace")
        fig.text(0.62, 0.855, f"ε = {s} px  =  {s*res:.0f} m", color=INK, fontsize=22, family="monospace")
        fig.text(0.62, 0.815, f"N = {N:,} occupied boxes", color=ACCENT, fontsize=22, family="monospace")
        fig.text(0.62, 0.20, f"D ≈ {D_txt}", color=INK, fontsize=30, family="monospace")
        fig.text(0.62, 0.15, "the slope of the line is the fractal dimension", color=MUTED, fontsize=12)
        # attribution burned in
        fig.text(0.985, 0.02, ATTRIB, color=MUTED, fontsize=9, ha="right")

        frame = out_dir / f"frame_{i:02d}.png"
        fig.savefig(frame, facecolor=BG)
        plt.close(fig)
        print(f"  {frame.relative_to(config.ROOT)}   (ε={s}px, N={N})")

    print(f"\n{len(sizes)} frames -> {out_dir.relative_to(config.ROOT)}  (1920×1080, hold each ~1–1.5 s)")


def main() -> None:
    print("=" * 62)
    print("axis-fractal — Phase 9 video assets")
    print("=" * 62)
    video_style()
    render_boxcount()
    print("\nPhase 9 (box-counting animation) done.")


if __name__ == "__main__":
    main()
