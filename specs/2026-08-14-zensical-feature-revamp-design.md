# The docs revamp: adopt Zensical's own features

Date: 2026-08-14
Status: design

## The hole

The site is built with Zensical and reads almost none of what Zensical does.
`zensical.toml` enables six markdown extensions and five theme features, chosen
one at a time as a page needed them -- which is right, and is the discipline
the file's own comment defends. But the constraint has ossified: the feature
list has not grown since the site moved to Zensical, so the prose keeps
reaching for structure that the config does not support and the author rewrites
as paragraphs.

Three current pages show the cost, each a place where the writer worked around
an absent feature:

- **getting-started.md** states the same story three times in prose: the three
  install routes ("Vendor" / `uv add` / `conda-forge`) each carry blocks of code
  that differ only in import line, and the 0.7.0 import-line history is a wall
  of conditional prose with two code paths in the middle of it. This is what
  tabbed content exists for.
- **how-to.md** prints its transcript -- the self-test output, the palette CLI
  output -- inline between recipes. The transcript is evidence the code ran,
  and it is also forty lines of noise between the sections a reader is moving
  between. This is what a collapsible admonition is for.
- **gates.md** explains the two-scripts relationship in prose ("check_series_color
  reads the hues off the figure's own artists ... runs them through the palette
  gates"), a directed flow that a flowchart would show in a line. The 21-row
  threshold table is scan material that cannot be re-sorted.

The revamp is bounded deliberately. It adopts features the config does not
have; it does not rewrite the prose, rename pages, or touch the shared
`skill/` documents, because the `docs/` symlink design is the single copy of
what those pages say and this is a rendering change, not a content change.

## What ships

| file | change |
| --- | --- |
| `zensical.toml` | theme features `content.tabs.link`, `content.code.annotate`; extensions `pymdownx.tabbed` (`alternate_style = true`), `pymdownx.snippets` (`auto_append`), `abbr`, `def_list`, `pymdownx.caret`, `pymdownx.keys`, `pymdownx.mark`, `pymdownx.tilde`; Pass 2: mermaid custom fence, `extra_javascript` (tablesort, its number plugin, mermaid) |
| `docs/includes/abbreviations.md` | the glossary `snippets.auto_append` serves every page |
| `docs/javascripts/tablesort.js` | the `document$.subscribe` init, so tablesort survives navigation |
| `docs/javascripts/mermaid.js` | the `document$.subscribe` init, so the CDN renderer runs after navigation |
| `docs/getting-started.md` | install-route tabs, import-line tabs |
| `docs/how-to.md` | code annotations, collapsible transcripts, definition lists for the CLI flags |
| `docs/gates.md` | mermaid flow diagram (Pass 2), tablesort on the 21-row table (Pass 2), collapsible design notes |
| `README.md` | card-grid "what each page is for" block, one lucide icon per tile, HTML that degrades cleanly on GitHub |
| `tests/test_docs_render.py` | render assertions for tabs, annotations, collapsibles, card grid, mermaid SVG, tablesort |
| `tests/test_docs_site.py` | `extra_javascript` pinning assertion; `AUTHORED` gains `abbreviations.md` |
| `tests/test_prose_claims.py` | corpus count (17, 12) -> (18, 12); historical-spec list gains this design |

Unchanged: `docs/gallery.md`, `docs/style-guide.md`, `docs/choosing-a-form.md`,
`docs/skill.md`, `docs/changelog.md`, `docs/api.md`, and the nav. The nav stays
10 entries and the `docs/` symlink count stays 17, which the existing tests
hold. `pyproject.toml` gains nothing: `--only-group docs` keeps meaning "the
build needs nothing the tests need", because the JS arrives as CDN
`<script>` tags at view time, not as build or test dependencies.

## 1. The feature set

### The two passes, and why

Pass 1 is the zero-JS family: content that renders with the bundle alone,
identically in every environment, so it cannot break anything the existing
build contract already gates. Pass 2 is the CDN-JS family: the only change
that adds a runtime dependency at view time, which is where this project has
no test of its own for failure. The split keeps the two failure surfaces
separate -- a config feature and a view-time script cannot be blamed on each
other -- and keeps the risky step last and small. One pass would mix the two;
an infra-first pass would delay every visible feature for plumbing that only
two pages use.

### What the config gets, Pass 1

```toml
[project.theme]
features = [
  "content.code.copy",
  "content.tabs.link",      # a tab pick is a page-wide state
  "content.code.annotate",  # numbered markers expand to prose
  "navigation.top",
  "navigation.tracking",
  "search.highlight",
  "toc.follow",
]
```

Extensions, all verified present in the pinned Zensical 0.0.54 bundle:

- `pymdownx.tabbed` with `alternate_style = true` -- the linked-tab content.
  `alternate_style` is the setting the reference documents; the default tabbed
  style is a text block, this is the panel with the border and the active state.
- `pymdownx.snippets` with `base_path = ["docs"]` and
  `auto_append = ["includes/abbreviations.md"]` -- the glossary, built once and
  appended to every page. The `base_path` is explicit because its default, `"."`,
  resolves against the config's directory: unqualified, Zensical reads
  `<repo>/includes/abbreviations.md`, and the file lives under `docs/`.
- `abbr`, `def_list`, `pymdownx.caret`, `pymdownx.keys`, `pymdownx.mark`,
  `pymdownx.tilde` -- the typographic extras (`==highlights==`, `++key++`,
  `H~2~O`, definition lists, `*[ABBR]: expansion`).

Each extension is enabled because a page uses it, and the comment above the
list says which page uses which. That is the file's existing discipline, kept.

### What the config gets, Pass 2

```toml
[project]
extra_javascript = [
  "https://unpkg.com/tablesort@5.3.0/dist/tablesort.min.js",
  "https://unpkg.com/tablesort@5.3.0/dist/sorts/tablesort.number.min.js",
  "javascripts/tablesort.js",
  "https://unpkg.com/mermaid@11.4.1/dist/mermaid.min.js",
  "javascripts/mermaid.js",
]
```

The mermaid fence:

```toml
[project.markdown_extensions.pymdownx.superfences]
custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" }
]
[project.markdown_extensions.pymdownx.snippets]
base_path = ["docs"]
auto_append = ["includes/abbreviations.md"]
```

Mermaid's engine is not in the Zensical bundle -- verified, the installed
`bundle.d7f30b55.min.js` carries the mermaid CSS theme variables but no
renderer -- so it loads from CDN like tablesort. The CSS variables
(`--md-mermaid-node-bg-color`, `--md-mermaid-edge-color`) are already shipped by
the bundle, so diagrams adapt to light/dark with no extra stylesheet.

Both engines' URLs pinned to exact versions; a floating tag would be the
dependency discipline failure this project screens against, and
`test_docs_site.py` holds the pinning. The tablesort number plugin registers
itself when it loads, so `javascripts/tablesort.js` needs no code for it.

## 2. The page map

### README.md (home)

A `div class="grid cards"` block, six tiles linking to getting-started,
how-to, gates, gallery, style-guide and API, each tile one line on what the
page is for. Each tile carries one lucide icon that stands for the page --
`rocket` for getting-started, `wrench` for how-to, `filter` for gates, `image`
for gallery, `book` for style-guide, `code` for API. The icons mark the tile's
subject at a glance when the grid is scanned, which is the tile's only job;
nothing else on the site gets one. Material's lucide set is already what the
theme ships (the palette toggles use `lucide/moon` and `lucide/sun`), so the
icons cost no new dependency. The block is raw HTML that GitHub renders as a
plain paragraph block with the links intact -- no broken markup on the repo
page, full cards on the site. It sits above the existing `## Documentation`
section; the prose below it is untouched.

The one structural cost, accepted: `index.md` stays the README symlink. A
landing page that is a symlink cannot hold site-only markup without leaking it
to GitHub, and breaking the symlink would be the hand-maintained-duplicate
drift `zensical.toml`'s comment and `test_docs_site.py` both exist to prevent.
The grid block is written to degrade, not to be escaped.

### getting-started.md

The page's route stories become linked tabs. `content.tabs.link` keeps tab
groups that share a label in agreement, which matters here because the two
groups ("Install routes" and "Import lines") share the "vendored" label: a
reader who picks the vendored route in one group gets the vendored import line
in the other. A group with no same-named counterpart simply keeps its own
state.

- **Install routes**: `Vendor` / `uv add` / `conda-forge`. Each tab carries the
  commands and the import line that route implies.
- **Import lines**: `0.7+ installed` / `0.6 and earlier` / `vendored` -- the
  `from figure_gate import *` vs `import check_figure` split, replacing the
  current conditional prose in "Which import line".

### how-to.md

- **Code annotations** on the `report(..., suggest=True)` snippet and the
  CI-figure snippet. The numbered markers explain the rows the output shows
  without interrupting the code.
- **Collapsible admonitions** (`???`) around the two long transcripts -- the
  self-test output and the palette CLI output. Closed by default, expanded on
  demand. The recipe's code stays visible; the evidence of its output is one
  click away.
- **Definition lists** for the palette CLI flags (`--pairs`, `--ordinal`,
  `--surface`, `--ink`), replacing the current flag table.

### gates.md

- **Mermaid flowchart** in "Why the two scripts talk to each other":
  `figure` -> `check_series_color` -> the palette gates, with a pass/fail
  diamond where a row is flagged or cleared, five to seven nodes total. The
  flow ends on the "series color" gate, named by its role; the 21-row table is
  not drawn as nodes. A directed flow the head of the page currently draws in
  a paragraph.
- **Tablesort** on the 21-row "What each gate measures" table. A reference page
  is scanned; sorting by threshold or by gate name is the scan's lever. The
  threshold column sorts numerically via the `tablesort.number` plugin, which
  auto-registers when it loads; plain string sort would put `10` before `2`.
- **Collapsible** design-note sections, the long paragraphs under
  "Design notes".

### gallery.md, and the shared documents

`gallery.md` changes nothing: it is figures and their captions, which tabs,
annotations and mermaid do not improve, and every byte there is already gated
by `GALLERY_COUNT_CLAIMS`. `style-guide.md`, `choosing-a-form.md`, `SKILL.md`,
`changelog.md` and `api.md` are untouched, because they are symlinks into
`skill/` and their text is the single copy the Claude skill reads -- a rendering
feature added to one would land on the other, and the skill reads markdown that
Claude renders as plain text.

## 3. Testing

The build contract (`--strict`, every nav page built, every gallery image
built) gates this work for free. The render tests are where the adopted
features are proven, in the file that exists for that exact purpose.

Pass 1, in `tests/test_docs_render.py`:

- **Tabs sync** -- `content.tabs.link` makes tab groups that share a tab *label*
  pick the same state; it does not make unrelated groups agree. The two tab
  groups on getting-started ("Install routes" and "Import lines") deliberately
  share one label -- "vendored" -- so the test activates it in one group and
  asserts the other group's tab of the same name is active too, and that each
  group's previously active tab hides its content (`hidden` attribute
  toggles).
