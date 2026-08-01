"""Seven figures hard enough to be worth checking.

    python examples/gallery.py [output-directory]

`demo.py` is the method in miniature: one panel, three curves, every rule
visible at once. It is also easy for a gate to pass, which is the wrong thing
for a gate to be good at. This file is the other half of the evidence — the
compositions where the checks have somewhere to hide:

    gallery-small-multiples.png   shared scales, panel letters, per-panel color
    gallery-field.png             a filled field, isolines, a colorbar
    gallery-schematic.png         boxes and arrows, no axes at all
    gallery-forms.png             the three forms `choosing-a-form.md` argues for
    gallery-convergence.png       log-log error against h, with a slope triangle
    gallery-orbit.png             a dense attractor, where density IS the finding
    gallery-encoding.png          three colormap kinds, one per panel

Each one is audited and the script exits non-zero if any figure fails, so these
are regression tests with pictures attached rather than decoration.

Importing this file builds nothing. The seven builders are importable and each
returns its figure, so a change to a gate can be measured against the corpus:

    import gallery
    gallery.OUT = None                  # build, audit, write nothing
    fig = gallery.field()

That is the point of the corpus, and it used to be the one thing this file made
hard. Importing it ran every builder, overwrote all seven committed PNGs, read
`sys.argv[1]` as an output directory, put the style sheet into the importing
process for good, and then called `sys.exit`.

Writing them
found six defects in the checks themselves, and the comments below say which:
the readability gate reported a schematic's invisible tick labels, `check_ink`
called every colorbar a saturated panel, the line-weight gate measured a
colorbar's own dividers, a path and its start marker in one hue read as a
wrapped color cycle, testing a label's backdrop against its dominant color
failed every annotation ever placed on a heatmap, and `check_label_attribution`
was passing nearly everything it was given.

Two more defects were in the FIGURES and no gate caught either: the schematic's
feedback loop ran off the bottom of the canvas, and the convergence plot's slope
triangle sat in the only corner its direct labels could use. Both were obvious
in the PNG and invisible to every check. That is step 7 of the procedure, and it
is why the procedure has a step 7.
"""

from pathlib import Path
import functools
import sys

import matplotlib
import numpy as np

