# Documentation after the colormap gate

Date: 2026-07-28
Status: implemented

## The hole

PR #12 shipped 122 lines of gate logic and 13 lines of documentation. The
thirteen are correct. They are also the whole of it: one table row, two counts,
one comma in a roster sentence, and a figcaption. A reader who wants to know
what "Colormap kind" measures, what the four kinds are, or which key each kind
takes has nowhere to go.

That is the visible hole. Auditing it turned up a larger one behind it.

**The README's Threshold column is ungated prose.** `readme_gate_names()` at
`test_docs_match_code.py:218` reads `cells[0]` and nothing else. Four rosters
are held to `audit()`: the module docstring, the README's first column, the
SKILL.md prose sentence, and the advisory tags. The numbers beside them are
held to nothing. Twenty rows, eleven of which name a constant and quote its
value.

Measured against the modules today, all eleven agree:

| gate | constant | quoted | code |
| --- | --- | --- | --- |
| Text readability | `TEXT_CONTRAST_MIN` | 4.5 | 4.5 |
| Contrast stack | `ALPHA_LEVELS_MAX` | 3 | 3 |
| Mark ratio | `MARK_RATIO_MAX` | 5.0 | 5.0 |
| Overplotting | `OVERPLOT_THRESHOLD` | 0.5 | 0.5 |
| Type size | `TYPE_FLOOR_PT` | 7.5 | 7.5 |
| Line weight | `LINE_FLOOR_PT` | 1.0 | 1.0 |
| Ink coverage | `INK_MIN, INK_MAX` | 0.02, 0.55 | 0.02, 0.55 |
| Series color | `MAX_SERIES_HUES` | 6 | 6 |
| Label attribution | `LABEL_MARGIN` | 2.0 | 2.0 |
| Colormap kind | `CMAP_BACKTRAVEL_MAX` | 0.02 | 0.02 |
| Alt text | `ALT_TEXT_MIN_CHARS` | 60 | 60 |

**This gate finds no drift on the day it is written, and that is the argument
for writing it now rather than after.** Every drift this repository has already
paid for was a number that was right when someone typed it: `#fcfcfb` was the
surface the contrast table had been computed against, the ink table credited
`#898781` to a sheet that had shipped it, the test count said 171 when the
suite was larger, and the advisory count said five when seven rows were tagged.
The Threshold column is the same shape of claim with none of the machinery, and
it has eleven entries rather than one.

## What ships

| file | change |
| --- | --- |
| `tests/test_docs_match_code.py` | threshold parser, the value gate, the prose allowlist, the kind table, the constant gate, two count gates, the gate-to-guidance map |
| `skill/references/style-guide.md` | `### Cyclic`, `### Which kind, and the key it takes`, the constants, the key rule |
| `skill/SKILL.md` | cyclic row in the colormap table, the kind and key paragraphs |
| `README.md` | the Colormap kind fail condition, two blind spots, five stale counts, test count |

No new page, so `zensical.toml`'s nav and the symlink count in
`tests/test_docs_site.py` are untouched. `style-guide.md` is symlinked into
`docs/`, so one edit lands on both the site and the skill; that is the property
worth preserving and it is why this design adds sections rather than files.

Three things came out different from the plan above, and are recorded here
rather than quietly dropped.

**The colormap classification tests went to `test_docs_match_code.py`, not
`test_palette.py`.** They are a doc-versus-code join, they parse `GUIDE`, and
every other test that does lives in that file. `test_palette.py` already tests
`cmap_kind()` against a literal map of its own; the guide's table is a different
claim by a different author and belongs beside the contrast table it resembles.

**`NO_GUIDANCE` holds two gates, not the four this spec predicted.** The keyword
sweep that produced the estimate missed `**Dual y axes.**` in
`choosing-a-form.md`, because it searched for "dual ax" against a heading that
spells it "Dual y axes". Colormap kind came out of the set in section 2. What is
left is Clipping and Ink coverage, which is the actual debt.

**The audit found two live drifts, which this spec did not predict and which are
the reason it was worth running.** Both are counts in prose, both were correct
when typed:

- The README states the roster size in seven places. The colormap gate took it
  from 19 to 20 and updated two of them, so five sentences said 19, including
  "20 passing rows means the figure avoids 20 named defects" and the advisory
  paragraph. `ROSTER_COUNT_CLAIMS` now holds all seven against `audit()`. An
  eighth mention, an anecdote about a `tab10` figure that predates the Dual axis
  gate, had its number removed instead of pinned: it recounts an incident at a
  particular roster size, and holding history to today's count would make it
  drift on every new gate.
- The gallery has seven figures. `gallery.py` and `docs/gallery.md` said seven;
  the README said six and enumerated six forms, omitting the encoding figure the
  colormap gate exists for. `GALLERY_COUNT_CLAIMS` now holds all three against
  the number of `finish()` calls in the script.

## 1. Gate the threshold column

A second parser over the same table the roster parser already reads, taking
`cells[1]` instead of `cells[0]`.

**Extraction.** `` `NAME = value` `` inside the cell. The parser must handle the
multi-name form, because one row already uses it: `INK_MIN, INK_MAX = 0.02,
0.55` is one code span declaring two constants, and a regex written for the
single form silently matches zero on that row rather than failing.

**Resolution.** Eleven rows carry twelve names, because the ink row declares
two. Eleven of the twelve are in `check_figure.py` and `CMAP_BACKTRAVEL_MAX` is
in `check_palette.py`. The lookup searches both and
**raises on a name in neither**, rather than skipping it. A constant that was
renamed in code and left in the table is precisely the failure this gate is for,
and a lookup that skips what it cannot find reports agreement with nothing.

**Comparison.** `float(quoted) == float(actual)` when both parse as numbers,
exact string equality otherwise. Not `str(actual) == quoted`: `3` against `3.0`
is the kind of formatting difference that turns a real gate into one that has to
be appeased with the wrong edit.

**The prose allowlist.** Nine rows quote no constant. Two of the nine are
checkable numbers wearing prose, and are worth converting rather than exempting:

- `Style sheet | 40 keys`. Verified: `rc_params_from_file` on
  `figure.mplstyle` returns exactly 40. Assert it against the sheet.
- `Fonts | Type 42`. Assert `figure.mplstyle` sets `pdf.fonttype` and
  `ps.fonttype` to 42, which is the claim the cell is making and the one
  `check_fonts` reads at `check_figure.py:1734`.

That leaves seven genuinely unquantified rows: Clipping, Text collision, Axis
redundancy, Dual axis, Form, Identity channel, Contour dash. They go in a
literal `PROSE_THRESHOLDS` set, asserted to be a subset of the roster, so a
twenty-first gate cannot arrive with a prose threshold by accident. Adding a row
to that set is then a decision someone writes down, which is the same discipline
`ADVISORY_GATES` already imposes on the other optional column.

**Parseability first.** Per the pattern at
`test_the_readme_table_is_still_parseable`, assert the threshold parser matched
eleven constant-bearing rows before any test draws a conclusion from what it
read. A parser that matches nothing agrees with everything.

## 2. Colormap kind has no guidance, only a table row

`check_palette.py` grew five constants. One is documented.

| constant | value | documented |
| --- | --- | --- |
| `CMAP_BACKTRAVEL_MAX` | 0.02 | README threshold column |
| `CMAP_SAMPLES` | 256 | nowhere |
| `CMAP_QUALITATIVE_N` | 40 | nowhere |
| `CMAP_SPAN_MIN` | 0.02 | nowhere |
| `CMAP_WRAP_DE_MAX` | 3.0 | nowhere |

`CMAP_SPAN_MIN` is a fail path. A colormap whose lightness never moves more than
0.02 across its whole length classifies `misc` and FAILs, and no reader can
predict that from any document. `CMAP_WRAP_DE_MAX` is the threshold that decides
cyclic against diverging, which is the one distinction the new gallery figure
turns on.

