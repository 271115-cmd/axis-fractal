"""
audit.py — data completeness audit.  [PHASE 1]

WHAT THIS MODULE DOES
    Before we trust any fractal number, it asks: is the OSM data actually complete enough?
    For each transect it:
      1. cuts the zone into 500 m tiles,
      2. measures, per tile, street length + building footprint count + built-area coverage,
      3. draws density heatmaps so gaps are visible,
      4. overlays OSM on SATELLITE imagery at three known hutong spots (the decisive check),
      5. flags low-coverage tiles and, if needed, writes a QGIS hand-digitizing template,
      6. writes an honest assessment (numbers only — the human makes the final call) to results.

    Run it with:  python src/audit.py

KEY IDEA FOR THE BEGINNER
    "Coverage" here means: of a tile's 500x500 m area, what fraction is covered by mapped
    building footprints? Dense hutong fabric is ~40-70% built. If a tile we KNOW is hutong
    reads near 0%, OSM is probably missing data there — and the satellite overlay will show it.
"""
from __future__ import annotations

import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config


# --- load ---------------------------------------------------------------------------------

def load_zone(zone: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Read the streets (edges) and buildings we saved in Phase 1 for one zone."""
    streets = gpd.read_file(config.DATA_RAW / f"beijing_{zone}_streets.gpkg", layer="edges")
    buildings = gpd.read_file(config.DATA_RAW / f"beijing_{zone}_buildings.gpkg")
    return streets, buildings


# --- tiling -------------------------------------------------------------------------------

def make_tiles(zone: str, bounds_m: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Partition a zone's metric bounding box into TILE_M tiles (edge tiles may be smaller).

    We snap the grid to a global 500 m origin so tiles line up in neat rows across all three
    zones when we plot them together.
    """
    minx, miny, maxx, maxy = bounds_m
    t = config.TILE_M
    x0 = np.floor(minx / t) * t
    y0 = np.floor(miny / t) * t
    polys, ids, rows, cols = [], [], [], []
    nx = int(np.ceil((maxx - x0) / t))
    ny = int(np.ceil((maxy - y0) / t))
    for i in range(nx):
        for j in range(ny):
            # clip each tile to the zone box so tiles never spill past the transect edge
            tile = box(x0 + i * t, y0 + j * t, x0 + (i + 1) * t, y0 + (j + 1) * t)
            tile = tile.intersection(box(minx, miny, maxx, maxy))
            if tile.is_empty or tile.area < 1.0:
                continue
            polys.append(tile)
            ids.append(f"{zone}_{i:02d}_{j:02d}")
            rows.append(j)
            cols.append(i)
    tiles = gpd.GeoDataFrame(
        {"tile_id": ids, "zone": zone, "row": rows, "col": cols},
        geometry=polys, crs=config.BEIJING_CRS,
    )
    tiles["tile_area_m2"] = tiles.geometry.area
    return tiles


# --- per-tile metrics ---------------------------------------------------------------------

def tile_metrics(streets: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame,
                 tiles: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add street length, building count, building area, and coverage to each tile."""
    tiles = tiles.copy()

    # street length inside each tile: intersect the lines with the tiles, then sum lengths
    s_int = gpd.overlay(streets[["geometry"]], tiles[["tile_id", "geometry"]],
                        how="intersection", keep_geom_type=True)
    s_int["seg_len_m"] = s_int.geometry.length
    street_len = s_int.groupby("tile_id")["seg_len_m"].sum()

    # building area inside each tile: intersect polygons with tiles, then sum areas
    b_int = gpd.overlay(buildings[["geometry"]], tiles[["tile_id", "geometry"]],
                        how="intersection", keep_geom_type=True)
    b_int["a_m2"] = b_int.geometry.area
    bldg_area = b_int.groupby("tile_id")["a_m2"].sum()

    # building COUNT per tile: a footprint belongs to the tile that contains its centroid
    cent = buildings.copy()
    cent["geometry"] = buildings.geometry.centroid
    cent = gpd.sjoin(cent[["geometry"]], tiles[["tile_id", "geometry"]], predicate="within")
    bldg_count = cent.groupby("tile_id").size()

    tiles["street_len_m"] = tiles["tile_id"].map(street_len).fillna(0.0)
    tiles["bldg_area_m2"] = tiles["tile_id"].map(bldg_area).fillna(0.0)
    tiles["bldg_count"] = tiles["tile_id"].map(bldg_count).fillna(0).astype(int)
    # densities normalised by real tile area (so smaller edge tiles compare fairly)
    tiles["street_km_per_km2"] = (tiles["street_len_m"] / 1000) / (tiles["tile_area_m2"] / 1e6)
    tiles["bldg_coverage"] = tiles["bldg_area_m2"] / tiles["tile_area_m2"]
    return tiles


# --- figures ------------------------------------------------------------------------------

def plot_heatmaps(all_tiles: gpd.GeoDataFrame) -> None:
    """Two side-by-side density maps over the whole study area."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 9))
    for ax, col, title, cmap in [
        (axes[0], "bldg_coverage", "Building coverage (fraction built)", "viridis"),
        (axes[1], "street_km_per_km2", "Street density (km per km²)", "magma"),
    ]:
        all_tiles.plot(column=col, ax=ax, cmap=cmap, legend=True,
                       edgecolor="white", linewidth=0.3,
                       legend_kwds={"shrink": 0.5})
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Phase 1 audit — per-500 m-tile density (West | Center | East)", y=0.93)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase1_audit_density_heatmaps.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   saved {out.relative_to(config.ROOT)}")


def plot_groundtruth(all_tiles: gpd.GeoDataFrame,
                     zone_data: dict) -> bool:
    """Overlay OSM streets+footprints on satellite imagery at the 3 hutong ground-truth spots.

    Returns True if the satellite basemap loaded, False if we had to fall back to no imagery.
    """
    try:
        import contextily as cx
    except Exception as exc:  # noqa: BLE001
        print(f"   contextily unavailable ({exc}); skipping satellite overlay")
        return False

    pts = config.HUTONG_GROUNDTRUTH
    fig, axes = plt.subplots(1, len(pts), figsize=(6 * len(pts), 6))
    if len(pts) == 1:
        axes = [axes]
    basemap_ok = True

    # project the ground-truth points to metric to find their tiles/windows
    pts_gdf = gpd.GeoDataFrame(
        {"name": list(pts.keys())},
        geometry=gpd.points_from_xy([lon for _, lon in pts.values()],
                                    [lat for lat, _ in pts.values()]),
        crs=config.WGS84,
    ).to_crs(config.BEIJING_CRS)

    half = config.TILE_M / 2
    for ax, (name, pm) in zip(axes, zip(pts_gdf["name"], pts_gdf.geometry)):
        # a 500 m window centred on the point
        win = box(pm.x - half, pm.y - half, pm.x + half, pm.y + half)
        win_gdf = gpd.GeoDataFrame(geometry=[win], crs=config.BEIJING_CRS).to_crs(3857)

        # which zone is this point in? use its transect for the overlay data
        zone = name.split("(")[-1].strip(") ")
        streets, buildings = zone_data[zone]
        s = gpd.clip(streets, win).to_crs(3857)
        b = gpd.clip(buildings, win).to_crs(3857)

        # the OSM building coverage this window reports (to compare against the image)
        cov = (b.to_crs(config.BEIJING_CRS).geometry.area.sum() / (config.TILE_M ** 2)) * 100

        if len(b):
            b.plot(ax=ax, facecolor="#ffd24d", edgecolor="#c98a00", linewidth=0.4, alpha=0.55)
        if len(s):
            s.plot(ax=ax, color="#ff3b3b", linewidth=0.8)
        xmin, ymin, xmax, ymax = win_gdf.total_bounds
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution_size=6)
        except Exception as exc:  # noqa: BLE001
            basemap_ok = False
            print(f"   basemap fetch failed for {name} ({exc}); showing vectors only")
        ax.set_title(f"{name}\nOSM says {cov:.0f}% built", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle("Phase 1 audit — OSM (red=streets, yellow=footprints) vs. satellite imagery", y=1.02)
    out = config.FIGURES / "phase1_audit_groundtruth_hutong.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   saved {out.relative_to(config.ROOT)}" + ("" if basemap_ok else "  (NOTE: some basemaps failed)"))
    return basemap_ok