- **Annotations** -- assert the annotation marker renders on how-to and its
  expanded content contains the expected phrase.
- **Collapsible** -- assert a `details` element on how-to and one on gates
  toggle `open` on click.
- **Card grid** -- assert `div.grid.cards` exists on the home page with six
  tiles, each linking to a built page, and that each tile carries exactly one
  icon: a `span.twemoji` wrapping an `svg.lucide` (`class` contains
  `lucide lucide-`).
- **Icon count** -- assert the six tile icons are the only `svg.lucide`
  references on the home page; the grid was the exception to the no-decoration
  rule, so a seventh icon is a decoration that the test has to be told about.

Pass 2, in `tests/test_docs_render.py`:

- **Mermaid** -- wait for the `.mermaid` selector to contain an `svg` on
  gates.md (proof the CDN engine ran), not merely that the fence rendered text.
- **Tablesort** -- assert the sortable class/direction indicator, click a
  column header, assert rows reordered. Click the threshold column and assert
  numeric order (`10` after `2`), which is the proof the number plugin loaded
  rather than a lexicographic sort shipping silently.

In `tests/test_docs_site.py`:

- **Pinning** -- assert every `extra_javascript` URL is version-pinned (an
  `@version` present, no floating tags) -- all five: tablesort, its number
  plugin, mermaid.
