"""The README's threshold claim, read off the modules instead of trusted.

`README.md` says every threshold is a module-level constant you can read and
change. It was true of the ones anybody had thought about and false of the rest:
the prose audit found the ink-detection cutoff written as `> 24` inside
`check_ink`, the WCAG large-text sizes as `>= 18.0` and `>= 14.0` inside
`check_text_readability`, the placement warning as `< 0.35`, the opaque-mark
definition as `>= 0.99`, and all three ordinal rows of `check_palette` as
literals while every categorical threshold sat at module level.

Two of those had already been promoted for this exact reason, each with a
comment saying so -- `OVERPLOT_THRESHOLD` and `ADVISORY_GATES` both cite the
README. Promoting them one at a time as somebody notices is what this file
replaces.

The sweep: every comparison in either module against a numeric literal. Most are
structural -- `len(x) < 2`, `size == 0`, `> 0` -- and say nothing about where a
verdict falls, so they are recognised by shape rather than listed. What is left
is a number somebody chose, and it either names a constant or it appears below
with the reason it is not one.
"""

import ast
import inspect
import pathlib

import pytest

from conftest import SKILL                                   # noqa: E402

import check_figure as cf                                    # noqa: E402
import check_palette as cp                                   # noqa: E402

MODULES = {"check_figure.py": cf, "check_palette.py": cp}

# Comparator values that are guards rather than thresholds: emptiness,
# positivity, and "is there one of these". A gate cannot express a judgement in
# them, and read off the AST rather than off the text so that `1.0` and `1` are
# the same guard.
STRUCTURAL_VALUES = (0, 1, -1)

# Left-hand shapes that make a comparison a count rather than a measurement.
# `len(distinct) >= 2` is "are there two series", not "is two enough".
# `.sum()` is deliberately absent: `np.abs(nm1 - m1).sum() < 0.5` sums a
# distance, not a population, and calling that structural would excuse a real
# number by the shape of the expression in front of it.
COUNTING = ("len(", ".size", ".ndim", "count", "int(mpl.rcParams")


def _comparisons(module):
    """(module, function, line, source, structural) per literal comparison."""
    path = pathlib.Path(inspect.getfile(module))
    tree = ast.parse(path.read_text())
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Compare):
                continue
            for comparator in node.comparators:
                if not isinstance(comparator, ast.Constant):
                    continue
                value = comparator.value
                if isinstance(value, bool) or not isinstance(value,
                                                             (int, float)):
                    continue
                source = ast.unparse(node)
                structural = (value in STRUCTURAL_VALUES
                              or any(token in ast.unparse(node.left)
                                     for token in COUNTING))
                out.append((path.name, func.name, node.lineno, source,
                            structural))
    return out


def thresholds():
    """Comparisons that state where a verdict falls, not how big a list is."""
    return sorted((name, func, line, source)
                  for module in MODULES.values()
                  for name, func, line, source, structural
                  in _comparisons(module)
                  if not structural)


# Numbers that are not thresholds anybody would tune. Each is a constant of a
# formula, a format, or a numerical method: changing it does not move a gate, it
# breaks a definition.
#
# Keyed by the comparison itself rather than by the function holding it. A
# per-function key excuses every literal that function ever grows, which is how
# a ledger stops being a ledger.
NOT_A_THRESHOLD = {
    ("check_figure.py", "_contrast_255", "c <= 0.04045"):
        "the breakpoint of the sRGB transfer function, from the specification "
        "and not from this project",
    ("check_figure.py", "lin", "c <= 0.04045"):
        "the same breakpoint, in the local helper `_contrast_255` defines",
    ("check_palette.py", "_srgb_to_linear", "c <= 0.04045"):
        "the same sRGB breakpoint",
    ("check_figure.py", "check_ink", "np.abs(nm1 - m1).sum() < 0.5"):
        "the convergence tolerance of the two-means split that finds the page "
        "colour, in summed 0-255 RGB. It decides when the loop stops, not "
        "whether a panel passes",
    ("check_figure.py", "check_ink", "np.abs(nm2 - m2).sum() < 0.5"):
        "the same tolerance, for the other centroid",
    ("check_figure.py", "check_overplotting", "n < 2"):
        "`n` is `len(xy)` one line up, so this is the emptiness guard the "
        "shape rule recognises everywhere it is not read through a name",
}


