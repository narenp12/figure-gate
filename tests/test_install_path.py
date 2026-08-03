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

# The name and location `_style_sheet` probes first, which is what the wheel's
# force-include has to match for the gate to fire on an install. Through 0.6.0
# this was a bare `figure.mplstyle` at the root of site-packages, a generic
# name any other distribution could also claim.
INSTALLED_DIR = "figure_gate_data"
INSTALLED_NAME = f"{INSTALLED_DIR}/figure.mplstyle"

PYPROJECT = SCRIPTS.parent.parent / "pyproject.toml"


def test_the_wheel_maps_the_sheet_beside_the_script():
    """The build config, against the path the checker actually probes."""
    tomllib = pytest.importorskip("tomllib")     # 3.11+; the build runs there
    config = tomllib.loads(PYPROJECT.read_text())
    wheel = config["tool"]["hatch"]["build"]["targets"].get("wheel", {})
    source = STYLE_SHEET.relative_to(PYPROJECT.parent).as_posix()
    assert wheel.get("force-include", {}).get(source) == INSTALLED_NAME, (
        f"the wheel no longer ships figure.mplstyle in {INSTALLED_DIR}/, so "
        "gate 16 cannot fire on the install path")


def _installed(tmp_path, with_sheet=True):
    """`tmp_path` laid out the way the wheel lays out site-packages."""
    shutil.copy(SCRIPTS / "check_figure.py", tmp_path / "check_figure.py")
    shutil.copy(SCRIPTS / "check_palette.py", tmp_path / "check_palette.py")
    if with_sheet:
        (tmp_path / INSTALLED_DIR).mkdir()
        shutil.copy(STYLE_SHEET, tmp_path / INSTALLED_NAME)
    return tmp_path


def _run(tmp_path, body):
    """Run `body` with only `tmp_path` importable, so the checkout's `assets/`
    cannot be what answers."""
    script = tmp_path / "probe.py"
    script.write_text(textwrap.dedent("""
        import matplotlib
        matplotlib.use("agg")
        import matplotlib.pyplot as plt
        import check_figure
    """) + textwrap.dedent(body))
    result = subprocess.run([sys.executable, str(script)],
                            capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


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
    assert out.startswith("True | no figure.mplstyle in figure_gate_data/"), out


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
    import zipfile

    root = PYPROJECT.parent
    subprocess.run(["uv", "build", "--wheel", "--out-dir", "dist"],
                   cwd=root, check=True, capture_output=True)
    wheel = sorted((root / "dist").glob("*.whl"))[-1]
    names = zipfile.ZipFile(wheel).namelist()
    assert "audit_api.py" not in names, (
        f"{wheel.name} ships audit_api.py, which is release tooling: "
        f"{sorted(n for n in names if 'dist-info' not in n)}")
