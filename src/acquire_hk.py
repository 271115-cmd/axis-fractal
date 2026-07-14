"""
acquire_hk.py — Hong Kong data acquisition + coverage check.  [PHASE 8]

Reuses the exact Beijing recipe (streets from OSM, footprints from Overture — the SAME
sources, for a fair cross-city comparison) but projects to EPSG:2326 (Hong Kong 1980 Grid)
and downloads the three district sample boxes instead of transects. Then it checks coverage:
per-site built fraction + a satellite ground-truth overlay (the brief claims HK coverage is
strong — we verify rather than assume, exactly as we did for Beijing).

    Run it with:  python src/acquire_hk.py
"""
from __future__ import annotations

import subprocess

import geopandas as gpd
import osmnx as ox
from shapely.geometry import box as sbox
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from acquire_footprints import OVERTURE, KEEP_COLS

HK_GROUNDTRUTH = {
    "Sham Shui Po · tong lau": (22.3306, 114.1625),
    "Tseung Kwan O · podium towers": (22.3072, 114.2595),
}


def download_streets(site: str, bbox) -> gpd.GeoDataFrame:
    graph = ox.graph_from_bbox(bbox, network_type=config.NETWORK_TYPE)
    graph = ox.project_graph(graph, to_crs=config.HONGKONG_CRS)
    edges = ox.graph_to_gdfs(ox.convert.to_undirected(graph), nodes=False, edges=True)
    ox.save_graph_geopackage(graph, filepath=config.DATA_RAW / f"hk_{site}_streets.gpkg",
                             directed=False)
    return edges


def download_footprints(site: str, bbox) -> gpd.GeoDataFrame:
    w, s, e, n = bbox
    tmp = config.DATA_RAW / f"_ovt_hk_{site}.geojson"
    subprocess.run([str(OVERTURE), "download", f"--bbox={w},{s},{e},{n}",
                    "-f", "geojson", "--type=building", "-o", str(tmp)], check=True)
    g = gpd.read_file(tmp)
    if g.crs is None:
        g = g.set_crs(config.WGS84)
    g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(config.HONGKONG_CRS)
    cols = [c for c in KEEP_COLS if c in g.columns] + ["geometry"]
    g[cols].to_file(config.DATA_RAW / f"hk_{site}_buildings_overture.gpkg", driver="GPKG")
    tmp.unlink(missing_ok=True)
    return g[cols]


def box_area_km2(bbox) -> float:
    return float(gpd.GeoSeries([sbox(*bbox)], crs=config.WGS84)
                 .to_crs(config.HONGKONG_CRS).area.iloc[0] / 1e6)


def overview_map(collected: dict) -> None:
    fig, axes = plt.subplots(1, len(collected), figsize=(5 * len(collected), 6))
    for ax, (site, (edges, blds)) in zip(axes, collected.items()):
        if len(blds):
            blds.plot(ax=ax, color="#D55E00", alpha=0.5, edgecolor="none")
        edges.plot(ax=ax, color="#1a1a1a", linewidth=0.3)
        ax.set_title(site, fontsize=11)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Phase 8 — Hong Kong sample sites (streets + Overture footprints, EPSG:2326)", y=1.0)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase8_hk_sites_overview.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview map -> {out.relative_to(config.ROOT)}")


