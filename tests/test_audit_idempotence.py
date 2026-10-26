"""Auditing a figure twice gives one answer and hands the figure back unchanged.

`audit` draws on its own Agg canvas at `MEASURE_DPI` under the rcParams the
first audit recorded, then puts the canvas, the dpi, `_original_dpi` and the
layout back. Each of those restores has broken once on some matplotlib version,
so this runs the whole corpus through two audits and compares everything
`audit` touches: the rows, `fig.dpi`, `_original_dpi`, `fig.canvas`, rcParams,
artist visibility and the bytes `savefig` writes.

The bytes are compared with an unaudited twin of the figure, saved the same
number of times, and not with the figure's own earlier `savefig`. Two plain
`savefig` calls on a `constrained_layout` figure already differ, because every
draw runs the layout solver again from where the last one left it.
"""

import contextlib
import hashlib
import io
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

import check_figure as cf                                     # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
sys.path.insert(0, str(EXAMPLES))

import demo                                                   # noqa: E402
import gallery                                                # noqa: E402
import test_external_style_corpus as external                 # noqa: E402


def _png(fig):
    """The bytes of a plain and of a tight `savefig`, hashed."""
    out = []
    for kw in ({}, {"bbox_inches": "tight"}):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", **kw)
        out.append(hashlib.sha256(buf.getvalue()).hexdigest())
    return tuple(out)


def _state(fig):
    return {
        "dpi": fig.dpi,
        "original_dpi": getattr(fig, "_original_dpi", None),
        "canvas": id(fig.canvas),
        "rc": dict(mpl.rcParams),
        "visible": [a.get_visible() for a in fig.findobj()],
    }


def _audit_twice(fig, **audit_kw):
    """Save, audit twice, save. What each step left behind."""
    first_png = _png(fig)
    entry = _state(fig)
    first = cf.audit(fig, **audit_kw)
    after_one = _state(fig)
    second = cf.audit(fig, **audit_kw)
    after_two = _state(fig)
    return {"rows": (first, second), "states": (entry, after_one, after_two),
            "png": (first_png, _png(fig))}


def _unaudited(fig, **_):
    """The same two saves with no audit between them."""
    return {"png": (_png(fig), _png(fig))}


def _assert_idempotent(audited, twin):
    first, second = audited["rows"]
    assert first == second
    entry, after_one, after_two = audited["states"]
    for key in entry:
        assert after_one[key] == entry[key], key
        assert after_two[key] == entry[key], key
    assert audited["png"] == twin["png"]


@contextlib.contextmanager
def _captured(step):
    """Run a corpus builder with `report` replaced by `step`.

    `step` runs where `report` would have, inside the builder's own style
    context, and `gallery.OUT = None` keeps the committed PNGs untouched.
    """
    seen = []

    def spy(fig, name="", scale=None, placed_frac=1.0, *,
            context_axes=None, venue=None, suggest=False):
        seen.append(step(fig, scale=scale, placed_frac=placed_frac,
                         context_axes=context_axes, venue=venue))
        return True

    real, out = cf.report, gallery.OUT
    cf.report = gallery.cf.report = demo.cf.report = spy
    gallery.OUT = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield seen
    finally:
        cf.report = gallery.cf.report = demo.cf.report = real
        gallery.OUT = out
        plt.close("all")


def _corpus_pair(build):
    with _captured(_audit_twice) as audited:
        build()
    with _captured(_unaudited) as twins:
        build()
    assert audited and len(audited) == len(twins)
    for one, twin in zip(audited, twins):
        _assert_idempotent(one, twin)


@pytest.mark.parametrize("build", gallery.BUILDERS, ids=lambda b: b.__name__)
def test_a_gallery_figure_survives_two_audits(build):
    _corpus_pair(build)


def test_the_demo_figure_survives_two_audits():
    _corpus_pair(lambda: demo.build(out=None))


@pytest.mark.parametrize("build", external.BUILDERS, ids=lambda b: b.__name__)
def test_an_external_style_figure_survives_two_audits(build):
    """Every installed style, looped rather than parametrized, because the
    style list grows with the matplotlib version and the collected test count
    is a stated number."""
    for sheet in external.external_styles():
        with plt.style.context(sheet):
            fig, twin = build(), build()
            try:
                _assert_idempotent(_audit_twice(fig), _unaudited(twin))
            except AssertionError as exc:
                raise AssertionError(f"{sheet}: {exc}") from exc
            finally:
                plt.close(fig)
                plt.close(twin)


def test_audit_never_resizes_a_gui_window():
    """`fig.dpi = MEASURE_DPI` resizes the window of a GUI canvas, through
    `set_size_inches(forward=True)`. Under TkAgg the resize event came back
    after the audit and resized the figure."""
    from matplotlib.backend_bases import FigureCanvasBase, FigureManagerBase

    resized = []

    class Manager(FigureManagerBase):
        def resize(self, w, h):
            resized.append((w, h))

    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    ax.plot([0, 1], [0, 1])
    canvas = FigureCanvasBase(fig)
    canvas.manager = Manager(canvas, 1)
    cf.audit(fig)
    cf.check_ink(fig)
    cf.check_text_readability(fig, None)
    handed_back = fig.canvas is canvas
    plt.close(fig)
    assert resized == []
    assert handed_back
