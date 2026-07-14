"""
sampling.py — tiling + per-zone statistics.  [Implemented in PHASE 5]

WHAT THIS MODULE WILL DO
    Cut each transect into non-overlapping 500 m x 500 m tiles and compute D_b and
    Λ(r) for every tile. That turns "one number per zone" (which proves nothing)
    into a DISTRIBUTION per zone. Then compare zones with a Mann-Whitney U test
    (plus effect size) and report medians and IQRs.

HONESTY CLAUSE
    Results are written to results/results.md exactly as computed — including any
    that contradict the hypothesis that hutong and Axis textures converge.

STATUS: stub. This will be written together in Phase 5.
"""

def main() -> None:
    raise NotImplementedError(
        "sampling.py is a Phase 5 stub. We'll implement it together, explaining each step."
    )


if __name__ == "__main__":
    main()
