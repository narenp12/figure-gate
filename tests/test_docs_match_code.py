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

# | 2 | orange | `#E69F00`{ .sw style="--c:#E69F00" } | 2.25 † | series |
#
# The swatch is optional in this pattern and mandatory in the test below. Making
# it optional here keeps the two questions apart: this regex asks what the guide
# claims about a hue's contrast, and it should keep answering that if the
# swatches are ever pulled. `test_every_palette_row_carries_a_swatch` is what
# makes a row without one a failure rather than a silent hole.
SWATCH_ATTRS = r'\{ \.sw style="--c:(#[0-9A-Fa-f]{6})" \}'
ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*[^|]+\|\s*`(#[0-9A-Fa-f]{6})`(?:" + SWATCH_ATTRS + r")?"
    r"\s*\|\s*([\d.]+)\s*[†‡]?\s*\|")


def table_rows():
    return [(m.group(1), float(m.group(3)))
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

    That branch used to `pytest.skip`, which left the one row with a marker
    collision as the one row whose marker nothing checked -- the suite reported
    a permanent 1 skipped and the ‡ was taken on trust. A skip is not a weaker
    assertion, it is the absence of one. So ‡ now asserts its own claim: the hue
    really is outside the band, and it does not also wear the † it supersedes.

    The converse is scoped to the role column rather than applied to every
    unmarked row, because black is out of the band at L 0.000 and carries no ‡
    on purpose. It is held out as the ink token, which the guide states as a
    preference and not a measurement -- so "unmarked" means "in band" only for
    the rows offered as series hues, which is also the only place
    `check_palette` gates the band.
    """
    line = next((l for l in GUIDE.read_text().splitlines()
                 if f"`{hex_color}`" in l and l.startswith("|")), None)
    if line is None:
        pytest.fail(f"`{hex_color}` not found in guide table")
    role = line.strip().strip("|").split("|")[-1].strip()

    lightness = cp.linear_to_oklab(cp.hex_to_linear(hex_color))[0]
    in_band = cp.L_MIN <= lightness <= cp.L_MAX
    if "‡" in line:
        assert not in_band, (
            f"{hex_color} is marked ‡ (outside the lightness band) at OKLab L "
            f"{lightness:.3f}, which is inside {cp.L_MIN}-{cp.L_MAX}")
        assert "†" not in line, (
            f"{hex_color} carries both markers. ‡ supersedes †: a hue held out "
            "of line and hairline use has no direct-label obligation left to "
            "carry, so the row states one rule, not two")
        assert role != "series", (
            f"{hex_color} is offered as a series hue and marked ‡. The ‡ is "
            "what holds a hue out of line use; a row cannot do both")
        return

    if role == "series":
        assert in_band, (
            f"{hex_color} is offered as a series hue at OKLab L "
            f"{lightness:.3f}, outside the {cp.L_MIN}-{cp.L_MAX} band, and the "
            "row carries no ‡ to say so")
    marked = "†" in line
    below = cp.contrast(hex_color, SURFACE) < cp.CONTRAST_MIN
    assert marked == below, (
        f"{hex_color} at {cp.contrast(hex_color, SURFACE):.2f}:1 is "
        f"{'below' if below else 'at or above'} {cp.CONTRAST_MIN}:1, but the "
        f"table {'marks' if marked else 'does not mark'} it with †")


# --- the swatches are the hex they label -------------------------------------
# A swatch is the guide's only unrecomputable claim: every other cell is a number
# a reader can put back through `contrast()`, while a swatch asserts "this hex is
# this hue" with a painted square. It states the hex a second time to do it, in
# an inline style, and two copies of one color agreeing until someone edits one
# of them is how the ink table came to credit the style sheet with a token the
# sheet had stopped shipping.
#
# So the copy is checked here and the paint is checked in `test_docs_render.py`.
# Neither alone is enough: this file cannot see a stylesheet that stopped
# applying, and a browser cannot see that the square is confidently the wrong
# color when both copies were changed together but only one of them was meant.

SWATCH = re.compile(SWATCH_ATTRS)
LABELLED_SWATCH = re.compile(r"`(#[0-9A-Fa-f]{6})`" + SWATCH_ATTRS)


def swatch_pairs():
    """(declared, labelled) for every swatch, as (`--c`, the code span's text).

    The two cannot be separated in the source -- the attribute list belongs to
    the code span it follows -- so an unpaired swatch is not a state this needs
    to check for. That is the point of writing them this way; a sibling `<span>`
    could be orphaned from its hex both in the file and on the rendered line.
    """
    return [(m.group(2), m.group(1))
            for m in LABELLED_SWATCH.finditer(GUIDE.read_text())]


def test_the_guide_still_carries_swatches():
    """`SWATCH_ATTRS` is a literal attribute list. If the syntax is reformatted
    -- a `{:` prefix, different spacing -- every test parametrized over
    `swatch_pairs()` silently becomes zero tests."""
    declared = SWATCH.findall(GUIDE.read_text())
    assert len(declared) == len(swatch_pairs()) and declared, (
        f"{len(declared)} `.sw` attribute list(s) in the guide, "
        f"{len(swatch_pairs())} of them attached to a hex in a code span")


@pytest.mark.parametrize("declared,labelled", swatch_pairs())
def test_the_swatch_color_is_the_hex_it_labels(declared, labelled):
    assert declared.lower() == labelled.lower(), (
        f"a swatch is drawn {declared} on `{labelled}`. The square is what a "
        "reader believes; the hex is what the figure gets.")


@pytest.mark.parametrize("hex_color,_quoted", table_rows())
def test_every_palette_row_carries_a_swatch(hex_color, _quoted):
    """The Okabe-Ito table is where the swatches earn their place: "vermillion"
    and "reddish purple" are the guide asking a reader to imagine a color. A row
    added without one is the omission this catches; `ROW` treats the swatch as
    optional so that a missing one fails here, by name, instead of dropping the
    row out of every contrast assertion above."""
    declared = [d for d, labelled in swatch_pairs()
                if labelled.lower() == hex_color.lower()]
    assert declared, f"the {hex_color} row of the palette table has no swatch"


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


# --- which rows can actually fail --------------------------------------------
# The roster test above proved the README names every gate. It said nothing
# about what each one is allowed to return, and the table was wrong there in
# both directions: `Overplotting` and `Contour dash` were given a "Fails when"
# neither can do -- both return only True or "warn" -- and the prose counted
# five advisory rows against an actual seven. `ADVISORY_GATES` in
# check_figure.py is now the one list, and these hold the docs to it.

def readme_advisory_names():
    """Gates the README table marks *(advisory)*, from the same parse the
    roster test uses, so the two cannot disagree about which rows exist."""
    lines = README.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if "**`check_figure.py`**" in l)
    out = []
    for line in lines[start:]:
        if line.startswith("|"):
            cells = line.strip().strip("|").split("|")
            if "*(advisory)*" in line:
                out.append(cells[0].strip())
        elif out:
            break
    return set(out)


def test_the_readme_marks_exactly_the_advisory_gates():
    import check_figure as cf

    assert readme_advisory_names() == set(cf.ADVISORY_GATES)


def test_the_readme_states_the_advisory_count_it_marks():
    """The number in the prose and the tags in the table are the same claim
    written twice, which is how one of them came to be wrong."""
    import check_figure as cf

    claimed = re.search(r"\*\*WARN is not FAIL\.\*\*\s+(\w+)", README.read_text())
    assert claimed, ("the README no longer states an advisory count in the "
                     "form this test reads")
    word = claimed.group(1).lower()
    assert word in WORD_NUMBERS, f"unreadable advisory count {word!r}"
    assert WORD_NUMBERS[word] == len(cf.ADVISORY_GATES)


def test_every_advisory_gate_is_a_gate_that_exists():
    import check_figure as cf

    assert set(cf.ADVISORY_GATES) <= set(audit_gate_names())


def test_no_advisory_gate_ever_returns_false():
    """The claim `ADVISORY_GATES` makes, asked of the code rather than trusted.

    A gate moved into the set by mistake -- or one that grows a hard failure
    later without being moved out -- is a README that promises a row cannot
    fail a build while it can.

    This is a heuristic and worth naming as one: it reads return statements out
    of the source and looks for the shapes that can evaluate False. It cannot
    see a False routed through a variable or a helper, so it catches the
    obvious regression rather than proving the negative. The per-gate tests in
    `test_figure.py` are what actually pin each row's behaviour; this is the
    cheap tripwire over the set as a whole.
    """
    import inspect

    import check_figure as cf

    by_gate = {
        "Overplotting": cf.check_overplotting,
        "Ink coverage": cf.check_ink,
        "Identity channel": cf.check_identity_channel,
        "Style sheet": cf.check_style_sheet,
        "Contour dash": cf.check_contour_dash,
        "Fonts": cf.check_fonts,
        "Alt text": cf.check_alt_text,
    }
    assert set(by_gate) == set(cf.ADVISORY_GATES), (
        "this mapping is out of date with ADVISORY_GATES")
    for name, fn in by_gate.items():
        returns = re.findall(r"return\s+(.+)", inspect.getsource(fn))
        bad = [r for r in returns if r.startswith(("False", "(False", "ok,",
                                                   "(ok", "not "))]
        assert not bad, f"{name} has a returning-False path: {bad}"


# --- the threshold column ----------------------------------------------------
# Four rosters are held to `audit()`: the module docstring, the README table's
# first column, SKILL.md's sentence, and the advisory tags. The numbers beside
# them were held to nothing. Eleven of the twenty rows name a constant and quote
# its value, and every one of them agreed on the day this was written - which is
# the argument for writing it, not against. `#fcfcfb` was the surface the
# contrast table really had been computed against; `#898781` really was in the
# style sheet; the test count really was 171. Each was right when it was typed.
# This column is eleven claims of that shape with no machinery under them.

THRESHOLD_CONST = re.compile(
    r"`([A-Z][A-Z0-9_]*(?:\s*,\s*[A-Z][A-Z0-9_]*)*)\s*=\s*([^`]+)`")

# Rows whose threshold is a phrase rather than a constant. A literal set, so
# that a gate arriving with an unquantified threshold is a decision someone
# writes down - the discipline `ADVISORY_GATES` already imposes on the other
# optional column. Two of these are checkable numbers wearing prose and have
# their own tests below; the remaining seven have nothing to check.
PROSE_THRESHOLDS = {
    "Clipping",           # canvas bounds
    "Text collision",     # bbox overlap
    "Axis redundancy",    # shared scale
    "Dual axis",          # no threshold
    "Form",               # no threshold
    "Identity channel",   # no threshold
    "Contour dash",       # no threshold
    "Style sheet",        # "40 keys", checked below
    "Fonts",              # "Type 42", checked below
}


def readme_gate_rows():
    """(gate, threshold) for every row of the README gate table.

    A second read of the table `readme_gate_names` parses, taking the column
    beside the one that parser takes. Deliberately not folded into it: that
    function's docstring records a README rewrite which added this very column
    and turned a regex-based parser into one that silently matched zero rows,
    and the fix was to stop caring how many columns there are. Reaching into a
    second cell by index cares again, so it cares here rather than making the
    roster check care too.
    """
    lines = README.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if "**`check_figure.py`**" in l)
    rows = []
    for line in lines[start:]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                rows.append((cells[0], cells[1]))
        elif rows:
            break
    return [(gate, threshold) for gate, threshold in rows
            if gate != "Gate" and set(gate) != {"-"}]


def quoted_thresholds():
    """(gate, constant, quoted value) for every constant the column names.

    One row declares two in one code span - `INK_MIN, INK_MAX = 0.02, 0.55` -
    and a pattern written for the single form matches that row zero times
    rather than failing on it. The names and the values are zipped, and
    `test_every_quoted_constant_got_a_value` is what makes a row that lists
    three names and two values a failure instead of a dropped assertion.
    """
    out = []
    for gate, cell in readme_gate_rows():
        for names, values in THRESHOLD_CONST.findall(cell):
            for name, value in zip(names.split(","), values.split(",")):
                out.append((gate, name.strip(), value.strip()))
    return out


def constant_value(name):
    """(module, value) for a constant named in the table.

    Raises rather than skipping. A constant renamed in code and left in the
    README is exactly what this gate is for, and a lookup that shrugs at a name
    it cannot find reports agreement with nothing.
    """
    import check_figure as cf

    for module in (cf, cp):
        if hasattr(module, name):
            return module.__name__, getattr(module, name)
    raise AssertionError(
        f"the README threshold column names {name}, which is in neither "
        "check_figure.py nor check_palette.py")


def test_the_threshold_column_is_still_parseable():
    """Every row either quotes a constant or is a named exception. Written this
    way rather than as a count so that it stays true as gates are added, and
    still fails loudly if the column moves or changes shape."""
    quoted = {gate for gate, _, _ in quoted_thresholds()}
    silent = [gate for gate, _ in readme_gate_rows()
              if gate not in quoted and gate not in PROSE_THRESHOLDS]
    assert not silent, (
        f"{silent} quote no threshold constant and are not in "
        "PROSE_THRESHOLDS - either the cell names a constant in a form "
        "THRESHOLD_CONST no longer matches, or the row genuinely has no "
        "number and belongs in the set")


def test_the_prose_thresholds_are_gates_that_exist():
    assert PROSE_THRESHOLDS <= set(audit_gate_names()), (
        "PROSE_THRESHOLDS names rows the README table does not have: "
        f"{sorted(PROSE_THRESHOLDS - set(audit_gate_names()))}")


def test_every_quoted_constant_got_a_value():
    """`zip` truncates. A cell naming three constants and quoting two values
    would otherwise drop the third assertion rather than fail."""
    for gate, cell in readme_gate_rows():
        for names, values in THRESHOLD_CONST.findall(cell):
            assert len(names.split(",")) == len(values.split(",")), (
                f"{gate} names {len(names.split(','))} constants and quotes "
                f"{len(values.split(','))} values: {cell!r}")


@pytest.mark.parametrize("gate,name,quoted", quoted_thresholds())
def test_the_quoted_threshold_is_the_constants_value(gate, name, quoted):
    module, actual = constant_value(name)
    try:
        agrees = float(quoted) == float(actual)
    except (TypeError, ValueError):
        agrees = quoted == str(actual)
    assert agrees, (
        f"the README's {gate} row quotes {name} = {quoted}; "
        f"{module}.{name} is {actual!r}. One of the two is wrong, and it is "
        "not automatically the README")


def test_the_style_sheet_row_states_the_number_of_keys_the_sheet_sets():
    """"40 keys" is a measurement in prose, in a column this file now checks
    everywhere else. The sheet is the thing that can change under it."""
    import matplotlib as mpl

    from conftest import STYLE_SHEET

    cell = dict(readme_gate_rows())["Style sheet"]
    claimed = re.search(r"(\d+)\s+keys", cell)
    assert claimed, (
        f"the Style sheet row no longer states a key count: {cell!r}")
    actual = len(mpl.rc_params_from_file(STYLE_SHEET,
                                         use_default_template=False))
    assert int(claimed.group(1)) == actual, (
        f"the README says figure.mplstyle sets {claimed.group(1)} keys; it "
        f"sets {actual}")


def test_the_fonts_row_names_the_type_the_sheet_declares():
    """The other prose number. `check_fonts` fails a figure whose rcParams say
    Type 3, and the only reason they do not is that the shipped sheet declares
    42 - so the README's claim is really a claim about the sheet."""
    import matplotlib as mpl

    from conftest import STYLE_SHEET

    cell = dict(readme_gate_rows())["Fonts"]
    claimed = re.search(r"Type\s+(\d+)", cell)
    assert claimed, f"the Fonts row no longer names a font type: {cell!r}"
    params = mpl.rc_params_from_file(STYLE_SHEET, use_default_template=False)
    for key in ("pdf.fonttype", "ps.fonttype"):
        assert key in params, f"figure.mplstyle does not set {key}"
        assert params[key] == int(claimed.group(1)), (
            f"the README says {claimed.group(0)}; figure.mplstyle sets "
            f"{key} to {params[key]}")


# --- the ink tokens the guide hands you --------------------------------------
# Same failure as the contrast table and the retired surface, a third time: the
# guide's ink table listed muted ink as `#898781`, which the sheet stopped
# shipping when `check_text_readability` failed the sheet's own tick labels
# against it at 3.59:1. The table said "Defined in figure.mplstyle" beside a
# value figure.mplstyle does not define.

INK_TABLE_ROW = re.compile(r"^\|[^|]+\|([^|]*`#[0-9A-Fa-f]{6}`[^|]*)\|\s*"
                           r"`figure\.mplstyle`\s*\|")


def guide_ink_hexes():
    out = []
    for line in GUIDE.read_text().splitlines():
        m = INK_TABLE_ROW.match(line)
        if m:
            out.extend(h.lower() for h in
                       re.findall(r"`(#[0-9A-Fa-f]{6})`", m.group(1)))
    return out


def sheet_hexes():
    """Every color the style sheet actually sets, as normalised hex.

    Read through `rc_params_from_file` rather than grepped, because the sheet
    spells white as `white` and its hexes bare (a leading `#` is a comment in
    that format).
    """
    import matplotlib as mpl
    from matplotlib.colors import to_hex

    from conftest import STYLE_SHEET

    out = set()
    for value in mpl.rc_params_from_file(
            STYLE_SHEET, use_default_template=False).values():
        for item in (value if isinstance(value, (list, tuple)) else [value]):
            try:
                out.add(to_hex(item).lower())
            except (ValueError, TypeError):
                continue
    return out


def test_the_ink_table_is_still_parseable():
    assert len(guide_ink_hexes()) == 6, (
        f"expected the 6 ink/furniture tokens, matched {guide_ink_hexes()}")


@pytest.mark.parametrize("hex_color", guide_ink_hexes())
def test_every_token_the_guide_credits_to_the_sheet_is_in_the_sheet(hex_color):
    assert hex_color in sheet_hexes(), (
        f"{hex_color} is listed as defined in figure.mplstyle, which sets "
        f"{sorted(sheet_hexes())}")


# --- the all-pairs limit -----------------------------------------------------
# "Only the first four slots clear all-pairs" was in three documents and the
# appendix constant, and no one had run it: five clear it at dE 11.2 against a
# target of 8, and six is the first count that fails. A recommendation stated
# as a measurement has to be the measurement.

SERIES_SLOTS = ["#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00", "#CC79A7"]


def largest_all_pairs_count():
    """The most slots, taken in order, that clear every gate in all-pairs mode."""
    best = 1
    for n in range(2, len(SERIES_SLOTS) + 1):
        _, ok = cp.check(SERIES_SLOTS[:n], all_pairs=True)
        if not ok:
            break
        best = n
    return best


def test_the_series_slots_are_the_ones_the_style_sheet_cycles():
    """If the sheet's cycle changes, the number below is about a palette
    nothing draws."""
    import matplotlib as mpl

    from conftest import STYLE_SHEET

    cycle = mpl.rc_params_from_file(
        STYLE_SHEET, use_default_template=False)["axes.prop_cycle"]
    assert [c.lower() for c in cycle.by_key()["color"]] == \
        [c.lower() for c in SERIES_SLOTS]


def test_the_guide_quotes_the_all_pairs_limit_it_measures():
    written = re.search(r"MAX_SERIES, MAX_SERIES_ALL_PAIRS = (\d+), (\d+)",
                        GUIDE.read_text())
    assert written, "the appendix no longer states the constants in this form"
    assert int(written.group(2)) == largest_all_pairs_count()


def test_the_prose_agrees_with_the_appendix_constant():
    """Two documents say the limit in words. Both have been wrong."""
    words = {"three": 3, "four": 4, "five": 5, "six": 6}
    limit = largest_all_pairs_count()
    for path in (GUIDE, SKILL / "SKILL.md"):
        found = re.findall(r"first[- ](\w+) slots? clear", path.read_text())
        assert found, f"{path.name} no longer states the limit in words"
        for word in found:
            assert words.get(word.lower()) == limit, (
                f"{path.name} says 'first {word}', measured {limit}")


def test_validator_default_surface_is_what_the_style_sheet_renders():
    """The two have to be the same value or the table is measuring a page the
    figures are not drawn on. That is the whole bug this file guards."""
    import inspect
    sig = inspect.signature(cp.check)
    assert sig.parameters["surface"].default == SURFACE


# --- the same claim, told three times ----------------------------------------
# `examples/gallery.py` says writing the six figures found six defects in the
# checks, and enumerates six. The README said five. Both numbers are prose, so
# neither could be wrong loudly, and the wrong one had been sitting in the
# README long enough to be copied into the docs site when that was written -
# which is how a number in prose spreads rather than gets corrected.

GALLERY = README.parent / "examples" / "gallery.py"
DOCS_GALLERY = README.parent / "docs" / "gallery.md"

DEFECT_COUNT = re.compile(r"found (\w+) defects? in")


def defect_claims():
    """Every file that states how many defects writing the gallery found."""
    return {path.name: DEFECT_COUNT.search(path.read_text())
            for path in (GALLERY, README, DOCS_GALLERY)}


def test_every_source_still_states_a_defect_count():
    """A regex that matches nothing agrees with everything."""
    missing = [name for name, match in defect_claims().items() if not match]
    assert not missing, (
        f"{missing} no longer state a defect count in the form this test "
        "reads - the sentence was rewritten and this test needs updating")


def test_the_three_sources_agree_on_the_defect_count():
    claims = {name: match.group(1) for name, match in defect_claims().items()}
    assert len(set(claims.values())) == 1, (
        f"the sources disagree: {claims}. gallery.py enumerates its six by "
        "name, so it is the one to trust.")


# --- the fourth roster, the one in prose -------------------------------------
# The roster tests above cover the README table and the module docstring.
# `SKILL.md` names every gate a third time, in a sentence, and nothing read it:
# it listed eighteen of the nineteen, omitting `Contour dash`, from the commit
# that added the gate until this one. Same failure as the other two rosters, in
# the file an agent actually loads.
#
# Prose does not use the gate's label, so the join has to be written down. It is
# asserted complete against `audit` rather than trusted, which is what stops a
# twentieth gate from being added to the code and to two rosters but not this
# one - the map goes stale loudly.

SKILL_MD = SKILL / "SKILL.md"

FIGURE_PROSE = {
    "Clipping": "clipping",
    "Text collision": "text collision",
    "Text readability": "text readability",
    "Contrast stack": "alpha stacking",
    "Mark ratio": "mark ratio",
    "Overplotting": "overplotting",
    "Axis redundancy": "axis redundancy",
    "Type size": "type size",
    "Line weight": "line weight",
    "Ink coverage": "ink coverage",
    "Series color": "series color",
    "Dual axis": "dual axes",
    "Form": "form",
    "Identity channel": "the identity channel",
    "Label attribution": "label attribution",
    "Style sheet": "whether the style sheet is the one actually in effect",
    "Contour dash": "contour dash",
    "Colormap kind": "colormap kind",
    "Fonts": "font embedding",
    "Alt text": "alt text",
}

PALETTE_PROSE = {
    "Lightness band": "lightness band",
    "Chroma floor": "chroma floor",
    "CVD separation (adjacent)": "colorblind separation",
    "Normal-vision floor (adjacent)": "normal-vision separation",
    "Contrast vs surface": "contrast against the surface",
}


def roster_paragraph():
    """The one paragraph in SKILL.md that lists both rosters.

    Found by holding both openings at once, because neither is unique on its
    own: "`check_figure.py` gates the mechanical subset" appears earlier, in the
    section on choosing a form, and anchoring on the first match read the roster
    out of that sentence instead - a parser that matched three words of prose
    and reported that eighteen gates were missing from it.
    """
    blocks = [" ".join(b.split())
              for b in re.split(r"\n\s*\n", SKILL_MD.read_text())]
    hits = [b for b in blocks if "`check_palette.py` gates " in b
            and "`check_figure.py` gates " in b]
    assert len(hits) == 1, (
        f"expected one paragraph in SKILL.md listing both rosters, found "
        f"{len(hits)} - the section was rewritten and this parser needs "
        "updating with it")
    return hits[0]


def prose_roster(script):
    """One script's list, out of that paragraph.

    Bounded by the next `check_*.py` mention rather than by a full stop: the
    sentence opens with a filename, so splitting on "." cuts it in half at the
    first word.
    """
    paragraph = roster_paragraph()
    opening = f"`{script}` gates "
    rest = paragraph[paragraph.index(opening) + len(opening):]
    end = rest.find("`check_")
    return rest if end == -1 else rest[:end]


def palette_gate_names():
    """The executable palette roster, in the order `check` returns it."""
    rows, _ = cp.check(SERIES_SLOTS[:3])
    return [name for name, _, _ in rows]


@pytest.mark.parametrize("script,names,prose", [
    ("check_figure.py", audit_gate_names, FIGURE_PROSE),
    ("check_palette.py", palette_gate_names, PALETTE_PROSE),
])
def test_the_prose_map_covers_exactly_the_gates_that_exist(script, names, prose):
    """Asserted before the tests below draw conclusions from the map. A map
    missing a gate would otherwise let that gate go unmentioned in the prose
    and unnoticed here - which is precisely how `Contour dash` was lost."""
    assert set(prose) == set(names()), (
        f"the {script} prose map is out of date with the roster {script} "
        f"actually returns: {sorted(set(names()) ^ set(prose))}")


@pytest.mark.parametrize("script,names,prose", [
    ("check_figure.py", audit_gate_names, FIGURE_PROSE),
    ("check_palette.py", palette_gate_names, PALETTE_PROSE),
])
def test_the_skill_prose_names_every_gate_in_order(script, names, prose):
    sentence = prose_roster(script)
    positions = {}
    for gate in names():
        phrase = prose[gate]
        found = re.search(rf"\b{re.escape(phrase)}\b", sentence)
        assert found, (
            f"SKILL.md's {script} sentence does not name {gate!r} "
            f"(looked for {phrase!r})")
        positions[gate] = found.start()

    ordered = sorted(positions, key=positions.get)
    assert ordered == names(), (
        f"SKILL.md lists the {script} gates in a different order than "
        f"{script} returns them:\n  prose: {ordered}\n  code:  {names()}")


# --- quoted contrast ratios outside the palette table ------------------------
# The contrast table is checked row by row. A ratio written into a sentence was
# not, and one had been computed against `#fcfcfb` - the surface retired three
# releases ago - since before that retirement: full-range viridis was quoted at
# 1.23:1, which is its ratio on `#fcfcfb`. On white, which is what the sheet
# renders, it is 1.26:1. Fourth instance of the retired-surface bug, and the
# reason the guard for it cannot just be a grep for the string "fcfcfb".

# The optional swatch is the guide's; SKILL.md states the same endpoint in plain
# prose and carries none. One pattern reads both, so neither document can state
# the endpoint in a form this stops matching without the guard below noticing.
VIRIDIS_CLAIM = re.compile(
    r"viridis\s+ends\s+at\s+`(#[0-9A-Fa-f]{6})`(?:" + SWATCH_ATTRS + r")?"
    r",\s*([\d.]+):1", re.I)


def viridis_claims():
    return {path.name: VIRIDIS_CLAIM.search(" ".join(path.read_text().split()))
            for path in (GUIDE, SKILL_MD)}


def test_both_documents_still_quote_the_viridis_endpoint():
    missing = [name for name, m in viridis_claims().items() if not m]
    assert not missing, (
        f"{missing} no longer state the viridis endpoint in the form this test "
        "reads - the sentence was rewritten and this test needs updating")


@pytest.mark.parametrize("name", ["style-guide.md", "SKILL.md"])
def test_the_quoted_viridis_endpoint_is_the_real_one(name):
    """Both halves of the claim: that the hex is where viridis actually ends,
    and that the ratio is that hex against the surface the sheet renders."""
    from matplotlib import colormaps
    from matplotlib.colors import to_hex

    # Groups, not `.groups()`: the second is the optional swatch, whose
    # agreement with the first is `test_the_swatch_color_is_the_hex_it_labels`'s
    # job.
    match = viridis_claims()[name]
    hex_color, quoted = match.group(1), match.group(3)
    assert hex_color.lower() == to_hex(colormaps["viridis"](1.0)).lower(), (
        f"{name} says viridis ends at {hex_color}, matplotlib says "
        f"{to_hex(colormaps['viridis'](1.0))}")
    computed = cp.contrast(hex_color, SURFACE)
    assert computed == pytest.approx(float(quoted), abs=0.01), (
        f"{name} quotes {quoted}:1 for {hex_color}; against {SURFACE} it is "
        f"{computed:.2f}:1 (it is {cp.contrast(hex_color, '#fcfcfb'):.2f}:1 "
        "against the retired #fcfcfb surface, which is where 1.23 came from)")


# --- the grayscale numbers are in a different unit ---------------------------
# `ΔL 0.011` read as the OKLab lightness the rest of the guide measures in, and
# it is not: it is WCAG relative luminance, which is the right channel for a
# question about desaturation and the wrong label for a document whose stated
# unit is OKLab ΔE ×100. In OKLab the same pairs are 0.018 and 0.221. Nothing
# was wrong except the unit, which is enough - a reader recomputing it concludes
# the guide drifted. Both documents now name the unit, and both are checked.

LUMINANCE_CLAIM = re.compile(
    r"relative luminance ([\d.]+) \(`(#[0-9A-Fa-f]{6})` vs `(#[0-9A-Fa-f]{6})`\)")


def luminance_claims():
    out = []
    for path in (GUIDE, SKILL_MD):
        for m in LUMINANCE_CLAIM.finditer(" ".join(path.read_text().split())):
            out.append((path.name, float(m.group(1)), m.group(2), m.group(3)))
    return out


def test_both_documents_still_state_the_grayscale_separations():
    found = {name for name, *_ in luminance_claims()}
    assert found == {"style-guide.md", "SKILL.md"}, (
        f"only {sorted(found)} state a relative-luminance separation in the "
        "form this test reads")
    assert len(luminance_claims()) == 4, (
        f"expected two pairs in each document, matched {len(luminance_claims())}")


@pytest.mark.parametrize("name,quoted,a,b", luminance_claims())
def test_quoted_relative_luminance_matches_computed(name, quoted, a, b):
    computed = abs(cp.relative_luminance(cp.hex_to_linear(a))
                   - cp.relative_luminance(cp.hex_to_linear(b)))
    assert computed == pytest.approx(quoted, abs=0.001), (
        f"{name}: {a} vs {b} quoted at {quoted}, relative_luminance() gives "
        f"{computed:.3f}")


OKLAB_ASIDE = re.compile(
    r"In OKLab lightness the same two pairs are ([\d.]+) and ([\d.]+)")


def test_the_oklab_aside_quotes_the_oklab_numbers():
    """The sentence that disambiguates the unit quotes the other convention's
    values, which makes it two more numbers in prose - the species this whole
    file exists for. It states them so a reader who recomputed in OKLab and got
    a different answer can see their own arithmetic rather than suspect the
    guide, so it is worth keeping and worth checking.
    """
    written = OKLAB_ASIDE.search(" ".join(GUIDE.read_text().split()))
    assert written, ("the guide no longer states the OKLab equivalents in the "
                     "form this test reads")

    pairs = [(a, b) for name, _, a, b in luminance_claims()
             if name == "style-guide.md"]
    assert len(pairs) == 2, f"expected two pairs in the guide, found {pairs}"

    for quoted, (a, b) in zip(written.groups(), pairs):
        computed = abs(cp.linear_to_oklab(cp.hex_to_linear(a))[0]
                       - cp.linear_to_oklab(cp.hex_to_linear(b))[0])
        assert computed == pytest.approx(float(quoted), abs=0.001), (
            f"the guide says {a} vs {b} is {quoted} in OKLab lightness; "
            f"linear_to_oklab() gives {computed:.3f}")


def test_the_guide_says_which_unit_the_grayscale_numbers_are_in():
    """The fix for the original defect, held in place. Without the sentence
    naming the unit, the numbers are correct and unreadable: the guide states
    OKLab ΔE ×100 as its convention everywhere else."""
    for path in (GUIDE, SKILL_MD):
        text = " ".join(path.read_text().split())
        assert re.search(r"relative luminance[^.]*OKLab", text), (
            f"{path.name} quotes relative-luminance separations without saying "
            "they are not the OKLab unit the rest of the document uses")


# --- the alt text on the site is the alt text the figure carries -------------
# `docs/gallery.md` states outright that every alt text on the page is the
# string passed to `describe(fig, ...)`, which is what makes the page's alt text
# checked rather than written once and forgotten. It was true of the six gallery
# figures and false of `demo.png`, whose alt had been paraphrased in the README
# and copied into the site from there. A claim that the docs are generated from
# the code, made in prose, about docs that are not.

DEMO = README.parent / "examples" / "demo.py"

MARKDOWN_IMAGE = re.compile(r"!\[([^\]]+)\]\((?:[^)]*/)?([\w.-]+\.png)\)")


def described_strings():
    """Every alt text the examples actually attach to a figure.

    Two call shapes, and both are read rather than one being assumed:
    `demo.py` calls `describe(fig, "...")` with the literal inline, and
    `gallery.py` routes it through `finish(fig, name, "...")`, which calls
    `describe` with a name the AST cannot resolve to a string.
    """
    import ast

    out = []
    for path in (DEMO, GALLERY):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            func = getattr(node.func, "attr", None) or getattr(
                node.func, "id", None)
            index = {"describe": 1, "finish": 2}.get(func)
            if index is None or len(node.args) <= index:
                continue
            try:
                value = ast.literal_eval(node.args[index])
            except ValueError:
                continue
            if isinstance(value, str):
                out.append(" ".join(value.split()))
    return out


def site_alt_texts():
    return {" ".join(alt.split()): image for alt, image
            in MARKDOWN_IMAGE.findall(DOCS_GALLERY.read_text())}


def test_the_examples_still_describe_every_figure():
    """Seven figures, seven descriptions. A refactor that changes the call
    shape would otherwise leave this file comparing the site against a shorter
    list and finding no disagreement."""
    assert len(described_strings()) == 8, (
        f"read {len(described_strings())} descriptions out of demo.py and "
        "gallery.py, expected 8 - the call shape changed and "
        "described_strings() needs updating with it")


def test_the_gallery_page_shows_every_figures_own_alt_text():
    assert set(site_alt_texts()) == set(described_strings()), (
        "docs/gallery.md says every alt text on the page is the string the "
        "figure carries. Not on the page but described: "
        f"{sorted(set(described_strings()) - set(site_alt_texts()))}. On the "
        "page but described by nothing: "
        f"{sorted(set(site_alt_texts()) - set(described_strings()))}")


def test_the_readme_shows_the_demo_figures_own_alt_text():
    """The README is where the paraphrase entered, and it is the copy PyPI
    renders, so it is checked separately from the page it was copied into."""
    alts = [" ".join(alt.split())
            for alt, image in MARKDOWN_IMAGE.findall(README.read_text())]
    assert alts, "the README no longer embeds an image with alt text"
    for alt in alts:
        assert alt in described_strings(), (
            f"the README's alt text is not one any example attaches:\n"
            f"  README: {alt}")


# --- the call the docs teach ------------------------------------------------
# `alt_metadata(fig)` without the path warns on every PDF save and returns the
# wrong key for SVG. It was corrected in SKILL.md and in both examples and left
# standing in the style guide, so the release note announcing the fix shipped
# beside a document still teaching the break. The CHANGELOG is excluded: it
# quotes the broken form deliberately, as the history of it.

TEACHING_DOCS = [README, SKILL_MD, GUIDE, DOCS_GALLERY,
                 SKILL / "references" / "choosing-a-form.md",
                 README.parent / "CONTRIBUTING.md"]


def test_no_document_teaches_the_pathless_alt_metadata_call():
    bad = []
    for path in TEACHING_DOCS:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"metadata\s*=\s*alt_metadata\(\s*\w+\s*\)", line):
                bad.append(f"{path.name}:{number}")
    assert not bad, (
        f"{bad} pass alt_metadata a figure and no path. That returns "
        "'Description', which matplotlib warns about on every PDF save and "
        "which SVG rejects outright - pass the path too")


# --- the colormap kinds the guide names --------------------------------------
# The guide now recommends a colormap per kind and states which key that kind
# takes. "twilight is cyclic" is a claim about `cmap_kind()`, in the same class
# as every contrast ratio in this file: prose asserting something the code
# computes. It is also the first claim of that class the guide has ever made
# about a colormap, and the gate row that motivated it shipped with a table row
# and no explanation anywhere, so the join is worth having from the start.

KIND_ROW = re.compile(
    r"^\|\s*(Sequential|Diverging|Cyclic|Qualitative)\s*\|[^|]*\|\s*"
    r"`([A-Za-z_0-9]+)`\s*\|")
MISC_CLAIM = re.compile(r"((?:`[A-Za-z_0-9]+`(?:,\s*|\s+and\s+)?)+)\s*land there")


def guide_kind_claims():
    """(kind, colormap) for every row of the guide's kind table."""
    return [(m.group(1).lower(), m.group(2))
            for m in map(KIND_ROW.match, GUIDE.read_text().splitlines()) if m]


def guide_misc_claims():
    """The colormaps the guide names as failing."""
    match = MISC_CLAIM.search(" ".join(GUIDE.read_text().split()))
    return re.findall(r"`([A-Za-z_0-9]+)`", match.group(1)) if match else []


def cmap_levels(name):
    """The guide's colormap, sampled the way `check_colormap` samples it."""
    from matplotlib import colormaps
    from matplotlib.colors import to_hex

    cmap = colormaps[name]
    if cmap.N < cp.CMAP_QUALITATIVE_N:
        return [to_hex(cmap(i)) for i in range(cmap.N)]
    return [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
            for i in range(cp.CMAP_SAMPLES)]


def test_the_kind_table_is_still_parseable():
    """Four kinds, four rows. A parser that matched three would let one
    recommendation go unchecked and report agreement about the rest."""
    claims = guide_kind_claims()
    assert len(claims) == 4, (
        f"expected the guide's four kind rows, matched {claims}")


def test_the_misc_sentence_is_still_parseable():
    assert guide_misc_claims(), (
        "the guide no longer names the colormaps that classify misc in the "
        "form this test reads - the sentence was rewritten")


@pytest.mark.parametrize("kind,name", guide_kind_claims())
def test_the_colormap_the_guide_recommends_is_that_kind(kind, name):
    from matplotlib import colormaps

    if name not in colormaps:
        pytest.skip(f"this matplotlib has no {name} colormap")
    measured = cp.cmap_kind(cmap_levels(name))
    assert measured == kind, (
        f"the guide recommends {name} for {kind} encodings; cmap_kind() "
        f"classifies it {measured}, so the gate would judge it as one")


@pytest.mark.parametrize("name", guide_misc_claims())
def test_the_colormaps_the_guide_condemns_do_fail(name):
    from matplotlib import colormaps

    if name not in colormaps:
        pytest.skip(f"this matplotlib has no {name} colormap")
    measured = cp.cmap_kind(cmap_levels(name))
    assert measured == "misc", (
        f"the guide says {name} classifies misc and fails; cmap_kind() "
        f"returns {measured}, which passes")


# --- constants quoted in the reference material ------------------------------
# The README's threshold column is checked above. The guide quotes constants
# too, now that it explains how the kind is measured, and a guide that names a
# threshold is making the same executable claim a table cell does. One pattern,
# both documents, so a constant renamed in code cannot be left standing in
# either.

CONSTANT_DOCS = [GUIDE, SKILL_MD]


def doc_constant_claims():
    out = []
    for path in CONSTANT_DOCS:
        for names, values in THRESHOLD_CONST.findall(path.read_text()):
            for name, value in zip(names.split(","), values.split(",")):
                out.append((path.name, name.strip(), value.strip()))
    return out


def test_the_reference_material_still_quotes_constants():
    """This gate is only worth its line count while something matches it. If
    the guide stops naming thresholds the test should be removed, not left
    passing on an empty parse."""
    assert doc_constant_claims(), (
        f"{[p.name for p in CONSTANT_DOCS]} quote no `NAME = value` constants "
        "in the form this test reads")


@pytest.mark.parametrize("document,name,quoted", doc_constant_claims())
def test_the_constant_the_guide_quotes_is_the_codes_value(document, name,
                                                          quoted):
    module, actual = constant_value(name)
    try:
        agrees = float(quoted) == float(actual)
    except (TypeError, ValueError):
        agrees = quoted == str(actual)
    assert agrees, (
        f"{document} quotes {name} = {quoted}; {module}.{name} is {actual!r}")


# --- the roster count, written in prose seven times ---------------------------
# The gate table's rows are checked against `audit()`. The number of them is
# stated in prose beside it, and that was not: the colormap gate took the roster
# from 19 to 20, updated two of the seven places the README says how many there
# are, and left five reading 19 - including "20 passing rows means the figure
# avoids 20 named defects", which is the sentence that tells a reader what a
# passing run means.
#
# One sentence is deliberately not here. "A figure on matplotlib's default
# tab10 cycle ... returned nothing but passing rows" recounts an incident that
# happened at a particular roster size, and pinning it to today's count would
# make a historical anecdote drift every time a gate is added. It had a number
# in it and the number is now gone, which is the fix for that class rather than
# an exemption from this one.

WORD_NUMBERS = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                "ten": 10}

