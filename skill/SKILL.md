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
| Cyclic (phase, angle, heading) | `cmap="twilight"` | a sequential ramp with a seam at the wrap |
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

**For a named algorithm or model, ground the figure in its canonical definition**
(paper, repo, standard reference) — not the slide prose or a remembered summary.
Check that the figure shows the objects the algorithm is *defined* by: if a
method's whole idea is a stochastic weight average, the figure must show that
average, not just the trajectories around it. A figure that illustrates an
algorithm but omits its defining object is a diagram of something else.

Compute real numbers. Fit the actual model, compute the actual curve. A
hand-drawn approximation of a statistical object will eventually be wrong in a
way a reader notices, and this matters most in teaching material, because
readers believe it.

**3. Choose the form, before any code.** This is the decision the other rules
cannot rescue: palette, type and composition make a wrong reading *legible*, not
right. Read `references/choosing-a-form.md` — it is organised around Cleveland &
McGill's ordering of how accurately people read each encoding, and every rule in
it names the perceptual or inferential result behind it.

The three that come up most: n under about 30 wants a strip or dot plot showing
every point, because a box hides n and hides bimodality; a comparison whose
baseline is not meaningful wants a dot plot, not a bar with the axis cut, because
length needs a zero and position does not; and paired measurements want a slope
graph or the differences themselves, because two bars throw the pairing away.
`check_figure.py` gates the mechanical subset — pie, 3D, truncated bar baseline.

**4. Build on the style sheet.**

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

**5. Compose deliberately.** Every gate in this skill is an *elimination* gate:
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

**A direct label is a box, not a point, and the alignment is the whole
decision.** On a curve with any slope, `ha="center"` is the one alignment that
puts both ends of the label back down on the line: it clears the curve at the
anchor and nowhere else, because across the label's own width the curve has
moved further than the offset holding the text up. Pick the side the curve is
leaving:

```python
# descending curve: clear ground above it runs RIGHT, below it runs LEFT
ha = "left" if above else "right"
```

Anchor on the extreme of the data across the label's span, not on its value at
one point — sampled noise routinely spikes further than any sane offset. And
casing (`path_effects=[pe.withStroke(...)]`) rescues a 0.7pt gridline behind a
label; it does not rescue a 1.6pt curve, where it only hides the collision by
erasing the data. `check_text_readability` measures the backdrop rather than the
finished render for exactly that reason.

**6. Run both validators.** They answer different questions, and passing one
says nothing about the other.

```bash
python check_figure.py                          # self-test on a deliberately bad figure
python check_palette.py "#E69F00,#56B4E9"       # lines, bars, stacked marks
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all   # scatter, small multiples
python check_palette.py "#471365,#2c718e,#44bf70" --ordinal     # ordered ramp
```

```python
from check_figure import report, audit, describe, alt_metadata
report(fig, "my-figure")             # PASS/WARN/FAIL per check
report(fig, suggest=True)            # and what to do about the marked rows
ok, rows = audit(fig)                # same, programmatically
ok, rows = audit(fig, venue="neurips")   # measure type against \textwidth
```

A marked row's detail says what broke, then carries two marks that mean
different things. [FIX] introduces an action and nothing else wears it; [WHY]
introduces the reason the row fired, the published floor or the perceptual fact
behind it. Read the first, keep the second for the sentence you write in the
caption.

```
[FAIL] Line weight  under 1.0pt on page at scale 0.50: ['fit at 0.20pt']
       [FIX] set linewidth to at least 2.00 at this scale
       [WHY] SIAM: lines thinner than one point break up or disappear in print
```

`suggest=True` prints remedies from `suggest_fixes.py`, which is separate from
the gates on purpose: a gate measures, and what to do about it is a claim that
can be wrong on its own. Some rows carry more than one, because the choice
between them is yours. Every remedy that ships a code snippet is executed by
the test suite against a figure that fails its gate, and the gate has to pass
afterwards.

**Describe the figure for a reader who cannot see it.** Across 100,000 public
notebooks, 99.81% of generated images shipped with no alt text, nearly all of
them matplotlib. Say what the reader would have taken from looking — the
numbers and the direction — not what the figure is made of:

```python
describe(fig, "Validation loss against epoch for three optimisers. All three "
              "fall; the Bayesian run reaches 0.12 by epoch 6, the baseline is "
              "still at 0.25 at 12.")
fig.savefig(path, metadata=alt_metadata(fig, path))
```

Pass `path` to `alt_metadata` as well as to `savefig`. PNG, PDF and SVG all keep
a description and none of them calls it the same thing: PDF's info dictionary
has no `Description` and matplotlib warns on every save, while SVG *raises* on
PDF's `Subject`. With the path it picks the right one. For a format with no
description field — ps, or any of the rasters — it returns `None`, which is the
only value `savefig` accepts there; a jpeg rejects `metadata={}` as hard as a
full dict.

`check_figure.py` gates clipping, text collision, text readability, alpha
stacking, mark ratio, overplotting, axis redundancy, type size, line weight,
banking, ink
coverage, series color, dual axes, form, the identity channel, label
attribution, whether the style sheet is the one actually in effect, contour
dash, colormap kind, font embedding, and alt text — in that order. `check_palette.py` gates
lightness band, chroma floor, colorblind separation, normal-vision separation,
and contrast against the surface.

The two used to be unable to speak: `check_palette.py` judged a list of hexes
someone remembered to paste into a terminal, and `check_figure.py` never looked
at color. So a figure on matplotlib's default `tab10` cycle, whose orange and
green sit at CAM02-UCS ΔE 2.4 under protanopia against a floor of 10.5 and are
one hue to that reader, passed the whole composition suite clean. **Series color** closes it by reading the hues the
figure actually drew and putting those through the palette gates, inferring
adjacent-versus-all-pairs from whether the marks are scatter.

**WARN is not FAIL, and the difference matters.** A sub-3:1 hue is legal
*if* it carries a visible direct label; a saturated panel is fine *if* it is a
heatmap. Read the row and decide — do not skim past it. A gate everyone learns
to ignore is worse than no gate, which is why the context-dependent checks warn
instead of failing.

**7. Then render a PNG and look at it.** Vector output is not readable as a
file. The checker sees geometry, not meaning: it cannot tell you an arrow points
at the wrong thing, that reading order runs backwards, or that a label is true
of the concept and false of the curve beside it.

Save with `fig.savefig(path)` and let the style sheet set dpi and bbox. Never
`bbox_inches="tight"`: it trims to the drawn content, so the saved width stops
being the width you authored, and the type gate derives its floor from that
width. The gate then passes a figure whose shipped size it never measured.

**8. Render the finished document and look at that too.** A figure that is
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

One limit worth knowing: scatter and small multiples compare *every* series
against every other, and the first six slots clear that. The worst pair is
`#0072B2` vs `#CC79A7` at ΔE 12.8 under protanopia, against a target of 10.5.
That used to read five: the sixth measured 7.9 against a target of 8 in OKLab,
whose distances have no calibrated threshold, and the two spaces do not even
agree on which pair is worst. And there is no seventh series hue; a generated one
is indistinguishable from an existing slot under simulated color blindness.

`figure.mplstyle` now sets `axes.prop_cycle` to the six series slots, so a
figure built on the sheet is on the right palette without anyone remembering to
say so. Pass an explicit `color=` only when you mean to depart from it.

Orange and sky blue sit under 3:1 on a white page. Legal, but each needs a
**visible direct label**, and **a legend entry does not count as one.** The
obligation exists because the mark is faint against the page; a legend leaves
the reader matching a small faint swatch to a small faint curve, which is the
step a direct label removes. Put the text at the mark. Yellow at 1.32:1
genuinely vanishes as a hairline — use it as a fill with a dark edge or not at
all.

**Grayscale is a separate question and Okabe-Ito does not solve it.** The
canonical first two, orange and sky blue, separate by relative luminance 0.011
(`#E69F00` vs `#56B4E9`) — invisible once desaturated, and the single worst pair
in the set. When the figure must survive a photocopier, select by luminance
instead — relative luminance 0.264 (`#E69F00` vs `#0072B2`) — say so, and add a
second channel: dash pattern or marker shape. WCAG relative luminance, not the
CAM02-UCS ΔE the separation gates use, and not the OKLab lightness this guide
quotes elsewhere, because luminance is what a desaturation keeps.

