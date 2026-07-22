"""Composition checks for a rendered matplotlib figure.

`check_palette.py` answers "are these colors legal". This answers "is this
figure composed". They fail on different things: a figure can clear every
palette, type-size and ornament gate and still land as a washed-out smudge with
its axis label sliced off.

Every check here is mechanical and reads the figure's own artists, so it runs in
a test rather than in a design review.

    from check_figure import audit
    ok, rows = audit(fig)

    python check_figure.py            # self-test on a deliberately bad figure

Checks
    1. Clipping        - no text extends past the canvas
    2. Text collision  - no two text bounding boxes overlap
    3. Contrast stack  - something is at full opacity; alpha levels are few
    4. Mark ratio      - largest / smallest mark area within MARK_RATIO_MAX
    5. Redundancy      - shared-axis panels do not repeat a tick label column
    6. Type size       - every rendered string clears the floor once scaled
    7. Ink coverage    - the data region is neither empty nor packed
    8. Series color    - the drawn hues separate under color blindness
    9. Dual axis       - no second y scale carrying data of its own
   10. Style sheet     - figure.mplstyle is the one actually in effect
   11. Form            - no pie, no 3D, no truncated bar baseline
   12. Identity        - series are not told apart by color alone
"""

import itertools
from collections import Counter
from pathlib import Path

MARK_RATIO_MAX = 5.0        # area ratio of largest to smallest data mark
ALPHA_LEVELS_MAX = 3        # distinct transparency levels in one figure
INK_MIN, INK_MAX = 0.02, 0.55   # fraction of the axes area carrying data ink

# The theme has six categorical slots and the guide's claim is that there is no
# seventh: a generated hue is indistinguishable from an existing slot under
# simulated color blindness. Until now that claim was prose only.
MAX_SERIES_HUES = 6

# Ink and furniture from `figure.mplstyle`. These land in `ax.lines` and
# `ax.patches` beside the data - reference rules, annotation boxes, spine-colored
# strokes - and none of them carries a categorical identity, so counting them as
# a data hue would fail figures for the color of their own furniture.
INK_TOKENS = {"#000000", "#52514e", "#898781",     # ink primary/secondary/muted
              "#e1e0d9", "#c3c2b7", "#ffffff"}     # grid, axis, surface

# Two axes are the same frame when their bounds agree this closely. An inset or
# a colorbar never does; `twinx`/`twiny` always does.
FRAME_TOL = 1e-3

# Type floor, in points ON THE PAGE, after the figure is scaled to fit.
TYPE_FLOOR_PT = 7.5

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


def page_scale(fig, placed_frac=1.0):
    """Scale from authored inches to points on the page.

    `placed_frac` is the fraction of the content width the figure is placed at,
    so it reads like the call site: `\\includegraphics[width=0.48\\textwidth]`
    is `placed_frac=0.48`. Without it every figure is measured as if it were
    full width, and a half-width figure is certified at twice the type size it
    actually ships at - which is the wrong direction for a legibility gate to
    be wrong in.
    """
    if CONTENT_WIDTH_PT is None:
        if placed_frac != 1.0:
            raise ValueError(
                "placed_frac requires CONTENT_WIDTH_PT to be set. With it None "
                "the checker assumes you authored the figure at the width it "
                "is placed at, which already makes the scale 1.0; a fractional "
                "placement contradicts that. Set CONTENT_WIDTH_PT, or author "
                "at the placed width and drop placed_frac.")
        return 1.0
    return CONTENT_WIDTH_PT * placed_frac / (fig.get_size_inches()[0] * 72)


def _renderer(fig):
    """Text extents need a renderer that can measure. The SVG canvas cannot, so
    swap in an Agg one when that is what the figure was built under."""
    if hasattr(fig.canvas, "get_renderer"):
        fig.canvas.draw()
        return fig.canvas.get_renderer()
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    return canvas.get_renderer()


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
    in points, so squared to match). Bars and other patches are deliberately
    NOT counted: a bar thirty times another bar is the encoding working, not a
    defect. This gate is about marks whose size is not carrying the value.
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
                sizes.append(ms ** 2)
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
            tuple(t.get_text() for t in a.get_yticklabels() if t.get_text())
            for a in axes)
        dup_ticks += sum(n - 1 for v, n in cols_seen.items() if v and n > 1)

    ok = not dupes and not dup_ticks
    if ok:
        return True, "axis furniture not duplicated"
    bits = dupes + ([f"repeated y tick column x{dup_ticks}"] if dup_ticks else [])
    return False, "; ".join(bits) + "  <- use sharex/sharey"


