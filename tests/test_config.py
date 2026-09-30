"""The configuration file, against the constants it moves.

`docs/how-to.md` teaches two ways to change a threshold: edit the constant in a
vendored copy, or assign it before calling `audit`. Both are one person's copy,
and the page names what the second costs: a threshold moved in one test file is a
figure that passes locally and fails in CI.

`load_config` assigns the same module globals the by-hand route does, so what is
tested here is the reading and the refusing, not a second way to measure.
"""

import textwrap

import pytest

import check_figure as cf
import check_palette as cp

# Constants the tests below move. Restored after each one, because `load_config`
# writes module globals and the suite runs in one process per worker: a floor
# left at 9.0 makes the next test's figure pass for the wrong reason.
TOUCHED = ("TYPE_FLOOR_PT", "CONTENT_WIDTH_PT", "LINE_FLOOR_PT", "STYLE_SHEET",
           "TEXT_EDGE_WINDOW")


@pytest.fixture(autouse=True)
def _restore():
    saved = {name: getattr(cf, name) for name in TOUCHED}
    saved_cvd = cp.CVD_TARGET
    yield
    for name, value in saved.items():
        setattr(cf, name, value)
    cp.CVD_TARGET = saved_cvd


def write(folder, name="figure-gate.toml", body=""):
    path = folder / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# --- what it reads -----------------------------------------------------------

def test_it_sets_a_threshold_in_each_module(tmp_path):
    """One file reaches both files. A palette floor is a threshold this project
    enforces as much as a type floor, and `check_figure` is the only one of the
    two that may read TOML: CI runs `check_palette.py` on Python 3.8."""
    path = write(tmp_path, body="""
        TYPE_FLOOR_PT = 9.0
        CVD_TARGET = 12.0
    """)
    applied = cf.load_config(path)
    assert applied == {"TYPE_FLOOR_PT": 9.0, "CVD_TARGET": 12.0}
    assert cf.TYPE_FLOOR_PT == 9.0
    assert cp.CVD_TARGET == 12.0


def test_venue_sets_the_content_width(tmp_path):
    path = write(tmp_path, body='venue = "amsart"\n')
    assert cf.load_config(path) == {
        "CONTENT_WIDTH_PT": cf.VENUE_WIDTH_PT["amsart"]}
    assert cf.CONTENT_WIDTH_PT == cf.VENUE_WIDTH_PT["amsart"]


def test_a_none_valued_constant_takes_a_string(tmp_path):
    """`STYLE_SHEET` is None until someone points it somewhere."""
    path = write(tmp_path, body='STYLE_SHEET = "docs/thesis.mplstyle"\n')
    cf.load_config(path)
    assert cf.STYLE_SHEET == "docs/thesis.mplstyle"


