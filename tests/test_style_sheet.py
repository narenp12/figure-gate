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
    for lineno, raw in enumerate(STYLE_SHEET.read_text(encoding="utf-8").splitlines(), 1):
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


def test_mark_defaults_are_in_the_sheet_not_at_the_call_site():
    """These were prose, passed by hand as `lw=1.6` wherever someone
    remembered. The sheet is the mechanism for exactly that."""
    p = parsed()
    assert float(p["lines.linewidth"]) == pytest.approx(1.6)
    assert float(p["lines.markersize"]) == pytest.approx(5)
    assert float(p["axes.linewidth"]) == pytest.approx(0.8)


def test_output_settings_survive_a_save(tmp_path):
    """`savefig.bbox: standard` reads back as None - matplotlib's own spelling.
    The value that must never appear is 'tight': it trims to drawn content, so
    the saved width stops matching the authored width the type gate measures.
    """
    written = parsed()
    assert written["savefig.bbox"] is None, written["savefig.bbox"]

    with plt.style.context(str(STYLE_SHEET)):
        assert plt.rcParams["savefig.bbox"] != "tight"
        assert float(plt.rcParams["savefig.dpi"]) == pytest.approx(300)
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([0, 1], [0, 1])
        out = tmp_path / "f.png"
        fig.savefig(out)
        plt.close(fig)

    from PIL import Image
    with Image.open(out) as im:
        # 4in authored at 300dpi. bbox_inches="tight" would land under this.
        assert im.size[0] == 1200, f"saved width {im.size[0]}px, expected 1200"


def test_the_surface_the_guide_measures_against_is_what_the_sheet_renders():
    """Contrast ratios are quoted against a surface. If the sheet stops drawing
    on it, every number in the palette table is measuring a page that does not
    exist -- which is precisely what happened with #fcfcfb."""
    import check_palette as cp
    p = parsed()
    assert mpl.colors.to_hex(p["figure.facecolor"]) == "#ffffff"
    assert mpl.colors.to_hex(p["axes.facecolor"]) == "#ffffff"
    import inspect
    assert inspect.signature(cp.check).parameters["surface"].default == "#ffffff"


def test_font_stack_ends_in_a_face_that_ships_with_matplotlib():
    """A missing face falls back silently. Putting an always-available family
    last is what keeps that fallback from landing somewhere arbitrary."""
    stack = parsed()["font.serif"]
    assert stack[-1] in {"DejaVu Serif", "DejaVu Sans"}, stack


OKABE_SERIES = ["#E69F00", "#56B4E9", "#009E73",
                "#0072B2", "#D55E00", "#CC79A7"]


def test_the_series_cycle_is_the_palette_the_guide_prescribes():
    """Until this key existed the sheet set every visual default except the one
    that decides whether a colorblind reader can separate two curves, so a
    figure built on it inherited matplotlib's `tab10` -- whose orange and green
    measure dE 1.4 under protanopia."""
    cycle = [c.upper() for c in parsed()["axes.prop_cycle"].by_key()["color"]]
    assert cycle == OKABE_SERIES, cycle


def test_the_cycle_clears_the_palette_gates_it_is_measured_by():
    """The sheet cannot prescribe a palette that its own validator rejects.
    Adjacent for lines and bars; the first four for scatter and small
    multiples, which compare every series against every other."""
    import check_palette as cp
    cycle = parsed()["axes.prop_cycle"].by_key()["color"]
    ok, rows = cp.check(cycle)
    assert ok, rows
    ok, rows = cp.check(cycle[:4], all_pairs=True)
    assert ok, rows


def test_the_held_out_slots_stay_held_out():
    """Yellow is 1.32:1 on white and vanishes as a hairline; black is the ink
    token. Both are measured or stated in the guide, so a future edit that
    quietly restores them to the series cycle should fail here."""
    cycle = {c.upper() for c in parsed()["axes.prop_cycle"].by_key()["color"]}
    assert "#F0E442" not in cycle
    assert "#000000" not in cycle


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


def test_the_sheet_embeds_fonts_as_type_42():
    """Matplotlib defaults to Type 3 and IEEE PDF eXpress rejects the upload.
    `check_fonts` can only warn about this, because it reads global rcParams
    rather than anything a figure carries — so the hard gate lives here, on the
    one artifact this repo actually controls."""
    p = parsed()
    assert int(p["pdf.fonttype"]) == 42
    assert int(p["ps.fonttype"]) == 42


def test_tick_labels_clear_the_wcag_text_threshold():
    """Tick labels are text and take 4.5:1, not the 3:1 a mark gets. The muted
    ink token shipped here at 3.59:1 until the readability check failed the
    sheet's own ticks on every figure in the repo."""
    import check_figure as cf
    import check_palette as cp
    p = parsed()
    surface = mpl.colors.to_hex(p["axes.facecolor"])
    for key in ("xtick.color", "ytick.color"):
        ratio = cp.contrast(mpl.colors.to_hex(p[key]), surface)
        assert ratio >= cf.TEXT_CONTRAST_MIN, (key, round(ratio, 2))