def groundtruth(collected: dict) -> None:
    try:
        import contextily as cx
    except Exception as exc:  # noqa: BLE001
        print(f"contextily unavailable ({exc}); skipping satellite overlay")
        return
    site_of = {"Sham Shui Po · tong lau": "shamshuipo",
               "Tseung Kwan O · podium towers": "tseungkwano"}
    pts = gpd.GeoDataFrame(
        {"name": list(HK_GROUNDTRUTH)},
        geometry=gpd.points_from_xy([lon for _, lon in HK_GROUNDTRUTH.values()],
                                    [lat for lat, _ in HK_GROUNDTRUTH.values()]),
        crs=config.WGS84).to_crs(config.HONGKONG_CRS)
    half = config.TILE_M / 2
    fig, axes = plt.subplots(1, len(pts), figsize=(6 * len(pts), 6))
    for ax, (name, pm) in zip(axes, zip(pts["name"], pts.geometry)):
        blds = collected[site_of[name]][1]
        win = sbox(pm.x - half, pm.y - half, pm.x + half, pm.y + half)
        cov = gpd.clip(blds, win).area.sum() / (config.TILE_M ** 2) * 100
        b3857 = gpd.GeoDataFrame(geometry=[win], crs=config.HONGKONG_CRS).to_crs(3857)
        gpd.clip(blds, win).to_crs(3857).plot(ax=ax, facecolor="#ffd24d",
                                              edgecolor="#c98a00", lw=0.3, alpha=0.55)
        xmin, ymin, xmax, ymax = b3857.total_bounds
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)
        except Exception as exc:  # noqa: BLE001
            print(f"  basemap failed for {name}: {exc}")
        ax.set_title(f"{name}\nOverture {cov:.0f}% built", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Phase 8 — HK footprint coverage vs satellite (Overture, yellow)", y=1.02)
    out = config.FIGURES / "phase8_hk_groundtruth.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Ground-truth -> {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 66)
    print("axis-fractal — Phase 8 Hong Kong acquisition + coverage check")
    print(f"Projecting to {config.HONGKONG_CRS} (Hong Kong 1980 Grid)")
    print("=" * 66)
    collected, rows = {}, []
    for site, bbox in config.HONGKONG_SITES.items():
        print(f"\n[{site}]  bbox {bbox}")
        edges = download_streets(site, bbox)
        blds = download_footprints(site, bbox)
        collected[site] = (edges, blds)
        area = box_area_km2(bbox)
        roof = blds.area.sum() / 1e6
        print(f"   streets {len(edges)} segs, {edges['length'].sum()/1000:.1f} km | "
              f"footprints {len(blds)}, {roof:.3f} km² roof over {area:.2f} km² box "
              f"({roof/area*100:.0f}% built)")
        rows.append({"site": site, "street_segments": len(edges),
                     "street_km": round(edges["length"].sum() / 1000, 1),
                     "footprints": len(blds), "roof_km2": round(roof, 3),
                     "box_km2": round(area, 2), "built_pct": round(roof / area * 100, 1)})

    summary = gpd.pd.DataFrame(rows)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    summary.to_csv(config.TABLES / "phase8_hk_acquire_summary.csv", index=False)
    print("\nSUMMARY (real counts):")
    print(summary.to_string(index=False))

    overview_map(collected)
    groundtruth(collected)

    (config.RESULTS / "results.md").open("a", encoding="utf-8").write(
        "\n## Phase 8 — Hong Kong data acquired + coverage check (2026-07-14)\n\n"
        "Three district sample boxes (NOT transects — HK has no axis): Sham Shui Po tong-lau, "
        "Tseung Kwan O podium towers, Kat Hing Wai walled village. Streets = OSM, footprints = "
        "Overture (same sources as Beijing), projected to EPSG:2326. Real counts in "
        "`results/tables/phase8_hk_acquire_summary.csv`; overview "
        "`results/figures/phase8_hk_sites_overview.png`; satellite ground-truth "
        "`results/figures/phase8_hk_groundtruth.png`.\n\n"
        "| site | streets (km) | footprints | roof km² | box km² | % built |\n"
        "|---|--:|--:|--:|--:|--:|\n"
        + "".join(f"| {r['site']} | {r['street_km']} | {r['footprints']} | {r['roof_km2']} | "
                  f"{r['box_km2']} | {r['built_pct']} |\n" for r in rows) + "\n"
        "Caveat: Kat Hing Wai is a ~1 ha walled village; its box is mostly village+field, so it "
        "yields few dense tiles — a small-sample qualitative reference, not a full distribution.\n")
    print("\nPhase 8 acquisition done.")


if __name__ == "__main__":
    main()
