"""The style-sheet gate on the installed layout, and the way to redirect it.

Gate 16 exists to catch a forgotten `plt.style.use`. Through 0.1.3 the wheel
shipped `skill/scripts` and nothing else, so on `uv add figure-gate` there was
no `figure.mplstyle` anywhere near `check_figure.py`, `_style_sheet` returned
None, and the row read "nothing to compare" -- a pass -- for exactly the figure
the gate was written for. Nothing in the suite noticed, because every test here
runs from the checkout, where `assets/` is one directory up.

So these tests do not read the source layout: they build the layout the wheel
produces and run the checker inside it.
"""

import shutil
import subprocess
import sys
import textwrap

import pytest

from conftest import SCRIPTS, STYLE_SHEET

# Where the sheet lands, and what the wheel's force-include has to match for
# the gate to fire on an install. This has moved twice: a bare
# `figure.mplstyle` at the root of site-packages through 0.1.3, a namespacing
# `figure_gate_data/` through 0.6.0, and now inside the package itself, where
# the module that reads it lives and no other distribution can reach.
PACKAGE = "figure_gate"
INSTALLED_NAME = f"{PACKAGE}/figure.mplstyle"

PYPROJECT = SCRIPTS.parent.parent / "pyproject.toml"


def _wheel_config():
    tomllib = pytest.importorskip("tomllib")     # 3.11+; the build runs there
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return config["tool"]["hatch"]["build"]["targets"].get("wheel", {})


def test_the_wheel_maps_the_sheet_beside_the_script():
    """The build config, against the path the checker actually probes."""
    source = STYLE_SHEET.relative_to(PYPROJECT.parent).as_posix()
    assert _wheel_config().get("force-include", {}).get(source) == INSTALLED_NAME, (
        f"the wheel no longer ships figure.mplstyle in {PACKAGE}/, so "
        "gate 16 cannot fire on the install path")


def test_the_wheel_installs_a_package_not_top_level_modules():
    """The whole point of the 0.7.0 layout change.

    `sources` used to be `["skill/scripts"]`, which strips the prefix and puts
    `check_figure`, `check_palette` and `suggest_fixes` at the top level of
    site-packages -- three generic names on a shared namespace, permanent once
    callers import them. Asserting the mapping here states the intent; the
    build-the-wheel test below is what proves it came out that way.
    """
    assert _wheel_config().get("sources") == {"skill/scripts": PACKAGE}, (
        "the wheel no longer remaps skill/scripts onto the figure_gate "
        "package, so the modules install at the top level of site-packages")


def _installed(tmp_path, with_sheet=True):
    """`tmp_path` laid out the way the wheel lays out site-packages."""
    pkg = tmp_path / PACKAGE
    pkg.mkdir()
    for name in ("__init__.py", "check_figure.py", "check_palette.py",
                 "suggest_fixes.py", "py.typed"):
        shutil.copy(SCRIPTS / name, pkg / name)
    if with_sheet:
        shutil.copy(STYLE_SHEET, tmp_path / INSTALLED_NAME)
    return tmp_path


def _run(tmp_path, body):
    """Run `body` with the checkout off `sys.path`, so only `tmp_path` answers.

    The pruning loop is the point, and it is not defensive. An editable install
    of this project drops a `.pth` into the environment that puts
    `skill/scripts` on `sys.path` of every interpreter started from it --
    including this subprocess, which then resolves a flat `import check_palette`
    against the repository. That is invisible and it inverts the test: the
    layout being probed is the installed one, and the checkout answering for it
    is the exact confusion these tests exist to rule out.

    It cost a real result. `test_no_gate_degrades_on_the_install_path` was
    written, the defect it describes was reintroduced deliberately to check the
    test could see it, and the test passed -- because the leaked path made the
    broken import work.
    """
    script = tmp_path / "probe.py"
    script.write_text(textwrap.dedent(f"""
        import os, sys
        # Exactly the two entries that let a flat `import check_palette`
        # resolve against the repository, and not the checkout as a whole:
        # `.venv/` lives inside it, so pruning by prefix takes matplotlib with
        # it and the probe dies on the import instead of the assertion.
        _leaked = {{os.path.normpath(p) for p in
                   ({str(SCRIPTS)!r}, {str(PYPROJECT.parent)!r})}}
        sys.path[:] = [p for p in sys.path
                       if os.path.normpath(p or ".") not in _leaked]
        import matplotlib
        matplotlib.use("agg")
        import matplotlib.pyplot as plt
        from figure_gate import check_figure
    """) + textwrap.dedent(body), encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)],
                            capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_no_gate_degrades_on_the_install_path(tmp_path):
    """No row of a full audit reports a sibling module as missing.

    `check_figure` reaches `check_palette` for the series-colour and colormap
    gates and `suggest_fixes` for the remedy block, and imports none of them at
    module scope -- the files are meant to be vendored one at a time, so each
    use is guarded. On the install path they are siblings in a package, where
    the flat `import check_palette` those sites used to do resolves to nothing.

    The whole audit rather than one gate, and a substring rather than a status,
    because the failure this is written for was invisible in both. When the
    package layout arrived, `check_series_color` was converted and
    `check_colormap` was missed; its guard returns True, so gate 19 reported a
    PASS carrying the words "not importable beside this file" and had silently
    stopped classifying colormaps. A green row is exactly what a degraded gate
    looks like, so the assertion has to read the detail.
    """
    out = _run(_installed(tmp_path), """
        import numpy as np
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], color="#0072b2", label="a")
        ax.imshow(np.random.rand(4, 4), cmap="viridis")
        ok, rows = check_figure.audit(fig)
        for label, status, detail in rows:
            print(f"{label}\t{status}\t{detail}")
    """)
    degraded = [line for line in out.splitlines() if "not importable" in line]
    assert not degraded, (
        "these gates stopped checking on the install path and still "
        f"reported: {degraded}")


