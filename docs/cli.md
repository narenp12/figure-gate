---
description: "check_palette.py and check_figure.py from a shell: their arguments, flags, exit codes, and the twelve venue widths."
---

# Commands

figure-gate ships two command-line tools. Installed, they are on your PATH as
`check-palette` and `check-figure`. Vendored, run them as
`python check_palette.py` and `python check_figure.py`.

## check_palette.py

Gates a list of hex colors. Imports nothing outside the standard library.

```text
usage: check_palette.py [-h] [--surface SURFACE] [--pairs {adjacent,all}]
                        [--ordinal] [--ink INK] [--json]
                        colors
```

### Arguments

`colors`
:   Comma-separated hex colors. Required.

### Options

`--surface SURFACE`
:   The background the marks sit on. Contrast is measured against this.
    Default `#ffffff`.

`--pairs {adjacent,all}`
:   Which pairs to compare for separation. `adjacent` compares neighbours and
    is the default, which is what a line chart needs. `all` compares every
    pair, which is what a scatter needs.

`--ordinal`
:   Treat the colors as an ordered ramp. Swaps the five categorical rows for
    the four ramp rows.

`--ink INK`
:   Comma-separated hex values for neutrals. These are exempt from the chroma
    and lightness rules.

`--json`
:   Print the verdict as a JSON object instead of the table. The exit code does
    not change, so a build that already branches on it keeps working.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Every row passed. Advisory `[WARN]` rows still exit 0. |
| 1 | At least one row failed. |

```bash
python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
echo $?
```

### JSON output

`--json` prints one object: `schema`, `tool`, `ok`, the `inputs` that produced
the verdict, and a `rows` array of `name`, `status`, `detail`. `status` is
`pass`, `fail` or `warn`, spelled out rather than the Python API's `True`,
`False` and `"warn"`.

```bash
python check_palette.py "#E69F00,#56B4E9,#009E73" --json | jq '.rows[] | select(.status != "pass")'
```

The `inputs` are there because a palette verdict is a verdict about a palette on
a surface, gated as categorical or as a ramp. The same hexes pass on white and
fail on a tinted page, and a stored artifact that recorded only `ok` cannot be
read back a month later.

`check_figure.py` has no matching flag, because it audits no figure of yours from
a shell. The equivalent is `audit_json` in the API, which emits the same `schema`
so a CI step can collect both and read `ok` and `rows` out of either. See
[the API reference](api.md).

## check_figure.py

Run with no arguments, `check_figure.py` audits a deliberately broken figure and
reports on it:

```bash
python check_figure.py
```

It exits 0 when the checker correctly rejects that figure, so a build step can
use it to verify the checker itself still works. If the broken figure passes,
the command exits non-zero: that outcome means the checker is broken.

This command takes no figure of your own. To audit a figure, import `audit` or
`report`. See [the API reference](api.md).

### Options

`--venues`
:   Print every venue's content width and exit. This flag is read before the
    matplotlib import, so it works on a machine with no matplotlib installed.

## Venue widths

`python check_figure.py --venues` prints all twelve widths. Pass a name as
`venue=` to `audit`, `report`, or `page_scale`.

| Venue | Width (pt) | Width (in) | Source |
|---|---|---|---|
| acl | 455.24 | 6.32 | `\textwidth`, acl.sty (16cm) |
| acl-column | 219.08 | 3.04 | `\columnwidth` (7.7cm) |
| article-a4 | 418.25 | 5.81 | `\textwidth`, article 10pt a4paper |
| article-letter | 345.00 | 4.79 | `\textwidth`, article 10pt letterpaper |
| iclr | 397.48 | 5.52 | `\textwidth`, iclr*_conference.sty |
| icml | 487.82 | 6.78 | `\textwidth`, icml*.sty (two-column page) |
| icml-column | 234.88 | 3.26 | `\columnwidth` |
| ieee | 516.00 | 7.17 | `\textwidth`, IEEEtran |
| ieee-column | 252.00 | 3.50 | `\columnwidth`, IEEEtran |
| nature | 518.74 | 7.20 | double column, 183mm |
| nature-column | 252.28 | 3.50 | single column, 89mm |
| neurips | 397.48 | 5.52 | `\textwidth`, neurips_*.sty (5.5in) |

!!! warning "Verify before trusting"

    Put `\the\textwidth` in your own document and read the log. Style files get
    revised between years, a `geometry` call in your preamble silently
    overrides all of this, and a figure certified against the wrong width is
    certified at the wrong type size.
