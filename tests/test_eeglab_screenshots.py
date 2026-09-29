"""Screenshots of the EEGLAB plugin in EEGLAB's interface under GNU Octave
(TST018, automated part): tools/eeglab_screenshots.py must operate the real
file dialog, options dialog and naming dialog from outside (xdotool) and
show export 3 with pop_eegplot, writing four non-blank screenshots of the
expected shapes. Judging what they show is the manual part of TST018
(docs/screenshots/eeglab/README.md).

Skipped when Octave, Xvfb, xdotool, ImageMagick, EEGLAB (EEGLAB_DIR,
DIPFIT_DIR) or public export 3 is missing."""
import importlib.util
from pathlib import Path

import pytest
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eeglab_screenshots", ROOT / "tools" / "eeglab_screenshots.py")
shots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shots)

pytestmark = pytest.mark.skipif(bool(shots.missing()), reason="missing: " + ", ".join(shots.missing()))

EXPECTED = {  # file: (minimum width, minimum height)
    "1-file-dialog.png": (300, 200),
    "2-options-dialog.png": (500, 150),
    "3-naming-dialog.png": (300, 100),
    "4-eegplot-10s.png": (1200, 800),
}


def test_screenshots(tmp_path):
    shots.main(tmp_path)
    for name, (w, h) in EXPECTED.items():
        img = Image.open(tmp_path / name)
        assert img.width >= w and img.height >= h, (name, img.size)
        spread = ImageStat.Stat(img.convert("L")).stddev[0]
        assert spread > 10, f"{name} looks blank (grey-level spread {spread:.1f})"
