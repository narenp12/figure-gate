"""Gates for check_figure.py.

The point of this file is the same as the point of the checker: a gate nobody
has watched fail is decoration. Each test below builds a figure with exactly one
defect and asserts that the matching gate is the one that catches it. Asserting
only "audit returned False" would pass even if every check had silently broken
except one, which is close to what happened twice while the checker was written.
"""

import re
import shutil

import matplotlib
import matplotlib.pyplot as plt
import pytest

import check_figure as cf


@pytest.fixture
def clean():
    """A figure with nothing wrong with it, built without the style sheet so
    these tests measure the checker rather than the defaults."""
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot([0, 1, 2], [0, 1, 0], lw=1.6)
    ax.set_xlabel("Time")
    ax.set_ylabel("Signal")
    yield fig
    plt.close(fig)


def gates(rows):
    return {name: status for name, status, _ in rows}


def test_a_clean_figure_passes_every_check(clean):
    ok, rows = cf.audit(clean)
    assert ok, [r for r in rows if r[1] is not True]


def test_clipping_catches_text_off_canvas():
    fig, ax = plt.subplots(figsize=(2, 2))       # no layout manager on purpose
    ax.set_xlabel("an axis label far too long to fit inside two inches")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Clipping"] is False


def hidpi(fig):
    """Make `fig` look like it was built under a HiDPI GUI backend.

    A Retina macosx canvas, or Qt on a scaled desktop, sets `fig.dpi` to the
    authored dpi times the display's device pixel ratio at creation time and
    reports `get_width_height()` back in logical pixels. Those two lines are the
    whole of it, so the condition reproduces here without a display — which
    matters, because conftest pins Agg and so does every gallery script, and
    that is exactly why this class of bug survived a green suite.
    """
    fig.canvas._device_pixel_ratio = 2
    fig.dpi = 2 * fig._original_dpi
    return fig


def test_a_clean_figure_passes_on_a_hidpi_canvas(clean):
    """The regression: text extents come back in physical pixels, the canvas
    reports its width in logical ones, and the clipping check called every
    label past the midpoint clipped. A figure's verdict is a property of the
    figure, not of the display the checker happened to run on."""
    ok, rows = cf.audit(hidpi(clean))
    assert ok, [r for r in rows if r[1] is not True]


def test_hidpi_does_not_move_any_verdict():
    """Clipping was the loud half. The quiet half is that every threshold
    calibrated in pixels — the edge window, the footprint floor — covers half
    the distance it was calibrated for once dpi has been doubled underneath it.
    Same figure, both canvases, every row identical including the messages."""
    def build():
        fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
        ax.plot([0, 1, 2, 3], [0, 1, 0.5, 2], lw=1.6)
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")
        return fig

    normal = build()
    _, normal_rows = cf.audit(normal)
    plt.close(normal)

    retina = hidpi(build())
    _, retina_rows = cf.audit(retina)
    plt.close(retina)

    assert retina_rows == normal_rows


def test_hidpi_figure_is_measured_at_its_authored_dpi():
    """The dpi the figure was authored at is the one the caller gets back.

    Measuring now happens at `MEASURE_DPI` rather than at the authored value
    (see `test_renderer_invariance.py` for why, and for the general form of this
    test), but the figure is borrowed, not kept. Leaving the doubled value in
    place would hand back a figure whose next `savefig` writes at twice the
    resolution its author asked for.
    """
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    authored = fig.dpi
    cf.audit(hidpi(fig))
    assert fig.dpi == authored
    plt.close(fig)


def test_collision_catches_two_labels_in_the_same_place():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.text(0.5, 0.5, "first label", ha="center")
    ax.text(0.5, 0.5, "second label", ha="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text collision"] is False


def test_contrast_stack_catches_a_figure_with_nothing_opaque():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], alpha=0.4)
    ax.plot([0, 1], [1, 0], alpha=0.5)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contrast stack"] is False


def test_contrast_stack_catches_too_many_alpha_levels():
    """Haze, rather than hierarchy. This one is worth separating from the
    nothing-opaque case because the fix is different: fewer levels, not a
    solid mark."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])                       # opaque, so the other half passes
    for a in (0.2, 0.35, 0.5, 0.65, 0.8):
        ax.plot([0, 1], [a, a], alpha=a)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contrast stack"] is False


def test_contrast_stack_survives_a_per_point_alpha_array():
    """matplotlib has taken array alpha since 3.4. float() raises on one, and
    _rows turns a raising non-advisory gate into False, so a legal figure was
    hard-failed by a defect in the checker."""
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.scatter([0, 1], [0, 1], s=40, alpha=[0.5, 1.0])
    status, detail = cf.check_contrast_stack(fig)
    assert status is True, detail
    assert "raised" not in detail
    plt.close(fig)


def test_an_alpha_ramp_is_one_level_not_sixteen():
    """A continuous alpha ramp across one artist is one decision the reader
    resolves, not sixteen. Counting each value made an ordinary pcolormesh
    report '16 levels reads as haze'."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.pcolormesh(np.arange(16).reshape(4, 4),
                  alpha=np.linspace(0.2, 1.0, 16).reshape(4, 4))
    status, detail = cf.check_contrast_stack(fig)
    assert status is True, detail
    plt.close(fig)


def test_an_array_alpha_with_nothing_opaque_still_fails():
    """The over-fire fix must not blind the row to the defect it exists for."""
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.scatter([0, 1, 2], [0, 1, 2], s=40, alpha=[0.2, 0.4, 0.6])
    status, detail = cf.check_contrast_stack(fig)
    assert status is False
    assert "nothing is opaque" in detail
    plt.close(fig)


def test_mark_ratio_catches_an_ornamental_star():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.scatter([1, 2, 3], [1, 2, 3], s=12)
    ax.scatter([2], [2], marker="*", s=400)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Mark ratio"] is False


def test_mark_ratio_sees_line_markers_not_only_scatter():
    """`ax.plot(marker=...)` is a mark like any other. Reading only
    `collections` meant a 3pt marker beside a 30pt one passed clean."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([1, 2, 3], [1, 2, 3], marker="o", markersize=3)
    ax.plot([1, 2, 3], [3, 2, 1], marker="s", markersize=30)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Mark ratio"] is False


def test_scatter_size_is_a_squared_diameter_not_an_area():
    """The premise `scatter_diameter_pt` rests on, pinned against matplotlib
    rather than against its own docstring.

    matplotlib documents `s` as "the marker size in points**2", and every
    conversion in this module would be wrong by 4/pi if that were an area. It
    is not: `scatter(s=d**2)` and `plot(markersize=d)` draw the same disc. This
    asserts it in ink, so a matplotlib release that changed the scaling would
    land here rather than silently re-skewing two gates.
    """
    import numpy as np

    def ink(draw):
        fig, ax = plt.subplots(figsize=(3, 3), dpi=200)
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        draw(ax)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[..., :3]
        plt.close(fig)
        return int((buf.sum(axis=2) < 400).sum())

    scatter = ink(lambda ax: ax.scatter([0.5], [0.5], s=100.0, color="k"))
    line = ink(lambda ax: ax.plot([0.5], [0.5], marker="o", markersize=10.0,
                                  color="k")[0])
    assert scatter == line, (
        f"scatter(s=100) drew {scatter}px and plot(markersize=10) drew "
        f"{line}px; scatter_diameter_pt assumes markersize == sqrt(s)")
    assert cf.scatter_diameter_pt(100.0) == 10.0


def test_mark_ratio_measures_both_mark_kinds_in_the_same_unit():
    """`plot(markersize=...)` is a diameter in points and `scatter(s=...)` is
    that diameter squared, despite matplotlib calling `s` an area. Feeding `s`
    straight in as an area leaves the operands 4/pi = 1.27x apart — invisible
    on a figure drawing one kind, because the bias cancels in the ratio, and a
    standing 27% error on any figure mixing the two.

    Two assertions, because one alone is satisfiable by a broken conversion.
    Marks of identical drawn area must report 1.0x, which the old code failed
    at 1.3x on two marks measurably 741 pixels each. And the second figure is
    sized so the two formulas straddle the threshold: truly 4.5x apart in drawn
    area, which is legal, and 5.73x apart if `s` is read as an area, which is
    not. It asserts the verdict rather than a substring of the message, so it
    does not have to be rewritten the next time anyone changes how the row is
    phrased.
    """
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.scatter([1, 2], [1, 2], s=100.0)
    ax.plot([1, 2], [2, 1], marker="o", markersize=10.0, linestyle="none")
    ok, rows = cf.audit(fig)
    detail = {r[0]: r[2] for r in rows}["Mark ratio"]
    plt.close(fig)
    assert "1.0x" in detail, (
        f"scatter(s=100) and plot(markersize=10) draw the same disc, so the "
        f"ratio is 1.0x; got {detail!r}")

    # markersize 10 draws a disc of area pi * 25; s = 450 draws pi * 450 / 4,
    # which is 4.5x it. Reading `s` as an area makes the same pair 5.73x.
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.scatter([1, 2], [1, 2], s=450.0)
    ax.plot([1, 2], [2, 1], marker="o", markersize=10.0, linestyle="none")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Mark ratio"] is True, (
        "4.5x apart in drawn area is inside MARK_RATIO_MAX; only reading `s` "
        "as an area puts it over")


def test_mark_ratio_ignores_bar_height():
    """A bar thirty times another bar is the encoding working. Counting patch
    area here would fail every honest bar chart, and a gate that fires on
    correct work is how a suite gets ignored."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.bar([1, 2, 3], [1, 2, 30])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Mark ratio"] is True


def test_axis_redundancy_catches_a_repeated_y_label():
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 3), constrained_layout=True)
    for ax in (a, b):
        ax.plot([0, 1], [0, 1])
        ax.set_ylabel("Batch size")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Axis redundancy"] is False


def test_side_by_side_x_labels_are_not_redundant():
    """A false positive spends the credibility the gate runs on. Sharing runs
    along the axis the panels are stacked on -- two panels side by side each
    legitimately need their own x label."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 3), constrained_layout=True,
                               sharey=True)
    for ax, lab in ((a, "Epoch"), (b, "Learning rate")):
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel(lab)
    a.set_ylabel("Loss")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Axis redundancy"] is True


def test_ticks_outside_the_view_are_not_reported_as_clipped():
    """matplotlib keeps tick artists for locations outside the current limits.
    They never render, so counting them as clipped reports a defect that is not
    there."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 10], [0, 10])
    ax.set_xlim(2, 3)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Clipping"] is True


