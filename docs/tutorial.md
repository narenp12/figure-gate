# Gate your first figure

In this tutorial you build a figure the way matplotlib builds one by default,
find out what it fails, and fix it until every row passes. You then place the
same figure at half the width of a conference column and watch it fail again for
a reason that was invisible on your screen.

You need Python 3.11 or later and matplotlib 3.8 or later. You do not need to
know anything about the checks: reading their output is the point of the
exercise.

This tutorial takes about fifteen minutes.

## Step 1: Get the checkers

Clone the repository and copy four files into a working directory:

```bash
git clone https://github.com/narenp12/figure-gate
mkdir figures && cd figures
cp ../figure-gate/skill/scripts/check_palette.py .
cp ../figure-gate/skill/scripts/check_figure.py .
cp ../figure-gate/skill/scripts/suggest_fixes.py .
cp ../figure-gate/skill/assets/figure.mplstyle .
```

Your working directory now holds the two checkers, the remedies file, and a
style sheet:

```text
check_figure.py
check_palette.py
figure.mplstyle
suggest_fixes.py
```

## Step 2: Build a figure and audit it

Save this as `loss.py` in the same directory:

```python
import matplotlib
matplotlib.use("agg")

import matplotlib.pyplot as plt
import numpy as np

from check_figure import report

epochs = np.arange(1, 13)
baseline = 0.9 * np.exp(-0.06 * epochs) + 0.22
tuned = 0.9 * np.exp(-0.35 * epochs) + 0.02

fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(epochs, baseline, label="baseline")
ax.plot(epochs, tuned, label="tuned")
ax.set_xlabel("Epoch", fontsize=6)
ax.set_ylabel("Validation loss", fontsize=6)
ax.legend()

report(fig, "loss")     # prints 21 rows, returns True if ok
```

Run it:

```bash
python loss.py
```

`report` prints one row per check and ends with a verdict:

```text
Composition audit: loss
  [PASS] Clipping           no text past the canvas
  [PASS] Text collision     4 text objects, none overlapping
  [PASS] Text readability   16 strings read clean against their backdrop
  [PASS] Contrast stack     alpha levels [1.0]
  [PASS] Mark ratio         fewer than two mark sizes
  [PASS] Overplotting       no scatter overplotting
  [PASS] Axis redundancy    axis furniture not duplicated
  [FAIL] Type size          under 7.5pt on page at scale 1.0: [(6.0, 'Epoch'), (6.0, 'Validation loss')]  [FIX] cut words, do not shrink type
  [PASS] Line weight        2 strokes, thinnest 1.50pt on page (floor 1.0)
  [PASS] Banking            1 line panel, typical segment 12-12 deg
  [PASS] Ink coverage       ink fraction: ax0 0.04 (typical 0.02-0.55)
  [PASS] Series color       up to 2 data hues per panel: worst pair dE 51.4 ...
  [PASS] Dual axis          one data scale per frame
  [PASS] Form               no pie, no 3D, no truncated bar baseline
  [PASS] Identity channel   2 series, legend present
  [PASS] Label attribution  no direct labels matched to a series
  [WARN] Style sheet        34 of 40 keys differ from figure.mplstyle: [...]
  [PASS] Contour dash       no auto-dashed negative contours
  [PASS] Colormap kind      no colormapped artists
  [WARN] Fonts              pdf.fonttype and ps.fonttype = 3 (Type 3)  [FIX] ...
  [WARN] Alt text           no description attached  [FIX] ...

  -> FIX THE MARKED CHECKS
```

You have one `[FAIL]` and three `[WARN]` rows. A `[FAIL]` is a hard failure and
sets the verdict. A `[WARN]` is advisory: it reports, but it never fails a
build.

## Step 3: Read the failing row

Look at the row that failed:

```text
[FAIL] Type size   under 7.5pt on page at scale 1.0: [(6.0, 'Epoch'), (6.0, 'Validation loss')]
                   [FIX] cut words, do not shrink type
```

Every detail string is built the same way. It names the measurement, the two
strings that produced it, and after `[FIX]`, the action to take. You set both
axis labels to 6pt, and the floor is 7.5pt.

## Step 4: Apply the style sheet

Rather than change the two font sizes by hand, apply the style sheet you copied.
It sets type sizes, line widths, colors, and font embedding together.

