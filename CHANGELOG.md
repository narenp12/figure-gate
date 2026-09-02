# Changelog

Each release is written in two blocks. **What changed** is the reference half:
one line per change, naming the symbol, the row or the value that moved, and
nothing else. **Why it changed** is the explanation half: the measurement, the
defect it exposed, and what it cost. A release whose entry is already a short
list of self-explaining lines carries the first block only.

The split is deliberate. A reader who wants to know whether an upgrade will
break them should not have to read an essay to find out, and the essays are
worth keeping: most of them record a measurement that is the only evidence
behind a threshold this project enforces.

## Unreleased

### What changed

#### Changed

- `audit(context_axes)`, `audit(venue)`, `report(context_axes)`,
  `report(venue)` and `report(suggest)` changed to keyword-only.
- `check_figure.audit` measures under the rcParams the figure's first audit
  saw. `METRIC_RC_KEYS` names them. `Style sheet` and the Type 3 clause of
  `Fonts` still read the live rcParams.

#### Added

- `check_palette.cmap_kind_rgb` and `check_palette.cmap_back_travel_rgb`,
  classifying a ramp from float sRGB. The hex-taking `cmap_kind` and
  `cmap_back_travel` are unchanged.
- Two gallery figures, `gallery-callout` and `gallery-secondary-scale`,
  carrying an annotation drawn with a leader line and a secondary axis.
- Six gallery figures, `gallery-survival`, `gallery-raster`, `gallery-rose`,
  `gallery-parity`, `gallery-phase` and `gallery-trendmap`: a Kaplan-Meier
  staircase, a spike raster, a polar rose, a parity plot, boundaries labelled
  along themselves, and a field faded by its own significance. The corpus is
  nineteen figures.
- `examples/gallery.py` audits the sheet's own palette with `check_palette`,
  categorical and ordinal, alongside the figures. `main` fails on a palette row
  as it does on a figure.
- `check_figure.MARK_RIDE_TOL_PX` and `check_figure.MARK_RIDE_FRAC_MIN`, the
  two thresholds separating a companion mark from a rival series.
- `tests/test_style_context_invariance.py`, holding every row identical across
  the sheet boundary for `demo` and `encoding`.

#### Fixed

- `Contrast stack` no longer fails a figure that uses matplotlib's per-point
  alpha. An alpha ramp counts as one level.
- `Text collision`, `Label attribution` and `Text readability` measure a
  callout's string rather than its leader line.
- `Label attribution` reads an annotation at the anchor its leader points to,
  rather than at the string. A leader drawn to the wrong curve still fails.
- `Label attribution` no longer judges a panel title, axis label or colorbar
  label as a direct label.
- `Axis redundancy` requires the panels to share limits, scale type and axis
  title before it calls a tick column repeated.
- `Clipping` recognises off-view ticks on a child axes, so `secondary_xaxis`
  and `secondary_yaxis` no longer report them as clipped text.
- `Colormap kind` classifies a ramp before the 8-bit round trip.
- Auditing one figure twice returns one verdict, and a gate called on its own
  reports what `audit` reports.
- `audit_api.py` matches a reported name with lookarounds rather than `\b`, so
  a parameter change can be written down at all.
- `Line weight` no longer raises TypeError on an `EventCollection`, which
  reports one linewidth where every other collection reports a sequence. A
  raising non-advisory gate is a hard fail, so a spike raster failed on a defect
  in the checker.
- `Label attribution` no longer counts a series' own companion marks as a rival.
  Censoring ticks drawn along a survival curve sit 0px from it by construction,
  so no placement of a direct label could clear them.
- `docs/images` carries the eight figures this cycle added to the corpus.
- The home page's card icons render at 1.5rem. They are inline `<svg>` with a
  viewBox and no width or height, which SVG defaults to 100%, so each one had
  been taking the full width of its card.
- The release bump no longer requires `^## Unreleased$` on the bump that opens
  the next development cycle. `exclude_bumps` on that entry; the release bump
  still refuses to run without notes.
- `uv.lock` is a bump entry, anchored across its `name` and `version` lines.

### Why it changed

**The release procedure runs as written, and the version moves in five files
rather than four.** Both halves are defects that only ever ran on a release
commit, so nothing exercised them until 0.8.0 was being cut.

Every `[[tool.bumpversion.files]]` entry applied to every bump, so the
changelog's `^## Unreleased$` was required by the bump that opens the next
development cycle as well as by the one that cuts a release. That bump runs
immediately after a release, when the heading has just been renamed to the
version and the next notes do not exist, so it failed every time it was run.
0.7.0 is what that cost: its cycle never opened, the tree kept reading `0.7.0`,
and 0.8.0 could not be cut with the documented command.

`uv.lock` records the project's own version and nothing wrote it, so it still
read `0.7.0` after 0.8.0 shipped. That one was not cosmetic. Any command that
syncs the environment rewrites that line to match `pyproject.toml`, and a bump
refuses to start on an unclean tree, so the version site nobody maintained was
blocking the command that maintains the rest. It needs anchoring rather than a
plain search: the lock names a version for every package in the graph, it is
sorted by name, and it currently carries annotated-types 0.8.0, ast-serialize
0.6.0 and mdurl 0.1.2, all versions this project has shipped. An unanchored
search cutting 0.8.0 would have found annotated-types first and pinned a
dependency to a version that does not exist.

**A string is iterable, so a `venue` passed positionally was accepted.** It
landed in the `context_axes` slot, was iterated into a frozenset of axes ids
rather than raising, and the figure was measured at the wrong page width: a
wrong verdict, reported green, from an argument order. Keyword-only is the only
shape in which that call cannot be written.

**The gate that requires this to be written down could not be satisfied.**
`audit_api.py` matched a name griffe reported with `\b` on both sides, and half
the names it reports cannot clear that: a parameter change comes back as
`audit(context_axes)`, and a `\b` after the `)` asks for a word character next
to it, which no sentence puts there. So the keyword-only change above failed CI
with the section naming every one of the five parameters. Eight releases passed
because griffe had only ever reported bare names like `GATES` and `delta_e`,
which end in a word character. Lookarounds instead, which keep what `\b` was
there for: `delta_e` still does not match inside `delta_error`.

**Most of the fixes above are one round of false positives, found by putting
two constructs into the corpus that were not in it.** An annotation drawn with
a leader line and a secondary axis between them exposed six rows that failed
correct figures, and the pattern in all six is the same: a gate read an
artist's window extent, or an rcParam, or a quantised colour, and took it for a
fact about the figure when it was a fact about how the measurement was taken.

An annotation's window extent spans its text and its arrow together, so a
one-character label measured 285 points wide and ordinary annotated figures
failed all three text rows. Drawing a leader line is the remedy
`Label attribution`'s own `[FIX]` and `docs/gates.md` both offer, and taking it
could not discharge the row: a leader exists to set the string away from the
ink, so the string was measured nearer whichever curve lay in between. Two
quantities in different units whose ticks happened to coincide were told to use
`sharey`. `Contrast stack` called `float()` on an array, raised, and the raising
gate became a hard failure. `winter` and `Wistia` failed on quantisation
artifacts of about 0.001 OKLab, amplified by their narrow lightness spans.

**Auditing one figure twice returned two verdicts, and it is the same
measurement error one level up.** `examples/demo.py` builds and reports inside
`plt.style.context` and hands the figure back with the context closed, so a
caller who audited the returned object was measuring somewhere else. `demo` and
`encoding` printed all-PASS from inside their own builders and failed the sweep
that audited them a moment later.

The mechanism is not a family fallback. `font.family` is captured into each
Text artist's FontProperties at construction and does not move; the list that
`serif` resolves through is not captured. The sheet leads `font.serif` with STIX
Two Text and matplotlib's default leads it with DejaVu Serif, so the same label
at the same nominal size measured 100.0 px instead of 82.0.
`constrained_layout` re-solved against the wider tick labels and moved the axes
9 px, the annotations are anchored in data coordinates and did not follow, and
`Label attribution` read a label as nearest a curve that is not its own.

Pinning the rcParams a measurement depends on is the same move `MEASURE_DPI`
already makes for resolution, and it is the second half of one bug class: a
measurement read against a knob nobody pinned. The record is taken at the first
audit because there is no hook at construction, so a figure whose first audit
happens outside its sheet records the wrong baseline and is then wrong
consistently rather than differently each time.

### Changed

- `audit(context_axes)`, `audit(venue)`, `report(context_axes)`,
  `report(venue)` and `report(suggest)` changed to keyword-only. A `venue`
  passed positionally landed in the `context_axes` slot, where a string is
  iterable and so was accepted silently, and the figure was then measured at
  the wrong page width.
- `audit_api.py` matches a reported name with lookarounds rather than `\b`.
  The parameter names griffe reports end in `)`, which `\b` cannot follow, so
  the gate could not be satisfied for a parameter change by any wording. It is
  the first such change this project has made.

### Added

- `check_palette.cmap_kind_rgb` and `check_palette.cmap_back_travel_rgb`
  classify a ramp from float sRGB. The hex-taking `cmap_kind` and
  `cmap_back_travel` are unchanged.
- Two gallery figures, `gallery-callout` and `gallery-secondary-scale`,
  carrying the two constructs that exposed most of the fixes below: an
  annotation drawn with a leader line, and a secondary axis. The corpus is
  thirteen figures.

### Fixed

- `Contrast stack` no longer fails a figure that uses matplotlib's per-point
  alpha. `float()` raised on an array and the raising gate became a hard
  failure. An alpha ramp now counts as one level, because a continuous
  encoding is one decision the reader resolves.
- `Text collision`, `Label attribution` and `Text readability` measure a
  callout's string rather than its leader line. An annotation's window extent
  spans text and arrow together, so a one-character label measured 285 points
  wide and ordinary annotated figures failed all three rows.
- `Label attribution` reads an annotation at the anchor its leader points to,
  rather than at the string. Drawing a leader line is the remedy the row's own
  `[FIX]` and `docs/gates.md` both offer, and taking it could not discharge the
  row: a leader exists to set the string away from the ink, so the string was
  measured nearer whichever curve lay in between. A leader drawn to the wrong
  curve still fails.
- `Label attribution` no longer judges a panel title, axis label or colorbar
  label as a direct label.
- `Axis redundancy` requires the panels to share limits, scale type and axis
  title before it calls a tick column repeated. Two quantities in different
  units whose ticks coincide were being told to use `sharey`.
- `Clipping` recognises off-view ticks on a child axes, so a `secondary_xaxis`
  or `secondary_yaxis` no longer reports them as clipped text.
- `Colormap kind` classifies a ramp before the 8-bit round trip. `winter` and
  `Wistia` failed on quantisation artifacts of about 0.001 OKLab, amplified by
  their narrow lightness spans.

## 0.8.0 — 2026-08-18

### What changed

- `delta_e` **changed** what it returns: CAM02-UCS ΔE, not OKLab ×100. Same
  name, same signature, different number, and the sharpest edge in this release.
- `oklab_distance` was **added**, returning exactly what `delta_e` returned
  before.
- `linear_to_cam02ucs` was **added**: a stdlib CIECAM02, held to colorspacious
  within 1e-9 on identical XYZ.
- `CVD_TARGET` **changed** 8.0 → **10.5**; `NORMAL_FLOOR` **changed**
  15.0 → **21.0**; `CMAP_WRAP_DE_MAX` **changed** 3.0 → **1.0**.
- All six cycle slots now clear all-pairs. Okabe-Ito's orange and yellow miss
  the new normal-vision floor at 20.75 against 21.0.
- `audit` draws at `MEASURE_DPI = 150` and hands the figure back on the dpi it
  arrived on. `check_ink` and `check_text_readability` do the same when called
  directly. No verdict changed at 150 dpi; verdicts at other authored dpi
  changed to match it.
- `DOCUMENT_TO_GATE_MAX` **changed** 0.92 → 0.93 → 0.998 → **1.009**.
- `getting-started.md` is **gone**, split across `tutorial.md`, `install.md`
  and `compatibility.md`. A link or bookmark to that page breaks.
- Added: `tutorial.md`, `install.md`, `cli.md`, `compatibility.md`,
  `docs/how-to.md`, and API-page entries for the 21 gate functions.
- Added: `tests/test_renderer_invariance.py`,
  `tests/test_external_style_corpus.py`, `tests/test_suite_balance.py`,
  `tests/test_tutorial.py`, `tests/test_how_to.py`.
- The declared `matplotlib>=3.8` floor is asserted against CI's matrix.
- Seven unused markdown extensions removed from the site config;
  `navigation.tabs`, `sections`, `path` and `footer` set; nine pages carry
  their own meta description.
- Corrected: `design.md`'s "0.988 specificity" credit, the Science type floor
  (retracted, it publishes none), PNAS's 6pt (one requirement in two units, not
  two floors), a blank panel's furniture reading, and the mermaid diamond on
  `gates.md`.

### Why it changed

**The separation gates measure in CAM02-UCS instead of OKLab, and both floors
moved.** This is the largest correctness change the project has made and it
changes verdicts, so it is first.

`delta_e` returned OKLab Euclidean distance ×100 and the two separation floors
were quoted in it. OKLab was fitted for hue uniformity and never calibrated
against discrimination data, so a distance of 8 in it had no referent: there was
no measurement anyone could look up saying what a reader does at 8, which meant
`CVD_TARGET = 8.0` was a preference wearing a citation's clothes. Worse, the CVD
rows measured that uncalibrated distance *between colour-blind simulations* —
coordinates OKLab was never fitted for at all.

Measured against colorspacious (CAM02-UCS + Machado) over 79 800 pairs the
validator would accept as series slots, the old metric ranked pairs correctly
(Spearman 0.964, ROC AUC 0.988) but its operating point did not: specificity at
the shipped floor was **0.786**, so about one pair in twenty that the gate passed
an independent implementation called too close, concentrated in violet (12.8%)
and blue-violet (11.7%). The same measurement now reads **0.988**.

- `delta_e` **changed** what it returns: CAM02-UCS ΔE, not OKLab ×100. Same name,
  same signature, different number. A caller comparing its result against a
  hard-coded threshold gets a wrong answer silently, which is the sharpest edge
  in this release.
- `oklab_distance` was **added**, returning exactly what `delta_e` returned
  before, for callers who need the old scale.
- `linear_to_cam02ucs` was **added**: a stdlib CIECAM02, held to colorspacious
  within 1e-9 on identical XYZ by `tests/test_colour_space_oracle.py`.