ROSTER_COUNT_CLAIMS = {
    "the audit() summary": r"returns `\(ok, rows\)`\s*\S*\s*(\d+) rows",
    "the report() comment": r"prints (\d+) rows, returns True if ok",
    "the series-color row number": r"That is row 11 of the (\d+)",
    "the gate table lead-in": r"`audit\(\)` returns these (\d+) rows",
    "the elimination-gate claim": r"(\d+) passing rows means the",
    "the named-defect count": r"figure avoids (\d+) named defects",
    "the advisory paragraph": r"of the (\d+) rows are advisory",
}


def roster_count_claims():
    text = " ".join(README.read_text().split())
    return {label: re.search(pattern, text)
            for label, pattern in ROSTER_COUNT_CLAIMS.items()}


def test_every_roster_count_claim_is_still_stated():
    """A regex that matches nothing agrees with everything, and this file has
    seven of them pointed at one document."""
    missing = [label for label, match in roster_count_claims().items()
               if not match]
    assert not missing, (
        f"{missing} no longer state the roster count in the form this test "
        "reads - the sentence was rewritten and ROSTER_COUNT_CLAIMS needs "
        "updating with it")


@pytest.mark.parametrize("label", sorted(ROSTER_COUNT_CLAIMS))
def test_the_readme_states_the_real_roster_count(label):
    match = roster_count_claims()[label]
    assert int(match.group(1)) == len(audit_gate_names()), (
        f"{label} says {match.group(1)} gates; `audit()` returns "
        f"{len(audit_gate_names())}")


