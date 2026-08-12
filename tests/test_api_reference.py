"""`docs/api.md` against the modules it documents.

The page is `:::` directives and nothing else: mkdocstrings reads the
signatures and docstrings out of `skill/scripts/` when the site is built, so
what it shows cannot drift from what the code has. What it *can* do is go
quiet. A public function added to either module appears nowhere, and no build
error says so -- the page is still valid, still renders, and is now an
incomplete reference that reads like a complete one.

So the coverage is asserted here rather than at build time: every public
callable is either documented on the page or named below with the reason it is
not. The exemptions are the interesting part of this file.

Docstrings are checked too. `:::` on a function with no docstring renders a
bare signature under a heading, which is worse than leaving it out: it looks
like documentation and carries nothing.
"""

import ast
import re

import pytest

from conftest import SCRIPTS

ROOT = SCRIPTS.parent.parent
PAGE = ROOT / "docs" / "api.md"
CONFIG = ROOT / "zensical.toml"

MODULES = ("check_figure", "check_palette", "suggest_fixes")

# Public callables the page deliberately does not document.
#
# The gates used to be exempt as a class, on the argument that `audit()` runs
# them and computes the renderer, scale and canvas arguments they take, so
# `docs/gates.md` documenting their thresholds was enough. It was not: a public
# callable whose signature appears nowhere is one you read the source for, and
# the exemption also meant a gate added later joined the page's blind spot
# rather than the page. They are documented now, and
# `test_the_page_documents_every_gate_in_order` keeps a new one from being
# forgotten.
EXEMPT = {
    "main": "the CLI entry point, documented by --help and the docs site",
    "self_test_figure": "builds the deliberately broken figure `main` checks; "
                        "not something a caller constructs",
}


def public_callables(module):
    """Module-level `def`s not starting with an underscore, from the source.

    Parsed rather than imported: `check_palette.py` is claimed to run on 3.8
    with nothing installed, and reading it with `ast` keeps this test honest
    about what is in the file rather than what the local interpreter managed
    to import.
    """
    tree = ast.parse((SCRIPTS / f"{module}.py").read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")}


def documented():
    """`::: module.name` directives on the page, as `(module, name)` pairs."""
    return set(re.findall(r"^::: (\w+)\.(\w+)$", PAGE.read_text(encoding="utf-8"), re.M))


def undocumented(module):
    covered = {name for mod, name in documented() if mod == module}
    return [name for name in public_callables(module)
            if name not in covered and name not in EXEMPT]


def test_the_page_has_directives_at_all():
    """Guards every other test here: a page that stopped using `:::` would
    make all of them pass by documenting nothing."""
    assert len(documented()) >= 10, documented()


@pytest.mark.parametrize("module", MODULES)
def test_every_public_callable_is_documented_or_exempt(module):
    missing = undocumented(module)
    assert not missing, (
        f"{module}: {missing} are public and absent from docs/api.md. Add a "
        f"`::: {module}.<name>` block, or name it in EXEMPT with the reason.")


@pytest.mark.parametrize("module,name", sorted(documented()))
def test_every_documented_name_exists(module, name):
    """A directive naming something that was renamed or removed. mkdocstrings
    fails the build on this, but only when someone builds the site."""
    assert module in MODULES, module
    assert name in public_callables(module), (
        f"docs/api.md documents {module}.{name}, which is not a public "
        f"callable in {module}.py")


@pytest.mark.parametrize("module,name", sorted(documented()))
def test_every_documented_name_has_a_docstring(module, name):
    """`:::` on a bare function renders a heading and a signature and nothing
    else, which reads as documentation and is not."""
    node = public_callables(module)[name]
    assert ast.get_docstring(node), (
        f"{module}.{name} is on the API page with no docstring, so it renders "
        f"as a heading over an empty block")


def gate_functions():
    """The gate functions in the order `audit` runs them, from the registry."""
    import check_figure as cf

    return [gate.func.__name__ for gate in cf.GATES]


def documented_gates():
    """`::: check_figure.check_*` directives, in the order the page lists them."""
    text = PAGE.read_text(encoding="utf-8")
    return re.findall(r"^::: check_figure\.(check_\w+)$", text, re.M)


def test_the_page_documents_every_gate_in_order():
    """A gate is a public callable, so it is on the page like any other. The
    order is asserted with the membership because the page is read against
    `docs/gates.md` and a printed report, and both of those are in `GATES`
    order: three rosters that agree on the set and disagree on the sequence is
    still three rosters to reconcile by hand."""
    assert documented_gates() == gate_functions(), (
        "docs/api.md lists the gates in a different order or misses one. It is "
        "`GATES` order, the same as docs/gates.md and a printed report.")


def test_the_page_is_in_the_nav():
    """An unreferenced page builds and is reachable only by URL. The site
    builds with --strict, which catches a nav entry with no page; this is the
    other direction."""
    assert '"api.md"' in CONFIG.read_text(encoding="utf-8"), (
        "docs/api.md is not in the zensical.toml nav")


def test_the_handler_is_pointed_at_the_scripts():
    """The scripts are loose files, not an installed package. Without this
    path mkdocstrings resolves nothing and every block on the page is a build
    error."""
    assert 'paths = ["skill/scripts"]' in CONFIG.read_text(encoding="utf-8")
