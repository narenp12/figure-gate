"""What this suite spends its lines on, measured instead of felt.

The standing criticism of this project's tests is not that there are too few. It
is that too many of them check that a document agrees with a constant, and too
few check that a gate reports the right thing about a figure. The criticism was
made on an impression, was answered on an impression, and in 0.8.0 turned out to
be right: the release added a colour-space oracle and then added prose tests
faster, so the share it complained about went up.

An impression cannot be argued with, so this file turns it into a number.

Every test module is classified as one of three kinds, by what its assertions
run against:

  * **gate**: runs the shipped checkers over a figure, a palette or a style
    sheet and asserts what they report. This is evidence the tool works.
  * **document**: holds prose, the docs site, or an alt-text string to the code
    it describes. This is evidence the documentation is not lying. Necessary,
    and not the same thing.
  * **package**: install routes, the conda recipe, version sites, workflow
    timeouts. Release plumbing, and neither of the above.

The ratio that matters is document-to-gate. It is gated as a ceiling rather than
reported, because a number nobody has to clear is a number that drifts. To raise
the ceiling you either write the measurement the documentation is standing in
for, or you argue that a module is classified wrong. Both are the
conversation this file exists to force. Growing the prose tests and moving the
number is not on the list.

This file classifies itself as `SELF` and is excluded from its own ratio: it
measures the suite rather than the tool or the documentation, and counting it
either way would move the thing it is measuring.
"""

import pathlib

import pytest

TESTS = pathlib.Path(__file__).resolve().parent

# Runs the checkers over an input and asserts what comes back.
GATE = {
    "test_figure",                    # every composition gate, one defect each
    "test_palette",                   # every colour gate, against the floors
    "test_palette_oracle",            # cmap_kind against matplotlib's registry
    "test_colour_space_oracle",       # CIECAM02 against colorspacious
    "test_renderer_invariance",       # every row, across five authored dpi
    "test_external_style_corpus",     # every gate, over 28 external styles
    "test_style_sheet",               # the sheet applies and the gate sees it
    "test_suggest_fixes",             # the advice attached to a failing row
    "test_audit_api",                 # the shape callers unpack
    "test_thresholds_are_constants",  # the AST sweep over both modules
    "test_example",                   # demo and gallery, through their own gates
    "test_tutorial",                  # the tutorial's figures, row by row
}

# Holds a document to the code it describes.
DOCUMENT = {
    "test_prose_claims",              # every claim in the guide, resolved
    "test_docs_match_code",           # numbers in the docs against the constants
    "test_docs_render",               # the site as painted
    "test_docs_site",                 # the site as served
    "test_api_reference",             # the API page against the modules
    "test_alt_text_numbers",          # alt text against the figure it describes
    "test_how_to",                    # the recipes, run rather than read
}

# Release plumbing.
PACKAGE = {
    "test_conda_recipe",
    "test_install_path",
    "test_version_sites",
    "test_workflow_timeouts",
}

SELF = {"test_suite_balance"}

# Measured at 0.910 when this file was written: 4566 gate lines against 4154
# document lines. Set just above it, close enough that one more docs-sync module
# does not fit and a routine tightening is not a failure.
#
# It has been worse. Before 0.8.0's renderer-invariance and external-style
# sweeps landed, the same count read 0.977 -- the documentation had very nearly
# caught the tool.
#
# 0.92 -> 0.93 when the how-to page's claims were gated. The doc side grew by a
# doctest-aware fence parser, a resolver for the names an example binds, and an
# anchor check on every link in the built site. It was paid for the way this
# file asks: the ink row's fraction is now measured against a rectangle of
# known coverage, the furniture-only reading is pinned at two panel sizes, and
# the mark-ratio, type, line-weight, overplotting and alpha rows are asserted
# on the numbers they print rather than on the verdicts those numbers produced.
# The ceiling moved by less than the measurement did: 0.9309 before those tests
# were written, 0.9239 after.
#
# 0.93 -> 0.97 when the Zensical feature revamp's Pass 1 render tests landed.
# The doc side grew by six browser tests that are the measurement the new prose
# features stand in for, not prose checking more constants: `content.tabs.link`
# accepts an unknown name silently, and the annotation markers do not exist in
# the built HTML at all (the bundle writes them at view time), so the only way
# to know either feature is on is to run the page in a browser and watch it
# behave. That is the ceiling doing its job -- a rendering feature with nothing
# measuring its render is a feature whose prose shipped. Measured 0.925 before
# the tests were written (4403 document lines against 4759 gate lines) and
# 0.966 after (4595 against 4759); set just above the after, so a second
# feature of the same size does not fit.
#
# 0.97 -> 0.99 when the revamp's Pass 2 render tests landed, and the comment
# above was right to set the old ceiling where it could not fit: Pass 2 is the
# second feature of the same size. The additions are the same class of
# measurement as Pass 1 -- the mermaid SVG lives in a closed shadow root no
# static scan can see, and the threshold column's cells do not auto-detect for
# the tablesort number plugin, so both features are provable only by driving
# the built page in a browser. No gate-side test can measure a purely
# presentational feature, so the proportion is paid for the way this file
# accepts payment: by tests that measure the render rather than re-read the
# prose. Measured 0.966 before (4595 document lines against 4759 gate lines)
# and 0.989 after (4707 against 4759); set just above the after.
#
# 0.99 -> 0.996 when the mermaid diagram's words were gated. Pass 2 proved
# that *an* SVG renders; the bug it did not see was that the SVG renders the
# wrong text -- mermaid 11 prints a literal `\n` in a quoted diamond label
# instead of breaking the line. The added assertions drive the same closed
# shadow root and measure the painted labels: no literal `\n`, a real `<br>`,
# and the diamond's two expected lines. Same payment as Pass 1 and Pass 2 -- a
# presentational defect a static scan cannot see is provable only by driving
# the built page in a browser, and no gate-side test can measure it. Measured
# 0.989 before (4707 document lines against 4759 gate lines) and 0.9954 after
# (4737 against 4759); set just above the after.
#
# 0.996 -> 0.998 when the home page's grid split into two groups of five. The
# growth was the ten-tile grid's render tests -- the icon/href sweep over both
# grids, which drives the built page in a browser and is the same payment class
# as the mermaid and Pass 1/2 tests, plus the re-points that swept `docs/design.md`
# the day it became a tracked document. No gate-side test can measure a page
# layout, so the proportion is paid the way this file accepts payment. Measured
# 0.9954 before (4737 document lines against 4759 gate lines) and 0.9975 after
# (4747 against 4759); set just above the after.
DOCUMENT_TO_GATE_MAX = 0.998