# --- how many figures the gallery has ----------------------------------------
# Same shape, one document over. The seventh figure landed in `gallery.py` and
# in `docs/gallery.md`, and the README kept describing six and enumerating six
# forms. The count is executable - it is how many times the script calls
# `finish` - so nothing here needs to agree with anything but the script.

GALLERY_PY = README.parent / "examples" / "gallery.py"

GALLERY_COUNT_CLAIMS = {
    "gallery.py's docstring": (GALLERY_PY, r"(\w+) figures hard enough"),
    "the gallery page": (DOCS_GALLERY, r"builds these (\w+) and audits"),
    "the README": (README, r"Writing those (\w+) found"),
}


def gallery_figure_count():
    """The executable roster: the figures `gallery.py` actually finishes."""
    return len(re.findall(r'finish\(\s*\w+,\s*"gallery-',
                          GALLERY_PY.read_text()))


def gallery_count_claims():
    return {label: re.search(pattern, " ".join(path.read_text().split()))
            for label, (path, pattern) in GALLERY_COUNT_CLAIMS.items()}


def test_the_gallery_roster_is_still_readable():
    assert gallery_figure_count() > 1, (
        "matched no `finish(fig, \"gallery-...\")` calls in gallery.py - the "
        "script was restructured and gallery_figure_count() needs updating")
    missing = [label for label, match in gallery_count_claims().items()
               if not match]
    assert not missing, (
        f"{missing} no longer state how many figures the gallery has in the "
        "form this test reads")


