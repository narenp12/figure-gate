"""The composition gates, run over material this project did not author.

Every other measurement of these gates is against the eleven figures in
`examples/gallery.py`, which the same person wrote to pass them. That is
circular and has been the standing criticism of this project's evidence: the
colour gates now answer to an independent implementation (`colorspacious`, in
`test_colour_space_oracle.py`) and to a published palette, and the composition
gates answered to nobody.

There is no importable corpus of published figures, because journals ship PDFs
and not `Figure` objects, so this is the nearest external material there is: the
twenty-eight style sheets matplotlib itself ships. Seaborn's authors wrote
fourteen of them, Tableau one, Petroff two, and the rest come from ggplot,
FiveThirtyEight, Solarized, Bayesian Methods for Hackers and matplotlib's own
pre-2.0 defaults. Three neutral figures are built under each, so the content is
held constant and the styling (colour cycle, type sizes, stroke widths, grid,
spines, background) is the only thing that varies.

What makes it a test rather than a survey is that four of the styles carry a
ground-truth label from their own authors: `tableau-colorblind10`,
`seaborn-v0_8-colorblind`, `petroff6` and `petroff10` are all published as
accessible under colour vision deficiency (Petroff 2021, *Accessible Color
Sequences for Data Visualization*, arXiv:2107.02270). A colour gate that
rejected any of them would be rejecting the thing it claims to enforce. None is
rejected, and twenty-one of the twenty-four unlabelled styles are.

The negative result is here too, and it is the sharp one: `Style sheet` and
`Fonts` fire on 28 styles out of 28. Neither is measuring the figure. The first
asks whether this project's sheet is in effect, which is a tautology on anyone
else's, and the second asks for Type 42 embedding, which no stock style sets.
Both are advisory, both are pinned below by name, and neither should ever be
quoted as evidence that these gates discriminate.
"""

import functools

import matplotlib.pyplot as plt
import numpy as np
import pytest

from conftest import STYLE_SHEET                              # noqa: E402

import check_figure as cf                                     # noqa: E402

# Styles published by their authors as accessible under colour vision
# deficiency. This is the corpus's ground truth and the only label in it that
# does not come from this project. Filtered against what is installed, because
# the Petroff cycles arrived in matplotlib 3.10 and CI's oldest leg is 3.8.4.
CVD_SAFE = ("tableau-colorblind10", "seaborn-v0_8-colorblind",
            "petroff6", "petroff10")

# Rows that fire on every external style because of what they ask, not because
# of what the style did. Kept as a named set so the sweep's headline number
# cannot quietly come to rest on them.
TAUTOLOGICAL = frozenset({"Style sheet", "Fonts"})

DESCRIPTION = (
    "Three series plotted against a shared horizontal scale, drawn to compare "
    "their level and spread across the range shown. The figure exists to carry "
    "an external style sheet, not a finding.")


def line_panel():
    x = np.linspace(0, 10, 200)
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    for k in range(4):
        ax.plot(x, np.sin(x + k), label=f"series {k}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal (mV)")
    # Above the axes rather than inside them. `loc="best"` put an entry on a
    # curve and the readability gate caught it, correctly. But a defect in the
    # builder fires under every style and would be read as a property of all
    # twenty-eight.
    ax.legend(ncols=4, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              frameon=False)
    return fig


def scatter_panel():
    rng = np.random.default_rng(3)
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    x = np.linspace(0, 10, 25)
    for k in range(3):
        ax.scatter(x, 0.8 * x + 3 * k + rng.normal(0, 0.4, 25), label=f"g{k}")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Observed")
    # Twenty-five marks along a line, not a Gaussian blob. Any cluster dense
    # enough to look like real data overplots under every style including this
    # project's own, so the blob measured the data and not the sheet.
    ax.legend(ncols=3, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              frameon=False)
    return fig


def bar_panel():
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    ax.bar(range(6), [3, 5, 2, 7, 4, 6])
    ax.set_xlabel("Condition")
    ax.set_ylabel("Count")
    return fig


BUILDERS = (line_panel, scatter_panel, bar_panel)


def external_styles():
    return tuple(sorted(plt.style.available))


def audit_under(sheet):
    """Every non-passing row from the three builders under one sheet.

    Returns `{gate name: status}`, worst status per gate. The builder is run
    inside the style context and so is the audit, because `check_style_sheet`
    reads the rcParams that are live at the moment it runs rather than the ones
    the figure was built under.
    """
    worst = {}
    for build in BUILDERS:
        with plt.style.context(sheet):
            fig = build()
            cf.describe(fig, DESCRIPTION)
            try:
                rows = cf.audit(fig)[1]
            finally:
                plt.close(fig)
        for label, status, _ in rows:
            if status is not True and worst.get(label) is not False:
                worst[label] = status
    return worst


@functools.cache
def sweep():
    """`{style: {gate: status}}` over every installed style. Cached because it
    is six seconds of rendering and five tests read it."""
    return {style: audit_under(style) for style in external_styles()}


def fired(gate, hard_only=False):
    return {style for style, rows in sweep().items()
            if rows.get(gate, True) is not True
            and (not hard_only or rows[gate] is False)}


def test_the_sweep_reads_a_corpus_and_not_an_empty_list():
    """Every assertion below is a rate over `plt.style.available`. A sweep that
    came back with two styles in it would satisfy most of them and measure
    nothing, which is the failure mode a corpus test has instead of an error."""
    styles = external_styles()
    assert len(styles) >= 20, (
        f"matplotlib is shipping {len(styles)} styles: {styles}. The numbers "
        "below were measured over 28 and are rates, not counts, but a corpus "
        "this small is no longer external evidence of anything")
    assert set(CVD_SAFE) & set(styles), (
        f"none of {CVD_SAFE} is installed, so the corpus has lost its ground "
        "truth and every remaining assertion is about the unlabelled class")


