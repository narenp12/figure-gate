"""Prose claims, swept rather than enumerated one at a time.

`test_docs_match_code.py` gates named claims: this table, that threshold, this
gate's guidance anchor. Every one of them was written after somebody noticed the
claim. The audit that produced this file found five defects that suite could not
have caught, because nobody had written the assertion for them:

  - `#b1182b` / `#2065ab` described as RdBu's poles. They are t=0.098 and
    t=0.899; the actual ends fail two palette gates.
  - five `CMAP_*` constants attributed to `check_figure.py`, where they are not
    defined.
  - Cleveland & McGill's six ranks printed as seven, with a rank they do not
    contain.
  - "ACM and Elsevier reject the submission", which neither publishes.
  - the 99.81% alt-text figure, correct and uncited.

The first two are mechanically checkable and are checked here. The last three
are claims about the world, and no test can verify one. What a test can do is
refuse to let a claim about the world be made without a source and a recorded
verification, which is `EXTERNAL_CLAIMS` below.

The organising idea is a sweep with an exemption ledger, the same shape as
`GUIDANCE_ANCHORS` and `NO_GUIDANCE` next door: enumerate the syntactic carriers
of a claim (code spans, hex literals, numbers with units), resolve each against
the code, and require anything unresolved to be named in a ledger with a reason.
A new paragraph then cannot introduce an unchecked claim quietly. It either
resolves, or it fails until somebody writes down why it cannot.
"""

import ast
import builtins
import contextlib
import doctest
import inspect
import io
import pathlib
import re
import subprocess
import textwrap

import numpy
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402
from matplotlib import colormaps                             # noqa: E402
from matplotlib.axes import Axes                             # noqa: E402
from matplotlib.colors import to_hex                         # noqa: E402
from matplotlib.figure import Figure                         # noqa: E402
import matplotlib.patheffects                                # noqa: E402

from conftest import SKILL                                   # noqa: E402

import check_figure as cf                                    # noqa: E402
import check_palette as cp                                   # noqa: E402

ROOT = SKILL.parent

GUIDE = SKILL / "references" / "style-guide.md"
FORMS = SKILL / "references" / "choosing-a-form.md"
SKILL_MD = SKILL / "SKILL.md"
README = ROOT / "README.md"

MODULES = {"check_figure.py": cf, "check_palette.py": cp}


# --- the corpus, derived rather than listed -----------------------------------
# This file swept four documents for its first two releases: the guide, the
# forms reference, SKILL.md and the README. The repository had eleven, and
# nothing anywhere said which seven were unswept. `CONTRIBUTING.md`,
# `SECURITY.md`, `conda/README.md` and both site-only pages could say anything
# they liked about the code and the suite stayed green, which is the same defect
# one level out: an unchecked claim, invisible because nobody enumerated the
# place it could hide.
#
# So the corpus is read out of git. A new document is swept the day it is
# committed, or else it fails until `_is_historical` catches it and the tests
# below record the reason it should not be.
#
# `git ls-files` rather than a glob over the tree, for two reasons. A scratch
# note left in the working directory is not documentation and should not fail
# anybody's test run; and `docs/` is symlinks, so a glob reports `index.md` and
# `README.md` as two documents and sweeps the same file twice under two names.
# Resolving before deduplicating collapses them.


def _tracked_markdown():
    listed = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                            capture_output=True, text=True)
    assert listed.returncode == 0, (
        f"`git ls-files` failed in {ROOT}: {listed.stderr.strip()!r}. The "
        "prose corpus is derived from what the repository tracks, so this "
        "suite needs to run inside the checkout")
    paths = sorted({(ROOT / name).resolve() for name in listed.stdout.split()})
    assert paths, "git tracks no markdown at all, which cannot be right"
    return paths


# Documents that record what was true on a date, not what is true now. A
# changelog entry saying `check()` returned `(rows, ok)` is accurate history:
# it did, until 0.4.0. Sweeping it against today's modules would turn a correct
# record into a failure, and the only way to pass would be to falsify the
# history. The specs are the same shape -- each states the code as it stood when
# the design was written, and one of them is explicitly a record of an audit.
#
# The repository already settled this once, in
# `specs/2026-07-28-documentation-audit-design.md`: an anecdote in the README
# about a figure at a particular roster size had its number removed rather than
# pinned, because "holding history to today's count would make it drift on every
# new gate". Same reasoning, applied to whole documents instead of one sentence.
#
# This is an exemption by class, not by convenience, which is why it is a rule
# and not a list of filenames someone can append to. Anything not matching it is
# current-state prose and gets swept.
def _is_historical(path):
    relative = path.relative_to(ROOT)
    return relative.name == "CHANGELOG.md" or relative.parts[0] == "specs"


PROSE_DOCS = [p for p in _tracked_markdown() if not _is_historical(p)]
HISTORICAL_DOCS = [p for p in _tracked_markdown() if _is_historical(p)]

FENCE = re.compile(r"```.*?```", re.S)
CODE_SPAN = re.compile(r"`([^`\n]+(?:\n[^`\n]+)?)`")
# ``a literal `span` `` -- markdown's way of putting a backtick inside a code
# span. The single-backtick pattern reads the pair as an empty span and reports
# `''` as an unresolvable claim, which is a bug in the sweep that reads like a
# defect in the document. Matched first, and its contents swept as a span in
# their own right rather than dropped: a doubled span is still a claim.
DOUBLE_SPAN = re.compile(r"``(.+?)``", re.S)
HEX = re.compile(r"#[0-9a-fA-F]{6}")


def doc_id(path):
    """How a document is named in failure messages: its path from the root.

    Not `path.name`. The corpus has two `README.md`, and a message naming one
    of them tells the reader nothing about which.
    """
    return path.relative_to(ROOT).as_posix()


def prose_only(text):
    """The document with its fenced blocks removed.

    Fences are backticks too. Sweeping inline spans without taking them out
    pairs a fence's backtick with the next span's and reports whole sentences
    as symbols. The blocks are not skipped, they are gated differently, by
    `test_every_fenced_python_block_parses` below.
    """
    return FENCE.sub("", text)


def _spans_in(text):
    """Every inline code span in one document's prose, doubled ones included."""
    out = [" ".join(m.group(1).split()) for m in DOUBLE_SPAN.finditer(text)]
    for m in CODE_SPAN.finditer(DOUBLE_SPAN.sub("", text)):
        out.append(" ".join(m.group(1).split()))
    return out


def spans():
    """(document, span) for every inline code span in the prose corpus.

    A span may wrap one line - `audit(fig,\\nvenue="neurips")` does - so the
    pattern tolerates a single newline and the whitespace is collapsed
    afterwards. A strictly line-bounded pattern instead pairs the closing
    backtick of one span with the opening backtick of the next and reports the
    prose between them as a symbol, which is a bug in the sweep that reads like
    a defect in the document.
    """
    return [(doc_id(path), span)
            for path in PROSE_DOCS
            for span in _spans_in(prose_only(path.read_text(encoding="utf-8")))]


def test_the_corpus_accounts_for_every_tracked_document():
    """Parseability first, per the pattern the doc suite already uses.

    Every test below is parametrized over `PROSE_DOCS`. A corpus that came back
    empty, or short, would not fail them -- it would delete them, and the suite
    would report a green sweep of nothing.
    """
    tracked = _tracked_markdown()
    accounted = {p for p in PROSE_DOCS} | {p for p in HISTORICAL_DOCS}
    assert accounted == set(tracked), (
        "documents are tracked but in neither class: "
        f"{sorted(doc_id(p) for p in set(tracked) - accounted)}")
    assert (len(tracked), len(PROSE_DOCS)) == (24, 17), (
        f"the repository tracks {len(tracked)} distinct markdown documents and "
        f"sweeps {len(PROSE_DOCS)}, expected 24 and 17 - if that is a real "
        "addition, these numbers move with it, which is the point of writing "
        "them down")


def test_the_historical_class_holds_only_the_records():
    """The exemption is a rule, and a rule can be widened by editing one line.

    Naming the documents it currently catches means widening it is visible in a
    diff: a guide moved into `specs/` to get out of the sweep would fail here
    rather than quietly stop being checked.
    """
    assert sorted(doc_id(p) for p in HISTORICAL_DOCS) == [
        "CHANGELOG.md",
        "specs/2026-07-28-colormap-kind-gate-design.md",
        "specs/2026-07-28-documentation-audit-design.md",
        "specs/2026-07-30-standardized-docs-audit.md",
        "specs/2026-08-03-packaging-and-policy-design.md",
        "specs/2026-08-14-zensical-feature-revamp-design.md",
        "specs/2026-08-15-docs-rewrite-ground-up-design.md",
    ], "the set of documents exempted as historical records changed"


@pytest.mark.parametrize("path", HISTORICAL_DOCS, ids=doc_id)
def test_a_historical_document_says_what_it_is_dated_to(path):
    """The exemption is only honest if a reader can tell the document is a
    record. A changelog is dated by its headings and a spec by its front
    matter; something in `specs/` with neither is current-state prose that has
    been filed somewhere the sweep does not look."""
    text = path.read_text(encoding="utf-8")
    assert re.search(r"^(Date: |## )\d{4}-\d{2}-\d{2}", text, re.M) or \
        re.search(r"^## \d+\.\d+\.\d+ — \d{4}-\d{2}-\d{2}", text, re.M), (
            f"{doc_id(path)} is exempted from the prose sweep as a historical "
            "record, but carries no date saying what it is a record of")


def fenced_python():
    """(document, index, source) for every ```python block in the corpus.

    A block nested in a tab is indented with the tab's content, and a Python
    module is not a markdown list item: that shared indent is markdown, not
    Python, so dedent it before anything parses the block.
    """
    out = []
    for path in PROSE_DOCS:
        blocks = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
        out.extend((doc_id(path), i, textwrap.dedent(src))
                   for i, src in enumerate(blocks))
    return out


PROMPT = re.compile(r"^ *>>> ", re.M)


