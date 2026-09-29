"""Research prototype tools/cadwell_add_events.py (no REQ/TST item yet; see
docs/research/writing-events.md): events added to a copy of a public export
from wall-clock times land where the vendor put the same events, and the
copy converts to the same EDF plus the new annotations."""
import datetime as dt
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import convert

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "testdata" / "public" / "cadwell-export1"
E3 = ROOT / "testdata" / "public" / "cadwell-export3"

_spec = importlib.util.spec_from_file_location("cadwell_add_events", ROOT / "tools" / "cadwell_add_events.py")
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

pytestmark = pytest.mark.skipif(not (E3 / "native-export").exists(), reason="public test export missing")


def vendor_text_events(export):
    path = next((export / "native-export" / "CadLink" / "Data").glob("*.ezevents"))
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
        return con.execute("select Text, StartTime, StartOffset from Events "
                           "where EventType in ('Comment','UserEvent') and Deleted=0").fetchall()


def folder_digest(folder):
    h = hashlib.sha256()
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(folder)).encode() + p.read_bytes())
    return h.hexdigest()


def annotations(path):
    with pyedflib.EdfReader(str(path)) as f:
        sig = np.column_stack([f.readSignal(i, digital=True) for i in range(f.signals_in_file)])
        return f.getHeader(), sig, list(zip(f.readAnnotations()[0], f.readAnnotations()[2]))


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    """Every vendor comment / user event of export 3 re-added as 'REPLAY <text>' from its
    Oslo local wall-clock time, as an external system would supply it."""
    tmp = tmp_path_factory.mktemp("addev")
    oslo = ZoneInfo("Europe/Oslo")
    vendor = vendor_text_events(E3)
    items = [{"time": dt.datetime.fromisoformat(t[:26]).replace(tzinfo=dt.timezone.utc).astimezone(oslo).isoformat(),
              "text": "REPLAY " + x} for x, t, _ in vendor]
    (tmp / "events.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    before = folder_digest(E3 / "native-export")
    report = tool.add_events(str(E3 / "native-export"), str(tmp / "events.json"), str(tmp / "out"))
    assert folder_digest(E3 / "native-export") == before, "input export was modified"
    return tmp, vendor, report


def test_tick_offsets_match_the_vendors(replay):
    _, vendor, report = replay
    assert report["integrity_check"] == "ok"
    assert len(report["events"]) == len(vendor) >= 10
    for ours, (_, _, ticks) in zip(report["events"], vendor):
        assert abs(ours["start_offset"] - ticks) < 10_000          # < 1 ms (0.5 sample at 500 Hz)


@pytest.mark.parametrize("mode", ["raw", "vendor"])
def test_reconversion_adds_only_the_new_annotations(replay, mode):
    tmp, vendor, _ = replay
    for src, name in ((E3 / "native-export", "orig"), (tmp / "out", "new")):
        convert(open_recording(str(src)), str(tmp / f"{name}-{mode}.edf"), mode=mode, timezone="Europe/Oslo")
    h0, s0, a0 = annotations(tmp / f"orig-{mode}.edf")
    h1, s1, a1 = annotations(tmp / f"new-{mode}.edf")
    assert h0 == h1 and np.array_equal(s0, s1)
    assert sorted(a for a in a1 if not a[1].startswith("REPLAY ")) == sorted(a0)
    added = [a for a in a1 if a[1].startswith("REPLAY ")]
    assert len(added) == len(vendor)
    # raw mode places by ticks (< 1 ms from the vendor event), vendor mode by stamp (identical)
    tol = 1e-3 if mode == "raw" else 1e-6
    for onset, text in added:
        assert min(abs(onset - o) for o, t in a0 if t == text[7:]) < tol, text


def test_refuses_events_without_eeg_and_times_without_zone(tmp_path):
    (tmp_path / "late.json").write_text('[{"time": "2025-10-31T14:50:00+01:00", "text": "x"}]')
    with pytest.raises(ValueError, match="no stored EEG"):
        tool.add_events(str(E1), str(tmp_path / "late.json"), str(tmp_path / "o1"))
    (tmp_path / "naive.json").write_text('[{"time": "2025-10-31T14:38:10", "text": "x"}]')
    with pytest.raises(ValueError, match="no UTC offset"):
        tool.add_events(str(E1), str(tmp_path / "naive.json"), str(tmp_path / "o2"))
    assert not (tmp_path / "o1").exists() and not (tmp_path / "o2").exists()
