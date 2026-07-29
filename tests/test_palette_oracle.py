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


# name: (ours, cmasher's). An empty dict here would be a claim of exact parity
# between two colour spaces, which is not true. Each entry says who is right.
KNOWN_DISAGREEMENTS = {
    # OURS. L runs 0.877 -> 0.355 -> 0.875: light ends, dark centre, RdBu
    # inverted. cmasher's strict `np.isclose` monotonicity test trips on its
    # micro-reversals -- the same 8-bit quantization noise that made a direct
    # transcription of that test misclassify viridis. Back-travel tolerates it.
    "managua": ("diverging", "misc"),
    # OURS, for the same reason. L runs 0.906 -> 0.201 -> 0.931. Both are
    # Crameri maps added in matplotlib 3.10.
    "vanimo": ("diverging", "misc"),
    # CMASHER. Wistia descends monotonically, 0.954 -> 0.726, but over a span
    # of only 0.228. Back-travel divides by span, so its 0.0128 of wobble reads
    # as 5.61% where viridis's 0.0006 over 0.633 reads as 0.10%. Narrow-span
    # maps get noisy ratios. Wistia is sequential by kind; its real defect is a
    # lightness range too narrow to read as an order, which is a quality
    # judgement and not this classifier's job. Fixing it needs either an
    # absolute back-travel floor or a minimum span, and either constant has to
    # be measured across the registry first. Deferred on purpose.
    "Wistia": ("misc", "sequential"),
}


def registry_names():
    return sorted(n for n in colormaps if not n.endswith("_r"))


def samples(name):
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
    assert len(registry_names()) >= 100, registry_names()


def test_only_the_three_known_colormaps_disagree_with_cmasher():
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
