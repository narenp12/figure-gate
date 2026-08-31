# Auditing a figure outside the sheet it was built under changes the verdict

Branched from `check-figure-false-positives`. Present on `main`.

## The report

Auditing the same figure twice returns different verdicts. `demo` passes
`Label attribution` on the first audit and fails on the second. The offered
cause was that `_renderer`'s draw settles `constrained_layout` and moves the
label. It is also why the baseline sweep shows `demo` and `encoding` failing
while their own internal reports print all-PASS.

## What was measured

Both halves reproduce. The offered cause does not survive.

`examples/demo.py` builds and reports under `@styled`, which holds
`plt.style.context(skill/assets/figure.mplstyle)` open across construction and
across `cf.report` (`examples/demo.py:82`). `examples/gallery.py:110` has the
same decorator, which is why `encoding` behaves the same way.

Auditing after `build(out=None)` returns, so with the context closed:

```
after report():       axes x0=76.08   'Baseline' w= 82.00  'Tuned' w= 62.31
audit-time draw 1:    axes x0=85.08   'Baseline' w=100.00  'Tuned' w= 74.00
audit-time draw 2:    axes x0=85.08   'Baseline' w=100.00  'Tuned' w= 74.00
```

`Label attribution` passes for the first and fails for the second and third:
`'Tuned' is 12px from its own curve and 18px from another`.

Auditing the undecorated builder inside a style context we hold open ourselves,
so that every draw sees the same rcParams:

```
report() verdict: True
draw after report:      axes x0=76.08  'Baseline' w=82.00  'Tuned' w=62.31
audit #1: passed=True   3 direct labels, each nearest the curve it names
draw after audit 1:     axes x0=76.08  'Baseline' w=82.00  'Tuned' w=62.31
audit #2: passed=True   ...
draw after audit 2:     identical
audit #3: passed=True   ...
draw after audit 3:     identical
```

Four draws, byte-identical geometry, one verdict.

## The cause

The audit is idempotent. What is not idempotent is the rcParams the figure is
measured under.

Outside the sheet, `font.family` falls back to the matplotlib default. Every
glyph gets wider: `'Baseline'` 82.00 → 100.00 px, `'Tuned'` 62.31 → 74.00,
`'Bayesian'` 87.44 → 106.00, all at unchanged heights, which is the signature
of a font swap rather than a layout settle. `constrained_layout` then re-solves
against wider tick labels and axis titles and moves the axes: `x0` 76.08 →
85.08. The annotations are anchored in data coordinates, so the curves and the
labels move by different amounts and `'Tuned'` lands nearer a neighbour.

`constrained_layout` is downstream of the font change, not the cause of it. A
figure with the layout engine live re-solves identically on every draw as long
as the text it is solving around measures the same.

Two rows in the same sweep already say so and were read as separate noise:

- `Style sheet`: `34 of 40 keys differ from figure.mplstyle`
- `Fonts`: `pdf.fonttype and ps.fonttype = 3 (Type 3)`

Both are `warn`, so neither failed the sweep, and the row that did fail was the
one with no obvious connection to rcParams.

## Scope

The defect is in how a figure is handed to `audit`, not in any gate. Options,
in the order they should be considered:

1. Have the sweep harness audit each builder inside the builder's own context.
   Smallest change, fixes the reported symptom, leaves the trap in place for
   the next caller.
2. Have the figure carry the sheet it was drawn under, and have `audit` measure
   inside it. Fixes the class. Needs a decision about a figure built under no
   sheet, and about a figure whose sheet has since changed on disk.
3. Have `audit` refuse, or warn loudly, when `Style sheet` reports drift on
   this scale. Cheap, and turns a silent wrong verdict into a legible one, but
   drift is legitimate for a figure built on another project's sheet, which is
   exactly why that row is a warning today.

Whichever lands, the fire-rate harness needs a regression that audits one
builder twice, once inside its context and once outside, and asserts the
verdicts agree.

## Reproduction

Scripts used: `repro.py` (double audit), `repro3.py` (snapshot around
`report`'s draw), `repro4.py` (both audits inside one held style context).
