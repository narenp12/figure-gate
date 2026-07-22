---
name: research-figures
description: >
  Produce publication-quality static figures for documents — papers, slides,
  lecture decks, reports, theses, posters — using matplotlib, with mechanical
  gates for colorblind-safe color, composition, and type legibility at the size
  the figure actually prints. Use this whenever the user is making a figure,
  diagram, chart, or explanatory graphic that will be placed in a written or
  presented document, even if they only say "add a figure to the paper," "make
  a diagram for this slide," "plot the results for my thesis," or hand you a
  .tex/.typ/.md file and ask for a visual. Also use it when the user asks about
  colorblind-safe or accessible palettes, Okabe-Ito, viridis, reliability or
  calibration diagrams, figure typography, why a figure looks amateurish or
  "AI-generated," or why text in a rendered figure came out too small to read.
  Not for interactive web dashboards or HTML/React charts — that is a different
  problem with different constraints.
---

# Research figures

Figures that look authored rather than generated. The method is: decide the
figure's one job, build it on the bundled style sheet, then run two validators
that catch the failures the eye reliably misses.

Nearly every rule here was earned by a specific defect on a real figure, and
`references/style-guide.md` names the failure beside the rule. When you are
about to deviate, read the relevant note first — most deviations were already
tried and reverted for a measured reason.

## What matplotlib already handles

Do not hand-roll these. Reaching for a custom colormap or a manual rcParams dict
is the most common way this work goes wrong, because the builtin was designed by
people who measured it:

| Need | Use | Not |
|---|---|---|
| Sequential / ordinal | `cmap="viridis"` | a hand-built ramp |
| Diverging | `cmap="RdBu"` (`RdBu_r` if low = blue) | two hand-picked poles |
| Colorblind-safe categorical | `colormaps["okabe_ito"]` (matplotlib ≥ 3.11) | a private palette |
| Defaults: type, ink, spines, grid | `assets/figure.mplstyle` | an rcParams dict in the plotting file |
| Layout | `constrained_layout=True` | manual `subplots_adjust` |

What remains genuinely project-specific: which figure to draw, how large the
type must end up **on the page**, and whether the composition works.

## Setup

Copy the bundled files into the project, once:

```bash
mkdir -p diagrams
cp <skill>/assets/figure.mplstyle diagrams/
cp <skill>/scripts/check_palette.py <skill>/scripts/check_figure.py diagrams/
```

Then set two things and nothing else:

1. `font.serif` in `figure.mplstyle` → the surrounding document's body face.
2. `CONTENT_WIDTH_PT` at the top of `check_figure.py` → the usable width, in
   points, of the page the figure lands in. Render one page, place a full-width
   figure, measure. Within ~5% is fine; it only sets the type floor.

If the project already has brand colors, use them and re-run `check_palette.py`.
The method survives the swap; the specific hex values do not.

## Procedure

**1. Write the read before drawing anything.** One sentence: *"This is a
&lt;form&gt; for &lt;audience&gt;, whose job is &lt;the one takeaway&gt;."* It is
what you check the finished figure against, and it prevents the most expensive
failure — a well-made figure answering a question nobody asked.

**2. Ground it in the surrounding text.** Read the section the figure lands in
and steal its vocabulary. If the text says "binding affinity," the figure says
that, not "potency." Two vocabularies for one idea on one page reads as two
authors.

Compute real numbers. Fit the actual model, compute the actual curve. A
hand-drawn approximation of a statistical object will eventually be wrong in a
way a reader notices, and this matters most in teaching material, because
readers believe it.

**3. Build on the style sheet.**

```python
from pathlib import Path
import matplotlib.pyplot as plt

plt.style.use(str(Path(__file__).parent / "figure.mplstyle"))
fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
```

Resolve the style sheet relative to the *file*, not the working directory.
`plt.style.use("figure.mplstyle")` raises `OSError: not a valid package style`
the moment anything runs from a different cwd — a test runner, a build script,
an editor's run button.