def test_hidden_axes_do_not_trip_the_checks():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.axis("off")
    ax.text(0.5, 0.5, "diagram label", ha="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert ok, [r for r in rows if r[1] is not True]


# --- type size --------------------------------------------------------------

def test_type_size_uses_the_rendered_size_not_the_source(clean):
    """The check this replaced was a regex over the source hunting for
    `fontsize=`, which saw nothing set through rcParams. Setting a size the
    regex could never have found still has to be caught."""
    with plt.rc_context({"xtick.labelsize": 4}):
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        ax.plot([0, 1], [0, 1])
        ok, rows = cf.audit(fig)
        plt.close(fig)
    assert gates(rows)["Type size"] is False


def test_type_floor_is_measured_on_the_page_not_in_the_figure():
    """A 10pt label is comfortable in a narrow figure and illegible in a wide
    one placed at the same width. That per-figure difference is the entire
    reason this check exists."""
    def smallest(width_in):
        fig, ax = plt.subplots(figsize=(width_in, 4), constrained_layout=True)
        ax.set_xlabel("Time", fontsize=10)
        ok, rows = cf.audit(fig)
        plt.close(fig)
        return gates(rows)["Type size"]

    saved = cf.CONTENT_WIDTH_PT
    try:
        cf.CONTENT_WIDTH_PT = 750          # a 16:9 slide, margins removed
        assert smallest(8.0) is True       # scale 1.30 -> 13.0pt on page
        assert smallest(20.0) is False     # scale 0.52 ->  5.2pt on page
    finally:
        cf.CONTENT_WIDTH_PT = saved


def test_placed_frac_measures_the_width_the_figure_actually_ships_at():
    """A half-width figure is half the size on the page. Measured as full
    width it is certified at twice the type it ships at, which is the wrong
    direction for a legibility gate to be wrong in."""
    fig, ax = plt.subplots(figsize=(6.0, 4), constrained_layout=True)
    ax.set_xlabel("Time", fontsize=9)

    saved = cf.CONTENT_WIDTH_PT
    try:
        cf.CONTENT_WIDTH_PT = 430              # a single-column page
        _, full = cf.audit(fig)                # scale 1.00 -> 9.0pt, fine
        _, half = cf.audit(fig, placed_frac=0.5)   # scale 0.50 -> 4.5pt, not
        assert gates(full)["Type size"] is True
        assert gates(half)["Type size"] is False
    finally:
        cf.CONTENT_WIDTH_PT = saved
        plt.close(fig)


def test_placed_frac_without_a_content_width_is_a_contradiction():
    """With CONTENT_WIDTH_PT unset the checker assumes you authored at the
    placed width, which already fixes the scale at 1.0. Silently ignoring a
    fractional placement there would report a legibility pass nobody earned."""
    fig, _ = plt.subplots(figsize=(6, 4))
    try:
        with pytest.raises(ValueError, match="CONTENT_WIDTH_PT"):
            cf.page_scale(fig, placed_frac=0.5)
    finally:
        plt.close(fig)


def test_scale_of_none_means_points_are_points():
    assert cf.CONTENT_WIDTH_PT is None, "shipped default should be project-neutral"
    fig, ax = plt.subplots(figsize=(20, 4))
    assert cf.page_scale(fig) == 1.0
    plt.close(fig)


# --- the meta-test ----------------------------------------------------------

def test_the_self_test_figure_fails_several_gates_at_once():
    """The module's own `python check_figure.py` demo. If this ever passes, the
    checker has stopped working and every downstream build is green for the
    wrong reason."""
    fig = cf.self_test_figure()
    ok, rows = cf.audit(fig)
    plt.close(fig)
    failed = {name for name, status, _ in rows if status is False}
    assert not ok
    assert {"Clipping", "Contrast stack", "Mark ratio",
            "Axis redundancy"} <= failed


# --- series color -----------------------------------------------------------

TAB10 = ["#1f77b4", "#ff7f0e", "#2ca02c"]
OKABE = ["#e69f00", "#56b4e9", "#009e73", "#0072b2", "#d55e00", "#cc79a7"]


def test_series_color_catches_the_default_matplotlib_cycle():
    """The failure that motivated the gate. A figure on matplotlib's own `tab10`
    cycle passed Clipping, Text collision, Contrast stack, Mark ratio, Axis
    redundancy, Type size and Ink coverage clean, and its orange and green
    measure CAM02-UCS dE 2.4 under protanopia -- one hue to a reader who cannot
    separate them. `check_palette.py` had always known; nothing asked it."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for i, c in enumerate(TAB10):
        ax.plot([0, 1], [i, i + 1], color=c)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is False


def test_series_color_passes_the_palette_the_guide_prescribes():
    """The nearest legitimate case: the theme's own six slots, in order, as
    lines. If this ever fails the gate is rejecting the thing it exists to
    prescribe."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for i, c in enumerate(OKABE):
        ax.plot([0, 1], [i, i + 1], color=c)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_pairs_mode_is_inferred_from_the_marks():
    """Drawn as lines a reader compares neighbours; drawn as scatter every
    series lands beside every other, and the mode has to follow the marks.

    The palette is not the shipped cycle any more. Before 0.8.0 the cycle's six
    slots cleared adjacent and failed all-pairs, so it demonstrated the two
    modes for free; under CAM02-UCS its worst all-pairs view is 12.8 against a
    10.5 floor and it clears both. That is a real result and it is pinned in
    `test_the_whole_cycle_now_clears_all_pairs` -- but it leaves this test
    needing a palette that still separates the modes, so it builds one: blue and
    violet are 8.6 apart under protan simulation and never adjacent, with orange
    between them.
    """
    palette = ["#0072b2", "#d55e00", "#87019f"]

    def audit_three(scatter):
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        for i, c in enumerate(palette):
            if scatter:
                ax.scatter([0, 1], [i, i + 1], color=c)
            else:
                ax.plot([0, 1], [i, i + 1], color=c)
        ok, rows = cf.audit(fig)
        plt.close(fig)
        return gates(rows)["Series color"]

    assert audit_three(scatter=False) is True
    assert audit_three(scatter=True) is False


def test_the_whole_cycle_now_clears_all_pairs():
    """What the metric change bought, stated as a test rather than left in a
    changelog entry.

    The style sheet ships six slots and the guide used to say only the first
    five could be used where every series sits beside every other, because the
    sixth pair measured 7.7 against an OKLab floor of 8.0. In CAM02-UCS the same
    pair is 12.8 against 10.5. The restriction was an artefact of measuring in a
    space with no calibrated threshold, and removing it is the only place a
    reader gets *more* room out of 0.8.0 rather than less.
    """
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for i, c in enumerate(OKABE):
        ax.scatter([0, 1], [i, i + 1], color=c)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True, gates(rows)


def test_series_color_catches_a_seventh_hue():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for i, c in enumerate(OKABE + ["#7f4fc9"]):
        ax.plot([0, 1], [i, i + 1], color=c)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is False
    assert "7 distinct data hues" in dict(
        (n, d) for n, _, d in rows)["Series color"]


def test_series_color_catches_two_identities_sharing_a_hue():
    """What a seventh series looks like after the cycler wraps: matplotlib
    reuses slot 1 without complaint and the legend confidently lists both."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Baseline")
    ax.plot([0, 1], [1, 0], color=OKABE[0], label="Tuned")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is False


def test_one_identity_drawn_twice_in_one_hue_is_not_a_collision():
    """A fit and its data, or a solid and a dashed segment of one curve, share a
    label because they share an identity. Keying the check on the artist count
    instead of the label text would fail every one of them."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Baseline")
    ax.plot([1, 2], [1, 2], color=OKABE[0], ls="--", label="Baseline")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_a_gray_series_is_legal():
    """The lightness-band and chroma-floor rows are deliberately not applied to
    harvested colors. A gray control curve beside a colored one is correct work,
    and failing it is the noise that teaches people to skim past the row."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color="#808080", label="Control")
    ax.plot([0, 1], [1, 0], color=OKABE[0], label="Treated")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_a_colormapped_artist_is_not_a_categorical_palette():
    """Scatter colored by magnitude is a continuous encoding answering to the
    viridis rule. Harvesting its per-point colors would hand the palette gates
    256 hues and fail every heatmap in the world."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.scatter([1, 2, 3, 4], [1, 4, 2, 3], c=[0.1, 0.4, 0.7, 1.0], cmap="viridis")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_grid_and_reference_ink_are_not_counted_as_series_hues():
    """Furniture drawn in the sheet's own ink tokens lands in `ax.lines`
    alongside the data. Counting it would fail a figure for the color of its
    own axis rules."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Signal")
    ax.axhline(0.5, color="#52514e")          # ink secondary
    ax.axvline(0.5, color="#c3c2b7")          # axis
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True
    assert "1 data hue" in dict((n, d) for n, _, d in rows)["Series color"]


def test_series_color_scopes_the_comparison_to_a_panel():
    """Two hues in different panels never sit side by side for a reader, so
    gating them against each other is a defect the reader can't see. The
    figure-wide harvest did exactly that: a flow-chart node in panel a measured
    against a regression curve in panel b. Each panel here separates internally;
    only the cross-panel pair is close, and that pair is not a comparison."""
    # Ordered so the close cross-panel pair (blue vs violet) is consecutive in
    # the figure-wide harvest -- otherwise adjacent mode never compares them and
    # the old figure-wide code passes for the wrong reason.
    #
    # Violet rather than the teal this used before 0.8.0. The teal was picked to
    # sit ~dE 6 from blue under the old OKLab metric and reads 8.6 under
    # CAM02-UCS, still close enough for the cross-panel point -- but it also read
    # 9.8 against the pink in its own panel, which the 10.5 floor now fails, so
    # the fixture stopped isolating the thing it was built to isolate. Violet
    # against blue is the same confusion and a cleaner one: it is where protan
    # simulation collapses hardest, and it is 33.3 clear of the pink beside it.
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    a.plot([0, 1], [1, 0], color="#d55e00", label="Acquisition")  # orange
    a.plot([0, 1], [0, 1], color="#0072b2", label="GP mean")      # blue
    b.plot([0, 1], [0, 1], color="#87019f", label="DMTA node")    # violet, dE 8.9 vs blue
    b.plot([0, 1], [1, 0], color="#cc79a7", label="Assay")        # pink
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_a_scatter_in_one_panel_does_not_force_all_pairs_on_another():
    """`_axes_all_pairs` returned True if *any* axes held a scatter, which
    flipped line-only panels into the stricter regime too. The six theme slots
    clear adjacent separation (what lines need) but not all-pairs; a scatter two
    panels over must not be what fails them."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    for i, c in enumerate(OKABE):
        a.plot([0, 1], [i, i + 1], color=c)          # six lines: adjacent-legal
    b.scatter([0, 1], [0, 1], color=OKABE[0])        # one scatter, one hue
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_one_series_drawn_as_band_line_and_points_is_one_identity():
    """A posterior shown as a credible band, its mean line and its observed
    points is one series in one hue, drawn three ways -- each artist legitimately
    labelled. The wrap check keyed on 'distinct labels sharing a hue', which
    can't tell that from an actual cycler wrap. A wrap reuses one artist type;
    this is three kinds, so it is not a wrap."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.fill_between([0, 1], [0, 0], [1, 1], color=OKABE[3], alpha=0.3,
                    label="95% credible band")
    ax.plot([0, 1], [0.5, 0.6], color=OKABE[3], label="Posterior mean")
    ax.scatter([0.2, 0.8], [0.3, 0.7], color=OKABE[3], label="Observations")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is True


def test_two_lines_in_one_hue_still_read_as_a_wrapped_cycler():
    """The narrowing must not blunt the check it narrows: two *lines* in one hue
    with two labels is the wrap the gate exists to catch. Same kind, two
    identities -- still a failure."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Baseline")
    ax.plot([0, 1], [1, 0], color=OKABE[0], label="Tuned")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Series color"] is False


# --- dual axis --------------------------------------------------------------

def test_dual_axis_catches_twinx_carrying_its_own_data():
    """Both scales are chosen by the author, so where the two curves cross is
    an artifact of the limits rather than anything in the data. This figure
    passed every other check in this file clean."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1, 2], [1, 2, 3], color=OKABE[0])
    tw = ax.twinx()
    tw.plot([0, 1, 2], [300, 200, 100], color=OKABE[1])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Dual axis"] is False


def test_a_bare_unit_relabel_axis_is_not_a_dual_axis():
    """The one legitimate second scale: a pure unit relabel, where the twin is
    furniture and carries no data of its own. Failing this would ban degrees
    C against degrees F."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1, 2], [0, 10, 20], color=OKABE[0])
    ax.secondary_yaxis("right", functions=(lambda c: c * 9 / 5 + 32,
                                           lambda f: (f - 32) * 5 / 9))
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Dual axis"] is True


def test_an_inset_is_not_a_dual_axis():
    """An inset carries its own data on its own scale and is correct work. It
    is told apart by geometry: it does not share the parent's frame."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1, 2], [0, 1, 2], color=OKABE[0])
    sub = ax.inset_axes([0.6, 0.15, 0.3, 0.3])
    sub.plot([0, 1], [1, 0], color=OKABE[1])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Dual axis"] is True


# --- form -------------------------------------------------------------------

def test_form_catches_a_pie_chart():
    fig, ax = plt.subplots(figsize=(4, 4), constrained_layout=True)
    ax.pie([3, 4, 5])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is False


def test_form_catches_a_3d_axes():
    fig = plt.figure(figsize=(4, 4))
    ax = fig.add_subplot(projection="3d")
    ax.plot([0, 1], [0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is False


def test_form_catches_a_truncated_bar_baseline():
    """Bar length encodes the value, so a cut baseline misstates every ratio on
    the chart. The fix is the form, not the axis."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.bar([1, 2, 3], [101, 103, 108])
    ax.set_ylim(100, 110)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is False


def test_an_honest_bar_chart_keeps_its_baseline_and_passes():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.bar([1, 2, 3], [101, 103, 108])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is True


def test_a_log_axis_bar_chart_is_not_a_truncated_baseline():
    """A log axis cannot include zero, so it is truncated by construction. This
    gate has nothing to say about it, and saying something would be a false
    positive on every order-of-magnitude comparison."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.bar([1, 2, 3], [10, 1000, 100000])
    ax.set_yscale("log")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is True


def test_a_dot_plot_is_the_sanctioned_alternative_and_passes():
    """The fix the truncated-bar message names has to itself clear the suite,
    or the gate is telling people to trade one failure for another."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.scatter([101, 103, 108], [1, 2, 3], color=OKABE[0], zorder=3)
    ax.set_xlim(100, 110)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Form"] is True


# --- identity channel -------------------------------------------------------

def test_identity_channel_warns_on_color_alone_and_does_not_gate():
    """A warning, not a gate: the script can count the hues but cannot tell a
    direct label from any other annotation, and failing on that guess would
    fire on correct work."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Baseline")
    ax.plot([0, 1], [1, 0], color=OKABE[1], label="Tuned")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Identity channel"] == "warn"
    assert ok, [r for r in rows if r[1] is False]


def test_identity_channel_is_satisfied_by_a_legend():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0], label="Baseline")
    ax.plot([0, 1], [1, 0], color=OKABE[1], label="Tuned")
    ax.legend()
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Identity channel"] is True


# --- label attribution ------------------------------------------------------

def _two_lines_with_a_drifting_label(offset):
    """Two flat curves 0.4 apart, with `Alpha`'s direct label lifted `offset`
    off its own line and toward the other one."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    x = [0, 5, 10]
    ax.plot(x, [1.0] * 3, color=OKABE[0], label="Alpha")
    ax.plot(x, [1.4] * 3, color=OKABE[1], label="Beta")
    ax.annotate("Alpha", (5, 1.0 + offset), ha="center", va="center")
    return fig


def test_label_attribution_catches_a_label_nearer_the_wrong_curve():
    """The defect text-on-text collision cannot see. This figure has exactly one
    annotation, so nothing overlaps anything and `Text collision` is clean while
    the label reads as belonging to the curve above it."""
    fig = _two_lines_with_a_drifting_label(0.28)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is False
    assert gates(rows)["Text collision"] is True


def test_label_attribution_passes_a_label_hugging_its_own_curve():
    """The same figure with the label where it belongs. A gate that fired here
    would fire on every correct direct label in the project."""
    fig = _two_lines_with_a_drifting_label(0.02)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