def python_statements(source):
    """The parseable Python in one fenced block.

    A block written as a REPL session is Python interleaved with output, and
    handing the whole thing to `ast.parse` reports the prompt as a syntax
    error. The prompt is not the defect: `docs/how-to.md` states two returned
    values that way and `test_how_to.py` computes both from the code. Split
    with `doctest`, which understands the form, and parse what it returns.

    Every prompt has to come back as an example. One `doctest` reads as output
    -- which is what an indented prompt is -- would otherwise vanish, and a
    block whose examples vanished passes by having nothing left to check.
    """
    if not PROMPT.search(source):
        return [source]
    try:
        examples = doctest.DocTestParser().get_examples(source)
    except ValueError as exc:
        raise AssertionError(
            f"doctest cannot read this block as a session: {exc}") from None
    assert len(examples) >= len(PROMPT.findall(source)), (
        f"{len(PROMPT.findall(source))} prompt line(s) came back as "
        f"{len(examples)} example(s): doctest is reading part of this block as "
        "output rather than as the code it is written as")
    return [example.source for example in examples]


@pytest.mark.parametrize("document,index,source", fenced_python())
def test_every_fenced_python_block_parses(document, index, source):
    """A worked example that does not parse is a claim that does not run.

    Parsing only: executing them would need the figures they assume. It catches
    the class of defect that ships when an example is edited in prose rather
    than in an editor.
    """
    try:
        for statement in python_statements(source):
            ast.parse(statement)
    except SyntaxError as exc:
        pytest.fail(f"{document} python block {index} does not parse: {exc}")


def test_a_broken_session_is_not_excused_by_being_a_session():
    """The gate above grew a second path, and a second path is somewhere a
    defect hides. Both ways a session can be wrong: Python that does not parse
    behind a well-formed prompt, and a prompt `doctest` cannot read as one."""
    with pytest.raises(SyntaxError):
        for statement in python_statements(">>> check_form(fig\n"):
            ast.parse(statement)
    with pytest.raises(AssertionError):
        python_statements(">>> check_form(fig)\n(True, 'x')\n  >>> page_scale(fig)\n1.0\n")


# --- resolving a code span ---------------------------------------------------
# Each resolver answers "is there something in the code this names?" and returns
# a label, or None. Named separately so a failure says which kind of claim broke
# rather than only that a backtick did not resolve.

def _matplotlib_names():
    names = set(dir(plt)) | set(dir(Axes)) | set(dir(Figure))
    names |= set(matplotlib.rcParams)
    names |= set(dir(matplotlib.colors)) | set(dir(matplotlib.cm))
    for owner in (plt.subplots, Figure.savefig, Axes.text, Axes.plot,
                  Axes.contour, Axes.scatter, Axes.imshow):
        try:
            names |= set(inspect.signature(owner).parameters)
        except (TypeError, ValueError):       # C-implemented or wrapped
            pass
    # Artist properties are the other half of matplotlib's keyword surface and
    # are not in any signature: `ha`, `linestyles` and friends live here.
    names |= {"ha", "va", "alpha", "linestyles", "linewidth", "linestyle",
              "color", "colors", "edgecolor", "facecolor", "zorder", "clip_on",
              "bbox_inches", "constrained_layout", "layout", "figsize", "dpi",
              "metadata", "cmap", "norm", "vmin", "vmax", "label",
              "path_effects", "foreground", "sharey", "sharex"}
    return names


MPL_NAMES = _matplotlib_names()

# Words the prose uses as vocabulary in a code span rather than as a reference
# to a symbol: gate verdicts, colormap kind names, Python literals. They are
# spans because they are terms of art, not because they name code.
VOCABULARY = {"misc", "sequential", "diverging", "cyclic", "qualitative",
              "warn", '"warn"', "True", "False", "None", "ggplot2",
              "facet_wrap", "n"}


def _cli_flags(module):
    """Long options a script's `--help` would list.

    Read out of the module source rather than by building the parser, because
    building it means running `argparse` against a `sys.argv` the test does not
    own.
    """
    source = pathlib.Path(inspect.getfile(module)).read_text(encoding="utf-8")
    return set(re.findall(r'"(--[a-z-]+)"', source))


CLI_FLAGS = {name: _cli_flags(module) for name, module in MODULES.items()}
ALL_FLAGS = set().union(*CLI_FLAGS.values())


