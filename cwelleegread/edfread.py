"""Minimal EDF / EDF+ reader for the self-test (DES024).

Written here rather than taken from a library because the self-test must
compare with the vendor's file exactly: pyedflib reads the vendor's 7-digit
sub-second start (``+0.2766482``) as 0.027665 s, and the digital samples are
what is compared. Returns digital samples as int16, the signal headers, the
start time with its sub-second part from the first TAL, and the annotations
with onsets parsed from their decimal text. The patient and recording
identification fields are skipped on purpose and never returned, so nothing
built on this reader can print or store them.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np

ANNOTATION_LABEL = "EDF Annotations"


@dataclass
class EdfSignal:
    label: str
    dimension: str
    physical_min: float
    physical_max: float
    digital_min: int
    digital_max: int
    samples_per_record: int
    prefilter: str

    @property
    def step(self) -> float:
        """Physical value of one digital step."""
        return (self.physical_max - self.physical_min) / (self.digital_max - self.digital_min)

    def physical(self, digital: np.ndarray) -> np.ndarray:
        return (digital.astype(np.float64) - self.digital_min) * self.step + self.physical_min


@dataclass
class EdfFile:
    edf_type: str                  # "EDF", "EDF+C" or "EDF+D"
    start: dt.datetime             # naive, whole seconds, as in the header
    start_subsecond: float         # onset of the first record's time-keeping TAL (EDF+), else 0
    record_duration: float
    n_records: int
    signals: list[EdfSignal]       # without the annotation signal
    digital: list[np.ndarray]      # int16 samples per signal
    annotations: list[tuple[float, float | None, str]] = field(default_factory=list)   # onset from header start
    record_onsets: list[float] = field(default_factory=list)                             # EDF+ only


def _num(b: bytes) -> float:
    return float(b.decode("ascii").strip())


def _parse_tals(buf: bytes) -> tuple[float | None, list[tuple[float, float | None, str]]]:
    """(record onset from the time-keeping TAL, annotations) of one record's annotation bytes."""
    record_onset, out = None, []
    for tal in buf.split(b"\x00"):
        if not tal:
            continue
        parts = tal.split(b"\x14")
        onset_s, _, dur_s = parts[0].partition(b"\x15")
        try:
            onset = float(onset_s.decode("ascii"))
        except ValueError:
            continue
        dur = float(dur_s.decode("ascii")) if dur_s else None
        texts = [p.decode("utf-8", "replace") for p in parts[1:] if p]
        if not texts and record_onset is None:
            record_onset = onset
        out.extend((onset, dur, t) for t in texts)
    return record_onset, out


def read_edf(path: str) -> EdfFile:
    with open(path, "rb") as f:
        head = f.read(256)
        if len(head) < 256 or not head[:8].strip().isdigit():
            raise ValueError(f"{path} is not an EDF file")
        header_bytes = int(_num(head[184:192]))
        ns = int(_num(head[252:256]))
        sh = f.read(ns * 256)
        raw = np.frombuffer(f.read(), dtype="<i2")

    def col(offset: int, width: int) -> list[bytes]:
        base = offset * ns
        return [sh[base + i * width: base + (i + 1) * width] for i in range(ns)]

    labels = [b.decode("ascii", "replace").strip() for b in col(0, 16)]
    dims = [b.decode("ascii", "replace").strip() for b in col(96, 8)]
    pmin, pmax = [_num(b) for b in col(104, 8)], [_num(b) for b in col(112, 8)]
    dmin, dmax = [int(_num(b)) for b in col(120, 8)], [int(_num(b)) for b in col(128, 8)]
    pref = [b.decode("ascii", "replace").strip() for b in col(136, 80)]
    spr = [int(_num(b)) for b in col(216, 8)]

    d, t = head[168:176].decode("ascii"), head[176:184].decode("ascii")
    yy = int(d[6:8])
    start = dt.datetime(1900 + yy if yy >= 85 else 2000 + yy, int(d[3:5]), int(d[0:2]),
                        int(t[0:2]), int(t[3:5]), int(t[6:8]))
    reserved = head[192:236].decode("ascii", "replace").strip().upper()
    record_duration = _num(head[244:252])
    per_record = sum(spr)
    n_records = int(_num(head[236:244]))
    if n_records < 0 or n_records * per_record > raw.size:      # -1 = unknown, or a truncated file
        n_records = raw.size // per_record
    recs = raw[:n_records * per_record].reshape(n_records, per_record)
    offsets = np.concatenate([[0], np.cumsum(spr)])

    signals, digital, annotations, record_onsets = [], [], [], []
    for i in range(ns):
        block = recs[:, offsets[i]:offsets[i + 1]]
        if labels[i] == ANNOTATION_LABEL:
            for k in range(n_records):
                onset, anns = _parse_tals(block[k].tobytes())
                record_onsets.append(onset if onset is not None else k * record_duration)
                annotations.extend(anns)
            continue
        signals.append(EdfSignal(labels[i], dims[i], pmin[i], pmax[i], dmin[i], dmax[i], spr[i], pref[i]))
        digital.append(block.reshape(-1).copy())
    edf_type = reserved[:5] if reserved.startswith("EDF+") else "EDF"
    subsecond = record_onsets[0] % 1.0 if record_onsets else 0.0
    return EdfFile(edf_type, start, subsecond, record_duration, n_records, signals, digital,
                   annotations, record_onsets)
