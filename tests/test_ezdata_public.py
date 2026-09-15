"""Decode the public test export and prove equivalence with the vendor's
text export (REQ009 / TST005 on public data) and structural agreement with
the vendor's EDF+ export (REQ008 / TST002)."""
from pathlib import Path

import numpy as np
import pytest

from cwelleegread import open_recording

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "testdata" / "public" / "cadwell-export1"
TEXT = EXPORT / "test" / "test-eeg20251031.txt"
EDF = EXPORT / "edf" / "test.edf"

pytestmark = pytest.mark.skipif(not (EXPORT / "native-export").exists(), reason="public test export missing")


def read_text_export(path):
    rows = [l.rstrip("\n") for l in open(path, encoding="utf-8", errors="replace")
            if not l.startswith("%") and l.strip()]
    return np.array([[float(x.replace(",", ".")) for x in l.split("\t")[1:]] for l in rows]) * 1000.0  # mV -> µV


@pytest.fixture(scope="module")
def rec():
    return open_recording(str(EXPORT))


@pytest.fixture(scope="module")
def signals(rec):
    return rec.read_signals()


def test_structure(rec):
    assert rec.sample_rate == 250
    assert len(rec.channels) == 32
    assert sorted(c.amp_input for c in rec.channels) == list(range(1, 33))
    assert len(rec.frame_index) == 45
    assert rec.gaps == []
    assert rec.record_guid == "56659ea9-99fd-4d8d-a85c-7502a29229e6"


def test_frames_have_248_250_or_251_samples(signals):
    data, amp_inputs, per_frame = signals
    assert per_frame[0] == 248 and set(per_frame[1:]) <= {250, 251}
    assert data.shape == (sum(per_frame), 32)


def test_equivalent_to_text_export(signals):
    """Every sample equals the vendor's text export within its 0.1 µV rounding
    (0.05 µV) plus a 0.01 µV allowance for the fitted microvolt scale."""
    data, _, _ = signals
    txt = read_text_export(TEXT)
    n = len(txt)
    diff = np.abs(data[:n] - txt)
    assert diff.max() <= 0.06, f"max deviation {diff.max():.4f} µV"


def test_edf_header_matches(rec, signals):
    pyedflib = pytest.importorskip("pyedflib")
    with pyedflib.EdfReader(str(EDF)) as f:
        assert f.signals_in_file == 32
        assert {int(round(f.getSampleFrequency(i))) for i in range(32)} == {rec.sample_rate}
        labels = f.getSignalLabels()
        edf = np.column_stack([f.readSignal(i) for i in range(32)])
    assert labels[0] == "EEG E1-Cz" and labels[14] == "EEG Cz-Cz"
    data, _, _ = signals
    # The vendor EDF resamples (one sample dropped by linear interpolation every
    # 1224 samples); before the first drop point the samples agree within one EDF
    # quantisation step (17.17 µV; half a step plus rounding-direction differences).
    lsb = 1125000 / 65535
    nz = [c for c in range(32) if c != 14]
    assert np.abs(data[:1222, nz] - edf[:1222, nz]).max() <= lsb
