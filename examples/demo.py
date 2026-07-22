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

# Okabe-Ito is a matplotlib builtin as of 3.11. Slot 0 is black (the ink token
# here), so the series ramp starts at 1 and is taken IN ORDER -- picking slots by
# meaning is what puts two hues that collide under protanopia in one figure.
OKABE = colormaps["okabe_ito"]
SERIES = [OKABE(i) for i in (1, 2, 3)]

# Prove it before drawing it. This is the cheap half of the method.
rows, ok = cp.check([matplotlib.colors.to_hex(c) for c in SERIES], all_pairs=True)
assert ok, rows

rng = np.random.default_rng(0)
x = np.linspace(0, 12, 300)

fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
# Check the label against the drawn data, not against the idea it names. If the
# legend orders these as improvements, the curves have to actually improve --
# the guide's most-repeated failure is a callout that is true of the concept and
# false of the line beside it.
for color, decay, label in zip(
        SERIES, (0.12, 0.22, 0.35), ("Baseline", "Tuned", "Bayesian")):
    y = np.exp(-decay * x) + 0.02 * rng.standard_normal(x.size)
    ax.plot(x, y, color=color, lw=1.6, label=label)

ax.set_xlabel("Training epoch")
ax.set_ylabel("Validation loss")
ax.legend(loc="upper right")

# The caption carries the mechanism; the figure carries no internal title.
passed = cf.report(fig, "demo")
fig.savefig(HERE / "demo.png", dpi=200)
plt.close(fig)

print(f"wrote {HERE / 'demo.png'}")
sys.exit(0 if passed else 1)
