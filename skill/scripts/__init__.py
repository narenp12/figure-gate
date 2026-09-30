"""figure-gate: mechanical gates for publication figures.

This directory is the source of both ways the checkers are used, and they are
not the same shape.

**Vendored.** Copy `check_palette.py`, `check_figure.py` or `suggest_fixes.py`
into your own project and import it flat:

    import check_figure as cf

That is the documented route and the one the skill teaches. The three files do
not import each other at module scope, `check_palette.py` imports nothing
outside the standard library, and none of that changes here.

**Installed.** `pip install figure-gate` puts the same three files in a package:

    from figure_gate import check_figure as cf

They sit under `figure_gate` rather than at the top level of `site-packages`
because `check_figure`, `check_palette` and `suggest_fixes` are generic names
any distribution could claim.

This file is what makes the second form a package. It deliberately re-exports
nothing: the modules are independent, two of the three are useful without
matplotlib installed, and an `__init__` that imported all three would make
`from figure_gate import check_palette` -- the one with no third-party
dependency at all -- fail on a machine without matplotlib.
"""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("figure-gate")
except PackageNotFoundError:                                # pragma: no cover
    # Imported out of a source tree rather than an installation, which is what
    # the test suite does.
    __version__ = "0.0.0.dev0"

# Read off the installed distribution rather than written here. The version
# already lives in six files that one `bump-my-version` run rewrites together,
# and `tests/test_version_sites.py` exists because two of them once drifted; a
# literal here would be a seventh site, hand-maintained, that the bump config
# does not know about.

__all__ = ["__version__"]

