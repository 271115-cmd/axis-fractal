"""
rasterize.py — turn vector maps into binary images.  [Implemented in PHASE 2]

WHAT THIS MODULE WILL DO
    Take the streets (lines) and buildings (polygons) and "paint" them onto a grid
    of pixels at a fixed resolution (start: 2 m/pixel). Streets get buffered to a
    real width by road class (e.g. alley 4 m, residential 8 m, primary 20 m). The
    result is a matrix of 0s and 1s: 1 = built structure, 0 = empty void. Saved as
    GeoTIFF (keeps real-world coordinates) plus a PNG quick-look.

WHY BINARY
    Box-counting and lacunarity operate on a black-and-white pattern. Everything
    downstream reads these 0/1 rasters, so this step defines what we actually measure.

STATUS: stub. This will be written together in Phase 2.
"""

def main() -> None:
    raise NotImplementedError(
        "rasterize.py is a Phase 2 stub. We'll implement it together, explaining each step."
    )


if __name__ == "__main__":
    main()
