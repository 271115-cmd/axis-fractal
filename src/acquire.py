"""
acquire.py — download the raw map data.  [PHASE 1]

WHAT THIS MODULE DOES
    For each Beijing transect (west / center / east) defined in config.py it:
      1. downloads the OSM street network (lines) and building footprints (polygons),
      2. projects both from WGS-84 degrees into metres (EPSG:32650, our Beijing CRS),
      3. saves each layer to data/raw/ as a GeoPackage (.gpkg) so we never re-download,
      4. prints an honest per-zone summary and draws one overview map for a visual check.

    Run it with one command (from the repo root, venv active):
        python src/acquire.py

KEY IDEA FOR THE BEGINNER
    OpenStreetMap is stored in WGS-84 (lat/lon degrees). Degrees are useless for measuring
    lengths and areas, so the very first thing we do after downloading is PROJECT to a metric
    CRS (metres). No GCJ-02 correction is applied — OSM is already WGS-84 in China. (parameters.md)
"""
from __future__ import annotations

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # save figures to files; no interactive window
import matplotlib.pyplot as plt
import osmnx as ox

import config


# --- helpers ---------------------------------------------------------------------------

def _sanitize_for_gpkg(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Make an OSM GeoDataFrame safe to write to GeoPackage.

    OSM tags sometimes arrive as Python lists (e.g. a way with two 'highway' values) and the
    GeoPackage format cannot store a list in a cell. We flatten any list/dict/set cell to a
    string. We also move the (element, id) index into ordinary columns so it is preserved.
    """
    gdf = gdf.reset_index()
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        if gdf[col].apply(lambda v: isinstance(v, (list, dict, set))).any():
            gdf[col] = gdf[col].apply(
                lambda v: "; ".join(map(str, v)) if isinstance(v, (list, set))
                else (str(v) if isinstance(v, dict) else v)
            )
    return gdf


def download_transect(name: str, bbox: tuple[float, float, float, float]):
    """Download + project streets and buildings for one transect. Returns (edges, buildings)."""
    print(f"\n[{name}]  bbox (W,S,E,N) = {bbox}")

    # --- streets: download as a graph, then project the whole graph to metres ---
    graph = ox.graph_from_bbox(bbox, network_type=config.NETWORK_TYPE)
    graph = ox.project_graph(graph, to_crs=config.BEIJING_CRS)
    # A two-way street is stored as TWO directed edges (one per direction). For measuring
    # physical street geometry we want the UNDIRECTED graph, or we'd count every two-way
    # street — and its length — twice. This matches what we save below (directed=False).
    edges = ox.graph_to_gdfs(ox.convert.to_undirected(graph), nodes=False, edges=True)
    print(f"       streets:   {len(edges):>6} segments (undirected), "
          f"{edges['length'].sum() / 1000:.1f} km total length")

    # --- buildings: download footprints, project, keep only polygons ---
    try:
        buildings = ox.features_from_bbox(bbox, tags={"building": True})
        buildings = buildings.to_crs(config.BEIJING_CRS)
        buildings = buildings[buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        area_km2 = buildings.geometry.area.sum() / 1_000_000
        print(f"       buildings: {len(buildings):>6} footprints, "
              f"{area_km2:.3f} km² total roof area")
    except Exception as exc:  # noqa: BLE001 — report honestly, never fake data
        print(f"       buildings: FAILED to download ({exc}). Saving streets only.")
        buildings = gpd.GeoDataFrame(geometry=[], crs=config.BEIJING_CRS)

    # --- save both to data/raw/ ---
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    streets_path = config.DATA_RAW / f"beijing_{name}_streets.gpkg"
    ox.save_graph_geopackage(graph, filepath=streets_path, directed=False)
    if len(buildings):
        buildings_path = config.DATA_RAW / f"beijing_{name}_buildings.gpkg"
        _sanitize_for_gpkg(buildings).to_file(buildings_path, driver="GPKG")
    print(f"       saved -> {streets_path.name}" + (f" + beijing_{name}_buildings.gpkg" if len(buildings) else ""))

    return edges, buildings


def make_overview_map(collected: dict) -> None:
    """Draw all three transects (streets + buildings) on one map for a visual sanity check."""
    colors = {"west": "#2b8cbe", "center": "#e34a33", "east": "#31a354"}
    fig, ax = plt.subplots(figsize=(9, 10))
    for name, (edges, buildings) in collected.items():
        if len(buildings):
            buildings.plot(ax=ax, color=colors[name], alpha=0.35, edgecolor="none")
        edges.plot(ax=ax, color=colors[name], linewidth=0.3)
    # a proxy legend
    handles = [plt.Line2D([0], [0], color=c, lw=3, label=n.capitalize())
               for n, c in colors.items()]
    ax.legend(handles=handles, title="Transect", loc="upper right", frameon=False)
    ax.set_title("Phase 1 — Beijing study area: three N-S transects (EPSG:32650, metres)")
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase1_transects_overview.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nOverview map saved -> {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 64)
    print("axis-fractal — Phase 1 acquisition (Beijing transects)")
    print(f"Downloading from OpenStreetMap; projecting to {config.BEIJING_CRS}")
    print("=" * 64)
    collected = {}
    rows = []
    for name, bbox in config.BEIJING_TRANSECTS.items():
        edges, buildings = download_transect(name, bbox)
        collected[name] = (edges, buildings)
        rows.append({
            "zone": name,
            "street_segments": len(edges),
            "street_length_km": round(edges["length"].sum() / 1000, 2),
            "building_footprints": len(buildings),
            "building_area_km2": round(buildings.geometry.area.sum() / 1_000_000, 4) if len(buildings) else 0.0,
        })

    # a tidy summary table, printed and saved for the record
    summary = gpd.pd.DataFrame(rows)
    print("\n" + "=" * 64)
    print("SUMMARY (what actually downloaded — real counts, nothing invented):")
    print(summary.to_string(index=False))
    config.TABLES.mkdir(parents=True, exist_ok=True)
    summary.to_csv(config.TABLES / "phase1_acquire_summary.csv", index=False)
    print(f"\nSummary table saved -> results/tables/phase1_acquire_summary.csv")

    make_overview_map(collected)
    print("\nPhase 1 acquisition done. Next: the completeness AUDIT (audit.py).")


if __name__ == "__main__":
    main()