matplotlib.use("agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "skill"
sys.path.insert(0, str(SKILL / "scripts"))

import check_figure as cf          # noqa: E402

STYLE = SKILL / "assets" / "figure.mplstyle"

# Where `finish` writes. Same optional argument as `demo.py`, and for the same
# reason: the test that runs this file used to rewrite all seven committed PNGs
# on every `pytest`. Resolved in `main` rather than from `sys.argv` at import,
# because under a test runner `sys.argv[1]` is the runner's own argument and
# this file would take it for an output directory.
OUT = HERE

# Read under the sheet, not with it left in effect. `plt.style.use` at module
# scope put the sheet into every process that imported this file, and
# `check_style_sheet` -- whose whole job is noticing the sheet is NOT in effect
# -- stopped being able to fail in that process. See `styled`.
with plt.style.context(str(STYLE)):
    SERIES = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    SURFACE = plt.rcParams["axes.facecolor"]
INK = "#000000"
MUTED = "#777570"

results: list[tuple[str, bool]] = []


def styled(build):
    """Run one builder with the skill's sheet in effect, and only then.

    The sheet has to be live while the figure is constructed, and it has to be
    live through `finish`, because `check_style_sheet` compares the rcParams
    that are in effect against the sheet on disk. Both happen inside the
    builder, so wrapping the builder covers both and leaves the import inert.
    """
    @functools.wraps(build)
    def run(*args, **kwargs):
        with plt.style.context(str(STYLE)):
            return build(*args, **kwargs)
    return run


def finish(fig, name, description, **audit_kw):
    """Describe, audit, save. In that order, on purpose — `describe` before
    `audit` because the alt-text row is part of what is being checked, and
    `audit` before `savefig` because a figure that fails should still be
    written out so you can look at what failed.

    Returns the figure, and with `OUT` set to None writes nothing and leaves it
    open. That is the mode for measuring a change against this corpus: the
    seven figures are the evidence a gate is checked against, and getting at
    them used to mean either rewriting the committed PNGs or not getting at
    them at all.
    """
    cf.describe(fig, description)
    ok = cf.report(fig, name, **audit_kw)
    results.append((name, ok))
    if OUT is None:
        return fig
    out = OUT / f"{name}.png"
    # `alt_metadata` takes the path so it can pick a key the format has. PNG
    # takes `Description`; PDF's info dictionary does not have one, and asking
    # for it there makes matplotlib warn on every save.
    fig.savefig(out, metadata=cf.alt_metadata(fig, out))
    plt.close(fig)
    return fig


# --- 1. small multiples ------------------------------------------------------
# Four panels, one shared pair of scales. The composition rule is that panels
# sharing a scale share their axis furniture, and the gate that enforces it
# (`check_redundancy`) is the reason this is a `subplots(..., sharex, sharey)`
# rather than four independently labelled axes.

@styled
def small_multiples():
    rng = np.random.default_rng(11)
    epochs = np.arange(1, 41)
    datasets = ("CIFAR-10", "CIFAR-100", "SVHN", "Tiny-ImageNet")
    floors = (0.08, 0.31, 0.05, 0.44)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), sharex=True,
                             sharey=True, constrained_layout=True)

    for k, (ax, name, floor) in enumerate(zip(axes.flat, datasets, floors)):
        for j, (color, rate, label) in enumerate(
                zip(SERIES[:2], (0.09, 0.16), ("SGD", "Adam"))):
            y = floor + (1.0 - floor) * np.exp(-rate * epochs)
            y = y + 0.012 * rng.standard_normal(epochs.size)
            ax.plot(epochs, y, color=color, label=label)
            # Direct labels once, in the first panel only. Repeating them in
            # all four would be the identity restated three times it was not
            # needed; putting them in a legend would leave the reader matching
            # a faint swatch to a faint curve, which is the thing the guide
            # spends most of its color section arguing against.
            #
            # ALIGNMENT: these curves fall, so clear ground above one runs to
            # the RIGHT of the anchor and clear ground below runs to the LEFT.
            # `ha="center"` puts both ends of the box back down on the line.
            if k == 0:
                side = 1 if j == 0 else -1
                at, span = 14, 9
                lo, hi = ((at, at + span) if side > 0 else (at - span, at))
                w = (epochs >= lo) & (epochs <= hi)
                y_at = y[w].max() if side > 0 else y[w].min()
                ax.annotate(label, (at, y_at), textcoords="offset points",
                            xytext=(0, 6 * side),
                            ha="left" if side > 0 else "right",
                            va="bottom" if side > 0 else "top", color=INK)
        # The panel letter register. `(a)` in the title slot rather than a
        # free-floating text call, so constrained_layout reserves room for it
        # and the type-size gate measures it like any other string.
        ax.set_title(f"({'abcd'[k]}) {name}", loc="left")

    # One label per shared scale, not one per panel: the sharing runs along the
    # axis the panels are stacked on, and repeating it four times is the exact
    # redundancy the gate names.
    fig.supxlabel("Training epoch")
    fig.supylabel("Validation loss")

    return finish(fig, "gallery-small-multiples",
           "Validation loss against training epoch on four datasets, SGD "
           "against Adam. Adam falls faster on all four and reaches a lower "
           "floor on CIFAR-10 and SVHN; on CIFAR-100 and Tiny-ImageNet the two "
           "converge to the same floor and only the speed differs.")


# --- 2. a filled field with isolines and a colorbar --------------------------
# The case that broke `check_ink` and taught it about context surfaces: a
# contourf backdrop covers the whole panel, so measured as data ink it reads
# 100% and every such figure stood at WARN. `context_axes` says the fill is
# ground rather than figure, and the ink fraction is measured off what sits on
# top of it.

