"""Numbers in alt text, read against the figure that carries them.

`test_docs_match_code.py` already holds the site's alt text to the string the
example attaches, so the page cannot drift from the code. What neither file did
was read the string against the picture. Both halves of the prose audit's
figure findings sat inside strings that suite called correct:

  - `eleven of twelve rise` on the slope graph. All twelve rise, and always
    have: `after` adds a normal centred at 0.11 with a spread of 0.05, so a
    fall needs a draw 2.2 sigma low, and under seed 4 the smallest gain is
    0.047.
  - `the Bayesian run reaches 0.05 by epoch 6` on the demo. At epoch 6 that
    curve is at 0.115, and 0.05 arrives at epoch 6.9.

Alt text is the figure for a reader who cannot see it. A wrong number there is
not a typo, it is the finding, told wrong, to the reader with no way to check.

The shape is the one the prose sweep uses next door: enumerate the carriers of a
claim -- here every number in every description -- resolve each against the
built figure, and require anything unresolved to be named in a ledger with a
reason. The relational claims ("0.12 by epoch 6", "all twelve rise") get
checkers of their own, because a number that is right in isolation and attached
to the wrong curve is the defect this file exists for.
"""

import ast
import pathlib
import re
import sys
from contextlib import contextmanager

import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402

from conftest import SKILL                                   # noqa: E402

import check_figure as cf                                    # noqa: E402

ROOT = SKILL.parent
# Read as source, below, as well as imported: the descriptions are checked
# against the string literals the examples actually pass.
DEMO = ROOT / "examples" / "demo.py"
GALLERY = ROOT / "examples" / "gallery.py"
sys.path.insert(0, str(ROOT / "examples"))

import demo                                                  # noqa: E402
import gallery                                               # noqa: E402

TOL = 0.01          # how close a quoted value has to sit to the plotted one


# --- building the figures the descriptions belong to -------------------------
# Both examples are importable: the driver, the `sys.argv` read and the
# `sys.exit` sit under `if __name__ == "__main__"`, and the style sheet is
# scoped to the builders rather than applied at module scope. This file used to
# cut each source at a marker string and execute the prefix, because importing
# either one built every figure, rewrote the committed PNGs and then exited the
# interpreter.

@contextmanager
def _quiet_audit():
    """Build without auditing.

    The descriptions are what this file reads; the 20-odd gates behind
    `cf.report` are checked by their own tests, and running them here would be
    eight audits nothing looks at, printed to the test log.
    """
    original = cf.report
    cf.report = lambda fig, name, **kwargs: True
    try:
        yield
    finally:
        cf.report = original


def _demo():
    """The demo figure, described and not yet saved."""
    with _quiet_audit():
        fig, _passed = demo.build(out=None)
    alt = getattr(fig, cf.ALT_TEXT_ATTR, "")
    assert alt, "demo.py no longer describes its figure before saving it"
    return {"demo": (fig, " ".join(alt.split()))}


def _gallery():
    """Every gallery figure, keyed by the name `finish` gives it.

    `finish` audits and saves; here it only records, so the suite neither
    rewrites the committed PNGs nor pays for eleven audits it is not reading.
    """
    captured = {}
    original = gallery.finish

    def capture(fig, name, description, **_kwargs):
        captured[name] = (fig, " ".join(description.split()))
        return fig

    gallery.finish = capture
    try:
        for build in gallery.BUILDERS:
            build()
    finally:
        gallery.finish = original
    return captured


def figures():
    if not hasattr(figures, "cache"):
        built = _demo()
        built.update(_gallery())
        figures.cache = built
    return figures.cache


# --- the carriers ------------------------------------------------------------

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19, "twenty": 20}

# A number, and not a digit inside a name. `CIFAR-100`, `RK4` and `period-3`
# are words with numerals in them, and a sweep that reads them as claims spends
# its ledger excusing dataset names. Scientific notation is matched whole, so
# `1e-3.2` is one claim about a limit rather than a 1 and a -3.2.
SCIENTIFIC = r"\d+(?:\.\d+)?e-?\d+(?:\.\d+)?"
PLAIN = r"(?<![\w.-])-?\d+(?:\.\d+)?(?![\w])"
NUMBER = re.compile(f"{SCIENTIFIC}|{PLAIN}|" + r"\b(?:" + "|".join(WORDS)
                    + r")\b", re.I)


