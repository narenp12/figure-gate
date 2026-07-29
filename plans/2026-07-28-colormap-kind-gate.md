# Colormap-kind gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a twentieth gate to `check_figure.py` that classifies every colormap a figure actually uses and fails the ones a reader cannot order values in, plus a seventh gallery figure that exercises three different colormap kinds.

**Architecture:** `check_palette.py` gains a pure, stdlib-only `cmap_kind(samples)` that takes a list of hex strings and returns one of `sequential` / `diverging` / `cyclic` / `qualitative` / `misc`, decided from OKLab lightness back-travel plus an end-to-end OKLab ΔE. `check_figure.py` gains `check_colormap(fig)`, which harvests colormaps off `ax.images` and `ax.collections`, samples each, calls `cmap_kind`, fails on `misc`, and routes `qualitative` through `check_palette.check`'s separation rows. A `cmasher` differential test acts as an external oracle in dev only.

**Tech Stack:** Python 3.9+, matplotlib >= 3.8, pytest, uv. One new dev-only dependency: `cmasher`. Zero new runtime dependencies.

**User decisions (already made):**
- Scope is "Coverage + colormap gate" — a new gate, not coverage-only, and no form-guidance prose in `choosing-a-form.md`.
- Gallery objects are escape-time fractal, domain coloring / phase portrait, and Newton fractal basins. Explicitly NOT the Barnsley fern / IFS option.
- Classifier approach is "Port cmasher to OKLab" — not a colormap name table, not declared-intent.
- Dependency posture: "small package that is portable but dependencies can be more efficient" — spend a dependency where it buys something, and here that means dev-only.
- The design in `specs/2026-07-28-colormap-kind-gate-design.md` is approved.

**Plan location:** `plans/`, not `docs/superpowers/plans/`. `tests/test_docs_site.py::test_no_page_has_become_a_copy` fails on any real (non-symlink) `.md` under `docs/` that is not in its `AUTHORED` list. The spec went to `specs/` for the same reason.

---

## Spec amendment made during planning (read this before Task 3)

The spec's routing step 3 says:

> - qualitative -> `check_palette.check(levels, all_pairs=True)` …
> - sequential -> `check_palette.check(ramp, ordinal=True)`, monotone lightness and even steps
> - diverging, cyclic -> the ordinal check per half

**Both halves of that were measured during planning and both are wrong.** The measurements:

**`check(ordinal=True)` fails every canonical sequential colormap.** Its `Light-end contrast` row requires the lightest step to clear 2.0:1 against the surface:

| colormap | light end | contrast vs white | verdict |
| --- | --- | --- | --- |
| viridis | `#fde725` | 1.26:1 | FAIL |
| cividis | `#fee838` | 1.25:1 | FAIL |
| magma | `#fcfdbf` | 1.05:1 | FAIL |
| Blues | `#f7fbff` | 1.04:1 | FAIL |

That row is correct for what it was written for — a discrete ramp of hand-picked swatches sitting on a white page, where the lightest swatch must be tellable from the page. A continuous colormap's light end sits against its own neighbouring values, not against the page. Its `Adjacent dL >= 0.06` row is also a function of how many samples the caller took, not a property of the colormap: Blues passes at 5 and 7 samples and fails at 9. Routing sequential maps there would fail `examples/gallery.py`'s existing `field()` figure, which draws `contourf(..., cmap="viridis")`.

**`check(all_pairs=True)` unfiltered fails the repository's own palette.** Run over all 8 Okabe-Ito levels it fails `Lightness band`, `Chroma floor` and `Contrast vs surface`, because Okabe-Ito contains black and yellow.

**The fix is the repository's own existing precedent.** `check_series_color` at `skill/scripts/check_figure.py:1209-1217` already calls `cp.check(...)` and then reads **only** the `CVD separation` and `Normal-vision floor` rows, for the reason written into its docstring at `check_figure.py:1162-1166`: a black or gray series is legal and failing it "is precisely the noise that teaches people to skim past the row." `check_colormap` does exactly the same.

**Amended routing, which is what Task 3 implements:**

| kind | what the gate does |
| --- | --- |
| `misc` | **FAIL**, naming the colormap and its back-travel |
| `qualitative` | `cp.check(levels, all_pairs=True)`, filtered to the `CVD separation` and `Normal-vision floor` rows only. FAIL if either is False. |
| `sequential` | PASS. The kind *is* the finding; `cmap_kind` already proved monotone lightness. |
| `diverging` | PASS, same reason, per half. |
| `cyclic` | PASS, same reason. |

**What this gives up, stated plainly:** the gate no longer says anything about a sequential map whose lightness span is too narrow to carry an ordinal reading. That is the Wistia defect the spec already deferred, and it needs a span-floor threshold with its own registry-wide measurement. It is not invented here. Task 3 records it in the spec's Limits section as the follow-up it is.

**What the gate still catches, all verified during planning:** `jet`, `hsv`, `rainbow`, `brg`, `nipy_spectral`, `gist_ncar`, `Wistia` — and any qualitative colormap whose levels do not separate, including matplotlib's default `tab10` (orange vs green at OKLab ΔE 1.4 under protanopia).

---

## File structure

| file | responsibility | task |
| --- | --- | --- |
| `skill/scripts/check_palette.py` | pure classifier: hex list in, kind string out. Stdlib only. | 1 |
| `tests/test_palette.py` | pins every threshold and every named colormap | 1 |
| `tests/test_palette_oracle.py` | **new file** — the cmasher differential, isolated so its skip is one file's problem | 2 |
| `pyproject.toml` | one dev-group dependency | 2 |
| `skill/scripts/check_figure.py` | harvest, route, report. Knows matplotlib; knows no color math. | 3 |
| `tests/test_figure.py` | harvest paths, routing, colorbar, regression | 3 |
| `specs/2026-07-28-colormap-kind-gate-design.md` | amended to match what shipped | 3 |
| `README.md`, `skill/SKILL.md`, `tests/test_docs_match_code.py` | the roster, in its four places | 4 |
| `examples/gallery.py` | the seventh figure | 5 |
| `docs/gallery.md`, `tests/test_example.py` | gallery count and prose | 5, 6 |

The classifier lives in `check_palette.py` and takes **hex strings, never a matplotlib `Colormap`**. That is what keeps the file's opening promise — "No dependencies beyond the standard library" — true. All matplotlib contact lives in `check_figure.py`.

---

## Task 1: `cmap_kind()` classifier in `check_palette.py`

**Goal:** A stdlib-only function that takes a list of hex strings and returns the colormap's kind, with every threshold pinned by a test.

**Files:**
- Modify: `skill/scripts/check_palette.py` — add after `delta_e` (ends line 87), before the `# --- gates ---` banner at line 90
- Modify: `tests/test_palette.py` — append at end of file

**Acceptance Criteria:**
- [ ] `cmap_kind(samples)` takes a list of hex strings and returns one of `"sequential"`, `"diverging"`, `"cyclic"`, `"qualitative"`, `"misc"`
- [ ] `check_palette.py` still imports nothing outside the standard library — no matplotlib, no numpy
- [ ] All 23 named colormaps in the test table classify as the table says
- [ ] The 2% back-travel boundary is pinned: 0.019 is sequential, 0.021 is not
- [ ] An isoluminant (flat) sample list returns `"misc"`, not `"sequential"`
- [ ] Fewer than 40 samples returns `"qualitative"` regardless of lightness

**Verify:** `uv run rtk pytest tests/test_palette.py -q` → all pass, no failures

**Steps:**

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_palette.py`:

```python
# --- colormap kind -----------------------------------------------------------
# The classifier is a port of cmasher's `get_cmap_type()` into OKLab, and every
# number in it was measured against matplotlib 3.11.1's registry rather than
# reasoned about. These tests are that measurement, written down. A threshold
# that moves has to move a row here with it.