@styled
def field():
    gx, gy = np.meshgrid(np.linspace(-2.2, 2.2, 400),
                         np.linspace(-1.6, 2.4, 400))
    # Rosenbrock, on a log scale so the valley is visible rather than a single
    # black hairline against a saturated everything-else.
    z = np.log10(1.0 + (1 - gx) ** 2 + 60 * (gy - gx ** 2) ** 2)

    fig, ax = plt.subplots(figsize=(6.4, 4.4), constrained_layout=True)
    fill = ax.contourf(gx, gy, z, levels=24, cmap="viridis")
    # Isolines over the fill: structure on the context surface, not a fourth
    # series, so they take the surface color rather than a palette slot. The
    # guide's rule is that a context surface gets structure and not just a hue
    # — an unstructured gradient gives the eye no edge to hold.
    #
    # Six levels, not the sixteen this started with. Isoline density is a
    # legibility budget and the labels are spending from the same one: at
    # sixteen there was no band anywhere in the panel wide enough to set a word
    # in, which the readability check reported as 41% of 'start' sitting on
    # other ink. Thinning the isolines is what bought the clear ground.
    ax.contour(gx, gy, z, levels=6, colors=SURFACE, linewidths=1.0,
               alpha=1.0, linestyles="solid")

    # A descent path over the field. Drawn as a path because these points ARE
    # ordered — the encoding asserts a sequence and the sequence exists.
    # f = (1 - x)^2 + 60(y - x^2)^2, so the step is the true gradient rather
    # than a plausible-looking one: a figure that illustrates gradient descent
    # and descends along something else is a diagram of nothing.
    p = np.array([[-1.75, 2.15]])
    for _ in range(6000):
        x0, y0 = p[-1]
        grad = np.array([-2 * (1 - x0) - 240 * x0 * (y0 - x0 ** 2),
                         120 * (y0 - x0 ** 2)])
        p = np.vstack([p, p[-1] - 0.0009 * grad])
    ax.plot(p[:, 0], p[:, 1], color=SERIES[4], lw=1.8, zorder=3,
            solid_capstyle="round", label="descent path")
    ax.plot(*p[0], marker="o", color=SERIES[4], ms=5, zorder=4, linestyle="none",
            label="start")
    ax.plot(1.0, 1.0, marker="*", color=SURFACE, ms=11, zorder=4,
            linestyle="none", markeredgecolor=INK, markeredgewidth=0.8,
            label="optimum")

    # THE ONE FIGURE HERE THAT DOES NOT GET DIRECT LABELS, and the exception is
    # the interesting part. Direct labels beat a legend everywhere else in this
    # repo. On a field they need clear ground, and this field has none: a scan
    # of every position in the panel found flat, dark-enough ground only in the
    # valley basin, nowhere near either point being named. Casing does not
    # rescue it either — over a field a halo does not sit behind the label, it
    # deletes the field under the label.
    #
    # So the labels come off the field and onto the page, where the surface is
    # uniform by construction. `check_identity_channel` is satisfied without
    # color doing the work alone, because the three handles are a line, a dot
    # and a star.
    fig.legend(loc="outside lower center", ncols=3, frameon=False)

    ax.set_xlabel("$x_1$")
    ax.set_ylabel("$x_2$")
    # contourf fills exactly the sampled rectangle; without this matplotlib
    # pads the view and the figure ships with a bare strip of page along two
    # edges of what reads as a continuous field.
    ax.set_xlim(gx.min(), gx.max())
    ax.set_ylim(gy.min(), gy.max())
    bar = fig.colorbar(fill, ax=ax, pad=0.02)
    bar.set_label(r"$\log_{10}(1 + f)$")
    # The colorbar's own outline is furniture; matplotlib draws it in the
    # foreground color, which on this sheet is the axis rule already.
    bar.outline.set_linewidth(0.0)

    return finish(fig, "gallery-field",
           "Rosenbrock function on a log scale as a filled viridis field with "
           "isolines, and a 6000-step gradient descent path from "
           "(-1.75, 2.15). The path drops into the curved valley within two "
           "steps and then crawls along it, ending at (0.93, 0.86), still "
           "short of the optimum at (1, 1).",
           context_axes=[ax])


