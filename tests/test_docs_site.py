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
import subprocess

import pytest

from conftest import SKILL

import check_palette as cp

ROOT = SKILL.parent
DOCS = ROOT / "docs"
CONFIG = ROOT / "zensical.toml"


def _tracked_under_docs():
    """The paths under `docs/` that git tracks, or None outside a checkout.

    This file used to walk `docs/` off the filesystem, which made the working
    tree an input: `.gitignore` carries `docs/superpowers/`, so a maintainer
    with design notes on disk got five failures naming files that are not part
    of the project, while CI -- which clones -- stayed green. A gate whose
    verdict depends on what is lying around in an ignored directory is not
    reporting on the repository.

    None, not an empty set, when git is absent or this is not a checkout: the
    sdist ships `tests/`, so the suite has to keep running where there is no
    git to ask. Callers fall back to walking the filesystem there, which is the
    old behaviour and is right when every file present is a shipped one.
    """
    try:
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--", "docs"],
            capture_output=True, text=True,
        )
    except OSError:                                         # pragma: no cover
        return None
    if listed.returncode != 0:                              # pragma: no cover
        return None
    return {ROOT / name for name in listed.stdout.split("\0") if name}


TRACKED = _tracked_under_docs()


def docs_paths(pattern="*"):
    """`DOCS.rglob(pattern)`, restricted to tracked files where git can say."""
    found = DOCS.rglob(pattern)
    if TRACKED is None:                                     # pragma: no cover
        return found
    return (p for p in found if p in TRACKED)

# `  { "The gates" = "style-guide.md" },`
NAV_ENTRY = re.compile(r'^\s*\{\s*"[^"]+"\s*=\s*"([^"]+\.md)"\s*\},?\s*$')

# The pages written for the site. Everything else is a pointer.
#
# `api.md` is site-only for the opposite reason to the symlinks rather than in
# spite of it: it holds no reference material to keep one copy of. It is `:::`
# directives, and mkdocstrings reads the signatures and docstrings out of
# `skill/scripts/` at build time, so the single copy it serves is the code.
# `tests/test_api_reference.py` holds the directives to the modules.
#
# `gates.md` and `getting-started.md` are site-only in the same sense
# `gallery.md` is: they are the one copy of what they say. Both came out of the
# README, which was carrying the threshold tables, the install routes and the
# usage examples for a project that has a docs site. Nothing was duplicated in
# the move, which is what keeps this set honest rather than a growing exemption.
# `how-to.md` is site-only for the third reason: it is task recipes, and a
# recipe is a claim about what the code does when you type it. `test_how_to.py`
# runs the commands, recomputes the numbers and re-derives the row table from
# the registry, so the page cannot drift from the behaviour it teaches.
AUTHORED = {"gallery.md", "api.md", "design.md", "gates.md", "tutorial.md",
            "install.md", "cli.md", "compatibility.md",
            "how-to.md", "abbreviations.md"}


def nav_targets():
    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("nav = ["))
    out = []
    for line in lines[start + 1:]:
        match = NAV_ENTRY.match(line)
        if match:
            out.append(match.group(1))
        elif line.strip() == "]":
            break
    return out


def test_the_nav_is_still_parseable():
    """A parser that matches nothing agrees with nothing. Same guard as the
    gate-table parser in `test_docs_match_code.py`, and for the same reason."""
    assert len(nav_targets()) == 16, (
        f"matched {len(nav_targets())} nav entries in zensical.toml, expected "
        "13 - the nav changed shape and nav_targets() needs updating with it")


@pytest.mark.parametrize("target", nav_targets())
def test_every_nav_entry_exists(target):
    assert (DOCS / target).is_file(), (
        f"zensical.toml navigates to a missing {target}")


def symlinks():
    return sorted(p.name for p in docs_paths("*") if p.is_symlink())


def test_the_symlinks_were_found():
    """Both tests below are parametrized over this list, so an empty one does
    not fail them -- it deletes them. Twenty-seven pages and images point out of
    `docs/`; if that count drops, either something became a copy (which
    `test_no_page_has_become_a_copy` catches) or this collection stopped
    working (which nothing else would).

    The number is written three times on purpose -- the assertion, the message
    and the sentence above -- and all three said something different until now:
    the assertion had been moved to 17 and the prose still read twelve and 13.
    That is the defect this whole file exists to catch, one level in.
    """
    assert len(symlinks()) == 27, (
        f"found {len(symlinks())} symlinks under docs/, expected 27 - if the "
        "site legitimately gained or lost a page, update this number with it")


