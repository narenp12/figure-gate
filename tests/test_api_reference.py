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

MODULES = ("check_figure", "check_palette")

# Public callables the page deliberately does not document.
#
# The twenty gates are the substantive exemption. `audit()` runs all of them
# and computes the renderer, scale and canvas arguments they take; calling one
# directly means reproducing that. What a caller needs from a gate is its
# threshold and its failure condition, and the README documents all twenty in
# two tables -- `docs/api.md` says so and points at them.
EXEMPT = {
    "main": "the CLI entry point, documented by --help and the README",
    "self_test_figure": "builds the deliberately broken figure `main` checks; "
                        "not something a caller constructs",
}
EXEMPT_PREFIX = ("check_",)      # the twenty gates, minus `check_palette.check`


def public_callables(module):
    """Module-level `def`s not starting with an underscore, from the source.

    Parsed rather than imported: `check_palette.py` is claimed to run on 3.8
    with nothing installed, and reading it with `ast` keeps this test honest
    about what is in the file rather than what the local interpreter managed
    to import.
    """
    tree = ast.parse((SCRIPTS / f"{module}.py").read_text())
    return {node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")}


def documented():
    """`::: module.name` directives on the page, as `(module, name)` pairs."""
    return set(re.findall(r"^::: (\w+)\.(\w+)$", PAGE.read_text(), re.M))


def undocumented(module):
    covered = {name for mod, name in documented() if mod == module}
    return [name for name in public_callables(module)
            if name not in covered
            and name not in EXEMPT
            and not (name.startswith(EXEMPT_PREFIX) and name != "check")]


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


def test_the_page_is_in_the_nav():
    """An unreferenced page builds and is reachable only by URL. The site
    builds with --strict, which catches a nav entry with no page; this is the
    other direction."""
    assert '"api.md"' in CONFIG.read_text(), (
        "docs/api.md is not in the zensical.toml nav")


def test_the_handler_is_pointed_at_the_scripts():
    """The scripts are loose files, not an installed package. Without this
    path mkdocstrings resolves nothing and every block on the page is a build
    error."""
    assert 'paths = ["skill/scripts"]' in CONFIG.read_text()
