"""EDF variants and header fields (REQ002 / DES002 / TST001, REQ019 / DES019 / TST015):
EDF+D for recordings with gaps on request, plain EDF when nothing needs EDF+, the prefilter
field when the vendor high-pass is applied, and read-back by MNE-Python as the
second independent reader."""
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import HIGHPASS_PREFILTER, convert
from cwelleegread.edfwrite import write_edf

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "testdata" / "public" / "cadwell-export1"
E3 = ROOT / "testdata" / "public" / "cadwell-export3"

needs_e1 = pytest.mark.skipif(not (E1 / "native-export").exists(), reason="public test export 1 missing")
needs_e3 = pytest.mark.skipif(not (E3 / "native-export").exists(), reason="public test export 3 missing")


def read_raw_edf(path):
    """Independent minimal EDF/EDF+ reader for what pyedflib (EDFlib) refuses: EDF+D.
    Returns (reserved field, signal labels, per-signal digital samples, record onsets
    from the time-keeping TALs, annotations [(onset, duration, text)])."""
    b = Path(path).read_bytes()
    hbytes, reserved, n_rec, ns = int(b[184:192]), b[192:236].decode().strip(), int(b[236:244]), int(b[252:256])
    field = lambda off, w: [b[256 + off * ns + i * w:256 + off * ns + (i + 1) * w].decode().strip() for i in range(ns)]
    labels = field(0, 16)
    spr = [int(x) for x in field(16 + 80 + 8 * 5 + 80, 8)]      # after label, transducer, dimension, pmin..dmax, prefilter
    rec_len = 2 * sum(spr)
    body = np.frombuffer(b[hbytes:hbytes + n_rec * rec_len], dtype="<i2").reshape(n_rec, sum(spr))
    offs = np.concatenate([[0], np.cumsum(spr)])
    ann_i = labels.index("EDF Annotations") if "EDF Annotations" in labels else None
    sig = [body[:, offs[i]:offs[i + 1]].ravel() for i in range(ns) if i != ann_i]
    onsets, ann = [], []
    if ann_i is not None:
        for k in range(n_rec):
            raw = body[k, offs[ann_i]:offs[ann_i + 1]].tobytes()
            tals = [t for t in raw.split(b"\x00") if t]
            onsets.append(float(tals[0].split(b"\x14")[0]))
            for t in tals[1:]:
                parts = t.split(b"\x14")
                head = parts[0].split(b"\x15")
                ann.append((float(head[0]), float(head[1]) if len(head) > 1 else -1.0, parts[1].decode("utf-8")))
    return reserved, [l for i, l in enumerate(labels) if i != ann_i], sig, onsets, ann


@pytest.fixture(scope="module")
def e3_pad_and_d(tmp_path_factory):
    d = tmp_path_factory.mktemp("e3")
    rec = open_recording(str(E3))
    rep_d = convert(rec, str(d / "disc.edf"), mode="raw", gaps="discontinuous")
    rep_p = convert(rec, str(d / "pad.edf"), mode="raw")                  # default: gaps='pad'
    return d, rep_d, rep_p


@needs_e3
def test_gaps_padded_by_default_and_edf_plus_d_on_request(e3_pad_and_d):
    d, rep_d, rep_p = e3_pad_and_d
    assert rep_d["edf_type"] == "EDF+D" and rep_d["gaps_policy"] == "discontinuous"
    assert rep_p["edf_type"] == "EDF+C" and rep_p["gaps_policy"] == "pad"
    assert rep_d["records_written"] == 1207 and rep_d["records_omitted_in_gaps"] == 10
    reserved, _, sig_d, onsets, ann = read_raw_edf(d / "disc.edf")
    reserved_p, _, sig_p, onsets_p, _ = read_raw_edf(d / "pad.edf")
    assert reserved == "EDF+D" and reserved_p == "EDF+C" and len(onsets_p) == 1217
    subsec = onsets_p[0]
    # data start = frame 1; the gap is frames 328-337 = seconds 327-336 after it
    expected = [k for k in range(1217) if not 327 <= k < 337]
    assert np.allclose(np.array(onsets) - subsec, expected, atol=1e-6)
    keep = np.repeat(np.isin(np.arange(1217), expected), 500)
    for j in range(32):                                    # the same samples as the padded file minus the gap
        assert np.array_equal(sig_d[j], sig_p[j][keep])
    gap = [a for a in ann if a[2].startswith("Recording gap")]
    assert len(gap) == 1 and gap[0][2] == "Recording gap 10 s" and abs(gap[0][0] - subsec - 327) < 1e-6
    assert gap[0][1] == 10
    # Stop/Start Recording (inside the gap) are still written, in the record before the gap
    assert {"Stop Recording", "Start Recording"} <= {a[2] for a in ann}


