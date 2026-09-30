"""What the vendor's export filters do (public exports 2 and 3, and 3-withfilter):
the text export is always the raw data; the EDF export ignores the viewer's
filters but applies its own ~0.16 Hz high-pass on Essentia recordings."""
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.ezdata import UNIT_UV

ROOT = Path(__file__).resolve().parents[1] / "testdata" / "public"
E2, E3, E3F = ROOT / "cadwell-export2", ROOT / "cadwell-export3", ROOT / "cadwell-export3-withfilter"
TZ = dt.timezone(dt.timedelta(hours=2))

pytestmark = pytest.mark.skipif(not (E3F / "native-export").exists(), reason="public export 3-withfilter missing")


def read_text(path):
    if str(path).endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(path) as z:
            name = [n for n in z.namelist() if n.endswith(".txt")][0]
            lines = z.read(name).decode("utf-8", "replace").split("\n")
    else:
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    rows = [l for l in lines if not l.startswith("%") and l.strip()]
    stamps = [r.split("\t")[0] for r in rows]
    return stamps, np.array([l.replace(",", ".").split("\t")[1:] for l in rows], dtype=np.float64) * 1000.0


def frames_from(rec, first_stamp, n_frames):
    """Decoded µV block for the n frames starting at the frame whose time stamp falls in the given local second."""
    t0 = dt.datetime.strptime(first_stamp, "%d.%m.%Y %H:%M:%S").replace(tzinfo=TZ)
    frames = {fr.number: fr for fr in rec.frames()}
    n0 = [n for n, fr in frames.items() if 0 <= (fr.timestamp - t0).total_seconds() < 1][0]
    return np.column_stack([np.concatenate([frames[k].samples[a] for k in range(n0, n0 + n_frames)])
                            for a in rec.amp_inputs]) * UNIT_UV, n0


@pytest.mark.parametrize("export, text", [(E2, E2 / "cadwell2.txt"), (E3F, E3F / "text" / "cadwell3-with-filter.zip")])
def test_text_export_is_raw_even_with_viewer_filters(export, text):
    """TST005: text exports equal the raw frames within 0.05 µV rounding - also the full-range one made
    with a 10-15 Hz viewer filter (the gap is omitted in the text, so compare frame by frame)."""
    rec = open_recording(str(export))
    stamps, txt = read_text(text)
    t0 = dt.datetime.strptime(stamps[0], "%d.%m.%Y %H:%M:%S").replace(tzinfo=TZ)
    frames = [fr for fr in rec.frames() if (fr.timestamp - t0).total_seconds() >= 0]
    n_frames = len(txt) // rec.sample_rate
    dec = np.column_stack([np.concatenate([fr.samples[a] for fr in frames[:n_frames]]) for a in rec.amp_inputs]) * UNIT_UV
    assert dec.shape == txt.shape
    assert np.abs(dec - txt).max() <= 0.06


def test_full_text_exports_identical_and_differ_only_in_header():
    """The two full-range text exports (viewer unfiltered / 10-15 Hz) have identical data rows; only the
    patient header differs (one was exported without 'Anonymize Information')."""
    import zipfile
    def lines(p):
        with zipfile.ZipFile(p) as z:
            return z.read([n for n in z.namelist() if n.endswith(".txt")][0]).decode("utf-8", "replace").split("\n")
    a = lines(E3 / "text" / "cadwell3.zip"); b = lines(E3F / "text" / "cadwell3-with-filter.zip")
    assert [l for l in a if not l.startswith("%")] == [l for l in b if not l.startswith("%")]
    diff = [(x, y) for x, y in zip(a, b) if x.startswith("%") and x != y]
    assert all("Patient" in x for x, _ in diff) and diff


def test_native_files_identical_between_export3_versions():
    a = sorted((E3 / "native-export" / "CadLink" / "Data").glob("*.ez*")); b = sorted((E3F / "native-export" / "CadLink" / "Data").glob("*.ez*"))
    assert [p.name for p in a] == [p.name for p in b]
    for p, q in zip(a, b):
        assert p.read_bytes() == q.read_bytes()


