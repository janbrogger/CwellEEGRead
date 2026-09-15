"""Minimal EDF+C writer (Kemp et al. 1992; Kemp & Olivan 2003).

Written here rather than taken from a library so that annotation texts are
not truncated, the sub-second start offset is written in the first TAL of
every record (as the Cadwell export does), and every header field is under
our control. Reading back is done with an independent library in the tests.
"""
from __future__ import annotations

import datetime as dt
import math

import numpy as np

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _field(value, width: int) -> bytes:
    s = str(value)
    b = s.encode("ascii", "replace")
    if len(b) > width:
        raise ValueError(f"EDF header field {s!r} longer than {width} bytes")
    return b.ljust(width)


def _num(value, width: int) -> str:
    """Shortest ASCII form of a number that fits the field."""
    if float(value).is_integer():
        s = str(int(value))
    else:
        s = repr(float(value))
        if len(s) > width:
            s = f"{value:.{max(0, width - 2 - len(str(int(abs(value)))))}f}".rstrip("0").rstrip(".")
    if len(s) > width:
        raise ValueError(f"number {value} does not fit in {width} chars")
    return s


def _edf_text(s: str) -> str:
    return s.replace(" ", "_") if s else "X"


def write_edf_plus(path: str, signals: list[np.ndarray], signal_headers: list[dict], *,
                   start: dt.datetime, annotations: list[tuple[float, float, str]] | None = None,
                   patient_code: str = "X", patient_sex: str = "X", patient_birthdate: str = "X",
                   patient_name: str = "X", patient_additional: str = "",
                   admincode: str = "X", technician: str = "X", equipment: str = "X",
                   recording_additional: str = "", record_duration: float = 1.0) -> dict:
    """Write an EDF+C file. Signals are physical values (float arrays), all with a
    whole number of records; ``signal_headers`` items need label, dimension,
    sample_frequency, physical_min, physical_max, digital_min, digital_max,
    transducer, prefilter. ``start`` is a naive datetime (sub-seconds allowed).
    Annotations are (onset_seconds, duration_seconds or -1, text)."""
    annotations = annotations or []
    ns = len(signals)
    spr = [int(round(h["sample_frequency"] * record_duration)) for h in signal_headers]
    n_records = len(signals[0]) // spr[0]
    for x, n in zip(signals, spr):
        if len(x) != n_records * n:
            raise ValueError("all signals must span the same whole number of records")

    # --- digitise
    digital = []
    for x, h in zip(signals, signal_headers):
        pmin, pmax, dmin, dmax = h["physical_min"], h["physical_max"], h["digital_min"], h["digital_max"]
        d = np.rint((np.asarray(x, dtype=np.float64) - pmin) / (pmax - pmin) * (dmax - dmin) + dmin)
        digital.append(np.clip(d, dmin, dmax).astype("<i2"))

    # --- annotations: one TAL list per record, first TAL = record start offset
    subsec = start.microsecond / 1e6
    per_record: list[list[bytes]] = [[] for _ in range(n_records)]
    # EDF+: every TAL onset is relative to the header start time (whole seconds), so
    # annotation onsets given relative to the data start get the sub-second offset added.
    for onset, dur, text in sorted(annotations, key=lambda a: a[0]):
        k = min(max(int(onset // record_duration), 0), n_records - 1)
        tal = f"+{onset + subsec:.6f}".rstrip("0").rstrip(".").encode("ascii")
        if dur is not None and dur >= 0:
            tal += b"\x15" + f"{dur:.6f}".rstrip("0").rstrip(".").encode("ascii")
        tal += b"\x14" + text.replace("\x14", " ").replace("\x00", " ").encode("utf-8") + b"\x14\x00"
        per_record[k].append(tal)
    tal_records = []
    for k in range(n_records):
        head = f"+{subsec + k * record_duration:.6f}".rstrip("0").rstrip(".").encode("ascii") + b"\x14\x14\x00"
        tal_records.append(head + b"".join(per_record[k]))
    ann_bytes = max(len(t) for t in tal_records)
    ann_spr = max(30, math.ceil(ann_bytes / 2))

    # --- header
    if start.year < 1985 or start.year > 2084:
        raise ValueError("EDF+ start date must be between 1985 and 2084")
    patient = " ".join([_edf_text(patient_code), patient_sex or "X", patient_birthdate or "X",
                        _edf_text(patient_name)] + ([patient_additional] if patient_additional else []))
    recording = " ".join(["Startdate", f"{start.day:02d}-{MONTHS[start.month - 1]}-{start.year}",
                          _edf_text(admincode), _edf_text(technician), _edf_text(equipment)]
                         + ([recording_additional] if recording_additional else []))
    n_all = ns + 1
    header_bytes = 256 * (n_all + 1)
    hdr = b"".join([
        _field("0", 8), _field(patient, 80), _field(recording, 80),
        _field(start.strftime("%d.%m.%y"), 8), _field(start.strftime("%H.%M.%S"), 8),
        _field(header_bytes, 8), _field("EDF+C", 44), _field(n_records, 8),
        _field(_num(record_duration, 8), 8), _field(n_all, 4),
    ])
    labels = [h["label"] for h in signal_headers] + ["EDF Annotations"]
    transducers = [h.get("transducer", "") for h in signal_headers] + [""]
    dims = [h["dimension"] for h in signal_headers] + [""]
    pmins = [_num(h["physical_min"], 8) for h in signal_headers] + ["-1"]
    pmaxs = [_num(h["physical_max"], 8) for h in signal_headers] + ["1"]
    dmins = [str(h["digital_min"]) for h in signal_headers] + ["-32768"]
    dmaxs = [str(h["digital_max"]) for h in signal_headers] + ["32767"]
    prefs = [h.get("prefilter", "") for h in signal_headers] + [""]
    sprs = spr + [ann_spr]
    for width, values in ((16, labels), (80, transducers), (8, dims), (8, pmins), (8, pmaxs),
                          (8, dmins), (8, dmaxs), (80, prefs), (8, sprs), (32, [""] * n_all)):
        hdr += b"".join(_field(v, width) for v in values)
    assert len(hdr) == header_bytes

    # --- records
    with open(path, "wb") as f:
        f.write(hdr)
        for k in range(n_records):
            for d, n in zip(digital, spr):
                f.write(d[k * n:(k + 1) * n].tobytes())
            f.write(tal_records[k].ljust(ann_spr * 2, b"\x00"))
    return {"records": n_records, "record_duration": record_duration, "annotation_samples_per_record": ann_spr,
            "header_bytes": header_bytes}
