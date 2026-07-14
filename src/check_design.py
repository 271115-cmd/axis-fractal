"""
check_design.py — score a design against the measured fabric benchmarks.  [PHASE 10]

The analysis-to-design loop: model an infill design in Grasshopper, export its footprints
(GeoJSON) or a plan image (PNG), and run this. It rasterizes the design at the project's
standard 2 m/pixel, computes its box-counting dimension Dᵦ and lacunarity curve Λ(r), and
compares them to the REAL per-tile benchmarks from Phases 5 and 8 — so you can re-tune the
design toward a target texture (e.g. hutong fine grain Λ(64 m) ≈ 1.2, not megastructure ≈ 3.0).

    python src/check_design.py my_design.geojson --target hutong
    python src/check_design.py plan.png --res 2 --target tonglau

Benchmarks are computed live from results/tables/, so they always match the study.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.transform import from_origin
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from rasterize import burn
from boxcount import box_counts, fit_dimension
from lacunarity import lacunarity_at
import viz

LAC_R = config.TILE_LAC_RADII                     # [4,8,16,32,64] px = [8,16,32,64,128] m
HEADLINE_R = 32                                   # 64 m — the paper's headline scale
# friendly target name -> (source table, key, label)
TARGETS = {
    "hutong": ("bj", "west", "Beijing hutong (fine)"),
    "axis": ("bj", "center", "Beijing Axis"),
    "commercial": ("bj", "east", "Beijing commercial"),
    "tonglau": ("hk", "shamshuipo", "HK Sham Shui Po (fine)"),
    "ssp": ("hk", "shamshuipo", "HK Sham Shui Po (fine)"),
    "megastructure": ("hk", "tseungkwano", "HK Tseung Kwan O (podium)"),
    "tko": ("hk", "tseungkwano", "HK Tseung Kwan O (podium)"),
}


def load_benchmarks() -> dict:
    """Per-zone median Dᵦ and Λ(r) curve, computed from the saved per-tile tables."""
    bench = {}
    for tbl, keycol, tag in [("phase5_tile_metrics.csv", "zone", "bj"),
                             ("phase8_hk_tile_metrics.csv", "unit", "hk")]:
        df = pd.read_csv(config.TABLES / tbl)
        fp = df[df.rep == "footprints"]
        for key, grp in fp.groupby(keycol):
            bench[(tag, key)] = {
                "Db": grp["Db"].median(),
                "lam": {r: grp[f"lam{r}"].median() for r in LAC_R},
            }
    return bench


def rasterize_design(path: Path, crs_override: str | None, res: float) -> np.ndarray:
    """Rasterize a design (GeoJSON polygons OR a plan image) to a binary 2 m/px array."""
    if path.suffix.lower() in (".geojson", ".json", ".gpkg", ".shp"):
        g = gpd.read_file(path)
        if crs_override:
            g = g.set_crs(crs_override, allow_override=True)
        if g.crs is None:
            raise SystemExit("Design has no CRS — pass --crs (e.g. --crs EPSG:2326).")
        if g.crs.is_geographic:                      # degrees -> project to metres
            g = g.to_crs(g.estimate_utm_crs())
        minx, miny, maxx, maxy = g.total_bounds
        w = int(np.ceil((maxx - minx) / res)); h = int(np.ceil((maxy - miny) / res))
        transform = from_origin(minx, maxy, res, res)
        return burn(g.geometry.values, transform, (h, w))
    # else: a plan image — grayscale, threshold; res is m/pixel (default 2)
    img = plt.imread(path)
    if img.ndim == 3:
        img = img[..., :3].mean(axis=2)
    return (img > 0.5 * img.max()).astype(np.uint8)


def design_metrics(arr: np.ndarray) -> dict:
    H, W = arr.shape
    sizes = np.array([s for s in config.TILE_BOX_SIZES if s <= min(H, W) // 2] or [1, 2, 4])
    counts = box_counts(arr, list(sizes))
    lo = max(2, config.TILE_BOX_FIT_MIN_PX); hi = min(config.TILE_BOX_FIT_MAX_PX, int(sizes.max()))
    fit = fit_dimension(sizes, counts, lo, hi)
    return {"Db": fit["D"], "r2": fit["r2"], "built": float(arr.mean()),
            "lam": {r: lacunarity_at(arr, r) for r in LAC_R}, "shape": (H, W)}


def report(dm: dict, bench: dict, target: str | None, out_png: Path) -> None:
    dh = dm["lam"][HEADLINE_R]
    print("\n" + "=" * 60)
    print("DESIGN CHECK")
    print("=" * 60)
    print(f"raster {dm['shape'][1]}×{dm['shape'][0]} px @ 2 m  ·  {dm['built']:.0%} built  ·  "
          f"fit R²={dm['r2']:.3f}")
    print(f"  Dᵦ            = {dm['Db']:.3f}")
    print(f"  Λ(64 m)       = {dh:.3f}   (higher = gappier / coarser grain)")

    print("\nvs measured benchmarks (Λ(64 m) | Dᵦ):")
    ranked = sorted(bench.items(), key=lambda kv: abs(kv[1]["lam"][HEADLINE_R] - dh))
    for (tag, key), b in ranked:
        near = "  <- closest" if (tag, key) == ranked[0][0] else ""
        print(f"  {tag}:{key:<12} Λ={b['lam'][HEADLINE_R]:.2f}  Dᵦ={b['Db']:.2f}{near}")

    if target:
        if target not in TARGETS:
            print(f"\nunknown --target '{target}'. options: {', '.join(sorted(TARGETS))}")
        else:
            tag, key, label = TARGETS[target]
            tb = bench[(tag, key)]["lam"][HEADLINE_R]
            diff = dh - tb
            verdict = ("on target" if abs(diff) < 0.15 else
                       "TOO GAPPY — merge masses / break up large voids / add fine infill"
                       if diff > 0 else
                       "TOO UNIFORM — introduce courtyards/setbacks to open the grain")
            print(f"\nTarget: {label}  Λ(64 m)={tb:.2f}")
            print(f"  your design Λ(64 m)={dh:.2f}  (Δ={diff:+.2f})  ->  {verdict}")

    # comparison plot: design Λ(r) over benchmark curves
    viz.apply_style()
    fig, ax = plt.subplots(figsize=(7.5, 5))
    xm = [r * config.RASTER_RES_M for r in LAC_R]
    anchors = {("bj", "west"): "hutong (finest)", ("hk", "tseungkwano"): "megastructure (coarsest)"}
    for (tag, key), b in bench.items():
        ax.plot(xm, [b["lam"][r] for r in LAC_R], color=viz.FAINT, lw=1.2, zorder=2)
        if (tag, key) in anchors:   # label only the two reference extremes to avoid clutter
            ax.text(xm[-1] * 1.02, b["lam"][LAC_R[-1]], anchors[(tag, key)],
                    color=viz.MUTED, fontsize=8, va="center")
    ax.plot(xm, [dm["lam"][r] for r in LAC_R], color="#D55E00", lw=2.6, marker="o", zorder=4, label="your design")
    ax.set_xscale("log", base=2); ax.set_xlabel("box size r (m)"); ax.set_ylabel("Λ(r)")
    ax.set_title("Design lacunarity vs measured fabric benchmarks")
    ax.legend(loc="upper right")
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\ncurve comparison saved -> {out_png.relative_to(config.ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Score a design's texture against measured benchmarks.")
    ap.add_argument("design", help="GeoJSON of footprints, or a plan image (PNG)")
    ap.add_argument("--crs", default=None, help="CRS of the design if the file lacks one (e.g. EPSG:2326)")
    ap.add_argument("--res", type=float, default=config.RASTER_RES_M, help="m/pixel for image input")
    ap.add_argument("--target", default=None, help=f"tune toward: {', '.join(sorted(TARGETS))}")
    args = ap.parse_args()

    arr = rasterize_design(Path(args.design), args.crs, args.res)
    if arr.sum() == 0:
        raise SystemExit("Rasterized design is empty — check the input/CRS/resolution.")
    dm = design_metrics(arr)
    out_png = config.FIGURES / f"phase10_designcheck_{Path(args.design).stem}.png"
    report(dm, load_benchmarks(), args.target, out_png)


if __name__ == "__main__":
    main()
