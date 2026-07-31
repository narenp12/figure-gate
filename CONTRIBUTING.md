# Contributing

## Reporting a defect

Open defects live in the issue tracker, and nowhere else. Not a "known issues"
heading in the README, not a caveat in the style guide. Prose in this repo is
gated — `tests/test_prose_claims.py` sweeps the reference material and pins
every number and every backticked name against the code — and a bug description
is the one kind of sentence that cannot be gated, so a known-issues list rots
quietly in exactly the file whose discipline is that it does not. The 0.4.0 note
in the CHANGELOG names the general version of this: documentation standing in
for a fix. The CHANGELOG records what shipped; the tracker records what has not.

`.github/ISSUE_TEMPLATE/` has four forms, split by what the report is evidence
of rather than by severity:

- **A gate fired on a figure that is fine.** The report needs the case for the
  figure at the size it will print, because that is what decides whether the
  threshold moves or the figure is genuinely broken.
- **A broken figure passed.** The most valuable report here, since a gate that
  never fires is the failure mode this project guards against hardest.
- **Something else is broken.** Crashes, wrong numbers, and documents that
  describe behaviour the code does not have.
- **Propose a new gate.** Held to the three things below.

## The bar for a new gate

This project is a pile of elimination gates, and the failure mode it guards
against hardest is a gate that sounds sensible and never fires. So a new check
ships with three things:

1. **A named failure.** Not "figures should have good contrast" — a real figure
   that was really broken, and how. The style guide is written this way
   throughout, and it's the reason the thresholds are arguable rather than
   arbitrary.
2. **A test proving it fails.** Build a figure with exactly that defect and
   assert *that* gate is the one that catches it. Asserting only that `audit`
   returned `False` would pass even if every other check had silently broken.
3. **A test proving it doesn't over-fire.** Whatever legitimate case sits
   nearest the line — side-by-side panels each needing their own x label, a
   heatmap at 0.98 ink coverage. Every false positive spends the credibility the
   gate runs on, and three of the existing checks fired on things that never
   render before they were tuned.

If the right density or spacing genuinely depends on the form, make it a `WARN`
rather than a `FAIL`. A gate people learn to skip is worse than no gate.

## Changing a threshold

Thresholds are measured, and several are quoted in the guide and pinned in
`tests/test_palette.py`. If you change one, update both — a reader who catches
the docs quoting a number the code doesn't produce has no reason to trust
anything else in them.

## Writing prose

`tests/test_prose_claims.py` sweeps the reference material rather than checking
named claims one at a time. Three things follow from that when you write a
sentence.

**Anything in backticks has to exist.** Constants, functions, files, flags,
rcParam keys, colormap names. A name that resolves nowhere fails, and the fix is
usually that the name is wrong. If it genuinely cannot resolve — a LaTeX
package, an error string quoted so a reader recognises it — add it to
`UNRESOLVED_SPANS` with the reason. That set is meant to stay small.

**A constant belongs to the module the paragraph names.** A paragraph about
`check_figure.py` that names a `check_palette.py` constant fails, because a
reader porting the checks greps the module the paragraph named. This is a real
defect that shipped.

**A claim about the world needs a source and a recorded verification.** Journal
type floors, font requirements, published results: those go in
`EXTERNAL_CLAIMS` with the document, an anchor phrase, the source, the date it
was checked, and the passage that supports it. No test can verify a claim about
the world; what the ledger does is make the human check enumerable, dated, and
auditable without repeating the search. The cited work also has to appear in the
document's own References, because a source only the test file knows about is
not a source the reader has.

Numbers keep working the way they already did: write them as
`` `NAME = value` `` and the doc suite pins them against the code.

## Style

Comments explain *why*, since the *what* is usually legible from the code.
Several of the longer comments exist to stop a future reader from "fixing"
something that was already tried and reverted for a measured reason; keep them.

## Running things

```bash
uv sync --group dev
uv run pytest -q                              # the suite
uv run ruff check .                           # lint
uv run mypy                                   # type check
uv run python skill/scripts/check_figure.py   # the checker rejects a bad figure
uv run python examples/demo.py                # end-to-end
```

`dev` is a dependency group, not an extra, so it is `--group dev` rather than
`.[dev]`.

Ruff runs at the project floor of 3.11 with one exception, set through
`per-file-target-version`: `check_palette.py` is read against the 3.8 grammar,
because that file is claimed to run on 3.8 when vendored. The `stdlib-only` CI
job proves the two invocations it makes still work on 3.8; ruff reads the whole
file, and does it before the commit rather than after the push.

mypy runs unannotated. The code is written without type annotations on purpose,
so the strict flags are off and what is left is the contradiction a reader would
also catch: an attribute that cannot exist, a return that cannot happen.

`check_palette.py` must keep importing nothing outside the standard library.
That's what makes it usable from a non-Python toolchain, and CI has a job with
no install step in it to make sure the claim stays true.

## Cutting a release

The version is written in four files. Do not edit them by hand:

```bash
uv run bump-my-version bump minor    # or patch, or major
git push && git push --tags
```

That rewrites `CHANGELOG.md`, `pyproject.toml`,
`skill/.claude-plugin/plugin.json` and `conda/recipe.yaml`, commits, and tags
`v<new>`. Pushing the tag is what publishes: `release.yml` runs the suite,
builds, uploads to PyPI with attestations, and cuts the GitHub release from the
changelog section named after the version.

Write the notes first, under a `## Unreleased` heading. The bump renames that
heading to the version and the date, and fails if there is no such heading, so
a release with nothing written about it stops before the tag rather than in the
workflow after it.

Rehearse anything that changes packaging on TestPyPI first. `testpypi.yml` is
manual and takes the branch you dispatch it on, and TestPyPI refuses version
reuse just as PyPI does, so a rehearsal needs a `.devN` version that is never
tagged and a branch that is never merged.

`sha256` in `conda/recipe.yaml` is the one version-shaped field the bump leaves
alone, because it cannot be known until the sdist exists on PyPI. Update it
with `conda/update_recipe.py` after the release lands.
