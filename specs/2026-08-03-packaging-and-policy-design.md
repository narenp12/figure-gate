# Wheel layout and API stability policy

Date: 2026-08-03

A readiness review of 0.6.0 found four things that read as unfinished to
somebody evaluating the project for use. Three are real, one was a
misdiagnosis, and the review's own arithmetic was wrong in a way this
repository has been bitten by before. All three corrections are recorded here,
because the corrections are the useful part.

## What the review found

The suite was green, `ruff`, `mypy` and `codespell` were clean, the README
quickstart ran verbatim, and PyPI, conda-forge and the docs site all served
0.6.0. The gaps were not in the code.

1. The wheel ships `audit_api.py`, which is release tooling, onto every
   installing user's import path, and force-includes the style sheet as a bare
   `figure.mplstyle` at the root of `site-packages`.
2. The GitHub repository has no topics set, so none of the keywords already in
   `pyproject.toml` reach anyone browsing.
3. Nothing states what the public API promises between versions, and the gate
   that would enforce such a statement exists twice, as a tested script nobody
   runs unattended and an untested copy inlined into CI.
4. The working tree carried the `audit_api` hardening uncommitted, which fails
   the stated-test-count gate in `tests/test_docs_match_code.py`.

## The misdiagnosis

The review's first framing was that the wheel needs a `figure_gate/` package,
because `import figure_gate` fails. Two rounds of checking retired that.

The first was empirical. `check_figure.py` reaches for its neighbours by flat
name at three sites, each guarded:

```python
try:
    import check_palette as cp
except ImportError:
    notes.append("check_palette.py is not importable beside this file, ")
```

Inside a package that import is absolute and fails, so the gate does not error.
It takes the `except` branch and returns a pass carrying a note. Two of the
three sites are `import check_palette as cp`, at `check_figure.py:1582` and
`check_figure.py:2426`, and they downgrade the CVD separation gate and the
palette oracle. The third, `check_figure.py:2874`, is `import suggest_fixes` in
the report path, and it suppresses remediation output rather than a gate. All
three degrade silently, which is the same class of defect as the style-sheet
silent pass pinned in `tests/test_install_path.py`. A package move is therefore
not a relayout; it is an edit to the checker's import logic with a new
silent-pass risk attached.

The second was that the packaging ecosystem does not say what the review
assumed it said. Distributions consisting only of top-level modules are
supported; setuptools documents the single-module distribution directly. The
Python Packaging User Guide does advise putting modules under one top-level
package named after the project, in its guide to distributing packages with
setuptools, but it states that as the most common practice rather than a
requirement. The concrete risk it mitigates is narrower than the advice: PyPI
enforces uniqueness on the distribution name and never on the import name, so
two distributions can ship the same top-level module.

What has no exemption is the data file. The setuptools documentation recommends
that data files meant to be readable at run time be included inside the package,
and says that for data files outside a package there is no supported facility to
retrieve them reliably. A bare sheet at the `site-packages` root is exactly such
a file, so it, and not the flat modules, is the part with no defence.

Flat modules therefore stay. Vendored code and installed code keep importing
identically, which is the property that made the flat layout worth choosing,
and it is now a decision the documentation states rather than an oddity a
reader has to infer.

## The wheel

Three changes, none of which touch how a vendored copy behaves.

`audit_api.py` leaves the wheel. It is reachable only from the `audit-api`
target in the `Makefile` and from its own test, and no installing user has any
use for it.

The sheet moves into `figure_gate_data/`, a directory named for the
distribution, and keeps its filename:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["skill/scripts"]
sources = ["skill/scripts"]
exclude = ["skill/scripts/audit_api.py"]

[tool.hatch.build.targets.wheel.force-include]
"skill/assets/figure.mplstyle" = "figure_gate_data/figure.mplstyle"
```

The obvious alternative, renaming the file to `figure_gate.mplstyle` and
leaving it at the root, was designed first and then withdrawn. It fails this
repository's own prose sweep. `tests/test_prose_claims.py` resolves every inline
code span against something in the tree, and `figure.mplstyle` resolves because
`skill/assets/figure.mplstyle` is tracked, while a name that exists only inside
a built wheel resolves to nothing:

```
'figure.mplstyle'      -> file
'figure_gate.mplstyle' -> None
```

Documenting the renamed sheet anywhere in the swept corpus would fail the sweep,
and the only exit is an `UNRESOLVED_SPANS` ledger entry that
`test_the_unresolved_ledger_has_no_stale_entries` then pins in place. Keeping
the filename and moving the directory avoids that entirely: the prose keeps
saying `figure.mplstyle`, and only the sentence describing where the install
puts it has to move.

The other alternative, the wheel's `.data/` directory, is declined. It installs
to a path `sysconfig` decides, which is not `sys.prefix` and differs between a
Homebrew prefix, a virtual environment and a `--user` install. That would
replace a `Path(__file__).parent` probe with a lookup whose answer varies by
environment, on a gate whose failure mode is a silent pass.

`_style_sheet` probes the installed location first:

```python
for cand in (here / "figure_gate_data" / "figure.mplstyle",
             here / "figure.mplstyle",
             here.parent / "assets" / "figure.mplstyle"):
    if cand.is_file():
        return cand
