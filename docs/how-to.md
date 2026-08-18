# How-to guides

Each guide here solves one task. They assume you have the checkers installed and
have run an audit before. If you have not, start with
[Gate your first figure](tutorial.md).

Every snippet uses the vendored import, `import check_figure`. If you installed
the package, the line is `from figure_gate import check_figure`. Nothing else
changes.

For what a row measures, see [The gates](gates.md). For why a threshold sits
where it does, see [the figure style guide](style-guide.md).

## Print the remedy for a row that failed

Pass `suggest=True` to `report`. It prints the table, then what to do about the
rows that did not pass:

```python
import matplotlib
matplotlib.use("agg")                            # (1)!

from check_figure import report, self_test_figure

report(self_test_figure(), "self-test", suggest=True)  # (2)!
```

1. Set the backend before pyplot imports. A figure built for measurement has no
   reason to open a window.
2. `suggest=True` turns a failed row into a remedy. Without the optional
   `suggest_fixes.py` beside the checker, it prints the table alone.

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

To work with the remedies as data rather than as printed text:

```python
from check_figure import audit
from suggest_fixes import suggest

ok, rows = audit(fig)
for gate, remedies in suggest(rows):
    print(gate, [r.suggestion for r in remedies])
```

Each snippet is a template against a bound `fig`, not a drop-in.

## Gate every figure in your test suite

Use your figure-building function as the fixture. `audit` returns `(ok, rows)`,
and advisory rows never return `False`, so `ok` is the whole assertion:

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
   page, so text is measured where it renders rather than where it was authored.
2. Only hard failures print. Advisory rows are `"warn"`, a truthy string, so
   `s is False` leaves them out of the message.

To see the advisory rows too, select the rows that are not `True`:

```python
for name, status, detail in rows:
    if status is not True:
        print(name, status, detail)
```

## Gate a palette from a toolchain that is not Python

`check_palette.py` imports nothing outside the standard library and exits 1 on a
failing row. That exit code is the contract for a non-Python build:

```bash
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
echo $?    # 0 all rows pass, 1 something failed
```

A `[WARN]` row still exits 0. Advisory rows report; they do not gate.

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

For every flag, see [the command reference](cli.md#check_palettepy).

## Place a figure at a venue's width

The type and line-weight gates measure what renders on the page, so they need to
know how far the figure is scaled on the way there. Three arguments carry that:

```python
audit(fig, venue="neurips")                       # full content width
audit(fig, venue="neurips", placed_frac=0.48)     # \includegraphics[width=0.48\textwidth]
audit(fig, scale=0.74)                            # points per authored inch, set outright
```

To see what a placement does to the scale, call `page_scale` on a 4-inch-wide
figure with 10pt labels:

```python
>>> float(page_scale(fig, venue="neurips"))
1.380138888888889
>>> float(page_scale(fig, venue="neurips", placed_frac=0.48))
0.6624666666666666
```

At full width the labels arrive at 13.8pt and pass. At `placed_frac=0.48` they
arrive at 6.6pt, under the 7.5pt floor, and the row fails. Same figure, same
call, different page.

`float()` appears here because the scale comes back as a `numpy.float64`, which
a REPL prints as `np.float64(1.38...)` on numpy 2. It compares and computes like
a float everywhere it matters.

For all twelve venue widths, see [Venue widths](cli.md#venue-widths). Verify one
against `\the\textwidth` in your own document before you trust it.

## Attach alt text

Call `describe` to attach the text, then `alt_metadata` to turn it into the
keyword your output format wants:

```python
from check_figure import alt_metadata, describe

describe(fig, "Validation loss against epoch for three optimisers. All three "
              "fall; the Bayesian run reaches 0.02 by epoch 12, while the "
              "baseline is still at 0.25.")
fig.savefig("figure-1.png", metadata=alt_metadata(fig, "figure-1.png"))
```

Pass the path to both calls. `alt_metadata` reads the suffix to pick the key:
PNG takes `Description`, PDF takes `Subject`. Called without a path, it assumes
PNG, which warns on a PDF save and is rejected outright by SVG.

The row wants 60 characters. If your document's caption already carries the
description, you can leave the row: it is advisory and never fails a build.

## Read one row, or call one gate

Audit the figure and take the row you want. `audit` normalises the canvas, so a
row read out of it is the row your CI will see:

```python
rows = {name: (status, detail) for name, status, detail in audit(fig)[1]}
status, detail = rows["Type size"]
```

The gate functions are importable and callable on their own, and
[the API reference](api.md#the-gate-functions) has their signatures:

```python
>>> check_form(fig)
(True, 'no pie, no 3D, no truncated bar baseline')
```

Two limits apply when you call a gate directly:

- Several gates need a renderer, which means drawing the figure yourself.
- A gate called directly measures at whatever dpi the figure is carrying, so its
  pixel thresholds are read at a resolution nobody pinned.

Gates that take no renderer argument and use no pixel threshold, such as
`check_form` and `check_dual_axis`, are the ones this is safe for.

## Change a threshold

If you vendored the checkers, edit the constant at the top of the file. That is
the reason the default route is a copy.

If you installed the package, assign to the constant. The gates read the module
global when they run:

```python
import check_figure as cf

cf.TYPE_FLOOR_PT = 9.0        # a venue whose floor is higher than SIAM's
ok, rows = cf.audit(fig)
```

Assign before you call `audit`, not inside a gate, and put the assignment
somewhere your reader will find it. A threshold moved in one test file is a
figure that passes locally and fails in CI.

Every threshold is a module-level constant for this reason.
[The gates](gates.md) names each one, and
[the figure style guide](style-guide.md) records what was measured to land on
it.
