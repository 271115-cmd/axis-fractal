"""
acquire_footprints.py — download COMPLETE building footprints from Overture Maps.  [PHASE 1+]

WHY THIS EXISTS
    The Phase 1 audit proved OSM building footprints are too sparse for Beijing's hutongs
    (Shichahai 5%, Nanluoguxiang 9% built vs ~60-70% in imagery). Overture Maps aggregates
    better sources (including a China rooftop dataset) that DO cover the hutongs. We keep the
    OSM STREET network (it was fine) and replace only the Beijing FOOTPRINTS.

WHAT IT DOES
    For each transect it runs the Overture downloader over the transect's bbox, keeps only
    building polygons, projects to EPSG:32650, and saves
    data/raw/beijing_<zone>_buildings_overture.gpkg.

    Run it with:  python src/acquire_footprints.py

TEACHING NOTE
    This is the honest way to fix a data gap: don't invent buildings — bring in a better,
    citable open dataset, then AUDIT it the same way we audited OSM (audit_footprints step).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import geopandas as gpd

import config

# the overturemaps CLI installed into this venv (same folder as our python)
OVERTURE = Path(sys.executable).parent / "overturemaps"

# only these scalar columns survive to the GeoPackage (Overture also has nested
# 'sources'/'names' columns that GeoPackage cannot store)
KEEP_COLS = ["id", "class", "subtype", "height"]


def download_zone(zone: str, bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Download + project Overture building footprints for one transect."""
    w, s, e, n = bbox
    tmp = config.DATA_RAW / f"_overture_{zone}.geojson"
    print(f"[{zone}] downloading Overture buildings for bbox {w},{s},{e},{n} ...")
    subprocess.run(
        [str(OVERTURE), "download", f"--bbox={w},{s},{e},{n}",
         "-f", "geojson", "--type=building", "-o", str(tmp)],
        check=True,
    )
    g = gpd.read_file(tmp)
    if g.crs is None:
        g = g.set_crs(config.WGS84)
    g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(config.BEIJING_CRS)
    cols = [c for c in KEEP_COLS if c in g.columns] + ["geometry"]
    g = g[cols]
    out = config.DATA_RAW / f"beijing_{zone}_buildings_overture.gpkg"
    g.to_file(out, driver="GPKG")
    tmp.unlink(missing_ok=True)
    print(f"       {len(g)} footprints, {g.geometry.area.sum() / 1e6:.3f} km² roof area "
          f"-> {out.name}")
    return g


def main() -> None:
    print("=" * 64)
    print("axis-fractal — Overture building footprints (Beijing)")
    print("=" * 64)
    for zone, bbox in config.BEIJING_TRANSECTS.items():
        download_zone(zone, bbox)
    print("\nDone. Next: audit_footprints compares Overture vs OSM coverage at the "
          "same hutong ground-truth points.")


if __name__ == "__main__":
    main()
