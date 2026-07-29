# Figure style guide

Portable method for figures that look authored: diagrams for slides, papers, reports.

This is the reasoning behind `SKILL.md` — the measurements, and the failure each rule
was written to prevent. Read it when deviating from a constraint, when a validator fails
in a way you want to argue with, or when porting the checks off matplotlib.

Everything here is downstream of the form being right in the first place, which is
`choosing-a-form.md` — the perceptual and statistical argument for what to draw, before
any question of how it looks.

Ships with one style sheet and two validators:

| File | In the skill | Needs | What it is |
|---|---|---|---|
| `figure.mplstyle` | `assets/` | matplotlib | visual defaults as a style sheet |
| `check_palette.py` | `scripts/` | Python 3.8+, stdlib only | color gates, any toolchain |
| `check_figure.py` | `scripts/` | Python 3.9+, matplotlib 3.8+ | composition + type-size gates |

Copy all three into the project (conventionally `diagrams/`), where they sit beside each
other as the guide assumes. Only `check_figure.py` is coupled to matplotlib; the
composition rules it enforces are library-agnostic, and each reads geometry any mature
plotting library reports.

Everything matplotlib ships is used as-shipped — viridis, `RdBu`, style sheets,
`constrained_layout`. What remains is the part matplotlib has no opinion about: which
palette, whether the figure is composed, and whether the type clears the page.

Every rule here was earned by a specific failure. Nothing is taste-by-assertion.

---

## Fast path

```
plt.style.use("figure.mplstyle")

STYLE:       journal figure, no shadows/cards/chips
             dashing = unobserved/projected/threshold only
             layout = constrained_layout

COLOR:       categorical  Okabe-Ito, first N in order
             sequential   cmap="viridis"   (window t∈[0.05,0.70] for discrete tiers)
             diverging    cmap="RdBu"      (RdBu_r when low=blue)
             status       #009E73 / #E69F00 / #D55E00, always with icon

SIZE:        author at placed width → scale = 1.0, points are points
             otherwise check_figure.py derives scale from CONTENT_WIDTH_PT
             type floor 7.5pt on page; cut words before shrinking

VALIDATE:    check_palette.py "<hexes>"  &&  check_figure.py  &&  open PNG
```

---

## Procedure

1. **Ground content.** Use the document's exact nouns. Compute real numbers. Every label
   checked against the drawn data, not the idea it names.
2. **Choose the form** — `choosing-a-form.md`. Nothing downstream fixes a wrong one.
3. **Build** on `figure.mplstyle`.
4. **Compose, run `check_figure.py`, render a PNG, look at it.**
5. **Validate palette with `check_palette.py`.** Do not eyeball color.
6. **Render the finished document and look at *that*.**

### Composition rules (what the checker cannot tell you)

- One thing opaque; ≤3 alpha levels. Context gets the alpha, data does not.
- Marks within ~4× area of each other. Emphasis = shape or label, not 5× the area.
- Context surfaces get structure (bands, isolines), not just a neutral fill.
- Shared scale → shared axis furniture.
- Encode only what exists. A path through unordered data draws a sequence that is not
  there.
- A path with real order (a trajectory) must read as directed — downsample or smooth
  it, add a single arrowhead pointing forward, or model it so it stays visually
  contained (a noisy SGD walk near a minimum is an Ornstein–Uhlenbeck process, whose
  stationary distribution is the Gaussian being drawn). A self-intersecting scribble
  drowns out every other mark.
- Marks over a textured or variable-value context surface need a 1–3px white stroke
  behind them (`pe.withStroke(foreground="white")` in matplotlib) — a knockout halo
  that guarantees separation regardless of the local background value. A line that
  vanishes where it crosses a contour is not a line; a marker that disappears into a
  filled band is not a marker.
- Ordinal emphasis is a lightness ramp, not a transparency stack.

### Then still look at it

The checker sees geometry, not meaning: it cannot tell you an arrow points at the wrong
thing or that the reading order runs backwards.

---

## Color

