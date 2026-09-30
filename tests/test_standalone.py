"""TST019 - the standalone program file and its README (REQ023, DES023)."""
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from cwelleegread import __version__
from cwelleegread.edfread import read_edf
from cwelleegread.selftest import BUNDLED

ROOT = Path(__file__).resolve().parents[1]
STANDALONE = ROOT / "uses" / "standalone"
E1 = ROOT / "testdata" / "public" / "cadwell-export1"

pytestmark = pytest.mark.skipif(not (E1 / "native-export").exists(), reason="public test export missing")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("standalone")
    r = subprocess.run([sys.executable, str(STANDALONE / "build.py"), "--outdir", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_archive_contents(built):
    folder = f"cwelleegread-standalone-{__version__}"
    with zipfile.ZipFile(built / f"{folder}.zip") as z:
        assert sorted(z.namelist()) == [f"{folder}/{n}" for n in ("LICENSE", "README.md", "cwelleegread.pyz")]
        assert z.read(f"{folder}/README.md") == (STANDALONE / "README.md").read_bytes()
    with zipfile.ZipFile(built / "cwelleegread.pyz") as z:
        names = set(z.namelist())
        assert {"__main__.py", "cwelleegread/__main__.py", "cwelleegread/selftest.py", "cwelleegread/edf.py"} <= names
        for name, (_, sha) in BUNDLED.items():
            assert hashlib.sha256(z.read(f"cwelleegread/selftest_data/{name}")).hexdigest() == sha


def run_pyz(built, *args, cwd):
    return subprocess.run([sys.executable, str(built / "cwelleegread.pyz"), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True)


def test_pyz_selftest_uses_its_bundled_data(built, tmp_path):
    r = run_pyz(built, "selftest", "--json", tmp_path / "r.json", cwd=tmp_path)     # outside the repository
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout
    rep = json.loads((tmp_path / "r.json").read_text())
    assert rep["test_data"] == f"bundled in {built / 'cwelleegread.pyz'}"


def test_pyz_converts_and_reports_version(built, tmp_path):
    r = run_pyz(built, "--version", cwd=tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == __version__
    r = run_pyz(built, "convert", E1, tmp_path / "e1.edf", "--timezone", "UTC+01:00", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    e = read_edf(str(tmp_path / "e1.edf"))
    assert e.n_records == 45 and len(e.signals) == 32 and e.start.isoformat() == "2025-10-31T14:37:50"


def test_readme_is_short_and_names_the_shortcomings():
    text = (STANDALONE / "README.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 45
    for pattern in (r"schema 2\.5", r"Apollo", r"Essentia", r"--labels", r"microvolt", r"sample clock",
                    r"wall clock", r"Gaps", r"high-pass", r"Not handled", r"Windows", r"macOS", r"selftest"):
        assert re.search(pattern, text), f"README does not mention {pattern}"
