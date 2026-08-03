# API

Signatures and docstrings are read out of `skill/scripts/` when this page
builds, so what is shown is what the code has.

```python
import check_figure as cf     # needs matplotlib
import check_palette as cp    # standard library only
import suggest_fixes as sf
```

Not on this page:

- **Thresholds.** Module-level constants, one table per module on
  [the gates](gates.md), with the measurement behind each on
  [the style guide](style-guide.md). Read them as `cf.TYPE_FLOOR_PT`.
- **The 21 gate functions** (`check_clipping`, `check_type_size` and the rest).
  `audit` runs them and computes the arguments they take.
  [The gates](gates.md) is their reference.

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

::: check_palette.cmap_back_travel

::: check_palette.contrast

::: check_palette.delta_e

::: check_palette.simulate

::: check_palette.simulate_anomalous

::: check_palette.hex_to_linear

::: check_palette.linear_to_oklab

::: check_palette.relative_luminance

## suggest_fixes

Remedies. Both take the rows `audit` returned, not the figure.

::: suggest_fixes.suggest

::: suggest_fixes.format_suggestions