# --- 3. a schematic with no axes ---------------------------------------------
# The figure the checker understands least and the reader understands fastest.
# Nothing here is data, so most gates have nothing to say — which is the point
# of including it. What still applies is type size, clipping, readability, and
# whether the ink is legible; those are the ones that break schematics in
# practice, and they are exactly the ones that survive `ax.axis("off")`.

@styled
def schematic():
    fig, ax = plt.subplots(figsize=(7.2, 2.6), constrained_layout=True)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 34)
    ax.axis("off")

    stages = [("Candidate\npool", 6), ("Surrogate\nmodel", 29),
              ("Acquisition", 52), ("Wet lab", 75)]
    W, H, Y = 19, 13, 11

    for label, x in stages:
        # White fill, colored rule, ink text. A colored FILL would put the text
        # on a surface it has to clear 4.5:1 against, and only two slots in the
        # palette manage that with black text — so the identity rides on the
        # edge, where the 3:1 mark threshold applies and the whole palette
        # qualifies.
        ax.add_patch(FancyBboxPatch(
            (x, Y), W, H, boxstyle="round,pad=0,rounding_size=1.2",
            linewidth=1.0, edgecolor=SERIES[0], facecolor=SURFACE))
        ax.text(x + W / 2, Y + H / 2, label, ha="center", va="center",
                color=INK, linespacing=1.35)

    for _, x in stages[:-1]:
        ax.annotate("", xy=(x + W + 5.2, Y + H / 2), xytext=(x + W + 1.0,
                                                             Y + H / 2),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0,
                                    shrinkA=0, shrinkB=0))

    # The feedback edge is the whole point of the diagram, so it gets the
    # second slot and a weight the forward arrows do not have. It is drawn
    # solid: dashing means unobserved, projected or threshold, and this loop is
    # none of those — it is the measured labels going back into the model.
    # Drawn as an explicit three-segment path rather than with
    # `connectionstyle="bar"`. The bar's drop is a FRACTION of the span between
    # the two ends, so on a wide loop it reached fifteen units below an axes
    # that stops at zero and the figure shipped with two vertical stubs running
    # off the bottom edge and no loop between them. Nothing gates that — the
    # stubs are inside the canvas, so the clipping check is satisfied — which
    # is what step 7 of the procedure is for.
    LOOP_Y = 5.0
    ax.plot([75 + W / 2, 75 + W / 2, 29 + W / 2],
            [Y, LOOP_Y, LOOP_Y], color=SERIES[1], lw=1.4,
            solid_joinstyle="miter", zorder=1)
    ax.annotate("", xy=(29 + W / 2, Y), xytext=(29 + W / 2, LOOP_Y),
                arrowprops=dict(arrowstyle="-|>", color=SERIES[1], lw=1.4,
                                shrinkA=0, shrinkB=0))
    ax.text((29 + 75) / 2 + W / 2, LOOP_Y - 1.4,
            "measured labels retrain the surrogate",
            ha="center", va="top", color=INK)

    return finish(fig, "gallery-schematic",
           "A four-stage active learning loop: a candidate pool feeds a "
           "surrogate model, an acquisition function ranks its predictions, "
           "and the top candidates go to the wet lab. Measured labels return "
           "from the wet lab to retrain the surrogate.")


# --- 4. three forms in one figure --------------------------------------------
# Three panels that deliberately do NOT share a scale, so the redundancy gate
# has to tell "repeated furniture" apart from "three different measurements".
# Each panel is a form `choosing-a-form.md` argues for against a more obvious
# alternative, and the caption of each names the alternative it beats.

