import re
import subprocess
import sys
import pathlib
import tomllib

REPORTED = re.compile(r"^\S+?:\d+: (\S+?): ", re.M)
CHANGED = (
    r"break|broke|removed|renamed|replaced|deleted|deprecated|"
    r"moved|changed|gained|added|no longer"
)
MODULES = ("check_figure", "check_palette", "suggest_fixes")


def _existed_at(tag: str, module: str) -> bool:
    """Whether `module` was a file in `skill/scripts` at `tag`.

    griffe resolves a module by importing it out of a worktree checked out at
    the tag, so a module added since then raises ModuleNotFoundError: a
    non-zero exit with no finding in it, which `main` refuses as the tool
    failing. That refusal is right for a broken griffe and wrong here. A module
    with no history at the tag has no API a caller could have depended on.
    """
    listed = subprocess.run(
        ["git", "ls-tree", "--name-only", tag, f"skill/scripts/{module}.py"],
        capture_output=True, text=True,
    )
    return listed.returncode == 0 and listed.stdout.strip() != ""


def _notes(changelog: str) -> tuple[str, str]:
    """The section a break has to be named in, and the heading it sits under.

    `## Unreleased` while the cycle is open, and the release's own heading once
    it is cut. bump-my-version renames `## Unreleased` to `## 0.7.0 — 2026-08-03`
    in the same commit that drops the `.dev` suffix from `pyproject.toml`, so
    from the bump until the next cycle opens there is no Unreleased section at
    all. Reading only that heading failed every release that carried a break --
    on the commit that had just written the break down, under its own version.

    The version comes from `pyproject.toml` rather than from taking whichever
    section is topmost: a paragraph in an already-shipped release would
    otherwise stand in for a break made after it went out.
    """
    unreleased = re.search(
        r"^## Unreleased\n(.*?)(?=^## |\Z)", changelog, re.S | re.M,
    )
    if unreleased:
        return unreleased.group(1), "Unreleased"

    pyproject = pathlib.Path("pyproject.toml")
    if not pyproject.is_file():
        return "", "Unreleased"
    with pyproject.open("rb") as handle:
        version = tomllib.load(handle).get("project", {}).get("version")
    if not version:
        return "", "Unreleased"

    released = re.search(
        rf"^## {re.escape(version)}(?:\s[^\n]*)?\n(.*?)(?=^## |\Z)",
        changelog, re.S | re.M,
    )
    return (released.group(1) if released else ""), version


def main() -> None:
    tag_result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True,
    )
    if tag_result.returncode != 0:
        sys.exit("no release tag to compare against")
    tag = tag_result.stdout.strip()

    broken = {}
    for module in MODULES:
        if not _existed_at(tag, module):
            print(f"--- {module} against {tag} ---")
            print(f"  new since {tag}, no API it could have broken")
            continue
        try:
            result = subprocess.run(
                ["griffe", "check", "-s", "skill/scripts", module, "-a", tag],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            sys.exit(
                f"griffe is not installed, so the public API of {module} "
                "cannot be compared against the last tag.\n"
                "That is the tool failing, not the API passing."
            )
        report = (result.stdout + result.stderr).strip()
        print(f"--- {module} against {tag} ---")
        print(report or "  no breaking change")
        if result.returncode != 0:
            found = REPORTED.findall(report)
            if not found:
                sys.exit(
                    f"griffe exited {result.returncode} for {module} "
                    f"without reporting a finding:\n{report}\n"
                    "That is the tool failing, not the API passing."
                )
            for name in found:
                broken[name] = module

    if not broken:
        print(f"\nNothing a caller could do at {tag} has stopped working.")
        sys.exit(0)

    # The changelog gate is deliberately coarse: griffe reports the top-level
    # name that broke, so a tuple change surfaces as `GATES` and not the row
    # that moved. This proves "the notes name the symbol next to a change
    # verb", not "the specific break is written down", and a symbol already
    # named there can pass without a new entry. Diffing the symbol's
    # repr against the last tag would catch that, but parsing it is more
    # brittle than the bar this holds.
    changelog = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
    section, heading = _notes(changelog)
    paragraphs = section.split("\n\n")
    # `(?<!\w)`/`(?!\w)` rather than `\b`, because half the names griffe reports
    # end in a character `\b` cannot follow. A parameter change is reported as
    # `audit(context_axes)`, and a `\b` after that `)` asks for a word character
    # next to it -- so it matched only when the name was immediately followed by
    # a letter, which no sentence does. The gate was unsatisfiable for that whole
    # class of break: no wording of the notes could clear it, and the first
    # parameter change this project made failed CI with the section naming every
    # one of the five. Every earlier release passed because griffe had only ever
    # reported bare names like `delta_e` and `GATES`, which end in a word
    # character.
    #
    # The lookarounds keep what `\b` was there for: `delta_e` still does not
    # match inside `delta_error`.
    silent = sorted(
        name for name in broken
        if not any(
            re.search(rf"(?<!\w){re.escape(name)}(?!\w)", para)
            and re.search(CHANGED, para, re.I)
            for para in paragraphs
        )
    )

    if not silent:
        print(f"\nBreaking, and the {heading} section names every one.")
        sys.exit(0)

    sys.exit(
        "\nThese changed in a way a caller would notice, and "
        f"CHANGELOG.md's {heading} section does not name them:\n"
        + "\n".join(f"  {name} ({broken[name]})" for name in silent)
        + "\n\nThese modules are vendored by copy. A reader who pasted "
          "one into their toolchain finds out at import, so the break "
          "belongs in the changelog before it belongs in a release."
    )


if __name__ == "__main__":
    main()
