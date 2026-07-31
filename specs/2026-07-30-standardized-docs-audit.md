# The documentation audit, as a procedure rather than a memory

Date: 2026-07-30
Status: implemented

## Why this is a document

The documentation audit has been run four times. Each run found real defects and
each one was reconstructed from the last one's changelog entry, because nothing
wrote down what an audit consists of.

The cost is visible in what each run missed rather than in what it found:

- 0.3.0's audit gated the README's Threshold column and the guide's contrast
  table. It did not look at whether the corpus it swept was the whole corpus.
- 0.4.0's audit produced `test_prose_claims.py`, which sweeps rather than
  enumerates, and swept four documents. The repository had eleven. Nothing said
  which seven were unswept, so `CONTRIBUTING.md` and `conda/README.md` could
  make any claim they liked about the code with the suite green.
- 0.5.0's version bump touched three of four version sites, because the fourth,
  `conda/recipe.yaml`, was not on anybody's list.
- The docs build carried its dependency list twice, and the copies drifted the
  first time the site needed a package one of them did not name.

Every one of those is the same failure at a different level: a check exists, the
thing it should cover is larger than the thing it covers, and the gap is
invisible because nobody enumerated it. Writing the audit down does not stop
somebody missing something. It makes the list of what was checked a thing that
can be reviewed, which is the only version of this that improves.

## What ships

| file | change |
| --- | --- |
| `Makefile` | `make audit`, and one target per class of check |
| `tests/test_prose_claims.py` | the corpus derived from git; new resolver domains; corpus and historical-class gates |
| `tests/test_docs_site.py` | the docs build installs the declared dependency group and may not name a package inline |
| `pyproject.toml` | four `DOC` rules; the `api` group; the codespell configuration |
| `.github/workflows/ci.yml` | the API-break job |
| `.github/workflows/docs.yml` | `--only-group docs`, replacing the second dependency list |

## 1. The corpus is derived, not listed

`PROSE_DOCS` was four hand-written paths. It is now every markdown file
`git ls-files` reports, resolved through the `docs/` symlinks and deduplicated,
minus a historical class.

**git rather than a glob.** A glob over the tree sweeps a scratch note somebody
left in their working directory, which is not documentation and should not fail
their test run. It also reports `docs/index.md` and `README.md` as two
documents, because `docs/` is symlinks, and sweeps the same file twice under two
names. Resolving before deduplicating collapses them; asking git first keeps
untracked files out.

**The historical class.** `CHANGELOG.md` and everything under `specs/` record
what was true on a date. A changelog entry saying `check()` returned
`(rows, ok)` is accurate: it did, until 0.4.0. Sweeping it against today's
modules turns a correct record into a failure whose only fix is to falsify the
history.

This is a rule, `name == "CHANGELOG.md" or parts[0] == "specs"`, not a list of
filenames. A list is a place to put a document that is failing; a rule has to be
widened in a diff. `test_the_historical_class_holds_only_the_records` names what
the rule currently catches, so widening it is visible, and
`test_a_historical_document_says_what_it_is_dated_to` requires each exempted
document to carry the date it is a record of. A guide moved into `specs/` to
escape the sweep fails both.

The repository had already settled this reasoning once, at a smaller scale: an
anecdote in the README about a figure at a particular roster size had its number
removed rather than pinned, because holding history to today's count would make
it drift on every new gate.

## 2. The resolver learned the rest of the repository

Four documents could be resolved against two modules and matplotlib. Eleven
could not, and the sweep's first run over the full corpus returned 229
unresolved spans -- which is not 229 defects. It is a resolver meeting
vocabulary nobody had needed it to know.

Six domains were added, each a real place a name can be checked:

| domain | what it resolves | example |
| --- | --- | --- |
| tracked files | any path the repository tracks, by name or basename | `examples/demo.py`, `release.yml` |
| headings | a markdown heading quoted as code | `## Unreleased` |
| TOML tables and keys | `pyproject.toml` and `conda/recipe.yaml` | `[project.scripts]`, `per-file-target-version` |
| dependency groups and distributions | what the project declares | `dev`, `bump-my-version` |
| CI names | job ids, job and step names | `stdlib-only` |
| test symbols | module-level names and test functions under `tests/` | `UNRESOLVED_SPANS` |
| status words | verdict strings the modules print | `FAIL` |

That left 23, of which 22 are conda-forge's, git's or a placeholder, and are in
the ledger with the reason. The twenty-third was a bug in the sweep: `` `x` ``
written with doubled backticks, markdown's way of showing a literal backtick,
matched as an empty span and reported `''` as an unresolvable claim. The doubled
form is now matched first and its contents swept in their own right, because a
doubled span is still a claim.

**The CI domain was written twice.** The first version accepted any word of five
characters or more appearing anywhere in the six workflow files, which resolved
the bare word `status` -- the third field of a gate's row triple, nothing to do
with CI. A resolver that agrees with almost anything reports agreement with
nothing, which is the failure this whole file exists to prevent, one level in.
It now reads job ids and `name:` values only.

## 3. Three tools, and what was rejected

The audit's own question was whether any of this is already somebody's library.

**`ruff`'s `DOC102`, `DOC202`, `DOC403`, `DOC502`.** A docstring that names a
parameter the signature does not have, or documents a return, a yield or an
exception the body never produces. Same defect class as everything above, on a
surface no sweep over `*.md` reaches. Ruff already runs in CI, so the cost is
four codes in `select`.

