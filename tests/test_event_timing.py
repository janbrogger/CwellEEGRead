"""REQ021 / TST016: events placed on the sample clock (StartOffset ticks through
the frames' tick spans) versus by wall-clock stamp (the vendor's rule). The two
clocks drift about 96 ppm on the Essentia recordings; the photic flash
response shows which axis the samples are on."""
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import convert

ROOT = Path(__file__).resolve().parents[1]
CASES = [("cadwell-export2", 65, 95), ("cadwell-export3", 85, 115)]   # export, expected drift range over the photic run (ms)


def flash_average(edf_path, rate=500, pre=0.05, post=0.35):
    with pyedflib.EdfReader(str(edf_path)) as f:
        on, _, tx = f.readAnnotations()
        labels = f.getSignalLabels()
        o1 = f.readSignal(labels.index("EEG O1-Cz")); o2 = f.readSignal(labels.index("EEG O2-Cz"))
    flashes = [o for o, t in zip(on, tx) if t == "Photic Stim"]
    a, b = int(pre * rate), int(post * rate)
    ep = np.stack([(o1[i - a:i + b] + o2[i - a:i + b]) / 2 for i in (int(round(o * rate)) for o in flashes)])
    ep -= ep[:, :a].mean(axis=1, keepdims=True)
    avg = ep.mean(axis=0); t_ms = np.arange(-a, b) / rate * 1e3
    w = (t_ms >= 0) & (t_ms <= 300)
    return flashes, t_ms[w][np.argmax(np.abs(avg[w]))]


@pytest.mark.parametrize("export, drift_lo, drift_hi", CASES)
def test_ticks_versus_stamp(tmp_path, export, drift_lo, drift_hi):
    base = ROOT / "testdata" / "public" / export
    if not (base / "native-export").exists():
        pytest.skip("public test export missing")
    rec = open_recording(str(base))
    out = {}
    for et in ("ticks", "stamp"):
        out[et] = tmp_path / f"{et}.edf"
        report = convert(rec, str(out[et]), mode="raw", event_timing=et, all_events=True, gaps="pad")
        assert report["event_timing"] == et
    assert convert(rec, str(tmp_path / "auto.edf"), mode="raw")["event_timing"] == "ticks"
    assert convert(rec, str(tmp_path / "vendor.edf"), mode="vendor")["event_timing"] == "stamp"
    flashes_t, peak_t = flash_average(out["ticks"])
    flashes_s, peak_s = flash_average(out["stamp"])
    assert len(flashes_t) == len(flashes_s) == 244
    # the stamp placement is early by the clock drift accumulated at the photic run
    # (the stamp clock runs behind the sample clock), and the drift keeps growing over the run
    diff_ms = 1e3 * (np.array(flashes_t) - np.array(flashes_s))
    assert diff_ms.min() > drift_lo and diff_ms.max() < drift_hi and 0 < np.ptp(diff_ms) < 15, (diff_ms.min(), diff_ms.max())
    # the same difference the frames show: tick clock minus stamp clock at that time
    origin = rec.frame_index[0]["timestamp"]; first = next(rec.frames())
    ev = next(v for v in rec.events() if v.text == "Photic Stim")
    frame_lag = {}                                   # tick seconds minus stamp seconds per frame
    for fi in rec.frame_index:
        frame_lag[fi["number"]] = (fi["number"] - first.number) - (fi["timestamp"] - origin).total_seconds()
    k = max(n for n in frame_lag if n <= ev.start_ticks / 1e7)
    expected = 1e3 * ((ev.start_ticks - first.start_ticks) / 1e7 - (ev.start - origin).total_seconds())
    assert abs(diff_ms[0] - expected) < 1.0 and abs(1e3 * frame_lag[k] - expected) < 2.0
    # physiology: a flash VEP on the sample clock, the same complex shifted later by stamp
    assert peak_t < 150, peak_t
    assert peak_s > 170, peak_s


def test_vendor_mode_ticks_follow_the_removed_samples(tmp_path):
    """Vendor mode removes samples (vendor_resample); with --event-timing ticks the
    onsets are mapped onto the resampled axis (DES021). On export 1 (Apollo, 250 Hz,
    ~251-sample frames) the uncorrected onsets drift up to 8 samples (32 ms) late."""
    from cwelleegread.edf import (read_padded, vendor_resample, vendor_raw_positions,
                                  raw_to_output_position)
    from cwelleegread.ezdata import UNIT_UV
    base = ROOT / "testdata" / "public" / "cadwell-export1"
    if not (base / "native-export").exists():
        pytest.skip("public test export missing")
    rec = open_recording(str(base))
    # the position map reproduces the resampled data exactly: copied samples on their
    # raw index, the two-point means half-way between their raw neighbours
    data, _, per_frame, _ = read_padded(rec, UNIT_UV)
    out, removed, _ = vendor_resample(data, per_frame, rec.sample_rate)
    pos = vendor_raw_positions(removed, len(out))
    assert len(removed) >= 8 and np.all(np.diff(pos) > 0)
    for j in (0, 13, 31):
        assert np.allclose(out[:, j], np.interp(pos, np.arange(len(data)), data[:, j]))
    assert raw_to_output_position(float(removed[-1]) + 5, pos) == pytest.approx(removed[-1] + 5 - len(removed))

    rep_raw = convert(rec, str(tmp_path / "raw.edf"), mode="raw", event_timing="ticks", all_events=True)
    rep_ven = convert(rec, str(tmp_path / "ven.edf"), mode="vendor", event_timing="ticks", all_events=True)
    assert rep_ven["samples_removed_by_vendor_rule"] == removed
    with pyedflib.EdfReader(str(tmp_path / "raw.edf")) as f:
        raw_on = dict((t, o) for o, _, t in zip(*f.readAnnotations()) if not t.startswith("Recording gap"))
    with pyedflib.EdfReader(str(tmp_path / "ven.edf")) as f:
        ven_on = dict((t, o) for o, _, t in zip(*f.readAnnotations()))
    common = sorted(set(raw_on) & set(ven_on), key=raw_on.get)
    assert len(common) >= 3
    rate = rec.sample_rate
    for t in common:
        p = raw_on[t] * rate
        n_before = sum(r < p for r in removed)
        assert abs(ven_on[t] * rate - (p - n_before)) <= 1.0, t   # within one sample of the mapped position
    late = common[-1]
    assert raw_on[late] - ven_on[late] > 0.02      # the correction is material at the end (~32 ms)