CMAP_KINDS = {
    "viridis": "sequential",
    "cividis": "sequential",
    "plasma": "sequential",
    "magma": "sequential",
    "gray": "sequential",
    "Blues": "sequential",
    "twilight": "cyclic",
    "twilight_shifted": "cyclic",
    "RdBu": "diverging",
    "Spectral": "diverging",
    "coolwarm": "diverging",
    "PuOr": "diverging",
    # turbo is diverging BY LIGHTNESS and this is not a mistake. Its back-travel
    # is 0.38% and 0.58%, cleaner than coolwarm's -- it was designed to fix the
    # lightness defects that put jet in the misc bucket. What is still wrong
    # with turbo is hue banding, which produces false boundaries without any
    # lightness reversal, and a lightness-only classifier cannot see it. The row
    # is called "Colormap kind", not "Colormap quality", for exactly this.
    "turbo": "diverging",
    "rainbow": "misc",
    "jet": "misc",
    "hsv": "misc",
    "brg": "misc",
    "nipy_spectral": "misc",
    "gist_ncar": "misc",
    # Wistia is the one known false positive. It descends monotonically, 0.954
    # to 0.726, but over a span of only 0.228 -- and back-travel is a ratio with
    # span in its denominator, so its 0.0128 of absolute wobble reads as 5.61%
    # where viridis's 0.0006 over a 0.633 span reads as 0.10%. Narrow-span maps
    # get noisy ratios. Wistia IS sequential by kind; its real defect is a
    # lightness range too narrow to carry an ordinal reading, which is a
    # QUALITY defect and not this function's job. Pinned as misc so the
    # disagreement is visible rather than forgotten. Fixing it needs a span
    # floor measured across the whole registry, which is a separate change.
    "Wistia": "misc",
    "tab10": "qualitative",
    "Set1": "qualitative",
}


def cmap_samples(name):
    """One colormap as the hex list `cmap_kind` takes.

    The sample count is part of the contract and not an implementation detail:
    `cmap_kind` decides qualitative by counting what it is handed, so a caller
    that always took 256 samples would never see a qualitative map. Under 40
    entries means take them all; at or above, take 256 along the ramp.
    """
    colormaps = pytest.importorskip("matplotlib").colormaps
    from matplotlib.colors import to_hex
    cmap = colormaps[name]
    if cmap.N < cp.CMAP_QUALITATIVE_N:
        return [to_hex(cmap(i)) for i in range(cmap.N)]
    return [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
            for i in range(cp.CMAP_SAMPLES)]


@pytest.mark.parametrize("name,expected", sorted(CMAP_KINDS.items()))
def test_named_colormaps_classify_as_measured(name, expected):
    colormaps = pytest.importorskip("matplotlib").colormaps
    if name not in colormaps:
        pytest.skip(f"this matplotlib has no {name}")
    assert cp.cmap_kind(cmap_samples(name)) == expected


def test_viridis_is_not_misc():
    """The regression that motivated back-travel in the first place.

    A direct transcription of cmasher's strict sign test into OKLab returned
    misc for viridis, and for cividis, twilight, coolwarm and RdBu with it --
    37 of the registry as misc. viridis has two lightness reversals totalling
    0.0006 OKLab L, which is 0.10% of its span and is 8-bit quantization noise,
    not design. A tolerance is what tells those apart from a real reversal.
    """
    colormaps = pytest.importorskip("matplotlib").colormaps
    assert cp.cmap_kind(cmap_samples("viridis")) == "sequential"


def lightness_with_one_reversal(reverse, n=101):
    """A rise of span 1.0 carrying exactly one backward step of size `reverse`.

    Built as raw lightness rather than as hex, because 8-bit quantization moves
    a hex round-trip by more than the boundary being tested.
    """
    ls = [i / (n - 1) for i in range(n)]
    ls[n // 2] = ls[n // 2 - 1] - reverse
    return ls


def test_the_back_travel_threshold_is_where_it_says_it_is():
    """2% of span, from both sides. The binding pair in the registry is
    coolwarm's high half at 1.05% against rainbow's low half at 2.79% -- 2.7x
    apart, about 1.9x of headroom either way. This is the tightest constraint
    in the design and the number most likely to need revisiting."""
    assert cp._back_travel(lightness_with_one_reversal(0.019)) < cp.CMAP_BACKTRAVEL_MAX
    assert cp._back_travel(lightness_with_one_reversal(0.021)) > cp.CMAP_BACKTRAVEL_MAX
    assert cp._back_travel(lightness_with_one_reversal(0.0)) == 0.0


def test_an_isoluminant_ramp_is_misc_not_sequential():
    """A map whose lightness never moves carries no ordinal information, and
    back-travel -- a ratio with span in the denominator -- is meaningless for
    it. The span guard is what makes that division safe as well."""
    assert cp.cmap_kind(["#808080"] * 256) == "misc"


def test_fewer_than_forty_samples_is_qualitative_whatever_its_lightness():
    """A perfectly monotone eight-step gray ramp is still a category list if
    that is how many entries it has. Sample count is the discriminator, exactly
    as it is in cmasher."""
    grays = ["#111111", "#333333", "#555555", "#777777",
             "#999999", "#bbbbbb", "#dddddd", "#ffffff"]
    assert cp.cmap_kind(grays) == "qualitative"


def test_the_cyclic_wrap_is_a_colour_distance_not_a_lightness_one():
    """The error the differential caught before it shipped.

    A symmetric diverging map has EQUAL LIGHTNESS AT BOTH ENDS by construction
    -- that is what makes it symmetric. RdYlGn ends red and ends green: same
    lightness, opposite colour. Testing the wrap in lightness classified 11 of
    148 colormaps as cyclic that are diverging. Only a cyclic map closes the
    loop in COLOUR, so the wrap is an OKLab dE. The measured gap runs 0.74
    (hsv) to 7.48 (cmr.fusion), a factor of 10 -- the widest margin in the
    design.
    """
    colormaps = pytest.importorskip("matplotlib").colormaps
    if "RdYlGn" not in colormaps:
        pytest.skip("this matplotlib has no RdYlGn")
    from matplotlib.colors import to_hex
    ends = cmap_samples("RdYlGn")
    lab = [cp.linear_to_oklab(cp.hex_to_linear(h)) for h in (ends[0], ends[-1])]
    assert abs(lab[0][0] - lab[1][0]) < 0.05, "the ends match in lightness"
    assert cp.delta_e(cp.hex_to_linear(ends[0]),
                      cp.hex_to_linear(ends[-1])) > cp.CMAP_WRAP_DE_MAX
    assert cp.cmap_kind(ends) == "diverging"


def test_check_palette_still_imports_nothing_outside_the_standard_library():
    """The file's opening line is a promise: 'No dependencies beyond the
    standard library.' The classifier is the first thing in it that had an
    obvious reason to reach for matplotlib, so the promise gets a test."""
    import ast
    from pathlib import Path
    source = Path(cp.__file__).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"argparse", "itertools", "math"}, imported
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run rtk pytest tests/test_palette.py -q -k "cmap or back_travel or isoluminant or qualitative or standard_library"
```

Expected: FAIL, with `AttributeError: module 'check_palette' has no attribute 'CMAP_QUALITATIVE_N'`

- [ ] **Step 3: Write the implementation**

In `skill/scripts/check_palette.py`, insert this block after `delta_e` (which ends at line 87) and before the `# --- gates ---` banner at line 90:

```python
# --- colormap kind ----------------------------------------------------------
# A port of `cmasher.get_cmap_type()` into OKLab, keeping its STRUCTURE and
# none of its arithmetic. The theory underneath both is Kovesi, "Good Colour
# Maps: How to Design Them" (arXiv:1509.03700): uniform incremental change in
# perceptual lightness is the governing requirement.
#
# matplotlib groups its colormaps by kind in prose documentation only. There is
# no API and no metadata on a `Colormap` object, so the kind has to be measured.
#
# Every constant below was measured against matplotlib 3.11.1's registry and
# each has a stated margin; `tests/test_palette.py` pins the measurement and
# `tests/test_palette_oracle.py` differentials the whole thing against cmasher.

CMAP_SAMPLES = 256          # samples taken along a continuous colormap
CMAP_QUALITATIVE_N = 40     # entries below which a colormap is a category list
CMAP_SPAN_MIN = 0.02        # OKLab L; under this the map is isoluminant
CMAP_BACKTRAVEL_MAX = 0.02  # reverse motion as a fraction of a segment's span
CMAP_WRAP_DE_MAX = 3.0      # OKLab dE x100 between the two ends


def _back_travel(ls):
    """Motion against a segment's dominant direction, over that segment's span.

    The measure that replaced a strict sign test. Transcribing cmasher's
    `|sum(dL)| ~= sum(|dL|)` straight into OKLab misclassified viridis, whose
    two reversals total 0.0006 OKLab L -- 0.10% of its span, and 8-bit
    quantization noise rather than anything anyone designed. A sign test cannot
    tell that from a real reversal; a tolerance can.

    Normalised by span rather than left absolute so the number means the same
    thing on a map that runs black-to-white as on one that runs mid-gray to
    white. That normalisation is also this measure's one known weakness: on a
    map whose span is small the ratio is noisy, which is why Wistia comes out
    misc. See the Limits section of the design spec.
    """
    steps = [b - a for a, b in zip(ls, ls[1:])]
    if not steps:
        return 0.0
    span = max(ls) - min(ls)
    if span <= 0:
        return 0.0
    sign = 1 if sum(1 for s in steps if s > 0) > len(steps) / 2 else -1
    return sum(abs(s) for s in steps if s * sign < 0) / span


def cmap_back_travel(samples):
    """`_back_travel` over a list of hex colors. What the gate reports."""
    return _back_travel([linear_to_oklab(hex_to_linear(h))[0] for h in samples])


def cmap_kind(samples):
    """Which family a colormap belongs to, from a list of hex samples.

    Returns "sequential", "diverging", "cyclic", "qualitative" or "misc".
    `misc` is the failure bucket: it is where jet, hsv, rainbow and the gist_*
    maps land, and it is the only outcome that fails the gate.

    Takes hex strings rather than a matplotlib `Colormap` on purpose. This file
    promises to import nothing outside the standard library, and the caller --
    `check_figure.check_colormap` -- is the one that already has matplotlib.

    THE SAMPLE COUNT IS PART OF THE CONTRACT. Qualitative is decided by
    counting what this function is handed, so a caller that always took 256
    samples would never produce one. Sample all entries when the colormap has
    fewer than `CMAP_QUALITATIVE_N`, and `CMAP_SAMPLES` along the ramp when it
    has more.
    """
    if len(samples) < CMAP_QUALITATIVE_N:
        return "qualitative"

    ls = [linear_to_oklab(hex_to_linear(h))[0] for h in samples]

    # On the span, not on the individual steps: a map whose lightness never
    # moves more than this across its whole length carries no ordinal
    # information at all. Guarding the span also keeps `_back_travel`'s
    # division safe.
    if max(ls) - min(ls) < CMAP_SPAN_MIN:
        return "misc"

    if _back_travel(ls) < CMAP_BACKTRAVEL_MAX:
        return "sequential"

    half = len(ls) // 2
    if (_back_travel(ls[:half + 1]) < CMAP_BACKTRAVEL_MAX
            and _back_travel(ls[half:]) < CMAP_BACKTRAVEL_MAX):
        # A COLOUR distance, not a lightness one, and the distinction is the
        # whole discriminator. A symmetric diverging map has equal lightness at
        # both ends by construction -- RdYlGn ends red and ends green -- so
        # both families close the loop in lightness and only a cyclic map
        # closes it in colour. Testing lightness here put 11 of 148 colormaps
        # in the wrong family.
        wrap = delta_e(hex_to_linear(samples[0]), hex_to_linear(samples[-1]))
        return "cyclic" if wrap < CMAP_WRAP_DE_MAX else "diverging"

    return "misc"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run rtk pytest tests/test_palette.py -q
```

Expected: all pass, 0 failures.

- [ ] **Step 5: Commit**

```bash
rtk git add skill/scripts/check_palette.py tests/test_palette.py && rtk git commit -m "feat: classify a colormap's kind from its OKLab lightness profile"
```

---

## Task 2: cmasher differential test as an external oracle

**Goal:** Prove `cmap_kind` agrees with an independent, published implementation across matplotlib's whole registry, and record the three places it deliberately does not.

**Files:**
- Create: `tests/test_palette_oracle.py`
- Modify: `pyproject.toml` — `[dependency-groups] dev`

**Acceptance Criteria:**
- [ ] `cmasher>=1.9` is in the dev group with a `python_version >= '3.10'` marker
- [ ] Nothing in `skill/scripts/` imports cmasher
- [ ] The test skips cleanly when cmasher is absent, and on Python 3.9
- [ ] Exactly three colormaps are listed as known disagreements, each with a comment saying which implementation is right and why
- [ ] Any *new* disagreement fails the test by name

**Verify:** `uv run rtk pytest tests/test_palette_oracle.py -q` → 2 passed (or 2 skipped on Python 3.9)

**Steps:**

- [ ] **Step 1: Add the dependency**

```bash
uv add --dev "cmasher>=1.9 ; python_version >= '3.10'"
```

Expected: `pyproject.toml`'s `[dependency-groups] dev` list gains `"cmasher>=1.9 ; python_version >= '3.10'"`, and `uv.lock` updates.

Then add this comment immediately above the `dev = [` list in `pyproject.toml`, so the reason the marker exists survives:

```toml
# cmasher is a TEST ORACLE and never a runtime dependency. `cmap_kind` is a
# port of its `get_cmap_type()` into OKLab, and `tests/test_palette_oracle.py`
# differentials the two across matplotlib's registry. It earned its place
# before it was written into a test: running the differential during design
# caught a wrong threshold that would otherwise have shipped 11 colormaps in
# the wrong family.
#
# Same marker reasoning as `docs` below -- cmasher 1.9.2 needs Python >= 3.10
# and this project supports 3.9, so without the marker uv resolves the group
# across the full range and fails outright. It pulls colorspacious, numpy and
# matplotlib, none of which the shipped scripts may import.
```

- [ ] **Step 2: Write the test file**

Create `tests/test_palette_oracle.py`:

```python
"""`cmap_kind` against an independent implementation, over the whole registry.

The classifier is a port of `cmasher.get_cmap_type()` from CAM02-UCS into
OKLab. A port with no oracle is a rewrite nobody checked, and this one was
wrong in a way that unit tests would not have caught: an earlier draft measured
the cyclic/diverging wrap in lightness, which put 11 of 148 colormaps in the
wrong family because a symmetric diverging map has equal lightness at both ends
BY CONSTRUCTION. Running this differential is what found that.

cmasher is a dev-group dependency and is never imported by anything under
`skill/scripts/`. It needs Python >= 3.10; this project supports 3.9.
"""

import sys

import pytest

import check_palette as cp

cmr = pytest.importorskip("cmasher", reason="dev-only test oracle")
colormaps = pytest.importorskip("matplotlib").colormaps

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="cmasher requires Python 3.10")


# The three colormaps where the two implementations disagree, out of 148
# measured on cmasher 1.9.2 and matplotlib 3.11.1. This list is the design
# record. An EMPTY list would be a claim of exact parity across two colour
# spaces, which is not true and should not be asserted.
KNOWN_DISAGREEMENTS = {
    # OURS IS RIGHT. managua runs L 0.877 -> 0.355 -> 0.875 and vanimo runs
    # 0.906 -> 0.201 -> 0.931: light ends, dark centre, the shape of RdBu
    # inverted. Both are Crameri maps added in matplotlib 3.10, and cmasher's
    # strict `np.isclose` test fails on their micro-reversals -- the same
    # defect that made a direct transcription of it misclassify viridis. The
    # tolerance-based measure is the more robust of the two here.
    "managua": ("diverging", "misc"),
    "vanimo": ("diverging", "misc"),
    # CMASHER IS RIGHT, and this one exposes a real limit of back-travel.
    # Wistia's lightness descends monotonically, 0.954 -> 0.726, but over a
    # span of only 0.228. Back-travel is a ratio with span in its denominator,
    # so 0.0128 of absolute wobble reads as 5.61% where viridis's 0.0006 over a
    # 0.633 span reads as 0.10%. Narrow-span maps get noisy ratios.
    #
    # Not tuned away here, deliberately. Two fixes are available -- a floor on
    # ABSOLUTE back-travel alongside the ratio, or a minimum span below which
    # the ratio is not trusted -- and both need their own measurement across
    # the registry before a constant is picked. Shipping a known, documented
    # disagreement beats shipping an unmeasured threshold.
    "Wistia": ("misc", "sequential"),
}


def registry_names():
    """Every registered colormap, minus the `_r` reversals.

    A reversal has the same kind as its forward map by construction, so
    including them would double the count and prove nothing extra.
    """
    return sorted(n for n in colormaps if not n.endswith("_r"))


def samples(name):
    """One colormap as the hex list `cmap_kind` takes. Under
    `CMAP_QUALITATIVE_N` entries means take them all; at or above, take
    `CMAP_SAMPLES` along the ramp."""
    from matplotlib.colors import to_hex
    cmap = colormaps[name]
    if cmap.N < cp.CMAP_QUALITATIVE_N:
        return [to_hex(cmap(i)) for i in range(cmap.N)]
    return [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
            for i in range(cp.CMAP_SAMPLES)]


def disagreements():
    out = {}
    for name in registry_names():
        ours = cp.cmap_kind(samples(name))
        theirs = cmr.get_cmap_type(colormaps[name])
        if ours != theirs:
            out[name] = (ours, theirs)
    return out


def test_the_registry_is_large_enough_to_be_evidence():
    """A differential over three colormaps agrees with anything. The measured
    run was 148; anything far below that means the registry did not load."""
    assert len(registry_names()) >= 100, registry_names()


def test_only_the_three_known_colormaps_disagree_with_cmasher():
    """145 of 148 agree. Each of the three that does not is adjudicated in
    `KNOWN_DISAGREEMENTS` above, with a comment saying which implementation is
    right. A NEW disagreement is what this test exists to catch -- most likely
    from a future matplotlib adding or revising a colormap and moving one of
    the binding pairs the thresholds were measured against."""
    found = disagreements()
    new = {k: v for k, v in found.items() if k not in KNOWN_DISAGREEMENTS}
    gone = {k: v for k, v in KNOWN_DISAGREEMENTS.items() if k not in found}
    assert not new, (
        f"new disagreements with cmasher: {new}. Adjudicate each one -- say "
        "which implementation is right and why -- and either fix cmap_kind or "
        "add it to KNOWN_DISAGREEMENTS with that reasoning written down.")
    assert not gone, (
        f"these no longer disagree: {gone}. Good news, but the comment "
        "explaining each is now stale and should come out with it.")
    assert found == KNOWN_DISAGREEMENTS, found
```

- [ ] **Step 3: Run it**

```bash
uv run rtk pytest tests/test_palette_oracle.py -q -rs
```

Expected: `2 passed`. On Python 3.9, `2 skipped`.

- [ ] **Step 4: Prove the shipped scripts stay clean**

```bash
rtk grep -rn "cmasher\|colorspacious" skill/
```

Expected: no matches.

- [ ] **Step 5: Commit**

```bash
rtk git add pyproject.toml uv.lock tests/test_palette_oracle.py && rtk git commit -m "test: differential the colormap classifier against cmasher"
```

---

## Task 3: `check_colormap` gate row in `check_figure.py`

**Goal:** A twentieth gate that harvests every colormap the figure actually uses, classifies it, and fails the ones a reader cannot order values in.

**Files:**
- Modify: `skill/scripts/check_figure.py` — add `check_colormap` before `check_fonts` (line 1633); add the row to `audit` (line 1889, after `("Contour dash", ...)`)
- Modify: `tests/test_figure.py` — append at end
- Modify: `specs/2026-07-28-colormap-kind-gate-design.md` — amend the routing section and the Limits section

**Acceptance Criteria:**
- [ ] `audit(fig)` returns 20 rows, with `("Colormap kind", ...)` at index 17, between `Contour dash` and `Fonts`
- [ ] `imshow(cmap="jet")` FAILs; `imshow(cmap="viridis")` PASSes
- [ ] `imshow(cmap="hsv")` FAILs; `imshow(cmap="twilight")` PASSes
- [ ] Harvest reaches `imshow`, `pcolormesh`, `contourf`, `hexbin` and `scatter(c=, cmap=)`
- [ ] A figure with no colormapped artist returns `True, "no colormapped artists"` and does not raise
- [ ] A plain `scatter(x, y, color="#0072b2")` is NOT gated — it returns a default viridis from `get_cmap()` but `None` from `get_array()`
- [ ] A colorbar does not make its parent's colormap report twice
- [ ] `imshow(cmap="tab10")` FAILs on separation, proving routing reaches `check_palette`
- [ ] `_data_colors_by_axes` still excludes colormapped artists, so a heatmap is not gated twice
- [ ] The gate is NOT in `ADVISORY_GATES` — it returns hard False

**Verify:** `uv run rtk pytest tests/test_figure.py -q` → all pass

**Steps:**

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_figure.py`:

```python
# --- the colormap kind gate --------------------------------------------------
# The hole this closes: `check_figure` had nineteen ways to be wrong about a
# figure and none of them looked at a colormap. Every other gate reads artists
# that carry an IDENTITY -- a line's color, a bar's face. A figure whose entire
# content is one colormapped image has no such artist, so it passed every check
# by having nothing the checks knew how to read. A Mandelbrot set in `jet` was
# a PASS.
#
# `_data_colors_by_axes` has excluded colormapped artists since it was written,
# with a comment saying they "answer to the viridis rule instead". No such rule
# existed. This is it.

import numpy as np


def heat(cmap, n=24):
    """One axes carrying one colormapped image, and nothing else."""
    import matplotlib.pyplot as plt
    z = np.add.outer(np.linspace(0, 1, n), np.linspace(0, 1, n))
    fig, ax = plt.subplots()
    ax.imshow(z, cmap=cmap)
    return fig


@pytest.mark.parametrize("cmap", ["viridis", "cividis", "twilight", "RdBu",
                                  "coolwarm", "magma"])
def test_a_legible_colormap_passes(cmap):
    fig = heat(cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail


@pytest.mark.parametrize("cmap", ["jet", "hsv", "rainbow", "nipy_spectral",
                                  "gist_ncar"])
def test_a_rainbow_colormap_fails(cmap):
    """The whole point of the row. `jet` and its family reverse in lightness,
    so a reader cannot order two values by looking at them -- and every one of
    these figures passed all nineteen previous gates clean."""
    fig = heat(cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is False
    assert cmap in detail


def test_hsv_fails_and_twilight_passes_which_is_the_phase_portrait_case():
    """A phase portrait needs a CYCLIC map: the value wraps, so the colormap
    has to as well or there is a false seam at the branch cut. hsv wraps and is
    still unreadable -- its lightness swings wildly within each hue -- while
    twilight wraps AND holds lightness. This pair is why the gate classifies
    rather than just asking 'does it wrap'."""
    bad, good = heat("hsv"), heat("twilight")
    try:
        assert cf.check_colormap(bad)[0] is False
        assert cf.check_colormap(good)[0] is True
    finally:
        plt.close(bad)
        plt.close(good)


@pytest.mark.parametrize("draw,cmap", [
    ("imshow", "viridis"),
    ("pcolormesh", "magma"),
    ("contourf", "viridis"),
    ("hexbin", "cividis"),
    ("scatter_c", "plasma"),
])
def test_harvest_reaches_every_colormapped_call(draw, cmap):
    """Every colormapped matplotlib call lands in `ax.images` or
    `ax.collections`, so those two containers are the whole sweep. Verified
    against matplotlib 3.11.1 for seven call types; these are the five the
    gallery and the docs actually use."""
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(0)
    gx, gy = np.meshgrid(np.linspace(-2, 2, 40), np.linspace(-2, 2, 40))
    z = gx ** 2 + gy ** 2
    fig, ax = plt.subplots()
    if draw == "imshow":
        ax.imshow(z, cmap=cmap)
    elif draw == "pcolormesh":
        ax.pcolormesh(gx, gy, z, cmap=cmap)
    elif draw == "contourf":
        ax.contourf(gx, gy, z, levels=12, cmap=cmap)
    elif draw == "hexbin":
        ax.hexbin(rng.normal(size=300), rng.normal(size=300), cmap=cmap)
    elif draw == "scatter_c":
        ax.scatter(rng.random(20), rng.random(20), c=rng.random(20), cmap=cmap)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail
    assert cmap in detail, detail


def test_a_figure_with_no_colormapped_artist_says_so_and_passes():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 4])
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True
    assert detail == "no colormapped artists"