def _value(token):
    """The number a token states.

    `1e-3.2` is not a Python float literal -- the exponent is fractional -- and
    it is how a log axis's limit is written in a sentence. Read as mantissa and
    exponent rather than rejected, because the alternative is a limit claim
    nothing can check.
    """
    if token.lower() in WORDS:
        return float(WORDS[token.lower()])
    scientific = re.fullmatch(r"(\d+(?:\.\d+)?)e(-?\d+(?:\.\d+)?)", token,
                              re.I)
    if scientific:
        return float(scientific.group(1)) * 10 ** float(scientific.group(2))
    return float(token)


def _agrees(measured, stated):
    """Absolute for the values a reader reads off an axis, relative for the
    ones written as powers of ten: 1e-3.2 and 1e-3.3 are 0.0002 apart and are
    not the same claim."""
    return (abs(measured - stated) <= TOL
            or (stated != 0 and abs(measured - stated) / abs(stated) <= 0.01))


def numbers():
    """(figure, token) for every number any alt text states."""
    return sorted({(name, match.group(0))
                   for name, (_fig, alt) in figures().items()
                   for match in NUMBER.finditer(alt)})


# --- resolving one against the figure ----------------------------------------
# Narrow on purpose. "the number appears somewhere in the figure's data" agrees
# with almost anything on a plot of 300 samples, and a resolver that agrees with
# anything reports agreement with nothing.

def _data_axes(fig):
    return [ax for ax in fig.axes if ax.get_label() != "<colorbar>"]


def _structural_values(fig):
    """Quantities a figure states about itself: counts, limits, ticks."""
    axes = _data_axes(fig)
    values = {float(len(axes)), float(len(fig.axes))}
    for ax in fig.axes:
        values |= {float(v) for v in ax.get_xlim() + ax.get_ylim()}
        values |= {float(v) for v in ax.get_xticks()}
        values |= {float(v) for v in ax.get_yticks()}
        lines = [line for line in ax.lines if line.get_label()
                 and not line.get_label().startswith("_")]
        values |= {float(len(lines)), float(len(ax.collections)),
                   float(len(ax.images))}
        for line in ax.lines:
            data = line.get_ydata()
            if len(data):
                values |= {float(np.min(data)), float(np.max(data))}
            xdata = line.get_xdata()
            if len(xdata):
                values |= {float(np.min(xdata)), float(np.max(xdata))}
    return values


def resolves(fig, token):
    value = _value(token)
    return any(abs(value - candidate) <= TOL
               for candidate in _structural_values(fig))


# --- the relational claims, each executed ------------------------------------
# A number that is right about the figure and wrong about which curve it belongs
# to resolves structurally and is still false. These read the sentence.

def _curve(fig, label):
    for ax in _data_axes(fig):
        for line in ax.lines:
            if line.get_label() == label:
                return line
    for ax in _data_axes(fig):
        for text in ax.texts:
            if text.get_text() == label:
                raise AssertionError(
                    f"{label} is a direct label with no line of that name; "
                    "the demo labels its curves through `plot(label=...)` and "
                    "this lookup depends on it")
    raise AssertionError(f"no curve labelled {label!r} in the figure")


def _value_at(fig, label, x):
    line = _curve(fig, label)
    xs, ys = np.asarray(line.get_xdata()), np.asarray(line.get_ydata())
    return float(ys[int(np.argmin(np.abs(xs - x)))])


def check_demo_bayesian_at_6(fig):
    return _value_at(fig, "Bayesian", 6)


def check_demo_bayesian_at_12(fig):
    return _value_at(fig, "Bayesian", 12)


def check_demo_baseline_at_12(fig):
    return _value_at(fig, "Baseline", 12)


def _slope_pairs(fig):
    """(before, after) for panel (b) of the forms figure."""
    panel = _data_axes(fig)[1]
    marks = [line for line in panel.lines
             if line.get_linestyle() == "None" and len(line.get_xdata())]
    assert len(marks) == 2, (
        f"panel (b) draws {len(marks)} marker series, expected the before and "
        "after columns")
    return (np.asarray(marks[0].get_ydata()),
            np.asarray(marks[1].get_ydata()))


