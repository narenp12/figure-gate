# Colormap-kind gate, and the figures that need it

Date: 2026-07-28
Status: approved, not yet implemented

## The hole

`check_figure.py` has nineteen ways to be wrong about a figure and none of them
look at a colormap. Every gate reads artists that carry an identity — a line's
color, a bar's face, a scatter's marks. A figure whose entire content is one
colormapped image has no such artist, so it passes every check by having nothing
the checks know how to read.

A Mandelbrot set rendered in `jet` is currently a PASS.

This is not an oversight that went unnoticed. `_data_colors_by_axes` already
excludes colormapped artists, at `check_figure.py:1096`, with a comment saying
they answer to "the viridis rule instead." No such rule is implemented. This
spec implements it.

Two further gaps follow from the same root:

- `_data_colors_by_axes` iterates `ax.lines`, `ax.patches` and `ax.collections`.
  `AxesImage` lives in `ax.images` and is invisible to every color path.
- `check_palette.py` can judge an ordinal ramp, but only when an author hands it
  a list of hexes on the command line. Nothing extracts a ramp from a figure.

## What ships

| file | change |
| --- | --- |
| `skill/scripts/check_palette.py` | `cmap_kind()` classifier, stdlib only |
| `skill/scripts/check_figure.py` | new gate row 18, "Colormap kind" |
| `examples/gallery.py` | seventh figure, `gallery-encoding.png` |
| `tests/test_palette.py` | classifier unit tests, thresholds pinned |
| `tests/test_figure.py` | harvest and routing tests |
| `tests/test_example.py` | gallery count 6 -> 7 |
| `tests/test_docs_match_code.py` | roster 19 -> 20, two name maps |
| `README.md` | gate table row, and "row 11 of the 19" |
| `pyproject.toml` | one dev-only optional dependency |

### The roster ripple

Adding a gate is not a one-file change here, by design. `check_colormap` is a
content check, so it belongs beside `Contour dash` at position 18, which pushes
`Fonts` to 19 and `Alt text` to 20. That renumbering has to land in:

- the numbered list in the `check_figure.py` module docstring
- the gate table in `README.md`, and the sentence at `README.md:45` that reads
  "That is row 11 of the 19"
- `tests/test_docs_match_code.py`: the roster count at line 224, the name-to-
  function map at line 359, and the name-to-prose map at line 553

This is the repository's own discipline working. The comment at
`test_docs_match_code.py:525` records that the documentation once "listed
eighteen of the nineteen, omitting `Contour dash`" — the roster check exists
because a gate was silently lost from the prose. A new gate that does not
update all three structures will fail the suite, which is the intended outcome.

## Dependencies: one, and not at runtime

Runtime dependencies stay exactly as they are: `matplotlib>=3.8`, with `scipy`
optional. Two promises in the repository forbid more. `check_palette.py` opens
with "No dependencies beyond the standard library," and `pyproject.toml:44`
records that scipy is optional because "the README promises three files and no
install, and a hard scipy import broke that."

`colorspacious` would buy nothing. The reference implementation (see below) uses
CAM02-UCS; this repository hand-rolls OKLab in `linear_to_oklab`. Classification
takes the *sign* of a lightness difference, and the two spaces agree on sign.
Carrying a second definition of lightness beside OKLab dE x100 is the failure
this repository has already had once.

One new dependency, dev-only, as a test oracle:

```
cmasher>=1.9; python_version>='3.10'
```

cmasher 1.9.2 requires Python >=3.10 and pulls `colorspacious`, `matplotlib`,
`numpy`. The repository floor is 3.9, so the marker plus a skip keeps 3.9 green.
It is never imported by shipped code.

## Prior art

`cmasher.get_cmap_type()` is this classifier, already shipping. It samples the
colormap, converts to CAM02-UCS, differences the lightness channel, and decides:

1. fewer than 40 entries -> qualitative
2. lightness differences all near zero -> misc
3. `|sum(dL)| ~= sum(|dL|)` -> sequential
4. both halves monotone -> diverging, or cyclic when the wrap-around step is
   comparable to the interior steps
5. otherwise -> misc

The theory is Kovesi, *Good Colour Maps: How to Design Them* (arXiv:1509.03700):
uniform incremental change in perceptual lightness is the governing requirement,
with separate stated criteria for linear, diverging, rainbow and cyclic maps.

matplotlib groups its colormaps by kind in prose documentation only. There is no
API and no metadata on a `Colormap` object. The kind has to be measured.

## The classifier

`cmap_kind()` takes the structure above and none of its arithmetic. A direct
transcription of test 3 into OKLab misclassifies **viridis**, because a strict
sign test cannot tell a designed reversal from 8-bit quantization noise.

