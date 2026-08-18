"""The `[tool.bumpversion]` config against the files it claims to rewrite.

`uv run bump-my-version bump <part>` is the only supported way to move the
version, because the version is written in five files and the release before
this config existed moved two of them. The tool makes that one command, and
this file makes the command's own configuration checkable.

Two ways the config rots, both silent until a release:

`current_version` is a sixth copy of the version. A hand-edit to
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

That is true of the release bump only, and the config said it of every bump
until 0.8.0. The cycle-opening bump runs immediately after a release, when the
heading has just been consumed and the next one is unwritten, so it failed on a
missing `## Unreleased` every time -- which is why 0.7.0 left the tree reading
`0.7.0` rather than `0.8.0.dev0`, and why 0.8.0 could not be cut with the
documented command. The entry excludes those parts now, and
`test_the_changelog_is_left_alone_by_the_cycle_opening_bump` is that exclusion.
"""

import pytest

from conftest import SKILL

ROOT = SKILL.parent
PYPROJECT = ROOT / "pyproject.toml"

# The file whose absent pattern is a normal state rather than a broken config.
NOT_A_CONSTANT_PATTERN = "CHANGELOG.md"


def pyproject():
    tomllib = pytest.importorskip("tomllib")     # 3.11+, as the build needs
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


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

    text = path.read_text(encoding="utf-8")
    found = (re.search(pattern, text, re.MULTILINE) if entry.get("regex")
             else pattern in text)
    assert found, (
        f"{entry['filename']} does not contain {pattern!r}, so the bump would "
        f"fail there -- after rewriting every file configured ahead of it")


def test_the_commit_message_is_configured_where_the_tool_reads_it():
    """`message` belongs to `[tool.bumpversion]`. Under a part table --
    `[tool.bumpversion.parts.dev]`, where it sat through 0.6.0 -- it is a key on
    the part, bump-my-version never looks for it there, and the release commit
    gets the stock `Bump version: X → Y` the key exists to replace. Nothing
    reports the miss: the config parses, the bump succeeds, and the message is
    wrong."""
    assert bumpversion().get("message") == "chore: release {new_version}"
    parts = bumpversion().get("parts", {})
    assert "message" not in parts.get("dev", {}), (
        "message is on the dev part, where bump-my-version does not read it")


def test_the_changelog_search_is_anchored_to_a_heading():
    """The changelog writes about its own headings, so `## Unreleased` occurs
    inside sentences as well as at the top of the open section. Unanchored, the
    bump replaces all of them: 0.6.0 shipped with two sentences saying a missing
    `## 0.6.0 — 2026-07-30` heading, describing a gate that asks for no such
    thing."""
    entry = next(e for e in bumpversion()["files"]
                 if e["filename"] == "CHANGELOG.md")
    assert entry.get("regex"), "an unanchored search rewrites inline mentions"
    assert entry["search"].startswith("^") and entry["search"].endswith("$")


def test_the_changelog_is_left_alone_by_the_cycle_opening_bump():
    """The release is two bumps, and only one of them writes the changelog.

    `bump dev` cuts, and renames `## Unreleased` to the version. `bump minor`,
    `patch` or `major` opens the next cycle, and runs when that heading has just
    been consumed by the release and the next set of notes does not exist yet.
    Without the exclusion the entry above applies to that bump too, looks for a
    heading that cannot be there, and fails: the tree then keeps the version of
    the release that already shipped, which is the state `parse` was rewritten
    to prevent and the state 0.7.0 actually left behind.

    Asserting the three parts by name rather than the presence of the key: a
    part dropped from the list is a bump that starts failing again, and it
    should fail here first.
    """
    entry = next(e for e in bumpversion()["files"]
                 if e["filename"] == "CHANGELOG.md")
    assert sorted(entry.get("exclude_bumps", [])) == ["major", "minor", "patch"], (
        "the changelog entry must be excluded from the cycle-opening bumps and "
        "from those only -- `dev` is the bump that cuts a release, and it is "
        "the one that has to fail when no notes were written")


def test_the_lock_pattern_is_anchored_to_the_project_and_matches_once():
    """uv.lock names a version for every package in the graph, and the
    project's own is identified only by the `name` line above it.

    `test_each_configured_pattern_is_in_the_file_it_points_at` proves the
    pattern matches something. This proves it matches the right thing, and only
    it: an unanchored `version = "X"` finds whichever package sorts first with
    that number, and the lock currently holds annotated-types 0.8.0,
    ast-serialize 0.6.0 and mdurl 0.1.2, all versions this project has shipped.
    Cutting 0.8.0 unanchored would have pinned annotated-types to a version
    that does not exist, in a file nobody reads in a diff.
    """
    import re

    entry = next(e for e in bumpversion()["files"]
                 if e["filename"] == "uv.lock")
    assert 'name = "figure-gate"' in entry["search"], (
        "the lock's search must carry the project's name, or it matches by "
        "version number alone")

    pattern = entry["search"].format(
        current_version=re.escape(bumpversion()["current_version"]))
    found = re.findall(pattern, (ROOT / "uv.lock").read_text(encoding="utf-8"),
                       re.MULTILINE)
    assert len(found) == 1, (
        f"the lock pattern matches {len(found)} places, expected exactly one")


def test_only_the_changelog_is_excluded_from_any_bump():
    """The other three sites are the version itself. A bump that skipped one
    would leave the four copies disagreeing, which is the failure this whole
    config exists to prevent and the one that cost 0.5.0."""
    excluded = {e["filename"] for e in bumpversion()["files"]
                if e.get("exclude_bumps") or e.get("include_bumps")}
    assert excluded == {"CHANGELOG.md"}, (
        f"{sorted(excluded)} are filtered by bump part. Only the changelog has "
        "a reason to be: the version sites move on every bump")


def test_no_section_names_its_own_heading_inside_a_sentence():
    """The damage the anchor prevents, checked on the file itself rather than on
    the config that writes it.

    A bump rewrites `## Unreleased` to the version being cut, so a mention it
    corrupted always names the heading of the section it sits in. Writing about
    another release's heading is ordinary prose -- the entry describing this
    very defect quotes 0.6.0's -- and only the self-reference is the tell."""
    import re

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = None
    buried = []
    for line in changelog.splitlines():
        match = re.match(r"^## (\d+\.\d+\.\d+ — \d{4}-\d{2}-\d{2})$", line)
        if match:
            heading = match.group(1)
            continue
        if line.startswith("## "):
            heading = None
            continue
        if heading and f"## {heading}" in line:
            buried.append(line)
    assert not buried, (
        "a bump rewrote `## Unreleased` inside these sentences:\n"
        + "\n".join(buried))
