# figure-gate

[![CI](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/figure-gate)](https://pypi.org/project/figure-gate/)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/figure-gate)](https://anaconda.org/conda-forge/figure-gate)
[![Docs](https://img.shields.io/badge/docs-narenp12.github.io-0072B2)](https://narenp12.github.io/figure-gate/)

**Two scripts that read a built matplotlib figure and report which gates it
fails, and a third that answers the rows that failed.** `audit(fig)` returns
`(ok, rows)`, 21 rows, one per gate, each a `(label, status, detail)` triple
where `status` is `True`, `False`, or `"warn"`. `check(colors)` gates a palette
the same way in 5 rows and returns the same shape. `suggest(rows)` turns the
rows that did not pass into remedies, in the order the gates reported them.
Every threshold is a module-level constant you can read and change.

There is also an [Agent Skill](https://code.claude.com/docs/en/skills) wrapper
that applies the same checks when Claude Code builds a figure.

```bash
git clone https://github.com/narenp12/figure-gate && cd figure-gate
python skill/scripts/check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
python skill/scripts/check_figure.py     # self-test on a broken figure
```

![Validation loss against training epoch for three optimisers over 12 epochs.
All three fall; the Bayesian run reaches 0.12 by epoch 6 and 0.02 by epoch 12,
while the baseline is still at 0.25 at epoch 12.](https://raw.githubusercontent.com/narenp12/figure-gate/main/examples/demo.png)

*`python examples/demo.py` builds that figure and audits it, and `python
examples/gallery.py` covers the harder forms.
Writing those eleven found seven defects in the checks themselves.*

## Documentation

Everything below the quickstart lives on the
[docs site](https://narenp12.github.io/figure-gate/):

- [Getting started](https://narenp12.github.io/figure-gate/getting-started/):
  install or vendor, the two settings that need your document's values, and the
  code to call.
- [The gates](https://narenp12.github.io/figure-gate/gates/): what each row
  measures, its threshold, and what a passing run does not mean.
- [The style guide](https://narenp12.github.io/figure-gate/style-guide/): the
  measurement behind each threshold, and the rules tried and reverted.
- [Choosing a form](https://narenp12.github.io/figure-gate/choosing-a-form/):
  the decision no styling rule rescues.
- [API reference](https://narenp12.github.io/figure-gate/api/): signatures and
  defaults, generated from the scripts when the site builds.

```bash
uv add figure-gate          # or: conda install -c conda-forge figure-gate
```

## Where this sits

Prescriptive style sheets already exist and are good:
[SciencePlots](https://github.com/garrettj403/SciencePlots) and LovelyPlots for
journal looks, [tueplots](https://github.com/pnkraemer/tueplots) and mpl_sizes
for exact conference sizing. Accessibility tooling exists too:
[matplotalt](https://github.com/KaiNylund/matplotalt) generates alt text,
Chart4Blind converts a chart image into an accessible one, contrast reporters
check colors in isolation.

Each of those acts before or beside the figure. None of them reads the built
result and reports what it fails, which is the only thing here, so a style
sheet and this are complementary: set defaults with one, verify them with the
other.

## What the API promises

The public API is every name without a leading underscore in `check_figure.py`,
`check_palette.py` and `suggest_fixes.py`. That is broader than the handful you
would guess, and it is deliberately the same set the release gate compares, so
the statement and the enforcement cannot drift apart.

Below 1.0, a minor bump may break it. Every break is named in the changelog
under its release heading, and no change reaches `main` whose `## Unreleased`
section fails to name what moved: CI runs
[`audit_api.py`](https://github.com/narenp12/figure-gate/blob/main/skill/scripts/audit_api.py)
against the last tag on every pull request, and a symbol that changed without
being written down fails the build.

The number of rows is not part of the contract. The shape is: `audit` returns
`(ok, rows)`, each row a `(label, status, detail)` triple whose `status` is
`True`, `False` or `"warn"`, and `check` returns the same shape. Gates get
added; `check_banking` arrived after 0.6.0 and moved the count.

What is not enforced is the sentence rather than the symbol. The gate checks
that a changed name appears in `## Unreleased` next to a word admitting a
change. It cannot check that the sentence describes the change accurately.

## Contributing

New gates are welcome at the bar the project holds itself to: a test proving
the gate fails on a figure with that defect, a test proving it does not
over-fire on the nearest legitimate case, and a note naming the real failure
that motivated it. See [CONTRIBUTING.md](https://github.com/narenp12/figure-gate/blob/main/CONTRIBUTING.md)
and [SECURITY.md](https://github.com/narenp12/figure-gate/blob/main/SECURITY.md).

## License

MIT, see [LICENSE](https://github.com/narenp12/figure-gate/blob/main/LICENSE).
