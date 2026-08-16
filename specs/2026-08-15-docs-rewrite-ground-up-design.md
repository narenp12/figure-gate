# The docs, ground up: an audience-split rewrite

Date: 2026-08-15
Status: design

## The hole

The site is ten flat pages and one voice, and the two audiences it serves
are mixed through them. The threshold tables and the "what a passing run does
not mean" essay live under the same nav as the install tutorial; the API
reference and the figure style guide are one click apart. A figure author who
wants to know whether a colormap is safe has to pass the maintainer's design
notes to get to it, and a maintainer who wants the API contract has to pass the
author's gallery.

The prose is also telegraphic to the point of being unreadable as prose:
"Stacked bars have one honest series", "A row failed. Print the remedy with
it". Every fact is gated, which is right, but the sentences stopped being
sentences. The rewrite is the ground-up pass the docs have never had: split the
site by audience, organize each half by documentation type, and write every
page in the plain voice the Google developer documentation style guide
prescribes -- sentence case, bare-infinitive task headings, noun-phrase concept
headings, active voice, second person, complete sentences.

The facts do not change. The rewrite changes voice and structure; every number,
threshold, signature and claim in the new prose is read out of `skill/scripts/`
or carried over from the existing docs, and where a claim cannot be verified
against code it earns an `EXTERNAL_CLAIMS` ledger entry rather than a silent
pass. That is the constraint the previous rewrite already held, and it holds
again: the tests are rewritten alongside the docs so the enforcement survives,
but the enforcement direction does not flip -- prose still has to match code,
not the other way around.

## What ships

| file | change |
| --- | --- |
| `zensical.toml` | nav rebuilt to the two-section audience split |
| `docs/contributing.md` | new symlink to `../CONTRIBUTING.md` |
| `docs/security.md` | new symlink to `../SECURITY.md` |
| `README.md` | home page: two-audience entry points, doc links match the new nav |
| `docs/getting-started.md` | tutorial voice, complete sentences, facts kept |
| `docs/how-to.md` | guide voice, bare-infinitive task headings, facts kept |
| `docs/gallery.md` | captions restyled to plain sentences, `alt` text added, image files unchanged |
| `docs/gates.md` | reference-only: threshold tables, what each gate measures, the flow diagram |
| `docs/design.md` | maintainer concept page: two-scripts relationship, Retina history, what a pass does not mean |
| `docs/api.md` | generated reference; "what the API promises" restated in new voice |
| `docs/style-guide.md` | (symlink to `skill/references/style-guide.md`) mechanical rules applied, content kept |
| `docs/choosing-a-form.md` | (symlink to `skill/references/choosing-a-form.md`) restyled, "Choosing a form" -> "Choose a form" heading |
| `docs/skill.md` | (symlink to `skill/SKILL.md`) prose restyled, frontmatter and function untouched |
| `CONTRIBUTING.md` | prose in the new voice, sections kept |
| `SECURITY.md` | prose in the new voice, sections kept |
| `conda/README.md` | prose in the new voice |
| `CHANGELOG.md` | preserved record, not rewritten |
| `tests/test_docs_site.py` | nav assertions `10 -> 13` (the new two-section nav has 13 leaf pages); symlink count `17 -> 19` (the two new site pages are symlinks); `AUTHORED` gains `design.md` (the one new real page) |
| `tests/test_docs_match_code.py` | claims table rewritten to the new sentences |
| `tests/test_prose_claims.py` | corpus accounting `(20, 13) -> (21, 14)` -- the design spec's own commit already moved the baseline to `(20, 13)` (it is a tracked `specs/*.md`, so it joined the historical class and HEAD's `(19, 13)` pin already fails); the two new site pages are symlinks that resolve to already-tracked root files, so only the new real `design.md` joins the corpus; `HISTORICAL_DOCS` gains the design spec; `EXTERNAL_CLAIMS` ledger reset to the new prose |
| `tests/test_docs_render.py` | page/path assertions -> new nav; rendering checks kept |

Unchanged: `skill/scripts/`, `palette.css`, the image assets under `docs/images/`,
the Zensical build plumbing itself (features, extensions, CDN pins), and the
`docs/` symlink discipline -- every page stays a pointer to its single prose
source, and the two new site pages are symlinks to the existing root files.

## 1. The information architecture

The site splits by audience, then by documentation type. Two sections, each
serving one reader:

```
Home
Make a figure          <- figure authors
  Getting started         (tutorial)
  How to                  (guides)
  Gallery                 (examples)
  Figure style guide      (author-facing concept/reference)
  Choose a form           (author-facing concept)
Build the tool          <- maintainers
  Design                  (concept)
  The gates               (reference: thresholds)
  API                     (reference: signatures)
  Contributing            (reference: policy)
  Security                (reference: policy)
Agent skill             <- the Claude Code contract, one reader
Changelog               <- a record
```

The split is the single highest-value move a ground-up rewrite buys. Today an
author navigates past Design and API to reach the style guide; after the split
the author section is self-contained and the maintainer material lives in one
place. The two sections make the audience explicit in the nav, which is the
first thing Google's audience-first principle asks for.