- `CVD_TARGET` **changed** 8.0 → **10.5** and `NORMAL_FLOOR` **changed**
  15.0 → **21.0**. Both were re-derived from Stone, Szafir & Setlur (2014), not
  rescaled: the per-pair ratio between the two spaces runs 1.16 to 2.02, so no
  single factor converts them.
- `CMAP_WRAP_DE_MAX` **changed** 3.0 → **1.0**, which is now one JND rather than
  a number picked between two clusters.

Two consequences worth knowing before you upgrade:

**All six cycle slots now clear all-pairs.** The guide said five, because the
sixth pair measured 7.9 against a floor of 8. In CAM02-UCS the worst all-pairs
view is a *different pair* — `#0072B2` vs `#CC79A7`, at 12.8 against 10.5 — and
it clears. Scatter and small multiples may use the whole cycle. This is the only
place 0.8.0 gives more room rather than less.

**Okabe-Ito's orange and yellow miss the new normal-vision floor**, at 20.75
against 21.0, the one miss out of that set's 28 pairs. The floor was derived
without reference to any palette, and yellow is one of the two colours
`figure.mplstyle` already drops from its cycle. Arriving at that independently is
the strongest evidence these floors have, so the result is pinned in a test
rather than smoothed away.

**The composition gates measure at a fixed resolution, `MEASURE_DPI = 150`.**
Half of `check_figure`'s thresholds are pixel counts, and a pixel count is a
measurement only when the resolution is pinned. It was not: the gates drew at
`fig.dpi`, which is whatever the author set, whatever sheet is in effect, or the
authored value times the device pixel ratio of an attached display. Audited
across 100/150/200/300/600 dpi, the eleven gallery figures moved **34 rows and
flipped one**. `orbit`'s ink fraction ran 0.13 at 100 dpi down to 0.04 at 300
and out of the band at 600, because a mark's antialiased fringe is a fixed
number of pixels wide and so a shrinking share of a mark that grows with the
resolution. The figure never changed; only the knob did.

- `audit` now draws at `MEASURE_DPI` and hands the figure back on the dpi it
  arrived on. `check_ink` and `check_text_readability` do the same when they are
  called directly, so a gate called on its own reports what `audit` reports.
- 150 is the number every pixel threshold was already calibrated at, so no
  threshold moved and no verdict changed at 150 dpi. Verdicts at other authored
  dpi changed to match it.
- `tests/test_renderer_invariance.py` sweeps that range and requires every row
  identical down to the message, and puts the old behaviour back to check the
  sweep can still see it.
- One documented number was wrong as a result and is corrected: a blank panel's
  furniture does not always measure inside the ink band. Furniture is a
  perimeter and a panel is an area, so at `MEASURE_DPI` the blank half of a
  3x1.5in pair reads 0.03, inside it, and the blank half of a 6x3in pair reads
  0.01, under it. Only the first is caught by asking whether anything was drawn,
  which is the mechanism the guide describes.

**The composition gates are now measured against material this project did not
author.** `tests/test_external_style_corpus.py` builds three neutral figures
under each of matplotlib's 28 shipped style sheets (seaborn's, Tableau's,
Petroff's, ggplot's, FiveThirtyEight's, Solarized's), holding the content fixed
so styling is the only variable. Four of those styles carry a ground-truth label
from their own authors, being published as accessible under colour vision
deficiency, and **none of the four is rejected** by the colour gate while **21 of
the 24 unlabelled styles are**. Solarize_Light2 is the corpus's one WCAG text
failure, and the two presentation styles are its two clipping failures.

The negative result from the same sweep is pinned beside it: `Style sheet` and
`Fonts` fire on **28 styles out of 28**. Neither is measuring the figure. The
first asks whether this project's sheet is in effect and the second asks for
Type 42 embedding that no stock style sets, and neither should ever be counted
as evidence that these gates discriminate.

**The suite's balance is a number now, with a ceiling on it.**
`tests/test_suite_balance.py` classifies every test module as measuring the
tool, checking a document against the code, or release plumbing, and gates the
document-to-gate ratio. It arrived at a ceiling of 0.92 reading **0.910**;
before the two sweeps above it read 0.977, which is the shape of the criticism
that prompted this: the documentation tests had very nearly caught the tool.
Raising the ceiling means writing the measurement the prose is standing in for,
or arguing a module is classified wrong. The documentation work below moved it
four times under that rule and ended by inverting it; the final reading is
recorded there.

**The declared matplotlib floor is checked against CI's matrix.**
`matplotlib>=3.8` was a support claim that nothing verified was ever run. It is
true (`ci.yml` pins a 3.8.4 leg), and it is now asserted, so raising the floor
without moving the leg fails rather than quietly shipping a claim no test has
touched.

Documentation, unchanged from what was already here:

**The documentation is restructured by Diátaxis, one mode per page.** The split
before this was by audience, author against maintainer, which left four modes on
one page: `getting-started.md` was an install how-to, a tutorial, a requirements
reference and an explanation of the API contract at once. `gates.md` had the CVD
sweep rationale welded into its reference table, and `how-to.md` carried a
21-row reference table. The site now splits by what the reader came to do:

- Tutorial: `tutorial.md`, new. One path, no alternatives, every transcript
  captured from running the steps in a clean directory.
- How-to: `install.md`, new, and `how-to.md`, task-titled.
- Reference: `gates.md`, `cli.md` and `compatibility.md`, the last two new, and
  `api.md`.
- Explanation: `design.md`, `style-guide.md`, `choosing-a-form.md`,
  `gallery.md`.

**`getting-started.md` is gone**, split across `tutorial.md`, `install.md` and
`compatibility.md`, so a link or bookmark to that page breaks. Sentence-level
voice follows Google's technical writing course: second person, active voice,
one idea per sentence, key point first. The project history stays, quarantined
in the explanation pages where Diátaxis puts it.

Two claims were wrong and are corrected rather than carried over:

- `design.md` credited the colour oracle with "0.988 specificity". 0.988 was the
  ROC AUC of the superseded OKLab metric; that metric's specificity was 0.786,
  and `tests/test_colour_space_oracle.py` pins the current one above 0.95.
- The journal type floors, re-verified against the three publishers on
  2026-08-17. Science publishes no text floor at all, so the "5-7pt labels,
  6-8pt axes" it was credited with is retracted. PNAS gives 6pt and 2mm as one
  requirement in two units, not two floors, and also sets a maximum the docs
  never carried. Nature's 5pt minimum and 7pt maximum are confirmed. The
  retraction sweep found the same wrong sentence still in `check_figure.py`
  after both documents were fixed, which is what that sweep exists for.

Adding pages pushed the document side of the suite past the gate side and over
the ceiling. It was paid the way `tests/test_suite_balance.py` asks, with the
measurement the new prose stands in for: `tests/test_tutorial.py` builds each
tutorial step's figure and asserts the row transitions, so the tutorial cannot
silently stop working. Ratio 0.985 against a ceiling of 0.998 that did not move.

**Every site feature the config names is now asserted, and the ones that do
nothing are gone.** Seven markdown extensions were configured that no page used.
Six were inert; `pymdownx.emoji` read the `:::` of a prose mention of an
mkdocstrings directive as a shortcode and swallowed the rest of the line into a
code span. The config comment claiming "only what the pages actually use" is a
test now, failing on any extension nothing uses.

The nav had been Diátaxis since the restructure, but only the sidebar said so.
`navigation.tabs`, `sections`, `path` and `footer` put the four modes in the
chrome. A feature name is accepted silently, so each is asserted: the four that
emit markup in `tests/test_docs_site.py`, and `content.tooltips` in
`tests/test_docs_render.py`, which hovers an abbr and reads the painted tooltip.
`navigation.indexes` and `search.suggest` measured as no-ops and are not set,
with the reason written beside the list; `search.suggest` is a Material feature
Zensical does not implement at all. Nine pages carry their own meta description,
where all nine had shared one.

`DOCUMENT_TO_GATE_MAX` **changed** 0.998 → **1.009**, and the documentation side
is now the larger of the two: 1.0088 measured, 4919 document lines against 4876
gate lines. Both additions that moved it found a live defect, which is the
payment that file accepts.

**The site is themed, and the home page's card grid renders on GitHub too.**
`zensical.toml` swaps the default book-open glyph for a fence logo and
`palette.css` adds the accent underline tint for `fg-blue` and `fg-sky`. The
card grid used Material-specific syntax, a `markdown`-attributed `div` plus
`:lucide-*` shortcodes, which GFM does not parse: markdown inside an HTML block
is passed through raw and the shortcodes are unknown to it, so the whole block
rendered as literal text on GitHub. It is raw HTML with inline lucide SVGs now,
which is cards on the docs site and a clickable link list on GitHub.

**The mermaid diamond on `gates.md` says what it meant to say.** mermaid 11
renders a literal `\n` in a quoted diamond label instead of breaking the line,
so the `need` node used `<br/>`. `tests/test_docs_render.py` measures the
diagram's painted labels, so the defect cannot ship again.

Earlier in the same cycle, before the restructure:

**The docs say which import line a given install wants.** 0.7.0 moved the
installed modules into a package, and the two indexes do not publish in the
same hour: conda-forge follows PyPI through the feedstock's autotick bot, so
for a while after each release `conda install` hands back the release before
it. On the day 0.7.0 shipped that was 0.6.0, whose modules are flat and whose
import line is the vendored one. The README and `compatibility.md` name the
version each import line belongs to, and how to read which one you got, rather
than presenting the two install routes as interchangeable.

**The vendoring instructions cover `suggest_fixes.py`.** They copied three
files and named two scripts while the README advertised a third, so the route
the docs call the default was the one route with no way to reach `suggest`. It
is a fourth `cp`, marked optional, beside a sentence saying what a copy without
it loses and what `check_figure.py` genuinely cannot run without.

**`py.typed` is documented where a caller would look for it.** It shipped in
0.7.0 and the release notes were the only place saying so.

**The gates page names the row a crashed gate produces.** The audit stopped
losing itself to one raising gate in 0.7.0, and the row it reports instead
is a row about the checker rather than about the figure, which is a thing a
reader of that page has to be able to recognise.

**The release procedure in `CONTRIBUTING.md` is the one that was followed.** It
still said `bump minor` cuts a release, which stopped being true when the tree
started carrying a development version: `bump dev` cuts, and `bump minor` opens
the next cycle. Both bumps tag, `release.yml` triggers on any `v*` tag, and its
version guard compares the tag against the project rather than judging the shape
of either, so the cycle-opening tag is one that would publish a development
version to PyPI if it were ever pushed. The section says that, and it says that
the tag goes on the merged commit, which is where v0.7.0 sits and is not where
the bump put it.

**One copy of the API promise.** It was in the README and on the
getting-started page verbatim, 1246 characters each, in a repository whose docs
site is built on symlinks so that no page is a second copy of another. The docs
site has the statement, now on `compatibility.md`; the README has the two
sentences a reader of the PyPI page needs and a link.

**There is a how-to page, and it is the one the docs did not have.** Every page
on the site explained: `gates.md` what a row measures, `style-guide.md` what was
measured to land on the threshold. Nothing said what to type. A reader whose
build had just gone red on `Type size` had a 666-line essay and a table of
constants to work from, while `report(fig, suggest=True)` had been printing the
remedy for that row since the marks were split, undocumented anywhere a reader
would look. `docs/how-to.md` is the recipes: printing the remedies, the row
table with a first move for each of the 21, gating a suite, gating a palette
from a toolchain that is not Python, placing at a fraction of the content
width, alt text, reading one row, moving a threshold.

`tests/test_how_to.py` runs it. The row table is re-derived from `GATES` and
`REMEDIES` rather than proofread, the quoted scales are recomputed, the quoted
CLI output is the CLI's. Writing it found two defects in its own prose before
the page shipped: a paragraph warning about a difference between `not s` and
`s is False` that does not exist, since `"warn"` is truthy, and a REPL block
quoting `page_scale` as `1.380138888888889` when the value is a `numpy.float64`
and prints as `np.float64(...)`.

**The API page documents the 21 gate functions.** They were exempt as a class,
on the argument that `audit` runs them and `gates.md` carries their thresholds.
What that left was 21 public callables whose signatures appeared nowhere, so
calling one meant reading the source to find out that some take a renderer.
`check_colormap` had no docstring at all, which is why it could not have been
added without writing one. `test_the_page_documents_every_gate_in_order` keeps
a gate added later from joining a blind spot instead of a page.

**What gating the how-to page cost, and what paid for it.** The page arrived
with claims the doc suite could not read. A REPL block is Python interleaved
with output, so `ast.parse` called a correct example a syntax error;
`python_statements` splits a session with `doctest` and parses each source,
and every prompt has to come back as an example so a block cannot pass by
having nothing left in it. A sentence about a snippet names what the snippet
bound, so `ok`, `s` and the predicates over them now resolve against the names
the corpus' own examples assign, parsed rather than listed. `float()` resolves
as a builtin call, `numpy.float64` against numpy, and `adjacent` against the
`choices=` its flag is declared with. `status` came out of the unresolved
ledger: it resolves now, for a reason.

The link check in the docs job was reading `../api/#the-gate-functions` as a
path and asking the filesystem for a directory named after the anchor. It
splits the fragment off, resolves the page, and then checks the anchor exists
on it, which is a check the old version could not make at all: a link into a
section somebody renamed used to land on the page and scroll nowhere.

`test_ink_coverage_does_not_call_a_sparse_panel_empty` had built a panel
measuring 0.0198 on matplotlib 3.8 and 0.0216 on 3.11, either side of the 0.02
floor, so one supported matplotlib passed it and another warned. The figure now
states its own weights and asserts its margin. That is a test defect rather
than a gate defect, and finding it exposed a real gap: nothing anywhere
asserted that a row's *number* is the quantity its name claims. The ink
fraction is now measured against a rectangle of known coverage, the
furniture-only reading is pinned at two panel sizes, and the mark-ratio, type,
line-weight, overplotting and alpha rows are asserted on what they print.
`DOCUMENT_TO_GATE_MAX` **changed** 0.92 → **0.93**, moved by less than the
measurement written to pay for it.

## 0.7.0 — 2026-08-03

### What changed

- Installed, the checkers are a package. `import check_figure` no longer
  resolves; `from figure_gate import check_figure` does. The console scripts
  `check-palette` and `check-figure` are unchanged, and vendoring is untouched.
- `py.typed` ships. The style sheet installs to `figure_gate/figure.mplstyle`.
  An install that named the sheet by its old path has to say the new one.