def check_type_size(fig, r, scale=None, placed_frac=1.0):
    """Every rendered string clears the legibility floor once the figure is
    scaled into the document.

    This used to be a regex over the source file hunting for `fontsize=`, which
    missed anything set through rcParams, anything computed, and anything set by
    a helper. Reading `get_fontsize()` off the artists that actually rendered
    reports what is on the page instead of what is in the source.
    """
    scale = page_scale(fig, placed_frac) if scale is None else scale
    ghosts = _ghost_ticks(fig)
    sizes = [(round(float(t.get_fontsize()) * scale, 1), str(t.get_text())[:22])
             for t, _ in _texts(fig, r) if id(t) not in ghosts]
    if not sizes:
        return True, "no text"
    small = sorted({(pt, s) for pt, s in sizes if pt < TYPE_FLOOR_PT})
    mn = min(pt for pt, _ in sizes)
    if not small:
        return True, f"smallest {mn:.1f}pt on page (floor {TYPE_FLOOR_PT})"
    return False, (f"under {TYPE_FLOOR_PT}pt on page at scale {scale}: {small[:4]}"
                   "  <- cut words, do not shrink type")


def check_ink(fig):
    """Ink as a fraction of each plotting area, measured off the rendered
    pixels rather than estimated from artist properties.

    Near zero means a panel that did not need to be a panel. Very high means a
    panel with no ground left in it. Reported per-axes, and advisory only: the
    right density genuinely depends on the form, so this flags panels worth a
    second look rather than declaring them wrong.
    """
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = np.asarray(canvas.buffer_rgba())[:, :, :3].astype(int)
    h = buf.shape[0]
    bg = buf[0, 0]
    # anything more than a few levels off the page color counts as ink
    ink_mask = (np.abs(buf - bg).sum(axis=2) > 24)

    rows = []
    for i, ax in enumerate(fig.axes):
        bb = ax.get_window_extent(renderer=canvas.get_renderer())
        x0, x1 = int(max(bb.x0, 0)), int(min(bb.x1, buf.shape[1]))
        y0, y1 = int(max(bb.y0, 0)), int(min(bb.y1, h))
        # Agg's origin is top-left, the figure's is bottom-left
        sub = ink_mask[h - y1:h - y0, x0:x1]
        if sub.size == 0:
            continue
        frac = float(sub.mean())
        rows.append((i, frac, INK_MIN <= frac <= INK_MAX))

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


def _data_colors(fig):
    """`(hex, label)` for every color on the figure that carries a categorical
    identity. `label` is None for an artist matplotlib named itself.

    Harvested narrowly on purpose. Two exclusions do the work:

    - an artist with a colormap attached (`get_array()` is not None) encodes a
      *value*, not an identity - a heatmap or a scatter colored by magnitude is
      a continuous encoding and answers to the viridis rule instead
    - the ink tokens, per `INK_TOKENS` above
    """
    out = []
    for ax in fig.axes:
        for artist in list(ax.lines) + list(ax.patches) + list(ax.collections):
            if not artist.get_visible():
                continue
            if getattr(artist, "get_array", lambda: None)() is not None:
                continue
            raw = str(artist.get_label() or "")
            label = raw if raw and not raw.startswith("_") else None
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
                    if h and h not in INK_TOKENS:
                        out.append((h, label))
    return out


