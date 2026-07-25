# figure-gate

Mechanical gates for figures that go into documents — papers, slides, theses,
reports. Two validators and a matplotlib style sheet, plus written guides, and
an [Agent Skill](https://code.claude.com/docs/en/skills) wrapper so Claude Code
applies the same method.

The premise: a figure can be correct, legible and colorblind-safe and still be
bad, but it can't be good while failing any of those. Those three are
checkable, so check them instead of squinting.

```bash
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
python check_figure.py              # self-test on a deliberately broken figure
```

![Example figure](examples/demo.png)

*(`python examples/demo.py` — the whole method in 40 lines. `python
examples/gallery.py` is the harder half: a shared-axis grid, a filled field
with a colorbar, an axis-free schematic, three statistical forms, a log-log
convergence plot with a slope triangle, and a dense attractor. Writing those
found five defects in the checks themselves.)*

## What it catches

**`check_palette.py`** — standard library only, takes hex strings, so it works
from any language or toolchain.

| Gate | Fails when |
|---|---|
| Lightness band | a hue is too light or too dark to read as a mark |
| Chroma floor | a "color" is effectively gray |
| CVD separation | two hues collapse under protanopia or deuteranopia |
| Normal-vision floor | two hues are hard to tell apart even in full color |
| Contrast vs surface | a hue is under 3:1 on the page *(advisory)* |
| Ordinal: monotone, even steps, light end | an ordered ramp reads as unordered |

**`check_figure.py`** — reads a built matplotlib figure's own artists.

| Gate | Fails when |
|---|---|
| Clipping | text runs past the canvas |
| Text collision | two labels overlap |
| Text readability | data ink crosses a label's glyphs, or text misses WCAG on the backdrop it actually got |
| Contrast stack | nothing is opaque, or transparency has too many levels |
| Mark ratio | one mark is so large it reads as ornament |
| Overplotting | a scatter is dense enough that the marks merge into a blob |
| Axis redundancy | panels on a shared scale repeat their axis furniture |
| Type size | a string lands under 7.5pt *on the printed page* |
| Line weight | a stroke lands under 1pt on the printed page (SIAM's floor) |
| Ink coverage | a panel is empty or saturated *(advisory)* |
| Series color | the hues actually drawn collapse under color blindness |
| Dual axis | a second y scale carries data of its own |
| Form | pie, 3D, or bars on a truncated baseline |
| Identity channel | series are told apart by hue alone *(advisory)* |
| Label attribution | a direct label sits nearer some other series than the one it names |
| Style sheet | `figure.mplstyle` is not the one in effect *(advisory)* |
| Contour dash | a signed contour spends dashing on its negative levels |
| Fonts | PDF/PS export is Type 3, or no named typeface is installed *(advisory)* |
| Alt text | the figure carries no description for a reader who cannot see it *(advisory)* |

**Series color is the one that ties the two scripts together.** They used to be
unable to speak: `check_palette.py` judged a list of hex strings someone
remembered to paste into a terminal, and `check_figure.py` never looked at color
at all. So a figure on matplotlib's default `tab10` cycle — whose orange and
green measure ΔE 1.4 under protanopia, one hue to that reader — passed the whole
composition suite clean. The gate now reads the hues off the figure's own
artists and puts them through the palette gates, working out from the marks
whether the figure needs adjacent separation (lines, bars) or all pairs
(scatter). `figure.mplstyle` sets the cycle to Okabe-Ito, so a figure built on
the sheet starts out right.

The type gate is the one people are usually surprised by. A figure authored at
14 inches and placed on a 750pt slide shrinks to 0.74×, so a 9pt label arrives
at 6.7pt — fine on your monitor, unreadable from the back of a lecture hall.
The check derives the scale per figure and measures what actually renders, so
sizes set through rcParams or by a helper are caught too. Placing at a fraction
of the content width? Say so — `audit(fig, placed_frac=0.48)` mirrors
`\includegraphics[width=0.48\textwidth]`, and without it a half-width figure is
certified at twice the type size it ships at. If your document is a venue the
table knows, skip the measuring: `audit(fig, venue="neurips")`, and
`python check_figure.py --venues` lists them.

## Where this sits

Prescriptive style sheets already exist and are good:
[SciencePlots](https://github.com/garrettj403/SciencePlots) and LovelyPlots for
journal looks, [tueplots](https://github.com/pnkraemer/tueplots) and mpl_sizes
for exact conference sizing. Accessibility tooling exists too:
[matplotalt](https://github.com/KaiNylund/matplotalt) generates alt text,
Chart4Blind converts a chart image into an accessible one, contrast reporters
check colors in isolation.

None of them verifies a built figure. That is the gap this fills — a style
sheet says what to do, and this says whether it happened, in a test, on the
figure's own artists. The two are complementary: use a style sheet, then gate
it.

## Install

Copy three files into your project. `check_palette.py` is standard library
only; `check_figure.py` needs matplotlib. scipy is optional and only a
speed-up.

```bash
git clone https://github.com/narenp12/figure-gate
cp figure-gate/skill/assets/figure.mplstyle       your-project/diagrams/
cp figure-gate/skill/scripts/check_palette.py     your-project/diagrams/
cp figure-gate/skill/scripts/check_figure.py      your-project/diagrams/
```

Then set two things and nothing else:

1. `font.serif` in `figure.mplstyle` → your document's body typeface.
2. `CONTENT_WIDTH_PT` at the top of `check_figure.py` → the usable width, in
   points, of the page the figure lands in. Leave it `None` if you author each
   figure at the width it's placed at, which makes the scale 1.0 and the whole
   calculation disappear — or skip it entirely and pass `audit(fig,
   venue="neurips")` for one of the twelve venues the table already knows.

### As a Claude Code skill

```bash
cp -r figure-gate/skill ~/.claude/skills/research-figures
```

Claude then applies the method when you ask for a figure for a paper or deck.
`skill/SKILL.md` is the workflow; `skill/references/style-guide.md` is the
reasoning behind every threshold.

## Use it

```python
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib import colormaps

plt.style.use(str(Path(__file__).parent / "figure.mplstyle"))

okabe = colormaps["okabe_ito"]          # matplotlib >= 3.11
fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
ax.plot(x, y, color=okabe(1), label="Baseline")   # widths come from the sheet

from check_figure import report
report(fig, "my-figure")
```

Resolve the style sheet relative to the *file*, not the working directory —
`plt.style.use("figure.mplstyle")` breaks the moment a test runner or build
script invokes it from elsewhere.

Wire it into your build so a broken figure fails CI:

```python
@pytest.mark.parametrize("name", sorted(FIGURES))
def test_figure_is_composed(name):
    ok, rows = audit(build(name))
    assert ok, "\n".join(f"{k}: {d}" for k, s, d in rows if not s)
```

## What it doesn't do

It won't tell you the figure is worth making. Every check here is an
*elimination* gate — each forbids one enumerated failure, and none of them ever
looks at the figure as a whole. A figure that passes has been judged not-bad in
exactly the ways someone thought to write down, which is not the same as good.
Render a PNG and look at it. The checker can't see that an arrow points at the
wrong thing, that reading order runs backwards, or that a label is true of the
concept and false of the curve beside it.

It also isn't for interactive web charts. Dashboards have different constraints
(hover, responsive reflow, dark mode) and most of the rules here don't transfer.

## Design notes

**Use what matplotlib ships.** viridis for sequential, `RdBu` for diverging,
`okabe_ito` for categorical, style sheets for defaults, `constrained_layout` for
layout. Earlier versions of this hand-rolled all four and every one was worse.
`RdBu`'s poles clear every gate in `check_palette.py` unmodified; a windowed
custom ramp threw away 35% of viridis for no benefit.

**WARN is not FAIL.** A sub-3:1 hue is legal if it carries a direct label; a
heatmap panel legitimately measures 0.98 ink coverage. Failing those would train
everyone to ignore the row, and a gate people learn to skip is worse than no
gate.

**Gates get tested for their ability to fail.** `tests/` asserts that each check
catches a figure with exactly that one defect, and that the style sheet's colors
actually apply. That last one exists because `#` starts a comment in matplotlib's
style format, so `grid.color: #e1e0d9` silently parses as empty and matplotlib
keeps its defaults — with every other test still green.

The full reasoning, including the measurements behind each threshold and the
rules that were tried and reverted, is in
[`skill/references/style-guide.md`](skill/references/style-guide.md).

Which *form* the data wants — the decision the styling rules cannot rescue — is
in [`skill/references/choosing-a-form.md`](skill/references/choosing-a-form.md).
It is built on Cleveland & McGill's ordering of the elementary perceptual tasks,
and only its mechanical subset is gated: a script can rule out a pie or a cut
bar baseline, but it cannot tell you a box plot is hiding an n of 8.

## Requirements

- `check_palette.py` — Python 3.8+, standard library only. Tested on 3.8–3.13.
- `check_figure.py` — Python 3.9+, matplotlib 3.8+.
- `colormaps["okabe_ito"]` needs matplotlib 3.11+. On older versions the
  palette is eight hex strings; they're listed in the style guide.

## Contributing

New gates are welcome, and the bar is the one the project holds itself to: a
gate ships with a test proving it fails on a figure with that defect, and a note
naming the real failure that motivated it. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