| Encoding | What |
|---|---|
| Categorical | Okabe-Ito |
| Sequential / ordinal | `cmap="viridis"` |
| Diverging | `cmap="RdBu"` or `RdBu_r` |
| Cyclic | `cmap="twilight"` |
| Context backdrop | achromatic ramp, below |

### Categorical: Okabe-Ito

Established colorblind-safe categorical, published order. Adopting it as-is beats a
private set: it carries a decade of use and readers who know it recognize it.

| Slot | Hue | Hex | Contrast `#ffffff` | Role |
|---|---|---|---|---|
| 1 | black | `#000000`{ .sw style="--c:#000000" } | 21.00 | ink token by convention |
| 2 | orange | `#E69F00`{ .sw style="--c:#E69F00" } | 2.25 † | series |
| 3 | sky blue | `#56B4E9`{ .sw style="--c:#56B4E9" } | 2.31 † | series |
| 4 | bluish green | `#009E73`{ .sw style="--c:#009E73" } | 3.42 | series |
| 5 | yellow | `#F0E442`{ .sw style="--c:#F0E442" } | 1.32 ‡ | fills, not hairlines |
| 6 | blue | `#0072B2`{ .sw style="--c:#0072B2" } | 5.19 | series |
| 7 | vermillion | `#D55E00`{ .sw style="--c:#D55E00" } | 3.87 | series |
| 8 | reddish purple | `#CC79A7`{ .sw style="--c:#CC79A7" } | 3.06 | series |

† below 3:1 — must carry a visible direct label. ‡ below lightness band.

The hue is the one cell here a reader cannot recompute. "Vermillion" is the Hue
column attempting it in words; the swatch is the same claim in color. It renders
on the site only. In the file it is an attribute list on the code span, restating
the hex that span already holds, and a second copy of a color is how the ink
table below came to credit the sheet with a token the sheet had stopped shipping.
So both ends are held: `tests/test_docs_match_code.py` reads the source and
asserts the pair agrees, `tests/test_docs_render.py` renders the page and asserts
the browser paints it.

**A legend entry is not a direct label.** The rule was ambiguous on this and
`examples/demo.py` read it the other way for a while. It is settled the strict
way, because the obligation follows from the measurement: a sub-3:1 mark is
faint against the page, and a legend leaves the reader matching a small faint
swatch to a small faint curve — the exact step a direct label exists to remove.
Text at the mark, in ink, with the mark beside it carrying the identity.

Ratios are against white, because that is what `figure.mplstyle` renders and
what the page under it is. They were previously quoted against `#fcfcfb`, a
surface no figure in this project ever had; the numbers were all slightly wrong
and reddish purple was listed as needing a direct label when on white it clears
3:1 at 3.06. `tests/test_docs_match_code.py` now reads this table and checks
every number against `contrast()`, so it cannot drift again. On a genuinely
tinted page, pass `--surface`.

Two slots held out: yellow at 1.32:1 genuinely vanishes as a hairline (fills only). Black
is a preference (keeps "ink" unambiguous), not a measurement — take it as a series color
if you want.

The remaining six, in canonical order: `#E69F00 #56B4E9 #009E73 #0072B2 #D55E00 #CC79A7`

Adjacent CVD ΔE 16.6, adjacent normal-vision ΔE 16.4, first-five all-pairs ΔE 11.2/15.6.

**Take slots in order.** One → orange. Three → orange, sky blue, bluish green. Never
cherry-pick by meaning. Two limits: the first five slots clear all-pairs; there is no
seventh hue.

The all-pairs limit was written as four for a long time and the measurement does not
support it: five slots come to ΔE 11.2 under deuteranopia against a target of 8, and
six is the first count that fails, at 7.9 (`#009E73` vs `#CC79A7`). Four was a number
nobody had run. `tests/test_docs_match_code.py` now derives it by asking
`check_palette.check(..., all_pairs=True)` for the largest count that passes, so the
constant below and this sentence cannot drift from the validator again.

**Grayscale:** Okabe-Ito does not solve it. Orange and sky blue, the canonical first
two, separate by relative luminance 0.011 (`#E69F00` vs `#56B4E9`) and are invisible
once desaturated. Take orange and blue instead — relative luminance 0.264 (`#E69F00`
vs `#0072B2`) — and add a second channel when it must survive a photocopier.