@styled
def forms():
    rng = np.random.default_rng(4)
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.6, 2.9),
                                  constrained_layout=True)

    # (a) Every point, because n is small. A box plot here would hide both n
    # and the bimodality in the second group, and both are the finding.
    groups = ("Control", "Treated")
    samples = [rng.normal(0.42, 0.06, 14),
               np.concatenate([rng.normal(0.38, 0.04, 7),
                               rng.normal(0.71, 0.04, 7)])]
    for i, (_name, vals) in enumerate(zip(groups, samples)):
        jitter = rng.uniform(-0.09, 0.09, vals.size)
        a.plot(np.full(vals.size, i) + jitter, vals, linestyle="none",
               marker="o", ms=4.5, color=SERIES[i], alpha=1.0)
        a.plot([i - 0.19, i + 0.19], [vals.mean()] * 2, color=INK, lw=1.4)
    a.set_xticks(range(len(groups)), groups)
    a.set_xlim(-0.5, 1.5)
    a.set_ylabel("Binding fraction")
    a.set_title("(a) every point", loc="left")

    # (b) Paired measurements as a slope graph. Two bars would throw the
    # pairing away, and the pairing is what the panel is about: every one of
    # the twelve individuals rises, and the spread they start from is wider
    # than the change itself, neither of which survives a pair of means.
    # The comment here said eleven of twelve for two releases. The draw has
    # never produced a fall: `after` adds a normal centred at 0.11 with a
    # spread of 0.05, so a drop needs a draw 2.2 sigma low, and under this
    # seed the smallest gain is 0.047. `test_alt_text_numbers.py` now counts.
    before = rng.uniform(0.22, 0.68, 12)
    after = before + rng.normal(0.11, 0.05, 12)
    for lo, hi in zip(before, after):
        b.plot([0, 1], [lo, hi], color=MUTED, lw=1.0, zorder=1)
    b.plot(np.zeros(12), before, linestyle="none", marker="o", ms=4,
           color=SERIES[0], zorder=2)
    b.plot(np.ones(12), after, linestyle="none", marker="o", ms=4,
           color=SERIES[1], zorder=2)
    b.set_xticks([0, 1], ["Before", "After"])
    b.set_xlim(-0.35, 1.35)
    b.set_title("(b) pairing kept", loc="left")

    # (c) A reliability diagram against the diagonal. The diagonal is the
    # reference, so it wears an ink token rather than a series slot — a
    # reference line is not a third condition.
    edges = np.linspace(0, 1, 11)
    mid = (edges[:-1] + edges[1:]) / 2
    observed = np.clip(mid ** 1.45 + rng.normal(0, 0.02, mid.size), 0, 1)
    c.plot([0, 1], [0, 1], color=MUTED, lw=1.0, zorder=1)
    c.plot(mid, observed, marker="o", ms=4, color=SERIES[2], zorder=2)
    c.set_xlabel("Predicted")
    c.set_ylabel("Observed")
    c.set_xlim(0, 1)
    c.set_ylim(0, 1)
    c.set_aspect("equal")
    c.set_title("(c) against the ideal", loc="left")

    return finish(fig, "gallery-forms",
           "Three panels. (a) Binding fraction for 14 controls and 14 treated "
           "samples, every point shown: the treated group is bimodal, which a "
           "box plot would hide. (b) Twelve paired before-and-after "
           "measurements as a slope graph: all twelve rise. (c) A "
           "reliability diagram: observed frequency sits below the diagonal "
           "across the whole range, so the model is overconfident.")


# --- 5. the convergence plot -------------------------------------------------
# The characteristic figure of numerical analysis, and the one with the most
# convention attached to it: error against step size on log-log axes, with a
# slope triangle stating the observed order. The convention exists because the
# reader's question is not "how big is the error" but "what power of h is it",
# and on log-log a power law is a straight line whose SLOPE is the answer. Every
# rule below follows from that one fact.