def check_forms_pairs_that_rise(fig):
    before, after = _slope_pairs(fig)
    return float((after > before).sum())


def check_forms_pair_count(fig):
    before, _after = _slope_pairs(fig)
    return float(before.size)


def _descent_path(fig):
    """The gradient-descent polyline of the field figure."""
    line = _curve(fig, "descent path")
    return np.column_stack([line.get_xdata(), line.get_ydata()])


def check_field_step_count(fig):
    """Steps, which is one fewer than the points: the start is not a step.

    The description said 28 for three releases. The loop runs 6000 times, and
    28 was neither the step count nor a count of anything else on the panel.
    """
    return float(len(_descent_path(fig)) - 1)


def check_field_start_x(fig):
    return float(_descent_path(fig)[0][0])


def check_field_start_y(fig):
    return float(_descent_path(fig)[0][1])


def check_field_end_x(fig):
    return float(_descent_path(fig)[-1][0])


def check_field_end_y(fig):
    return float(_descent_path(fig)[-1][1])


# "Drops into the curved valley" needs a criterion, and this is it: the floor
# of the Rosenbrock valley is the parabola y = x^2, so the path is in the
# valley once it is within this much of it. Written here rather than left
# implicit, because a claim measured against an unstated rule is unfalsifiable.
VALLEY_TOL = 0.05


def check_field_steps_to_valley(fig):
    path = _descent_path(fig)
    inside = np.abs(path[:, 1] - path[:, 0] ** 2) <= VALLEY_TOL
    assert inside.any(), "the descent path never reaches the valley floor"
    return float(np.argmax(inside))


def _fitted_slope(fig, label, half=slice(6, None)):
    """The observed order of a method, fitted on a log-log panel.

    Taken from the large-step end. At the small-step end round-off dominates
    truncation, which is the finding the panel's own comment records, and a fit
    over the whole range reports neither slope.
    """
    line = _curve(fig, label)
    xs = np.log10(np.asarray(line.get_xdata())[half])
    ys = np.log10(np.asarray(line.get_ydata())[half])
    return float(np.polyfit(xs, ys, 1)[0])


def check_convergence_euler_slope(fig):
    return _fitted_slope(fig, "forward Euler")


def check_convergence_heun_slope(fig):
    return _fitted_slope(fig, "Heun")


def check_convergence_rk4_slope(fig):
    return _fitted_slope(fig, "RK4")


def _step_sizes(fig):
    return np.asarray(_curve(fig, "forward Euler").get_xdata())


def check_convergence_smallest_step(fig):
    return float(_step_sizes(fig).min())


def check_convergence_largest_step(fig):
    return float(_step_sizes(fig).max())


def check_orbit_period_three_window(fig):
    """Where the widest period-3 window sits, found rather than assumed.

    The attractor is one dense mark cloud, so "a period-3 window" is a run of
    step sizes at which the plotted iterates collapse to three values. The
    widest such run above the chaos onset is the one the sentence names.
    """
    line = max((line for ax in _data_axes(fig) for line in ax.lines),
               key=lambda line: len(line.get_xdata()))
    x = np.asarray(line.get_xdata())
    y = np.asarray(line.get_ydata())
    rs = np.unique(x)
    branches = np.array([len(np.unique(np.round(y[x == r], 3))) for r in rs])
    chaotic = (branches == 3) & (rs > 3.5)

    best, run, start, span = (0, 0), 0, 0, (0, 0)
    for i, inside in enumerate(chaotic):
        run = run + 1 if inside else 0
        if inside and run > best[0]:
            start = i - run + 1
            best, span = (run, i), (start, i)
    assert best[0] > 2, "no period-3 window above the chaos onset"
    return float((rs[span[0]] + rs[span[1]]) / 2)


def check_schematic_stage_count(fig):
    """Boxes, which is what "a four-stage loop" counts."""
    from matplotlib.patches import FancyBboxPatch
    return float(sum(isinstance(patch, FancyBboxPatch)
                     for ax in _data_axes(fig) for patch in ax.patches))


