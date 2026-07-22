"""Gates for check_palette.py.

Two jobs here. The obvious one is that good palettes pass and bad ones fail. The
less obvious one is that the *numbers quoted in the documentation* stay true:
the guide makes specific claims (adjacent CVD dE 16.6, orange and sky blue
differing by dL 0.011) and a reader who cannot trust those has no reason to
trust anything else in it. Pinning them here means a change to the color math
breaks a test instead of quietly making the prose wrong.
"""

import pytest

import check_palette as cp

OKABE_ITO = ["#000000", "#E69F00", "#56B4E9", "#009E73",
             "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
SERIES = [OKABE_ITO[i] for i in (1, 2, 3, 5, 6, 7)]


def gates(rows):
    return {name: status for name, status, _ in rows}


# --- the palette the guide actually recommends ------------------------------

def test_series_pairs_pass_adjacent():
    rows, ok = cp.check(SERIES[:2])
    assert ok, rows


def test_first_four_pass_all_pairs():
    """Scatter and small multiples compare every series against every other.
    The guide says only the first four slots clear that, so it had better."""
    rows, ok = cp.check(SERIES[:4], all_pairs=True)
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
    assert worst == pytest.approx(16.6, abs=0.1)


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
    rows, ok = cp.check(["#F0E442", "#0072B2"])
    assert not ok
    assert gates(rows)["Lightness band"] is False


def test_chroma_floor_rejects_gray():
    rows, ok = cp.check(["#808080", "#0072B2"])
    assert not ok
    assert gates(rows)["Chroma floor"] is False


def test_normal_vision_floor_rejects_two_near_identical_hues():
    rows, ok = cp.check(["#0072B2", "#0d76b5"])
    assert not ok
    assert gates(rows)["Normal-vision floor (adjacent)"] is False


def test_cvd_gate_rejects_a_red_green_pair_that_looks_fine_in_color():
    """The failure mode the whole validator exists for: a pair that is obvious
    to normal vision and collapses under protanopia."""
    a, b = "#c1272d", "#5a8f29"
    normal = cp.delta_e(cp.hex_to_linear(a), cp.hex_to_linear(b))
    assert normal >= cp.NORMAL_FLOOR, "should be clearly distinct in full color"
    rows, ok = cp.check([a, b])
    assert not ok
    assert gates(rows)["CVD separation (adjacent)"] is False


def test_low_contrast_warns_rather_than_fails():
    """Sub-3:1 is legal if it carries a direct label. Reporting it as FAIL while
    the run still passes would read as a contradiction, so it warns."""
    rows, ok = cp.check(["#E69F00", "#0072B2"])
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
    rows, ok = cp.check(viridis_window(n), ordinal=True)
    assert ok, rows


def test_full_range_viridis_fails_light_end_contrast():
    """The reason discrete tiers get windowed at all: viridis finishes at
    #fde725, which is invisible as a hairline on a light page."""
    rows, ok = cp.check(viridis_window(4, 0.0, 1.0), ordinal=True)
    assert not ok
    assert gates(rows)["Light-end contrast"] is False


def test_jet_fails_lightness_monotone():
    """The guide replaced a 'single hue' gate with monotone lightness plus even
    steps, and claims jet still fails on the honest reason it was always
    unreadable. This is that claim, as a test."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    from matplotlib.colors import to_hex
    jet = [to_hex(colormaps["jet"](i / 5)) for i in range(6)]
    rows, ok = cp.check(jet, ordinal=True)
    assert not ok
    assert gates(rows)["Lightness monotone"] is False


def test_uneven_steps_fail_even_when_monotone():
    """A ramp can descend in lightness the whole way and still read as having a
    boundary in it, because one step is much larger than the rest."""
    rows, ok = cp.check(["#f7f7f7", "#eaeaea", "#dddddd", "#111111"],
                        ordinal=True)
    assert not ok
    assert gates(rows)["Step uniformity"] is False


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
