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
    """The dpi the figure was authored at is the one the page gets. Leaving the
    doubled value in place would put the checker a factor of two away from
    every pixel constant at the top of the file."""
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


def test_series_color_scopes_the_comparison_to_a_panel():
    """Two hues in different panels never sit side by side for a reader, so
    gating them against each other is a defect the reader can't see. The
    figure-wide harvest did exactly that: a flow-chart node in panel a measured
    against a regression curve in panel b. Each panel here separates internally;
    only the cross-panel pair is close, and that pair is not a comparison."""
    # Ordered so the close cross-panel pair (blue vs teal) is consecutive in the
    # figure-wide harvest -- otherwise adjacent mode never compares them and the
    # old figure-wide code passes for the wrong reason.
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)
    a.plot([0, 1], [1, 0], color="#d55e00", label="Acquisition")  # orange
    a.plot([0, 1], [0, 1], color="#0072b2", label="GP mean")      # blue
    b.plot([0, 1], [0, 1], color="#2c738e", label="DMTA node")    # teal, ~dE 6 vs blue
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
    """
    pytest.importorskip("matplotlib.backends.backend_pgf")
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


# --- label attribution: the case a KD-tree silently passed -------------------

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
    all is empty."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.plot([0, 1], [0.2, 0.8], marker="o")
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] is True


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
    assert ok is True, detail


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
    assert len(names) == 20, names
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
