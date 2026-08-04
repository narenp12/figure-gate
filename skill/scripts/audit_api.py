import re
import subprocess
import sys
import pathlib

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
    # that moved. This proves "Unreleased names the symbol next to a change
    # verb", not "the specific break is written down", and a symbol already
    # named in Unreleased can pass without a new entry. Diffing the symbol's
    # repr against the last tag would catch that, but parsing it is more
    # brittle than the bar this holds.
    changelog = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = re.search(
        r"^## Unreleased\n(.*?)(?=^## |\Z)", changelog, re.S | re.M,
    )
    section = unreleased.group(1) if unreleased else ""
    paragraphs = section.split("\n\n")
    silent = sorted(
        name for name in broken
        if not any(
            re.search(rf"\b{re.escape(name)}\b", para)
            and re.search(CHANGED, para, re.I)
            for para in paragraphs
        )
    )

    if not silent:
        print("\nBreaking, and the Unreleased section names every one.")
        sys.exit(0)

    sys.exit(
        "\nThese changed in a way a caller would notice, and "
        "CHANGELOG.md's Unreleased section does not name them:\n"
        + "\n".join(f"  {name} ({broken[name]})" for name in silent)
        + "\n\nThese modules are vendored by copy. A reader who pasted "
          "one into their toolchain finds out at import, so the break "
          "belongs in the changelog before it belongs in a release."
    )


if __name__ == "__main__":
    main()