@pytest.mark.parametrize("link", symlinks())
def test_every_symlink_resolves(link):
    """`--strict` makes the build fail on a dangling page, but only when
    someone builds. A file moved under `skill/` should fail the test run."""
    path = next(p for p in docs_paths("*") if p.name == link)
    assert path.exists(), (
        f"docs/{path.relative_to(DOCS)} points at "
        f"{path.readlink()}, which does not exist")


@pytest.mark.parametrize("link", symlinks())
def test_symlinks_stay_inside_the_repository(link):
    """An absolute target works on the machine it was made on and nowhere
    else, and a target outside the checkout would publish a file that is not
    in the repository."""
    path = next(p for p in docs_paths("*") if p.name == link)
    assert not path.readlink().is_absolute(), f"{link} has an absolute target"
    assert ROOT in path.resolve().parents, (
        f"{link} resolves to {path.resolve()}, outside the repository")


def test_no_page_has_become_a_copy():
    """The one that matters. If someone replaces a symlink with a real file to
    fix a rendering nit, the site keeps building and the guide starts drifting
    from the code that computes its numbers."""
    copies = sorted(str(p.relative_to(DOCS)) for p in docs_paths("*.md")
                    if not p.is_symlink() and p.name not in AUTHORED)
    assert not copies, (
        f"{copies} are real files under docs/ - they should be symlinks to the "
        "single copy, or added to AUTHORED if they are genuinely site-only")


# --- a `#` in column one is a heading, whatever it was meant to be ------------
# Python-Markdown splits blocks before it parses inline spans, so a line that
# begins with `#` becomes an ATX heading even when it is plainly the middle of a
# sentence -- or, as here, the middle of a wrapped `code span`. Two pages shipped
# that way: `#E69F00`, and `#2ca02c` in the changelog, both the second line of a
# hex pair inside backticks. Each rendered as an <h1> holding the rest of the
# sentence, left an unclosed backtick in the paragraph above, added a permalink
# `¶` mid-sentence, and put a line of prose in the table of contents.
#
# `--strict` does not fail on it: nothing is broken, a heading was simply
# invented. It is the same defect as everything else this file guards -- prose
# that does not say what it renders -- so it is checked rather than watched for.


def source_pages():
    """The markdown the site serves, resolved through the symlinks."""
    return sorted((p, p.resolve()) for p in docs_paths("*.md"))


def accidental_headings(text):
    """Lines that Python-Markdown will make a heading out of by accident.

    A real ATX heading is `#` through `######` followed by a space. Anything
    else in column one -- `#E69F00`, `#2ca02c` -- is a hex color, or the tail
    of a wrapped code span, about to become an <h1>. Fenced blocks are skipped:
    inside them a leading `#` is a comment and stays one.
    """
    out, fenced = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#") and not re.match(r"#{1,6} ", line):
            out.append((number, line))
    return out


@pytest.mark.parametrize("page,target", source_pages(),
                         ids=lambda v: getattr(v, "name", v))
def test_no_line_becomes_a_heading_by_accident(page, target):
    bad = accidental_headings(target.read_text(encoding="utf-8"))
    report = "\n".join(f"  {target.name}:{n}: {line}" for n, line in bad)
    assert not bad, (
        f"{len(bad)} line(s) start with `#` but are not headings, so the "
        f"build will turn each into one:\n{report}\n"
        "Re-wrap the paragraph so the `#` is not in column one.")


# --- one list of build dependencies, in pyproject.toml ------------------------
# The build step used to read `uv run --no-project --with "zensical>=0.0.51,<0.1"`,
# which is the `docs` dependency group spelled out a second time in a file
# nothing resolves against `pyproject.toml`. It was correct for exactly as long
# as the two lists happened to agree, and they stopped agreeing the first time
# the build needed a package only one of them named: the group gained
# `mkdocstrings-python` for the API page, the workflow line did not, and CI
# failed with `No module named 'mkdocstrings'` after the same build passed
# locally in a project environment that had it. `--group docs` leaves one list.

WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
PYPROJECT = ROOT / "pyproject.toml"


def build_steps():
    """The lines of the docs workflow that build the site."""
    return [line.strip() for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
            if "zensical build" in line]


def test_the_build_step_was_found():
    """The two tests below say nothing about a workflow they cannot find."""
    assert len(build_steps()) == 1, (
        f"found {len(build_steps())} `zensical build` lines in "
        f"{WORKFLOW.name}, expected 1 - the workflow changed shape and "
        "build_steps() needs updating with it")


