# Changelog

## 0.1.0 — 2026-07-27

First release on PyPI. Everything below is the work that preceded it.

### Four gates that were measuring the wrong thing

Found by running the checker over ordinary matplotlib figures nobody built for
it — the corpus check CONTRIBUTING asks for, applied to the checker itself
rather than to a new gate.

- **Polar radial tick labels are no longer judged by `check_text_readability`.**
  Every ordinary polar plot failed. matplotlib places radial labels inside the
  disc and `set_rlabel_position` only moves them to another angle, so "move the
  label to clear ground" named a move that does not exist. The first fix
  exempted only the clutter clause and was not enough: the contrast clause went
  on failing **eight of eight** polar plots built on this project's own
  `figure.mplstyle`, at 2.0:1 against a curve the radial axis crosses by
  construction. A gate the bundled sheet cannot satisfy is measuring the
  projection, not the figure. Both clauses now skip these labels and the row
  reports how many went unjudged, so the author is told rather than left to
  assume they passed. Author-placed text on a polar axes is still judged.

- **`check_redundancy` no longer reads furniture that never renders.** Three
  `imshow` panels at `axis("off")` were told to "use sharex/sharey" on the
  strength of the tick `Text` objects matplotlib keeps for an axis it is not
  drawing. Axes with `axison` false are skipped, and the tick clause now counts
  only visible labels.

- **`check_ink` can see an empty panel again.** The README has always claimed
  the row catches "a panel is empty", and the pixel fraction could not: a blank
  axes measures about 0.03 from its frame and ticks alone, over the 0.02 floor.
  The blank subplot in a grid — the case that actually ships in papers — read as
  merely sparse. Emptiness is now structural: was anything drawn into this axes.
  The fraction clause is unchanged and still governs sparse and saturated
  panels.

- **`check_line_weight` has tests.** It shipped with none, which is the one
  thing CONTRIBUTING says a gate may not do. Four now: a hairline fails, a
  legal stroke passes, a 1.2pt stroke fails once placement thins it to 0.6pt on
  the page, and the grid is not held to the data floor. The gate was correct —
  it had simply never been watched work.

### Text readability — the gate the demo needed

- **`check_text_readability` measures whether each string can be read where it
  sits.** Two clauses, both off rendered pixels. *Clutter*: the figure is drawn
  a second time with every string hidden, and that render is the backdrop each
  label was placed onto; pixels inside a label's box that no blend of {its
  surface, the grid, the axis rule} explains are data ink passing through the
  text. *Contrast*: the text against the backdrop it actually got, at the WCAG
  **text** threshold (4.5:1, or 3:1 large) rather than the 3:1 a mark gets,
  because a glyph stem is thinner than a mark.
- **Measuring the backdrop rather than the finished render is the point.**
  Casing hides the evidence: a white halo over an orange curve renders as clean
  white while punching a visible gap through the data. Both halves of that are
  defects and this reads them as one number.
- **Clutter is an *edge*, not a deviation from the dominant color.** The first
  version tested each pixel against the box's modal color and failed every
  annotation ever placed on a heatmap, because a smooth ramp differs from its
  own mode everywhere while being, to a reader, one surface. Now each pixel is
  tested against a local average of its neighbours, so a viridis field is
  ground and a hairline is a mark.
- **It found the sheet's own ticks.** `xtick.color`/`ytick.color` shipped at
  `898781`, which is 3.59:1 on white — under the text threshold on every figure
  in the repo. Now `777570` at 4.6:1, still below the 7.94:1 axis label, so the
  hierarchy axis label > tick label > grid survives.
- **`examples/demo.py` was the first thing it failed.** All three direct labels
  sat *on* their own curves — `'Baseline'` on data ink over 17% of its box —
  while `check_label_attribution` passed them, correctly, because a label
  printed on its own line is attributed perfectly. The cause was alignment:
  `ha="center"` clears a sloped curve at the anchor and puts both ends of the
  box back down on the line. Fixed by aligning toward the side the curve is
  leaving, and by anchoring on the extreme of the noise across the label's own
  span rather than on one point.

### Research-standard gates

- **`check_line_weight`: 1pt on the page, per SIAM's instructions for authors**
  ("lines one point or thicker; thinner lines may break up or disappear").
  Measured through `page_scale` like the type floor, since it is the same
  failure. Gridlines are held to a lower floor than data on purpose.
- **`check_fonts`: Type 42 embedding, and the face you named.** matplotlib
  defaults `pdf.fonttype`/`ps.fonttype` to 3; IEEE PDF eXpress rejects the
  upload and ACM/Elsevier reject the submission, with nothing warning you
  because the figure renders identically. Also warns when none of the faces in
  `font.<family>` is installed and matplotlib has silently substituted its own.
  Advisory, because it reads global rcParams rather than anything the figure
  carries — the hard gate is on the shipped sheet, in the test suite.
- **`figure.mplstyle` now sets `pdf.fonttype: 42` and `ps.fonttype: 42`.**

### Venue content widths

- **`audit(fig, venue="neurips")`** replaces hand-measuring `CONTENT_WIDTH_PT`
  for twelve known venues (NeurIPS, ICLR, ICML, ACL, IEEE, Nature, LaTeX
  `article`, and the column widths of the two-column ones). `python
  check_figure.py --venues` lists them. `CONTENT_WIDTH_PT` still works and still
  wins for anything not in the table.