# --- flagging + QGIS template -------------------------------------------------------------

def write_digitize_template(flagged: gpd.GeoDataFrame) -> None:
    """Write an empty polygon layer (to trace into) + instructions, for flagged tiles."""
    manual_dir = config.ROOT / "data" / "manual"
    manual_dir.mkdir(parents=True, exist_ok=True)

    # the tiles to trace over, in WGS-84 so they drop straight onto imagery in QGIS
    ref = flagged[["tile_id", "zone", "bldg_coverage", "geometry"]].to_crs(config.WGS84)
    ref.to_file(manual_dir / "hutong_flagged_tiles.geojson", driver="GeoJSON")

    # an empty template with the schema to digitize INTO
    template = gpd.GeoDataFrame({"tile_id": [], "feature": [], "note": []},
                                geometry=[], crs=config.WGS84)
    template.to_file(manual_dir / "hutong_digitize_template.geojson", driver="GeoJSON")

    (manual_dir / "DIGITIZING_INSTRUCTIONS.md").write_text(
        "# Hand-digitizing flagged hutong tiles (QGIS)\n\n"
        "Some tiles fell below the coverage flag and MAY be missing building/alley data.\n"
        "Check each against imagery; digitize only where OSM is genuinely incomplete.\n\n"
        "1. Open QGIS. Add a satellite basemap (Browser > XYZ Tiles > add Esri World Imagery:\n"
        "   `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`).\n"
        "2. Drag in `hutong_flagged_tiles.geojson` (the tiles to inspect) and\n"
        "   `hutong_digitize_template.geojson` (the empty layer to trace into).\n"
        "3. Toggle editing on the template layer; trace missing building footprints as polygons.\n"
        "   Fill `tile_id` (matching the flagged tile), `feature`='building', add any `note`.\n"
        "4. Save. Phase 2 can rasterize these hand-traced polygons alongside the OSM data.\n\n"
        "NOTE: A tile can be legitimately empty (park, lake, plaza). Do NOT invent buildings —\n"
        "only trace what is visibly there in the imagery. Honesty over completeness.\n",
        encoding="utf-8",
    )
    print(f"   wrote QGIS template + instructions to data/manual/ ({len(flagged)} flagged tiles)")


