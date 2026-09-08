# check_figure defect round: the fires that should not happen

Date: 2026-08-31

Branch `check-figure-false-positives`, cut from `main` at `19f6409`. It does not
depend on `spec-r-svg-substrate` and is intended to merge ahead of it.

## Why this round exists

An adversarial sweep of `check_figure.audit` over roughly 207 figures found
about twenty defects in the checker itself. That is a larger and more severe set
than the SVG substrate carries, which was not the expected result: the SVG
checker had been the one under suspicion.

The suite did not catch any of them. `check_figure.py` sits at 91.2% line
coverage and 87.6% branch coverage, and all 21 of its gates meet CONTRIBUTING's
two-test bar. Neither number helped, because the corpus behind them never
contained an inset axes, an annotation carrying an arrow, a Gantt chart, a
size-encoded scatter, or a per-point alpha array. Coverage measures the code the
tests were written against. It cannot measure the figures nobody drew.

That is the finding this round is built on, and it is why the remedy is corpus
breadth rather than more tests against the existing corpus.

## What this branch takes, and why that boundary

The twenty defects split cleanly by which direction their fix moves the fire
rate, and that split is what makes a first branch safe to merge.

**This branch takes only fixes that strictly reduce fires**: one crash, one API
trap, and five false positives. None of them can introduce a new over-fire,
because every one of them makes a gate fire less often than it does today. For
the six gate changes the guarantee is exact: a figure that passes on `main`
still passes after this branch, so no caller's green run turns red.

Item 2 is the one exception and it is deliberate. Making `venue` keyword-only
turns a positional call that silently returned a wrong verdict into a
`TypeError`. That is a caller break rather than a gate change, it is the only
way to close the path, and it is confined to a call form that was already
producing a wrong answer.

Everything whose fix *adds* fires is deferred, because each addition needs to be
measured against the corpus and adjudicated before it can be trusted. Those are
listed at the end so they are not lost.

## Verified defects

Every item below was reproduced against `main`'s `check_figure.py` on
2026-08-31. The quoted output is real, not paraphrased.

### 1. Contrast stack crashes on a per-point alpha array

```python
fig, ax = plt.subplots(figsize=(3, 2))
ax.scatter([0, 1], [0, 1], s=40, alpha=[0.5, 1.0])
```

```text
Contrast stack = False :: gate raised TypeError: only 0-dimensional arrays
                          can be converted to Python scalars
```

`check_contrast_stack` calls `float(a.get_alpha())`. Array alpha has been
documented matplotlib since 3.4, and `_rows` turns a crashed non-advisory gate
into `False`. Legal matplotlib, legal composition, hard failure. Also reproduces
through `ax.pcolormesh(..., alpha=array)`.

**Fix.** Treat a non-scalar alpha as the set of levels it contains, so an array
contributes its distinct values rather than raising. A gate that cannot read an
artist must not convert that into a verdict about the figure.

**Acceptance.** The figure above passes. A scatter carrying an array with four
distinct alpha levels still fails, for the right reason and with the levels
named in the detail. No gate in the roster can turn an exception into `False`
without saying so.

### 2. `audit()` silently discards `venue` passed positionally

```text
audit(fig, None, 1.0, 'neurips')  -> (True,  'smallest 8.0pt on page (floor 7.5)')
audit(fig, venue='neurips')       -> (False, 'under 7.5pt on page at scale 0.92')
signature: (fig, scale=None, placed_frac=1.0, context_axes=None, venue=None)
```

The fourth positional parameter is `context_axes`. A venue string passed there
is iterated into `frozenset(id(ax) for ax in ...)`, which succeeds silently
because a string is iterable. Nothing raises. The venue is discarded and a
failing figure reports green.

**Fix.** Make `context_axes` and `venue` keyword-only. This is a breaking change
to a public signature below 1.0, so it is named in the changelog under its
release heading as the stability statement requires.

**Acceptance.** The positional form raises `TypeError` rather than returning a
wrong verdict. `check_svg.audit` and `report` are checked for the same shape and
made consistent if they share it.

### 3. An annotation's arrow inflates its text box

```python
ax.annotate("A", xy=(8, np.sin(8)), xytext=(2, 0.9), arrowprops=dict(arrowstyle="->"))
ax.annotate("B", xy=(2, np.sin(2)), xytext=(8, -0.9), arrowprops=dict(arrowstyle="->"))
```

```text
Text collision: (False, "overlapping: [('A', 'B')]")
  'A' bbox w=285.4 h= 23.5
  'B' bbox w=301.0 h=283.1
```

Two single-character labels at opposite corners, reported as overlapping. Their
strings are nowhere near each other; only the arrows cross.
`get_window_extent` on an `Annotation` spans text and leader together, so a
one-character label measures 285 points wide.