def test_label_attribution_ignores_text_that_names_no_series():
    """A callout, a panel letter or an `n = 300` attributes nothing to a curve.
    Judging those means guessing intent, and guessing wrong is what teaches
    people to skim the row."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 5, 10], [1.0] * 3, color=OKABE[0], label="Alpha")
    ax.plot([0, 5, 10], [1.4] * 3, color=OKABE[1], label="Beta")
    ax.annotate("n = 300", (5, 1.2), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


def test_label_attribution_ignores_legend_entries():
    """A legend is a lookup key placed *away* from the curves by design, so
    judging its entries by proximity to those curves can only ever fail. The
    entries' strings match the series labels and a legend child's `.axes` is the
    parent axes, so the `t.axes is ax` guard let them through -- a figure that
    keeps its legend got failed by the attribution check for doing so."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    # Own curves sit low-left and low-right; the legend rides the upper-right
    # corner, so each entry is nearer the *other* curve than its own.
    ax.plot([0, 2, 4], [0.0, 0.2, 0.0], color=OKABE[0], label="Small eta")
    ax.plot([6, 8, 10], [0.0, 0.2, 0.0], color=OKABE[1], label="Large eta")
    ax.legend(loc="upper center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


def test_label_attribution_is_quiet_on_a_single_curve():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 5, 10], [1.0] * 3, color=OKABE[0], label="Alpha")
    ax.annotate("Alpha", (5, 1.0), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


# --- style sheet ------------------------------------------------------------

def test_style_sheet_row_notices_the_sheet_is_not_in_effect():
    """The three silent failures at once: a color written with a leading `#`,
    a forgotten `plt.style.use`, and a later rcParams override. Every one of
    them ships stock matplotlib with the whole suite green."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Style sheet"] == "warn"
    assert ok, "advisory only -- another project's sheet is correct work"


def test_style_sheet_row_passes_when_the_sheet_is_the_one_in_effect():
    from conftest import STYLE_SHEET
    with plt.style.context(str(STYLE_SHEET)):
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        ax.plot([0, 1], [0, 1])
        ok, rows = cf.audit(fig)
        plt.close(fig)
    assert gates(rows)["Style sheet"] is True


# --- contour dash ---------------------------------------------------------


def _grid():
    import numpy as np
    return np.meshgrid(np.linspace(-2, 2, 50), np.linspace(-2, 2, 50))


def test_contour_dash_warns_on_a_signed_field():
    """The case the gate is named for, and the one it used to miss entirely.

    The condition was that EVERY level be non-positive, which a genuinely
    signed field never satisfies: `contour` over data spanning zero draws levels
    either side of it and matplotlib dashes the negative half. The only test
    this gate had drew `-(X**2 + Y**2)` — non-positive throughout, the one shape
    that met the condition — so a gate that fired on nothing real looked green.
    """
    import numpy as np
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    cs = ax.contour(X, Y, np.sin(X) * np.cos(Y), colors="black")
    assert min(cs.levels) < 0 < max(cs.levels), "the field has to span zero"
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] == "warn"
    assert ok


def test_contour_dash_warns_on_negative_levels():
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.contour(X, Y, -(X**2 + Y**2), colors="black")   # monochrome: auto-dash
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] == "warn"
    assert ok


def test_contour_dash_passes_with_explicit_solid_linestyle():
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.contour(X, Y, -(X**2 + Y**2), linestyles="solid")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] is True


def test_contour_dash_passes_on_a_signed_field_drawn_solid():
    """The fix the warning tells you to make has to actually clear the row."""
    import numpy as np
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.contour(X, Y, np.sin(X) * np.cos(Y), colors="black", linestyles="solid")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] is True


def test_contour_dash_does_not_fire_without_a_negative_level():
    """Nothing is dashed when there is nothing negative to dash, so widening
    the condition to 'any negative level' must not start firing on ordinary
    positive-valued fields."""
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    cs = ax.contour(X, Y, X**2 + Y**2 + 1.0, colors="black")
    assert min(cs.levels) > 0
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] is True


def test_contour_dash_does_not_fire_on_a_colormapped_contour():
    """A non-monochrome contour is solid at every level: matplotlib only
    applies `negative_linestyles` when one color is doing all the work."""
    import numpy as np
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.contour(X, Y, np.sin(X) * np.cos(Y), cmap="viridis")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] is True


def test_contour_dash_does_not_fire_on_a_filled_contour():
    """`contourf` draws bands, not isolines. There is no stroke to be dashed."""
    import numpy as np
    X, Y = _grid()
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.contourf(X, Y, np.sin(X) * np.cos(Y), cmap="viridis")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Contour dash"] is True


def test_contour_dash_does_not_fire_on_clean_figure(clean):
    ok, rows = cf.audit(clean)
    plt.close(clean)
    assert gates(rows).get("Contour dash", True) is True


def test_ink_coverage_warns_and_does_not_gate():
    """A heatmap legitimately measures near 1.0. Failing on that would train
    everyone to ignore the row, which is worse than not having it."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.imshow([[1, 2], [3, 4]])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] in (True, "warn")
    assert ok


def test_context_ink_does_not_warn():
    """A contourf backdrop should not trigger the ink WARN when declared as
    a context surface."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    X, Y = np.meshgrid(np.linspace(0, 10, 50), np.linspace(0, 10, 50))
    Z = np.sin(X) * np.cos(Y)
    ax.contourf(X, Y, Z, levels=20, cmap="viridis")
    ax.scatter([2, 4, 6, 8], [2, 4, 6, 8], c="red", s=30)
    ok, rows = cf.audit(fig, context_axes=[ax])
    plt.close(fig)
    assert gates(rows)["Ink coverage"] is True


def test_overplotting_warns_on_dense_scatter():
    """~70 points packed into a tiny cluster at large size should WARN."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    rng = np.random.default_rng(42)
    x = rng.normal(0.5, 0.015, 70)
    y = rng.normal(0.5, 0.015, 70)
    ax.scatter(x, y, s=160, alpha=0.5)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn"


def test_overplotting_clean_on_spread_scatter():
    """Well-separated points should not trigger the overplotting WARN."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([1, 2, 3, 4, 5, 6, 7, 8], [1, 4, 2, 5, 3, 6, 8, 7], s=40)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] is True


def test_overplotting_catches_discs_that_touch_without_swallowing_centres():
    """The regression the radius arithmetic was hiding.

    A grid of marks spaced at 1.5x the drawn radius: every disc overlaps each
    neighbour by a quarter of its diameter, and the 64 of them render as one
    solid square. The old test was `nn_dist < radius_px` on a radius computed
    as `sqrt(s / pi)`, so it wanted the centres 1.13 radii apart when contact
    happens at 2, and it called this figure clean.

    Spacing is set in display pixels and mapped back through the data
    transform, so the geometry does not move if the figure size or the default
    dpi changes underneath it.
    """
    import numpy as np
    size = 400.0
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.set_xlim(0, 400)
    ax.set_ylim(0, 400)
    radius_px = cf.scatter_diameter_pt(size) / 2.0 * fig.dpi / 72.0
    inv = ax.transData.inverted()
    origin = inv.transform((100.0, 100.0))
    step = inv.transform((100.0 + 1.5 * radius_px,
                          100.0 + 1.5 * radius_px)) - origin
    grid = np.arange(8)
    x, y = np.meshgrid(origin[0] + step[0] * grid, origin[1] + step[1] * grid)
    ax.scatter(x.ravel(), y.ravel(), s=size)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn", (
        "discs 1.5 radii apart overlap by a quarter of their diameter and "
        "render as one blob")


def test_overplotting_uses_both_radii_when_sizes_differ():
    """Contact is `d < r_i + r_j`. With one big mark and one small one, testing
    against a single radius asks the wrong question of whichever point it is
    reading, and which one that is depends on iteration order."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    big, small = 900.0, 25.0          # radii 15.0 and 2.5 pt
    r_big = cf.scatter_diameter_pt(big) / 2.0 * fig.dpi / 72.0
    r_small = cf.scatter_diameter_pt(small) / 2.0 * fig.dpi / 72.0
    # Sit them where the discs plainly overlap but the centres are further
    # apart than either radius alone.
    gap = 0.95 * (r_big + r_small)
    assert gap > r_big and gap > r_small
    inv = ax.transData.inverted()
    a = inv.transform((150.0, 150.0))
    b = inv.transform((150.0 + gap, 150.0))
    ax.scatter([a[0], b[0]], [a[1], b[1]], s=np.array([big, small]))
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn"


def _eclipsed_marks(figsize=(6, 4.5), dpi=200):
    """40 small marks in pairs, each pair under a disc that swallows both.

    Within a pair the two small marks are each other's nearest neighbour and
    sit 8px apart, clear of contact at radius 3. The big mark is 20px off, so
    it is nobody's nearest neighbour, and its radius is 60, so it covers both.
    Geometry is laid out in display pixels and mapped back through the data
    transform, so it does not move if the default figure size changes.
    """
    import numpy as np
    r_small, r_big, spread, offset = 3.0, 60.0, 8.0, 20.0

    def size_for(radius_px):
        return (2.0 * radius_px * 72.0 / dpi) ** 2

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    up = np.sqrt(offset ** 2 - (spread / 2) ** 2)
    px, sizes = [], []
    for cx in np.arange(bb.x0 + 90, bb.x1 - 90, 150.0):
        for cy in np.arange(bb.y0 + 90, bb.y1 - 90, 150.0):
            px += [(cx - spread / 2, cy), (cx + spread / 2, cy), (cx, cy + up)]
            sizes += [size_for(r_small)] * 2 + [size_for(r_big)]
    data = ax.transData.inverted().transform(np.array(px))
    ax.scatter(data[:, 0], data[:, 1], s=sizes)
    return fig


def test_overplotting_catches_a_mark_eclipsed_by_a_non_nearest_neighbour():
    """Nearest is the wrong neighbour to ask about once radii vary.

    Contact is `d < r_i + r_j`, and the `j` that minimises `d` need not be the
    `j` that maximises `r_j`. Measured on this fixture: all 60 marks are in
    contact and 40 of them do not appear in the render at all, while the 1-NN
    test found 33% and the gate returned "no scatter overplotting".

    The render assertion is what makes it a defect rather than an arithmetic
    quibble: the small marks' colour is not on the page.
    """
    import numpy as np
    fig = _eclipsed_marks()
    coll = fig.axes[0].collections[0]
    xy = fig.axes[0].transData.transform(coll.get_offsets())
    rad = (cf.scatter_diameter_pt(np.asarray(coll.get_sizes(), float)) / 2.0
           * fig.dpi / 72.0)
    d = np.hypot(xy[:, 0][:, None] - xy[None, :, 0],
                 xy[:, 1][:, None] - xy[None, :, 1])
    np.fill_diagonal(d, np.inf)
    nn = d.argmin(axis=1)
    by_nn = (d[np.arange(len(xy)), nn] < rad + rad[nn]).mean()
    truth = (d < rad[:, None] + rad[None, :]).any(axis=1).mean()
    assert by_nn <= cf.OVERPLOT_THRESHOLD < truth, (
        f"the fixture stopped separating the two tests: 1-NN {by_nn:.0%}, "
        f"truth {truth:.0%}")

    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn"


def test_eclipse_is_caught_without_scipy_too(monkeypatch):
    """CI installs no scipy, so the numpy path is the one that runs there. The
    eclipse fixture has to fail on both or the gate is only fixed on a dev
    machine."""
    _without_scipy(monkeypatch)
    fig = _eclipsed_marks()
    verdict = cf.check_overplotting(fig)
    plt.close(fig)
    assert verdict[0] == "warn", verdict


def test_contact_fraction_fast_path_agrees_with_the_exact_one():
    """The uniform-radii shortcut rests on one identity: where `r_i + r_j` is a
    constant, some mark is within it exactly when the nearest mark is. Assert it
    against the full pair enumeration rather than against the derivation, so a
    change to either path that broke the agreement shows up here."""
    import numpy as np
    cKDTree = pytest.importorskip("scipy.spatial").cKDTree
    rng = np.random.default_rng(7)
    for spread in (12.0, 30.0, 90.0):
        xy = rng.uniform(0, 400, size=(300, 2))
        radius = np.full(len(xy), spread / 2.0)
        fast = cf._contact_fraction(xy, radius, cKDTree)
        exact = cf._contact_fraction(xy, radius, None)
        assert fast == pytest.approx(exact), (
            f"at radius {spread / 2}: nearest-neighbour {fast}, all-pairs "
            f"{exact}")
        # And nudging one radius off constant moves it onto the pair path
        # without moving the answer.
        radius[0] += 1e-9
        assert cf._contact_fraction(xy, radius, cKDTree) == pytest.approx(exact)


def test_contact_fraction_is_exact_across_radius_octaves():
    """The mixed-radii path groups marks by radius octave and bounds each group
    by its own largest radius rather than the scatter's. That bound is the whole
    correctness argument, so assert it against the full pair enumeration on the
    shapes that stress it: graded radii spanning six octaves, a single oversized
    mark among uniform ones, and zero-radius marks, which draw nothing and can
    still be contacted."""
    import numpy as np
    cKDTree = pytest.importorskip("scipy.spatial").cKDTree
    rng = np.random.default_rng(11)
    for trial in range(24):
        n = int(rng.integers(2, 250))
        xy = rng.uniform(0, 300, size=(n, 2))
        shape = trial % 4
        if shape == 0:              # graded, every octave populated
            radius = np.exp(rng.uniform(np.log(0.5), np.log(32.0), n))
        elif shape == 1:            # one mark far larger than the rest
            radius = np.full(n, 4.0)
            radius[rng.integers(0, n)] = 90.0
        elif shape == 2:            # zero-radius marks mixed in
            radius = rng.choice([0.0, 2.0, 50.0], n)
        else:                       # everything sub-pixel
            radius = rng.uniform(0.0, 2.0, n)
        assert (cf._contact_fraction(xy, radius, cKDTree)
                == cf._contact_fraction(xy, radius, None)), (
            f"trial {trial}: shape {shape}, n {n}")


def test_contact_fraction_does_not_inflate_the_query_radius():
    """One oversized mark used to set the candidate radius for every other mark
    in the scatter. At 50000 uniform points with a single mark 13x their radius
    that enumerated 62 million candidate pairs into a 994MB array, and on a
    Gaussian cloud of 60000 it did not return at all. Grouped by octave, the
    oversized mark is a group of one. Asserted as a candidate count rather than
    as a running time, because a timing threshold measures the CI runner."""
    import numpy as np
    cKDTree = pytest.importorskip("scipy.spatial").cKDTree
    rng = np.random.default_rng(3)
    n = 20000
    xy = rng.uniform(0, 600, size=(n, 2))
    radius = np.full(n, 3.0)
    radius[0] = 40.0

    inflated = cKDTree(xy).count_neighbors(cKDTree(xy), 2.0 * radius.max())
    assert inflated > 5_000_000, (
        "this fixture no longer reproduces the blowup it was written for")

    groups = cf._radius_octaves(radius)
    assert sorted(len(g) for g in groups) == [1, n - 1]
    # A mark in group A is asked about group B out to `r_i + max(r_B)`, and
    # `r_i <= max(r_A)`, so `max(r_A) + max(r_B)` bounds every candidate the
    # grouped path can look at. The oversized mark widens only the two pairings
    # its own one-point group takes part in.
    trees = {id(g): cKDTree(xy[g]) for g in groups}
    bounded = sum(
        trees[id(a)].count_neighbors(trees[id(b)],
                                     radius[a].max() + radius[b].max())
        for a in groups for b in groups)
    assert bounded < inflated / 50, (inflated, bounded)


# --- overplotting boundary conditions ---------------------------------------

def test_overplotting_threshold_is_strict_greater_than():
    """Exactly 50% overlapping points should pass (frac > 0.5, not >=)."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0, 0, 50, -50], [0, 0.01, 50, -50], s=100)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] is True


def test_overplotting_single_point_is_skipped():
    """Fewer than 2 offsets: no pairwise distance to compute."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0.5], [0.5], s=200)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] is True


def test_overplotting_all_points_overlap():
    """Every point on top of every other: fraction should be 1.0."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0.5] * 10, [0.5] * 10, s=100)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn"


def test_overplotting_two_points_overlap():
    """2 of 3 overlapping = 0.67 > 0.5, should warn."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0, 0, 100], [0, 0, 100], s=100)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] == "warn"


def test_overplotting_empty_sizes_is_skipped():
    """A PathCollection with no sizes should be skipped (len(sizes) == 0)."""
    from matplotlib.collections import PathCollection
    from matplotlib.path import Path
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    coll = PathCollection(
        [Path([(0, 0), (1, 1)])],
        sizes=np.array([]),
        offsets=np.column_stack([[1, 2, 3], [1, 2, 3]]),
        offset_transform=ax.transData)
    ax.add_collection(coll)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Overplotting"] is True


# --- multi-panel attribution ------------------------------------------------

def test_label_attribution_is_scoped_per_panel():
    """Labels in one panel must not be judged against curves in another panel.
    Panel A has two close curves; panel B has a label naming B's own curve
    that sits nearer A's curve in absolute space. That must not fail."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    a.plot([0, 5, 10], [0, 2, 0], color=OKABE[0], label="Alpha")
    a.plot([0, 5, 10], [0, 3, 0], color=OKABE[1], label="Beta")
    b.plot([0, 5, 10], [10, 10, 10], color=OKABE[2], label="Gamma")
    b.annotate("Gamma", (5, 10), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


def test_label_attribution_in_one_panel_does_not_break_another():
    """A misattached label in panel A must not stop panel B from being
    checked. Both panels have two curves; panel A's label is misattached
    and should fail, panel B's label is correct."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    a.plot([0, 5, 10], [0, 2, 0], color=OKABE[0], label="Alpha")
    a.plot([0, 5, 10], [0, 3, 0], color=OKABE[1], label="Beta")
    a.annotate("Alpha", (5, 2.8), ha="center", va="center")
    b.plot([0, 5, 10], [10, 10, 10], color=OKABE[2], label="Gamma")
    b.plot([0, 5, 10], [8, 8, 8], color=OKABE[3], label="Delta")
    b.annotate("Gamma", (5, 10), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is False


# --- _legend_text_ids -------------------------------------------------------

def test_legend_text_ids_returns_only_legend_texts():
    """Direct unit test for _legend_text_ids: only legend text IDs, not
    axis label IDs."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], label="Signal")
    ax.set_xlabel("Time")
    ax.legend()
    ids = cf._legend_text_ids(fig)
    plt.close(fig)
    assert isinstance(ids, set)
    ax_label_ids = {id(t) for t in ax.get_xticklabels() + ax.get_yticklabels()}
    assert not ids & ax_label_ids, "legend texts should not include tick labels"
    assert len(ids) >= 1, "should contain at least one legend text"


def test_legend_text_ids_handles_figure_level_legend():
    """fig.legend() creates a figure-level legend; _legend_text_ids must
    include its texts."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], label="Signal")
    ax.plot([1, 0], [0, 1], label="Noise")
    fig.legend()
    ids = cf._legend_text_ids(fig)
    plt.close(fig)
    assert len(ids) >= 2, "figure-level legend should have 2+ entries"


def test_legend_text_ids_empty_when_no_legend():
    """No legends on the figure means an empty set."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], label="Signal")
    ids = cf._legend_text_ids(fig)
    plt.close(fig)
    assert ids == set()


# --- text readability -------------------------------------------------------

def test_readability_catches_a_label_printed_on_its_own_curve():
    """The defect that motivated the check: a direct label sitting on the line
    it names. Attribution is perfect — it is nearest its own curve by a mile —
    and the curve runs straight through the letterforms."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    x = np.linspace(0, 10, 400)
    y = np.exp(-0.2 * x)
    ax.plot(x, y, color=OKABE[0], lw=1.6)
    at = 200
    ax.annotate("Baseline", (x[at], y[at]), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is False
    assert gates(rows)["Label attribution"] is True


def test_halo_reads_withstroke():
    """`_halo` reads `Stroke._gc`, a matplotlib internal with no public
    accessor, and returns `(None, 0.0)` when it cannot find it.

    That fallback is the dangerous shape: a rename upstream would not raise,
    it would silently mean 'this label wears no casing', and every cased label
    in every figure would then be judged against the raw backdrop the casing
    exists to survive. Correct work would start failing and nothing would say
    why. Asserting the read directly turns a matplotlib upgrade that moves the
    attribute into a red suite here instead.
    """
    from matplotlib import patheffects as pe
    fig, ax = plt.subplots()
    t = ax.text(0.5, 0.5, "cased",
                path_effects=[pe.withStroke(linewidth=3.0, foreground="white")])
    color, width = cf._halo(t)
    plt.close(fig)
    assert color == "white", "the casing color did not come back off the artist"
    assert width == 3.0


def test_halo_is_none_without_a_stroke_effect():
    fig, ax = plt.subplots()
    t = ax.text(0.5, 0.5, "bare")
    assert cf._halo(t) == (None, 0.0)
    plt.close(fig)


def test_casing_does_not_launder_a_label_sitting_on_a_curve():
    """A white halo makes the finished render look clean by punching a gap
    through the data. Measuring the backdrop instead of the render is what
    stops the casing from hiding the collision it caused."""
    import numpy as np
    from matplotlib import patheffects as pe
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    x = np.linspace(0, 10, 400)
    y = np.exp(-0.2 * x)
    ax.plot(x, y, color=OKABE[0], lw=1.6)
    ax.annotate("Baseline", (x[200], y[200]), ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=3.0, foreground="white")])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is False


def test_readability_passes_a_label_on_clear_ground():
    """Same figure, label moved off the line. Gridlines still pass behind it."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    x = np.linspace(0, 10, 400)
    y = np.exp(-0.2 * x)
    ax.plot(x, y, color=OKABE[0], lw=1.6)
    ax.annotate("Baseline", (x[200], y[200] + 0.35), ha="left", va="bottom")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is True


def test_readability_does_not_fire_on_a_gridline_behind_a_label():
    """Casing exists so a gridline can pass behind a label. Furniture is read
    off the figure's own gridlines, so a project that changed the grid color
    does not get every label failed."""
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.grid(True, color="#c9c9c9", linewidth=1.2)
    ax.plot([0, 1], [0, 1], color=OKABE[0])
    ax.text(0.5, 0.2, "Annotation on the grid", ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is True


def test_readability_catches_faint_text_on_the_page():
    """WCAG's text threshold, not the 3:1 a mark gets: a glyph stem is thinner
    than a mark, so text that clears the mark gate can still be unreadable."""
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color=OKABE[0])
    ax.text(0.5, 0.5, "Barely there", color="#aaaaaa", ha="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is False


def _rotated_labels(rotation, places, figsize=(5, 4)):
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    ax.set_axis_off()
    for text, x, y in places:
        ax.text(x, y, text, rotation=rotation, transform=ax.transAxes,
                fontsize=11)
    return fig


def test_oriented_box_round_trips_the_extent_matplotlib_reports():
    """`_corners` reconstructs the oriented box from the rotated AABB and the
    unrotated extent. The reconstruction is only sound if the AABB of the
    corners comes back as the AABB matplotlib gave, so assert that across a
    spread of angles rather than trusting the derivation.

    The second assertion is the point of the exercise: the oriented box holds
    the same area at every angle, because it is the same string, while the
    axis-aligned one reaches 5x that at 45 degrees.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    ax.set_axis_off()
    r, _ = cf._renderer(fig)
    areas = {}
    for rotation in (0, 15, 30, 45, 60, 90, 120, -37):
        t = ax.text(0.4, 0.4, "ascending label", rotation=rotation,
                    transform=ax.transAxes, fontsize=11)
        bb = t.get_window_extent(renderer=r)
        box = cf._corners(t, bb, r)
        span = box.max(axis=0) - box.min(axis=0)
        assert span[0] == pytest.approx(bb.width, abs=0.5)
        assert span[1] == pytest.approx(bb.height, abs=0.5)
        edge_a, edge_b = box[1] - box[0], box[3] - box[0]
        areas[rotation] = float(np.hypot(*edge_a) * np.hypot(*edge_b))
        t.remove()
    plt.close(fig)
    upright = areas[0]
    for rotation, area in areas.items():
        assert area == pytest.approx(upright, rel=0.02), (
            f"the same string at {rotation} degrees came back as a box of "
            f"{area:.0f} against {upright:.0f} upright")


def test_collisions_do_not_fire_on_separated_oblique_labels():
    """Two parallel 45-degree labels with clear page between them. Their
    axis-aligned boxes overlap heavily and their ink does not touch, which is
    the false positive the oriented box exists to remove."""
    import numpy as np
    places = [("ascending label", 0.05, 0.05), ("parallel label", 0.05, 0.28)]

    def ink(one):
        fig = _rotated_labels(45, [one])
        fig.canvas.draw()
        mask = np.asarray(fig.canvas.buffer_rgba())[..., :3].sum(axis=2) < 700
        plt.close(fig)
        return mask

    assert not (ink(places[0]) & ink(places[1])).any(), (
        "the fixture stopped being a false positive: the glyphs now touch")

    fig = _rotated_labels(45, places)
    r, _ = cf._renderer(fig)
    ok, detail = cf.check_collisions(fig, r)
    plt.close(fig)
    assert ok is True, detail


def test_collisions_still_fire_on_oblique_labels_that_do_overlap():
    """The other half. Removing a false positive by never firing is not a fix,
    so the same two labels moved on top of each other still collide."""
    fig = _rotated_labels(45, [("ascending label", 0.30, 0.30),
                               ("parallel label", 0.33, 0.27)])
    r, _ = cf._renderer(fig)
    ok, _detail = cf.check_collisions(fig, r)
    plt.close(fig)
    assert ok is False


def test_clipping_is_unaffected_by_rotation():
    """Why `check_clipping` was left on the axis-aligned box.

    An AABB is the bounding box of the oriented box's own corners, so every
    extreme it reports is attained by a real corner of the label and a min/max
    test against the canvas gives the same answer on either shape. Asserted so
    the next reader does not 'fix' this gate the way the collision gate needed
    fixing, and so a change to `_corners` that broke the identity is caught.
    """
    fig = _rotated_labels(45, [("ascending label", 0.62, 0.62)])
    r, _ = cf._renderer(fig)
    for t, bb in cf._texts(fig, r):
        box = cf._corners(t, bb, r)
        assert box[:, 0].min() == pytest.approx(bb.x0, abs=0.5)
        assert box[:, 0].max() == pytest.approx(bb.x1, abs=0.5)
        assert box[:, 1].min() == pytest.approx(bb.y0, abs=0.5)
        assert box[:, 1].max() == pytest.approx(bb.y1, abs=0.5)
    plt.close(fig)


def _oblique_label_with_strokes(offsets):
    """A 45-degree label with strokes laid parallel to it, `offsets` pixels off
    perpendicular. Positive offsets put them in the empty upper-left triangle of
    the label's axis-aligned box; offsets near zero run them through the glyphs.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xticks([])
    ax.set_yticks([])
    t = ax.text(5, 5, "annotation text", rotation=45, ha="center", va="center",
                fontsize=11, color="#000000")
    r, _ = cf._renderer(fig)
    bb = t.get_window_extent(renderer=r)
    inv = ax.transData.inverted()
    centre = np.array([(bb.x0 + bb.x1) / 2.0, (bb.y0 + bb.y1) / 2.0])
    along = np.array([1.0, 1.0]) / np.sqrt(2.0)
    perp = np.array([-1.0, 1.0]) / np.sqrt(2.0)
    for off in offsets:
        mid = centre + off * perp
        half = bb.width / np.sqrt(2.0) - abs(off) - 4
        seg = inv.transform(np.array([mid - half * along, mid + half * along]))
        ax.plot(seg[:, 0], seg[:, 1], color=OKABE[1], lw=2.0,
                solid_capstyle="butt")
    return fig


def test_readability_does_not_sample_the_page_beside_an_oblique_label():
    """The clutter fraction was measured over the axis-aligned block, which for
    an oblique label is mostly page the label does not sit on.

    Measured on this fixture: a 191.5 x 191.5 block, 36669 pixels, around an
    oriented box of 239.5 x 31.3, 7505. Six strokes laid in the empty upper-left
    triangle, none of them touching a glyph, came back as 'data ink over 14% of
    its box'. The first assertion is what makes that a false positive rather
    than a threshold argument: the mask the gate now measures over contains none
    of the stroke ink.
    """
    import numpy as np
    from matplotlib.colors import to_rgb
    fig = _oblique_label_with_strokes((34, 44, 54, 64, 74, 84))
    r, canvas = cf._renderer(fig)
    backdrop = np.asarray(canvas.buffer_rgba())[..., :3]
    H, W = backdrop.shape[:2]
    (t, bb), = [(t, bb) for t, bb in cf._texts(fig, r)]
    xa, xb = max(int(bb.x0) - 1, 0), min(int(bb.x1) + 2, W)
    ya, yb = max(int(bb.y0) - 1, 0), min(int(bb.y1) + 2, H)
    block = backdrop[H - yb:H - ya, xa:xb]
    mask = cf._oriented_mask(cf._corners(t, bb, r), xa, yb, block.shape[:2])
    stroke = (np.abs(block.astype(int)
                     - np.array(to_rgb(OKABE[1])) * 255).sum(axis=2) < 30)
    assert stroke.any(), "the fixture drew no strokes to be a false alarm about"
    assert not (stroke & mask).any(), (
        "the fixture stopped being a false positive: the strokes now cross the "
        "label's oriented box")

    ok, detail = cf.check_text_readability(fig, r, canvas)
    plt.close(fig)
    assert ok is True, detail


def test_readability_still_catches_ink_crossing_an_oblique_label():
    """The other half. Removing a false positive by never firing is not a fix,
    so the same strokes moved onto the glyphs still fail."""
    fig = _oblique_label_with_strokes((-12, -6, 0, 6, 12))
    r, canvas = cf._renderer(fig)
    ok, _detail = cf.check_text_readability(fig, r, canvas)
    plt.close(fig)
    assert ok is False


def test_oriented_mask_covers_the_box_and_nothing_else():
    """The mask is the oriented box rasterised, so its pixel count has to be
    that box's area, and every pixel it selects has to be inside the corners.

    Asserted against `_corners` rather than against a stored number: the two
    have to stay the same rectangle, and a mask that quietly drifted a few
    degrees off would still look plausible by area alone.
    """
    import numpy as np
    fig = _rotated_labels(37, [("ascending label", 0.35, 0.35)])
    r, _ = cf._renderer(fig)
    (t, bb), = cf._texts(fig, r)
    box = cf._corners(t, bb, r)
    xa, yb = int(bb.x0) - 1, int(bb.y1) + 2
    shape = (yb - (int(bb.y0) - 1), (int(bb.x1) + 2) - xa)
    mask = cf._oriented_mask(box, xa, yb, shape)
    plt.close(fig)

    edge_a, edge_b = box[1] - box[0], box[3] - box[0]
    area = float(np.hypot(*edge_a) * np.hypot(*edge_b))
    assert int(mask.sum()) == pytest.approx(area, rel=0.02)

    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xa + xs + 0.5, yb - ys - 0.5]) - box[0]
    for edge in (edge_a, edge_b):
        proj = pts @ edge
        assert proj.min() >= 0 and proj.max() <= float(edge @ edge)


def test_oriented_mask_is_the_whole_block_for_an_upright_box():
    """An upright label keeps the numbers it was measured on. `_corners` hands
    back the axis-aligned box there, and a mask built from it selects the block
    entire, so the caller's shortcut of passing None costs nothing."""
    import numpy as np
    box = np.array([(10.0, 20.0), (70.0, 20.0), (70.0, 44.0), (10.0, 44.0)])
    mask = cf._oriented_mask(box, 10, 44, (24, 60))
    assert mask.all()


def test_separating_axis_agrees_with_the_old_test_on_upright_boxes():
    """`_overlap` used to be a min/max comparison of two axis-aligned boxes.
    SAT has to give that same answer wherever both boxes are upright, or this
    change moved verdicts on every figure that draws no rotated text."""
    import numpy as np

    def box(x0, y0, x1, y1):
        return np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], dtype=float)

    def aabb_overlap(a, b):
        dx = min(a[2][0], b[2][0]) - max(a[0][0], b[0][0])
        dy = min(a[2][1], b[2][1]) - max(a[0][1], b[0][1])
        return dx > 0 and dy > 0

    cases = [
        ((0, 0, 10, 10), (5, 5, 15, 15)),        # corner overlap
        ((0, 0, 10, 10), (10, 0, 20, 10)),       # edge to edge, touching
        ((0, 0, 10, 10), (11, 0, 20, 10)),       # clear
        ((0, 0, 10, 10), (2, 2, 4, 4)),          # contained
        ((0, 0, 10, 10), (0, 0, 10, 10)),        # identical
        ((0, 0, 10, 2), (0, 1, 10, 3)),          # thin, overlapping
        ((0, 0, 10, 2), (0, 2, 10, 4)),          # thin, touching
    ]
    for first, second in cases:
        a, b = box(*first), box(*second)
        assert cf._overlap(a, b) == bool(aabb_overlap(a, b)), (first, second)


