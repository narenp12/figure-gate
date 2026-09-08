"""Every row of every corpus figure, as JSON, so a gate change can be diffed.

A change that makes a gate fire more often has to be measured before it ships,
and the measurement is always the same: run the corpus on the commit before,
run it after, diff the rows. That procedure has been reconstructed from memory
every round it was needed, which is the failure this file exists to stop, and
the same one the `Makefile` header describes.

Usage:

    python examples/corpus_sweep.py before.json          # on the base commit
    python examples/corpus_sweep.py after.json           # on the branch
    python examples/corpus_sweep.py --diff before.json after.json

Nothing is written into the tree. `gallery.OUT = None` makes `finish` return
the figure instead of saving it, `demo.build(out=None)` does the same, and
`gallery.main` is never called, so no committed PNG is touched. Check that with
`git status --porcelain examples/` after a run: it should be empty.

The rows come from `audit`, not from `report`, and with the same keyword
arguments each builder passes to `report`. Reading `report`'s printed table
back would measure the formatting as well as the verdict.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

import matplotlib                                                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

sys.path.insert(0, str(ROOT / "skill" / "scripts"))
sys.path.insert(0, str(HERE))

import check_figure as cf                                        # noqa: E402
import demo                                                      # noqa: E402
import gallery                                                   # noqa: E402


def sweep() -> dict:
    """Audit every corpus figure and return `{name: [[row, status, detail]]}`.

    `gallery.BUILDERS` is the enumeration rather than everything callable in
    the module: `main` writes the PNGs, `finish` is the shared tail, `styled`
    is the decorator, and `palettes` gates colours rather than a figure.
    """
    gallery.OUT = None
    captured: dict[str, list] = {}

    def spy(fig, name="", scale=None, placed_frac=1.0, *,
            context_axes=None, venue=None, suggest=False):
        """`report`'s signature, `audit`'s answer, kept."""
        ok, rows = cf.audit(fig, scale, placed_frac,
                            context_axes=context_axes, venue=venue)
        captured[name] = [[row, str(status), detail]
                          for row, status, detail in rows]
        return ok

    # Both modules did `import check_figure as cf` at their own module scope,
    # so patching the attribute on `cf` alone would leave their bound names
    # pointing at the real `report`.
    real = cf.report
    cf.report = gallery.cf.report = demo.cf.report = spy
    errors: dict[str, str] = {}
    try:
        for build in gallery.BUILDERS:
            try:
                # The builders print their own table. That is the point of them
                # when a person runs the gallery, and noise when a machine
                # diffs them.
                with contextlib.redirect_stdout(io.StringIO()):
                    build()
            except Exception as exc:                             # noqa: BLE001
                errors[build.__name__] = f"{type(exc).__name__}: {exc}"
            plt.close("all")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                demo.build(out=None)
        except Exception as exc:                                 # noqa: BLE001
            errors["demo.build"] = f"{type(exc).__name__}: {exc}"
        plt.close("all")
    finally:
        cf.report = gallery.cf.report = demo.cf.report = real

    return {"figures": captured, "errors": errors}


def diff(before: dict, after: dict) -> int:
    """Print every row that moved. Returns the number of verdict changes.

    A detail string that moved under an unchanged verdict is printed too, and
    deliberately does not count: it is not a behaviour change, but it is the
    thing a reader notices in a report and it should not appear unexplained.
    """
    bf, af = before["figures"], after["figures"]
    gone = sorted(set(bf) - set(af))
    new = sorted(set(af) - set(bf))
    for name in gone:
        print(f"MISSING  {name} audited before and not after")
    for name in new:
        print(f"NEW      {name} audited after and not before")

    moved = 0
    for name in sorted(set(bf) & set(af)):
        b = {row: (status, detail) for row, status, detail in bf[name]}
        a = {row: (status, detail) for row, status, detail in af[name]}
        for row in b:
            bs, bd = b[row]
            as_, ad = a.get(row, ("MISSING", ""))
            if bs != as_:
                moved += 1
                print(f"VERDICT  {name:24s} {row:22s} {bs} -> {as_}")
                print(f"         {ad}")
            elif bd != ad:
                print(f"detail   {name:24s} {row:22s} ({bs})")
                print(f"         - {bd}")
                print(f"         + {ad}")

    figures = len(set(bf) & set(af))
    print(f"\n{figures} figures compared; {moved} verdict changes")
    return moved + len(gone) + len(new)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", metavar="PATH",
                        help="output file, or two input files with --diff")
    parser.add_argument("--diff", action="store_true",
                        help="compare two sweep files instead of running one")
    args = parser.parse_args(argv)

    if args.diff:
        if len(args.paths) != 2:
            parser.error("--diff takes exactly two files")
        before, after = (json.loads(Path(p).read_text()) for p in args.paths)
        return 0 if diff(before, after) == 0 else 1

    if len(args.paths) != 1:
        parser.error("a sweep takes exactly one output file")
    result = sweep()
    out = Path(args.paths[0])
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(f"{len(result['figures'])} figures, "
          f"{len(result['errors'])} errors -> {out}")
    for name, err in result["errors"].items():
        print(f"  ERROR {name}: {err}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
