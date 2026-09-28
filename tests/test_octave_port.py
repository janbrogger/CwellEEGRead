"""Run the MATLAB/Octave port's self-test under GNU Octave when it is installed
(TST001-style round trip of the native reader: decoder equals the Python
decoder on stored frames; native SQLite read via the JDBC backend equals the
Python index/labels/events; export-1 read equals the vendor text export)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "uses" / "EEGLAB" / "cadwellio"
EXPORTS = [ROOT / "testdata" / "public" / f"cadwell-export{i}" for i in (1, 2, 3)]

octave = shutil.which("octave-cli") or shutil.which("octave")
pytestmark = pytest.mark.skipif(octave is None or not all(e.exists() for e in EXPORTS),
                                reason="GNU Octave or the public test exports are not available")


def test_octave_selftest(tmp_path):
    for i, e in enumerate(EXPORTS, 1):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_matlab_reference.py"), str(e), str(tmp_path / f"export{i}"), "20"],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    code = (f"addpath('{PLUGIN}'); r = cadwell_selftest('{tmp_path}'); "
            "disp(cadwell_sqlite('backends')); exit(double(~r.ok));")
    r = subprocess.run([octave, "--no-gui", "--quiet", "--eval", code], cwd=ROOT, capture_output=True, text=True, timeout=1800)
    print(r.stdout, r.stderr)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