def test_the_gates_read_what_the_file_set(tmp_path):
    """The claim the file is for, asked of `audit` rather than of the global.

    A 10pt label passes the shipped 7.5pt floor and fails an 11pt one. Same
    figure, same call, and nothing between them but the file.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 2.5))
    ax.set_xlabel("x", fontsize=10)
    try:
        rows = {n: s for n, s, _ in cf.audit(fig)[1]}
        assert rows["Type size"] is True
        cf.load_config(write(tmp_path, body="TYPE_FLOOR_PT = 11.0\n"))
        rows = {n: s for n, s, _ in cf.audit(fig)[1]}
        assert rows["Type size"] is False
    finally:
        plt.close(fig)


# --- what it refuses ---------------------------------------------------------

def test_a_key_that_names_no_threshold_raises(tmp_path):
    """The failure mode the strictness exists for. Skipping the key would leave
    a project reading its own file and believing a floor moved."""
    path = write(tmp_path, body="TYPE_FLOR_PT = 9.0\n")
    with pytest.raises(ValueError, match="names no threshold"):
        cf.load_config(path)


def test_a_wrong_type_raises_and_names_the_current_value(tmp_path):
    path = write(tmp_path, body='TYPE_FLOOR_PT = "big"\n')
    with pytest.raises(ValueError, match=r"expected a number \(TYPE_FLOOR_PT"):
        cf.load_config(path)


def test_a_bool_is_not_a_number(tmp_path):
    """`True` is an `int` in Python and a typo in a threshold file."""
    path = write(tmp_path, body="TYPE_FLOOR_PT = true\n")
    with pytest.raises(ValueError, match="expected a number"):
        cf.load_config(path)


def test_a_whole_float_for_an_integer_constant_is_stored_as_an_int(tmp_path):
    """TOML writes `9.0` as a float. `TEXT_EDGE_WINDOW` is a blur window, and a
    float there made `check_text_readability` raise, which `_rows` turns into a
    hard False."""
    import matplotlib.pyplot as plt

    cf.load_config(write(tmp_path, body="TEXT_EDGE_WINDOW = 9.0\n"))
    assert cf.TEXT_EDGE_WINDOW == 9 and type(cf.TEXT_EDGE_WINDOW) is int
    fig = cf.self_test_figure()
    try:
        rows = {n: d for n, _, d in cf.audit(fig)[1]}
        assert "gate raised" not in rows["Text readability"]
    finally:
        plt.close(fig)


def test_a_fractional_value_for_an_integer_constant_raises(tmp_path):
    path = write(tmp_path, body="TEXT_EDGE_WINDOW = 9.5\n")
    with pytest.raises(ValueError, match="expected a whole number"):
        cf.load_config(path)


def test_content_width_takes_a_number_only(tmp_path):
    """None until set, so the current value cannot say what type it takes. A
    string here reached `page_scale`, which multiplies it."""
    path = write(tmp_path, body='CONTENT_WIDTH_PT = "345"\n')
    with pytest.raises(ValueError, match="expected a number"):
        cf.load_config(path)


def test_style_sheet_takes_a_string_only_even_once_set(tmp_path):
    cf.STYLE_SHEET = "a.mplstyle"
    path = write(tmp_path, body="STYLE_SHEET = 3\n")
    with pytest.raises(ValueError, match="expected a string"):
        cf.load_config(path)


def test_venue_and_content_width_together_raise(tmp_path):
    path = write(tmp_path, body="""
        venue = "amsart"
        CONTENT_WIDTH_PT = 360.0
    """)
    with pytest.raises(ValueError, match="same width written twice"):
        cf.load_config(path)


def test_an_unknown_venue_raises_and_lists_the_known_ones(tmp_path):
    path = write(tmp_path, body='venue = "jmlr"\n')
    with pytest.raises(KeyError, match="unknown venue"):
        cf.load_config(path)


def test_a_venue_that_is_not_a_string_raises(tmp_path):
    path = write(tmp_path, body="venue = 360.0\n")
    with pytest.raises(ValueError, match="expected a string"):
        cf.load_config(path)


def test_unreadable_toml_raises(tmp_path):
    path = write(tmp_path, body="TYPE_FLOOR_PT = = 9\n")
    with pytest.raises(ValueError, match="not readable as TOML"):
        cf.load_config(path)


def test_one_bad_key_changes_nothing(tmp_path):
    """Every key is checked before any is assigned. A file half applied is a
    verdict nobody can reproduce from the file."""
    before = (cf.TYPE_FLOOR_PT, cf.LINE_FLOOR_PT)
    path = write(tmp_path, body="""
        TYPE_FLOOR_PT = 9.0
        LINE_FLOOR_PT = 2.0
        NOT_A_FLOOR = 1
    """)
    with pytest.raises(ValueError):
        cf.load_config(path)
    assert (cf.TYPE_FLOOR_PT, cf.LINE_FLOOR_PT) == before


# --- where it looks ----------------------------------------------------------

def test_it_walks_up_from_a_subdirectory(tmp_path):
    """Figures live in a subdirectory of the project that configures them."""
    write(tmp_path, body="TYPE_FLOOR_PT = 9.0\n")
    figures = tmp_path / "figures"
    figures.mkdir()
    assert cf.find_config(figures) == tmp_path / "figure-gate.toml"


def test_its_own_file_wins_over_pyproject(tmp_path):
    write(tmp_path, "pyproject.toml", '[tool.figure-gate]\nTYPE_FLOOR_PT = 8.0\n')
    write(tmp_path, "figure-gate.toml", "TYPE_FLOOR_PT = 9.0\n")
    assert cf.find_config(tmp_path).name == "figure-gate.toml"


def test_a_pyproject_table_is_read(tmp_path):
    path = write(tmp_path, "pyproject.toml", """
        [project]
        name = "thesis"

        [tool.figure-gate]
        TYPE_FLOOR_PT = 9.0
    """)
    assert cf.load_config(path) == {"TYPE_FLOOR_PT": 9.0}


def test_a_pyproject_without_the_table_is_not_a_config_file(tmp_path):
    """And the walk continues past it. A project whose figures sit in a package
    with its own `pyproject.toml` would otherwise stop at the inner one, which
    configures nothing, and never see the file that does."""
    write(tmp_path, body="TYPE_FLOOR_PT = 9.0\n")
    inner = tmp_path / "package"
    inner.mkdir()
    write(inner, "pyproject.toml", '[project]\nname = "inner"\n')
    assert cf.find_config(inner) == tmp_path / "figure-gate.toml"


def test_no_file_anywhere_applies_nothing(tmp_path):
    """`load_config()` in a project with no file is not an error. It is the
    ordinary case, and the constants are the answer."""
    assert cf.find_config(tmp_path) is None
    assert cf.load_config(start=tmp_path) == {}


def test_naming_a_file_that_configures_nothing_raises(tmp_path):
    """Searching and finding nothing is silence. Being handed a path and finding
    nothing in it is a mistake, and is reported."""
    path = write(tmp_path, "pyproject.toml", '[project]\nname = "thesis"\n')
    with pytest.raises(ValueError, match="carries no keys for this tool"):
        cf.load_config(path)


# --- what it will not set ----------------------------------------------------

def test_a_wire_format_is_not_a_threshold():
    """`AUDIT_SCHEMA` and the two attribute names are module-level constants and
    are not floors. A file that could move `AUDIT_SCHEMA` could rename the JSON
    contract from a TOML file."""
    keys = cf.config_keys()
    for name in ("AUDIT_SCHEMA", "DRAW_RC_ATTR", "ALT_TEXT_ATTR",
                 "ALT_TEXT_KEY_DEFAULT"):
        assert name not in keys, name


def test_the_thresholds_the_docs_quote_are_all_settable():
    """Every constant the how-to and the gate table name, checked against the
    list rather than assumed into it."""
    for name in ("TYPE_FLOOR_PT", "LINE_FLOOR_PT", "FURNITURE_FLOOR_PT",
                 "MATH_SCRIPT_FLOOR_PT", "PLACED_FRAC_WARN", "MARK_RATIO_MAX",
                 "MAX_SERIES_HUES", "ALT_TEXT_MIN_CHARS", "CVD_TARGET",
                 "NORMAL_FLOOR", "CONTRAST_MIN", "CMAP_BACKTRAVEL_MAX"):
        assert name in cf.config_keys(), name


def test_nothing_is_read_on_import():
    """The file is read when something asks. A constant that moved because of a
    file the caller never named is worse than one they had to type."""
    assert cf.TYPE_FLOOR_PT == 7.5
    assert cf.CONTENT_WIDTH_PT is None


# --- what it refuses to make everyone's -------------------------------------
# `_config_targets` selects by shape, and shape cannot tell a floor from the
# frame the floors are measured in. `MEASURE_DPI` is the case that motivated
# the split: it is a float named in capitals like every threshold, and a file
# setting it would rescale every pixel threshold in `check_figure` at once
# while each threshold's value stayed where a reader could see it.

def test_a_pinned_constant_is_not_a_key():
    for name in cf.NOT_CONFIGURABLE:
        assert name not in cf.config_keys(), name
    for name in cp.NOT_CONFIGURABLE:
        assert name not in cf.config_keys(), name


def test_setting_a_pinned_constant_raises_with_the_reason(tmp_path):
    """Not "names no threshold": that message sends a reader to check their
    spelling, and the spelling is right."""
    path = write(tmp_path, body="MEASURE_DPI = 300.0\n")
    with pytest.raises(ValueError, match="which is not a threshold: the "
                                         "resolution every pixel threshold"):
        cf.load_config(path)
    assert cf.MEASURE_DPI == 150.0


def test_a_pinned_palette_constant_raises_through_the_sibling(tmp_path):
    """`check_palette` reads no TOML, so its own pinned list only bites if
    `check_figure` reads it across the sibling import."""
    path = write(tmp_path, body="CMAP_SAMPLES = 64\n")
    with pytest.raises(ValueError, match="not a threshold: the sample count"):
        cf.load_config(path)
    assert cp.CMAP_SAMPLES == 256


def test_a_pinned_key_leaves_the_rest_of_the_file_unapplied(tmp_path):
    """Every key is checked before any is assigned, and a pinned one is a bad
    key like any other."""
    path = write(tmp_path, body="TYPE_FLOOR_PT = 9.0\nMEASURE_DPI = 300.0\n")
    with pytest.raises(ValueError, match="not a threshold"):
        cf.load_config(path)
    assert cf.TYPE_FLOOR_PT == 7.5


def test_every_pinned_constant_exists_and_records_why():
    """A name that has been renamed away pins nothing, and an entry with no
    reason is indistinguishable from one added to make a test pass."""
    for module, pinned in ((cf, cf.NOT_CONFIGURABLE), (cp, cp.NOT_CONFIGURABLE)):
        for name, reason in pinned.items():
            value = getattr(module, name, None)
            assert isinstance(value, (int, float)), (
                f"{name} is pinned in {module.__name__} and is {value!r}. Only "
                "a number can reach the config surface, so pinning anything "
                "else excuses nothing")
            assert len(reason) > 30, f"{name} is pinned with {reason!r}"


def test_the_pinned_constants_are_the_ones_the_shape_rule_would_have_taken():
    """The list only means something against the rule it narrows: each name has
    to be one `_config_targets` would otherwise have accepted."""
    for module, pinned in ((cf, cf.NOT_CONFIGURABLE), (cp, cp.NOT_CONFIGURABLE)):
        for name in pinned:
            assert name.isupper() and not name.startswith("_"), name
            assert not isinstance(getattr(module, name), bool), name
