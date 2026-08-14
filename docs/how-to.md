# How to

Recipes. Each one is a task, the code that does it, and the output it produces.

[The gates](gates.md) is the reference for what each row measures.
[The style guide](style-guide.md) is the measurement behind each threshold.
This page is neither. It is what to type.

Every snippet here runs against the vendored import (`import check_figure`).
Installed, the line is `from figure_gate import check_figure`. Nothing else
changes.

## A row failed. Print the remedy with it

`report(..., suggest=True)` prints the table, then what to do about the marked
rows:

```python
import matplotlib
matplotlib.use("agg")                            # (1)!

from check_figure import report, self_test_figure

report(self_test_figure(), "self-test", suggest=True)  # (2)!
```

1. The backend is set before pyplot imports, exactly as the getting-started
   example does: a figure built for measurement has no reason to open a window.
2. `suggest=True` is what turns a failed row into a remedy. Without the optional
   `suggest_fixes.py` beside the checker it prints the table alone.

??? note "The transcript, and what each marked row is telling you"

    ```text
    Composition audit: self-test
      [FAIL] Clipping           clipped: ['a very long axis label that will', ...]  [FIX] add constrained_layout or widen the figure
      [FAIL] Mark ratio         largest/smallest mark area 33.3x  (drawn area 9 to 314 pt^2)  [FIX] cap at 5.0x
      ...
      -> FIX THE MARKED CHECKS

      What to do about the marked rows:
      Clipping:
        - let a layout engine place the artists, or widen the figure
            fig.set_layout_engine("constrained")
      Mark ratio:
        - cap the size range, so the largest mark still reads as a mark
            for ax in fig.axes:
                for c in ax.collections:
                    s = c.get_sizes()
                    if len(s):
                        c.set_sizes(s.clip(None, s.min() * 5.0))
    ```

Each snippet is executed by `tests/test_suggest_fixes.py` against a figure that
fails its gate, and the gate has to pass afterwards. A remedy that does not move
its row fails the build.

For the rows rather than the print:

```python
from check_figure import audit
from suggest_fixes import suggest

ok, rows = audit(fig)
for gate, remedies in suggest(rows):
    print(gate, [r.suggestion for r in remedies])
```

## Every row, and the first move

Eleven rows carry a remedy in `suggest_fixes.py`, and eight of those come with
a snippet. The other ten name their fix in the detail string and stop, mostly
because the answer is to draw something else.

| Row | First move | `suggest()` |
|---|---|---|
| Clipping | Turn on `constrained_layout`, or widen the figure | yes |
| Text collision | Move one of the two named strings. Which one is free is yours to know | |
| Text readability | Move the label to clear ground, or case it against the ink under it | |
| Contrast stack | Take one artist to alpha 1, and keep to three alpha levels | yes |
| Mark ratio | Clip the size array so the largest mark is 5x the smallest | yes |
| Overplotting | Thin the counts, or switch to `hexbin`. Alpha does not move this row | yes |
| Axis redundancy | `sharex`/`sharey` at creation, or `ax.label_outer()` after | yes |
| Type size | Cut words. Do not shrink type | |
| Line weight | Raise `linewidth` to clear 1pt *at the placed scale* | |
| Banking | Set the panel aspect or the figure size to the ratio the row names | |
| Ink coverage | Look at the named panel: empty and saturated both read as a defect | |
| Series color | Fold the tail into "Other", or facet. Both need a redraw | yes |
| Dual axis | Split the two scales into two panels | |
| Form | Redraw: bars from zero, no pie, no 3D | |
| Identity channel | Direct labels, not a legend | |
| Label attribution | Move the label nearer the series it names, or rely on a leader line | |
| Style sheet | Apply the sheet in the same `rc_context` the figure is drawn in | yes |
| Contour dash | `linestyles="solid"` on signed contour data | yes |
| Colormap kind | viridis for sequential, `RdBu` for diverging, `twilight` for cyclic | yes |
| Fonts | Set `pdf.fonttype` and `ps.fonttype` to 42 | yes |
| Alt text | `describe(fig, "...")`, then pass `alt_metadata(fig, path)` to `savefig` | yes |

## Gate every figure in the test suite

The build function is the fixture. `audit` returns `(ok, rows)`, and advisory
rows never return `False`, so `ok` is the whole assertion:

```python
import pytest

from check_figure import audit

from mypaper.figures import FIGURES, build


@pytest.mark.parametrize("name", sorted(FIGURES))
def test_figure_is_composed(name):
    ok, rows = audit(build(name), venue="neurips")  # (1)!
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if s is False)  # (2)!
```

1. `venue="neurips"` tells the type gate how far the figure scales onto the
   page, so text is measured where it renders, not where it was authored.
2. Only hard failures print. Advisory rows are `"warn"` -- a truthy string --
   so `s is False` leaves them out of the assertion message.

Advisory rows never fail a build, and the message follows that on its own:
`"warn"` is a truthy string, so both `not s` and `s is False` select the hard
failures and leave the advisories out. Assert on `ok` and print the rows; there
is no third thing to get right.