**Status colors come from the same palette** —
`good #009E73`, `warning #E69F00`, `critical #D55E00` — always shipped with an
icon or label. An independent status set lands in near-misses rather than
matches, and a reader cannot tell whether two nearly-identical reds mean two
things or one. Status is a role, not a reservation: a hue can be a series color
or a status color in a given figure, never both.

**Sequential is `cmap="viridis"` as shipped.** A filled cell is read against its
neighbours and the colorbar, never against the page, so its light end carries no
contrast obligation and windowing it only throws range away. The one exception:
*discrete tiers drawn as standalone lines or marks* do stand alone against the
page, and full-range viridis ends at `#fde725`, 1.26:1, invisible as a hairline
— sample `t ∈ [0.05, 0.70]`, evenly.

**A colormap's kind is measured, not taken on the name.** `check_figure.py`
samples the map, reads its OKLab lightness, and classifies it sequential,
diverging, cyclic, qualitative, or `misc`; `misc` fails. `jet`, `rainbow`, `hsv`
and `gist_ncar` are `misc`, because a reader cannot put two of their values in
order. Phase, angle and heading are cyclic and take `twilight`: they close the
loop, and a sequential ramp on them draws a seam where the data is continuous.

**The key follows the kind.** A colorbar is a ruler, so the three continuous
kinds get one and categories get a legend instead. A bar beside categories is a
scale along nothing. A value outside the measured range ("did not converge", "no
data") is a separate class and not a small value: draw it in an explicit neutral
and key it *off* the bar, never as `cmap(0)`. The bar is the range that was
measured, and putting a non-value at the bottom of it claims a quantity nobody
measured.

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

**A figure placed at a fraction of the content width must say so**, or it is
measured as though it were full width and certified at a type size it does not
ship at:

```python
audit(fig, placed_frac=0.48)     # \includegraphics[width=0.48\textwidth]
```

The kwarg mirrors the call site on purpose — you never know your scale, but you
always know what you wrote in the document.

**Skip the measuring when the venue is a known one.** `audit(fig,
venue="neurips")` measures against that class file's `\textwidth`;
`python check_figure.py --venues` lists what it knows. Verify against
`\the\textwidth` in your own document before trusting one for anything that
matters — a `geometry` call in the preamble silently overrides all of it.

7.5pt is stricter than every journal that publishes a number (Nature 5pt,
Science 5–7pt for labels, PNAS 6–8pt with nothing under 2mm printed). Those are
the sizes at which a string is still *possible* to read; 7.5 is where it is
comfortable, and it is cheap to hold because the fix is nearly always cutting
words.

**Strokes have a floor too, and it is 1pt on the page.** SIAM states it in its
instructions for authors: lines thinner than one point break up or disappear in
print. Same arithmetic as the type floor — a 0.8pt stroke in a 9-inch figure
placed at 5.5 inches prints at 0.49pt — so `check_line_weight` runs it through
the same `page_scale`. Gridlines are held to a lower floor than data: a
gridline that drops out costs the reader a reference, a curve that drops out
costs them the finding.

**Embed fonts as Type 42.** matplotlib defaults `pdf.fonttype` to 3. IEEE PDF
eXpress does not accept Type 3 and refuses the upload; ACM and Elsevier check
embedding in production, so there it surfaces after acceptance instead.
`figure.mplstyle` sets it; nothing else warns you, because the figure renders
identically and the paper bounces at the latest possible moment.

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

`references/choosing-a-form.md` — which form the data wants, before any of the
styling rules apply. Built on Cleveland & McGill's ordering of the elementary
perceptual tasks, with the statistical results behind the rules that matter most
for teaching material: what a box plot hides at small n, why a cut baseline
misstates every ratio, why two bars are the wrong form for paired data, and why
overlapping confidence intervals are not a significance test.

`references/style-guide.md` — the full guide: the measurements behind every
threshold, the named failures each rule prevents, the palette tables with
contrast ratios, and the notes on rules that were changed or deleted and why.
Read it when deviating from a constraint, when a validator fails in a way you
want to argue with, or when porting the checks to a non-matplotlib stack.
