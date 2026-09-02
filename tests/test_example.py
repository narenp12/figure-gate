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
    result = subprocess.run([sys.executable, str(DEMO), str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "COMPOSED" in result.stdout
    assert (tmp_path / "demo.png").is_file(), result.stdout


def test_the_example_palette_is_valid_without_the_builtin_colormap():
    """The fallback branch, exercised directly. It only runs on matplotlib
    < 3.11, so on a modern install nothing else would ever touch it."""
    import check_palette as cp
    fallback = ["#000000", "#e69f00", "#56b4e9", "#009e73",
                "#f0e442", "#0072b2", "#d55e00", "#cc79a7"]
    ok, rows = cp.check(fallback[1:4], all_pairs=True)
    assert ok, rows


def test_the_fallback_matches_the_builtin_where_the_builtin_exists():
    """Two sources for one palette is a drift risk, so pin them together."""
    colormaps = pytest.importorskip("matplotlib").colormaps
    if "okabe_ito" not in colormaps:
        pytest.skip("matplotlib < 3.11 has no okabe_ito colormap")
    from matplotlib.colors import to_hex
    source = DEMO.read_text(encoding="utf-8")
    start = source.index('OKABE_ITO = [')
    end = source.index("]", start) + 1
    literal = eval(source[start + len("OKABE_ITO = "):end])   # noqa: S307
    assert literal == [to_hex(colormaps["okabe_ito"](i)) for i in range(8)]


GALLERY = Path(__file__).resolve().parent.parent / "examples" / "gallery.py"


def test_the_gallery_runs_and_every_figure_passes(tmp_path):
    """The harder half of the evidence. `demo.py` is one panel and three
    curves; a gate that only ever runs on that has not been tried. These
    nineteen put a shared-axis grid, a filled field with a colorbar, an
    axis-free schematic, three statistical forms, a log-log convergence plot, a
    dense attractor, three colormapped complex-plane images, a pair of
    confidence bands, a bar chart with a second unit, a signed field, a scatter
    beside the hexbin of the same measurement, a leader line, two unit scales, a
    survival staircase, a spike raster, a polar rose, a parity plot, labels set
    along their curves and a field faded by its own significance through the
    same audit.

    The palette rows `main` prints alongside them are counted separately: they
    have no PNG, and this assertion is about the figures."""
    result = subprocess.run([sys.executable, str(GALLERY), str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert result.stdout.count("PASS  gallery-") == 19, result.stdout[-4000:]
    assert len(list(tmp_path.glob("gallery-*.png"))) == 19, result.stdout[-4000:]
    # An advisory row does not fail the run, so a gate that over-fires here
    # would be invisible to the assertions above. Banking is the newest and the
    # loosest, and the corpus is the only evidence that its band is not a
    # nuisance: the 9 line panels it reads across these figures report typical
    # segments from 20 to 63 degrees, well inside the band the row accepts.
    assert "[WARN] Banking" not in result.stdout, result.stdout[-4000:]


def test_running_the_scripts_elsewhere_leaves_the_committed_pngs_alone(tmp_path):
    """The reason both tests above take a directory.

    The example scripts write beside themselves by default, which is what
    someone running them wants and what the README's `python examples/demo.py`
    promises. It is not what a test run wants: the PNG bytes depend on the fonts
    installed locally, so every `pytest` left a dozen modified files in the
    working tree and a `git add -A` swept a binary diff into whatever commit
    came next. That happened, on the 0.5.0 release branch.

    Both scripts run here, so a directory argument that is accepted and then
    ignored fails this even though the tests above would still pass."""
    committed = sorted(DEMO.parent.glob("*.png"))
    assert len(committed) == 20, [p.name for p in committed]
    before = {path: (path.stat().st_mtime_ns, path.stat().st_size)
              for path in committed}

    for script in (DEMO, GALLERY):
        result = subprocess.run([sys.executable, str(script), str(tmp_path)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]

    after = {path: (path.stat().st_mtime_ns, path.stat().st_size)
             for path in committed}
    rewritten = [path.name for path in committed if before[path] != after[path]]
    assert not rewritten, (
        f"{rewritten} were rewritten by a run that named another directory")