@needs_e3
def test_edf_plus_d_rules(tmp_path):
    x = [np.zeros(3 * 10)]
    h = [dict(label="A", dimension="uV", sample_frequency=10, physical_min=-1, physical_max=1,
              digital_min=-32768, digital_max=32767)]
    start = dt.datetime(2026, 1, 1, 12, 0, 0, 250000)
    with pytest.raises(ValueError):
        write_edf(tmp_path / "a.edf", x, h, start=start, edf_type="edf+d", record_onsets=[0, 0.5, 3])
    with pytest.raises(ValueError):
        write_edf(tmp_path / "a.edf", x, h, start=start, edf_type="edf", annotations=[(0, -1, "x")])
    with pytest.raises(ValueError):                         # plain EDF has no sub-second start
        write_edf(tmp_path / "a.edf", x, h, start=start, edf_type="edf")
    rec = open_recording(str(E3))
    with pytest.raises(ValueError):
        convert(rec, str(tmp_path / "v.edf"), mode="vendor", gaps="discontinuous")


@needs_e1
def test_discontinuous_without_gaps_stays_continuous(tmp_path):
    rep = convert(open_recording(str(E1)), str(tmp_path / "e1.edf"), mode="raw", gaps="discontinuous")
    assert rep["edf_type"] == "EDF+C" and rep["gaps_policy"] == "pad" and rep["records_omitted_in_gaps"] == 0


@needs_e1
def test_plain_edf_when_nothing_needs_edf_plus(tmp_path):
    rec = open_recording(str(E1))
    rep = convert(rec, str(tmp_path / "plus.edf"), mode="raw")
    assert rep["edf_type"] == "EDF+C"                     # annotations and a sub-second start
    rec.events = lambda: []                                # nothing to annotate ...
    rep = convert(rec, str(tmp_path / "still_plus.edf"), mode="raw")
    assert rep["edf_type"] == "EDF+C"                     # ... but the start is 13:37:50.276647
    rec.start_time = rec.start_time.replace(microsecond=0)
    rep = convert(rec, str(tmp_path / "plain.edf"), mode="raw")
    assert rep["edf_type"] == "EDF" and rep["annotations_written"] == 0
    reserved, labels, sig, onsets, _ = read_raw_edf(tmp_path / "plain.edf")
    assert reserved == "" and "EDF Annotations" not in labels and len(labels) == 32 and onsets == []
    with pyedflib.EdfReader(str(tmp_path / "plain.edf")) as f:
        assert f.filetype == pyedflib.FILETYPE_EDF and f.signals_in_file == 32 and f.datarecords_in_file == 45
    _, _, sig_plus, _, _ = read_raw_edf(tmp_path / "plus.edf")
    assert all(np.array_equal(a, b) for a, b in zip(sig, sig_plus))


@needs_e1
def test_forced_plain_edf_drops_annotations_with_warnings(tmp_path):
    rec = open_recording(str(E1))
    rep = convert(rec, str(tmp_path / "e.edf"), mode="raw", edf_format="edf")
    assert rep["edf_type"] == "EDF" and rep["annotations_written"] == 0
    assert any("annotation(s) not written" in w for w in rep["warnings"])
    assert any("truncated by 0.276647 s" in w for w in rep["warnings"])
    with pyedflib.EdfReader(str(tmp_path / "e.edf")) as f:
        assert f.getStartdatetime() == dt.datetime(2025, 10, 31, 13, 37, 50)


@needs_e1
def test_prefilter_field_states_the_highpass(tmp_path):
    rec = open_recording(str(E1))
    for kw, expected in (({"mode": "vendor"}, ""),                         # Apollo: vendor applies no high-pass
                         ({"mode": "raw", "highpass": "on"}, HIGHPASS_PREFILTER),
                         ({"mode": "raw"}, "")):
        out = tmp_path / "p.edf"
        convert(rec, str(out), **kw)
        with pyedflib.EdfReader(str(out)) as f:
            assert [f.getPrefilter(i) for i in range(32)] == [expected] * 32, kw
    assert HIGHPASS_PREFILTER == "HP: unknown (0.16 Hz?)"


@needs_e1
@pytest.mark.parametrize("mode", ["raw", "vendor"])
def test_mne_reads_back(tmp_path, mode):
    """TST001 with MNE-Python, the second independent reader."""
    mne = pytest.importorskip("mne")
    rec = open_recording(str(E1))
    out = tmp_path / f"{mode}.edf"
    rep = convert(rec, str(out), mode=mode)
    raw = mne.io.read_raw_edf(str(out), preload=True, verbose="error")
    assert len(raw.ch_names) == 32 and raw.info["sfreq"] == 250
    assert raw.n_times == rep["seconds"] * 250
    assert len(raw.annotations) == rep["annotations_written"]
    with pyedflib.EdfReader(str(out)) as f:
        ref = np.vstack([f.readSignal(i) for i in range(32)])        # µV
        res = np.array([(f.getPhysicalMaximum(i) - f.getPhysicalMinimum(i)) / 65535 for i in range(32)])
        start = f.getStartdatetime()
    assert np.all(np.abs(raw.get_data() * 1e6 - ref) <= res[:, None] * 0.51)
    # MNE keeps only the whole-second start of the header (pyedflib's sub-second value is
    # also off: .027665 for the .276647 in the time-keeping TAL), so compare whole seconds
    assert raw.info["meas_date"].replace(tzinfo=None) == start.replace(microsecond=0)
