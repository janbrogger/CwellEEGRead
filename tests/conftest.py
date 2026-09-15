"""Shared fixtures.

Tests that need the clinical test recordings (never committed; see
testdata/README.md) request the ``testdata`` fixture and are skipped with
an explicit message when the folder or the manifest is missing (REQ011).
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTDATA = ROOT / "testdata" / "private"
MANIFEST = ROOT / "testdata" / "manifest.json"


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


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
    if not TESTDATA.is_dir():
        pytest.skip(f"private test recordings not present at {TESTDATA}")
    for rec in manifest["recordings"]:
        for key in ("cadwell", "native_edf", "native_csv"):
            entry = rec[key]
            path = TESTDATA / entry["file"]
            assert path.exists(), f"{path} listed in manifest but missing"
            assert sha256(path) == entry["sha256"], f"checksum mismatch for {path}"
    return TESTDATA