**The README row also under-describes the failure.** It reads "a colormap's
lightness reverses, or a qualitative one's levels fail all-pairs separation".
The gate fails on `kind == "misc"`, which is three distinct causes: back-travel
over budget, span under the floor, and halves-monotone-but-ends-too-far-apart,
which fails cyclic and diverging both. Rewrite the cell to say what the gate
does.

**The guides have no cyclic.** `style-guide.md:96` opens the color section with
a four-row encoding table: Categorical, Sequential/ordinal, Diverging, Context
backdrop. `SKILL.md:38` has the same table with three rows. Neither names a
cyclic map, and `### Sequential: viridis` and `### Diverging: RdBu` have no
sibling. The gallery now ships a twilight phase portrait, so the repository
recommends by example a form its guidance does not mention.

What ships in `style-guide.md`, after `### Diverging`:

- `### Cyclic: twilight, as shipped`. Angles, phases and headings close the
  loop, so the colormap has to; a sequential ramp on a phase produces a false
  seam at the wrap. twilight and `twilight_shifted` are the two matplotlib
  ships. The measurement is already in
  `specs/2026-07-28-colormap-kind-gate-design.md`: twilight's halves back-travel
  0.00% and 0.02% with a wrap dE of 0.00, against a diverging field starting at
  7.48.
- `### Which kind, and what it costs to be wrong`. The four kinds as four
  questions rather than four names. Can a reader order two values (sequential).
  Is there a meaningful middle the data is signed around (diverging). Does the
  scale close (cyclic). Are the levels identities with no order at all
  (qualitative). Plus the fifth outcome, `misc`, which is the only one that
  fails, and what it means: the encoding is not orderable, so the figure asks a
  reader to compare two colors that carry no comparison.
- The five constants, with the two thresholds' measured margins cited to the
  gate spec rather than restated. This repository's rule is that a number in
  prose is a claim; the safest form for a derived number is a pointer to the
  document that measured it, and the gate below is what keeps the pointer
  honest.

**Gate it.** The guide will name colormaps and assign them kinds. That is
exactly the shape of the contrast table, so it takes the same treatment: parse
the kind table out of the guide, parametrize over it, and assert
`cp.cmap_kind(samples(name))` returns what the guide claims. A guide that
recommends twilight for cyclic and a classifier that calls it diverging is a
drift the reader hits and the suite does not.

## 3. The key follows the kind, and it lives in a figcaption

The most reusable rule PR #12 produced is not in any guide. It is in
`docs/gallery.md`, in the caption and the alt text:

> a colorbar is a ruler, so the two continuous panels get one and the
> categorical panel gets a legend instead

with the corollary that the Mandelbrot interior is drawn in an explicit neutral
and keyed off the bar, because "did not escape" is a separate class and not a
small value.

A figcaption is the least discoverable surface in the repository and the one no
gate reads for guidance. The rule belongs in `style-guide.md` beside the kind
table, stated once:

- continuous kinds (sequential, diverging, cyclic) take a colorbar
- qualitative takes a legend, because a colorbar along nothing is a ruler along
  nothing
- a cyclic bar is ticked at both ends and the middle, and its two ends are the
  same color because they are the same angle
- a value outside the measured range is a separate class: a neutral, keyed off
  the bar, never `cmap(0)`

No gate is proposed for this one. It is a composition rule, and the repository's
own position is that composition rules go in the review checklist rather than
into a check that cannot see intent. It goes under
`### Composition rules (what the checker cannot tell you)` or beside it.

## 4. The join that does not exist: gate to explanation

The README table says what each gate measures. The style guide says why the rule
is there and what to do instead. Nothing binds them, and PR #12 is the proof:
the gate got a row and no explanation, and the suite was green.

A keyword sweep over `style-guide.md` and `choosing-a-form.md` finds no
plausible home for Clipping, Ink coverage, Dual axis, or Colormap kind. It also
scored Line weight as covered, on the word "hairline" in the viridis section,
which is about a colormap's light end and not about stroke width. So the sweep
is evidence that the gap is real and is not a measurement of it.