Journal figure, not dashboard: hairlines and bare text positioned by geometry,
panel letters `(a)` `(b)`, frameless legends. No drop shadows, tinted cards,
pill chips, gradients, or an in-figure title competing with the caption. If an
element can be deleted without losing meaning, it was decoration.

Dashing means something specific — *unobserved*, *projected*, *threshold*. A
true-but-unknown curve is dashed because it is unknown; a guide ring is not,
because "this is a cycle" is not a hedge.

**4. Compose deliberately.** Every gate in this skill is an *elimination* gate:
each forbids one enumerated failure, and none of them ever looks at the figure
as a whole. A figure can pass all of them and still be a gray smudge. These are
the composition rules no script can infer for you:

- One thing is opaque. At most 3 alpha levels. Context layers get the
  transparency; the data does not. Everything semi-transparent reads as haze
  with no focal point.
- Marks stay within ~4× of each other in area. Emphasis is a different *shape*
  or a label, never 5× the area — past that a mark stops reading as data and
  starts reading as an ornament stuck on top.
- Context surfaces get structure — bands, hairline isolines — not just a neutral
  hue. An unstructured gradient is a coffee stain, because the eye has no edge
  to hold. Neutral does not mean formless.
- Panels sharing a scale share their axis furniture (one y label, one tick
  column). Sharing runs along the axis the panels are stacked on, not both.
- Encode only what exists. A path drawn through unordered points asserts a
  sequence the data does not have. When a figure looks wrong and you cannot say
  why, suspect the encoding before the styling.
- Ordinal emphasis is a lightness ramp, not a transparency stack — a ramp keeps
  every mark opaque; ten alpha steps produce ten kinds of haze.

**5. Run both validators.** They answer different questions, and passing one
says nothing about the other.

```bash
python check_figure.py                          # self-test on a deliberately bad figure
python check_palette.py "#E69F00,#56B4E9"       # lines, bars, stacked marks
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all   # scatter, small multiples
python check_palette.py "#471365,#2c718e,#44bf70" --ordinal     # ordered ramp
```

```python
from check_figure import report, audit
report(fig, "my-figure")     # PASS/WARN/FAIL per check
ok, rows = audit(fig)        # same, programmatically
```

`check_figure.py` gates clipping, text collision, alpha stacking, mark ratio,
axis redundancy, type size, and ink coverage. `check_palette.py` gates lightness
band, chroma floor, colorblind separation, normal-vision separation, and
contrast against the surface.

**WARN is not FAIL, and the difference is load-bearing.** A sub-3:1 hue is legal
*if* it carries a visible direct label; a saturated panel is fine *if* it is a
heatmap. Read the row and decide — do not skim past it. A gate everyone learns
to ignore is worse than no gate, which is why the context-dependent checks warn
instead of failing.

**6. Then render a PNG and look at it.** Vector output is not readable as a
file. The checker sees geometry, not meaning: it cannot tell you an arrow points
at the wrong thing, that reading order runs backwards, or that a label is true
of the concept and false of the curve beside it.

**7. Render the finished document and look at that too.** A figure that is
perfect as a standalone PNG can be illegible on the page it ships on. This is
the step that gets skipped and the one that catches the most embarrassing
defects.

## Color

Read `references/style-guide.md` before deviating — every constraint below has a
measurement behind it, and several obvious-looking "improvements" were tried and
reverted.

**Categorical: Okabe-Ito, in its published order.** Builtin since matplotlib
3.11 as `colormaps["okabe_ito"]`; the eight are black, orange `#E69F00`, sky
blue `#56B4E9`, bluish green `#009E73`, yellow `#F0E442`, blue `#0072B2`,
vermillion `#D55E00`, reddish purple `#CC79A7`.

