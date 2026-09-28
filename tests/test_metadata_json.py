"""The Metadata.json written next to the vendor's EDF export carries integer
event 'Timestamp's. They are microseconds since 1970-01-01 expressed in local
wall-clock time (not UTC), equal to the Events table StartTime (100 ns
resolution) plus the PcTimeSync clock correction, rounded to the microsecond.
They add no precision beyond the .ezevents database (and less than the EDF+
annotations, which keep 7 decimals); the list is the EDF export's own event
selection (bookkeeping types left out). RecordCreateDate follows the same
convention. Documented in docs/research/cadwell-file-format.md."""
import datetime as dt
import json
from pathlib import Path

import pytest

from cwelleegread import open_recording

ROOT = Path(__file__).resolve().parents[1]
CASES = [  # export, Metadata.json, local UTC offset at the recording date (Europe/Oslo)
    ("cadwell-export1", "edf/Metadata.json", 1),
    ("cadwell-export2", "export-edf/Metadata.json", 2),
    ("cadwell-export3", "export-edf/Metadata.json", 2),
]
UTC = dt.timezone.utc


def unix_us(t: dt.datetime) -> float:
    return (t - dt.datetime(1970, 1, 1, tzinfo=UTC)) / dt.timedelta(microseconds=1)


@pytest.mark.parametrize("export, meta_rel, utc_offset_h", CASES)
def test_metadata_timestamps_equal_database_stamps(export, meta_rel, utc_offset_h):
    base = ROOT / "testdata" / "public" / export
    if not (base / "native-export").exists() or not (base / meta_rel).exists():
        pytest.skip("public test export missing")
    rec = open_recording(str(base))
    meta = json.load(open(base / meta_rel))
    events = rec.events()
    shift_us = utc_offset_h * 3600e6 + rec.clock_correction / dt.timedelta(microseconds=1)
    matched = 0
    for j in meta["Events"]:
        # the same text can occur many times (photic, HV), so match on the predicted instant
        predicted = {round(unix_us(ev.start) + shift_us) for ev in events if ev.text == j["Message"] and not ev.deleted}
        assert predicted, f"json event without database counterpart: {j['Message']!r}"
        assert min(abs(j["Timestamp"] - p) for p in predicted) <= 1, (j, sorted(predicted)[:3])
        matched += 1
    assert matched == len(meta["Events"]) and matched > 0
    # the json keeps the EDF export's selection: no amplifier/impedance bookkeeping, no reviewed-data marks
    json_texts = {j["Message"] for j in meta["Events"]}
    for ev in events:
        if ev.type in ("AmpConfigurationData", "LiveAmpConfigurationData", "ReviewedDataEvent",
                       "ContinuousImpedanceEvent", "BaselineImpedanceEvent"):
            assert ev.text not in json_texts or ev.type == "BaselineImpedanceEvent"
