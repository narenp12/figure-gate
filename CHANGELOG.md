# Changelog

## Unreleased

### The series-color and label gates learn the figure's structure

The new gates above read a flat bag of hues and text, and a bag throws away the
structure the author encoded — which panel a hue lives in, what kind of artist
drew it, whether a piece of text is a direct label or a legend key. Four figures
that were mechanically correct got failed for it. Each fix gives the harvester
back one piece of that structure.

- **Series color is scoped per panel.** The comparison, the hue count and the
  adjacent-versus-all-pairs mode are now asked of one axes at a time. A
  figure-wide harvest gated hues that never share a frame — a flow-chart node in
  one panel measured against a regression curve in another — and let a single
  scatter flip every line-only panel into the stricter all-pairs regime. The
  panel is the unit a reader separates hues within.
- **One series drawn several ways is one identity.** The wrap check — one hue,
  two labels — is narrowed to labels on artists of the *same kind*. A cycler that
  wraps reuses one artist type; a posterior shown as a credible band, its mean
  line and its observed points is three kinds in one hue, one series shown three
  ways. Two lines in one hue with two labels is still the wrap it always caught.
- **Label attribution ignores legend entries.** A legend is a lookup key placed
  away from the curves by design, so judging its entries by proximity to those
  curves could only ever fail. They slipped the `t.axes is ax` guard because a
  legend child's `.axes` is the parent axes; they are now dropped explicitly.
- **Ordinal ramps on marks belong in a colormap** (guidance). A ramp is built to
  violate the categorical floor, and a `scatter(c=[rgba, …])` list reads as that
  many independent hues. The style guide now says to draw it
  `scatter(c=values, cmap=ListedColormap(ramp))`, which the harvester already
  exempts as a value encoding — the intent lands in the code instead of a flat
  bag of hues.

### Five new gates, and the two scripts finally speak

The motivating failure, reproduced end to end: a figure drawn on matplotlib's
default `tab10` cycle with a `twinx` second y axis passed every check in
`check_figure.py` and printed `-> COMPOSED`. The same three hues through
`check_palette.py` reported `CVD separation (adjacent) worst #ff7f0e vs
#2ca02c dE 1.4 (protan)` — one hue to a protanopic reader. Two scripts in one
project, and nothing connected them.

- **`figure.mplstyle` sets `axes.prop_cycle`** to the six Okabe-Ito series slots,
  in canonical order. Until now the sheet set every visual default except the one
  that decides whether a colorblind reader can separate two curves, so a figure
  built on it inherited `tab10`. Yellow and black stay held out — yellow at 1.32:1
  vanishes as a hairline, black is the ink token.
- **Series color** reads the hues off the figure's own artists and puts them
  through the palette gates, inferring adjacent-versus-all-pairs from whether the
  marks are scatter. Also fails a seventh distinct hue, and one hue carrying two
  labelled identities — which is what the cycler wrapping looks like, and was
  prose only before. Harvest excludes colormapped artists and the sheet's ink
  tokens; the lightness-band and chroma rows are deliberately not applied, because
  a gray control curve is legal.
- **Dual axis** fails two axes sharing a frame when both carry data: the crossing
  point of the curves is then set by the limits rather than the data. A bare unit
  relabel — `secondary_yaxis` with no artists of its own — still passes.
- **Form** fails the mechanical subset of form choice: pie/donut, 3D axes, and
  bars on a truncated baseline. Log-scale bars are exempt, since a log axis cannot
  contain zero.
- **Identity channel** warns when two or more labelled hues carry identity with no
  legend and no in-axes text. A warning rather than a gate: the script cannot tell
  a direct label from any other annotation, and guessing would fire on correct work.
- **Style sheet** warns when the keys in `figure.mplstyle` are not the ones in
  effect. Catches the `#`-is-a-comment trap, a forgotten `plt.style.use`, and a
  later rcParams override in one row.
- **Label attribution** fails a direct label that is not plainly nearest the
  curve it names. `Text collision` compares text against text, so a label alone
  in the corridor between two curves clears it; text against *data* is a
  different question and nothing was asking it. Measured in display space as a
  ratio — the reader's judgement is comparative, not a distance in points — and
  harvested only from text matching exactly one series label, because a callout
  or a panel letter attributes nothing to a curve.

### Decided: identity does not ride on label color