- `pip install -e .` no longer works on a clone; `[tool.uv] package = false`
  records that.
- **New gate: `check_banking`**, advisory, with `BANKING_SLOPE_MAX = 10.0` and
  `BANKING_MIN_POINTS = 8`. `GATES` gained a row and every row after
  `Line weight` moved down one, so `audit()` returns 21 rows and not 20. This
  breaks anything indexing that tuple rather than reading it by name.
- The remediation marker `  <- ` became two marks, `[FIX]` and `[WHY]`.
- `SERIES_ENCLOSED_FRAC = 0.7` **added**: a fill holding that share of another
  series' ink is that series' band, rather than a rival, and a band no longer
  has to be labelled to be recognised.
- `MACHADO` and `simulate_anomalous` **added**, with `ANOMALOUS_SEVERITIES`.
  The separation row takes the worst over them alongside dichromacy and names
  the severity its verdict came from.
- `scatter_diameter_pt` **added**. `s` is a squared diameter, not an area, so
  `Mark ratio` and `Overplotting` both report different numbers than before.
- Four gallery figures **added**: `gallery-uncertainty`, `gallery-counts`,
  `gallery-residual`, `gallery-density`. The corpus is eleven figures.
- `examples/gallery.py` and `examples/demo.py` are importable. The driver, the
  argv read and the exit are under `__main__`; the builders return their
  figures and write nothing with `OUT`/`out` set to None.
- A gate that raises reports its own row instead of losing the audit. An
  advisory that crashed warns; a hard gate that crashed fails.
- The tree carries a development version between releases (`0.7.0.dev0` here).
  `uv run bump-my-version bump dev` drops the suffix.
- Nine thresholds moved to module level. Values unchanged, so no verdict moves.
- Added: `tests/test_thresholds_are_constants.py`,
  `tests/test_alt_text_numbers.py`, and `RETRACTED_CLAIMS`.
- Corrected in alt text: the slope graph's `eleven of twelve rise`, the demo's
  `reaches 0.05 by epoch 6`, and the field's `28-step ... from (-1.9, 2.2)`.
- **Measured and not shipped:** a size-weighted separation gate. The finding
  ships as a test; the gate does not.
- CI runs the suite on macOS and Windows. The sdist config is an allowlist. The
  wheel excludes `audit_api.py`.

### Why it changed

**Installed, the checkers are a package: `from figure_gate import
check_figure`.** This is a breaking change on the install path and the reason
the next release is 0.7.0. Through 0.6.0 the wheel put `check_figure` and
`check_palette` at the top level of `site-packages` -- two of the most generic
module names a distribution could claim, on a namespace shared with every other
installed package. `import check_figure` no longer resolves; `from figure_gate
import check_figure` does. The console scripts `check-palette` and
`check-figure` are unchanged. `suggest_fixes` is new in this release and has
only ever been importable from the package.

Vendoring is untouched. The files stay at `skill/scripts/`, still import
nothing of each other at module scope, and a copied `check_figure.py` still
does `import check_palette` beside it -- the two sites that reach for a sibling
now try the relative import first and fall back to the flat one, so one file
serves both layouts.

Two things follow from the move. `py.typed` ships, so the annotations added in
the previous release are visible to a caller's type checker for the first time;
until now PEP 561 required every one of them to be read as `Any`, because the
marker has nothing to attach to when the modules are loose files. And the style
sheet installs to `figure_gate/figure.mplstyle`, beside the module that reads
it, rather than as a bare `figure.mplstyle` at the root of `site-packages` --
another generic name in a directory every distribution shares. A package
directory is already namespaced, so the sheet needs nothing around it: the
first location `_style_sheet` probes is beside the module, which is the
installed package on one route and a vendored copy on the other. An install
that named the sheet by its old path has to say the new one; the gate finds it
either way.

`pip install -e .` no longer works on a clone, and `[tool.uv] package = false`
records that. hatchling refuses editable installs when a `sources` entry
rewrites a prefix rather than removing one, which is what mapping
`skill/scripts` onto `figure_gate` does. Nothing in the suite needs the
installed package -- `conftest.py` puts `skill/scripts` on `sys.path` -- and
keeping the skill's own directory layout was worth more than the editable
install.

**A gate that raises no longer loses the audit.** `audit` ran its twenty-one
gates in a list comprehension, so one exception anywhere propagated and the
caller got a traceback instead of the twenty rows already measured. Each gate
is now called inside a `try`, and a gate that raised reports as its own row,
with the exception in the detail and a note that the defect is in the checker
rather than in the figure. The verdict follows the gate's own severity: an
advisory that crashed warns, a hard gate that crashed fails, because a gate
that measured nothing has not cleared the figure. No gate is known to raise --
twenty adversarial figures, including 3D, polar, all-NaN, infinite and
zero-sized ones, found none -- but `matplotlib>=3.8` has no upper bound and
these gates read deep internals.

**The version between releases says so.** It is `0.7.0.dev0` here, and the last
step before tagging is `uv run bump-my-version bump dev`, which drops the
suffix. The tree used to carry the version of the release that had already
happened, so `uv build` on a checkout ahead of v0.6.0 produced a
`figure_gate-0.6.0` wheel that was not the 0.6.0 on PyPI. Releases build from a
tag on a clean checkout and were never affected.

Two things the bump config said and did not do. Its `## Unreleased` search was
unanchored, so cutting a release rewrote every mention of that string in the
file and not only the heading: the 0.6.0 notes explain the gate that requires an
Unreleased section, and shipped saying a missing `## 0.6.0 — 2026-07-30`
heading. Those two sentences are repaired here and the search is anchored to a
line of its own. And `message = "chore: release {new_version}"` sat under
`[tool.bumpversion.parts.dev]`, a table where nothing reads it, so both releases
cut with this config carried the stock `Bump version: X → Y` the key exists to
replace. `tests/test_version_sites.py` holds both, and holds the changelog to
having no release heading buried inside a sentence.

**The source distribution lists what it is instead of what it is not.** The
sdist config was a blacklist of agent-scratch paths and it had a hole:
`.superpowers/` is neither tracked nor gitignored, so a local `make dist`
shipped a dozen task briefs and review diffs, along with any other untracked
file lying in the tree. It is an allowlist now, and `.superpowers/` is
gitignored. Releases were never affected, for the same reason as above.

**`tests/test_docs_site.py` reads the repository, not the working tree.** It
walked `docs/` off the filesystem, and `.gitignore` carries
`docs/superpowers/`, so a maintainer with design notes on disk got five
failures naming files that are not part of the project while CI stayed green.
It asks `git ls-files` now, and falls back to walking the filesystem where
there is no git to ask, which is how the suite keeps running from an unpacked
sdist.

**CI runs the suite on macOS and Windows.** One leg each, on the newest
supported Python and matplotlib; Linux still carries the version matrix. Font
resolution is the most OS-dependent thing `check_fonts` touches and every run
until now was on one Linux image.

**Every function in the three modules is annotated, and the API page renders
as a reference.** The 19 documented callables carry Google-style
`Args:` and `Returns:` sections, so each entry on the page is a signature and
two tables rather than three paragraphs. `check_figure.py` and
`suggest_fixes.py` gained `from __future__ import annotations`;
`check_palette.py` gained it too, which is what keeps `tuple[float, float,
float]` from being evaluated on the 3.8 the file still claims. The 21 gates
and every private helper are annotated as well, so the whole of
`skill/scripts` type checks rather than the documented surface of it.

Annotating found one wrong claim. `check_palette.check` documented `status` as
True or False, and the contrast row has returned `"warn"` since it became
advisory. The docstring now says what the function does, and the return type
says it too.

`Gate.func` was annotated `object`, which is not callable, and `audit` calls
it. It is now `Callable[..., tuple[bool | str, str]]`, and `Gate.needs` is
`tuple[str, ...]` rather than a bare `tuple`.

**The API gate stopped existing twice.** `ci.yml` carried an inline copy of
`skill/scripts/audit_api.py`, and the two had drifted: the copy accepted six
changelog verbs where the script accepts twelve, missed an `Unreleased` section
that was last in the file, and had no branch for griffe being absent. A release
note saying a symbol "gained" a row passed `make audit-api` and failed CI. The
job now runs the script, which is the copy with tests.

`suggest_fixes` joins the compared modules. It was in neither roster, so
`suggest` was advertised as public and covered by nothing. Comparing it against
a tag older than the file needed a new branch: a module with no history at the
tag is reported as new rather than as griffe failing to run.

The gate also reads the release's own heading, not only `## Unreleased`. The
release commit renames that heading to the version it cuts, in the same commit
that drops the `.dev` suffix, so the gate ran against an empty section and
failed every release carrying a break -- on the commit that had just written
the break down. It matches the heading to `pyproject.toml`'s version rather
than taking whichever section is topmost, so a paragraph in a shipped release
cannot stand in for a break made after it went out.

**What the API promises is now written down**, in the README and in the getting
started guide: every non-underscore name in the three modules, breakable by a
minor bump below 1.0, with the row *shape* rather than the row *count* being
what callers can rely on.

**The wheel does not ship release tooling.** `audit_api.py`, added this cycle,
compares this project's public API against its last tag and has no caller
outside this repository: it reaches the checkout through the `audit-api` target
in the Makefile and through its own test. The wheel excludes it, so the only
thing an install puts on the import path is the three modules a caller uses.

**The remediation marker became two marks, `[FIX]` and `[WHY]`.** A gate's
detail appended `  <- ` and everything after it was read, by the guide and by
`test_a_gates_message_either_names_a_fix_or_is_named_here`, as what to do. Six
clauses named no action. `check_line_weight` cited SIAM on strokes under a
point, `check_banking` cited Cleveland on 45 degrees, `check_colormap`'s
qualitative-on-image branch explained that an image puts every category beside
every other, the normal-vision floor said two hues are hard to tell apart, and
`check_contrast_stack` and `check_series_color` each had a branch doing the
same. All six are true and none is a fix, so the test counted six explanations
as six routes to a fix, and the count of gates that route the reader was wrong
by six.

`[FIX]` now introduces an action and only an action; `[WHY]` introduces the
reason the row fired. A detail may carry both, in that order, which is what
keeps `check_colormap`'s existing cut at the fix mark taking the whole
clause when it quotes a palette row. The marks are words rather than glyphs
because the arrow never said which of the two it was introducing, and splitting
it against a tilde would have put the distinction on one character in a wall of
detail text; `[FIX]` and `[WHY]` read against the `[PASS]`/`[FAIL]` the report
already prints. The six converted clauses gained a real action each: a minimum
linewidth computed at the figure's own scale, the panel aspect, an explicit
color per series. `test_a_reason_clause_never_stands_in_for_a_fix` is the new
direction, and it fails a gate that explains without routing.

**Four gallery figures, added for the rows that had never measured anything.**
Every gate returns a detail string, and reading all 21 of them across the seven
figures showed five rows passing without having run the code that decides: no
figure drew a confidence band, a bar, a diverging colormap, a signed contour set
or a `scatter`, so `_encloses`, `check_form`'s `BarContainer` branch, the
diverging arm of `cmap_kind`, `check_contour_dash` and `check_overplotting` had
each returned a clean row seven times over having seen nothing. A row that
passes by having seen nothing looks exactly like a row that passed.

`gallery-uncertainty.png` puts a direct label under a confidence band on a log
axis, and is the only figure in the corpus audited for a place rather than for
its canvas (`venue="neurips", placed_frac=0.75`). `gallery-counts.png` is bars
from a zero baseline with a `secondary_yaxis` relabel, which is the twin-scale
case `check_dual_axis` exists to permit. `gallery-residual.png` is a diverging
field with solid signed isolines. `gallery-density.png` is a `scatter` whose
mark area varies, so the overplotting row's radius-octave path runs rather than
its equal-radii shortcut, beside a hexbin of the same measurement at 40000
points. All eleven figures pass every gate.

**A confidence band on a log axis is its curve's band again.** `_encloses`
asked `Path.contains_points(pts, transform=t)`, which freezes the transform and
hands it to the C containment test — and that test applies its AFFINE part only.
On a log axis the band's outline was therefore tested at coordinates it does not
occupy, every point of the curve read as outside, and `_encloses` returned False
without raising. The band went back to being a rival for the curve it covers, at
0px from any label on that curve, so every direct label under a band on a
log-scaled figure failed `check_label_attribution`. Only the non-affine case was
ever wrong, which is why the linear fixtures beside it stayed green;
`Path.transformed` applies the whole transform, and the regression test is
parametrised over both scales.

**A band is now told from a rival by what it encloses, not by whether it was
labelled.** `check_label_attribution` skipped a filled collection unless it
carried a legend-visible label. The intent was right, since a confidence band
lies on top of the curve it belongs to and counting it as a rival ties every
direct label with its own curve at zero. The discriminator was not: labelling a
band for the legend is the normal reason to label one, and `plot(label=
"signal")` under `fill_between(label="95% CI")`, with "signal" printed on the
curve, returned "0px from its own curve and 0px from another". The label also
decided visibility rather than only rivalry, so an unlabelled band could drop a
panel below the two-series minimum and the gate skipped that panel outright.

Fills are harvested like anything else now, and the band relation is tested
where rivals are chosen: a filled region holding at least
`SERIES_ENCLOSED_FRAC = 0.7` of another series' ink is that series' band. The
threshold separates two measured shapes. Adjacent `stackplot` bands share a
dividing edge, so each holds part of the other's outline and they have to stay
rivals; the worst reading over 200 random stackplots, two to five bands each and
degenerate near-flat ones included, is 43.9%. A `fill_between` band over its
curve's whole range reads 100.0%. The residual is recorded rather than fixed: a
band covering part of its curve reads in proportion, 88.1% over nine tenths of
the range, and below the floor goes back to competing with the curve it belongs
to. The Label attribution row is unchanged on the seven gallery figures that
existed then and on `demo.py`.

**Constants quoted in prose are pinned against the code, not just the ones in
the table.** CONTRIBUTING.md has been telling contributors that a constant
written `` `NAME = value` `` is held to the code by the doc suite. That was true
of the gate table's threshold column and of nowhere else, and
`SERIES_ENCLOSED_FRAC = 0.7` in the paragraph beneath that table passed the
whole suite with a deliberately wrong value. Seventeen prose constants across
the documentation files are now checked the same way the column is.