def _compares_all_pairs(fig):
    """Which separation mode the figure needs. `check_palette.py` has to ask for
    this on the command line because a list of hexes does not say what it will be
    drawn as; a built figure does say. Scatter puts every series next to every
    other, so every pair has to separate. Lines and bars only ever put
    neighbours next to each other, and gating all pairs there would fail
    palettes the guide explicitly sanctions."""
    from matplotlib.collections import PathCollection
    return any(isinstance(c, PathCollection)
               for ax in fig.axes for c in ax.collections)


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
    """
    harvested = _data_colors(fig)
    if not harvested:
        return True, "no categorical series colors"

    distinct = list(dict.fromkeys(h for h, _ in harvested))
    plural = "s" if len(distinct) != 1 else ""
    fails, notes = [], []

    if len(distinct) > MAX_SERIES_HUES:
        fails.append(f"{len(distinct)} distinct data hues, theme has "
                     f"{MAX_SERIES_HUES}  <- fold the tail into 'Other' or facet")

    # One hue carrying two identities is what a seventh series looks like once
    # the cycler wraps: matplotlib reuses slot 1 without complaint and the
    # legend confidently lists both. Keyed on the label text rather than a count,
    # so one entity drawn as several artists in one color stays legal.
    identities = {}
    for h, label in harvested:
        if label:
            identities.setdefault(h, set()).add(label)
    for h, labels in sorted(identities.items()):
        if len(labels) > 1:
            fails.append(f"{h} carries two identities {sorted(labels)}"
                         "  <- the color cycle wrapped")

    if len(distinct) >= 2:
        try:
            import check_palette as cp
        except ImportError:
            notes.append("check_palette.py is not importable beside this file, "
                         "so separation went unchecked")
        else:
            mode = "all-pairs" if _compares_all_pairs(fig) else "adjacent"
            rows, _ = cp.check(distinct, all_pairs=(mode == "all-pairs"))
            for name, status, detail in rows:
                if not name.startswith(("CVD separation", "Normal-vision floor")):
                    continue
                if status is False:
                    fails.append(detail)
                else:
                    notes.append(detail.split("  <-")[0].strip())

    head = f"{len(distinct)} data hue{plural}"
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
    return False, (f"two y scales sharing a frame: {', '.join(pairs)}  <- the "
                   "crossing point is set by the limits, not the data. Two "
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


LABEL_MARGIN = 2.0


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


def _box_distance(bb, pts):
    """Shortest distance from a text's box to any point on a polyline, in px.
    Zero when the stroke passes under the text."""
    import numpy as np
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
        owners = {}
        for line in px:
            owners.setdefault(str(line.get_label()), []).append(line)
        for t, bb in _texts(fig, r):
            if t.axes is not ax:
                continue
            match = owners.get(str(t.get_text()).strip())
            if not match or len(match) != 1:
                continue
            own = match[0]
            checked += 1
            # A floor on the own-curve distance: without it a label printed
            # directly on its line divides by ~zero, and every other line in the
            # figure reads as infinitely far.
            d_own = max(_box_distance(bb, px[own]), 0.5)
            d_other = min(_box_distance(bb, p)
                          for line, p in px.items() if line is not own)
            if d_other < LABEL_MARGIN * d_own:
                bad.append(f"{str(t.get_text())[:22]!r} is {d_own:.0f}px from "
                           f"its own curve and {d_other:.0f}px from another")
    if not checked:
        return True, "no direct labels matched to a series"
    if not bad:
        return True, f"{checked} direct label{'s' if checked != 1 else ''}, "\
                     f"each nearest the curve it names"
    return False, ("; ".join(bad) + f"  <- the reader resolves a direct label "
                   "by proximity, so it has to be plainly nearest its own "
                   "curve. Move it to where that curve is furthest from its "
                   "neighbours, or draw a leader line to the anchor")


# --- the sheet itself -------------------------------------------------------

def _style_sheet():
    """`figure.mplstyle` as the skill tells you to lay it out (beside this
    script), and as this repository lays it out (`assets/` next to
    `scripts/`)."""
    here = Path(__file__).resolve().parent
    for cand in (here / "figure.mplstyle",
                 here.parent / "assets" / "figure.mplstyle"):
        if cand.is_file():
            return cand
    return None


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
    written = mpl.rc_params_from_file(path, use_default_template=False)
    drift = []
    for key, value in written.items():
        try:
            same = mpl.rcParams[key] == value
        except KeyError:
            continue
        if not isinstance(same, bool):        # a numpy array of comparisons
            same = bool(getattr(same, "all", lambda: same)())
        if not same:
            drift.append(key)
    if not drift:
        return True, f"all {len(written)} keys match {path.name}"
    return "warn", (f"{len(drift)} of {len(written)} keys differ from "
                    f"{path.name}: {sorted(drift)[:5]}"
                    f"{' ...' if len(drift) > 5 else ''}  <- the sheet is not "
                    "the one in effect: check plt.style.use, and check no color "
                    "in the sheet was written with a leading #")


def audit(fig, scale=None, placed_frac=1.0):
    r = _renderer(fig)
    rows = [
        ("Clipping", *check_clipping(fig, r)),
        ("Text collision", *check_collisions(fig, r)),
        ("Contrast stack", *check_contrast_stack(fig)),
        ("Mark ratio", *check_mark_ratio(fig)),
        ("Axis redundancy", *check_redundancy(fig, r)),
        ("Type size", *check_type_size(fig, r, scale, placed_frac)),
        ("Ink coverage", *check_ink(fig)),
        ("Series color", *check_series_color(fig)),
        ("Dual axis", *check_dual_axis(fig)),
        ("Form", *check_form(fig)),
        ("Identity channel", *check_identity_channel(fig)),
        ("Label attribution", *check_label_attribution(fig, r)),
        ("Style sheet", *check_style_sheet(fig)),
    ]
    # "warn" rows are advisory: they report something worth a look without
    # failing the build. Only a hard False gates.
    return all(s is not False for _, s, _ in rows), rows


def report(fig, name="", scale=None, placed_frac=1.0):
    ok, rows = audit(fig, scale, placed_frac)
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
    try:
        import matplotlib
    except ImportError:
        raise SystemExit(
            "check_figure.py needs matplotlib (numpy comes with it):\n"
            "    pip install matplotlib\n\n"
            "The composition RULES are library-agnostic and written up in the "
            "style guide; only this automated check is matplotlib-specific. On "
            "another plotting stack, apply the rules by hand or port the "
            "checks - each one reads geometry any library can report.")
    matplotlib.use("agg")
    composed = report(self_test_figure(), "self-test (expected: FAIL)")
    if composed:
        raise SystemExit(
            "The self-test figure passed, which means the checker is broken.")
    print("  The gate correctly rejected a deliberately bad figure.\n")


if __name__ == "__main__":
    main()
