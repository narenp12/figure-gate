# Gallery

`python examples/gallery.py` builds these six and audits each one. The script
exits non-zero if any figure fails, so they are regression tests with pictures
attached rather than decoration.

They exist because `demo.py` — one panel, three curves — is easy for a gate to
pass, and passing an easy case is the wrong thing for a gate to be good at.
These are the compositions where the checks have somewhere to hide. Writing
them found five defects in the checks themselves, and two in the figures that
no check caught. Both kinds are named below.

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
  ![Rosenbrock function on a log scale as a filled viridis field with isolines, and a 28-step gradient descent path from (-1.9, 2.2). The path drops into the curved valley within four steps and then crawls along it, still short of the optimum at (1, 1) after 28.](images/gallery-field.png)
  <figcaption>The hardest case in the set, and the one that broke the most checks. <code>check_ink</code> called every colorbar a saturated panel; the line-weight gate measured the colorbar's own dividers as hairline strokes; the path and its start marker in one hue read as a wrapped color cycle; and testing a label's backdrop against its dominant color failed every annotation ever placed on a heatmap. Four gate defects, one figure.</figcaption>
</figure>

## No axes at all

<figure markdown="span">
  ![A four-stage active learning loop: a candidate pool feeds a surrogate model, an acquisition function ranks its predictions, and the top candidates go to the wet lab. Measured labels return from the wet lab to retrain the surrogate.](images/gallery-schematic.png)
  <figcaption>Boxes and arrows with <code>ax.axis("off")</code>. The readability gate was reporting clipped tick labels on a figure that has no visible tick labels. Also the first of the two defects <em>no</em> gate caught: the feedback arrow originally ran off the bottom of the canvas — obvious in the PNG, invisible to every check.</figcaption>
</figure>

## Three statistical forms

<figure markdown="span">
  ![Three panels. (a) Binding fraction for 14 controls and 14 treated samples, every point shown: the treated group is bimodal, which a box plot would hide. (b) Twelve paired before-and-after measurements as a slope graph: eleven of twelve rise. (c) A reliability diagram: observed frequency sits below the diagonal across the whole range, so the model is overconfident.](images/gallery-forms.png)
  <figcaption>The three forms <a href="../choosing-a-form/">choosing-a-form.md</a> argues for, drawn as it argues for them. Panel (a) is the case a script cannot decide: a box plot here clears every mechanical gate and still hides both the n of 14 and the bimodality, which are the finding.</figcaption>
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

---

## The one the checker is supposed to fail

`python skill/scripts/check_figure.py` with no arguments builds a deliberately
broken figure and audits it, so the self-test proves the gates can fail rather
than only that they can pass.

And the figure from the README, which is the method in miniature:

<figure markdown="span">
  ![Validation loss against training epoch for three optimisers. All three curves fall; the Bayesian run reaches 0.05 by epoch 6, the baseline is still at 0.25 at epoch 12.](images/demo.png)
  <figcaption><code>python examples/demo.py</code> — every decision commented against the failure it avoids.</figcaption>
</figure>
