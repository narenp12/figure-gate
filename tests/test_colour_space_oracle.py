"""`check_palette`'s CIECAM02 against colorspacious, the reference implementation.

`check_palette` ships its own CIECAM02 because the file imports nothing outside
the standard library and CAM02-UCS is where every separation threshold is
quoted. A hand-rolled appearance model with no oracle is exactly the thing this
project spent 0.8.0 removing, so it gets the same treatment `cmap_kind` gets in
`test_palette_oracle.py`: a differential against an independent implementation,
run over enough colours to be evidence.

The two assertions are deliberately separate, because they fail for different
reasons and only one of them would ever be this project's fault:

  * fed identical XYZ, the appearance model has to agree to floating-point
    noise. Any drift there is an arithmetic error in `linear_to_cam02ucs`.
  * fed sRGB, the two disagree by about 0.015 dE, because colorspacious derives
    its sRGB primaries at full precision and this file uses the rounded matrix
    IEC 61966-2-1 publishes. That is a convention difference, it is four orders
    of magnitude below `CVD_TARGET`, and pinning it separately keeps it from
    being mistaken for the first kind of error.

colorspacious arrives with cmasher, which is a dev-group dependency and is never
imported by anything under `skill/scripts/`.
"""

import importlib.util
import math
import random

import pytest

import check_palette as cp

HAVE = importlib.util.find_spec("colorspacious") is not None

pytestmark = pytest.mark.skipif(
    not HAVE, reason="colorspacious is a dev-only oracle")

# Below this, the difference is float noise in a chain with a cube root, three
# matrix products and a log in it.
CORE_TOL = 1e-9
# The sRGB matrix convention, measured. Asserted as a ceiling rather than an
# equality so a tightening is not a failure, and quoted here because a reader
# comparing this file's numbers against colorspacious's needs to know the gap
# exists and how big it is.
SRGB_MATRIX_TOL = 0.02


def random_srgb(n, seed=0):
    rng = random.Random(seed)
    return [tuple(rng.randrange(256) / 255 for _ in range(3)) for _ in range(n)]


def to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def test_the_appearance_model_matches_colorspacious_on_identical_xyz():
    """The arithmetic, isolated from the sRGB matrix.

    Feeding colorspacious's own XYZ100 back into this file's CIECAM02 removes
    the one input the two implementations do not share, so what is left is the
    appearance model and nothing else. It has to agree to noise.
    """
    from colorspacious import cspace_convert

    worst = 0.0
    for srgb in random_srgb(2000):
        xyz = tuple(cspace_convert(srgb, "sRGB1", "XYZ100"))
        want = tuple(cspace_convert(srgb, "sRGB1", "CAM02-UCS"))
        # `linear_to_cam02ucs` takes linear RGB, so reach past its first step
        # rather than reimplementing the model here.
        rgb_c = tuple(d * v for d, v in zip(cp._D_RGB, cp._mul3(cp._M_CAT02, xyz)))
        rgb_a = cp._post_adapt(
            cp._mul3(cp._M_HPE, cp._mul3(cp._M_CAT02_INV, rgb_c)), cp._F_L)
        got = cp._cam02ucs_from_post_adapted(rgb_a)
        worst = max(worst, math.dist(got, want))

    assert worst < CORE_TOL, (
        f"CIECAM02 drifted from colorspacious by {worst:.3e} on identical "
        f"XYZ100. That is an arithmetic error in this file, not a convention "
        f"difference - see the sRGB test for what those look like.")


def test_the_full_path_matches_colorspacious_to_the_srgb_matrix_convention():
    from colorspacious import cspace_convert

    worst = 0.0
    for srgb in random_srgb(2000, seed=1):
        want = tuple(cspace_convert(srgb, "sRGB1", "CAM02-UCS"))
        got = cp.linear_to_cam02ucs(tuple(to_linear(c) for c in srgb))
        worst = max(worst, math.dist(got, want))

    assert worst < SRGB_MATRIX_TOL, (
        f"end-to-end disagreement with colorspacious is {worst:.4f} dE, over "
        f"the {SRGB_MATRIX_TOL} this file expects from the rounded sRGB matrix. "
        f"Something other than the matrix convention has moved.")
    assert worst > CORE_TOL, (
        "the two implementations now agree exactly end to end, so this file "
        "and colorspacious have converged on one sRGB matrix and the tolerance "
        "above is documenting a difference that no longer exists.")


