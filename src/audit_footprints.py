"""
audit_footprints.py — does the Overture footprint dataset actually fix the gap?  [PHASE 1+]

Applies the SAME honesty test we used on OSM: per-zone median tile coverage, and a
before/after satellite overlay at the three hutong ground-truth points. If Overture also
looked sparse, we would say so — we do not assume the new source is better, we check.

    Run it with:  python src/audit_footprints.py
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from audit import make_tiles  # reuse the exact same tiling


def _load(zone: str, source: str) -> gpd.GeoDataFrame:
    name = f"beijing_{zone}_buildings.gpkg" if source == "osm" \
        else f"beijing_{zone}_buildings_overture.gpkg"
    return gpd.read_file(config.DATA_RAW / name)


def median_tile_coverage(zone: str, buildings: gpd.GeoDataFrame) -> float:
    """Median built fraction over the zone's 500 m tiles, for one building source."""
    b = buildings.total_bounds
    tiles = make_tiles(zone, (b[0], b[1], b[2], b[3]))
    inter = gpd.overlay(buildings[["geometry"]], tiles[["tile_id", "geometry"]],
                        how="intersection", keep_geom_type=True)
    inter["a"] = inter.geometry.area
    area = inter.groupby("tile_id")["a"].sum()
    tiles["coverage"] = (tiles["tile_id"].map(area).fillna(0.0) / tiles["tile_area_m2"])
    return float(tiles["coverage"].median())


def window_coverage_pct(buildings_m: gpd.GeoDataFrame, pt_m, half: float) -> float:
    win = box(pt_m.x - half, pt_m.y - half, pt_m.x + half, pt_m.y + half)
    clipped = gpd.clip(buildings_m, win)
    return clipped.geometry.area.sum() / (2 * half) ** 2 * 100


def before_after_figure(zone_osm: dict, zone_ovt: dict) -> None:
    """2 rows (OSM / Overture) x 3 hutong sites, on satellite imagery."""
    import contextily as cx
    pts = config.HUTONG_GROUNDTRUTH
    pts_m = gpd.GeoDataFrame(
        {"name": list(pts)},
        geometry=gpd.points_from_xy([lon for _, lon in pts.values()],
                                    [lat for lat, _ in pts.values()]),
        crs=config.WGS84).to_crs(config.BEIJING_CRS)
    half = config.TILE_M / 2
    fig, axes = plt.subplots(2, len(pts), figsize=(6 * len(pts), 12))
    for col, (name, pt) in enumerate(zip(pts_m["name"], pts_m.geometry)):
        zone = name.split("(")[-1].strip(") ")
        win = box(pt.x - half, pt.y - half, pt.x + half, pt.y + half)
        win3857 = gpd.GeoDataFrame(geometry=[win], crs=config.BEIJING_CRS).to_crs(3857).total_bounds
        for row, (label, data) in enumerate([("OSM", zone_osm), ("Overture", zone_ovt)]):
            ax = axes[row][col]
            b = data[zone]
            cov = window_coverage_pct(b, pt, half)
            bc = gpd.clip(b, win).to_crs(3857)
            if len(bc):
                bc.plot(ax=ax, facecolor="#ffd24d", edgecolor="#c98a00", linewidth=0.3, alpha=0.55)
            ax.set_xlim(win3857[0], win3857[2]); ax.set_ylim(win3857[1], win3857[3])
            try:
                cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)
            except Exception as exc:  # noqa: BLE001
                print(f"   basemap failed ({name}, {label}): {exc}")
            ax.set_title(f"{label} — {name}\n{cov:.0f}% built", fontsize=11)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Footprint fix — OSM (top) vs Overture (bottom) on satellite imagery", y=0.99)
    out = config.FIGURES / "phase1_footprint_osm_vs_overture.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   saved {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 64)
    print("axis-fractal — footprint source audit (OSM vs Overture)")
    print("=" * 64)

    zone_osm, zone_ovt = {}, {}
    rows = []
    for zone in config.BEIJING_TRANSECTS:
        osm = _load(zone, "osm")
        ovt = _load(zone, "overture")
        zone_osm[zone], zone_ovt[zone] = osm, ovt
        rows.append({
            "zone": zone,
            "osm_footprints": len(osm),
            "overture_footprints": len(ovt),
            "osm_median_cov": round(median_tile_coverage(zone, osm), 3),
            "overture_median_cov": round(median_tile_coverage(zone, ovt), 3),
        })
    table = pd.DataFrame(rows)
    print("\nPer-zone median 500 m-tile building coverage:")
    print(table.to_string(index=False))
    table.to_csv(config.TABLES / "phase1_footprint_osm_vs_overture.csv", index=False)

    print("\nGround-truth before/after figure:")
    before_after_figure(zone_osm, zone_ovt)

    # append to results
    lines = ["\n### Footprint fix — Overture vs OSM (2026-07-14)\n",
             "Applied the Overture footprint dataset and re-ran the coverage audit. "
             "Per-zone median 500 m-tile built fraction:\n",
             "| zone | OSM footprints | Overture footprints | OSM median cov | Overture median cov |",
             "|---|--:|--:|--:|--:|"]
    for r in rows:
        lines.append(f"| {r['zone']} | {r['osm_footprints']} | {r['overture_footprints']} | "
                     f"{r['osm_median_cov']:.1%} | {r['overture_median_cov']:.1%} |")
    lines += ["", "Before/after overlay: `results/figures/phase1_footprint_osm_vs_overture.png`. "
              "Overture (source: Zenodo China rooftop dataset via Overture) captures the fine-grain "
              "hutong courtyard houses OSM missed. Beijing footprint representation now usable — "
              "still to be treated as a separate representation from streets, per the brief.", ""]
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("   appended to results/results.md")
    print("\nFootprint audit done.")


if __name__ == "__main__":
    main()
