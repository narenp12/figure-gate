# Getting started

## Install

Copy three files. `check_palette.py` needs only the standard library;
`check_figure.py` needs matplotlib; scipy is optional and changes only speed
(`check_overplotting` uses a KD-tree when scipy imports and an O(n^2) numpy
path when it does not).

```bash
git clone https://github.com/narenp12/figure-gate
cp figure-gate/skill/assets/figure.mplstyle       your-project/diagrams/
cp figure-gate/skill/scripts/check_palette.py     your-project/diagrams/
cp figure-gate/skill/scripts/check_figure.py      your-project/diagrams/
```

Installing instead of vendoring pins a version and puts the same two checkers
on PATH as `check-palette` and `check-figure`:

```bash
uv add figure-gate          # or: uv tool install figure-gate
conda install -c conda-forge figure-gate
```

The install ships `figure.mplstyle` beside the checkers, which is where the
style-sheet gate looks for it. Without that the gate has nothing to compare and
reports a pass, including for the figure it exists to catch: one drawn with
`plt.style.use` forgotten entirely.

Copying is the default because a vendored checker is one you can read and edit
beside the figures it gates, and the thresholds are meant to be edited.

## Two settings need your document's values

1. `font.serif` in `figure.mplstyle`, your document's body typeface.
2. `CONTENT_WIDTH_PT` at the top of `check_figure.py`, the usable width of the
   page, in points. Left `None`, the scale is 1.0 and the page calculation does
   nothing, which is correct if you author each figure at the width it is
   placed at. `venue=` overrides it per call.

If your sheet lives somewhere other than beside `check_figure.py`, set
`STYLE_SHEET` at the top of it to that path and the style-sheet gate compares
against yours. Left `None`, it looks beside the script and then in `assets/`
next to it.

## As a Claude Code skill

The repository is also a plugin marketplace, so Claude Code can install the
skill and track updates against the tags this project already cuts:

```bash
/plugin marketplace add narenp12/figure-gate
```

then `/plugin install figure-gate@figure-gate`. The skill is invoked as
`figure-gate:research-figures`.

Copying works too, and is the right choice if you want to edit the thresholds
in place:

```bash
cp -r figure-gate/skill ~/.claude/skills/research-figures
```

Claude then runs these checks when you ask for a figure for a paper or a deck.
[The agent skill](skill.md) is the workflow; [the style guide](style-guide.md)
is the measurement behind each threshold.

## Use it

```python
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
from matplotlib import colormaps

from check_figure import report

plt.style.use(str(Path(__file__).parent / "figure.mplstyle"))

x = np.linspace(0, 12, 300)
y = np.exp(-0.12 * x)

okabe = colormaps["okabe_ito"]          # matplotlib >= 3.11
fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
ax.plot(x, y, color=okabe(1))           # line width comes from the sheet

report(fig, "my-figure")                # prints 21 rows, returns True if ok
```

Two details in that block carry weight. The style sheet is resolved relative to
`__file__`, because `plt.style.use("figure.mplstyle")` resolves against the
working directory and breaks the first time a test runner or build script
invokes the module from elsewhere. And the backend is set explicitly, which is
what every example in this repository does before importing pyplot: a figure
built for measurement has no reason to open a window.

`audit` is the same checks without the printing, which is what a test wants:

```python
from check_figure import audit

@pytest.mark.parametrize("name", sorted(FIGURES))
def test_figure_is_composed(name):
    ok, rows = audit(build(name))
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if not s)
```

## Retina, and why the backend used to change the answer

You do not have to set the backend for the numbers to come out right. The
checker normalises for this itself, and that is worth knowing about because it
did not always.

A HiDPI GUI backend, macosx on a Retina display or Qt on a scaled desktop, sets
`fig.dpi` to the authored dpi times the display's device pixel ratio at the
moment the figure is created. A figure built under one arrives at the checker at
2×. Through 0.1.1 that meant two wrong answers at once: text extents come back
in physical pixels while the canvas reports its width in logical ones, so the
clipping gate compared 2× coordinates against a 1× bound and failed labels that
fit; and thresholds calibrated in pixels covered half the distance they were
calibrated for. The same figure passed under Agg and failed under macosx.

Since 0.1.2 the checker resets the figure to its authored dpi and measures on
Agg regardless of what it was built under, so the verdict is a property of the
figure rather than of the display. One consequence: an audited figure is no
longer attached to its GUI canvas and will not show in a window. Audit last, or
audit a figure you rebuild for the purpose.

The bug is worth reading as a warning about the shape of this project's own test
suite rather than as a fixed defect. Every test and every example here pins Agg,
so nothing in CI could construct the failing condition, and it stayed green
across a release. Tests that all share one assumption cannot see that
assumption.

## Requirements

- `check_palette.py` needs Python 3.8+ and the standard library only. Tested on
  3.8, 3.9, 3.11 and 3.13. Copied, it runs on 3.8; installed from PyPI it does
  not, because the package carries `check_figure.py` too and that needs 3.11.
  The vendoring case is the one that matters here, and a job with no install in
  it is what keeps the 3.8 claim true.
- `check_figure.py` needs Python 3.11+ and matplotlib 3.8+. The Python floor is
  support status, not syntax: 3.9 reached end of life in October 2025, and
  3.10 follows in October 2026. The matplotlib floor is deliberately older,
  because pinned matplotlib is normal in scientific environments and the
  checks are written to survive it.
- `colormaps["okabe_ito"]` needs matplotlib 3.11+. On older versions the
  palette is eight hex strings, listed in [the style guide](style-guide.md).

Those are the versions CI runs the palette checker on, with no `pip install` at
all, because "standard library only" is what makes the file usable from a
non-Python toolchain and a claim nobody tests is a claim. The test job runs
against the current matplotlib and pins one row to 3.8.4, so a break in either
direction shows up.