The working measure is **back-travel**: the sum of steps against a segment's
dominant direction, as a fraction of that segment's lightness span. Measured
over matplotlib's registry at 256 samples in OKLab:

| colormap | lo half | hi half | wrap/span | verdict |
| --- | --- | --- | --- | --- |
| viridis | 0.10% whole-map | | | sequential |
| cividis | 0.03% whole-map | | | sequential |
| plasma, magma, gray, Blues | 0.00% whole-map | | | sequential |
| twilight | 0.00% | 0.02% | 0.00% | cyclic |
| twilight_shifted | 0.05% | 0.02% | 0.34% | cyclic |
| RdBu | 0.00% | 0.00% | 2.09% | diverging |
| Spectral | 0.00% | 0.00% | 6.62% | diverging |
| coolwarm | 0.36% | 1.05% | 2.86% | diverging |
| PuOr | 0.52% | 0.00% | 26.7% | diverging |
| turbo | 0.38% | 0.58% | 17.8% | diverging (see Limits) |
| rainbow | 2.79% | 3.24% | 25.0% | misc |
| jet | 1.04% | 10.0% | 15.4% | misc |
| hsv | 27.9% | 53.4% | 0.15% | misc |
| brg | 25.2% | 25.8% | 87.6% | misc |
| nipy_spectral | 27.5% | 141% | 91.8% | misc |
| gist_ncar | 37.3% | 121% | 98.1% | misc |

Two thresholds, each with a measured margin:

- **Monotone: back-travel below 2% of span.** The binding pair is coolwarm's
  high half at 1.05% against rainbow's low half at 2.79% — 2.7x total, roughly
  1.9x of headroom on each side. This is the tightest constraint in the design
  and the number most likely to need revisiting.
- **Cyclic rather than diverging: end-to-end colour distance below OKLab
  dE x100 of 3.0.** Not a lightness difference. See below.

### The wrap is a colour distance, not a lightness difference

The first draft of this spec tested the wrap in lightness, at 1% of span. The
differential against cmasher rejected it: 13 of 148 colormaps disagreed, and 11
of those 13 were the same mistake — RdYlGn, `cmr.fusion`, `cmr.holly`,
`cmr.iceburn`, `cmr.pride`, `cmr.redshift`, `cmr.seaweed`, `cmr.viola`,
`cmr.watermelon`, `cmr.wildfire` and `managua`, every one classified cyclic by
us and diverging by cmasher.

The reason is structural. A symmetric diverging map has *equal lightness at both
ends by construction* — that is cmasher's own definition of the family. RdYlGn
ends red and ends green: same lightness, opposite colour. Lightness wrap cannot
tell the two families apart, because both families close the loop in lightness.
Only a cyclic map closes it in colour.

Measuring the ends with `check_palette.delta_e`, already in the file:

| cyclic | wrap dE | | diverging | wrap dE |
| --- | --- | --- | --- | --- |
| twilight | **0.00** | | cmr.fusion | **7.48** |
| cmr.infinity | 0.26 | | cmr.viola | 7.90 |
| twilight_shifted | 0.29 | | cmr.holly | 9.07 |
| hsv | 0.74 | | wildfire, redshift, iceburn | 14.5–19.7 |
| | | | RdBu, Spectral, managua, vanimo | 19.8–21.6 |
| | | | PuOr, RdYlGn, coolwarm, watermelon | 27.0–31.1 |

The gap runs from 0.74 to 7.48 — **10x**, the widest margin in the design.
Every threshold from dE 1.0 to 5.0 produces an identical differential result.
**3.0** is taken as near the geometric mean of the gap.

(hsv appears in the cyclic column because its ends genuinely do meet. It is
still classified misc, on back-travel, long before the wrap is consulted.)

Order of tests, mirroring cmasher:

```
N < 40                          -> qualitative
total span < 0.02 OKLab L       -> misc          (isoluminant)
whole-map back-travel < 2%      -> sequential
both halves back-travel < 2%    -> cyclic if wrap dE < 3.0, else diverging
otherwise                       -> misc
```

The isoluminant test is on the span, not on the individual steps: a map whose
lightness never moves more than 0.02 across its whole length carries no ordinal
information, and back-travel — a ratio with span in the denominator — is
meaningless for it. Guarding the span also keeps that division safe.

`misc` is the failure bucket. It is where `jet`, `hsv`, `rainbow` and the
`gist_*` maps land, and it is the only outcome that fails the gate.

## The gate row

