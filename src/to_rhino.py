"""
to_rhino.py — prepare context massing for Rhino, and the Rhino-side loader.  [PHASE 10]

Two steps (Rhino runs a separate Python interpreter, so the bridge is deliberately split):

  1) HERE (venv):   python src/to_rhino.py --area beijing_center --lat 39.9175 --lon 116.396 --half 650
     Crops the exported footprints to a site, offsets them to a local origin (so the model
     sits near 0,0 — Rhino loses precision far from origin), and writes a compact JSON to
     data/exports/_rhino_<area>_context.json  (metric metres, with per-building height_m).

  2) IN RHINO:      paste RHINO_LOADER (below) into Rhino's Python editor and run it.
     It reads that JSON and builds capped extrusions on layer AXIS_FRACTAL::02_CONTEXT_FOOTPRINTS
     and the site boundary on AXIS_FRACTAL::01_SITE_BOUNDARY. Create those layers first, or
     change the names in the loader.

This keeps the 3D bridge reproducible instead of a one-off. Heights come from Overture where
present, else the zone's median (see export3d.py); Beijing is genuinely low-rise (~7 m).
"""
from __future__ import annotations

import argparse
import json

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

import config

RHINO_LOADER = r'''
# --- paste into Rhino's Python editor; edit PATH if needed ---
import scriptcontext as sc, Rhino, Rhino.Geometry as rg, json
PATH = "REPLACE_WITH_JSON_PATH"
data = json.load(open(PATH))
def attr(fullpath):
    a = Rhino.DocObjects.ObjectAttributes(); a.LayerIndex = sc.doc.Layers.FindByFullPath(fullpath, -1); return a
sc.doc.Objects.AddPolyline([rg.Point3d(x, y, 0) for x, y in data["boundary"]],
                           attr("AXIS_FRACTAL::01_SITE_BOUNDARY"))
ac = attr("AXIS_FRACTAL::02_CONTEXT_FOOTPRINTS"); made = 0
for b in data["buildings"]:
    pts = [rg.Point3d(x, y, 0.0) for x, y in b["ring"]]
    if len(pts) < 4: continue
    if pts[0].DistanceTo(pts[-1]) > 1e-6: pts.append(pts[0])
    crv = rg.Polyline(pts).ToPolylineCurve()
    if crv is None or not crv.IsClosed or not crv.IsPlanar(): continue
    ext = rg.Extrusion.Create(crv, abs(float(b["h"])) or 6.0, True)
    if ext: sc.doc.Objects.AddExtrusion(ext, ac); made += 1
sc.doc.Views.Redraw(); print("extrusions made:", made)
'''


def _rings(geom):
    if geom.geom_type == "Polygon":
        return [list(geom.exterior.coords)]
    if geom.geom_type == "MultiPolygon":
        return [list(p.exterior.coords) for p in geom.geoms]
    return []


def prepare(area: str, lat: float, lon: float, half: float) -> None:
    g = gpd.read_file(config.DATA_RAW / f"{area}_buildings_overture.gpkg")
    crs = config.HONGKONG_CRS if area.startswith("hk") else config.BEIJING_CRS
    h = pd.to_numeric(g["height"], errors="coerce") if "height" in g.columns else pd.Series(np.nan, index=g.index)
    zdef = float(h[h > 0].median()) if h[h > 0].count() >= 5 else 7.0
    g["h"] = np.where(h > 0, h, zdef).round(1)

    c = gpd.GeoSeries([Point(lon, lat)], crs=config.WGS84).to_crs(crs)
    cx, cy = c.x.iloc[0], c.y.iloc[0]
    minx, miny, maxx, maxy = cx - half, cy - half, cx + half, cy + half
    sub = g.cx[minx:maxx, miny:maxy]

    buildings = [{"ring": [[round(x - minx, 2), round(y - miny, 2)] for x, y in ring], "h": float(r["h"])}
                 for _, r in sub.iterrows() for ring in _rings(r.geometry)]
    out = {"boundary": [[0, 0], [maxx - minx, 0], [maxx - minx, maxy - miny], [0, maxy - miny], [0, 0]],
           "buildings": buildings}
    path = config.DATA_RAW.parent / "exports" / f"_rhino_{area}_context.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    print(f"{len(sub)} footprints -> {len(buildings)} solids (median {np.median([b['h'] for b in buildings]):.0f} m)")
    print(f"wrote {path}")
    print(f"\nNow in Rhino, run RHINO_LOADER with PATH = \"{path}\"  (see this module's top docstring).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare a cropped context massing JSON for Rhino.")
    ap.add_argument("--area", default="beijing_center", help="e.g. beijing_center, hk_tseungkwano")
    ap.add_argument("--lat", type=float, default=39.9175)
    ap.add_argument("--lon", type=float, default=116.396)
    ap.add_argument("--half", type=float, default=650.0, help="half-size of the crop box (m)")
    a = ap.parse_args()
    prepare(a.area, a.lat, a.lon, a.half)


if __name__ == "__main__":
    main()