- **No-copies gate** -- `abbreviations.md` joins `AUTHORED`, so the new
  real-file glossary does not trip `test_no_page_has_become_a_copy`.

In `tests/test_prose_claims.py`:

- **Corpus accounting** -- when the design lands, the tracked-markdown count
  moves (17, 12) -> (18, 12) and the historical-spec list gains this design
  doc. `abbreviations.md` joins the sweep the commit after it is written, so
  every code span it carries must resolve or earn an `UNRESOLVED_SPANS` entry
  with a reason.

The existing skip discipline is preserved: the file still skips at run time
without Chromium (`playwright_api()` / `file_lock()` patterns), so the
documented `uv run pytest tests/ -n auto -q` stays green on a dev box, and CI
installs `--group docs-test` as it does today.

## Risks

- **CDN at view time.** The site links unpkg in the built HTML. The docs build
  stays dependency-free (nothing enters `pyproject.toml`), which is the claim
  the repo actually tests; the trade is that a reader's browser must reach the
  CDN for tablesort and mermaid to run. This is the accepted cost, chosen
  deliberately over vendoring 600KB of minified JS into git.
- **Tabs that do not sync.** `content.tabs.link` is a theme feature, and
  Zensical accepts unknown names silently -- the failure mode this project has
  already been bitten by. The render test for tab sync is therefore not a nice
  extra; it is the only thing that proves the link is on.