def _report_marks():
    """The bracketed marks a report actually prints.

    Captured from a real report rather than listed here, so a mark renamed in
    code stops resolving in prose instead of quietly disagreeing with it. The
    self-test figure is the one that produces all of them: it fails hard rows,
    warns on advisory ones, passes the rest, and its details carry both the
    action mark and the reason mark.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        cf.report(cf.self_test_figure(), "resolver probe", suggest=True)
    return set(re.findall(r"\[[A-Z]+\]", buffer.getvalue()))


def _row_names():
    """Every row name the two checkers return.

    `audit` names its gates on the `GATES` roster. `check` builds its row names
    at run time and suffixes two of them with the comparison that ran, so those
    are collected by calling it both ways rather than by pattern.
    """
    names = {gate.name for gate in cf.GATES}
    swatches = ["#e69f00", "#56b4e9", "#009e73", "#0072b2"]
    for kwargs in ({}, {"all_pairs": True}, {"ordinal": True}):
        names |= {row[0] for row in cp.check(swatches, **kwargs)[1]}
    return names


REPORT_MARKS = _report_marks()
ROW_NAMES = _row_names()


def _cli_choices(module):
    """Values a flag will accept, read out of its `choices=[...]`.

    `adjacent` is one of the two `--pairs` takes, so naming it in prose is a
    claim the parser settles -- as the flag itself is. Source-read, for the
    reason `_cli_flags` is."""
    source = pathlib.Path(inspect.getfile(module)).read_text(encoding="utf-8")
    return {value
            for group in re.findall(r"choices=\[([^\]]*)\]", source)
            for value in re.findall(r'"([^"]+)"', group)}


CLI_CHOICES = set().union(*(_cli_choices(m) for m in MODULES.values()))

CONSOLE_SCRIPTS = set(re.findall(r"^([a-z-]+) = \"",
                                 (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
                                 re.M))

# Aliases the prose uses in code spans, spelled the way the import line in the
# same document spells them. `numpy` because the gates return its scalars:
# `page_scale` hands back a `numpy.float64`, and docs/how-to.md saying so is a
# claim about a type that either has that name or does not.
NAMESPACES = {"plt": plt, "matplotlib": matplotlib, "mpl": matplotlib,
              "pe": matplotlib.patheffects, "cp": cp, "cf": cf,
              "colormaps": colormaps, "numpy": numpy, "np": numpy,
              "check_figure": cf, "check_palette": cp}

# Keys the alt-text helper writes into a saved file, per format. `Subject` and
# `Description` are claims about what lands in the file, so they resolve
# against the mapping that puts them there.
METADATA_KEYS = set(cf.ALT_TEXT_KEY_BY_SUFFIX.values()) | {
    cf.ALT_TEXT_KEY_DEFAULT}


def _appendix_definitions():
    """Helpers the guide defines in its own appendix rather than shipping.

    `ordinal()` and `series()` are guide-defined, so nothing in the scripts has
    those names, and a resolver that only knows the modules calls them typos.
    """
    return set(re.findall(r"^def ([a-z_][a-z0-9_]*)\(", GUIDE.read_text(encoding="utf-8"),
                          re.M))


APPENDIX = _appendix_definitions()


def _example_bindings():
    """Names the corpus' own worked examples bind to a value.

    `ok, rows = audit(fig)` is followed by prose about `ok`, and nothing in the
    scripts is called that: it is the caller's name for the first half of the
    return. A sentence explaining a snippet may name what the snippet named.
    Parsed out of the blocks rather than listed as words, so a variable that
    leaves the examples stops resolving with them. Assignment targets only: a
    `def` in an example would otherwise license every parameter name in it,
    and the guide's appendix helpers resolve through `APPENDIX` already.
    """
    names = set()
    for _, _, source in fenced_python():
        for statement in python_statements(source):
            for node in ast.walk(ast.parse(statement)):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    names.add(node.id)
    return names


EXAMPLE_NAMES = _example_bindings()


def _parameter_names():
    names = set()
    for module in MODULES.values():
        for _, obj in inspect.getmembers(module, inspect.isfunction):
            try:
                names |= set(inspect.signature(obj).parameters)
            except (TypeError, ValueError):   # builtins have no signature
                pass
    return names


PARAMETERS = _parameter_names()


# Colormaps the prose is entitled to name that a supported matplotlib may not
# have. `okabe_ito` ships from 3.11 and this project supports matplotlib 3.8
# upward, so on an older one the registry says the guide names something that
# does not exist - which is a fact about the reader's matplotlib, not about the
# guide.
#
# The general rule is the point, not the entry. A resolver that consults the
# live environment gives different answers on different machines, so the sweep
# passes locally and fails in CI. It did exactly that. Anything version-
# dependent belongs here with the version that introduced it, and
# `test_the_later_colormaps_are_real_where_the_version_has_them` stops the map
# from becoming somewhere to hide a typo.
COLORMAPS_ADDED_LATER = {"okabe_ito": "matplotlib 3.11"}


def _is_colormap(name):
    return name in colormaps or name in COLORMAPS_ADDED_LATER


# --- what the wider repository has a name for ---------------------------------
# Four documents could be resolved against two modules and matplotlib. Eleven
# cannot: `CONTRIBUTING.md` names workflows and dependency groups, `conda/
# README.md` names recipe keys, and the pages name scripts that live outside
# `skill/`. Each of the domains below is a real place a name can be checked
# against, so a typo in one of them fails rather than landing in the ledger.


def _tracked_files():
    """Every path the repository tracks, by relative path and by basename.

    The old file resolver looked under `skill/` and the repository root, which
    is where the documents it swept pointed. `examples/demo.py`,
    `conda/update_recipe.py` and `.github/workflows/release.yml` are named in
    prose too, and were unresolvable for no better reason than that nothing had
    needed them yet.
    """
    listed = subprocess.run(["git", "ls-files"], cwd=ROOT,
                            capture_output=True, text=True)
    assert listed.returncode == 0, f"`git ls-files` failed in {ROOT}"
    names = listed.stdout.split()
    assert names, "git tracks nothing at all, which cannot be right"
    return set(names) | {pathlib.Path(name).name for name in names}


TRACKED_FILES = _tracked_files()

PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
RECIPE = (ROOT / "conda" / "recipe.yaml").read_text(encoding="utf-8")
WORKFLOWS = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")))


def _ci_names():
    """Job ids and job or step names, which is what prose points at.

    Structural positions only, not "any word that occurs in a workflow file".
    The loose version resolved the bare word `status` -- the third field of a
    gate's row triple, and nothing to do with CI -- because the string appears
    somewhere in six YAML files. A resolver that agrees with almost anything
    reports agreement with nothing, which is the failure this whole file exists
    to prevent, one level in.
    """
    names = set()
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        names |= set(re.findall(r"^  ([a-z][a-z0-9_-]*):$", text, re.M))
        names |= set(re.findall(r"^\s*-?\s*name:\s*(.+?)\s*$", text, re.M))
    return names


CI_NAMES = _ci_names()

# `make audit-prose` is a claim that the target exists. The Makefile is the one
# place in the repository where a documented command is also a definition, so it
# reads as one.
MAKE_TARGETS = set(re.findall(r"^([a-z][a-z-]*):",
                              (ROOT / "Makefile").read_text(encoding="utf-8"), re.M))

# Ruff rule codes the project selects, and the prefixes they belong to. Prose
# names both: `E741` is a rule the configuration ignores by name, and `DOC` is
# the family the four docstring rules come from. A code the project neither
# selects nor ignores is a claim about a lint that does not run here.
_ruff = re.search(r"\[tool\.ruff\.lint\](.*?)^\[", PYPROJECT, re.S | re.M)
assert _ruff, "pyproject.toml no longer has a [tool.ruff.lint] section"
RUFF_CODES = set(re.findall(r'"([A-Z]+\d*)"', _ruff.group(1)))
RUFF_CODES |= {re.sub(r"\d+$", "", code) for code in RUFF_CODES}

# `[project.scripts]`, `[tool.ruff.lint]`. A table header is a claim that the
# section exists, and it is the one form of TOML reference the prose uses that a
# bare key lookup would miss.
TOML_TABLES = set(re.findall(r"^\[+([^]\n]+)\]+", PYPROJECT, re.M))

# Bare keys, from both files that carry configuration the prose describes.
# `per-file-target-version` is a real key in one and `sha256` is a real key in
# the other; neither is a Python name and both are claims.
CONFIG_KEYS = set(re.findall(r"^\s*\"?([A-Za-z][A-Za-z0-9_.-]*)\"?\s*[:=]",
                             PYPROJECT + "\n" + RECIPE, re.M))

DEPENDENCY_GROUPS = set(re.findall(r"^([a-z][a-z-]*) = \[",
                                   PYPROJECT.split("[dependency-groups]")[-1],
                                   re.M))

# Distribution names this project depends on or ships beside, which is what
# `bump-my-version` and `matplotlib-base` are: packages, not importable modules.
DEPENDENCIES = set(re.findall(r'"([A-Za-z][A-Za-z0-9_.-]+)\s*[><=;\[]',
                              PYPROJECT)) | set(
    re.findall(r"^\s*-\s*([a-z][a-z0-9_.-]+)", RECIPE, re.M))


def _module_strings(module):
    """String literals the module can print, which is where `PASS` lives.

    Read from the source rather than by running a gate: the verdict words are
    what a caller greps for, so they are a claim about output, and output is
    what the source spells.
    """
    return set(re.findall(r'"([A-Z][A-Z ]*)"',
                          pathlib.Path(inspect.getfile(module)).read_text(encoding="utf-8")))


STATUS_WORDS = set().union(*(_module_strings(m) for m in MODULES.values()))

# Module-level names the test suite defines. The contributing guide explains how
# to add to `UNRESOLVED_SPANS` and `EXTERNAL_CLAIMS`, which are as real as any
# constant in the scripts and were unresolvable only because nothing looked in
# `tests/`.
TEST_SYMBOLS = set(re.findall(
    r"^([A-Z][A-Z0-9_]{2,})\s*[:=]", "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "tests").glob("*.py"))),
    re.M)) | set(re.findall(
        r"^def (test_[a-z0-9_]+)", "\n".join(
            path.read_text(encoding="utf-8") for path in sorted((ROOT / "tests").glob("*.py"))),
        re.M))


def _headings():
    """Every markdown heading in the corpus, historical documents included.

    `## Unreleased` is a heading in the changelog that the contributing guide
    tells a reader to write under, and `### Cyclic: twilight, as shipped` is a
    section the specs point at. A heading quoted as code is a claim that the
    section exists, checkable against the documents themselves.
    """
    out = set()
    for path in _tracked_markdown():
        out |= set(re.findall(r"^(#{1,6} .+?)\s*$", path.read_text(encoding="utf-8"), re.M))
    return out


HEADINGS = _headings()

# A heading the release process defines rather than one a document carries.
# `## Unreleased` exists exactly while somebody is writing the next entry:
# bump-my-version renames it to the version at the tag, and its absence is what
# stops a release with nothing written about it.
#
# It was in `UNRESOLVED_SPANS` for one release, which fixed a suite that went
# red at every tagged commit and produced one that went red the moment a
# maintainer followed `CONTRIBUTING.md` and wrote the heading: the ledger's own
# "this entry now resolves" test fired on it. Both states are correct, so the
# span resolves in both, and the check that it does is
# `test_the_process_heading_resolves_whether_or_not_it_is_written`.
PROCESS_HEADINGS = {"## Unreleased"}


def _defining_modules(name):
    return [doc for doc, module in MODULES.items() if hasattr(module, name)]


def _resolves_dotted(dotted):
    """Walk `a.b.c` from a namespace the prose is entitled to assume."""
    head, *rest = dotted.split(".")
    obj = NAMESPACES.get(head)
    if obj is None:
        if any(hasattr(module, head) for module in MODULES.values()):
            return True
        if head in APPENDIX or head in PARAMETERS:
            return True
        return head in MPL_NAMES or _is_colormap(head)
    for part in rest:
        obj = getattr(obj, part, None)
        if obj is None:
            return False
    return True


def _identifiers_resolve(snippet):
    """Every name in a multi-token snippet that could be ours has to be ours.

    Used for the fenced one-liners: `from check_palette import contrast;
    contrast("#471365", "#ffffff")` is four claims in one span.
    """
    names = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", snippet)
    ours = [n for n in names
            if n.split(".")[0] in NAMESPACES
            or any(hasattr(m, n.split(".")[0]) for m in MODULES.values())
            or n in APPENDIX]
    return bool(ours) and all(_resolves_dotted(n) for n in ours)


def _is_predicate(span):
    """`not s`, `s is False`: a test written over a name, not a name.

    Parsed rather than pattern-matched, so the names inside are held to the
    standard a bare span is and a predicate over something nothing defines
    still fails. Only the shapes prose uses for a verdict -- negation,
    comparison, their `and`/`or` -- so this is not a licence for code.
    """
    try:
        tree = ast.parse(span, mode="eval")
    except SyntaxError:
        return False
    if not isinstance(tree.body, (ast.UnaryOp, ast.Compare, ast.BoolOp)):
        return False
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return bool(names) and all(
        n in EXAMPLE_NAMES or n in PARAMETERS or _resolves_dotted(n)
        for n in names)


def resolve(span):
    """A label for what `span` names in the code, or None when nothing does."""
    if span in VOCABULARY:
        return "vocabulary"
    if HEX.search(span) and not re.search(r"[(){}\[\]=]", span):
        return "hex"                          # checked by the hex sweep below
    if span.startswith("\\"):
        return "latex"                        # a control sequence, not a symbol
    if span in METADATA_KEYS:
        return "metadata-key"
    if span in CONSOLE_SCRIPTS:
        return "console-script"
    if span in PROCESS_HEADINGS:
        return "process-heading"
    if span in HEADINGS:
        return "heading"
    if span in STATUS_WORDS:
        return "status"
    if span in TEST_SYMBOLS:
        return "test-symbol"
    if span.startswith("[") and span.strip("[]") in TOML_TABLES:
        return "toml-table"
    if span in DEPENDENCY_GROUPS:
        return "dependency-group"
    if span in DEPENDENCIES:
        return "dependency"
    if span.startswith("--"):
        flags = set(re.findall(r"--[a-z-]+", span))
        if flags <= ALL_FLAGS:
            return "cli"
        # A flag of a tool this project runs rather than one it ships:
        # `--group dev` is uv's, and the claim it makes is that the project is
        # invoked that way somewhere. The workflows are where that is true.
        rest = span.split(None, 1)
        if span in WORKFLOWS or (len(rest) == 2 and rest[1] in DEPENDENCY_GROUPS
                                 and rest[0] in WORKFLOWS):
            return "tooling-flag"
        return None
    make = re.fullmatch(r"make(?:\s+([a-z][a-z-]*))?", span)
    if make:
        target = make.group(1)
        return ("make-target"
                if target is None or target in MAKE_TARGETS else None)
    shell = re.fullmatch(r"(python|pip|uv)\s+(\S+)(.*)", span, re.S)
    if shell:
        tool, target, tail = shell.groups()
        flags = set(re.findall(r"--[a-z-]+", tail))
        if flags - ALL_FLAGS:
            return None
        if tool == "pip":
            return "shell"
        for base in ("", "scripts"):
            if (SKILL / base / target).exists() or (ROOT / target).exists():
                return "shell"
        return None
    # `py.typed` and `uv.lock` are the odd ones: tracked files whose suffixes
    # name nothing, one shipped for PEP 561 and one the fifth version site the
    # bump rewrites. Both resolve against the tree like every other file span,
    # by full name because ".typed" and ".lock" are not kinds with a second.
    if span in {"py.typed", "uv.lock"} or span.endswith(
            (".py", ".mplstyle", ".md", ".toml",
             ".yml", ".yaml", ".css", ".json")):
        if span in TRACKED_FILES:
            return "file"
        for base in ("", "scripts", "assets", "references"):
            if (SKILL / base / span).exists() or (ROOT / span).exists():
                return "file"
        return None
    if re.search(r"[+*/^]", span) and re.fullmatch(
            r"[A-Za-z0-9_^+*/() ,.-]+", span):
        return "expression"                   # `1/sqrt(n)`, `se_a + se_b`
    comparison = re.fullmatch(r"([a-z_]+)\s*[<>=]+\s*[\d.]+", span)
    if comparison:
        return ("comparison" if comparison.group(1) in PARAMETERS
                else None)
    if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", span) and _defining_modules(span):
        return "constant"                     # `DOC` falls through to the codes
    assign = re.fullmatch(r"([A-Z][A-Z0-9_, ]*)=\s*(.+)", span)
    if assign:            # `NAME = value`; the value is gated in the doc suite
        names = [n.strip() for n in assign.group(1).split(",")]
        return ("constant-assignment"
                if all(_defining_modules(n) for n in names) else None)
    if re.fullmatch(r"t\s*[∈=]\s*\[?[\d.]+(?:[,\s]+[\d.]+)?\]?", span):
        return "window"                       # value checked by the window test
    if re.fullmatch(r"[a-z_.]+", span) and span in matplotlib.rcParams:
        return "rcparam"
    rcparam = re.fullmatch(r"([a-z_.]+):\s*(\S+)", span)
    if rcparam and rcparam.group(1) in matplotlib.rcParams:
        return "rcparam"                       # `noarch: python` falls through
    subscript = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\[\"([^\"]+)\"\]", span)
    if subscript:
        base, key = subscript.groups()
        return ("registry-lookup"
                if _resolves_dotted(base) and _is_colormap(key) else None)
    if re.fullmatch(r"\(\s*[a-z_]+(?:\s*,\s*[a-z_]+)+\s*\)", span):
        return "tuple-shape"                  # order checked by the API tests
    call = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(.*\)", span, re.S)
    if call:
        if _resolves_dotted(call.group(1)):
            return "call"
        # `float()`, and only as a call: `True` and `False` are in
        # `dir(builtins)` too, and they are vocabulary rather than code.
        return ("builtin-call" if call.group(1) in dir(builtins) else None)
    kwarg = re.fullmatch(r"([a-z_]+)\s*=.*", span, re.S)
    if kwarg:
        return ("keyword" if kwarg.group(1) in MPL_NAMES | PARAMETERS
                else None)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", span) and _resolves_dotted(span):
        return "identifier"
    if (re.fullmatch(r"[A-Za-z0-9_^+*/() .-]+", span) and not span.isalpha()
            and re.search(r"[+*/^]", span)):
        return "expression"
    if (";" in span or "import" in span) and _identifiers_resolve(span):
        return "snippet"
    if span in CLI_CHOICES:
        return "cli-value"
    # The report's own vocabulary. A page that quotes a row's name or one of
    # the marks a detail string carries is naming something the checker emits,
    # so it is resolved against what the checker emits rather than exempted.
    if span in REPORT_MARKS:
        return "report-mark"
    if span in ROW_NAMES:
        return "row-name"
    # The caller's names, after every resolver that knows the code's own. A
    # sentence about a snippet is entitled to name what the snippet bound, and
    # nothing else is: the set is parsed out of the examples themselves.
    if span in EXAMPLE_NAMES:
        return "example-binding"
    if _is_predicate(span):
        return "predicate"

    # The configuration domains, last. Everything above knows what a Python
    # name looks like, and a key such as `host` or `sha256` looks exactly like
    # one -- so these have to run after the Python resolvers have declined,
    # rather than before them where they would shadow a real identifier.
    if all(part in CONFIG_KEYS for part in span.split(".")):
        return "config-key"
    key = re.fullmatch(r"([A-Za-z][A-Za-z0-9_.-]*):\s*\S+", span)
    if key and key.group(1) in CONFIG_KEYS:
        return "config-key"
    if span in CI_NAMES:
        return "ci"
    if span in RUFF_CODES:
        return "ruff-rule"
    return None


# Spans no resolver can place, each one named with the reason. An entry here is
# a claim nothing checks, so the set is meant to stay small and its members are
# meant to be boring.
UNRESOLVED_SPANS = {
    "cmasher.get_cmap_type()": "the oracle the kind thresholds were measured "
                               "against; an optional dev dependency, absent in "
                               "the runtime the skill ships into",
    "loss.py": "the file the tutorial tells the reader to create; it exists "
               "in the reader's working directory, not in this repository",
    "geometry": "a LaTeX package, named where the guide explains how to read a "
                "text width out of a document",
    "OSError: not a valid package style": "the exception matplotlib raises for "
                                          "a style path it cannot find, quoted "
                                          "so a reader recognises it",
    "(a)": "a panel label in a figure, quoted as it appears on the figure",
    "(b)": "a panel label in a figure, quoted as it appears on the figure",
    "#": "the character itself, in the sentence about style-sheet colours "
         "written with a leading hash",
    "/plugin install figure-gate@figure-gate": "a Claude Code command, named "
                                               "where docs/install.md "
                                               "explains how to install the "
                                               "skill as a plugin; the "
                                               "resolvers see this project's "
                                               "Python, not the host's command "
                                               "set",
    "figure-gate:research-figures": "how Claude Code namespaces the skill once "
                                    "installed as a plugin: the plugin name "
                                    "from plugin.json, then the skill name "
                                    "from SKILL.md's frontmatter",

    # --- conda-forge, which this project is a package in and not a part of ---
    # Everything here belongs to somebody else's repository, bot or toolchain.
    # A resolver for them would have to read the feedstock, and the feedstock is
    # not in this checkout -- which is the whole point of `conda/README.md`
    # saying so. They are named because a maintainer needs the exact strings.
    "conda-forge": "the channel and the organisation, named where conda/"
                   "README.md explains where the package comes from",
    "conda install": "the command a reader runs, from a toolchain this project "
                     "does not ship and cannot resolve against",
    "conda install -c conda-forge figure-gate": "the install line, quoted whole "
                                               "so a reader can copy it",
    "regro-cf-autotick-bot": "the conda-forge bot that opens the version-bump "
                             "pull request; an account on another repository",
    "rattler-build": "the recipe format and builder conda-forge runs, named "
                     "where the local recipe explains which schema it is",
    "pixi.toml": "the local build harness the feedstock ships; a file in the "
                 "feedstock, not here",
    "pixi self-update": "a command from that harness",
    "recipe/recipe.yaml": "the copy of the recipe that actually builds the "
                          "package, in the feedstock repository",
    "recipes/figure-gate/recipe.yaml": "where the recipe sat in staged-recipes "
                                       "while the submission was open; a path "
                                       "in a repository that is not this one",
    "OSX_SDK_DIR": "an environment variable conda-forge's macOS build reads",
    "${{ }}": "rattler-build's template syntax, quoted as syntax rather than "
              "as a value",
    "python >=${{ python_min }}": "a dependency line in that syntax, quoted to "
                                  "show the form the recipe uses",
    "@conda-forge-admin, please update version": "an issue comment that "
                                                 "commands the admin bot; the "
                                                 "text is the interface",
    "@conda-forge-admin, please add bot automerge": "the same, for automerge",
    "@conda-forge-admin, please ping conda-forge/help-python": "the same, to "
                                                               "ask for review",
    "Add figure-gate": "the title of the staged-recipes pull request, recorded "
                       "so the submission can be found again",
    "git checkout -- .ci_support recipes": "a git command in the feedstock "
                                          "checkout, quoted verbatim because "
                                          "the paths are the instruction",
    "rm -rf": "the command, named in a warning about what not to run",

    # --- forms and placeholders, which resolve to nothing by construction ---
    "v<new>": "the shape of a release tag with the version elided, not a tag",
    ".devN": "the PEP 440 developmental-release suffix with its number elided, "
             "written where CONTRIBUTING.md explains how to rehearse a release "
             "on TestPyPI without spending a real version",
    ".[dev]": "the pip extra form, quoted by CONTRIBUTING.md in the sentence "
              "saying this project does NOT use it: `dev` is a dependency "
              "group. A counter-example has to be unresolvable to be one",
    "`NAME = value`": "the shape of a threshold cell in the README, quoted "
                      "with its backticks so a contributor can see the form. "
                      "The names it stands for are gated by the doc suite",
    "figure-gate security": "the subject line SECURITY.md asks a reporter to "
                            "use; a convention for a human reading email",
}


@pytest.mark.parametrize("document,span", sorted(set(spans())))
def test_every_code_span_names_something_that_exists(document, span):
    """A backtick is a claim that the thing inside it is real.

    This is the sweep that would have caught `CMAP_SAMPLES` being attributed to
    the module that does not define it, and it is the reason a renamed constant
    cannot be left standing in prose that never quoted its value.
    """
    if span in UNRESOLVED_SPANS:
        return
    assert resolve(span) is not None, (
        f"{document} writes `{span}` as code, and nothing in check_figure.py, "
        "check_palette.py, matplotlib or the skill's files has that name. "
        "Either the name is wrong, or it belongs in UNRESOLVED_SPANS with the "
        "reason it cannot be resolved")


def test_the_process_heading_resolves_whether_or_not_it_is_written():
    """The state that broke this twice is the one no run ever holds both of.

    A tagged commit has no `## Unreleased` and a development commit has one,
    and the resolver has to agree with the same sentence in `CONTRIBUTING.md`
    either way. Both states are constructed here rather than waited for.
    """
    assert resolve("## Unreleased") == "process-heading"

    saved = set(HEADINGS)
    HEADINGS.discard("## Unreleased")
    try:
        assert resolve("## Unreleased") == "process-heading", (
            "at a tagged commit, with the heading renamed to the version, the "
            "span stops resolving and CONTRIBUTING.md's instruction reads as "
            "a claim about a section that does not exist")
    finally:
        HEADINGS.update(saved)


def test_a_process_heading_is_not_a_licence_for_any_heading():
    """The class is two words wide on purpose. A resolver that let any `## x`
    through would excuse a pointer to a section somebody deleted."""
    assert resolve("## Gates that warn") is None or \
        "## Gates that warn" in HEADINGS
    assert resolve("## No Such Section Anywhere") is None


def test_the_unresolved_ledger_has_no_stale_entries():
    """A ledger entry outlives the sentence it was written for, and then it is
    just a licence nobody is using."""
    written = {span for _, span in spans()}
    stale = sorted(set(UNRESOLVED_SPANS) - written)
    assert not stale, (
        f"{stale} are excused from resolving but no longer appear in the "
        "prose. Drop them from UNRESOLVED_SPANS")


def test_no_vocabulary_entry_is_one_a_resolver_now_handles():
    """`figure.mplstyle` and `hexbin` sat in that set claiming to be terms of
    art. One is a file that ships and one is a matplotlib method, and both
    resolve on their own, so listing them exempted two real claims from being
    checked at all."""
    saved = set(VOCABULARY)
    VOCABULARY.clear()
    try:
        redundant = sorted(v for v in saved if resolve(v) is not None)
    finally:
        VOCABULARY.update(saved)
    assert not redundant, (
        f"{redundant} resolve without being called vocabulary. Take them out "
        "of VOCABULARY so the resolver checks them")


def test_no_ledger_entry_is_one_a_resolver_now_handles():
    """An excused span that resolves is a resolver improvement nobody noticed,
    and it leaves the span exempt from the check it would now pass."""
    redundant = sorted(s for s in UNRESOLVED_SPANS if resolve(s) is not None)
    assert not redundant, (
        f"{redundant} resolve now. Take them out of UNRESOLVED_SPANS so they "
        "are checked rather than excused")


# --- the sweep can fail ------------------------------------------------------
# The house rule next door is that a gate is tested for its ability to fail. A
# doc sweep is worth less than most gates in that respect: it runs against the
# real documents, so when they are correct every assertion passes and a broken
# resolver looks exactly like a clean corpus. These run it against text written
# to be wrong.

def test_the_resolver_rejects_names_the_code_does_not_have():
    assert resolve("CMAP_NOPE") is None
    assert resolve("check_nothing()") is None
    assert resolve("cp.no_such_helper") is None
    assert resolve("nonsense.attribute.chain") is None


def test_the_hex_sweep_rejects_a_colour_nothing_ships():
    assert "#123456" not in KNOWN_HEXES


def test_the_end_claim_sweep_catches_both_hexes_of_the_old_sentence():
    """`#b1182b` was called an RdBu pole for as long as that section existed.

    Both halves matter. The first version of this extractor took one hex per
    keyword, so ``Poles `#a` / `#b``` had its second colour checked by nothing,
    which is half the defect still shipping under a passing test.
    """
    sentence = "Poles `#b1182b` / `#2065ab` clear every gate."
    found = [h for s in _sentences(sentence) if END_WORDS.search(s)
             for h in HEX_SPAN.findall(s)]
    assert found == ["#b1182b", "#2065ab"], (
        f"the sweep pulls {found} out of the sentence it exists for, so a "
        "return of the same defect would go unchecked")

    rdbu = colormaps["RdBu"]
    ends = {to_hex(rdbu(t))[:7].lower() for t in (0.0, 1.0)}
    assert not {h.lower() for h in found} & (ends | {to_hex(rdbu(0.5))[:7]}), (
        "RdBu now has one of those at an end or its midpoint, which would "
        "make the sentence this test was written for correct after all")


# --- constants belong to the module the sentence names -----------------------
# The defect: five `CMAP_*` constants named in a paragraph whose subject was
# `check_figure.py`, all five defined in `check_palette.py`. Resolving the name
# against either module is not enough, because both modules resolve it.

MODULE_MENTION = re.compile(r"check_(?:figure|palette)\.py")


def constants_in_module_paragraphs():
    """(document, paragraph index, constant, the one module named) triples.

    Only paragraphs naming exactly one module are read. A paragraph naming both
    is making a claim about the pair, and which constant belongs to which is
    then a question this pattern cannot answer without guessing.
    """
    out = []
    for path in PROSE_DOCS:
        for i, para in enumerate(path.read_text(encoding="utf-8").split("\n\n")):
            named = set(MODULE_MENTION.findall(para))
            if len(named) != 1:
                continue
            module = named.pop()
            for span in CODE_SPAN.findall(para):
                name = span.split("=")[0].strip()
                if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", name):
                    out.append((doc_id(path), i, name, module))
    return out


@pytest.mark.parametrize("document,para,name,module",
                         constants_in_module_paragraphs())
def test_a_constant_is_defined_where_the_paragraph_says_it_is(document, para,
                                                              name, module):
    defined = _defining_modules(name)
    assert module in defined, (
        f"{document} paragraph {para} discusses {module} and names {name}, "
        f"which is defined in {defined or 'neither module'}. A reader porting "
        "the checks greps the module the paragraph named")


# --- hex literals are colours something actually ships -----------------------

def _style_sheet_hexes():
    """Colours the sheet ships, in both spellings it uses.

    matplotlib style files take a bare `52514e`, and `figure.mplstyle` writes
    them that way; its own comments write the same colour with a `#`. Reading
    only the `#` form finds the commentary and misses the settings, which made
    the two ink tokens the guide documents look like colours nothing ships.
    """
    text = (SKILL / "assets" / "figure.mplstyle").read_text(encoding="utf-8")
    bare = re.findall(r"(?<![#\w])([0-9a-fA-F]{6})(?![\w])", text)
    return {h.lower() for h in HEX.findall(text)} | {f"#{h.lower()}"
                                                    for h in bare}


# Okabe-Ito in publication order. matplotlib ships it as a colormap from 3.11,
# and this project floors at matplotlib 3.8, so a module that reads
# `colormaps["okabe_ito"]` at import fails collection on every older matplotlib
# rather than failing one test. Raising the Python floor to 3.11 does not
# change that: the matplotlib floor is separate and deliberately lower. `test_palette.py` and `test_example.py` both
# guard the same lookup with a skip; this needs the colours themselves, so it
# carries them and checks the copy against matplotlib wherever matplotlib has
# them.
OKABE_ITO = ("#000000", "#e69f00", "#56b4e9", "#009e73",
             "#f0e442", "#0072b2", "#d55e00", "#cc79a7")


def _okabe_hexes():
    if "okabe_ito" not in colormaps:
        return set(OKABE_ITO)
    cmap = colormaps["okabe_ito"]
    return {to_hex(cmap(i))[:7].lower() for i in range(cmap.N)}


@pytest.mark.parametrize("name,version", sorted(COLORMAPS_ADDED_LATER.items()))
def test_the_later_colormaps_are_real_where_the_version_has_them(name, version):
    """`COLORMAPS_ADDED_LATER` lets a name resolve that this matplotlib cannot
    confirm, which is also how a typo would get through. On a matplotlib new
    enough to know, the name is held to the registry."""
    if name not in colormaps:
        pytest.skip(f"{name} needs {version}")
    assert name in colormaps


def test_the_okabe_literal_is_matplotlibs_okabe():
    """The fallback above is a hand-copied palette, which is a claim like any
    other. Where matplotlib has the colormap, the copy is held to it."""
    if "okabe_ito" not in colormaps:
        pytest.skip("matplotlib < 3.11 has no okabe_ito colormap")
    cmap = colormaps["okabe_ito"]
    builtin = tuple(to_hex(cmap(i))[:7].lower() for i in range(cmap.N))
    assert OKABE_ITO == builtin, (
        f"the literal is {OKABE_ITO}; matplotlib ships {builtin}")


def _colormap_hexes(name, samples=1001):
    cmap = colormaps[name]
    return {to_hex(cmap(i / (samples - 1)))[:7].lower() for i in range(samples)}


NAMED_MAPS = ("viridis", "RdBu", "twilight", "Greys")
KNOWN_HEXES = (_style_sheet_hexes() | _okabe_hexes()
               | set().union(*(_colormap_hexes(m) for m in NAMED_MAPS)))
# Neutral backdrop ramp and the OKLab-derived tints are computed in the guide's
# own appendix rather than sampled off a colormap.
KNOWN_HEXES |= {h.lower() for h in
                ("#ffffff", "#e6e5de", "#c3c2b7", "#95938b", "#898781",
                 "#fcfcfb", "#471365", "#2c718e", "#44bf70")}

# Counter-examples: hues the guide names in order to say *not* this. The rule
# above is that a hex a reader is offered has to be one they can obtain, and a
# pair quoted to demonstrate a gate firing is the opposite of an offer -- but it
# still has to be a real pair, or the demonstration is a story. Each of these
# carries the measurement it appears with, and `test_palette.py` pins it.
COUNTEREXAMPLE_HEXES = {
    # 19.2 dE at dichromacy, 8.3 at severity 0.9: the pair that says dichromacy
    # is not the worst case. See test_dichromacy_is_not_the_worst_case.
    #
    # It used to be #288ac6/#fd00db, at 8.4 and 7.9 against a floor of 8. Those
    # two straddled the OKLab floor and sit either side of the CAM02-UCS one by
    # 0.03 dE, which is a fixture that demonstrates nothing once rounded. The
    # replacement clears dichromacy by 8.7 and misses the worst severity by 2.2.
    "#8e4dc7", "#1402ef",
}
KNOWN_HEXES |= COUNTEREXAMPLE_HEXES


def doc_hexes():
    return sorted({(path.name, h.lower())
                   for path in PROSE_DOCS
                   for h in HEX.findall(path.read_text(encoding="utf-8"))})


@pytest.mark.parametrize("document,hexcode", doc_hexes())
def test_every_hex_in_the_prose_is_a_colour_something_ships(document, hexcode):
    assert hexcode in KNOWN_HEXES, (
        f"{document} quotes {hexcode}, which is not in figure.mplstyle, not a "
        "slot of okabe_ito, and not a sample of any colormap the guide names. "
        "A hex nobody ships is a colour the reader cannot obtain")


# --- a hex called an end of a colormap has to be one -------------------------
# `#b1182b` was called an RdBu pole for as long as the section existed. It is
# the map at t=0.098. The claim is positional, so the check is positional.

END_WORDS = re.compile(
    r"\b(?:pole|poles|end|ends|extreme|extremes|midpoint|centre|center)\b",
    re.I)
HEX_SPAN = re.compile(r"`(#[0-9a-fA-F]{6})`")


def _sentences(text):
    """Crude, and crude in the safe direction. Running two sentences together
    over-reports, which fails loudly. Splitting mid-sentence under-reports,
    which is the silent direction. `.py` and a decimal keep their periods
    because the split needs whitespace after one."""
    return re.split(r"(?<=[.:])\s+", " ".join(text.split()))


def end_claims():
    """(document, colormap, hex) for every sentence calling a hex an end or a
    midpoint of a named colormap.

    Sentence-scoped rather than a fixed window after the keyword. The window
    version took the first hex after "Poles" and stopped, so
    ``Poles `#a` / `#b``` had its second colour checked by nothing, which is
    half of the exact defect this test exists for.

    The colormap is taken from the nearest preceding heading, which is how the
    guide is organised: one map per `###` section.
    """
    out = []
    for path in PROSE_DOCS:
        current = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                found = [m for m in list(colormaps) + list(COLORMAPS_ADDED_LATER)
                         if f"`{m}`" in line
                         or f" {m}," in line or line.endswith(m)]
                current = found[0] if found else current
            if current is None:
                continue
            for sentence in _sentences(line):
                if END_WORDS.search(sentence):
                    out.extend((path.name, current, h.lower())
                               for h in HEX_SPAN.findall(sentence))
    return sorted(set(out))


@pytest.mark.parametrize("document,cmap_name,hexcode", end_claims())
def test_a_hex_called_an_end_or_midpoint_is_at_that_position(document,
                                                             cmap_name,
                                                             hexcode):
    cmap = colormaps[cmap_name]
    ends = {to_hex(cmap(t))[:7].lower() for t in (0.0, 1.0)}
    middle = to_hex(cmap(0.5))[:7].lower()
    assert hexcode in ends | {middle}, (
        f"{document} calls {hexcode} an end or midpoint of {cmap_name}. That "
        f"map runs {sorted(ends)} through {middle}. Quoting an interior sample "
        "as an end tells a reader to take a colour off the ramp that the ramp "
        "does not have there")


# --- windows quoted in prose are the windows in the code ---------------------

WINDOW = re.compile(r"`t\s*[∈=]\s*\[([\d.]+),\s*([\d.]+)\]`")


def window_claims():
    return sorted({(path.name, float(a), float(b))
                   for path in PROSE_DOCS
                   for a, b in WINDOW.findall(path.read_text(encoding="utf-8"))})


@pytest.mark.parametrize("document,lo,hi", window_claims())
def test_a_sampling_window_matches_one_the_code_defines(document, lo, hi):
    """The guide states three windows: the viridis default, the cool variant,
    and the RdBu interior. Each is a claim that sampling there is safe, so each
    has to be a window something in the repo actually uses or the appendix
    defines."""
    defined = {(0.05, 0.70), (0.00, 0.38), (0.1, 0.9)}
    assert (lo, hi) in defined, (
        f"{document} tells a reader to sample t in [{lo}, {hi}], which is not "
        f"one of the windows this repo defines ({sorted(defined)})")


def test_the_rdbu_window_is_the_one_that_passes_the_palette_gates():
    """The window is not a preference. Outside it the map's own ends fail, and
    that is the whole reason the sentence exists."""
    rdbu = colormaps["RdBu"]
    inside = [to_hex(rdbu(t))[:7] for t in (0.1, 0.9)]
    outside = [to_hex(rdbu(t))[:7] for t in (0.0, 1.0)]
    inside_ok, _ = cp.check(inside)
    outside_ok, _ = cp.check(outside)
    assert inside_ok, f"{inside} no longer clear the palette gates"
    assert not outside_ok, (
        f"{outside} now clear the palette gates, so the guide's instruction to "
        "sample inside the ends has lost its reason. Rewrite the section "
        "rather than deleting this test")


# --- claims the audit retracted stay retracted -------------------------------
# `EXTERNAL_CLAIMS` above records what was verified. This records what was
# checked and found wanting, which is the other half and was missing: the
# audit that produced this file retracted "ACM and Elsevier reject the
# submission", and the retraction landed in `style-guide.md` alone. `SKILL.md`
# and `check_figure.py` carried the sentence for two more releases, the module
# in a gate message a reader sees on every Type 3 figure.
#
# A retraction that lives in one document is a correction the next writer
# copies over from the uncorrected one. So the wording is held out of every
# document and both modules at once, and the sweep reaches into the scripts
# because that is where the surviving copy was.

RETRACTED_CLAIMS = {
    "ACM or Elsevier rejecting a submission for Type 3 fonts": {
        "pattern": r"(ACM|Elsevier)[^.]{0,80}reject[^.]{0,40}submission",
        "instead": "IEEE PDF eXpress does not accept Type 3 and refuses the "
                   "upload; ACM and Elsevier check embedding in production, "
                   "so there it surfaces after acceptance",
        "why": "neither publishes a rule rejecting a submission for Type 3. "
               "What the sources say is quoted in EXTERNAL_CLAIMS under "
               "'Type 3 fonts'",
        "retracted": "2026-07-29",
    },
    "Science publishing a figure type-size range": {
        "pattern": r"Science[^.]{0,40}\d\s*[-–]\s*\d\s*(pt|point)",
        "instead": "Science publishes no text floor. It states a 6 point "
                   "minimum for symbols, a 0.5 point minimum for line widths "
                   "at the final reduced size, and 10 pt bold part labels",
        "why": "the guide credited Science with '5-7pt for labels and 6-8pt "
               "for axes'. Neither range is in Science's instructions for "
               "preparing an initial or a revised manuscript, checked "
               "2026-08-17. The numbers that are there are quoted in "
               "EXTERNAL_CLAIMS under 'journal type floors'",
        "retracted": "2026-08-17",
    },
    "PNAS requiring 2mm on top of its point floor": {
        "pattern": r"PNAS[^.]{0,60}(2\s*mm[^.]{0,30}(and|plus)|"
                   r"(and|with)[^.]{0,30}2\s*mm)",
        "instead": "PNAS requires numbers, letters and symbols no smaller "
                   "than 6pt after reduction, which its guidelines also "
                   "state as 2mm. The two are the same requirement",
        "why": "the guide read '6pt' and '2mm' as two separate floors and "
               "wrote 'nothing under 2mm printed' as an extra constraint. "
               "PNAS gives 2mm as the millimetre equivalent of its 6 point "
               "minimum, and also states a maximum the guide never carried",
        "retracted": "2026-08-17",
    },
}


def _retraction_corpus():
    """Documents and modules, because the claim survived in a module."""
    return PROSE_DOCS + [pathlib.Path(inspect.getfile(module))
                         for module in MODULES.values()]


@pytest.mark.parametrize("claim", sorted(RETRACTED_CLAIMS))
def test_a_retracted_claim_is_written_nowhere(claim):
    entry = RETRACTED_CLAIMS[claim]
    found = []
    for path in _retraction_corpus():
        text = " ".join(path.read_text(encoding="utf-8").split())
        if re.search(entry["pattern"], text, re.I):
            found.append(path.relative_to(ROOT).as_posix())
    assert not found, (
        f"{found} state {claim}, retracted {entry['retracted']}: "
        f"{entry['why']}. Write instead: {entry['instead']}")


@pytest.mark.parametrize("claim", sorted(RETRACTED_CLAIMS))
def test_a_retraction_records_why_and_what_to_say_instead(claim):
    """A retraction with no replacement is how the sentence comes back: the
    next writer needs the true version to hand, not only a prohibition."""
    entry = RETRACTED_CLAIMS[claim]
    for field in ("pattern", "instead", "why", "retracted"):
        assert entry.get(field), f"{claim} has no {field}"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["retracted"])


def test_the_retraction_pattern_still_matches_the_sentence_it_retired():
    """The sweep runs against a corpus that no longer contains the claim, so
    every assertion passes whether or not the pattern works. This is the
    sentence as `check_figure.py` shipped it."""
    shipped = ("IEEE PDF eXpress rejects the upload and ACM/Elsevier reject "
               "the submission; set both to 42")
    pattern = RETRACTED_CLAIMS[
        "ACM or Elsevier rejecting a submission for Type 3 fonts"]["pattern"]
    assert re.search(pattern, shipped, re.I), (
        "the pattern no longer matches the message it was written to retire")
    assert not re.search(pattern, " ".join(
        (SKILL / "references" / "style-guide.md").read_text(encoding="utf-8").split()), re.I), (
        "the pattern matches the corrected sentence too, so it forbids the "
        "replacement as well as the claim")


# --- claims about the world carry a source and a recorded verification -------
# No test reads a journal's instructions to authors. What this ledger does is
# make the human verification enumerable and dated, so a reviewer can audit the
# claim without repeating the search, and so an uncited external number fails.

EXTERNAL_CLAIMS = {
    "SIAM line weight": {
        "document": "style-guide.md",
        "anchor": "lines one point or thicker",
        "source": "SIAM instructions for authors, epubs.siam.org",
        "verified": "2026-07-29",
        "quote": "Illustrations must use lines one point or thicker; thinner "
                 "lines may break up or disappear when printed.",
    },
    "journal type floors": {
        "document": "style-guide.md",
        "anchor": "Nature sets a 5pt minimum and a 7pt maximum",
        "source": "Nature research figure guide, "
                  "research-figure-guide.nature.com, building and exporting "
                  "figure panels; PNAS, pnas.org/author-center/"
                  "submitting-your-manuscript; Science instructions for "
                  "preparing an initial manuscript, science.org",
        "verified": "2026-08-17",
        "quote": 'Nature: "Maximum text size: 7pt", "Minimum text size: 5pt". '
                 'PNAS: "Ensure that all numbers, letters, and symbols are no '
                 'smaller than 6 points (2 mm) and no larger than 12 points '
                 '(6 mm) after reduction." Science publishes no text floor: '
                 '"Size symbols so that they will be distinguishable when the '
                 'figure is reduced (6 point minimum)" and "minimum of 0.5 '
                 'point at the final reduced size" for line widths.',
    },
    "Type 3 fonts": {
        "document": "style-guide.md",
        "anchor": "does not accept Type 3",
        "source": "IEEE PDF eXpress author requirements; ACM TAPS LaTeX best "
                  "practices",
        "verified": "2026-07-29",
        "quote": "Embedded Type 1 or TrueType fonts are required as subset "
                 "fonts. Type 3 fonts (bitmaps) will not be accepted.",
    },
    "alt text prevalence": {
        "document": "style-guide.md",
        "anchor": "99.81% of programmatically",
        "source": "Potluri, Singanamalla, Tieanklin & Mankoff, ASSETS '23, "
                  "arXiv:2308.03241",
        "verified": "2026-07-29",
        "quote": "The vast majority of the programmatically generated images "
                 "(N=342102 (99.81%)) do not have associated alternative text.",
    },
    "data-ink evidence": {
        "document": "style-guide.md",
        "anchor": "not the data-ink ratio",
        "source": "Bateman, Mandryk, Gutwin, Genest, McDine & Brooks, CHI '10, "
                  "2573-2582",
        "verified": "2026-07-29",
        "quote": "We found that people's accuracy in describing the "
                 "embellished charts was no worse than for plain charts, and "
                 "that their recall after a two-to-three-week gap was "
                 "significantly better.",
    },
    "colour difference and target size": {
        "document": "style-guide.md",
        "anchor": "Why there is still no size-weighted gate",
        "source": "Stone, Szafir & Setlur, Color and Imaging Conference "
                  "2014(1), 253-258",
        "verified": "2026-07-31",
        "quote": "In the paper, we describe a way to model discriminability as "
                 "a function of size for target sizes ranging from 6 degrees "
                 "to 1/3 of visual angle. ... A theoretical CIELAB JND, where "
                 "p = 50% and s = 2 degrees, should correspond to a difference "
                 "of 1 ... For practical design under uncontrolled conditions, "
                 "we find the required difference, or in our notation, "
                 "ND(50,2), is closer to 6 ... For 0.33 degrees, the required "
                 "difference is closer to 11.",
    },
    "cvd severity matrices": {
        "document": "style-guide.md",
        "anchor": "Dichromacy is not the worst case",
        "source": "Machado, Oliveira & Fernandes, IEEE TVCG 15(6), 2009, "
                  "Table 1; coefficients read from the authors' page at "
                  "inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/",
        "verified": "2026-07-31",
        # What was checked is the table, cell by cell, not a sentence about it:
        # four matrices were read off the authors' page and asserted against the
        # shipped constants in `test_the_severity_table_is_the_one_the_paper_
        # publishes`. The first row of protanomaly at severity 0.1 is quoted
        # here as the sample a later reader can re-check in one lookup.
        "quote": "Protanomaly, severity 0.1, first row: 0.856167, 0.182038, "
                 "-0.038205.",
    },
    "graphical perception ordering": {
        "document": "choosing-a-form.md",
        "anchor": "six ranks and not",
        "source": "Cleveland & McGill, JASA 79(387), 1984",
        "verified": "2026-07-29",
        "quote": "The ordering is position along a common scale; position "
                 "along non-aligned scales; length, direction, angle; area; "
                 "volume, curvature; shading, colour saturation. Hue is not "
                 "ranked.",
    },
    "banking to 45 degrees": {
        "document": "choosing-a-form.md",
        "anchor": "Cleveland's banking to 45 degrees",
        "source": "Cleveland, McGill & McGill, JASA 83(402), 1988, as "
                  "surveyed by Heer & Agrawala 2006",
        "verified": "2026-08-01",
        "quote": "Cleveland et al. conducted human-subject experiments showing "
                 "that viewers judge the ratio of the slopes of two adjacent "
                 "line segments most accurately when the orientation "
                 "resolution between them is maximized ... choosing the aspect "
                 "ratio that sets the median absolute slope of the line "
                 "segments to 1.",
    },
    "slopeless lines culling": {
        "document": "choosing-a-form.md",
        "anchor": "after Heer and Agrawala's \"slopeless lines\"",
        "source": "Heer & Agrawala, IEEE TVCG 12(4), 2006, section 2.7",
        "verified": "2026-08-01",
        "quote": "an additional modification is to cull \"slopeless\" lines -- "
                 "those with either zero or infinite slope. Horizontal and "
                 "vertical lines remain unchanged by variations in aspect "
                 "ratio, yet contribute to the banking criteria.",
    },
}

# Ledger entries name a document by its basename, which was unambiguous while
# the corpus was four hand-listed files. It is not any more: the corpus has two
# `README.md`. Rather than respell every entry as a path, the index keeps the
# short names and refuses to guess when one is shared -- so a ledger entry that
# becomes ambiguous fails loudly instead of resolving to whichever file sorted
# first.
DOCS_BY_NAME: dict[str, list[pathlib.Path]] = {}
for _path in PROSE_DOCS:
    DOCS_BY_NAME.setdefault(_path.name, []).append(_path)


def document(name):
    found = DOCS_BY_NAME.get(name, [])
    assert found, (
        f"the ledger names {name}, which is not a document in the corpus "
        f"(have {sorted(DOCS_BY_NAME)})")
    assert len(found) == 1, (
        f"the ledger names {name}, and the corpus has "
        f"{[doc_id(p) for p in found]}. Name it by its path from the "
        "repository root instead")
    return found[0]


def test_every_swept_document_is_reachable_by_the_name_the_ledger_uses():
    """`document()` is only ever called for names already in a ledger, so an
    ambiguity introduced by a new file would sit undetected until somebody
    added an entry for it. Check the whole corpus, not the referenced part."""
    # Sorted, because the assertion is about which documents share a basename
    # and not about the order a directory walk happened to return them in. It
    # compared unsorted lists until the suite first ran on Windows, where the
    # walk yields `conda/README.md` before `README.md` and this failed on a
    # corpus that had not changed.
    shared = {name: sorted(doc_id(p) for p in paths)
              for name, paths in DOCS_BY_NAME.items() if len(paths) > 1}
    assert shared == {"README.md": ["README.md", "conda/README.md"]}, (
        f"documents sharing a basename changed: {shared}. Any ledger entry "
        "naming a shared basename has to be respelled as a path")


@pytest.mark.parametrize("claim", sorted(EXTERNAL_CLAIMS))
def test_every_external_claim_is_still_written_where_the_ledger_says(claim):
    entry = EXTERNAL_CLAIMS[claim]
    text = " ".join(document(entry["document"]).read_text(encoding="utf-8").split())
    assert entry["anchor"] in text, (
        f"{claim} is recorded as verified against {entry['source']}, but "
        f"{entry['anchor']!r} is no longer in {entry['document']}. A rewritten "
        "sentence is a new claim and needs verifying again")


@pytest.mark.parametrize("claim", sorted(EXTERNAL_CLAIMS))
def test_every_external_claim_records_a_source_and_a_quote(claim):
    """A ledger entry that says "verified" and nothing else is an assertion,
    which is the thing this file exists to stop."""
    entry = EXTERNAL_CLAIMS[claim]
    for field in ("document", "anchor", "source", "verified", "quote"):
        assert entry.get(field), f"{claim} has no {field}"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["verified"]), (
        f"{claim} records {entry['verified']!r} as a verification date")
    assert len(entry["quote"]) > 40, (
        f"{claim} quotes {entry['quote']!r}, which is too short to be the "
        "passage that supports the claim")


@pytest.mark.parametrize("claim", sorted(EXTERNAL_CLAIMS))
def test_an_external_source_is_named_in_the_references(claim):
    """The reader gets what the ledger has: a citation in the document, not a
    comment in a test file."""
    entry = EXTERNAL_CLAIMS[claim]
    text = " ".join(document(entry["document"]).read_text(encoding="utf-8").split())
    surname = entry["source"].split(",")[0].split()[0].strip()
    assert surname in text or surname.lower() in text.lower(), (
        f"{claim} cites {entry['source']}, and {surname} appears nowhere in "
        f"{entry['document']}. A source the reader cannot see is not a source")


# --- gate behaviour the prose describes, executed --------------------------
# The heatmap sentence said a heatmap "runs near the ceiling". It runs at 1.00
# and WARNs. Nothing read the sentence against the gate, so here the sentence's
# claim is the test's assertion.

def _heatmap():
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    im = ax.imshow([[0.1, 0.6], [0.3, 0.9]])
    fig.colorbar(im)
    return fig


def _grid_with_a_blank_panel(figsize=(3, 1.5)):
    """Two panels, one of them never drawn in.

    The size is an argument because the paragraph's claim turns on it: furniture
    is a perimeter and a panel is an area, so the blank half's reading falls as
    the pair grows. The default is the small size, where that reading lands
    inside the range and `_axes_drew_anything` is the only thing that can catch
    it.
    """
    fig, axs = plt.subplots(1, 2, figsize=figsize, constrained_layout=True)
    axs[0].plot([0, 1], [0, 1])
    return fig


def _contourf_with_sparse_marks():
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    x = np.linspace(0, 1, 40)
    X, Y = np.meshgrid(x, x)
    ax.contourf(X, Y, X + Y, levels=8)
    ax.plot([0.2, 0.8], [0.3, 0.7], "o", color="#000000")
    return fig


def test_a_heatmap_measures_full_ink_and_warns():
    """`### Panel occupancy` states both halves of this: the number and the
    warning. Both are the reason the gate is advisory."""
    fig = _heatmap()
    try:
        status, detail = cf.check_ink(fig)
    finally:
        plt.close(fig)
    assert status == "warn", f"a heatmap no longer warns: {detail}"
    assert "1.00" in detail, (
        f"the guide says an imshow heatmap measures 1.00; the gate reports "
        f"{detail!r}")


def _blank_panel_fraction(figsize):
    fig = _grid_with_a_blank_panel(figsize)
    try:
        status, detail = cf.check_ink(fig)
    finally:
        plt.close(fig)
    return status, detail, float(re.search(r"ax1 ([\d.]+)", detail).group(1))


def test_a_blank_panel_warns_from_inside_the_range():
    """The sentence a reader acts on is that a blank cell warns even when the
    range would have passed it. If the floor ever catches this one instead, the
    sentence is telling the reader about a mechanism that stopped running.
    """
    status, detail, blank = _blank_panel_fraction((3, 1.5))
    assert status == "warn", f"a blank panel no longer warns: {detail}"
    assert cf.INK_MIN <= blank <= cf.INK_MAX, (
        f"the blank panel measures {blank}, outside "
        f"[{cf.INK_MIN}, {cf.INK_MAX}]. The guide says it is caught by asking "
        "whether anything was drawn, not by the range")


def test_the_blank_panels_own_reading_falls_as_the_panel_grows():
    """The size dependence the paragraph now states, measured.

    The guide claimed for a while that a blank panel's furniture measures inside
    the range, full stop. It does at 3x1.5in and does not at 6x3in, and the
    figure that was standing in the guide as the example was the second one, so
    the sentence was being demonstrated by a case that contradicted it. Pinned
    here so the number in the prose is a measurement and not a memory.
    """
    _, _, small = _blank_panel_fraction((3, 1.5))
    status, detail, large = _blank_panel_fraction((6, 3))
    assert small > large, (
        f"a blank panel reads {small} at 3x1.5in and {large} at 6x3in, so "
        "furniture no longer thins out as the panel grows and the guide's "
        "explanation of why the drew-anything question exists is wrong")
    assert large < cf.INK_MIN, (
        f"the blank half of a 6x3in pair now measures {large}, inside "
        f"[{cf.INK_MIN}, {cf.INK_MAX}]. The guide names it as the case the "
        "range catches on its own")
    assert status == "warn", f"a blank panel no longer warns: {detail}"


def test_context_axes_turns_a_saturated_surface_into_a_pass():
    """`**When the fill is context, say so.**` is an instruction to pass an
    argument. This is that instruction, run."""
    fig = _contourf_with_sparse_marks()
    try:
        without, _ = cf.check_ink(fig)
        with_context, detail = cf.check_ink(fig, context_axes=[fig.axes[0]])
    finally:
        plt.close(fig)
    assert without == "warn", (
        "a filled contourf panel no longer warns without context_axes, so the "
        "paragraph is explaining a problem that no longer occurs")
    assert with_context is True, (
        f"context_axes no longer rescues a filled panel: {detail}")


# --- the shapes the prose teaches -------------------------------------------
# The two entry points returned their pair in opposite orders until 0.4.0, and
# the README carried a paragraph about the difference rather than the difference
# being fixed. Unpacking either one the wrong way binds a bool to the rows and
# raises nothing. They are the same shape now; this is what stops them drifting
# apart again.

def test_the_two_entry_points_return_the_same_shape():
    text = " ".join(README.read_text(encoding="utf-8").split())
    assert "`audit(fig)` returns `(ok, rows)`" in text, (
        "the README no longer states audit's return order in the form this "
        "test reads")

    fig, ax = plt.subplots(figsize=(3, 2), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    try:
        audit_ok, audit_rows = cf.audit(fig)
    finally:
        plt.close(fig)
    check_ok, check_rows = cp.check(["#E69F00", "#0072B2"])

    assert isinstance(audit_ok, bool) and isinstance(audit_rows, list), (
        "audit no longer returns (ok, rows)")
    assert isinstance(check_ok, bool) and isinstance(check_rows, list), (
        "check no longer returns (ok, rows). It was aligned to audit in 0.4.0 "
        "because two orders is a trap that raises nothing")
    assert all(len(row) == 3 for row in audit_rows + check_rows), (
        "the (label, status, detail) triple is the other half of the shape "
        "both entry points promise")


def test_both_entry_points_are_documented():
    """`audit` and `check` are the whole public surface. Both had no docstring
    while private helpers carried paragraphs, which is the wrong way round for
    anyone reading the module rather than the guide."""
    for name, func in (("check_figure.audit", cf.audit),
                       ("check_palette.check", cp.check)):
        assert (func.__doc__ or "").strip(), f"{name} has no docstring"


# Gates whose message stops at what broke. Every other gate appends a FIX_MARK
# clause, so the guide's premise - that a gate's own message routes the reader -
# holds for all but the one named here.
#
# The set was five. Four of those did route the reader and were misfiled: they
# wrote the fix as prose without adopting the marker, and a test reading for
# the marker reported "no remediation" when the remediation was right there.
# `check_contour_dash` was the sharpest case, exempted as "advisory" while
# naming an exact call. Rather than teach the detector to sniff prose for
# imperatives, which is a guess about intent that rots, those four adopted the
# marker. What is left is the gate that genuinely says nothing.
#
# The opposite error followed, and cost the marker its meaning: six clauses wore
# the remediation marker while naming no action, only the reason the row fired.
# `check_banking` said "Cleveland banks to 45 degrees", `check_line_weight`
# cited SIAM, the normal-vision floor said "hard to tell apart in full color".
# True, and not a fix, and the detector counted every one of them as one.
#
# So the one marker became two, and both are named rather than drawn. The old
# `  <- ` said nothing about which of the two things it introduced, and a split
# that turned on one glyph - an arrow against a tilde - would have been a
# distinction no reader scanning a wall of detail text could hold. `[FIX]` and
# `[WHY]` say it, and read against the `[PASS]`/`[FAIL]` the report already
# prints. A message may hold both, in that order.
# `test_a_reason_clause_never_stands_in_for_a_fix` stops the reasons drifting
# back into the fix mark.
FIX_MARK, WHY_MARK = "  [FIX] ", "  [WHY] "

MESSAGES_WITHOUT_A_FIX_CLAUSE = {
    "check_collisions": "names the two colliding strings and stops. Which of "
                        "the pair is free to move is a fact about the figure's "
                        "layout that the gate cannot see, and 'move one of "
                        "these' is not a fix, it is a restatement",
}


def _gate_functions():
    return {name: obj for name, obj in inspect.getmembers(cf, inspect.isfunction)
            if name.startswith("check_")}


def _message_strings(func):
    """Every string in a gate that can reach the detail a reader is shown.

    The docstring is excluded, and that exclusion is the point. It is the one
    string in a gate that nobody reading a failing build ever sees, and several
    of them explain the fix at length: `check_overplotting`'s names alpha,
    hexbin and hollow markers. Walking it would pass a gate whose actual
    message said nothing, which is the failure mode this detector exists to
    catch.
    """
    tree = ast.parse(inspect.getsource(func).lstrip())
    body = tree.body[0].body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return [node.value for stmt in body for node in ast.walk(stmt)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)]


def test_the_fix_clause_detector_ignores_the_docstring():
    """The detector's one assumption, asserted rather than trusted."""
    doc = cf.check_overplotting.__doc__
    assert doc and "hexbin" in doc, (
        "this test rides on check_overplotting's docstring naming a fix; it "
        "no longer does, so pick another gate or drop this")
    assert doc not in _message_strings(cf.check_overplotting), (
        "the docstring reached the detector, so a gate can now pass on prose "
        "its reader never sees")


