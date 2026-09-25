"""Gates for check_palette.py.

Two jobs here. The obvious one is that good palettes pass and bad ones fail. The
less obvious one is that the *numbers quoted in the documentation* stay true:
the guide makes specific claims (adjacent CVD dE 16.6, orange and sky blue
differing by dL 0.011) and a reader who cannot trust those has no reason to
trust anything else in it. Pinning them here means a change to the color math
breaks a test instead of quietly making the prose wrong.
"""

import math
import random
import re

import pytest

import check_palette as cp

OKABE_ITO = ["#000000", "#E69F00", "#56B4E9", "#009E73",
             "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
SERIES = [OKABE_ITO[i] for i in (1, 2, 3, 5, 6, 7)]


def gates(rows):
    return {name: status for name, status, _ in rows}


# --- the palette the guide actually recommends ------------------------------

def test_series_pairs_pass_adjacent():
    ok, rows = cp.check(SERIES[:2])
    assert ok, rows


def test_first_four_pass_all_pairs():
    """Scatter and small multiples compare every series against every other.
    The guide says only the first four slots clear that, so it had better."""
    ok, rows = cp.check(SERIES[:4], all_pairs=True)
    assert ok, rows


def test_okabe_ito_matches_matplotlib_builtin():
    """matplotlib ships this palette as of 3.11. If the hexes here ever drift
    from the builtin, the guide is teaching a private fork of a standard set."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    if "okabe_ito" not in colormaps:
        pytest.skip("matplotlib < 3.11 has no okabe_ito colormap")
    from matplotlib.colors import to_hex
    builtin = [to_hex(colormaps["okabe_ito"](i)) for i in range(8)]
    assert builtin == [c.lower() for c in OKABE_ITO]


# --- documented measurements ------------------------------------------------

def test_adjacent_cvd_separation_matches_documented_value():
    lin = [cp.hex_to_linear(c) for c in SERIES]
    worst = min(
        cp.delta_e(cp.simulate(lin[i], k), cp.simulate(lin[i + 1], k))
        for i in range(len(lin) - 1) for k in ("protan", "deutan"))
    assert worst == pytest.approx(32.0, abs=0.1)


def test_orange_and_sky_blue_are_the_worst_grayscale_pair():
    """The guide's sharpest counterintuitive claim: the canonical *first two*
    slots are the pair that vanishes in grayscale. Taking slots in order buys
    colorblind safety, not photocopier safety."""
    def lum(h):
        return cp.relative_luminance(cp.hex_to_linear(h))

    gaps = {(a, b): abs(lum(a) - lum(b))
            for i, a in enumerate(SERIES) for b in SERIES[i + 1:]}
    worst_pair = min(gaps, key=gaps.get)
    assert worst_pair == ("#E69F00", "#56B4E9")
    assert gaps[worst_pair] == pytest.approx(0.011, abs=0.001)
    assert abs(lum("#E69F00") - lum("#0072B2")) == pytest.approx(0.264, abs=0.001)


def test_contrast_matches_wcag_reference_values():
    assert cp.contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert cp.contrast("#ffffff", "#ffffff") == pytest.approx(1.0, abs=0.01)
    assert cp.contrast("#F0E442", "#ffffff") == pytest.approx(1.32, abs=0.01)


# --- each gate fails on something ------------------------------------------
# A gate that has never been observed to fail is decoration. Each of these
# targets one gate and asserts that specific gate is what caught it.

def test_lightness_band_rejects_a_color_that_is_too_light():
    ok, rows = cp.check(["#F0E442", "#0072B2"])
    assert not ok
    assert gates(rows)["Lightness band"] is False


def test_chroma_floor_rejects_gray():
    ok, rows = cp.check(["#808080", "#0072B2"])
    assert not ok
    assert gates(rows)["Chroma floor"] is False


def test_normal_vision_floor_rejects_two_near_identical_hues():
    ok, rows = cp.check(["#0072B2", "#0d76b5"])
    assert not ok
    assert gates(rows)["Normal-vision floor (adjacent)"] is False


def test_cvd_gate_rejects_a_red_green_pair_that_looks_fine_in_color():
    """The failure mode the whole validator exists for: a pair that is obvious
    to normal vision and collapses under protanopia."""
    a, b = "#c1272d", "#5a8f29"
    normal = cp.delta_e(cp.hex_to_linear(a), cp.hex_to_linear(b))
    assert normal >= cp.NORMAL_FLOOR, "should be clearly distinct in full color"
    ok, rows = cp.check([a, b])
    assert not ok
    assert gates(rows)["CVD separation (adjacent)"] is False


def test_low_contrast_warns_rather_than_fails():
    """Sub-3:1 is legal if it carries a direct label. Reporting it as FAIL while
    the run still passes would read as a contradiction, so it warns."""
    ok, rows = cp.check(["#E69F00", "#0072B2"])
    assert ok
    assert gates(rows)["Contrast vs surface"] == "warn"


# --- ordinal ramps ----------------------------------------------------------

def viridis_window(n, lo=0.05, hi=0.70):
    colormaps = pytest.importorskip("matplotlib").colormaps
    from matplotlib.colors import to_hex
    vir = colormaps["viridis"]
    return [to_hex(vir(lo + (hi - lo) * i / (n - 1))) for i in range(n)]


@pytest.mark.parametrize("n", [3, 4, 5])
def test_windowed_viridis_passes_ordinal_gates(n):
    ok, rows = cp.check(viridis_window(n), ordinal=True)
    assert ok, rows


def test_full_range_viridis_fails_light_end_contrast():
    """The reason discrete tiers get windowed at all: viridis finishes at
    #fde725, which is invisible as a hairline on a light page."""
    ok, rows = cp.check(viridis_window(4, 0.0, 1.0), ordinal=True)
    assert not ok
    assert gates(rows)["Light-end contrast"] is False


def test_jet_fails_lightness_monotone():
    """The guide replaced a 'single hue' gate with monotone lightness plus even
    steps, and claims jet still fails on the honest reason it was always
    unreadable. This is that claim, as a test."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    from matplotlib.colors import to_hex
    jet = [to_hex(colormaps["jet"](i / 5)) for i in range(6)]
    ok, rows = cp.check(jet, ordinal=True)
    assert not ok
    assert gates(rows)["Lightness monotone"] is False


def test_uneven_steps_fail_even_when_monotone():
    """A ramp can descend in lightness the whole way and still read as having a
    boundary in it, because one step is much larger than the rest."""
    ok, rows = cp.check(["#f7f7f7", "#eaeaea", "#dddddd", "#111111"],
                        ordinal=True)
    assert not ok
    assert gates(rows)["Step uniformity"] is False


# --- ink flag ---------------------------------------------------------------


def test_palette_ink_exempts_from_chroma_floor():
    ok, rows = cp.check(["#0072B2", "#52514e"], ink={"#52514e"})
    assert gates(rows)["Chroma floor"] is True


def test_palette_ink_exempts_from_lightness_band():
    ok, rows = cp.check(["#0072B2", "#ffffff"], ink={"#ffffff"})
    assert gates(rows)["Lightness band"] is True


def test_palette_without_ink_still_fails_chroma_floor():
    ok, rows = cp.check(["#0072B2", "#52514e"])
    assert gates(rows)["Chroma floor"] is False


def test_palette_separation_rows_unchanged_by_ink_flag():
    ok_with, rows_with = cp.check(["#0072B2", "#52514e", "#009E73"],
                                  ink={"#52514e"})
    ok_without, rows_without = cp.check(["#0072B2", "#52514e", "#009E73"])
    for name in ("CVD separation (adjacent)", "Normal-vision floor (adjacent)",
                 "Contrast vs surface"):
        assert gates(rows_with)[name] == gates(rows_without)[name], name


# --- CLI --------------------------------------------------------------------

def test_cli_exit_codes(tmp_path):
    """Non-zero on failure is what makes this usable in a build."""
    import subprocess
    import sys
    script = str(__import__("pathlib").Path(cp.__file__))
    good = subprocess.run([sys.executable, script, ",".join(SERIES[:2])],
                          capture_output=True)
    bad = subprocess.run([sys.executable, script, "#808080,#0072B2"],
                         capture_output=True)
    assert good.returncode == 0
    assert bad.returncode == 1


def test_cli_json_exits_the_same_way_the_table_does(tmp_path):
    """`--json` changes what is printed, not what is decided.

    The flag exists so a build can read the rows. A build that already branches
    on `$?` must keep working, and a flag that quietly made a failing palette
    exit 0 would turn every such build green at once.
    """
    import json
    import subprocess
    import sys
    script = str(__import__("pathlib").Path(cp.__file__))
    for colors, expected in ((",".join(SERIES[:2]), 0), ("#808080,#0072B2", 1)):
        run = subprocess.run([sys.executable, script, colors, "--json"],
                             capture_output=True, text=True)
        assert run.returncode == expected, colors
        document = json.loads(run.stdout)
        assert document["ok"] is (expected == 0)


def test_cli_json_prints_the_document_and_nothing_else():
    """stdout is the document, parseable without stripping a table off it.

    `json.loads` on the whole of stdout is the assertion: a stray heading, a
    trailing verdict line, or the table printed alongside would all raise here.
    The table is for a person and this is for a machine, and a stream carrying
    both is neither.
    """
    import json
    import subprocess
    import sys
    script = str(__import__("pathlib").Path(cp.__file__))
    run = subprocess.run([sys.executable, script, ",".join(SERIES), "--json"],
                         capture_output=True, text=True)
    document = json.loads(run.stdout)
    assert "PASS" not in run.stdout and "->" not in run.stdout
    assert document["tool"] == "check_palette"


# --- the JSON document ------------------------------------------------------

def test_check_json_reports_the_verdict_check_reported():
    """The serialiser serialises. It does not re-gate.

    Every row `check` returned, in order, with the same verdict. A document that
    disagreed with the tuple API would make the two routes two answers, which is
    the defect `check` and `audit` were made to return the same shape to avoid.
    """
    import json
    ok, rows = cp.check(SERIES, all_pairs=True)
    document = json.loads(cp.check_json(SERIES, all_pairs=True))
    assert document["ok"] is ok
    assert [row["name"] for row in document["rows"]] == [n for n, _, _ in rows]
    assert [row["detail"] for row in document["rows"]] == [d for _, _, d in rows]


def test_check_json_spells_the_three_statuses_out():
    """`pass`, `fail` and `warn`, never `True` or `False`.

    A JSON consumer should not have to know that one field holds a bool for two
    of the three cases and a string for the third. The mapping is asserted
    against a palette chosen to produce all three at once: gray fails the chroma
    floor, and the Okabe-Ito oranges warn on contrast against white.
    """
    import json
    colors = ["#808080", "#E69F00", "#56B4E9"]
    ok, rows = cp.check(colors)
    document = json.loads(cp.check_json(colors))
    assert {row["status"] for row in document["rows"]} == {"pass", "fail", "warn"}
    for row, (_, status, _) in zip(document["rows"], rows):
        assert row["status"] == {True: "pass", False: "fail", "warn": "warn"}[status]


def test_check_json_records_the_inputs_that_produced_the_verdict():
    """A verdict without its surface and its mode cannot be read back.

    The same hexes pass on white and fail on a tinted page, and are gated by
    different rows as a ramp than as a categorical set. An artifact that stored
    only `ok` would be a number nobody can reproduce, which is the whole reason
    the inputs are in the document rather than in the caller's memory.
    """
    import json
    document = json.loads(cp.check_json(
        SERIES, surface="#eeeeee", all_pairs=True, ordinal=False,
        ink=["#52514e", "#000000"]))
    assert document["inputs"] == {
        "colors": list(SERIES),
        "surface": "#eeeeee",
        "pairs": "all",
        "ordinal": False,
        # Sorted, so two runs that passed the same set in two orders produce the
        # same bytes.
        "ink": ["#000000", "#52514e"],
    }


def test_check_json_is_stable_across_ink_ordering():
    """Two callers passing the same ink in two orders get identical bytes.

    `ink` is a set in the signature, so the order it arrived in is not
    information. Left unsorted it would land in the document anyway, and two
    identical runs would produce two files that diff.
    """
    first = cp.check_json(SERIES, ink=["#000000", "#52514e"])
    second = cp.check_json(SERIES, ink=["#52514e", "#000000"])
    assert first == second


def test_the_two_checkers_agree_on_the_schema():
    """`AUDIT_SCHEMA` is written out in both modules, and must be one string.

    Not imported from one into the other: `check_palette.py` is vendored on its
    own and imports nothing outside the standard library, so the constant is
    duplicated on purpose. A duplicated constant is one that can drift, and a
    consumer pinning the schema would then accept one checker's document and
    reject the other's.
    """
    cf = pytest.importorskip("check_figure")
    assert cp.AUDIT_SCHEMA == cf.AUDIT_SCHEMA


# --- colormap kind -----------------------------------------------------------

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
    "turbo": "diverging",
    "rainbow": "misc",
    "jet": "misc",
    "hsv": "misc",
    "brg": "misc",
    "nipy_spectral": "misc",
    "gist_ncar": "misc",
    "Wistia": "misc",
    "tab10": "qualitative",
    "Set1": "qualitative",
}


def cmap_samples(name):
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


def test_winter_is_sequential_once_quantisation_is_out_of_the_way():
    """winter's only reversals are +/-0.001 OKLab artifacts of 1/255 channel
    steps in a linear ramp: 0.0139 measured in float against 0.0343 measured
    through hex, on a 0.02 floor."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    np = pytest.importorskip("numpy")
    rgb = [tuple(c) for c in colormaps["winter"](np.linspace(0, 1, 256))[:, :3]]
    assert cp.cmap_back_travel_rgb(rgb) < cp.CMAP_BACKTRAVEL_MAX
    assert cp.cmap_kind_rgb(rgb) == "sequential"


def test_the_genuinely_reversing_maps_still_fail():
    colormaps = pytest.importorskip("matplotlib").colormaps
    np = pytest.importorskip("numpy")
    for name in ("spring", "cool", "gist_earth", "turbo", "jet", "hsv"):
        rgb = [tuple(c) for c in colormaps[name](np.linspace(0, 1, 256))[:, :3]]
        assert cp.cmap_back_travel_rgb(rgb) > cp.CMAP_BACKTRAVEL_MAX, name


def test_the_hex_api_is_unchanged():
    """Callers holding only hex keep working."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    np = pytest.importorskip("numpy")
    from matplotlib.colors import to_hex
    hexes = [to_hex(c) for c in colormaps["viridis"](np.linspace(0, 1, 256))]
    assert cp.cmap_kind(hexes) == "sequential"


def test_only_the_quantisation_casualties_move_to_the_float_path():
    """Sweeping every installed colormap is what makes "one class of verdict
    moved" a measurement rather than a hope.

    Two maps move, each with its reverse, and both move in the same direction
    for the same reason: their lightness never actually reverses, and the hex
    path was reading 1/255 rounding as if it did. Back travel is divided by the
    lightness span, so a narrow-span map turns the same absolute wobble into a
    large fraction - `Wistia` spans 0.228 and reads 0.0561 through hex against
    0.0000 in float, `winter` spans 0.430 and reads 0.0343 against 0.0139.

    `Wistia` is not a new judgement. `tests/test_palette_oracle.py` already
    records it as sequential by kind and the `misc` verdict as this project's
    disagreement with cmasher, caused by exactly the rounding removed here. Its
    real defect, a lightness range too narrow to read as an order, is a
    separate measurement and is still deferred.
    """
    colormaps = pytest.importorskip("matplotlib").colormaps
    np = pytest.importorskip("numpy")
    from matplotlib.colors import to_hex
    t = np.linspace(0, 1, 256)
    movers = {}
    for name in sorted(colormaps):
        try:
            cols = colormaps[name](t)[:, :3]
        except Exception:
            continue
        old = cp.cmap_kind([to_hex(c) for c in cols])
        new = cp.cmap_kind_rgb([tuple(c) for c in cols])
        if old != new:
            movers[name] = (old, new)
    assert movers == {
        "winter": ("misc", "sequential"),
        "winter_r": ("misc", "sequential"),
        "Wistia": ("misc", "sequential"),
        "Wistia_r": ("misc", "sequential"),
    }, movers
    # Every mover moves out of `misc`, so the float path only ever removes
    # fires. A map that started passing and stopped would be a new failure
    # mode and is what this half of the assertion is watching for.
    assert all(old == "misc" for old, _new in movers.values()), movers


def test_viridis_is_not_misc():
    pytest.importorskip("matplotlib")
    assert cp.cmap_kind(cmap_samples("viridis")) == "sequential"


def lightness_with_one_reversal(reverse, n=101):
    ls = [i / (n - 1) for i in range(n)]
    ls[n // 2] = ls[n // 2 - 1] - reverse
    return ls


def test_the_back_travel_threshold_is_where_it_says_it_is():
    assert cp._back_travel(lightness_with_one_reversal(0.019)) < cp.CMAP_BACKTRAVEL_MAX
    assert cp._back_travel(lightness_with_one_reversal(0.021)) > cp.CMAP_BACKTRAVEL_MAX
    assert cp._back_travel(lightness_with_one_reversal(0.0)) == 0.0


def windowed_samples(name, lo, hi):
    from matplotlib import colormaps
    from matplotlib.colors import to_hex
    cmap = colormaps[name]
    n = cp.CMAP_SAMPLES
    return [to_hex(cmap(lo + (hi - lo) * i / (n - 1))) for i in range(n)]


def test_a_plateau_heavy_ramp_still_reads_as_monotone():
    # 8-bit sRGB rounding flattens consecutive samples, so a narrow window is
    # mostly plateaus. Counting those against ascending inverted the direction.
    ls = [(i // 4) / 64 for i in range(cp.CMAP_SAMPLES)]
    assert sum(1 for a, b in zip(ls, ls[1:]) if b == a) > len(ls) / 2
    assert cp._back_travel(ls) == 0.0
    assert cp._back_travel(ls[::-1]) == 0.0


def test_the_window_the_style_guide_asks_for_is_sequential():
    pytest.importorskip("matplotlib")
    # style-guide.md narrows viridis to t in [0.00, 0.38] beside status green.
    samples = windowed_samples("viridis", 0.00, 0.38)
    assert cp.cmap_kind(samples) == "sequential"
    assert cp.cmap_kind(windowed_samples("viridis", 0.05, 0.70)) == "sequential"


def test_a_narrow_window_classifies_the_same_read_either_way():
    pytest.importorskip("matplotlib")
    samples = windowed_samples("Greys", 0.20, 0.35)
    assert cp.cmap_kind(samples) == "sequential"
    assert cp.cmap_kind(samples[::-1]) == "sequential"


def test_an_isoluminant_ramp_is_misc_not_sequential():
    assert cp.cmap_kind(["#808080"] * 256) == "misc"


def test_fewer_than_forty_samples_is_qualitative_whatever_its_lightness():
    grays = ["#111111", "#333333", "#555555", "#777777",
             "#999999", "#bbbbbb", "#dddddd", "#ffffff"]
    assert cp.cmap_kind(grays) == "qualitative"


def test_the_cyclic_wrap_is_a_colour_distance_not_a_lightness_one():
    colormaps = pytest.importorskip("matplotlib").colormaps
    if "RdYlGn" not in colormaps:
        pytest.skip("this matplotlib has no RdYlGn")
    ends = cmap_samples("RdYlGn")
    lab = [cp.linear_to_oklab(cp.hex_to_linear(h)) for h in (ends[0], ends[-1])]
    assert abs(lab[0][0] - lab[1][0]) < 0.05
    assert cp.delta_e(cp.hex_to_linear(ends[0]),
                      cp.hex_to_linear(ends[-1])) > cp.CMAP_WRAP_DE_MAX
    assert cp.cmap_kind(ends) == "diverging"


def test_check_palette_still_imports_nothing_outside_the_standard_library():
    import ast
    from pathlib import Path
    source = Path(cp.__file__).read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # `__future__` and `collections.abc` are the annotations: the first makes
    # them strings, so `tuple[float, float, float]` is never evaluated and the
    # 3.8 floor holds, and the second is where `Sequence` comes from. Both are
    # standard library, which is what this test is about. A name that is not
    # belongs nowhere on this list.
    #
    # `json` arrived with `check_json` and `--json`, and is the reason the flag
    # could be added here at all: a wire format needing a third-party serialiser
    # would have cost this file the claim it exists to keep. The walk is over
    # every `Import` node, so the function-local `import json` is on this list
    # rather than hidden by being deferred.
    assert imported <= {"__future__", "argparse", "collections", "itertools",
                        "json", "math"}, imported


# --- anomalous trichromacy ---------------------------------------------------

def test_the_severity_table_is_the_one_the_paper_publishes():
    """Four cells checked against Table 1 on the authors' own page, verified
    2026-07-31. The table is the whole substance of this feature, so a
    transcription slip would be a wrong answer wearing a citation."""
    published = {
        ("protan", 10): (0.152286, 1.052583, -0.204868,
                         0.114503, 0.786281, 0.099216,
                         -0.003882, -0.048116, 1.051998),
        ("protan", 6): (0.385450, 0.769005, -0.154455,
                        0.100526, 0.829802, 0.069673,
                        -0.007442, -0.022190, 1.029632),
        ("deutan", 10): (0.367322, 0.860646, -0.227968,
                         0.280085, 0.672501, 0.047413,
                         -0.011820, 0.042940, 0.968881),
        ("deutan", 4): (0.605511, 0.528560, -0.134071,
                        0.155318, 0.812366, 0.032316,
                        -0.009376, 0.023176, 0.986200),
    }
    for (kind, tenths), want in published.items():
        got = tuple(v for row in cp.MACHADO[kind][tenths] for v in row)
        assert got == pytest.approx(want, abs=5e-7), (kind, tenths)

    # every severity present, and each row a 3x3
    for kind in ("protan", "deutan"):
        assert sorted(cp.MACHADO[kind]) == list(range(1, 11))
        for m in cp.MACHADO[kind].values():
            assert len(m) == 3 and all(len(r) == 3 for r in m)


def test_the_severity_matrices_belong_on_linear_light():
    """Which transfer function the published table wants, settled by
    measurement rather than by assumption.

    The paper calibrates severity 1.0 against the same Brettel/Vienot
    dichromacy `simulate` uses, so the domain that reproduces `simulate` is the
    domain the matrices are written for. Applying them to gamma-encoded sRGB
    instead is roughly twice as far off, which is the size of error that would
    have sat under every number this feature produces.
    """
    def to_srgb(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    def to_linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    swatches = ["#e69f00", "#56b4e9", "#009e73", "#0072b2", "#d55e00",
                "#cc79a7", "#7f3f1f", "#204080", "#b0d0a0", "#404040"]
    for kind in ("protan", "deutan"):
        on_linear = on_srgb = 0.0
        for h in swatches:
            lin = cp.hex_to_linear(h)
            reference = cp.simulate(lin, kind)
            on_linear += cp.delta_e(reference,
                                    cp.simulate_anomalous(lin, kind, 1.0))
            gamma = tuple(to_srgb(c) for c in lin)
            wrong = cp.simulate_anomalous(gamma, kind, 1.0)
            on_srgb += cp.delta_e(reference,
                                  tuple(to_linear(c) for c in wrong))
        # 1.2 rather than the 1.3 this held before 0.8.0. The finding is
        # unchanged - linear light reproduces Vienot dichromacy better, and it
        # is the domain the table wants - but the margin is smaller when the
        # difference is measured in CAM02-UCS instead of OKLab: mean 4.34 dE on
        # linear light against 5.46 (protan) and 6.73 (deutan) on gamma-encoded
        # sRGB, so ratios of 1.26 and 1.55 where OKLab reported 1.37 and 2.04.
        # A metric change that moved this number is expected; one that flipped
        # its sign would not be, and that is what the assertion is for.
        assert on_linear < on_srgb / 1.2, (
            f"{kind}: linear light {on_linear:.1f}, sRGB {on_srgb:.1f} - the "
            "two domains stopped being distinguishable, so this test no longer "
            "says which one the table wants")


def test_dichromacy_is_not_the_worst_case():
    """The named failure. Two hues this file would accept as series slots that
    clear `CVD_TARGET` under both dichromacy models and miss it at severity
    0.8, where far more readers actually sit.

    Measured over 244650 such pairs in CAM02-UCS, 1.27% of them do this, and
    dichromacy overstates separation by up to 12.7 dE. Both numbers grew when
    the metric changed in 0.8.0 - they read 0.87% and 10.5 in OKLab - so the
    sweep the gate does is doing more work now, not less.
    """
    a, b = "#8e4dc7", "#1402ef"
    la, lb = cp.hex_to_linear(a), cp.hex_to_linear(b)

    # Every dichromacy view, not just the one that crosses: the gate takes the
    # worst of them, so the claim is that all of them clear the floor.
    at_dichromacy = min(cp.delta_e(cp.simulate(la, kind), cp.simulate(lb, kind))
                        for kind in ("protan", "deutan"))
    at_severity = cp.delta_e(cp.simulate_anomalous(la, "protan", 0.9),
                             cp.simulate_anomalous(lb, "protan", 0.9))
    assert at_dichromacy >= cp.CVD_TARGET > at_severity, (
        f"the fixture stopped crossing the floor: {at_dichromacy:.2f} at "
        f"dichromacy, {at_severity:.2f} at severity 0.9")

    ok, rows = cp.check([a, b])
    assert ok is False
    row = next(r for r in rows if r[0].startswith("CVD separation"))
    assert row[1] is False
    assert "severity 0.9" in row[2], row[2]


def test_the_bundled_cycle_survives_the_severity_sweep():
    """The over-fire guard, and the one that matters most: a sweep that failed
    the palette this project ships would be a gate nobody could satisfy.

    The worst adjacent pair in the style sheet's own cycle reads 31.7 dE at
    severity 0.1, three times the 10.5 floor.
    """
    cycle = ["#e69f00", "#56b4e9", "#009e73", "#0072b2", "#d55e00", "#cc79a7"]
    ok, rows = cp.check(cycle)
    assert ok, rows
    row = next(r for r in rows if r[0].startswith("CVD separation"))
    worst = float(re.search(r"dE ([\d.]+)", row[2]).group(1))
    assert worst > cp.CVD_TARGET * 1.5, row[2]


def test_severity_zero_is_normal_vision_and_the_ends_are_rejected_cleanly():
    lin = cp.hex_to_linear("#e69f00")
    assert cp.simulate_anomalous(lin, "protan", 0.0) == pytest.approx(lin)
    # read at the nearest published tenth, with no interpolation invented
    assert (cp.simulate_anomalous(lin, "deutan", 0.63)
            == cp.simulate_anomalous(lin, "deutan", 0.6))
    with pytest.raises(ValueError):
        cp.simulate_anomalous(lin, "tritan", 0.5)
    with pytest.raises(ValueError):
        cp.simulate_anomalous(lin, "protan", 1.4)


def test_the_sweep_leaves_dichromacy_to_the_vienot_matrices():
    """`ANOMALOUS_SEVERITIES` stops at 0.9 on purpose. Reading 1.0 under both
    models would move every dichromacy number the style guide publishes, for a
    view `simulate` already covers."""
    assert 1.0 not in cp.ANOMALOUS_SEVERITIES
    assert max(cp.ANOMALOUS_SEVERITIES) == pytest.approx(0.9)
    assert min(cp.ANOMALOUS_SEVERITIES) == pytest.approx(0.1)


# --- the size-weighted gate that was measured and not shipped ----------------

def _cielab(lin):
    """CIELAB under D65, for comparing this file's units to a published model's.

    Here rather than in `check_palette.py` on purpose: nothing in the validator
    computes CIELAB, and shipping a conversion with no caller into a file whose
    whole claim is that it is small and stdlib-only would be paying for an
    argument this test settles once.
    """
    m = ((0.4124564, 0.3575761, 0.1804375),
         (0.2126729, 0.7151522, 0.0721750),
         (0.0193339, 0.1191920, 0.9503041))
    white = [sum(row) for row in m]
    xyz = [sum(m[i][j] * lin[j] for j in range(3)) / white[i] for i in range(3)]

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = (f(v) for v in xyz)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _de_lab(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(_cielab(a), _cielab(b))))


def _slot_pairs(n, seed=0):
    """Random pairs of colours that clear the lightness band and chroma floor.

    The population the separation rows actually see. Sampling the whole sRGB
    cube instead is what makes the CIELAB bridge read 1.85 rather than 1.99, and
    that 7.6% moves both floors, so the choice is load-bearing and is made here
    rather than left to whoever writes the next test.
    """
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        pair = []
        while len(pair) < 2:
            h = "#{:02x}{:02x}{:02x}".format(
                *(rng.randrange(256) for _ in range(3)))
            lin = cp.hex_to_linear(h)
            L, a, b = cp.linear_to_oklab(lin)
            if cp.L_MIN <= L <= cp.L_MAX and math.hypot(a, b) >= cp.CHROMA_MIN:
                pair.append(lin)
        out.append(tuple(pair))
    return out


def test_the_separation_floors_reproduce_the_size_model_they_derive_from():
    """Where `CVD_TARGET` and `NORMAL_FLOOR` come from.

    A small target needs more colour difference than a large one, and Stone,
    Szafir & Setlur (2014) measured how much: it rises as C + K/s with s the
    visual angle in degrees, fitted from 0.333 to 6, giving 6.1 CIELAB at a
    two-degree patch and 10.4 at a third of a degree. Before 0.8.0 that model
    could only be used as a sanity check, because the floors were OKLab
    distances and the model is CIELAB and nothing converts between an
    uncalibrated metric and a calibrated one. Since 0.8.0 the floors are
    CAM02-UCS, the conversion is a measurement, and they are derived from the
    model rather than merely compared against it.

    This test is that derivation, run forwards. If a future change to the colour
    maths moves the bridge, both floors are wrong by the amount it moved and
    this is where that surfaces.
    """
    # C and K are the mean of Stone, Szafir & Setlur's Table 3 over L*, a*, b*.
    C, K = (5.079 + 5.339 + 5.349) / 3, (0.751 + 1.541 + 2.871) / 3
    assert C + K / 2.0 == pytest.approx(6.1, abs=0.1), (
        "the mean of their three axes no longer reproduces the paper's own "
        "'closer to 6' at two degrees")
    smallest_fitted = C + K / 0.333
    assert smallest_fitted == pytest.approx(10.4, abs=0.2)

    # One CAM02-UCS unit, in CIELAB dE*ab, over the gamut the gate sees.
    ratios = sorted(_de_lab(la, lb) / d
                    for la, lb in _slot_pairs(4000)
                    if (d := cp.delta_e(la, lb)) >= 1)
    per_unit = ratios[len(ratios) // 2]
    assert per_unit == pytest.approx(1.99, abs=0.06), per_unit

    # The derivation: 2x and 4x the model's hardest requirement, converted.
    assert cp.CVD_TARGET == pytest.approx(2 * smallest_fitted / per_unit, abs=0.4)
    assert cp.NORMAL_FLOOR == pytest.approx(4 * smallest_fitted / per_unit, abs=0.8)

    # And the pair the discarded size gate fired on, on a 1.6pt gallery curve.
    green, sky = cp.hex_to_linear("#009e73"), cp.hex_to_linear("#56b4e9")
    assert _de_lab(green, sky) > 5 * smallest_fitted, (
        "the gallery pair the size gate flagged is no longer comfortably clear "
        "of the size model's requirement, which is the whole reason the gate "
        "was not shipped")


def test_the_bridge_between_the_two_colour_spaces_is_population_dependent():
    """Why `_slot_pairs` exists, as an assertion rather than a comment.

    The floors are Stone et al.'s CIELAB numbers divided by this ratio, so
    sampling the whole sRGB cube instead of the gamut the gate gates would put
    `CVD_TARGET` at 11.3 rather than 10.5. A reader who wants to re-derive the
    floors has to know which population to draw from, and a test that measures
    both is a better place to learn it than a sentence.
    """
    rng = random.Random(0)
    cube = []
    while len(cube) < 4000:
        pair = tuple(cp.hex_to_linear("#{:02x}{:02x}{:02x}".format(
            *(rng.randrange(256) for _ in range(3)))) for _ in range(2))
        if cp.delta_e(*pair) >= 1:
            cube.append(pair)

    def median_ratio(pairs):
        r = sorted(_de_lab(la, lb) / d for la, lb in pairs
                   if (d := cp.delta_e(la, lb)) >= 1)
        return r[len(r) // 2]

    slot, whole = median_ratio(_slot_pairs(4000)), median_ratio(cube)
    assert slot == pytest.approx(1.99, abs=0.06), slot
    assert whole == pytest.approx(1.85, abs=0.06), whole
    assert slot / whole > 1.05, (
        f"slot gamut {slot:.3f}, whole cube {whole:.3f} - the two populations "
        "stopped disagreeing, so the sampling choice in `_slot_pairs` no longer "
        "needs defending and this test has nothing left to say")


def test_no_size_weighting_leaked_into_the_validator():
    """The gate was measured and dropped. A helper left behind with no caller is
    the shape of a thing that gets wired back in without the measurement."""
    assert not hasattr(cp, "size_factor")
    assert not hasattr(cp, "ND_SIZE_C")


# --- the public surface no gate happens to call -----------------------------
# `oklab_distance` and `cmap_back_travel` are in `__all__`, are rendered on
# `docs/api.md`, and are held against the last tag by `audit_api.py`. Coverage
# reported both bodies as never executed: the separation gates moved to
# CAM02-UCS and `check_colormap` reads the float-sRGB `cmap_back_travel_rgb`,
# so nothing in the suite reached either one. The API gate protects a signature.
# It does not run a line, and a documented function nothing runs is a claim.

def test_oklab_distance_is_the_oklab_metric_it_documents():
    """Zero on a colour against itself, symmetric, and x100 the euclidean
    distance in the space `linear_to_oklab` returns."""
    blue = cp.hex_to_linear("#0072b2")
    orange = cp.hex_to_linear("#d55e00")
    assert cp.oklab_distance(blue, blue) == 0.0
    assert cp.oklab_distance(blue, orange) == cp.oklab_distance(orange, blue)
    a, b = cp.linear_to_oklab(blue), cp.linear_to_oklab(orange)
    expected = 100 * math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    assert cp.oklab_distance(blue, orange) == pytest.approx(expected)


def test_oklab_distance_is_not_delta_e():
    """The two are different metrics on the same pair, which is why the
    migration to CAM02-UCS was a migration and not a rename."""
    blue, orange = cp.hex_to_linear("#0072b2"), cp.hex_to_linear("#d55e00")
    assert cp.oklab_distance(blue, orange) != pytest.approx(
        cp.delta_e(blue, orange), abs=0.5)


@pytest.mark.parametrize("name", ("viridis", "Greys"))
def test_cmap_back_travel_agrees_with_the_float_srgb_route(name):
    """`cmap_back_travel_rgb` is the covered one. The hex route is the same
    measurement through an 8-bit round trip, so it has to land within it."""
    import matplotlib.pyplot as plt

    cmap = plt.get_cmap(name)
    rgb = [cmap(i / (cp.CMAP_SAMPLES - 1))[:3] for i in range(cp.CMAP_SAMPLES)]
    hexes = ["#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in channel))
             for channel in rgb]
    assert cp.cmap_back_travel(hexes) == pytest.approx(
        cp.cmap_back_travel_rgb(rgb), abs=0.01)


def test_cmap_back_travel_reads_zero_on_a_monotone_ramp():
    """0.0 is the documented reading for a ramp that never runs backwards."""
    grey = [f"#{v:02x}{v:02x}{v:02x}" for v in range(0, 256, 8)]
    assert cp.cmap_back_travel(grey) == 0.0


def test_cmap_back_travel_sees_a_ramp_that_turns_around():
    """The other side of the same line: out and back reads as travel."""
    out = list(range(0, 256, 8))
    there_and_back = [f"#{v:02x}{v:02x}{v:02x}" for v in out + out[::-1]]
    assert cp.cmap_back_travel(there_and_back) > cp.CMAP_BACKTRAVEL_MAX


@pytest.mark.parametrize("bad", ("#fff", "0072b2ff", "", "#0072b"))
def test_hex_to_linear_refuses_anything_that_is_not_six_digits(bad):
    """The only raise in the module's entry point, and it was unexercised. A
    three-digit hex is the shorthand a reader is likeliest to try."""
    with pytest.raises(ValueError, match="expected 6-digit hex"):
        cp.hex_to_linear(bad)


def test_cmap_back_travel_has_no_travel_to_report_on_one_sample():
    """`_back_travel`'s emptiness guard, reached through the public name. One
    colour has no steps between colours."""
    assert cp.cmap_back_travel(["#0072b2"]) == 0.0


def test_cmap_back_travel_has_no_span_to_divide_by_on_a_flat_ramp():
    """The other guard. Travel is reported as a fraction of the span, and a
    ramp of one lightness has none."""
    assert cp.cmap_back_travel(["#777570"] * 8) == 0.0


def test_cmap_kind_rgb_calls_a_flat_ramp_misc():
    """`misc` is the verdict the guide's colour rules exist to produce, and the
    float-sRGB route reached it nowhere in the suite."""
    flat = [(0.47, 0.46, 0.44)] * cp.CMAP_QUALITATIVE_N
    assert cp.cmap_kind_rgb(flat) == "misc"
