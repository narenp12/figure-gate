---
description: "Signatures and docstrings for the three modules, read out of the scripts when this page builds."
---

# API

Signatures and docstrings are read out of `skill/scripts/` when this page
builds, so what is shown is what the code has.

Installed, the three modules are a package:

```python
from figure_gate import check_figure as cf     # needs matplotlib
from figure_gate import check_palette as cp    # standard library only
from figure_gate import suggest_fixes as sf
```

Vendoring, the default route, copies the files into your own project. They are
then whatever you named them, imported flat:

```python
import check_figure as cf
import check_palette as cp
import suggest_fixes as sf
```

Same modules, same signatures; only the import line differs. Everything below
applies to both.

Not on this page: **the thresholds**. They are module-level constants, one
table per module on [the gates](gates.md), with the measurement behind each on
[the style guide](style-guide.md). Read them as `cf.TYPE_FLOOR_PT`.

Everything else is here, including the 21 gate functions, at the bottom.
`audit` is what most callers want: it runs all 21 and computes the renderer,
canvas and scale arguments they take. Call one directly and that is yours to
reproduce, which [the how-to](how-to.md#read-one-row-or-call-one-gate) covers.

## check_figure

Composition. Takes a built figure, measures what it renders at print size.

::: check_figure.audit

::: check_figure.report

::: check_figure.describe

::: check_figure.alt_metadata

::: check_figure.page_scale

::: check_figure.content_width_pt

::: check_figure.scatter_diameter_pt

## check_palette

Colour. Standard library only, so these are also the functions to port when
the checks are reimplemented elsewhere.

::: check_palette.check

::: check_palette.cmap_kind

::: check_palette.cmap_kind_rgb

::: check_palette.cmap_back_travel

::: check_palette.cmap_back_travel_rgb

::: check_palette.contrast

::: check_palette.delta_e

::: check_palette.simulate

::: check_palette.simulate_anomalous

::: check_palette.hex_to_linear

::: check_palette.oklab_distance

::: check_palette.linear_to_oklab

::: check_palette.linear_to_cam02ucs

::: check_palette.relative_luminance

## suggest_fixes

Remedies. Both take the rows `audit` returned, not the figure.

::: suggest_fixes.suggest

::: suggest_fixes.format_suggestions

## The gate functions

One row each, in the order `audit` runs them, which is the order
[the gates](gates.md) tables them in and the order a report prints. Every one
returns `(status, detail)`, where `status` is `True`, `False` or `"warn"`.

The signature says what the gate needs beyond the figure. A `r` parameter is a
renderer, `canvas` an already-drawn canvas, and `scale`/`placed_frac`/`venue`
the page arithmetic. `audit` supplies all of them.

::: check_figure.check_clipping

::: check_figure.check_collisions

::: check_figure.check_text_readability

::: check_figure.check_contrast_stack

::: check_figure.check_mark_ratio

::: check_figure.check_overplotting

::: check_figure.check_redundancy

::: check_figure.check_type_size

::: check_figure.check_line_weight

::: check_figure.check_banking

::: check_figure.check_ink

::: check_figure.check_series_color

::: check_figure.check_dual_axis

::: check_figure.check_form

::: check_figure.check_identity_channel

::: check_figure.check_label_attribution

::: check_figure.check_style_sheet

::: check_figure.check_contour_dash

::: check_figure.check_colormap

::: check_figure.check_fonts

::: check_figure.check_alt_text