@pytest.mark.parametrize("gate", sorted(_gate_functions()))
def test_a_gates_message_either_names_a_fix_or_is_named_here(gate):
    has_clause = any(FIX_MARK in s
                     for s in _message_strings(_gate_functions()[gate]))
    excused = gate in MESSAGES_WITHOUT_A_FIX_CLAUSE
    assert has_clause != excused, (
        f"{gate} {'carries' if has_clause else 'carries no'} a `{FIX_MARK}` "
        f"remediation clause and is {'named' if excused else 'not named'} in "
        "MESSAGES_WITHOUT_A_FIX_CLAUSE. A gate that tells a reader what broke "
        "and not what to do is the gap; a gate that grew a clause should come "
        "out of the set")


@pytest.mark.parametrize("gate", sorted(_gate_functions()))
def test_a_reason_clause_never_stands_in_for_a_fix(gate):
    """The split's whole content. WHY_MARK explains why the row fired, which is
    worth saying and is not a fix, so a gate that carries one and no FIX_MARK
    has told the reader nothing to do while looking like it has. That is the
    state the six converted clauses were in, and the shape a seventh would
    arrive in."""
    strings = _message_strings(_gate_functions()[gate])
    if not any(WHY_MARK in s for s in strings):
        return
    assert any(FIX_MARK in s for s in strings), (
        f"{gate} carries a `{WHY_MARK}` reason clause and no `{FIX_MARK}` "
        "fix clause. A reason is an addition to a fix, never a substitute: "
        "before the markers split, six clauses read as remediation while "
        "naming only why the row fired")


