# figure-gate

[![CI](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/narenp12/figure-gate/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/figure-gate)](https://pypi.org/project/figure-gate/)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/figure-gate)](https://anaconda.org/conda-forge/figure-gate)
[![Docs](https://img.shields.io/badge/docs-narenp12.github.io-0072B2)](https://narenp12.github.io/figure-gate/)

figure-gate reads a matplotlib figure you have already built and tells you which
publication requirements it fails. It checks colorblind-safe color, composition,
and whether your type is still legible at the size the figure actually prints.

`audit(fig)` returns `(ok, rows)`, 21 rows, one per check. Each row is a
`(name, status, detail)` triple:

```python
ok, rows = audit(fig)     # (False, [("Clipping", False, "clipped: [...]"), ...])
```

figure-gate verifies figures. It does not draw them, restyle them, or judge
whether a figure is good. Each check forbids one named defect, so a figure that
passes every row has avoided 21 named defects and nothing more.

Every threshold is a module-level constant you can read and change.

## Try it

```bash
git clone https://github.com/narenp12/figure-gate && cd figure-gate
python skill/scripts/check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
python skill/scripts/check_figure.py     # self-test on a deliberately broken figure
```

The second command prints a failing report and exits 0, because a checker that
cannot fail is not a checker.

![Validation loss against training epoch for three optimisers over 12 epochs.
All three fall; the Bayesian run reaches 0.12 by epoch 6 and 0.02 by epoch 12,
while the baseline is still at 0.25 at epoch 12.](https://raw.githubusercontent.com/narenp12/figure-gate/main/examples/demo.png)

*`python examples/demo.py` builds that figure and audits it, and
`python examples/gallery.py` covers the harder forms. Writing those thirteen
found seven defects in the checks themselves.*

## Documentation

The [documentation site](https://narenp12.github.io/figure-gate/) is organised
by what you came to do.

**Learning.** Start here if you have not run the checkers before:

<div class="grid cards">
<ul>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-rocket" viewBox="0 0 24 24"><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09"/><path d="M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/tutorial/">Gate your first figure</a></strong> — build a figure that fails, read the report, make it pass</li>
</ul>
</div>

**Doing a task.** Step-by-step directions for a goal you already have:

<div class="grid cards">
<ul>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-download" viewBox="0 0 24 24"><path d="M12 15V3m0 12-4-4m4 4 4-4M2 17l.621 2.485A2 2 0 0 0 4.561 21h14.878a2 2 0 0 0 1.94-1.515L22 17"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/install/">Install figure-gate</a></strong> — copy the scripts, install the package, or install from conda-forge</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-wrench" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/how-to/">How-to guides</a></strong> — fix a failing row, gate a test suite, place at half width, attach alt text</li>
</ul>
</div>

**Looking something up.** What each check measures and what each function takes:

<div class="grid cards">
<ul>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-filter" viewBox="0 0 24 24"><path d="M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/gates/">The gates</a></strong> — every row, its threshold, and whether it can fail a build</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-terminal" viewBox="0 0 24 24"><path d="m4 17 6-6-6-6M12 19h8"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/cli/">Commands</a></strong> — both command-line tools, their flags, and their exit codes</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-package-check" viewBox="0 0 24 24"><path d="m16 16 2 2 4-4"/><path d="M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0"/><path d="m7.5 4.27 9 5.15"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/compatibility/">Compatibility</a></strong> — Python and matplotlib floors, optional dependencies, import lines by version</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-code" viewBox="0 0 24 24"><path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/api/">API reference</a></strong> — signatures and defaults, generated from the scripts when the site builds</li>
</ul>
</div>

**Understanding why.** Background, evidence, and the decisions behind the thresholds:

<div class="grid cards">
<ul>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-layers" viewBox="0 0 24 24"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/design/">How the checkers decide</a></strong> — the measurement model, the evidence, and what a passing run does not mean</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-book" viewBox="0 0 24 24"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/style-guide/">Figure style guide</a></strong> — the measurement behind each threshold, and the rules tried and reverted</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-shapes" viewBox="0 0 24 24"><path d="M8.3 10a.7.7 0 0 1-.626-1.079L11.4 3a.7.7 0 0 1 1.198-.043L16.3 8.9a.7.7 0 0 1-.572 1.1Z"/><rect x="3" y="14" width="7" height="7" rx="1"/><circle cx="17.5" cy="17.5" r="3.5"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/choosing-a-form/">Choosing a form</a></strong> — the decision no styling rule rescues, built on Cleveland and McGill's ordering</li>
<li><svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-image" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg> <strong><a href="https://narenp12.github.io/figure-gate/gallery/">Gallery</a></strong> — thirteen audited figures covering the forms that are hard to check</li>
</ul>
</div>

## Use it with Claude Code

This repository is also a plugin marketplace, so Claude Code applies the same
checks when it builds a figure for you:

```bash
/plugin marketplace add narenp12/figure-gate
```

Then run `/plugin install figure-gate@figure-gate`. The skill is invoked as
`figure-gate:research-figures`.

## Where this sits

Prescriptive style sheets already exist and are good:
[SciencePlots](https://github.com/garrettj403/SciencePlots) and LovelyPlots for
journal looks, [tueplots](https://github.com/pnkraemer/tueplots) and mpl_sizes
for exact conference sizing. Accessibility tooling exists too:
[matplotalt](https://github.com/KaiNylund/matplotalt) generates alt text,
Chart4Blind converts a chart image into an accessible one, and contrast
reporters check colors in isolation.

Each of those acts before or beside the figure. None of them reads the built
result and reports what it fails, which is the only thing figure-gate does. A
style sheet and figure-gate are complementary: set your defaults with one,
verify them with the other.

## Stability

The public API is every name without a leading underscore in `check_figure.py`,
`check_palette.py`, and `suggest_fixes.py`. Below version 1.0, a minor release
may break it. Every break is named in
[the changelog](https://github.com/narenp12/figure-gate/blob/main/CHANGELOG.md)
under its release heading, and CI fails a pull request whose `## Unreleased`
section does not name a symbol that moved.

The number of rows is not part of the contract. The shape is. For the full
statement, see
[how the checkers decide](https://narenp12.github.io/figure-gate/design/#what-the-api-promises).

## Contributing

New gates are welcome at the bar the project holds itself to:

- A test proving the gate fails on a figure with that defect.
- A test proving it does not over-fire on the nearest legitimate case.
- A note naming the real failure that motivated it.

See [CONTRIBUTING.md](https://github.com/narenp12/figure-gate/blob/main/CONTRIBUTING.md)
and [SECURITY.md](https://github.com/narenp12/figure-gate/blob/main/SECURITY.md).

## License

MIT. See [LICENSE](https://github.com/narenp12/figure-gate/blob/main/LICENSE).