To see the advisory rows as well, ask for the ones that are not `True`:

```python
for name, status, detail in rows:
    if status is not True:
        print(name, status, detail)
```

## Gate a palette from a toolchain that is not Python

`check_palette.py` imports nothing outside the standard library and exits 1 on
a failing row. That is the whole CI contract:

```bash
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
echo $?    # 0 all rows pass, 1 something failed
```

??? note "The palette transcript"

    ```text
    Palette (categorical, surface #ffffff): 3 slots
      [PASS] Lightness band               all 3 inside L 0.43-0.77
      [PASS] Chroma floor                 all 3 >= 0.1
      [PASS] CVD separation (all-pairs)   worst #E69F00 vs #009E73 dE 20.7 (protan at severity 1.0) - tritan 12.5
      [PASS] Normal-vision floor (all-pairs) worst #56B4E9 vs #009E73 dE 31.5
      [WARN] Contrast vs surface          under 3.0:1, each needs a visible direct label: [('#E69F00', 2.25), ('#56B4E9', 2.31)]

      -> ALL CHECKS PASS (with advisories - act on the WARN rows)
    ```

The flags:

`--pairs all`
:   scatter and anything a reader reads out of order. Default is `adjacent`

`--ordinal`
:   an ordered ramp. Swaps the five categorical rows for four ramp rows

`--surface "#f4f4f4"`
:   a tinted page. Contrast is measured against this

`--ink "#333333"`
:   neutrals that are exempt from the chroma and lightness rules

A WARN alone still exits 0. Advisory rows report; they do not gate.

## Place a figure at half width, or in a venue's column

The type gate measures what renders on the page, so it needs to know how far
the figure is scaled on the way there. Two arguments carry that.

```python
audit(fig, venue="neurips")                       # full content width
audit(fig, venue="neurips", placed_frac=0.48)     # \includegraphics[width=0.48\textwidth]
audit(fig, scale=0.74)                            # points per authored inch, set outright
```

`python check_figure.py --venues` prints all twelve widths. Verify one against
`\the\textwidth` in your own document before trusting it.

What that changes, on a 4-inch-wide figure with 10pt labels:

```python
>>> float(page_scale(fig, venue="neurips"))
1.380138888888889
>>> float(page_scale(fig, venue="neurips", placed_frac=0.48))
0.6624666666666666
```

The `float()` is there because the scale comes back as a `numpy.float64`, which
a REPL prints as `np.float64(1.38...)` on numpy 2. It compares and computes
like a float everywhere it matters.

At full width the labels arrive at 13.8pt and pass. At `placed_frac=0.48` they
arrive at 6.6pt, under the 7.5pt floor, and the row fails. Same figure, same
call, different page.

## Attach alt text

Two calls. `describe` attaches the text; `alt_metadata` turns it into the
keyword the format wants:

```python
from check_figure import alt_metadata, describe

describe(fig, "Validation loss against epoch for three optimisers. All three "
              "fall; the Bayesian run reaches 0.02 by epoch 12, while the "
              "baseline is still at 0.25.")
fig.savefig("figure-1.png", metadata=alt_metadata(fig, "figure-1.png"))
```

Pass the path twice. `alt_metadata` reads the suffix to pick the key: PNG takes
`Description`, PDF takes `Subject`. Called without a path it assumes PNG, which
warns on a PDF save.

The row wants 60 characters. That floor is there because "Figure 1" and "loss
curve" are what people type when a checker asks for a string. If the document's
caption already carries the description, the row is discharged: it is advisory
and never fails a build.

## Read one row, or one gate

Audit the figure and take the row. `audit` is what normalises the canvas to
`MEASURE_DPI`, so a row read out of it is the row CI will see:

```python
rows = {name: (status, detail) for name, status, detail in audit(fig)[1]}
status, detail = rows["Type size"]
```

The gate functions are importable and callable on their own, and
[the API page](api.md#the-gate-functions) has their signatures. Two caveats.
Several want a renderer, which means drawing the figure yourself. And a gate
called directly measures at whatever dpi the figure is carrying, so its pixel
thresholds are being read at a resolution nobody pinned. Gates with no
renderer argument and no pixel threshold, `check_form` and `check_dual_axis`
among them, are the ones this is safe for:

```python
>>> check_form(fig)
(True, 'no pie, no 3D, no truncated bar baseline')
```

## Change a threshold

Vendored, edit the constant at the top of the file. That is the reason the
default route is a copy.

Installed, assign to it. The gates read the module global when they run:

```python
import check_figure as cf

cf.TYPE_FLOOR_PT = 9.0        # a venue whose floor is higher than SIAM's
ok, rows = cf.audit(fig)
```

Assign before `audit`, not inside a gate, and put it somewhere your reader will
find it. A threshold moved in one test file is a figure that passes locally and
fails in CI.

Every threshold is a module-level constant for this reason. The tables on
[the gates](gates.md) name each one, and
[the style guide](style-guide.md) records what was measured to land on it. A
number you move against a measurement you have read is a decision. A number you
move because a row was inconvenient is the gate deleted, slowly.
