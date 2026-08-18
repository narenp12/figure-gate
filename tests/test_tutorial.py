"""The tutorial's figures, run through the gates it says they fail.

A tutorial is the one document that has to work end to end: a reader following
it who does not get the printed result stops trusting the checker rather than
their own typing. `docs/tutorial.md` states a specific transition at each step,
and every one of them is a claim about what `audit` returns for a figure the
page tells the reader to build.

So the figures are built here the way the page builds them, and the rows are
asserted by name. This is gate-side measurement: it runs the checkers over an
input and asserts what comes back. What it protects is the page.
"""

from pathlib import Path

import numpy as np
import pytest

import matplotlib.pyplot as plt

import check_figure as cf

TUTORIAL = Path(__file__).resolve().parent.parent / "docs" / "tutorial.md"
STYLE_SHEET = (Path(__file__).resolve().parent.parent / "skill" / "assets"
               / "figure.mplstyle")

# The page's own numbers. Written here so a step edited on the page without
# being re-run fails, rather than drifting.
FIGSIZE_AUTHORED = (6, 3.5)
FIGSIZE_PLACED = (2.65, 1.9)
VENUE = "neurips"
PLACED_FRAC = 0.48
ALT_TEXT = ("Validation loss against training epoch for a baseline and a "
            "tuned run over 12 epochs. Both fall; the tuned run reaches 0.02 "
            "by epoch 12, while the baseline is still at 0.25.")


def curves():
    epochs = np.arange(1, 13)
    return (epochs,
            0.9 * np.exp(-0.06 * epochs) + 0.22,
            0.9 * np.exp(-0.35 * epochs) + 0.02)


def audited(styled, figsize, ticks=False, described=False, **audit_kwargs):
    """Build one of the tutorial's figures and audit it, returning `(ok, rows)`.

    `styled` is step 4's `plt.style.use`, `described` is step 5's `describe`,
    and `ticks` is step 7's explicit x ticks. Every combination below is a step
    the page prints a transcript for.

    The audit happens inside the style context rather than after it, because
    the page's script calls `plt.style.use` at module level and never leaves
    it. `check_style_sheet` reads the rcParams in effect when it runs, not the
    ones the figure was drawn under, so auditing outside the context would ask
    a different question than the page asks.
    """
    epochs, baseline, tuned = curves()
    context = (plt.style.context(str(STYLE_SHEET)) if styled
               else plt.style.context("default"))
    with context:
        fig, ax = plt.subplots(figsize=figsize, constrained_layout=styled)
        try:
            ax.plot(epochs, baseline, label="baseline")
            ax.plot(epochs, tuned, label="tuned")
            if styled:
                ax.set_xlabel("Epoch")
                ax.set_ylabel("Validation loss")
            else:
                ax.set_xlabel("Epoch", fontsize=6)
                ax.set_ylabel("Validation loss", fontsize=6)
            if ticks:
                ax.set_xticks([2, 4, 6, 8, 10, 12])
            ax.legend()
            if described:
                cf.describe(fig, ALT_TEXT)
            ok, rows = cf.audit(fig, **audit_kwargs)
        finally:
            plt.close(fig)
    return ok, rows


def statuses(rows):
    return {name: status for name, status, _ in rows}


def test_step_2_fails_only_the_type_size_row():
    """The page prints one `[FAIL]` and three `[WARN]`. A reader who gets a
    fourth failure is reading a transcript for a different figure."""
    rows = statuses(audited(styled=False, figsize=FIGSIZE_AUTHORED)[1])
    assert rows["Type size"] is False
    assert [name for name, status in rows.items() if status is False] \
        == ["Type size"]
    assert {name for name, status in rows.items() if status == "warn"} \
        == {"Style sheet", "Fonts", "Alt text"}


def test_step_4_clears_three_rows_at_once():
    """"Three rows change at once" is the sentence this holds: applying the
    sheet fixes the type size the reader shrank, the sheet row itself, and the
    font embedding they never touched."""
    rows = statuses(audited(styled=True, figsize=FIGSIZE_AUTHORED)[1])
    assert rows["Type size"] is True
    assert rows["Style sheet"] is True
    assert rows["Fonts"] is True
    assert rows["Alt text"] == "warn", (
        "step 4 leaves exactly one advisory row for step 5 to clear")


def test_step_5_reaches_the_passing_verdict():
    ok, rows = audited(styled=True, figsize=FIGSIZE_AUTHORED, described=True)
    assert ok, [(n, d) for n, s, d in rows if s is not True]


def test_step_6_fails_type_and_stroke_once_the_figure_is_placed():
    """The point of the step: nothing about the figure changed, and two rows
    that passed now fail because the page it lands on is narrower."""
    rows = statuses(audited(styled=True, figsize=FIGSIZE_AUTHORED,
                            described=True, venue=VENUE,
                            placed_frac=PLACED_FRAC)[1])
    assert {name for name, status in rows.items() if status is False} \
        == {"Type size", "Line weight"}


def test_step_7_passes_at_the_size_it_is_placed_at():
    ok, rows = audited(styled=True, figsize=FIGSIZE_PLACED, ticks=True,
                       described=True, venue=VENUE, placed_frac=PLACED_FRAC)
    assert ok, [(n, d) for n, s, d in rows if s is not True]


@pytest.mark.parametrize("quoted", [
    "figsize=(6, 3.5)",
    "figsize=(2.65, 1.9)",
    'venue="neurips", placed_frac=0.48',
    "ax.set_xticks([2, 4, 6, 8, 10, 12])",
    'ax.set_xlabel("Epoch", fontsize=6)',
])
def test_the_page_still_builds_the_figures_this_file_measures(quoted):
    """The fixtures above are a copy of the page's code, and a copy is a thing
    that drifts. If the page stops writing one of these, the copy is measuring
    a figure no reader builds."""
    text = " ".join(TUTORIAL.read_text(encoding="utf-8").split())
    assert " ".join(quoted.split()) in text, (
        f"docs/tutorial.md no longer writes {quoted!r}, so the figures in this "
        "file are no longer the figures the page tells a reader to build")
