"""Write a CadwellRecording to EDF+ (REQ002-REQ005, REQ014, REQ019, REQ020).

Two policies for the sample clock (REQ020):

* ``raw``    - every raw sample is kept; the EDF declares the nominal rate;
               a trailing partial second is dropped and reported.
* ``vendor`` - reproduces the vendor's EDF export: the frames that start
               inside the whole seconds of the recording are used, the
               surplus samples (frames with 251 samples) are removed at
               evenly spaced positions, and at each removal the two samples
               around it are replaced by two-point means (this is what the
               Cadwell Arc export does; see the research note). Physical
               range is the vendor's ±562500 µV.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import zoneinfo

import numpy as np

from . import __version__
from .ezdata import CadwellRecording, UNIT_UV, TICKS_PER_SECOND
from .layout import default_labels, headbox_for, parse_amp_layout
from .edfwrite import write_edf_plus

# event types the vendor does not export (amplifier bookkeeping) - skipped in both modes
SKIPPED_EVENT_TYPES = {"AmpConfigurationData", "LiveAmpConfigurationData", "ReviewedDataEvent",
                       "ContinuousImpedanceEvent"}


def vendor_resample(data: np.ndarray, per_frame: list[int], rate: int) -> tuple[np.ndarray, list[int], int]:
    """Reduce the raw stream to whole seconds the way the vendor's EDF export does.

    Observed on cadwell-export1 (see the research note): the last frame is not
    exported (frames = whole seconds, N_out = frames x rate); the surplus
    samples S = N_in - N_out are removed at evenly spaced positions with period
    T = ceil(N_in / (S + 1)) in output coordinates; at each position the two
    output samples are two-point means of the raw neighbours and one raw
    sample is dropped.  Returns (data, removed raw indices, frames used)."""
    frames_used = max(len(per_frame) - 1, 1)
    n_in = int(sum(per_frame[:frames_used]))
    n_out = frames_used * rate
    if n_in <= n_out:                       # short first frame etc.: nothing to remove
        return data[:n_out].copy(), [], frames_used
    surplus = n_in - n_out
    period = math.ceil(n_in / (surplus + 1))
    out = np.empty((n_out, data.shape[1]), dtype=np.float64)
    removed = []
    o = r = 0
    for i in range(surplus):
        oi = period - 2 + i * period          # output index of the first smoothed sample
        n = oi - o
        out[o:oi] = data[r:r + n]
        r += n
        out[oi] = (data[r] + data[r + 1]) / 2.0
        out[oi + 1] = (data[r + 1] + data[r + 2]) / 2.0
        removed.append(r + 2)
        o, r = oi + 2, r + 3
    out[o:] = data[r:r + (n_out - o)]
    return out, removed, frames_used


def read_padded(rec: CadwellRecording, unit_uv: float):
    """Decode all track-0 frames and pad missing frame numbers (recording gaps)
    with zeros so that the sample axis stays aligned with wall-clock time, as
    the vendor's EDF export does (REQ019). Returns (data, amp_inputs, per_frame,
    gaps) where gaps = [(first padded sample index, seconds)]."""
    rate = rec.sample_rate
    cols = {a: [] for a in rec.amp_inputs}
    per_frame, gaps = [], []
    prev = None
    cursor = 0
    for fr in rec.frames():
        if prev is not None and fr.number > prev + 1:
            missing = fr.number - prev - 1
            for a in rec.amp_inputs:
                cols[a].append(np.zeros(missing * rate))
            gaps.append((cursor, float(missing)))
            per_frame.extend([rate] * missing)
            cursor += missing * rate
        n = None
        for a in rec.amp_inputs:
            x = fr.samples[a]
            cols[a].append(x)
            n = len(x) if n is None else n
        per_frame.append(n)
        cursor += n
        prev = fr.number
    data = np.column_stack([np.concatenate(cols[a]) for a in rec.amp_inputs]) * unit_uv
    return data, rec.amp_inputs, per_frame, gaps


def nice_range(x: np.ndarray, margin: float = 0.01, minimum: float = 100.0) -> tuple[float, float]:
    """Symmetric physical range covering the data with a margin, rounded up to 2 significant digits."""
    m = float(np.nanmax(np.abs(x))) if x.size else minimum
    m = max(m * (1 + margin), minimum)
    exp = 10 ** (math.floor(math.log10(m)) - 1)
    m = math.ceil(m / exp) * exp
    return -m, m


def convert(rec: CadwellRecording, out_path: str, *, mode: str = "raw", labels: dict | None = None,
            timezone: str | None = None, anonymize: bool = False, patient: dict | None = None,
            unit_uv: float = UNIT_UV, report_path: str | None = None, all_events: bool = False) -> dict:
    if mode not in ("raw", "vendor"):
        raise ValueError("mode must be 'raw' or 'vendor'")
    rate = rec.sample_rate
    data, amp_inputs, per_frame, gaps_padded = read_padded(rec, unit_uv)
    n_raw = len(data)
    removed, frames_used = [], len(per_frame)
    if mode == "vendor":
        data, removed, frames_used = vendor_resample(data, per_frame, rate)
    else:
        data = data[:(n_raw // rate) * rate]
    n_out = len(data)
    if n_out == 0:
        raise ValueError("recording shorter than one second")
    seconds = n_out // rate

    amp = parse_amp_layout(rec.amp_layout_blob)
    headbox, headbox_known = headbox_for(amp["amp_type"])
    labels = {**default_labels(amp_inputs, amp["amp_type"]), **(labels or {})}
    vendor_max = headbox["vendor_physical_max"] or round(32767 * unit_uv, 2)
    if timezone:
        start_local = rec.start_time.astimezone(zoneinfo.ZoneInfo(timezone))
    else:
        start_local = rec.start_time
    start_naive = start_local.replace(tzinfo=None)

    headers = []
    for j, a in enumerate(amp_inputs):
        pmin, pmax = (-vendor_max, vendor_max) if mode == "vendor" else nice_range(data[:, j])
        headers.append({"label": labels[a][:16], "dimension": "uV", "sample_frequency": rate,
                        "physical_min": pmin, "physical_max": pmax, "digital_min": -32768, "digital_max": 32767,
                        "transducer": "X", "prefilter": ""})

    # events -> annotations (onset relative to the EDF start = frame-0 origin + clock correction)
    events = rec.events()
    ann, skipped = [], []
    for e in events:
        # The vendor places annotations by the event's absolute time stamp relative to
        # the frame-0 origin (the tick offsets can differ from that by a few ms).
        onset = (e.start - rec.origin).total_seconds()
        dur = (e.end - e.start).total_seconds()
        if e.deleted or (not all_events and e.type in SKIPPED_EVENT_TYPES):
            skipped.append((e.type, e.text, "type skipped" if not e.deleted else "deleted"))
        elif onset < 0 or onset > seconds:
            skipped.append((e.type, e.text, "outside exported range"))
        elif anonymize and e.type in ("Comment", "UserEvent"):
            ann.append((onset, dur if dur > 0 else -1, e.type))
        else:
            ann.append((onset, dur if dur > 0 else -1, e.text))
    if mode == "raw":
        for start_sample, gap_seconds in gaps_padded:
            if start_sample < n_out:
                ann.append((start_sample / rate, gap_seconds, f"Recording gap {gap_seconds:g} s (padded with zeros)"))

    p = patient or {}
    write_edf_plus(
        out_path, [np.ascontiguousarray(data[:, j]) for j in range(len(amp_inputs))], headers,
        start=start_naive, annotations=ann,
        patient_code=p.get("code", "X" if anonymize else (rec.patient_guid or "X")),
        patient_name=p.get("name", "X"),
        # EDF+ recording field is 80 chars: record GUID prefix here, full GUIDs in the JSON report
        admincode=(rec.record_guid or "X")[:8], technician="X", equipment="CadwellArc",
        recording_additional=f"CwellEEGRead_{mode}_{(timezone or 'UTC')}"[:34],
    )

    per_frame_hist = {}
    for n in per_frame:
        per_frame_hist[n] = per_frame_hist.get(n, 0) + 1
    span = (rec.frame_index[-1]["timestamp"] - rec.origin).total_seconds() if len(rec.frame_index) > 1 else None
    report = {
        "cwelleegread_version": __version__, "input": rec.index_path, "output": os.path.abspath(out_path),
        "mode": mode, "record_guid": rec.record_guid, "patient_guid": None if anonymize else rec.patient_guid,
        "schema_versions": rec.schema_versions,
        "start_utc": rec.start_time.isoformat(), "start_written": start_naive.isoformat(), "timezone": timezone or "UTC",
        "clock_correction_us": rec.clock_correction.total_seconds() * 1e6,
        "headbox": {"amp_type": amp["amp_type"], "layout_guid": amp["layout_guid"], "name": headbox["name"], "known": headbox_known},
        "sample_rate_nominal": rate, "unit_uv": unit_uv,
        "frames": len(rec.frame_index), "frames_padded": len(per_frame) - len(rec.frame_index), "samples_per_frame": {str(k): v for k, v in sorted(per_frame_hist.items())},
        "raw_samples": n_raw, "written_samples": n_out, "seconds": seconds,
        "frames_used": frames_used,
        "samples_dropped_at_end": n_raw - sum(per_frame[:frames_used]) if mode == "vendor" else n_raw - n_out,
        "samples_removed_by_vendor_rule": removed,
        "effective_rate_hz": (sum(per_frame[:-1]) / span) if span else None,
        "gaps": [{k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in g.items()} for g in rec.gaps],
        "gaps_padded": [{"start_second": st / rate, "seconds": sec} for st, sec in gaps_padded],
        "channels": [{"amp_input": a, "label": h["label"], "physical_min": h["physical_min"], "physical_max": h["physical_max"],
                      "resolution_uv": (h["physical_max"] - h["physical_min"]) / 65535} for a, h in zip(amp_inputs, headers)],
        "annotations_written": len(ann), "events_skipped": [{"type": t, "text": x, "reason": r} for t, x, r in skipped],
        "warnings": [f"channel labels are inferred from the {headbox['name']} amplifier-input layout table (not stored in the Cadwell files)"
                     + ("" if headbox_known else f" - amplifier type {amp['amp_type']} is UNKNOWN, labels may be wrong"),
                     "microvolt scale is the empirical constant verified on cadwell-export1 (250 Hz)"],
    }
    if gaps_padded:
        report["warnings"].append(f"{len(gaps_padded)} recording gap(s) padded with zeros (total {sum(g[1] for g in gaps_padded):g} s)")
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
            f.write("\n")
    return report
