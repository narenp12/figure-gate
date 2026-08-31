---
description: "Eleven audited figures covering the forms that are hard to check, and the defects that writing them found."
---

# Gallery

`python examples/gallery.py` builds these thirteen figures and audits each one.
The script exits non-zero if any figure fails, so they are regression tests with
pictures attached rather than decoration.

They exist because `demo.py`, one panel and three curves, is easy for a gate to
pass, and passing an easy case is the wrong thing for a gate to be good at.
These are the compositions where a check has somewhere to hide. Writing them
found seven defects in the checks themselves, and two in the figures that no
check caught. Both kinds are listed at the end of this page.

Every alt text here is the string the figure itself carries, passed to
`describe(fig, ...)` before the audit runs, so the alt-text gate reads it.

---

## Shared scales

<figure markdown="span">
  ![Validation loss against training epoch on four datasets, SGD against Adam. Adam falls faster on all four and reaches a lower floor on CIFAR-10 and SVHN; on CIFAR-100 and Tiny-ImageNet the two converge to the same floor and only the speed differs.](images/gallery-small-multiples.png)
  <figcaption>Four panels on one scale, panel letters, per-panel color. The axis-redundancy gate exists for this shape: tick labels and axis titles repeated down a shared column are ink spent saying nothing.</figcaption>
</figure>

## A filled field

<figure markdown="span">
  ![Rosenbrock function on a log scale as a filled viridis field with isolines, and a 6000-step gradient descent path from (-1.75, 2.15). The path drops into the curved valley within two steps and then crawls along it, ending at (0.93, 0.86), still short of the optimum at (1, 1).](images/gallery-field.png)
  <figcaption>A field, isolines, and a colorbar in one panel. This figure broke four checks on its own, more than any other in the set.</figcaption>
</figure>

## No axes at all

<figure markdown="span">
  ![A four-stage active learning loop: a candidate pool feeds a surrogate model, an acquisition function ranks its predictions, and the top candidates go to the wet lab. Measured labels return from the wet lab to retrain the surrogate.](images/gallery-schematic.png)
  <figcaption>Boxes and arrows with <code>ax.axis("off")</code>. A figure with no data and no visible tick labels is the case most gates were not written against.</figcaption>
</figure>

## Three statistical forms

<figure markdown="span">
  ![Three panels. (a) Binding fraction for 14 controls and 14 treated samples, every point shown: the treated group is bimodal, which a box plot would hide. (b) Twelve paired before-and-after measurements as a slope graph: all twelve rise. (c) A reliability diagram: observed frequency sits below the diagonal across the whole range, so the model is overconfident.](images/gallery-forms.png)
  <figcaption>The three forms <a href="choosing-a-form/">choosing a form</a> argues for. Panel (a) is the case no script can decide: a box plot here clears every mechanical gate and still hides both the n of 14 and the bimodality, which are the finding.</figcaption>
</figure>

## Log-log, with a slope triangle

<figure markdown="span">
  ![Maximum global error against step size for forward Euler, Heun and RK4 on log-log axes, over step sizes from 1e-3.2 to 1e-0.6. Each method is a straight line of slope 1, 2 and 4 respectively; a slope triangle marks slope 2 for reference. RK4 flattens at the smallest step sizes, where double-precision round-off dominates truncation.](images/gallery-convergence.png)
  <figcaption>RK4's flat left end is deliberate: a convergence plot that descends forever is a plot of the model, not of the computation. The direct labels sit at the left end, where a log-log fan separates the curves by three decades.</figcaption>
</figure>

## Density as the finding

<figure markdown="span">
  ![Orbit diagram of the logistic map for r from 2.5 to 4. A single fixed point splits at r = 3, doubles repeatedly at an accelerating rate, and dissolves into a dense chaotic band at r about 3.57, with windows of periodic behaviour inside it; the widest is a period-3 window near r = 3.83.](images/gallery-orbit.png)
  <figcaption>One mark, one opacity, one hue. 168,000 points that are a single object seen at density, not a series, which is why the ink-coverage row is advisory rather than a failure.</figcaption>
</figure>

## Three encodings