def test_an_unmapped_scatter_is_not_gated_against_a_ramp_it_never_used():
    """The trap the guard exists for. EVERY `ScalarMappable` carries a default
    colormap whether or not anything was mapped through it: a plain
    `scatter(x, y, color="#0072b2")` returns viridis from `get_cmap()` and None
    from `get_array()`. Guarding on the colormap instead of the array would
    gate every unmapped scatter in the repository against a ramp it never
    touched. This is the same discrimination `_data_colors_by_axes` already
    makes, in the opposite direction."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    art = ax.scatter([1, 2, 3], [1, 2, 3], color="#0072b2")
    try:
        assert art.get_cmap() is not None, "the trap is still live"
        assert art.get_array() is None, "the trap is still live"
        assert cf.check_colormap(fig) == (True, "no colormapped artists")
    finally:
        plt.close(fig)


def test_a_colorbar_does_not_report_its_parents_colormap_twice():
    """A colorbar axes carries its own QuadMesh, with `get_array()` not None
    and the same colormap attached. Without the `<colorbar>` skip every
    colormap in every figure would be counted twice -- the same reason
    `check_ink` and `check_line_weight` skip that axes."""
    import matplotlib.pyplot as plt
    z = np.add.outer(np.linspace(0, 1, 12), np.linspace(0, 1, 12))
    fig, ax = plt.subplots()
    im = ax.imshow(z, cmap="viridis")
    fig.colorbar(im, ax=ax)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True
    assert detail.count("viridis") == 1, detail


def test_a_qualitative_colormap_that_does_not_separate_fails():
    """Proof the routing reaches `check_palette` rather than stopping at
    classification. matplotlib's default `tab10` puts orange and green at OKLab
    dE 1.4 under protanopia, which is the defect `check_series_color` was
    written for -- and used AS A COLORMAP it slipped past that gate entirely,
    because `_data_colors_by_axes` excludes colormapped artists."""
    fig = heat("tab10")
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is False
    assert "tab10" in detail
    assert "dE" in detail, detail


def test_a_qualitative_colormap_that_does_separate_passes():
    """The Newton-basin case: three categories, three Okabe-Ito slots."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    basins = ListedColormap(["#e69f00", "#56b4e9", "#009e73"], name="basins")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.imshow(rng.integers(0, 3, (20, 20)), cmap=basins)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail
    assert "qualitative" in detail


def test_the_qualitative_route_does_not_apply_the_band_and_chroma_rows():
    """Okabe-Ito contains black and yellow, so all eight levels fail
    `Lightness band`, `Chroma floor` and `Contrast vs surface`. Those rows are
    for a palette someone is CHOOSING, not for colors already drawn -- exactly
    the reason `check_series_color` reads only the separation rows off
    `cp.check`. Applying them here would fail the repository's own palette."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    okabe = ListedColormap(["#e69f00", "#56b4e9", "#009e73", "#f0e442"],
                           name="okabe4")
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots()
    ax.imshow(rng.integers(0, 4, (20, 20)), cmap=okabe)
    try:
        ok, detail = cf.check_colormap(fig)
    finally:
        plt.close(fig)
    assert ok is True, detail


def test_a_heatmap_is_not_gated_twice_under_two_different_rules():
    """Regression on the exclusion this gate was built to complete.
    `_data_colors_by_axes` skips artists with an array attached, so a heatmap's
    colors reach `check_colormap` and nothing else. If that exclusion ever came
    out, one figure would answer to two colour rules with different
    thresholds."""
    fig = heat("viridis")
    try:
        assert cf._data_colors_by_axes(fig) == {}
        assert cf.check_colormap(fig)[0] is True
    finally:
        plt.close(fig)


def test_the_gate_is_a_row_in_audit_between_contour_dash_and_fonts():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    try:
        _, rows = cf.audit(fig)
    finally:
        plt.close(fig)
    names = [n for n, _, _ in rows]
    assert len(names) == 20, names
    assert names[names.index("Contour dash") + 1] == "Colormap kind"
    assert names[names.index("Colormap kind") + 1] == "Fonts"


def test_a_jet_heatmap_fails_the_whole_audit():
    """End to end, and the sentence the spec opens with: a Mandelbrot set
    rendered in jet used to be a PASS."""
    fig = heat("jet")
    try:
        ok, rows = cf.audit(fig)
    finally:
        plt.close(fig)
    assert ok is False
    row = next(r for r in rows if r[0] == "Colormap kind")
    assert row[1] is False, row


def test_the_colormap_row_is_not_advisory():
    """A `jet` colormap is a definite defect with a known correct replacement,
    so it gates rather than warns. The repository's position is that a warning
    nobody reads is worse than no row at all."""
    assert "Colormap kind" not in cf.ADVISORY_GATES
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run rtk pytest tests/test_figure.py -q -k "colormap or rainbow or harvest or colorbar_does_not or qualitative"
```

Expected: FAIL, with `AttributeError: module 'check_figure' has no attribute 'check_colormap'`

- [ ] **Step 3: Write the implementation**

In `skill/scripts/check_figure.py`, insert this function immediately before `def check_fonts(fig):` (line 1633):

```python
def check_colormap(fig):
    """Every colormap the figure actually uses, classified and routed.

    The hole this closes. Every other gate in this file reads artists that
    carry an IDENTITY: a line's color, a bar's face, a scatter's marks. A
    figure whose entire content is one colormapped image has no such artist, so
    it passed all nineteen checks by having nothing they knew how to read. A
    Mandelbrot set rendered in `jet` was a PASS.

    This is not an oversight that went unnoticed. `_data_colors_by_axes` above
    already excludes colormapped artists, with a comment saying they answer to
    "the viridis rule instead". No such rule was implemented. This is it, and
    the two exclusions are now complements: a colormapped artist is read here
    and nowhere else, so no figure answers to two colour rules at once.

    A ROUTER, not a new body of checking. The classification is
    `check_palette.cmap_kind`; the separation gate a qualitative map goes
    through is the same `check_palette.check` that `check_series_color` uses.

      misc         -> FAIL. jet, hsv, rainbow, the gist_* maps. A reader cannot
                      order two values in one of these, which is the entire job
                      a colormap has.
      qualitative  -> the separation rows of `check_palette.check`, all-pairs.
                      An image puts every category next to every other, so
                      adjacent-only separation is not enough.
      sequential   -> pass. `cmap_kind` already proved monotone lightness.
      diverging    -> pass. Monotone per half, which is the contract this
                      family signs; end-to-end monotonicity is not.
      cyclic       -> pass, same.

    WHY NOT `check(ordinal=True)` FOR SEQUENTIAL. That gate's `Light-end
    contrast` row requires the lightest step to clear 2.0:1 against the
    surface, which viridis (1.26:1), cividis (1.25:1), magma (1.05:1) and Blues
    (1.04:1) all fail -- every canonical scientific ramp. The row is right for
    what it was written for, a discrete ramp of swatches on a white page where
    the lightest swatch must be tellable from the page. A continuous colormap's
    light end sits against its own neighbouring values instead. Its
    `Adjacent dL` row is likewise a function of how many samples the caller
    took rather than a property of the colormap.

    The consequence, stated rather than hidden: this gate says nothing about a
    sequential map whose lightness span is too narrow to carry an ordinal
    reading. That needs a span floor measured across the registry, and it is
    the same open question as the Wistia disagreement in
    `tests/test_palette_oracle.py`. The row is named "Colormap kind" and not
    "Colormap quality" for this reason and for turbo's.
    """
    try:
        import check_palette as cp
    except ImportError:
        return True, ("check_palette.py is not importable beside this file, "
                      "so no colormap was classified")

    from matplotlib.colors import to_hex

    seen = {}
    for ax in fig.axes:
        # A colorbar axes carries its own QuadMesh, with an array attached and
        # the parent's colormap on it. Without this skip every colormap would
        # be counted twice. Same reason `check_ink` and `check_line_weight`
        # skip this axes.
        if ax.get_label() == "<colorbar>":
            continue
        for artist in list(ax.images) + list(ax.collections):
            if not artist.get_visible():
                continue
            # THE GUARD IS THE ARRAY, NEVER THE COLORMAP. Every ScalarMappable
            # carries a default colormap whether or not anything was mapped
            # through it -- a plain `scatter(x, y, color="#0072b2")` returns
            # viridis from get_cmap() and None from get_array(). Testing the
            # colormap would gate every unmapped scatter against a ramp it
            # never used.
            if getattr(artist, "get_array", lambda: None)() is None:
                continue
            cmap = getattr(artist, "get_cmap", lambda: None)()
            if cmap is not None:
                seen.setdefault(getattr(cmap, "name", "unnamed"), cmap)

    if not seen:
        return True, "no colormapped artists"

    fails, notes = [], []
    for name, cmap in sorted(seen.items()):
        # The sample count is `cmap_kind`'s contract, not a detail: it decides
        # qualitative by counting what it is handed, so always taking 256 would
        # mean never producing one.
        if cmap.N < cp.CMAP_QUALITATIVE_N:
            levels = [to_hex(cmap(i)) for i in range(cmap.N)]
        else:
            levels = [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
                      for i in range(cp.CMAP_SAMPLES)]

        kind = cp.cmap_kind(levels)

        if kind == "misc":
            fails.append(
                f"{name}: lightness reverses over "
                f"{cp.cmap_back_travel(levels):.0%} of its span  <- a reader "
                "cannot order two values in it. viridis for sequential, RdBu "
                "for diverging, twilight for cyclic")
            continue

        if kind == "qualitative":
            # Only the separation rows, exactly as `check_series_color` does at
            # the top of this file. The lightness-band and chroma-floor rows
            # are for a palette someone is CHOOSING; these colors are already
            # drawn, and a black or gray category is legal. Applying them here
            # would fail Okabe-Ito, which this repository ships.
            rows, _ = cp.check(levels, all_pairs=True)
            bad = [detail.split("  <-")[0].strip()
                   for row_name, status, detail in rows
                   if row_name.startswith(("CVD separation",
                                           "Normal-vision floor"))
                   and status is False]
            if bad:
                fails.append(f"{name} ({cmap.N} categories): " + "; ".join(bad)
                             + "  <- an image puts every category beside every "
                             "other, so every pair has to separate")
                continue

        notes.append(f"{name} {kind}")

    if fails:
        return False, "; ".join(fails)
    return True, ", ".join(notes)
```

