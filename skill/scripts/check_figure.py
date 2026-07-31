"""Composition checks for a rendered matplotlib figure.

`check_palette.py` answers "are these colors legal". This answers "is this
figure composed". They fail on different things: a figure can clear every
palette, type-size and ornament gate and still land as a washed-out smudge with
its axis label sliced off.

Every check here is mechanical and reads the figure's own artists, so it runs in
a test rather than in a design review.

    from check_figure import audit
    ok, rows = audit(fig)
    ok, rows = audit(fig, context_axes=[ax])   # contourf background is not ink
    ok, rows = audit(fig, venue="neurips")     # measure type against \textwidth

    python check_figure.py            # self-test on a deliberately bad figure
    python check_figure.py --venues   # the content widths it knows

Checks, in the order `audit` runs them
    1. Clipping          - no text extends past the canvas
    2. Text collision    - no two text bounding boxes overlap
    3. Text readability  - no data ink crosses a label; text clears WCAG on the
                           backdrop it actually got
    4. Contrast stack    - something is at full opacity; alpha levels are few
    5. Mark ratio        - largest / smallest mark area within MARK_RATIO_MAX
    6. Overplotting      - scatter marks do not merge into an unreadable mass
    7. Axis redundancy   - shared-axis panels do not repeat a tick label column
    8. Type size         - every rendered string clears the floor once scaled
    9. Line weight       - every stroke clears LINE_FLOOR_PT once scaled
   10. Ink coverage      - the data region is neither empty nor packed
   11. Series color      - the hues in each panel separate under color blindness
   12. Dual axis         - no second y scale carrying data of its own
   13. Form              - no pie, no 3D, no truncated bar baseline
   14. Identity channel  - series are not told apart by color alone
   15. Label attribution - each label is nearest the curve it names
   16. Style sheet       - figure.mplstyle is the one actually in effect
    17. Contour dash      - dashing is not spent on a signed contour's negatives
    18. Colormap kind     - the colormaps in use are ones a reader can order
    19. Fonts             - Type 42 embedding; the named face is installed
    20. Alt text          - the figure carries a description
"""

import itertools
import math
from collections import Counter
from pathlib import Path
from typing import NamedTuple

MARK_RATIO_MAX = 5.0        # area ratio of largest to smallest data mark
ALPHA_LEVELS_MAX = 3        # distinct transparency levels in one figure
INK_MIN, INK_MAX = 0.02, 0.55   # fraction of the axes area carrying data ink
# Share of a scatter's points whose nearest neighbour sits inside one marker
# radius before the cloud is called an unreadable mass. Up here with its
# siblings rather than inside `check_overplotting`, because the README's claim
# is that every threshold is a module-level constant you can read and change,
# and this was the one that was not.
OVERPLOT_THRESHOLD = 0.5

# The theme has six categorical slots and the guide's claim is that there is no
# seventh: a generated hue is indistinguishable from an existing slot under
# simulated color blindness. Until now that claim was prose only.
MAX_SERIES_HUES = 6

# Rows `audit` can return "warn" for and never False. They are the checks whose
# verdict depends on something the script cannot see: whether the document's
# caption already carries the description, whether the saturated panel is a
# heatmap, whether the figure was built under another project's sheet. Failing
# on a guess there is how a row becomes one everyone skims past.
#
# Up here with the thresholds rather than beside `audit`, because the README
# says every constant worth knowing about is a module-level one you can read,
# and this is the one that says which rows can stop a build.
#
# A constant rather than a sentence in the README, because "which rows are
# advisory" was stated in prose in two places and was wrong in both: the table
# gave Overplotting and Contour dash a "Fails when" they cannot do, and the
# count said five against an actual seven. `tests/test_docs_match_code.py`
# reads this set and holds the prose to it.
# Built from `GATES` at the bottom of this module, where each row declares
# whether it is advisory beside the function that decides it. It was a second
# hand-maintained list of the same twenty names for a while, which is two places
# to update and one of them silently optional.
def _advisory_gates():
    return frozenset(gate.name for gate in GATES if gate.advisory)

# Ink and furniture from `figure.mplstyle`. These land in `ax.lines` and
# `ax.patches` beside the data - reference rules, annotation boxes, spine-colored
# strokes - and none of them carries a categorical identity, so counting them as
# a data hue would fail figures for the color of their own furniture.
INK_TOKENS = {"#000000", "#52514e", "#777570",     # ink primary/secondary/muted
              "#898781",                           # muted, pre-4.5:1 spelling
              "#e1e0d9", "#c3c2b7", "#ffffff"}     # grid, axis, surface

# Two axes are the same frame when their bounds agree this closely. An inset or
# a colorbar never does; `twinx`/`twiny` always does.
FRAME_TOL = 1e-3

# A label is correctly attributed when its own curve is at least this many times
# closer than the next nearest curve. A ratio rather than an absolute distance
# because the judgement the reader makes is comparative: "is this label nearer
# that curve or this one?"
LABEL_MARGIN = 2.0

# --- text readability --------------------------------------------------------
# Data ink inside a label's box, as a fraction of that box. Calibrated against
# a lw=1.6 curve at 150 dpi: crossing a label horizontally is ~14% of the box,
# a single vertical spike ~4%, and a label on clean ground with gridlines behind
# it measures 0.
TEXT_CLUTTER_MAX = 0.03
# Distance, in 0-255 RGB, at which a pixel stops being explainable as a blend of
# the label's surface with the figure's furniture. Well above subpixel and gamma
# noise, well below any two distinguishable hues.
TEXT_BLEND_TOL = 26.0
# A mark is an edge; ground is whatever varies slowly. These set where the line
# between the two falls: how wide a neighbourhood a pixel is compared against,
# and how far it has to sit from that neighbourhood's average to be a mark. The
# window is wider than a 1.6pt hairline at 150 dpi (~3px) so a hairline stands
# clear of its own average, and narrow enough that a viridis ramp does not.
TEXT_EDGE_WINDOW = 9
TEXT_EDGE_TOL = 14.0
# A backdrop color has to cover at least this much of a label's box before it
# can set the contrast verdict. Without a floor, one stray antialiased pixel on
# a field decides whether the label is legible.
TEXT_BACKDROP_MIN_SHARE = 0.10
# Below this many pixels a text box is a glyph or two and the fractions computed
# off it are noise.
TEXT_FOOTPRINT_MIN_PX = 60
# WCAG 2.1 text thresholds. A glyph stem is thinner than a mark, so text does
# not get the 3:1 the mark gates use; large text (>=18pt, or >=14pt bold, ON
# PAGE) does.
TEXT_CONTRAST_MIN = 4.5
TEXT_CONTRAST_MIN_LARGE = 3.0

# Type floor, in points ON THE PAGE, after the figure is scaled to fit.
#
# Stricter than every journal that publishes a number: Nature's floor is 5pt,
# Science asks 5-7pt for labels and 6-8pt for axes, PNAS 6-8pt with nothing
# under 2mm printed. Those are the sizes at which a string is still *possible*
# to read. 7.5 is the size at which it is comfortable, and it is cheap to hold
# because the fix is nearly always cutting words rather than shrinking type.
TYPE_FLOOR_PT = 7.5

# Stroke floor, in points ON THE PAGE. SIAM's instructions for authors: "lines
# one point or thicker; thinner lines may break up or disappear."
LINE_FLOOR_PT = 1.0

# SET THIS PER PROJECT if your sheet is not beside this file: the path to the
# `figure.mplstyle` that `check_style_sheet` compares the live rcParams
# against. A str or a Path; it wins over both locations `_style_sheet` probes.
#
# The sheet is meant to be edited per document, so a project that keeps its own
# somewhere else needs a way to say so, and monkeypatching a private function is
# not one. None means "look beside this script, then in `assets/` next to it".
STYLE_SHEET = None

# SET THIS PER PROJECT: the usable width, in points, of the page the figure
# lands in. Render one page, place a full-width figure, measure it. Within ~5%
# is fine, since it only sets the type floor.
#
# Set it once and the scale is derived per figure from that figure's own width,
# which is the part people get wrong: a wide figure shrinks much harder than a
# narrow one, so the same 8pt label is comfortable in one and illegible in the
# other.
#
# None means "assume scale 1.0" - correct when you author each figure at the
# width it is actually placed at, which makes points authored equal points
# printed and this whole calculation disappear.
CONTENT_WIDTH_PT = None

# `\the\textwidth` and `\the\columnwidth`, read out of the class and style files
# these venues ship. The measure-it-yourself instruction above is the honest
# general answer and it is also the step people skip, so the common cases are
# here already. Pass one as `venue=` rather than editing CONTENT_WIDTH_PT.
#
# VERIFY BEFORE TRUSTING for anything that matters: put `\the\textwidth` in your
# own document and read the log. Style files get revised between years, a
# `geometry` package call in the preamble silently overrides all of this, and a
# figure certified against the wrong width is certified at the wrong type size.
VENUE_WIDTH_PT = {
    "neurips": 397.48,             # \textwidth, neurips_*.sty (5.5in)
    "iclr": 397.48,                # \textwidth, iclr*_conference.sty
    "icml": 487.82,                # \textwidth, icml*.sty (two-column page)
    "icml-column": 234.88,         # \columnwidth
    "acl": 455.24,                 # \textwidth, acl.sty (16cm)
    "acl-column": 219.08,          # \columnwidth (7.7cm)
    "ieee": 516.0,                 # \textwidth, IEEEtran
    "ieee-column": 252.0,          # \columnwidth, IEEEtran
    "nature": 518.74,              # double column, 183mm
    "nature-column": 252.28,       # single column, 89mm
    "article-letter": 345.0,       # \textwidth, article 10pt letterpaper
    "article-a4": 418.25,          # \textwidth, article 10pt a4paper
}


def content_width_pt(venue=None):
    """The usable page width to measure against, in points."""
    if venue is None:
        return CONTENT_WIDTH_PT
    try:
        return VENUE_WIDTH_PT[venue]
    except KeyError:
        raise KeyError(
            f"unknown venue {venue!r}. Known: "
            f"{', '.join(sorted(VENUE_WIDTH_PT))}. For anything else, put "
            "\\the\\textwidth in the document, read the log, and set "
            "CONTENT_WIDTH_PT to what it says.") from None


def page_scale(fig, placed_frac=1.0, venue=None):
    """Scale from authored inches to points on the page.

    `placed_frac` is the fraction of the content width the figure is placed at,
    so it reads like the call site: `\\includegraphics[width=0.48\\textwidth]`
    is `placed_frac=0.48`. Without it every figure is measured as if it were
    full width, and a half-width figure is certified at twice the type size it
    actually ships at - which is the wrong direction for a legibility gate to
    be wrong in.

    `venue` names a row of `VENUE_WIDTH_PT` and overrides `CONTENT_WIDTH_PT` for
    this call, which is the usual way in: the width is a property of the
    document, not of the checkout.
    """
    width = content_width_pt(venue)
    if width is None:
        if placed_frac != 1.0:
            raise ValueError(
                "placed_frac requires a content width. With CONTENT_WIDTH_PT "
                "None and no venue= the checker assumes you authored the "
                "figure at the width it is placed at, which already makes the "
                "scale 1.0; a fractional placement contradicts that. Pass "
                "venue=, set CONTENT_WIDTH_PT, or author at the placed width "
                "and drop placed_frac.")
        return 1.0
    return width * placed_frac / (fig.get_size_inches()[0] * 72)