def test_delta_e_is_the_distance_colorspacious_would_report():
    """The gate's actual operation, not just the transform under it."""
    from colorspacious import cspace_convert

    worst = 0.0
    pairs = list(zip(random_srgb(600, seed=2), random_srgb(600, seed=3)))
    for a, b in pairs:
        want = math.dist(cspace_convert(a, "sRGB1", "CAM02-UCS"),
                         cspace_convert(b, "sRGB1", "CAM02-UCS"))
        got = cp.delta_e(tuple(to_linear(c) for c in a),
                         tuple(to_linear(c) for c in b))
        worst = max(worst, abs(got - want))

    assert worst < 2 * SRGB_MATRIX_TOL, worst


def test_the_gate_agrees_with_the_oracle_on_the_pairs_it_judges():
    """The end the colleague cares about: same verdict, same threshold.

    Both sides simulate colour vision and measure the worst view, so this is the
    gate's whole decision compared against an independent implementation of it.
    They are not identical by construction - this file uses Vienot at dichromacy
    where colorspacious uses Machado at severity 100 - so a handful of pairs
    near the threshold are expected to differ and the assertion is on the rate.

    Before 0.8.0 the same comparison put specificity at 0.786: the OKLab metric
    passed one pair in twenty that the oracle called too close. That number is
    what this replacement exists to fix, and this test is what would catch it
    coming back.
    """
    from colorspacious import cspace_convert

    rng = random.Random(4)
    slots = []
    while len(slots) < 90:
        h = "#{:02x}{:02x}{:02x}".format(*(rng.randrange(256) for _ in range(3)))
        lin = cp.hex_to_linear(h)
        L, a, b = cp.linear_to_oklab(lin)
        if cp.L_MIN <= L <= cp.L_MAX and math.hypot(a, b) >= cp.CHROMA_MIN:
            slots.append(h)

    def oracle_worst(i, j):
        out = math.inf
        for kind in ("protanomaly", "deuteranomaly"):
            for sev in (*[s * 100 for s in cp.ANOMALOUS_SEVERITIES], 100.0):
                space = {"name": "sRGB1+CVD", "cvd_type": kind, "severity": sev}
                sim = [cspace_convert(
                    tuple(int(h[k:k + 2], 16) / 255 for k in (1, 3, 5)),
                    space, "CAM02-UCS") for h in (slots[i], slots[j])]
                out = min(out, math.dist(sim[0], sim[1]))
        return out

    def ours_worst(i, j):
        la, lb = cp.hex_to_linear(slots[i]), cp.hex_to_linear(slots[j])
        views = [cp.delta_e(cp.simulate(la, k), cp.simulate(lb, k))
                 for k in ("protan", "deutan")]
        views += [cp.delta_e(cp.simulate_anomalous(la, k, s),
                             cp.simulate_anomalous(lb, k, s))
                  for k in ("protan", "deutan") for s in cp.ANOMALOUS_SEVERITIES]
        return min(views)

    tp = tn = fp = fn = 0
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            ours = ours_worst(i, j) >= cp.CVD_TARGET
            theirs = oracle_worst(i, j) >= cp.CVD_TARGET
            if ours and theirs:
                tp += 1
            elif not ours and not theirs:
                tn += 1
            elif ours:
                fp += 1
            else:
                fn += 1

    assert tn + fp > 100, (
        f"only {tn + fp} of {tp + tn + fp + fn} pairs were too close for the "
        "oracle, which is too few to say anything about specificity")
    specificity = tn / (tn + fp)
    assert specificity > 0.95, (
        f"specificity against colorspacious is {specificity:.3f}, under the "
        f"0.95 this metric was adopted to reach. It was 0.786 in OKLab; a "
        f"number back down there means the gate is passing pairs an "
        f"independent implementation calls too close. {fp} false passes, "
        f"{fn} false failures.")