@styled
def convergence():
    h = np.logspace(-3.2, -0.6, 12)
    methods = (("forward Euler", 1, 0.55),
               ("Heun", 2, 0.40),
               ("RK4", 4, 0.30))

    fig, ax = plt.subplots(figsize=(5.4, 4.2), constrained_layout=True)
    for (name, order, c), color in zip(methods, SERIES):
        # Round-off floor added on purpose: a convergence plot that descends
        # forever is a plot of the model, not of the computation. RK4 hits
        # double-precision noise at the left edge, which is the finding a real
        # study reports and the reason the fitted slope is taken from the
        # asymptotic middle rather than from the whole range.
        err = c * h ** order + 2e-16 / h
        ax.loglog(h, err, marker="o", ms=3.5, color=color, label=name)
        # Labelled at the LEFT, not at the right end past the last marker,
        # which is where this started. Out in the right margin the three labels
        # sat 29px from their own curve and 35px from a neighbour's, and
        # `check_label_attribution` failed all three: a label outside the data
        # is not resolved by proximity to anything. On a log-log fan the curves
        # are three decades apart at small h and the labels are unambiguous
        # there.
        #
        # ALIGNMENT: these curves rise left to right, so clear ground above one
        # runs to the LEFT of the anchor. Anchored on the highest sample across
        # the label's own span, so the box clears the round-off wobble too.
        at = 4
        window = slice(max(at - 3, 0), at + 1)
        ax.annotate(name, (h[at], err[window].max()),
                    textcoords="offset points", xytext=(0, 6),
                    ha="right", va="bottom", color=INK)

    # The slope triangle. It is a *statement of the observed order*, so it is
    # drawn against the fitted slope rather than the theoretical one, and it
    # sits on clear ground rather than on the curve it describes.
    # Bottom right, under RK4. It started in the upper left, which is also the
    # only clear ground for the direct labels — two things competing for one
    # empty corner, and the collision check said so.
    x0, x1 = 3.0e-2, 1.0e-1
    y0 = 1.0e-10
    y1 = y0 * (x1 / x0) ** 2
    ax.plot([x0, x1, x1, x0], [y0, y0, y1, y0], color=MUTED, lw=1.0)
    ax.annotate("2", ((x0 * x1) ** 0.5, y0), textcoords="offset points",
                xytext=(0, -9), ha="center", va="top", color=INK)

    ax.set_xlabel("Step size $h$")
    ax.set_ylabel(r"$\max_n |y_n - y(t_n)|$")
    # No equal aspect. One decade of x is not one decade of y here and cannot
    # be: the errors span twelve decades and the step sizes three, so forcing
    # it would produce a sliver four times taller than it is wide. This is
    # exactly why the slope triangle is drawn rather than left to the reader —
    # it states the reference slope IN THE PANEL'S OWN distorted space, where a
    # protractor would be useless and a comparison against the triangle is not.
    ax.set_xlim(h[0] / 1.6, h[-1] * 1.6)

    return finish(fig, "gallery-convergence",
           "Maximum global error against step size for forward Euler, Heun and "
           "RK4 on log-log axes, over step sizes from 1e-3.2 to 1e-0.6. Each "
           "method is a straight line of slope 1, 2 and 4 respectively; a slope "
           "triangle marks slope 2 for reference. RK4 flattens at the smallest "
           "step sizes, where double-precision round-off dominates truncation.")


# --- 6. a dense orbit diagram ------------------------------------------------
# The case where overplotting is the message rather than a defect: a bifurcation
# diagram IS a density plot, and the black mass in the chaotic regime is the
# finding. The gate warns, correctly, and the warning is one to read and accept
# — which is the whole reason the context-dependent checks warn instead of
# failing. A gate everyone learns to ignore is worse than no gate.

