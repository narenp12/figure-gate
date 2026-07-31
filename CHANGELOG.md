# Changelog

## Unreleased

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

### Prose is now swept, not spot-checked

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

### Clipping and Ink coverage have guidance

`NO_GUIDANCE` held the two gates the reference material never explained, on the
argument that both were mechanical rows with nothing to advise. Both turned out
to have something a reader could not get anywhere else. Clipping's two natural
fixes are shrinking the type, which moves the failure to the Type size gate,
and `bbox_inches="tight"`, which fails nothing while trimming the canvas away
from the authored width that every legibility number is derived from. Ink
coverage is routinely read as Tufte's data-ink ratio, which it is not, and
which it moves opposite to under the edit that reading suggests.

The set is empty now, with a test to keep a future re-entry deliberate.

### Standardization

- **One gate registry.** `GATES` holds the twenty rows with their functions,
  their advisory flag and the arguments they need. `audit()` builds its rows
  from it and `ADVISORY_GATES` is derived from it, where both were separately
  maintained lists of the same names.
- **Both entry points are documented.** `audit()` and `check()` were the only
  functions in either module with no docstring.
- **Remediation clauses are enumerable.** Fifteen of twenty gate messages end
  in a `<-` clause naming the fix. The five that do not are listed in the test
  suite with the reason, rather than being an invisible inconsistency.

### The oracle no longer depends on which matplotlib you have

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

### A conda package

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

A minor release, for the same reason 0.2.0 was one: a figure that passed on
0.2.0 can fail on this one. There is a twentieth gate, and it is a hard failure
rather than an advisory. A heatmap drawn in `jet` was a PASS in every release
before this and is a FAIL now.

The four sections below are the release in the order it happened: a gate, the
site it was published on, an audit of the documents it arrived with, and the
two ways the suite stayed green while CI was red.

### A twentieth gate: colormap kind

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

### The swatches, and the stylesheet that had stopped reaching the page

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

### An audit of the documents the gate arrived with

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

### Two ways the suite was green and CI was not

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

### Also

- `plans/` is untracked. It held an implementation plan written for an agent to
  execute and its task queue, and the queue still recorded every task as
  pending for a gate that had been in `main` for three merges. `specs/` stays:
  a design note is the evidence behind a number the code enforces, and the
  style guide cites one.

Suite: 286 → 482 tests. Gates: 19 → 20.

## 0.2.0 — 2026-07-28

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

### An audit of the documentation, and what it found

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
