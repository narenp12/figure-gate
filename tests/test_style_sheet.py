"""The style sheet has to actually apply.

This file exists because of a real bug, and it is the kind worth guarding
permanently. `#` starts a comment in matplotlib's style-sheet format, so a color
written as `grid.color: #e1e0d9` parses as an empty value. matplotlib logs a
warning and keeps its own default. Nothing else notices: the figure still
renders, the composition checks still pass, the palette checks never look at the
figure, and the test suite stays green while every figure ships in stock
matplotlib colors.

So: load the sheet, assert it parsed without complaint, and assert the values
that came out are the ones written down.
"""

import logging

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

from conftest import STYLE_SHEET


def parsed():
    return mpl.rc_params_from_file(STYLE_SHEET, use_default_template=False)


def test_the_sheet_exists_where_the_skill_says_it_does():
    assert STYLE_SHEET.is_file()


def test_no_key_is_silently_dropped(caplog):
    """matplotlib reports a bad line by logging, not by raising, which is
    exactly how the original bug survived. Turn the log into the assertion."""
    with caplog.at_level(logging.WARNING, logger="matplotlib"):
        params = parsed()
    bad = [r.getMessage() for r in caplog.records
           if "Bad value" in r.getMessage() or "does not look like" in r.getMessage()]
    assert not bad, "\n".join(bad)
    assert params, "style sheet parsed to nothing"


def test_colors_are_written_bare_not_with_a_hash():
    """The direct form of the same check, so a failure names the cause rather
    than leaving you to infer it from a log line."""
    offenders = []
    for lineno, raw in enumerate(STYLE_SHEET.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if "color" in key and "#" in value:
            offenders.append(f"line {lineno}: {line}")
    assert not offenders, (
        "`#` starts a comment in a .mplstyle file, so these parse as empty and "
        "matplotlib keeps its defaults:\n  " + "\n  ".join(offenders))


@pytest.mark.parametrize("key", [
    "text.color", "axes.labelcolor", "axes.edgecolor",
    "xtick.color", "ytick.color", "grid.color",
])
def test_every_color_key_resolves_to_a_real_color(key):
    value = parsed()[key]
    assert value, f"{key} parsed to an empty value"
    mpl.colors.to_rgba(value)          # raises if it is not a color


def test_the_sheet_applies_through_style_use():
    """Parsing it is not the same as it taking effect."""
    written = parsed()
    with plt.style.context(str(STYLE_SHEET)):
        for key in ("grid.color", "text.color", "font.size",
                    "legend.frameon", "axes.spines.top"):
            assert plt.rcParams[key] == written[key], key


def test_structure_choices_the_guide_promises():
    """These are the rules the guide moved out of prose and into the sheet. If
    the sheet stops carrying them, the prose is lying."""
    p = parsed()
    assert p["axes.spines.top"] is False
    assert p["axes.spines.right"] is False
    assert p["legend.frameon"] is False


def test_font_stack_ends_in_a_face_that_ships_with_matplotlib():
    """A missing face falls back silently. Putting an always-available family
    last is what keeps that fallback from landing somewhere arbitrary."""
    stack = parsed()["font.serif"]
    assert stack[-1] in {"DejaVu Serif", "DejaVu Sans"}, stack


def test_type_sizes_clear_the_floor_at_scale_one():
    """The sheet's defaults have to be legal for the case the guide recommends:
    authoring at the width the figure is placed at."""
    import check_figure as cf
    p = parsed()
    sizes = {k: p[k] for k in
             ("font.size", "axes.labelsize", "xtick.labelsize",
              "ytick.labelsize", "legend.fontsize")}
    small = {k: v for k, v in sizes.items() if float(v) < cf.TYPE_FLOOR_PT}
    assert not small, small
