"""The site is measured where it is painted, not where it is written.

`test_docs_site.py` reads the hex values out of `palette.css` and checks the
contrast numbers quoted in its comment. Every one of those assertions passed
through a release in which the stylesheet reached nothing: the scheme rules had
been prefixed with `:root`, Zensical puts `data-md-color-scheme` on `<body>`,
and a selector that matches zero elements has no contrast to be wrong about.
Links shipped at 2.85:1 and the light-mode header at 1.00:1 -- its text was the
background color exactly -- with 44 tests green.

Arithmetic on two hex values cannot catch that, because the defect is not in the
arithmetic. So this file renders the built site in a real browser, lets the
browser resolve the cascade and composite the translucent surfaces, and hands
the resulting foreground and background back to `check_palette.contrast()` --
the same function that gates the figures. The browser is used for what only a
browser knows; the floor is enforced by the project's own code.

Skipped, not failed, when the browser or the site builder is missing: the
documented test command is `uv run rtk pytest tests/ -n auto -q`, and it should
not start requiring a 150MB Chromium to run the figure gates. CI installs both
and runs this file in the docs workflow, where a docs regression belongs.
"""

import http.server
import os
import posixpath
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

import pytest

from conftest import SKILL

import check_palette as cp

from test_docs_match_code import swatch_pairs
from test_docs_site import CONFIG, CSS, SLATES, nav_targets, scheme_link_colors

ROOT = SKILL.parent
SITE = ROOT / "site"

# Set by the nested run at the bottom of this file, and read by the test that
# starts it, so that run does not start one of its own.
NESTED = "FIGURE_GATE_DOCS_GROUP_BLOCKED"


def playwright_api():
    """Imported in a fixture, deliberately, not with a module-level
    `importorskip`.

    A module-level skip fires during *collection*, so this file would contribute
    its tests to the suite on a machine with Chromium installed and nothing on
    one without. `test_docs_match_code.py` holds the documented test count
    to what pytest collects, and that number would then depend on which machine
    asked. Collect always, skip at run time.
    """
    try:
        import playwright.sync_api as api
    except ImportError:
        pytest.skip("playwright is in the docs-test group; the figure gates "
                    "do not need it. `uv sync --group docs-test`")
    else:
        # `else` rather than a bare `return`, here and in the two below.
        # `pytest.skip` raises, so the two spellings run identically; CodeQL
        # does not model that and reported the name as possibly unbound.
        return api


def file_lock():
    """`playwright_api()`'s twin, for the other docs-test dependency.

    Its own function, and called unconditionally, because the first version of
    this import was neither. `built_site` did a bare `from filelock import
    FileLock` on the path xdist workers take, so the file that promises to skip
    when the docs group is absent instead raised ModuleNotFoundError at fixture
    setup and turned every `pytest -n auto` job red -- on a test that had only
    just started depending on the fixture.

    Unconditional even where the lock is not used -- the single-worker path
    needs no lock at all -- because a dependency that only bites under `-n auto`
    gives `pytest` and the documented `pytest -n auto` different skip sets, and
    a gate whose behaviour depends on how it was invoked is not a gate.
    """
    try:
        from filelock import FileLock
    except ImportError:
        pytest.skip("filelock is in the docs-test group; the figure gates "
                    "do not need it. `uv sync --group docs-test`")
    else:
        return FileLock

# WCAG 2.2 AA for text. Deliberately not the 3:1 series floor the figures are
# held to -- a link is text being read, not a mark being told apart from its
# neighbour. `palette.css` makes the same distinction in prose; this is it in
# executable form.
BODY_TEXT_MIN = 4.5
LARGE_TEXT_MIN = 3.0

SCHEMES = {"light": "default", "dark": "slate"}


def expected_link_color(mode):
    """What the stylesheet says this scheme's links should be.

    Parsed out of `palette.css` by `test_docs_site.scheme_link_colors()`, not
    pasted here. A hard-coded pair would be a second place to state the palette,
    and the two would agree right up until someone changed one of them -- which
    is the drift this repository keeps writing tests about. Whether the value is
    the *right* one is that file's question; this file only asks whether it
    reached the page.
    """
    return scheme_link_colors()[SCHEMES[mode]].lower()