def test_contrast_field_agrees_with_the_scalar_helper():
    """`_contrast_field_255` is the vectorisation of `_contrast_255`, not a
    second definition of WCAG contrast. Walk a spread of colours through both
    and they cannot drift apart without this going red."""
    import numpy as np
    swatches = np.array([
        [0, 0, 0], [255, 255, 255], [128, 128, 128], [10, 10, 10],
        [253, 231, 37], [68, 1, 84], [33, 145, 140], [0, 114, 178],
        [1, 2, 3], [254, 0, 128],
    ], dtype=float)
    for fg in ([255, 255, 255], [0, 0, 0], [230, 159, 0]):
        field = cf._contrast_field_255(fg, swatches)
        for row, got in zip(swatches, field):
            assert got == pytest.approx(cf._contrast_255(fg, row), rel=1e-12)


def test_worst_backdrop_reads_a_smooth_field_not_its_mean():
    """The regression the `pix // 8` binning was hiding.

    A viridis ramp under a label's box splits into dozens of 8-cubes, none of
    them covering `TEXT_BACKDROP_MIN_SHARE` of it, so the old code fell through
    to the mean of the whole box -- the summary its own docstring rules out,
    returned by the branch written to avoid it. Measured there: 76 bins, a 3.5%
    mode, and a verdict identical to the mean against a true worst pixel of
    1.34:1.

    Asserted as a bound rather than a fixed number: the point is that the
    verdict tracks the dark tenth of the box and not its average, and pinning
    the exact ratio would make this a test of viridis's sample values.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), dpi=200)
    Z = np.linspace(0, 1, 200)[None, :].repeat(200, 0)
    ax.imshow(Z, cmap="viridis", aspect="auto")
    r, canvas = cf._renderer(fig)
    block = np.asarray(canvas.buffer_rgba())[..., :3][100:130, 100:700]
    plt.close(fig)

    fg = np.array([255.0, 255.0, 255.0])
    _, ratio = cf._worst_backdrop(block, fg, cf.TEXT_BACKDROP_MIN_SHARE)

    pix = block.reshape(-1, 3).astype(float)
    per_pixel = cf._contrast_field_255(fg, pix)
    mean_of_box = cf._contrast_255(fg, pix.mean(axis=0))

    assert ratio < mean_of_box / 2, (
        f"the box mean reads {mean_of_box:.2f}:1 and the verdict came back "
        f"{ratio:.2f}:1, which is the mean again rather than the dark tenth")
    assert per_pixel.min() <= ratio <= float(np.percentile(per_pixel, 15))

    # And the colour reported alongside it is a pixel that is really there.
    color, _ = cf._worst_backdrop(block, fg, cf.TEXT_BACKDROP_MIN_SHARE)
    assert (pix == color).all(axis=1).any()


def test_worst_backdrop_still_reads_a_flat_fill_as_itself():
    """The case the binning got right has to keep working: a box entirely on
    one colour reports that colour's contrast, with no quantile artefact."""
    import numpy as np
    block = np.full((30, 60, 3), 0x00, dtype=np.int16)
    block[..., 1] = 0x72
    block[..., 2] = 0xB2                                    # solid #0072b2
    fg = np.array([255.0, 255.0, 255.0])
    color, ratio = cf._worst_backdrop(block, fg, cf.TEXT_BACKDROP_MIN_SHARE)
    assert list(color) == [0x00, 0x72, 0xB2]
    assert ratio == pytest.approx(cf._contrast_255(fg, (0x00, 0x72, 0xB2)))