- [ ] **Step 4: Add the row to `audit`**

In `skill/scripts/check_figure.py`, in the `rows = [` list inside `audit` (line 1871), insert one line between the `Contour dash` entry and the `Fonts` entry:

```python
        ("Contour dash", *check_contour_dash(fig)),
        ("Colormap kind", *check_colormap(fig)),
        ("Fonts", *check_fonts(fig)),
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run rtk pytest tests/test_figure.py -q
```

Expected: all pass. `tests/test_docs_match_code.py` will now fail — that is Task 4.

- [ ] **Step 6: Amend the spec to match what shipped**

In `specs/2026-07-28-colormap-kind-gate-design.md`, replace the three bullets under "3. **Route to the check that kind already has.**" with:

```markdown
3. **Route to the check that kind already has.**
   - qualitative -> `check_palette.check(levels, all_pairs=True)`, read for its
     `CVD separation` and `Normal-vision floor` rows only, exactly as
     `check_series_color` reads it at `check_figure.py:1209`. The lightness-band
     and chroma-floor rows are for a palette being chosen, not for colors
     already drawn; applied here they fail Okabe-Ito, which this repository
     ships.
   - sequential, diverging, cyclic -> pass on the kind. `cmap_kind` has already
     proved monotone lightness, whole-map or per half.
   - misc -> FAIL, naming the colormap and its back-travel

   **Not `check(ordinal=True)`, and this was measured rather than assumed.**
   That gate's `Light-end contrast` row requires the lightest step to clear
   2.0:1 against the surface, which viridis (1.26:1), cividis (1.25:1), magma
   (1.05:1) and Blues (1.04:1) all fail. The row is correct for a discrete ramp
   of swatches on a white page; a continuous colormap's light end sits against
   its own neighbouring values instead. Its `Adjacent dL` row is a function of
   the caller's sample count, not of the colormap: Blues passes it at 5 and 7
   samples and fails at 9. Routing sequential maps there would have failed
   `gallery-field.png`, which this repository already ships.
```

Then add this bullet to the **Limits, stated on purpose** section, after the turbo paragraph:

```markdown
**A narrow-span sequential map passes.** Because sequential now passes on kind
alone, nothing gates a ramp whose lightness moves too little to be read as an
order. This is the same open question as the Wistia disagreement above and
takes the same fix: a lightness-span floor measured across the registry. It is
deferred with the reason written down rather than resolved with a guessed
constant.
```

- [ ] **Step 7: Commit**

```bash
rtk git add skill/scripts/check_figure.py tests/test_figure.py specs/2026-07-28-colormap-kind-gate-design.md && rtk git commit -m "feat: gate the colormaps a figure actually uses"
```

---

## Task 4: the roster ripple, 19 gates to 20

**Goal:** Every place that names the gates names the new one, so the suite goes green again.

**Files:**
- Modify: `skill/scripts/check_figure.py:19-40` — the module docstring's numbered list
- Modify: `README.md:70` (the count), `README.md:45` (the prose), and the gate table around `README.md:73-93`
- Modify: `skill/SKILL.md:206-212` — the prose roster
- Modify: `tests/test_docs_match_code.py:536-556` — `FIGURE_PROSE`

**Acceptance Criteria:**
- [ ] The docstring list has 20 numbered entries, `Colormap kind` at 18, `Fonts` at 19, `Alt text` at 20
- [ ] The README gate table has a `Colormap kind` row between `Contour dash` and `Fonts`
- [ ] `README.md:70` says "these 20 rows"
- [ ] `README.md:45` says "row 11 of the 20"
- [ ] `SKILL.md`'s roster sentence includes "colormap kind" between "contour dash" and "font embedding"
- [ ] `FIGURE_PROSE` has a `"Colormap kind"` key
- [ ] `ADVISORY_GATES` is unchanged — the new gate is not advisory, so the advisory map at `test_docs_match_code.py:354` needs no edit

**Verify:** `uv run rtk pytest tests/test_docs_match_code.py -q` → all pass except the test-count test, which Task 6 fixes

**Steps:**

- [ ] **Step 1: The module docstring**

In `skill/scripts/check_figure.py`, replace lines 37-39:

```
   17. Contour dash      - dashing is not spent on a signed contour's negatives
   18. Fonts             - Type 42 embedding; the named face is installed
   19. Alt text          - the figure carries a description
```

with:

```
   17. Contour dash      - dashing is not spent on a signed contour's negatives
   18. Colormap kind     - the colormaps in use are ones a reader can order
   19. Fonts             - Type 42 embedding; the named face is installed
   20. Alt text          - the figure carries a description
```

- [ ] **Step 2: The README table and its two counts**

In `README.md`, on line 70 change `returns these 19 rows in` to `returns these 20 rows in`.

In the gate table, insert this row between the `Contour dash` row and the `Fonts` row:

