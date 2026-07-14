"""
lacunarity.py — gliding-box lacunarity.  [Implemented in PHASE 4]

WHAT THIS MODULE WILL DO
    Measure the "gappiness" of a binary raster at many scales. A box of radius r
    glides over the image; at each position we count the structure inside it. The
    spread (variance) of those counts, normalized, is the lacunarity Λ at scale r.
    Two patterns can share a fractal dimension yet feel completely different — one
    even, one clumpy — and lacunarity is what distinguishes them.

    Output: the FULL curve Λ(r) for r = 8,16,32,...,512 px, never a single number.

MEMORY NOTE (important)
    Uses a summed-area table (integral image) so each box sum is O(1). A naive
    sliding window on a ~4096x4096 array would exhaust RAM.

STATUS: stub. This will be written together in Phase 4.
"""

def main() -> None:
    raise NotImplementedError(
        "lacunarity.py is a Phase 4 stub. We'll implement it together, explaining each step."
    )


if __name__ == "__main__":
    main()
