# API

Everything here is read out of `skill/scripts/` when this page is built, so a
signature or a default shown below is the one the code has. That is the point
of the page: a hand-written reference is a second copy of every default, and
this project has a test file about prose drifting from the code it describes.

Two modules, and they are files rather than a package. `check_palette.py`
imports nothing outside the standard library, which is what makes it
vendorable into a non-Python toolchain; `check_figure.py` needs matplotlib.
Copy them, or `pip install figure-gate` and import them by name:

```python
import check_figure as cf
import check_palette as cp
```

The **thresholds are module-level constants** and are not repeated here. The
tables on [the gates](gates.md) list every one with its failure condition, and
[the style guide](style-guide.md) explains what each was measured against. Read
them in the source with `cf.TYPE_FLOOR_PT` and the like; they are meant to be
changed.

The **twenty-one gate functions**, meaning `check_clipping`, `check_type_size`,
`check_series_color` and the rest, are deliberately not documented here.
`audit()` runs all of them, in the order [the gates](gates.md) lists, and
calling one directly means reproducing the renderer and scale arguments
`audit()` computes. What a caller needs from them is the threshold and the
failure condition, which is what those tables are.

## check_figure

The composition side. Everything takes a built matplotlib figure and measures
what it renders, at the size it will print.

::: check_figure.audit

::: check_figure.report

::: check_figure.describe

::: check_figure.alt_metadata

::: check_figure.page_scale

::: check_figure.content_width_pt

::: check_figure.scatter_diameter_pt

## check_palette

The colour side. Standard library only, so these run anywhere and are also the
functions to port if the checks are being reimplemented elsewhere.

::: check_palette.check

::: check_palette.cmap_kind

::: check_palette.cmap_back_travel

::: check_palette.contrast

::: check_palette.delta_e

::: check_palette.simulate

::: check_palette.simulate_anomalous

::: check_palette.hex_to_linear

::: check_palette.linear_to_oklab

::: check_palette.relative_luminance