@styled
def orbit():
    rs = np.linspace(2.5, 4.0, 1400)
    keep, burn = 120, 400
    x = np.full(rs.size, 0.4)
    for _ in range(burn):
        x = rs * x * (1 - x)
    xs = np.empty((keep, rs.size))
    for k in range(keep):
        x = rs * x * (1 - x)
        xs[k] = x

    fig, ax = plt.subplots(figsize=(6.8, 4.0), constrained_layout=True)
    # One mark, one opacity, one hue: this is a single object seen at density,
    # not several series. Ink rather than a palette slot for the same reason —
    # nothing here carries a categorical identity.
    ax.plot(np.repeat(rs, keep), xs.T.ravel(), linestyle="none", marker=",",
            color=INK, alpha=0.35, rasterized=True)

    # The two structural facts a reader wants marked, on clear ground above the
    # attractor rather than inside it.
    for r, _name in ((3.0, "period doubles"), (3.5699, "chaos onset")):
        ax.axvline(r, color=MUTED, lw=1.0, zorder=1)
    ax.annotate("first doubling\n$r = 3$", (3.0, 0.06), textcoords="offset points",
                xytext=(-6, 0), ha="right", va="bottom", color=INK)
    ax.annotate("onset of chaos\n$r \\approx 3.57$", (3.5699, 0.06),
                textcoords="offset points", xytext=(-6, 0), ha="right",
                va="bottom", color=INK)

    ax.set_xlabel("$r$")
    ax.set_ylabel("attractor of $x \\mapsto rx(1-x)$")
    ax.set_xlim(rs[0], rs[-1])
    ax.set_ylim(0, 1)
    ax.grid(False)

    return finish(fig, "gallery-orbit",
           "Orbit diagram of the logistic map for r from 2.5 to 4. A single "
           "fixed point splits at r = 3, doubles repeatedly at an accelerating "
           "rate, and dissolves into a dense chaotic band at r about 3.57, with "
           "windows of periodic behaviour inside it — the widest a period-3 "
           "window near r = 3.83.")


# --- 7. three encodings, three colormap kinds --------------------------------

