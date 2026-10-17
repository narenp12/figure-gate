"""`check_palette`'s Brettel 1997 tritan simulation against DaltonLens-Python.

`check_palette` carries the constants in `BRETTEL_TRITAN` so the file stays
stdlib-only. This differential is what stands behind them: DaltonLens computes
the same projection from first principles, and the two have to agree.

daltonlens is a dev-group dependency and is never imported by anything under
`skill/scripts/`.
"""

import importlib.util
import random

import pytest

import check_palette as cp

HAVE = importlib.util.find_spec("daltonlens") is not None

pytestmark = pytest.mark.skipif(not HAVE, reason="daltonlens is a dev-only oracle")

# daltonlens works in float32. Measured over the sample below, the gap is
# 4.7e-8 in linear RGB (3.2e-6 dE); the ceiling sits above float32 noise.
LINEAR_TOL = 1e-6


def test_tritan_matches_daltonlens_brettel_1997():
    import numpy as np
    from daltonlens import simulate

    rng = random.Random(0)
    colours = [tuple(rng.random() for _ in range(3)) for _ in range(4000)]
    # Both half-planes and the neutral axis, named so a regression in either
    # projection cannot hide in the random sample.
    colours += [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0),
                (1.0, 1.0, 1.0), (0.5, 0.5, 0.5), (0.0, 0.0, 0.0)]

    image = np.array(colours, dtype=np.float32).reshape(-1, 1, 3)
    want = simulate.Simulator_Brettel1997()._simulate_dichromacy_linear_rgb(
        image, simulate.Deficiency.TRITAN)
    want = np.clip(want.reshape(-1, 3), 0.0, 1.0)

    got = np.array([cp.simulate(c, "tritan") for c in colours])
    worst = float(np.abs(got - want).max())
    assert worst < LINEAR_TOL, (
        f"Brettel tritan drifted from daltonlens by {worst:.3e} in linear RGB")


def test_tritan_uses_both_half_planes():
    """A sample that only ever lands on one plane would pass the oracle with
    the other plane's row wrong."""
    t = cp.BRETTEL_TRITAN
    sides = set()
    for c in [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)]:
        lms = [sum(t["lms_from_rgb"][i][j] * c[j] for j in range(3))
               for i in range(3)]
        sides.add(sum(n * v for n, v in zip(t["separation"], lms)) >= 0)
    assert sides == {True, False}


def test_tritan_leaves_white_alone():
    assert cp.simulate((1.0, 1.0, 1.0), "tritan") == pytest.approx(
        (1.0, 1.0, 1.0), abs=1e-6)
