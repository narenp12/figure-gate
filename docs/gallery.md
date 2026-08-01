# Gallery

`python examples/gallery.py` builds these eleven and audits each one. The script
exits non-zero if any figure fails, so they are regression tests with pictures
attached rather than decoration.

They exist because `demo.py` — one panel, three curves — is easy for a gate to
pass, and passing an easy case is the wrong thing for a gate to be good at.
These are the compositions where the checks have somewhere to hide. Writing
them found seven defects in the checks themselves, and two in the figures that
no check caught. Both kinds are named below.

The last four were added by reading every gate's detail string across the first
seven and looking for the ones that had never measured anything. Five had not:
no figure drew a confidence band, a bar, a diverging colormap, a signed contour
set or a `scatter`, so those rows returned a passing detail seven times over
without once running the code that decides. A row that passes by having seen
nothing looks exactly like a row that passed, which is the failure mode the
[gates page](gates.md) names and this page had been an example of.

Every alt text on this page is the string the figure itself carries, passed to
`describe(fig, ...)` before the audit runs — the alt-text gate reads it, so it
is checked rather than written once and forgotten.

---

## Shared scales

<figure markdown="span">
  ![Validation loss against training epoch on four datasets, SGD against Adam. Adam falls faster on all four and reaches a lower floor on CIFAR-10 and SVHN; on CIFAR-100 and Tiny-ImageNet the two converge to the same floor and only the speed differs.](images/gallery-small-multiples.png)
  <figcaption>Four panels on one scale, panel letters, per-panel color. The axis-redundancy gate exists for this shape: tick labels and axis titles repeated down a shared column are ink spent saying nothing.</figcaption>
</figure>

## A filled field

<figure markdown="span">
  ![Rosenbrock function on a log scale as a filled viridis field with isolines, and a 6000-step gradient descent path from (-1.75, 2.15). The path drops into the curved valley within two steps and then crawls along it, ending at (0.93, 0.86), still short of the optimum at (1, 1).](images/gallery-field.png)
  <figcaption>The hardest case in the set, and the one that broke the most checks. <code>check_ink</code> called every colorbar a saturated panel; the line-weight gate measured the colorbar's own dividers as hairline strokes; the path and its start marker in one hue read as a wrapped color cycle; and testing a label's backdrop against its dominant color failed every annotation ever placed on a heatmap. Four gate defects, one figure.</figcaption>
</figure>

## No axes at all

<figure markdown="span">
  ![A four-stage active learning loop: a candidate pool feeds a surrogate model, an acquisition function ranks its predictions, and the top candidates go to the wet lab. Measured labels return from the wet lab to retrain the surrogate.](images/gallery-schematic.png)
  <figcaption>Boxes and arrows with <code>ax.axis("off")</code>. The readability gate was reporting clipped tick labels on a figure that has no visible tick labels. Also the first of the two defects <em>no</em> gate caught: the feedback arrow originally ran off the bottom of the canvas — obvious in the PNG, invisible to every check.</figcaption>
</figure>

## Three statistical forms

<figure markdown="span">
  ![Three panels. (a) Binding fraction for 14 controls and 14 treated samples, every point shown: the treated group is bimodal, which a box plot would hide. (b) Twelve paired before-and-after measurements as a slope graph: all twelve rise. (c) A reliability diagram: observed frequency sits below the diagonal across the whole range, so the model is overconfident.](images/gallery-forms.png)
  <figcaption>The three forms <a href="choosing-a-form/">choosing-a-form.md</a> argues for, drawn as it argues for them. Panel (a) is the case a script cannot decide: a box plot here clears every mechanical gate and still hides both the n of 14 and the bimodality, which are the finding.</figcaption>
</figure>

## Log-log, with a slope triangle

<figure markdown="span">
  ![Maximum global error against step size for forward Euler, Heun and RK4 on log-log axes, over step sizes from 1e-3.2 to 1e-0.6. Each method is a straight line of slope 1, 2 and 4 respectively; a slope triangle marks slope 2 for reference. RK4 flattens at the smallest step sizes, where double-precision round-off dominates truncation.](images/gallery-convergence.png)
  <figcaption>RK4's flat left end is deliberate: a convergence plot that descends forever is a plot of the model, not of the computation. The second defect no gate caught lived here — the slope triangle sat in the only corner the direct labels could use.</figcaption>
</figure>

## Density as the finding

<figure markdown="span">
  ![Orbit diagram of the logistic map for r from 2.5 to 4. A single fixed point splits at r = 3, doubles repeatedly at an accelerating rate, and dissolves into a dense chaotic band at r about 3.57, with windows of periodic behaviour inside it — the widest a period-3 window near r = 3.83.](images/gallery-orbit.png)
  <figcaption>One mark, one opacity, one hue. 168,000 points that are a single object seen at density, not a series — which is why the ink-coverage row is advisory and not a failure.</figcaption>
</figure>

## Three encodings

