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
