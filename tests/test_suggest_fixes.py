"""Every suggestion that ships a snippet is executed against a figure that
fails its gate, and the gate has to pass afterwards.

This is the only test shape that can catch a suggestion which does not work.
Reading the message tells you a fix was named; running it tells you the fix
was real. `check_overplotting` advised adding transparency for as long as
nobody ran it, against a gate that measures nearest-neighbour distance in
pixels and never reads alpha.
"""

import matplotlib.pyplot as plt
import numpy as np
import pytest

import check_figure as cf
import suggest_fixes as sf


# A figure that fails the named gate, one per remedy that ships code. Kept here
# rather than beside the remedy because a broken figure is test scaffolding,
# while the remedy is the thing being shipped.
def _broken_clipping():
    # Rotated tick labels taller than the default bottom margin: the case
    # constrained layout exists for. A label physically longer than the figure
    # would be a fixture no layout engine can rescue, which would report the
    # snippet as broken when the figure is.
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot(range(5), range(5))
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"category number {i}" for i in range(5)], rotation=90)
    return fig


def _broken_axis_redundancy():
    fig, axes = plt.subplots(1, 2, figsize=(6, 2))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_ylabel("shared quantity")
    return fig


def _broken_contour_dash():
    fig, ax = plt.subplots()
    x = np.linspace(-3, 3, 40)
    X, Y = np.meshgrid(x, x)
    ax.contour(X, Y, np.sin(X) * np.cos(Y), colors="black")
    return fig


def _broken_fonts():
    plt.rcParams["pdf.fonttype"] = 3
    plt.rcParams["ps.fonttype"] = 3
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    return fig


def _broken_alt_text():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    return fig


def _broken_contrast_stack():
    fig, ax = plt.subplots()
    for alpha in (0.3, 0.4):
        ax.plot([0, 1], [0, 1], alpha=alpha)
    return fig


def _broken_mark_ratio():
    fig, ax = plt.subplots()
    ax.scatter([0, 1, 2], [0, 1, 2], s=[10, 10, 900])
    return fig


def _broken_colormap():
    fig, ax = plt.subplots()
    ax.imshow(np.random.default_rng(0).random((8, 8)), cmap="jet")
    return fig


BROKEN = {
    "Clipping": _broken_clipping,
    "Axis redundancy": _broken_axis_redundancy,
    "Contour dash": _broken_contour_dash,
    "Fonts": _broken_fonts,
    "Alt text": _broken_alt_text,
    "Contrast stack": _broken_contrast_stack,
    "Mark ratio": _broken_mark_ratio,
    "Colormap kind": _broken_colormap,
}

GATE_BY_NAME = {g.name: g for g in cf.GATES}

WITH_CODE = [r for r in sf.REMEDIES if r.code]


def _run_gate(gate, fig):
    """A gate, given whatever `audit` would have given it."""
    r, canvas = cf._renderer(fig)
    available = {"r": r, "canvas": canvas, "scale": None, "placed_frac": 1.0,
                 "venue": None, "context_axes": None}
    return gate.func(fig, **{n: available[n] for n in gate.needs})


@pytest.mark.parametrize("remedy", WITH_CODE,
                         ids=lambda r: f"{r.gate}: {r.suggestion[:32]}")
def test_a_suggestion_with_code_actually_fixes_its_gate(remedy):
    """Build the defect, run the shipped snippet, and require the verdict to
    move. A snippet that leaves the gate where it was is a wrong suggestion,
    however well it reads."""
    gate = GATE_BY_NAME[remedy.gate]
    fig = BROKEN[remedy.gate]()
    try:
        before, detail = _run_gate(gate, fig)
        assert before is not True, (
            f"the fixture for {remedy.gate} does not fail it, so this test "
            f"would pass without the snippet doing anything: {detail}")

        exec(remedy.code, {"fig": fig, "plt": plt, "check_figure": cf})

        after, detail = _run_gate(gate, fig)
        assert after is True, (
            f"{remedy.gate} still reports {after!r} after running the snippet "
            f"this file offers as the fix: {detail}")
    finally:
        plt.close(fig)


def test_every_remedy_names_a_gate_that_exists():
    """A remedy for a renamed or deleted gate is unreachable, and `suggest`
    would drop it silently rather than raise."""
    unknown = sorted({r.gate for r in sf.REMEDIES} - set(GATE_BY_NAME))
    assert not unknown, f"REMEDIES names gates that are not in GATES: {unknown}"


def test_every_code_backed_remedy_has_a_fixture():
    """The round-trip is the point. A snippet with no figure to run against is
    an untested claim wearing the same shape as a tested one."""
    missing = sorted({r.gate for r in WITH_CODE} - set(BROKEN))
    assert not missing, (
        f"these remedies ship code with no broken figure to prove it on: "
        f"{missing}")


def test_suggest_offers_nothing_for_a_clean_run():
    rows = [(g.name, True, "fine") for g in cf.GATES]
    assert sf.suggest(rows) == []


def test_suggest_covers_a_gate_that_warns_not_only_one_that_fails():
    """Advisory rows are where most of the remedies are: Overplotting, Alt
    text, Contour dash and Fonts never fail a build, and are exactly the rows
    a reader is most likely to want an answer for."""
    rows = [(g.name, "warn" if g.name == "Alt text" else True, "d")
            for g in cf.GATES]
    assert [name for name, _ in sf.suggest(rows)] == ["Alt text"]


def test_a_gate_with_no_remedy_is_skipped_rather_than_padded():
    """`check_collisions` has no remedy anywhere in this project, because
    which of two colliding labels is free to move is not something either
    file can see. It should produce nothing, not a restatement."""
    rows = [(g.name, g.name != "Text collision", "d") for g in cf.GATES]
    assert sf.suggest(rows) == []


def test_the_overplotting_remedy_does_not_advise_transparency():
    """The suggestion this whole file exists to have caught. `check_overplotting`
    reads offsets and sizes; alpha is not among them, so transparency cannot
    move the row and must not be offered as though it could."""
    text = " ".join(r.suggestion.lower() for r in sf.REMEDIES
                    if r.gate == "Overplotting")
    assert "transparen" in text, (
        "the remedy no longer mentions transparency at all; it should still "
        "say why transparency is not the answer, or this row goes back to "
        "being advice people retry")
    assert "do not help" in text or "does not help" in text


def test_transparency_really_does_not_move_the_overplotting_gate():
    """The measurement behind the remedy above, asserted rather than trusted."""
    rng = np.random.default_rng(0)
    xy = rng.normal(size=(4000, 2))
    figs = []
    try:
        for kwargs in ({}, {"alpha": 0.15}, {"facecolors": "none"}):
            fig, ax = plt.subplots()
            figs.append(fig)
            ax.scatter(xy[:, 0], xy[:, 1], s=400, **kwargs)
            status, _ = cf.check_overplotting(fig)
            assert status == "warn", (
                f"scatter with {kwargs or 'no adjustment'} no longer "
                "overplots, so this test proves nothing")

        fig, ax = plt.subplots()
        figs.append(fig)
        ax.hexbin(xy[:, 0], xy[:, 1], gridsize=30)
        assert cf.check_overplotting(fig)[0] is True, (
            "binning is what the remedy offers instead, and it no longer works")
    finally:
        for fig in figs:
            plt.close(fig)
