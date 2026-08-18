# The gates

This page lists every row the two checkers return, the threshold each one
measures against, and what makes it fail.

`audit(fig)` returns `(ok, rows)` with one row per figure gate. `check(colors)`
returns the same shape for a palette. Each row is a
`(name, status, detail)` triple, and `status` is `True`, `False`, or `"warn"`.

For what to type when a row fails, see [the how-to guides](how-to.md). For why a
threshold sits where it does, see
[the figure style guide](style-guide.md).

## Figure gates

`check_figure.py` renders the figure through an Agg canvas at
`MEASURE_DPI = 150`, measures the result, and hands the figure back on the dpi
it arrived on. `audit()` returns these 21 rows in this order.

<div class="sortable" markdown>

| Gate | Threshold | Fails when |
|---|---|---|
| Clipping | canvas bounds | a text artist's bbox extends past the canvas |
| Text collision | oriented box overlap | two text boxes overlap, rotation included, tick labels on a shared axis exempted |
| Text readability | `TEXT_CONTRAST_MIN = 4.5` | text misses WCAG AA against the backdrop it actually got, or data ink crosses its glyphs |
| Contrast stack | `ALPHA_LEVELS_MAX = 3` | nothing in the figure is opaque, or transparency uses more than 3 distinct levels |
| Mark ratio | `MARK_RATIO_MAX = 5.0` | largest data mark exceeds 5x the smallest by area |
| Overplotting | `OVERPLOT_THRESHOLD = 0.5` | over half a scatter's points sit close enough to some other point for the two marks to touch on the page *(advisory)* |
| Axis redundancy | shared scale | panels on a shared scale repeat tick labels or axis titles |
| Type size | `TYPE_FLOOR_PT = 7.5` | a string renders under 7.5pt *on the printed page* |
| Line weight | `LINE_FLOOR_PT = 1.0` | a stroke renders under 1pt on the printed page |
| Banking | `BANKING_SLOPE_MAX = 10.0` | a line panel's median segment slope is over 10 or under 1/10, so the aspect ratio puts the typical segment past 84 degrees or under 6 *(advisory)* |
| Ink coverage | `INK_MIN, INK_MAX = 0.02, 0.55` | a panel's ink fraction falls outside the band *(advisory)* |
| Series color | palette gates, `MAX_SERIES_HUES = 6` | the hues actually drawn fail CVD or normal-vision separation, or one panel carries more than 6 |
| Dual axis | none | a `twinx` second scale carries data of its own |
| Form | none | pie, 3D, or bars on a truncated baseline |
| Identity channel | none | two or more series, no legend and no text in the axes *(advisory)* |
| Label attribution | `LABEL_MARGIN = 2.0` | a label's nearest rival series, line or scatter or filled region, is closer than 2x its distance to the one it names |
| Style sheet | 40 keys | the rcParams in effect differ from `figure.mplstyle` *(advisory)* |
| Contour dash | none | a signed contour set dashes its negative levels *(advisory)* |
| Colormap kind | `CMAP_BACKTRAVEL_MAX = 0.02` | a colormap classifies `misc`: its lightness reverses, or its span is flat, or its halves are monotone and its ends match neither cyclic nor diverging. Also when a qualitative map's levels fail all-pairs separation |
| Fonts | Type 42 | PDF or PS export would embed Type 3, or no named typeface resolves *(advisory)* |
| Alt text | `ALT_TEXT_MIN_CHARS = 60` | no description is attached, or the attached one is under 60 characters *(advisory)* |

</div>

### Advisory rows

Eight of the 21 rows are advisory. An advisory row can return `"warn"` but never
`False`, so it never fails a build. `ADVISORY_GATES` in `check_figure.py` is the
list:

- Overplotting
- Banking
- Ink coverage
- Identity channel
- Style sheet
- Contour dash
- Fonts
- Alt text

Type size is the one row that does both. It fails under the floor, and warns on
a figure placed under `PLACED_FRAC_WARN = 0.35` of the content width.

### Detail strings

A row's detail carries up to two marks:

`[FIX]`
:   introduces an action. Nothing else uses this mark.

`[WHY]`
:   introduces the reason the row fired: the published floor, the perceptual
    fact, or what a reader loses.

A detail may carry both, in that order:

```text
under 1.0pt on page at scale 0.50: ['a stroke at 0.40pt']
  [FIX] set linewidth to at least 2.00 at this scale
  [WHY] SIAM: lines thinner than one point break up or disappear in print
```

Every gate except `check_collisions` names a fix. That gate names the two
colliding strings and stops, because which of the pair is free to move is a fact
about the layout it cannot see.

## Palette gates

`check_palette.py` takes hex strings on the command line or through `check()`,
and imports nothing outside the standard library. Distances are CAM02-UCS dE.
The lightness and chroma rows stay in OKLab.

`check(colors)` returns these five rows:

| Gate | Threshold | Fails when |
|---|---|---|
| Lightness band | `L_MIN, L_MAX = 0.43, 0.77` | OKLab lightness outside the band |
| Chroma floor | `CHROMA_MIN = 0.10` | OKLab chroma below it, so the color reads as gray |
| CVD separation | `CVD_TARGET = 10.5` | two hues under 10.5 dE in protan or deutan simulation, at dichromacy or at any severity in `ANOMALOUS_SEVERITIES` |
| Normal-vision floor | `NORMAL_FLOOR = 21.0` | two hues under 21 dE in full color |
| Contrast vs surface | `CONTRAST_MIN = 3.0` | a hue under 3:1 on the page *(advisory)* |

Ink tokens passed through `ink=` are exempt from the lightness and chroma rows.

The separation rows are named `CVD separation (adjacent)` or
`CVD separation (all-pairs)` after the comparison they ran. `all_pairs=False` is
the default and compares neighbours, which is what a line chart needs.
`all_pairs=True` compares every pair, which is what a scatter needs.

Protanopia and deuteranopia are gated. Tritan separation is measured and printed
in the detail string, but not gated.

### Ordinal rows

`ordinal=True` swaps the five categorical rows for four that apply to an ordered
ramp:

| Gate | Threshold | Fails when |
|---|---|---|
| Lightness monotone | direction | lightness does not run one way along the ramp |
| Adjacent dL | `ORDINAL_DL_MIN = 0.06` | two neighbouring steps are closer in lightness than the floor |
| Light-end contrast | `ORDINAL_LIGHT_END_CONTRAST_MIN = 2.0` | the lightest step is under 2:1 against the surface |
| Step uniformity | `ORDINAL_STEP_RATIO_MAX = 2.0` | the largest lightness step is over twice the smallest |

## What each row tells you to do

Eleven rows carry a remedy in `suggest_fixes.py`, and eight of those come with a
runnable snippet. The other ten name their fix in the detail string and stop,
mostly because the answer is to draw something else.

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

## Thresholds

Every threshold is a module-level constant. To change one, see
[Change a threshold](how-to.md#change-a-threshold).

Thresholds cite a published floor where one exists: SIAM's one point, WCAG's
4.5:1, and the Nature, Science, and PNAS type minima. The rest were measured.
[The figure style guide](style-guide.md) records the measurement and the figure
that motivated each one.