def test_edf_exports_ignore_viewer_filter_but_share_a_highpass():
    """The two vendor EDFs of export 3 (viewer unfiltered vs 10-15 Hz band-pass) are identical after each file's
    own ~10 s high-pass start-up transient; neither is band-passed."""
    def read(p):
        with pyedflib.EdfReader(str(p)) as f:
            return np.column_stack([f.readSignal(i) for i in range(32)])
    u = read(E3 / "export-edf" / "cadwell3.edf")            # starts at frame 30
    v = read(E3F / "export-edf" / "cadwell3-withfilter.edf")  # starts at tick 0 (frame 0 padded)
    lsb = (23919.03 + 23919.0) / 65535
    n = len(u)
    d = np.abs(u[:n] - v[30 * 500:30 * 500 + n]).max(axis=1) / lsb
    assert (d[6000:] > 1.001).sum() == 0            # identical beyond the transient of the later-starting file
    assert d[:5000].max() > 100                      # the transient itself is large
    # the filtered-viewer EDF still holds 1-3 Hz and 20-30 Hz content comparable to the raw data
    rec = open_recording(str(E3)); frames = {fr.number: fr for fr in rec.frames() if 1 <= fr.number <= 120}
    raw = np.concatenate([frames[k].samples[3] for k in range(1, 121)]) * UNIT_UV     # Fp1
    e = v[500:500 + len(raw), 2]
    fr = np.fft.rfftfreq(len(raw), 1 / 500); fa = np.abs(np.fft.rfft(raw - raw.mean())); fb = np.abs(np.fft.rfft(e - e.mean()))
    ratio = lambda lo, hi: fb[(fr >= lo) & (fr < hi)].sum() / fa[(fr >= lo) & (fr < hi)].sum()
    assert ratio(1, 3) > 0.9 and ratio(20, 30) > 0.9 and ratio(0.02, 0.1) < 0.5


def test_export2_vendor_edf_matches_raw_in_band():
    """Every export-2 EDF channel is its raw amplifier input (unit gain, corr > 0.98 in 1-30 Hz), start = frame 1."""
    scipy_signal = pytest.importorskip("scipy.signal")
    rec = open_recording(str(E2)); raw, amps, _ = rec.read_signals()
    with pyedflib.EdfReader(str(E2 / "export-edf" / "cadwell2.edf")) as f:
        edf = np.column_stack([f.readSignal(i) for i in range(32)])
        assert f.datarecords_in_file == 960
    raw_hdr = open(E2 / "export-edf" / "cadwell2.edf", "rb").read(256)
    predicted = (rec.frame_index[0]["timestamp"] + rec.clock_correction).astimezone(TZ)
    assert raw_hdr[176:184] == predicted.strftime("%H.%M.%S").encode()
    b, a = scipy_signal.butter(4, [1, 30], btype="band", fs=500)
    s = slice(40 * 500, 100 * 500)
    R = scipy_signal.filtfilt(b, a, raw[s], axis=0); E = scipy_signal.filtfilt(b, a, edf[s], axis=0)
    for j in range(32):
        if j == 14:
            continue
        c = np.corrcoef(R[:, j], E[:, j])[0, 1]
        assert c > 0.98, f"column {j} corr {c:.3f}"


@pytest.mark.parametrize("export, vendor_edf, kw", [
    (E2, E2 / "export-edf" / "cadwell2.edf", {}),
    (E3, E3F / "export-edf" / "cadwell3-withfilter.edf", {"start_at": "record-origin"}),
])
def test_vendor_mode_reproduces_essentia_edf_in_full(tmp_path, export, vendor_edf, kw):
    """TST003/TST004 vendor mode on Essentia recordings: mirror-primed 0.16 Hz high-pass, gap and
    leading padding, event policy -> every sample within one quantisation step, identical annotations."""
    from cwelleegread.edf import convert
    rec = open_recording(str(export)); out = tmp_path / "v.edf"
    report = convert(rec, str(out), mode="vendor", timezone="Europe/Oslo", **kw)
    assert report["highpass_hz"] == 0.16
    with pyedflib.EdfReader(str(out)) as f:
        X = np.column_stack([f.readSignal(i) for i in range(32)]); ann = list(zip(*f.readAnnotations())); n = f.datarecords_in_file
    with pyedflib.EdfReader(str(vendor_edf)) as f:
        V = np.column_stack([f.readSignal(i) for i in range(32)]); vann = list(zip(*f.readAnnotations())); nv = f.datarecords_in_file
    assert n == nv and X.shape == V.shape
    lsb = (23919.03 + 23919.0) / 65535
    nz = [c for c in range(32) if c != 14]
    d = np.abs(X[:, nz] - V[:, nz]).max(axis=1) / lsb
    assert d.max() <= 1.001, f"max {d.max():.2f} steps at row {d.argmax()}"
    assert sorted((round(o, 3), t) for o, _, t in ann) == sorted((round(o, 3), t) for o, _, t in vann)
