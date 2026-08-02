import re
import subprocess
import sys
import pathlib

REPORTED = re.compile(r"^\S+?:\d+: (\S+?): ", re.M)
CHANGED = r"break|broke|removed|renamed|replaced|no longer"
MODULES = ("check_figure", "check_palette")


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
        result = subprocess.run(
            ["griffe", "check", "-s", "skill/scripts", module, "-a", tag],
            capture_output=True, text=True,
        )
        report = (result.stdout + result.stderr).strip()
        print(f"--- {module} against {tag} ---")
        print(report or "  no breaking change")
        found = REPORTED.findall(report)
        if result.returncode != 0 and not found:
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

    changelog = pathlib.Path("CHANGELOG.md").read_text()
    unreleased = re.search(
        r"^## Unreleased\n(.*?)(?=^## )", changelog, re.S | re.M,
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
