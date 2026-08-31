"""A verdict is a property of the figure, not of the font list in effect when
it was measured.

`test_renderer_invariance.py` closed one half of this bug class: a pixel
threshold read against a resolution nobody pinned. This is the other half, and
it is the harder one to see, because nothing about the figure looks different
when it happens.

`examples/demo.py` and every gallery builder construct *and* report inside
`plt.style.context(figure.mplstyle)`, then hand the figure back with the context
closed. A caller who audits the returned figure is measuring under matplotlib's
defaults. The artists do not change: a label built under the sheet keeps
`family=['serif']`, because `font.family` is captured into its FontProperties at
construction. What changes is what `serif` resolves to. The sheet leads
`font.serif` with STIX Two Text; matplotlib's default leads it with DejaVu
Serif, and the same string at the same nominal size is 20% wider in the second
face. `constrained_layout` then re-solves against wider tick labels and moves
the axes, the annotations are anchored in data coordinates and do not move with
them, and `check_label_attribution` reads a label as nearer a curve that is not
its own.

That is not hypothetical either. On `demo` it produced a figure that printed
all-PASS from inside its own builder and failed `Label attribution` in the
sweep that audited the same object a moment later, with 'Tuned' measured 12px
from its own curve and 18px from another.

`check_figure.METRIC_RC_KEYS` and `_at_draw_rc` are the fix. The first audit of
a figure records those keys; every audit after it runs under the recorded
values.
"""

import contextlib
import importlib
import io
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

import check_figure as cf

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# Two builders, for two reasons. `demo` is the figure the defect was reported
# on. `encoding` is the gallery figure that failed the same sweep beside it, and
# it is a colormapped image rather than three curves, so a fix that only works
# on direct labels does not clear both.
BUILDERS = ("demo", "encoding")

# The rows that answer for the environment the caller is standing in rather than
# for the figure. They are the two rows that are *supposed* to move when the
# sheet is not in effect, and the test below says why each one is here.
ENVIRONMENT_ROWS = {"Style sheet", "Fonts"}


@pytest.fixture(scope="module")
def modules():
    """`demo` and `gallery`, imported with their writers switched off.

    Importing rather than running, for the reason `test_example.py` gives: the
    scripts write beside themselves by default and the committed PNG bytes
    depend on the locally installed fonts, so running them here leaves a binary
    diff in the working tree.
    """
    sys.path.insert(0, str(EXAMPLES))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            demo = importlib.import_module("demo")
            gallery = importlib.import_module("gallery")
    finally:
        sys.path.remove(str(EXAMPLES))
    gallery.OUT = None
    return {"demo": demo, "gallery": gallery}


