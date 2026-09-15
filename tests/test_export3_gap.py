"""Third public export: 500 Hz Essentia recording with a 10 s break and both a
text and an EDF export from the vendor (REQ009/TST005 at 500 Hz, REQ019/TST015
gap handling, REQ004 start time and labels, TST002)."""
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import convert
from cwelleegread.ezdata import UNIT_UV

ROOT = Path(__file__).resolve().parents[1]
E3 = ROOT / "testdata" / "public" / "cadwell-export3"
TEXT = E3 / "text" / "cadwell3.txt"
NATIVE = E3 / "export-edf" / "cadwell3.edf"

pytestmark = pytest.mark.skipif(not (E3 / "native-export").exists(), reason="public test export 3 missing")


@pytest.fixture(scope="module")
def rec():
    return open_recording(str(E3))


@pytest.fixture(scope="module")
def raw_edf(tmp_path_factory, rec):
    out = tmp_path_factory.mktemp("edf") / "e3.edf"
    report = convert(rec, str(out), mode="raw", timezone="Europe/Oslo")
    with pyedflib.EdfReader(str(out)) as f:
        hdr = f.getHeader(); labels = f.getSignalLabels()
        data = np.column_stack([f.readSignal(i) for i in range(32)]); ann = list(zip(*f.readAnnotations()))
        res = [(f.getPhysicalMaximum(i) - f.getPhysicalMinimum(i)) / 65535 for i in range(32)]
        n_rec = f.datarecords_in_file
    return report, hdr, labels, data, ann, res, n_rec


def test_gap_in_index(rec):
    assert rec.sample_rate == 500 and len(rec.frame_index) == 1207
    assert [g["start_offset"] for g in rec.gaps] == [328] and [g["end_offset"] for g in rec.gaps] == [338]
    numbers = [f["number"] for f in rec.frame_index]
    assert numbers[0] == 1 and numbers[-1] == 1217 and set(range(328, 338)).isdisjoint(numbers)


def test_text_export_equivalence_at_500hz(rec):
    """The vendor text export (frames 30-61) equals the decoded samples within its 0.05 µV rounding."""
    frames = {fr.number: fr for fr in rec.frames() if 30 <= fr.number <= 61}
    dec = np.column_stack([np.concatenate([frames[k].samples[a] for k in range(30, 62)]) for a in rec.amp_inputs]) * UNIT_UV
    rows = [l.rstrip("\n") for l in open(TEXT, encoding="utf-8", errors="replace") if not l.startswith("%") and l.strip()]
    txt = np.array([[float(x.replace(",", ".")) for x in l.split("\t")[1:]] for l in rows]) * 1000.0
    assert txt.shape == dec.shape == (16000, 32)
    assert np.abs(dec - txt).max() <= 0.06


def test_gap_is_padded_and_annotated(raw_edf):
    """REQ019: the 10 missing frames become 10 s of zeros at 327-337 s, with a gap annotation."""
    report, hdr, labels, data, ann, res, n_rec = raw_edf
    assert n_rec == 1217 and report["frames_padded"] == 10
    assert report["gaps_padded"] == [{"start_second": 327.0, "seconds": 10.0}]
    gap = data[327 * 500:337 * 500]
    assert np.abs(gap).max() <= max(res)          # digital zero read back within one step
    assert np.abs(data[327 * 500 - 1]).max() > 1 and np.abs(data[337 * 500]).max() > 1
    texts = {t for _, _, t in ann}
    assert "Recording gap 10 s (padded with zeros)" in texts and "Stop Recording" in texts and "Start Recording" in texts
    stop = [o for o, _, t in ann if t == "Stop Recording"][0]
    assert 328.9 < stop < 329.0                       # 08:34:39.785 - 08:29:10.844


def test_labels_and_start_time_match_vendor(rec, raw_edf):
    """Essentia labels equal the vendor's; our start rule reproduces the vendor's start (frame 30 + clock offset)."""
    report, hdr, labels, data, ann, res, n_rec = raw_edf
    with pyedflib.EdfReader(str(NATIVE)) as f:
        vlabels = f.getSignalLabels(); vstart = f.getStartdatetime()
    assert labels == vlabels[:32]
    assert report["headbox"] == {"amp_type": 1, "layout_guid": "69e10080ea586145af1eb5a238dcb47b", "name": "Essentia", "known": True}
    frame30 = [fi for fi in rec.frame_index if fi["number"] == 30][0]["timestamp"]
    predicted = (frame30 + rec.clock_correction).astimezone(dt.timezone(dt.timedelta(hours=2))).replace(tzinfo=None)
    raw = open(NATIVE, "rb").read(); assert raw[176:184] == predicted.strftime("%H.%M.%S").encode()
    hdr_bytes = int(raw[184:192]); ns = int(raw[252:256])
    spr = [int(raw[256 + ns * 216 + i * 8:256 + ns * 216 + (i + 1) * 8]) for i in range(ns)]
    first_tal = raw[hdr_bytes + sum(spr[:-1]) * 2:hdr_bytes + sum(spr) * 2].split(b"\x14")[0]
    assert abs(float(first_tal) - predicted.microsecond / 1e6) < 1e-6


def test_vendor_edf_is_highpass_filtered(rec):
    """Documented finding: this vendor EDF export has a ~0.16-0.2 Hz high-pass applied; above 0.7 Hz it equals the raw data."""
    frames = {fr.number: fr for fr in rec.frames() if 30 <= fr.number <= 109}
    dec = np.concatenate([frames[k].samples[3] for k in range(30, 110)]) * UNIT_UV     # Fp1 = input 3
    with pyedflib.EdfReader(str(NATIVE)) as f:
        v = f.readSignal(2)[: len(dec)]
    n = len(dec)
    fa = np.abs(np.fft.rfft(dec - dec.mean())); fb = np.abs(np.fft.rfft(v - v.mean())); fr = np.fft.rfftfreq(n, 1 / 500)
    ratio = lambda lo, hi: fb[(fr >= lo) & (fr < hi)].sum() / fa[(fr >= lo) & (fr < hi)].sum()
    assert ratio(0.02, 0.1) < 0.5
    assert 0.97 < ratio(1, 30) < 1.03 and 0.97 < ratio(30, 100) < 1.03
