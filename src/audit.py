"""
audit.py — data completeness audit.  [Implemented in PHASE 1]

WHAT THIS MODULE WILL DO
    Before trusting any fractal number, check whether OSM actually covers the
    fabric we care about. For each 500 m tile it will count street segments and
    building footprints, render quick-look maps, and compare 3 known hutong tiles
    against satellite imagery. Output: an honest per-zone verdict on coverage, and
    a list of tiles that may need hand-digitizing in QGIS.

WHY THIS COMES FIRST
    Beijing hutong alleys and footprints are unevenly mapped in OSM. Measuring the
    fractal dimension of missing data would produce confident, wrong numbers.

STATUS: stub. This will be written together in Phase 1.
"""

def main() -> None:
    raise NotImplementedError(
        "audit.py is a Phase 1 stub. We'll implement it together, explaining each step."
    )


if __name__ == "__main__":
    main()
