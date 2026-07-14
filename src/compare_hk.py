"""
compare_hk.py — measure Hong Kong and set it beside Beijing.  [PHASE 8b]

Rasterizes the three HK sites (2 m/px, EPSG:2326), computes per-tile Dᵦ and Λ(r) with the
SAME functions used for Beijing, then compares:
  * within HK: Sham Shui Po (fine tong-lau) vs Tseung Kwan O (podium megastructure),
  * across cities: HK sites paired with their Beijing analogues by fabric type.

    Run it with:  python src/compare_hk.py

LIMITATION STATED UP FRONT
    This is 2D plan analysis. Hong Kong is extremely vertical; building HEIGHT is not captured.
    We measure the footprint/street plan texture, which is valid — verticality is out of scope.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box as sbox
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from rasterize import burn, street_width
from sampling import tile_metrics, iter_full_tiles, rank_biserial
from boxcount import load_binary
from viz import apply_style, INK, MUTED, FAINT, GRID

# fabric-type colours pair each HK site with its Beijing analogue
FABRIC_COLOR = {"vernacular": "#0072B2", "modern": "#D55E00", "heritage": "#009E73",
                "transitional": "#7a5195"}
HK_FABRIC = {"shamshuipo": "vernacular", "tseungkwano": "modern", "kathingwai": "heritage",
             "wanchai": "transitional"}
BJ_FABRIC = {"west": "vernacular", "east": "modern", "center": "heritage"}
HK_LABEL = {"shamshuipo": "HK · Sham Shui Po", "tseungkwano": "HK · Tseung Kwan O",
            "kathingwai": "HK · walled village", "wanchai": "HK · Wan Chai"}
BJ_LABEL = {"west": "BJ · hutong", "east": "BJ · commercial", "center": "BJ · Axis"}


def save_tif(arr, transform, path) -> None:
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype="uint8", crs=config.HONGKONG_CRS, transform=transform,
                       compress="lzw") as dst:
        dst.write(arr, 1)


def hk_grid(site: str):
    w, s, e, n = config.HONGKONG_SITES[site]
    b = gpd.GeoSeries([sbox(w, s, e, n)], crs=config.WGS84).to_crs(config.HONGKONG_CRS).total_bounds
    res = config.RASTER_RES_M
    minx, miny = np.floor(b[0] / res) * res, np.floor(b[1] / res) * res
    maxx, maxy = np.ceil(b[2] / res) * res, np.ceil(b[3] / res) * res
    shape = (int(round((maxy - miny) / res)), int(round((maxx - minx) / res)))
    return from_origin(minx, maxy, res, res), shape


def rasterize_site(site: str) -> None:
    transform, shape = hk_grid(site)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    st = gpd.read_file(config.DATA_RAW / f"hk_{site}_streets.gpkg", layer="edges")
    widths = st["highway"].map(street_width).values
    save_tif(burn(st.geometry.buffer(widths / 2, cap_style=2).values, transform, shape),
             transform, config.DATA_PROCESSED / f"hk_{site}_streets_2m.tif")
    bl = gpd.read_file(config.DATA_RAW / f"hk_{site}_buildings_overture.gpkg")
    save_tif(burn(bl.geometry.values, transform, shape),
             transform, config.DATA_PROCESSED / f"hk_{site}_footprints_2m.tif")


def measure_site(site: str) -> pd.DataFrame:
    rows = []
    for rep in ("streets", "footprints"):
        suffix = "streets_2m" if rep == "streets" else "footprints_2m"
        arr = load_binary(config.DATA_PROCESSED / f"hk_{site}_{suffix}.tif")
        for r, c, sub in iter_full_tiles(arr, config.TILE_PX):
            m = tile_metrics(sub)
            m.update({"unit": site, "rep": rep})
            rows.append(m)
    return pd.DataFrame(rows)


def cross_city_boxplot(bj: pd.DataFrame, hk: pd.DataFrame) -> None:
    """Footprint Λ(64 m) for the three fabric pairs, Beijing beside Hong Kong."""
    order = [("west", "bj"), ("shamshuipo", "hk"),      # vernacular pair
             ("east", "bj"), ("tseungkwano", "hk"),     # modern pair
             ("center", "bj"), ("kathingwai", "hk"),    # heritage pair
             ("wanchai", "hk")]                         # HK-only transitional context
    data, labels, colors = [], [], []
    for unit, city in order:
        src = bj if city == "bj" else hk
        col = "zone" if city == "bj" else "unit"
        v = src[(src.rep == "footprints") & (src[col] == unit)]["lam32"].dropna()
        data.append(v)
        labels.append((BJ_LABEL if city == "bj" else HK_LABEL)[unit].replace(" · ", "\n"))
        fab = (BJ_FABRIC if city == "bj" else HK_FABRIC)[unit]
        colors.append(FABRIC_COLOR[fab])
    fig, ax = plt.subplots(figsize=(11, 6))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6, showfliers=True,
                    flierprops=dict(marker="o", ms=3, mfc=FAINT, mec="none"),
                    medianprops=dict(color=INK, lw=2),
                    whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED))
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col); patch.set_alpha(0.35); patch.set_edgecolor(col)
    ax.set_ylim(0.9, 6.5)   # clip extreme void-edge outliers so the boxes are legible
    for i, v in enumerate(data):
        if len(v):
            ax.text(i + 1, 6.15, f"n={len(v)}", va="center", ha="center",
                    fontsize=8, color=MUTED)
            ax.text(i + 1, v.median(), f"{v.median():.2f}", va="bottom", ha="center",
                    fontsize=8.5, color=INK)
    for x in (2.5, 4.5, 6.5):
        ax.axvline(x, color=GRID, lw=1)
    for xc, fab in [(1.5, "vernacular"), (3.5, "modern"), (5.5, "heritage"), (7.0, "transitional")]:
        ax.text(xc, 6.38, fab, ha="center", color=FABRIC_COLOR[fab], fontsize=10)
    ax.set_ylabel("footprint Λ(64 m) per 500 m tile")
    ax.set_title("Two cities, three fabric types — neighbourhood-scale gappiness")
    ax.grid(axis="x", visible=False)
    fig.text(0.5, -0.02, "Higher = gappier / coarser grain. A few extreme void-edge outliers "
             "clipped. 2D plan analysis; Hong Kong's verticality is not captured.",
             ha="center", color=MUTED, fontsize=9)
    fig.savefig(config.FIGURES / "phase8_cross_city_lacunarity.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("  phase8_cross_city_lacunarity.png")


def main() -> None:
    apply_style()
    print("=" * 66)
    print("axis-fractal — Phase 8b Hong Kong measurement + cross-city comparison")
    print("=" * 66)
    hk = []
    for site in config.HONGKONG_SITES:
        rasterize_site(site)
        df = measure_site(site)
        hk.append(df)
        fp = df[df.rep == "footprints"]
        print(f"[{site:>12}] footprint tiles used {fp['Db'].notna().sum():>2}/{len(fp):>2}; "
              f"median Dᵦ={fp['Db'].median():.3f}, median Λ(64m)={fp['lam32'].median():.3f}")
    hk = pd.concat(hk, ignore_index=True)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    hk.round(5).to_csv(config.TABLES / "phase8_hk_tile_metrics.csv", index=False)

    # within-HK key contrast: Sham Shui Po (fine) vs Tseung Kwan O (podium)
    ssp = hk[(hk.unit == "shamshuipo") & (hk.rep == "footprints")]["lam32"].dropna()
    tko = hk[(hk.unit == "tseungkwano") & (hk.rep == "footprints")]["lam32"].dropna()
    U, p, r = rank_biserial(ssp, tko)
    print(f"\nSSP vs TKO footprint Λ(64m): medians {ssp.median():.3f} vs {tko.median():.3f}, "
          f"p={p:.4f}, effect r={r:.3f} ({'SSP<TKO' if ssp.median() < tko.median() else 'SSP>=TKO'})")

    # cross-city table + figure
    bj = pd.read_csv(config.TABLES / "phase5_tile_metrics.csv")
    _write_results(bj, hk, ssp, tko, p, r)
    cross_city_boxplot(bj, hk)
    print("\nPhase 8b done.")


def _median(df, unit, col, metric):
    v = df[(df.rep == "footprints") & (df[col] == unit)][metric].dropna()
    return v.median(), len(v)


def _write_results(bj, hk, ssp, tko, p, r) -> None:
    lines = ["\n## Phase 8b — Hong Kong measured + cross-city comparison (2026-07-14)\n",
             "Same pipeline (2 m/px, per-500 m-tile Dᵦ and Λ(r)) on the three HK sites; "
             "footprints from Overture. **2D plan analysis — HK verticality not captured.** "
             "Per-tile data `results/tables/phase8_hk_tile_metrics.csv`; figure "
             "`results/figures/phase8_cross_city_lacunarity.png`.\n",
             "**Footprint medians by fabric type (Dᵦ; Λ(64 m); n tiles):**\n",
             "| fabric | Beijing | Hong Kong |", "|---|---|---|"]
    pairs = [("vernacular", "west", "shamshuipo"), ("modern", "east", "tseungkwano"),
             ("heritage", "center", "kathingwai"), ("transitional", None, "wanchai")]
    for fab, bjz, hks in pairs:
        db_h, n_h = _median(hk, hks, "unit", "Db")
        la_h, _ = _median(hk, hks, "unit", "lam32")
        if bjz is None:
            bj_cell = "— (no Beijing analogue)"
        else:
            db_b, n_b = _median(bj, bjz, "zone", "Db")
            la_b, _ = _median(bj, bjz, "zone", "lam32")
            bj_cell = f"{BJ_LABEL[bjz]}: Dᵦ {db_b:.3f}, Λ {la_b:.3f} (n={n_b})"
        lines.append(f"| {fab} | {bj_cell} | "
                     f"{HK_LABEL[hks]}: Dᵦ {db_h:.3f}, Λ {la_h:.3f} (n={n_h}) |")
    mag = "negligible" if abs(r) < .1 else "small" if abs(r) < .3 else "medium" if abs(r) < .5 else "large"
    lines += ["",
              f"**Key HK contrast — Sham Shui Po (fine tong-lau) vs Tseung Kwan O (podium "
              f"megastructure), footprint Λ(64 m):** medians {ssp.median():.3f} vs "
              f"{tko.median():.3f}, Mann-Whitney p = {p:.4f}, effect r = {r:.3f} ({mag}). "
              + ("SSP is the finer/more-uniform fabric, TKO the gappier — as the eye predicts. "
                 if ssp.median() < tko.median() else
                 "Direction unexpected — see figure. ")
              + "Interpretation vs Beijing written up in the response, honestly.",
              "",
              "Kat Hing Wai (walled village) is a small-sample qualitative reference only "
              "(few dense tiles amid fields)."]
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("Appended to results/results.md.")


if __name__ == "__main__":
    main()
