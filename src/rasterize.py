"""
rasterize.py — turn vector maps into binary images.  [PHASE 2]

WHAT THIS MODULE DOES
    For each Beijing transect it builds TWO separate binary rasters at 2 m/pixel:
      (a) STREETS  — each street line inflated to its real width by road class, then painted;
      (b) FOOTPRINTS — the Overture building polygons painted directly.
    1 = structure, 0 = void. Each raster is saved as a GeoTIFF (keeps real-world coordinates)
    plus a PNG quick-look. A 3x2 overview compares all zones and both representations.

    Run it with:  python src/rasterize.py

KEY IDEAS FOR THE BEGINNER
    * A street in OSM is a zero-width LINE. A real street has width. So before painting we
      "buffer" each line by half its width (a primary road = 20 m wide => buffer 10 m each side).
    * "Rasterizing" = laying a grid of 2 m pixels over the map and marking each pixel 1 if a
      shape covers it, else 0. That grid of 0s and 1s is literally what Phases 3-4 measure.
"""
from __future__ import annotations

import ast

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize as rio_rasterize
from rasterio.transform import from_origin
from shapely.geometry import box as shapely_box
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config


# --- street width handling ----------------------------------------------------------------

def _classes(highway_value) -> list[str]:
    """A 'highway' cell can be 'residential' or a list-string like "['footway', 'steps']"."""
    s = str(highway_value)
    if s.startswith("["):
        try:
            return [str(x) for x in ast.literal_eval(s)]
        except (ValueError, SyntaxError):
            return [s]
    return [s]


def street_width(highway_value) -> float:
    """Widest matching class wins (a way tagged footway+service takes the wider width)."""
    widths = [config.STREET_WIDTHS.get(c, config.STREET_WIDTHS["_default"])
              for c in _classes(highway_value)]
    return max(widths) if widths else config.STREET_WIDTHS["_default"]


def buffer_streets(streets: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """Buffer each street line by half its width, so it becomes a strip of real width."""
    widths = streets["highway"].map(street_width)
    # buffer distance is HALF the width (half on each side of the centreline)
    return streets.geometry.buffer(widths.values / 2.0, cap_style=2)  # flat caps


# --- rasterization ------------------------------------------------------------------------

def zone_grid(zone: str):
    """The 2 m pixel grid for a transect, from its projected bounding box (same for both reps)."""
    w, s, e, n = config.BEIJING_TRANSECTS[zone]
    bounds = gpd.GeoSeries([shapely_box(w, s, e, n)], crs=config.WGS84) \
        .to_crs(config.BEIJING_CRS).total_bounds
    res = config.RASTER_RES_M
    minx = np.floor(bounds[0] / res) * res
    miny = np.floor(bounds[1] / res) * res
    maxx = np.ceil(bounds[2] / res) * res
    maxy = np.ceil(bounds[3] / res) * res
    width = int(round((maxx - minx) / res))
    height = int(round((maxy - miny) / res))
    transform = from_origin(minx, maxy, res, res)  # north-up
    return transform, (height, width)


def burn(geoms, transform, shape) -> np.ndarray:
    """Paint shapes onto the grid: 1 where a shape is, 0 elsewhere."""
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(shape, dtype=np.uint8)
    return rio_rasterize([(g, 1) for g in geoms], out_shape=shape, transform=transform,
                         fill=0, all_touched=config.RASTER_ALL_TOUCHED, dtype="uint8")


def save_geotiff(arr: np.ndarray, transform, path) -> None:
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype="uint8", crs=config.BEIJING_CRS, transform=transform,
                       compress="lzw") as dst:
        dst.write(arr, 1)


def rasterize_zone(zone: str) -> dict:
    """Build + save both rasters for one zone. Returns arrays + built fractions."""
    transform, shape = zone_grid(zone)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # (a) streets
    streets = gpd.read_file(config.DATA_RAW / f"beijing_{zone}_streets.gpkg", layer="edges")
    street_arr = burn(buffer_streets(streets).values, transform, shape)
    save_geotiff(street_arr, transform, config.DATA_PROCESSED / f"beijing_{zone}_streets_2m.tif")

    # (b) footprints (Overture)
    buildings = gpd.read_file(config.DATA_RAW / f"beijing_{zone}_buildings_overture.gpkg")
    bldg_arr = burn(buildings.geometry.values, transform, shape)
    save_geotiff(bldg_arr, transform, config.DATA_PROCESSED / f"beijing_{zone}_footprints_2m.tif")

    sfrac = street_arr.mean()
    bfrac = bldg_arr.mean()
    print(f"[{zone}] grid {shape[1]}x{shape[0]} px | "
          f"streets {sfrac:.1%} of pixels built | footprints {bfrac:.1%}")
    return {"zone": zone, "streets": street_arr, "footprints": bldg_arr,
            "street_frac": sfrac, "bldg_frac": bfrac}


def overview_figure(results: list[dict]) -> None:
    """3 zones (rows) x 2 representations (cols) of the binary rasters."""
    fig, axes = plt.subplots(len(results), 2, figsize=(8, 4 * len(results)))
    for row, r in enumerate(results):
        for col, key in enumerate(["streets", "footprints"]):
            ax = axes[row][col]
            ax.imshow(r[key], cmap="binary", interpolation="nearest")  # 1=black
            frac = r["street_frac"] if key == "streets" else r["bldg_frac"]
            ax.set_title(f"{r['zone']} — {key}  ({frac:.0%} built)", fontsize=10)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Phase 2 — binary rasters (2 m/px): streets vs footprints", y=0.995)
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    out = config.FIGURES / "phase2_rasters_overview.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nOverview saved -> {out.relative_to(config.ROOT)}")


def main() -> None:
    print("=" * 64)
    print(f"axis-fractal — Phase 2 rasterization ({config.RASTER_RES_M:.0f} m/pixel)")
    print("=" * 64)
    results = [rasterize_zone(z) for z in config.BEIJING_TRANSECTS]
    overview_figure(results)

    # record the built fractions
    import pandas as pd
    tbl = pd.DataFrame([{"zone": r["zone"], "street_built_frac": round(r["street_frac"], 4),
                         "footprint_built_frac": round(r["bldg_frac"], 4)} for r in results])
    config.TABLES.mkdir(parents=True, exist_ok=True)
    tbl.to_csv(config.TABLES / "phase2_raster_fractions.csv", index=False)
    print("\nBuilt-pixel fractions:")
    print(tbl.to_string(index=False))
    print("\nGeoTIFFs in data/processed/. Phase 2 done — next is box-counting (Phase 3).")


if __name__ == "__main__":
    main()