def test_stock_matplotlib_fails_the_gate_on_the_installed_layout(tmp_path):
    """The failure the docstring of `check_style_sheet` names first: a figure
    drawn with no `plt.style.use` at all."""
    out = _run(_installed(tmp_path), """
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        status, detail = check_figure.check_style_sheet(fig)
        print(status)
    """)
    assert out.strip() == "warn", out


def test_the_shipped_sheet_matches_itself_once_applied(tmp_path):
    """The other half: applying the sheet the install ships clears the gate.
    A warn that cannot be cleared is noise, not a gate."""
    out = _run(_installed(tmp_path), f"""
        plt.style.use("{INSTALLED_NAME}")
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        status, detail = check_figure.check_style_sheet(fig)
        print(status, "|", detail)
    """)
    assert out.startswith("True |"), out


def test_without_the_sheet_the_row_is_the_old_silent_pass(tmp_path):
    """Pinned so the regression is legible: this is what shipped through
    0.1.3, and it is a pass."""
    out = _run(_installed(tmp_path, with_sheet=False), """
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        status, detail = check_figure.check_style_sheet(fig)
        print(status, "|", detail)
    """)
    assert out.startswith("True | no figure.mplstyle beside this script"), out


def test_STYLE_SHEET_wins_over_both_probed_locations(tmp_path):
    """A project whose sheet lives somewhere else. The sheet is meant to be
    edited per document, so this is the ordinary case, not the exotic one --
    and before 0.1.4 the only way to say it was to patch a private function."""
    elsewhere = tmp_path / "docs" / "thesis.mplstyle"
    elsewhere.parent.mkdir()
    shutil.copy(STYLE_SHEET, elsewhere)
    out = _run(_installed(tmp_path), f"""
        check_figure.STYLE_SHEET = r"{elsewhere}"
        print(check_figure._style_sheet())
    """)
    assert out.strip() == str(elsewhere), out


def test_a_configured_sheet_that_does_not_exist_warns(tmp_path):
    """Falling back to the shipped sheet would compare against a sheet the
    project did not ask for and report a clean row for it."""
    out = _run(_installed(tmp_path), """
        check_figure.STYLE_SHEET = "does-not-exist.mplstyle"
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        status, detail = check_figure.check_style_sheet(fig)
        print(status, "|", detail)
    """)
    assert out.startswith("warn | STYLE_SHEET is set to"), out


def test_the_wheel_does_not_ship_release_tooling():
    """`audit_api.py` compares the public API against the last tag and is run
    from the Makefile and from CI. Nobody installs this distribution for it,
    and through 0.6.0 it landed on every installing user's import path.

    The check is on the built wheel rather than on the config, because the
    config can grow a second `[tool.hatch...]` table that reinstates it without
    the `exclude` line changing.
    """
    names = _built_wheel_names()
    assert f"{PACKAGE}/audit_api.py" not in names, (
        f"the wheel ships audit_api.py, which is release tooling: {names}")


def _built_wheel_names():
    """The non-metadata entries of a freshly built wheel."""
    import zipfile

    root = PYPROJECT.parent
    subprocess.run(["uv", "build", "--wheel", "--out-dir", "dist"],
                   cwd=root, check=True, capture_output=True)
    wheel = sorted((root / "dist").glob("*.whl"))[-1]
    names = zipfile.ZipFile(wheel).namelist()
    return sorted(n for n in names if "dist-info" not in n)


def test_the_wheel_claims_no_name_outside_its_own_package():
    """The gate on the layout, checked against what the build actually emits.

    The config test above states the mapping; this one refuses the outcome. Any
    entry that is not under `figure_gate/` is a name this distribution has
    taken on a namespace it shares with every other installed package, and
    `check_figure` was exactly that until 0.7.0.
    """
    stray = [n for n in _built_wheel_names()
             if not n.startswith(f"{PACKAGE}/")]
    assert not stray, (
        f"the wheel installs {stray} outside {PACKAGE}/, claiming top-level "
        "names on a shared namespace")


def test_the_wheel_ships_the_typing_marker():
    """Every function in these modules is annotated. Without `py.typed` in the
    installed package, PEP 561 says a caller's type checker must ignore all of
    it -- which is what happened for as long as the modules were top-level
    files, where the marker has nothing to attach to.
    """
    assert f"{PACKAGE}/py.typed" in _built_wheel_names(), (
        "the wheel has no py.typed, so every annotation in it resolves to Any "
        "in a caller's type checker")