def check_forms_group_size(fig):
    """Points per group in panel (a). Both groups are stated as 14."""
    panel = _data_axes(fig)[0]
    clouds = [line for line in panel.lines
              if line.get_linestyle() == "None" and len(line.get_xdata()) > 2]
    sizes = {len(line.get_xdata()) for line in clouds}
    assert len(sizes) == 1, f"panel (a) draws groups of {sorted(sizes)}"
    return float(sizes.pop())


def check_uncertainty_crossing(fig):
    """Where the two learning curves swap places.

    Read off the drawn samples rather than from the closed form they were
    generated with: the sentence is a claim about the picture, and a checker
    that re-evaluates the generator would agree with the picture even if the
    picture had been drawn from something else.
    """
    panel = _data_axes(fig)[0]
    lines = [line for line in panel.lines
             if line.get_label() and not line.get_label().startswith("_")]
    assert len(lines) == 2, f"expected two curves, found {len(lines)}"
    x = np.asarray(lines[0].get_xdata(), dtype=float)
    gap = (np.asarray(lines[0].get_ydata(), dtype=float)
           - np.asarray(lines[1].get_ydata(), dtype=float))
    sign = np.flatnonzero(np.sign(gap[:-1]) != np.sign(gap[1:]))
    assert len(sign) == 1, f"the curves cross {len(sign)} times, not once"
    i = int(sign[0])
    # Linear in log x, which is the axis the reader reads the crossing off.
    lo, hi = np.log(x[i]), np.log(x[i + 1])
    return float(np.exp(lo + (hi - lo) * gap[i] / (gap[i] - gap[i + 1])))


def _bars(fig):
    from matplotlib.patches import Rectangle
    panel = _data_axes(fig)[0]
    bars = [p for p in panel.patches if isinstance(p, Rectangle)]
    assert bars, "the panel draws no bars"
    return panel, bars


def check_counts_total(fig):
    """The population the shares are shares OF, summed off the bars."""
    _panel, bars = _bars(fig)
    return float(sum(bar.get_height() for bar in bars))


def check_counts_modal_height(fig):
    _panel, bars = _bars(fig)
    return float(max(bar.get_height() for bar in bars))


def _modal_bin_edges(fig):
    """The two numbers in the tick label of the tallest bar.

    This is the relational half: 268 being a bar height somewhere and 2.0-2.4
    being a bin somewhere would both pass on a figure where the peak is in a
    different bin, which is the sentence told wrong.
    """
    panel, bars = _bars(fig)
    tallest = max(bars, key=lambda bar: bar.get_height())
    centre = tallest.get_x() + tallest.get_width() / 2
    labels = {round(float(tick), 6): text.get_text()
              for tick, text in zip(panel.get_xticks(),
                                    panel.get_xticklabels())}
    label = labels[round(centre, 6)]
    edges = re.findall(r"\d+(?:\.\d+)?", label)
    assert len(edges) == 2, f"the modal bin is labelled {label!r}"
    return [float(edge) for edge in edges]


def check_counts_modal_bin_low(fig):
    return _modal_bin_edges(fig)[0]


def check_counts_modal_bin_high(fig):
    return _modal_bin_edges(fig)[1]


def check_density_scatter_points(fig):
    """Marks in panel (a), across both genotypes."""
    panel = _data_axes(fig)[0]
    return float(sum(len(coll.get_offsets()) for coll in panel.collections))


def check_density_binned_points(fig):
    """Cells in panel (b), summed out of the hexbin's own counts rather than
    from the draw. The bins are what the panel shows, so they are what the
    number has to come from."""
    panel = _data_axes(fig)[1]
    assert len(panel.collections) == 1, "panel (b) is not one binned artist"
    return float(np.asarray(panel.collections[0].get_array()).sum())


# What each checked number is a claim about. The value the checker returns has
# to be the number the sentence states.
def check_secondary_scale_top_limit_mm(fig):
    """The millimetre axis's upper end, read off the child axes that carries it.

    A secondary axis is added through `add_child_axes` and never reaches
    `fig.axes`, so the figure's own axes list cannot answer this: the number has
    to come from the axes the reader is actually reading.

    Drawn first, because a secondary axis holds the default 0..1 until a draw
    runs its forward function over the parent's limits. Reading it undrawn
    measures matplotlib's placeholder rather than the figure's millimetres.
    """
    fig.canvas.draw()
    panel = _data_axes(fig)[0]
    children = list(getattr(panel, "child_axes", []) or [])
    assert len(children) == 1, f"expected one secondary axis, got {children}"
    return float(children[0].get_xlim()[1])


