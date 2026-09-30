"""TST020 - the equivalence self-test (REQ024, DES024) on the public exports and on
vendor EDF files altered on purpose, and the EDF reader it relies on."""
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from cwelleegread import selftest
from cwelleegread.edf import resolve_timezone
from cwelleegread.edfread import read_edf

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "testdata" / "public"
E1, E2, E3 = PUB / "cadwell-export1", PUB / "cadwell-export2", PUB / "cadwell-export3"
E1_EDF = E1 / "edf" / "test.edf"
E2_EDF = E2 / "export-edf" / "cadwell2.edf"
E3_EDF = E3 / "export-edf" / "cadwell3.edf"                                   # starts at frame 30
E3F_EDF = PUB / "cadwell-export3-withfilter" / "export-edf" / "cadwell3-withfilter.edf"   # record origin

pytestmark = pytest.mark.skipif(not (E1 / "native-export").exists(), reason="public test export missing")


def run(*args, **kw):
    lines = []
    report = selftest.run(*args, out=lines.append, **kw)
    return report, "\n".join(lines)


def status(report):
    return {c["check"]: c["status"] for c in report["checks"]}


def check(report, name):
    return next(c for c in report["checks"] if c["check"] == name)


def edit_edf(src, dst, signals=None, raw=None):
    """Copy an EDF, applying signals(index, int16 samples of one record) -> new samples to every
    data signal and raw(bytes) -> bytes to the whole file."""
    b = bytearray(Path(src).read_bytes())
    if raw:
        b = bytearray(raw(bytes(b)))
    if signals:
        hdr, ns = int(b[184:192]), int(b[252:256])
        labels = [b[256 + 16 * i:256 + 16 * (i + 1)].decode().strip() for i in range(ns)]
        spr = [int(b[256 + 216 * ns + 8 * i:256 + 216 * ns + 8 * (i + 1)]) for i in range(ns)]
        data = np.frombuffer(bytes(b[hdr:]), dtype="<i2").copy().reshape(-1, sum(spr))
        off = np.concatenate([[0], np.cumsum(spr)])
        for i in range(ns):
            if labels[i] != "EDF Annotations":
                data[:, off[i]:off[i + 1]] = signals(i, data[:, off[i]:off[i + 1]])
        b[hdr:] = data.tobytes()
    Path(dst).write_bytes(bytes(b))
    return dst


# ------------------------------------------------------------------ passes
def test_bundled_selftest_passes():
    report, text = run()
    assert report["verdict"] == "PASS", text
    assert status(report) == {"bundled files": "PASS", "recording": "INFO", "alignment": "PASS", "signals": "PASS",
                              "start time": "PASS", "samples": "PASS", "gain and lag": "PASS", "annotations": "PASS"}
    al = report["alignment"]
    assert (al["first_frame"], al["last_frame"], al["utc_offset"], al["timezone_source"]) == (0, 44, "UTC+01:00", "inferred")
    s = check(report, "samples")
    assert (s["identical"], s["samples"], s["max_steps"]) == (341000, 352000, 1)
    assert [c["label"] for c in s["channels_differing"]] == ["EEG Cz-Cz"]        # vendor writes 0 µV as -1
    g = check(report, "gain and lag")
    assert abs(g["gain"] - 1) <= 1e-4 and g["lag_samples"] == 0 and g["channels"] == 31
    assert check(report, "annotations")["matched"] == 7
    assert "RESULT: PASS" in text


def test_cli_selftest_json_has_no_patient_fields(tmp_path):
    out = tmp_path / "r.json"
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "selftest", "--json", str(out)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(out.read_text())
    assert rep["verdict"] == "PASS" and len(rep["checks"]) == 8
    assert "patient" not in out.read_text().lower()
    assert "test_test" not in out.read_text() and "test_test" not in r.stdout   # the vendor file's patient name
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "selftest", str(E1)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "both" in r.stderr


@pytest.mark.parametrize("timezone", [None, "Europe/Oslo"])
@pytest.mark.parametrize("recording, edf, first", [
    (E2, E2_EDF, 1),                          # starts at the first stored frame
    (E3, E3F_EDF, 0),                         # starts at the record origin, before the first stored frame; one gap
    (E3, E3_EDF, 30),                         # part of the recording: from frame 30
])
def test_user_selftest_passes_on_essentia_exports(tmp_path, recording, edf, first, timezone):
    keep = tmp_path / "ours.edf"
    report, text = run(str(recording), str(edf), timezone=timezone, keep_edf=str(keep))
    assert report["verdict"] == "PASS", text
    assert report["alignment"]["first_frame"] == first and report["alignment"]["utc_offset"] == "UTC+02:00"
    assert report["alignment"]["timezone_source"] == ("given" if timezone else "inferred")
    assert report["conversion"]["highpass_hz"] == 0.16
    s = check(report, "samples")
    assert s["max_steps"] <= 1 and s["identical_share"] > 0.98
    assert keep.exists() and read_edf(str(keep)).n_records == read_edf(str(edf)).n_records