The unit is WCAG relative luminance here, not the OKLab ΔE ×100 the separation gates
use, because that is the channel a desaturation keeps. In OKLab lightness the same two
pairs are 0.018 and 0.221: the ordering is the same, the numbers are not, and a reader
who recomputes one convention against the other concludes the guide has drifted.

### Sequential: viridis, as shipped

Perceptually uniform, monotone in lightness, colorblind-safe, in matplotlib.

```python
ax.pcolormesh(X, Y, Z, cmap="viridis")    # continuous — as shipped
```

**Window only for discrete tiers drawn as standalone lines/marks.** Full-range viridis
ends at `#fde725`{ .sw style="--c:#fde725" }, 1.26:1, invisible as a hairline. Sample `t ∈ [0.05, 0.70]` via
`ordinal()` from the appendix. Two things to get right: sample
evenly (ΔL ratio < 2×), and narrow to `t ∈ [0.00, 0.38]` when the figure also carries
status green (viridis passes through green near `t=0.7`, ΔE 10.7 from `#009E73`).

**On marks, hand the ramp to a colormap, not a list of colors.** An ordinal ramp is
built to violate the categorical separation floor — its steps are meant to be close, and
there can be many. `check_figure.py` reads a scatter drawn `scatter(c=[rgba, rgba, …])` as
that many independent categorical identities and fails it against the ΔE floor, because a
pre-evaluated RGBA list carries no signal that the steps are ordered. Draw it
`scatter(c=values, cmap=ListedColormap(ramp))` (or with a `Normalize`) instead: the gate
reads that as the value encoding it is and exempts it, and the intent is now in the code
rather than lost in a flat bag of hues. A ramp drawn as standalone *lines* has no colormap
to hand it to — keep those tiers few and evenly stepped, and validate with
`--ordinal`, since the composition gate measures them against the categorical floor.

### Diverging: `RdBu`, as shipped

ColorBrewer, colorblind-safe, in matplotlib. Poles `#b1182b`{ .sw style="--c:#b1182b" } /
`#2065ab`{ .sw style="--c:#2065ab" } clear every gate. Midpoint is `#f6f7f7`{ .sw style="--c:#f6f7f7" }.
Never a hue at the midpoint; never two cool poles.

### Cyclic: `twilight`, as shipped

An angle has no ends. Phase, heading, direction, time of day: the last value is
adjacent to the first, and a ramp that starts dark and ends light draws a seam
straight across the figure at the one place the data is continuous. `twilight`
and `twilight_shifted` close the loop and are monotone in lightness over each
half, so a reader can still order two values within a half turn.

```python
ax.imshow(np.angle(w), cmap="twilight", vmin=-np.pi, vmax=np.pi)
```

Tick the bar at both ends and the centre. The two ends are the same colour
because they are the same angle, and a bar that does not show that reads as a
scale someone got wrong.

### Which kind, and the key it takes

Four kinds, four questions. The kind is a property of the data, not a
preference, and picking the wrong one is not a matter of taste: it claims an
ordering the values do not have, or hides one they do.

| Kind | The question it answers | matplotlib | Key |
|---|---|---|---|
| Sequential | can a reader put two values in order? | `viridis` | colorbar |
| Diverging | is there a middle the values are signed around? | `RdBu` | colorbar, centred on that middle |
| Cyclic | does the last value touch the first? | `twilight` | colorbar, ticked at both ends and the centre |
| Qualitative | are the levels identities, with no order to read? | `okabe_ito` | legend |

**A colorbar is a ruler, so it needs something to be a ruler along.** The three
continuous kinds have one. Categories do not, and a bar drawn beside them is a
scale along nothing: name them in a legend instead. The same rule decides where
a value that falls outside the measured range goes. "Did not converge", "no
data", "censored" are separate classes, not small values, so they are drawn in
an explicit neutral and keyed *off* the bar, never as `cmap(0)`. The bar is the
range that was measured, and putting a non-value at the bottom of it claims a
quantity nobody measured.

