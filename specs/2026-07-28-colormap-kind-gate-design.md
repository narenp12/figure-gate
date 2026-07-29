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
- **Cyclic rather than diverging: wrap below 1% of span.** `twilight_shifted` at
  0.34% against RdBu at 2.09%, a 6x margin.

Order of tests, mirroring cmasher:

```
N < 40                          -> qualitative
total span < 0.02 OKLab L       -> misc          (isoluminant)
whole-map back-travel < 2%      -> sequential
both halves back-travel < 2%    -> cyclic if wrap < 1%, else diverging
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

1. **Harvest.** Every artist in `ax.images`, plus every artist anywhere in the
   figure whose `get_array()` is not None. Take `get_cmap()` off each. Colorbar
   axes are skipped, as they already are in `check_ink`.
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

- **The differential test may disagree more than expected.** cmasher's cyclic
  test is threshold-sensitive and runs in a different color space. If the
  disagreement list grows past a handful of entries, the oracle is not earning
  its dependency and should be dropped rather than papered over.
- **Three dense panels may not survive the existing gates.** If
  `gallery-encoding.png` cannot be made to pass, the finding is either a real
  composition limit worth documenting or a defect in a gate — both are outcomes
  the gallery exists to produce. It is not a reason to weaken a check.
- **`hexbin` and `contourf` harvest paths are unverified.** Both are asserted to
  expose a colormap through `get_array()`/`get_cmap()`; neither has been run.
  Verify before relying on the routing.