def build(modules, name):
    """One built figure, with its builder's own report already run.

    Built through the decorated builder on purpose. The sheet being live across
    construction and across `cf.report`, and closed by the time the figure is
    returned, is not incidental to this test -- it is the situation under test.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        if name == "demo":
            fig, _ = modules["demo"].build(out=None)
            return fig
        return getattr(modules["gallery"], name)()


@pytest.mark.parametrize("name", BUILDERS)
def test_no_row_moves_when_the_sheet_is_no_longer_in_effect(modules, name):
    """The reported defect, as an assertion.

    Compared row by row including the detail strings, for the reason
    `test_renderer_invariance.py` gives: a status is a thresholded number, most
    of this corpus sits nowhere near a threshold, and the details carry the
    measurements.

    Two rows are excluded, and they are exactly the two that report on the
    *environment* rather than on the figure. `Style sheet` says whether the
    rcParams in effect are the sheet's, which is supposed to differ between a
    caller standing inside the sheet and one standing outside it; pinning it
    would have deleted the only warning that says the environment is not the
    sheet. `Fonts` differs on its Type 3 clause, which reads `pdf.fonttype` and
    `ps.fonttype` -- deliberately not metric keys, because that clause answers
    what a `savefig` from where the caller is standing would embed. Its other
    clause, the one that asks which face the figure was set in, reads the pinned
    family and does not move.
    """
    fig = build(modules, name)
    try:
        sheet = str(modules["demo"].STYLE)
        with plt.style.context(sheet):
            inside = cf.audit(fig)[1]
        outside = cf.audit(fig)[1]
    finally:
        plt.close(fig)

    moved = [(a[0], a[1], a[2], b[1], b[2])
             for a, b in zip(inside, outside)
             if a != b and a[0] not in ENVIRONMENT_ROWS]
    assert not moved, (
        f"{name} audited outside the sheet it was built under disagrees with "
        f"the same figure audited inside it: {moved}. A verdict is a property "
        f"of the figure; which font list happened to be in effect when the "
        f"caller asked is not.")


@pytest.mark.parametrize("name", BUILDERS)
def test_the_builders_own_verdict_survives_a_second_audit(modules, name):
    """The symptom as it was reported: audit the same figure twice, get two
    answers. The builders print their own report during `build`, so the audits
    below are the second and third, and all three have to agree."""
    fig = build(modules, name)
    try:
        first = cf.audit(fig)[0]
        second = cf.audit(fig)[0]
        third = cf.audit(fig)[0]
    finally:
        plt.close(fig)
    assert first is second is third, (
        f"{name} audited three times returned {first}, {second}, {third}")


def test_the_sweep_can_fail(modules, monkeypatch):
    """The behaviour `_at_draw_rc` replaced, put back, and caught.

    Emptying `METRIC_RC_KEYS` is exactly what this module did before the
    constant existed -- measure under whatever rcParams are live -- so this runs
    the old code path through the new one rather than asserting against a copy
    of it that could rot.

    `demo` because it is the figure the defect was reported on, and the row is
    named because a test that only asserts "something moved" would still pass
    once the thing that moved was some unrelated drift.
    """
    monkeypatch.setattr(cf, "METRIC_RC_KEYS", ())
    fig = build(modules, "demo")
    try:
        with plt.style.context(str(modules["demo"].STYLE)):
            inside = dict((label, detail) for label, _, detail in cf.audit(fig)[1])
        outside = dict((label, detail) for label, _, detail in cf.audit(fig)[1])
    finally:
        plt.close(fig)

    row = "Label attribution"
    assert inside[row] != outside[row], (
        "measuring under the live rcParams no longer moves demo's label "
        "attribution, so either the gate stopped reading text extents or this "
        f"test stopped reaching it. Either way it is no longer evidence that "
        f"METRIC_RC_KEYS does anything: {inside[row]!r}")


def test_the_record_is_taken_once_and_not_overwritten(modules):
    """Which audit sets the baseline, asserted rather than assumed.

    The whole fix rests on the record being the *first* audit's, because that is
    the one the builder runs while its sheet is still open. A record refreshed
    on every audit would restore the defect exactly: each audit would pin what
    the caller happened to be standing in, which is what it was already doing.
    """
    fig = build(modules, "demo")
    try:
        recorded = getattr(fig, cf.DRAW_RC_ATTR)
        assert recorded["font.serif"][0] == "STIX Two Text", (
            "demo's first audit runs inside its own builder, under the sheet, "
            f"so the record should be the sheet's font list: {recorded!r}")
        cf.audit(fig)
        assert getattr(fig, cf.DRAW_RC_ATTR)["font.serif"][0] == "STIX Two Text", (
            "a later audit overwrote the record with the caller's rcParams")
    finally:
        plt.close(fig)


@pytest.mark.parametrize("gate", ("check_ink", "check_text_readability"))
def test_a_gate_called_on_its_own_draws_under_the_record_audit_draws_under(
        modules, gate, monkeypatch):
    """The invariant `test_renderer_invariance.py` states for resolution, held
    for the font list as well.

    `check_ink` and `check_text_readability` are public and documented as
    callable directly, and each builds its own canvas when it is not handed one.
    Pinning the rcParams in `audit` alone put the two routes on two different
    faces the moment a builder had reported on the figure, which every gallery
    builder does. Measured on `gallery-density` under matplotlib 3.8.4, ax0's
    ink fraction came back 0.07 through `audit` and 0.08 called straight.

    Asserted on the font list live at the draw, not on the number that comes
    out of it. Comparing the two routes' details is what CI already does, and
    three of its four pytest legs passed the broken version: the two faces move
    a fraction by about 0.01, so whether the defect is visible depends on which
    side of a rounding boundary the figure happens to sit. The mechanism does
    not depend on that.
    """
    fig = build(modules, "demo")
    seen = []
    real = cf._renderer
    monkeypatch.setattr(
        cf, "_renderer",
        lambda f: (seen.append(matplotlib.rcParams["font.serif"][0]), real(f))[1])
    try:
        # A font list neither route was drawn under, so reading the caller's
        # rcParams and reading the record give different answers.
        with plt.rc_context({"font.serif": ["DejaVu Serif"]}):
            if gate == "check_ink":
                cf.check_ink(fig)
            else:
                cf.check_text_readability(fig, None)
    finally:
        plt.close(fig)

    assert seen, f"{gate} never reached _renderer, so this asserts nothing"
    assert set(seen) == {"STIX Two Text"}, (
        f"{gate} called on its own drew under {sorted(set(seen))} rather than "
        "the sheet's font list, which is what the figure was drawn under and "
        "what `audit` measures it under")


def test_the_record_does_not_alias_the_live_rcparams(modules):
    """The family lists are mutable and `rcParams` hands out the object itself,
    so a record that aliased them would be rewritten by anyone who edited a font
    list in place -- and the figure would then be measured under a font list it
    was never drawn in."""
    fig = build(modules, "demo")
    try:
        recorded = list(getattr(fig, cf.DRAW_RC_ATTR)["font.serif"])
        plt.rcParams["font.serif"].insert(0, "Nonexistent Face")
        try:
            assert getattr(fig, cf.DRAW_RC_ATTR)["font.serif"] == recorded, (
                "editing the live font list in place rewrote the record of "
                "what the figure was drawn under")
        finally:
            plt.rcParams["font.serif"].remove("Nonexistent Face")
    finally:
        plt.close(fig)
