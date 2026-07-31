"""The `[tool.bumpversion]` config against the files it claims to rewrite.

`uv run bump-my-version bump <part>` is the only supported way to move the
version, because the version is written in four files and the release before
this config existed moved two of them. The tool makes that one command, and
this file makes the command's own configuration checkable.

Two ways the config rots, both silent until a release:

`current_version` is a fifth copy of the version. A hand-edit to
`pyproject.toml` that skips it leaves the tool searching for a string that is
no longer in any of these files, and every entry fails at once.

A `search` pattern drifts from the file it points at. Reformat `plugin.json`,
re-indent `recipe.yaml`, and the pattern stops matching. bump-my-version does
notice -- it refuses to write a file whose pattern is missing -- but only when
someone runs it, which is the moment a release is being cut, and only after it
has already rewritten the files listed ahead of it.

CHANGELOG.md is configured too and is deliberately not checked here. Its
pattern is `## Unreleased`, a heading that is absent for most of the life of
the repository and present only once notes have been written for the next
release. A test asserting it exists would fail on every clean checkout; the
bump failing when it is missing is the intended behaviour, not a defect.
"""

import pytest

from conftest import SKILL

ROOT = SKILL.parent
PYPROJECT = ROOT / "pyproject.toml"

# The file whose absent pattern is a normal state rather than a broken config.
NOT_A_CONSTANT_PATTERN = "CHANGELOG.md"


def pyproject():
    tomllib = pytest.importorskip("tomllib")     # 3.11+, as the build needs
    return tomllib.loads(PYPROJECT.read_text())


def bumpversion():
    config = pyproject().get("tool", {}).get("bumpversion")
    assert config, "pyproject.toml no longer configures bump-my-version"
    return config


def test_the_bump_config_version_is_the_project_version():
    """`current_version` drives every `{current_version}` pattern below it. If
    it disagrees with the project, no pattern matches anything."""
    assert bumpversion()["current_version"] == pyproject()["project"]["version"]


def test_the_bump_config_tags_the_way_release_yml_expects():
    """release.yml triggers on `v*` and compares `${GITHUB_REF_NAME#v}` against
    the project version. A tag template without the `v` releases nothing; one
    that decorated the version would fail that comparison."""
    assert bumpversion()["tag_name"] == "v{new_version}"


@pytest.mark.parametrize("entry", [
    pytest.param(entry, id=entry["filename"])
    for entry in pyproject().get("tool", {}).get("bumpversion", {}).get("files", [])
    if entry["filename"] != NOT_A_CONSTANT_PATTERN
])
def test_each_configured_pattern_is_in_the_file_it_points_at(entry):
    """The version site exists, in the shape the config expects to find it."""
    import re

    path = ROOT / entry["filename"]
    assert path.is_file(), f"{entry['filename']} does not exist"

    version = bumpversion()["current_version"]
    pattern = entry.get("search", "{current_version}").format(
        current_version=re.escape(version) if entry.get("regex") else version)

    text = path.read_text()
    found = (re.search(pattern, text, re.MULTILINE) if entry.get("regex")
             else pattern in text)
    assert found, (
        f"{entry['filename']} does not contain {pattern!r}, so the bump would "
        f"fail there -- after rewriting every file configured ahead of it")