**One oversized mark no longer sets the overplotting query radius for the whole
scatter.** `_contact_fraction` enumerated candidate pairs at `2 * r_max`. The
bound is correct, since `r_i + r_j` cannot exceed it, but a single large mark
inflates it for every other mark in the figure, and a highlighted point in a
large scatter is an ordinary thing to draw. Measured: 50000 uniform points at
r=3 with one r=40 among them produced 62 million candidate pairs in a 994MB
array, and 60000 points on a Gaussian cloud with one r=100 mark did not return
in 120 seconds. The gate is advisory, but it runs inside `audit`, so what it
takes down is the whole audit.

Marks are grouped by radius octave, so radii inside a group vary by under 2x and
a group is bounded by its own largest radius. The nearest member of a group is
tested exactly first, which settles almost every mark, and only a mark still
unhit whose nearest member lies inside `r_i + max(r_B)` needs a ball query. The
oversized mark becomes a group of one. Same answers, asserted exact against the
full pair enumeration over 24 random scatters spanning graded radii, a single
oversized mark, zero-radius marks and sub-pixel marks; the uniform-radii fast
path and the scipy-absent fallback are untouched. The three cases above now run
in 0.06s, 0.07s and 0.21s.

**The examples are importable, so the corpus can be measured.** `gallery.py` and
`demo.py` did their work at import: every figure built, all eight committed PNGs
overwritten, `sys.argv[1]` read as an output directory, the style sheet applied
to the importing process for good, and then `sys.exit`. That made the corpus,
which is the evidence every gate is checked against, the one thing hardest to
get at; `test_alt_text_numbers.py` worked around it by cutting each source at a
marker string and executing the prefix. The driver, the argv read and the exit
are under `__main__` now, the sheet is scoped to the builders, and the builders
return their figures and write nothing with `OUT`/`out` set to None. All eight
figures render byte-identical to the previous code.

**A size-weighted separation gate was built, measured, and not shipped.** The
intuition is sound: a hue pair that reads as two on a filled band ought to read
as one on a hairline, and a small target really does need more colour difference
than a large one. Stone, Szafir & Setlur (2014) measured how much, fitting the
noticeable difference as C + K/s over target sizes from 0.333 to 6 degrees of
visual angle. A gate multiplying `NORMAL_FLOOR` by that ratio warned on
`gallery-convergence` and on `demo.py` - on the Okabe-Ito cycle at the 1.6pt
stroke this project recommends.

That is not a threshold to tune, it is a unit error. The floors here are OKLab
dE x100 and the model is CIELAB, and measured over 20000 random pairs one OKLab
unit is a median 2.94 CIELAB. So `NORMAL_FLOOR = 15.0` is about 44 CIELAB and
`CVD_TARGET = 8.0` about 24, against the 10.4 the size model asks for at the
smallest size it was fitted at. The pair the gate flagged, Okabe-Ito's green and
sky blue, are 59.5 CIELAB apart - 5.7 times the requirement. The floors already
exceed what the size model demands at every size the model can speak to, and
publication line widths sit two decades below its fitted range, where
extrapolating an inverse-size fit produces a number nothing supports.

So the finding ships and the gate does not. `test_the_size_model_is_already_
inside_the_normal_vision_floor` pins the arithmetic, a second test asserts no
size-weighting helper was left behind with no caller, and the style guide states
the rule as a rule: a hairline is where a palette gets tested, so give thin
strokes the widest-separated slots. CONTRIBUTING says to drop a gate that
false-positives on the corpus, and this one did, on the corpus's own palette.

**Dichromacy is not the worst case, and the CVD gate was reading only
dichromacy.** Most colour vision deficiency is anomalous trichromacy - a cone
whose peak sensitivity is shifted rather than one that is missing - and
simulating the endpoint alone would be sound if the endpoint were the hardest
view. It is not. Measured over 240000 pairs of hues `check_palette.py` would
accept as series slots, 0.87% clear `CVD_TARGET` under dichromacy and miss it at
some lower severity, and dichromacy overstates separation by as much as 10.5 dE.
`#288ac6` and `#fd00db` is one such pair: 8.4 at dichromacy, 7.9 at severity 0.8,
and it passed the gate.

`MACHADO` ships Table 1 of Machado, Oliveira & Fernandes (2009) for protan and
deutan at severities in tenths, and `simulate_anomalous` reads it. The
separation row now takes the worst over `ANOMALOUS_SEVERITIES` alongside the
existing dichromacy reading and names the severity its verdict came from.

Three decisions here were settled by measurement rather than by assumption, and
each has a test.

- **The matrices belong on linear light.** The published table does not state a
  transfer function. Machado calibrates severity 1.0 against the same
  Brettel/Vienot dichromacy this file already uses, so the domain that
  reproduces it is the domain the table is written for: on 4000 random hues the
  severity-1.0 matrices land within a mean 2.84 dE (protan) and 2.44 (deutan) of
  `simulate` when applied to linear light, against 3.89 and 4.97 on
  gamma-encoded sRGB. Getting this backwards would have put an error of that
  size under every number the feature produces.
- **1.0 is left out of the sweep.** It is dichromacy, which `simulate` already
  covers with the matrices every number in the style guide was measured on.
  Reading it twice under two models would have moved published figures for a
  view already gated.
- **Protan and deutan only.** The repository already reports tritan without
  gating it, and this model's own reference implementation notes that it does
  not do tritanopia well. A tritan severity table would be spending credibility
  on the one form neither model is validated for.

The four matrices quoted in the suite were read off the authors' own page and
are asserted against the shipped constants, because the table is the whole
substance of this and a transcription slip would be a wrong answer wearing a
citation. The bundled cycle's worst adjacent pair reads 15.8 dE under the sweep,
which is what says the stricter reading is not a floor nobody can satisfy.

**New gate: banking to 45 degrees.** The aspect ratio has been in
`choosing-a-form.md` since that document existed and nothing measured it, which
is the shape of guidance this project exists to replace.

The failure is a resolution failure and it is measurable. On a saw wave whose
decay limbs alternate between two rates, one exactly twice the other: at
2.4 x 5.2 inches the two limbs land 1.6 degrees apart on the page and the
alternation cannot be seen at all; at 6.4 x 1.9 they land 10.6 degrees apart and
it is the first thing you see. Same data, same axes, same limits. Both numbers
are asserted in the fixtures, so a change that stopped the tall figure
collapsing the rates fails the test that calls it a defect rather than quietly
testing nothing.

`GATES` gained a row and every row after `Line weight` moved down one, which is
a break for anything that indexes that tuple rather than reading it by name;
`audit()` returns 21 rows now and not 20.

`check_banking` reads the median absolute segment slope of each panel's strokes
in display space, and is advisory. `BANKING_SLOPE_MAX = 10.0` is a factor of ten
either side of banked - a typical segment past 84 degrees or under 6 - which is
a panel essentially vertical or essentially flat over its own typical step. The
band was picked against the corpus rather than argued: the 14 series in
`examples/` that this gate reads span 0.19 to 2.95, so [0.25, 4] would have
fired on one of them and [0.1, 10] leaves the nearest legitimate case a factor
of 1.9 clear. The gallery test now asserts no banking warning, because an
advisory row does not fail a run and an over-firing advisory would have been
invisible there.

Four exclusions, each measured rather than reasoned into existence. A line with
`linestyle="none"` draws marks; the orbit figure's 168000-point cloud is one. A
fixed aspect is a statement about the data. Under `BANKING_MIN_POINTS = 8`
vertices is furniture rather than a rate, and the corpus has 24 such strokes. An
x that does not run one way is a parametric curve, where the typical slope is
not a rate of anything. Slopes come off the authored vertices and not the
densified stroke, because densifying makes every segment 2px and the median of
that measures the densifier.

**`step`, `stackplot` and contour sets are read now.** The last notes left these
three as geometry the attribution harvest does not reach, and each was unread
for its own reason.

`ax.step` keeps the points it was handed and draws a staircase through them, so
densifying `get_xydata` lays the harvested geometry along the diagonal chord of
every riser. Measured on a six-point square wave: 836 harvested points, 785 of
them on blank page. `_drawstyle_xy` runs the vertices through the `pts_to_*step`
helpers in `matplotlib.cbook`, which is what `Line2D` itself does, rather than
writing a second staircase that can disagree with the first. A test asserts
those helpers still resolve, because a rename upstream would not raise - it
would mean "this line has no drawstyle" and quietly revert every step plot to
its chords.

`stackplot` bands and contour sets carry paths and no offsets, so `_series_px`
returned None for them and the offsets branch was the only branch. `_path_px`
reads `Path.to_polygons`, not `path.vertices`, because the dummy vertex a
CLOSEPOLY carries and the jump a MOVETO makes are not points on the stroke -
the same bridging defect NaN handling exists to avoid, one level down.

Filled series are judged on containment rather than on distance to their
outline. `stackplot` hands neighbouring bands the same dividing edge, so on
boundary distance a label inside the upper band is exactly as far from the lower
band's outline as from its own and every stacked label reads as ambiguous.

A fill has to carry a legend-visible label to count as a series and a stroke
does not, which is the one asymmetry here and it is deliberate. A confidence
band lies on top of the curve it belongs to, so counting an anonymous
`fill_between` puts a competitor at distance zero from every direct label on
that curve. `stackplot(labels=...)` and a deliberate `fill_between(label=...)`
are series; `_child3` is a band bound to somebody else's line.

**A mark eclipsed by a mark that is not its nearest neighbour was not
overplotting.** The last notes named this as the case no 1-NN test reaches and
left it. Contact is `d < r_i + r_j`, and the `j` that minimises `d` need not be
the `j` that maximises `r_j`, so a mark clears its nearest neighbour and is
swallowed whole by a larger one further off. Measured on 60 marks - 40 small
ones in pairs 8px apart, each pair under a 120px disc centred 20px away - every
mark is in contact, 40 of them do not appear in the render at all, and
`check_overplotting` returned "no scatter overplotting" off a 33% reading.

Rendered coverage was the fix those notes proposed and it is not the one this
takes, because the predicate was already exact and only asked of the wrong
neighbour. `_contact_fraction` asks it of every neighbour. Where radii are
uniform the nearest one still answers it outright, since `r_i + r_j` is then a
constant and "some mark is within it" and "the nearest mark is within it" are
the same statement; that keeps the common case on one k=2 query, and a test
pins the two paths to the same number rather than trusting the argument. Where
radii differ, candidates come out of one range query at `2 * r_max`, which
cannot miss a touching pair, and each is filtered on its own two radii.

The numpy fallback got the same treatment, because CI installs no scipy and a
gate fixed only where scipy is present is fixed nowhere that matters. A short
size list is now tiled over the offsets the way a `Collection` cycles it, so
the radii the gate reads are the radii it drew.

**Readability was measured over page the label does not sit on.** The oriented
box landed in `check_collisions` and `check_text_readability` was left sampling
the axis-aligned block, which the last notes said out loud and left open. On one
45-degree 11pt string that block is 191.5 x 191.5, 36669 pixels, around an
oriented box of 239.5 x 31.3, 7505: four fifths of what was sampled belonged to
the label only through its bounding box. Six strokes laid in the empty
upper-left triangle, none of them touching a glyph, were reported as data ink
over 14% of the label's box.

`_oriented_mask` rasterises `_corners` over the sampled block, and both clauses
now read through it. The clutter fraction counts edge pixels inside the box
against the box's own area, and the contrast quantile draws from the same
pixels, so a dark field in a corner the label never reaches no longer sets the
verdict for a string on light ground. The mask is applied after the blur rather
than before, because the local average is what says whether a pixel is an edge
and a stroke entering from outside has to be compared against its neighbours out
there.

Upright labels are handed `None` and stay on the code path they were measured
on: `_corners` returns the axis-aligned box for them, so a mask would only shave
off the 1px ring the slice adds, and that is a number nobody measured. The same
strokes moved onto the glyphs still fail at 95%, which is what says the false
positive went without the gate going with it.

**Label attribution measured against strokes that are not on the page, and did
not measure against half the ones that are.** Two defects in the same gate,
both of them about what counts as a series.

- **A break in the data was bridged.** `_polyline_px` dropped non-finite
  vertices and then densified across what was left, which joins the two sides
  of every hole. A 100-point sine with `y[40:60] = nan` came back with 326
  invented points strung across blank page, and a label sitting in that gap was
  judged against a curve that is not there. Masked arrays arrive the same way,
  because `Line2D` fills a masked input with NaN on recache. Densifying per run
  of consecutive finite vertices fixes both spellings.
- **Only `ax.lines` was read.** A point cloud could not own a direct label and
  could not be the neighbour that made one ambiguous, so a label sitting on top
  of a dense scatter passed clean. `_series_px` now takes scatters too,
  recognised by carrying sizes, which is the discriminator `check_overplotting`
  already uses and which keeps `fill_between` from planting a phantom series at
  data (0, 0) off its single zero offset.

`step`, `stackplot` and contour sets were left unread here - `PolyCollection` and
`LineCollection` geometry rather than offsets, a different harvest than this one.
They are the first entry above.

**Text collision compared the boxes rotation left behind, not the boxes.**
`get_window_extent` returns the axis-aligned bounding box of the *rotated*
string. Measured on one 11pt label: 119.0 x 15.3 at 0 degrees, 15.3 x 119.0 at
90, and 94.9 x 94.9 at 45. That last one is five times the ink, and the extra
area is two right triangles nothing is drawn in. Two parallel 45-degree labels
with clear page between them were reported as colliding, which is the shape of
false positive that teaches people to skim the row.

`_corners` reconstructs the oriented box without private API or a rebuilt
transform: rotating a rectangle about any point sends its centre to the centre
of the result, so the centre of the rotated AABB is the centre of the oriented
box, and the unrotated extent supplies the sides. The reconstruction is checked
rather than trusted, and anything that does not round-trip to the extent
matplotlib reported falls back to the axis-aligned corners. `_overlap` is now
the separating axis theorem over four edge normals, which is exact for
rectangles and gives the old min/max answer whenever both boxes are upright.

`check_clipping` was left alone and a test says why. An AABB is the bounding
box of the oriented box's own corners, so its extremes are attained by real
corners of the label and a min/max test against the canvas gives the same
answer on either shape. Rotation costs that gate nothing. `check_text_readability`
sampled the axis-aligned block, and masking it to the oriented box was a further
change; it is the first entry above.