### Alt text

- **`describe(fig, ...)` / `alt_metadata(fig)` / `check_alt_text`.** Across
  100,000 public Jupyter notebooks, 99.81% of programmatically generated images
  shipped with no alt text, nearly all matplotlib. `alt_metadata` produces the
  `metadata=` dict for `savefig`, so the description survives into the PNG, PDF
  or SVG. Advisory: on a paper the description frequently *is* the caption, and
  the caption lives where this cannot see it.

### `check_label_attribution` was passing nearly everything

- **Fixed a regression that had disabled the gate in its common case.** The
  comparison distance had been changed from "the minimum over every other curve"
  to a KD-tree query for the *k* nearest pooled points. For a label sitting near
  its own dense curve, every one of those points belongs to that curve, no other
  curve is ever reached, and `d_other` stays infinite — so the gate passed every
  label whose own curve was nearest, which is nearly all of them. Back to the
  explicit minimum, with a regression test for a label in the corridor between
  two curves.
- **It found a real defect the moment it worked.** `gallery-convergence.png` had
  its direct labels past the right-hand end of each curve, 29px from their own
  and 35px from a neighbour's: a label outside the data is not resolved by
  proximity to anything. Moved to the left of the panel where the log-log fan is
  three decades wide.

### No hard scipy dependency

- The README promises three files and no install, and a hard `scipy` import had
  quietly broken it. `scipy.ndimage.uniform_filter` is replaced by a separable
  cumulative-sum box blur in numpy; `scipy.spatial.KDTree` is gone from label
  attribution entirely; `check_overplotting` uses `cKDTree` when it is
  importable and an O(n²) numpy path when it is not. scipy is now an optional
  `fast` extra. Tested with the import forced to fail.

### `examples/gallery.py` — six harder figures

- Small multiples on shared scales; a filled field with isolines and a colorbar;
  an axis-free schematic; the three forms `choosing-a-form.md` argues for; a
  log-log convergence plot with a slope triangle; a dense orbit diagram. Each is
  audited, and CI fails if any figure fails.
- **Writing them found six defects in the checks themselves**, which is what
  they are for:
  - the readability gate reported a schematic's tick labels, which
    `ax.axis("off")` means never reach the page — it now skips `_ghost_ticks`
    the way `check_clipping` already did;
  - `check_ink` measured colorbar axes, which are a solid ramp by construction,
    so every figure with a colorbar stood at WARN for the one axes in it whose
    density nobody chose;
  - `check_line_weight` measured a colorbar's own 0.4pt dividers;
  - `_artist_kind` called `plot(..., linestyle="none", marker="o")` a line, so a
    path and its own start marker in one hue read as a wrapped color cycle;
  - the clutter metric failed every heatmap annotation, as above;
  - `check_label_attribution` was passing nearly everything, as above.
- **And two defects in the figures that no gate caught**, which is what step 7
  of the procedure is for: the schematic's feedback loop ran off the bottom of
  the canvas (`connectionstyle="bar"` drops by a *fraction* of the span, so a
  wide loop went fifteen units below an axes that stops at zero), and the
  convergence plot's slope triangle sat in the only corner its direct labels
  could use. Both were obvious in the PNG and invisible to every check.

### Overplotting / mark-density WARN

- **`check_overplotting` detects scatter marks that merge into a blob.** For
  each scatter (`PathCollection` with offsets), estimates the fraction of points
  whose nearest neighbour in display pixels is within one marker radius — points
  that visually overlap. Above ~50% overlap the WARN fires: reduce counts, use
  hollow markers, add transparency, or switch to hexbin. The 0.5 threshold keeps
  the entire existing corpus clean (all well-separated scatters pass). A WARN,
  not a FAIL — dense marks are legitimate for some forms (e.g. a swarm plot).

### Context-surface ink stops a standing WARN

- **Ink coverage accepts `context_axes`.** A filled contourf backdrop (loss
  landscape, terrain) saturated 100% of the axes pixels, triggering a standing
  ink WARN on every such figure — the "advisory everyone learns to ignore." New
  `audit(fig, context_axes=[ax])` declaration tells the checker the fill is a
  context surface, not data-ink. The pixel buffer is split into two clusters via
  2-means on color; the larger cluster (the surface) is subtracted from the ink
  count, so only marks *on top* of the backdrop are measured. A terrain panel
  with a few sparse marks now PASSes instead of WARNing. Existing heatmap
  behavior is unchanged (no `context_axes` → same as before).

### Two false-signal fixes, no new gates

- **Contour dash warns on auto-dashed negative levels.** A monochrome contour
  with all-negative Z ships dashed isolines via matplotlib default
  (`contour.negative_linestyle`). The skill's own convention is dashing =
  unobserved / projected / threshold, so this is a silent semantic error no
  existing gate saw. New `check_contour_dash` warns; pass `linestyles="solid"`
  on signed data. Style guide note added.
- **`check_palette.py` learns `--ink`.** Ink/neutral hexes were flagged by the
  chroma-floor and lightness-band rows, but an ink token is not a series hue.
  New `--ink "#52514e,#898781"` flag exempts listed hexes from those checks
  while keeping them in CVD/normal separation and contrast-vs-surface coverage.
  Mirrors `check_figure`'s `INK_TOKENS`.

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
