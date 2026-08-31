# Auditing a figure outside the sheet it was built under changes the verdict

Date: 2026-08-31
Status: design

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

It is not a family fallback. `font.family` is captured into each Text artist's
FontProperties at construction and does not move: measured on either side of
the context boundary, every label still reports `family=['serif']` at
`size=11.00`. What is not captured is the list that `serif` resolves through.

```
inside the sheet   font.serif = ['STIX Two Text', 'STIXGeneral', 'DejaVu Serif']
                   findfont -> STIXTwoText.ttf
outside            font.serif = ['DejaVu Serif', 'Bitstream Vera Serif', ...]
                   findfont -> DejaVuSerif.ttf
```

Same family, same nominal size, different face, so every glyph gets wider:
`'Baseline'` 82.00 → 100.00 px, `'Tuned'` 62.31 → 74.00, `'Bayesian'` 87.44 →
106.00. `constrained_layout` then re-solves against wider tick labels and axis
titles and moves the axes: `x0` 76.08 → 85.08. The annotations are anchored in
data coordinates, so the curves move with the axes and the labels do not move
the same way, and `'Tuned'` lands nearer a neighbour.

`constrained_layout` is downstream of the face change, not the cause of it. A
figure with the layout engine live re-solves identically on every draw as long
as the text it is solving around measures the same.

Two rows in the same sweep already say so and were read as separate noise:

- `Style sheet`: `34 of 40 keys differ from figure.mplstyle`
- `Fonts`: `pdf.fonttype and ps.fonttype = 3 (Type 3)`

Both are `warn`, so neither failed the sweep, and the row that did fail was the
one with no obvious connection to rcParams.

## What shipped

The defect is in how a figure is handed to `audit`, not in any gate, so the fix
is one level above the gates and none of them changed.

`METRIC_RC_KEYS` names the rcParams a string's measured size depends on: the
family and the six lists a family name resolves through, size and the four style
axes, the two mathtext keys, `text.usetex` and `text.antialiased`.
`_at_draw_rc` records them onto the figure at its first audit and runs every
later audit under the recorded values. `audit` enters it alongside
`_at_measure_dpi`, which is the same move for the same reason: a measurement
read against a knob nobody pinned.

Two rows are deliberately left reading the live rcParams, because they answer
for the environment rather than for the figure. `check_fonts` splits along that
line on its own, since `pdf.fonttype` and `ps.fonttype` are not metric keys: its
Type 3 clause still says what a `savefig` from here would embed, while its face
clause reads the pinned family. `check_style_sheet` keeps reporting the drift
that says the sheet is not applied.

`tests/test_style_context_invariance.py` holds every other row identical across
the two contexts for `demo` and `encoding`, asserts the three-audit agreement
the report asked about, pins the record to the first audit rather than the
latest, and — following `test_renderer_invariance.py` — puts the old behaviour
back through the new code path by emptying `METRIC_RC_KEYS`, so the sweep is
known to be able to fail.

### The limitation, stated

The record is taken at the first audit because that is the earliest moment this
module is handed the figure; there is no hook at construction. A figure built
under a sheet whose *first* audit happens outside it records the wrong baseline
and is then wrong consistently rather than differently each time. `demo` and
the gallery builders are not in that case: they call `cf.report` inside their
own `@styled` context.

Closing that would mean recording at draw time rather than at audit time, which
needs either a hook this module does not have or a new public call for the
author to make. Neither is worth it for a case the `Style sheet` and `Fonts`
rows already flag.

## Reproduction

Scripts used: `repro.py` (double audit), `repro3.py` (snapshot around
`report`'s draw), `repro4.py` (both audits inside one held style context),
`mech2.py` (the resolved font file on either side of the boundary). `mech.py`
was a false start worth recording: it pinned `font.serif` to the same first
entry the default list already has, so it could not have detected the face
change and appeared to exonerate the fonts.