<figure markdown="span">
  ![Three complex-plane images, each on a colormap matched to what it encodes, and each with the key that kind of encoding takes. (a) Mandelbrot escape time in viridis, a sequential ramp, read against a colorbar running 0 to 60 iterations; the set's interior is a neutral keyed separately as 'did not escape', because that is a separate class and not a small value. (b) Newton basins for z^3 - 1 in three separated hues with a legend naming the three roots, because a basin is a category, nothing orders them, and a colorbar would be a ruler along nothing. (c) The phase of (z^2 - 1)/(z^2 + i/2) in twilight, a cyclic map, on a colorbar ticked at -pi, 0 and pi whose two ends are the same colour because they are the same angle.](images/gallery-encoding.png)
  <figcaption>The figure the colormap gate exists for. Escape time is a quantity and takes a sequential ramp; a Newton basin is a category and takes separated hues; a phase is an angle, so its colormap has to close the loop or a false seam appears where it wraps. Each panel also takes the key its kind implies — a colorbar is a ruler, so the two continuous panels get one and the categorical panel gets a legend instead. The interior of the Mandelbrot set is drawn in a neutral rather than at the bottom of the ramp, because "did not escape" is a separate class and not a small value, and it is keyed off the bar for the same reason.</figcaption>
</figure>

## A band around each curve

<figure markdown="span">
  ![Held-out RMSE against training set size for a Gaussian process and a random forest, each drawn as a line inside its own shaded interval band. The random forest is lower at 25 training points; the curves cross at 40 and the Gaussian process is lower from there on, ending at 0.10 against 0.22 at 1600.](images/gallery-uncertainty.png)
  <figcaption>The seventh gate defect, and the first one a log scale hid. A band lies on top of the curve it belongs to, so <code>check_label_attribution</code> needs <code>_encloses</code> to tell a band from a rival — and <code>_encloses</code> was testing the band's outline through the <em>affine</em> part of the transform only. On a log axis every point read as outside, the band went back to being a rival, and both direct labels failed against their own bands at 0px. This is also the one figure here audited for a place rather than for its canvas: <code>venue="neurips", placed_frac=0.75</code> measures the type and stroke floors at the 0.90x it prints at.</figcaption>
</figure>

## Counts, and a second unit for them

<figure markdown="span">
  ![Counts of 812 deposited structures by resolution bin, as bars from a zero baseline. The distribution peaks at 268 structures in the 2.0 to 2.4 angstrom bin and falls away on both sides; the right-hand axis relabels the same bars as a share of the 812.](images/gallery-counts.png)
  <figcaption>The only bar chart in the corpus. <code>check_form</code> forbids a bar on a truncated baseline and had no <code>BarContainer</code> anywhere to measure, so the row had passed seven times without looking at a bar. Counts from zero is the one comparison <a href="choosing-a-form/">choosing-a-form.md</a> sends to a bar rather than to a dot plot. The right-hand axis is a pure relabel of the same bars, which is the case <code>check_dual_axis</code> exists to permit: <code>secondary_yaxis</code> derives its ticks from the left scale, so the two cannot drift apart the way a <code>twinx</code> with hand-set limits silently can.</figcaption>
</figure>

## A signed field

<figure markdown="span">
  ![Observed minus fitted yield across a grid of flow rate against temperature, as a diverging red-blue field centred on zero with solid isolines. The residual is not noise: it alternates in a checkerboard of positive and negative cells across both factors, so the fitted model is missing an interaction term.](images/gallery-residual.png)
  <figcaption>The fourth colormap kind. A residual has a meaningful zero and two directions away from it, which is what a diverging scale is for, and <code>cmap_kind</code> had never been handed one from this corpus — the encoding figure covers sequential, qualitative and cyclic. The isolines are the second reason: <code>contour.negative_linestyle</code> defaults to dashed, so a monochrome contour over signed data ships its negative half dashed with nobody having chosen it, and in this repo's vocabulary dashing means unobserved or projected. <code>check_contour_dash</code> warns on exactly that and had no signed contour set to look at.</figcaption>
</figure>

## Marks, then bins

<figure markdown="span">
  ![Two panels of log activity against log expression on one pair of scales. (a) 110 cells as a scatter, the two genotypes in two hues, with mark area carrying cell mass. (b) the same measurement on 40000 cells, where the marks would merge, drawn as a hexbin whose color is the count per bin.](images/gallery-density.png)
  <figcaption>The orbit diagram is not a scatter — it is <code>plot(marker=",")</code>, which <code>check_overplotting</code> skips for want of offsets — so the row had returned "no scatter overplotting" seven times without ever building a tree. Panel (a) gives it one, with mark area carrying a third variable so the radii vary and the octave path runs rather than the equal-radii shortcut. Panel (b) is the answer the row's own message gives at 40000 points. The shared window is set rather than inherited: limits driven by the large panel's tails squeezed the 110 marks of (a) into a corner until the overplotting row fired at 73%.</figcaption>
</figure>

---

## The one the checker is supposed to fail

`python skill/scripts/check_figure.py` with no arguments builds a deliberately
broken figure and audits it, so the self-test proves the gates can fail rather
than only that they can pass.

And the figure from the README, which is the method in miniature:

<figure markdown="span">
  ![Validation loss against training epoch for three optimisers over 12 epochs. All three fall; the Bayesian run reaches 0.12 by epoch 6 and 0.02 by epoch 12, while the baseline is still at 0.25 at epoch 12.](images/demo.png)
  <figcaption><code>python examples/demo.py</code> — every decision commented against the failure it avoids.</figcaption>
</figure>