```markdown
| Colormap kind | `CMAP_BACKTRAVEL_MAX = 0.02` | a colormap's lightness reverses, or a qualitative one's levels fail all-pairs separation |
```

On line 45, change `That is row 11 of the 19.` to `That is row 11 of the 20.`

- [ ] **Step 3: The SKILL.md prose roster**

In `skill/SKILL.md`, in the paragraph at line 206, change:

```
attribution, whether the style sheet is the one actually in effect, contour
dash, font embedding, and alt text — in that order.
```

to:

```
attribution, whether the style sheet is the one actually in effect, contour
dash, colormap kind, font embedding, and alt text — in that order.
```

- [ ] **Step 4: The prose map in the test**

In `tests/test_docs_match_code.py`, in `FIGURE_PROSE`, insert one entry between `"Contour dash"` and `"Fonts"`:

```python
    "Contour dash": "contour dash",
    "Colormap kind": "colormap kind",
    "Fonts": "font embedding",
```

- [ ] **Step 5: Run the roster tests**

```bash
uv run rtk pytest tests/test_docs_match_code.py -q -k "roster or docstring or readme_table or prose"
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
rtk git add skill/scripts/check_figure.py README.md skill/SKILL.md tests/test_docs_match_code.py && rtk git commit -m "docs: name the twentieth gate in all four rosters"
```

---

## Task 5: `gallery-encoding.png`, the seventh gallery figure

**Goal:** One figure whose three panels each carry an encoding the other two cannot, put through the same audit as every other gallery figure.

**Files:**
- Modify: `examples/gallery.py` — new `encoding()` function, added to the build list at line 467; docstring updated
- Modify: `tests/test_example.py:53-62` — count 6 to 7, docstring
- Modify: `docs/gallery.md` — "these six" to "these seven", plus a section for the new figure

**Acceptance Criteria:**
- [ ] `python examples/gallery.py` exits 0 and prints `PASS  gallery-encoding.png`
- [ ] Left panel is a Mandelbrot escape-time image in viridis, classified sequential
- [ ] The set's interior is drawn in an explicit neutral, NOT `cmap(0)`
- [ ] Centre panel is Newton basins for `z^3 - 1` in a 3-entry `ListedColormap`, classified qualitative
- [ ] Right panel is a phase portrait in twilight, classified cyclic
- [ ] `test_the_gallery_runs_and_every_figure_passes` asserts a count of 7
- [ ] No gate was weakened to make the figure pass

**Verify:** `uv run python examples/gallery.py` → exits 0, `PASS  gallery-encoding.png` in output

**Steps:**

- [ ] **Step 1: Write the figure**

In `examples/gallery.py`, insert this before the build list at line 467:

```python
# --- 7. three encodings, three colormap kinds --------------------------------
# The figure the colormap gate exists for, and the one place in this repository
# where all three continuous kinds appear side by side. Each panel is an
# encoding the other two cannot carry: escape time is a QUANTITY and takes a
# sequential ramp; a basin is a CATEGORY and takes separated hues; a phase is
# an ANGLE, so its colormap has to close the loop or there is a false seam at
# the branch cut where -pi meets pi.
#
# It is also the hardest composition in the gallery on purpose -- three dense
# full-bleed images in one row. Per the docstring above, these figures exist to
# find defects in the checks, and the ones with somewhere to hide here are text
# readability over a busy backdrop and `check_ink` on three saturated panels at
# once.

def encoding():
    # The interior of the Mandelbrot set is not a small escape time, it is a
    # SEPARATE CLASS: "did not escape in the budget". Drawing it as cmap(0)
    # would claim a quantity that was never measured, and would put it at the
    # dark end of a ramp where a reader reads it as "escaped slowly". A masked
    # value in an explicit neutral says what it is.
    UNMEASURED = "#d9d7d2"

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.6, 2.9),
                                  constrained_layout=True)

    # (a) escape time -- a quantity, so a sequential ramp.
    n = 400
    budget = 60
    ax_x = np.linspace(-2.05, 0.65, n)
    ax_y = np.linspace(-1.25, 1.25, n)
    cc = ax_x[None, :] + 1j * ax_y[:, None]
    z = np.zeros_like(cc)
    escape = np.full(cc.shape, np.nan)
    for k in range(budget):
        z = z * z + cc
        # Freeze escaped points rather than letting them run: |z| squares each
        # step, so by iteration 60 an escaped point overflows to inf and the
        # whole array fills with warnings.
        out = np.abs(z) > 2.0
        escape[out & np.isnan(escape)] = k
        z[out] = 2.0
    ramp = plt.get_cmap("viridis").with_extremes(bad=UNMEASURED)
    a.imshow(np.ma.masked_invalid(escape), cmap=ramp, origin="lower",
             extent=(ax_x[0], ax_x[-1], ax_y[0], ax_y[-1]),
             interpolation="nearest", aspect="auto")
    a.set_title("(a) quantity: sequential", loc="left")
    a.set_xlabel(r"$\Re c$")
    a.set_ylabel(r"$\Im c$")

    # (b) Newton basins -- a category, so separated hues and no ramp at all.
    # Three roots of z^3 - 1, three Okabe-Ito slots. Nothing orders these: the
    # basins are not more or less of anything.
    bx = np.linspace(-1.4, 1.4, n)
    by = np.linspace(-1.4, 1.4, n)
    w = bx[None, :] + 1j * by[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        for _ in range(40):
            w = w - (w ** 3 - 1) / (3 * w ** 2)
    roots = np.array([1.0 + 0j,
                      -0.5 + 0.8660254037844386j,
                      -0.5 - 0.8660254037844386j])
    basin = np.argmin(np.abs(w[..., None] - roots[None, None, :]), axis=-1)
    from matplotlib.colors import ListedColormap
    basins = ListedColormap(list(SERIES[:3]), name="newton-basins")
    b.imshow(basin, cmap=basins, origin="lower",
             extent=(bx[0], bx[-1], by[0], by[-1]),
             interpolation="nearest", aspect="auto")
    b.set_title("(b) category: qualitative", loc="left")
    b.set_xlabel(r"$\Re z_0$")
    b.set_ylabel(r"$\Im z_0$")

    # (c) phase -- an angle, so a cyclic map. twilight closes the loop AND
    # holds its lightness, which is the pair of properties hsv has only half
    # of: hsv wraps and swings lightness wildly within every hue, so it prints
    # false bands that a reader takes for structure in the function.
    px = np.linspace(-2.0, 2.0, n)
    py = np.linspace(-2.0, 2.0, n)
    v = px[None, :] + 1j * py[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        f = (v ** 2 - 1.0) / (v ** 2 + 0.5j)
    c.imshow(np.angle(f), cmap="twilight", origin="lower",
             vmin=-np.pi, vmax=np.pi,
             extent=(px[0], px[-1], py[0], py[-1]),
             interpolation="nearest", aspect="auto")
    c.set_title("(c) angle: cyclic", loc="left")
    c.set_xlabel(r"$\Re z$")
    c.set_ylabel(r"$\Im z$")

    # All three panels are full-bleed fields, so all three are context rather
    # than data ink -- the same declaration `field()` makes for its contourf
    # backdrop, and for the same reason.
    finish(fig, "gallery-encoding",
           "Three complex-plane images, each on a colormap matched to what it "
           "encodes. (a) Mandelbrot escape time in viridis, a sequential ramp, "
           "with the set's interior in a neutral because it did not escape "
           "rather than escaping slowly. (b) Newton basins for z^3 - 1 in "
           "three separated hues, because a basin is a category and nothing "
           "orders them. (c) The phase of (z^2 - 1)/(z^2 + i/2) in twilight, a "
           "cyclic map, so there is no false seam where the angle wraps.",
           context_axes=[a, b, c])
```

Then change the build list on line 467 from:

```python
for build in (small_multiples, field, schematic, forms, convergence, orbit):
```

to:

```python
for build in (small_multiples, field, schematic, forms, convergence, orbit,
              encoding):
```

- [ ] **Step 2: Update the gallery docstring**

