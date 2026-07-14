"""
boxcount.py — fractal (box-counting) dimension.  [Implemented in PHASE 3]

WHAT THIS MODULE WILL DO
    Lay grids of boxes of different sizes over a binary raster and, for each box
    size, count how many boxes contain any structure. Plot log(count) against
    log(1/box-size): the slope of the straight-line part is the box-counting
    dimension D_b. Reports slope, 95% confidence interval, and R², and SAVES the
    log-log plot for every single computation (so no fit is ever unexamined).

WHAT IT WILL NOT DO
    Never report a D_b without its R² and the plot. If R² < 0.99 over the chosen
    range, it flags the case so we pick the linear scaling range by eye.

STATUS: stub. This will be written together in Phase 3.
"""

def main() -> None:
    raise NotImplementedError(
        "boxcount.py is a Phase 3 stub. We'll implement it together, explaining each step."
    )


if __name__ == "__main__":
    main()
