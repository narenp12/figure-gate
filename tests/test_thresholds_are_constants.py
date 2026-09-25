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

The sweep runs both ways.

Outward: every comparison in either module against a numeric literal. Most are
structural -- `len(x) < 2`, `size == 0`, `> 0` -- and say nothing about where a
verdict falls, so they are recognised by shape rather than listed. What is left
is a number somebody chose, and it either names a constant or it appears below
with the reason it is not one.

Inward: every module-level constant has to be read by something. That direction
was missing until `SURFACE_MIN_FRAC` turned up in the SVG substrate, declared in
the commit that created its module under four lines of comment about telling a
panel background from a filled mark, and consulted by no gate, ever. That
substrate is archived at `archive/r-svg-substrate` rather than merged, so the
constant itself never reached these two modules. The missing direction is what
carried over: 52 constants here, and nothing asserted that any of them moved a
verdict.
"""

import ast
import inspect
import pathlib
import re

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
    tree = ast.parse(path.read_text(encoding="utf-8"))
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
    ("check_figure.py", "_contrast_field_255", "c <= 0.04045"):
        "the same breakpoint, vectorised",
    ("check_figure.py", "lum", "c <= 0.04045"):
        "the same breakpoint again, in the local helper "
        "`_contrast_field_255` defines",
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
    text = " ".join((SKILL.parent / "README.md").read_text(encoding="utf-8").split())
    assert "Every threshold is a module-level constant" in text, (
        "the README no longer makes the claim this file exists to hold it to. "
        "If the sentence went, this file should go with it rather than "
        "gating a promise nobody made")


def _declared(module):
    """Module-level `NAME = <number>` assignments, in source order."""
    path = pathlib.Path(inspect.getfile(module))
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Constant):
            continue
        if isinstance(value.value, bool) or not isinstance(value.value,
                                                           (int, float)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                out.append((path.name, target.id, node.lineno))
    return out


def declarations():
    return sorted(row for module in MODULES.values()
                  for row in _declared(module))


@pytest.mark.parametrize("module,name,line", declarations(), ids=str)
def test_a_declared_threshold_is_read_somewhere(module, name, line):
    """The other half of the README's sentence, which nothing asserted.

    `test_a_threshold_is_a_named_constant` runs one way: a number that decides a
    verdict has to carry a name. It says nothing about a name that decides
    nothing. A reader who lowered such a constant would change no verdict and
    have no way to find that out.

    Documentation is not a use. Neither is a test: a constant only the suite
    mentions still moves nothing on a figure.
    """
    sources = {path.name: path.read_text(encoding="utf-8")
               for path in (pathlib.Path(inspect.getfile(m))
                            for m in MODULES.values())}
    word = re.compile(rf"\b{re.escape(name)}\b")
    own = len(word.findall(sources[module])) - 1        # minus the declaration
    elsewhere = sum(len(word.findall(text))
                    for other, text in sources.items() if other != module)
    assert own + elsewhere > 0, (
        f"{module}:{line} declares {name} and nothing in "
        f"{', '.join(sorted(sources))} reads it. A threshold no gate consults "
        "is a number a reader can change with no effect, which is worse than "
        "an unnamed one. Either wire it into the check its comment describes, "
        "or delete it along with the comment")


def test_the_declaration_sweep_reads_every_module():
    """Same guard as `test_the_sweep_still_sees_the_comparisons_it_reads`: a
    parametrized assertion over an empty sweep is a deleted assertion."""
    found = declarations()
    modules = {module for module, _, _ in found}
    assert modules == set(MODULES), (
        f"the declaration sweep read {sorted(modules)} of {sorted(MODULES)}")
    assert len(found) > 40, (
        f"the sweep found {len(found)} module-level numeric constants across "
        "two modules that held 52 at the measurement this floor was set from")


def test_the_declaration_sweep_would_catch_an_unread_constant():
    """`SURFACE_MIN_FRAC = 0.20`, in the shape it sat in for the whole life of
    the archived SVG substrate, written back so the sweep has to see it."""
    source = ("# Below this share of the canvas an element is furniture.\n"
              "SURFACE_MIN_FRAC = 0.20\n"
              "OUTLINE_MIN_ELEMENTS = 20\n"
              "def check(doc):\n"
              "    return doc.elements > OUTLINE_MIN_ELEMENTS\n")
    tree = ast.parse(source)
    names = [t.id for node in tree.body if isinstance(node, ast.Assign)
             for t in node.targets
             if isinstance(t, ast.Name) and t.id.isupper()
             and isinstance(node.value, ast.Constant)]
    assert names == ["SURFACE_MIN_FRAC", "OUTLINE_MIN_ELEMENTS"], names
    reads = {name: len(re.findall(rf"\b{name}\b", source)) - 1
             for name in names}
    assert reads["SURFACE_MIN_FRAC"] == 0, (
        "the sweep no longer reads the exact defect it was written for")
    assert reads["OUTLINE_MIN_ELEMENTS"] == 1, (
        "the sweep calls a constant unread when a gate does consult it, so it "
        "would fail on correct source")