@pytest.mark.parametrize("step", build_steps())
def test_the_build_installs_the_declared_group(step):
    assert re.search(r"--(only-)?group docs\b", step), (
        f"the docs build runs `{step}`, which does not install the `docs` "
        "dependency group - whatever it installs instead is a second list of "
        "build dependencies that nothing keeps in step with pyproject.toml")
    assert "--with" not in step, (
        f"the docs build names a package inline: `{step}`. Add it to the "
        "`docs` group in pyproject.toml instead, so there is one list.")


def docs_group():
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"^docs = \[(.*?)^\]", text, re.S | re.M)
    assert match, "pyproject.toml no longer declares a `docs` group"
    return re.findall(r'"([A-Za-z0-9_.-]+)', match.group(1))


def test_the_docs_group_supplies_the_builder():
    """`--group docs` is only the whole list if the builder is in it."""
    assert "zensical" in docs_group(), (
        f"the `docs` group names {docs_group()}, which does not include "
        "zensical - the workflow installs this group and nothing else")


def test_a_page_using_directives_declares_the_handler_that_reads_them():
    """`:::` in a page is silently inert prose without mkdocstrings installed:
    the extension raises at import, the build exits 1, and the message names a
    module no page mentions. Tie the need to the declaration."""
    using = sorted(p.name for p in docs_paths("*.md")
                   if re.search(r"^::: ", p.resolve().read_text(encoding="utf-8"), re.M))
    if not using:
        pytest.skip("no page uses mkdocstrings directives")
    assert "mkdocstrings-python" in docs_group(), (
        f"{using} use `:::` directives, but the `docs` group names "
        f"{docs_group()} - the build would fail on a missing handler")


def test_the_build_is_not_left_configured_for_mkdocs():
    """Zensical reads a `mkdocs.yml` if it finds one, and prefers it to nothing
    -- but `strict: true` is a MkDocs key it silently ignores, so a leftover
    file is a build that stops failing on a dangling page without saying so."""
    assert not (ROOT / "mkdocs.yml").exists()
    assert not (ROOT / "mkdocs.yaml").exists()


def test_every_cdn_script_is_pinned_to_an_exact_version():
    """The gates page's sort and its flow diagram load from a CDN, and a CDN
    URL without a version is a floating dependency: tablesort or mermaid
    releases a breaking version and the page breaks, with nothing in the
    repository having changed. The config comment and this test are the
    project's answer -- every `extra_javascript` entry that names a host must
    carry an exact `@version`, and a floating tag (`@latest`, `@5`) or no tag
    at all is the failure the site screens against.

    Local `javascripts/` files are the vendor floor and are exempt by design:
    they cannot float, they are read at build time, and `--strict` fails the
    build if they vanish.
    """
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"extra_javascript = \[(.*?)\]", text, re.S)
    assert match, "zensical.toml no longer declares extra_javascript"
    urls = re.findall(r'"([^"]+)"', match.group(1))
    assert len(urls) >= 2, (
        f"expected the gates page's engine scripts in extra_javascript, "
        f"found {urls}")
    floating = [u for u in urls
                if "://" in u and not re.search(r"@\d+(?:\.\d+){0,2}(?=/|$)", u)]
    assert not floating, (
        f"CDN script(s) without an exact version pin: {floating}. A floating "
        "dependency is how this page breaks with no commit behind it -- pin "
        "the exact version (e.g. mermaid@11.4.1) or vendor the file.")
    local = [u for u in urls if "://" not in u]
    assert local, (
        "no local javascripts/ init remains in extra_javascript - the sort "
        "may have stopped being driven by document$.subscribe")


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
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


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
            for m in map(QUOTED.match, CSS.read_text(encoding="utf-8").splitlines()) if m]


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
    assert surface in CSS.read_text(encoding="utf-8"), (
        f"palette.css does not name {surface}, the {variant} slate background")


def test_the_configured_variant_is_one_the_stylesheet_measured():
    """Flipping `variant` in zensical.toml changes the dark background under
    every link on the site. A variant with no row in the table is a site whose
    contrast nobody has checked."""
    match = re.search(r'^variant\s*=\s*"(\w+)"', CONFIG.read_text(encoding="utf-8"), re.M)
    assert match, "zensical.toml no longer states a theme variant"
    assert match.group(1) in SLATES, (
        f"zensical.toml selects the {match.group(1)!r} variant, which "
        f"palette.css has no measurement for (has {sorted(SLATES)})")


