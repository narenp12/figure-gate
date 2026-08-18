"""The task and reference pages against the code they quote. Only what a page
states: the behaviour behind the recipes is gate-side already, and asserting it
twice is what `test_suite_balance.py` catches.

The pages split by Diataxis mode, so what this file reads is now spread over
three of them: `how-to.md` holds the recipes and the values they quote,
`gates.md` holds the every-row remedy table, and `cli.md` holds the venue count.
One file still, because the three claims are one claim about `suggest_fixes.py`
and `VENUE_WIDTH_PT` and splitting the test would let a page drop its half
quietly.
"""

import re
import subprocess
import sys

import pytest

from conftest import SCRIPTS

import matplotlib.pyplot as plt

import check_figure as cf
import suggest_fixes as sf

DOCS = SCRIPTS.parent.parent / "docs"
TEXT = (DOCS / "how-to.md").read_text(encoding="utf-8")
GATES_TEXT = (DOCS / "gates.md").read_text(encoding="utf-8")
CLI_TEXT = (DOCS / "cli.md").read_text(encoding="utf-8")

# Counts the pages write in words. A `KeyError` is one that moved.
WORDS = {8: "eight", 10: "ten", 11: "Eleven", 12: "twelve"}


def table_rows():
    """`(row name, has a suggest() entry)` for the first-move table."""
    lines = GATES_TEXT.splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.startswith("| Row | First move |"))
    end = next(i for i, l in enumerate(lines[start:], start)
               if not l.startswith("|"))
    cells = [l.strip().strip("|").split("|") for l in lines[start + 1:end]]
    return [(c[0].strip(), c[2].strip() == "yes") for c in cells
            if set(c[0].strip()) != {"-"}]


def test_the_table_is_every_gate_in_order_marked_where_a_remedy_exists():
    """A row a reader meets in a report and cannot find here is the failure
    that table exists to fix; a `suggest()` mark on a row with no remedy
    promises a line that will not print. Length first: a parser that matched
    nothing would agree with anything."""
    assert len(table_rows()) > 1
    assert [n for n, _ in table_rows()] == [g.name for g in cf.GATES]
    assert ({n for n, marked in table_rows() if marked}
            == {r.gate for r in sf.REMEDIES})


def test_the_prose_counts_the_remedies_it_marks():
    with_remedy = len({r.gate for r in sf.REMEDIES})
    assert (f"{WORDS[with_remedy]} rows carry a remedy" in GATES_TEXT
            and f"{WORDS[sum(1 for r in sf.REMEDIES if r.code)]} of those"
            in GATES_TEXT)
    assert (f"The other {WORDS[len(cf.GATES) - with_remedy]} name their fix"
            in GATES_TEXT)


def quoted_from_code():
    """`(page text, string)` the pages state, computed from what each is about.

    The figure is the placement section's own: 4 inches wide, 10pt labels."""
    fig, ax = plt.subplots(figsize=(4, 2.5))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    try:
        out = [f">>> check_form(fig)\n{cf.check_form(fig)}"]
        for call, kwargs in ((")", {}), (", placed_frac=0.48)", {"placed_frac": 0.48})):
            scale = cf.page_scale(fig, venue="neurips", **kwargs)
            # `float()` is quoted too: the scale is a numpy.float64.
            out.append(f'>>> float(page_scale(fig, venue="neurips"{call})\n'
                       f"{float(scale)!r}")
    finally:
        plt.close(fig)
    listed = subprocess.run([sys.executable, "check_figure.py", "--venues"],
                            cwd=SCRIPTS, capture_output=True, text=True).stdout
    venues = len(re.findall(r"^\s+\S+\s+[\d.]+ pt", listed, re.M))
    return ([("how-to.md", q) for q in out]
            + [("how-to.md", f"under the {cf.TYPE_FLOOR_PT}pt floor"),
               ("how-to.md", f"The row wants {cf.ALT_TEXT_MIN_CHARS} characters"),
               ("cli.md", f"prints all {WORDS[venues]} widths")])


@pytest.mark.parametrize("page,quoted", quoted_from_code(),
                         ids=lambda q: q[:40] if isinstance(q, str) else q)
def test_the_page_quotes_what_the_code_returns(page, quoted):
    assert quoted in {"how-to.md": TEXT, "cli.md": CLI_TEXT}[page]
