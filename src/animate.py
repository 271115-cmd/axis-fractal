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
from boxcount import load_binary
from lacunarity import lacunarity_at

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


def tile_by_index(fname: str, tile_row: int, tile_col: int, size: int = config.TILE_PX) -> np.ndarray:
    """Crop the (tile_row, tile_col) 500 m tile from a processed raster — same tiling as Phase 5,
    so we can select a tile that is *representative* of a zone's reported median lacunarity."""
    with rasterio.open(config.DATA_PROCESSED / fname) as src:
        arr = (src.read(1) > 0).astype(np.uint8)
    r0, c0 = tile_row * size, tile_col * size
    return arr[r0:r0 + size, c0:c0 + size]


def render_gliding_box(episode: str = "ep2_gliding_box_lacunarity") -> None:
    """A box glides across a fine-grain tile vs a megastructure tile; live mass + running Λ.

    On the fine grain the captured mass barely changes (low lacunarity); on the megastructure
    it lurches between a full podium and an empty gap (high lacunarity). Same box, same sweep.
    """
    from matplotlib.patches import Rectangle
    r, step, size = 32, 20, config.TILE_PX          # 32 px box = 64 m (the headline scale); 250 px tile
    # tiles chosen to be REPRESENTATIVE of each zone's reported median Λ(64 m):
    #   Beijing west tile (14,1) → Λ≈1.21 (median 1.21);  HK TKO tile (2,3) → Λ≈3.05 (median 2.92)
    cols = [
        ("Beijing · hutong (fine grain)", tile_by_index("beijing_west_footprints_2m.tif", 14, 1)),
        ("Hong Kong · Tseung Kwan O (megastructure)", tile_by_index("hk_tseungkwano_footprints_2m.tif", 2, 3)),
    ]
    true_lam = [lacunarity_at(a, r) for _, a in cols]
    struct_cmap = ListedColormap([BG, STRUCT])
    positions = [(rr, cc) for rr in range(0, size - r + 1, step)
                 for cc in range(0, size - r + 1, step)]
    series = [[] for _ in cols]

    out_dir = config.RESULTS / "video_assets" / episode
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (rr, cc) in enumerate(positions):
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        fig.text(0.5, 0.95, "LACUNARITY — how gappy is the fabric?", color=INK, fontsize=20,
                 ha="center", family="monospace")
        for j, (x0, (label, arr)) in enumerate(zip([0.04, 0.54], cols)):
            m = int(arr[rr:rr + r, cc:cc + r].sum())
            series[j].append(m)
            ms = np.array(series[j], float)
            run = float((ms ** 2).mean() / ms.mean() ** 2) if ms.mean() > 0 else float("nan")

            axImg = fig.add_axes([x0, 0.40, 0.42, 0.46])
            axImg.imshow(arr, cmap=struct_cmap, interpolation="nearest")
            axImg.add_patch(Rectangle((cc - 0.5, rr - 0.5), r, r, fill=True,
                                      facecolor=ACCENT, alpha=0.20, edgecolor=ACCENT, lw=2.5))
            axImg.set_xlim(-0.5, size - 0.5); axImg.set_ylim(size - 0.5, -0.5)
            axImg.set_xticks([]); axImg.set_yticks([])
            fig.text(x0, 0.885, label, color=INK, fontsize=15)
            fig.text(x0, 0.345, f"box mass m = {m:<5}   Λ ≈ {run:.2f}  (measured {true_lam[j]:.2f})",
                     color=ACCENT, fontsize=15, family="monospace")

            axSpark = fig.add_axes([x0, 0.13, 0.42, 0.17])
            axSpark.plot(series[j], color=ACCENT, lw=2)
            axSpark.set_ylim(0, r * r); axSpark.set_xlim(0, len(positions))
            axSpark.set_title("box mass as the box glides  (flat = uniform, jagged = gappy)",
                              color=MUTED, fontsize=11)
            axSpark.set_yticks([]); axSpark.set_xticks([])
        fig.text(0.985, 0.02, ATTRIB, color=MUTED, fontsize=9, ha="right")
        fig.savefig(out_dir / f"frame_{i:03d}.png", facecolor=BG)
        plt.close(fig)
    print(f"  {len(positions)} frames -> {out_dir.relative_to(config.ROOT)}  "
          f"(hutong Λ={true_lam[0]:.2f} stays low, TKO Λ={true_lam[1]:.2f} lurches high)")


def render_maps() -> None:
    """High-res dark figure-ground maps of each transect/site, attribution burned in."""
    out_dir = config.RESULTS / "video_assets" / "maps"
    out_dir.mkdir(parents=True, exist_ok=True)
    struct_cmap = ListedColormap([BG, STRUCT])
    jobs = [
        ("Beijing · West (hutong)", "beijing_west_footprints_2m.tif"),
        ("Beijing · Center (Axis)", "beijing_center_footprints_2m.tif"),
        ("Beijing · East (commercial)", "beijing_east_footprints_2m.tif"),
        ("Hong Kong · Sham Shui Po (tong lau)", "hk_shamshuipo_footprints_2m.tif"),
        ("Hong Kong · Tseung Kwan O (podium towers)", "hk_tseungkwano_footprints_2m.tif"),
        ("Hong Kong · Kat Hing Wai (walled village)", "hk_kathingwai_footprints_2m.tif"),
        ("Hong Kong · Wan Chai (mixed)", "hk_wanchai_footprints_2m.tif"),
    ]
    for title, fname in jobs:
        arr = load_binary(config.DATA_PROCESSED / fname)
        H, W = arr.shape
        long_in = 12.0
        figsize = (long_in * W / H, long_in) if H >= W else (long_in, long_in * H / W)
        fig, ax = plt.subplots(figsize=figsize, dpi=150)
        fig.subplots_adjust(0, 0, 1, 1)
        ax.imshow(arr, cmap=struct_cmap, interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.plot([20, 20 + 250], [H - 25, H - 25], color=INK, lw=3)  # 500 m
        ax.text(20, H - 45, "500 m", color=INK, fontsize=10)
        ax.text(20, 55, title, color=INK, fontsize=14)
        ax.text(W - 15, H - 12, ATTRIB, color=MUTED, fontsize=8, ha="right")
        slug = fname.replace("_footprints_2m.tif", "")
        fig.savefig(out_dir / f"map_{slug}.png", facecolor=BG)
        plt.close(fig)
        print(f"  map_{slug}.png")
    print(f"maps -> {out_dir.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 62)
    print("axis-fractal — Phase 9 video assets")
    print("=" * 62)
    video_style()
    print("[1/3] box-counting animation")
    render_boxcount()
    print("[2/3] gliding-box lacunarity animation")
    render_gliding_box()
    print("[3/3] figure-ground map renders")
    render_maps()
    print("\nPhase 9 video assets done.")


if __name__ == "__main__":
    main()