@pytest.mark.parametrize("module,func,line,source", thresholds(),
                         ids=str)
def test_a_threshold_is_a_named_constant(module, func, line, source):
    """The README's sentence, as an assertion.

    A reader who wants a stricter ink floor greps for a constant. A number
    inside a function is one they have to find by reading the gate.
    """
    if (module, func, source) in NOT_A_THRESHOLD:
        return
    pytest.fail(
        f"{module}:{line} in {func} compares against a literal: {source}. "
        "The README says every threshold is a module-level constant you can "
        "read and change. Either promote it, or name it in NOT_A_THRESHOLD "
        "with the reason it is not one")


def test_the_ledger_has_no_stale_entries():
    """An entry outlives the line it excuses, and then it is a licence nobody
    is using -- the same failure mode `UNRESOLVED_SPANS` guards against."""
    present = {(module, func, source)
               for module, func, _, source in thresholds()}
    stale = sorted(set(NOT_A_THRESHOLD) - present)
    assert not stale, (
        f"{stale} are excused from naming a constant but no longer compare "
        "against a literal. Drop them from NOT_A_THRESHOLD")


def test_the_sweep_still_sees_the_comparisons_it_reads():
    """Every assertion above is parametrized over the sweep. A sweep that came
    back empty would not fail them, it would delete them."""
    seen = _comparisons(cf) + _comparisons(cp)
    assert len(seen) > 30, (
        f"the sweep found {len(seen)} literal comparisons across two modules "
        "that have always had dozens, so it is reading something other than "
        "the source")


def test_the_sweep_would_catch_a_threshold_written_inline():
    """The house rule is that a gate is tested for its ability to fail, and a
    sweep over correct source passes whether or not it works.

    `> 24` inside `check_ink` is the literal the audit found, written back in
    the shape the sweep has to reject.
    """
    tree = ast.parse("def check_ink(fig):\n"
                     "    return (mask.sum(axis=2) > 24).mean() > INK_MIN\n")
    found = [ast.unparse(node) for node in ast.walk(tree)
             if isinstance(node, ast.Compare)
             and any(isinstance(c, ast.Constant) and not isinstance(c.value, bool)
                     and isinstance(c.value, (int, float))
                     for c in node.comparators)]
    assert found, "the sweep no longer sees a literal comparison at all"
    inline = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)
              and any(isinstance(c, ast.Constant) and c.value == 24
                      for c in node.comparators)]
    assert inline and not any(
        token in ast.unparse(node.left) for node in inline
        for token in COUNTING), (
        f"the sweep reads {found} as structural, so the exact defect it was "
        "written for would pass")


def test_the_promoted_constants_are_the_values_that_were_inline():
    """Promotion is a refactor, and a refactor that changes a number changes
    every verdict downstream of it. These are the values the literals had."""
    assert (cf.INK_DELTA_MIN, cf.LARGE_TEXT_PT, cf.LARGE_TEXT_BOLD_PT,
            cf.BOLD_WEIGHT_MIN, cf.PLACED_FRAC_WARN,
            cf.OPAQUE_ALPHA_MIN) == (24, 18.0, 14.0, 600, 0.35, 0.99)
    assert (cp.ORDINAL_DL_MIN, cp.ORDINAL_LIGHT_END_CONTRAST_MIN,
            cp.ORDINAL_STEP_RATIO_MAX) == (0.06, 2.0, 2.0)


def test_the_readme_still_makes_the_claim_this_file_gates():
    text = " ".join((SKILL.parent / "README.md").read_text().split())
    assert "Every threshold is a module-level constant" in text, (
        "the README no longer makes the claim this file exists to hold it to. "
        "If the sentence went, this file should go with it rather than "
        "gating a promise nobody made")