@pytest.mark.parametrize("label", sorted(GALLERY_COUNT_CLAIMS))
def test_every_source_states_the_real_gallery_count(label):
    word = gallery_count_claims()[label].group(1).lower()
    assert word in WORD_NUMBERS, f"{label} states an unreadable count {word!r}"
    assert WORD_NUMBERS[word] == gallery_figure_count(), (
        f"{label} says {word} figures; gallery.py builds "
        f"{gallery_figure_count()}")


# --- every gate has somewhere to send a reader --------------------------------
# The fifth roster, and the one that is not a roster: the README table says what
# a gate measures, the reference material says why the rule is there and what to
# do instead, and nothing joined them. The colormap gate is the proof - it
# shipped with a table row, a threshold, an advisory tag, four rosters updated,
# and no explanation anywhere a reader would look. The suite was green.
#
# Prose does not use the gate's label, so the join is written down, the same way
# `FIGURE_PROSE` is. Asserted complete against `audit()`, so a twenty-first gate
# goes stale loudly instead of quietly having no guidance.

GUIDE_FILES = {"style-guide.md": GUIDE,
               "choosing-a-form.md": SKILL / "references" / "choosing-a-form.md"}

GUIDANCE_ANCHORS = {
    "Text collision": ("style-guide.md",
                       "hides the collision by deleting the data underneath"),
    "Text readability": ("style-guide.md", "4.5:1, or 3:1 at ≥14pt bold"),
    "Contrast stack": ("style-guide.md", "One thing opaque; ≤3 alpha levels"),
    "Mark ratio": ("style-guide.md",
                   "Emphasis = shape or label, not 5× the area"),
    "Overplotting": ("choosing-a-form.md",
                     "At large n, marks stop being individually visible"),
    "Axis redundancy": ("style-guide.md",
                        "Shared scale → shared axis furniture"),
    "Type size": ("style-guide.md", "fails any string under 7.5pt on page"),
    "Line weight": ("style-guide.md",
                    "Strokes have the same problem and the same arithmetic"),
    "Series color": ("style-guide.md", "### Categorical: Okabe-Ito"),
    "Dual axis": ("choosing-a-form.md", "**Dual y axes.**"),
    "Form": ("choosing-a-form.md", "The forms with no research-figure use"),
    "Identity channel": ("style-guide.md",
                         "add a second channel when it must survive a "
                         "photocopier"),
    "Label attribution": ("style-guide.md",
                          "### Direct labels: the alignment is the decision"),
    "Style sheet": ("style-guide.md", "**Build** on `figure.mplstyle`"),
    "Contour dash": ("style-guide.md",
                     '`linestyles="solid"` to `contour` on signed data'),
    "Colormap kind": ("style-guide.md", "### Which kind, and the key it takes"),
    "Fonts": ("style-guide.md", "**Embed fonts as Type 42.**"),
    "Alt text": ("style-guide.md", "shipped with no alt text"),
}