Add the style call before you create the figure, delete the two font-size
arguments, and turn on `constrained_layout`:

```python
import matplotlib
matplotlib.use("agg")

import matplotlib.pyplot as plt
import numpy as np

from check_figure import report

plt.style.use("figure.mplstyle")          # add this

epochs = np.arange(1, 13)
baseline = 0.9 * np.exp(-0.06 * epochs) + 0.22
tuned = 0.9 * np.exp(-0.35 * epochs) + 0.02

fig, ax = plt.subplots(figsize=(6, 3.5), constrained_layout=True)
ax.plot(epochs, baseline, label="baseline")
ax.plot(epochs, tuned, label="tuned")
ax.set_xlabel("Epoch")                    # no font size
ax.set_ylabel("Validation loss")          # no font size
ax.legend()

report(fig, "loss")
```

Run it again. Three rows change at once:

```text
  [PASS] Type size          smallest 9.5pt on page (floor 7.5)
  [PASS] Style sheet        all 40 keys match figure.mplstyle
  [PASS] Fonts              Type 42 embedding, serif face resolves within the list
  [WARN] Alt text           no description attached  [FIX] ...

  -> FIX THE MARKED CHECKS
```

The series colors changed too. The sheet replaces matplotlib's default cycle
with one that stays separable under the two common forms of color vision
deficiency.

## Step 5: Attach alt text

One advisory row is left. Import `describe` and call it before the audit:

```python
from check_figure import describe, report
```

```python
describe(fig, "Validation loss against training epoch for a baseline and a "
              "tuned run over 12 epochs. Both fall; the tuned run reaches 0.02 "
              "by epoch 12, while the baseline is still at 0.25.")

report(fig, "loss")
```

Run it again:

```text
  [PASS] Alt text           described in 173 characters

  -> COMPOSED
```

`COMPOSED` is the passing verdict. Every row passes.

## Step 6: Place the figure on a page

The figure passes at the size you drew it. Papers rarely print figures at the
size they were drawn.

Tell the checker where this one is going. The `venue` argument supplies a
content width, and `placed_frac` says what fraction of that width the figure
occupies, the way `\includegraphics[width=0.48\textwidth]` does:

```python
report(fig, "loss", venue="neurips", placed_frac=0.48)
```

Two rows that passed a moment ago now fail:

```text
  [FAIL] Type size    under 7.5pt on page at scale 0.44164444444444445: [(4.2, 'baseline'), (4.2, 'tuned'), (4.4, '0.0'), (4.4, '0.2')]
                      [FIX] cut words, do not shrink type
  [FAIL] Line weight  under 1.0pt on page at scale 0.44: ['baseline at 0.71pt', 'tuned at 0.71pt']
                      [FIX] set linewidth to at least 2.26 at this scale
                      [WHY] SIAM: lines thinner than one point break up or disappear in print
```

Nothing about the figure changed. A 6-inch figure placed in a 2.65-inch slot is
reproduced at 0.44 times its authored size, and every piece of type and every
stroke shrinks with it. Your 9.5pt labels arrive at 4.2pt.

## Step 7: Author at the size you place at

Draw the figure at the width it will occupy. Change the figure size, and set the
x ticks so the last label does not overhang the narrower canvas:

```python
fig, ax = plt.subplots(figsize=(2.65, 1.9), constrained_layout=True)
```

```python
ax.set_xticks([2, 4, 6, 8, 10, 12])
```

Run it once more:

```text
Composition audit: loss
  ...
  [PASS] Type size          smallest 9.5pt on page (floor 7.5)
  [PASS] Line weight        2 strokes, thinnest 1.60pt on page (floor 1.0)
  ...
  -> COMPOSED
```

The figure passes at the size it will actually print.

## What you did

You audited a figure, read a failing row, and fixed it three ways: with a style
sheet, with a call that attaches a description, and by changing the size you
authored at.

Two things are worth carrying forward:

- A `[FAIL]` sets the verdict and a `[WARN]` does not.
- Type and stroke measurements are taken on the printed page, not on the canvas,
  so where a figure is placed changes whether it passes.

## Next steps

- [How-to guides](how-to.md) for tasks you now have: gating a whole test suite,
  fixing a specific row, moving a threshold.
- [The gates](gates.md) for what every row measures.
- [How the checkers decide](design.md) for what a passing run does not mean.