# --- rendering ----------------------------------------------------------------

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_the_site():
    """One `zensical build`, failing loudly.

    Not `pytest.skip` on a bad exit: the first version of this fixture skipped,
    and under `-n auto` that turned a build the workers were racing each other
    to run into nine quietly absent tests and a green suite. A gate that removes
    itself when something goes wrong is the failure this file exists to catch,
    one level further out again.
    """
    if shutil.which("uv") is None:
        pytest.skip("uv is needed to build the site")
    result = subprocess.run(
        ["uv", "run", "--only-group", "docs",
         "zensical", "build", "--strict"],
        cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, (
        "the site did not build, so there is nothing to measure:\n"
        f"{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="session")
def built_site(tmp_path_factory, worker_id):
    """Build from source once per run, across every xdist worker.

    Rebuilt rather than reused because a stale `site/` would let this file pass
    against the previous commit's stylesheet -- the same class of mistake it
    exists to catch.

    Built once because session scope is per *worker*, not per run. `zensical`
    has no `--site-dir` (it is config-only), so all eight workers cleaned and
    rewrote the same `site/` underneath each other:

        site directory could not be cleaned: Os { code: 2, kind: NotFound }

    This is pytest-xdist's documented answer -- a lock on
    `tmp_path_factory.getbasetemp().parent`, which is the one directory every
    worker shares -- with a marker file so the workers that lose the race wait
    for the build rather than repeat it.
    """
    # Before the `master` branch below, not inside the worker path that needs
    # it: this is the fixture's declaration of what it costs to use, and every
    # test that asks for a built site now inherits the skip from one place.
    # Asking after the branch is what shipped -- see `file_lock()`.
    FileLock = file_lock()

    if worker_id == "master":
        _build_the_site()
        return SITE

    shared = tmp_path_factory.getbasetemp().parent
    with FileLock(str(shared / "zensical-build.lock")):
        marker = shared / "zensical-build.done"
        if not marker.is_file():
            _build_the_site()
            marker.write_text("built", encoding="utf-8")
    return SITE


@pytest.fixture(scope="session")
def server(built_site):
    """Serve `site/` at the root.

    `zensical serve` mounts under `site_url`'s path; a plain static server does
    not, and the paths this file navigates to are simpler for it.
    """
    port = _free_port()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(built_site), **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture(scope="session")
def browser():
    with playwright_api().sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:                      # noqa: BLE001
            pytest.skip(f"no chromium: {exc} -- run `uv run playwright install chromium`")
        else:
            yield b
            b.close()


@pytest.fixture()
def page(browser, server):
    """A blank page for the interaction tests.

    `rendered` above measures every page and closes the contexts; behaviour --
    a click on a tab, a toggle on a `<details>` -- needs a page its test can
    drive, which is what this is. Function scope: an interaction test that
    navigated a session page would leave every test after it standing on
    whatever page the last one finished on.
    """
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = context.new_page()
    yield pg
    context.close()


# The browser's half of the job: resolve the cascade, composite every
# translucent layer down to an opaque pair, and report it. No thresholds here --
# it reports what is painted and Python decides whether that passes.
#
# `--md-typeset-a-color` is read off `<body>`, not `<html>`, because that is
# where the scheme attribute lives and therefore where the custom properties
# this site sets actually resolve. Reading it at the root is what made the
# original defect invisible to inspection.
PROBE = r"""
() => {
  const parse = c => { const m = (c || '').match(/[\d.]+/g);
    return m ? {r:+m[0], g:+m[1], b:+m[2], a: m[3] !== undefined ? +m[3] : 1} : null; };
  const over = (f, b) => ({r: f.r*f.a + b.r*(1-f.a), g: f.g*f.a + b.g*(1-f.a),
                           b: f.b*f.a + b.b*(1-f.a), a: 1});
  const hex = c => '#' + [c.r, c.g, c.b]
    .map(v => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('');

  // Every painted layer between the element and the page, composited bottom-up.
  // A single getComputedStyle().backgroundColor is usually transparent and says
  // nothing about what the text is actually sitting on.
  const surface = el => {
    const stack = [];
    for (let n = el; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) stack.push(c);
    }
    stack.reverse();
    let cur = parse(getComputedStyle(document.body).backgroundColor) || {r:255,g:255,b:255,a:1};
    if (cur.a < 1) cur = over(cur, {r:255,g:255,b:255,a:1});
    stack.forEach(c => { cur = over(c, cur); });
    return cur;
  };

  const items = [];
  document.querySelectorAll('body *').forEach(el => {
    // Only elements holding their own text. Without this every ancestor is
    // reported too, at whatever color it happens to inherit.
    const own = [...el.childNodes]
      .some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!own) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
    const box = el.getBoundingClientRect();
    if (!box.width || !box.height) return;
    const fg = parse(cs.color);
    if (!fg) return;
    const bg = surface(el);
    const size = parseFloat(cs.fontSize) || 0;
    const weight = +cs.fontWeight || 400;
    // Which part of the chrome this string lives in, by ancestry rather than by
    // its own class. The header's title renders inside `.md-ellipsis`, whose
    // class name says nothing about the header -- a region test matching on the
    // element's own selector silently checks nothing.
    const region =
      el.closest('.md-header') ? 'header' :
      el.closest('.md-nav, .md-sidebar') ? 'nav' :
      el.closest('.md-typeset') ? 'content' :
      el.closest('.md-footer') ? 'footer' : 'other';

    items.push({
      selector: el.tagName.toLowerCase() +
        (typeof el.className === 'string' && el.className
          ? '.' + el.className.trim().split(/\s+/).join('.') : ''),
      region,
      text: el.textContent.trim().slice(0, 60),
      fg: hex(over(fg, bg)),
      bg: hex(bg),
      size, weight,
      large: size >= 24 || (size >= 18.66 && weight >= 700),
    });
  });

  // Palette swatches. The square is `::before` on the code span holding the
  // hex, so the element in `items` above is the hex text and the square is the
  // thing measured here: that it is painted the color its own element spells
  // out, and that it has area and a frame, which for a white or near-white
  // swatch is the whole of its visibility.
  //
  // `getComputedStyle(el, '::before')` reports used values for a rendered
  // pseudo-element, so `width` is the laid-out px rather than the declared em.
  // There is no `getBoundingClientRect` for a pseudo-element to disagree with.
  //
  // `surface(el)` would composite the square against itself and report it
  // correct whatever the stylesheet did, so the background behind it is the
  // code span's own, taken from `el` upward.
  const swatches = [...document.querySelectorAll('code.sw')].map(el => {
    const before = getComputedStyle(el, '::before');
    return {
      declared: getComputedStyle(el).getPropertyValue('--c').trim(),
      painted: hex(over(parse(before.backgroundColor) || {r:0,g:0,b:0,a:0},
                        surface(el))),
      labels: el.textContent.trim(),
      width: parseFloat(before.width) || 0,
      height: parseFloat(before.height) || 0,
      border: parseFloat(before.borderTopWidth) || 0,
    };
  });

  const cs = getComputedStyle(document.body);
  return {
    scheme: document.body.getAttribute('data-md-color-scheme'),
    link_color: cs.getPropertyValue('--md-typeset-a-color').trim(),
    primary: cs.getPropertyValue('--md-primary-fg-color').trim(),
    accent: cs.getPropertyValue('--md-accent-fg-color').trim(),
    page_bg: hex(parse(cs.backgroundColor)),
    items,
    swatches,
  };
}
"""


def page_paths():
    """`index.md` is served at the root; everything else gets a directory."""
    return ["/" if t == "index.md" else f"/{t[:-3]}/" for t in nav_targets()]


@pytest.fixture(scope="session")
def rendered(browser, server):
    """Every page, in both schemes, measured once.

    `color_scheme` emulation with a fresh context and no stored preference is
    the first-visit path: the theme picks the scheme from the media query, which
    is the state most readers actually get and the one the broken selectors were
    hiding in.
    """
    out = {}
    for mode in SCHEMES:
        context = browser.new_context(color_scheme=mode,
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        for path in page_paths():
            page.goto(server + path, wait_until="networkidle")
            out[(mode, path)] = page.evaluate(PROBE)
        context.close()
    return out


# --- the selectors reach the page ---------------------------------------------
# The direct guard on the original defect. If `palette.css` stops applying,
# these fail before any contrast question is asked, and the failure names the
# cause instead of leaving someone to infer it from a ratio.

@pytest.mark.parametrize("mode,scheme", sorted(SCHEMES.items()))
def test_the_theme_selected_the_scheme_we_think_it_did(rendered, mode, scheme):
    for (m, path), data in rendered.items():
        if m != mode:
            continue
        assert data["scheme"] == scheme, (
            f"{path} in {mode} mode rendered as {data['scheme']!r}, expected "
            f"{scheme!r} - the media query no longer drives the scheme, so "
            "every measurement below is of the wrong surface")


@pytest.mark.parametrize("mode", sorted(SCHEMES))
def test_palette_css_actually_applies(rendered, mode):
    """The direct one. A link color that is not the stylesheet's means the
    stylesheet is not reaching the page, whatever its own numbers say."""
    want = expected_link_color(mode)
    for (m, path), data in rendered.items():
        if m != mode:
            continue
        got = data["link_color"].lower()
        assert got == want, (
            f"{path} in {mode} mode resolves --md-typeset-a-color to {got!r}, "
            f"expected {want!r} from palette.css. A selector there is matching "
            "nothing - check it is not prefixed with `:root`, which is <html>, "
            "while Zensical sets data-md-color-scheme on <body>.")


def test_the_stylesheet_does_not_reintroduce_the_root_prefix():
    """Cheap, and it fails with the reason attached. The rendered checks above
    catch this too, but only where a browser is installed.

    Comments are stripped first, and that is not incidental: the comment in
    `palette.css` explains the defect by naming the selector that caused it, so
    a scanner reading raw text fails on the documentation of the bug rather than
    the bug. Read declarations, not prose.
    """
    source = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    offenders = [line.strip() for line in source.splitlines()
                 if ":root[data-md-color-scheme" in line]
    assert not offenders, (
        f"{offenders} - `:root` is <html>, which never carries "
        "data-md-color-scheme; Zensical sets it on <body>. Use the bare "
        "attribute selector. Both upstreams document `:root > *` for this, "
        "which selects the body, not the root.")


# --- contrast, measured where it is painted -----------------------------------

def failures(data):
    """Everything under its floor, worst first.

    The contrast arithmetic is `check_palette.contrast()`, not a second
    implementation living in the browser -- if the project's own definition of
    contrast ever changes, the site is held to the new one automatically.
    """
    out = []
    for item in data["items"]:
        floor = LARGE_TEXT_MIN if item["large"] else BODY_TEXT_MIN
        ratio = cp.contrast(item["fg"], item["bg"])
        if ratio < floor:
            out.append((ratio, floor, item))
    return sorted(out, key=lambda row: row[0])


@pytest.mark.parametrize("mode", sorted(SCHEMES))
@pytest.mark.parametrize("path", page_paths())
def test_every_visible_string_clears_the_text_floor(rendered, mode, path):
    bad = failures(rendered[(mode, path)])
    report = "\n".join(
        f"  {ratio:5.2f}:1 (needs {floor}) {item['fg']} on {item['bg']}  "
        f"{item['size']:.0f}px/{item['weight']}  {item['selector'][:70]}\n"
        f"            {item['text']!r}"
        for ratio, floor, item in bad)
    assert not bad, (
        f"{len(bad)} string(s) under the WCAG AA text floor on {path} in "
        f"{mode} mode:\n{report}")


@pytest.mark.parametrize("mode", sorted(SCHEMES))
def test_the_header_is_not_invisible(rendered, mode):
    """Named separately from the sweep above, which already covers it.

    The sweep reports a ratio; this reports that the site's own name is
    unreadable, which is the thing someone needs to be told. The header is the
    one surface here that is translucent, so it is also the one where a color
    can look right in the stylesheet and composite to nothing on the page.
    """
    for (m, path), data in rendered.items():
        if m != mode:
            continue
        header = [i for i in data["items"] if i["region"] == "header"]
        assert header, (
            f"no header text found on {path} in {mode} mode - the probe's "
            "region tagging has drifted and this test is checking nothing")
        for item in header:
            ratio = cp.contrast(item["fg"], item["bg"])
            floor = LARGE_TEXT_MIN if item["large"] else BODY_TEXT_MIN
            assert ratio >= floor, (
                f"header text on {path} in {mode} mode is {item['fg']} on "
                f"{item['bg']} at {ratio:.2f}:1, under {floor}. The header is "
                "translucent in the `modern` variant - anything colored here "
                "has to be measured against the composited surface, not "
                "against --md-primary-fg-color.")


@pytest.mark.parametrize("mode,scheme", sorted(SCHEMES.items()))
def test_the_page_background_is_the_surface_the_stylesheet_measured(
        rendered, mode, scheme):
    """Half of every contrast number in `palette.css` is the background it was
    computed against. If the theme's slate stops being the value the comment
    names, the quoted figures are describing a surface nobody is looking at."""
    # Either slate is allowed because `zensical.toml` picks the variant and
    # `palette.css` quotes both -- the same reason `test_docs_site.py` asserts
    # its floors against the worse of the two rather than the selected one.
    allowed = ({"#ffffff"} if scheme == "default"
               else {v.lower() for v in SLATES.values()})
    for (m, path), data in rendered.items():
        if m != mode:
            continue
        got = data["page_bg"].lower()
        assert got in allowed, (
            f"{path} in {mode} mode paints {got}, which is not a surface "
            f"palette.css measured against ({sorted(allowed)}). The contrast "
            "numbers in that comment are now about a surface the site does "
            "not draw.")


# --- the swatches are painted the hex they label ------------------------------
# `test_docs_match_code.py` checks that a swatch's inline `--c` matches the hex
# its code span spells out. That is arithmetic on two strings in one file, and it
# is the half this project has already been caught believing: the same file's
# link colors were correct in the stylesheet and reaching nothing on the page for
# a whole release.
#
# A swatch fails more quietly than a link did. A link that loses its color is
# still a link; a square that loses its fill is a square of page color sitting
# beside a hex, which on the light page is what `#ffffff` is supposed to look
# like. So the fill is measured, in both schemes, against the hex the reader can
# see next to it -- not against the inline style, which is the copy under test.

GUIDE_PATH = "/style-guide/"


def guide_swatches(rendered, mode):
    return rendered[(mode, GUIDE_PATH)]["swatches"]


def test_the_style_guide_is_among_the_pages_measured():
    """The swatch tests all index one page. If the nav renames it they would
    raise KeyError, which reports a missing dictionary key rather than the fact
    that the palette tables are no longer being looked at."""
    assert GUIDE_PATH in page_paths(), (
        f"{GUIDE_PATH} is not in {page_paths()} - the page carrying the palette "
        "tables moved, and the swatch tests below are pointed at nothing")


@pytest.mark.parametrize("mode", sorted(SCHEMES))
def test_every_swatch_in_the_guide_reached_the_page(rendered, mode):
    """Count first, colors second. The swatches are an `attr_list` attribute
    list; drop that extension from `zensical.toml` and every one of them becomes
    literal `{ .sw style="..." }` text at once, with no `code.sw` left for a
    per-swatch assertion to iterate over. An empty loop is green."""
    got = len(guide_swatches(rendered, mode))
    want = len(swatch_pairs())
    assert got == want, (
        f"the guide's source declares {want} swatch(es); {got} rendered on "
        f"{GUIDE_PATH} in {mode} mode. They are written as `attr_list` "
        "attribute lists - check that extension is still enabled.")


@pytest.mark.parametrize("mode", sorted(SCHEMES))
def test_every_swatch_paints_the_hex_it_labels(rendered, mode):
    bad = [f"  labelled {sw['labels']}, painted {sw['painted']}"
           + ("  (its --c did not resolve, so `background: var(--c)` is invalid "
              "and the square is showing the page)" if not sw["declared"] else "")
           for sw in guide_swatches(rendered, mode)
           if sw["painted"].lower() != sw["labels"].lower()]
    assert not bad, (
        f"{len(bad)} swatch(es) on {GUIDE_PATH} in {mode} mode are not the "
        f"color they label:\n" + "\n".join(bad))


@pytest.mark.parametrize("mode", sorted(SCHEMES))
def test_every_swatch_has_area_and_a_frame(rendered, mode):
    """Both halves of "a reader can see it".

    A `::before` with `content: ""` and no box is 0x0 and paints the right color
    over no pixels, which the fill test above cannot tell from a correct swatch.
    And the frame is not trim: `#ffffff` is in the surface row of the ink table,
    so on the light page the frame is the entire difference between a swatch and
    nothing at all.

    The floor is a real size rather than "not zero", because the borders alone
    give a collapsed swatch a few pixels of box: with the fill rule removed and
    only the dark-mode frame left, every swatch measured 4px wide and passed a
    `> 0` test while showing the reader nothing. The declared 0.85em is 11px at
    the smallest type on the page, so 8 is under every correct swatch and over
    every collapsed one.
    """
    bad = [f"  {sw['labels']}: {sw['width']:.1f}x{sw['height']:.1f}px, "
           f"{sw['border']:.1f}px border"
           for sw in guide_swatches(rendered, mode)
           if sw["width"] < 8 or sw["height"] < 8 or sw["border"] < 1]
    assert not bad, (
        f"{len(bad)} swatch(es) on {GUIDE_PATH} in {mode} mode have no area or "
        "no frame, so they are not visible whatever color they are:\n"
        + "\n".join(bad))


# --- headings are headings ----------------------------------------------------

def test_no_built_heading_holds_a_code_span_marker(built_site):
    """The symptom, checked where the cause cannot be seen.

    `test_docs_site.py` lints the markdown for a `#` in column one, which is
    what produced this: two pages had a hex color wrapped onto the second line
    of a code span, and Python-Markdown -- which splits blocks before it parses
    inline spans -- made each one an <h1> holding the rest of the sentence, with
    a permalink `¶` mid-paragraph and a line of prose in the table of contents.

    That lint knows the one cause it was written for. A backtick surviving into
    rendered heading text means some span did not close, whatever opened it, so
    this reads the built HTML instead of the source and does not care why.
    """
    offenders = []
    for page in sorted(built_site.rglob("index.html")):
        for inner in re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>",
                                page.read_text(encoding="utf-8"), re.S):
            body = re.sub(r"<[^>]+>", "", inner)
            if "`" in body:
                offenders.append(
                    f"  {page.relative_to(built_site)}: {body.strip()[:80]}")
    assert not offenders, (
        "rendered heading(s) contain a backtick, so a code span did not close "
        "and the text after it became a heading:\n" + "\n".join(offenders))


# --- links land on the deploy base --------------------------------------------

def deploy_base():
    """The path `site_url` publishes under, `/figure-gate/`.

    Read from the config rather than written here, and it is the whole reason
    this check exists: on a project Pages site every page hangs one directory
    below the domain root, so a link with one `../` too many resolves to
    `narenp12.github.io/choosing-a-form/` -- off the site, 404, and identical to
    a correct link in every local preview served at `/`.
    """
    match = re.search(r'^site_url\s*=\s*"([^"]+)"', CONFIG.read_text(encoding="utf-8"), re.M)
    assert match, "zensical.toml no longer states a site_url"
    path = urllib.parse.urlparse(match.group(1)).path
    return path if path.endswith("/") else path + "/"


def test_the_deploy_base_is_a_subdirectory():
    """Guard on the guard above. If `site_url` ever moved to a domain root the
    test below would still pass every link it was given while checking nothing,
    because escaping a base of `/` is not possible."""
    assert deploy_base() != "/", (
        "site_url now publishes at a domain root, so the link test below can no "
        "longer catch a link that walks off the site. Point it at something "
        "else before deleting this.")


# The skip-to-content link on the generated 404 page, which the theme emits
# without the `id="__skip"` it points at. No source document here mentions it.
THEME_LINKS = {("404.html", "#__skip")}


def broken_links(pages, files, base):
    """Every href in `pages` that does not land, resolved as a browser would.

    `pages` maps a page's path from the site root -- `api/index.html` -- to its
    HTML, and `files` is everything the build wrote, directories included: many
    hrefs point at a stylesheet or a favicon, which have to exist and have no
    anchors to check. Taking both as arguments keeps this a function of text,
    so it can be handed a site written to be broken -- the only way to watch it
    fail, since against correct documents a check that resolved nothing looks
    exactly like this one.

    The fragment is split off before the path is resolved and then checked on
    its own, because both halves are claims that fail differently. Keeping the
    `#` on the path asks for `how-to/#read-one-row-or-one-gate` and calls a
    correct cross-page link a 404; dropping the fragment instead lands on a
    page whose section somebody renamed and scrolls nowhere, silently.
    """
    anchors = {name: set(re.findall(r'\bid="([^"]+)"', text))
               | set(re.findall(r'\bname="([^"]+)"', text))
               for name, text in pages.items()}
    offenders = []
    for name, text in sorted(pages.items()):
        parent = posixpath.dirname(name)
        here = base + (f"{parent}/" if parent else "")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if (name, href) in THEME_LINKS:
                continue
            path, _, fragment = href.partition("#")
            fragment = urllib.parse.unquote(fragment)
            if not path:                       # `#section` on this page
                landing = name
            else:
                target = posixpath.normpath(posixpath.join(here, path))
                if path.endswith("/") or path in (".", ".."):
                    target += "/"
                if not (target + "/").startswith(base):
                    offenders.append(f"  {name}: {href} -> {target} (off the site)")
                    continue
                landing = target[len(base):]
                if target.endswith("/"):
                    landing += "index.html"
                if landing not in files:
                    offenders.append(f"  {name}: {href} -> {target} (404)")
                    continue
            # Only answerable where the landing is a page: `#page=3` into a PDF
            # is a claim about a file format, and not this test's to read.
            if fragment and landing in pages and fragment not in anchors[landing]:
                offenders.append(
                    f"  {name}: {href} -> {landing} has no #{fragment}")
    return offenders


def test_every_internal_link_resolves_under_the_deploy_base(built_site):
    """Every href in the built HTML, resolved the way a browser resolves it.

    `--strict` fails on a broken link between *markdown* pages and says nothing
    about an `<a href>` written by hand in a raw HTML block -- which is how the
    gallery's figcaption shipped `../../choosing-a-form/` from a source that
    reads `../choosing-a-form/`: paths in raw HTML are resolved against the
    docs directory and then rewritten relative to the output page, so the `../`
    that looks right in the source is applied twice.

    Checked against the base, not just for existence: `posixpath.normpath`
    clamps at `/`, so a link that walks off the site normalises to a path that
    exists and the naive version of this test passes.
    """
    base = deploy_base()
    pages = {path.relative_to(built_site).as_posix():
             path.read_text(encoding="utf-8")
             for path in sorted(built_site.rglob("*.html"))}
    assert len(pages) > 1, "the build produced no pages to check"
    # The empty string is the site root, which `./..` from a page resolves to.
    files = {path.relative_to(built_site).as_posix()
             for path in built_site.rglob("*")} | {""}
    offenders = broken_links(pages, files, base)
    assert not offenders, (
        f"link(s) in the built site do not resolve under {base}:\n"
        + "\n".join(offenders))


def test_the_link_check_catches_each_way_a_link_can_miss():
    """Three failures the corpus does not contain, and one link correct in the
    way the real cross-page links are: the missing anchor is the half a
    fragment-blind check cannot see, and the working `../page/#section` is the
    one such a check calls a 404."""
    pages = {
        "index.html": ('<a href="api/#the-gate-functions">into a section</a>'
                       '<a href="api/#no-such-section">a section that went</a>'
                       '<a href="nowhere/">a page that went</a>'
                       '<a href="../../elsewhere/">off the site</a>'),
        "api/index.html": '<h2 id="the-gate-functions">The gate functions</h2>',
    }
    reported = broken_links(pages, set(pages) | {"api", ""}, "/figure-gate/")
    assert [r.split(": ", 1)[1] for r in reported] == [
        "api/#no-such-section -> api/index.html has no #no-such-section",
        "nowhere/ -> /figure-gate/nowhere/ (404)",
        "../../elsewhere/ -> /elsewhere/ (off the site)"]


# --- the figures are not recolored --------------------------------------------

def test_no_filter_is_applied_to_gallery_figures():
    """The dark-mode temptation, foreclosed.

    The gallery PNGs are opaque white because they are drawn for paper, and on
    the dark page that is 19.56:1 of it. `filter: invert()` fixes the glare and
    moves every Okabe-Ito hue off the palette -- the gallery would stop showing
    what the checker passed, on the one page whose whole job is showing it.
    """
    # Reads the source, so it needs no browser and runs everywhere the rest of
    # the suite does -- the temptation it forecloses arrives while someone is
    # looking at the dark page, not while they are running the docs job.
    text = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    for bad in ("invert(", "hue-rotate(", "saturate("):
        assert bad not in text, (
            f"palette.css applies {bad} - a filter on a gallery figure changes "
            "the colors the gates certified. Frame the white instead of "
            "recoloring the figure.")


# --- the adopted features behave as built --------------------------------------
# An unknown name in the `features` list is accepted silently -- a build with
# `content.tabs.link` misspelled exits 0 and no part of the site syncs -- so
# each Pass 1 feature is proven on the page, the way the contrast defect above
# was. The tab sync test in particular is the only thing that can show the link
# feature is on.

GETTING_STARTED_PATH = "/getting-started/"
HOW_TO_PATH = "/how-to/"
GATES_PATH = "/gates/"


def _tab_groups(page):
    """Every `.tabbed-set` measured by what a reader sees.

    Visibility is read off `getComputedStyle`, deliberately not off the
    `hidden` attribute: pymdownx's alternate style hides a block under a
    `:checked` sibling selector, so a block's not being rendered never shows up
    as an attribute. Asserting the attribute would be asserting the CSS
    implementation, which is not what this site is being held to.
    """
    return page.evaluate("""() => {
      return [...document.querySelectorAll('.tabbed-set.tabbed-alternate')].map(s => {
        const radios = [...s.querySelectorAll('input')];
        return {
          labels: [...s.querySelectorAll('.tabbed-labels > label')]
            .map(l => l.textContent.trim()),
          active: [...s.querySelectorAll('.tabbed-labels > label')]
            .findIndex(l => l.getAttribute('for') ===
                            (radios.find(i => i.checked) || {}).id),
          shown: [...s.querySelectorAll('.tabbed-block')].map(bl =>
            getComputedStyle(bl).display !== 'none'),
        };
      });
    }""")


def test_getting_started_tabs_sync_the_shared_label_and_nothing_else(page, server):
    """`content.tabs.link`, proven.

    The two groups share "Vendored" at different positions (0 in the install
    routes, 2 in the import lines). A link by *position* would move the import
    group whenever the first group changed at all; a link by *label* moves it
    only for the shared word. The sequence distinguishes the two:

    - `conda-forge` has no counterpart in the import group, so that group must
      not move -- a position-based link would have moved it anyway.
    - `Vendored` has a counterpart, so that group must move to its own
      "Vendored", and the previously active tab of each group hides its block.
    """
    page.goto(server + GETTING_STARTED_PATH, wait_until="networkidle")
    groups = page.locator(".tabbed-set.tabbed-alternate")
    assert groups.count() == 2, (
        "getting-started.md writes two tab groups (install routes and import "
        f"lines); the build produced {groups.count()}")
    assert _tab_groups(page) == [
        {"labels": ["Vendored", "Installed", "conda-forge"],
         "active": 0, "shown": [True, False, False]},
        {"labels": ["0.7+ installed", "0.6 and earlier", "Vendored"],
         "active": 0, "shown": [True, False, False]},
    ]

    groups.nth(0).locator(".tabbed-labels label", has_text="conda-forge").click()
    state = _tab_groups(page)
    assert state[0]["active"] == 2, state
    assert state[0]["shown"] == [False, False, True], state
    assert state[1]["active"] == 0, state

    groups.nth(0).locator(".tabbed-labels label", has_text="Vendored").click()
    assert _tab_groups(page) == [
        {"labels": ["Vendored", "Installed", "conda-forge"],
         "active": 0, "shown": [True, False, False]},
        {"labels": ["0.7+ installed", "0.6 and earlier", "Vendored"],
         "active": 2, "shown": [False, False, True]},
    ]


def test_how_to_annotations_render_and_expand_in_the_browser(page, server):
    """The annotation markers are built by the bundle at view time.

    The built HTML keeps `# (1)!` as literal text in the code span; the
    `.md-annotation` aside exists only after the page's own JavaScript has run,
    which is exactly why this is a browser test and a static-HTML scan is not
    the one that proves anything. There is no static text to scan.
    """
    page.goto(server + HOW_TO_PATH, wait_until="networkidle")
    page.wait_for_selector(".md-annotation")
    annotations = page.locator(".md-annotation")
    assert annotations.count() == 4, (
        f"how-to.md writes four `# (n)!` markers; the bundle turned "
        f"{annotations.count()} of them into .md-annotation")

    annotations.first.focus()
    tooltip = page.locator(".md-tooltip--active")
    page.wait_for_selector(".md-tooltip--active")
    assert "The backend is set before pyplot imports" in tooltip.inner_text(), (
        f"the expanded annotation reads {tooltip.inner_text()[:80]!r} -- the "
        "ordered list that answers the marker is not reaching the tooltip")


@pytest.mark.parametrize("path,count,starts_open", [
    (HOW_TO_PATH, 2, False),   # transcripts: closed, a click of the title opens
    (GATES_PATH, 5, True),     # design notes: open, a click of the title folds
])
def test_collapsible_notes_toggle_open_on_click(page, server, path, count,
                                               starts_open):
    """A `???` / `???+` admonition toggles on clicking its title.

    The count is pinned because a collapsible that stops being one takes its
    story with it: the transcripts become a wall of text between recipes and
    the design notes can no longer be folded. Whether the note starts open is
    itself pinned -- gates' notes read as prose and fold on demand, how-to's
    transcripts are evidence kept out of the way until asked for.
    """
    page.goto(server + path, wait_until="networkidle")
    notes = page.locator("details.note")
    assert notes.count() == count, (
        f"expected {count} collapsible note(s) on {path}, found {notes.count()}")
    assert all((notes.nth(i).get_attribute("open") is not None) == starts_open
               for i in range(count)), (
        f"on {path} every note should start "
        f"{'open' if starts_open else 'collapsed'}")

    notes.nth(0).locator("summary").click()
    opened = notes.nth(0).get_attribute("open") is not None
    assert opened != starts_open
    assert notes.nth(0).locator(":scope > :not(summary)").first.is_visible() \
        == opened

    notes.nth(0).locator("summary").click()
    assert (notes.nth(0).get_attribute("open") is not None) == starts_open


def test_the_gates_flow_diagram_draws_an_svg(page, server):
    """mermaid, proven on the page.

    The built HTML keeps the fence's text in a `<pre class="mermaid">`; the
    diagram's SVG exists only after the page's own JavaScript has run, and the
    bundle renders it into a *closed* shadow root, so no selector can reach it
    and a static-HTML scan sees nothing. This test overrides
    `attachShadow` before any page script runs to record every closed root,
    then asks whether any of them holds an SVG with real content -- the only
    way to prove the renderer ran, short of re-implementing the bundle.

    The diagram's words are checked too, because an SVG that renders is not
    necessarily an SVG that reads right: mermaid 11 prints a literal `\n` in a
    quoted diamond label instead of breaking the line, so the `need` diamond's
    question is asserted to carry a real `<br>` element. That spelling is
    coupled to the engine's htmlLabels/foreignObject path -- `zensical.toml`
    pins mermaid@11.4.1, and a bump that switched to `<tspan>` breaks would
    fail this test with the message below rather than silently.

    The diagram's floor is that a fence whose engine never loaded leaves a
    `<pre>` and no shadow root at all, which fails this test's first assert
    with the cause attached.
    """
    page.add_init_script("""
      window.__closedRoots = [];
      const _attach = Element.prototype.attachShadow;
      Element.prototype.attachShadow = function (init) {
        const root = _attach.call(this, init);
        if (init && init.mode === "closed") window.__closedRoots.push(root);
        return root;
      };
    """)
    page.goto(server + GATES_PATH, wait_until="networkidle")
    page.wait_for_selector("div.mermaid")
    drawn = page.evaluate("""() => {
      const svgs = window.__closedRoots
        .filter(r => r.querySelector("svg"))
        .map(r => ({ nodes: r.querySelectorAll("*").length,
                     w: r.querySelector("svg").getBoundingClientRect().width,
                     text: [...r.querySelectorAll("span")]
                       .map(s => s.textContent),
                     brs: r.querySelectorAll("br").length }));
      return { roots: window.__closedRoots.length, svgs };
    }""")
    assert drawn["roots"] >= 1, (
        "gates.md's mermaid fence rendered no closed shadow root - the engine "
        "did not run, or the bundle stopped rendering mermaid into a shadow")
    assert any(s["nodes"] >= 50 and s["w"] > 0 for s in drawn["svgs"]), (
        f"no closed shadow root holds a real diagram, got {drawn['svgs']} - "
        "the fence is a <pre> the renderer never consumed")
    assert page.locator("pre.mermaid").count() == 0, (
        "the mermaid fence was left as a literal <pre class='mermaid'> - the "
        "renderer did not replace it")

    labels = [t for s in drawn["svgs"] for t in s["text"]]
    assert not any("\\n" in t for t in labels), (
        f"a mermaid label reached the page as a literal `\\n`, got {labels} - "
        "mermaid 11 does not turn `\\n` into a line break; the break has to "
        "be a `<br>` element")

    diamond = [s for s in drawn["svgs"]
               if any("all-pairs" in t for t in s["text"])]
    assert len(diamond) == 1, (
        f"expected one diagram root carrying the 'all-pairs' diamond, got "
        f"{len(diamond)} - gates.md's story changed, or a second diagram "
        "matches the label search")
    root = diamond[0]
    assert root["brs"] >= 1, (
        "the flow diagram's `need` diamond carries no `<br>`, so 'adjacent or' "
        "and 'all-pairs?' sit on one line - a literal `\\n` renders as text, "
        "which is the defect this assertion is written to see")
    diamond_text = " | ".join(root["text"])
    assert "adjacent or" in diamond_text and "all-pairs?" in diamond_text, (
        f"the diamond's two lines are {diamond_text!r} - the label no longer "
        "reads 'adjacent or' over 'all-pairs?', or the diagram's story changed")


def test_the_gates_threshold_column_sorts_by_value(page, server):
    """tablesort's number plugin, proven.

    The threshold column's cells are prose or backtick-quoted constants
    ("canvas bounds", "`BANKING_SLOPE_MAX = 10.0`"), so the number plugin's
    detect() -- which requires a cell to *start* with a digit -- never engages
    on its own. `javascripts/tablesort.js` forces `data-sort-method="number"`
    on that one header; this test proves the force landed and that the sorted
    order is numeric, with `10.0` after `2.0` as the design specifies.

    A string sort would order the value column differently ("10" before "2",
    alphabetically) and no code on the page could be blamed but the missing
    force.
    """
    page.goto(server + GATES_PATH, wait_until="networkidle")
    table = page.locator(".sortable table")
    assert table.count() == 1, (
        "the gates page should carry exactly one sortable table; found "
        f"{table.count()} - gates.md's div wrapper or the tablesort selector "
        "drifted")
    header = table.locator("th", has_text="Threshold")
    assert header.get_attribute("data-sort-method") == "number", (
        "javascripts/tablesort.js no longer forces the number method on the "
        "Threshold column - its cells do not auto-detect, so it would sort "
        "as strings")

    header.click()
    page.wait_for_timeout(200)
    assert header.get_attribute("aria-sort") == "ascending", (
        "tablesort did not mark the clicked header, so the plugin did not run")

    values = page.evaluate("""() => [...document.querySelectorAll(
      ".sortable tbody tr")].map(tr => tr.cells[1].textContent.trim())""")
    keys = [_number_sort_key(v) for v in values]
    assert keys == sorted(keys), (
        f"the Threshold column did not sort numerically: {values} - keys "
        f"{keys} are not non-decreasing; '10' would precede '2' in a string "
        "sort, which is the failure this test is written to see")


def _number_sort_key(cell):
    """A cell's tablesort.number key, mirrored from the plugin.

    The plugin cleans a cell to digits, minus, dot and question mark, then
    parseFloat reads the leading number; no number sorts as 0.
    """
    cleaned = "".join(c for c in cell if c.isdigit() or c in "-.?")
    match = re.match(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else 0.0


TILE_ICONS = {
    "rocket": "getting-started",
    "wrench": "how-to",
    "filter": "gates",
    "image": "gallery",
    "book": "style-guide",
    "code": "api",
}


def home_article(built_site):
    """The home page's article, and nothing around it.

    Seven of the page's `svg.lucide` live in the header, the search dialog and
    the table of contents; scoping to the article is how "the grid's six icons
    are the only icons in the prose" is asserted without a list of chrome to
    keep in step here.
    """
    html = (built_site / "index.html").read_text(encoding="utf-8")
    article = re.search(r"<article class=\"[^\"]*\">(.*?)</article>", html, re.S)
    assert article, "the home page no longer renders an article container"
    grid = re.search(r'<div class="grid cards">\s*<ul>(.*?)</ul>',
                     article.group(1), re.S)
    assert grid, "the card grid is no longer a `<div class=\"grid cards\">`"
    return grid.group(1)


def test_the_home_card_grid_has_six_iconed_tiles(built_site):
    """Six tiles, each with its designed lucide icon and a link that lands.

    The icon classes in `TILE_ICONS` are the design's answer to "which page is
    this", and the hrefs are checked against the built site rather than for
    text, because the grid is raw HTML: `--strict` knows nothing about a link
    written by hand in a `<div>`, and `test_every_internal_link_resolves...`
    skips absolute URLs (its scheme guard) -- these absolute `https://` hrefs
    are exactly the links that check never sees.
    """
    lis = re.findall(r"<li>.*?</li>", home_article(built_site), re.S)
    assert len(lis) == 6, (
        f"the README's grid should hold six tiles, found {len(lis)}")

    base = deploy_base()
    files = {p.relative_to(built_site).as_posix()
             for p in built_site.rglob("*")}
    got = {}
    for li in lis:
        icons = re.findall(r"lucide lucide-([a-z-]+)", li)
        assert len(icons) == 1, (
            f"a tile must carry exactly one icon, got {icons} in {li[:120]!r}")
        name = icons[0]
        assert name in TILE_ICONS, f"{name} is not one of the designed tile icons"
        href = re.search(r'<a href="([^"]+)">', li)
        assert href, f"a tile links nowhere: {li[:120]!r}"
        page = urllib.parse.urlparse(href.group(1)).path
        assert page.startswith(base), (
            f"tile href {href.group(1)} leaves the deploy base {base}")
        landing = page[len(base):]
        built = landing if not landing.endswith("/") else landing + "index.html"
        assert built in files, (
            f"tile href {href.group(1)} does not land on a built page")
        got[name] = landing.rstrip("/")
    assert got == TILE_ICONS, (
        f"the tile hrefs are {got}, expected the six designed pages")


def test_the_six_tile_icons_are_the_only_icons_in_the_home_prose(built_site):
    """The icon-count rule behind the grid being the exception.

    The site's voice is contrast arithmetic, and the grid exists because one
    icon per tile carries information. A seventh `svg.lucide` in the article is
    a decoration the review never signed off on, and it is the count's whole
    job to name it.
    """
    icons = re.findall(r'class="lucide lucide-[a-z-]+"',
                       home_article(built_site))
    assert len(icons) == 6, (
        f"{len(icons)} icon(s) in the home article, expected the grid's 6 -- "
        "a seventh icon is decoration the count was written to catch")


# --- this file skips, it does not error ---------------------------------------

BLOCKER = """
import sys


class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {"filelock", "playwright"}:
            raise ImportError(f"{name} is blocked for this run")
        return None


sys.meta_path.insert(0, Blocker())
"""


@pytest.mark.skipif(os.environ.get(NESTED) is not None,
                    reason="this is the nested run; it does not start another")
def test_this_file_skips_rather_than_errors_without_the_docs_group(tmp_path):
    """The docstring at the top of this file, made executable.

    It has claimed since it was written that the file is "skipped, not failed,
    when the browser or the site builder is missing" -- and that claim shipped
    false. Everything that needed a browser went through `playwright_api()` and
    skipped; the one test that needed only a built site went straight to
    `built_site`, hit an unguarded `from filelock import FileLock`, and errored
    on all four `pytest` jobs in the matrix.

    So this asks rather than asserts: run this file in a subprocess with both
    docs-test distributions unimportable, and require a clean exit. Reading the
    source for guarded imports would pass a file where a fixture forgot to call
    one, which is the defect that happened.

    Cheap because it is supposed to be: with nothing importable, nothing builds
    the site or launches a browser, and a run that does take minutes has failed
    the point of the test as surely as a red one.
    """
    (tmp_path / "sitecustomize.py").write_text(BLOCKER, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(tmp_path), **{NESTED: "1"})

    run = subprocess.run(
        [sys.executable, "-m", "pytest", str(Path(__file__).resolve()),
         "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, env=env)

    assert "no tests ran" not in run.stdout, (
        "the nested run collected nothing, so its clean exit says nothing "
        f"about this file:\n{run.stdout}\n{run.stderr}")
    assert run.returncode == 0, (
        "without the docs-test group this file must skip, not error. It "
        f"exited {run.returncode}:\n{run.stdout}\n{run.stderr}")