`check_colormap(fig)` becomes row 18, directly after "Contour dash", renumbering
`Fonts` to 19 and `Alt text` to 20 as described above. It is a router, not a new
body of checking:

1. **Harvest.** Every artist in `ax.images` and `ax.collections` whose
   `get_array()` is not None. Take `get_cmap()` off each. Colorbar axes are
   skipped, as they already are in `check_ink`.

   Verified on matplotlib 3.11.1 — every colormapped call lands in one of those
   two containers and exposes both methods, so no wider sweep is needed:

   | call | artist | container |
   | --- | --- | --- |
   | `imshow` | AxesImage | `images` |
   | `pcolormesh` | QuadMesh | `collections` |
   | `contourf` / `contour(cmap=)` | QuadContourSet | `collections` |
   | `hexbin` / `tripcolor` | PolyCollection | `collections` |
   | `scatter(c=, cmap=)` | PathCollection | `collections` |
   | `quiver(C, cmap=)` | Quiver | `collections` |
   | `streamplot(color=, cmap=)` | LineCollection | `collections` |

   **The guard is `get_array() is not None`, never `get_cmap() is not None`.**
   Every `ScalarMappable` carries a default colormap whether or not anything was
   mapped through it: a plain `scatter(x, y, color="#0072b2")` returns `viridis`
   from `get_cmap()` and `None` from `get_array()`. Testing the colormap instead
   of the array would gate every unmapped scatter in the repository against a
   ramp it never used. This is the same discrimination `_data_colors_by_axes`
   already makes, in the opposite direction, at `check_figure.py:1096`.
2. **Classify.** Sample 256 colors, call `cmap_kind()`.
3. **Route to the check that kind already has.**
   - qualitative -> `check_palette.check(levels, all_pairs=True)`, the same
     colorblind-separation gate a categorical palette clears
   - sequential -> `check_palette.check(ramp, ordinal=True)`, monotone lightness
     and even steps
   - diverging, cyclic -> the ordinal check per half; end-to-end monotonicity is
     not the contract either one signs
   - misc -> FAIL, naming the colormap and its back-travel

FAIL rather than WARN. A `jet` colormap is a definite defect with a known
correct replacement, and the repository's own position — `test_figure.py:836` —
is that a warning nobody reads is worse than no row at all.

The import of `check_palette` follows the existing soft pattern at
`check_figure.py:1180`: if it is not importable beside this file, the row
reports that rather than raising.

## The gallery figure

One figure, three panels in a row, saved as `gallery-encoding.png`. Named for
what it demonstrates rather than the mathematics in it, following
`gallery-field` and `gallery-forms`.

| panel | object | kind | colormap |
| --- | --- | --- | --- |
| left | Mandelbrot escape time | sequential | viridis |
| centre | Newton basins for `z^3 - 1` | qualitative | Okabe-Ito subset |
| right | phase of a rational function | cyclic | twilight |

Each panel is an encoding the other two cannot carry, which is the argument the
figure exists to make. The escape-time panel carries a second point: the set's
interior is not a small value, it is a separate class — "did not escape" — and
drawing it as the bottom of the ramp claims a quantity that was never measured.
The interior is drawn in an explicit neutral, not `cmap(0)`.

Three dense images with three colorbars in one row is the hardest composition in
the gallery. That is deliberate. Per the gallery's own docstring, the figures
exist to find defects in the checks, and the checks most likely to be found
wanting here are text readability over a busy backdrop, axis redundancy across
image panels, and `check_ink` on three saturated axes at once.

The figure is audited by `finish()` like every other, and the script exits
non-zero if it fails.

## Tests

**Classifier, in `tests/test_palette.py`**

- every row of the table above, pinned by name and expected kind
- the two thresholds asserted directly: a synthetic ramp at 1.9% back-travel
  classifies sequential, one at 2.1% classifies misc
- viridis specifically, as the regression that motivated back-travel — it must
  not be misc
- a colormap with fewer than 40 entries is qualitative regardless of lightness
- an isoluminant ramp is misc, not sequential

**Differential, in `tests/test_palette.py`**

- `cmap_kind()` against `cmr.get_cmap_type()` across every registered
  matplotlib colormap, skipped when cmasher is absent or Python is 3.9
- disagreements are listed explicitly in the test with a comment for each
  saying which implementation is right and why. The list is the design record;
  an empty list would be a claim of exact parity across two color spaces, which
  is not true and should not be asserted.

**The differential has been run.** cmasher 1.9.2, matplotlib 3.11.1, 148
colormaps excluding reversals. At the thresholds above: **145 agree, 3
disagree.** Each is adjudicated, and the adjudication is the expected content of
that comment list:

| colormap | ours | cmasher | who is right |
| --- | --- | --- | --- |
| `managua` | diverging | misc | **ours** |
| `vanimo` | diverging | misc | **ours** |
| `Wistia` | misc | sequential | **cmasher** |

`managua` runs L 0.877 -> 0.355 -> 0.875 and `vanimo` runs 0.906 -> 0.201 ->
0.931: light ends, dark centre, the same shape as RdBu inverted. They are
Crameri maps added in matplotlib 3.10, and cmasher's strict `np.isclose` test
fails on their micro-reversals — the same defect that made a direct
transcription misclassify viridis. The tolerance-based method is the more robust
of the two, and the test should record that rather than defer.

`Wistia` is the one we get wrong, and it exposes a real limit of the metric.
Its lightness descends monotonically, 0.954 -> 0.726, but over a span of only
0.228. Back-travel is a ratio with span in the denominator, so its 0.0128 of
absolute wobble reads as 5.61% where viridis's 0.0006 over a 0.633 span reads as
0.10%. Narrow-span maps get noisy ratios.

Wistia is sequential *by kind*. Its problem — a lightness range too narrow to
carry an ordinal reading — is a quality defect, and quality is what the routed
`check(ordinal=True)` exists to judge. Conflating the two in the classifier is a
category error.

Two ways to fix it, neither chosen here: a floor on absolute back-travel
alongside the ratio, or a minimum span below which the ratio is not trusted.
Both need their own measurement across the registry before a constant is picked,
and per this spec's own rule a new colormap is a new row in the table, not a
quiet change to a threshold. **Ship with Wistia as a known, documented
disagreement; resolve it with evidence in a follow-up.**

**Gate, in `tests/test_figure.py`**

- `imshow` with `jet` FAILs; with `viridis` PASSes
- `imshow` with `hsv` FAILs; with `twilight` PASSes — the phase-portrait case
- harvest reaches `imshow`, `pcolormesh`, `contourf`, `hexbin`, and
  `scatter(c=..., cmap=...)`
- a figure with no colormapped artist reports "no colormapped artists" and
  passes, rather than erroring
- a qualitative map whose levels fail all-pairs separation FAILs, proving the
  routing reaches `check_palette` rather than stopping at classification
- colorbar axes do not contribute a colormap of their own
- regression: `_data_colors_by_axes` still excludes colormapped artists, so a
  heatmap is not gated twice under two different rules

**Gallery, in `tests/test_example.py`**

- the count assertion moves from 6 to 7

## Limits, stated on purpose

**turbo passes as diverging.** Its back-travel is 0.38% and 0.58%, cleaner than
coolwarm's. That is correct by the measurement: turbo's lightness profile
genuinely is diverging-shaped — it was designed to fix exactly the lightness
defects that put jet in the misc bucket. Turbo's remaining problem is hue
banding, which produces false boundaries without any lightness reversal.

A lightness-only classifier cannot condemn turbo, and this design does not
pretend otherwise. Catching it would need a second measurement over hue or
chroma travel. That is a separate gate with its own thresholds and its own
evidence, and folding it in here would mean shipping two half-measured checks
instead of one measured one.

The row is therefore named "Colormap kind" and not "Colormap quality".

**The 2% threshold is empirical.** It separates the colormaps matplotlib ships.
A custom colormap sitting between 1.05% and 2.79% will be classified by a number
that has 1.9x of justification behind it and no theory. When such a map appears,
the fix is another row in the table above, not a quiet change to the constant.

## Risks

- ~~The differential test may disagree more than expected.~~ **Resolved by
  running it.** 3 of 148, adjudicated above. The oracle earned its dependency
  before being written into a test: it caught the lightness-wrap error, which was
  a real design defect that would have shipped 11 colormaps misclassified.
- ~~`hexbin` and `contourf` harvest paths are unverified.~~ **Resolved.** Both
  verified on matplotlib 3.11.1, along with five other call types, and the
  `get_cmap()`-versus-`get_array()` trap found in the process.
- **Three dense panels may not survive the existing gates.** Still open, and not
  resolvable without building the figure. If `gallery-encoding.png` cannot be
  made to pass, the finding is either a real composition limit worth documenting
  or a defect in a gate — both are outcomes the gallery exists to produce. It is
  not a reason to weaken a check.
- **The 2% back-travel threshold has one known false positive.** Wistia. See the
  adjudication above; the resolution is deferred with evidence, not hidden.
- **Thresholds are pinned to matplotlib 3.11.1's registry.** A future matplotlib
  that adds or revises colormaps can move the binding pairs. The differential
  test is what will catch that, which is the second reason to keep it.
