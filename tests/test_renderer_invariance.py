"""A verdict is a property of the figure, not of the resolution it was drawn at.

Half of `check_figure`'s thresholds are pixel counts: `TEXT_EDGE_WINDOW`,
`TEXT_FOOTPRINT_MIN_PX`, `INK_DELTA_MIN`, and the fractions built on top of them.
A pixel count is a measurement only when the resolution is fixed, and until
`MEASURE_DPI` existed it was not: the gates drew at `fig.dpi`, which is whatever
the author set, whatever sheet is in effect, or the authored value times the
device pixel ratio of a display that happened to be attached.

`test_figure.py` already held one instance of this: a Retina canvas must not
move a verdict. That test was written as a HiDPI test. It was really a
resolution test, and this file is the general form of it: the same eleven
figures the composition gates are calibrated against, audited across a range of
authored dpi wider than anyone would use, with every row required to come back
identical down to the message.

The sweep is not hypothetical. Before `MEASURE_DPI`, across 100/150/200/300/600:
thirty-four rows moved and one flipped. `orbit`'s ink fraction ran 0.13 at 100
dpi to 0.04 at 300 and out the bottom of the band at 600, because a mark's
antialiased fringe is a fixed number of pixels wide and therefore a shrinking
share of a mark that grows with the resolution. `test_the_sweep_can_fail` puts
that behaviour back and checks the sweep still sees it.

Resolution is one axis of renderer dependence and this file closes it. The other
is the rasteriser itself: Agg and FreeType decide what a stroke covers and how a
glyph is hinted, and `matplotlib>=3.8` spans several years of both. Nothing here
can hold that still. What can be done is to make sure the range this project
claims is a range it runs on, so the last test asserts that the floor in
`pyproject.toml` is an actual leg of CI's matrix -- which is what makes the
whole suite, this sweep included, a measurement taken at both ends of the
declared support rather than at whichever version the author has installed.
"""

import contextlib
import importlib
import io
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

import check_figure as cf

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# Wider than the useful range on both sides on purpose. 100 is matplotlib's
# default, 150 is the sheet's and `MEASURE_DPI`, 300 is what `savefig.dpi`
# writes, and 72 and 600 are there because a constant that holds only over the
# values somebody expected is not a constant.
DPIS = (72, 100, 150, 300, 600)

# The eleven the composition gates are calibrated against, by name. Read off the
# module rather than listed twice, so a twelfth figure joins this sweep by being
# added to the gallery.
BUILDER_NAMES = ("small_multiples", "field", "schematic", "forms",
                 "convergence", "orbit", "encoding", "uncertainty", "counts",
                 "residual", "density")


@pytest.fixture(scope="module")
def gallery():
    """The gallery module, imported with its writer switched off.

    `OUT = None` is the mode the gallery documents for exactly this: build and
    audit the corpus, write nothing. Running the script instead would rewrite
    the committed PNGs, which is the accident `test_example.py` exists to
    prevent.
    """
    sys.path.insert(0, str(EXAMPLES))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            module = importlib.import_module("gallery")
    finally:
        sys.path.remove(str(EXAMPLES))
    module.OUT = None
    return module


def build(gallery, name, dpi):
    """One gallery figure, authored at `dpi`.

    The dpi is set after the build rather than through `rcParams`, because the
    gallery builds under the skill's sheet and `check_style_sheet`'s whole job
    is noticing when the rcParams in effect are not the sheet's. Overriding
    `figure.dpi` in the context would fail that gate on every leg of the sweep
    and the sweep would be measuring the override.

    `_original_dpi` is set alongside it because that is the attribute
    `check_figure` restores to, and a figure whose two disagree is the HiDPI
    case rather than the authored one.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        fig = getattr(gallery, name)()
    fig.set_dpi(dpi)
    fig._original_dpi = dpi
    return fig


def rows_at(gallery, name, dpi):
    fig = build(gallery, name, dpi)
    try:
        return cf.audit(fig)[1]
    finally:
        plt.close(fig)


@pytest.mark.parametrize("name", BUILDER_NAMES)
def test_no_row_moves_with_the_authored_dpi(gallery, name):
    """Every row, every message, identical across the range.

    Statuses alone would be too weak. The status is a thresholded number and
    most of this corpus sits nowhere near a threshold, so a gate could drift by
    a factor of three and still report PASS on all eleven, which is roughly
    what was happening. The detail strings carry the measurements, so comparing
    them is comparing the numbers.
    """
    baseline = rows_at(gallery, name, cf.MEASURE_DPI)
    for dpi in DPIS:
        got = rows_at(gallery, name, dpi)
        moved = [(b[0], b[1], b[2], g[1], g[2])
                 for b, g in zip(baseline, got) if b != g]
        assert not moved, (
            f"{name} audited at {dpi} dpi disagrees with the same figure at "
            f"{cf.MEASURE_DPI}: {moved}. A verdict is a property of the "
            f"figure; dpi is a knob the author turned for a reason that has "
            f"nothing to do with whether the figure reads.")


def test_the_sweep_can_fail(gallery, monkeypatch):
    """The behaviour `MEASURE_DPI` replaced, put back, and caught.

    Pointing `MEASURE_DPI` at the figure's own dpi is exactly what the gates did
    before it existed (draw at whatever the author set), so this reproduces the
    old code path through the new one, rather than asserting against a copy of
    it that could rot.

    `orbit` because it is the figure the drift was largest on and the only one
    whose verdict flipped: a dense attractor is thousands of marks a pixel or
    two across, which is the regime where the antialiased fringe is most of the
    mark.
    """
    fractions = {}
    for dpi in (100, 300):
        monkeypatch.setattr(cf, "MEASURE_DPI", float(dpi))
        rows = dict((label, detail) for label, _, detail in
                    rows_at(gallery, "orbit", dpi))
        fractions[dpi] = rows["Ink coverage"]

    assert fractions[100] != fractions[300], (
        "measuring at the authored dpi no longer moves `orbit`'s ink fraction, "
        "so either the gate stopped counting pixels or this sweep stopped "
        "reaching it. Either way it is no longer evidence that MEASURE_DPI "
        f"does anything: {fractions[100]!r}")


def test_the_figure_comes_back_on_the_dpi_it_arrived_on(gallery):
    """`audit` borrows the figure; it does not get to keep it.

    Measuring means moving the figure to `MEASURE_DPI`, and a caller who audits
    and then saves would get a file at a resolution this file chose. Checked at
    a dpi on either side of `MEASURE_DPI` so a restore that happens to be a
    no-op at one of them is not mistaken for a restore.
    """
    for dpi in (100, 300):
        fig = build(gallery, "convergence", dpi)
        try:
            cf.audit(fig)
            assert fig.dpi == dpi, (
                f"a figure authored at {dpi} dpi came back on {fig.dpi}")
        finally:
            plt.close(fig)


def test_the_figure_comes_back_even_when_a_gate_raises(gallery, monkeypatch):
    """The restore is a `finally`, and the reason it has to be is that `audit`
    catches gate exceptions one at a time and keeps going. A gate that raises is
    a supported outcome, with its own row and its own verdict, so it must not
    be the case that leaves the caller's figure on the wrong dpi."""
    def boom(*args, **kwargs):
        raise RuntimeError("deliberate")

    monkeypatch.setattr(cf, "check_ink", boom)
    monkeypatch.setattr(cf, "GATES",
                        [gate._replace(func=boom) for gate in cf.GATES])

    fig = build(gallery, "convergence", 300)
    try:
        ok, rows = cf.audit(fig)
        assert not ok and rows, "the raising gates reported nothing"
        assert fig.dpi == 300, f"the figure came back on {fig.dpi}"
    finally:
        plt.close(fig)


