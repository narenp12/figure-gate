"""What to do about a gate that fired.

Deliberately not part of the gates. A gate measures; it says what broke, then in
a `[FIX]` clause what kind of thing fixes it and in a `[WHY]` clause why the row
fired at all. This file holds the other half: the statement you would actually
write. Keeping them apart means a gate stays a measurement, and a remedy can be
wrong without a gate being wrong.

Nothing here is applied for you. `suggest` returns text and a snippet; which of
several a figure wants is the author's call, and several gates fire on figures
where the right answer is to draw something different rather than to patch what
is there.

`Remedy.code` is a template against a bound `fig`, not a drop-in. Where it says
"the artist that carries the point", the code picks one and the choice is yours.
Where the fix needs the figure rebuilt rather than adjusted, `code` is empty and
the suggestion stands alone.

What `code` buys is that the suggestion is checked. Every non-empty snippet is
executed by `tests/test_suggest_fixes.py` against a figure that fails its gate,
and the gate has to pass afterwards. That is not decoration: `check_overplotting`
used to advise adding transparency, and the gate measures nearest-neighbour
distance in pixels, so alpha could never have moved it. A round-trip test is the
only thing that catches a suggestion that does not work.
"""

from typing import NamedTuple


class Remedy(NamedTuple):
    """One thing a reader could do about a gate that fired.

    `gate` is a `check_figure.Gate` name, and several remedies may share one:
    a gate that fires for two reasons wants two answers, and picking between
    them is what the reader is for.
    """
    gate: str
    suggestion: str
    code: str = ""


REMEDIES = (
    Remedy(
        "Clipping",
        "let a layout engine place the artists, or widen the figure",
        'fig.set_layout_engine("constrained")',
    ),
    Remedy(
        "Axis redundancy",
        "share the furniture between panels: sharex/sharey when the axes are "
        "created, or label_outer on a figure that already exists",
        "for ax in fig.axes:\n"
        "    ax.label_outer()",
    ),
    Remedy(
        "Contour dash",
        'draw signed contours solid, so dashing keeps meaning "projected" '
        "rather than \"negative\"",
        "from matplotlib.contour import ContourSet\n"
        "for ax in fig.axes:\n"
        "    for c in ax.collections:\n"
        "        if isinstance(c, ContourSet):\n"
        '            c.set_linestyle("solid")',
    ),
    Remedy(
        "Fonts",
        "embed Type 42, which is what the submission systems check",
        'plt.rcParams["pdf.fonttype"] = 42\n'
        'plt.rcParams["ps.fonttype"] = 42',
    ),
    Remedy(
        "Alt text",
        "attach a description of what a reader who cannot see it would have "
        "seen, then pass alt_metadata(fig, path) to savefig",
        "check_figure.describe(\n"
        "    fig,\n"
        '    "Measured throughput against offered load, with the fitted "\n'
        '    "model overlaid; throughput saturates near 80% of capacity.")',
    ),
    Remedy(
        "Contrast stack",
        "raise the artist that carries the point to full opacity, so the "
        "figure has somewhere to look",
        "# the artist that carries the point; here, the last line drawn\n"
        "for ax in fig.axes:\n"
        "    if ax.lines:\n"
        "        ax.lines[-1].set_alpha(1.0)",
    ),
    Remedy(
        "Contrast stack",
        "keep to at most three alpha levels; more reads as haze rather than "
        "as depth",
    ),
    Remedy(
        "Mark ratio",
        "cap the size range, so the largest mark still reads as a mark",
        "for ax in fig.axes:\n"
        "    for c in ax.collections:\n"
        "        s = c.get_sizes()\n"
        "        if len(s):\n"
        "            c.set_sizes(s.clip(None, s.min() * 5.0))",
    ),
    Remedy(
        "Colormap kind",
        "use a ramp whose lightness runs one way: viridis for sequential, "
        "RdBu for diverging, twilight for cyclic",
        "for ax in fig.axes:\n"
        "    for artist in list(ax.images) + list(ax.collections):\n"
        '        if getattr(artist, "get_array", lambda: None)() is not None:\n'
        '            artist.set_cmap("viridis")',
    ),
    Remedy(
        "Overplotting",
        "thin the counts or bin the data. Transparency and hollow markers do "
        "not help: the gate measures how close the marks are, not how dark "
        "the pile is, and neither moves a point",
    ),
    Remedy(
        "Series color",
        "fold the tail of the series into 'Other', or facet into panels. Both "
        "need the figure redrawn rather than adjusted",
    ),
    Remedy(
        "Style sheet",
        "apply the sheet where the figure is drawn, inside the same "
        "rc_context. Note this row reads the rcParams in effect and not the "
        "figure, so applying the sheet afterwards clears the row without "
        "changing anything that was already rendered",
    ),
)


def suggest(rows):
    """Remedies for the rows of an `audit` that are not passing.

    Takes `rows` rather than the figure: what is on offer depends on which
    gates fired, and nothing here needs to look at the figure again. Returns
    `[(gate_name, [Remedy, ...]), ...]` in the order the gates reported, and
    skips gates with nothing to offer rather than padding them with a
    restatement of the failure.
    """
    marked = [name for name, status, _ in rows if status is not True]
    out = []
    for name in marked:
        found = [r for r in REMEDIES if r.gate == name]
        if found:
            out.append((name, found))
    return out


def format_suggestions(rows, indent="      "):
    """`suggest`, as lines ready to print under a report. Empty when nothing
    fired that this file has an answer for."""
    lines = []
    for name, remedies in suggest(rows):
        lines.append(f"{indent}{name}:")
        for remedy in remedies:
            lines.append(f"{indent}  - {remedy.suggestion}")
            for code_line in remedy.code.splitlines():
                lines.append(f"{indent}      {code_line}")
    return lines