# --- main ---------------------------------------------------------------------------------

def main() -> None:
    print("=" * 64)
    print("axis-fractal — Phase 1 completeness AUDIT")
    print("=" * 64)

    zone_data = {}
    all_tiles = []
    for zone in config.BEIJING_TRANSECTS:
        streets, buildings = load_zone(zone)
        zone_data[zone] = (streets, buildings)
        # tile the zone over the combined extent of its streets and buildings
        sb, bb = streets.total_bounds, buildings.total_bounds
        bounds_m = (min(sb[0], bb[0]), min(sb[1], bb[1]), max(sb[2], bb[2]), max(sb[3], bb[3]))
        tiles = make_tiles(zone, bounds_m)
        tiles = tile_metrics(streets, buildings, tiles)
        all_tiles.append(tiles)
        print(f"[{zone}] {len(tiles)} tiles; "
              f"median coverage {tiles['bldg_coverage'].median():.1%}, "
              f"median street density {tiles['street_km_per_km2'].median():.1f} km/km²")

    all_tiles = gpd.GeoDataFrame(pd.concat(all_tiles, ignore_index=True), crs=config.BEIJING_CRS)

    # per-zone summary
    summary = all_tiles.groupby("zone").agg(
        n_tiles=("tile_id", "size"),
        median_coverage=("bldg_coverage", "median"),
        median_street_density=("street_km_per_km2", "median"),
        median_bldg_count=("bldg_count", "median"),
        low_coverage_tiles=("bldg_coverage", lambda s: int((s < config.LOW_COVERAGE_FLAG).sum())),
    ).round(3)
    print("\nPer-zone summary:")
    print(summary.to_string())

    # save tables
    config.TABLES.mkdir(parents=True, exist_ok=True)
    all_tiles.drop(columns="geometry").to_csv(config.TABLES / "phase1_audit_tiles.csv", index=False)
    summary.to_csv(config.TABLES / "phase1_audit_zone_summary.csv")

    # figures
    print("\nFigures:")
    plot_heatmaps(all_tiles)
    basemap_ok = plot_groundtruth(all_tiles, zone_data)

    # flag + template
    flagged = all_tiles[all_tiles["bldg_coverage"] < config.LOW_COVERAGE_FLAG]
    print(f"\n{len(flagged)} of {len(all_tiles)} tiles below {config.LOW_COVERAGE_FLAG:.0%} coverage "
          f"(candidates to check vs. imagery).")
    if len(flagged):
        write_digitize_template(flagged)

    _append_results(summary, all_tiles, flagged, basemap_ok)
    print("\nPhase 1 audit done. Inspect the figures, then we decide: proceed to Phase 2, or "
          "hand-digitize flagged tiles first.")


def _append_results(summary, all_tiles, flagged, basemap_ok) -> None:
    """Write the audit's numbers to results.md — evidence for the human to judge, not a verdict."""
    lines = ["\n## Phase 1 — completeness audit (2026-07-14)\n",
             f"Tiled the three transects into {len(all_tiles)} tiles of {config.TILE_M:.0f} m. "
             "Per-tile metrics in `results/tables/phase1_audit_tiles.csv`; "
             "maps in `results/figures/phase1_audit_*`.\n",
             "| zone | tiles | median coverage | median street km/km² | median bldg count | tiles < 10% |",
             "|---|--:|--:|--:|--:|--:|"]
    for zone, r in summary.iterrows():
        lines.append(f"| {zone} | {int(r.n_tiles)} | {r.median_coverage:.1%} | "
                     f"{r.median_street_density:.1f} | {int(r.median_bldg_count)} | "
                     f"{int(r.low_coverage_tiles)} |")
    lines += [
        "",
        f"**Ground-truth check:** OSM overlaid on Esri satellite imagery at three known hutong "
        f"spots (`phase1_audit_groundtruth_hutong.png`)"
        + ("." if basemap_ok else " — NOTE: some/all satellite tiles failed to load; re-run with a connection."),
        f"**Flagged:** {len(flagged)} tiles below {config.LOW_COVERAGE_FLAG:.0%} built coverage. "
        "These are *candidates to inspect*, not confirmed gaps — many will be genuine voids "
        "(lakes, plazas, the Forbidden City grounds). Template for tracing real gaps written to "
        "`data/manual/` if any were flagged.",
        "",
        "**Preliminary read (to be confirmed by eye against the imagery):** compare the median "
        "coverage across zones and check whether the hutong ground-truth tiles look fully mapped. "
        "No fractal claims until this is settled.",
    ]
    (config.RESULTS / "results.md").open("a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("   appended audit summary to results/results.md")


if __name__ == "__main__":
    main()