The measurement has to be a hand-written map, for the same reason `FIGURE_PROSE`
is hand-written: prose does not use the gate's label. Propose `GUIDANCE_ANCHORS`,
mapping each gate name to a heading or a distinctive phrase in one of the two
reference documents, with:

- the map asserted complete against `audit_gate_names()`, so a new gate goes
  stale loudly rather than silently
- each anchor asserted to be findable in the file it names
- an explicit `NO_GUIDANCE` exemption set for gates that genuinely need none,
  which starts as whatever the audit leaves and is expected to shrink

**Filling the gaps is not in this spec.** Writing guidance for a gate is its own
work with its own evidence, and folding it in here would mean sections written
to satisfy a test rather than because someone had something to say. Ship the map
with the remainder in `NO_GUIDANCE`, named, so the debt is visible and
enumerable. Colormap kind comes out of that set in section 2 of this same spec;
Dual axis turned out never to have been in it.

## Ripples

- `test_the_readme_test_count_is_the_real_one` reads a number out of the README
  and asks pytest for the real one. Every test this spec adds moves it. The
  README currently says 416.
- The Colormap kind row's "Fails when" cell is being rewritten. It is read by
  `readme_advisory_names()`, which only looks for the `*(advisory)*` marker, so
  the rewrite is safe as long as the marker stays absent. `Colormap kind` FAILs;
  `test_the_colormap_row_is_not_advisory` already pins that.
- `PROSE_THRESHOLDS` and `GUIDANCE_ANCHORS` are two more structures a
  twenty-first gate has to update. That is the intended cost. Adding a gate here
  is deliberately not a one-file change.

## Not doing, and why

**Splitting README from `docs/index.md`.** They are one file, symlinked, 323
lines serving both a GitHub landing page and a site home that has nav beside it.
The site reader does not need "License" and "Contributing" as sections; the
GitHub reader does. The fix is a second copy, and a `docs/` of hand-maintained
duplicates is the exact drift `zensical.toml`'s own comment says the symlink
design exists to prevent. Not worth it for two sections of mild redundancy.

**A "which page do you want" block on the index.** Real, small, and independent
of everything above. It can ride along or go in its own change; it needs no
gate, which is also why it should not hold this one up.

## References worth adding, once verified

The colormap taxonomy has a literature, and citing it makes the four kinds a
standard rather than a house rule. The gate spec already cites Kovesi
(arXiv:1509.03700) for the lightness-monotonicity criterion `_back_travel`
measures. Candidates for the guide's `## References`:

- Crameri, Shephard, Heron, "The misuse of colour in science communication",
  *Nature Communications* 11, 5444 (2020), for the general argument and for
  cyclic maps specifically.
- Nuñez, Anderton, Renslow, on CVD-aware colormap design (*PLoS ONE* 2018),
  which connects the qualitative branch to the Okabe-Ito material already in the
  guide.
- Moreland, on diverging colormap construction, for the midpoint rule the guide
  already states without a source.

**None of these has been checked in this session.** Titles, years and venues are
from memory, and a citation is a claim like any other. Verify each before it
lands, and quote no number out of one that has not been read.

**None of them shipped, for that reason.** The guide's new section cites Kovesi
only, which the gate spec had already read, and points at that spec for the
measurements rather than restating them.

## Risks

- **The threshold gate could be appeased with the wrong edit.** A failure means
  the doc and the code disagree, and the code is not automatically right. The
  test's message should print both values and name the module, so the reader is
  choosing rather than pattern-matching a fix.
- **`GUIDANCE_ANCHORS` invites anchor-shaped writing.** A map that requires
  every gate to have a phrase in the guide can be satisfied by a sentence that
  exists to be found. The `NO_GUIDANCE` exemption is the pressure valve: an
  honest "nothing to say here yet" is better than a paragraph written for a
  regex.
- **The kind table pins the guide to matplotlib's registry.** If a future
  matplotlib revises twilight or RdBu, the guide's claimed kind and
  `cmap_kind()` can disagree and the failure will read as a documentation bug.
  It is the same exposure the gate spec already accepted and records under
  Limits, and it is caught in the same place.