**The contrast clause read a smooth backdrop as its own average, through the
branch written to stop it doing that.** `_worst_backdrop` binned a label's box
on `pix // 8` and took the worst bin covering at least
`TEXT_BACKDROP_MIN_SHARE`. On a figure made of flat fills that is right. On a
smooth one an 8-cube splits the ramp into dozens of bins, none of them reaches
the share floor, and the function falls through to `pix.mean(axis=0)` with
nothing in the output saying it did. Measured on a viridis ramp under a 30x600
box: 76 bins, a 3.5% mode, a verdict of 4.25:1 exactly equal to the box mean,
against a true worst pixel of 1.34:1 and a true tenth percentile of 1.63:1. Its
own docstring named the mean as the wrong summary and the fallback returned it.

Contrast is defined per pixel, so the quantile was available directly and the
binning was only ever standing in for it. The gate now reports the contrast the
text holds over all but the worst tenth of its box, and there is no fallback
branch because no case reaches one. `TEXT_BACKDROP_MIN_SHARE` keeps its value
and its meaning: a backdrop covering a tenth of the box sets the verdict, a
handful of stray antialiased pixels does not.

`_contrast_field_255` vectorises the existing scalar helper rather than
restating WCAG contrast, and `test_contrast_field_agrees_with_the_scalar_helper`
walks a spread of colours through both so they cannot drift. All seven gallery
figures still pass, including the viridis field with 31 strings on it, which is
what says the stricter reading does not over-fire.

**`scatter(s=...)` is not an area, and two gates were built on the assumption
that it is.** matplotlib documents `s` as "the marker size in points**2". The
unit marker path is a circle of radius 0.5 scaled by `sqrt(s)`, so the drawn
diameter is `sqrt(s)` points and the drawn area is `pi * s / 4`. Measured, not
inferred: at 200 dpi `scatter(s=100)` and `plot(markersize=10)` each lay down
741 pixels of ink. `scatter_diameter_pt` now carries the conversion, and
`test_scatter_size_is_a_squared_diameter_not_an_area` pins it against
matplotlib rather than against a docstring.

- **Mark ratio reported 1.3x on two marks of identical drawn area.** The 4/pi
  bias the 0.3.0 notes describe was corrected on the `markersize` side and left
  standing on the `s` side, so the ratio it printed was wrong by exactly the
  factor that release set out to remove, on exactly the figures it named. Both
  operands now convert to the area of the disc actually drawn, and the row
  reports that area rather than a raw `s`.
- **Overplotting needed the marks to be roughly 1.8x past contact before it
  said anything.** Two errors compounded: the radius came from
  `sqrt(s / pi)`, 12.8% too large, and the comparison was `nn_dist <
  radius_px`, which is the condition for a mark's *centre* to be swallowed
  rather than for two marks to touch. A grid of 64 discs each overlapping its
  neighbours by a quarter of their diameter renders as one solid square and
  returned "no scatter overplotting". Contact is `d < r_i + r_j`, and the
  neighbour's own radius now comes from the index the query already returned,
  so a big mark beside a small one is judged on both.

A case no nearest-neighbour test can reach - a small mark covered by a large one
that is not its nearest neighbour - was left standing here and is the second
entry above.

**Alt text is swept for the numbers it states.** `tests/test_docs_match_code.py`
already held every description on the site to the string the example attaches,
so the page could not drift from the code. Nothing read either against the
picture, and three figures described something the code does not draw:

- the slope graph said `eleven of twelve rise`. All twelve rise, and always
  have: `after` adds a normal centred at 0.11 with a spread of 0.05, so a fall
  needs a draw 2.2 sigma low, and under seed 4 the smallest gain is 0.047.
- the demo said the Bayesian run `reaches 0.05 by epoch 6`. At epoch 6 that
  curve is at 0.115, and 0.05 arrives at epoch 6.9.
- the field said `a 28-step gradient descent path from (-1.9, 2.2)`. The loop
  runs 6000 steps from (-1.75, 2.15). None of the three numbers was the
  figure's, and one of them, 2.2, is the panel's x limit, so a resolver reading
  the sentence loosely would have called it correct.

`tests/test_alt_text_numbers.py` builds every described figure and sweeps its
description: each number either resolves against a count, limit, tick or extreme
the figure has, or names a computation that confirms it, or sits in a ledger with
the reason nothing can. The relational claims get checkers of their own, because
a number that is right about the figure and attached to the wrong curve is the
defect here. The three PNGs whose description changed were rebuilt so the
metadata a screen reader reads is the corrected text.

**A claim the last audit retracted was still shipping in a gate message.**
"ACM and Elsevier reject the submission" was corrected in the style guide alone;
`SKILL.md` and `check_figure.py` kept it, the module in the message printed under
every Type 3 figure. `RETRACTED_CLAIMS` in `tests/test_prose_claims.py` now holds
a retraction out of both documents and modules at once, with the wording to use
instead, because a retraction that lives in one file is one the next writer
copies back from another.

**The prose sweep went red the moment somebody wrote release notes.** 0.6.0
fixed a suite that failed at every tagged commit by putting `## Unreleased` in
the unresolved ledger. The ledger has a test asserting none of its entries
resolves, so the failure moved rather than went: it now fired on every commit
where the heading existed, which is every commit a maintainer writes notes in.
The heading is defined by the release process rather than by a document, exists
in exactly one of the two states, and now resolves in both.

**Every threshold is a module-level constant, as the README has said since
0.2.0.** Nine were not: the ink-detection cutoff, the two WCAG large-text sizes,
the numeric bold weight, the placement warning and the opaque-mark definition in
`check_figure.py`, and all three ordinal rows of `check_palette.py`, whose
categorical siblings have sat at module level throughout.
`tests/test_thresholds_are_constants.py` sweeps both modules for a comparison
against a literal, recognises the structural ones by shape, and requires the rest
to name a constant or a reason. Values are unchanged, so no verdict moves.

## 0.6.0 — 2026-07-30

### What changed

- The README is a landing page. The reference material moved to `docs/gates.md`
  and `docs/getting-started.md`, both authored pages named in `AUTHORED`.
  Nothing was duplicated in the move.
- `docs/api.md` **added**: `:::` directives read by mkdocstrings at build time,
  documenting fifteen functions. Eight of them gained a docstring.
  `tests/test_api_reference.py` holds the page to the modules.
- `PROSE_DOCS` is derived from git rather than listed: every tracked markdown
  file, minus `CHANGELOG.md` and `specs/`, which are exempt by a rule and not a
  list. Six resolver domains **added**, taking 229 unresolved spans to 23.
- Three tools **added** to CI: ruff's `DOC102`, `DOC202`, `DOC403`, `DOC502`;
  `griffe check` against the last tag, failing only when a break is not
  mentioned in the Unreleased section; and `codespell` with three ignore-words.
  `pymarkdownlnt` was measured and rejected.
- `uv run bump-my-version bump minor` rewrites `CHANGELOG.md`,
  `pyproject.toml`, `plugin.json` and `recipe.yaml`, commits, and tags `v<new>`.
  `CHANGELOG.md` is first in the file list and the order is load-bearing.
- `tests/test_version_sites.py` **added**, holding the bump config to the files
  it points at.
- `examples/demo.py` and `examples/gallery.py` take an optional output
  directory. The default is unchanged.
- The docs build installs `--only-group docs` instead of naming its
  dependencies inline.
- `make audit` **added**, with `specs/2026-07-30-standardized-docs-audit.md`
  recording what each check proves and what it does not.
- `conda/README.md` describes a submission that has happened rather than one
  that is planned.
- Em dashes removed from the README and the pages cut out of it.

### Why it changed

**The README is a landing page now, and the documentation is on the docs site.**
It had grown to 361 lines carrying both threshold tables, three install routes,
the usage examples, the retina history and the design notes, for a project that
has published a docs site since 0.4.0. Someone deciding whether to use this had
to read the reference material to find out what it was.

Nothing was duplicated in the move, which is the only version of this worth
doing. `docs/gates.md` is the one copy of the two tables and the roster prose;
`docs/getting-started.md` is the one copy of install, the two settings that need
your document's values, the usage examples and the requirements. Both are
authored pages in the sense `docs/gallery.md` already was, and `AUTHORED` in
`tests/test_docs_site.py` names them so that a page becoming a hand-maintained
copy still fails.

The gates that read the README read those pages instead. Eleven parsers and
seven roster-count claims were pointed at one file; the count claims now carry
the document each is made in, because the reason they exist is that one copy of
a claim gets updated and the others do not. `docs/api.md` had been sending
readers to tables on the home page that are no longer there.

**Em dashes are gone from the README and from the pages cut out of it.**

**Comments naming the README were swept.** A dozen of them cited it as the
source of a promise that had moved: three files and no install, the Python 3.8
claim the stdlib-only CI job exists to keep true, the test count
`tests/test_docs_render.py` explains its collection strategy against. One named
`_compares_all_pairs`, a function renamed to `_axes_all_pairs` long enough ago
that nothing in the repository still used the old name.

**The prose sweep failed on every release and nobody had run it on one.**
`CONTRIBUTING.md` tells a maintainer to write release notes under a
`## Unreleased` heading, and the heading resolver added in this cycle checks
that a heading named in prose exists. It does, right up until the bump renames
it to the version, so the suite went red at the tagged commit and green again
with the next change. The absence is correct and load-bearing: it is what makes
a release with nothing written about it stop before the tag. The span is in the
unresolved ledger with that reason.

**The documentation audit is a procedure now, not a memory.** It had been run
four times, each time reconstructed from the previous run's changelog entry, and
each run missed something the next one found: seven of eleven prose documents
unswept, a fourth version site nobody had listed, a docs dependency list that
existed twice. `make audit` runs every mechanical check in one command, and
`specs/2026-07-30-standardized-docs-audit.md` records what each one proves and
what it deliberately does not.

**The prose corpus is derived from git rather than listed.** `PROSE_DOCS` was
four hand-written paths; it is now every tracked markdown file, resolved through
the `docs/` symlinks and deduplicated, minus a historical class.
`CONTRIBUTING.md`, `SECURITY.md`, `conda/README.md`, `docs/gallery.md` and
`docs/api.md` were making unchecked claims about the code with the suite green.

`CHANGELOG.md` and `specs/` are exempt, by a rule and not a list. A changelog
entry saying `check()` returned `(rows, ok)` is accurate history — it did, until
0.4.0 — and sweeping it against today's modules would turn a correct record into
a failure whose only fix is to falsify it. Two tests keep the exemption from
being a hiding place: one names the documents the rule currently catches, and
one requires each of them to carry the date it is a record of.

Six resolver domains were added so the new documents could be checked rather
than excused: tracked files anywhere in the repository, markdown headings, TOML
tables and keys, dependency groups and distributions, CI job and step names, and
test-suite symbols. The first run over the full corpus left 229 unresolved
spans; the domains took that to 23, of which 22 are conda-forge's names or
placeholders and are in the ledger with the reason.

The twenty-third was a bug in the sweep rather than a defect in a document.
A span written with doubled backticks, which is how markdown shows a literal
backtick, matched as empty and reported `''` as an unresolvable claim. The
doubled form is matched first now and its contents swept in their own right.

The CI domain had to be written twice. The first version accepted any word of
five characters or more occurring anywhere in the workflow files, which resolved
the bare word `status` — the third field of a gate's row triple, nothing to do
with CI. A resolver that agrees with almost anything reports agreement with
nothing. It reads job ids and `name:` values only.

**Three tools, after checking whether any of this was already somebody's
library.** Ruff's `DOC102`, `DOC202`, `DOC403` and `DOC502` fail on a docstring
that names a parameter the signature does not have, or documents a return, a
yield or an exception the body never produces — the same defect class the
markdown sweeps look for, on a surface they cannot reach. The rules that flag an
absent section are not adopted: `DOC201` alone reports 59, and asks for a house
style this project does not write in.

`griffe check` compares both modules against the last release tag. It is not a
veto, because a 0.x project may break its API; the new CI job fails only when a
break is not mentioned in the Unreleased section. `check_palette.py` is meant to
be vendored by copy, so a renamed function does not break a resolver, it breaks
a file somebody pasted into their repository six months ago.

`codespell` reads the words, which nothing else here does. Three ignore-words,
each a term the documents are right to use: `vermillion` is the Okabe-Ito
palette's own spelling, `commun` is an abbreviated journal title, and `theses`
is the plural of thesis.

`pymarkdownlnt` was measured and rejected. It finds two things on the whole
corpus and misses the accidental-heading defect this project hand-rolled: given
a hex color wrapped mid-span, it reports a missing top-level heading and does
not notice the `<h1>` that was invented.

**The docs build carried its dependency list twice.** The build step ran
`uv run --no-project --with "zensical>=0.0.51,<0.1"`, which is the `docs`
dependency group written out again in a file nothing resolves against
`pyproject.toml`. It was correct only while the two happened to agree, and they
stopped agreeing the first time the build needed a package one of them did not
name: the group gained `mkdocstrings-python` for the API page, that line did
not, and CI failed with `No module named 'mkdocstrings'` after the same build
passed locally in an environment that already had it. `--only-group docs` now,
with three gates: the build step has to install the declared group and may not
name a package inline, the group has to contain the builder, and a page using
`:::` directives has to be matched by a handler in the group.

**The docs site has an API page, and it is not written by hand.** `docs/api.md`
is `:::` directives; Zensical's mkdocstrings extension reads the signatures and
docstrings out of `skill/scripts/` when the site builds, so a default shown
there is the default the code has. A hand-written reference would have been a
second copy of every signature, which is the drift `tests/test_prose_claims.py`
already exists to catch one level down.

Fifteen functions, chosen rather than swept: `audit`, `report`, `describe`,
`alt_metadata`, `page_scale` and `content_width_pt` from `check_figure`, and
`check`, `cmap_kind`, `cmap_back_travel`, `contrast`, `delta_e`, `simulate`,
`hex_to_linear`, `linear_to_oklab` and `relative_luminance` from
`check_palette`. The twenty gates are deliberately absent: `audit()` computes
the renderer, canvas and scale arguments they take, so calling one directly
means reproducing that, and what a caller needs from a gate is the threshold
and the failure condition the README tables already carry.

Eight of those fifteen had no docstring and now do. Writing them turned up a
stale one: `audit()` said `check_palette.check` "returns its pair the other way
round, as `(rows, ok)`", which stopped being true in 0.4.0 when the two were
made to agree. The README and `check()` itself both record the change; the
docstring at the call site was the copy nobody updated, and it was wrong for
two releases.