Naming follows the style guide mechanically:

- Task pages get bare-infinitive headings ("Install", "Gate a figure",
  "Choose a form"). "Choosing a form" -> "Choose a form" is the visible rename.
- Concept pages keep noun-phrase headings ("Why the two scripts talk to each
  other" stays a noun phrase).
- All headings sentence case; no title case anywhere.

## 2. The voice

The Google developer documentation style guide is the mechanical ruleset for
every page:

- **Sentence case headings** everywhere.
- **Task headings are bare infinitives**; concept headings are noun phrases.
- **Active voice, second person**: "You run `figure-gate audit`", not "the
  audit is run by figure-gate". Imperative mood for instructions.
- **Plain, complete sentences.** This is the large voice shift. The current
  pages run on fragments ("A row failed. Print the remedy with it"); the new
  prose is dense but grammatical -- the fact stays, the telegraphy goes.
- **Accessible writing**: links say what they point to ("the API reference",
  not "here"), gallery images carry `alt` text, the glossary include keeps
  serving every page.

The voice rule lands differently by file, because the skill's own documents
are instructions an agent executes, and brevity there is a feature:

- **Site prose and repo prose** (`getting-started`, `how-to`, `gallery`, repo
  README/CONTRIBUTING/SECURITY/conda): full Google-style sentences.
- **Skill files** (`SKILL.md`, `skill/references/*`): the compact
  command-oriented register stays; only the mechanical rules that do not cost
  clarity apply (sentence case, imperative mood). `SKILL.md`'s frontmatter and
  every functional directive are untouched -- an agent must still be able to
  run the gates correctly after the rewrite.

The style-guide and choosing-a-form pages are the awkward ones today: they
live under `skill/references/` but read as authoring guidance, not project
style. The rewrite keeps their content and their single-copy symlink role, but
their titles and opening lines stop reading like a project style guide and
start reading like what they are: how to make a figure that passes the gates.

## 3. The page plan

### README.md (home)

What the tool is, then two entry points: "Make a figure" for authors,
"Build the tool" for maintainers. The existing card-grid tile block is updated
to point at the new section pages and the two new pages (Contributing,
Security). `index.md` stays the README symlink.

### Make a figure

- **Getting started** (tutorial): install routes (vendored vs. `uv add` vs.
  conda-forge), the two settings that need the document's values, running the
  skill, requirements. Facts and tabs kept; prose written in full sentences.
- **How to** (guides): the remedies, gating figures in the test suite,
  palettes from non-Python toolchains, half-width placement, alt text, reading
  one row, changing a threshold. Task headings become bare infinitives
  ("Change a threshold" is already right; "A row failed. Print the remedy with
  it" becomes "Print the remedy for a failed row").
- **Gallery** (examples): the 11 example figures, captions rewritten as plain
  declarative sentences, `alt` text on every image, filenames unchanged.
- **Figure style guide** (`style-guide.md`): composition, color (Okabe-Ito,
  viridis, RdBu, twilight, palette constants), legibility budget, prose,
  discipline, ship. Content kept; mechanical style applied.
- **Choose a form** (`choosing-a-form.md`): the ordering, the table,
  distributions/baselines/paired data/uncertainty, forms with no use. Title
  and headings restyled; content kept.

### Build the tool

- **Design** (concept): why the two scripts talk to each other, the
  Retina/backend history, the gate that catches people, what a passing run
  does not mean. This is the maintainer concept page the previous rewrite
  consolidated; it consolidates here as a first-class section page.
- **The gates** (reference): the threshold tables, what each gate measures,
  the flow diagram. Pure reference -- the editorial that used to sit on this
  page moves to Design.
- **API**: generated signatures from `skill/scripts/` via the mkdocstrings
  extension; "what the API promises" restated in the new voice. No hand-written
  signatures.
- **Contributing** (new site page -> `CONTRIBUTING.md`): reporting defects,
  the bar for a new gate, changing a threshold, writing prose, style, running
  things, the audit, cutting a release.
- **Security** (new site page -> `SECURITY.md`): reporting vulnerabilities,
  supported versions, what counts here, what the project does on its own
  behalf.

### Agent skill and Changelog

- **Agent skill** (`skill.md` -> `skill/SKILL.md`): the Claude Code contract.
  Prose restyled per the compact register above; frontmatter, procedure, and
  every directive preserved verbatim in function.
- **Changelog** (`changelog.md` -> `CHANGELOG.md`): a record, not prose. Not
  rewritten.

## 4. Testing

The four doc-gating test files are rewritten alongside the docs so the
enforcement survives the new prose. Their job -- claims must match code -- is
unchanged; what they pin changes to the new sentences and the new nav.

- **`test_docs_site.py`** -- nav assertions move `10 -> 13` (the two-section nav has 13 leaf pages: Home + 5 author + 5 maintainer + Agent skill + Changelog); the symlink count moves `17 -> 19` (the two new site pages are symlinks to root files); `AUTHORED` gains `design.md`, the one new real file -- the two new symlinks need no `AUTHORED` entry because the no-copy test excludes symlinks by construction. The hex and CDN pins survive untouched.
- **`test_docs_match_code.py`** -- the claims table is rewritten to the new
  sentences. Same extraction mechanism; new expected strings, each still
  verified against the code's actual output.
- **`test_prose_claims.py`** -- corpus accounting moves `(20, 13) -> (21, 14)`
  (the design spec's own commit already moved the baseline: it is a tracked
  `specs/*.md`, so it joined the historical class and HEAD's `(19, 13)` pin
  already fails on two tests). The two new site pages are symlinks that
  resolve to already-tracked root files (`CONTRIBUTING.md`, `SECURITY.md`), so
  they add nothing to the resolved-path corpus; only the new real `design.md`
  does. The `HISTORICAL_DOCS` list gains the design spec. The
  `EXTERNAL_CLAIMS` exemption ledger is reset to the new prose. Any claim the
  new prose makes that code cannot verify lands in the ledger only if it is
  genuinely external -- a URL, a version constraint, a venue rule.
- **`test_docs_render.py`** -- page/path assertions update to the new nav;
  the rendering checks (tabs, annotations, collapsibles, card grid, mermaid in
  the closed shadow root, tablesort numeric order) are kept as they are.

Two audit claims the rewrite adds or keeps:

- **Every nav page builds.** The strict build contract already enforces this;
  the site test keeps asserting the nav entries point at built pages.
- **No orphan page, no missing target.** The site test asserts every page on
  the site appears in the nav and no nav entry points at a missing file.

Verification stays `uv run rtk pytest tests/ -n auto -q`. The full suite (1619
tests today) and the docs subset both stay green as the rewrite lands in
steps, not just at the end.

## 5. Rollout

1. **Baseline reset.** The in-flight working-tree rewrite is discarded
   (uncommitted `design.md`, trimmed `gates.md`/`getting-started.md`, their
   test edits, the nav change) so the ground-up rewrite starts from a clean
   `HEAD`. The symlink structure, Zensical config and `palette.css` stay.
2. **Commit boundary.** Confirmed in review 2026-08-15: a single commit
   covering the whole rewrite, not small per-step commits. The doc-gating
   tests are rewritten in the same pass, so intermediate states may be red
   and only the final tree must be green. The in-flight stash is preserved at
   `stash@{0}` for recovery.
3. **Order.** IA/nav + symlinks -> page prose -> test rewrite -> full suite
   green -> done.
4. **No fabricated facts.** Every number, threshold, signature and claim in
   the new prose is read out of `skill/scripts/`, not carried from memory.
   Existing docs serve as a checklist of claims that must survive; where a
   claim cannot be verified against code it earns an `EXTERNAL_CLAIMS` ledger
   entry rather than a silent pass. The rewrite changes voice and structure,
   not facts.

## Risks

- **Test rewrite is part of the job.** The doc-gating tests are deliberately
  sensitive to prose; resetting their expected strings is where a rewrite can
  quietly stop gating. The discipline is to keep the extraction mechanism and
  re-verify each new string against code output, never to delete an assertion
  because it is inconvenient.
- **The skill contract.** Restyling `SKILL.md` and the references risks
  breaking an agent-facing instruction if a directive is reworded past
  recognition. Mitigated by the compact-register rule and a functional check:
  the skill's frontmatter, procedure steps, and gate wiring are preserved
  verbatim in function; the test suite gates the scripts those steps invoke.
- **Single copy can break.** Rewriting the symlink targets (README, skill
  files, CHANGELOG, CONTRIBUTING, SECURITY) is the single copy, so any style
  mistake lands on the site and the skill at once. Contained by the voice
  split in Section 2.
- **"Complete sentences" vs. density.** The repo's whole culture is dense
  prose; going full Google-plain risks bloat. The guard is the tests: the new
  prose still has to name the same facts, and the prose-claims ledger caps
  what can be asserted without code backing.

## Not doing, and why

- **New pages from scratch.** The two new site pages (Contributing, Security)
  are symlinks to existing root files whose prose is restyled in place. No
  hand-written duplicate is introduced; the single-copy design holds.
- **Rewriting the CHANGELOG.** It is a record of what shipped and when.
- **Changing the build.** Zensical config, features, extensions, CDN pins,
  `palette.css` and the symlink discipline all stay. This is a content
  rewrite; the rendering contract is out of scope.
- **Rewriting `skill/scripts/`.** The code the docs describe is not touched.
- **Inventing new facts.** Where the old docs asserted something, the new
  prose re-verifies it against code or earns an `EXTERNAL_CLAIMS` entry. A
  rewrite that adds a number is a bug.

## Changes

- 2026-08-15: initial design. Scope (whole repo), test treatment (rewrite
  alongside), baseline (discard in-flight work), skill treatment (restyle,
  keep function), IA (audience split), governing standard (Google developer
  documentation style guide) all confirmed with the user in review.
- 2026-08-15: execution confirmed in brainstorm. Fact source: code-first,
  docs as checklist (every number read out of `skill/scripts/`, existing docs
  only enumerated as claims to preserve). Commit rhythm: single commit, full
  pass, suite green at the end.