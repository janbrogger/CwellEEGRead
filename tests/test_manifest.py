"""TST008 / DES007: every test recording is listed in testdata/manifest.json with
sizes and SHA-256 checksums; the committed public ones are verified here (the
private ones by the conftest ``testdata`` fixture when present).
TST014 / DES001: the supported storage schema versions are documented in code and
each is represented by at least one manifest recording whose data carries it."""
import json
from pathlib import Path

import pytest

from conftest import FILE_KEYS, MANIFEST, sha256_of
from cwelleegread import open_recording
from cwelleegread.ezdata import SUPPORTED_SCHEMA_VERSIONS

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(MANIFEST.read_text(encoding="utf-8"))["recordings"]
PUBLIC = [r for r in DATA if r.get("location") == "public"]


def test_manifest_entries_are_complete():
    assert PUBLIC, "no public recordings listed"
    for rec in DATA:
        assert rec.get("location", "private") in ("public", "private")
        assert rec["id"] and rec["cadwell_software_version"] and rec["schema_version"]
        for key in FILE_KEYS:
            assert len(rec[key]["sha256"]) == 64 and rec[key]["bytes"] > 0, (rec["id"], key)


@pytest.mark.parametrize("rec", PUBLIC, ids=[r["id"] for r in PUBLIC])
def test_public_files_match_the_manifest(rec):
    base = ROOT / "testdata" / "public"
    if not (base / rec["cadwell"]["file"]).exists():
        pytest.skip(f"public test export {rec['id']} not checked out")
    for key in FILE_KEYS:
        path = base / rec[key]["file"]
        assert path.exists(), f"{path} listed in the manifest but missing"
        assert sha256_of(path) == rec[key]["sha256"], f"checksum mismatch for {path}"


def test_every_supported_version_has_a_test_recording():
    assert SUPPORTED_SCHEMA_VERSIONS
    listed = {r["schema_version"] for r in DATA}
    assert set(SUPPORTED_SCHEMA_VERSIONS) <= listed
    for rec in PUBLIC:                                     # the manifest's claim matches the data
        path = ROOT / "testdata" / "public" / rec["cadwell"]["file"]
        if path.exists():
            assert open_recording(str(path)).schema_version == rec["schema_version"], rec["id"]