`tests/test_api_reference.py` holds the page to the modules: every public
callable is documented or named in `EXEMPT` with a reason, every directive
names something that exists, and every documented name has a docstring, since
`:::` on a bare function renders a heading over an empty block. Coverage is
what the tests are for -- a public function added to either module would
otherwise appear nowhere, with no build error, leaving an incomplete reference
that reads like a complete one.

**`conda/README.md` described a submission that had already happened.** It read
as a plan -- "that costs one manual submission to staged-recipes" -- while
`conda-forge/figure-gate-feedstock` had existed since 2026-07-30 and the
channel was serving 0.4.0. Anyone following it would have opened a second
staged-recipes PR for a package conda-forge already builds.

It now says where the package comes from, that the feedstock's own
`recipe/recipe.yaml` is the copy that builds and this one is not, and what
maintainer access does and does not change: the autotick bot produces the
version bump either way, and being a maintainer decides who merges it. The
admin-bot commands are written down, including
`@conda-forge-admin, please add bot automerge`, and the submission steps are
kept as a record rather than as instructions.

**One command moves the version.** It is written in four files and a tag, and
until now nothing wrote them together. 0.5.0 is what that cost: the bump moved
`pyproject.toml` and `skill/.claude-plugin/plugin.json`, and all three pytest
jobs failed on the release PR because `conda/recipe.yaml` still said 0.4.0.
`uv run bump-my-version bump minor` now rewrites `CHANGELOG.md`,
`pyproject.toml`, `plugin.json` and `recipe.yaml`, commits, and tags `v<new>`.
Pushing the tag still publishes; `release.yml` has not moved.

`CHANGELOG.md` is first in the file list, and the order is load-bearing.
bump-my-version writes each file as it reaches it rather than validating the
set first, so with the changelog last a missing `## Unreleased` heading leaves
the other three bumped on disk before it errors. First, it touches nothing. The
failure itself is deliberate: a release with no notes written for it now stops
before the tag rather than at the `no '## $version' section` check in
`release.yml`, which runs after the tag is already pushed.

`tests/test_version_sites.py` holds the config to the files it points at:
`current_version` against the project version, `tag_name` against what
`release.yml` triggers on, and each `search` pattern against the file it claims
to find it in. The last one is the reason the test exists. bump-my-version does
refuse to write a file whose pattern is missing, but only when someone runs it,
which is the moment a release is being cut. `CHANGELOG.md` is exempt from that
check, since `## Unreleased` is absent for most of the life of the repository
and present only once there are notes.

The two checks that caught the 0.4.0 recipe stay. What changes is their job:
they stop being the only thing between a half-finished bump and a release, and
become the proof that one command ran.

**`pytest` no longer rewrites the eight committed example PNGs.**
`tests/test_example.py` runs `examples/demo.py` and `examples/gallery.py` as
subprocesses, because a README whose first code block crashes is worse than no
README. Both scripts wrote beside themselves, and the PNG bytes depend on the
fonts installed locally, so every run left eight modified files in the working
tree. A `git add -A` then swept a binary diff into whatever commit came next,
which is how eight unrelated PNGs reached the 0.5.0 release branch.

Both scripts now take an optional output directory,
`python examples/demo.py [output-directory]`, and the tests pass `tmp_path`.
The default is unchanged: run either one by hand and the files land beside it,
which is what the README promises.

`test_running_the_scripts_elsewhere_leaves_the_committed_pngs_alone` runs both
and compares the committed files before and after, so a directory argument that
is accepted and then ignored fails even though the other tests would still pass.

## 0.5.0 — 2026-07-30

### What changed

- The repository is a Claude Code plugin marketplace.
  `/plugin marketplace add narenp12/figure-gate` installs the skill. Two CI
  checks come with it, both in the `skill` job.
- Ruff and mypy run in CI. Neither existed before. Thirteen findings were fixed
  rather than suppressed; two carry a `noqa` with the reason beside it.
  `per-file-target-version` reads `check_palette.py` against the 3.8 grammar,
  and `E741` is ignored because `l` is the OKLab lightness channel.
- `_back_travel` takes direction from net travel, `ls[-1] >= ls[0]`, rather
  than by majority vote over the steps. No named colormap changes kind.

### Why it changed

**The repository is a Claude Code plugin marketplace.**
`.claude-plugin/marketplace.json` lists the skill and `skill/.claude-plugin/plugin.json`
describes it, so `/plugin marketplace add narenp12/figure-gate` installs it and
follows the tags this project already cuts. The route that existed before was
`cp -r skill ~/.claude/skills/`, which pins nothing and updates never. Nothing
publishes: the marketplace resolves against git, so pushing is the release.

Two CI checks come with it, both in the `skill` job. `plugin.json` carries its
own `version` and Claude Code pins installs to that string, so a release that
bumped `pyproject.toml` alone would ship new files under the old version and no
installed copy would ever update. The second check resolves each marketplace
entry to a real plugin directory with a matching name, because a broken
`source` is otherwise found by a user whose `/plugin install` fails.

**Ruff and mypy run in CI.** Neither existed before. The reason for ruff is one
file: `check_palette.py` is claimed to run on Python 3.8, and that claim is what
makes it vendorable into a non-Python toolchain. The `stdlib-only` job proves
the two invocations it makes still run there; `per-file-target-version` sets
that one file to `py38` and reads all of it against the 3.8 grammar. Ruff is
configured to ignore `E741`, since `l` is the name of the OKLab lightness
channel and `linear_to_oklab` returns `l, m, s` because that is what the
published matrix calls its rows.

Thirteen findings were fixed rather than suppressed: four dead imports, a
`pytest.importorskip` whose binding was unused, two percent-format strings, an
f-string with no placeholders, two unused loop variables, a missing
`raise ... from None`, and one annotation mypy needed. Two carry a `noqa` with
the reason written next to it.

**`cmap_kind` called a windowed viridis "misc".** `_back_travel` picked its
direction by majority vote over the steps, counting strictly positive steps
against the length of the whole list. Plateau steps therefore counted as
evidence against ascending, and 8-bit sRGB rounding makes plateaus the majority
whenever the lightness span is narrow relative to the sample count. Viridis
windowed to `t ∈ [0.00, 0.38]`, the window `style-guide.md` asks for beside
status green, is 158 plateaus in 255 steps: the vote read it as descending and
scored every genuine rise as back travel, 1.00 against a 0.02 threshold.

The bug was one-sided, which is why it survived. A descending ramp with the same
plateaus landed on `-1` by accident and passed, so only ascending ramps failed.
Direction is now net travel, `ls[-1] >= ls[0]`, which is what the vote was
approximating. No named colormap changes kind.

## 0.4.0 — 2026-07-29

### What changed

- `check_palette.check()` **changed** what it returns: `(ok, rows)`, matching
  `check_figure.audit()`. It returned `(rows, ok)` before. If you unpack it,
  swap the names.
- `requires-python` **changed** `>=3.9` → **`>=3.11`**. `check_palette.py` still
  runs on 3.8 when vendored, and matplotlib stays floored at 3.8.
- `GATES` **added**: one registry holding the twenty rows with their functions,
  advisory flag and arguments. `ADVISORY_GATES` is derived from it.
- `audit()` and `check()` gained docstrings. They were the only functions in
  either module without one.
- `NO_GUIDANCE` is empty: `Clipping` and `Ink coverage` have guidance, with a
  test to keep a future re-entry deliberate.
- `tests/test_prose_claims.py` **added**, sweeping the four prose documents.
  `EXTERNAL_CLAIMS` carries claims about the world with a source and a date.
- `KNOWN_DISAGREEMENTS` is compared only against colormaps the running
  matplotlib has. A broken cmasher skips with its reason instead of erroring.
- `conda/recipe.yaml` and `conda/update_recipe.py` **added**, with
  `tests/test_conda_recipe.py` holding the recipe to `pyproject.toml`.
- Corrected: RdBu's poles (`#b1182b` and `#2065ab` are t=0.098 and t=0.899, not
  the ends), five `CMAP_*` constants attributed to the wrong module, Cleveland
  & McGill's ordering, the ACM/Elsevier claim, and the uncited 99.81% figure.

### Why it changed

A minor release because it breaks a call. `check_palette.check()` returned
`(rows, ok)` while `check_figure.audit()` returned `(ok, rows)`, and the README
carried a paragraph warning readers about the difference. Documentation
standing in for a fix: unpacking either one the wrong way binds a bool to the
rows and raises nothing at the call site, so the failure surfaces later,
somewhere else, as a bool that will not iterate.

**Python 3.11 is the floor.** `requires-python` was `>=3.9`, and 3.9 reached
end of life on 2025-10-31, so the package was being offered to an interpreter
upstream had stopped patching. 3.10 goes the same way in October 2026, so the
floor skips it. Two things deliberately did not move with it:

- **`check_palette.py` still runs on Python 3.8** when vendored, which is what
  the file is for, and CI still proves it in a job that installs nothing.
  Installed from PyPI it needs 3.11, because the package carries
  `check_figure.py` too.
- **matplotlib stays floored at 3.8.** Pinned matplotlib is normal in
  scientific environments, the checks are written to survive the 3.8-to-3.11
  API drift, and the CI leg that pins 3.8.4 now runs under Python 3.11 rather
  than disappearing.

**`check()` now returns `(ok, rows)`.** If you unpack it, swap the names. The
paragraph in the README is gone and a test holds both entry points to the same
shape.

#### Prose is now swept, not spot-checked

An accuracy audit of the reference material found five defects the doc suite
could not have caught, because every assertion in it was written after somebody
noticed the claim. Two were mechanical and are now mechanically prevented:

- `#b1182b` and `#2065ab` were described as RdBu's poles. They are the map at
  t=0.098 and t=0.899. Its actual ends, `#67001f` and `#053061`, fail the
  lightness band, and the dark blue also fails the chroma floor. A reader
  taking two swatches off the ends got a failing pair. The section now states
  a sampling window, the same shape as the viridis rule beside it.
- Five `CMAP_*` constants were named in a paragraph about `check_figure.py`.
  They are defined in `check_palette.py`, which is where a reader porting the
  checks needs to look.

Three were claims about the world, which no test can verify: Cleveland &
McGill's ordering was printed with seven ranks and a rank the paper does not
contain, "ACM and Elsevier reject the submission" overstated what either
publishes, and the 99.81% alt-text figure was correct and uncited.

`tests/test_prose_claims.py` sweeps the four prose documents: every code span
has to name something that exists, every hex has to be a colour something
ships, every fenced python block has to parse, every sampling window has to be
one the repo defines, and a constant named in a paragraph about one module has
to be defined in that module. Claims about the world go in `EXTERNAL_CLAIMS`
with a source, a date and the passage that supports them, and the cited work
has to appear in the document's own references. Anything a resolver cannot
place is named in a ledger with the reason.

#### Clipping and Ink coverage have guidance

`NO_GUIDANCE` held the two gates the reference material never explained, on the
argument that both were mechanical rows with nothing to advise. Both turned out
to have something a reader could not get anywhere else. Clipping's two natural
fixes are shrinking the type, which moves the failure to the Type size gate,
and `bbox_inches="tight"`, which fails nothing while trimming the canvas away
from the authored width that every legibility number is derived from. Ink
coverage is routinely read as Tufte's data-ink ratio, which it is not, and
which it moves opposite to under the edit that reading suggests.

The set is empty now, with a test to keep a future re-entry deliberate.

#### Standardization

- **One gate registry.** `GATES` holds the twenty rows with their functions,
  their advisory flag and the arguments they need. `audit()` builds its rows
  from it and `ADVISORY_GATES` is derived from it, where both were separately
  maintained lists of the same names.
- **Both entry points are documented.** `audit()` and `check()` were the only
  functions in either module with no docstring.
- **Remediation clauses are enumerable.** Fifteen of twenty gate messages end
  in a `<-` clause naming the fix. The five that do not are listed in the test
  suite with the reason, rather than being an invisible inconsistency.

#### The oracle no longer depends on which matplotlib you have

- **`KNOWN_DISAGREEMENTS` is scoped to the registry it is about.**
  `test_only_the_three_known_colormaps_disagree_with_cmasher` asserted that all
  three of its adjudicated colormaps still disagree. Two of them, `managua` and
  `vanimo`, arrive in matplotlib 3.10, so under the 3.8.4 floor this project
  still supports the test read their absence as a resolved disagreement and
  failed. CI never saw it, because cmasher is installed on the latest-matplotlib
  job only; `uv sync --group dev` with an older matplotlib pinned did.

  Same defect class as the swatch sweep: an expectation derived from a registry,
  written down as a constant. The constant stays, because each entry is an
  adjudication that has to live somewhere, and it is now compared only against
  the colormaps the running matplotlib actually has. A second test holds every
  key to a real name on 3.10 and up, so scoping cannot quietly swallow a typo.

- **A broken oracle skips with its reason instead of erroring.** cmasher 1.9.2
  builds each of its 114 colormaps with `ListedColormap(..., N=...)`, deprecated
  in matplotlib 3.11 and removed in 3.13, which is what those 114 identical
  warnings on every test run were counting down to. When 3.13 lands, cmasher
  stops importing at all, through no fault of anything here. The differential
  now reports that as a skip naming the ImportError and the matplotlib version,
  rather than a suite that fails on someone else's deprecation. The warnings are
  filtered with the countdown written next to the filter; nothing under
  `skill/scripts/` constructs a `ListedColormap`, so the filter cannot hide a
  defect of this project's.

#### A conda package

`conda/recipe.yaml` is a rattler-build v1 recipe for conda-forge, so the install
line will be `conda install -c conda-forge figure-gate` with no extra channel to
add. Submission is one manual PR to conda-forge/staged-recipes after this
release reaches PyPI; the autotick bot opens the version bump on every release
after that. `conda/README.md` is the checklist, and
`conda/update_recipe.py` stamps the version and the sdist hash, downloading and
hashing the sdist itself rather than trusting PyPI's declared digest.

Nothing in this repo builds it, which is precisely why `tests/test_conda_recipe.py`
exists: it holds the recipe's version, runtime dependencies, Python floor and
entry points to `pyproject.toml`. A conda package that disagrees with the wheel
about any of those is a defect only a conda user meets, and they meet it as "the
gate does not run" rather than as a build failure. The recipe depends on
`matplotlib-base`, not `matplotlib`, which on conda-forge is the difference
between the library and a package that pulls pyqt for a backend these checkers
never open.

The README claimed no conda install at this release, because there was not one
until the staged-recipes PR merged. It has since merged, and the README gained
the badge and the `conda install -c conda-forge figure-gate` line after 0.4.0
shipped.

## 0.3.0 — 2026-07-29

