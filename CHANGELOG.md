# Changelog

## Unreleased

Corrections, no new gates. Nothing that passed before fails now.

- **Surface is white everywhere.** `check_palette.py` defaulted to `#fcfcfb`, a
  surface `figure.mplstyle` never rendered, so every contrast ratio in the style
  guide was measured against a page that did not exist. Reddish purple was
  listed as needing a mandatory direct label at 2.98:1; against the surface
  actually used it clears 3:1 at 3.06. Table recomputed, `--surface` still
  available for a genuinely tinted page.
- **`tests/test_docs_match_code.py`** parses the guide's contrast table and
  checks every quoted number, and every † marker, against `contrast()`. The
  drift above is now a test failure rather than something noticed in a year.
- **`placed_frac` on `audit()`/`report()`.** A figure placed at
  `0.48\textwidth` was measured as if it were full width and certified at twice
  the type size it shipped at. Passing `placed_frac` without `CONTENT_WIDTH_PT`
  raises rather than silently assuming 1.0.
- **Mark ratio sees line markers.** It read only `ax.collections`, so
  `markersize=3` beside `markersize=30` passed clean. Bars stay excluded on
  purpose — a bar 30× another bar is the encoding working, and the docstring now
  says so instead of leaving it to look like an oversight.
- **`figure.mplstyle` carries the mark and output defaults**: `lines.linewidth`,
  `lines.markersize`, `axes.linewidth`, `patch.linewidth`,
  `legend.handlelength`, `errorbar.capsize`, `axes.axisbelow`, plus
  `figure.dpi`, `savefig.dpi`, `savefig.bbox`, `savefig.facecolor`. These were
  prose passed by hand at each call site; at matplotlib's default 100 dpi the
  "render a PNG and look at it" step produced a PNG too soft to show the
  defects it was opened to find.
- **`bbox_inches="tight"` documented as a trap** beside the `#`-is-a-comment
  one, and pinned in the sheet. It trims to drawn content, so the saved width
  stops being the authored width the type gate derives its floor from — the
  gate then certifies a size the shipped file does not have.
- `axes.titlesize`/`titleweight` annotated as panel-title settings, resolving a
  contradiction with the guide's ban on in-figure titles.

## 0.1.0 — 2026-07-22

First release.

- `check_palette.py` — lightness band, chroma floor, CVD separation (protanopia
  and deuteranopia, OKLab ΔE), normal-vision separation, contrast against the
  surface, and a four-gate mode for ordered ramps. Standard library only.
- `check_figure.py` — clipping, text collision, alpha stacking, mark ratio, axis
  redundancy, type size on the printed page, and ink coverage, read off a built
  matplotlib figure's own artists.
- `figure.mplstyle` — typeface, ink, type sizes, spines, grid, frameless
  legends.
- `skill/` — Agent Skill wrapper (`SKILL.md` plus the full style guide).
- 49 tests, including per-gate failure cases and a guard against the style
  sheet's colors silently not applying.