The usual advice is to color a direct label to match its series. Measured on
this palette, against this project's own thresholds, it cannot be done: text
needs 4.5:1 to be legible, and darkening the Okabe-Ito hues that far puts orange
at dE 18.6 from its own line and sky blue at 17.1 — both past the `NORMAL_FLOOR`
of 15 at which `check_palette` calls two colors different series. The label
would read as a fourth hue. Below 15 the text is not legible. No setting
satisfies both, so labels stay ink black and identity rides on proximity, which
`Label attribution` now gates rather than assumes.

`examples/demo.py` gains cartographic casing on its labels — a surface-colored
stroke under the glyphs — so a gridline crossing behind a label stops breaking
its edges.

### Decided: a legend entry is not a direct label

The guide required a "visible direct label" for a sub-3:1 hue and `examples/demo.py`
used a legend, so one of the two was wrong. Settled the strict way, because the
obligation follows from the measurement: a faint mark plus a legend leaves the
reader matching a small faint swatch to a small faint curve, which is the step a
direct label removes. The demo now labels its curves directly.

### New reference

`skill/references/choosing-a-form.md`, plus a step in `SKILL.md`'s procedure.
Grounded in statistical graphics rather than general information design —
Cleveland & McGill's ordering of the elementary perceptual tasks, and the
statistical results behind the rules that matter most in teaching material: what a
box plot hides at small n, why a cut baseline misstates every ratio, why two bars
are the wrong form for paired data, and why overlapping confidence intervals are
not a significance test.

## Earlier in Unreleased

Corrections, no new gates. Nothing that passed before fails now.

- **Surface is white everywhere.** `check_palette.py` defaulted to `#fcfcfb`, a
  surface `figure.mplstyle` never rendered, so every contrast ratio in the style
  guide was measured against a page that did not exist. Reddish purple was
  listed as needing a mandatory direct label at 2.98:1; against the surface
  actually used it clears 3:1 at 3.06. Table recomputed, `--surface` still
  available for a genuinely tinted page.
- **`tests/test_docs_match_code.py`** parses the guide's contrast table and
  checks every quoted number, and every † marker, against `contrast()`. The
  drift above is now a test failure rather than something noticed in a year.
- **`placed_frac` on `audit()`/`report()`.** A figure placed at
  `0.48\textwidth` was measured as if it were full width and certified at twice
  the type size it shipped at. Passing `placed_frac` without `CONTENT_WIDTH_PT`
  raises rather than silently assuming 1.0.
- **Mark ratio sees line markers.** It read only `ax.collections`, so
  `markersize=3` beside `markersize=30` passed clean. Bars stay excluded on
  purpose — a bar 30× another bar is the encoding working, and the docstring now
  says so instead of leaving it to look like an oversight.
- **`figure.mplstyle` carries the mark and output defaults**: `lines.linewidth`,
  `lines.markersize`, `axes.linewidth`, `patch.linewidth`,
  `legend.handlelength`, `errorbar.capsize`, `axes.axisbelow`, plus
  `figure.dpi`, `savefig.dpi`, `savefig.bbox`, `savefig.facecolor`. These were
  prose passed by hand at each call site; at matplotlib's default 100 dpi the
  "render a PNG and look at it" step produced a PNG too soft to show the
  defects it was opened to find.
- **`bbox_inches="tight"` documented as a trap** beside the `#`-is-a-comment
  one, and pinned in the sheet. It trims to drawn content, so the saved width
  stops being the authored width the type gate derives its floor from — the
  gate then certifies a size the shipped file does not have.
- `axes.titlesize`/`titleweight` annotated as panel-title settings, resolving a
  contradiction with the guide's ban on in-figure titles.

## 0.1.0 — 2026-07-22

First release.

- `check_palette.py` — lightness band, chroma floor, CVD separation (protanopia
  and deuteranopia, OKLab ΔE), normal-vision separation, contrast against the
  surface, and a four-gate mode for ordered ramps. Standard library only.
- `check_figure.py` — clipping, text collision, alpha stacking, mark ratio, axis
  redundancy, type size on the printed page, and ink coverage, read off a built
  matplotlib figure's own artists.
- `figure.mplstyle` — typeface, ink, type sizes, spines, grid, frameless
  legends.
- `skill/` — Agent Skill wrapper (`SKILL.md` plus the full style guide).
- 49 tests, including per-gate failure cases and a guard against the style
  sheet's colors silently not applying.