**Take slots in order, never cherry-picked by meaning.** One series → orange.
Three → orange, sky blue, bluish green. Choosing semantically ("blue is
structure, red is training") is how a palette that looks fine measures ΔE 3.2
under protanopia. The in-order rule exists to keep that from happening.

Two limits worth knowing: scatter and small multiples compare *every* series
against every other, and only the first four slots clear that — past four, fold
the tail into "Other" or facet. And there is no seventh series hue; a generated
one is indistinguishable from an existing slot under simulated color blindness.

Orange, sky blue and reddish purple sit under 3:1 on a light page. Legal, but
each needs a **visible direct label**. Yellow at 1.29:1 genuinely vanishes as a
hairline — use it as a fill with a dark edge or not at all.

**Grayscale is a separate question and Okabe-Ito does not solve it.** The
canonical first two, orange and sky blue, differ by ΔL 0.011 — invisible once
desaturated, and the single worst pair in the set. When the figure must survive
a photocopier, select by luminance instead (orange + blue, ΔL 0.264), say so,
and add a second channel: dash pattern or marker shape.

**Status colors come from the same palette** — `good #009E73`, `warning
#E69F00`, `critical #D55E00` — always shipped with an icon or label. An
independent status set lands in near-misses rather than matches, and a reader
cannot tell whether two nearly-identical reds mean two things or one. Status is
a role, not a reservation: a hue can be a series color or a status color in a
given figure, never both.

**Sequential is `cmap="viridis"` as shipped.** A filled cell is read against its
neighbours and the colorbar, never against the page, so its light end carries no
contrast obligation and windowing it only throws range away. The one exception:
*discrete tiers drawn as standalone lines or marks* do stand alone against the
page, and full-range viridis ends at `#fde725`, 1.23:1, invisible as a hairline
— sample `t ∈ [0.05, 0.70]`, evenly.

**Categorical or ordinal is the decision that matters,** and the intuitive
answer is usually wrong. Categorical = independent identities. Ordinal = ordered
steps of one thing, which takes a lightness ramp. **A numbered cycle is
ordinal.** Reaching for four unrelated hues because there are four boxes is the
most common mistake in this whole skill.

**Text on a colored fill** clears the *text* threshold, not the mark threshold:
4.5:1, or 3:1 at ≥14pt bold. Text otherwise wears ink tokens, never the series
color — a colored mark *beside* text carries the identity.

## Type legibility

**Author each figure at the width it will actually be placed at.** Then the
scale is 1.0, authored points are printed points, and there is no budget to
compute. This is what journal templates have always done and it makes the whole
problem disappear.

When you cannot, `check_figure.py` derives the scale per figure from that
figure's own width against `CONTENT_WIDTH_PT` and fails any string landing under
7.5pt on the page. Per-figure is the entire point: a 14-inch figure on a 750pt
slide shrinks to 0.74×, an 8.6-inch one is blown up to 1.21×, and the same 10pt
label is comfortable in one and unreadable in the other.

**If text does not fit, cut the text.** "Acquisition function ranks the candidate
molecules" becomes "Rank every candidate." The caption carries the rest.
Shrinking type to fit is how a figure ends up rendering at 6pt on a lecture-hall
screen while looking fine on your monitor.

## Wire the gates into the build

A figure that silently breaks is worse than one that fails loudly.

```python
import pytest
from check_figure import audit

@pytest.mark.parametrize("name", sorted(DIAGRAMS))
def test_figure_is_composed(name):
    fig = build(name)
    ok, rows = audit(fig)
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if not s)
```

Also include a test asserting the gate **fails** on a deliberately bad figure. A
gate that cannot fail is decoration, and this one silently stopped working twice
while it was being written.

## When a figure passes everything and still looks wrong

That is information, not noise: it names a failure mode with no gate yet. Write
the gate. Every check in `check_figure.py` exists because a figure passed all
the checks that came before it and was still visibly broken.

Prefer moving a rule into `figure.mplstyle` over writing it as prose — a rule
you have to remember is a rule that eventually gets forgotten. Prefer a check
you can run over an adjective you have to feel.

## Reference

`references/style-guide.md` — the full guide: the measurements behind every
threshold, the named failures each rule prevents, the palette tables with
contrast ratios, and the notes on rules that were changed or deleted and why.
Read it when deviating from a constraint, when a validator fails in a way you
want to argue with, or when porting the checks to a non-matplotlib stack.
