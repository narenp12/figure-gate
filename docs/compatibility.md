# Compatibility

What each file needs to run, and what changes between versions.

## Requirements

| Component | Python | Other |
|---|---|---|
| `check_palette.py` | 3.8+ | standard library only |
| `check_figure.py` | 3.11+ | matplotlib 3.8+ |
| figure-gate from PyPI or conda-forge | 3.11+ | matplotlib 3.8+ |
| `colormaps["okabe_ito"]` | 3.11+ | matplotlib 3.11+ |

`check_palette.py` runs on Python 3.8 when you copy the file. It does not when
you install the package, because the package carries `check_figure.py` too and
that needs 3.11. The `requires-python` floor for the distribution is 3.11.

CI runs the palette checker on Python 3.8, 3.9, 3.11, and 3.13 with no
`pip install` at all. The test job runs against the current matplotlib and pins
one row to matplotlib 3.8.4, so a break in either direction shows up.

### Optional dependencies

SciPy is optional and changes only speed. `check_overplotting` uses a KD-tree
when scipy imports, and an O(n²) numpy path when it does not. The verdict is the
same either way.

`suggest_fixes.py` is optional. Without it, `check_figure.py` audits
identically; you lose `report(fig, suggest=True)` and `suggest(rows)`.

### Type annotations

`py.typed` ships with the installed package, so your type checker sees the
annotations on that route. It does not on the vendored route: those files are
loose modules with no package for the marker to attach to, and PEP 561 reads
every annotation in them as `Any`.

## Import lines by version

| Route | Version | Import line |
|---|---|---|
| Vendored | any | `import check_figure` |
| Installed | 0.7.0 and later | `from figure_gate import check_figure` |
| Installed | 0.6.0 and earlier | `import check_figure` |

Version 0.7.0 moved the modules into the `figure_gate` package. Through 0.6.0
the wheel put them at the top level of site-packages, which is why an older
install uses the same line as a vendored copy.

To check which version you have:

```bash
uv pip show figure-gate      # or: conda list figure-gate
```

## Version policy

The public API is every name without a leading underscore in `check_figure.py`,
`check_palette.py`, and `suggest_fixes.py`.

Below 1.0, a minor release may break that API. Version 0.7.0 broke the install
path's import line. Every break is named in
[the changelog](changelog.md) under its release heading.

Two things about the contract:

- The number of rows is not part of it. Gates get added: `check_banking`
  arrived after 0.6.0 and moved the count.
- The shape is part of it. `audit` returns `(ok, rows)`, each row a
  `(name, status, detail)` triple whose `status` is `True`, `False`, or
  `"warn"`. `check` returns the same shape.

For how that contract is enforced, see
[What the API promises](design.md#what-the-api-promises).

## Other plotting libraries

The checks in `check_figure.py` are matplotlib-specific, because they read a
matplotlib `Figure`. The rules they enforce are not.
[The figure style guide](style-guide.md) writes up each rule independently of
any library, so you can apply them by hand or port the checks. Each one reads
geometry that any plotting library can report.

`check_palette.py` has no such limit. It takes hex strings, so any toolchain can
call it.