# Gates the reference material does not explain. Named rather than absent: an
# enumerable debt is worth more than a map that quietly covers eighteen of
# twenty. Both are mechanical rows with nothing to advise - a clipped label is
# fixed by moving it, and an ink fraction is read off the figure - but if
# either grows a rule it belongs in the guide and out of this set.
NO_GUIDANCE = {"Clipping", "Ink coverage"}


def test_the_guidance_map_covers_exactly_the_gates_that_exist():
    """Asserted before the test below draws conclusions from the map. A map
    missing a gate would otherwise let that gate go unexplained and unnoticed,
    which is how `Colormap kind` shipped without a word of guidance."""
    mapped = set(GUIDANCE_ANCHORS) | NO_GUIDANCE
    assert mapped == set(audit_gate_names()), (
        "the guidance map is out of date with the roster `audit()` returns: "
        f"{sorted(mapped ^ set(audit_gate_names()))}")


def test_no_gate_is_both_explained_and_exempt():
    assert not (set(GUIDANCE_ANCHORS) & NO_GUIDANCE), (
        f"{sorted(set(GUIDANCE_ANCHORS) & NO_GUIDANCE)} are in both the "
        "anchor map and the exemption set")


@pytest.mark.parametrize("gate", sorted(GUIDANCE_ANCHORS))
def test_every_gate_has_guidance_a_reader_can_find(gate):
    document, anchor = GUIDANCE_ANCHORS[gate]
    text = " ".join(GUIDE_FILES[document].read_text().split())
    assert anchor in text, (
        f"{gate} is anchored to {document} at {anchor!r}, which is no longer "
        "in that file. Either the passage was rewritten and the anchor needs "
        "updating, or the guidance was removed and the gate now explains "
        "itself nowhere")
