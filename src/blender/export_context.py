"""
export_context.py — local-origin GeoJSON of footprints for Blender.  [PHASE 9b/10]

Blender scenes import building footprints in METRES with a LOCAL origin (absolute UTM/HK-grid
coords sit millions of metres from 0,0 and destroy Blender's float precision). This crops the
Phase 10 footprints to a site, offsets to a local origin, and writes a plain GeoJSON whose
features carry a `height` property (data-driven, as in export3d.py).

    python src/blender/export_context.py --area beijing_center --lat 39.9175 --lon 116.396 \
        --half 500 --name forbidden_city_context

Output: data/exports/<name>.geojson  (coordinates are LOCAL METRES, not WGS-84).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import config from src/
import config  # noqa: E402


def export(area: str, lat: float, lon: float, half: float, name: str) -> Path:
    g = gpd.read_file(config.DATA_RAW / f"{area}_buildings_overture.gpkg")
    crs = config.HONGKONG_CRS if area.startswith("hk") else config.BEIJING_CRS
    h = pd.to_numeric(g["height"], errors="coerce") if "height" in g.columns else pd.Series(np.nan, index=g.index)
    zdef = float(h[h > 0].median()) if h[h > 0].count() >= 5 else 7.0
    g["height"] = np.where(h > 0, h, zdef).round(1)

    c = gpd.GeoSeries([Point(lon, lat)], crs=config.WGS84).to_crs(crs)
    cx, cy = c.x.iloc[0], c.y.iloc[0]
    minx, miny = cx - half, cy - half
    sub = g.cx[cx - half:cx + half, cy - half:cy + half].copy()
    sub["geometry"] = sub.translate(xoff=-minx, yoff=-miny)   # -> local origin at (0,0)

    feats = [{"type": "Feature", "properties": {"height": float(r.height)},
              "geometry": mapping(r.geometry)} for r in sub.itertuples()]
    out = config.DATA_RAW.parent / "exports" / f"{name}.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(f"{len(sub)} footprints (median {sub['height'].median():.0f} m) -> {out} "
          f"[{2*half:.0f}×{2*half:.0f} m, local origin]")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Local-origin GeoJSON footprints for Blender.")
    ap.add_argument("--area", default="beijing_center")
    ap.add_argument("--lat", type=float, default=39.9175)
    ap.add_argument("--lon", type=float, default=116.396)
    ap.add_argument("--half", type=float, default=500.0)
    ap.add_argument("--name", default="forbidden_city_context")
    a = ap.parse_args()
    export(a.area, a.lat, a.lon, a.half, a.name)


if __name__ == "__main__":
    main()
