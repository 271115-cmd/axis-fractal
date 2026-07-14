"""
verify_setup.py — Phase 0 sanity check.

Run this once after installing requirements. It proves three things:
  1. every core library imports and reports its version,
  2. osmnx can actually reach OpenStreetMap and download a small area, and
  3. we can project that data into our metric CRS and plot it.

If it finishes with "PHASE 0 OK", the environment is ready for Phase 1.

    python src/verify_setup.py

Nothing here is part of the analysis — it only checks the plumbing. It writes one
throwaway quick-look image to results/figures/ so we can see the whole stack works.
"""
from __future__ import annotations

import sys
from pathlib import Path

# A tiny, reliably-mapped test area: the Drum Tower (Gulou), the north anchor of
# Beijing's Central Axis. center_point is (latitude, longitude) in WGS-84 degrees.
TEST_CENTER = (39.9417, 116.3882)   # Drum Tower, Beijing
TEST_RADIUS_M = 300                 # small on purpose: fast, and gentle on the OSM server
BEIJING_METRIC_CRS = "EPSG:32650"   # UTM zone 50N — metres, for Beijing (see parameters.md)

# results/figures/ lives one level up from src/
FIG_DIR = Path(__file__).resolve().parent.parent / "results" / "figures"


def check_imports() -> bool:
    """Import every core library and print its version. Returns True if all import."""
    print("1) Checking library imports and versions")
    libs = [
        "osmnx", "geopandas", "shapely", "rasterio",
        "numpy", "scipy", "matplotlib", "skimage", "contextily",
    ]
    ok = True
    for name in libs:
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", "(no __version__)")
            print(f"   ok  {name:<12} {version}")
        except Exception as exc:  # noqa: BLE001 — we want to report any failure plainly
            print(f"   FAIL {name:<12} could not import: {exc}")
            ok = False
    return ok


def check_osmnx_download() -> bool:
    """Download a tiny real area, project it to metres, and save a quick-look PNG."""
    print("\n2) Checking osmnx download + projection + plotting")
    import matplotlib
    matplotlib.use("Agg")  # no on-screen window; we only save a file
    import matplotlib.pyplot as plt
    import osmnx as ox

    try:
        # --- (a) download the street network around the test point ---
        graph = ox.graph_from_point(
            TEST_CENTER, dist=TEST_RADIUS_M, network_type="all"
        )
        n_edges = graph.number_of_edges()
        print(f"   ok  downloaded street network: {n_edges} edges "
              f"around {TEST_CENTER} (r={TEST_RADIUS_M} m)")

        # --- (b) project from lat/lon degrees into metres (our Beijing CRS) ---
        graph_m = ox.project_graph(graph, to_crs=BEIJING_METRIC_CRS)
        edges_m = ox.graph_to_gdfs(graph_m, nodes=False, edges=True)
        print(f"   ok  projected to {BEIJING_METRIC_CRS} (metric); "
              f"edges CRS is now {edges_m.crs.to_string()}")

        # --- (c) grab a few building footprints (confirms the features API works) ---
        buildings = ox.features_from_point(
            TEST_CENTER, tags={"building": True}, dist=TEST_RADIUS_M
        )
        print(f"   ok  downloaded {len(buildings)} building footprints")

        # --- (d) plot both layers and save a throwaway quick-look ---
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        buildings_m = buildings.to_crs(BEIJING_METRIC_CRS)
        fig, ax = plt.subplots(figsize=(5, 5))
        buildings_m.plot(ax=ax, color="0.75", edgecolor="none")
        edges_m.plot(ax=ax, color="crimson", linewidth=0.6)
        ax.set_title("Phase 0 quick-look — Drum Tower, Beijing (test area)")
        ax.set_aspect("equal")
        ax.axis("off")
        out = FIG_DIR / "phase0_verify_quicklook.png"
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        print(f"   ok  saved quick-look -> {out.relative_to(FIG_DIR.parent.parent)}")
        return True

    except Exception as exc:  # noqa: BLE001
        print(f"   FAIL osmnx step failed: {exc}")
        print("        (If this is a network error, check your internet connection and "
              "re-run — osmnx downloads live from OpenStreetMap.)")
        return False


def main() -> int:
    print("=" * 60)
    print("axis-fractal — Phase 0 setup verification")
    print("=" * 60)
    imports_ok = check_imports()
    download_ok = check_osmnx_download()
    print("\n" + "=" * 60)
    if imports_ok and download_ok:
        print("PHASE 0 OK — environment ready for Phase 1.")
        return 0
    print("PHASE 0 FAILED — see the messages above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