<figure markdown="span">
  ![Three complex-plane images, each on a colormap matched to what it encodes, and each with the key that kind of encoding takes. (a) Mandelbrot escape time in viridis, a sequential ramp, read against a colorbar running 0 to 60 iterations; the set's interior is a neutral keyed separately as 'did not escape', because that is a separate class and not a small value. (b) Newton basins for z^3 - 1 in three separated hues with a legend naming the three roots, because a basin is a category, nothing orders them, and a colorbar would be a ruler along nothing. (c) The phase of (z^2 - 1)/(z^2 + i/2) in twilight, a cyclic map, on a colorbar ticked at -pi, 0 and pi whose two ends are the same colour because they are the same angle.](images/gallery-encoding.png)
  <figcaption>The figure the colormap gate exists for. Escape time is a quantity and takes a sequential ramp; a Newton basin is a category and takes separated hues; a phase is an angle, so its colormap has to close the loop or a false seam appears where it wraps. Each panel takes the key its kind implies: a colorbar is a ruler, so the two continuous panels get one and the categorical panel gets a legend.</figcaption>
</figure>

## A band around each curve

<figure markdown="span">
  ![Held-out RMSE against training set size for a Gaussian process and a random forest, each drawn as a line inside its own shaded interval band. The random forest is lower at 25 training points; the curves cross at 40 and the Gaussian process is lower from there on, ending at 0.10 against 0.22 at 1600.](images/gallery-uncertainty.png)
  <figcaption>A confidence band lies on top of the curve it belongs to, so the label-attribution gate has to tell a band from a rival series. This is also the one figure here audited for a place rather than for its canvas: <code>venue="neurips", placed_frac=0.75</code> measures the type and stroke floors at the 0.90x it prints at.</figcaption>
</figure>

## Counts, and a second unit for them

<figure markdown="span">
  ![Counts of 812 deposited structures by resolution bin, as bars from a zero baseline. The distribution peaks at 268 structures in the 2.0 to 2.4 angstrom bin and falls away on both sides; the right-hand axis relabels the same bars as a share of the 812.](images/gallery-counts.png)
  <figcaption>The only bar chart in the corpus. Counts from zero is the one comparison <a href="choosing-a-form/">choosing a form</a> sends to a bar rather than to a dot plot. The right-hand axis is a pure relabel of the same bars, which is the case <code>check_dual_axis</code> exists to permit: <code>secondary_yaxis</code> derives its ticks from the left scale, so the two cannot drift apart the way a <code>twinx</code> with hand-set limits silently can.</figcaption>
</figure>

## A signed field

<figure markdown="span">
  ![Observed minus fitted yield across a grid of flow rate against temperature, as a diverging red-blue field centred on zero with solid isolines. The residual is not noise: it alternates in a checkerboard of positive and negative cells across both factors, so the fitted model is missing an interaction term.](images/gallery-residual.png)
  <figcaption>A residual has a meaningful zero and two directions away from it, which is what a diverging scale is for. The isolines are drawn solid on purpose: <code>contour.negative_linestyle</code> defaults to dashed, so a monochrome contour over signed data ships its negative half dashed with nobody having chosen it, and dashing here means unobserved or projected.</figcaption>
</figure>

## Marks, then bins

<figure markdown="span">
  ![Two panels of log activity against log expression on one pair of scales. (a) 110 cells as a scatter, the two genotypes in two hues, with mark area carrying cell mass. (b) the same measurement on 40000 cells, where the marks would merge, drawn as a hexbin whose color is the count per bin.](images/gallery-density.png)
  <figcaption>Panel (a) varies mark area to carry a third variable. Panel (b) is the answer the overplotting row's own message gives at 40000 points. The shared window is set rather than inherited: limits driven by the large panel's tails squeezed the 110 marks of (a) into a corner until the overplotting row fired at 73%.</figcaption>
</figure>

## A callout that points

<figure markdown="span">
  ![A damped oscillation in millivolts against time in seconds. The amplitude decays from 1.0 at time zero, each swing smaller than the last, and a leader line marks the first trough at about 1.5 seconds, where the signal reaches -0.63.](images/gallery-callout.png)
  <figcaption>The leader is the point of the figure. Three rows read one box per string, and on an annotation that box spanned the arrow too, so a one-character callout measured 285 points wide and two labels at opposite corners were reported as overlapping. No corpus figure drew a leader line, which is why three rows could misfire on one for as long as they did.</figcaption>
</figure>

## Two scales for one quantity

<figure markdown="span">
  ![Load in pounds rising linearly with length in inches, from 3 pounds at one inch to 25 pounds at twelve. A second axis across the top carries the same lengths in millimetres, 25 to 305, so the figure can be read in either unit.](images/gallery-secondary-scale.png)
  <figcaption>A second axis carrying the same quantity in another unit is not a dual axis: there is still one data scale, and the top axis is a unit conversion of the bottom one. A secondary axis is a child axes and never reaches <code>fig.axes</code>, so ticks the locator placed outside its own view were read as clipped text rather than as ghosts.</figcaption>
</figure>

---

## Why the last four exist

The first seven figures were audited against every gate, and the detail strings
showed which rows had never measured anything. Five had not. No figure drew a
confidence band, a bar, a diverging colormap, a signed contour set, or a
`scatter`, so those rows returned a passing detail seven times over without once
running the code that decides.

A row that passes by having seen nothing looks exactly like a row that passed.
That is the blind spot [how the checkers decide](design.md#what-a-passing-run-does-not-mean)
names, and this page had been an example of it.

## The seven defects in the checks

1. The readability gate reported a schematic's invisible tick labels.
2. `check_ink` called every colorbar a saturated panel.
3. The line-weight gate measured a colorbar's own dividers as hairline strokes.
4. A path and its start marker in one hue read as a wrapped color cycle.
5. Testing a label's backdrop against its dominant color failed every annotation
   ever placed on a heatmap.
6. `check_label_attribution` passed labels in the right margin that sat 29px
   from their own curve and 35px from a neighbour's. A label outside the data is
   not resolved by proximity to anything.
7. `_encloses` tested a band's outline through the affine part of the transform
   only, so on a log axis a confidence band stopped being its own curve's band
   and became its rival.

## The two defects no check caught

- The schematic's feedback arrow ran off the bottom of the canvas.
- The convergence plot's slope triangle sat in the only corner its direct labels
  could use.

Both were obvious in the PNG and invisible to every check. They are why the
procedure has a step that says to render the figure and look at it.

## The figure the checker is supposed to fail

`python skill/scripts/check_figure.py` with no arguments builds a deliberately
broken figure and audits it, so the self-test proves the gates can fail rather
than only that they can pass.

<figure markdown="span">
  ![Validation loss against training epoch for three optimisers over 12 epochs. All three fall; the Bayesian run reaches 0.12 by epoch 6 and 0.02 by epoch 12, while the baseline is still at 0.25 at epoch 12.](images/demo.png)
  <figcaption><code>python examples/demo.py</code>, with every decision commented against the failure it avoids.</figcaption>
</figure>
