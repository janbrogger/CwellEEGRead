"""TST011 / DES017: the development environment. The full check - `./setup.sh` on a
fresh clone followed by the test suite - is the CI job in .github/workflows/tests.yml;
these are the parts that can be checked in any checkout."""
import importlib.metadata
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    except OSError:
        pytest.skip("git not available")


def test_venv_and_caches_are_ignored():
    # paths inside the directories: "dir/" patterns match a bare name only if it exists as a directory
    for p in (".venv/bin/python", ".cache/eeglab-src/x", "testdata/private/x.edf", "cwelleegread.egg-info/PKG-INFO"):
        assert git("check-ignore", "-q", p).returncode == 0, f"{p} is not gitignored"


def test_doorstop_matches_the_pin():
    pin = re.search(r"^doorstop==(\S+)", (ROOT / "requirements-dev.txt").read_text(), re.M).group(1)
    try:
        installed = importlib.metadata.version("doorstop")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("doorstop not installed (run ./setup.sh)")
    assert installed == pin


def test_setup_script_is_valid_and_installs_the_package():
    text = (ROOT / "setup.sh").read_text()
    assert "requirements-dev.txt" in text and "pip install --quiet -e ." in text
    bash = shutil.which("bash")
    if bash:
        assert subprocess.run([bash, "-n", str(ROOT / "setup.sh")]).returncode == 0
    assert git("ls-files", "-s", "setup.sh").stdout.startswith("100755"), "setup.sh not executable in git"


def test_runtime_dependencies_agree():
    """pyproject.toml (pip install) and requirements.txt list the same runtime packages."""
    tomllib = pytest.importorskip("tomllib")     # Python 3.11+
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    req = [l.split("#")[0].strip() for l in (ROOT / "requirements.txt").read_text().splitlines()]
    assert sorted(deps) == sorted(l for l in req if l)
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]["cwelleegread"] == "cwelleegread.__main__:main"
