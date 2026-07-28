"""The guide quotes numbers. The code computes them. They have to agree.

This exists because they did not. Every contrast ratio in the palette table was
computed against a surface (`#fcfcfb`) that no figure in this project ever
rendered - `figure.mplstyle` has always drawn on white. The numbers were all
slightly wrong, and one of them was wrong in a way that changed a rule: reddish
purple was marked as needing a mandatory direct label at 2.98, when against the
surface actually used it clears 3:1 at 3.06.

Nothing caught it, because a number in prose is not executable. So: read the
table out of the guide and check every row against `contrast()`. A quoted
measurement that drifts from the code is now a test failure rather than a thing
someone notices in a year.
"""

import re
import subprocess
import sys

import pytest

from conftest import SKILL

import check_palette as cp

GUIDE = SKILL / "references" / "style-guide.md"
README = SKILL.parent / "README.md"
SURFACE = "#ffffff"

# | 2 | orange | `#E69F00` | 2.25 † | series |
ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*[^|]+\|\s*`(#[0-9A-Fa-f]{6})`\s*\|\s*([\d.]+)\s*[†‡]?\s*\|")


def table_rows():
    return [(m.group(1), float(m.group(2)))
            for m in (ROW.match(line) for line in GUIDE.read_text().splitlines())
            if m]


def test_the_table_is_still_parseable():
    """If the table's shape changes, this file has to be updated with it -
    silently matching zero rows would turn the whole check into a no-op."""
    rows = table_rows()
    assert len(rows) == 8, f"expected the 8 Okabe-Ito slots, matched {len(rows)}"


@pytest.mark.parametrize("hex_color,quoted", table_rows())
def test_quoted_contrast_matches_computed(hex_color, quoted):
    computed = cp.contrast(hex_color, SURFACE)
    assert computed == pytest.approx(quoted, abs=0.01), (
        f"{hex_color}: guide says {quoted}, contrast() says {computed:.2f} "
        f"against {SURFACE}")


@pytest.mark.parametrize("hex_color,quoted", table_rows())
def test_the_dagger_matches_the_number(hex_color, quoted):
    """The † footnote means 'below 3:1, needs a direct label'. That marker is a
    rule, so it has to follow the measurement rather than sit beside it.

    ‡ (outside the lightness band) takes precedence: a hue held out of line and
    hairline use altogether has no direct-label obligation to carry, so it is
    marked ‡ alone even though it is also under 3:1. Yellow is the only slot
    where the two overlap.
    """
    line = next((l for l in GUIDE.read_text().splitlines()
                 if f"`{hex_color}`" in l and l.startswith("|")), None)
    if line is None:
        pytest.fail(f"`{hex_color}` not found in guide table")
    if "‡" in line:
        pytest.skip("held out of line use entirely; ‡ supersedes †")
    marked = "†" in line
    below = cp.contrast(hex_color, SURFACE) < cp.CONTRAST_MIN
    assert marked == below, (
        f"{hex_color} at {cp.contrast(hex_color, SURFACE):.2f}:1 is "
        f"{'below' if below else 'at or above'} {cp.CONTRAST_MIN}:1, but the "
        f"table {'marks' if marked else 'does not mark'} it with †")


def test_the_guide_does_not_quote_a_retired_surface():
    """`#fcfcfb` was the surface the numbers used to be computed against. It is
    not what anything renders, so a reappearance means the drift came back."""
    assert "fcfcfb" not in GUIDE.read_text().lower().replace(
        "`#fcfcfb`, a", ""), "the retired surface is quoted again"


# --- the gate roster ---------------------------------------------------------
# Same failure as the contrast table, one level up: the list of gates is written
# out in three places and only one of them executes. `check_overplotting` and
# `check_contour_dash` shipped with tests and were never added to the README
# table; `check_line_weight` was never added to the module docstring. Nobody
# noticed, because a roster in prose cannot fall out of date loudly.

DOCSTRING_ROW = re.compile(r"^\s*\d+\.\s+(.+?)\s+-\s")


def audit_gate_names():
    """The only executable roster: what `audit` actually returns a row for."""
    import matplotlib.pyplot as plt

    import check_figure as cf

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    try:
        _, rows = cf.audit(fig)
    finally:
        plt.close(fig)
    return [name for name, _, _ in rows]


def docstring_gate_names():
    import check_figure as cf

    body = cf.__doc__.split("Checks, in the order `audit` runs them", 1)[1]
    return [m.group(1) for m in map(DOCSTRING_ROW.match, body.splitlines()) if m]


def readme_gate_names():
    """First column of the gate table, however many columns it has.

    The gate name has always been the first cell; the columns beside it have
    not been stable. Matching the row shape with a regex meant a README rewrite
    that added a Threshold column turned this parser into one that matched zero
    rows — a roster check that reads nothing and compares it against 19 gates.
    Splitting on the delimiter instead makes the column count irrelevant.
    """
    lines = README.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if "**`check_figure.py`**" in l)
    names = []
    for line in lines[start:]:
        if line.startswith("|"):
            names.append(line.strip().strip("|").split("|")[0].strip())
        elif names:
            break
    # drop the header row and the |---|---| separator, which both match
    return [n for n in names if n != "Gate" and set(n) != {"-"}]


def test_the_readme_table_is_still_parseable():
    """The failure this file exists to prevent, in its own machinery: a parser
    that matches nothing reports agreement with nothing. Assert the roster was
    actually read before any test draws a conclusion from its contents."""
    assert readme_gate_names(), (
        "matched no rows in the README gate table - the table moved or changed "
        "shape and readme_gate_names() needs updating with it")


def test_the_module_docstring_lists_every_gate_in_order():
    assert docstring_gate_names() == audit_gate_names()


def test_the_readme_table_lists_every_gate_in_order():
    stripped = [n.replace("*(advisory)*", "").strip()
                for n in readme_gate_names()]
    assert stripped == audit_gate_names()


def collected_test_count():
    """The size of the suite, asked of pytest in a subprocess.

    Not `request.session.testscollected`: the documented command here is
    `pytest -n auto`, where each xdist worker collects a slice and no worker
    can see the total. A fresh collection is the only number that is the
    suite's.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(README.parent / "tests"),
         "--collect-only", "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=README.parent)
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, result.stdout
    return int(match.group(1))


def test_the_readme_test_count_is_the_real_one():
    """A number in prose is not executable -- the same reason the rest of this
    file exists. 0.1.3 shipped a README claiming 166 tests against a suite of
    171, and the only thing that catches that is asking pytest."""
    claimed = re.search(r"The suite is (\d+) tests", README.read_text())
    assert claimed, ("the README no longer states a test count in the form "
                     "this test reads")
    assert int(claimed.group(1)) == collected_test_count()


def test_validator_default_surface_is_what_the_style_sheet_renders():
    """The two have to be the same value or the table is measuring a page the
    figures are not drawn on. That is the whole bug this file guards."""
    import inspect
    sig = inspect.signature(cp.check)
    assert sig.parameters["surface"].default == SURFACE
