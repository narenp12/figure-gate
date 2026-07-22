"""A minimal figure built the way the guide describes, with both gates run on it.

    python examples/demo.py

Writes `examples/demo.png` and prints the composition audit. Everything here is
the whole method in miniature: load the style sheet, take palette slots in
order, run the checks, and only then look at the picture.
"""

from pathlib import Path
import sys

import matplotlib
import numpy as np

matplotlib.use("agg")
import matplotlib.pyplot as plt
from matplotlib import colormaps

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "skill"
sys.path.insert(0, str(SKILL / "scripts"))

import check_figure as cf          # noqa: E402
import check_palette as cp         # noqa: E402

# Resolve the sheet relative to this file. A bare "figure.mplstyle" only works
# when the working directory happens to be the right one, which stops being true
# the moment a test runner or a build script invokes this.
plt.style.use(str(SKILL / "assets" / "figure.mplstyle"))

# Okabe-Ito is a matplotlib builtin as of 3.11. Before that it is eight hex
# strings, which is all it ever was -- so falling back costs nothing and keeps
# this runnable on any matplotlib the checks themselves support.
OKABE_ITO = ["#000000", "#e69f00", "#56b4e9", "#009e73",
             "#f0e442", "#0072b2", "#d55e00", "#cc79a7"]
if "okabe_ito" in colormaps:
    OKABE_ITO = [matplotlib.colors.to_hex(colormaps["okabe_ito"](i))
                 for i in range(8)]

# Slot 0 is black (the ink token here), so the series ramp starts at 1 and is
# taken IN ORDER -- picking slots by meaning is what puts two hues that collide
# under protanopia in the same figure.
SERIES = OKABE_ITO[1:4]

# The style sheet carries the same six slots as `axes.prop_cycle`, so a figure
# that just draws inherits them. Pinning the two together here means a future
# edit to either one shows up as a failure in the example rather than as two
# palettes that quietly disagree.
CYCLE = plt.rcParams["axes.prop_cycle"].by_key()["color"]
assert [c.lower() for c in CYCLE[:3]] == SERIES, (CYCLE[:3], SERIES)

# Prove it before drawing it. This is the cheap half of the method.
rows, ok = cp.check(SERIES, all_pairs=True)
assert ok, rows

rng = np.random.default_rng(0)
x = np.linspace(0, 12, 300)

fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
# Check the label against the drawn data, not against the idea it names. If the
# legend orders these as improvements, the curves have to actually improve --
# the guide's most-repeated failure is a callout that is true of the concept and
# false of the line beside it.
# Where each curve is labelled, and on which side. Staggered rather than set at
# one epoch: with all three at x=9 the lowest label landed in the gap the middle
# curve was passing through, which is legible in the PNG and invisible to the
# collision check -- that gate compares text against text, not text against a
# line. Step 6 of the procedure exists for exactly this class of defect.
for color, decay, label, at_x, side in zip(
        SERIES,
        (0.12, 0.22, 0.35),
        ("Baseline", "Tuned", "Bayesian"),
        (9.0, 10.5, 6.5),
        (1, 1, -1)):
    y = np.exp(-decay * x) + 0.02 * rng.standard_normal(x.size)
    ax.plot(x, y, color=color, lw=1.6, label=label)
    # Direct labels, not a legend. Orange and sky blue are under 3:1 on white,
    # and the guide's rule for a sub-3:1 hue is a visible direct label -- a
    # legend does not discharge it, because it leaves the reader matching a
    # small faint swatch to a small faint curve, which is the step being
    # removed. The anchor is read off the drawn array rather than the analytic
    # curve, so the text sits on the line that actually rendered.
    at = int(np.argmin(np.abs(x - at_x)))
    ax.annotate(label, (x[at], y[at]), textcoords="offset points",
                xytext=(0, 7 * side), ha="center",
                va="bottom" if side > 0 else "top")

ax.set_xlabel("Training epoch")
ax.set_ylabel("Validation loss")

# The caption carries the mechanism; the figure carries no internal title.
passed = cf.report(fig, "demo")
# No dpi or bbox here on purpose: both come from the style sheet, which is the
# point of having one. `bbox_inches="tight"` in particular would change the
# saved width and quietly invalidate the type-size check that just ran.
fig.savefig(HERE / "demo.png")
plt.close(fig)

print(f"wrote {HERE / 'demo.png'}")
sys.exit(0 if passed else 1)
