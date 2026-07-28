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
import re
import shutil
import socket
import socketserver
import subprocess
import threading
from pathlib import Path

import pytest

from conftest import SKILL

import check_palette as cp

from test_docs_site import CSS, SLATES, nav_targets, scheme_link_colors

ROOT = SKILL.parent
SITE = ROOT / "site"


def playwright_api():
    """Imported in a fixture, deliberately, not with a module-level
    `importorskip`.

    A module-level skip fires during *collection*, so this file would contribute
    its tests to the suite on a machine with Chromium installed and nothing on
    one without. `test_docs_match_code.py` holds the README's stated test count
    to what pytest collects, and that number would then depend on which machine
    asked. Collect always, skip at run time.
    """
    try:
        import playwright.sync_api as api
    except ImportError:
        pytest.skip("playwright is in the docs-test group; the figure gates "
                    "do not need it. `uv sync --group docs-test`")
    return api

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
        ["uv", "run", "--no-project", "--with", "zensical>=0.0.51,<0.1",
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
    if worker_id == "master":
        _build_the_site()
        return SITE

    # Imported here rather than at the top for the same reason as playwright:
    # a module-level import of a docs-test dependency turns "this file skips"
    # into "this file fails to collect", and the README's test count is held to
    # what pytest collects.
    from filelock import FileLock

    shared = tmp_path_factory.getbasetemp().parent
    with FileLock(str(shared / "zensical-build.lock")):
        marker = shared / "zensical-build.done"
        if not marker.is_file():
            _build_the_site()
            marker.write_text("built")
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
        yield b
        b.close()


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

  const cs = getComputedStyle(document.body);
  return {
    scheme: document.body.getAttribute('data-md-color-scheme'),
    link_color: cs.getPropertyValue('--md-typeset-a-color').trim(),
    primary: cs.getPropertyValue('--md-primary-fg-color').trim(),
    accent: cs.getPropertyValue('--md-accent-fg-color').trim(),
    page_bg: hex(parse(cs.backgroundColor)),
    items,
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
    source = re.sub(r"/\*.*?\*/", "", CSS.read_text(), flags=re.S)
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
    text = re.sub(r"/\*.*?\*/", "", CSS.read_text(), flags=re.S)
    for bad in ("invert(", "hue-rotate(", "saturate("):
        assert bad not in text, (
            f"palette.css applies {bad} - a filter on a gallery figure changes "
            "the colors the gates certified. Frame the white instead of "
            "recoloring the figure.")
