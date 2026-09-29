"""TST006 / DES006 / DES018: batch mode, the supported-version check, a corrupt
database, the installed console command and output piped into a closed reader."""
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from cwelleegread.ezdata import SUPPORTED_SCHEMA_VERSIONS

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "testdata" / "public" / "cadwell-export1"
E1_DATA = E1 / "native-export" / "CadLink" / "Data"

pytestmark = pytest.mark.skipif(not E1_DATA.exists(), reason="public test export missing")


def cli(*args):
    return subprocess.run([sys.executable, "-m", "cwelleegread", *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True)


def copy_record(dst):
    """Copy export 1's record files (not the media databases) to dst/CadLink/Data."""
    d = dst / "CadLink" / "Data"
    d.mkdir(parents=True)
    for p in E1_DATA.iterdir():
        if p.suffix in (".ezdataindex", ".ezdata", ".ezevents"):
            shutil.copy(p, d / p.name)
    return next(d.glob("*.ezdataindex"))


def set_schema(index, version):
    """Make `version` the recording's current schema (the last SchemaUpdateLog row's NewVersion)."""
    con = sqlite3.connect(index)
    con.execute("update SchemaUpdateLog set NewVersion = ? where rowid = "
                "(select rowid from SchemaUpdateLog order by TimeStamp desc limit 1)", (version,))
    con.commit()
    con.close()


def test_unsupported_schema_is_refused(tmp_path):
    index = copy_record(tmp_path / "rec")
    set_schema(index, "9.9")
    assert "9.9" not in SUPPORTED_SCHEMA_VERSIONS
    out = tmp_path / "x.edf"
    r = cli("convert", tmp_path / "rec", out)
    assert r.returncode == 1 and "unsupported Cadwell storage schema version 9.9" in r.stderr
    assert "Traceback" not in r.stderr and not out.exists() and not Path(str(out) + ".part").exists()
    r = cli("inspect", tmp_path / "rec")                    # still inspectable
    assert r.returncode == 0 and "schema 9.9 (NOT SUPPORTED)" in r.stdout
    r = cli("convert", tmp_path / "rec", out, "--allow-unsupported", "--json", tmp_path / "x.json")
    assert r.returncode == 0 and out.exists(), r.stderr
    rep = json.loads((tmp_path / "x.json").read_text())
    assert rep["schema_version"] == "9.9" and any("--allow-unsupported" in w for w in rep["warnings"])


def test_corrupt_database_gives_a_diagnostic(tmp_path):
    index = copy_record(tmp_path / "rec")
    index.write_bytes(index.read_bytes()[:3000])            # truncated SQLite file
    out = tmp_path / "x.edf"
    r = cli("convert", tmp_path / "rec", out)
    assert r.returncode == 1 and r.stderr.startswith("error:") and "Traceback" not in r.stderr
    assert not out.exists() and not Path(str(out) + ".part").exists()


def test_batch_converts_every_recording_and_reports_failures(tmp_path):
    src = tmp_path / "in"
    copy_record(src / "a")
    copy_record(src / "b" / "nested")                      # the same record again: -2 suffix
    bad = copy_record(src / "c")
    set_schema(bad, "9.9")
    outdir, summary = tmp_path / "out", tmp_path / "batch.json"
    r = cli("batch", src, outdir, "--reports", "--json", summary)
    assert r.returncode == 1, r.stdout + r.stderr           # one failure -> non-zero
    s = json.loads(summary.read_text())
    assert s["converted"] == 2 and s["failed"] == 1 and len(s["recordings"]) == 3
    stem = bad.name[:-len(".ezdataindex")]
    assert sorted(p.name for p in outdir.glob("*.edf")) == [f"{stem}-2.edf", f"{stem}.edf"]
    assert sorted(p.name for p in outdir.glob("*.json")) == [f"{stem}-2.json", f"{stem}.json"]
    failed = [x for x in s["recordings"] if x["status"] == "failed"]
    assert "UnsupportedVersionError" in failed[0]["error"] and not Path(failed[0]["output"]).exists()
    assert not list(outdir.glob("*.part"))
    # a second run refuses to overwrite without --force, then succeeds with it (bad one aside)
    r = cli("batch", src / "a", outdir)
    assert r.returncode == 1 and "exists" in r.stderr
    r = cli("batch", src / "a", outdir, "--force")
    assert r.returncode == 0, r.stderr
    r = cli("batch", tmp_path / "empty-nothing-here", outdir)
    assert r.returncode == 1 and "no .ezdataindex" in r.stderr


def test_console_command_and_broken_pipe():
    exe = shutil.which("cwelleegread", path=str(Path(sys.executable).parent))
    if exe is None:
        pytest.skip("package not installed (setup.sh runs `pip install -e .`)")
    r = subprocess.run([exe, "--version"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip()
    r = subprocess.run(f'"{exe}" inspect "{E1}" | head -1', shell=True, capture_output=True, text=True)
    assert r.stdout.startswith("record ") and "Traceback" not in r.stderr and "BrokenPipe" not in r.stderr