def test_unsupported_schema_is_converted_with_a_warning(tmp_path):
    d = tmp_path / "CadLink" / "Data"
    d.mkdir(parents=True)
    for p in (E1 / "native-export" / "CadLink" / "Data").iterdir():
        if p.suffix in (".ezdataindex", ".ezdata", ".ezevents"):
            shutil.copy(p, d / p.name)
    index = next(d.glob("*.ezdataindex"))
    con = sqlite3.connect(index)
    con.execute("update SchemaUpdateLog set NewVersion = '9.9' where rowid = "
                "(select rowid from SchemaUpdateLog order by TimeStamp desc limit 1)")
    con.commit(); con.close()
    report, text = run(str(tmp_path), str(E1_EDF))
    assert report["verdict"] == "PASS", text
    rec = check(report, "recording")
    assert rec["status"] == "WARN" and "9.9" in rec["detail"] and "NOT supported" in rec["detail"]


# ------------------------------------------------------------------ failures
def test_edf_of_another_recording_fails_alignment():
    report, text = run(str(E1), str(E2_EDF))
    assert report["verdict"] == "FAIL" and status(report)["alignment"] == "FAIL"
    assert "another recording" in text and "RESULT: FAIL" in text


def test_wrong_timezone_fails_alignment():
    report, text = run(timezone="UTC+03:00")
    assert report["verdict"] == "FAIL" and status(report)["alignment"] == "FAIL" and "--timezone" in text


def test_one_changed_sample_fails(tmp_path):
    def bump(i, x):
        if i == 4:
            x = x.copy(); x[10, 100] += 3
        return x
    edf = edit_edf(E1_EDF, tmp_path / "v.edf", signals=bump)
    report, text = run(str(E1), str(edf))
    assert report["verdict"] == "FAIL"
    assert status(report)["samples"] == "FAIL" and check(report, "samples")["max_steps"] == 3
    assert status(report)["signals"] == status(report)["annotations"] == "PASS"


def test_scale_error_below_one_step_is_caught_by_the_gain(tmp_path):
    """A 0.1 % scale error stays within one quantisation step on export 1 but not within the gain tolerance."""
    edf = edit_edf(E1_EDF, tmp_path / "v.edf", signals=lambda i, x: np.rint(x * 1.001).astype("<i2"))
    report, text = run(str(E1), str(edf))
    assert status(report)["samples"] == "PASS"
    assert status(report)["gain and lag"] == "FAIL" and check(report, "gain and lag")["gain"] > 1.0005
    assert report["verdict"] == "FAIL"


def test_changed_annotation_text_fails(tmp_path):
    edf = edit_edf(E1_EDF, tmp_path / "v.edf", raw=lambda b: b.replace(b"Paper Speed", b"Paper Sheep"))
    report, text = run(str(E1), str(edf))
    assert status(report)["annotations"] == "FAIL" and "Paper Sheep" in text and report["verdict"] == "FAIL"


def test_changed_label_fails_signals_but_samples_are_compared(tmp_path):
    def relabel(b):
        i = b.index(b"EEG Fp1-Cz")
        return b[:i] + b"EEG Fp1-XX" + b[i + 10:]
    edf = edit_edf(E1_EDF, tmp_path / "v.edf", raw=relabel)
    report, text = run(str(E1), str(edf))
    assert status(report)["signals"] == "FAIL" and "EEG Fp1-XX" in text
    assert status(report)["samples"] == "PASS" and report["verdict"] == "FAIL"


# ------------------------------------------------------------------ building blocks
def test_edfread_matches_pyedflib_and_reads_the_subsecond_start():
    pyedflib = pytest.importorskip("pyedflib")
    e = read_edf(str(E1_EDF))
    assert e.edf_type == "EDF+C" and e.n_records == 44 and len(e.signals) == 32
    assert e.start.isoformat() == "2025-10-31T14:37:50" and e.start_subsecond == pytest.approx(0.2766482, abs=1e-9)
    with pyedflib.EdfReader(str(E1_EDF)) as f:
        for i in range(32):
            assert np.array_equal(f.readSignal(i, digital=True), e.digital[i])
        onsets, _, texts = f.readAnnotations()
    assert [t for _, _, t in e.annotations] == list(texts)


def test_resolve_timezone():
    import datetime as dt
    assert resolve_timezone(None) == dt.timezone.utc
    assert resolve_timezone("UTC+01:00").utcoffset(None) == dt.timedelta(hours=1)
    assert resolve_timezone("UTC-05:30").utcoffset(None) == -dt.timedelta(hours=5, minutes=30)
    with pytest.raises(ValueError):
        resolve_timezone("Mars/Olympus")