@styled
def encoding():
    UNMEASURED = "#d9d7d2"
    from matplotlib.patches import Patch

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.9, 3.1),
                                  constrained_layout=True)

    # (a) escape time -- a quantity, so a sequential ramp.
    n = 400
    budget = 60
    ax_x = np.linspace(-2.05, 0.65, n)
    ax_y = np.linspace(-1.25, 1.25, n)
    cc = ax_x[None, :] + 1j * ax_y[:, None]
    z = np.zeros_like(cc)
    escape = np.full(cc.shape, np.nan)
    for k in range(budget):
        z = z * z + cc
        out = np.abs(z) > 2.0
        escape[out & np.isnan(escape)] = k
        z[out] = 2.0
    ramp = plt.get_cmap("viridis").with_extremes(bad=UNMEASURED)
    escaped = a.imshow(np.ma.masked_invalid(escape), cmap=ramp, origin="lower",
                       extent=(ax_x[0], ax_x[-1], ax_y[0], ax_y[-1]),
                       interpolation="nearest", aspect="auto")
    a.set_title("(a) quantity: sequential", loc="left")
    a.set_xlabel(r"$\Re c$")
    a.set_ylabel(r"$\Im c$")
    # A ramp without a scale is a picture of a quantity nobody can read back.
    # The neutral is NOT on this bar and cannot be: the bar is the range that
    # was measured, and "did not escape" is outside it. That is the whole point
    # the panel exists to make, so it takes a key of its own rather than a
    # silently unexplained grey.
    bar_a = fig.colorbar(escaped, ax=a, pad=0.02)
    bar_a.set_label("escape iterations")
    bar_a.outline.set_linewidth(0.0)
    a.legend(handles=[Patch(facecolor=UNMEASURED, edgecolor="none",
                            label="did not escape")],
             loc="upper center", bbox_to_anchor=(0.5, -0.25), frameon=False,
             handlelength=1.1, borderpad=0.0, borderaxespad=0.0)

    # (b) Newton basins -- a category, so separated hues and no ramp at all.
    bx = np.linspace(-1.4, 1.4, n)
    by = np.linspace(-1.4, 1.4, n)
    w = bx[None, :] + 1j * by[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        for _ in range(40):
            w = w - (w ** 3 - 1) / (3 * w ** 2)
    roots = np.array([1.0 + 0j,
                      -0.5 + 0.8660254037844386j,
                      -0.5 - 0.8660254037844386j])
    basin = np.argmin(np.abs(w[..., None] - roots[None, None, :]), axis=-1)
    from matplotlib.colors import ListedColormap
    basins = ListedColormap(list(SERIES[:3]), name="newton-basins")
    b.imshow(basin, cmap=basins, origin="lower",
             extent=(bx[0], bx[-1], by[0], by[-1]),
             interpolation="nearest", aspect="auto")
    b.set_title("(b) category: qualitative", loc="left")
    b.set_xlabel(r"$\Re z_0$")
    b.tick_params(labelleft=False)
    # A legend and not a colorbar, and the difference IS the panel's argument:
    # a colorbar is a ruler, and three basins have nothing to be a ruler along.
    # The key names the roots because "orange" is not what the reader wants back.
    b.legend(handles=[Patch(facecolor=col, edgecolor="none", label=lab)
                      for col, lab in zip(SERIES[:3],
                                          ("$1$", r"$e^{2\pi i/3}$",
                                           r"$e^{-2\pi i/3}$"))],
             loc="upper center", bbox_to_anchor=(0.5, -0.25), ncols=3,
             frameon=False, handlelength=1.1, borderpad=0.0,
             borderaxespad=0.0, columnspacing=1.2)

    # (c) phase -- an angle, so a cyclic map.
    px = np.linspace(-2.0, 2.0, n)
    py = np.linspace(-2.0, 2.0, n)
    v = px[None, :] + 1j * py[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        f = (v ** 2 - 1.0) / (v ** 2 + 0.5j)
    phase = c.imshow(np.angle(f), cmap="twilight", origin="lower",
                     vmin=-np.pi, vmax=np.pi,
                     extent=(px[0], px[-1], py[0], py[-1]),
                     interpolation="nearest", aspect="auto")
    c.set_title("(c) angle: cyclic", loc="left")
    c.set_xlabel(r"$\Re z$")
    c.tick_params(labelleft=False)
    # Ticked at the wrap and at both ends, so the bar shows the reader that its
    # two ends are the same angle. A bar whose ends match is the visible claim
    # that the colormap closes the loop -- exactly what `cmap_kind` measures as
    # a wrap dE below 3.0.
    bar_c = fig.colorbar(phase, ax=c, pad=0.02,
                         ticks=[-np.pi, 0.0, np.pi])
    bar_c.set_ticklabels([r"$-\pi$", "$0$", r"$\pi$"])
    bar_c.set_label(r"$\arg f(z)$")
    bar_c.outline.set_linewidth(0.0)

    return finish(fig, "gallery-encoding",
           "Three complex-plane images, each on a colormap matched to what it "
           "encodes, and each with the key that kind of encoding takes. (a) "
           "Mandelbrot escape time in viridis, a sequential ramp, read against "
           "a colorbar running 0 to 60 iterations; the set's interior is a "
           "neutral keyed separately as 'did not escape', because that is a "
           "separate class and not a small value. (b) Newton basins for "
           "z^3 - 1 in three separated hues with a legend naming the three "
           "roots, because a basin is a category, nothing orders them, and a "
           "colorbar would be a ruler along nothing. (c) The phase of "
           "(z^2 - 1)/(z^2 + i/2) in twilight, a cyclic map, on a colorbar "
           "ticked at -pi, 0 and pi whose two ends are the same colour because "
           "they are the same angle.",
           context_axes=[a, b, c])


BUILDERS = (small_multiples, field, schematic, forms, convergence, orbit,
            encoding)


def main(argv=None):
    """Build all seven, audit each, and report. Returns a process exit code.

    Under `if __name__ == "__main__"`, so that importing this file builds
    nothing, writes no PNG, reads no `sys.argv` and does not exit the
    interpreter. Importing it used to do all four, which is why the test that
    reads these figures cut the source at a marker string and executed the
    prefix instead of importing it, and why measuring a gate against this
    corpus overwrote the seven committed PNGs as a side effect.
    """
    global OUT
    argv = sys.argv[1:] if argv is None else list(argv)
    OUT = Path(argv[0]) if argv else HERE

    results.clear()
    for build in BUILDERS:
        build()

    print("\n" + "=" * 62)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}.png")
    print("=" * 62 + "\n")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
