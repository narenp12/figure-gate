"""The docs site serves the files, not copies of them.

`docs/` is symlinks. That is the whole design: `test_docs_match_code.py` reads
`skill/references/style-guide.md` and asserts its numbers against `contrast()`,
and it can only keep doing that if the page the site serves *is* that file. A
`docs/` of hand-maintained duplicates would pass every test in this suite while
publishing a guide whose numbers had drifted -- the exact failure this project
already has a test file about, one level further out.

So: assert the pointers point somewhere, assert nothing has quietly become a
copy, and assert the contrast numbers written into the stylesheet comment are
numbers `contrast()` actually returns, on the surfaces the theme actually draws.
"""

import colorsys
import re

import pytest

from conftest import SKILL

import check_palette as cp

ROOT = SKILL.parent
DOCS = ROOT / "docs"
CONFIG = ROOT / "zensical.toml"

# `  { "The gates" = "style-guide.md" },`
NAV_ENTRY = re.compile(r'^\s*\{\s*"[^"]+"\s*=\s*"([^"]+\.md)"\s*\},?\s*$')

# gallery.md is the one page written for the site. Everything else is a pointer.
AUTHORED = {"gallery.md"}


def nav_targets():
    lines = CONFIG.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("nav = ["))
    out = []
    for line in lines[start + 1:]:
        match = NAV_ENTRY.match(line)
        if match:
            out.append(match.group(1))
        elif line.strip().startswith("]"):
            break
    return out


def test_the_nav_is_still_parseable():
    """A parser that matches nothing agrees with nothing. Same guard as the
    README gate-table parser, and for the same reason."""
    assert len(nav_targets()) == 6, (
        f"matched {len(nav_targets())} nav entries in zensical.toml, expected "
        "6 - the nav changed shape and nav_targets() needs updating with it")


@pytest.mark.parametrize("target", nav_targets())
def test_every_nav_entry_exists(target):
    assert (DOCS / target).is_file(), (
        f"zensical.toml navigates to a missing {target}")


@pytest.mark.parametrize(
    "link", sorted(p.name for p in DOCS.rglob("*") if p.is_symlink()))
def test_every_symlink_resolves(link):
    """`--strict` makes the build fail on a dangling page, but only when
    someone builds. A file moved under `skill/` should fail the test run."""
    path = next(p for p in DOCS.rglob("*") if p.name == link)
    assert path.exists(), (
        f"docs/{path.relative_to(DOCS)} points at "
        f"{path.readlink()}, which does not exist")


@pytest.mark.parametrize(
    "link", sorted(p.name for p in DOCS.rglob("*") if p.is_symlink()))
def test_symlinks_stay_inside_the_repository(link):
    """An absolute target works on the machine it was made on and nowhere
    else, and a target outside the checkout would publish a file that is not
    in the repository."""
    path = next(p for p in DOCS.rglob("*") if p.name == link)
    assert not path.readlink().is_absolute(), f"{link} has an absolute target"
    assert ROOT in path.resolve().parents, (
        f"{link} resolves to {path.resolve()}, outside the repository")


def test_no_page_has_become_a_copy():
    """The one that matters. If someone replaces a symlink with a real file to
    fix a rendering nit, the site keeps building and the guide starts drifting
    from the code that computes its numbers."""
    copies = sorted(p.name for p in DOCS.glob("*.md")
                    if not p.is_symlink() and p.name not in AUTHORED)
    assert not copies, (
        f"{copies} are real files under docs/ - they should be symlinks to the "
        "single copy, or added to AUTHORED if they are genuinely site-only")


def test_the_build_is_not_left_configured_for_mkdocs():
    """Zensical reads a `mkdocs.yml` if it finds one, and prefers it to nothing
    -- but `strict: true` is a MkDocs key it silently ignores, so a leftover
    file is a build that stops failing on a dangling page without saying so."""
    assert not (ROOT / "mkdocs.yml").exists()
    assert not (ROOT / "mkdocs.yaml").exists()


# --- the stylesheet quotes measurements too -----------------------------------
# Same rule as the style guide: a number in a comment is not executable, so it
# is checked. Both link colors are chosen against a contrast floor, and the
# whole point of the dark-mode override is that one of them misses it.

CSS = DOCS / "stylesheets" / "palette.css"
BODY_TEXT_MIN = 4.5        # WCAG AA for text, not the 3:1 series floor


