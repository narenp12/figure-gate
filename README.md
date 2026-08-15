# figure-gate

[![CI](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/figure-gate)](https://pypi.org/project/figure-gate/)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/figure-gate)](https://anaconda.org/conda-forge/figure-gate)
[![Docs](https://img.shields.io/badge/docs-narenp12.github.io-0072B2)](https://narenp12.github.io/figure-gate/)

**One script reads a built matplotlib figure and reports which gates it fails,
a second gates a palette on its own, and a third answers the rows that
failed.** `audit(fig)` returns `(ok, rows)`, 21 rows, one per gate, each a
`(label, status, detail)` triple where `status` is `True`, `False`, or
`"warn"`. `check(colors)` gates a palette the same way in 5 rows and returns
the same shape. `suggest(rows)` turns the rows that did not pass into remedies,
in the order the gates reported them. Every threshold is a module-level
constant you can read and change.

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

<div class="grid cards">
<ul>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-rocket" viewBox="0 0 24 24"><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09"/><path d="M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/getting-started/">Getting started</a></strong> — install or vendor, the two settings that need your document's values, and the code to call</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-wrench" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/how-to/">How to</a></strong> — the recipes: fix a row that failed, gate figures in CI, place at half width, attach alt text, move a threshold</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-filter" viewBox="0 0 24 24"><path d="M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/gates/">The gates</a></strong> — what each row measures, its threshold, and what a passing run does not mean</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-image" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/gallery/">Gallery</a></strong> — eleven figures covering the harder forms, each with its audit</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-book" viewBox="0 0 24 24"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/style-guide/">Style guide</a></strong> — the measurement behind each threshold, and the rules tried and reverted</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-code" viewBox="0 0 24 24"><path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/api/">API reference</a></strong> — signatures and defaults, generated from the scripts when the site builds</li>
</ul>
</div>

## Documentation

Everything below the quickstart lives on the
[docs site](https://narenp12.github.io/figure-gate/). The six cards above link
the main pages; the one page the grid does not carry is
[Choosing a form](https://narenp12.github.io/figure-gate/choosing-a-form/), the
decision no styling rule rescues.

```bash
uv add figure-gate          # or: conda install -c conda-forge figure-gate
```

```python
from figure_gate import check_figure as cf
```

That import line is 0.7.0 and later; through 0.6.0 it was `import
check_figure`, the same line a vendored copy uses at every version. The two
badges may disagree on which version that is, because conda-forge follows PyPI
through a bot rather than in the same hour.
[Getting started](https://narenp12.github.io/figure-gate/getting-started/#install)
has both routes and how to tell which one you are on.

Copying the files into your own project is the other route, and the default one
the docs teach.

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
`check_palette.py` and `suggest_fixes.py`, and below 1.0 a minor bump may break
it: 0.7.0 broke the install path's import line. Every break is named in the
changelog under its release heading, and CI fails a pull request whose
`## Unreleased` section does not name a symbol that moved.

The row count is not part of the contract; the shape is. The full statement,
including what the gate cannot check, is on
[the docs site](https://narenp12.github.io/figure-gate/getting-started/#what-the-api-promises).

## Contributing

New gates are welcome at the bar the project holds itself to: a test proving
the gate fails on a figure with that defect, a test proving it does not
over-fire on the nearest legitimate case, and a note naming the real failure
that motivated it. See [CONTRIBUTING.md](https://github.com/narenp12/figure-gate/blob/main/CONTRIBUTING.md)
and [SECURITY.md](https://github.com/narenp12/figure-gate/blob/main/SECURITY.md).

## License

MIT, see [LICENSE](https://github.com/narenp12/figure-gate/blob/main/LICENSE).
