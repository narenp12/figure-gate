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
"""

import itertools
from collections import Counter

MARK_RATIO_MAX = 5.0        # area ratio of largest to smallest data mark
ALPHA_LEVELS_MAX = 3        # distinct transparency levels in one figure
INK_MIN, INK_MAX = 0.02, 0.55   # fraction of the axes area carrying data ink

# Type floor, in points ON THE PAGE, after the figure is scaled to fit.
TYPE_FLOOR_PT = 7.5

# Usable width of the page the figure lands in, in points. Set it once and the
# scale is derived per figure from that figure's own width - which is the part
# people get wrong, because a wide figure shrinks much harder than a narrow one
# and the same 8pt label is fine in one and illegible in the other.
#
# Author at the width the figure is actually placed at and the scale is 1.0:
# points authored are points printed, and this whole calculation disappears.
# SET THIS PER PROJECT. Render one page, place a full-width figure, measure it.
# Within ~5% is fine; it only sets the type floor. None means "assume scale 1.0",
# which is correct when you author each figure at the width it is placed at.
CONTENT_WIDTH_PT = None


def page_scale(fig):
    if CONTENT_WIDTH_PT is None:
        return 1.0
    return CONTENT_WIDTH_PT / (fig.get_size_inches()[0] * 72)


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
    reading as an ornament stuck on top of the plot."""
    worst = None
    for ax in fig.axes:
        sizes = []
        for c in ax.collections:
            s = getattr(c, "get_sizes", lambda: [])()
            sizes.extend(float(v) for v in s if v > 0)
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


def check_type_size(fig, r, scale=None):
    """Every rendered string clears the legibility floor once the figure is
    scaled into the document.

    This used to be a regex over the source file hunting for `fontsize=`, which
    missed anything set through rcParams, anything computed, and anything set by
    a helper. Reading `get_fontsize()` off the artists that actually rendered
    reports what is on the page instead of what is in the source.
    """
    scale = page_scale(fig) if scale is None else scale
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


def audit(fig, scale=None):
    r = _renderer(fig)
    rows = [
        ("Clipping", *check_clipping(fig, r)),
        ("Text collision", *check_collisions(fig, r)),
        ("Contrast stack", *check_contrast_stack(fig)),
        ("Mark ratio", *check_mark_ratio(fig)),
        ("Axis redundancy", *check_redundancy(fig, r)),
        ("Type size", *check_type_size(fig, r, scale)),
        ("Ink coverage", *check_ink(fig)),
    ]
    # "warn" rows are advisory: they report something worth a look without
    # failing the build. Only a hard False gates.
    return all(s is not False for _, s, _ in rows), rows


def report(fig, name="", scale=None):
    ok, rows = audit(fig, scale)
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