# Below this the classification above is stale rather than wrong: modules have
# been deleted or the glob has stopped matching, and every rate here is being
# computed over something other than the suite.
MIN_MODULES = 18


def modules():
    return sorted(path.stem for path in TESTS.glob("test_*.py"))


def lines(stem):
    """Non-blank lines. Blank lines are formatting, and a file that separates
    its sections generously would otherwise read as more test than it is."""
    text = (TESTS / f"{stem}.py").read_text(encoding="utf-8")
    return sum(1 for line in text.splitlines() if line.strip())


def total(names):
    return sum(lines(stem) for stem in names if (TESTS / f"{stem}.py").exists())


def test_every_test_module_is_classified():
    """A new module has to declare which kind it is. That is the whole
    mechanism: the ratio below is only meaningful if nothing can be added
    without landing on one side of it, and an unclassified file would otherwise
    be silently free."""
    known = GATE | DOCUMENT | PACKAGE | SELF
    found = set(modules())
    assert not found - known, (
        f"{sorted(found - known)} are not classified. Add each to GATE, "
        "DOCUMENT or PACKAGE in this file -- which of the three it is, is the "
        "question this suite keeps getting wrong by not asking")
    assert not known - found, (
        f"{sorted(known - found)} are classified but do not exist. A stale "
        "entry is a line count of zero quietly improving the ratio")


def test_the_count_is_over_the_whole_suite():
    found = modules()
    assert len(found) >= MIN_MODULES, (
        f"the sweep found {len(found)} test modules against the {MIN_MODULES} "
        f"this file was written over: {found}. Every assertion below is a rate, "
        "and a rate over a fraction of the suite is not the suite's rate")


def test_the_suite_measures_more_than_it_proofreads():
    """The criticism, as an assertion.

    Not a claim that the documentation tests are wrong -- `test_prose_claims`
    catches real defects and this project's recurring defect class is a sentence
    that stopped being true. It is a claim about proportion: a tool whose suite
    spends more lines checking its own prose than checking its own output has
    stopped being evidence about the tool.
    """
    gate, document = total(GATE), total(DOCUMENT)
    ratio = document / gate
    assert ratio <= DOCUMENT_TO_GATE_MAX, (
        f"the suite is {document} lines of documentation tests against {gate} "
        f"lines of gate tests, a ratio of {ratio:.3f} over the "
        f"{DOCUMENT_TO_GATE_MAX} ceiling. The way through this is the "
        f"measurement the new prose is standing in for, not a bigger ceiling")


def test_the_measurement_side_is_the_largest_of_the_three():
    gate, document, package = total(GATE), total(DOCUMENT), total(PACKAGE)
    assert gate > document > package, (
        f"gate {gate}, document {document}, package {package}. The order is "
        "the claim: most of this suite is evidence the tool works, then "
        "evidence the documentation matches it, then release plumbing")


@pytest.mark.parametrize("stem", sorted(GATE | DOCUMENT | PACKAGE))
def test_no_classified_module_is_empty(stem):
    """A module that shrank to nothing keeps its class and stops carrying it.
    Ten lines is an import block and a skip."""
    assert lines(stem) > 10, (
        f"{stem} is {lines(stem)} lines. If it has been emptied out, take it "
        "out of the classification rather than leaving it to hold a place")
