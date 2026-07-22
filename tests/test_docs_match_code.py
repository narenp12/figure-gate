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

import pytest

from conftest import SKILL

import check_palette as cp

GUIDE = SKILL / "references" / "style-guide.md"
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
    line = next(l for l in GUIDE.read_text().splitlines()
                if f"`{hex_color}`" in l and l.startswith("|"))
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


def test_validator_default_surface_is_what_the_style_sheet_renders():
    """The two have to be the same value or the table is measuring a page the
    figures are not drawn on. That is the whole bug this file guards."""
    import inspect
    sig = inspect.signature(cp.check)
    assert sig.parameters["surface"].default == SURFACE