def _renderer(fig):
    """Return (renderer, canvas): an Agg canvas at the authored dpi, drawn.

    Text extents need a renderer that can measure, and the SVG canvas cannot,
    so measuring on Agg is the baseline. Measuring there *unconditionally* is
    what keeps the verdict off the machine it ran on.

    A HiDPI GUI backend — macosx on a Retina display, Qt on a scaled desktop —
    sets `fig.dpi` to the authored dpi times the display's device pixel ratio
    when the figure is created. Two things then go wrong at once. Text window
    extents come back in physical pixels while `canvas.get_width_height()`
    reports logical ones, so the clipping check measures 2x coordinates against
    a 1x bound and calls the right half of every figure clipped. And every
    threshold below that is calibrated in pixels — the edge window, the
    footprint floor — covers half the distance it was calibrated for.

    Putting the figure back on `_original_dpi` fixes both. That attribute is
    private but is set unconditionally in `Figure.__init__`, and it is the only
    record of the authored value once a HiDPI canvas has overwritten `fig.dpi`.

    Note this rebinds `fig.canvas`: a figure that has been audited is no longer
    attached to its GUI canvas and will not show in a window. `check_ink` and
    `check_text_readability` already did this; it is now unconditional.

    Reused across checks so check_ink does not render a second time.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    original = getattr(fig, "_original_dpi", fig.dpi)
    if fig.dpi != original:
        fig.dpi = original
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    return canvas.get_renderer(), canvas


def _texts(fig, r):
    """Visible, non-empty Text artists with their window extents.

    Matched on the concrete class, not on `hasattr(get_text)` - a ContourSet
    also has a `get_text`, with a different signature.
    """
    from matplotlib.text import Text
    out, seen = [], set()
    for t in fig.findobj(match=lambda a: isinstance(a, Text)):
        if id(t) in seen:
            continue
        seen.add(id(t))
        if not t.get_visible() or not str(t.get_text()).strip():
            continue
        try:
            bb = t.get_window_extent(renderer=r)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        out.append((t, bb))
    return out


def _tick_texts(fig):
    ids = set()
    for ax in fig.axes:
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            ids.add(id(t))
    return ids


def _ghost_ticks(fig):
    """Tick artists that exist on an axes but never reach the page: those on a
    hidden axes (`ax.axis("off")`), and those at locations outside the current
    view. Counting either as clipped text reports a defect that is not there.
    """
    ids = set()
    for ax in fig.axes:
        if not ax.axison:
            ids.update(id(t) for t in
                       ax.get_xticklabels() + ax.get_yticklabels())
            continue
        for locs, labels, (lo, hi) in (
            (ax.get_xticks(), ax.get_xticklabels(), ax.get_xlim()),
            (ax.get_yticks(), ax.get_yticklabels(), ax.get_ylim()),
        ):
            lo, hi = min(lo, hi), max(lo, hi)
            for pos, lab in zip(locs, labels):
                if not (lo <= pos <= hi):
                    ids.add(id(lab))
    return ids


def _polar_radial_ticks(fig):
    """Radial tick labels on polar axes.

    matplotlib places these inside the disc, because on a polar plot there is
    no outside to place them in — `set_rlabel_position` moves them to a
    different angle, never off the data. So a curve running under '0.8' is not
    a composition mistake anybody made, and the advice this gate gives ("move
    the label to clear ground") names a move that does not exist.

    Both clauses, not just clutter. Exempting clutter alone still left the
    contrast clause failing eight of eight ordinary polar plots built on this
    project's own style sheet, at 2.0:1 against a curve the radial axis crosses
    by construction. A gate the bundled sheet cannot satisfy is measuring the
    projection, not the figure.

    The count is reported rather than dropped, so the author is told these
    strings went unjudged instead of assuming they passed.
    """
    ids = set()
    for ax in fig.axes:
        if getattr(ax, "name", "") == "polar":
            ids.update(id(t) for t in ax.get_yticklabels())
    return ids


def _overlap(a, b):
    dx = min(a.x1, b.x1) - max(a.x0, b.x0)
    dy = min(a.y1, b.y1) - max(a.y0, b.y0)
    return dx > 0 and dy > 0


def check_clipping(fig, r):
    w, h = fig.canvas.get_width_height()
    ghosts = _ghost_ticks(fig)
    bad = []
    for t, bb in _texts(fig, r):
        if id(t) in ghosts:
            continue
        if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > w + 1 or bb.y1 > h + 1:
            bad.append(str(t.get_text())[:32])
    return (not bad,
            "no text past the canvas" if not bad
            else f"clipped: {bad}  <- add constrained_layout or widen the figure")


def check_collisions(fig, r):
    """Text-on-text overlap. Tick labels on a shared axis are exempt: matplotlib
    lays those out itself and a 1px touch there is not a defect."""
    ticks = _tick_texts(fig)
    items = [(t, bb) for t, bb in _texts(fig, r) if id(t) not in ticks]
    hits = []
    for (ta, ba), (tb, bb) in itertools.combinations(items, 2):
        if _overlap(ba, bb):
            hits.append((str(ta.get_text())[:22], str(tb.get_text())[:22]))
    return (not hits,
            f"{len(items)} text objects, none overlapping" if not hits
            else f"overlapping: {hits[:4]}")


def _halo(t):
    """(color, linewidth) of a stroke path effect, when the text wears casing.

    Casing — the cartographic term for a contrasting outline around a label —
    is what lets a label sit over busy ground at all. Reading it off the artist
    rather than guessing from the pixels keeps the two clauses below separable:
    whether the halo *should* have worked, and whether it *did*.

    `Stroke` keeps its kwargs in a private `_gc` dict and matplotlib exposes no
    public accessor. That is a dependency on an internal name, so it fails the
    way internals do — silently, returning no halo, at which point every cased
    label in every figure gets judged against the raw backdrop it was cased to
    survive, and correct work starts failing. Any other dict attribute carrying
    a `foreground` is tried before giving up, and `test_halo_reads_withstroke`
    exists to make a rename a red suite rather than a quiet regression.
    """
    from matplotlib import patheffects as pe
    for effect in (t.get_path_effects() or ()):
        if not isinstance(effect, pe.Stroke):     # withStroke subclasses Stroke
            continue
        # `_gc` first by name, then any other dict the effect carries. Scanning
        # `vars` covers `_gc` too, so the named lookup is only there to fix the
        # order: the attribute matplotlib actually uses wins over a same-shaped
        # one that happens to be declared earlier.
        for gc in (getattr(effect, "_gc", None), *vars(effect).values()):
            if not isinstance(gc, dict):
                continue
            fg = gc.get("foreground")
            if fg is not None:
                return fg, float(gc.get("linewidth", 0.0) or 0.0)
    return None, 0.0


def _furniture(fig):
    """Colors a label is allowed to sit on, read off the figure that drew them.

    Casing exists precisely so a gridline can pass behind a label; the axis rule
    and the tick marks are the same kind of thing. Data ink is not furniture,
    which is the whole distinction this list draws.

    Harvested from the artists rather than from `INK_TOKENS` for two reasons.
    The token set contains the text ink itself, and a black reference line
    crossing a black label is a defect rather than furniture. And a project that
    swapped the style sheet's grid color would otherwise have every gridline in
    every figure counted as data passing through its labels — the check would
    fire hardest on exactly the people who customised it.
    """
    from matplotlib.colors import to_rgb
    out = {tuple(to_rgb(fig.get_facecolor()))}
    for ax in fig.axes:
        out.add(tuple(to_rgb(ax.get_facecolor())))
        for axis in (ax.xaxis, ax.yaxis):
            for line in axis.get_gridlines():
                out.add(tuple(to_rgb(line.get_color())))
            for tick in axis.get_ticklines():
                out.add(tuple(to_rgb(tick.get_color())))
        for spine in ax.spines.values():
            out.add(tuple(to_rgb(spine.get_edgecolor())))
    return [tuple(c * 255.0 for c in rgb) for rgb in out]


def _near_any(pixels, anchors, tol):
    """Which of an (N, 3) block of pixels a blend of `anchors` explains.

    Antialiasing puts pixels on the straight line between two colors that meet,
    so the test is distance to the nearest *segment* joining a pair of anchors,
    not distance to the nearest anchor. Without that, the halfway pixel where a
    gridline meets the page reads as a third color and every gridline in the
    figure counts as foreign ink.
    """
    import numpy as np
    pix = pixels.astype(float)
    best = np.full(len(pix), np.inf)
    for a, b in itertools.combinations_with_replacement(anchors, 2):
        a, b = np.asarray(a, float), np.asarray(b, float)
        seg = b - a
        span = float(seg @ seg)
        if span < 1.0:
            d = np.linalg.norm(pix - a, axis=1)
        else:
            u = np.clip(((pix - a) @ seg) / span, 0.0, 1.0)
            d = np.linalg.norm(pix - (a + u[:, None] * seg), axis=1)
        np.minimum(best, d, out=best)
    return best <= tol


def _box_blur(field, size):
    """Moving average over an (H, W, 3) block, edges extended.

    `scipy.ndimage.uniform_filter` does this and is what the first version
    called. Written out in numpy instead so `check_figure.py` stays a file you
    can copy next to your figures with nothing but matplotlib installed —
    the promise in the README is three files and no install, and a hard scipy
    import quietly broke it. Separable and cumulative, so it costs two passes
    regardless of the window.
    """
    import numpy as np
    half = size // 2
    out = field.astype(float)
    for axis in (0, 1):
        padded = np.concatenate(
            [np.repeat(out.take([0], axis=axis), half, axis=axis),
             out,
             np.repeat(out.take([-1], axis=axis), half, axis=axis)],
            axis=axis)
        cum = np.cumsum(padded, axis=axis)
        zero = np.zeros_like(cum.take([0], axis=axis))
        cum = np.concatenate([zero, cum], axis=axis)
        n = out.shape[axis]
        hi = cum.take(range(size, size + n), axis=axis)
        lo = cum.take(range(0, n), axis=axis)
        out = (hi - lo) / size
    return out


def _foreign_ink(block, furniture, tol):
    """Fraction of a backdrop patch that is a mark rather than ground.

    Ground is whatever varies slowly: the page, a flat fill, a viridis field.
    A mark is an *edge* — a curve, a marker, an isoline — so the test is each
    pixel against a local average of its neighbours rather than against the
    patch's dominant color. Testing against the dominant color was the obvious
    first version and it failed every annotation on a heatmap, because a smooth
    ramp differs from its own mode everywhere while being, to a reader, one
    surface.

    Furniture is exempt at the second step rather than the first: a gridline IS
    an edge, and casing exists precisely so it can pass behind a label.
    """
    import numpy as np

    field = block.astype(float)
    local = _box_blur(field, TEXT_EDGE_WINDOW)
    edge = np.linalg.norm(field - local, axis=2) > TEXT_EDGE_TOL
    if not edge.any():
        return 0.0
    pix = field[edge].reshape(-1, 3)
    return float(edge.sum() - _near_any(pix, furniture, tol).sum()) / edge.size


def _worst_backdrop(block, fg, min_share):
    """The backdrop color the text reads worst against, among those covering at
    least `min_share` of its box.

    A single color is the wrong summary for a field: a label on viridis sits on
    a range, and both the mean and the mode can clear the threshold while a
    third of the box does not. A share floor keeps a handful of stray pixels
    from setting the verdict.
    """
    import numpy as np
    pix = block.reshape(-1, 3)
    keys, counts = np.unique(pix // 8, axis=0, return_counts=True)
    worst, ratio = None, float("inf")
    for key, n in zip(keys, counts):
        if n / len(pix) < min_share:
            continue
        color = pix[((pix // 8) == key).all(axis=1)].mean(axis=0)
        r = _contrast_255(fg, color)
        if r < ratio:
            worst, ratio = color, r
    if worst is None:
        return pix.mean(axis=0), _contrast_255(fg, pix.mean(axis=0))
    return worst, ratio


def check_text_readability(fig, r, canvas=None, scale=None, placed_frac=1.0,
                           venue=None):
    """Whether each string can be read where it sits.

    `check_label_attribution` asks which curve a label belongs to. This asks the
    prior question — whether the label is legible at all — and the two come
    apart hard: a label printed *on* its own curve is attributed perfectly, and
    is read through the line crossing its letterforms.

    Both clauses are measured off rendered pixels, because both depend on what
    happened to land behind the glyphs and no artist knows that about itself.
    The figure is drawn a second time with every string hidden; that render is
    the backdrop each label was placed onto.

    *Clutter.* Inside a label's box the backdrop should be one surface. Pixels
    that no blend of {that surface, the grid, the axis rule} explains are data
    ink passing through the text — a curve, a marker, a spike between the
    strokes. Measuring the backdrop rather than the finished render is the whole
    trick: casing hides the evidence, because a white halo over an orange curve
    renders as clean white while punching a visible gap through the data. Both
    halves of that are defects and this sees them as one number.

    Uniform data ink is not clutter. A label on a heatmap cell has the cell as
    its surface, so it is the contrast clause that governs there, which is the
    correct division: a flat fill is a background, a curve is not.

    *Contrast.* The text against the backdrop it actually got, at the WCAG text
    threshold (4.5:1, or 3:1 for large text) rather than the 3:1 mark threshold,
    because a glyph stem is thinner than a mark. Casing counts: a black label
    with a white halo on a dark field is read against the halo.

    Tick labels are included. They sit outside the axes on most figures and cost
    nothing to check there, and on the figures where they do not — an inset, a
    twinned frame, a label moved inside — that is exactly where they get
    crossed.
    """
    import numpy as np
    from matplotlib.colors import to_rgb

    items = _texts(fig, r)
    if not items:
        return True, "no text to read"
    if canvas is None:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        canvas.draw()

    # Hiding text changes what constrained_layout has to fit, so the second
    # render would come back with every artist in a slightly different place and
    # the backdrop would not line up with the boxes measured against the first.
    # Pin the layout for the duration; the engine is put back before returning.
    engine = fig.get_layout_engine()
    fig.set_layout_engine("none")
    visible = [t.get_visible() for t, _ in items]
    try:
        for t, _ in items:
            t.set_visible(False)
        canvas.draw()
        backdrop = np.asarray(
            canvas.buffer_rgba())[:, :, :3].astype(np.int16).copy()
    finally:
        for (t, _), v in zip(items, visible):
            t.set_visible(v)
        canvas.draw()
        if engine is not None:
            fig.set_layout_engine(engine)

    if scale is None:
        scale = page_scale(fig, placed_frac, venue)
    H, W = backdrop.shape[:2]
    furniture = _furniture(fig)
    # Ticks that exist on the axes but never reach the page — a hidden axes, a
    # location outside the view. `check_clipping` learned about these the same
    # way this did: by reporting a defect on a schematic that draws no axes and
    # still carries the tick Text objects matplotlib made for it.
    ghosts = _ghost_ticks(fig)
    radial = _polar_radial_ticks(fig)
    cluttered, faint, checked, unjudged = [], [], 0, 0

    for t, bb in items:
        if id(t) in ghosts:
            continue
        if id(t) in radial:
            unjudged += 1
            continue
        xa, xb = max(int(bb.x0) - 1, 0), min(int(bb.x1) + 2, W)
        ya, yb = max(int(bb.y0) - 1, 0), min(int(bb.y1) + 2, H)
        # Agg's origin is top-left, the figure's is bottom-left
        block = backdrop[slice(H - yb, H - ya), slice(xa, xb)]
        # Below this the fractions are counting antialiasing, not measuring.
        if block.size // 3 < TEXT_FOOTPRINT_MIN_PX:
            continue
        checked += 1

        fg = np.array(to_rgb(t.get_color())) * 255.0
        halo_color, _ = _halo(t)
        name = str(t.get_text())[:22]

        frac = _foreign_ink(block, furniture, TEXT_BLEND_TOL)
        if frac > TEXT_CLUTTER_MAX:
            cluttered.append(
                f"{name!r} sits on data ink over {frac:.0%} of its box"
                + (" — the casing hides it by erasing the data underneath"
                   if halo_color else " and wears no casing"))

        pt = t.get_fontsize() * scale
        weight = t.get_fontweight()
        bold = (weight in ("bold", "heavy", "black", "extra bold", "semibold")
                or (isinstance(weight, (int, float)) and weight >= 600))
        floor = (TEXT_CONTRAST_MIN_LARGE
                 if pt >= 18.0 or (pt >= 14.0 and bold) else TEXT_CONTRAST_MIN)
        if halo_color:
            # Casing replaces the backdrop under the strokes, so that is what
            # the reader reads against.
            ratio = _contrast_255(fg, np.array(to_rgb(halo_color)) * 255.0)
        else:
            _, ratio = _worst_backdrop(block, fg, TEXT_BACKDROP_MIN_SHARE)
        if ratio < floor:
            faint.append(f"{name!r} at {ratio:.1f}:1 on its backdrop "
                         f"(text needs {floor}:1)")

    skipped = (f"; {unjudged} polar radial labels not judged (matplotlib "
               "places them on the data and offers nowhere else to put them)"
               if unjudged else "")
    if not checked:
        return True, "no text large enough to measure" + skipped
    bad = cluttered + faint
    if not bad:
        return True, (f"{checked} strings read clean against their backdrop"
                      + skipped)
    return False, ("; ".join(bad[:3])
                   + "  <- move the label to clear ground; casing rescues a "
                     "gridline, not a curve")


def _contrast_255(rgb_a, rgb_b):
    """WCAG contrast for two 0-255 RGB triples.

    Duplicated from `check_palette.contrast` rather than imported: this file
    already treats that import as optional (`check_series_color` degrades to a
    note when it is missing), and a legibility gate that silently stops running
    when a sibling file is absent is the kind of decoration this repo exists to
    argue against.
    """
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    lums = []
    for rgb in (rgb_a, rgb_b):
        r, g, b = (lin(float(v)) for v in rgb)
        lums.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    hi, lo = max(lums), min(lums)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast_stack(fig):
    """A figure where nothing is at full opacity has no focal point, and a long
    tail of alpha values reads as haze rather than hierarchy."""
    alphas = []
    for ax in fig.axes:
        for a in list(ax.collections) + list(ax.lines) + list(ax.patches):
            if not a.get_visible():
                continue
            al = a.get_alpha()
            # unset alpha means opaque, and that is exactly what this check
            # wants to know about, so it counts as 1.0 rather than being skipped
            alphas.append(1.0 if al is None else round(float(al), 2))
    if not alphas:
        return True, "no data artists"
    levels = sorted(set(alphas))
    solid = any(x >= 0.99 for x in alphas)
    ok = len(levels) <= ALPHA_LEVELS_MAX and solid
    note = ""
    if not solid:
        note = "  <- nothing is opaque, so the figure has no focal point"
    elif len(levels) > ALPHA_LEVELS_MAX:
        note = f"  <- {len(levels)} levels reads as haze; keep to {ALPHA_LEVELS_MAX}"
    return ok, f"alpha levels {levels}{note}"


def check_mark_ratio(fig):
    """One mark far larger than the rest stops reading as a mark and starts
    reading as an ornament stuck on top of the plot.

    Reads scatter sizes (already an area in pt^2) and line markers (a diameter
    in points, converted to the area of the disc it draws). Bars and other
    patches are deliberately NOT counted: a bar thirty times another bar is the
    encoding working, not a defect. This gate is about marks whose size is not
    carrying the value.

    The conversion used to be `markersize ** 2`, which is the bounding square
    rather than the mark, and it is 4/pi = 1.27x too large. On a figure drawing
    only one artist type the bias cancels in the ratio and nothing shows; on one
    mixing `scatter` with `plot(marker=...)` it does not, and two marks of
    identical drawn area reported 1.3x. Against a 5.0 threshold that is enough
    to fail a legal figure at a true 3.9x and pass a bad one at 6.4x.
    """
    worst = None
    for ax in fig.axes:
        sizes = []
        for c in ax.collections:
            s = getattr(c, "get_sizes", lambda: [])()
            sizes.extend(float(v) for v in s if v > 0)
        for ln in ax.lines:
            if not ln.get_visible() or ln.get_marker() in ("", "None", None):
                continue
            ms = float(ln.get_markersize())
            if ms > 0:
                sizes.append((ms / 2.0) ** 2 * math.pi)
        if len(sizes) < 2:
            continue
        ratio = max(sizes) / min(sizes)
        if worst is None or ratio > worst[0]:
            worst = (ratio, min(sizes), max(sizes))
    if worst is None:
        return True, "fewer than two mark sizes"
    ratio, lo, hi = worst
    return (ratio <= MARK_RATIO_MAX,
            f"largest/smallest mark area {ratio:.1f}x  (s={lo:.0f} to {hi:.0f})"
            + ("" if ratio <= MARK_RATIO_MAX
               else f"  <- cap at {MARK_RATIO_MAX}x"))


def check_overplotting(fig):
    """Warn when scatter points overlap into an unreadable mass.

    For each PathCollection with offsets (a scatter), estimates the fraction of
    points whose nearest neighbour in display pixels is within one marker
    radius. Above the threshold the marks merge into a blob — thin the count,
    use hollow markers, add transparency, or switch to hexbin.
    """
    import numpy as np
    try:
        from scipy.spatial import cKDTree
    except ImportError:                      # optional, see `_box_blur`
        cKDTree = None

    dpi = fig.dpi

    bad = []
    for i, ax in enumerate(fig.axes):
        for j, coll in enumerate(ax.collections):
            try:
                offsets = coll.get_offsets()
            except Exception:
                continue
            if offsets.size < 2:
                continue
            try:
                xy = ax.transData.transform(offsets)
            except Exception:
                continue
            sizes = getattr(coll, "get_sizes", lambda: [])()
            if len(sizes) == 0:
                continue
            sizes = np.asarray(sizes, dtype=float)
            if sizes.size == 1:
                sizes = np.full(len(offsets), sizes[0])
            radius_px = np.sqrt(sizes / np.pi) * dpi / 72.0

            n = len(xy)
            if n < 2:
                continue
            if cKDTree is not None:
                dists, _ = cKDTree(xy).query(xy, k=2)
                if dists.ndim < 2:
                    continue
                nn_dist = dists[:, 1]
            else:
                # Same nearest-neighbour distance, O(n^2). Only reached where
                # scipy is absent, and only for the scatters this check looks
                # at, so the cost lands on figures that already draw n points.
                d = np.hypot(xy[:, 0][:, None] - xy[None, :, 0],
                             xy[:, 1][:, None] - xy[None, :, 1])
                np.fill_diagonal(d, np.inf)
                nn_dist = d.min(axis=1)
            overlap = int((nn_dist < radius_px).sum())
            frac = overlap / n
            if frac > OVERPLOT_THRESHOLD:
                bad.append((i, j, frac))

    if not bad:
        return True, "no scatter overplotting"
    detail = "; ".join(f"ax{i}.col{j} {f:.0%}" for i, j, f in bad)
    return "warn", (f"overplotting: {detail} — marks merge into blob; "
                    "thin counts, use hollow markers, add transparency, "
                    "or switch to hexbin")


def check_redundancy(fig, r):
    """Side-by-side panels on the same scale should share their axis furniture.
    Two identical tick columns and two identical axis labels is duplicated ink."""
    # Only same-row panels can share a y axis, and only same-column panels can
    # share an x axis. Two panels side by side each legitimately need their own
    # x label; repeating the y label between them is the duplication.
    rows, cols = {}, {}
    for ax in fig.axes:
        ss = ax.get_subplotspec()
        if ss is None:
            continue
        # A panel at `axis("off")` shows no furniture to duplicate. Its tick
        # Text objects still exist and still carry their strings, which is how
        # three image panels with no visible axis at all came to be told to
        # "use sharex/sharey" — advice with nothing to act on.
        if not ax.axison:
            continue
        r_, c_ = ss.rowspan.start, ss.colspan.start
        rows.setdefault(r_, []).append(ax)
        cols.setdefault(c_, []).append(ax)

    dupes = []
    for group, getter, axis in ((rows, "get_ylabel", "y"),
                                (cols, "get_xlabel", "x")):
        for _, axes in group.items():
            vals = [getattr(a, getter)().strip() for a in axes]
            vals = [v for v in vals if v]
            for label, n in Counter(vals).items():
                if n > 1:
                    dupes.append(f"{axis}label {label!r} x{n}")

    dup_ticks = 0
    for _, axes in rows.items():
        cols_seen = Counter(
            tuple(t.get_text() for t in a.get_yticklabels()
                  if t.get_text() and t.get_visible())
            for a in axes)
        dup_ticks += sum(n - 1 for v, n in cols_seen.items() if v and n > 1)

    ok = not dupes and not dup_ticks
    if ok:
        return True, "axis furniture not duplicated"
    bits = dupes + ([f"repeated y tick column x{dup_ticks}"] if dup_ticks else [])
    return False, "; ".join(bits) + "  <- use sharex/sharey"


def check_type_size(fig, r, scale=None, placed_frac=1.0, venue=None):
    """Every rendered string clears the legibility floor once the figure is
    scaled into the document.

    This used to be a regex over the source file hunting for `fontsize=`, which
    missed anything set through rcParams, anything computed, and anything set by
    a helper. Reading `get_fontsize()` off the artists that actually rendered
    reports what is on the page instead of what is in the source.
    """
    scale = page_scale(fig, placed_frac, venue) if scale is None else scale
    ghosts = _ghost_ticks(fig)
    sizes = [(round(float(t.get_fontsize()) * scale, 1), str(t.get_text())[:22])
             for t, _ in _texts(fig, r) if id(t) not in ghosts]
    if not sizes:
        return True, "no text"
    small = sorted({(pt, s) for pt, s in sizes if pt < TYPE_FLOOR_PT})
    mn = min(pt for pt, _ in sizes)
    if not small:
        detail = f"smallest {mn:.1f}pt on page (floor {TYPE_FLOOR_PT})"
        if placed_frac < 0.35:
            return "warn", (f"{detail}; placed at {placed_frac:.0%} of content width"
                           " — labels may be too small to read; author at the"
                           " width it ships at")
        return True, detail
    return False, (f"under {TYPE_FLOOR_PT}pt on page at scale {scale}: {small[:4]}"
                   "  <- cut words, do not shrink type")


def _axes_drew_anything(ax):
    """Whether anything was drawn into this axes.

    Not `_has_data`, which is a different question defined further down this
    file: that one asks whether an axes carries *data*, which is what the
    dual-axis gate needs. This asks whether the panel was used at all, so a
    table or a lone annotation counts. The two names are close enough that one
    shadowed the other once; keep them apart.

    Every container matplotlib puts drawn content in: a blank axes has all of
    them at zero, and a panel holding only an annotation or only a bar still
    reports through one of them. `ax.patch` is the background and is
    deliberately not consulted — it exists on the blank axes too.
    """
    return any(len(getattr(ax, name, ())) for name in
               ("lines", "collections", "patches", "images", "texts",
                "tables", "artists"))


def check_ink(fig, context_axes=None, canvas=None):
    """Ink as a fraction of each plotting area, measured off the rendered
    pixels rather than estimated from artist properties.

    Near zero means a panel that did not need to be a panel. Very high means a
    panel with no ground left in it. Reported per-axes, and advisory only: the
    right density genuinely depends on the form, so this flags panels worth a
    second look rather than declaring them wrong.

    Pass `context_axes` — a list of Axes whose fill is a context surface (e.g. a
    contourf landscape) rather than data-ink. For those axes, the ink fraction
    measures only marks ON TOP of the surface by separating the pixel values
    into two clusters (k-means with k=2) and removing the larger cluster (the
    surface). A figure with a filled terrain plus a few sparse marks will PASS
    rather than WARN.

    Pass `canvas` — an already-drawn Agg canvas — to avoid a second render.
    """
    import numpy as np

    if canvas is None:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
    buf = np.asarray(canvas.buffer_rgba())[:, :, :3].astype(int)
    h = buf.shape[0]
    bg = buf[0, 0]
    # anything more than a few levels off the page color counts as ink
    ink_mask = (np.abs(buf - bg).sum(axis=2) > 24)

    if context_axes is None:
        context_axes = []
    context_ids = frozenset(id(ax) for ax in context_axes)

    rows = []
    for i, ax in enumerate(fig.axes):
        # A colorbar is a solid ramp by construction: 100% ink, always, on
        # every figure that has one. Measuring it means every heatmap in the
        # world stands at WARN for the one axes in it whose density is not a
        # choice anybody made. matplotlib labels the axes it creates.
        if ax.get_label() == "<colorbar>":
            continue
        bb = ax.get_window_extent(renderer=canvas.get_renderer())
        x0, x1 = int(max(bb.x0, 0)), int(min(bb.x1, buf.shape[1]))
        y0, y1 = int(max(bb.y0, 0)), int(min(bb.y1, h))
        # Agg's origin is top-left, the figure's is bottom-left
        sub = ink_mask[h - y1:h - y0, x0:x1]
        if sub.size == 0:
            continue

        if id(ax) in context_ids:
            # Separate surface pixels from mark pixels via 2-means on color.
            sub_buf = buf[h - y1:h - y0, x0:x1].astype(float)
            flat = sub_buf.reshape(-1, 3)
            m1 = flat.mean(axis=0)
            # init second centroid offset so they diverge
            m2 = m1 + 30.0
            for _ in range(12):
                d1 = np.abs(flat - m1).sum(axis=1)
                d2 = np.abs(flat - m2).sum(axis=1)
                c1 = d1 <= d2
                c2 = ~c1
                if c1.sum() == 0 or c2.sum() == 0:
                    break
                nm1 = flat[c1].mean(axis=0)
                nm2 = flat[c2].mean(axis=0)
                if (np.abs(nm1 - m1).sum() < 0.5
                        and np.abs(nm2 - m2).sum() < 0.5):
                    break
                m1, m2 = nm1, nm2
            surf = c1 if c1.sum() > c2.sum() else c2
            surf_mask = surf.reshape(sub.shape)
            # Ink = pixels in the ink_mask AND not in the surface cluster
            frac = float((sub & ~surf_mask).mean())
        else:
            frac = float(sub.mean())
        # An empty panel is structural, not a low number. The frame and the
        # tick marks of a blank axes measure about 0.03 on their own, over the
        # 0.02 floor, so the blank subplot in a grid — the case that actually
        # ships — read as merely sparse. Ask whether anything was drawn.
        rows.append((i, frac,
                     _axes_drew_anything(ax) and INK_MIN <= frac <= INK_MAX))

    if not rows:
        return True, "no measurable axes"
    detail = ", ".join(f"ax{i} {f:.2f}" for i, f, _ in rows)
    odd = [i for i, _, g in rows if not g]
    if not odd:
        return True, f"ink fraction: {detail} (typical {INK_MIN}-{INK_MAX})"
    return "warn", (f"ink fraction: {detail} (typical {INK_MIN}-{INK_MAX})"
                    f" - look at ax{odd}: empty panels and saturated ones both"
                    " read badly, though a heatmap legitimately runs high")


# --- color ------------------------------------------------------------------

def _hex(c):
    """A drawn color as lowercase 6-digit hex, or None if it never reaches the
    page. Fully transparent is the case that matters: a bar's default edge color
    is `none`, and reading it as black would put the ink token on every bar."""
    from matplotlib.colors import to_hex, to_rgba
    try:
        r, g, b, a = to_rgba(c)
    except (ValueError, TypeError):
        return None
    return None if a == 0 else to_hex((r, g, b))


def _colors_of(value):
    """Normalize the several shapes matplotlib returns a color in: a string from
    `Line2D`, an RGBA tuple from `Patch`, an Nx4 array from a `Collection`."""
    if isinstance(value, str):
        return [value]
    import numpy as np
    try:
        arr = np.asarray(value, dtype=float)
    except (ValueError, TypeError):
        return []
    if arr.ndim == 1:
        return [tuple(arr)] if arr.size in (3, 4) else []
    if arr.ndim == 2 and arr.shape[1] in (3, 4):
        return [tuple(row) for row in arr]
    return []


def _artist_kind(artist):
    """A coarse artist family: a line, a scatter's marks, or a filled area.

    The wrap check needs it. A cycler that wraps reuses one artist *type* - two
    lines, two scatters - and hands them different labels. One series shown as a
    band and its mean line and its points is three types in one hue, which is
    the opposite: one identity, several artists. Kind tells them apart."""
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    if isinstance(artist, Line2D):
        # `plot(..., linestyle="none", marker="o")` is a Line2D that draws no
        # line. Calling it one made a path and its own start marker, in one
        # hue, read as a wrapped cycler handing two identities to one color —
        # which is the exact case this function exists to tell apart.
        stroke = str(artist.get_linestyle()).strip().lower()
        drawn = stroke not in ("none", "", " ") and artist.get_linewidth() > 0
        return "line" if drawn else "marks"
    if isinstance(artist, PathCollection):
        return "marks"
    return "area"          # bars, fill_between polys, other patches


def _data_colors_by_axes(fig):
    """`{axes: [(hex, label, kind), ...]}` - the categorical colors on the
    figure, kept apart by the panel they were drawn in and tagged with the kind
    of artist that drew them. `label` is None for an artist matplotlib named
    itself.

    Structure the old figure-wide bag threw away. The panel is the unit a reader
    compares a hue within: two hues in different panels never sit side by side,
    so pooling every axes into one set gated a flow-chart node in one panel
    against a regression curve in another. The kind lets one identity drawn as
    several artist types in one hue read as one series, not a wrapped cycler.

    Harvested narrowly on purpose. Two exclusions do the work:

    - an artist with a colormap attached (`get_array()` is not None) encodes a
      *value*, not an identity - a heatmap or a scatter colored by magnitude is
      a continuous encoding and answers to the viridis rule instead. This is
      also the escape hatch for an ordinal ramp: draw it `c=values, cmap=...`,
      never as a pre-evaluated RGBA list, and it is read as the value it is.
    - the ink tokens, per `INK_TOKENS` above
    """
    out = {}
    for ax in fig.axes:
        items = []
        for artist in list(ax.lines) + list(ax.patches) + list(ax.collections):
            if not artist.get_visible():
                continue
            if getattr(artist, "get_array", lambda: None)() is not None:
                continue
            raw = str(artist.get_label() or "")
            label = raw if raw and not raw.startswith("_") else None
            kind = _artist_kind(artist)
            seen = set()
            for getter in ("get_color", "get_facecolor", "get_edgecolor"):
                fn = getattr(artist, getter, None)
                if fn is None:
                    continue
                try:
                    value = fn()
                except (ValueError, TypeError, AttributeError):
                    continue
                for c in _colors_of(value):
                    h = _hex(c)
                    if h and h not in INK_TOKENS and h not in seen:
                        seen.add(h)
                        items.append((h, label, kind))
        if items:
            out[ax] = items
    return out


def _data_colors(fig):
    """Flat `(hex, label)` across the whole figure, for the checks that only
    need the bag of identified hues and not the panel each lives in."""
    return [(h, label) for items in _data_colors_by_axes(fig).values()
            for h, label, _ in items]


def _axes_all_pairs(ax):
    """Which separation mode a *panel* needs. `check_palette.py` has to ask for
    this on the command line because a list of hexes does not say what it will be
    drawn as; a built figure does say. Scatter puts every series next to every
    other, so every pair has to separate. Lines and bars only ever put
    neighbours next to each other, and gating all pairs there would fail
    palettes the guide explicitly sanctions.

    Asked per axes, not per figure: a scatter in one panel does not make a
    line-only panel two panels over answer to the stricter rule."""
    from matplotlib.collections import PathCollection
    return any(isinstance(c, PathCollection) for c in ax.collections)


def check_series_color(fig):
    """The hues actually drawn, put through the palette gates.

    The hole this closes: `check_palette.py` judges a list of hexes someone
    remembered to paste into a terminal, and this file never looked at color at
    all. A figure on matplotlib's default `tab10` cycle - whose orange and green
    measure OKLab dE 1.4 under protanopia - passed every composition check
    clean. Two scripts in one project that never spoke.

    Only what is never legitimate is gated: separation under color blindness,
    and separation in normal vision. The lightness-band and chroma-floor rows
    are deliberately *not* applied to harvested colors. A black or gray series
    is legal - a reference curve, a control group - and failing it is precisely
    the noise that teaches people to skim past the row.

    Scoped per panel. The comparison, the hue count and the all-pairs mode are
    all asked of one axes at a time, because the panel is the unit a reader
    separates hues within - a figure-wide bag gated hues that never share a
    frame against each other.
    """
    by_ax = _data_colors_by_axes(fig)
    if not by_ax:
        return True, "no categorical series colors"

    fails, notes = [], []
    cp = None
    try:
        import check_palette as cp
    except ImportError:
        notes.append("check_palette.py is not importable beside this file, "
                     "so separation went unchecked")

    for ax, items in by_ax.items():
        distinct = list(dict.fromkeys(h for h, _, _ in items))

        if len(distinct) > MAX_SERIES_HUES:
            fails.append(f"{len(distinct)} distinct data hues in one panel, "
                         f"theme has {MAX_SERIES_HUES}  <- fold the tail into "
                         "'Other' or facet")

        # One hue carrying two identities is what a seventh series looks like
        # once the cycler wraps: matplotlib reuses slot 1 without complaint and
        # the legend confidently lists both. Narrowed to labels on artists of the
        # *same kind*: a wrap reuses one artist type, whereas a band, its mean
        # line and its points in one hue is one series shown three ways, each
        # legitimately labelled. Keyed on kind, that reads as one identity.
        by_hue_kind = {}
        for h, label, kind in items:
            if label:
                by_hue_kind.setdefault((h, kind), set()).add(label)
        for (h, kind), labels in sorted(by_hue_kind.items()):
            if len(labels) > 1:
                fails.append(f"{h} carries {len(labels)} identities "
                             f"{sorted(labels)} on {kind} artists"
                             "  <- the color cycle wrapped")

        if len(distinct) >= 2 and cp is not None:
            _, rows = cp.check(distinct, all_pairs=_axes_all_pairs(ax))
            for name, status, detail in rows:
                if not name.startswith(("CVD separation", "Normal-vision floor")):
                    continue
                if status is False:
                    fails.append(detail)
                else:
                    notes.append(detail.split("  <-")[0].strip())

    max_per_panel = max(
        (len(list(dict.fromkeys(h for h, _, _ in items)))
         for items in by_ax.values()), default=0)
    head = f"up to {max_per_panel} data hues per panel"
    if fails:
        return False, f"{head}: " + "; ".join(fails)
    return True, f"{head}: " + ("; ".join(notes) if notes else "nothing to compare")


# --- structure --------------------------------------------------------------

def _has_data(ax):
    return any(a.get_visible() for a in
               list(ax.lines) + list(ax.patches)
               + list(ax.collections) + list(ax.images))


def check_dual_axis(fig):
    """Two y scales in one frame, which nothing in this project banned and a
    `twinx` figure sailed straight through.

    Both scales are set by the author, so the crossing point of the two curves
    is an artifact of the limits chosen rather than anything in the data. Move
    the limits and the story changes; a reader cannot tell that from the figure.

    The escape hatch is the one legitimate case: a *pure unit relabel* - degrees
    C against degrees F, eV against nm - where the twin is furniture and carries
    no data of its own. So the discriminator is data on both, not a shared
    frame, which keeps the gate off `secondary_yaxis` and off correct work.
    """
    pairs = []
    for i, j in itertools.combinations(range(len(fig.axes)), 2):
        a, b = fig.axes[i], fig.axes[j]
        if any(abs(x - y) > FRAME_TOL for x, y in
               zip(a.get_position().bounds, b.get_position().bounds)):
            continue
        if _has_data(a) and _has_data(b):
            pairs.append(f"ax{i}+ax{j}")
    if not pairs:
        return True, "one data scale per frame"
    # "two scales", not "two y scales": `twiny` lands here on exactly the same
    # argument, and naming the wrong axis sends the reader looking for a defect
    # on the one that is fine.
    return False, (f"two data scales sharing a frame: {', '.join(pairs)}  <- "
                   "the crossing point is set by the limits, not the data. Two "
                   "panels, small multiples, or index both to a common base")


def check_form(fig):
    """The mechanical subset of form choice - the three cases where the form is
    wrong no matter what the data is. `references/choosing-a-form.md` carries
    the judgement calls this cannot make.
    """
    from matplotlib.container import BarContainer
    from matplotlib.patches import Wedge

    bad = []
    for i, ax in enumerate(fig.axes):
        if any(isinstance(p, Wedge) for p in ax.patches):
            bad.append(f"ax{i} pie/donut: angle and area are the two tasks the "
                       "eye judges worst - a dot plot or a bar reads as position")
        if hasattr(ax, "get_zlim"):
            bad.append(f"ax{i} 3D: perspective makes the encoding unreadable and "
                       "occludes data - facet or use color for the third variable")
        for con in getattr(ax, "containers", []):
            if not isinstance(con, BarContainer):
                continue
            vertical = getattr(con, "orientation", "vertical") == "vertical"
            lim = ax.get_ylim() if vertical else ax.get_xlim()
            scale = ax.get_yscale() if vertical else ax.get_xscale()
            # A log axis cannot include zero, so a log bar chart is truncated by
            # construction and this gate has nothing to say about it.
            if scale == "linear" and min(lim) > 0:
                axis = "y" if vertical else "x"
                bad.append(
                    f"ax{i} bars on a truncated {axis} axis (starts at "
                    f"{min(lim):.4g}): bar length encodes the value, so a "
                    "cut baseline misstates every ratio  <- the fix is the "
                    "form, not the axis - use a dot plot")
            break
    if not bad:
        return True, "no pie, no 3D, no truncated bar baseline"
    return False, "; ".join(bad)


def check_identity_channel(fig):
    """Identity carried by color and nothing else.

    A warning rather than a gate, and the reason is honesty about what the
    script can see: it can count the hues, but it cannot tell a direct label
    from any other piece of text in the axes. Failing on that guess would fire
    on correct work, and a gate people learn to skip is worse than no gate.
    """
    labeled = {h for h, label in _data_colors(fig) if label}
    if len(labeled) < 2:
        return True, "fewer than two identified series"
    if fig.legends or any(ax.get_legend() is not None for ax in fig.axes):
        return True, f"{len(labeled)} series, legend present"
    if any(ax.texts for ax in fig.axes):
        return True, f"{len(labeled)} series, in-axes text (assumed direct labels)"
    return "warn", (f"{len(labeled)} series told apart by hue alone - no legend "
                    "and no text in the axes. Direct labels beat a legend here: "
                    "they remove the match-the-swatch step, and orange and sky "
                    "blue are under 3:1 on white, where that step is hardest")


def _polyline_px(line, ax):
    """A line's vertices in display space, densified so no gap exceeds 2px.

    Vertices alone are not enough on a sparsely sampled line: two points 200px
    apart say nothing about the stroke between them, and that stroke is what the
    label actually lands next to.
    """
    import numpy as np
    xy = np.asarray(line.get_xydata(), dtype=float)
    if xy.ndim != 2 or len(xy) == 0:
        return None
    pts = ax.transData.transform(xy)
    pts = pts[np.isfinite(pts).all(axis=1)]
    if len(pts) < 2:
        return pts if len(pts) else None
    step = pts[1:] - pts[:-1]
    counts = np.maximum(1, np.ceil(np.hypot(step[:, 0], step[:, 1]) / 2.0)
                        ).astype(int)
    out = [p + (np.arange(k) / k)[:, None] * d
           for p, d, k in zip(pts[:-1], step, counts)]
    out.append(pts[-1:])
    return np.vstack(out)


def _legend_text_ids(fig):
    """Ids of every Text that belongs to a legend, figure-level or axes-level.

    A legend is a lookup key placed *away* from the curves by design, so its
    entries can never pass a proximity check - and they slip past the `t.axes is
    ax` guard, because a legend child's `.axes` resolves to the parent axes. The
    attribution check has to drop them explicitly or it fails every figure that
    keeps a legend."""
    ids = set()
    legends = list(fig.legends)
    for ax in fig.axes:
        lg = ax.get_legend()
        if lg is not None:
            legends.append(lg)
    for lg in legends:
        for t in lg.get_texts():
            ids.add(id(t))
    return ids


def _box_distance(bb, pts):
    """Shortest distance from a text's box to any point on a polyline, in px.
    Zero when the stroke passes under the text."""
    import numpy as np
    if len(pts) == 0:
        return float('inf')
    dx = np.maximum.reduce([bb.x0 - pts[:, 0], pts[:, 0] - bb.x1,
                            np.zeros(len(pts))])
    dy = np.maximum.reduce([bb.y0 - pts[:, 1], pts[:, 1] - bb.y1,
                            np.zeros(len(pts))])
    return float(np.min(np.hypot(dx, dy)))


def check_label_attribution(fig, r):
    """A direct label sitting nearer some other series than the one it names.

    `check_collisions` compares text against text, so a label that clears every
    other label and still floats in the corridor between two curves passes it
    clean. That is not hypothetical: `examples/demo.py` shipped with "Tuned"
    closer to a neighbouring curve than to its own and the whole suite was
    green. Text against text and text against data are different questions.

    Harvested narrowly on purpose - only text whose string matches exactly one
    series label is judged, because only there is the intent known. A callout,
    a panel letter, an "n = 300" attributes nothing to a curve, and failing
    those is the noise that teaches people to skim the row.

    The threshold is a ratio rather than a distance because the judgement the
    reader makes is comparative: a label is unambiguous when its own curve is
    plainly the closest thing to it, not when it is some absolute number of
    points away.
    """
    bad, checked = [], 0
    legend_ids = _legend_text_ids(fig)
    all_texts = _texts(fig, r)
    for ax in fig.axes:
        px = {}
        for line in ax.lines:
            if not line.get_visible():
                continue
            p = _polyline_px(line, ax)
            if p is not None and len(p):
                px[line] = p
        if len(px) < 2:
            continue

        lines_list = list(px.keys())
        owners = {}
        for i, line in enumerate(lines_list):
            owners.setdefault(str(line.get_label()).strip(), []).append(i)

        for t, bb in all_texts:
            if t.axes is not ax or id(t) in legend_ids:
                continue
            match = owners.get(str(t.get_text()).strip())
            if not match or len(match) != 1:
                continue
            own_line = lines_list[match[0]]
            checked += 1
            # A floor on the own-curve distance: without it a label printed
            # directly on its line divides by ~zero, and every other line in
            # the figure reads as infinitely far.
            d_own = max(_box_distance(bb, px[own_line]), 0.5)
            # The minimum over every OTHER curve, box-to-polyline. A KD-tree
            # over the pooled points was tried here for speed and was wrong:
            # it returns the nearest *points*, so for a label sitting close to
            # its own dense curve all the near points belong to that curve, no
            # other curve is ever reached, and `d_other` stays infinite. Which
            # is to say it passed every label it was closest to — the common
            # case, and the one the gate exists for.
            d_other = min(_box_distance(bb, p)
                          for line, p in px.items() if line is not own_line)
            if d_other < LABEL_MARGIN * d_own:
                bad.append(f"{str(t.get_text())[:22]!r} is {d_own:.0f}px from "
                           f"its own curve and {d_other:.0f}px from another")
    if not checked:
        return True, "no direct labels matched to a series"
    if not bad:
        return True, f"{checked} direct label{'s' if checked != 1 else ''}, "\
                     f"each nearest the curve it names"
    return False, ("; ".join(bad) + "  <- the reader resolves a direct label "
                   "by proximity, so it has to be plainly nearest its own "
                   "curve. Move it to where that curve is furthest from its "
                   "neighbours, or draw a leader line to the anchor")


# --- the sheet itself -------------------------------------------------------

def _style_sheet():
    """`STYLE_SHEET` if the project set one, else `figure.mplstyle` as the skill
    tells you to lay it out (beside this script), and as this repository lays it
    out (`assets/` next to `scripts/`).

    A configured path is returned whether or not it exists: a sheet named and
    missing is a mistake worth a row, not a silent fall-through to a sheet the
    project did not ask for.
    """
    if STYLE_SHEET is not None:
        return Path(STYLE_SHEET)
    here = Path(__file__).resolve().parent
    for cand in (here / "figure.mplstyle",
                 here.parent / "assets" / "figure.mplstyle"):
        if cand.is_file():
            return cand
    return None


def _is_dashed_linestyle(ls):
    """True if a linestyle value is not solid.

    Accepts strings ('dashed', '--', '-.', ':') and (offset, dashes) tuples.
    """
    if isinstance(ls, str):
        return ls.lower() not in ("solid", "-", "", "none")
    if isinstance(ls, (tuple, list)):
        if len(ls) < 2:
            return False
        dashes = ls[1]
        return dashes is not None and bool(dashes)
    return False


def _negative_levels_are_dashed(cs):
    """Whether a ContourSet ships its negative levels dashed.

    Asked of the strokes the set actually drew — `get_linestyle()` returns one
    (offset, dashes) per level, and a `dashes` of None is solid — rather than
    inferred from `negative_linestyles`. The artist is the thing that decides,
    and reading it is what keeps this gate honest about the case matplotlib
    silently handles for you.

    Falls back to the configured `negative_linestyles` when the drawn styles do
    not line up one-per-level (matplotlib broadcasts a single entry, and older
    versions did so more often), so the gate degrades to the previous, coarser
    reading rather than to no reading at all.
    """
    levels = getattr(cs, "levels", None)
    if levels is None or len(levels) == 0:
        return False
    negative = [i for i, lv in enumerate(levels) if lv < 0]
    if not negative:
        return False

    try:
        drawn = list(cs.get_linestyle())
    except (AttributeError, TypeError):
        drawn = []
    if len(drawn) == len(levels):
        return any(_is_dashed_linestyle(drawn[i]) for i in negative)

    if not getattr(cs, "monochrome", False):
        return False
    nl = getattr(cs, "negative_linestyles", None)
    if nl is None:
        return False
    # A scalar (string or tuple) or a list; any non-solid entry triggers.
    styles = nl if isinstance(nl, list) else [nl]
    return any(_is_dashed_linestyle(s) for s in styles)


def check_contour_dash(fig):
    """Negative-level contours auto-dash via matplotlib default.

    In a monochrome contour, `rcParams["contour.negative_linestyle"]` is
    "dashed" by default, so negative-Z contours ship dashed isolines nobody
    chose. The skill's own convention is dashing = unobserved / projected /
    threshold, making this a silent semantic error every existing gate misses.

    Non-monochrome (colored) contours are always solid and unaffected.

    The condition used to be that EVERY level was non-positive, which is the
    one shape a genuinely signed field never has: `contour` over data spanning
    zero draws levels either side of it, matplotlib dashes the negative half,
    and the gate skipped the figure entirely. It fired only on data that is
    non-positive throughout — which is what the original test drew, so the hole
    was invisible from inside the suite. The rule is now "any negative level",
    asked of the drawn strokes.
    """
    from matplotlib.contour import ContourSet

    warned = []
    for i, ax in enumerate(fig.axes):
        for c in ax.collections:
            if not isinstance(c, ContourSet):
                continue
            if _negative_levels_are_dashed(c):
                warned.append(
                    f"ax{i}: negative-level contours auto-dashed — dashing "
                    "reads as projected/unobserved here; pass "
                    'linestyles="solid" to contour on signed data')
                break

    if not warned:
        return True, "no auto-dashed negative contours"
    return "warn", "; ".join(warned)


def check_line_weight(fig, scale=None, placed_frac=1.0, venue=None):
    """Every drawn stroke against the printer's floor, measured ON THE PAGE.

    SIAM states it plainly in its instructions for authors: illustrations must
    use lines one point or thicker, because thinner lines break up or disappear.
    It is the same failure as the type floor and it has the same cause — a
    stroke authored at 0.8pt in a 9-inch figure placed at 5.5 inches prints at
    0.49pt — so it is measured the same way, through `page_scale`.

    Furniture is held to a lower floor than data. A gridline that drops out at
    the printer costs the reader a reference; a data curve that drops out costs
    them the finding. The sheet ships the grid at 0.7pt deliberately, and
    failing it against the data floor would be failing the sheet's own design.
    """
    from matplotlib.lines import Line2D
    from matplotlib.collections import LineCollection

    if scale is None:
        scale = page_scale(fig, placed_frac, venue)

    thin, widths = [], []
    for ax in fig.axes:
        # A colorbar's dividers ship at 0.4pt and are matplotlib's, not
        # anybody's design decision — the same reason `check_ink` skips this
        # axes entirely.
        if ax.get_label() == "<colorbar>":
            continue
        gridlines = {id(g) for axis in (ax.xaxis, ax.yaxis)
                     for g in axis.get_gridlines()}
        for artist in list(ax.lines) + list(ax.collections):
            if not artist.get_visible() or id(artist) in gridlines:
                continue
            if isinstance(artist, Line2D):
                stroke = str(artist.get_linestyle()).strip().lower()
                if stroke in ("none", "", " "):
                    continue
                raw = [artist.get_linewidth()]
            elif isinstance(artist, LineCollection):
                raw = list(artist.get_linewidth())
            elif getattr(artist, "filled", None) is False:
                # An unfilled ContourSet is strokes. A *filled* one is bands
                # whose linewidth is the seam between two fills, which no
                # reader is being asked to see.
                raw = list(artist.get_linewidth())
            else:
                continue
            for w in raw:
                on_page = float(w) * scale
                if on_page <= 0:
                    continue
                widths.append(on_page)
                if on_page < LINE_FLOOR_PT:
                    name = str(artist.get_label() or "")
                    thin.append(f"{name if name and not name.startswith('_') else 'a stroke'}"
                                f" at {on_page:.2f}pt")

    if not widths:
        return True, "no strokes to measure"
    if not thin:
        return True, (f"{len(widths)} strokes, thinnest {min(widths):.2f}pt on "
                      f"page (floor {LINE_FLOOR_PT})")
    seen = list(dict.fromkeys(thin))
    return False, (f"under {LINE_FLOOR_PT}pt on page at scale {scale:.2f}: "
                   f"{seen[:4]}  <- SIAM: lines thinner than one point break up "
                   "or disappear in print")


# The names matplotlib gives a colormap it built itself, from colours the
# author handed to an artist. `contour(colors=[...])` produces one, and it must
# not be read as a colour encoding: three near-black levels are one encoding in
# one hue, not three categories, and classifying them qualitative fails them
# against the all-pairs separation floor.
#
# The name is version-dependent and that is why this is a list rather than one
# string. matplotlib 3.8.4, 3.9.4 and 3.10.0 call it "from_list"; 3.11.1 calls
# it "unnamed". Shipping only the 3.11 spelling is what put every contour
# figure - including `gallery-field.png` - into a hard FAIL on the two CI jobs
# that run older matplotlib, while every local run on 3.11 stayed green.
# `test_matplotlib_still_names_an_author_built_colormap_something_we_skip`
# fails loudly if a future version invents a fourth spelling.
ANONYMOUS_CMAP_NAMES = ("_no_name", "unnamed", "from_list", None)


def check_colormap(fig):
    try:
        import check_palette as cp
    except ImportError:
        return True, ("check_palette.py is not importable beside this file, "
                      "so no colormap was classified")

    from matplotlib.colors import to_hex

    seen = {}
    for ax in fig.axes:
        if ax.get_label() == "<colorbar>":
            continue
        for artist in list(ax.images) + list(ax.collections):
            if not artist.get_visible():
                continue
            if getattr(artist, "get_array", lambda: None)() is None:
                continue
            cmap = getattr(artist, "get_cmap", lambda: None)()
            if cmap is not None:
                name = getattr(cmap, "name", "")
                # An unnamed colormap means the artist has explicit colours set
                # (e.g. `contour(colors="black")`), rather than a continuous
                # encoding named by the author.
                if not name or name in ANONYMOUS_CMAP_NAMES:
                    continue
                seen.setdefault(name, cmap)

    if not seen:
        return True, "no colormapped artists"

    fails, notes = [], []
    for name, cmap in sorted(seen.items()):
        if cmap.N < cp.CMAP_QUALITATIVE_N:
            levels = [to_hex(cmap(i)) for i in range(cmap.N)]
        else:
            levels = [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
                      for i in range(cp.CMAP_SAMPLES)]

        kind = cp.cmap_kind(levels)

        if kind == "misc":
            fails.append(
                f"{name}: lightness reverses over "
                f"{cp.cmap_back_travel(levels):.0%} of its span  <- a reader "
                "cannot order two values in it. viridis for sequential, RdBu "
                "for diverging, twilight for cyclic")
            continue

        if kind == "qualitative":
            _, rows = cp.check(levels, all_pairs=True)
            bad = [detail.split("  <-")[0].strip()
                   for row_name, status, detail in rows
                   if row_name.startswith(("CVD separation",
                                            "Normal-vision floor"))
                   and status is False]
            if bad:
                fails.append(f"{name} ({cmap.N} categories): " + "; ".join(bad)
                             + "  <- an image puts every category beside every "
                             "other, so every pair has to separate")
                continue

        notes.append(f"{name} {kind}")

    if fails:
        return False, "; ".join(fails)
    return True, ", ".join(notes)


def check_fonts(fig):
    """Two silent failures between the figure on screen and the file you submit.

    *Type 3.* Matplotlib defaults `pdf.fonttype` and `ps.fonttype` to 3. IEEE,
    ACM and Elsevier all reject submissions carrying Type 3 fonts, and IEEE PDF
    eXpress fails the upload outright. Nothing warns you: the figure renders
    identically, and the paper bounces at the latest and most expensive possible
    moment. Type 42 embeds TrueType outlines instead. `figure.mplstyle` sets it;
    this catches the project that did not copy the sheet, and the notebook that
    called `rcParams.update` afterwards.

    *Silent substitution.* When none of the faces named in `font.<family>` is
    installed, matplotlib falls back to its own default and logs nothing at
    default verbosity. The guide calls the typeface the single largest visual
    lever in the whole method, so a figure set in DejaVu because someone named
    "Times New Roman" on a machine that does not have it is the lever quietly
    disengaged. Falling back *within* the named list is not flagged — that is
    what a fallback list is for, and the sheet ships one on purpose.

    A warning rather than a gate, for the same reason `check_style_sheet` is:
    both read the *global* rcParams rather than anything the figure carries, so
    neither can tell a figure built under someone else's settings from a figure
    built under none. A figure that will only ever be a PNG in a README is also
    genuinely unaffected by the PDF font type. What is gated instead is the
    thing this repo controls — the shipped `figure.mplstyle` declares 42, and
    the suite fails if that line ever goes missing.
    """
    import matplotlib as mpl
    from matplotlib.font_manager import FontProperties, findfont, get_font

    notes = []
    type3 = [k for k in ("pdf.fonttype", "ps.fonttype")
             if int(mpl.rcParams[k]) == 3]
    if type3:
        notes.append(f"{' and '.join(type3)} = 3 (Type 3)  <- IEEE PDF eXpress "
                     "rejects the upload and ACM/Elsevier reject the "
                     "submission; set both to 42")

    family = mpl.rcParams["font.family"]
    generic = family[0] if isinstance(family, (list, tuple)) else family
    wanted = list(mpl.rcParams.get(f"font.{generic}", []))
    if wanted:
        try:
            got = get_font(findfont(FontProperties(family=generic))).family_name
        except Exception:
            got = None
        if got is not None and not any(got.lower() == w.lower() for w in wanted):
            notes.append(f"asked for {wanted[:3]}, rendering in {got!r} — none "
                         "of the named faces is installed on this machine")

    if notes:
        return "warn", "; ".join(notes)
    return True, f"Type 42 embedding, {generic} face resolves within the list"


ALT_TEXT_ATTR = "_figure_gate_alt"
# Under this many characters a description is naming the figure, not describing
# it. "Validation loss" is a title; the alt text has to carry what the reader
# would have taken from looking.
ALT_TEXT_MIN_CHARS = 60


def describe(fig, text):
    """Attach a text description to a figure, for readers who cannot see it.

    Across 100,000 public Jupyter notebooks, 99.81% of programmatically
    generated images shipped with no alt text at all, and the overwhelming
    majority of them were matplotlib. Matplotlib has no field for this, so the
    description is stashed on the figure and handed to `savefig`:

        describe(fig, "Validation loss against training epoch for three "
                      "optimisers. All three fall; the Bayesian run reaches "
                      "0.05 by epoch 6, the baseline is still at 0.25 at 12.")
        fig.savefig(path, metadata=alt_metadata(fig, path))

    Say what the reader would have taken from looking, not what the figure is
    made of. "A line chart with three lines" describes the file; the numbers
    and the direction describe the finding.
    """
    setattr(fig, ALT_TEXT_ATTR, str(text))
    return fig


# What each output format does with a description, measured rather than
# assumed. `test_alt_metadata_matches_what_each_format_accepts` saves a real
# figure in every format named here and checks the result, because three of
# these five behaviours are ones no documentation states:
#
#   png            any key, lands in a tEXt chunk
#   pdf            a closed info dictionary (PDF 1.7 §14.3.3). `Description` is
#                  not in it: matplotlib warns "Unknown infodict keyword" on
#                  every save. `Subject` is the slot that carries a description
#   svg / svgz     a Dublin Core subset. `Description` lands -- and `Subject`
#                  RAISES ValueError, so the pdf spelling cannot just be used
#                  everywhere
#   ps / eps       accepts the kwarg and carries nothing into the file
#   jpg and the
#   other rasters  `metadata=` RAISES ValueError for any key at all
#
# That last row is why this is a table and not a default: the documented call
# is `savefig(path, metadata=alt_metadata(fig, path))`, and handing a non-empty
# dict to a jpeg save turns the happy path into a traceback.
ALT_TEXT_KEY_BY_SUFFIX = {
    ".png": "Description",
    ".pdf": "Subject",
    ".svg": "Description",
    ".svgz": "Description",
}
ALT_TEXT_KEY_DEFAULT = "Description"
# Formats that either drop the description or reject the kwarg outright. Named
# rather than inferred from "not in the table above", so that an unrecognised
# suffix keeps the old behaviour instead of silently losing the description.
ALT_TEXT_UNSUPPORTED_SUFFIXES = frozenset({
    ".ps", ".eps",                                    # carried nowhere
    ".jpg", ".jpeg", ".webp", ".tif", ".tiff",        # raise on any key
    ".raw", ".rgba", ".pgf",
})


def _savefig_suffix(path):
    """The lowercased suffix of a savefig target, or None when there is not one.

    `savefig` also takes an open file or a buffer. An open file knows the name
    it was opened under; a `BytesIO` does not, and its format lives in a
    `format=` kwarg this function never sees. None means "no format to read",
    which the caller treats the same as being passed no path at all.
    """
    import os

    name = getattr(path, "name", path)
    if not isinstance(name, (str, os.PathLike)):
        return None
    return Path(os.fspath(name)).suffix.lower() or None


def alt_metadata(fig, path=None):
    """The `metadata=` dict for `savefig`, carrying whatever `describe` set.

    Pass the same `path` you are about to save to, so the description lands in
    a field the target format actually has:

        fig.savefig(path, metadata=alt_metadata(fig, path))

    PNG, PDF and SVG all keep a description and none of them agrees with the
    others about what to call it, so the key is chosen from the suffix.

    For a format that carries no description -- ps, or any of the rasters --
    this returns `None` rather than an empty dict, and the difference is not
    cosmetic. matplotlib's guard is `elif metadata is not None: raise`, so an
    empty dict is rejected exactly as hard as a full one; `savefig(path,
    metadata={})` on a jpeg is a traceback. `None` is `savefig`'s own default
    for the argument and the only value those formats accept.

    Called without a path, or with a buffer whose format cannot be read, it
    returns `Description`. That is right for PNG and SVG and is what every
    earlier version returned unconditionally.
    """
    # Before the empty-description check, because a format that rejects the
    # kwarg rejects `{}` too -- the figure having nothing to say does not make
    # the jpeg save survive.
    suffix = _savefig_suffix(path) if path is not None else None
    if suffix in ALT_TEXT_UNSUPPORTED_SUFFIXES:
        return None
    text = getattr(fig, ALT_TEXT_ATTR, None)
    if not text:
        return {}
    if suffix is None:
        return {ALT_TEXT_KEY_DEFAULT: text}
    return {ALT_TEXT_KEY_BY_SUFFIX.get(suffix, ALT_TEXT_KEY_DEFAULT): text}


def check_alt_text(fig):
    """Whether the figure carries a description for a reader who cannot see it.

    A warning rather than a gate, and deliberately: on a paper the description
    frequently *is* the caption, and the caption lives in the .tex file where
    this cannot see it. Hard-failing every figure in that entirely reasonable
    setup is how a row becomes something everyone learns to skip, which is worse
    than not having it. Where there is no caption — a notebook, a README, a
    slide, a web page — nothing else is carrying this and the row is the only
    thing that will say so.
    """
    text = str(getattr(fig, ALT_TEXT_ATTR, "") or "").strip()
    if not text:
        return "warn", ("no description attached  <- describe(fig, \"...\") "
                        "and pass alt_metadata(fig, path) to savefig; if the "
                        "document's caption carries it, this row is discharged")
    if len(text) < ALT_TEXT_MIN_CHARS:
        return "warn", (f"description is {len(text)} characters — that is a "
                        "title, not a description of what the reader would "
                        "have seen")
    return True, f"described in {len(text)} characters"


def check_style_sheet(fig):
    """Every key in the sheet against the rcParams that are actually in effect.

    Three separate silent failures land here at once: a color written with a
    leading `#` (which is a comment in this format, so matplotlib keeps its own
    default), a forgotten `plt.style.use`, and an rcParams override applied
    later. All three ship stock matplotlib while every other check passes.

    A warning, not a gate, for one honest reason: a figure built on a *different*
    project's sheet is correct work, and this compares against the global
    rcParams rather than what the figure was drawn under, so a figure built
    inside an `rc_context` that has since exited reads as drift when it is not.
    Both make a hard failure the wrong instrument. The row names the keys.
    """
    import matplotlib as mpl
    path = _style_sheet()
    if path is None:
        return True, "no figure.mplstyle beside this script, nothing to compare"
    if not path.is_file():
        return "warn", (f"STYLE_SHEET is set to {path}, which is not a file: "
                        "nothing was compared, and the sheet you meant is not "
                        "the one in effect either")
    written = mpl.rc_params_from_file(path, use_default_template=False)
    drift = []
    for key, value in written.items():
        try:
            same = mpl.rcParams[key] == value
        except KeyError:
            continue
        if not isinstance(same, bool):        # a numpy array of comparisons
            # B023 reads the lambda as capturing the loop variable late. It is
            # called on the same line it is built, before the loop advances, so
            # there is no later binding for it to see.
            same = bool(getattr(same, "all", lambda: same)())  # noqa: B023
        if not same:
            drift.append(key)
    if not drift:
        return True, f"all {len(written)} keys match {path.name}"
    return "warn", (f"{len(drift)} of {len(written)} keys differ from "
                    f"{path.name}: {sorted(drift)[:5]}"
                    f"{' ...' if len(drift) > 5 else ''}  <- the sheet is not "
                    "the one in effect: check plt.style.use, and check no color "
                    "in the sheet was written with a leading #")


# Everything `audit` can hand a gate, named once. A gate asks for a subset of
# these in its `needs`, and a gate that takes one of them without asking runs on
# the default instead - measuring against a 1.0 page scale, say, on a figure
# placed at half width. The test suite reads this to catch that.
GATE_INPUTS = ("r", "canvas", "scale", "placed_frac", "venue", "context_axes")


class Gate(NamedTuple):
    """One row of the audit: what it is called, what runs it, what it needs.

    `needs` is the part worth having. The gates do not take the same arguments
    - some want the renderer, some the already-drawn canvas, some the page
    scale - and for as long as `audit` spelled each call out by hand, that
    variation was twenty hand-written argument lists nobody could see the shape
    of. Declaring it makes the variation data: `audit` supplies what a gate
    asks for, and a new gate says what it wants rather than being wired in.

    The signatures themselves stay as they are. A gate that takes a renderer
    says so in its own parameters, and `check_ink(fig, context_axes=[ax])` is a
    call the style guide teaches a reader to write. Hiding both behind one
    context object would cost more than the uniformity is worth.
    """
    name: str
    func: object
    advisory: bool = False
    needs: tuple = ()


GATES = (
    Gate("Clipping", check_clipping, needs=("r",)),
    Gate("Text collision", check_collisions, needs=("r",)),
    Gate("Text readability", check_text_readability,
         needs=("r", "canvas", "scale", "placed_frac", "venue")),
    Gate("Contrast stack", check_contrast_stack),
    Gate("Mark ratio", check_mark_ratio),
    Gate("Overplotting", check_overplotting, advisory=True),
    Gate("Axis redundancy", check_redundancy, needs=("r",)),
    Gate("Type size", check_type_size,
         needs=("r", "scale", "placed_frac", "venue")),
    Gate("Line weight", check_line_weight,
         needs=("scale", "placed_frac", "venue")),
    Gate("Ink coverage", check_ink, advisory=True,
         needs=("context_axes", "canvas")),
    Gate("Series color", check_series_color),
    Gate("Dual axis", check_dual_axis),
    Gate("Form", check_form),
    Gate("Identity channel", check_identity_channel, advisory=True),
    Gate("Label attribution", check_label_attribution, needs=("r",)),
    Gate("Style sheet", check_style_sheet, advisory=True),
    Gate("Contour dash", check_contour_dash, advisory=True),
    Gate("Colormap kind", check_colormap),
    Gate("Fonts", check_fonts, advisory=True),
    Gate("Alt text", check_alt_text, advisory=True),
)

ADVISORY_GATES = _advisory_gates()


def audit(fig, scale=None, placed_frac=1.0, context_axes=None, venue=None):
    """Run every gate over a figure. Returns `(ok, rows)`.

    `check_palette.check` returns the same shape. It returned `(rows, ok)`
    until 0.4.0, and unpacking either one the wrong way binds a bool to the
    rows and raises nothing at the call site, which is why they were made to
    agree rather than documented as differing.

    `rows` are `(label, status, detail)`, one per gate, in the order the report
    prints them. `status` is True, False, or the string "warn"; only a hard
    False sets `ok` to False, so an advisory row reports without gating a
    build.

    `placed_frac` is the fraction of the content width the figure is placed at,
    and `venue` names a row of `VENUE_WIDTH_PT` instead of setting
    `CONTENT_WIDTH_PT` by hand; between them they decide the page scale every
    type and stroke measurement runs through. `scale` overrides that
    calculation outright. `context_axes` names axes whose fill is a context
    surface rather than data ink, which is what stops a filled contourf panel
    reading as saturated.
    """
    r, canvas = _renderer(fig)
    available = dict(zip(GATE_INPUTS,
                         (r, canvas, scale, placed_frac, venue, context_axes)))
    # Passed by name, not by position. The gates take these in different
    # orders, and a registry that supplied them positionally would hand a
    # renderer to a `scale` parameter the moment a signature was reordered,
    # which is a wrong number rather than an exception.
    rows = [(gate.name, *gate.func(fig, **{n: available[n]
                                           for n in gate.needs}))
            for gate in GATES]
    # "warn" rows are advisory: they report something worth a look without
    # failing the build. Only a hard False gates.
    return all(s is not False for _, s, _ in rows), rows


def report(fig, name="", scale=None, placed_frac=1.0, context_axes=None,
           venue=None):
    """`audit()`, printed. Returns the same `ok` bool and nothing else.

    The arguments are `audit`'s, plus `name` for the heading. Advisory rows
    print as WARN and do not change the verdict, so a figure can be COMPOSED
    with advisories; only a hard FAIL makes this return False.

    This is what the examples and the CLI call. Use `audit()` when the rows
    themselves are wanted rather than a printed table.
    """
    ok, rows = audit(fig, scale, placed_frac, context_axes, venue)
    print(f"\nComposition audit{': ' + name if name else ''}")
    warned = False
    for label, status, detail in rows:
        tag = "WARN" if status == "warn" else ("PASS" if status else "FAIL")
        warned = warned or status == "warn"
        print(f"  [{tag}] {label:<18} {detail}")
    verdict = "COMPOSED" if ok else "FIX THE MARKED CHECKS"
    if ok and warned:
        verdict += " (with advisories)"
    print(f"\n  -> {verdict}\n")
    return ok


def self_test_figure():
    """A figure that breaks several checks on purpose.

    Kept as a function rather than inlined under __main__ so the test suite can
    assert the gate still fails on it. A gate nobody has watched fail is
    decoration, and this one silently stopped working twice while it was being
    written.
    """
    import matplotlib.pyplot as plt
    fig, (a, b) = plt.subplots(1, 2, figsize=(4, 2))
    for ax in (a, b):
        ax.scatter([1, 2, 3], [1, 2, 3], s=12, alpha=0.4)
        ax.scatter([2], [2], marker="*", s=400, alpha=0.7)
        ax.set_xlabel("a very long axis label that will not fit")
        ax.set_ylabel("Batch size")
    return fig


def main():
    """Run the self-test. Exits 0 when the gate correctly rejects a bad figure,
    so `check-figure` in a build verifies the checker itself is still working."""
    import sys
    # Before the matplotlib import, not after: `--venues` prints a dict of
    # numbers and needs nothing installed to do it. Asking for it on a machine
    # without matplotlib used to hit the install message instead.
    if "--venues" in sys.argv:
        print("\nContent widths, in points. Pass one as venue= to audit().")
        print("Verify against `\\the\\textwidth` in your own document before "
              "trusting one for anything that matters.\n")
        for name, pt in sorted(VENUE_WIDTH_PT.items()):
            print(f"  {name:<16} {pt:>7.2f} pt   ({pt / 72:.2f} in)")
        print()
        return

    try:
        import matplotlib
    except ImportError:
        raise SystemExit(
            "check_figure.py needs matplotlib (numpy comes with it; scipy is "
            "optional and only a speed-up):\n"
            "    pip install matplotlib\n\n"
            "The composition RULES are library-agnostic and written up in the "
            "style guide; only this automated check is matplotlib-specific. On "
            "another plotting stack, apply the rules by hand or port the "
            "checks - each one reads geometry any library can report.") from None

    matplotlib.use("agg")
    composed = report(self_test_figure(), "self-test (expected: FAIL)")
    if composed:
        raise SystemExit(
            "The self-test figure passed, which means the checker is broken.")
    print("  The gate correctly rejected a deliberately bad figure.\n")


if __name__ == "__main__":
    main()