def test_a_gate_called_on_its_own_measures_what_audit_measures(gallery):
    """`check_ink` and `check_text_readability` are public and documented as
    callable directly. Each builds its own canvas when it is not handed one, and
    each of those was a second place the resolution could come from, so a
    reader who called the gate straight got one number and the same gate through
    `audit` got another. Same figure, both routes, same string.
    """
    fig = build(gallery, "density", 300)
    try:
        standalone = cf.check_ink(fig, context_axes=None)
        through_audit = dict((label, (status, detail))
                             for label, status, detail in cf.audit(fig)[1])
    finally:
        plt.close(fig)
    assert standalone == through_audit["Ink coverage"], (
        "check_ink reports one thing on its own and another through audit, so "
        "one of the two is not at MEASURE_DPI")


def test_a_hidpi_canvas_is_still_the_case_it_always_was(gallery):
    """`_authored_dpi` reads `_original_dpi`, and a HiDPI backend is the one
    situation where that disagrees with `fig.dpi`. The figure has to come back
    on the authored value, not on the display's. That correction predates
    `MEASURE_DPI` and is the half of this problem that had already been found.
    """
    fig = build(gallery, "convergence", 150)
    fig.canvas._device_pixel_ratio = 2
    fig.dpi = 2 * fig._original_dpi
    try:
        cf.audit(fig)
        assert fig.dpi == 150, (
            f"a Retina figure came back on {fig.dpi} rather than on the 150 it "
            "was authored at")
    finally:
        plt.close(fig)


ROOT = Path(__file__).resolve().parent.parent


def test_the_declared_matplotlib_floor_is_a_leg_of_the_matrix():
    """`matplotlib>=3.8` is a promise, and until now nothing checked that the
    version named in it is one the suite is ever run against.

    It happens to be true (`ci.yml` pins a 3.8.4 leg), and that is exactly the
    kind of true that stops being true when somebody raises the floor and
    forgets the workflow, or bumps the leg and forgets the floor. Either way the
    project would be claiming support for a version no test had touched in
    months, which is the version-axis form of the bug this whole file is about.

    Parsed with regexes rather than a TOML and a YAML library, for the reason
    `test_workflow_timeouts.py` gives: the CI job that most needs these
    assertions installs matplotlib, pytest and xdist and nothing else.
    """
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(r'"matplotlib>=(\d+\.\d+)"', pyproject)
    assert floor, "pyproject.toml no longer declares a matplotlib floor"

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pinned = re.findall(r'matplotlib: "(\d+\.\d+(?:\.\d+)?)"', ci)
    assert pinned, (
        "ci.yml pins no matplotlib version at all, so every leg resolves to "
        "whatever is newest and the declared floor is never exercised")
    assert any(version.startswith(floor.group(1) + ".")
               or version == floor.group(1) for version in pinned), (
        f"pyproject declares matplotlib>={floor.group(1)} and ci.yml pins "
        f"{pinned}. Nothing runs this suite on the oldest version the package "
        f"says it supports, so the support claim is untested")
    assert "latest" in re.findall(r'matplotlib: "([^"]+)"', ci), (
        "no leg of the matrix tracks the newest matplotlib. The floor being "
        "tested is half of a range; the other half is where a rasteriser "
        "change would surface first")