Three rows read that box: Text collision, Label attribution, and Text
readability, which samples the backdrop under the whole arrow span. Label
attribution is the sharpest case, because the row's own `[FIX]` and
`docs/gates.md` both offer "draw a leader line" as the remedy, and using it
creates the failure:

```python
ax.annotate("Tuned", xy=(5.0, 1.0), xytext=(5.0, 1.7),
            arrowprops=dict(arrowstyle="-", lw=1.0))
```
```text
Label attribution: (False, "'Tuned' is 4px from its own curve and 0px from another")
```

**Fix.** Measure the string, not the annotation. Take the text extent excluding
the arrow patch for all three rows.

**Acceptance.** Both figures above pass. Two labels whose *strings* genuinely
overlap still fail. The remedy named in the detail string discharges the row it
is printed under, which is checked by a test that follows the advice and asserts
the row then passes.

### 4. A panel title is read as a direct label

```python
ax.plot(x, np.sin(x), label="Baseline")
ax.plot(x, np.sin(x) * 1.2, label="Ours")
ax.set_title("Baseline", fontsize=11)
```
```text
Label attribution: (False, "'Baseline' is 94px from its own curve and 83px from another")
```

A title's `.axes` is the parent axes, so it satisfies the `t.axes is ax` guard
and is judged as a direct label. `check_label_attribution`'s premise is that
"only text whose string matches exactly one series label is judged, because only
there is the intent known". That premise does not hold for titles, axis labels
or colorbar labels, which routinely repeat a series name without pointing at it.

**Fix.** Exclude the title, axis labels and colorbar labels from the direct
label candidates. Identity, not string matching, is what separates them.

**Acceptance.** The figure passes. A genuine in-axes direct label that is nearer
a rival series than its own still fails.

### 5. Axis redundancy never checks the scale is shared

```python
a.plot([0, 1], [0, 2]); a.set_ylabel("Distance (km)")
b.plot([0, 1], [0, 2]); b.set_ylabel("Duration (s)")
```
```text
Axis redundancy: (False, 'repeated y tick column x1  [FIX] use sharex/sharey')
```

Two different quantities in two different units, whose tick *strings* happen to
coincide. `docs/gates.md` promises the row fires when "panels on a shared scale
repeat tick labels". `check_redundancy` compares tick text only and never asks
whether the scale is shared. The advice it gives would be wrong to follow.

**Fix.** Require the panels to be on a shared scale before comparing their tick
labels: matching limits and matching scale type, or an actual shared-axis
relationship. Also reproduces in a `subplot_mosaic` where one panel spans two
rows and sharing is geometrically impossible.

**Acceptance.** The figure passes. Two panels genuinely on one scale, both
printing the tick column, still fail. The row's behaviour matches the sentence
in `docs/gates.md`, which is asserted by `tests/test_docs_match_code.py`.

### 6. Clipping fires on a secondary axis

```python
ax.plot([1, 2, 3], [1, 4, 9])
ax.secondary_xaxis("top", functions=(lambda v: v * 2, lambda v: v / 2))
```
```text
Clipping: (False, "clipped: ['1', '7']  [FIX] add constrained_layout or widen the figure")
```

A secondary axis is a child axes, so `secondary in fig.axes` is `False`.
`_texts` finds its tick labels through `fig.findobj`, but `_ghost_ticks` walks
`fig.axes` only, so ticks the locator placed outside the secondary's own view
are never recognised as ghosts and are reported as clipped text.

This shares a root cause with the child-axes blind spot deferred below, but only
the ghost-tick half belongs here, because fixing it removes fires. Making the
other rows *see* child axes adds them, and that is branch two.

**Fix.** Let `_ghost_ticks` walk child axes as well as `fig.axes`.

**Acceptance.** The figure passes, in both the `secondary_xaxis` and
`secondary_yaxis` forms and with the identity-function form. Text genuinely
running past the canvas still fails.

### 7. Colormap kind: 8-bit quantisation inflates back-travel

`cmap_back_travel` takes hex strings, so every sample is rounded to 8 bits per
channel before its lightness is computed. On a smooth ramp those roundings
produce oscillations of about 0.001 OKLab that accumulate into the back-travel
measure.

| cmap | float | quantised | floor 0.02 |
|---|---|---|---|
| **winter** | **0.0139** | **0.0343** | **verdict flips** |
| spring | 0.0427 | 0.0427 | fires in both, correct |
| cool | 0.2481 | 0.2481 | fires in both, correct |
| gist_earth | 0.0321 | 0.0354 | fires in both, correct |
| turbo | 0.8222 | 0.8275 | fires in both, correct |
| viridis | 0.0000 | 0.0010 | passes in both, correct |
| Blues | 0.0000 | 0.0000 | passes in both, correct |

