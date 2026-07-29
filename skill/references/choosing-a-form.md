# Choosing a form

The decision made before any of the other rules apply. A figure in the wrong form
cannot be rescued by palette, type or composition — those make a wrong reading
legible.

`check_figure.py` gates the mechanical subset of this file: pie, 3D, and a bar chart
on a truncated baseline. Those three are wrong regardless of the data, so a script
can decide them. Everything else here needs the data in front of you, which is why
it is prose.

The lineage is statistical graphics rather than general information design —
Cleveland and McGill's perceptual experiments, Tukey's exploratory work, Wilkinson's
grammar as it reached most people through `ggplot2`. Each rule below names the
perceptual or inferential result it rests on, so it can be argued with on those
terms.

---

## The ordering everything else follows

Cleveland & McGill (1984) measured how accurately people read the same quantity
encoded different ways. Their ordering, most accurate first, is six ranks and not
seven:

1. Position along a common scale
2. Position along identical, non-aligned scales
3. Length, direction, angle
4. Area
5. Volume, curvature
6. Shading, color saturation

Colour **hue** is not ranked there, and lists that append it are extending the
paper rather than quoting it. This guide gives hue no magnitude job at all: it
carries identity, which is a different question from how accurately a magnitude
can be read off it.

Almost every rule in this file is a corollary: **move the reader's judgement up the
list.** A dot plot beats a bar because position beats length. Small multiples beat
grouped bars because identical non-aligned scales beat comparing lengths across a
gap. A pie loses because angle and area are both near the bottom. Color sits at the
bottom, which is why it identifies series rather than carrying their magnitudes — and why
`check_palette.py` exists at all: the weakest channel is the one that has to survive
a reader who sees it differently.

---

## The table

| The data | Form | Not |
|---|---|---|
| One distribution, n < ~30 | strip / jittered dot, points shown | box plot |
| One distribution, large n | box or violin, with n stated | a bare mean |
| Comparison across categories | dot plot on a common scale | bar with a cut baseline |
| Counts from zero | bar, baseline at zero | dot plot with a floating axis |
| Paired before/after | slope graph, or difference with its CI | two bars side by side |
| More than ~3 series × groups | small multiples | grouped bars |
| Parts of a whole, 2 parts | one number in the caption | pie |
| Parts of a whole, many parts | small multiples of proportions | stacked bar, pie |
| Data and a fitted model | data as marks, model as one line | both as lines |
| Two continuous variables, large n | hexbin or 2-D density | smaller markers |
| Ordered steps of one quantity | lightness ramp (viridis) | several hues |
| A second unit for the same values | axis relabel with no data of its own | twin axis with data |

---

## Distributions: show the points while you can

**n < ~30 → strip or jittered dot plot, every observation drawn.** A box plot is a
five-number summary, and Tukey designed it for batches too large to draw by hand. At
n = 8 it hides the very thing a reader needs: how many observations there are, and
whether they are bimodal. Two groups with identical quartiles and completely
different shapes draw the same box. In teaching material this matters more, not
less — readers take the summary as the data.

Above roughly 30 the summary starts earning its ink, and above a few hundred a
violin or a box beats a cloud of overlapping points. **State n either way**, in the
axis label or the caption. A distribution figure without n is not interpretable.

**Never a bar with an error bar for a distribution.** The "dynamite plunger" plot
puts a mean on a length encoding and a spread on a whisker, so the eye reads the
bar's area as the quantity and the actual variation as decoration. It is also
ambiguous by construction: nothing on the figure says whether the whisker is an SD,
an SE, or a CI. Draw the points, or draw a dot with an interval.

## Baselines: length needs zero, position does not

**A bar encodes the value as length, so its baseline must be zero.** Cut the axis
and every ratio on the chart is misstated — bars at 101 and 108 drawn from a
baseline of 100 look like a sevenfold difference. This is the one form error that
reliably changes a reader's conclusion, and it is the one `check_figure.py` fails.

**When the baseline is not meaningful, change the form.** A Cleveland dot plot
encodes the value as position, which carries no zero obligation, so the axis can
start wherever the data lives. Categories go on the vertical axis, sorted by value
rather than alphabetically — sorting is free and it turns "find the biggest" from a
scan into a glance.

A log axis is the same argument in different clothes: it cannot contain zero, so it
cannot carry a bar. Use points, and say in the caption that the scale is
multiplicative.

## Paired data: draw the pairing

**Two bars side by side throw away the pairing.** If each subject was measured twice,
the estimand is the per-subject difference, and a reader cannot recover it from two
group means. A slope graph — one line per subject, before on the left, after on the
right, one common scale — puts every pair on the page and makes the exceptions
visible.

**Better still, plot the differences themselves** with their interval. When the
comparison is the point, make the comparison the thing on the axis.

## Small multiples over grouped bars

Beyond about three series in three groups, a grouped bar chart asks the reader to
compare lengths that are not adjacent and do not share a baseline position — task 3
crossed with task 2, done repeatedly. Trellis display (Cleveland, 1993; `facet_wrap`
to everyone who met it through `ggplot2`) splits it into panels on identical scales,
which is task 2 done once per panel.

Panels share their axis furniture — one tick column, one axis label. `check_figure.py`
gates that separately as Axis redundancy.

### Figure-family (small-multiple) consistency checklist

Every panel in a multi-panel figure was chosen for a reason the read declares, and the
same reason constrains how much the panels may differ. These are read-only — no script
decides them:

- **Same context surface, or deliberately different.** A filled-terrain backdrop in one
  panel and white space in another reads as two different kinds of figure, not two
  instances of the same thing. If the surface must differ (e.g. a posterior over one
  variable vs another), say so once and keep the colormap identical.
- **Shared reference points go in the same place.** If panel A draws a dashed circle at
  the optimum, panel B draws it at the same data coordinate, not at whatever the panel's
  limits happen to center on — unless the figure's point is that the second panel has no
  optimum, in which case the dashed circle is the distinctive absence.
- **Emphasis and scale stay comparable.** One panel at 10× the other's zoom asserts the
  tenth panel matters more. If it does, the difference should be explicit in the read
  and the scale bars should say so. If it does not, keep the limits comparable.
- **A consistent marker grammar.** A circle is an observation, a triangle is a prediction,
  a cross is an extremum — and the mapping is the same across every panel that shares
  that kind of mark.
- **Each panel's distinctive mark is actually present.** If three panels in a row carry
  a credible band, the fourth carries one too — or the caption says why it cannot. A
  missing band beside three that have one reads as an oversight rather than as a
  statement about the model, so either draw it, label the panel "not applicable", or
  name the omission in the caption.

## Stacked bars have one honest series

Only the bottom band of a stacked bar sits on a common baseline. Every band above it
starts at a shifted, category-dependent origin, so comparing the third series across
categories is a length judgement with a moving zero — the hardest reading on the
chart, and usually the one the figure was drawn to support. Stack only when the
**total** is the quantity of interest and the parts are context. Otherwise: one panel
per series, or one line per series.

## Model and data in one panel

**Data as marks, the model as a single line.** Drawing both as lines makes a fitted
curve indistinguishable from an observed one, and the fit is the claim being argued.
Drawing only the model is worse: Anscombe's quartet and its modern restatements exist
because summary statistics and fitted lines survive data that looks nothing like what
the reader is imagining.

Name the fit in the caption — OLS, loess with its span, a GAM with its basis. A
smoother is a claim about functional form, and an unnamed one cannot be reproduced or
argued with.

## Uncertainty: say which kind, and put it on the estimand

Every interval on a figure must be named in the caption, because SD, SE and CI are
three different objects and the drawing is identical:

- **SD** describes the spread of the observations. It does not shrink with n.
- **SE** describes the precision of the estimate. It shrinks as `1/sqrt(n)`.
- **CI** is an interval procedure with a stated coverage. Give the level.

**Overlapping confidence intervals are not a significance test.** Non-overlapping 95%
intervals do imply a difference significant at 0.05, but the converse fails: two 95%
intervals can overlap substantially while the difference is significant, because the
standard error of a difference is `sqrt(se_a^2 + se_b^2)`, not `se_a + se_b`. If the
comparison between two groups is the figure's job, plot the **difference** and its
interval. That is one reading of position on a common scale instead of a comparison
the reader has been quietly asked to do wrong.

## Overplotting

At large n, marks stop being individually visible and the figure reports density,
not observations. Shrinking the marker does not fix it — it trades one unreadable
picture for a fainter one. Use transparency (within the 3-alpha-level budget), hexbin,
or a 2-D density estimate, and say which. If the individual points genuinely matter,
the honest answer is that the sample is too large for a scatter and the figure needs
to change question.

## Encode only what exists

A line through unordered categories asserts a sequence the data does not have. A
smooth through five points asserts a function. An area fill under a curve asserts
that the integral means something. Each of these is a claim, and each is easy to make
by accident because the plotting call is one keyword away.

The corollary is the categorical/ordinal decision, which is in the style guide: a
numbered cycle is ordinal and takes a lightness ramp, not four unrelated hues.

## Time series and aspect ratio

When the reader's job is to judge **rates of change**, the aspect ratio is a data
choice, not a layout choice. Cleveland's banking to 45 degrees — choosing the
height-to-width ratio so the typical line segment sits near 45 degrees — is where
slope discrimination is most accurate. A cycle that is obvious in one aspect ratio
disappears in another, and the wrong one is usually the one the default produced.

## The forms with no research-figure use

- **Pie and donut.** Angle and area, the two weakest quantitative tasks, for a job a
  sorted dot plot does better. Two categories are a sentence, not a figure.
- **3D bars, 3D surfaces for 2D data.** Perspective makes identical values plot at
  different sizes, and near marks occlude far ones. A third variable belongs in a
  facet, a color scale, or a contour.
- **Radar / spider.** Area scales as the square of the values, the shape depends on
  the arbitrary order of the axes, and the axes rarely share units.
- **Dual y axes.** Both scales are set by the author, so the crossing point of the two
  curves is an artifact of the limits chosen. `check_figure.py` gates this; the
  exception is a bare unit relabel that carries no data of its own.

---

## References

- Cleveland, W. S. & McGill, R. (1984). Graphical perception: theory,
  experimentation, and application to the development of graphical methods.
  *JASA* 79(387), 531-554. — the perceptual ordering above.
- Cleveland, W. S. (1993). *Visualizing Data.* — dot plots, Trellis display, banking.
- Tukey, J. W. (1977). *Exploratory Data Analysis.* — the box plot, and what it was
  for.
- Wilkinson, L. (2005). *The Grammar of Graphics.* — the decomposition `ggplot2`
  implements.
- Anscombe, F. J. (1973). Graphs in statistical analysis. *The American
  Statistician* 27(1), 17-21.
- Schenker, N. & Gentleman, J. F. (2001). On judging the significance of differences
  by examining the overlap between confidence intervals. *The American Statistician*
  55(3), 182-186. — the overlapping-intervals result.
