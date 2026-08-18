# Install figure-gate

Three routes put the checkers on your machine. They all get you the same code.

Choose a route:

- **Vendored** if you want to read and edit the rules beside the figures they
  gate. This is the route the documentation teaches, because the thresholds are
  meant to be edited.
- **Installed** if you want to pin a version.
- **conda-forge** if your environment is managed by conda.

For the version each route needs, see [Compatibility](compatibility.md).

=== "Vendored"

    ```bash
    git clone https://github.com/narenp12/figure-gate
    cp figure-gate/skill/assets/figure.mplstyle       your-project/diagrams/
    cp figure-gate/skill/scripts/check_palette.py     your-project/diagrams/
    cp figure-gate/skill/scripts/check_figure.py      your-project/diagrams/
    cp figure-gate/skill/scripts/suggest_fixes.py     your-project/diagrams/  # optional
    ```

    !!! warning "Copy `check_palette.py` even if you only want to check figures"

        `check_figure.py` imports it, and that import is what the series-color
        and colormap rows travel on. Without it, neither row raises: both
        report that nothing was checked, and both pass.

    `suggest_fixes.py` is optional. `check_figure.py` imports it lazily, so a
    copy without it audits identically. You lose only `report(fig, suggest=True)`
    and `suggest(rows)`.

=== "Installed"

    ```bash
    uv add figure-gate                        # the library, and the two commands
    uv tool install figure-gate               # the two commands only, no import
    ```

    Installing puts the two checkers on your PATH as `check-palette` and
    `check-figure`.

    `py.typed` ships with the package, so your type checker sees the
    annotations. It does not see them on the vendored route: those files are
    loose modules with no package for the marker to attach to, and PEP 561 reads
    every annotation in them as `Any`.

=== "conda-forge"

    ```bash
    conda install -c conda-forge figure-gate
    ```

    conda-forge follows PyPI through the feedstock's autotick bot, which opens
    the version bump some hours after a release. Until that merges, the conda
    package is the previous release. The badges on
    [the repository](https://github.com/narenp12/figure-gate) show what each
    index is serving now.

To check what you got:

```bash
uv pip show figure-gate      # or: conda list figure-gate
```

## Choose your import line

The import line depends on your route and, if you installed, on your version.
Version 0.7.0 moved the modules into the `figure_gate` package. Through 0.6.0
the wheel put them at the top level of site-packages.

=== "0.7+ installed"

    ```python
    from figure_gate import check_figure as cf
    from figure_gate import check_palette as cp
    from figure_gate import suggest_fixes as sf
    ```

=== "0.6 and earlier"

    The same line a vendored copy uses:

    ```python
    import check_figure as cf
    import check_palette as cp
    import suggest_fixes as sf
    ```

=== "Vendored"

    ```python
    import check_figure as cf
    import check_palette as cp
    import suggest_fixes as sf
    ```

## Configure it for your document

Two settings take values only you know. Both are optional, and both change what
the checks measure against.

1. Set `font.serif` in `figure.mplstyle` to your document's body typeface.
2. Set `CONTENT_WIDTH_PT` at the top of `check_figure.py` to the usable width of
   your page, in points.

Left as `None`, `CONTENT_WIDTH_PT` gives a scale of 1.0 and the page calculation
does nothing. That is correct if you author every figure at the width it is
placed at. To override it for one call, pass `venue=` instead. See
[Place a figure at a venue's width](how-to.md#place-a-figure-at-a-venues-width).

If your style sheet lives somewhere other than beside `check_figure.py`, set
`STYLE_SHEET` at the top of that file to the path. Left as `None`, the checker
looks beside the script, then in an `assets/` directory next to it.

If you install the package rather than vendoring it, `figure.mplstyle` ships
inside it, beside the module that reads it. That is where the style-sheet gate
looks.

!!! warning "The style-sheet gate passes when it finds no sheet"

    Without a sheet to compare against, the gate reports a pass, including for
    the figure it exists to catch: one drawn with `plt.style.use` forgotten
    entirely.

## Install it as a Claude Code skill

This repository is also a plugin marketplace, so Claude Code can install the
skill and track updates against the tags the project already cuts:

```bash
/plugin marketplace add narenp12/figure-gate
```

Then run `/plugin install figure-gate@figure-gate`. The skill is invoked as
`figure-gate:research-figures`.

To edit the thresholds in place, copy the skill instead:

```bash
cp -r figure-gate/skill ~/.claude/skills/research-figures
```

Claude then runs these checks when you ask for a figure for a paper or a deck.

## Next steps

- [Gate your first figure](tutorial.md) if you have not run the checkers before.
- [How-to guides](how-to.md) for a task you already have in mind.