@pytest.mark.parametrize("build", BUILDERS, ids=lambda b: b.__name__)
def test_the_reference_sheet_passes_every_builder(build):
    """The control. These three figures have to be clean under this project's
    own sheet, or a fire anywhere in the sweep is a defect in the builder rather
    than a property of the style that was substituted into it. Both of the
    builders' comments are the two times that happened while this file was
    written."""
    with plt.style.context(str(STYLE_SHEET)):
        fig = build()
        cf.describe(fig, DESCRIPTION)
        try:
            ok, rows = cf.audit(fig)
        finally:
            plt.close(fig)
    assert ok, [r for r in rows if r[1] is not True]


def test_no_palette_published_as_colourblind_safe_is_rejected():
    """The corpus's one labelled class, and the assertion this file exists for.

    Four style sheets are published by their authors as accessible under colour
    vision deficiency. This project's colour gate has never been checked against
    anything except a palette the same project chose; if it rejected Tableau's
    or Petroff's, the floors would be measuring this project's taste rather than
    discriminability, and there would be no way to tell from inside the repo.
    """
    labelled = [s for s in CVD_SAFE if s in external_styles()]
    rejected = {s: sweep()[s]["Series color"] for s in labelled
                if sweep()[s].get("Series color", True) is not True}
    assert not rejected, (
        f"{rejected} are published as colourblind-safe by their own authors "
        f"and the Series color gate rejects them. CVD_TARGET is derived from "
        f"Stone, Szafir & Setlur rather than from any palette, so a clash here "
        f"is evidence about the floor and not about the palette")


def test_the_colour_gate_rejects_most_of_the_unlabelled_class():
    """The other half of a classifier. Accepting the four labelled palettes is
    only evidence if the gate is not accepting everything, and the twenty-four
    remaining styles are stock screen palettes with no accessibility claim
    attached to any of them."""
    styles = external_styles()
    unlabelled = [s for s in styles if s not in CVD_SAFE]
    rejected = fired("Series color", hard_only=True) - set(CVD_SAFE)
    rate = len(rejected) / len(unlabelled)
    assert rate > 0.75, (
        f"the colour gate rejects {len(rejected)} of {len(unlabelled)} "
        f"unlabelled styles ({rate:.2f}). It was 21 of 24 when this was "
        f"written. A gate that passes stock matplotlib palettes is passing the "
        f"figures this project exists to catch")
    passed = sorted(set(unlabelled) - rejected)
    assert len(passed) <= 6, (
        f"{passed} clear the colour gate without claiming to. Some always did "
        "-- fivethirtyeight, seaborn-v0_8-muted and seaborn-v0_8-bright were "
        "the three -- but a growing list means the floor has slipped")


def test_two_gates_fire_on_every_external_style_and_measure_nothing():
    """The negative result, pinned so it cannot be quoted as a success.

    `Style sheet` asks whether this project's sheet is the one in effect. On
    anyone else's sheet the answer is no, always, and the row carries no
    information about the figure. `Fonts` asks for Type 42 embedding, which no
    stock style sets. Both are advisory and both are correct to exist; neither
    belongs in a count of how well these gates discriminate.

    Asserted as an equality, not a floor: if either of these ever stops firing
    on all 28, it has started depending on something and the sentence above is
    wrong.
    """
    styles = set(external_styles())
    for gate in sorted(TAUTOLOGICAL):
        assert fired(gate) == styles, (
            f"{gate} fires on {len(fired(gate))} of {len(styles)} external "
            f"styles rather than all of them. It was written up as carrying no "
            f"information about the figure, and that is no longer true")
        assert not fired(gate, hard_only=True), (
            f"{gate} now hard-fails an external style. A row that fires on "
            "every sheet that is not this project's cannot be one that gates a "
            "build")


def test_the_gates_that_fire_selectively_fire_for_a_stated_reason():
    """Each remaining fire, attributed.

    A corpus result is only evidence if the fires can be explained; a gate that
    catches four styles for no reason anybody can name is a gate that will catch
    a reader's figure for no reason either. These are the three, with what in
    the style causes them. Named styles are asserted as subsets, because the
    sweep runs on two matplotlib versions in CI and the exact membership of the
    unnamed remainder is a property of the version.
    """
    # Default type large enough that a 5x3in panel's decorations run off it.
    clipped = fired("Clipping", hard_only=True)
    assert {"seaborn-v0_8-poster", "seaborn-v0_8-talk"} <= clipped, (
        f"the presentation styles no longer clip a 5x3in figure: {clipped}. "
        "They set 14-18pt defaults, and that is the case the gate exists for")

    # Solarized is a deliberately low-contrast scheme: tinted ground, tinted
    # text. Text on it is the one WCAG failure in the corpus, and finding it is
    # the strongest single thing this sweep does.
    assert "Solarize_Light2" in fired("Text readability", hard_only=True), (
        "Solarize_Light2 no longer fails the text contrast gate. Its own "
        "palette puts #586e75 text on #eee8d5 ground, and if that reads as "
        "clean the gate has stopped measuring contrast")

    # Dark grounds and heavy grids, counted as ink over the whole rectangle.
    inked = fired("Ink coverage")
    assert {"seaborn-v0_8-dark", "seaborn-v0_8-darkgrid"} <= inked, (
        f"the dark-ground styles no longer warn on ink coverage: {inked}")
    assert not fired("Ink coverage", hard_only=True), (
        "Ink coverage is advisory and just hard-failed an external style")
