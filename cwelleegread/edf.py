"""Write a CadwellRecording to EDF / EDF+ (REQ002-REQ005, REQ014, REQ019, REQ020).

Two policies for the sample clock (REQ020):

* ``raw``    - every raw sample is kept; the EDF declares the nominal rate;
               a trailing partial second is dropped and reported.
* ``vendor`` - reproduces the vendor's EDF export: the frames that start
               inside the whole seconds of the recording are used, the
               surplus samples (frames with 251 samples) are removed at
               evenly spaced positions, and at each removal the two samples
               around it are replaced by two-point means (this is what the
               Cadwell Arc export does; see the research note). Physical
               range is the vendor's (layout.HEADBOXES).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import zoneinfo

import numpy as np

from . import __version__
from .ezdata import CadwellRecording, UNIT_UV, TICKS_PER_SECOND
from .layout import default_labels, headbox_for, parse_amp_layout
from .edfwrite import write_edf

# event types the vendor does not export (amplifier bookkeeping) - skipped in both modes
SKIPPED_EVENT_TYPES = {"AmpConfigurationData", "LiveAmpConfigurationData", "ReviewedDataEvent",
                       "ContinuousImpedanceEvent", "BaselineImpedanceEvent"}
SKIPPED_EVENT_TEXTS = {"Photic Stim"}      # the individual flash markers (hundreds); "Photic Start 2Hz" etc. are kept
ANONYMIZED_EVENT_TYPES = {"Comment", "UserEvent", "Annotation", "PatientEvent"}   # free text typed by people


def resolve_timezone(name: str | None) -> dt.tzinfo:
    """None -> UTC; 'UTC+01:00' / 'UTC-05:30' -> that fixed offset; otherwise an IANA name
    such as 'Europe/Oslo' (on Windows these need the tzdata package; fixed offsets do not)."""
    if not name or name.upper() in ("UTC", "Z"):
        return dt.timezone.utc
    m = re.fullmatch(r"(?i)UTC([+-])(\d{1,2}):?(\d{2})", name.strip())
    if m:
        off = dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3)))
        return dt.timezone(-off if m.group(1) == "-" else off)
    try:
        return zoneinfo.ZoneInfo(name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown time zone {name!r} (IANA name such as Europe/Oslo, or UTC+01:00; "
                         "IANA names need the tzdata package on Windows)") from exc


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


def vendor_raw_positions(removed: list[int], n_out: int) -> np.ndarray:
    """Position on the raw sample axis of every output sample of vendor_resample():
    copied samples sit on their raw index, the two smoothed samples at a removal of
    raw sample q (means of q-2, q-1 and of q-1, q) at q-1.5 and q-0.5."""
    pos = np.arange(n_out, dtype=np.float64)
    if not removed:
        return pos
    q = np.asarray(removed, dtype=np.int64)
    oi = q - 2 - np.arange(len(q))                 # output index of the first smoothed sample
    pos += np.searchsorted(oi + 2, np.arange(n_out), side="right")
    pos[oi] = q - 1.5
    pos[oi + 1] = q - 0.5
    return pos


def raw_to_output_position(p: float, raw_pos: np.ndarray) -> float:
    """Map a fractional raw sample position onto the vendor-resampled axis (piecewise
    linear through vendor_raw_positions(); nominal rate before the start and past the end)."""
    if p <= raw_pos[0]:
        return p - raw_pos[0]
    if p >= raw_pos[-1]:
        return len(raw_pos) - 1 + (p - raw_pos[-1])
    return float(np.interp(p, raw_pos, np.arange(len(raw_pos), dtype=np.float64)))


def read_padded(rec: CadwellRecording, unit_uv: float, frame_table: list | None = None):
    """Decode all track-0 frames and pad missing frame numbers (recording gaps)
    with zeros so that the sample axis stays aligned with wall-clock time, as
    the vendor's EDF export does (REQ019). Returns (data, amp_inputs, per_frame,
    gaps) where gaps = [(first padded sample index, seconds)]. If frame_table is
    a list it is filled with one (start_ticks, end_ticks, first_sample, n_samples)
    per stored frame, the sample-clock map used by event_sample (REQ021)."""
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
        if frame_table is not None:
            frame_table.append((fr.start_ticks, fr.end_ticks, cursor, n))
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


VENDOR_HIGHPASS_HZ = 0.16      # causal 2nd-order Butterworth, identified on cadwell-export2 (max 0.52 steps)
# EDF prefilter text when that high-pass is applied: the vendor documents no filter and
# writes an empty field; 0.16 Hz is our identification, hence the question mark.
HIGHPASS_PREFILTER = "HP: unknown (0.16 Hz?)"


def event_sample(ticks: int, frame_table: list, rate: int) -> float:
    """Sample position (fractional, 0 = first sample of the first stored frame) of an
    instant given in amplifier ticks, using the per-frame tick spans of the stored
    frames (REQ021): inside a frame, linear between its first and last sample;
    in a padded gap, after the end or before the start, at the nominal rate from
    the nearest frame edge. Frame ticks are exact seconds on Essentia and
    measured (jittered) on Apollo, so this also absorbs the 248-251 samples per
    Apollo frame."""
    import bisect
    starts = [f[0] for f in frame_table]
    k = bisect.bisect_right(starts, ticks) - 1
    if k < 0:
        s0, _, first, _ = frame_table[0]
        return first - (s0 - ticks) / TICKS_PER_SECOND * rate
    s, e, first, n = frame_table[k]
    if ticks < e and e > s:
        return first + (ticks - s) / (e - s) * n
    return first + n + (ticks - e) / TICKS_PER_SECOND * rate


def vendor_highpass(data: np.ndarray, per_frame: list[int], gaps: list, rate: int, restart_at_gaps: bool = True) -> np.ndarray:
    """The vendor's EDF export high-pass (identified on cadwell-export2/3, see the
    research note): 2nd-order Butterworth, 0.16 Hz, applied causally to every
    contiguous data segment, primed by first running the filter over the
    time-reversed start of the segment (mirror including the first sample) so
    that there is no start-up transient. Padded gap seconds stay zero and the
    filter is primed again after each gap."""
    from scipy.signal import butter, lfilter
    b, a = butter(2, VENDOR_HIGHPASS_HZ, btype="high", fs=rate)
    out = data.astype(np.float64).copy()
    bounds = [0]
    for start, seconds in gaps:
        bounds += [start, start + int(seconds * rate)]
    bounds.append(len(data))
    segments = [(bounds[i], bounds[i + 1]) for i in range(0, len(bounds) - 1, 2) if bounds[i + 1] > bounds[i]]
    n_pre = 20 * rate                      # >> filter time constant (~1 s): converged
    for s0, e0 in segments:
        seg = data[s0:e0]
        n = min(n_pre, len(seg) - 1)
        pre = seg[n::-1]                    # mirror, first sample included
        out[s0:e0] = lfilter(b, a, np.concatenate([pre, seg]), axis=0)[len(pre):]
    for start, seconds in gaps:
        out[start:start + int(seconds * rate)] = 0.0
    return out


def convert(rec: CadwellRecording, out_path: str, *, mode: str = "raw", labels: dict | None = None,
            timezone: str | None = None, anonymize: bool = False, patient: dict | None = None,
            unit_uv: float = UNIT_UV, report_path: str | None = None, all_events: bool = False,
            highpass: str = "auto", start_at: str = "first-frame", restart_filter_at_gaps: bool = True,
            event_timing: str = "auto", gaps: str = "pad", edf_format: str = "auto",
            allow_unsupported: bool = False) -> dict:
    """highpass: 'auto' (vendor mode: on for Essentia, off for Apollo), 'on', 'off'.
    start_at: 'first-frame' (data start = first stored frame) or 'record-origin' (tick 0,
    leading missing frames padded with zeros, as the vendor does when the export range
    starts at the recording start).
    gaps: 'pad' (default: zeros inside a continuous EDF+C, as the vendor does; read
    correctly by every EDF reader) or 'discontinuous' (EDF+D without the gap seconds;
    raw mode only; EDFlib/pyedflib refuses such files and MNE-Python reads them as
    contiguous, so it is opt-in).
    edf_format: 'auto' (plain EDF when nothing needs EDF+: no annotations, no EDF+D and a
    start on a whole second; EDF+ otherwise), 'edf+' or 'edf' (plain EDF: annotations
    dropped and the start truncated to the whole second, both with a warning).
    allow_unsupported: convert even if the storage schema version is not supported."""
    if mode not in ("raw", "vendor"):
        raise ValueError("mode must be 'raw' or 'vendor'")
    if gaps not in ("pad", "discontinuous"):
        raise ValueError("gaps must be 'pad' or 'discontinuous'")
    if edf_format not in ("auto", "edf", "edf+"):
        raise ValueError("edf_format must be 'auto', 'edf' or 'edf+'")
    if gaps == "discontinuous" and mode == "vendor":
        raise ValueError("discontinuous (EDF+D) output is available in raw mode only")
    if gaps == "discontinuous" and edf_format == "edf":
        raise ValueError("plain EDF cannot be discontinuous; use --gaps pad or --format edf+")
    extra_warnings = []
    if allow_unsupported:
        try:
            rec.check_supported()
        except ValueError as exc:
            extra_warnings.append(f"{exc} - converted anyway (--allow-unsupported)")
    else:
        rec.check_supported()
    rate = rec.sample_rate
    frame_table: list = []
    data, amp_inputs, per_frame, gaps_padded = read_padded(rec, unit_uv, frame_table)
    if event_timing not in ("auto", "ticks", "stamp"):
        raise ValueError("event_timing must be 'auto', 'ticks' or 'stamp'")
    if event_timing == "auto":
        event_timing = "stamp" if mode == "vendor" else "ticks"
    lead = 0
    if start_at == "record-origin" and rec.frame_index and rec.frame_index[0]["number"] > 0:
        lead = rec.frame_index[0]["number"]
        data = np.vstack([np.zeros((lead * rate, data.shape[1])), data])
        per_frame = [rate] * lead + per_frame
        gaps_padded = [(0, float(lead))] + [(st + lead * rate, sec) for st, sec in gaps_padded]
    elif start_at != "first-frame":
        raise ValueError("start_at must be 'first-frame' or 'record-origin'")
    n_raw = len(data)
    removed, frames_used = [], len(per_frame)
    amp = parse_amp_layout(rec.amp_layout_blob)
    headbox, headbox_known = headbox_for(amp["amp_type"])
    apply_hp = (highpass == "on") or (highpass == "auto" and mode == "vendor" and headbox["name"] == "Essentia")
    if mode == "vendor":
        if apply_hp:
            data = vendor_highpass(data, per_frame, gaps_padded, rate, restart_filter_at_gaps)
        data, removed, frames_used = vendor_resample(data, per_frame, rate)
    else:
        if apply_hp:
            data = vendor_highpass(data, per_frame, gaps_padded, rate, restart_filter_at_gaps)
        data = data[:(n_raw // rate) * rate]
    n_out = len(data)
    if n_out == 0:
        raise ValueError("recording shorter than one second")
    seconds = n_out // rate

    labels = {**default_labels(amp_inputs, amp["amp_type"]), **(labels or {})}
    vendor_range = headbox["vendor_physical_range"]
    start_utc = rec.start_time - dt.timedelta(seconds=lead)
    start_local = start_utc.astimezone(resolve_timezone(timezone))
    start_naive = start_local.replace(tzinfo=None)

    headers = []
    for j, a in enumerate(amp_inputs):
        pmin, pmax = vendor_range if mode == "vendor" else nice_range(data[:, j])
        headers.append({"label": labels[a][:16], "dimension": "uV", "sample_frequency": rate,
                        "physical_min": pmin, "physical_max": pmax, "digital_min": -32768, "digital_max": 32767,
                        "transducer": "X", "prefilter": HIGHPASS_PREFILTER if apply_hp else ""})

    # events -> annotations. 'stamp': onset = wall-clock stamp relative to the first
    # frame's stamp, as the vendor's export does; the stamp clock drifts against the
    # sample clock (about 96 ppm on Essentia, the stamp clock behind), so this lands early by up to 0.35 s/h.
    # 'ticks': onset from the event's StartOffset ticks through the frames' tick
    # spans, i.e. on the sample clock (REQ021, the accurate choice).
    # Vendor mode removes samples (vendor_resample), so a tick position on the raw axis is
    # mapped onto the resampled axis; without this, onsets drift late (export 1: 32 ms at the end).
    raw_pos = vendor_raw_positions(removed, n_out) if (mode == "vendor" and event_timing == "ticks") else None
    events = rec.events()
    ann, skipped = [], []
    for e in events:
        if event_timing == "ticks":
            pos = event_sample(e.start_ticks, frame_table, rate) + lead * rate
            if raw_pos is not None:
                pos = raw_to_output_position(pos, raw_pos)
            onset = pos / rate
            dur = (e.end_ticks - e.start_ticks) / 1e7
        else:
            onset = (e.start - rec.origin).total_seconds() + lead
            dur = (e.end - e.start).total_seconds()
        # with --anonymize free text never leaves the recording, not even in the report's skipped list
        shown = e.type if anonymize and e.type in ANONYMIZED_EVENT_TYPES else e.text
        if e.deleted or (not all_events and (e.type in SKIPPED_EVENT_TYPES or e.text in SKIPPED_EVENT_TEXTS)):
            skipped.append((e.type, shown, "deleted" if e.deleted else "type skipped"))
        elif onset < 0 or onset > seconds:
            skipped.append((e.type, shown, "outside exported range"))
        elif anonymize and e.type in ANONYMIZED_EVENT_TYPES:
            ann.append((onset, dur if dur > 0 else -1, e.type))
        else:
            ann.append((onset, dur if dur > 0 else -1, e.text))
    # recording gaps (not the leading padding of --start-at record-origin)
    rec_gaps = gaps_padded[1:] if lead else list(gaps_padded)
    gap_policy = gaps if rec_gaps else "pad"      # EDF+D only when there is a gap to leave out
    keep = np.ones(seconds, dtype=bool)          # records written
    edge_zero_samples = 0
    if gap_policy == "discontinuous":
        for start_sample, gap_seconds in rec_gaps:
            end_sample = start_sample + int(gap_seconds * rate)
            k0, k1 = -(-start_sample // rate), min(end_sample // rate, seconds)   # records wholly inside
            keep[k0:k1] = False
            edge_zero_samples += (end_sample - start_sample) - max(k1 - k0, 0) * rate
    if mode == "raw":
        for start_sample, gap_seconds in gaps_padded:
            if start_sample < n_out:
                if gap_policy == "discontinuous" and (start_sample, gap_seconds) in rec_gaps:
                    text = f"Recording gap {gap_seconds:g} s"
                else:
                    text = f"Recording gap {gap_seconds:g} s (padded with zeros)"
                ann.append((start_sample / rate, gap_seconds, text))

    edf_type = "edf+d" if gap_policy == "discontinuous" else "edf+c"
    if edf_format == "edf" or (edf_format == "auto" and edf_type == "edf+c" and not ann
                               and start_naive.microsecond == 0):
        edf_type = "edf"
    if edf_type == "edf":
        if ann:
            extra_warnings.append(f"plain EDF has no annotations: {len(ann)} annotation(s) not written (--format edf)")
            ann = []
        if start_naive.microsecond:
            extra_warnings.append(f"plain EDF start time truncated by {start_naive.microsecond / 1e6:.6f} s to the whole second")
            start_naive = start_naive.replace(microsecond=0)
    if edge_zero_samples:
        extra_warnings.append(f"{edge_zero_samples} zero sample(s) kept at gap edges (gaps not aligned to 1-s records)")
    kept = np.flatnonzero(keep)
    rows = (kept[:, None] * rate + np.arange(rate)).ravel() if not keep.all() else slice(None)

    p = patient or {}
    write_edf(
        out_path, [np.ascontiguousarray(data[rows, j]) for j in range(len(amp_inputs))], headers,
        start=start_naive, annotations=ann, edf_type=edf_type,
        record_onsets=[float(k) for k in kept] if edf_type == "edf+d" else None,
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
        "mode": mode, "edf_type": edf_type.upper(), "gaps_policy": gap_policy,
        "records_written": int(keep.sum()), "records_omitted_in_gaps": int((~keep).sum()),
        "schema_version": rec.schema_version,
        "highpass_hz": VENDOR_HIGHPASS_HZ if apply_hp else None, "start_at": start_at, "event_timing": event_timing,
        "leading_padded_seconds": lead, "record_guid": rec.record_guid, "patient_guid": None if anonymize else rec.patient_guid,
        "schema_versions": rec.schema_versions,
        "start_utc": start_utc.isoformat(), "start_written": start_naive.isoformat(), "timezone": timezone or "UTC",
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
    report["warnings"] += extra_warnings
    if gap_policy == "discontinuous":
        report["warnings"].append(f"{len(rec_gaps)} recording gap(s) left out of the EDF+D file "
                                  f"(total {sum(g[1] for g in rec_gaps):g} s, {int((~keep).sum())} records)")
        if lead:
            report["warnings"].append(f"{lead} leading second(s) padded with zeros (--start-at record-origin)")
    elif gaps_padded:
        report["warnings"].append(f"{len(gaps_padded)} recording gap(s) padded with zeros (total {sum(g[1] for g in gaps_padded):g} s)")
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
            f.write("\n")
    return report