`winter` is the only map among these whose verdict the quantisation changes. Its
true reversals are ±0.001 artifacts of 1/255 channel steps in a linear ramp.

**Fix.** Give `check_palette` a float sampling path for colormap classification,
so the ramp is measured before the 8-bit round trip. The hex API stays for
callers that have only hex.

**Acceptance.** `winter` passes. `spring`, `cool`, `gist_earth`, `turbo`,
`jet`, `rainbow`, `hsv` and the qualitative maps still fail. A sweep over all
installed colormaps records which verdicts moved, and the answer is expected to
be `winter` alone; any other mover is adjudicated before merge.

## Testing

Each item gets the CONTRIBUTING pair: a test proving the gate no longer fires on
the legitimate figure above, and a test proving it still fires on the nearest
genuine defect. The second is what stops these fixes becoming holes.

The seven figures above join the corpus as builders, because the reason these
defects survived is that no corpus figure exercised the construct. Adding the
fix without adding the figure repeats the mistake.

Every change is measured against the eleven gallery builders plus `demo.build`
before the PR opens, and the result goes in the PR body including "no verdict
changed" when that is the answer. The sweep imports the modules and sets
`gallery.OUT = None`, and keeps `gallery.main` and `gallery.finish` out of the
enumeration, so the committed PNGs are not rewritten.

## Explicitly deferred

**Branch two, fixes that add fires.** Each needs a corpus sweep and adjudication
before it can be trusted, which is why none of them are here.

- Child axes are invisible to roughly 15 of 21 rows. A pie, a 0.15pt hairline
  and a `jet` heatmap inside `inset_axes` all pass; the same content in a normal
  axes fails. `add_child_axes` never reaches `fig.axes`.
- Line weight measures only `Line2D`, `LineCollection` and unfilled contours.
  Patch edges, annotation arrows, spines and tick marks are unmeasured, so a
  schematic drawn at 0.15pt returns "no strokes to measure". Note that spines
  default to 0.8pt, so this fix will fire widely and needs the same
  furniture-versus-data judgment the SVG substrate already had to make.
- Contrast stack cannot see alpha baked into an RGBA colour. Six levels with
  nothing opaque passes, while the identical picture drawn with `alpha=` as a
  kwarg fails.
- Type size reads nominal `get_fontsize()`, so mathtext shrink is invisible. A
  nested subscript at nominal 11pt renders at 5.39pt and passes a 7.5pt floor.
- Form reads only `BarContainer`, so a truncated-baseline bar chart drawn with
  patches passes.
- Overplotting sees only `PathCollection`, so the identical cloud drawn with
  `ax.plot(..., "o")` passes where `ax.scatter` warns.
- Axis redundancy checks duplicate y tick columns only; the x direction gets
  label-text checking but no tick-row checking.
- Text collision never forms tick-versus-annotation or tick-versus-title pairs,
  which is broader than the documented shared-axis exemption.
- Colormap kind sees only artists carrying an array, so a pre-evaluated `jet`
  ramp escapes both it and Series color.

**Branch three, threshold and design judgments.** These are arguments about
where a line sits, not logic errors, and each needs a decision before code.

- Form fires on any offset baseline, so Gantt, waterfall and floating bars fail
  although bar length still encodes the value exactly.
- Series color rejects every 4-step single-hue ramp: no spread of `Blues` or
  `Greys` clears the 21.0 normal-vision floor, best measured 18.1, so the
  `[FIX]` it prints cannot be carried out and ordered stacks are unconditionally
  red.
- Mark ratio fires on size-encoded scatters, against its own docstring, which
  exempts bars because "a bar thirty times another bar is the encoding working".
- Text readability fires on annotated heatmap cells where a gridline crosses the
  label, because the cell colour on either side of the gridline reads as foreign
  ink. A 5x5 confusion matrix on the project's own sheet fails at 39 to 52%.
- Contrast stack fails a single deliberate global alpha and a graded fan chart.
  Both are canonical statistical graphics.

## Risks

The `venue` keyword-only change is a public API break. It is deliberate, it is
the only way to close a silent wrong-verdict path, and it is small, but it needs
its changelog entry and a scan of the docs and skill for positional call sites.

Item 7 reaches into `check_palette.py`, which `check_figure` and `check_svg`
both depend on. The float path is additive and the hex API is unchanged, so
neither caller changes behaviour except for the `winter` verdict.

Items 3 and 4 both touch `check_label_attribution`. They are independent in
effect but will conflict in the diff, so they are written as one commit or in a
fixed order.
