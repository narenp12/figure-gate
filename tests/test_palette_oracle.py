"""`cmap_kind` against an independent implementation, over the whole registry.

The classifier is a port of `cmasher.get_cmap_type()` from CAM02-UCS into
OKLab. A port with no oracle is a rewrite nobody checked, and this one was
wrong in a way that unit tests would not have caught: an earlier draft measured
the cyclic/diverging wrap in lightness, which put 11 of 148 colormaps in the
wrong family because a symmetric diverging map has equal lightness at both ends
BY CONSTRUCTION. Running this differential is what found that.

cmasher is a dev-group dependency and is never imported by anything under
`skill/scripts/`.
"""

import importlib.util

import pytest

import check_palette as cp

# `pytest.importorskip` at module scope, which this used, raises during
# collection: the module contributes zero tests rather than two skipped ones.
# CI installs pytest, xdist and matplotlib and never the dev group, so it
# collected 479 where a machine with cmasher collects 481 - and
# `test_the_stated_test_count_is_the_real_one` compares a number written into
# the docs against whatever the local run collected. The count was therefore
# unwritable: 481 was honest here and wrong in CI, 479 the reverse, and the
# documented number had been failing that test on every CI run since the oracle
# was added.
#
# A collected-and-skipped test is visible in the count and in the summary. A
# module that never collected is neither.
HAVE_CMASHER = importlib.util.find_spec("cmasher") is not None

pytestmark = pytest.mark.skipif(
    not HAVE_CMASHER, reason="cmasher is a dev-only oracle")


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


def oracle():
    """cmasher, imported for its side effect as much as for its function.

    Importing it registers its own colormaps into matplotlib's registry, and
    the differential is over that registry: with the import deferred and not
    called here, `registry_names()` returns matplotlib's 91 instead of the 148
    the design was measured against. So every helper that reads the registry
    goes through this, and the ordering cannot come apart.

    The import is allowed to fail. cmasher 1.9.2 builds every one of its
    colormaps with `ListedColormap(..., N=...)`, which matplotlib deprecated in
    3.11 and removes in 3.13 -- so on a new enough matplotlib this import stops
    working entirely, through no fault of anything in this repo. An oracle that
    cannot be imported is a skip with the reason attached, not an error: the
    only thing lost is the differential, and the message says so out loud
    rather than leaving a green run that quietly stopped checking.
    """
    try:
        import cmasher as cmr
    except Exception as exc:                                # pragma: no cover
        import matplotlib

        pytest.skip(f"cmasher does not import under matplotlib "
                    f"{matplotlib.__version__}: {exc!r}")
    else:
        # `else`, not a bare `return` after the block: `pytest.skip` raises, so
        # both read the same at run time. Static analysis does not know that --
        # CodeQL's py/uninitialized-local-variable reported `cmr` as possibly
        # unbound on the fall-through path. Binding the return to "no exception
        # was raised" states the control flow instead of leaving it inferred.
        return cmr


def registry_names():
    oracle()
    from matplotlib import colormaps

    return sorted(n for n in colormaps if not n.endswith("_r"))


def samples(name):
    from matplotlib import colormaps
    from matplotlib.colors import to_hex

    cmap = colormaps[name]
    if cmap.N < cp.CMAP_QUALITATIVE_N:
        return [to_hex(cmap(i)) for i in range(cmap.N)]
    return [to_hex(cmap(i / (cp.CMAP_SAMPLES - 1)))
            for i in range(cp.CMAP_SAMPLES)]


def disagreements(names):
    cmr = oracle()
    from matplotlib import colormaps

    out = {}
    for name in names:
        ours = cp.cmap_kind(samples(name))
        theirs = cmr.get_cmap_type(colormaps[name])
        if ours != theirs:
            out[name] = (ours, theirs)
    return out


def expected(names):
    """`KNOWN_DISAGREEMENTS` narrowed to the colormaps this matplotlib has.

    `managua` and `vanimo` arrived in matplotlib 3.10, so on anything older the
    dict describes two colormaps that are not in the registry to disagree
    about. Unfiltered, the "these no longer disagree" assertion read their
    absence as a resolved disagreement and failed -- under matplotlib 3.8.4,
    the floor this project still supports, on any machine with cmasher
    installed. CI never hit it because cmasher goes on the latest-matplotlib
    job only; `uv sync --group dev` with an older matplotlib pinned does.

    Same defect class as the sweep fix: a registry-derived expectation stated
    as a constant. The constant stays -- each entry is an adjudication that has
    to be written down somewhere -- and what this does is scope it to what is
    present, so a missing colormap is silent and a present one that flipped
    still fails.
    """
    have = set(names)
    return {k: v for k, v in KNOWN_DISAGREEMENTS.items() if k in have}


def test_the_registry_is_large_enough_to_be_evidence():
    assert len(registry_names()) >= 100, registry_names()


def test_only_the_three_known_colormaps_disagree_with_cmasher():
    names = registry_names()
    found = disagreements(names)
    want = expected(names)
    new = {k: v for k, v in found.items() if k not in want}
    gone = {k: v for k, v in want.items() if k not in found}
    assert not new, (
        f"new disagreements with cmasher: {new}. Adjudicate each one -- say "
        "which implementation is right and why -- and either fix cmap_kind or "
        "add it to KNOWN_DISAGREEMENTS with that reasoning written down.")
    assert not gone, (
        f"these no longer disagree: {gone}. Good news, but the comment "
        "explaining each is now stale and should come out with it.")
    assert found == want, found


def test_the_three_known_colormaps_are_all_present_on_a_new_matplotlib():
    """`expected()` scopes the constant to the registry, which means a typo in
    a key -- or a colormap matplotlib renamed -- would drop out of the
    comparison and take its adjudication with it, silently. Nothing older than
    3.10 is missing an entry, so on 3.10+ every key has to be a real name."""
    from matplotlib import __version__ as mpl

    if tuple(int(p) for p in mpl.split(".")[:2]) < (3, 10):
        pytest.skip(f"managua and vanimo arrive in matplotlib 3.10 (have {mpl})")
    missing = set(KNOWN_DISAGREEMENTS) - set(registry_names())
    assert not missing, (
        f"KNOWN_DISAGREEMENTS names colormaps the registry does not have: "
        f"{sorted(missing)}")
