# The gates

`audit(fig)` returns `(ok, rows)`, one row per gate. `check(colors)` gates a
palette the same way. This page is what each row measures and the threshold it
measures against; [the style guide](style-guide.md) is the measurement behind
each threshold and what to do when a row fails.

## Why the two scripts talk to each other

A figure on matplotlib's default `tab10` cycle, with a `twinx` second axis,
returned nothing but passing rows from the composition checks. `check_palette.py` rated
that same cycle's orange and green at dE 1.4 under protanopia: one hue to that
reader, against a floor of 8. The composition checker had no access to the
colors it was drawing.

`check_series_color` closes that. It reads the hues off the figure's own
artists, decides from the mark types whether the figure needs adjacent
separation (lines, bars) or all-pairs separation (scatter), and runs them
through the palette gates. That is row 12 of the 21.

## What each gate measures

**`check_palette.py`** takes hex strings on the command line or via `check()`,
and imports nothing outside the standard library. Distances are OKLab dE x100.

| Gate | Threshold | Fails when |
|---|---|---|
| Lightness band | `L_MIN, L_MAX = 0.43, 0.77` | OKLab lightness outside the band |
| Chroma floor | `CHROMA_MIN = 0.10` | OKLab chroma below it, so the color reads as gray |
| CVD separation | `CVD_TARGET = 8.0` | two hues under 8 dE in protan or deutan simulation, at dichromacy or at any severity in `ANOMALOUS_SEVERITIES` |
| Normal-vision floor | `NORMAL_FLOOR = 15.0` | two hues under 15 dE in full color |
| Contrast vs surface | `CONTRAST_MIN = 3.0` | a hue under 3:1 on the page *(advisory)* |

`--ordinal` swaps those five rows for four that apply to a ramp: lightness
monotone, adjacent dL gap, light-end contrast, and step uniformity
(largest/smallest dL). Protanopia and deuteranopia are gated, together about 8%
of males. Tritan separation is measured and printed in the detail string but
not gated: prevalence is around 0.01%, and the Vienot matrix used here is
validated only for the red-green forms, so the number is indicative rather than
decisive.

The separation row is swept over severity rather than read at dichromacy. Most
colour vision deficiency is anomalous trichromacy, and dichromacy is not the
worst case for it: measured over 240000 pairs of hues `check_palette.py` would
accept as series slots, 0.87% clear the floor at dichromacy and miss it at some
lower severity, and dichromacy overstates separation by up to 10.5 dE. The row
names the severity its worst reading came from. `simulate_anomalous` is the
Machado, Oliveira & Fernandes (2009) model; `simulate` remains Vienot dichromacy
and is what every number quoted in the style guide was measured on.

**`check_figure.py`** renders the figure through an Agg canvas, at the dpi it
was authored at, and measures the result. `audit()` returns these 21 rows in
this order.

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
| Line weight | `LINE_FLOOR_PT = 1.0` | a stroke renders under 1pt on the printed page (SIAM's floor) |
| Banking | `BANKING_SLOPE_MAX = 10.0` | a line panel's median segment slope is over 10 or under 1/10, so the aspect ratio puts the typical segment past 84 degrees or under 6 *(advisory)* |
| Ink coverage | `INK_MIN, INK_MAX = 0.02, 0.55` | a panel's ink fraction falls outside the band *(advisory)* |
| Series color | palette gates, `MAX_SERIES_HUES = 6` | the hues actually drawn fail CVD or normal-vision separation, or one panel carries more than 6 |
| Dual axis | none | a `twinx` second scale carries data of its own |
| Form | none | pie, 3D, or bars on a truncated baseline |
| Identity channel | none | two or more series, no legend and no text in the axes *(advisory)* |
| Label attribution | `LABEL_MARGIN = 2.0` | a label's nearest other series, line or scatter, is closer than 2x its distance to the one it names |
| Style sheet | 40 keys | the rcParams in effect differ from `figure.mplstyle` *(advisory)* |
| Contour dash | none | a signed contour set dashes its negative levels *(advisory)* |
| Colormap kind | `CMAP_BACKTRAVEL_MAX = 0.02` | a colormap classifies `misc`: its lightness reverses, or its span is flat, or its halves are monotone and its ends match neither cyclic nor diverging. Also when a qualitative map's levels fail all-pairs separation |
| Fonts | Type 42 | PDF/PS export would embed Type 3, or no named typeface resolves *(advisory)* |
| Alt text | `ALT_TEXT_MIN_CHARS = 60` | no description is attached, or the attached one is under 60 characters *(advisory)* |

Thresholds cite a published floor where one exists: SIAM's one point, WCAG's
4.5:1, the Nature/Science/PNAS type minima. The rest were measured, and
[the style guide](style-guide.md) records the measurement and the figure that
motivated each one.

## The gate that catches people

Type size is measured on the printed page, not on the canvas. A figure authored
at 14 inches (1008pt) and placed on a 750pt slide renders at 750/1008 = 0.74x,
so a 9pt label arrives at 6.7pt, under the 7.5pt floor, and under it by an
amount no one notices on a monitor. `page_scale` derives that ratio per figure
and the type gate measures what renders, so sizes set through rcParams or by a
helper are caught along with the ones set inline.

Placing at a fraction of the content width changes the ratio again:
`audit(fig, placed_frac=0.48)` mirrors `\includegraphics[width=0.48\textwidth]`,
and without it a half-width figure is certified at twice the type size it
ships at. For a venue in the table, `audit(fig, venue="neurips")` supplies the
width; `python check_figure.py --venues` prints all twelve with their content
widths in points.

## What a passing run does not mean

Every check is an elimination gate: each one forbids a single enumerated
failure, and none looks at the figure as a whole. 21 passing rows means the
figure avoids 21 named defects. It does not mean the figure is good, and the
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

**WARN is not FAIL.** Eight of the 21 rows are advisory, in that they can
return `"warn"` but never `False`, and `ADVISORY_GATES` in `check_figure.py` is
the list. A sub-3:1 hue is legal when it carries a direct label; a heatmap panel
legitimately measures 0.98 ink coverage. Failing those would train people to
ignore the row, and an ignored gate is worth less than no gate. Type size is
the one row that does both: it fails under the floor, and warns on a figure
placed under 35% of the content width.

**Gates are tested for their ability to fail.** The suite is 1206 tests, and
each check has one asserting it catches a figure with exactly that defect. The
style sheet has its own tests because `#` starts a comment in matplotlib's
style format: `grid.color: #e1e0d9` parses as an empty value, matplotlib keeps
its default, and every other test stays green.

The full reasoning, meaning the measurements behind each threshold and the
rules that were tried and reverted, is in [the style guide](style-guide.md).

Which *form* the data wants is the decision no styling rule rescues, and it is
in [choosing a form](choosing-a-form.md), built on Cleveland & McGill's ordering
of the elementary perceptual tasks. Only its mechanical subset is gated: a
script can rule out a pie or a truncated bar baseline, but it cannot tell you a
box plot is hiding an n of 8.
