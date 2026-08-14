# Getting started

## Install

Three routes into the checkers. Copy them beside the figures to read and edit
them; install to pin a version. `check_palette.py` needs only the standard
library; `check_figure.py` needs matplotlib; scipy is optional and changes only
speed (`check_overplotting` uses a KD-tree when scipy imports and an O(n^2)
numpy path when it does not).

=== "Vendored"

    ```bash
    git clone https://github.com/narenp12/figure-gate
    cp figure-gate/skill/assets/figure.mplstyle       your-project/diagrams/
    cp figure-gate/skill/scripts/check_palette.py     your-project/diagrams/
    cp figure-gate/skill/scripts/check_figure.py      your-project/diagrams/
    cp figure-gate/skill/scripts/suggest_fixes.py     your-project/diagrams/  # optional
    ```

    The fourth file is what turns a failed row into a remedy, and nothing else
    needs it: `check_figure.py` imports it lazily, so a copy without it audits
    exactly the same and only `report(fig, suggest=True)` and `suggest(rows)`
    are missing. `check_figure.py` does need `check_palette.py` beside it: that
    is the import the series-color and colormap rows travel on, and without it
    neither raises: both say in their detail that nothing was checked and pass.

    Copying is the default because a vendored checker is one you can read and
    edit beside the figures it gates, and the thresholds are meant to be edited.

=== "Installed"

    Installing pins a version and puts the two checkers on PATH as
    `check-palette` and `check-figure`:

    ```bash
    uv add figure-gate                        # the library, and the two commands
    uv tool install figure-gate               # the two commands only, no import
    ```

    Installed, the checkers are a package, so import them from it:

    ```python
    from figure_gate import check_figure as cf
    from figure_gate import check_palette as cp
    from figure_gate import suggest_fixes as sf
    ```

    `py.typed` ships with them, so the annotations are visible to your type
    checker on this route. They are not on the vendored one, where the files are
    loose modules with no package for the marker to attach to, and PEP 561 reads
    every annotation in them as `Any`.

    What you got:

    ```bash
    uv pip show figure-gate      # or: conda list figure-gate
    ```

=== "conda-forge"

    ```bash
    conda install -c conda-forge figure-gate
    ```

    conda-forge follows PyPI through the feedstock's autotick bot rather than in
    the same hour, so the conda package is the previous release for a while
    after each one. The badges on
    [the repository](https://github.com/narenp12/figure-gate) say what each
    index is serving now.

    What you got:

    ```bash
    uv pip show figure-gate      # or: conda list figure-gate
    ```

The install ships `figure.mplstyle` inside that package, beside the module that
reads it, which is where the style-sheet gate looks. Without it the gate has
nothing to compare and reports a pass, including for the figure it exists to
catch: one drawn with `plt.style.use` forgotten entirely.

**Which import line depends on which version you installed.** Vendored, the
files are flat and `import check_figure` is the line. Installed, 0.7.0 moved
the modules into the `figure_gate` package; through 0.6.0 the wheel put them at
the top level of site-packages, so an install of 0.6.0 or earlier wants
`import check_figure`, the same line as a vendored copy. This says what you
got:

=== "0.7+ installed"

    ```python
    from figure_gate import check_figure as cf
    from figure_gate import check_palette as cp
    from figure_gate import suggest_fixes as sf
    ```

    ```bash
    uv pip show figure-gate      # or: conda list figure-gate
    ```

=== "0.6 and earlier"

    The same import line as a vendored copy:

    ```python
    import check_figure as cf
    import check_palette as cp
    import suggest_fixes as sf
    ```

    ```bash
    uv pip show figure-gate      # or: conda list figure-gate
    ```

=== "Vendored"

    ```python
    import check_figure as cf
    import check_palette as cp
    import suggest_fixes as sf
    ```

    `py.typed` is not on this route: the files are loose modules with no package
    for the marker to attach to, and PEP 561 reads every annotation in them as
    `Any`.

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

from check_figure import report      # installed: from figure_gate.check_figure import report

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

From here on, [the how-to](how-to.md) is the page you want: what to do when a
row fails, how to gate a whole suite, how to place a figure at half width, and
how to move a threshold.

`audit` is the same checks without the printing, which is what a test wants:

```python
from check_figure import audit       # installed: from figure_gate.check_figure import audit

@pytest.mark.parametrize("name", sorted(FIGURES))
def test_figure_is_composed(name):
    ok, rows = audit(build(name))
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if not s)
```

## Retina, and why the backend used to change the answer

You do not have to set the backend for the numbers to come out right. The
checker normalises for this itself; it did not always.

A HiDPI GUI backend, macosx on a Retina display or Qt on a scaled desktop, sets
`fig.dpi` to the authored dpi times the display's device pixel ratio at the
moment the figure is created. A figure built under one arrives at the checker at
2×. Through 0.1.1 that meant two wrong answers at once: text extents come back
in physical pixels while the canvas reports its width in logical ones, so the
clipping gate compared 2× coordinates against a 1× bound and failed labels that
fit; and thresholds calibrated in pixels covered half the distance they were
calibrated for. The same figure passed under Agg and failed under macosx.

Since 0.1.2 the checker measures on Agg regardless of what the figure was built
under, so the verdict is a property of the figure rather than of the display.
0.8.0 finished the job: the display's pixel ratio was only ever the loud case of
a pixel threshold read against a resolution nobody had pinned, so the canvas is
now drawn at `MEASURE_DPI = 150` whatever the figure was authored at, and the
figure is handed back on the dpi it arrived on. Setting `figure.dpi` yourself no
longer moves a verdict either. `savefig.dpi` is untouched, so what you write out
is still your choice.

One consequence, unchanged: an audited figure is no longer attached to its GUI
canvas and will not show in a window. Audit last, or audit a figure you rebuild
for the purpose.

The bug never reached CI. Every test and every example here pins Agg, so
nothing in the suite could construct the failing condition, and it stayed green
across a release.

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

## What the API promises

The public API is every name without a leading underscore in `check_figure.py`,
`check_palette.py` and `suggest_fixes.py`. That is broader than the handful you
would guess, and it is deliberately the same set the release gate compares, so
the statement and the enforcement cannot drift apart.

Below 1.0, a minor bump may break it. Every break is named in the changelog
under its release heading, and no change reaches `main` whose `## Unreleased`
section fails to name what moved: CI runs
[`audit_api.py`](https://github.com/narenp12/figure-gate/blob/main/skill/scripts/audit_api.py)
against the last tag on every pull request, and a symbol that changed without
being written down fails the build.

The number of rows is not part of the contract. The shape is: `audit` returns
`(ok, rows)`, each row a `(label, status, detail)` triple whose `status` is
`True`, `False` or `"warn"`, and `check` returns the same shape. Gates get
added; `check_banking` arrived after 0.6.0 and moved the count.

What is not enforced is the sentence rather than the symbol. The gate checks
that a changed name appears in `## Unreleased` next to a word admitting a
change. It cannot check that the sentence describes the change accurately.
