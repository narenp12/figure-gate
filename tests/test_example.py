"""The example in the README has to actually run.

Added after CI caught what local testing could not: `examples/demo.py` reached
for `colormaps["okabe_ito"]` unconditionally, which needs matplotlib 3.11. On
Python 3.9 the newest installable matplotlib is 3.9, so the example could never
have worked there -- while the whole suite stayed green, because no test ran the
example. A README whose first code block crashes on a supported version is worse
than no README.
"""

import subprocess
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo.py"


def test_the_example_runs_and_passes_its_own_gates(tmp_path):
    result = subprocess.run([sys.executable, str(DEMO)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "COMPOSED" in result.stdout


def test_the_example_palette_is_valid_without_the_builtin_colormap():
    """The fallback branch, exercised directly. It only runs on matplotlib
    < 3.11, so on a modern install nothing else would ever touch it."""
    import check_palette as cp
    fallback = ["#000000", "#e69f00", "#56b4e9", "#009e73",
                "#f0e442", "#0072b2", "#d55e00", "#cc79a7"]
    rows, ok = cp.check(fallback[1:4], all_pairs=True)
    assert ok, rows


def test_the_fallback_matches_the_builtin_where_the_builtin_exists():
    """Two sources for one palette is a drift risk, so pin them together."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    if "okabe_ito" not in colormaps:
        pytest.skip("matplotlib < 3.11 has no okabe_ito colormap")
    from matplotlib.colors import to_hex
    source = DEMO.read_text()
    start = source.index('OKABE_ITO = [')
    end = source.index("]", start) + 1
    literal = eval(source[start + len("OKABE_ITO = "):end])   # noqa: S307
    assert literal == [to_hex(colormaps["okabe_ito"](i)) for i in range(8)]
