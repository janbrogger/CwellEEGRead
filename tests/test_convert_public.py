"""Convert the public exports to EDF+ and check the result (TST001, TST002,
TST003 vendor mode, TST004, TST006, TST010 on public data)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import convert

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "testdata" / "public" / "cadwell-export1"
E2 = ROOT / "testdata" / "public" / "cadwell-export2"
NATIVE = E1 / "edf" / "test.edf"
LSB_VENDOR = 1125000 / 65535

pytestmark = pytest.mark.skipif(not (E1 / "native-export").exists(), reason="public test export missing")


def read_edf(path):
    with pyedflib.EdfReader(str(path)) as f:
        hdr = f.getHeader()
        sig = [f.getSignalHeader(i) for i in range(f.signals_in_file)]
        data = np.column_stack([f.readSignal(i) for i in range(f.signals_in_file)])
        ann = list(zip(*f.readAnnotations()))
        n_rec, rec_dur = f.datarecords_in_file, f.datarecord_duration
    return hdr, sig, data, ann, n_rec, rec_dur


@pytest.fixture(scope="module")
def vendor_edf(tmp_path_factory):
    out = tmp_path_factory.mktemp("edf") / "e1_vendor.edf"
    rec = open_recording(str(E1))
    report = convert(rec, str(out), mode="vendor", timezone="Europe/Oslo")
    return out, report


@pytest.fixture(scope="module")
def raw_edf(tmp_path_factory):
    out = tmp_path_factory.mktemp("edf") / "e1_raw.edf"
    rec = open_recording(str(E1))
    report = convert(rec, str(out), mode="raw")
    return out, report


def test_vendor_mode_reproduces_native_edf(vendor_edf):
    """TST002/TST003/TST004 in vendor-compatible mode against the Cadwell EDF export."""
    out, report = vendor_edf
    hdr, sig, data, ann, n_rec, rec_dur = read_edf(out)
    nhdr, nsig, ndata, nann, nn_rec, nrec_dur = read_edf(NATIVE)
    assert [s["label"] for s in sig] == [s["label"] for s in nsig]
    assert [s["sample_frequency"] for s in sig] == [s["sample_frequency"] for s in nsig]
    assert [(s["physical_min"], s["physical_max"]) for s in sig] == [(s["physical_min"], s["physical_max"]) for s in nsig]
    assert (n_rec, rec_dur) == (nn_rec, nrec_dur) == (44, 1.0)
    assert hdr["startdate"].replace(microsecond=0) == nhdr["startdate"].replace(microsecond=0)
    assert data.shape == ndata.shape == (11000, 32)
    nz = [c for c in range(32) if c != 14]
    diff = np.abs(data[:, nz] - ndata[:, nz])
    assert diff.max() <= LSB_VENDOR * 1.001, f"max {diff.max() / LSB_VENDOR:.2f} LSB at row {diff.max(axis=1).argmax()}"
    assert report["samples_removed_by_vendor_rule"] == [1224, 2449, 3674, 4899, 6124, 7349, 8574, 9799]
    # annotations: same onsets (to the ms) and texts
    mine = sorted((round(o, 3), t) for o, d, t in ann)
    theirs = sorted((round(o, 3), t) for o, d, t in nann)
    assert mine == theirs


def test_vendor_start_subsecond(vendor_edf):
    """The vendor writes the first record onset +0.2766482 (frame-0 time + PcTimeSync); we write the same to the ms."""
    out, _ = vendor_edf
    raw = open(out, "rb").read()
    ns = int(raw[252:256]); hdr = int(raw[184:192])
    spr = [int(raw[256 + ns * 216 + i * 8:256 + ns * 216 + (i + 1) * 8]) for i in range(ns)]
    tal = raw[hdr + sum(spr[:-1]) * 2: hdr + sum(spr) * 2].split(b"\x14")[0]
    assert tal.startswith(b"+0.2766")
    assert raw[168:176] == b"31.10.25" and raw[176:184] == b"14.37.50"


def test_raw_mode_round_trip(raw_edf):
    """TST001/TST010: our own EDF reads back to the decoded samples within its resolution, keeps every whole second."""
    out, report = raw_edf
    rec = open_recording(str(E1))
    data, amps, per_frame = rec.read_signals()
    hdr, sig, edf, ann, n_rec, _ = read_edf(out)
    assert n_rec == 45 and edf.shape == (11250, 32) and report["samples_dropped_at_end"] == 8
    for j, s in enumerate(sig):
        res = (s["physical_max"] - s["physical_min"]) / 65535
        # range is data-driven: resolution must be within ~2.2x the data's own peak / 65535
        assert res <= max(0.05, 2.3 * np.abs(data[:11250, j]).max() / 65535), f"{s['label']} resolution {res:.3f} uV too coarse"
        assert np.abs(edf[:, j] - data[:11250, j]).max() <= res * 0.51 + 1e-9
    assert hdr["startdate"].isoformat().startswith("2025-10-31T13:37:50")   # UTC by default
    assert len(ann) == 7


def test_export2_converts(tmp_path):
    """The 16-minute, 500 Hz, two-track recording converts and reads back."""
    out = tmp_path / "e2.edf"
    rec = open_recording(str(E2))
    report = convert(rec, str(out), mode="raw", timezone="Europe/Oslo")
    hdr, sig, data, ann, n_rec, _ = read_edf(out)
    assert rec.sample_rate == 500 and n_rec == 961 and data.shape == (480500, 32)
    assert report["samples_per_frame"] == {"500": 961}
    assert len(ann) == report["annotations_written"] == 52      # vendor policy: no individual photic flashes
    assert any("Hyperventilation" in t for _, _, t in ann) and any(t.startswith("Photic Start") for _, _, t in ann)
    assert hdr["startdate"].isoformat().startswith("2026-06-12T12:58:54")
    assert np.all(data[:, 14] == pytest.approx(0, abs=0.2))   # Cz reference


def test_cli_behaviour(tmp_path):
    """TST006: exit codes, JSON report, no partial file on failure."""
    out = tmp_path / "cli.edf"; rep = tmp_path / "cli.json"
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "convert", str(E1), str(out), "--json", str(rep)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.exists() and json.loads(rep.read_text())["seconds"] == 45
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "convert", str(tmp_path / "nope"), str(tmp_path / "x.edf")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and "error" in r.stderr.lower() and not (tmp_path / "x.edf").exists()
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "convert", str(E1), str(out)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0    # refuses to overwrite without --force