def test_the_reason_marker_does_not_read_as_a_fix_marker():
    """The two markers have to stay disjoint as substrings, or the detector
    above scores every reason clause as a fix and the split buys nothing."""
    assert FIX_MARK not in WHY_MARK and WHY_MARK not in FIX_MARK, (
        f"{FIX_MARK!r} and {WHY_MARK!r} now contain one another")


def test_the_palette_rows_split_their_markers_too():
    """`check_palette.check` writes rows that `check_colormap` splices
    into its own detail, so its clauses are read under the same convention and
    are not reached by the gate-function walk above."""
    tree = ast.parse(inspect.getsource(cp.check).lstrip())
    strings = [node.value for node in ast.walk(tree)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    reasons = [s for s in strings if WHY_MARK in s]
    assert reasons, (
        f"no check_palette row carries a `{WHY_MARK}` reason clause; the "
        "normal-vision floor's did, so either it moved or the marker changed")
    stranded = [s for s in reasons if not any(FIX_MARK in t for t in strings)]
    assert not stranded, f"{stranded} explain without routing"


def test_the_colormap_gate_strips_a_spliced_rows_whole_clause():
    """`check_colormap` quotes failing palette rows and cuts them at the
    fix mark. The reason clause sits after the fix clause precisely so that one
    cut takes both; a row that ordered them the other way would leak its reason
    into a message that then appends its own."""
    ok, rows = cp.check(["#E69F00", "#E8A00A"], all_pairs=True)
    floor = [d for name, status, d in rows
             if name.startswith("Normal-vision floor") and status is False]
    assert floor, "two near-identical hues no longer fail the normal-vision floor"
    assert FIX_MARK in floor[0] and WHY_MARK in floor[0], (
        f"the floor row is now {floor[0]!r}, which no longer carries both marks")
    assert WHY_MARK not in floor[0].split(FIX_MARK)[0], (
        "the reason survives the cut check_colormap makes at the fix mark")


@pytest.mark.parametrize("gate", cf.GATES, ids=lambda g: g.name)
def test_a_gates_declared_needs_are_the_arguments_it_takes(gate):
    """`needs` names what `audit` passes. It is dispatched by keyword, so a
    name that is not in the signature raises there; what this adds is the other
    direction, a gate that grew a parameter the registry does not supply and
    which therefore silently keeps its default."""
    params = list(inspect.signature(gate.func).parameters)
    assert params[0] == "fig", f"{gate.name} does not take a figure first"
    assert set(gate.needs) <= set(params), (
        f"{gate.name} declares needs={gate.needs}, and its signature is "
        f"{tuple(params)}")
    unfed = sorted((set(params) & set(cf.GATE_INPUTS)) - set(gate.needs))
    assert not unfed, (
        f"{gate.name} takes {unfed}, which audit knows how to supply and this "
        "row does not ask for. The gate runs on the default instead, which is "
        "a measurement against the wrong page")


def test_the_registry_is_the_only_place_the_advisory_rows_are_listed():
    assert cf.ADVISORY_GATES == frozenset(g.name for g in cf.GATES
                                          if g.advisory), (
        "ADVISORY_GATES has stopped being derived from GATES, which is how it "
        "came to disagree with the README twice")


def test_the_fix_clause_exemptions_are_gates_that_exist():
    unknown = sorted(set(MESSAGES_WITHOUT_A_FIX_CLAUSE) - set(_gate_functions()))
    assert not unknown, f"{unknown} are not gate functions"


def test_the_clipping_message_sends_the_reader_to_the_documented_fix():
    """The gate names constrained_layout and a wider figure; the guide's
    section is written around those two. A message that stops naming them
    leaves the section explaining a fix nobody was offered."""
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.set_title("x" * 80)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    try:
        ok, detail = cf.check_clipping(fig, canvas.get_renderer())
    finally:
        plt.close(fig)
    assert ok is False, "an 80-character title no longer clips a 3in figure"
    assert "constrained_layout" in detail and "widen" in detail, (
        f"the clipping message is now {detail!r}, which no longer names the "
        "fix the guide's section is built on")