def test_uniform_fill_under_a_label_is_a_background_not_clutter():
    """A label on a heatmap cell has the cell as its surface. Only the contrast
    clause governs there, which is the correct division: a flat fill is a
    background, a curve is not."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.set_facecolor("#0072b2")
    ax.plot([0, 1], [0, 1], color="white")
    ax.text(0.5, 0.2, "On the fill", color="white", ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is True


# --- fonts ------------------------------------------------------------------

def test_fonts_warns_on_type_3_and_does_not_gate():
    """Type 3 is read off global rcParams, not off anything the figure carries,
    so it cannot tell another project's settings from none — the same reason
    the style-sheet row is advisory."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    with plt.rc_context({"pdf.fonttype": 3, "ps.fonttype": 3}):
        ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Fonts"] == "warn"
    assert ok


def test_fonts_passes_on_type_42():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    with plt.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Fonts"] is True


def test_fonts_warns_when_no_named_face_is_installed():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    with plt.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42,
                         "font.family": "serif",
                         "font.serif": ["No Such Face Anywhere"]}):
        ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Fonts"] == "warn"


# --- alt text ---------------------------------------------------------------

def test_alt_text_warns_when_absent(clean):
    ok, rows = cf.audit(clean)
    assert gates(rows)["Alt text"] == "warn"
    assert ok, "a missing description is advisory: the caption may carry it"


def test_alt_text_warns_on_a_title_masquerading_as_a_description(clean):
    cf.describe(clean, "Validation loss")
    ok, rows = cf.audit(clean)
    assert gates(rows)["Alt text"] == "warn"


def test_alt_text_passes_on_a_real_description(clean):
    cf.describe(clean, "Validation loss against training epoch for three "
                       "optimisers. All three fall; the Bayesian run reaches "
                       "0.05 by epoch 6 while the baseline is still at 0.25.")
    ok, rows = cf.audit(clean)
    assert gates(rows)["Alt text"] is True


def test_alt_metadata_is_what_savefig_wants(clean):
    assert cf.alt_metadata(clean) == {}
    cf.describe(clean, "x" * 80)
    assert cf.alt_metadata(clean) == {"Description": "x" * 80}


def test_alt_metadata_uses_a_key_the_pdf_format_has(clean):
    """PDF's info dictionary is a closed set and `Description` is not in it."""
    cf.describe(clean, "x" * 80)
    assert cf.alt_metadata(clean, "out.pdf") == {"Subject": "x" * 80}
    assert cf.alt_metadata(clean, "OUT.PDF") == {"Subject": "x" * 80}
    for other in ("out.png", "out.svg"):
        assert cf.alt_metadata(clean, other) == {"Description": "x" * 80}


def test_alt_metadata_is_none_for_a_format_that_carries_nothing(clean):
    """jpeg and the other rasters reject `metadata=` outright, and matplotlib's
    guard is `is not None` -- so an empty dict raises exactly as hard as a full
    one. `None` is the only value the documented call can survive there, with
    or without a description attached."""
    for suffix in sorted(cf.ALT_TEXT_UNSUPPORTED_SUFFIXES):
        assert cf.alt_metadata(clean, f"out{suffix}") is None, suffix
    cf.describe(clean, "x" * 80)
    for suffix in sorted(cf.ALT_TEXT_UNSUPPORTED_SUFFIXES):
        assert cf.alt_metadata(clean, f"out{suffix}") is None, suffix


def test_alt_metadata_falls_back_when_there_is_no_readable_format(clean):
    """A buffer keeps its format in a `savefig` kwarg this never sees, so the
    only honest answer is the one every earlier version always gave."""
    import io
    cf.describe(clean, "x" * 80)
    assert cf.alt_metadata(clean, io.BytesIO()) == {"Description": "x" * 80}
    assert cf.alt_metadata(clean, "out") == {"Description": "x" * 80}
    assert cf.alt_metadata(clean) == {"Description": "x" * 80}


def test_alt_metadata_reads_the_name_of_an_open_file(clean, tmp_path):
    """`savefig` takes an open file, and an open file knows its own path."""
    cf.describe(clean, "x" * 80)
    with open(tmp_path / "fig.pdf", "wb") as fh:
        assert cf.alt_metadata(clean, fh) == {"Subject": "x" * 80}


@pytest.mark.parametrize("suffix", sorted(cf.ALT_TEXT_KEY_BY_SUFFIX))
def test_alt_metadata_matches_what_each_format_accepts(clean, tmp_path, suffix):
    """The format table, saved for real in every format it names.

    Three of its rows are behaviours nothing documents: PDF warns on
    `Description`, SVG *raises* on `Subject`, and the rasters raise on any key.
    A table of those written from memory is a table that rots, so this asks
    matplotlib instead -- no warning, and the text present in the bytes.
    """
    import warnings
    cf.describe(clean, "x" * 80)
    path = tmp_path / f"fig{suffix}"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        clean.savefig(path, metadata=cf.alt_metadata(clean, path))
    assert not caught, [str(w.message) for w in caught]
    blob = path.read_bytes()
    if suffix == ".svgz":
        import gzip
        blob = gzip.decompress(blob)
    assert b"x" * 80 in blob, f"{suffix} did not carry the description"


@pytest.mark.parametrize(
    "suffix", sorted(cf.ALT_TEXT_UNSUPPORTED_SUFFIXES - {".pgf"}))
def test_saving_an_unsupported_format_does_not_raise(clean, tmp_path, suffix):
    """The other half of the table: the documented call has to survive a format
    that has nowhere to put a description."""
    pytest.importorskip("PIL")          # matplotlib routes the rasters through it
    cf.describe(clean, "x" * 80)
    path = tmp_path / f"fig{suffix}"
    clean.savefig(path, metadata=cf.alt_metadata(clean, path))
    assert path.is_file()


def test_pgf_rejects_the_metadata_kwarg_at_any_value(clean, tmp_path):
    """The one format `alt_metadata` cannot rescue, asserted rather than skipped.

    Every other entry in the unsupported set accepts `metadata=None` — which is
    why returning None is the fix. The PGF backend does not take the argument at
    all, so `savefig(path, metadata=anything)` raises there no matter what this
    module returns, and `savefig(path)` is the only call that works.

    Stated as a test because a skip would assert nothing: if matplotlib gives
    PGF the kwarg later, this goes red and the row comes out of the table.

    Running it needs a real TeX on PATH, which is why CI installs texlive-xetex
    on one leg. `clean` is a constrained_layout figure with axis labels, so the
    PGF renderer measures its text through `pgf.texsystem` before savefig gets
    near the kwarg. With no xelatex the call still raises, but it raises
    LatexManager's "'xelatex' not found", which says nothing about the row this
    test guards. That is a missing tool, not a broken claim, so it skips.
    """
    pytest.importorskip("matplotlib.backends.backend_pgf")
    texsystem = matplotlib.rcParams["pgf.texsystem"]
    if shutil.which(texsystem) is None:
        pytest.skip(f"{texsystem} is not installed, so the PGF renderer cannot "
                    "measure text and savefig fails before reaching the kwarg")
    cf.describe(clean, "x" * 80)
    path = tmp_path / "fig.pgf"
    assert cf.alt_metadata(clean, path) is None
    with pytest.raises(TypeError):
        clean.savefig(path, metadata=None)


@pytest.mark.parametrize("suffix", ["png", "pdf", "svg"])
def test_saving_with_alt_metadata_is_warning_free(clean, tmp_path, suffix):
    """The documented call, run for real, in each format the guide names.

    `metadata={"Description": ...}` made matplotlib warn "Unknown infodict
    keyword" on every PDF save — the one format a paper figure ships as — while
    writing a key no reader looks for. A warning on the happy path is how a
    documented workflow teaches people it is doing something wrong.
    """
    import warnings
    cf.describe(clean, "x" * 80)
    path = tmp_path / f"fig.{suffix}"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        clean.savefig(path, metadata=cf.alt_metadata(clean, path))
    assert not [w for w in caught if "infodict" in str(w.message)], (
        [str(w.message) for w in caught])
    assert b"x" * 80 in path.read_bytes(), "the description did not reach the file"


# --- venue widths -----------------------------------------------------------

def test_venue_overrides_the_module_level_width():
    """A 7in figure on NeurIPS' 397.48pt textwidth shrinks to 0.79x, and the
    type floor moves with it."""
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    scale = cf.page_scale(fig, venue="neurips")
    plt.close(fig)
    assert scale == pytest.approx(397.48 / (7 * 72), rel=1e-6)


def test_unknown_venue_names_the_ones_it_knows():
    with pytest.raises(KeyError) as exc:
        cf.content_width_pt("nurips")
    assert "neurips" in str(exc.value)


def test_venue_and_placed_frac_compose():
    fig, ax = plt.subplots(figsize=(3.2, 2.4), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    scale = cf.page_scale(fig, placed_frac=0.48, venue="acl")
    plt.close(fig)
    assert scale == pytest.approx(455.24 * 0.48 / (3.2 * 72), rel=1e-6)


def test_placed_frac_without_any_width_still_refuses():
    """The guard that predates the venue table has to keep holding: a
    fractional placement with no width to measure against is a contradiction,
    not a default."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.plot([0, 1], [0, 1])
    with pytest.raises(ValueError, match="placed_frac"):
        cf.page_scale(fig, placed_frac=0.5)
    plt.close(fig)


def test_venue_cannot_be_passed_positionally():
    """The 4th positional is context_axes. A venue string lands there, is
    iterated into a frozenset of ids because a string is iterable, nothing
    raises, and the venue is discarded: a failing figure reported green."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("x", fontsize=8)
    with pytest.raises(TypeError):
        cf.audit(fig, None, 1.0, "neurips")
    assert gates(cf.audit(fig, venue="neurips")[1])["Type size"] is False
    plt.close(fig)


def test_scale_and_placed_frac_stay_positional():
    """The break is scoped to the two arguments that were being confused."""
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1])
    cf.audit(fig, 0.5)
    cf.audit(fig, None, 0.5)
    plt.close(fig)


# --- label attribution: the case a KD-tree silently passed -------------------

def test_polyline_does_not_bridge_a_gap_in_the_data():
    """A break in the data is a break in the stroke.

    Dropping non-finite vertices and then densifying across what is left joins
    the two sides of every hole: a 100-point sine with `y[40:60] = nan` came
    back with 326 invented points strung across a stretch of blank page, and
    `check_label_attribution` measured labels against a curve that is not
    there. Both spellings of a break are checked, because `Line2D` fills a
    masked array with NaN on recache and they arrive here as the same thing.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    x = np.linspace(0, 10, 101)

    nan_y = np.sin(x)
    nan_y[40:60] = np.nan
    masked_y = np.ma.masked_where((x >= x[40]) & (x <= x[59]), np.sin(x))

    edges = ax.transData.transform(np.column_stack([x, np.zeros_like(x)]))[:, 0]
    lo, hi = edges[39], edges[60]

    for label, y in (("nan", nan_y), ("masked", masked_y)):
        line, = ax.plot(x, y)
        pts = cf._polyline_px(line, ax)
        inside = int(((pts[:, 0] > lo + 2) & (pts[:, 0] < hi - 2)).sum())
        assert inside == 0, f"{label}: {inside} points invented across the gap"
        # and the stroke that IS drawn is still densified on both sides
        assert len(pts) > 101
        line.remove()
    plt.close(fig)


def test_label_attribution_sees_a_scatter_as_a_series():
    """`ax.lines` alone left a point cloud invisible twice over: it could not
    own a label, and it could not be the neighbour that made one ambiguous. A
    reader resolving a direct label by proximity does not know what artist
    class drew the ink."""
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    ax.plot([0, 1, 2, 3], [0, 1, 2, 3], label="Line")
    ax.scatter([0, 0.5, 1, 1.5, 2], [2.2, 2.3, 2.4, 2.5, 2.6], s=40,
               label="Cloud")
    ax.text(1.0, 2.0, "Line", ha="center")
    r, _ = cf._renderer(fig)
    ok, detail = cf.check_label_attribution(fig, r)
    plt.close(fig)
    assert ok is False, detail
    assert "another" in detail


def test_a_shaded_band_is_not_a_phantom_series_at_the_origin():
    """`fill_between` and the other `PolyCollection`s report a single zero
    offset and no sizes. Taking that at face value plants a series at data
    (0, 0) in every figure with a band in it, which is a neighbour no reader
    can see and the gate would measure every label against. A band is read
    through its paths, so what comes back is the outline actually drawn."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    ax.plot([1, 2, 3], [1, 2, 3], label="A")
    ax.plot([1, 2, 3], [3, 2, 1], label="B")
    band = ax.fill_between([1, 2, 3], [0.5, 1.5, 2.5], [1.5, 2.5, 3.5],
                           alpha=0.3)
    fig.canvas.draw()
    got = cf._series_px(band, ax)
    origin = ax.transData.transform((0, 0))
    inside = ax.transData.transform([(1, 0.5), (3, 3.5)])
    plt.close(fig)

    assert got is not None and len(got) > 2
    assert not (np.hypot(got[:, 0] - origin[0],
                         got[:, 1] - origin[1]) < 1.0).any(), (
        "the band is being read as a single offset at data (0, 0)")
    assert got[:, 0].min() >= inside[0, 0] - 1
    assert got[:, 1].max() <= inside[1, 1] + 1


