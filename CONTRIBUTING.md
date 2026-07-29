# Contributing

## The bar for a new gate

This project is a pile of elimination gates, and the failure mode it guards
against hardest is a gate that sounds sensible and never fires. So a new check
ships with three things:

1. **A named failure.** Not "figures should have good contrast" — a real figure
   that was really broken, and how. The style guide is written this way
   throughout, and it's the reason the thresholds are arguable rather than
   arbitrary.
2. **A test proving it fails.** Build a figure with exactly that defect and
   assert *that* gate is the one that catches it. Asserting only that `audit`
   returned `False` would pass even if every other check had silently broken.
3. **A test proving it doesn't over-fire.** Whatever legitimate case sits
   nearest the line — side-by-side panels each needing their own x label, a
   heatmap at 0.98 ink coverage. Every false positive spends the credibility the
   gate runs on, and three of the existing checks fired on things that never
   render before they were tuned.

If the right density or spacing genuinely depends on the form, make it a `WARN`
rather than a `FAIL`. A gate people learn to skip is worse than no gate.

## Changing a threshold

Thresholds are measured, and several are quoted in the guide and pinned in
`tests/test_palette.py`. If you change one, update both — a reader who catches
the docs quoting a number the code doesn't produce has no reason to trust
anything else in them.

## Writing prose

`tests/test_prose_claims.py` sweeps the reference material rather than checking
named claims one at a time. Three things follow from that when you write a
sentence.

**Anything in backticks has to exist.** Constants, functions, files, flags,
rcParam keys, colormap names. A name that resolves nowhere fails, and the fix is
usually that the name is wrong. If it genuinely cannot resolve — a LaTeX
package, an error string quoted so a reader recognises it — add it to
`UNRESOLVED_SPANS` with the reason. That set is meant to stay small.

**A constant belongs to the module the paragraph names.** A paragraph about
`check_figure.py` that names a `check_palette.py` constant fails, because a
reader porting the checks greps the module the paragraph named. This is a real
defect that shipped.

**A claim about the world needs a source and a recorded verification.** Journal
type floors, font requirements, published results: those go in
`EXTERNAL_CLAIMS` with the document, an anchor phrase, the source, the date it
was checked, and the passage that supports it. No test can verify a claim about
the world; what the ledger does is make the human check enumerable, dated, and
auditable without repeating the search. The cited work also has to appear in the
document's own References, because a source only the test file knows about is
not a source the reader has.

Numbers keep working the way they already did: write them as
`` `NAME = value` `` and the doc suite pins them against the code.

## Style

Comments explain *why*, since the *what* is usually legible from the code.
Several of the longer comments exist to stop a future reader from "fixing"
something that was already tried and reverted for a measured reason; keep them.

## Running things

```bash
pip install -e ".[dev]"
pytest -q                              # the suite
python skill/scripts/check_figure.py   # the checker rejects a bad figure
python examples/demo.py                # end-to-end
```

`check_palette.py` must keep importing nothing outside the standard library.
That's what makes it usable from a non-Python toolchain, and CI has a job with
no `pip install` in it to make sure the claim stays true.
