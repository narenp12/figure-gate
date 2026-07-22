# Figure style guide

Portable method for figures that look authored: diagrams for slides, papers, reports.

This is the reasoning behind `SKILL.md` — the measurements, and the failure each rule
was written to prevent. Read it when deviating from a constraint, when a validator fails
in a way you want to argue with, or when porting the checks off matplotlib.

Ships with one style sheet and two validators:

| File | In the skill | Needs | What it is |
|---|---|---|---|
| `figure.mplstyle` | `assets/` | matplotlib | visual defaults as a style sheet |
| `check_palette.py` | `scripts/` | Python 3.8+, stdlib only | color gates, any toolchain |
| `check_figure.py` | `scripts/` | Python 3.8+, matplotlib | composition + type-size gates |

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
2. **Build** on `figure.mplstyle`.
3. **Compose, run `check_figure.py`, render a PNG, look at it.**
4. **Validate palette with `check_palette.py`.** Do not eyeball color.
5. **Render the finished document and look at *that*.**

### Composition rules (what the checker cannot tell you)

- One thing opaque; ≤3 alpha levels. Context gets the alpha, data does not.
- Marks within ~4× area of each other. Emphasis = shape or label, not 5× the area.
- Context surfaces get structure (bands, isolines), not just a neutral fill.
- Shared scale → shared axis furniture.
- Encode only what exists. A path through unordered data draws a sequence that is not
  there.
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
| Context backdrop | achromatic ramp, below |

### Categorical: Okabe-Ito

Established colorblind-safe categorical, published order. Adopting it as-is beats a
private set: it carries a decade of use and readers who know it recognize it.

| Slot | Hue | Hex | Contrast `#fcfcfb` | Role |
|---|---|---|---|---|
| 1 | black | `#000000` | 20.46 | ink token by convention |
| 2 | orange | `#E69F00` | 2.19 † | series |
| 3 | sky blue | `#56B4E9` | 2.25 † | series |
| 4 | bluish green | `#009E73` | 3.33 | series |
| 5 | yellow | `#F0E442` | 1.29 ‡ | fills, not hairlines |
| 6 | blue | `#0072B2` | 5.05 | series |
| 7 | vermillion | `#D55E00` | 3.77 | series |
| 8 | reddish purple | `#CC79A7` | 2.98 † | series |

† below 3:1 — must carry a visible direct label. ‡ below lightness band.

Two slots held out: yellow at 1.29:1 genuinely vanishes as a hairline (fills only). Black
is a preference (keeps "ink" unambiguous), not a measurement — take it as a series color
if you want.

The remaining six, in canonical order: `#E69F00 #56B4E9 #009E73 #0072B2 #D55E00 #CC79A7`

Adjacent CVD ΔE 16.6, adjacent normal-vision ΔE 16.4, first-four all-pairs ΔE 11.5/18.4.

**Take slots in order.** One → orange. Three → orange, sky blue, bluish green. Never
cherry-pick by meaning. Two limits: first four clear all-pairs; there is no seventh hue.

**Grayscale:** Okabe-Ito does not solve it. Orange+sky blue (canonical first two) are
ΔL 0.011, invisible when desaturated. Take orange+blue (ΔL 0.264) and add a second
channel when it must survive a photocopier.

### Sequential: viridis, as shipped

Perceptually uniform, monotone in lightness, colorblind-safe, in matplotlib.

```python
ax.pcolormesh(X, Y, Z, cmap="viridis")    # continuous — as shipped
```

**Window only for discrete tiers drawn as standalone lines/marks.** Full-range viridis
ends at `#fde725`, 1.23:1, invisible as a hairline. Sample `t ∈ [0.05, 0.70]` via
`ordinal()` from the appendix or `generate_diagrams.py`. Two things to get right: sample
evenly (ΔL ratio < 2×), and narrow to `t ∈ [0.00, 0.38]` when the figure also carries
status green (viridis passes through green near `t=0.7`, ΔE 10.7 from `#009E73`).

### Diverging: `RdBu`, as shipped

ColorBrewer, colorblind-safe, in matplotlib. Poles `#b1182b` / `#2065ab` clear every
gate. Midpoint is `#f6f7f7`. Never a hue at the midpoint; never two cool poles.

### Ink, status, backdrop

| Token | Hex | Defined in |
|---|---|---|
| Ink primary / secondary / muted | `#000000` / `#52514e` / `#898781` | `figure.mplstyle` |
| Grid / axis / surface | `#e1e0d9` / `#c3c2b7` / `#fcfcfb` | `figure.mplstyle` |

Status, drawn from the palette, always with icon or label:

```
good #009E73    warning #E69F00    critical #D55E00
```

Status and series are mutually exclusive roles for a hue within one figure.

Neutral backdrop: `#ffffff → #e6e5de → #c3c2b7 → #95938b`.

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
tritan reported but not gated (~0.01%).

### Text on fills

4.5:1, or 3:1 at ≥14pt bold. `from check_palette import contrast; contrast("#471365", "#ffffff")`.

### Standing rules

- Text wears ink, never the series color.
- Status colors are status only.
- Color follows the entity, not its rank.
- Sequential is monotone in lightness, evenly stepped. Never jet.

---

## Legibility budget

Set `CONTENT_WIDTH_PT` once in `check_figure.py`. The script derives the scale per figure
and fails any string under 7.5pt on page. Per-figure is the point: a 14in figure on a
750pt slide shrinks to 0.74×, a 8.6in one is 1.21×, and the same 10pt label is fine in
one and illegible in the other.

If text does not fit, cut it: "Acquisition function ranks the candidate molecules" →
"Rank every candidate."

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
MAX_SERIES, MAX_SERIES_ALL_PAIRS = 6, 4

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
    return [to_hex(vir(lo + (hi - lo) * i / (n - 1))) for i in range(n)]
```

Ink tokens live in `figure.mplstyle`, not here.
