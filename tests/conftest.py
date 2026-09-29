"""Shared fixtures.

testdata/manifest.json lists every test recording with sizes and SHA-256
checksums (REQ007): "public" ones are committed under testdata/public/,
"private" (clinical) ones are supplied out of band under testdata/private/
and never committed. Tests that need the private recordings request the
``testdata`` fixture and are skipped with an explicit message when the
folder or its manifest entries are missing (REQ011).
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTDATA = ROOT / "testdata" / "private"
MANIFEST = ROOT / "testdata" / "manifest.json"
FILE_KEYS = ("cadwell", "native_edf", "native_csv")

_spec = importlib.util.spec_from_file_location("make_manifest", ROOT / "testdata" / "make_manifest.py")
make_manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_manifest)
sha256_of = make_manifest.sha256_of          # file, or a study folder (sorted paths + contents)


@pytest.fixture(scope="session")
def manifest():
    if not MANIFEST.exists():
        pytest.skip(f"no test-data manifest at {MANIFEST} (see testdata/README.md)")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not data.get("recordings"):
        pytest.skip("test-data manifest lists no recordings yet")
    return data


@pytest.fixture(scope="session")
def testdata(manifest):
    """The private Cadwell test recordings, verified against the manifest (TST008)."""
    private = [r for r in manifest["recordings"] if r.get("location", "private") == "private"]
    if not private:
        pytest.skip("test-data manifest lists no private recordings")
    if not TESTDATA.is_dir():
        pytest.skip(f"private test recordings not present at {TESTDATA}")
    for rec in private:
        for key in FILE_KEYS:
            entry = rec[key]
            path = TESTDATA / entry["file"]
            assert path.exists(), f"{path} listed in manifest but missing"
            assert sha256_of(path) == entry["sha256"], f"checksum mismatch for {path}"
    return TESTDATA
