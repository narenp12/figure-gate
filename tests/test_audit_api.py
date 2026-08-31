import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "audit_api.py"


def _load_audit_api():
    spec = importlib.util.spec_from_file_location("audit_api", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_run_factory(griffe_output: dict[str, tuple[int, str, str]],
                      missing_at_tag: tuple[str, ...] = ()):
    original_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git" and cmd[1] == "describe":
            return subprocess.CompletedProcess(cmd, 0, "v0.1.0\n", "")
        if cmd[0] == "git" and cmd[1] == "ls-tree":
            path = cmd[-1]
            absent = any(f"{m}.py" in path for m in missing_at_tag)
            return subprocess.CompletedProcess(
                cmd, 0, "" if absent else f"{path}\n", "")
        if cmd[0] == "griffe":
            assert cmd[1] == "check"
            assert cmd[2] == "-s" and cmd[3] == "skill/scripts"
            assert cmd[5] == "-a"
            module = cmd[4]
            rc, out, err = griffe_output.get(module, (0, "", ""))
            return subprocess.CompletedProcess(cmd, rc, out, err)
        return original_run(cmd, **kwargs)
    return fake_run


def _changelog(content: str) -> str:
    return content + "\n## 0.0.0\n\nInitial release.\n"


def test_audit_api_fails_on_silent_breaks(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\nNo mention of the break.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "does not name them" in str(exc_info.value)


def test_audit_api_passes_when_breaks_documented(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog(
            "## Unreleased\n\n"
            "- `contrast` was removed from the public API.\n"
        ), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_passes_when_no_breaks(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\nNothing yet.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (0, "", ""),
        "check_palette": (0, "", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_fails_on_griffe_tool_failure(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\nIrrelevant.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (2, "", "some internal griffe error\n"),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "That is the tool failing" in str(exc_info.value)


def test_audit_api_fails_when_no_git_tag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    original_run = subprocess.run

    def no_tag_run(cmd, **kwargs):
        if cmd[0] == "git":
            return subprocess.CompletedProcess(
                cmd, 1, "", "fatal: No names found, cannot describe anything.\n"
            )
        return original_run(cmd, **kwargs)

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=no_tag_run):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "no release tag to compare against" in str(exc_info.value)


def test_audit_api_fails_when_griffe_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def missing_run(cmd, **kwargs):
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, "v0.1.0\n", "")
        if cmd[0] == "griffe":
            raise FileNotFoundError(cmd[0])
        return subprocess.run(cmd, **kwargs)

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=missing_run):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "griffe is not installed" in str(exc_info.value)


def test_audit_api_ignores_report_shaped_output_on_clean_run(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_changelog("## Unreleased\n\nNothing.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (0, "skill/scripts/check_figure.py:0: GATES: Attribute value was changed\n", ""),
        "check_palette": (0, "", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_unreleased_is_last_section(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## Unreleased\n\n"
        "- `contrast` was removed from the public API.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_accepts_a_named_parameter_change(tmp_path, monkeypatch):
    """A parameter break is reported as `audit(context_axes)`, and a name
    ending in `)` is the case the matcher could not see.

    `\\b` after a `)` asks for a word character next to it, which no sentence
    puts there, so the gate was unsatisfiable for this whole class: the notes
    named all five changed parameters and CI failed anyway. It went unnoticed
    for eight releases because griffe had only ever reported bare names like
    `GATES` and `delta_e`, which end in a word character and so match.
    """
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\n`audit(context_axes)` and `audit(venue)` "
                   "changed to keyword-only.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (
            1,
            "skill/scripts/check_figure.py:0: audit(context_axes): Parameter "
            "kind was changed: positional or keyword -> keyword-only\n"
            "skill/scripts/check_figure.py:0: audit(venue): Parameter kind was "
            "changed: positional or keyword -> keyword-only\n",
            ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0, (
        "the notes name both changed parameters and the gate still failed")


def test_audit_api_still_fails_on_an_unnamed_parameter_change(tmp_path, monkeypatch):
    """The other half of the pair above. Loosening the boundary must not turn
    the gate into one that passes everything: a parameter the notes do not name
    still has to fail."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\n`audit(context_axes)` changed to "
                   "keyword-only.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (
            1,
            "skill/scripts/check_figure.py:0: audit(context_axes): Parameter "
            "kind was changed: positional or keyword -> keyword-only\n"
            "skill/scripts/check_figure.py:0: report(suggest): Parameter kind "
            "was changed: positional or keyword -> keyword-only\n",
            ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "report(suggest)" in str(exc_info.value.code)


def test_audit_api_does_not_match_a_name_inside_a_longer_one(tmp_path, monkeypatch):
    """What `\\b` was there for, kept. `delta_e` named nowhere must not be
    satisfied by a paragraph that happens to mention `delta_error`."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\n`delta_error` changed.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_palette": (
            1, "skill/scripts/check_palette.py:0: delta_e: Return value "
               "was changed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "delta_e" in str(exc_info.value.code)


def test_audit_api_changelog_accepts_other_break_words(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\n`GATES` moved down one row.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: GATES: Attribute value was changed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_skips_a_module_that_did_not_exist_at_the_tag(tmp_path, monkeypatch,
                                                                capsys):
    """`suggest_fixes.py` landed after v0.6.0. Comparing a module against a tag
    that has no such file makes griffe exit non-zero with an ImportError and no
    finding, which this script correctly refuses as the tool failing. A module
    with no history at the tag has no API that could have broken, and saying so
    is not the same as saying nothing broke."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_changelog("## Unreleased\n\nNothing.\n"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (0, "", ""),
        "check_palette": (0, "", ""),
    }

    mod = _load_audit_api()
    mod.MODULES = ("check_figure", "check_palette", "suggest_fixes")
    fake = _fake_run_factory(griffe_output, missing_at_tag=("suggest_fixes",))
    with patch("subprocess.run", side_effect=fake):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0
    assert "new since" in capsys.readouterr().out


def _pyproject(tmp_path, version: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "figure-gate"\nversion = "{version}"\n',
        encoding="utf-8")


def test_audit_api_reads_the_release_heading_after_the_bump(tmp_path, monkeypatch):
    """The release commit renames `## Unreleased` to the version it cuts, and
    the break is named in the section under that heading. Reading only
    `## Unreleased` failed every release that carried one."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog(
            "## 0.7.0 — 2026-08-03\n\n"
            "- `contrast` was removed from the public API.\n"
        ), encoding="utf-8")
    _pyproject(tmp_path, "0.7.0")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_still_fails_when_the_release_heading_is_silent(tmp_path, monkeypatch):
    """Reading the version's own section is not the gate going quiet: a break
    the notes do not name fails under a release heading exactly as it does
    under `## Unreleased`."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## 0.7.0 — 2026-08-03\n\nNo mention of the break.\n"),
        encoding="utf-8")
    _pyproject(tmp_path, "0.7.0")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0
    assert "0.7.0 section does not name them" in str(exc_info.value)


def test_audit_api_does_not_read_an_older_release_section(tmp_path, monkeypatch):
    """The section is the one matching `pyproject.toml`, not whichever is
    topmost. A paragraph in a shipped release must not stand in for a break
    made after it went out."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog(
            "## 0.6.0 — 2026-07-30\n\n"
            "- `contrast` was removed from the public API.\n"
        ), encoding="utf-8")
    _pyproject(tmp_path, "0.7.0")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code != 0


def test_audit_api_prefers_unreleased_while_the_cycle_is_open(tmp_path, monkeypatch):
    """Mid-cycle `pyproject.toml` carries `0.7.0.dev0` and the notes are still
    under `## Unreleased`. The dev version has no heading of its own, and the
    open section is the one that has to name the break."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog(
            "## Unreleased\n\n"
            "- `contrast` was removed from the public API.\n"
        ), encoding="utf-8")
    _pyproject(tmp_path, "0.7.0.dev0")
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0
