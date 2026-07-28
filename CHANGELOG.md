# Changelog

## Unreleased

### An audit of the gates, and what it found

Two of the nineteen rows were not measuring what they claimed, and four
documented numbers were not the numbers the code computes. All six are the same
species — a claim nobody had run — which is what the rest of this file is about,
so each fix ships with the executable link that keeps it true.

- **The contour-dash gate never fired on signed data.** It required *every*
  level to be non-positive, which is the one shape a genuinely signed field
  never has: `contour` over data spanning zero draws levels either side, and
  matplotlib dashes the negative half. A `sin(x)cos(y)` field shipped four
  dashed isolines and the gate reported "no auto-dashed negative contours". The
  only test it had drew `-(x² + y²)`, non-positive throughout — the one shape
  that met the condition — so the hole was invisible from inside the suite.

  The rule is now "any negative level", and it is asked of the strokes the set
  actually drew rather than of `negative_linestyles`, which is what the gate
  should have read from the start. Six tests cover it: the signed field, the
  signed field drawn solid, all-negative both ways, all-positive, colormapped,
  and filled.

- **Two rows were documented as able to fail, and cannot.** `Overplotting` and
  `Contour dash` return only `True` or `"warn"`, but the README table gave both
  a "Fails when" and the prose counted five advisory rows against an actual
  seven. `ADVISORY_GATES` in `check_figure.py` is now the one list; the table's
  tags, the count in the prose, and the claim that none of those functions has a
  returning-`False` path are all tested against it.

- **`check_mark_ratio` measured two mark kinds in different units.** Scatter
  `s` is an area in pt²; `markersize` is a diameter, and squaring it gives the
  bounding square rather than the disc — 4/π = 1.27× too large. On a figure
  drawing one kind the bias cancels in the ratio and nothing shows. On one
  mixing `scatter` with `plot(marker=...)`, two marks of identical drawn area
  reported 1.3×, which against a 5.0 threshold fails a legal figure at a true
  3.9× and passes a bad one at 6.4×.

- **`alt_metadata` warned on every PDF save, and crashed on every jpeg.** The
  documented call — the one in `SKILL.md`, in the README and in both examples —
  is `savefig(path, metadata=alt_metadata(fig))`, and what each format does
  with that turned out to be four different things, three of them undocumented:

  | Format | `Description` | `Subject` |
  |---|---|---|
  | png | lands in a tEXt chunk | lands |
  | pdf | **warns**, info dictionary is closed (PDF 1.7 §14.3.3) | lands |
  | svg / svgz | lands in Dublin Core | **raises** |
  | ps / eps | accepted, carried nowhere | carried nowhere |
  | jpg, webp, tif, raw, pgf | **raises** | **raises** |

  So the key cannot be one value, and for the bottom row it cannot be a value at
  all: matplotlib's guard is `elif metadata is not None: raise`, which rejects
  `{}` exactly as hard as a full dict. `savefig(path, metadata={})` on a jpeg
  was already a traceback before any of this — a figure with no description
  attached hit it too.

  `alt_metadata(fig, path)` now reads the suffix and returns the key that
  format has, or `None` — `savefig`'s own default for the argument — for the
  ones that have none. Called without a path, or with a buffer whose format
  cannot be read, it returns `Description` as every earlier version did. An open
  file is asked for its `name`. The table is not written from memory: the suite
  saves a real figure in every format it names and asserts no warning and the
  text present in the bytes, and saves in every format it excludes and asserts
  the call survives.

- **The guide's ink table credited the sheet with a token it does not ship.**
  Muted ink was listed as `#898781`, which `figure.mplstyle` stopped setting
  when `check_text_readability` failed the sheet's own tick labels against it at
  3.59:1 — under the 4.5:1 a glyph stem needs. It is `#777570`. The old spelling
  stays in `INK_TOKENS` so figures built on the old sheet still read it as
  furniture. Every hex the table credits to the sheet is now resolved against
  the sheet through `rc_params_from_file`, so the table cannot quote a value the
  sheet does not define. Third instance of this exact failure, after the
  contrast column and the retired `#fcfcfb` surface.

- **"Only the first four slots clear all-pairs" was off by one.** Five clear it,
  at ΔE 11.2 under deuteranopia against a target of 8; six is the first count
  that fails, at 7.9 (`#009E73` vs `#CC79A7`). Four was a number nobody had run,
  stated in three documents and the appendix constant as though it were a
  measurement. The limit is now derived in the suite by asking
  `check_palette.check(..., all_pairs=True)` for the largest passing count, and
  the prose and the constant are held to it.

- **`_halo` reads a matplotlib internal and failed silently.** `Stroke` keeps
  its kwargs in a private `_gc` and there is no public accessor; the fallback
  returned "no casing", which would have meant every cased label in every figure
  being judged against the raw backdrop the casing exists to survive — correct
  work failing, with nothing saying why. It now tries any other dict attribute
  carrying a `foreground`, and a direct test makes an upstream rename a red
  suite rather than a quiet regression.