def scheme_link_colors():
    """Declarations only -- the comments are stripped first, and that is
    load-bearing.

    `quoted_rows()` above reads the comment on purpose; this reads the CSS on
    purpose, and the two cannot share a source. The scheme regex walks forward
    from the first `[data-md-color-scheme="slate"]` it finds to the next
    `--md-typeset-a-color`, so a comment that *names* a selector -- as the one
    in `palette.css` now does, explaining the `:root` prefix that took the
    stylesheet off the page -- silently redirects the match into the wrong
    block and reports both schemes sharing a color.
    """
    text = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
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


# Seven were configured that no page used, and `pymdownx.emoji` was not inert:
# it read the `:::` of a prose mkdocstrings mention as a shortcode and ate the
# line. None = nothing to grep, so the entry says which test holds it instead.
EXTENSION_SYNTAX = {
    "admonition": r"^\s*(!!!|\?\?\?\+?) \w", "attr_list": r"\{ *[.#][A-Za-z]",
    "md_in_html": r"markdown=[\"']?(span|block|1)", "tables": r"^\s*\|.*\|",
    "footnotes": r"\[\^[^]]+\]", "abbr": r"^\*\[[^]]+\]:", "def_list": r"^:   \S",
    "pymdownx.details": r"^\s*\?\?\?\+? \w", "pymdownx.inlinehilite": r"`#![a-z]",
    "pymdownx.tabbed": r'^\s*=== "', "pymdownx.mark": r"==[^=\s][^=]*==",
    "pymdownx.caret": r"\^\^[^^]+\^\^|\^[A-Za-z0-9]+\^",
    "pymdownx.keys": r"\+\+[a-z0-9]+(\+[a-z0-9]+)*\+\+",
    "pymdownx.tilde": r"~~[^~]+~~|~[A-Za-z0-9]+~", "pymdownx.superfences": r"^\s*```",
    "pymdownx.emoji": r":[a-z][a-z0-9_-]+:", "pymdownx.highlight": r"^\s*``` ?\w",
    "toc": None, "pymdownx.snippets": None, "zensical.extensions.mkdocstrings": None,
}
EXTENSION_TABLE = re.compile(r"^\[project\.markdown_extensions\.(.+?)\]\s*$")


def test_every_configured_extension_is_used_by_a_page():
    """Count first: a parser matching nothing would pass by checking nothing."""
    found = (EXTENSION_TABLE.match(l) for l
             in CONFIG.read_text(encoding="utf-8").splitlines())
    extensions = sorted({m.group(1).replace('"', "").split(".handlers")[0]
                         for m in found if m})
    assert len(extensions) >= 10, (f"matched {len(extensions)} extension tables"
                                   " - the config changed shape, and"
                                   " EXTENSION_TABLE with it")
    unmapped = [e for e in extensions if e not in EXTENSION_SYNTAX]
    assert not unmapped, (f"zensical.toml configures {unmapped}: add its syntax "
                          "to EXTENSION_SYNTAX, or map it to None and say why")
    pages = [p.resolve().read_text(encoding="utf-8") for p in docs_paths("*.md")]
    unused = [e for e in extensions if EXTENSION_SYNTAX[e]
              and not any(re.search(EXTENSION_SYNTAX[e], t, re.M) for t in pages)]
    assert not unused, (f"zensical.toml configures {unused} and no page the "
                        "site serves uses their syntax. Drop them.")


# Each of these emits markup. The two view-time features are in
# test_docs_render.py, and `navigation.indexes` is not set: it measured as a
# no-op, because no section in the nav points at a file.
NAVIGATION_MARKUP = {
    "navigation.tabs": "md-tabs",
    "navigation.sections": "md-nav__item--section",
    "navigation.path": "md-path",
    "navigation.footer": "md-footer__link",
}


@pytest.mark.parametrize("feature,marker", sorted(NAVIGATION_MARKUP.items()))
def test_a_configured_navigation_feature_reaches_the_built_page(feature, marker):
    """The silent-typo guard, as an assertion."""
    built = ROOT / "site" / "gates" / "index.html"
    if not built.is_file():
        pytest.skip("no built site - run `zensical build` first")
    assert f'"{feature}"' in CONFIG.read_text(encoding="utf-8"), (
        f"{feature} left the features list; drop this row with it")
    assert marker in built.read_text(encoding="utf-8"), (
        f"{feature} is configured and `{marker}` is absent from the built "
        "page, so the name is doing nothing - check it against the theme's")
