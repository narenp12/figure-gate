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


def test_ink_coverage_warns_and_does_not_gate():
    """A heatmap legitimately measures near 1.0. Failing on that would train
    everyone to ignore the row, which is worse than not having it."""
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    ax.imshow([[1, 2], [3, 4]])
    ok, rows = cf.audit(fig)
    plt.close(fig)
    assert gates(rows)["Ink coverage"] in (True, "warn")
    assert ok