In `examples/gallery.py`, change line 1 from `"""Six figures hard enough to be worth checking.` to `"""Seven figures hard enough to be worth checking.` and add one line to the file list after the `gallery-orbit.png` line:

```
    gallery-encoding.png          three colormap kinds, one per panel
```

- [ ] **Step 3: Run it and read every row**

```bash
uv run python examples/gallery.py
```

Expected on the first run: `gallery-encoding` may FAIL. **This is anticipated and is the one open risk the design named.** Work the failing rows with this table, and note the standing rule — a gate is never weakened to make a figure pass:

| failing row | what to do |
| --- | --- |
| `Colormap kind` | A real defect in the figure. Check the panel actually got the colormap intended. |
| `Ink coverage` | Advisory, cannot fail the build. If it WARNs, confirm all three axes are in `context_axes`. |
| `Text readability` | Real. Move the offending string off the image — into the panel title or an axis label. Do not add a halo: over a field a halo does not sit behind the label, it deletes the field under it (see `field()`'s comment). |
| `Axis redundancy` | The three panels have different domains and must not share scales. If this fires, `sharex`/`sharey` got set somewhere. |
| `Type size` | The figure is too small for three panels. Widen `figsize`; do not shrink the type. |
| `Clipping` / `Text collision` | Composition. Shorten a title or widen the figure. |
| `Contrast stack` | Something is semi-transparent. Nothing here should be — remove the alpha. |

If a row fails in a way none of the above covers, that is a finding: it is either a real composition limit worth writing into the figure's comment block, or a defect in a gate. Both are outcomes this gallery exists to produce. Report it rather than working around it.

- [ ] **Step 4: Look at the PNG**

```bash
open examples/gallery-encoding.png
```

Step 7 of the procedure, and it is in the procedure because two of this gallery's defects were invisible to every check and obvious in the image. Confirm: the Mandelbrot interior is a flat neutral and not dark blue; the three basins meet at visible boundaries; the phase portrait has no hard seam running across it.

- [ ] **Step 5: Update the gallery test**

In `tests/test_example.py`, replace the body of `test_the_gallery_runs_and_every_figure_passes` (lines 53-62):

```python
def test_the_gallery_runs_and_every_figure_passes():
    """The harder half of the evidence. `demo.py` is one panel and three
    curves; a gate that only ever runs on that has not been tried. These seven
    put a shared-axis grid, a filled field with a colorbar, an axis-free
    schematic, three statistical forms, a log-log convergence plot, a dense
    attractor and three colormapped complex-plane images through the same
    audit."""
    result = subprocess.run([sys.executable, str(GALLERY)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert result.stdout.count("PASS  gallery-") == 7, result.stdout[-4000:]
```

- [ ] **Step 6: Run the test**

```bash
uv run rtk pytest tests/test_example.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
rtk git add examples/gallery.py examples/gallery-encoding.png tests/test_example.py && rtk git commit -m "feat: add gallery-encoding, three colormap kinds in one figure"
```

---

## Task 6: reconcile the counts the docs state in prose

**Goal:** Every number this repository states in prose about itself is true again.

**Files:**
- Modify: `docs/gallery.md` — "these six" to "these seven", plus a section for the new figure
- Modify: `README.md:281` — the test count

**Acceptance Criteria:**
- [ ] `docs/gallery.md` says "these seven" and carries a section for `gallery-encoding.png`
- [ ] The new section's alt text is byte-identical to the string `encoding()` passes to `finish`
- [ ] `README.md`'s "The suite is N tests" is the number `pytest --collect-only` reports
- [ ] The defect count stays at six in all three files, unless building the figure in Task 5 found a genuinely new defect in a gate — in which case all three move together
- [ ] The whole suite is green

**Verify:** `uv run rtk pytest tests/ -n auto -q` → 0 failures

**Steps:**

- [ ] **Step 1: `docs/gallery.md`**

On line 3, change `builds these six and audits each one` to `builds these seven and audits each one`.

Append a section at the end of the file, in the same shape as the others. **The alt text inside `![...]` must be the exact string `encoding()` passes to `finish`** — `tests/test_docs_render.py` and the alt-text discipline in this repository both depend on the page's alt text being the string the figure itself carries:

```markdown
## Three encodings

<figure markdown="span">
  ![Three complex-plane images, each on a colormap matched to what it encodes. (a) Mandelbrot escape time in viridis, a sequential ramp, with the set's interior in a neutral because it did not escape rather than escaping slowly. (b) Newton basins for z^3 - 1 in three separated hues, because a basin is a category and nothing orders them. (c) The phase of (z^2 - 1)/(z^2 + i/2) in twilight, a cyclic map, so there is no false seam where the angle wraps.](images/gallery-encoding.png)
  <figcaption>The figure the colormap gate exists for. Escape time is a quantity and takes a sequential ramp; a Newton basin is a category and takes separated hues; a phase is an angle, so its colormap has to close the loop or a false seam appears where it wraps. The interior of the Mandelbrot set is drawn in a neutral rather than at the bottom of the ramp, because "did not escape" is a separate class and not a small value.</figcaption>
</figure>
```

- [ ] **Step 2: Copy the image where the docs site reads it from**

```bash
ls docs/images/gallery-*.png
```

If `docs/images/` holds real copies, copy the new one in the same way the others got there. If they are symlinks, make a symlink to match — `tests/test_docs_site.py` distinguishes the two.

```bash
cp examples/gallery-encoding.png docs/images/gallery-encoding.png
```

- [ ] **Step 3: Get the real test count**

```bash
uv run python -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -3
```

Expected: a line reading `N tests collected`. Take that N.

- [ ] **Step 4: Write it into the README**

In `README.md` line 281, change `The suite is 356 tests` to `The suite is N tests`, using the N from Step 3. `docs/index.md` is a symlink to `README.md` and needs no separate edit — confirm with:

```bash
ls -l docs/index.md
```

- [ ] **Step 5: Run the whole suite**

```bash
uv run rtk pytest tests/ -n auto -q
```

Expected: 0 failures.

If `test_the_three_sources_agree_on_the_defect_count` fails, Task 5 changed a defect count somewhere. The number lives in `examples/gallery.py`, `README.md` and `docs/gallery.md`, and all three must say the same word. `gallery.py` enumerates its defects by name, so it is the one to trust.

- [ ] **Step 6: Commit**

```bash
rtk git add docs/ README.md && rtk git commit -m "docs: seven gallery figures, and the test count that goes with them"
```

---

## Self-review

**Spec coverage.** Every section of `specs/2026-07-28-colormap-kind-gate-design.md` maps to a task: "The classifier" and its thresholds to Task 1; "Dependencies" and the differential to Task 2; "The gate row" to Task 3; "The roster ripple" to Task 4; "The gallery figure" to Task 5; the `test_example.py` count to Task 5 and the doc counts to Task 6. The spec's routing step 3 is the one place the plan departs from the spec, and Task 3 Step 6 amends the spec rather than leaving the two disagreeing.

**Naming consistency across tasks.** `cmap_kind`, `cmap_back_travel`, `_back_travel`, `CMAP_SAMPLES`, `CMAP_QUALITATIVE_N`, `CMAP_SPAN_MIN`, `CMAP_BACKTRAVEL_MAX`, `CMAP_WRAP_DE_MAX` are defined in Task 1 and used with those exact names in Tasks 2 and 3. The gate is `check_colormap` and its row label is `"Colormap kind"` in Tasks 3 and 4.

**What was verified before this plan was written**, on matplotlib 3.11.1 and cmasher 1.9.2, rather than reasoned about: all 23 colormap classifications in Task 1's table; the 0.019/0.021 boundary construction; every harvest path in Task 3; the colorbar double-count; the `get_cmap()`-versus-`get_array()` trap; the Okabe-Ito and tab10 routing outcomes; and the two `check(ordinal=True)` failures that forced the spec amendment.

**Still open, and named rather than hidden:** whether three dense panels clear the existing gates. Task 5 Step 3 gives the decision table for working the failures and states the rule that no gate is weakened to pass a figure.
