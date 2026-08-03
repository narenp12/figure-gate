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


def _fake_run_factory(griffe_output: dict[str, tuple[int, str, str]]):
    original_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, "v0.1.0\n", "")
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
        _changelog("## Unreleased\n\nNo mention of the break.\n")
    )
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
        )
    )
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
        _changelog("## Unreleased\n\nNothing yet.\n")
    )
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
        _changelog("## Unreleased\n\nIrrelevant.\n")
    )
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
    changelog.write_text(_changelog("## Unreleased\n\nNothing.\n"))
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
        "- `contrast` was removed from the public API.\n"
    )
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: contrast: Public object was removed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0


def test_audit_api_changelog_accepts_other_break_words(tmp_path, monkeypatch):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        _changelog("## Unreleased\n\n`GATES` moved down one row.\n")
    )
    monkeypatch.chdir(tmp_path)

    griffe_output = {
        "check_figure": (1, "skill/scripts/check_figure.py:0: GATES: Attribute value was changed\n", ""),
    }

    mod = _load_audit_api()
    with patch("subprocess.run", side_effect=_fake_run_factory(griffe_output)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
    assert exc_info.value.code == 0