### What changed

- **New gate: `check_colormap`, row 18**, a hard failure. `Fonts` moves to 19
  and `Alt text` to 20. A heatmap drawn in `jet` was a PASS in every release
  before this and is a FAIL now.
- `cmap_kind()` **added** to `check_palette.py`, stdlib only, with
  `CMAP_SAMPLES = 256`, `CMAP_QUALITATIVE_N = 40`, `CMAP_SPAN_MIN = 0.02`,
  `CMAP_BACKTRAVEL_MAX = 0.02` and `CMAP_WRAP_DE_MAX = 3.0`. `misc` is the only
  outcome that fails; `jet`, `rainbow`, `hsv` and `gist_ncar` land there.
- A qualitative colormap is routed to the palette gates for its separation rows
  only.
- `ANONYMOUS_CMAP_NAMES` **added**, holding all three spellings matplotlib uses
  for an author-built colormap.
- A seventh gallery figure, `gallery-encoding.png`.
- Twenty-two swatches **added** across the style guide, gated at source and at
  paint. `palette.css` reaches the page again: the scheme rules no longer carry
  a `:root` prefix that matched nothing.
- `GUIDANCE_ANCHORS` **added**, binding eighteen of the twenty gates to a
  passage. `Clipping` and `Ink coverage` are named in an exemption set.
- The style guide gained a references section: Kovesi, Crameri et al., Nuñez et
  al., Moreland.
- The README's Threshold column is resolved against the modules. Two prose rows
  were converted to checkable numbers; seven remain a literal set.
- `test_palette_oracle.py` skips per test rather than at collection, so the
  test count is the same everywhere. The cmasher differential runs in CI.
- `main` is branch-protected: fourteen required checks, enforced for admins.
- `plans/` is untracked. `specs/` stays.
- Suite: 286 → 482 tests. Gates: 19 → 20.

### Why it changed

A minor release, for the same reason 0.2.0 was one: a figure that passed on
0.2.0 can fail on this one. There is a twentieth gate, and it is a hard failure
rather than an advisory. A heatmap drawn in `jet` was a PASS in every release
before this and is a FAIL now.

The four sections below are the release in the order it happened: a gate, the
site it was published on, an audit of the documents it arrived with, and the
two ways the suite stayed green while CI was red.

#### A twentieth gate: colormap kind

Every gate before this one read artists that carry an identity: a line's
colour, a bar's face, a scatter's marks. A figure whose entire content is one
colormapped image has no such artist, so it passed every check by having nothing
the checks knew how to read. `_data_colors_by_axes` had excluded colormapped
artists since it was written, with a comment saying they answer to "the viridis
rule instead". No such rule existed.

- **`check_colormap` is row 18**, directly after `Contour dash`, which moves
  `Fonts` to 19 and `Alt text` to 20. It harvests every artist in `ax.images`
  and `ax.collections` whose `get_array()` is not `None`, classifies each
  colormap, and fails the ones a reader cannot order values in.

  The guard is the array, never the colormap. Every `ScalarMappable` carries a
  default colormap whether or not anything was mapped through it: a plain
  `scatter(x, y, color="#0072b2")` returns `viridis` from `get_cmap()` and
  `None` from `get_array()`. Testing the colormap would gate every unmapped
  scatter against a ramp it never used.

- **`cmap_kind()` classifies, in `check_palette.py`, stdlib only.** It samples
  `CMAP_SAMPLES = 256` levels, converts to OKLab, and reads the lightness
  channel. Under `CMAP_QUALITATIVE_N = 40` levels is qualitative. A span under
  `CMAP_SPAN_MIN = 0.02` is isoluminant and carries no order. Otherwise the
  measure is **back-travel**, the fraction of a segment's lightness span spent
  moving against its own direction: under `CMAP_BACKTRAVEL_MAX = 0.02` over the
  whole map is sequential, under it over both halves is diverging, or cyclic
  when the ends are within `CMAP_WRAP_DE_MAX = 3.0` in OKLab ΔE ×100.

  Everything else is `misc`, and `misc` is the only outcome that fails. `jet`,
  `rainbow`, `hsv` and `gist_ncar` land there.

- **The cyclic wrap is a colour distance, not a lightness one, and that was
  found by running a differential rather than by reasoning.** The first draft
  measured the wrap in lightness and put 11 of 148 colormaps in the wrong
  family. RdYlGn, `managua` and nine `cmr.*` maps were every one of them called
  cyclic by us and diverging by cmasher. A symmetric diverging map has equal
  lightness at both ends *by construction*, so lightness cannot separate the
  families. Only a cyclic map closes the loop in colour. The gap in end-to-end
  ΔE runs from 0.74
  to 7.48, a factor of ten, and 3.0 sits near its geometric mean.

- **A qualitative colormap is routed to the palette gates**, read for its
  separation rows only, exactly as `check_series_color` reads them. The
  lightness-band and chroma-floor rows are for a palette being chosen, not for
  colours already drawn; applied here they fail Okabe-Ito, which this project
  ships.

- **A seventh gallery figure**, `gallery-encoding.png`, because the gate needed
  one that could not be drawn any other way. Three complex-plane panels:
  Mandelbrot escape time in viridis with a colorbar, Newton basins for `z³ − 1`
  in three separated hues with a legend, and the phase of a rational function in
  twilight on a bar ticked at −π, 0 and π whose ends are the same colour because
  they are the same angle. The set's interior is drawn in an explicit neutral
  and keyed off the bar: "did not escape" is a separate class, not a small
  value.

  Three dense images with three keys in one row is the hardest composition in
  the gallery, which is why it is there. The one failure on the way was `Text
  collision`, on a first attempt that put both keys through the x labels.

- **Stated limits, because the row is named "Colormap kind" and not "Colormap
  quality".** `turbo` passes as diverging: its lightness profile genuinely is
  diverging-shaped, and its real defect is hue banding, which a lightness-only
  measure cannot see. `Wistia` is classified `misc` and is sequential by kind;
  back-travel divides by span, and narrow-span maps get noisy ratios. Both are
  written down in `specs/2026-07-28-colormap-kind-gate-design.md` with the
  measurements, rather than resolved with a guessed constant.

#### The swatches, and the stylesheet that had stopped reaching the page

- **Twenty-two swatches across the style guide**: the Okabe-Ito table, the
  ink and furniture tokens, the achromatic ramp, the RdBu poles and midpoint,
  and the viridis endpoint. Every number in those sections is recomputable
  through `contrast()`; the hue was not, and the Hue column had been answering
  it with the word "vermillion". Each swatch restates its hex in an inline
  `--c`, so both copies are gated: the source in `test_docs_match_code.py`, the
  paint in `test_docs_render.py`.

- **`palette.css` had been reaching nothing.** Prefixing both scheme rules with
  `:root` won a specificity fight that did not exist: Zensical sets
  `data-md-color-scheme` on `<body>`, so `:root[data-md-color-scheme="slate"]`
  matches zero elements and the whole stylesheet went dead. The published site
  fell back to Material's default indigo, with body links at 2.85:1 against a
  4.5:1 floor.

  It shipped past 44 green tests, and that is the interesting part. They read
  hex values out of `palette.css` and checked the contrast numbers quoted in its
  comments, and every one of those assertions was arithmetically true. The
  defect was that the stylesheet reached nothing, which arithmetic on two hex
  values cannot see. The site is now rendered in Chromium and measured where it
  is painted, six pages in both schemes, by the same `contrast()` that gates the
  figures.

- **Two wrapped code spans had become `<h1>` headings.** Python-Markdown splits
  blocks before it parses inline spans, so a line beginning with `#` is a
  heading even mid-sentence. A hex colour wrapped onto a second line turned the
  rest of the sentence into a heading, left an unclosed backtick above it, and
  added a line of prose to the table of contents. `--strict` does not fail on
  it: nothing is broken, a heading was invented.

- **A `<figcaption>` link resolved off the site entirely.** Paths in raw HTML
  are resolved against the docs directory and then rewritten relative to the
  output page, so a `../` that reads correctly in the source is applied twice.
  The built page shipped a link to `narenp12.github.io/choosing-a-form/`. Every
  href in the built HTML is now resolved the way a browser does, against the
  base path `site_url` publishes under.

- **A bare `filelock` import errored on all four pytest jobs** instead of
  skipping, on the path xdist workers take. The file's promise (skipped, not
  failed, without the docs-test group) now has a test of its own that runs it
  in a subprocess with both distributions unimportable.

#### An audit of the documents the gate arrived with

The gate shipped with 122 lines of logic and 13 lines of documentation: one
table row, two counts, one comma in a roster sentence, and a figcaption. The
audit of that gap found a larger one behind it.

- **The README's Threshold column was ungated prose.** Four rosters are held to
  `audit()`: the module docstring, the table's first column, `SKILL.md`'s
  sentence, and the advisory tags. The numbers beside them were held to
  nothing. Eleven of the twenty rows name a constant and quote its value. All
  eleven agreed the day the gate was written, which is the argument for the
  gate: `#fcfcfb`, `#898781` and "171 tests" were each right when they were
  typed too. Every name is now resolved against `check_figure` and
  `check_palette`, and a name in neither raises rather than being skipped.

  Two of the nine prose rows were checkable numbers wearing prose and were
  converted rather than exempted: "40 keys" against `figure.mplstyle`, and
  "Type 42" against the `pdf.fonttype`/`ps.fonttype` the sheet declares. The
  remaining seven are a literal set, so an unquantified threshold is a decision
  someone writes down.

- **The roster size is stated in seven places in the README, and five of them
  said 19.** The gate took the roster to 20 and updated two, leaving "20 passing
  rows means the figure avoids 20 named defects" reading 19, the sentence that
  tells a reader what a passing run means. An eighth mention recounts an
  incident that happened at a particular roster size; its number was removed
  rather than pinned, because holding history to today's count would make it
  drift on every new gate.

- **The gallery has seven figures and the README described six**, omitting the
  encoding figure the gate exists for. `gallery.py` and the gallery page had
  been updated. All three are now held to the number of `finish()` calls in the
  script.

- **Neither guide had a cyclic colormap**, while the gallery shipped a twilight
  phase portrait. `### Cyclic: twilight, as shipped` and `### Which kind, and
  the key it takes` are new: the four kinds as four questions, the five
  constants that decide them, and what each kind costs to get wrong. The kind
  table is gated against `cmap_kind()`, as is the list of maps the guide names
  as failing.

- **"The key follows the kind" lived only in a figcaption**, the least
  discoverable text in the repository. A colorbar is a ruler, so the three
  continuous kinds take one and categories take a legend; a value outside the
  measured range is a separate class, drawn in a neutral and keyed off the bar,
  never as `cmap(0)`. It is in both guides now.

- **Nothing joined a gate to its explanation.** The README table says what a
  gate measures and the reference material says why the rule is there, and the
  colormap gate is the proof they were unconnected: a table row, a threshold, an
  advisory tag, four rosters updated, and no explanation anywhere a reader would
  look, with the suite green throughout. `GUIDANCE_ANCHORS` binds eighteen of
  the twenty gates to a passage that has to still be there. `Clipping` and `Ink
  coverage` are named in an exemption set rather than left silently uncovered.

- **The style guide now has a references section.** It had none while making
  the stronger claims; `choosing-a-form.md` has carried one since it was
  written. Kovesi (arXiv:1509.03700) for the lightness-monotonicity criterion
  back-travel measures, Crameri, Shephard & Heron (*Nat Commun* 11, 5444) for
  what rainbow and red-green maps cost a reader, Nuñez, Anderton & Renslow
  (*PLoS ONE* 13(7), e0199239) for the colour-vision-deficiency floor the
  Okabe-Ito section rests on, and Moreland (ISVC 2009, 92–103) for the midpoint
  rule the guide already stated without a source. Each was checked against the
  publisher. A citation is the one claim in this project that cannot be gated
  without making the suite depend on the network, and it is worth saying so.

#### Two ways the suite was green and CI was not

`main` failed CI on every run between the gate landing and this release. Both
causes are invisible on a developer machine, which is how a green local suite
shipped them twice.

- **An author-built colormap is named differently across matplotlib versions.**
  `contour(colors=[...])` builds a `ListedColormap` that 3.8.4, 3.9.4 and 3.10.0
  call `from_list` and 3.11.1 calls `unnamed`. The gate shipped knowing only the
  3.11 spelling, so on the two CI jobs running older matplotlib every contour
  drawn with explicit colours was harvested as a colour encoding, classified
  qualitative, and hard-failed against all-pairs separation. Three near-black
  levels are three indistinguishable categories by the letter of that check and
  one encoding in one hue in fact. Three tests and `gallery-field.png` went
  with it. `ANONYMOUS_CMAP_NAMES` holds all three spellings, and a test asks
  matplotlib what it calls one rather than assuming.

- **The test count was unwritable, not wrong.** `test_palette_oracle.py` opened
  with a module-level `pytest.importorskip("cmasher")`, which raises during
  collection: the module contributed zero tests rather than two skipped ones. CI
  installs pytest, xdist and matplotlib and never the dev group, so it collected
  two fewer than any machine with cmasher, and the README's test count is
  compared against whatever the local run collected. No single integer satisfied
  both. The oracle skips per test now, so collection is the same everywhere.

- **The differential had never run in CI at all.** The thresholds above were
  justified by differencing `cmap_kind()` against `cmasher.get_cmap_type()`
  across 148 colormaps, and that comparison only ever ran where someone had
  installed cmasher by hand. One job installs it now. An oracle that runs only
  where it is remembered is not a check.

- **`main` is branch-protected**: fourteen required status checks, enforced for
  administrators, and a branch must be up to date before it merges. The gate
  above was merged into a `main` that was already red, and nothing was in the
  way.

#### Also

- `plans/` is untracked. It held an implementation plan written for an agent to
  execute and its task queue, and the queue still recorded every task as
  pending for a gate that had been in `main` for three merges. `specs/` stays:
  a design note is the evidence behind a number the code enforces, and the
  style guide cites one.

Suite: 286 → 482 tests. Gates: 19 → 20.

## 0.2.0 — 2026-07-28

### What changed

- `Contour dash` fires on any negative level, asked of the strokes the set drew
  rather than of `negative_linestyles`. It required *every* level to be
  non-positive before, which is the one shape a signed field never has.
- `check_mark_ratio` measures scatter and `plot` markers in one unit. The ratio
  moves by 4/π.
