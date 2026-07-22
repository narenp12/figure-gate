"""Gates for check_figure.py.

The point of this file is the same as the point of the checker: a gate nobody
has watched fail is decoration. Each test below builds a figure with exactly one
defect and asserts that the matching gate is the one that catches it. Asserting
only "audit returned False" would pass even if every check had silently broken
except one, which is close to what happened twice while the checker was written.
"""

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
    measure OKLab dE 1.4 under protanopia -- one hue to a reader who cannot
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
    """Six slots clear adjacent separation and only the first four clear
    all-pairs -- the guide says so, and it is exactly the distinction the CLI
    has to be told with `--pairs`. Drawn as lines a reader compares neighbours;
    drawn as scatter every series lands beside every other."""
    def audit_six(scatter):
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        for i, c in enumerate(OKABE):
            if scatter:
                ax.scatter([0, 1], [i, i + 1], color=c)
            else:
                ax.plot([0, 1], [i, i + 1], color=c)
        ok, rows = cf.audit(fig)
        plt.close(fig)
        return gates(rows)["Series color"]

    assert audit_six(scatter=False) is True
    assert audit_six(scatter=True) is False


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


def test_ink_coverage_warns_and_does_not_gate():
    """A heatmap legitimately measures near 1.0. Failing on that would train
    everyone to ignore the row, which is worse than not having it."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.imshow([[1, 2], [3, 4]])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] in (True, "warn")
    assert ok