def slate(lightness):
    """A Zensical dark background, derived rather than pasted.

    Both variants are `hsla(var(--md-hue), 15%, L, 1)` with `--md-hue: 225`,
    which is a blue-tinted near-black rather than a neutral one. Writing the
    hex in by hand would have been a number nobody could check against its
    source, and the first guess at it was #1c1b1a -- close enough to look
    right and wrong by 0.2:1.
    """
    r, g, b = colorsys.hls_to_rgb(225 / 360, lightness, 0.15)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


# The two theme variants differ in their dark background, so they differ in
# every dark-mode contrast measurement. `zensical.toml` picks one, and picking
# is a one-line edit, so both are held to the floor rather than whichever is
# selected today.
SLATES = {"classic": slate(0.14), "modern": slate(0.05)}

#      #0072B2 (blue)       5.19:1       3.10:1          3.77:1
QUOTED = re.compile(
    r"^\s+(#[0-9a-fA-F]{6})\s+\(\w+\)\s+"
    r"([\d.]+):1\s+([\d.]+):1\s+([\d.]+):1")


def quoted_rows():
    return [(m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in map(QUOTED.match, CSS.read_text().splitlines()) if m]


def test_the_stylesheet_table_is_still_parseable():
    assert len(quoted_rows()) == 2, (
        f"matched {len(quoted_rows())} rows in palette.css, expected 2")


@pytest.mark.parametrize("hex_color,on_white,on_classic,on_modern",
                         quoted_rows())
def test_quoted_css_contrast_matches_computed(hex_color, on_white, on_classic,
                                              on_modern):
    assert cp.contrast(hex_color, "#ffffff") == pytest.approx(on_white, abs=0.01)
    assert cp.contrast(hex_color, SLATES["classic"]) == pytest.approx(
        on_classic, abs=0.01)
    assert cp.contrast(hex_color, SLATES["modern"]) == pytest.approx(
        on_modern, abs=0.01)


@pytest.mark.parametrize("variant,surface", sorted(SLATES.items()))
def test_the_stylesheet_names_the_surface_it_measured_against(variant, surface):
    """The surface is half of every contrast number. If the comment names one
    hex and the tests compute against another, both can be internally
    consistent and the site can still ship links under the floor."""
    assert surface in CSS.read_text(), (
        f"palette.css does not name {surface}, the {variant} slate background")


def test_the_configured_variant_is_one_the_stylesheet_measured():
    """Flipping `variant` in zensical.toml changes the dark background under
    every link on the site. A variant with no row in the table is a site whose
    contrast nobody has checked."""
    match = re.search(r'^variant\s*=\s*"(\w+)"', CONFIG.read_text(), re.M)
    assert match, "zensical.toml no longer states a theme variant"
    assert match.group(1) in SLATES, (
        f"zensical.toml selects the {match.group(1)!r} variant, which "
        f"palette.css has no measurement for (has {sorted(SLATES)})")


def scheme_link_colors():
    text = CSS.read_text()
    values = dict(re.findall(r"--(fg-\w+):\s*(#[0-9a-fA-F]{6})", text))
    out = {}
    for scheme in ("default", "slate"):
        match = re.search(rf'\[data-md-color-scheme="{scheme}"\].*?'
                          r"--md-typeset-a-color:\s*var\(--(fg-\w+)\)",
                          text, re.S)
        assert match, f"no link color found for the {scheme} scheme"
        out[scheme] = values[match.group(1)]
    return out


def test_light_mode_links_clear_the_text_floor():
    light = scheme_link_colors()["default"]
    assert cp.contrast(light, "#ffffff") >= BODY_TEXT_MIN, (
        f"light-mode links are {light} at "
        f"{cp.contrast(light, '#ffffff'):.2f}:1 on white")


@pytest.mark.parametrize("variant,surface", sorted(SLATES.items()))
def test_dark_mode_links_clear_the_text_floor_on_every_variant(variant, surface):
    dark = scheme_link_colors()["slate"]
    assert cp.contrast(dark, surface) >= BODY_TEXT_MIN, (
        f"dark-mode links are {dark} at {cp.contrast(dark, surface):.2f}:1 on "
        f"the {variant} background {surface}")


def test_the_two_schemes_do_not_share_one_color():
    """The reason there are two. Blue is 5.19:1 on white and 3.10:1 on the
    lighter of the two dark backgrounds -- fine as a series hue, under the
    floor as body text."""
    colors = scheme_link_colors()
    assert colors["default"] != colors["slate"], (
        "both schemes use one color - if that is now correct, this test and "
        "the comment in palette.css are both stale")
    assert cp.contrast(colors["default"], SLATES["classic"]) < BODY_TEXT_MIN, (
        "the light-mode color now clears the floor on dark too, so the "
        "override it exists to justify is no longer needed")
