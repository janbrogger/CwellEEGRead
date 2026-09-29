"""Minimal EDF / EDF+C / EDF+D writer (Kemp et al. 1992; Kemp & Olivan 2003).

Written here rather than taken from a library so that annotation texts are
not truncated, the sub-second start offset is written in the first TAL of
every record (as the Cadwell export does), and every header field is under
our control. Reading back is done with an independent library in the tests.
"""
from __future__ import annotations

import bisect
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


EDF_TYPES = ("edf", "edf+c", "edf+d")


def write_edf(path: str, signals: list[np.ndarray], signal_headers: list[dict], *,
              start: dt.datetime, annotations: list[tuple[float, float, str]] | None = None,
              edf_type: str = "edf+c", record_onsets: list[float] | None = None,
              patient_code: str = "X", patient_sex: str = "X", patient_birthdate: str = "X",
              patient_name: str = "X", patient_additional: str = "",
              admincode: str = "X", technician: str = "X", equipment: str = "X",
              recording_additional: str = "", record_duration: float = 1.0) -> dict:
    """Write an EDF, EDF+C or EDF+D file. Signals are physical values (float arrays), all
    with a whole number of records; ``signal_headers`` items need label, dimension,
    sample_frequency, physical_min, physical_max, digital_min, digital_max,
    transducer, prefilter. ``start`` is a naive datetime (sub-seconds allowed for EDF+).
    Annotations are (onset_seconds, duration_seconds or -1, text), onsets relative to
    the data start.

    ``edf_type``: ``edf+c`` - contiguous records; ``edf+d`` - record k starts at
    ``record_onsets[k]`` seconds after the data start (increasing, at least one record
    duration apart); ``edf`` - plain EDF without annotation signal (no annotations, and
    a start on a whole second, since plain EDF cannot carry a sub-second start)."""
    if edf_type not in EDF_TYPES:
        raise ValueError(f"edf_type must be one of {EDF_TYPES}")
    annotations = annotations or []
    ns = len(signals)
    spr = [int(round(h["sample_frequency"] * record_duration)) for h in signal_headers]
    n_records = len(signals[0]) // spr[0]
    for x, n in zip(signals, spr):
        if len(x) != n_records * n:
            raise ValueError("all signals must span the same whole number of records")
    if edf_type == "edf+d":
        if record_onsets is None or len(record_onsets) != n_records:
            raise ValueError("EDF+D needs one record onset per record")
        if any(b - a < record_duration - 1e-9 for a, b in zip(record_onsets, record_onsets[1:])):
            raise ValueError("EDF+D record onsets must increase by at least one record duration")
    else:
        record_onsets = [k * record_duration for k in range(n_records)]
    if edf_type == "edf":
        if annotations:
            raise ValueError("plain EDF cannot hold annotations")
        if start.microsecond:
            raise ValueError("plain EDF cannot hold a sub-second start time")

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
    # Each goes into the last record starting at or before it (EDF+D: an onset inside a
    # gap lands in the record before the gap), clamped to the first/last record.
    for onset, dur, text in sorted(annotations, key=lambda a: a[0]):
        k = min(max(bisect.bisect_right(record_onsets, onset + 1e-9) - 1, 0), n_records - 1)
        tal = f"+{onset + subsec:.6f}".rstrip("0").rstrip(".").encode("ascii")
        if dur is not None and dur >= 0:
            tal += b"\x15" + f"{dur:.6f}".rstrip("0").rstrip(".").encode("ascii")
        tal += b"\x14" + text.replace("\x14", " ").replace("\x00", " ").encode("utf-8") + b"\x14\x00"
        per_record[k].append(tal)
    tal_records = []
    for k in range(n_records):
        head = f"+{subsec + record_onsets[k]:.6f}".rstrip("0").rstrip(".").encode("ascii") + b"\x14\x14\x00"
        tal_records.append(head + b"".join(per_record[k]))
    with_ann = edf_type != "edf"
    ann_spr = max(30, math.ceil(max(len(t) for t in tal_records) / 2)) if with_ann else 0

    # --- header
    if start.year < 1985 or start.year > 2084:
        raise ValueError("EDF+ start date must be between 1985 and 2084")
    patient = " ".join([_edf_text(patient_code), patient_sex or "X", patient_birthdate or "X",
                        _edf_text(patient_name)] + ([patient_additional] if patient_additional else []))
    recording = " ".join(["Startdate", f"{start.day:02d}-{MONTHS[start.month - 1]}-{start.year}",
                          _edf_text(admincode), _edf_text(technician), _edf_text(equipment)]
                         + ([recording_additional] if recording_additional else []))
    extra = 1 if with_ann else 0              # the "EDF Annotations" signal
    n_all = ns + extra
    header_bytes = 256 * (n_all + 1)
    hdr = b"".join([
        _field("0", 8), _field(patient, 80), _field(recording, 80),
        _field(start.strftime("%d.%m.%y"), 8), _field(start.strftime("%H.%M.%S"), 8),
        _field(header_bytes, 8), _field(edf_type.upper() if with_ann else "", 44), _field(n_records, 8),
        _field(_num(record_duration, 8), 8), _field(n_all, 4),
    ])
    labels = [h["label"] for h in signal_headers] + ["EDF Annotations"][:extra]
    transducers = [h.get("transducer", "") for h in signal_headers] + [""][:extra]
    dims = [h["dimension"] for h in signal_headers] + [""][:extra]
    pmins = [_num(h["physical_min"], 8) for h in signal_headers] + ["-1"][:extra]
    pmaxs = [_num(h["physical_max"], 8) for h in signal_headers] + ["1"][:extra]
    dmins = [str(h["digital_min"]) for h in signal_headers] + ["-32768"][:extra]
    dmaxs = [str(h["digital_max"]) for h in signal_headers] + ["32767"][:extra]
    prefs = [h.get("prefilter", "") for h in signal_headers] + [""][:extra]
    sprs = spr + [ann_spr][:extra]
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
            if with_ann:
                f.write(tal_records[k].ljust(ann_spr * 2, b"\x00"))
    return {"records": n_records, "record_duration": record_duration, "annotation_samples_per_record": ann_spr,
            "header_bytes": header_bytes, "edf_type": edf_type}


def write_edf_plus(path: str, signals: list[np.ndarray], signal_headers: list[dict], **kw) -> dict:
    """EDF+C (the earlier interface of write_edf)."""
    return write_edf(path, signals, signal_headers, edf_type="edf+c", **kw)