def check_raster_stimulus_rules(fig):
    """The two rules marking the stimulus window, counted as drawn.

    A count of rules and not of anything else: the raster's spikes are an
    `EventCollection` and the only `Line2D`s on the panel are the two edges.
    """
    panel = _data_axes(fig)[0]
    return float(len([line for line in panel.lines if line.get_visible()]))


def check_rose_bin_count(fig):
    """Bins, counted off the bars the rose actually drew."""
    from matplotlib.patches import Rectangle
    panel = _data_axes(fig)[0]
    bars = [p for p in panel.patches if isinstance(p, Rectangle)]
    assert bars, "the rose draws no bars"
    return float(len(bars))


def check_rose_bin_width_degrees(fig):
    """The width of one bin, in degrees, off the bar rather than off the
    arithmetic. `16 bins of 22.5 degrees` is two claims and they have to agree
    with each other as well as with the figure."""
    import math
    from matplotlib.patches import Rectangle
    panel = _data_axes(fig)[0]
    bars = [p for p in panel.patches if isinstance(p, Rectangle)]
    widths = {round(math.degrees(bar.get_width()), 6) for bar in bars}
    assert len(widths) == 1, f"the bins are not one width: {sorted(widths)}"
    return widths.pop()


def check_parity_marks(fig):
    """Compounds, as marks. One scatter, one mark per compound."""
    panel = _data_axes(fig)[0]
    return float(sum(len(coll.get_offsets()) for coll in panel.collections))


CHECKED = {
    ("gallery-raster", "Two"): check_raster_stimulus_rules,
    ("gallery-rose", "16"): check_rose_bin_count,
    ("gallery-rose", "22.5"): check_rose_bin_width_degrees,
    ("gallery-parity", "84"): check_parity_marks,
    ("demo", "0.12"): check_demo_bayesian_at_6,
    ("demo", "0.02"): check_demo_bayesian_at_12,
    ("demo", "0.25"): check_demo_baseline_at_12,
    ("gallery-forms", "twelve"): check_forms_pairs_that_rise,
    ("gallery-forms", "Twelve"): check_forms_pair_count,
    ("gallery-forms", "14"): check_forms_group_size,
    ("gallery-field", "6000"): check_field_step_count,
    ("gallery-field", "-1.75"): check_field_start_x,
    ("gallery-field", "2.15"): check_field_start_y,
    ("gallery-field", "0.93"): check_field_end_x,
    ("gallery-field", "0.86"): check_field_end_y,
    ("gallery-field", "two"): check_field_steps_to_valley,
    ("gallery-convergence", "1"): check_convergence_euler_slope,
    ("gallery-convergence", "2"): check_convergence_heun_slope,
    ("gallery-convergence", "4"): check_convergence_rk4_slope,
    ("gallery-convergence", "1e-3.2"): check_convergence_smallest_step,
    ("gallery-convergence", "1e-0.6"): check_convergence_largest_step,
    ("gallery-schematic", "four"): check_schematic_stage_count,
    ("gallery-orbit", "3.83"): check_orbit_period_three_window,
    ("gallery-uncertainty", "40"): check_uncertainty_crossing,
    ("gallery-counts", "812"): check_counts_total,
    ("gallery-counts", "268"): check_counts_modal_height,
    ("gallery-counts", "2.0"): check_counts_modal_bin_low,
    ("gallery-counts", "2.4"): check_counts_modal_bin_high,
    ("gallery-density", "110"): check_density_scatter_points,
    ("gallery-density", "40000"): check_density_binned_points,
    ("gallery-secondary-scale", "305"): check_secondary_scale_top_limit_mm,
}

# Numbers no resolver places, each with the reason. Anything here is a claim
# nothing checks, so the set is meant to stay small and boring.
UNCHECKED = {
    ("gallery-encoding", "3"): "the exponent in z^3 - 1, part of the "
                               "function's name rather than a measurement",
    ("gallery-encoding", "2"): "the exponent in (z^2 - 1)/(z^2 + i/2), the "
                               "same",
    ("gallery-orbit", "3"): "the period-3 window of the logistic map, named "
                            "as a feature of the system",
    ("gallery-field", "1"): "the contour level the label points at, drawn by "
                            "`contour` rather than set as a limit",
}


