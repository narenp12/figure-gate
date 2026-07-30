"""`conda/recipe.yaml` against `pyproject.toml`.

The recipe is the one packaging file in this repo that nothing here builds:
conda-forge builds it, from a copy in a different repository. That is exactly
the condition under which a file rots. A `pip install figure-gate` and a
`conda install figure-gate` that disagree about the Python floor, the runtime
dependencies or the console scripts is a defect only the conda user ever meets,
and they meet it as "the gate does not run", not as a build failure.

So the three fields that can drift are held to the source of truth here. Not
`sha256`, which is unknowable before the release exists and is what
`conda/update_recipe.py` is for, and not `source.url`, which is checked only
for naming the version it claims to.

Deliberately parsed by hand rather than with PyYAML. The pytest job in CI
installs matplotlib, pytest and xdist and nothing else, so a test that needed a
YAML library would skip in the one place this most needs to run. The recipe is
a file this repo writes, in a shape this repo chose, and reading four fields
out of it does not need a parser.
"""

import re

import pytest

from conftest import SCRIPTS

ROOT = SCRIPTS.parent.parent
RECIPE = ROOT / "conda" / "recipe.yaml"
PYPROJECT = ROOT / "pyproject.toml"

# conda-forge does not mirror PyPI names. `matplotlib` there is a metapackage
# that pulls pyqt for an interactive backend; `matplotlib-base` is the library
# these checkers actually use. Every rename the recipe is allowed to make has
# to be written here, so a rename nobody decided on still fails.
CONDA_NAMES = {"matplotlib": "matplotlib-base"}


def recipe_text():
    return RECIPE.read_text()


def context():
    """The recipe's `context:` block, as a plain dict of strings.

    rattler-build interpolates these into the rest of the file as
    `${{ name }}`. A test that compared the raw text would be comparing
    `python ${{ python_min }}` against `3.11` and failing on a recipe that is
    correct, so the substitution happens here too. Only simple scalars: the
    block holds a name, a version and a floor, and nothing that needs an
    expression evaluator.
    """
    lines = recipe_text().splitlines()
    start = lines.index("context:")
    out = {}
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pair = re.fullmatch(r'  (\w+): "?([^"#]+?)"?', line)
        if not pair:
            break
        out[pair.group(1)] = pair.group(2)
    return out


def resolve(value):
    """`python >=${{ python_min }}` -> `python >=3.11`."""
    for key, replacement in context().items():
        value = value.replace("${{ %s }}" % key, replacement)
    return value


def items(header, indent):
    """The `- ` entries of a YAML block, by exact header line.

    Stops at the first line that is neither an item at `indent` nor a comment
    or blank, which is enough structure for a file of this shape and fails
    loudly -- an empty list -- rather than silently absorbing a later block.
    """
    lines = recipe_text().splitlines()
    start = next((i for i, line in enumerate(lines) if line == header), None)
    assert start is not None, f"{RECIPE.name} has no {header.strip()!r} block"

    out = []
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.fullmatch(rf"{' ' * indent}- (.+)", line)
        if not item:
            break
        out.append(item.group(1).strip())
    return out


def requirement(entry):
    """`matplotlib-base >=3.8` -> `("matplotlib-base", ">=3.8")`."""
    name, _, spec = resolve(entry).partition(" ")
    return name, spec.strip()


def pyproject():
    tomllib = pytest.importorskip("tomllib")     # 3.11+, as the build needs
    return tomllib.loads(PYPROJECT.read_text())


def test_the_recipe_version_is_the_project_version():
    """The version conda-forge builds, against the version this repo is. They
    are two hand-edited strings until something compares them."""
    claimed = re.search(r'(?m)^  version: "(.+)"$', recipe_text())
    assert claimed, "recipe.yaml no longer declares `version:` in context"
    assert claimed.group(1) == pyproject()["project"]["version"]


def test_the_recipe_source_url_is_built_from_that_version():
    """A url with the version hard-coded would pass the test above and still
    fetch the wrong sdist."""
    url = re.search(r"(?m)^  url: (.+)$", recipe_text())
    assert url, "recipe.yaml no longer declares `source.url`"
    assert "${{ version }}" in url.group(1), (
        f"source.url does not interpolate the version: {url.group(1)}")


def test_the_recipe_runtime_dependencies_match_the_project():
    """`requirements.run` against `[project].dependencies`, modulo the renames
    conda-forge forces. A conda package with a looser matplotlib floor than the
    wheel is a gate that imports and then fails on a missing colormap."""
    run = dict(requirement(entry) for entry in items("  run:", indent=4))
    run.pop("python", None)

    want = {}
    for spec in pyproject()["project"]["dependencies"]:
        name, _, constraint = re.match(r"([A-Za-z0-9_.-]+)(\s*)(.*)",
                                       spec).groups()
        want[CONDA_NAMES.get(name, name)] = constraint.strip()

    assert run == want, (
        f"recipe run-requirements {run} do not match pyproject dependencies "
        f"{want}. If conda-forge needs a different package name for one of "
        f"these, add it to CONDA_NAMES with the reason.")


def test_the_recipe_python_floor_is_the_project_floor():
    """Both of them: `run` is what users resolve against, and for a
    `noarch: python` package `host` is what the build pins."""
    floor = pyproject()["project"]["requires-python"].replace(" ", "")
    assert floor.startswith(">="), (
        f"requires-python is {floor!r}; this test only knows how to compare a "
        "`>=` floor")
    version = floor[2:]

    run = dict(requirement(entry) for entry in items("  run:", indent=4))
    assert run.get("python") == f">={version}", (
        f"recipe runs on python {run.get('python')!r}, project floor is "
        f">={version}")

    # `python 3.11` on its own is not a match spec -- rattler-build rejects it
    # outright, asking for `==3.11` or `3.11.*` -- so the host pin is the
    # `.*` form and the floor is what it is built from.
    host = dict(requirement(entry) for entry in items("  host:", indent=4))
    assert host.get("python") == f"{version}.*", (
        f"recipe builds against python {host.get('python')!r}, project floor "
        f"is {version}")


def test_the_recipe_entry_points_match_the_console_scripts():
    """`check-palette` and `check-figure` are how the README tells people to
    run this after an install. An entry point missing from the recipe is a
    conda install whose documented commands are not on PATH."""
    declared = items("    entry_points:", indent=6)
    found = dict(re.match(r"(\S+) = (\S+)", entry).groups()
                 for entry in declared)
    assert found == pyproject()["project"]["scripts"]
