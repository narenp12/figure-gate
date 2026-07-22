import sys
from pathlib import Path

import matplotlib

# Agg has no window and can measure text, which is what the checks need.
matplotlib.use("agg")

SKILL = Path(__file__).resolve().parent.parent / "skill"
SCRIPTS = SKILL / "scripts"
STYLE_SHEET = SKILL / "assets" / "figure.mplstyle"

sys.path.insert(0, str(SCRIPTS))