- Smaller, same shape: `--venues` no longer requires matplotlib to print a table
  of numbers; the dual-axis message says "two data scales" rather than "two y
  scales", since `twiny` lands there on the same argument; the appendix's
  `ordinal()` no longer divides by zero at `n=1`; and the scipy-optional test
  now compares the KD-tree and numpy nearest-neighbour paths against each other
  on a figure that actually has a scatter — the old one audited a figure with
  none, proving the import was soft but never that the fallback computes the
  same thing.

Suite: 224 → 268 tests.

### Docs site

Documentation only. No code, no thresholds, no packaging change — the wheel
built from this commit is byte-identical in what it ships.

- **A docs site**, [Zensical](https://zensical.org), published to GitHub Pages
  from `.github/workflows/docs.yml`. It exists because `style-guide.md` is 367
  lines of reference material whose only affordance on GitHub was scrolling,
  and the thing people do with it is look one threshold up.

  Every page except the gallery is a **symlink** to the file that already
  existed. That is not tidiness: `test_docs_match_code.py` reads
  `skill/references/style-guide.md` and asserts its contrast table against
  `contrast()`, and it can only keep doing that if the page the site serves *is*
  that file. A `docs/` of hand-maintained copies would pass the entire suite
  while publishing numbers that had drifted — the failure that file already
  exists to prevent, one level further out. `test_docs_site.py` asserts no page
  has quietly become a copy.

- **The theme's two link colors are a measurement, not a preference.** Okabe-Ito
  blue `#0072B2` is 5.19:1 on white but 3.10:1 and 3.77:1 on the two dark
  backgrounds Zensical ships (`classic` at `hsl(225, 15%, 14%)` = `#1e2129`,
  `modern` at `hsl(225, 15%, 5%)` = `#0b0c0f` — both blue-tinted, neither
  neutral). Body-text links need WCAG's 4.5:1, not the 3:1 floor series colors
  are held to, so dark mode takes sky `#56B4E9` at 6.98:1 and 8.48:1 instead.
  One hue for both would have shipped a site about colorblind-safe figures whose
  own dark-mode links miss the floor. Every number is recomputed by the test
  suite against a background derived from HSL rather than pasted, for the same
  reason every other quoted number here is executable.

  Both variants are measured, not just the configured one. `variant` is a
  one-line edit, and a measurement that is true until someone flips a line is
  the failure this project is about.

- **Strictness is a flag, and it does less than its name suggests.** The docs
  build runs on pull requests as `zensical build --strict`, which fails on a
  broken link between pages. It does *not* fail on a nav entry whose file
  cannot be read: that page is silently not built, the sidebar renders a raw
  `./style-guide.md` href, and the build exits 0. Measured, not assumed — every
  page here is a symlink, so that is the failure most likely to happen.

  Three checks rather than one, then. The symlink check runs before the build
  and is the only thing that catches a dangling pointer; `--strict` covers
  links between pages; and a post-build check asserts every page named in the
  nav produced HTML. `test_docs_site.py` carries the first as a unit test, so a
  file moved under `skill/` fails `pytest` and not only CI.

  Zensical also reads a leftover `mkdocs.yml` and silently ignores its
  `strict: true` — the first build of this site was exactly that config — so a
  test asserts there is no `mkdocs.yml` in the repository.

  Zensical is 0.0.x, so the docs dependency is pinned `>=0.0.51,<0.1` rather
  than floored. Nothing else in the project depends on it; the checkers are not
  involved in building the site.

- **The README claimed five defects; `examples/gallery.py` enumerates six.**
  Both numbers were prose, so neither could be wrong loudly, and the wrong one
  was old enough to get copied into the docs site while it was being written —
  a number in prose spreading rather than being corrected. Fixed to six, and
  `test_docs_match_code.py` now asserts the three places that state the count
  agree with each other.

## 0.1.4 — 2026-07-28

One dead gate on the install path, and the missing way to point a live one at
your own sheet. Nothing about the thresholds changed.

- **The wheel ships `figure.mplstyle`.** It ships beside `check_figure.py`,
  which is the first location `_style_sheet` probes. Through 0.1.3 the wheel
  carried `skill/scripts` and nothing else, so on `uv add figure-gate` there was
  no sheet anywhere the checker looks: the style-sheet row read *"no
  figure.mplstyle beside this script, nothing to compare"* and returned a pass
  — for a figure drawn on stock matplotlib with `plt.style.use` forgotten
  entirely, which is the first failure the check's own docstring names. The gate
  is advisory, so nothing was wrongly certified composed; it simply did nothing
  on the path the README advertises. No code changed, only the build config.

- **`STYLE_SHEET` is a module-level constant.** The sheet is meant to be edited
  per document, so a project whose sheet lives somewhere other than beside the
  checker needs a way to say so, and until now that way was patching a private
  function. `None` keeps the existing behaviour: beside the script, then
  `assets/` next to it. A path that is set and does not exist reports a warn
  naming it, rather than falling back to a sheet the project did not ask for.

- **The install path is tested, and tested twice over.** `tests/` builds the
  layout the wheel produces and runs the checker inside it, with the checkout's
  `assets/` off the import path — the copy-based tests could never have caught
  this, because from a checkout the sheet is always one directory up. And CI
  now builds the real wheel, installs it, and asserts the gate fires on a stock
  figure and clears once the shipped sheet is applied; a mapping in
  `pyproject.toml` is not evidence about what the build emits.

- **The README's test count is checked against pytest.** It was wrong at 0.1.2
  and hand-corrected at 0.1.3, which is the same fix twice. A test now reads the
  number out of the README and compares it to a fresh collection, so the next
  drift fails rather than ships. The count is 178.

## 0.1.3 — 2026-07-28

Mostly the README. 0.1.2's fix shipped without the project page explaining the
condition it fixed, and PyPI renders the README from the released sdist, so the
explanation could not reach the project page without a release of its own.

- **The README documents the HiDPI behaviour**, in a section under "Use it":
  what a Retina or scaled-display backend does to `fig.dpi`, both ways that went
  wrong through 0.1.1, and the one consequence a user can trip over — an audited
  figure is no longer attached to its GUI canvas and will not show in a window.
  It also names the reason the bug survived: every test and example here pins
  Agg, so nothing in CI could construct the failing condition.

- **`OVERPLOT_THRESHOLD` is a module-level constant.** The README's opening
  claim is that every threshold is one you can read and change, and this one was
  a local inside `check_overplotting` — cited in the gate table by a name that
  could not be imported. The value is unchanged at 0.5.

- **Two README claims corrected against the code.** The test count said 166 and
  the suite is 171. And `check()` returns `(rows, ok)` while `audit()` returns
  `(ok, rows)`; the opening paragraph said check "does the same", which reads as
  a promise about the tuple order that the code does not keep. The order is now
  stated. Neither function changed — unpacking is published API.

## 0.1.2 — 2026-07-28

- **The audit no longer depends on the display it ran on.** A HiDPI GUI backend
  — macosx on a Retina display, Qt on a scaled desktop — sets `fig.dpi` to the
  authored dpi times the display's device pixel ratio when the figure is
  created, and `_renderer` kept that canvas whenever it could measure text. So
  the checker ran at 2× on exactly the machines figures get authored on.

  Two things went wrong at once. Text window extents come back in physical
  pixels while `canvas.get_width_height()` reports logical ones, so
  `check_clipping` compared 2× coordinates against a 1× bound and called every
  label past the midpoint clipped — a full-width figure with tick labels failed
  a gate it should pass, which is the wrong direction for a gate to be wrong in.
  And every threshold calibrated in pixels — `TEXT_EDGE_WINDOW = 9`, measured
  against a 1.6pt hairline at 150 dpi — covered half the distance it was
  calibrated for. Ink coverage read 0.05 under macosx and 0.04 under Agg on the
  same figure.

  `_renderer` now resets `fig.dpi` to the authored value and builds the Agg
  canvas unconditionally, so a figure's verdict is a property of the figure.
  One consequence worth knowing: an audited figure is no longer attached to its
  GUI canvas and will not show in a window. `check_ink` and
  `check_text_readability` already rebound `fig.canvas`; it is now unconditional.

- **The tests can see this class of bug now.** They could not before, because
  `conftest` pins Agg and so does every script in `examples/` — which is why a
  real bug sat behind a green suite and a green CI. The new tests simulate a
  HiDPI canvas instead of requiring a display, and one of them asserts every
  audit row is identical at 1× and 2×, messages included.

- **The README gate roster is being read again.** The 0.1.1 README rewrite added
  a Threshold column to the `check_figure.py` table, and the test that checks
  that table against what `audit()` returns matched rows by shape. It matched
  nothing, and compared an empty list against 19 gates. It now reads the first
  cell whatever the column count, and asserts it read something at all — the
  guard the contrast table has had all along.

## 0.1.1 — 2026-07-27

- Releases are signed. 0.1.0 went out through `uv publish`, which despite
  offering `--no-attestations` uploaded no provenance at all — PyPI's integrity
  endpoint 404s for both of its files. The upload now runs through the PyPA
  action, which attaches a PEP 740 attestation. 0.1.0 cannot be fixed; published
  files are immutable.
- The TestPyPI rehearsal uploads the same way the real release does. It did not
  before, which is why the missing attestations survived a rehearsal.

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