def test_step_geometry_follows_the_staircase_not_the_chord():
    """`get_xydata` returns what was passed in, and `ax.step` draws a staircase
    through those points rather than the chords between them.

    Measured on this square wave: 836 harvested points, 785 of them on blank
    page. Asserted against the render rather than against a reimplementation of
    the staircase — every point the gate would measure a label against has to
    have ink within 2px of it, or the gate is judging a line nobody drew.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 3), dpi=150)
    x = np.arange(6, dtype=float)
    line, = ax.step(x, [1.0, 5.0, 1.0, 5.0, 1.0, 5.0], where="post",
                    label="stepped")
    fig.canvas.draw()
    pts = cf._polyline_px(line, ax)
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3]
    H = buf.shape[0]
    ink = np.abs(buf.astype(int) - buf[0, 0]).sum(axis=2) > 40
    plt.close(fig)

    off = 0
    for p in pts:
        col, row = int(round(p[0])), H - int(round(p[1])) - 1
        if not (0 <= row < ink.shape[0] and 0 <= col < ink.shape[1]):
            continue
        if not ink[max(row - 2, 0):row + 3, max(col - 2, 0):col + 3].any():
            off += 1
    assert off == 0, (
        f"{off} of {len(pts)} harvested points sit on blank page, so the "
        "geometry is the chord and not the staircase")


def test_the_step_expansion_is_still_where_matplotlib_keeps_it():
    """`_drawstyle_xy` reads `cbook.pts_to_*step` rather than reimplementing
    the staircase.

    That read has the dangerous failure shape: a rename upstream would not
    raise, it would mean 'this line has no drawstyle', and every step plot would
    quietly revert to its chords with correct work starting to fail and nothing
    saying why. Assert the three helpers resolve and that the expansion they
    give is the one matplotlib draws.
    """
    import numpy as np
    from matplotlib import cbook
    for name in ("pts_to_prestep", "pts_to_midstep", "pts_to_poststep"):
        assert hasattr(cbook, name), f"matplotlib moved cbook.{name}"

    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    x = np.arange(5, dtype=float)
    y = np.array([2.0, 4.0, 1.0, 5.0, 3.0])
    for where, fn in (("pre", cbook.pts_to_prestep),
                      ("mid", cbook.pts_to_midstep),
                      ("post", cbook.pts_to_poststep)):
        line, = ax.step(x, y, where=where)
        assert cf._drawstyle_xy(line) == pytest.approx(
            np.column_stack(fn(x, y)))
        line.remove()
    # and an ordinary line is left exactly as it came in
    line, = ax.plot(x, y)
    assert cf._drawstyle_xy(line) == pytest.approx(np.column_stack([x, y]))
    plt.close(fig)


def test_label_attribution_reads_a_stacked_band():
    """A `stackplot` band is `PolyCollection` geometry with no offsets, so the
    offsets harvest returned nothing for it and a label sitting in the wrong
    band passed clean.

    Bands share their dividing edge, which is why the filled case is judged on
    containment: on boundary distance alone a label inside the upper band is
    exactly as far from the lower band's outline as from its own, and every
    stacked label reads as ambiguous.
    """
    import numpy as np
    x = np.arange(6, dtype=float)
    lower, upper = np.full(6, 4.0), np.full(6, 4.0)

    def figure(text_y):
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        ax.stackplot(x, lower, upper, labels=("lower", "upper"),
                     colors=(OKABE[0], OKABE[1]))
        ax.text(2.5, text_y, "upper", ha="center", va="center")
        return fig

    fig = figure(2.0)                       # in the lower band, named "upper"
    r, _ = cf._renderer(fig)
    wrong = cf.check_label_attribution(fig, r)
    plt.close(fig)

    fig = figure(6.0)                       # in the upper band, named "upper"
    r, _ = cf._renderer(fig)
    right = cf.check_label_attribution(fig, r)
    plt.close(fig)

    assert wrong[0] is False, wrong
    assert right[0] is True, right


def test_label_attribution_reads_a_contour_set_as_a_neighbour():
    """Contour lines are `LineCollection`-shaped geometry with no offsets and
    no legend label, and they were harvested as nothing. A label on a curve
    threading a contour field had no neighbour to be ambiguous against."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    g = np.linspace(-3, 3, 60)
    X, Y = np.meshgrid(g, g)
    cs = ax.contour(X, Y, X ** 2 + Y ** 2, levels=[1.0, 4.0])
    plt.close(fig)
    assert cf._series_px(cs, ax) is not None, (
        "an unfilled contour set is a stroke and has to be read as one")


@pytest.mark.parametrize("band_label", [None, "95% CI"])
def test_an_error_band_is_not_a_rival_for_its_own_curves_label(band_label):
    """The over-fire the path harvest could have introduced.

    A confidence band lies on top of the curve it belongs to, so counting it as
    a rival puts a competitor at distance zero from every direct label on that
    curve and fails correct work.

    Parametrised because the first fix for this asked whether the band carried
    a legend-visible label, and that got the labelled case exactly backwards:
    labelling a band for the legend is the normal reason to label one, and it
    made the gate fail a figure it had passed unlabelled. The band's relation to
    the curve is the same either way, so the verdict has to be too.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    x = np.linspace(0, 10, 200)
    y = np.sin(x)
    ax.plot(x, y, color=OKABE[0], label="Alpha")
    ax.plot(x, y - 3.0, color=OKABE[1], label="Beta")
    ax.fill_between(x, y - 0.4, y + 0.4, color=OKABE[0], alpha=0.25,
                    **({"label": band_label} if band_label else {}))
    ax.annotate("Alpha", (5, np.sin(5.0)), ha="center", va="center")

    fig.canvas.draw()
    band = ax.collections[0]
    line = ax.lines[0]
    assert cf._encloses(band, cf._series_px(line, ax)), (
        "the band does not read as enclosing the curve it was drawn around")
    _ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


@pytest.mark.parametrize("scale", ["linear", "log"])
def test_a_band_encloses_its_curve_on_a_nonlinear_scale(scale):
    """`_encloses` on an axis whose transform is not affine.

    Every fixture above draws on linear axes, and on those the defect this
    catches is invisible. `Path.contains_points(pts, transform=t)` freezes `t`
    and hands it to the C containment test, which applies its AFFINE part only:
    on a log axis the band's outline was tested at coordinates it does not
    occupy, every point of the curve read as outside, and `_encloses` returned
    False without raising. The band then went back to being a rival for the
    curve it covers, sitting at 0px from any label on that curve, so a direct
    label under a confidence band failed `check_label_attribution` on every
    log-scaled figure. `examples/gallery.py`'s `uncertainty` figure is one, and
    is what found this.

    Parametrised over both scales so the linear case stays asserted beside it:
    the fix has to leave the case that already worked working.
    """
    import numpy as np
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    x = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
    y = 1.0 / x
    ax.fill_between(x, y * 0.8, y * 1.2, color=OKABE[0], alpha=0.25)
    line, = ax.plot(x, y, color=OKABE[0], label="rate")
    ax.set_xscale(scale)
    fig.canvas.draw()

    assert cf._encloses(ax.collections[0], cf._series_px(line, ax)), (
        f"on a {scale} x axis the band does not read as enclosing the curve "
        "it was drawn around")
    plt.close(fig)


def test_adjacent_stacked_bands_stay_rivals():
    """The other side of `SERIES_ENCLOSED_FRAC`. Neighbouring `stackplot` bands
    share a dividing edge, so each holds part of the other's outline; dismissing
    them as each other's bands would pass every mislabelled stackplot. The
    swapped-label figure below is the defect the gate exists for."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    xs = np.arange(20)
    ax.stackplot(xs, np.ones(20), np.ones(20) * 3, labels=["low", "high"])
    low, high = ax.collections[0], ax.collections[1]
    fig.canvas.draw()
    assert not cf._encloses(low, cf._series_px(high, ax))
    assert not cf._encloses(high, cf._series_px(low, ax))

    # Labels on the wrong bands, which is only reachable while they are rivals.
    ax.text(10, 2.5, "low", ha="center", va="center")
    ax.text(10, 0.5, "high", ha="center", va="center")
    r, _ = cf._renderer(fig)
    ok, detail = cf.check_label_attribution(fig, r)
    plt.close(fig)
    assert ok is False, detail


def test_label_attribution_catches_a_label_in_the_corridor():
    """The regression that motivated dropping the KD-tree. A label in the
    corridor between two curves, nearer its own but inside LABEL_MARGIN.

    Querying the k nearest *points* passes this: every near point belongs to
    the label's own curve, so no other curve is ever reached and the comparison
    distance stays infinite. Which is to say the gate passed every label whose
    own curve was nearest — which is nearly all of them, and exactly the
    population it was written to judge."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    x = np.linspace(0, 10, 600)
    ax.plot(x, np.zeros_like(x), color=OKABE[0], label="Alpha")
    ax.plot(x, np.ones_like(x), color=OKABE[1], label="Beta")
    # Nearer Alpha, but not by the factor of two the gate asks for: 0.4 to its
    # own curve against 0.6 to Beta. Alpha is dense, so every one of the k
    # nearest POINTS to the label belongs to it and a point-wise query never
    # reaches Beta at all.
    ax.annotate("Alpha", (5, 0.4), ha="center", va="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is False


def test_label_attribution_still_passes_a_well_separated_label():
    import numpy as np
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    x = np.linspace(0, 10, 600)
    ax.plot(x, np.full_like(x, 1.0), color=OKABE[0], label="Alpha")
    ax.plot(x, np.full_like(x, 5.0), color=OKABE[1], label="Beta")
    ax.annotate("Alpha", (5, 1.0), textcoords="offset points",
                xytext=(0, -8), ha="center", va="top")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Label attribution"] is True


# --- no hard scipy dependency -----------------------------------------------

def _without_scipy(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_scipy(name, *args, **kwargs):
        if name.split(".")[0] == "scipy":
            raise ImportError("scipy is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_scipy)


def test_the_checker_runs_with_scipy_unimportable(monkeypatch, clean):
    """The docs promise three files and no install. A hard scipy import
    quietly broke that, so the one place it is still used has a numpy path."""
    _without_scipy(monkeypatch)
    ok, rows = cf.audit(clean)
    assert ok, [r for r in rows if r[1] is not True]


def test_overplotting_agrees_with_and_without_scipy(monkeypatch):
    """Both branches, same verdict.

    `clean` draws no scatter, so the test above never reached the KD-tree at
    all: it proved the import was soft, not that the fallback computes the same
    nearest-neighbour distance. Which branch runs is a property of the machine
    — CI installs no scipy, a dev checkout does — so without this, one of the
    two paths is only ever exercised somewhere nobody is looking.
    """
    def dense():
        fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
        ax.scatter([0.5] * 8 + [3.0], [0.5] * 8 + [3.0], s=120)
        return fig

    pytest.importorskip("scipy.spatial")
    fig = dense()
    with_scipy = cf.check_overplotting(fig)
    plt.close(fig)

    _without_scipy(monkeypatch)
    fig = dense()
    without_scipy = cf.check_overplotting(fig)
    plt.close(fig)

    assert with_scipy[0] == "warn", with_scipy
    assert without_scipy == with_scipy, (
        f"the numpy path disagrees with the KD-tree: {without_scipy} vs "
        f"{with_scipy}")


def test_box_blur_matches_scipy_uniform_filter():
    """The numpy replacement has to be the same filter, not a similar one."""
    ndimage = pytest.importorskip("scipy.ndimage")
    import numpy as np
    rng = np.random.default_rng(3)
    field = rng.uniform(0, 255, (23, 31, 3))
    mine = cf._box_blur(field, 9)
    theirs = np.dstack([ndimage.uniform_filter(field[:, :, c], size=9,
                                               mode="nearest")
                        for c in range(3)])
    assert np.allclose(mine, theirs, atol=1e-9)


# --- line weight ----------------------------------------------------------
#
# This gate shipped without a single test, which is the one thing CONTRIBUTING
# says a gate may not do. Everything below is the coverage it should have had.


def test_line_weight_catches_a_hairline_stroke():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], lw=0.4)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Line weight"] is False


def test_line_weight_catches_a_stroke_thinned_by_placement():
    """1.2pt is legal as authored and 0.6pt on the page at half width. The
    whole point of the gate is that the second number is the one that prints."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], lw=1.2)
    ok, rows = cf.audit(fig, scale=0.5)
    plt.close(fig)
    assert gates(rows)["Line weight"] is False


def test_line_weight_does_not_fire_on_a_legal_stroke():
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.plot([0, 1], [0, 1], lw=1.5)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Line weight"] is True


def test_line_weight_does_not_fire_on_the_grid():
    """The bundled sheet ships the grid at 0.7pt on purpose. Holding furniture
    to the data floor would be failing the sheet's own design."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    ax.grid(True, lw=0.5)
    ax.plot([0, 1], [0, 1], lw=1.5)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Line weight"] is True


# --- banking ---------------------------------------------------------------


def _alternating_rates(figsize):
    """A saw wave whose decay limbs alternate between two rates, one exactly
    twice the other. Telling the two apart is the reader's whole job."""
    import numpy as np
    xs, ys = [0.0], [1.0]
    for cycle in range(10):
        steps = 12 if cycle % 2 == 0 else 6
        for k in range(1, steps + 1):
            xs.append(xs[-1] + 1.0)
            ys.append(1.0 - k / steps)
        xs.append(xs[-1] + 1.0)             # the rise back to 1, one step wide
        ys.append(1.0)
    x, y = np.array(xs), np.array(ys)
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    ax.plot(x, y, lw=1.2)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(0, 1)
    fig.canvas.draw()
    return fig, x, y


def _limb_orientations(fig, x, y):
    """Mean on-page orientation of the slow and the fast decay limbs, degrees."""
    import numpy as np
    ax = fig.axes[0]
    p = ax.transData.transform(np.column_stack([x, y]))
    d = np.diff(p, axis=0)
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    dy = np.diff(y)
    fast = (dy < 0) & (np.abs(dy) > 0.12)      # 1/6 = 0.167 against 1/12
    slow = (dy < 0) & ~fast
    return float(ang[slow].mean()), float(ang[fast].mean())


def test_banking_warns_when_the_aspect_collapses_two_rates_into_one():
    """The named failure, measured rather than asserted.

    Two decay rates differing by exactly a factor of two. At 2.4 x 5.2 inches
    they land 1.6 degrees apart on the page, which is not a difference any
    reader resolves; the first assertion is what makes that a fact about the
    figure rather than about the gate.
    """
    fig, x, y = _alternating_rates((2.4, 5.2))
    slow, fast = _limb_orientations(fig, x, y)
    assert abs(slow - fast) < 3.0, (
        f"the fixture stopped collapsing the two rates: {abs(slow - fast):.1f} "
        "degrees apart")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Banking"] == "warn"