- `alt_metadata(fig, path)` takes an optional path and returns the key that
  format has, or `None` for the formats that have none. Called without a path
  it returns `Description`, as every earlier version did.
- `ADVISORY_GATES` **added** as the one list. `Overplotting` and `Contour dash`
  are advisory and were documented as able to fail.
- A docs site, published to GitHub Pages from `.github/workflows/docs.yml`.
  Every page except the gallery is a symlink to the file that already existed.
- Dark mode takes sky `#56B4E9` for body links; light mode keeps Okabe-Ito blue
  `#0072B2`.
- Muted ink **changed** `#898781` → **`#777570`** in the guide's table, matching
  what `figure.mplstyle` ships. The old spelling stays in `INK_TOKENS`.
- Corrected: "only the first four slots clear all-pairs" is five; full-range
  viridis is 1.26:1 on white, not 1.23:1 on the retired `#fcfcfb`; the
  grayscale separations are relative luminance, not ΔL; `SKILL.md`'s roster
  listed eighteen of nineteen gates; `demo.png`'s site alt text was a
  paraphrase.
- `_halo` no longer returns "no casing" when matplotlib's private `_gc` moves.
- Smaller: `--venues` runs without matplotlib; the dual-axis message says "two
  data scales"; `ordinal()` no longer divides by zero at `n=1`.
- Suite: 224 → 268 → 286 tests.

### Why it changed

A minor release rather than a patch, because the gates now answer differently.
Nothing here is a redefinition — every change is a fix to code that was not
measuring what it said — but a figure that passed on 0.1.4 can fail on this
one, and that is the fact a version number is for. Two of the nineteen rows
changed verdict: `Contour dash` can fire on signed data, which is the only
shape it never fired on, and `Mark ratio` compares scatter against `plot`
markers in one unit rather than two, moving the ratio by 4/π. `alt_metadata`
takes an optional path and keeps its old behaviour without one.

The three sections below are three audits — the gates, the documentation site,
then the documents themselves — run in that order, each finding the same
species of defect one level further out.

#### An audit of the gates, and what it found

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

#### Docs site

Documentation only. No code, no thresholds, no packaging change — the wheel
built from this commit is byte-identical in what it ships.

- **A docs site**, [Zensical](https://zensical.org), published to GitHub Pages
  from `.github/workflows/docs.yml`. It exists because `style-guide.md` is a
  long reference document whose only affordance on GitHub was scrolling, and
  the thing people do with it is look one threshold up.

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

- **The palette sections now paint the hue beside the hex.** Twenty-two
  swatches: the Okabe-Ito table, the ink/furniture table, the achromatic
  backdrop ramp, the `RdBu` poles and midpoint, and the viridis endpoint. Every
  other cell in those tables is recomputable — a contrast ratio goes back
  through `contrast()` — and the hue is not. The Hue column had been answering
  it with the word "vermillion".

  Each one is `::before` on the code span holding the hex, written as an
  `attr_list` attribute list, and it restates that hex in an inline `--c`. The
  first version was a sibling `<span>`, which put a soft wrap opportunity
  between the square and the value it labels: the diverging poles wrapped, and
  the page shipped a red square at the end of one line with `#b1182b` at the
  start of the next. Generated content cannot be orphaned from the element that
  generates it.

  The restated hex is gated at both ends. `test_docs_match_code.py` reads the
  source and asserts the declared color is the hex the code span spells out, and
  that no palette row is missing a swatch. `test_docs_render.py` renders the
  page in both schemes and asserts the browser paints the hex the reader can
  see — compared against the code span's text, not against the inline style,
  which is the copy under test. It also asserts area and a frame: a `::before`
  with no box paints the right color over no pixels, and `#ffffff` is the
  surface row of the ink table, so on the light page the frame is the entire
  difference between a swatch and nothing at all.

  Neither end is sufficient alone. A source check cannot see a stylesheet that
  reaches nothing, which this site shipped for a release; a browser cannot see a
  square confidently painted the wrong color in both copies at once. Both first
  drafts here failed to their own species of that: the size test floored at "not
  zero", which a collapsed swatch clears on 4px of border, and dark mode drew
  its white mat in border rather than `box-shadow`, taking a third of the hue
  with it and turning slot 1 from black into an outline. The mat is there
  because the column beside it is headed "Contrast `#ffffff`". Orange at 2.25:1
  looks emphatic on a near-black page; the mat is the surface that number is
  about.

#### An audit of the documentation, and what it found

Every number, roster and code sample in the published documents, read against
the code that produces it. Five drifts, all the same species as the ones above,
and each now has the executable link it was missing.

- **The style guide still taught the `alt_metadata` call this release fixes.**
  `savefig(path, metadata=alt_metadata(fig))` — the form that warns on every PDF
  save and that SVG rejects. `SKILL.md` and both examples were corrected when
  the fix landed; `style-guide.md` was not, so the release note announcing the
  fix would have shipped beside a document still teaching the break. Every
  document that teaches the call is now checked for the pathless form. The
  CHANGELOG is excluded, because it quotes the broken call deliberately.

- **`SKILL.md`'s prose roster listed eighteen of the nineteen gates**, omitting
  `Contour dash`, from the commit that added that gate until this one. This is
  the fourth roster of the same list, and the only one nothing read — the README
  table and the module docstring have been checked against `audit` for two
  releases. Prose does not use the gate's own label, so the join is written down
  as a map, and the map is asserted complete against `audit`: a twentieth gate
  cannot be added to the code and to two rosters while quietly skipping this
  one. Order is checked too, and the roster now runs in the order `audit` does.

- **Full-range viridis was quoted at 1.23:1, which is its ratio on `#fcfcfb`** —
  the surface retired three releases ago. On white, which is what
  `figure.mplstyle` renders, it is 1.26:1. Fourth instance of the retired-surface
  bug, and the reason the existing guard for it cannot only be a grep for the
  string: this ratio was in a sentence, not in the table the row-by-row check
  reads. Both documents now have the hex checked against where viridis actually
  ends and the ratio against `contrast()`.

- **The grayscale separations were labelled ΔL and are not.** `ΔL 0.011` and
  `ΔL 0.264` are WCAG relative luminance, which is the right channel for a
  question about desaturation and the wrong label in a document that states
  OKLab ΔE ×100 as its unit. In OKLab the same pairs are 0.018 and 0.221 — the
  ordering survives, the numbers do not, and a reader who recomputes concludes
  the guide has drifted. Nothing was wrong except the unit, which is enough.
  Both documents now name the unit and both pairs carry their hexes, so all four
  numbers are checked against `relative_luminance()`; the aside giving the OKLab
  equivalents is checked against `linear_to_oklab()`, because it is two more
  numbers in prose and this file is about not shipping those.

- **`demo.png`'s alt text on the site was not the string the figure carries.**
  `docs/gallery.md` states outright that every alt text on the page is what was
  passed to `describe(fig, ...)`, which is what makes the page's alt text
  checked rather than written once and forgotten. True of the six gallery
  figures — exactly, verified — and false of the demo, whose alt had been
  paraphrased in the README and copied into the site from there. A claim that
  the documentation is generated from the code, written in prose, about
  documentation that was not. The seven alt texts are now asserted to be exactly
  the seven descriptions the examples attach.

Every gate added here was run against the defect it was written for: the drift
reintroduced, the gate confirmed red, the file restored. The CHANGELOG entry for
the docs site also claimed `style-guide.md` was 367 lines when it was 386 — that
number is gone rather than corrected, since it would drift again the next time
the guide grows.

Suite: 268 → 286 tests.

## 0.1.4 — 2026-07-28

One dead gate on the install path, and the missing way to point a live one at
your own sheet. Nothing about the thresholds changed.

### What changed

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

### What changed

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

### What changed

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

### What changed

- Releases are signed. 0.1.0 went out through `uv publish`, which despite
  offering `--no-attestations` uploaded no provenance at all — PyPI's integrity
  endpoint 404s for both of its files. The upload now runs through the PyPA
  action, which attaches a PEP 740 attestation. 0.1.0 cannot be fixed; published
  files are immutable.
- The TestPyPI rehearsal uploads the same way the real release does. It did not
  before, which is why the missing attestations survived a rehearsal.

## 0.1.0 — 2026-07-27

First release on PyPI. Everything below is the work that preceded it.

### What changed

- **Seven new gates**: `check_text_readability`, `check_line_weight`,
  `check_fonts`, `check_series_color`, `check_dual_axis`, `check_form`,
  `check_identity_channel`, `check_style_sheet`, `check_label_attribution`,
  `check_overplotting` and `check_contour_dash`.
- `figure.mplstyle` sets `axes.prop_cycle` to the six Okabe-Ito series slots,
  and `pdf.fonttype: 42` / `ps.fonttype: 42`. Yellow and black are held out.
- `xtick.color`/`ytick.color` **changed** `#898781` → **`#777570`**, 3.59:1 to
  4.6:1 on white.
- `audit(fig, venue=...)` **added** for twelve known venues, with
  `python check_figure.py --venues` listing them. `CONTENT_WIDTH_PT` still wins
  for anything not in the table.
- `describe(fig, ...)`, `alt_metadata(fig)` and `check_alt_text` **added**,
  advisory.
- `audit(fig, context_axes=[ax])` **added**: a filled backdrop is a context
  surface rather than data ink.
- `check_palette.py` learns `--ink`, exempting listed hexes from the
  chroma-floor and lightness-band rows.
- **scipy is optional**, a `fast` extra. `uniform_filter` is replaced by a
  numpy box blur, `KDTree` is gone from label attribution, and
  `check_overplotting` falls back to an O(n²) numpy path.
- Series color is scoped per panel. One series drawn several ways is one
  identity. Label attribution ignores legend entries.
- Polar radial tick labels are exempt from `check_text_readability`, and the
  row reports how many went unjudged.
- `check_redundancy` skips axes with `axison` false and counts only visible
  tick labels.
- `check_ink` decides emptiness structurally rather than by pixel fraction.
- `examples/gallery.py` **added**: six figures, each audited, with CI failing
  if any figure fails.
- `skill/references/choosing-a-form.md` **added**, plus a step in `SKILL.md`.
- Decided and written down: identity does not ride on label colour, and a
  legend entry is not a direct label. `examples/demo.py` labels its curves
  directly, with cartographic casing.

### Why it changed

#### Four gates that were measuring the wrong thing

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

#### Text readability — the gate the demo needed

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

#### Research-standard gates

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

#### Venue content widths

- **`audit(fig, venue="neurips")`** replaces hand-measuring `CONTENT_WIDTH_PT`
  for twelve known venues (NeurIPS, ICLR, ICML, ACL, IEEE, Nature, LaTeX
  `article`, and the column widths of the two-column ones). `python
  check_figure.py --venues` lists them. `CONTENT_WIDTH_PT` still works and still
  wins for anything not in the table.

#### Alt text

- **`describe(fig, ...)` / `alt_metadata(fig)` / `check_alt_text`.** Across
  100,000 public Jupyter notebooks, 99.81% of programmatically generated images
  shipped with no alt text, nearly all matplotlib. `alt_metadata` produces the
  `metadata=` dict for `savefig`, so the description survives into the PNG, PDF
  or SVG. Advisory: on a paper the description frequently *is* the caption, and
  the caption lives where this cannot see it.

#### `check_label_attribution` was passing nearly everything

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

#### No hard scipy dependency

- The README promises three files and no install, and a hard `scipy` import had
  quietly broken it. `scipy.ndimage.uniform_filter` is replaced by a separable
  cumulative-sum box blur in numpy; `scipy.spatial.KDTree` is gone from label
  attribution entirely; `check_overplotting` uses `cKDTree` when it is
  importable and an O(n²) numpy path when it is not. scipy is now an optional
  `fast` extra. Tested with the import forced to fail.

#### `examples/gallery.py` — six harder figures

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

#### Overplotting / mark-density WARN

- **`check_overplotting` detects scatter marks that merge into a blob.** For
  each scatter (`PathCollection` with offsets), estimates the fraction of points
  whose nearest neighbour in display pixels is within one marker radius — points
  that visually overlap. Above ~50% overlap the WARN fires: reduce counts, use
  hollow markers, add transparency, or switch to hexbin. The 0.5 threshold keeps
  the entire existing corpus clean (all well-separated scatters pass). A WARN,
  not a FAIL — dense marks are legitimate for some forms (e.g. a swarm plot).

#### Context-surface ink stops a standing WARN

- **Ink coverage accepts `context_axes`.** A filled contourf backdrop (loss
  landscape, terrain) saturated 100% of the axes pixels, triggering a standing
  ink WARN on every such figure — the "advisory everyone learns to ignore." New
  `audit(fig, context_axes=[ax])` declaration tells the checker the fill is a
  context surface, not data-ink. The pixel buffer is split into two clusters via
  2-means on color; the larger cluster (the surface) is subtracted from the ink
  count, so only marks *on top* of the backdrop are measured. A terrain panel
  with a few sparse marks now PASSes instead of WARNing. Existing heatmap
  behavior is unchanged (no `context_axes` → same as before).

#### Two false-signal fixes, no new gates

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

#### The series-color and label gates learn the figure's structure

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

#### Five new gates, and the two scripts finally speak

The motivating failure, reproduced end to end: a figure drawn on matplotlib's
default `tab10` cycle with a `twinx` second y axis passed every check in
`check_figure.py` and printed `-> COMPOSED`. The same three hues through
`check_palette.py` reported
`CVD separation (adjacent) worst #ff7f0e vs #2ca02c dE 1.4 (protan)` — one hue
to a protanopic reader. Two scripts in one project, and nothing connected them.

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

#### Decided: identity does not ride on label color

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

#### Decided: a legend entry is not a direct label

The guide required a "visible direct label" for a sub-3:1 hue and `examples/demo.py`
used a legend, so one of the two was wrong. Settled the strict way, because the
obligation follows from the measurement: a faint mark plus a legend leaves the
reader matching a small faint swatch to a small faint curve, which is the step a
direct label removes. The demo now labels its curves directly.

#### New reference

`skill/references/choosing-a-form.md`, plus a step in `SKILL.md`'s procedure.
Grounded in statistical graphics rather than general information design —
Cleveland & McGill's ordering of the elementary perceptual tasks, and the
statistical results behind the rules that matter most in teaching material: what a
box plot hides at small n, why a cut baseline misstates every ratio, why two bars
are the wrong form for paired data, and why overlapping confidence intervals are
not a significance test.

## Earlier in Unreleased

Corrections, no new gates. Nothing that passed before fails now.

### What changed

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

### What changed

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