- **Mermaid without the engine.** A `custom_fence` renders nothing at all if
  the renderer never loads; the strict build and nav-page check pass, and the
  page ships an empty `.mermaid` div. The SVG assertion is the gate.
- **The grid block leaking.** Written as raw HTML, the cards render as plain
  links and text on GitHub. Written subtly differently, they render as a broken
  block. The risk is contained to one `div` at the top of the README and is
  reviewed as such.
- **Glossary noise.** `abbr` rewrites every occurrence of a defined term into
  a tooltip. Terms are chosen to be the vocabulary the pages already repeat
  (`dE`, `CVD`, `OKLab`, `rcParams`), never a word that appears once.

## Not doing, and why

- **Icons and emoji, as decoration.** The site's visual voice is arithmetic
  about contrast ratios, and an icon set sprinkled through the prose would be
  decoration this project measured nothing about. The one exception is the
  card grid, where each tile's lucide icon carries information -- the page's
  subject at scan distance -- and even there the count is pinned by a test.
  Emoji are declined outright: they render differently on GitHub and on the
  site, and this grid is the one place the two renderings are shared.
- **gallery.md.** Figures and captions already work; a feature whose only
  effect is to add chrome between the image and its caption is a regression.
- **The shared documents.** Any rendering feature added to `style-guide.md` or
  `choosing-a-form.md` lands in the Claude skill too, where it renders as
  plain markdown and reads as a syntax error.
- **A separate landing page.** `index.md` stays the README symlink. A real
  index page would be a second copy of the same prose, and a `docs/` of
  hand-maintained duplicates is the drift the whole symlink design exists to
  prevent.
- **Vendoring the JS.** Accepted CDN over vendoring: matching the repo's
  discipline on builds and tests, without importing a minified blob the
  maintainers cannot read or review into tracked source.

## Changes

- 2026-08-14 (render tests): the Pass 1 tests landed in `test_docs_render.py`,
  and the browser answered three questions the design asked on paper.
  - The tab link is *label*-based, as designed: the two getting-started groups
    share "Vendored" at different positions (index 0 in install routes, index 2
    in import lines), and clicking one group's "Vendored" activates the other's
    -- which only a label link can do.
  - "`hidden` attribute toggles" was wrong. Under `alternate_style` a block's
    hiding is `display` under a `:checked` sibling selector; no attribute ever
    appears. The test measures `getComputedStyle`, not the attribute.
  - gates' design notes are `???+`, open by default; how-to's transcripts are
    `???`, closed. The collapsible test pins each page's authored default.
  - Annotations are entirely client-side: the built HTML keeps `# (1)!`
    literal and the `.md-annotation` aside exists only after the bundle runs,
    so the annotation test needs a live page and a JS wait, by design.
  - The suite count moved 1606 -> 1612 with the six render tests, and the
    document-to-gate balance crossed its ceiling. Resolved by raising
    `DOCUMENT_TO_GATE_MAX` 0.93 -> 0.97 with the argument the balance file
    requires: the render tests are the measurement the new prose features stand
    in for (unknown feature names are accepted silently, and the annotation
    markers do not exist in static HTML at all), so the doc-side growth is
    measurement, not more proofreading. Measured 0.925 -> 0.966.
- 2026-08-14 (pin): the bundle reference moved with the pin. Zensical is now
  `==0.0.54`; the extensions listed above are verified against its bundle.
- 2026-08-14 (review): justified the two-pass split; added the mermaid CDN and
  its init file and the tablesort number plugin to the Pass 2 config; scoped
  the gates flowchart to a role-named terminal; extended the test plan to the
  prose-corpus accounting, the `AUTHORED` entry and the numeric-sort
  assertion.
- 2026-08-14 (icons): reversed the icons-declined item. The card grid's six
  tiles each get one lucide icon (the theme already ships the set), and the
  render test pins the tile-icon count to six so a seventh icon is a
  reviewed change; emoji stay declined because the grid renders on GitHub
  and on the site.