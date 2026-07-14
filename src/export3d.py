"""
export3d.py — export geometry for Rhino/Grasshopper + Blender.  [PHASE 10]

For each transect/site, writes to data/exports/<area>/:
    <area>_footprints.geojson        building footprints, metric CRS, with a height_m attribute
    <area>_footprints.dxf            footprints as 2D polylines (CAD fallback; extrude by height_m)
    <area>_streets_buffered.geojson  streets buffered to real width (the figure-ground "poché")
    <area>_streets_buffered.dxf
    <area>_extent.geojson            the study-area rectangle
    CRS.txt                          the EPSG the coordinates are in (GeoJSON files are METRIC, not 4326)

    Run it with:  python src/export3d.py

HEIGHTS (documented assumption)
    Overture tags only 3–6 % of buildings with a height. Rather than invent numbers, the default
    height for the untagged majority is the MEDIAN of the SAME zone's tagged buildings (data-driven)
    — e.g. Tseung Kwan O ≈ 82 m, Sham Shui Po ≈ 30 m. Where a zone has <5 tagged buildings we fall
    back to a documented literature value. Every building carries a `height_src` flag
    ('overture' or 'zone_median_default') so nothing is silently invented.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box as sbox

import config
from rasterize import buffer_streets

EXPORTS = config.ROOT / "data" / "exports"

# CRS per area (Beijing = UTM 50N, HK = HK1980 Grid)
AREA_CRS = {
    "beijing_west": config.BEIJING_CRS, "beijing_center": config.BEIJING_CRS,
    "beijing_east": config.BEIJING_CRS,
    "hk_shamshuipo": config.HONGKONG_CRS, "hk_tseungkwano": config.HONGKONG_CRS,
    "hk_kathingwai": config.HONGKONG_CRS, "hk_wanchai": config.HONGKONG_CRS,
}
# literature fallback height (m) used ONLY when a zone has too few Overture heights to take a median
FALLBACK_H = {
    "beijing_west": 6.0, "beijing_center": 10.0, "beijing_east": 18.0,
    "hk_shamshuipo": 30.0, "hk_tseungkwano": 85.0, "hk_kathingwai": 6.0, "hk_wanchai": 45.0,
}


def _try_dxf(gdf: gpd.GeoDataFrame, path) -> bool:
    try:
        gdf.to_file(path, driver="DXF")
        return True
    except Exception as exc:  # noqa: BLE001 — DXF driver is optional; report, don't crash
        print(f"     DXF skipped for {path.name}: {exc}")
        return False


def export_area(key: str, crs: str) -> dict:
    out = EXPORTS / key
    out.mkdir(parents=True, exist_ok=True)

    # --- footprints + heights ---
    b = gpd.read_file(config.DATA_RAW / f"{key}_buildings_overture.gpkg")
    h = pd.to_numeric(b["height"], errors="coerce") if "height" in b.columns else pd.Series(np.nan, index=b.index)
    tagged = h[h > 0]
    zdef = float(tagged.median()) if tagged.count() >= 5 else FALLBACK_H[key]
    b["height_m"] = np.where(h > 0, h, zdef).round(1)
    b["height_src"] = np.where(h > 0, "overture", "zone_median_default")
    b[["height_m", "height_src", "geometry"]].to_file(out / f"{key}_footprints.geojson", driver="GeoJSON")
    _try_dxf(b[["geometry"]], out / f"{key}_footprints.dxf")

    # --- streets buffered to real width (the poché) ---
    e = gpd.read_file(config.DATA_RAW / f"{key}_streets.gpkg", layer="edges")
    sb = gpd.GeoDataFrame(geometry=buffer_streets(e).values, crs=e.crs)
    sb.to_file(out / f"{key}_streets_buffered.geojson", driver="GeoJSON")
    _try_dxf(sb, out / f"{key}_streets_buffered.dxf")

    # --- study-area extent ---
    gpd.GeoDataFrame(geometry=[sbox(*b.total_bounds)], crs=crs).to_file(
        out / f"{key}_extent.geojson", driver="GeoJSON")

    # --- CRS note (GeoJSON here is METRIC, not the usual WGS-84) ---
    (out / "CRS.txt").write_text(
        f"All GeoJSON/DXF in this folder use {crs} (metres), NOT WGS-84.\n"
        f"In Rhino/Blender, set the project CRS to {crs} or import as planar metric coordinates.\n",
        encoding="utf-8")

    pct_real = 100 * (b["height_src"] == "overture").mean()
    print(f"[{key:>15}] {len(b)} footprints ({pct_real:.0f}% real height, default {zdef:.0f} m), "
          f"{len(sb)} street polys -> data/exports/{key}/")
    return {"area": key, "footprints": len(b), "pct_real_height": round(pct_real, 1),
            "default_height_m": round(zdef, 1), "crs": crs}


def main() -> None:
    print("=" * 66)
    print("axis-fractal — Phase 10 geometry export (Rhino/Grasshopper + Blender)")
    print("=" * 66)
    rows = [export_area(k, crs) for k, crs in AREA_CRS.items()]
    config.TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(config.TABLES / "phase10_export_summary.csv", index=False)
    print("\nExports in data/exports/<area>/ (GeoJSON + DXF, metric CRS). "
          "Extrude footprints by `height_m` in Rhino/Blender for massing.")


if __name__ == "__main__":
    main()