def test_banking_is_quiet_on_the_same_data_banked():
    """The other half, and the one that says the gate is about the aspect and
    not about the data: same points, same limits, a shape that separates the
    two rates by 10.6 degrees instead of 1.6."""
    fig, x, y = _alternating_rates((6.4, 1.9))
    slow, fast = _limb_orientations(fig, x, y)
    assert abs(slow - fast) > 8.0, (
        f"the banked fixture only separates the limbs by {abs(slow - fast):.1f}"
        " degrees, so it is not the counter-example it claims to be")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Banking"] is True


def test_banking_never_returns_a_hard_failure():
    """Advisory by design. The right aspect is a judgement about what the
    reader's job is, and a gate that failed a build over it would be turned
    off."""
    fig, _x, _y = _alternating_rates((2.4, 5.2))
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Banking"] == "warn"
    assert "Banking" in cf.ADVISORY_GATES
    assert ok is not False or gates(rows)["Banking"] is not False


def test_banking_skips_the_panels_where_a_median_slope_means_nothing():
    """Four exclusions, each with a case. A steep aspect is applied to all four
    so that a panel which is *not* skipped would warn, which is what keeps this
    from passing by drawing nothing."""
    import numpy as np

    def steep(build):
        fig, ax = plt.subplots(figsize=(2.0, 6.0), dpi=100)
        build(ax)
        fig.canvas.draw()
        return fig, cf._banking_slopes(ax)

    # A full-amplitude zigzag, so the typical segment is far steeper than the
    # panel's own diagonal and a panel that is read cannot help but warn.
    x = np.arange(30, dtype=float)
    y = np.tile([0.0, 100.0], 15)

    cases = {
        "marks, not a stroke":
            lambda ax: ax.plot(x, y, linestyle="none", marker="."),
        "fixed aspect":
            lambda ax: (ax.plot(x, y), ax.set_aspect("equal")),
        "furniture, under BANKING_MIN_POINTS vertices":
            lambda ax: ax.plot(x[:4], y[:4]),
        "parametric, x does not run one way":
            lambda ax: ax.plot(np.cos(np.linspace(0, 6.2, 200)),
                               np.sin(np.linspace(0, 6.2, 200))),
    }
    for why, build in cases.items():
        fig, slopes = steep(build)
        plt.close(fig)
        assert slopes is None, f"{why}: got {slopes}"

    # and the same aspect with an ordinary stroke in it is read, and warns
    fig, slopes = steep(lambda ax: ax.plot(x, y))
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert slopes is not None and len(slopes)
    assert gates(rows)["Banking"] == "warn"


def test_banking_reads_the_authored_vertices_not_the_densified_stroke():
    """Densifying makes every segment 2px long, so a median taken over the
    densified points measures the densifier rather than the data. The two
    disagree by construction on a line whose segments differ in length."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    # Short steep steps and long shallow ones, in equal number: the authored
    # median sits between them, the densified one is dominated by the long
    # segments because densifying splits them into far more points.
    x = np.cumsum([0.0] + [0.2, 8.0] * 15)
    y = np.cumsum([0.0] + [4.0, 0.4] * 15)
    line, = ax.plot(x, y)
    fig.canvas.draw()
    authored = float(np.median(cf._banking_slopes(ax)))

    dense = cf._polyline_px(line, ax)
    d = np.diff(dense, axis=0)
    keep = np.abs(d[:, 0]) > 1e-9
    densified = float(np.median(np.abs(d[keep, 1] / d[keep, 0])))
    plt.close(fig)
    assert authored != pytest.approx(densified, rel=0.2), (
        f"authored {authored:.3f} and densified {densified:.3f} agree here, so "
        "this fixture no longer distinguishes the two readings")


def test_banking_culls_segments_that_render_flat():
    """A saturating curve - a converged training run - is 92 near-flat
    segments out of 119. Slope cannot tell the flat tail from flat at any
    aspect, and banking a panel on it asks for something sixteen hundred times
    taller; the cull has to happen before the median, or the gate warns on
    the most ordinary figure there is."""
    import numpy as np
    x = np.arange(120, dtype=float)
    y = 1.0 - np.exp(-x / 6.0)
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=100)
    ax.plot(x, y, lw=1.5)
    fig.canvas.draw()

    p = ax.transData.transform(np.column_stack([x, y]))
    d = np.diff(p, axis=0)
    dx, dy = d[:, 0], d[:, 1]
    drawn = (np.abs(dy) >= cf.BANKING_FLAT_PX) & (np.abs(dx) >= cf.BANKING_FLAT_PX)

    # The docstring's numbers, measured rather than imported: most of the
    # stroke renders flat, and the raw (unculled) median is below the floor.
    assert drawn.sum() < 0.5 * len(dx), (
        f"{drawn.sum()} of {len(dx)} segments drawn; the fixture stopped "
        "being a saturating curve")
    keep = np.abs(dx) > 1e-9
    raw = float(np.median(np.abs(dy[keep] / dx[keep])))
    assert raw < 1.0 / cf.BANKING_SLOPE_MAX, (
        f"raw median {raw:.4f}; the gate would not have warned anyway")

    ok, rows = cf.audit(fig)
    slopes = cf._banking_slopes(ax)
    plt.close(fig)
    assert gates(rows)["Banking"] is True, "the cull did not silence the warn"
    assert slopes is not None and np.median(slopes) >= 1.0 / cf.BANKING_SLOPE_MAX
    assert ok is True


def test_banking_leaves_the_saw_wave_alone():
    """The cull exists so that flat segments do not drown a real rate; it must
    not have the side effect of swallowing the figure the gate exists for. The
    saw wave renders nothing flat - every limb moves - so nothing is culled and
    the failure still lands."""
    import numpy as np
    fig, x, y = _alternating_rates((2.4, 5.2))
    ax = fig.axes[0]
    p = ax.transData.transform(np.column_stack([x, y]))
    d = np.diff(p, axis=0)
    dx, dy = d[:, 0], d[:, 1]
    drawn = (np.abs(dy) >= cf.BANKING_FLAT_PX) & (np.abs(dx) >= cf.BANKING_FLAT_PX)
    assert drawn.all(), (
        f"{int(drawn.sum())}/{len(dx)} segments drawn; the cull is eating the "
        "figure the gate exists for")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Banking"] == "warn"


# --- regressions: gates that fired on correct figures ----------------------


def test_polar_radial_tick_labels_are_not_judged():
    """Radial tick labels sit inside the disc on every polar plot matplotlib
    draws; there is no outside to move them to. Failing them told the author to
    "move the label to clear ground", which is not an available move.

    Eight seeds, not one. Exempting these labels from the clutter clause alone
    left the contrast clause failing the same figures at 2.0:1, and a single
    example passed the whole time it was still broken."""
    import numpy as np
    theta = np.linspace(0, 2 * np.pi, 80)
    for seed in range(8):
        rng = np.random.default_rng(seed)
        fig = plt.figure(figsize=(5, 5))
        ax = fig.add_subplot(projection="polar")
        ax.plot(theta, rng.random(80))
        ok, rows = cf.audit(fig)
        detail = dict((n, d) for n, _, d in rows)["Text readability"]
        plt.close(fig)
        assert gates(rows)["Text readability"] is True, (seed, detail)
        assert "not judged" in detail, detail


def test_polar_still_catches_an_illegible_label():
    """The exemption is for the radial ticks specifically, not for polar axes.
    A label the author placed on top of the curve is still a defect."""
    import numpy as np
    theta = np.linspace(0, 2 * np.pi, 200)
    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(projection="polar")
    ax.plot(theta, np.ones_like(theta), lw=6, color="#d55e00")
    ax.text(0, 1.0, "on the curve", ha="center", va="center", fontsize=14)
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Text readability"] is False


def test_redundancy_ignores_panels_with_their_axes_turned_off():
    """Three image panels at axis("off") display no tick column at all. The
    gate read the Text objects matplotlib keeps for ticks that never render,
    and advised sharey on panels with nothing to share."""
    import numpy as np
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(1, 3, figsize=(9, 3), constrained_layout=True)
    for a in axes:
        a.imshow(rng.random((8, 8)))
        a.axis("off")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Axis redundancy"] is True


def test_redundancy_still_catches_a_repeated_tick_column():
    fig, axes = plt.subplots(1, 3, figsize=(9, 3), constrained_layout=True)
    for a in axes:
        a.plot([0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Axis redundancy"] is False


def test_ink_coverage_flags_a_panel_that_was_never_filled():
    """The blank subplot in a grid -- the case that actually ships in papers.
    The frame and ticks alone measure 0.03, over the 0.02 floor, so the pixel
    fraction never caught it."""
    import numpy as np
    rng = np.random.default_rng(1)
    fig, axes = plt.subplots(2, 3, figsize=(9, 5), constrained_layout=True)
    for a in axes.flat[:5]:
        a.plot(np.linspace(0, 1, 40), rng.random(40))
    # axes.flat[5] is left empty on purpose
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] == "warn"
    assert "ax5" in dict((n, d) for n, _, d in rows)["Ink coverage"]


def test_ink_coverage_does_not_call_a_sparse_panel_empty():
    """Two points is a legitimate panel. Only a panel with no data artist at
    all is empty.

    The weights are written out rather than left to the rcParams. At the
    defaults this figure measures 0.0198 on matplotlib 3.8 and 0.0216 on 3.11 --
    a two-thousandth of rendering difference either side of the 0.02 floor, so
    the same figure passed on one supported matplotlib and warned on another,
    for a reason that has nothing to do with whether a two-point panel is
    empty. The margin is asserted below so a future drift toward the floor
    fails here saying that, instead of turning back into a version-dependent
    verdict.
    """
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.plot([0, 1], [0.2, 0.8], marker="o", linewidth=3, markersize=12)
    assert cf._axes_drew_anything(ax) is True
    ok, rows = cf.audit(fig)
    detail = dict((n, d) for n, _, d in rows)["Ink coverage"]
    plt.close(fig)
    assert gates(rows)["Ink coverage"] is True
    measured = float(re.search(r"ax0 ([\d.]+)", detail).group(1))
    assert measured >= cf.INK_MIN + 0.01, (
        f"the sparse panel now measures {measured}, back within rounding of "
        f"the {cf.INK_MIN} floor: this test is meant to exercise the structural "
        "clause, not to sit on the fraction one")


def test_ink_coverage_does_not_call_a_table_panel_empty():
    """A table lives in `ax.tables` and in none of the containers the
    dual-axis helper looks at. The emptiness check has to be the broader
    question -- was this panel used -- not the narrower one."""
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    ax.axis("off")
    ax.table(cellText=[[1, 2], [3, 4]], colLabels=["a", "b"], loc="center")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] is True


def test_ink_coverage_emptiness_is_structural_not_just_a_low_fraction():
    """The two clauses are separate on purpose. A panel holding one small
    annotation covers under 2% of its area and still warns -- that is the
    fraction clause, and it is right to. The structural clause exists for the
    panel the fraction clause cannot see, where the frame carries it over the
    floor with nothing drawn inside it."""
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    ax.axis("off")
    ax.annotate("start", xy=(0.7, 0.5), xytext=(0.2, 0.5),
                arrowprops=dict(arrowstyle="->"))
    assert cf._axes_drew_anything(ax) is True
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] == "warn"
    assert ok, "the ink row is advisory and must not gate"


def ink_fraction(fig):
    """The number the ink row reports for the first panel, read back out of it.

    Two decimals, because that is what the row prints. It is enough: what
    follows asks whether the fraction is the right quantity, not whether it is
    right in the fourth place.
    """
    return float(re.search(r"ax0 ([\d.]+)", cf.check_ink(fig)[1]).group(1))


@pytest.mark.parametrize("covered", [0.10, 0.25, 0.50])
def test_the_ink_fraction_is_the_share_of_the_panel_that_was_drawn_on(covered):
    """The row reports a number, and until now every test around it asserted
    only the verdict the number produced. A fraction that had drifted to half
    of the coverage it names would keep every one of those tests green and
    would move where the floor and the ceiling actually sit.

    Measured against a rectangle of known size in axes coordinates, with the
    furniture switched off so the only ink is the rectangle.
    """
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, covered, transform=ax.transAxes,
                               color="black"))
    measured = ink_fraction(fig)
    plt.close(fig)
    assert abs(measured - covered) <= 0.02, (
        f"a panel covered {covered} deep reports {measured}: the ink row is no "
        "longer reporting the share of the panel carrying ink, and INK_MIN and "
        "INK_MAX are thresholds on something else")


@pytest.mark.parametrize("figsize,blank", [((3, 1.5), (0.02, 0.03)),
                                           ((6, 3), (0.01, 0.01))])
def test_what_furniture_alone_measures_depends_on_the_panel_size(figsize, blank):
    """Why the emptiness clause is structural, as a measurement rather than as
    a comment in the checker.

    A blank panel's ink is its frame and ticks: a perimeter, against an area
    that grows with the panel. The blank half of a 3x1.5in pair lands on the
    0.02 floor and the blank half of a 6x3in pair lands under it -- the same
    defect, on either side of the threshold, which is exactly why asking the
    number whether a panel is empty does not work.

    The small pair is given as a range because it is the reading that moved:
    0.02 on matplotlib 3.8 and 0.03 on 3.11. A panel whose verdict hangs on
    that difference is one this suite should not be building, and
    `test_ink_coverage_does_not_call_a_sparse_panel_empty` is where that was
    learned.
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize, constrained_layout=True)
    axes[0].plot([0, 1], [0, 1])
    detail = cf.check_ink(fig)[1]
    empty = float(re.search(r"ax1 ([\d.]+)", detail).group(1))
    drew = cf._axes_drew_anything(axes[1])
    plt.close(fig)
    assert blank[0] <= empty <= blank[1], (
        f"the blank half of a {figsize} pair now measures {empty}, outside the "
        f"{blank} this was measured at")
    assert drew is False, (
        "the structural clause is what catches this panel at either reading, "
        "and it is the clause that just stopped firing")


# --- the rows report the quantity they name -----------------------------------
# Every test above this section asserts a verdict: the row that should have
# fired, fired. None of them asks whether the number the row prints is the
# number it says it is, and a gate whose measurement had drifted while its
# verdict stayed correct on the constructed figure would pass all of them --
# while every threshold in the file quietly moved, because a threshold is only
# as meaningful as the quantity it is compared against. These build a figure
# whose answer is known by arithmetic and read the number back out of the row.

@pytest.mark.parametrize("sizes,ratio", [([10, 90], 9.0), ([20, 20], 1.0),
                                         ([4, 100], 25.0)])