@pytest.mark.parametrize("figure,token", numbers())
def test_every_number_in_an_alt_text_is_accounted_for(figure, token):
    """A number in a description is a claim about the picture.

    `eleven of twelve rise` is what this catches: eleven is not a count the
    figure produces, so it resolves against nothing and has to be either
    checked or excused in writing.
    """
    if (figure, token) in CHECKED or (figure, token) in UNCHECKED:
        return
    fig, alt = figures()[figure]
    assert resolves(fig, token), (
        f"{figure} says {token!r} in its alt text, and the figure has no "
        f"count, limit, tick or extreme of that value. Either the number is "
        f"wrong, or it belongs in CHECKED with the computation that confirms "
        f"it, or in UNCHECKED with the reason nothing can.\n  {alt}")


@pytest.mark.parametrize("figure,token", sorted(CHECKED))
def test_a_checked_number_is_the_one_the_figure_produces(figure, token):
    fig, alt = figures()[figure]
    measured = CHECKED[(figure, token)](fig)
    assert _agrees(measured, _value(token)), (
        f"{figure} states {token!r}; the figure measures {measured:g}.\n"
        f"  {alt}")


def test_the_sweep_reads_every_described_figure():
    """Every assertion above is parametrized over the built figures. A capture
    that came back short would not fail them, it would delete them."""
    built = figures()
    assert len(built) == 20, (
        f"built {sorted(built)}, expected the demo and nineteen gallery figures")
    assert all(alt for _fig, alt in built.values()), (
        "a figure was built with no description attached")


def test_the_ledgers_name_numbers_that_are_still_written():
    written = set(numbers())
    stale = sorted((set(CHECKED) | set(UNCHECKED)) - written)
    assert not stale, (
        f"{stale} are in a ledger but no alt text states them any more")


def test_the_resolver_rejects_a_count_the_figure_does_not_have():
    """The house rule is that a gate is tested for its ability to fail, and
    this one runs against descriptions that are correct.

    Eleven is the number the slope graph carried for two releases. It has to
    resolve against nothing, or the sweep would have passed it too.
    """
    fig, _alt = figures()["gallery-forms"]
    assert not resolves(fig, "eleven"), (
        "the forms figure now has an eleven somewhere structural, so the "
        "sweep would no longer catch the sentence it was written for")
    assert resolves(fig, "three"), (
        "three panels is the one count that figure certainly has, so a "
        "resolver that rejects it is rejecting everything")


def test_the_relational_checkers_read_the_curve_they_name():
    """`0.12 by epoch 6` was `0.05 by epoch 6` and structurally plausible: the
    y axis runs through 0.05. What makes it false is the curve it names, so
    the checker is held to reading that curve rather than the axis."""
    fig, _alt = figures()["demo"]
    assert abs(check_demo_bayesian_at_6(fig)
               - check_demo_baseline_at_12(fig)) > TOL, (
        "the two curves the demo's sentence contrasts now read the same "
        "value, so the checkers cannot tell which one they are on")
    with pytest.raises(AssertionError):
        _curve(fig, "Nonexistent")


def test_the_examples_still_describe_the_figures_this_file_reads():
    """The descriptions are read out of built figures here and out of the AST
    in `test_docs_match_code.py`. Two readings of the same strings, and if they
    ever disagree it is this file that is executing something the site does not
    show."""
    literals = []
    for path in (DEMO, GALLERY):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
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
                literals.append(" ".join(value.split()))
    built = {alt for _fig, alt in figures().values()}
    assert built == set(literals), (
        "the descriptions attached to the built figures are not the string "
        "literals the examples pass:\n"
        f"  built and not written: {sorted(built - set(literals))}\n"
        f"  written and not built: {sorted(set(literals) - built)}")


@pytest.fixture(autouse=True, scope="module")
def _close_figures():
    yield
    plt.close("all")


def _unused():
    """`pathlib` is imported for the module docstring's paths in failures."""
    return pathlib.Path(__file__)
