# figure-gate

[![CI](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/figure-gate)](https://pypi.org/project/figure-gate/)
[![Docs](https://img.shields.io/badge/docs-narenp12.github.io-0072B2)](https://narenp12.github.io/figure-gate/)

**Two scripts that read a built matplotlib figure and report which gates it
fails.** `audit(fig)` returns `(ok, rows)` — 20 rows, one per gate, each a
`(label, status, detail)` triple where `status` is `True`, `False`, or
`"warn"`. `check(colors)` gates a palette the same way in 5 rows and returns
the same shape. It returned `(rows, ok)` until 0.4.0, and this paragraph
carried a warning about the difference instead of the difference being fixed.
Every threshold is a module-level constant you can read and change.

There is also an [Agent Skill](https://code.claude.com/docs/en/skills) wrapper
that applies the same checks when Claude Code builds a figure.

```bash
git clone https://github.com/narenp12/figure-gate && cd figure-gate
python skill/scripts/check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
python skill/scripts/check_figure.py     # self-test on a broken figure
```

![Validation loss against training epoch for three optimisers over 12 epochs.
All three fall; the Bayesian run reaches 0.05 by epoch 6, while the baseline is
still at 0.25 at epoch 12.](https://raw.githubusercontent.com/narenp12/figure-gate/main/examples/demo.png)

*`python examples/demo.py` builds that figure and audits it, with every
decision commented against the failure it avoids. `python examples/gallery.py`
covers the harder forms: a shared-axis grid, a filled field with a colorbar, an
axis-free schematic, three statistical forms, a log-log convergence plot with a
slope triangle, a dense attractor, and three complex-plane encodings on three
kinds of colormap. Writing those seven found six defects in the checks
themselves.*

## Why the two scripts talk to each other

A figure on matplotlib's default `tab10` cycle, with a `twinx` second axis,
returned nothing but passing rows from the composition checks. `check_palette.py` rated
that same cycle's orange and green at dE 1.4 under protanopia — one hue to that
reader, against a floor of 8. The composition checker had no access to the
colors it was drawing.

`check_series_color` closes that. It reads the hues off the figure's own
artists, decides from the mark types whether the figure needs adjacent
separation (lines, bars) or all-pairs separation (scatter), and runs them
through the palette gates. That is row 11 of the 20.

## What each gate measures

**`check_palette.py`** — takes hex strings on the command line or via
`check()`, imports nothing outside the standard library. Distances are OKLab
dE x100.

| Gate | Threshold | Fails when |
|---|---|---|
| Lightness band | `L_MIN, L_MAX = 0.43, 0.77` | OKLab lightness outside the band |
| Chroma floor | `CHROMA_MIN = 0.10` | OKLab chroma below it — the color reads as gray |
| CVD separation | `CVD_TARGET = 8.0` | two hues under 8 dE in protan or deutan simulation |
| Normal-vision floor | `NORMAL_FLOOR = 15.0` | two hues under 15 dE in full color |
| Contrast vs surface | `CONTRAST_MIN = 3.0` | a hue under 3:1 on the page *(advisory)* |

`--ordinal` swaps those five rows for four that apply to a ramp: lightness
monotone, adjacent dL gap, light-end contrast, and step uniformity
(largest/smallest dL). Protanopia and deuteranopia are gated, together about 8%
of males. Tritan separation is measured and printed in the detail string but
not gated: prevalence is around 0.01%, and the Vienot matrix used here is
validated only for the red-green forms, so the number is indicative rather than
decisive.

**`check_figure.py`** — renders the figure through an Agg canvas, at the dpi it
was authored at, and measures the result. `audit()` returns these 20 rows in
this order.

| Gate | Threshold | Fails when |
|---|---|---|
| Clipping | canvas bounds | a text artist's bbox extends past the canvas |
| Text collision | bbox overlap | two text bboxes overlap, tick labels on a shared axis exempted |
| Text readability | `TEXT_CONTRAST_MIN = 4.5` | text misses WCAG AA against the backdrop it actually got, or data ink crosses its glyphs |
| Contrast stack | `ALPHA_LEVELS_MAX = 3` | nothing in the figure is opaque, or transparency uses more than 3 distinct levels |
| Mark ratio | `MARK_RATIO_MAX = 5.0` | largest data mark exceeds 5x the smallest by area |
| Overplotting | `OVERPLOT_THRESHOLD = 0.5` | over half a scatter's points have a nearest neighbour inside one marker radius *(advisory)* |
| Axis redundancy | shared scale | panels on a shared scale repeat tick labels or axis titles |
| Type size | `TYPE_FLOOR_PT = 7.5` | a string renders under 7.5pt *on the printed page* |
| Line weight | `LINE_FLOOR_PT = 1.0` | a stroke renders under 1pt on the printed page (SIAM's floor) |
| Ink coverage | `INK_MIN, INK_MAX = 0.02, 0.55` | a panel's ink fraction falls outside the band *(advisory)* |
| Series color | palette gates, `MAX_SERIES_HUES = 6` | the hues actually drawn fail CVD or normal-vision separation, or one panel carries more than 6 |
| Dual axis | — | a `twinx` second scale carries data of its own |
| Form | — | pie, 3D, or bars on a truncated baseline |
| Identity channel | — | two or more series, no legend and no text in the axes *(advisory)* |
| Label attribution | `LABEL_MARGIN = 2.0` | a label's nearest other series is closer than 2x its distance to the one it names |
| Style sheet | 40 keys | the rcParams in effect differ from `figure.mplstyle` *(advisory)* |
| Contour dash | — | a signed contour set dashes its negative levels *(advisory)* |
| Colormap kind | `CMAP_BACKTRAVEL_MAX = 0.02` | a colormap classifies `misc`: its lightness reverses, or its span is flat, or its halves are monotone and its ends match neither cyclic nor diverging. Also when a qualitative map's levels fail all-pairs separation |
| Fonts | Type 42 | PDF/PS export would embed Type 3, or no named typeface resolves *(advisory)* |
| Alt text | `ALT_TEXT_MIN_CHARS = 60` | no description is attached, or the attached one is under 60 characters *(advisory)* |

Thresholds cite a published floor where one exists — SIAM's one point, WCAG's
4.5:1, the Nature/Science/PNAS type minima. The rest were measured, and
`skill/references/style-guide.md` records the measurement and the figure that
motivated each one.

### The gate that catches people

Type size is measured on the printed page, not on the canvas. A figure authored
at 14 inches (1008pt) and placed on a 750pt slide renders at 750/1008 = 0.74x,
so a 9pt label arrives at 6.7pt — under the 7.5pt floor, and under it by an
amount no one notices on a monitor. `page_scale` derives that ratio per figure
and the type gate measures what renders, so sizes set through rcParams or by a
helper are caught along with the ones set inline.

Placing at a fraction of the content width changes the ratio again:
`audit(fig, placed_frac=0.48)` mirrors `\includegraphics[width=0.48\textwidth]`,
and without it a half-width figure is certified at twice the type size it
ships at. For a venue in the table, `audit(fig, venue="neurips")` supplies the
width; `python check_figure.py --venues` prints all twelve with their content
widths in points.

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
```

The install ships `figure.mplstyle` beside the checkers, which is where the
style-sheet gate looks for it. Without that the gate has nothing to compare and
reports a pass, including for the figure it exists to catch — one drawn with
`plt.style.use` forgotten entirely.

Copying is the default because a vendored checker is one you can read and edit
beside the figures it gates, and the thresholds are meant to be edited.

Two settings need your document's values:

1. `font.serif` in `figure.mplstyle` — your document's body typeface.
2. `CONTENT_WIDTH_PT` at the top of `check_figure.py` — the usable width of the
   page, in points. Left `None`, the scale is 1.0 and the page calculation does
   nothing, which is correct if you author each figure at the width it is
   placed at. `venue=` overrides it per call.

If your sheet lives somewhere other than beside `check_figure.py`, set
`STYLE_SHEET` at the top of it to that path and the style-sheet gate compares
against yours. Left `None`, it looks beside the script and then in `assets/`
next to it.

### As a Claude Code skill

```bash
cp -r figure-gate/skill ~/.claude/skills/research-figures
```

Claude then runs these checks when you ask for a figure for a paper or a deck.
`skill/SKILL.md` is the workflow; `skill/references/style-guide.md` is the
measurement behind each threshold.

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

report(fig, "my-figure")                # prints 20 rows, returns True if ok
```

Two details in that block carry weight. The style sheet is resolved relative to
`__file__`, because `plt.style.use("figure.mplstyle")` resolves against the
working directory and breaks the first time a test runner or build script
invokes the module from elsewhere. And the backend is set explicitly, which is
what every example in this repository does before importing pyplot — a figure
built for measurement has no reason to open a window.

`audit` is the same checks without the printing, which is what a test wants:

```python
from check_figure import audit

@pytest.mark.parametrize("name", sorted(FIGURES))
def test_figure_is_composed(name):
    ok, rows = audit(build(name))
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if not s)
```

### Retina, and why the backend used to change the answer

You do not have to set the backend for the numbers to come out right. The
checker normalises for this itself, and that is worth knowing about because it
did not always.

A HiDPI GUI backend — macosx on a Retina display, Qt on a scaled desktop — sets
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

## Where this sits

Prescriptive style sheets already exist and are good:
[SciencePlots](https://github.com/garrettj403/SciencePlots) and LovelyPlots for
journal looks, [tueplots](https://github.com/pnkraemer/tueplots) and mpl_sizes
for exact conference sizing. Accessibility tooling exists too:
[matplotalt](https://github.com/KaiNylund/matplotalt) generates alt text,
Chart4Blind converts a chart image into an accessible one, contrast reporters
check colors in isolation.

Each of those acts before or beside the figure. None of them reads the built
result and reports what it fails, which is the only thing here — so a style
sheet and this are complementary: set defaults with one, verify them with the
other.

## What it does not do

Every check is an elimination gate: each one forbids a single enumerated
failure, and none looks at the figure as a whole. 20 passing rows means the
figure avoids 20 named defects. It does not mean the figure is good, and the
checker cannot see that an arrow points at the wrong object, that reading order
runs backwards, or that a label is true of the concept and false of the curve
beside it. Render it and look at it.

Two blind spots are worth naming because a passing row looks the same as an
absent one. The colormap gate reads a `Colormap`'s name to tell an encoding from
a hand-set list of colors, so a map matplotlib left unnamed is skipped rather
than judged; and it needs `check_palette.py` importable beside it, reporting
that it could not classify anything rather than raising if it is not. Both are
deliberate, and both mean the row can pass by having seen nothing.

The rules also do not transfer to interactive web charts, where hover,
responsive reflow and dark mode change most of the constraints.

## Design notes

**Use what matplotlib ships.** viridis for sequential, `RdBu` for diverging,
`okabe_ito` for categorical, style sheets for defaults, `constrained_layout`
for layout. Earlier versions hand-rolled all four and each was worse: `RdBu`'s
poles clear every gate in `check_palette.py` unmodified, and a windowed custom
ramp discarded 35% of viridis for no measured gain.

**WARN is not FAIL.** Seven of the 20 rows are advisory — they can return
`"warn"` but never `False` — and `ADVISORY_GATES` in `check_figure.py` is the
list. A sub-3:1 hue is legal when it carries a direct label; a heatmap panel
legitimately measures 0.98 ink coverage. Failing those would train people to
ignore the row, and an ignored gate is worth less than no gate. Type size is
the one row that does both: it fails under the floor, and warns on a figure
placed under 35% of the content width.

**Gates are tested for their ability to fail.** The suite is 875 tests, and
each check has one asserting it catches a figure with exactly that defect. The
style sheet has its own tests because `#` starts a comment in matplotlib's
style format: `grid.color: #e1e0d9` parses as an empty value, matplotlib keeps
its default, and every other test stays green.

The full reasoning — measurements behind each threshold, and the rules that
were tried and reverted — is in
[`skill/references/style-guide.md`](https://github.com/narenp12/figure-gate/blob/main/skill/references/style-guide.md).

Which *form* the data wants is the decision no styling rule rescues, and it is
in [`skill/references/choosing-a-form.md`](https://github.com/narenp12/figure-gate/blob/main/skill/references/choosing-a-form.md),
built on Cleveland & McGill's ordering of the elementary perceptual tasks. Only
its mechanical subset is gated: a script can rule out a pie or a truncated bar
baseline, but it cannot tell you a box plot is hiding an n of 8.

## Requirements

- `check_palette.py` — Python 3.8+, standard library only. Tested on 3.8, 3.9,
  3.11 and 3.13. Copied, it runs on 3.8; installed from PyPI it does not,
  because the package carries `check_figure.py` too and that needs 3.11. The
  vendoring case is the one that matters here, and a job with no install in it
  is what keeps the 3.8 claim true.
- `check_figure.py` — Python 3.11+, matplotlib 3.8+. The Python floor is
  support status, not syntax: 3.9 reached end of life in October 2025, and
  3.10 follows in October 2026. The matplotlib floor is deliberately older,
  because pinned matplotlib is normal in scientific environments and the
  checks are written to survive it.
- `colormaps["okabe_ito"]` needs matplotlib 3.11+. On older versions the
  palette is eight hex strings, listed in the style guide.

Those are the versions CI runs the palette checker on, with no `pip install` at
all, because "standard library only" is what makes the file usable from a
non-Python toolchain and a claim nobody tests is a claim. The test job runs
against the current matplotlib and pins one row to 3.8.4, so a break in either
direction shows up.

## Contributing

New gates are welcome at the bar the project holds itself to: a test proving
the gate fails on a figure with that defect, a test proving it does not
over-fire on the nearest legitimate case, and a note naming the real failure
that motivated it. See [CONTRIBUTING.md](https://github.com/narenp12/figure-gate/blob/main/CONTRIBUTING.md)
and [SECURITY.md](https://github.com/narenp12/figure-gate/blob/main/SECURITY.md).

## License

MIT — see [LICENSE](https://github.com/narenp12/figure-gate/blob/main/LICENSE).