def test_the_mark_ratio_row_reports_the_ratio_of_the_marker_areas(sizes, ratio):
    """`s` is an area in points squared, so the ratio the row names is the
    ratio of the two numbers the caller passed -- exactly, before any
    rendering. The drawn areas printed beside it are measured and will move
    with a renderer; this one cannot."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0, 1], [0, 1], s=sizes)
    _, detail = cf.check_mark_ratio(fig)
    plt.close(fig)
    assert f"{ratio}x" in detail, (
        f"marks of {sizes} pt^2 report {detail!r}, and the ratio in it is not "
        f"{ratio}x")


@pytest.mark.parametrize("authored,scale", [(10.0, 0.5), (12.0, 0.25)])
def test_the_type_row_reports_the_size_the_label_lands_at(authored, scale):
    """The type gate's whole claim is that it measures the page and not the
    file: a label is authored at one size and arrives at another. That product
    is the measurement, and it is the one number a reader is asked to trust
    when the row tells them to cut words."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.set_xticks([])
    ax.set_yticks([])          # so the label is the only string in the row
    ax.set_xlabel("x label", fontsize=authored)
    renderer, _ = cf._renderer(fig)
    status, detail = cf.check_type_size(fig, renderer, scale=scale)
    plt.close(fig)
    assert status is False and f"({authored * scale}, 'x label')" in detail, (
        f"a {authored}pt label at scale {scale} should land at "
        f"{authored * scale}pt on the page; the row says {detail!r}")


@pytest.mark.parametrize("authored,scale", [(0.8, 0.5), (1.5, 0.5), (0.6, 1.0)])
def test_the_line_weight_row_reports_the_stroke_the_printer_gets(authored, scale):
    """Same measurement, same reason, on the other artist a page scale moves.
    The remedy is checked with it: the linewidth it names has to be the one
    that clears the floor at this scale, or the row is telling a reader to
    make a change that leaves them under it."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.plot([0, 1], [0, 1], linewidth=authored)
    status, detail = cf.check_line_weight(fig, scale=scale)
    plt.close(fig)
    assert status is False, "the figure was built to be under the floor"
    assert f"a stroke at {authored * scale:.2f}pt" in detail, (
        f"a {authored}pt stroke at scale {scale} lands at "
        f"{authored * scale:.2f}pt on the page; the row says {detail!r}")
    assert f"at least {cf.LINE_FLOOR_PT / scale:.2f}" in detail


@pytest.mark.parametrize("stacked,share", [(2, 67), (3, 75), (9, 90)])
def test_the_overplotting_row_reports_the_share_of_marks_that_merged(stacked, share):
    """A dozen tests above assert that this row warns. The percentage in it is
    what a reader thins against -- 67% of the marks buried is a different
    figure from 100% -- and it is stated in three of those docstrings without
    being asserted in any of them. One mark is placed clear of the pile so the
    share is a fraction rather than everything."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.scatter([0] * stacked + [100], [0] * stacked + [100], s=100)
    _, detail = cf.check_overplotting(fig)
    plt.close(fig)
    assert f"{share}%" in detail, (
        f"{stacked} marks on one point and one clear of them is {share}% "
        f"merged; the row says {detail!r}")


def test_the_contrast_stack_row_reports_the_alpha_levels_it_found():
    """The remedy is "keep to three levels", so the levels are the working
    part of the row: a reader picks which one to drop out of that list. It has
    to be the alphas that were drawn, sorted and deduplicated -- the same value
    twice is one level, not two."""
    fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for alpha in (1.0, 0.8, 0.8, 0.6, 0.4):
        ax.plot([0, 1], [alpha, alpha], alpha=alpha)
    status, detail = cf.check_contrast_stack(fig)
    plt.close(fig)
    assert status is False and "alpha levels [0.4, 0.6, 0.8, 1.0]" in detail, (
        f"four levels, one of them drawn twice, report {detail!r}")


# --- the colormap kind gate --------------------------------------------------

# Deliberately here and not at the top: every test above imports numpy inside
# the function that needs it, so the file states per test what that test needs.
# This section is the one place several helpers share it.
import numpy as np  # noqa: E402


def heat(cmap, n=24):
    import matplotlib.pyplot as plt
    z = np.add.outer(np.linspace(0, 1, n), np.linspace(0, 1, n))
    fig, ax = plt.subplots()
    ax.imshow(z, cmap=cmap)
    return fig


@pytest.mark.parametrize("cmap", ["viridis", "cividis", "twilight", "RdBu",
                                  "coolwarm", "magma"])
def test_a_legible_colormap_passes(cmap):
    fig = heat(cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail


@pytest.mark.parametrize("cmap", ["jet", "hsv", "rainbow", "nipy_spectral",
                                  "gist_ncar"])
def test_a_rainbow_colormap_fails(cmap):
    fig = heat(cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is False
    assert cmap in detail


def test_hsv_fails_and_twilight_passes_which_is_the_phase_portrait_case():
    bad, good = heat("hsv"), heat("twilight")
    try:
        assert cf.check_colormap(bad)[0] is False
        assert cf.check_colormap(good)[0] is True
    finally:
        plt.close(bad)
        plt.close(good)


@pytest.mark.parametrize("draw,cmap", [
    ("imshow", "viridis"),
    ("pcolormesh", "magma"),
    ("contourf", "viridis"),
    ("hexbin", "cividis"),
    ("scatter_c", "plasma"),
])
def test_harvest_reaches_every_colormapped_call(draw, cmap):
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(0)
    gx, gy = np.meshgrid(np.linspace(-2, 2, 40), np.linspace(-2, 2, 40))
    z = gx ** 2 + gy ** 2
    fig, ax = plt.subplots()
    if draw == "imshow":
        ax.imshow(z, cmap=cmap)
    elif draw == "pcolormesh":
        ax.pcolormesh(gx, gy, z, cmap=cmap)
    elif draw == "contourf":
        ax.contourf(gx, gy, z, levels=12, cmap=cmap)
    elif draw == "hexbin":
        ax.hexbin(rng.normal(size=300), rng.normal(size=300), cmap=cmap)
    elif draw == "scatter_c":
        ax.scatter(rng.random(20), rng.random(20), c=rng.random(20), cmap=cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail
    assert cmap in detail, detail


def test_a_figure_with_no_colormapped_artist_says_so_and_passes():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 4])
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True
    assert detail == "no colormapped artists"


def test_matplotlib_still_names_an_author_built_colormap_something_we_skip():
    """The version-dependent fact the test below rests on, asked of matplotlib.

    `ANONYMOUS_CMAP_NAMES` is a list of spellings, not one string, because the
    name changes between releases: 3.8.4, 3.9.4 and 3.10.0 say "from_list" and
    3.11.1 says "unnamed". The gate shipped knowing only the 3.11 spelling, so
    on the two CI jobs running older matplotlib every contour drawn with
    explicit colours was classified qualitative and hard-failed, including
    `gallery-field.png`. Every local run was on 3.11 and stayed green.

    So the fact is asserted rather than assumed. If a future matplotlib invents
    a fourth spelling this fails here, naming the new one, instead of silently
    failing every contour figure in the suite.
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
    gx, gy = np.meshgrid(np.linspace(-2, 2, 20), np.linspace(-2, 2, 20))
    fig, ax = plt.subplots()
    ax.contour(gx, gy, gx * gy, levels=3,
               colors=["#000000", "#0a0a0a", "#141414"])
    try:
        names = {artist.get_cmap().name for artist in ax.collections
                 if artist.get_array() is not None}
    finally:
        plt.close(fig)

    assert names, ("matplotlib no longer hands `contour(colors=...)` a "
                   "colormap this can read the name off")
    unknown = names - set(cf.ANONYMOUS_CMAP_NAMES)
    assert not unknown, (
        f"matplotlib {matplotlib.__version__} names an author-built colormap "
        f"{unknown}, which is not in ANONYMOUS_CMAP_NAMES. Every contour drawn "
        "with explicit colours is now classified as a colour encoding")


def test_a_contour_given_explicit_colors_is_not_read_as_a_colormap():
    """The load-bearing half of the harvest guard, and the one the `get_array`
    rule does not cover.

    `contour(colors=[...])` builds a ListedColormap that matplotlib leaves
    anonymously named, and its `get_array()` IS the level values -- so the array
    test alone lets it through. Three near-black contour lines would then be
    classified qualitative and put through all-pairs separation, which they
    fail by construction: they are ONE encoding drawn in one hue with the
    levels labelled, not three categories that have to be told apart by colour.
    Naming is the discrimination that works here -- an author who wrote
    `cmap="viridis"` chose a continuous encoding, and one who wrote
    `colors="black"` chose not to encode in colour at all."""
    import matplotlib.pyplot as plt
    import numpy as np
    gx, gy = np.meshgrid(np.linspace(-2, 2, 50), np.linspace(-2, 2, 50))
    fig, ax = plt.subplots()
    ax.contour(gx, gy, gx * gy, levels=3,
               colors=["#000000", "#0a0a0a", "#141414"])
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True
    assert detail == "no colormapped artists"


def test_an_unmapped_scatter_is_not_gated_against_a_ramp_it_never_used():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    art = ax.scatter([1, 2, 3], [1, 2, 3], color="#0072b2")
    try:
        assert art.get_cmap() is not None
        assert art.get_array() is None
        assert cf.check_colormap(fig) == (True, "no colormapped artists")
    finally:
        plt.close(fig)


def test_a_colorbar_does_not_report_its_parents_colormap_twice():
    import matplotlib.pyplot as plt
    z = np.add.outer(np.linspace(0, 1, 12), np.linspace(0, 1, 12))
    fig, ax = plt.subplots()
    im = ax.imshow(z, cmap="viridis")
    fig.colorbar(im, ax=ax)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True
    assert detail.count("viridis") == 1, detail


def test_a_qualitative_colormap_that_does_not_separate_fails():
    fig = heat("tab10")
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is False
    assert "tab10" in detail
    assert "dE" in detail, detail


def test_a_qualitative_colormap_that_does_separate_passes():
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    basins = ListedColormap(["#e69f00", "#56b4e9", "#009e73"], name="basins")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.imshow(rng.integers(0, 3, (20, 20)), cmap=basins)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail
    assert "qualitative" in detail


def test_the_qualitative_route_does_not_apply_the_band_and_chroma_rows():
    """`#f0e442` is deliberately not in this fixture; see the test below it.

    The row under test is the band-and-chroma one, and Okabe-Ito's yellow fails
    a different row for a real reason, so leaving it here would have this test
    go red for something it is not about.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    okabe = ListedColormap(["#e69f00", "#56b4e9", "#009e73", "#0072b2"],
                           name="okabe4")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.imshow(rng.integers(0, 4, (20, 20)), cmap=okabe)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail


def test_okabe_ito_yellow_beside_its_orange_misses_the_normal_vision_floor():
    """The 0.8.0 floors' sharpest consequence, and the strongest evidence for
    them that this project has.

    `NORMAL_FLOOR` was derived from Stone, Szafir & Setlur and from a measured
    colour-space bridge, with no reference to any palette. Run against the
    published Okabe-Ito eight-colour set it clears 27 of the 28 pairs and misses
    one: orange `#e69f00` against yellow `#f0e442`, at 20.75 against a floor of
    21.0.

    Yellow is one of the two colours `figure.mplstyle` already leaves out of its
    cycle. The floor was not tuned to produce that answer and the agreement is
    the reason to trust it -- so the result is pinned here rather than sanded off
    by choosing a friendlier fixture, and if a future change makes Okabe-Ito
    clear this floor completely, that is a finding and this is where it lands.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    okabe = ListedColormap(["#e69f00", "#56b4e9", "#009e73", "#f0e442"],
                           name="okabe4")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.imshow(rng.integers(0, 4, (20, 20)), cmap=okabe)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is False, detail
    assert "#e69f00" in detail and "#f0e442" in detail, detail

    import check_palette as cp
    measured = cp.delta_e(cp.hex_to_linear("#e69f00"),
                          cp.hex_to_linear("#f0e442"))
    assert measured == pytest.approx(20.75, abs=0.1), measured
    assert measured < cp.NORMAL_FLOOR

    # The rest of the published set clears the floor it misses.
    rest = ["#56b4e9", "#009e73", "#0072b2", "#d55e00", "#cc79a7", "#000000"]
    worst = min(cp.delta_e(cp.hex_to_linear(a), cp.hex_to_linear(b))
                for i, a in enumerate(["#e69f00", *rest])
                for b in ["#e69f00", *rest][i + 1:])
    assert worst >= cp.NORMAL_FLOOR, (
        f"dropping yellow no longer rescues the set: worst remaining pair "
        f"{worst:.2f} against a floor of {cp.NORMAL_FLOOR}")


def test_a_heatmap_is_not_gated_twice_under_two_different_rules():
    fig = heat("viridis")
    try:
        assert cf._data_colors_by_axes(fig) == {}
        assert cf.check_colormap(fig)[0] is True
    finally:
        plt.close(fig)


def test_the_gate_is_a_row_in_audit_between_contour_dash_and_fonts():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    try:
        _, rows = cf.audit(fig)
    finally:
        plt.close(fig)
    names = [n for n, _, _ in rows]
    assert len(names) == 21, names
    assert names[names.index("Contour dash") + 1] == "Colormap kind"
    assert names[names.index("Colormap kind") + 1] == "Fonts"


def test_a_jet_heatmap_fails_the_whole_audit():
    fig = heat("jet")
    try:
        ok, rows = cf.audit(fig)
    finally:
        plt.close(fig)
    assert ok is False
    row = next(r for r in rows if r[0] == "Colormap kind")
    assert row[1] is False, row


def test_the_colormap_row_is_not_advisory():
    assert "Colormap kind" not in cf.ADVISORY_GATES


# --- a gate that raises ------------------------------------------------------
# `audit` ran its gates in a list comprehension, so one exception anywhere
# propagated and the caller lost the twenty rows already measured. No gate is
# known to raise -- twenty adversarial figures, including 3D, polar, all-NaN,
# infinite and zero-sized ones, found none -- but these gates read deep
# matplotlib internals and `matplotlib>=3.8` has no upper bound, so the version
# that breaks one is a version nobody has released yet.


def _with_broken_gate(monkeypatch, *names):
    """`GATES` with the named gates replaced by ones that raise."""
    def boom(fig, **kwargs):
        raise RuntimeError("simulated matplotlib API change")

    monkeypatch.setattr(cf, "GATES", tuple(
        gate._replace(func=boom) if gate.name in names else gate
        for gate in cf.GATES))


def test_a_raising_gate_does_not_lose_the_other_rows(monkeypatch):
    _with_broken_gate(monkeypatch, "Clipping")
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    assert len(rows) == len(cf.GATES), (
        "one raising gate cost the rest of the audit")


def test_a_raising_hard_gate_fails_rather_than_passing(monkeypatch):
    """A gate that measured nothing has not cleared the figure. Reporting it as
    a pass is the green run that quietly stopped checking."""
    _with_broken_gate(monkeypatch, "Clipping")
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    row = next(r for r in rows if r[0] == "Clipping")
    assert row[1] is False, row
    assert "RuntimeError" in row[2], row
    assert ok is False


def test_a_raising_advisory_gate_warns_rather_than_failing(monkeypatch):
    """An advisory that crashed says so without gating a build, which is the
    verdict it would have had if it had run and found something."""
    _with_broken_gate(monkeypatch, "Fonts")
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ok, rows = cf.audit(fig)
    row = next(r for r in rows if r[0] == "Fonts")
    assert row[1] == "warn", row
    assert ok is True, "a crashed advisory gated the build"


def test_the_row_says_the_defect_is_not_in_the_figure(monkeypatch):
    """A reader whose build just turned red should not start by looking at
    their own figure."""
    _with_broken_gate(monkeypatch, "Clipping")
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    _, rows = cf.audit(fig)
    detail = next(r for r in rows if r[0] == "Clipping")[2]
    assert "defect in the checker" in detail, detail