```

Order matters and the obvious order is wrong. With `here / "figure.mplstyle"`
first, and `here` being the `site-packages` root on the install path, a sheet
dropped there by another distribution would win over this project's own. The
reorder narrows that rather than removing it: an environment where this
project's own sheet is missing still falls through to the second candidate and
can compare a figure against a foreign sheet. The residual is bounded to a
broken install, and is written down here rather than claimed away.

Verified by building the wheel and running the checker against it, rather than
reasoned about. The wheel contains exactly:

```
check_figure.py
check_palette.py
suggest_fixes.py
figure_gate_data/figure.mplstyle
```

and on the install path a figure drawn with no `plt.style.use` returns
`warn` naming 34 of 40 differing keys, while the same figure drawn after
applying the shipped sheet returns `True`. That pair is the property
`tests/test_install_path.py` exists to hold, and it holds under the new layout.

This is a behaviour change on the install path, so it ships as 0.7.0.

### Files the wheel change has to move

The first draft of this document listed three and was wrong. The full set:

- `pyproject.toml`, the `exclude` and the `force-include` target.
- `skill/scripts/check_figure.py`, the probe tuple in `_style_sheet`, its
  docstring at `check_figure.py:2110` naming the old layout, and the diagnostic
  at `check_figure.py:2710` that still reads "no figure.mplstyle beside this
  script".
- `tests/test_install_path.py`, where `INSTALLED_NAME` and the force-include
  assertion move, and where `test_without_the_sheet_the_row_is_the_old_silent_pass`
  pins the diagnostic string at line 100. Changing the message without changing
  that assertion breaks the test; changing neither leaves a message naming a
  file the install no longer ships.
- `.github/workflows/ci.yml`, which is a separate assertion nobody had noticed.
  Line 248 is `if "figure.mplstyle" not in names`, a literal match on the built
  wheel's namelist, and line 241 is the step name asserting the sheet sits
  "beside the checkers". Left alone, the wheel branch fails CI deterministically
  and cannot merge into protected `main`.
- `docs/getting-started.md:25`, "The install ships `figure.mplstyle` beside the
  checkers, which is where the style-sheet gate looks for it." This is the only
  place in the documentation that describes the *installed* sheet's location;
  every other mention is the vendored copy and is untouched.
- `conda/recipe.yaml:17`, whose comment reads "Three unnamespaced entries in
  site-packages, deliberately". The wheel had five before this change and has
  three modules plus one directory after, so the comment was wrong in both
  states.

A new assertion goes in alongside them: nothing currently checks that
`audit_api.py` stays out of the wheel. The CI step prints the namelist and
asserts only the sheet's presence. A later edit to the build config could put
release tooling back on every user's import path with no test noticing, which
is the kind of unasserted claim this project does not otherwise ship.

## The stability policy

The first draft of this section asserted the changelog requirement was not
enforced by anything unattended, on the strength of this:

```
grep -rn "audit_api\|audit-api\|make audit" .github/workflows/
→ no matches
```

The grep is accurate and the conclusion drawn from it was wrong. `ci.yml:72`
holds an `api` job, "A break in the public API is one the changelog admits to",
which runs the same comparison as an inline heredoc against a `fetch-depth: 0`
checkout, on every pull request and every push to `main`. The check runs
unattended. The *script* does not.

That is a worse problem than the one the draft described, because there are now
two copies of one gate and they have already diverged. The heredoc at
`ci.yml:144` accepts six change verbs where `audit_api.py:7` accepts twelve, so
a changelog paragraph reading "`GATES` gained a row" passes `make audit-api`
locally and fails CI. The heredoc's `Unreleased` pattern is `(?=^## )` where the
script's is `(?=^## |\Z)`, so the heredoc misses the section entirely when it is
last in the file. The heredoc has no branch for griffe being absent, and it
collects findings from a run that exited zero. Every one of those differences is
the uncommitted hardening, which went into the copy CI does not run. The script
has eight tests. The heredoc has none.

Rather than weaken the claim, the claim is made true by removing the duplicate.

**`ci.yml`'s `api` job calls `skill/scripts/audit_api.py`** instead of carrying
its own copy. One gate, one implementation, and the implementation is the tested
one. The job keeps its `fetch-depth: 0` checkout and its `--only-group api`
invocation; only the heredoc goes.

`release.yml` deliberately gains nothing. On a tag push HEAD is the tag, so
`git describe --tags --abbrev=0` returns the version being released and the
comparison would be against itself. Verified: `git describe --tags --abbrev=0
v0.6.0` prints `v0.6.0`. A release-time API gate is a gate that cannot fail, and
the pull-request gate already stands between any change and `main`.

The draft also named `suggest` as covered, while `audit_api.py:11` reads
`MODULES = ("check_figure", "check_palette")` and `suggest` is defined in a
third module griffe never compares. `tests/test_api_reference.py:30` carries the
same pair, so `suggest_fixes.py` is second-class on both axes this project uses
to make a claim mechanical.

**`suggest_fixes` joins `MODULES`** in both `audit_api.py` and
`tests/test_api_reference.py`.

That second change does not work as-is, and the reason is worth writing down.
At `v0.6.0` the scripts directory held only `check_figure.py` and
`check_palette.py`; `suggest_fixes.py` and `audit_api.py` both landed after the
tag. Running griffe against the tag for a module that did not exist there
produces:

```
ImportError: accessing 'suggest_fixes' raises ModuleNotFoundError
```

which is a non-zero exit with no finding in it, and `audit_api.py` correctly
refuses that as the tool failing rather than the API passing. Correct rule,
wrong conclusion: a module absent at the comparison tag has no API that could
have broken. `audit_api.py` needs a branch that recognises this, reports the
module as new since the tag, and does not treat it as either a break or a tool
failure. That branch needs its own test, in the style of the ones already in
`tests/test_audit_api.py`.

With those in place the policy reads:

The public API is every name without a leading underscore in `check_figure`,
`check_palette` and `suggest_fixes`. That is broader than the handful a reader
would guess, and it is deliberately the same set griffe compares, so the
statement and the enforcement cannot drift. Naming five functions instead would
tell a reader that `contrast`, `delta_e`, `simulate`, `page_scale` and the rest
of what `docs/api.md` renders may be removed without a changelog entry, when in
fact the script would fail the release for any of them.

While the version is below 1.0, a minor bump may break that API. Every break is
named in the changelog under its release heading, and no change reaches `main`
whose `Unreleased` section does not name what moved.

The number of rows is explicitly not part of the contract. The shape is:
`(label, status, detail)`, with `status` being `True`, `False` or `"warn"`. The
`Banking` gate landed after 0.6.0 and moved the count, which is the policy
demonstrating itself rather than a hypothetical.

What remains ungated is the sentence rather than the symbol. `audit_api.py`
checks that a changed name appears in `Unreleased` next to a change verb. It
cannot check that the sentence describes the change accurately. That limit is
stated rather than papered over.

## Landing

`main` is protected, so each of these is a branch and a pull request.

The `audit_api` hardening and its tests go first, because until they land the
stated-test-count gate fails and every later branch inherits a red suite. That
change also carries this document, and adding a document to `specs/` is itself
gated: `tests/test_prose_claims.py:184` pins the tracked-document count and
`:198` names the set exempted as historical records, so both move in the same
commit. `_is_historical` is a rule keyed on the `specs/` prefix, so the new
document is classified automatically and `PROSE_DOCS` stays at 11 while
`tracked` goes from 15 to 16.

The suite goes from the 1305 stated in `docs/gates.md:166` to **1310**: four new
test functions in `tests/test_audit_api.py`, plus one because the historical
document date assertion is parametrized and there is now another document. The
first draft of this document said 1312, from a local collection run, and that
number was wrong for a reason worth recording. Two collected ids come from
`docs/superpowers/`, which is gitignored and therefore absent in CI:

```
tests/test_docs_site.py::test_no_line_becomes_a_heading_by_accident[2026-08-02-makefile-audit-api-fix.md-...]
tests/test_docs_site.py::test_no_line_becomes_a_heading_by_accident[2026-08-02-makefile-audit-api-fix-design.md-...]
```

Writing 1312 into `docs/gates.md` would have made the branch whose purpose is to
un-red the suite the branch that reds it. A local count is not the count; the
number that goes into prose has to come from a tree that matches what CI checks
out. The first draft also said six new tests where the diff adds four, the rest
of its hunks being assertions inside tests that already existed.

While `tests/test_prose_claims.py` is open for the pins, its failure message on
line 186 says "expected 13 and 9" against an assertion of `(15, 11)`. A stale
number in a string, which the corpus sweep cannot reach because the sweep reads
documents and this is inside a test. Same defect class, one level down, and it
costs nothing to fix in the commit that already edits those lines.

The wheel change follows, then the policy prose and the `ci.yml` de-duplication.
The topics are one API call and need no pull request:

```bash
gh api -X PUT repos/narenp12/figure-gate/topics \
  -f names='matplotlib,data-visualization,accessibility,colorblind,scientific-publishing,figures,python,okabe-ito'
```

## What this deliberately does not do

It does not add a `figure_gate` package, so `import figure_gate` keeps failing.
That is now a documented consequence of the flat layout rather than an
oversight.

It does not put the sheet inside an importable package, so the setuptools
recommendation is still not satisfied to the letter. `figure_gate_data/` is a
directory, not a package, and a directory without an `__init__.py` earns none of
the `importlib.resources` guarantees. What it buys is a uniquely named entry
instead of a bare generic file, at no cost in prose churn. A later maintainer
weighing the `.data/` route or a real package should read the two paragraphs
above before re-deriving them.

It does not close the probe fallthrough. An installation missing its own sheet
can still find a foreign one at the `site-packages` root.

It does not gate the accuracy of a changelog sentence, only the presence of the
symbol it must name.