`check_figure.py` measures the kind rather than trusting a name, because
matplotlib groups its colormaps by kind in prose documentation only: there is no
API and no metadata on a `Colormap` object. It samples `CMAP_SAMPLES = 256`
levels, converts to OKLab, and reads the lightness channel. Anything under
`CMAP_QUALITATIVE_N = 40` levels is qualitative and is sent to the categorical
gates instead. A map whose lightness span is under `CMAP_SPAN_MIN = 0.02` is
isoluminant and carries no order at all. Otherwise the measure is **back-travel**,
the fraction of a segment's lightness span spent moving against its own
direction: under `CMAP_BACKTRAVEL_MAX = 0.02` over the whole map is sequential,
under it over both halves is diverging, or cyclic when the two ends are within
`CMAP_WRAP_DE_MAX = 3.0` of each other in OKLab ΔE ×100.

Everything else is `misc`, and `misc` is the only outcome that fails. `jet`,
`rainbow`, `hsv` and `gist_ncar` land there. A reader cannot order two values in
any of them, which is the whole job.

The thresholds are empirical, measured across matplotlib's registry against
`cmasher.get_cmap_type()` as an oracle. The margins, the three adjudicated
disagreements, and the one known false positive are recorded in the design note
that ships with the repository, at
[`specs/2026-07-28-colormap-kind-gate-design.md`](https://github.com/narenp12/figure-gate/blob/main/specs/2026-07-28-colormap-kind-gate-design.md).
The theory is Kovesi; see the references at the end of this document.

Kind is not quality. `turbo` passes as diverging because its lightness profile
genuinely is diverging-shaped; its problem is hue banding, which a
lightness-only measure cannot see. The row is named "Colormap kind" for that
reason.

### Ink, status, backdrop

| Token | Hex | Defined in |
|---|---|---|
| Ink primary / secondary / muted | `#000000`{ .sw style="--c:#000000" } / `#52514e`{ .sw style="--c:#52514e" } / `#777570`{ .sw style="--c:#777570" } | `figure.mplstyle` |
| Grid / axis / surface | `#e1e0d9`{ .sw style="--c:#e1e0d9" } / `#c3c2b7`{ .sw style="--c:#c3c2b7" } / `#ffffff`{ .sw style="--c:#ffffff" } | `figure.mplstyle` |

Muted ink was `#898781` until `check_text_readability` was written and failed the
sheet's own tick labels on every figure in the repo: it measures 3.59:1 on white,
under the 4.5:1 a glyph stem needs. `#777570` is 4.6:1 and still sits below the
7.94:1 axis label, so the hierarchy survives the correction. The old spelling
stays in `check_figure.py`'s `INK_TOKENS` so that figures built on the old sheet
are still read as furniture; it is not a token to reach for. `tests/test_docs_match_code.py`
now resolves every hex in this table against the sheet, so the table cannot quote
a token the sheet does not ship.

Status, drawn from the palette, always with icon or label:

```
good #009E73    warning #E69F00    critical #D55E00
```

Status and series are mutually exclusive roles for a hue within one figure.

Neutral backdrop: `#ffffff`{ .sw style="--c:#ffffff" } → `#e6e5de`{ .sw style="--c:#e6e5de" }
→ `#c3c2b7`{ .sw style="--c:#c3c2b7" } → `#95938b`{ .sw style="--c:#95938b" }.

### Categorical or ordinal?

- **Categorical** = independent identities. Different models, different groups.
- **Ordinal** = ordered steps. **A numbered cycle is ordinal** → viridis, not four hues.

### Validator

```bash
python check_palette.py "#E69F00,#56B4E9"                    # lines, bars
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all # scatter
python check_palette.py "#471365,#2c718e,#44bf70" --ordinal   # ramps
```

Gates: lightness band, chroma floor, CVD separation ≥ 8, normal-vision ≥ 15, contrast ≥
3:1. Separations are OKLab ΔE ×100. CVD gating on protanopia/deuteranopia (~8% of males);
tritan reported but not gated (~0.01%). Surface defaults to white; `--surface` for a
tinted page.

### Text on fills

4.5:1, or 3:1 at ≥14pt bold. `from check_palette import contrast; contrast("#471365", "#ffffff")`.

`check_text_readability` enforces this against the backdrop each string *actually* got,
measured off the rendered pixels — which is the only way to know, because the backdrop is
whatever happened to be drawn under the label and no artist knows that about itself.

### Direct labels: the alignment is the decision

A label is a box, not a point. On a curve with any slope, `ha="center"` is the one
alignment that puts both ends of the box back down on the line: it clears the curve at
the anchor and nowhere else, because across the label's own width the curve has moved
further than the offset holding the text up. This shipped in `examples/demo.py` for
months. Every check passed; all three labels sat on their own curves and their casing
punched visible white gaps through the data.

- Align toward the side the curve is **leaving**. Descending curve: above it, clear
  ground runs right (`ha="left"`); below it, clear ground runs left (`ha="right"`).
- Anchor on the extreme of the data across the label's own span, not its value at one
  point. Sampled noise routinely spikes further than any sane offset.
- Casing (`pe.withStroke`) rescues a 0.7pt gridline behind a label. It does not rescue a
  1.6pt curve — there it only hides the collision by deleting the data underneath, which
  is why the gate measures the backdrop rather than the finished render.
- When a panel has no clear ground anywhere — a filled field crossed by isolines is the
  usual case — take the labels off the field entirely. `examples/gallery.py` is the one
  figure in this repo that uses a legend, and that is the reason.

### Standing rules

- Text wears ink, never the series color.
- Status colors are status only.
- Color follows the entity, not its rank.
- Sequential is monotone in lightness, evenly stepped. Never jet.
- Dashing means unobserved, projected, or threshold — nothing else. Pass
  `linestyles="solid"` to `contour` on signed data, because matplotlib dashes
  negative levels by default and that reads here as a hedge the contour is not
  making.

---

## Legibility budget

**Decide on-page placement before authoring.** "8-inch figure" means nothing until you
know what width the document gives it — a full page, a text block, two columns? Author it
at that width, and the scale is 1.0, the type gate is exact, and there is nothing to
compute.

A figure placed below roughly 35% of the content width (two-column width for a landscape
figure) puts every label at or below 6pt on the page, regardless of what the script says.
`check_figure.py` warns when `placed_frac < 0.35`, but the right thing is to change the
placement or the figure, not to shrink the type further.

Set `CONTENT_WIDTH_PT` once in `check_figure.py`, or pass `venue=` for one of the twelve
the table already knows (`python check_figure.py --venues`). The script derives the scale
per figure and fails any string under 7.5pt on page. Per-figure is the point: a 14in
figure on a 750pt slide shrinks to 0.74×, a 8.6in one is 1.21×, and the same 10pt label
is fine in one and illegible in the other.

**7.5pt is stricter than any journal that publishes a number** — Nature 5pt, Science 5–7pt
for labels and 6–8pt for axes, PNAS 6–8pt with nothing under 2mm printed. Those are the
sizes at which a string is still *possible* to read. 7.5 is where it is comfortable, and
it costs nothing to hold, because the fix is nearly always cutting words.

If text does not fit, cut it: "Acquisition function ranks the candidate molecules" →
"Rank every candidate."

**Strokes have the same problem and the same arithmetic.** SIAM's instructions for
authors: lines one point or thicker, because thinner lines break up or disappear in print.
A 0.8pt stroke in a 9in figure placed at 5.5in prints at 0.49pt, so `check_line_weight`
measures on the page through the same `page_scale`. Gridlines are held to a lower floor
than data deliberately — a gridline that drops out costs a reference, a curve that drops
out costs the finding.

**Embed fonts as Type 42.** matplotlib defaults to Type 3. IEEE PDF eXpress rejects the
upload; ACM and Elsevier reject the submission. The figure renders identically either way,
so nothing tells you until the latest and most expensive possible moment.
`figure.mplstyle` sets `pdf.fonttype: 42` and `ps.fonttype: 42`.

**Describe the figure.** Across 100,000 public notebooks, 99.81% of generated images
shipped with no alt text, nearly all of them matplotlib. `describe(fig, ...)` then
`savefig(path, metadata=alt_metadata(fig, path))` — the path a second time, so the call
can pick the key that format has. Say what the reader would have taken from
looking — the numbers and the direction — not what the figure is made of. "A line chart
with three lines" describes the file.

---

## Prose

Match the surrounding voice. Caption states the mechanism once. Every spatial claim
checked against the render. No invented precision. No em-dashes in rendered strings.

---

## Discipline

- **Declare the read before you draw.** One sentence: what, for whom, the job.
- **Prefer checks over adjectives.** A check you run beats taste you have to feel.
- **Every gate has a blind spot.** A figure that passes is not good — it is not-bad in
  exactly the ways enumerated. When it still looks wrong, write the gate.

### Review checklist — only things no script can check

- [ ] Uses the surrounding text's exact vocabulary
- [ ] Every label checked against the drawn data, not the idea
- [ ] Nothing drawn that the data does not support
- [ ] Ordinal vs categorical decided correctly
- [ ] Placement decided before authoring; figure authored at its placed width
- [ ] Named algorithm shown with its defining objects (paper/repo), not remembered
- [ ] Document compiled; caption states mechanism once; no em-dashes

---

## Ship

Build, run tests, compile document. Smoke-test each figure so a broken one fails the build
instead of shipping blank.

---

## Appendix: palette constants

```python
from matplotlib import colormaps
from matplotlib.colors import to_hex

_OKABE = colormaps["okabe_ito"]
# 0 black 1 #E69F00 2 #56B4E9 3 #009E73 4 #F0E442 5 #0072B2 6 #D55E00 7 #CC79A7

SERIES = [_OKABE(i) for i in (1, 2, 3, 5, 6, 7)]
MAX_SERIES, MAX_SERIES_ALL_PAIRS = 6, 5

STATUS = {"good": _OKABE(3), "warning": _OKABE(1), "critical": _OKABE(6)}
NEUTRAL_BACKDROP = ["#ffffff", "#e6e5de", "#c3c2b7", "#95938b"]

VIRIDIS_WINDOW = (0.05, 0.70)
VIRIDIS_WINDOW_COOL = (0.00, 0.38)


def series(n):
    if n > MAX_SERIES:
        raise ValueError(f"{n} series requested but theme has {MAX_SERIES} slots")
    return [to_hex(c) for c in SERIES[:n]]


def ordinal(n, window=VIRIDIS_WINDOW):
    lo, hi = window
    vir = colormaps["viridis"]
    if n < 2:                      # one step has no gap to space; n=1 divided by zero
        return [to_hex(vir(lo))] * n
    return [to_hex(vir(lo + (hi - lo) * i / (n - 1))) for i in range(n)]
```

Ink tokens live in `figure.mplstyle`, not here.

---

## References

The colour rules above are not house preference. Each of the four colormap
kinds, and the reason `misc` fails, comes from this literature.

- Kovesi, P. (2015). Good Colour Maps: How to Design Them. arXiv:1509.03700. —
  uniform incremental change in perceptual lightness as the governing
  requirement, with separate stated criteria for linear, diverging, rainbow and
  cyclic maps. The back-travel measure is this criterion made mechanical.
- Crameri, F., Shephard, G. E. & Heron, P. J. (2020). The misuse of colour in
  science communication. *Nature Communications* 11, 5444.
  doi:10.1038/s41467-020-19160-7. — why rainbow-like and red-green maps are
  still prevalent, and what they cost a reader.
- Nuñez, J. R., Anderton, C. R. & Renslow, R. S. (2018). Optimizing colormaps
  with consideration for color vision deficiency to enable accurate
  interpretation of scientific data. *PLoS ONE* 13(7), e0199239. — the
  CVD-safe side of the same question, and the argument the Okabe-Ito section
  above rests on.
- Moreland, K. (2009). Diverging Color Maps for Scientific Visualization. In
  *Advances in Visual Computing* (ISVC 2009), 92-103.
  doi:10.1007/978-3-642-10520-3_9. — the midpoint rule: never a hue at the
  centre, and why a diverging map needs a meaningful zero to diverge around.