Their `missing` counterparts are not adopted. `DOC201` alone reports 59: it asks
every function to carry a Returns section, which is a house style this project
does not write in. Missing prose is an editorial decision; prose that
contradicts the code is a defect.

Both `preview` and `explicit-preview-rules` are load-bearing. The pydoclint
rules are not stable yet, and without the second setting `preview` would also
change the behaviour of every stable rule already selected.

**`griffe check`.** Reads both modules as they stand and as they stood at the
last release tag, and reports what a caller could no longer do. It matters here
more than in a normal library because `check_palette.py` is meant to be
vendored: a renamed function does not break a resolver, it breaks a file
somebody pasted into their repository six months ago, silently, at import.

It is not a veto. A 0.x project may break its API. The job joins the break to
the prose instead: if griffe reports one and `CHANGELOG.md`'s Unreleased section
does not name it, that fails. The thing that harms a vendoring reader is not the
break, it is the break nobody wrote down.

The job took three attempts, and the two failures are worth recording because
both produced a check that passed.

**It read stdout.** griffe writes its findings to stderr. Reading stdout alone
returns an empty report for every run, which the job read as "nothing broke" --
a green check arrived at by not looking at where the answer is written. It reads
both streams now, and a non-zero exit with nothing parsed out of either is
treated as griffe failing to run rather than as the API passing.

**The changelog join matched a keyword.** Searching the Unreleased section for
"breaking" is satisfied by any paragraph that uses the word, including the
changelog entry announcing this job. Searching for the broken symbol's name is
satisfied by a paragraph that mentions it for an unrelated reason -- which is
what happened on the first real test: renaming `contrast` passed, because
`contrast` was listed in the API-page entry three paragraphs away. The join now
requires the name and a word for change in the same paragraph. That can still be
satisfied by coincidence; what it cannot be satisfied by is silence, which is
the case that reaches a reader.

**`codespell`.** The one documentation defect this repository had no machinery
for. Every other gate asks whether prose agrees with code; none of them reads
the words. Three ignore-words, each a term the documents are right to use:
`vermillion` is the Okabe-Ito palette's own spelling, `commun` is an abbreviated
journal title, `theses` is the plural of thesis.

**`pymarkdownlnt`, rejected.** Two findings on the whole corpus after disabling
five noisy rules, and it does not catch the accidental-heading defect this
project hand-rolled: given `` `#E69F00 `` wrapped mid-span, it reported a missing
top-level heading and missed the invented `<h1>` entirely. The hand-rolled check
is strictly better and stays.

**`sybil` and `pytest-examples`, not evaluated further.** They execute fenced
blocks rather than parsing them. The blocks here assume figures they do not
build, which is why `test_every_fenced_python_block_parses` parses only. Running
them is a different piece of work with its own design.

## 4. `make audit`

Six targets, ordered by how long each takes and how legible its failure is.
Spelling and lint fail in seconds and name a line; the site build takes longer
and fails with a traceback. A contributor who runs the audit wants the cheap
answer first.

`audit-prose` runs the five joining test files rather than the whole suite,
which is what makes a documentation change a fast edit-check loop instead of a
full run.

The Makefile is a convenience over CI, not a second definition of it. Every
target is a command CI already runs. That is a duplication, and the honest
mitigation is that each one is a single line: a Makefile that reimplemented a
job would drift from it, and this cannot, because there is nothing in it to
drift.

## What this does not cover

Named so the next audit starts from a list rather than from memory.

- **External links.** The corpus carries 22 of them, several to papers, and
  nothing checks that any still resolves. A dead citation is a broken claim.
  Deliberately out: a network check on every pull request fails for reasons that
  have nothing to do with the change. If it lands it should be scheduled, not
  per-PR.
- **The prose of the historical documents.** Exempt by class and correctly so,
  but that means a typo or a broken internal link in the changelog is caught by
  codespell alone.
- **Fenced blocks are parsed, not executed.** Unchanged from 0.4.0, and the
  reason is unchanged: they assume figures they do not build.
- **The gallery's alt text.** Written prose describing rendered images, and the
  one place in the repository where a claim about a figure is checked by nobody
  looking at the figure.
- **Claims about the world.** `EXTERNAL_CLAIMS` requires a source, a quote and a
  verification date; it cannot require that the source says what the quote says.
  That is a human reading a paper, and the ledger's purpose is to make it
  obvious when nobody has.

## Risks

- **A derived corpus makes adding documentation more expensive.** A new
  markdown file now has to survive the sweep or earn ledger entries. That is
  intended, and the cheap escape -- `specs/` -- is gated by the historical-class
  tests rather than left open.
- **The ledger is where an unchecked claim goes to be legal.** It has 27
  entries, up from 9. Most of the new ones are conda-forge's names, which no
  resolver in this repository could ever check. The guard against the ledger
  becoming a habit is `test_no_ledger_entry_is_one_a_resolver_now_handles`,
  which already forced one entry out during this work: `recipe-maintainers`
  became resolvable the moment the recipe's keys were readable.
- **`make audit` can be read as the whole audit.** It is the mechanical part.
  The three defects the 0.4.0 audit found that no test can catch were all
  claims about the world, and a clean `make audit` says nothing about those.
