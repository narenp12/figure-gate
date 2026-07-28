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

    words = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
    claimed = re.search(r"\*\*WARN is not FAIL\.\*\*\s+(\w+)", README.read_text())
    assert claimed, ("the README no longer states an advisory count in the "
                     "form this test reads")
    word = claimed.group(1).lower()
    assert word in words, f"unreadable advisory count {word!r}"
    assert words[word] == len(cf.ADVISORY_GATES)


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
    """Every colour the style sheet actually sets, as normalised hex.

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
