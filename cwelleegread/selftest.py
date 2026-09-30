"""Equivalence self-test: prove that vendor-mode conversion reproduces the
Cadwell EDF export (REQ024, DES024).

    cwelleegread selftest                          # the bundled public test recording
    cwelleegread selftest <recording> <vendor.edf> # the user's recording and Cadwell's EDF export of it

The vendor export may cover part of the recording: its start time and record
count give the frame range (and the UTC offset of the start time, unless
given), that range is converted in vendor mode (REQ020) and the two files are
compared check by check. Exit code 0 only if every check passes.
"""
from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import os
import sys
import tempfile
from importlib import resources
from pathlib import Path

import numpy as np

from . import __version__
from .edf import convert, resolve_timezone
from .edfread import EdfFile, read_edf
from .ezdata import SUPPORTED_SCHEMA_VERSIONS, open_recording
from .layout import headbox_for, parse_amp_layout

# The bundled test recording (public, no patient; testdata/manifest.json "cadwell-export1").
# Bundle path -> (path in a repository checkout, SHA-256). uses/standalone/build.py copies
# these files into the program file under cwelleegread/selftest_data/.
BUNDLED_ID = "cadwell-export1"
BUNDLED_DESCRIPTION = "46 s of amplifier noise, no patient, Apollo headbox, 250 Hz, 32 channels"
_E1 = "testdata/public/cadwell-export1/"
_REC = "56659ea9-99fd-4d8d-a85c-7502a29229e6-2025-10-31-13-37-42"
BUNDLED = {
    f"CadLink/Data/{_REC}.ezdataindex": (f"{_E1}native-export/CadLink/Data/{_REC}.ezdataindex",
                                         "81b17da22b8884720ba744ba1cfb03e68051a31008d0cf3f8e64d2106e984194"),
    f"CadLink/Data/{_REC}-1.ezdata": (f"{_E1}native-export/CadLink/Data/{_REC}-1.ezdata",
                                      "09b327f189906844b623d547b40493ccb4578745b5a0ffd03dde17914171db31"),
    f"CadLink/Data/{_REC}.ezevents": (f"{_E1}native-export/CadLink/Data/{_REC}.ezevents",
                                      "edc60c0d1dc71aa4b81473927471c04992fb520b3e2165933da634c7abc32248"),
    "test.edf": (f"{_E1}edf/test.edf", "db73ce407b3f4c7539e8cd73e576ce2529c861b82af538997d2e2f79232076fc"),
}
BUNDLED_EDF = "test.edf"

START_TOLERANCE_S = 0.002       # vendor start = frame start + clock correction, to ~1 µs
ANNOTATION_TOLERANCE_S = 0.001
MAX_STEPS = 1                   # samples: at most one quantisation step apart
GAIN_TOLERANCE = 1e-4           # |gain - 1|; rounding alone gives ~1e-6


class SelfTestError(Exception):
    """A check that failed so that the ones after it cannot run."""


def _check(report: dict, out, name: str, status: str, detail: str, **metrics) -> dict:
    item = {"check": name, "status": status, "detail": detail, **metrics}
    report["checks"].append(item)
    out(f"{status:<5} {name}: {detail}")
    return item


# ------------------------------------------------------------------ bundled data
def bundled_source():
    """(root to read BUNDLED paths from, description, 'bundle' or 'checkout') or None."""
    res = resources.files(__package__).joinpath("selftest_data")
    if res.is_dir():
        # frozen executable (DES025): name it, not its temporary unpack folder
        where = sys.executable if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return res, f"bundled in {where}", "bundle"
    repo = Path(__file__).resolve().parents[1]
    if all((repo / src).is_file() for src, _ in BUNDLED.values()):
        return repo, f"{_E1.rstrip('/')} (repository checkout)", "checkout"
    return None


def materialise_bundled(dest: str) -> tuple[str, list[str]]:
    """Copy the bundled files to dest (SQLite needs real files), verifying each SHA-256.
    Returns (source description, names of files whose checksum failed)."""
    src = bundled_source()
    if src is None:
        raise SelfTestError("bundled test recording not found (neither in the program file nor in a checkout)")
    root, where, kind = src
    bad = []
    for name, (repo_path, sha) in BUNDLED.items():
        data = root.joinpath(name if kind == "bundle" else repo_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            bad.append(name)
        target = Path(dest) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return where, bad


# ------------------------------------------------------------------ alignment
def _fmt_offset(off: dt.timedelta) -> str:
    minutes = int(off.total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    return f"UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def align(rec, vendor: EdfFile, timezone: str | None = None) -> dict:
    """Frame range and UTC offset of the vendor export (DES024). Frame n starts at its
    time stamp plus the clock correction, or, when not stored, at the nearest stored
    frame's start plus the difference in frame numbers in seconds."""
    numbers = [fi["number"] for fi in rec.frame_index]
    starts = [fi["timestamp"] + rec.clock_correction for fi in rec.frame_index]
    stored = dict(zip(numbers, starts))

    def frame_start(n: int) -> dt.datetime:
        if n in stored:
            return stored[n]
        i = min(max(bisect.bisect_left(numbers, n), 0), len(numbers) - 1)
        if i > 0 and abs(numbers[i - 1] - n) < abs(numbers[i] - n):
            i -= 1
        return starts[i] + dt.timedelta(seconds=n - numbers[i])

    local = vendor.start + dt.timedelta(seconds=vendor.start_subsecond)
    n_records = int(round(vendor.n_records * vendor.record_duration))
    if timezone:
        tz = resolve_timezone(timezone)
        u = local.replace(tzinfo=tz)
        offsets = [(timezone, u.utcoffset())]
    else:
        offsets = [(None, dt.timedelta(minutes=15 * q)) for q in range(-48, 57)]
    candidates = []
    for name, off in offsets:
        u = (local - off).replace(tzinfo=dt.timezone.utc)
        i = min(max(bisect.bisect_left(starts, u), 0), len(starts) - 1)
        guess = numbers[i] + round((u - starts[i]).total_seconds())
        best = min((abs((u - frame_start(n)).total_seconds()), n) for n in (guess - 1, guess, guess + 1))
        resid, n = best
        if resid <= START_TOLERANCE_S and n >= 0 and n + n_records <= numbers[-1]:
            candidates.append({"first_frame": n, "last_frame": n + n_records, "residual_us": round(resid * 1e6, 1),
                               "utc_offset": _fmt_offset(off), "timezone": name or _fmt_offset(off),
                               "timezone_source": "given" if name else "inferred"})
    result = {"vendor_start_local": local.isoformat(), "vendor_records": vendor.n_records,
              "recording_frames": [numbers[0], numbers[-1]], "candidates": candidates}
    if len(candidates) == 1:
        result.update(candidates[0])
    return result


# ------------------------------------------------------------------ comparisons
def _common(mine: EdfFile, vendor: EdfFile):
    """Channel pairs (index, our signal, vendor signal, our digital, vendor digital) over the
    common records, in file order; channels with different samples per record are skipped."""
    n_rec = min(mine.n_records, vendor.n_records)
    for j, (a, b) in enumerate(zip(mine.signals, vendor.signals)):
        if a.samples_per_record == b.samples_per_record:
            n = n_rec * a.samples_per_record
            yield j, a, b, mine.digital[j][:n], vendor.digital[j][:n]


def compare_signals(mine: EdfFile, vendor: EdfFile) -> tuple[bool, str, dict]:
    diffs = []
    if len(mine.signals) != len(vendor.signals):
        diffs.append(f"{len(mine.signals)} signals, vendor {len(vendor.signals)}")
    for j, (a, b) in enumerate(zip(mine.signals, vendor.signals)):
        for what, x, y in (("label", a.label, b.label), ("samples/record", a.samples_per_record, b.samples_per_record),
                           ("physical range", (a.physical_min, a.physical_max), (b.physical_min, b.physical_max)),
                           ("digital range", (a.digital_min, a.digital_max), (b.digital_min, b.digital_max))):
            if x != y:
                diffs.append(f"signal {j + 1} {what} {x!r}, vendor {y!r}")
    if mine.record_duration != vendor.record_duration:
        diffs.append(f"record duration {mine.record_duration:g} s, vendor {vendor.record_duration:g} s")
    if mine.n_records != vendor.n_records:
        diffs.append(f"{mine.n_records} records, vendor {vendor.n_records}")
    rates = sorted({s.samples_per_record / vendor.record_duration for s in vendor.signals})
    ok = not diffs
    detail = (f"{len(vendor.signals)} signals, labels, {'/'.join(f'{r:g}' for r in rates)} Hz, "
              f"{vendor.record_duration:g}-s records x {vendor.n_records}, physical and digital ranges identical"
              if ok else f"{len(diffs)} difference(s): " + "; ".join(diffs[:5]) + (" ..." if len(diffs) > 5 else ""))
    return ok, detail, {"differences": diffs}


def compare_start(mine: EdfFile, vendor: EdfFile) -> tuple[bool, str, dict]:
    d = (mine.start - vendor.start).total_seconds() + (mine.start_subsecond - vendor.start_subsecond)
    ok = mine.start == vendor.start and abs(d) <= 0.001
    detail = (f"{vendor.start:%d.%m.%y %H.%M.%S} +{vendor.start_subsecond:.7f} s, ours "
              f"{mine.start:%d.%m.%y %H.%M.%S} +{mine.start_subsecond:.7f} s (difference {d * 1e6:.1f} µs)")
    return ok, detail, {"difference_us": round(d * 1e6, 3)}


def compare_samples(mine: EdfFile, vendor: EdfFile) -> tuple[bool, str, dict]:
    total = identical = 0
    worst, per_channel = 0.0, []
    for j, a, b, x, v in _common(mine, vendor):
        if (a.physical_min, a.physical_max, a.digital_min, a.digital_max) == \
                (b.physical_min, b.physical_max, b.digital_min, b.digital_max):
            d = np.abs(x.astype(np.int32) - v.astype(np.int32)).astype(np.float64)
        else:                                      # different ranges: physical, in the coarser step
            d = np.abs(a.physical(x) - b.physical(v)) / max(a.step, b.step)
        total += d.size
        identical += int(np.count_nonzero(d < 1e-9))
        m = float(d.max()) if d.size else 0.0
        worst = max(worst, m)
        if m > 0:
            per_channel.append({"signal": j + 1, "label": b.label, "max_steps": round(m, 3),
                                "max_uv": round(m * max(a.step, b.step), 3),
                                "differing": int(np.count_nonzero(d >= 1e-9)), "first_row": int(np.argmax(d > 0))})
    if total == 0:
        return False, "no comparable samples", {}
    ok = worst <= MAX_STEPS + 1e-9
    share = identical / total
    detail = f"{identical} of {total} identical ({100 * share:.4f} %), maximum difference {worst:g} step(s)"
    if per_channel:
        worst_ch = sorted(per_channel, key=lambda c: -c["max_steps"])
        detail += "; differing: " + ", ".join(f"{c['label']} ({c['max_steps']:g} step, {c['differing']} samples)"
                                              for c in worst_ch[:4]) + (" ..." if len(worst_ch) > 4 else "")
    detail += f"; tolerance {MAX_STEPS} step"
    return ok, detail, {"samples": total, "identical": identical, "identical_share": share,
                        "max_steps": worst, "channels_differing": per_channel}


def compare_gain_lag(mine: EdfFile, vendor: EdfFile) -> tuple[bool, str, dict]:
    sxy = sxx = syy = 0.0
    n_used, n = 0, 0
    windows = []                     # first differences over the lag window only (memory)
    for j, a, b, x, v in _common(mine, vendor):
        px, pv = a.physical(x), b.physical(v)
        if px.size < 2 or np.ptp(px) == 0 or np.ptp(pv) == 0:       # constant (the reference channel)
            continue
        # through the origin, not centred: a scale error scales physical values about 0 µV,
        # and on unfiltered data the DC offset is where it shows most
        sxy += float(px @ pv)
        sxx += float(px @ px)
        syy += float(pv @ pv)
        n_used += 1
        n += px.size
        rate = int(round(a.samples_per_record / mine.record_duration))
        w = min(px.size, 60 * rate)
        s0 = (px.size - w) // 2
        windows.append((np.diff(px[s0:s0 + w]), np.diff(pv[s0:s0 + w]), rate))
    if not n_used or sxx == 0:
        return False, "no channel with signal in both files", {}
    gain = sxy / sxx
    residual = max(syy - 2 * gain * sxy + gain * gain * sxx, 0.0)
    se = float(np.sqrt(residual / max(n - 1, 1) / sxx))
    # lag: shift that maximises the summed cross-product of the first differences
    rate = windows[0][2]
    k_max = max(rate // 10, 1)
    score = np.zeros(2 * k_max + 1)
    for da, db, _ in windows:
        for i, k in enumerate(range(-k_max, k_max + 1)):
            score[i] += float(da[max(0, -k):len(da) - max(0, k)] @ db[max(0, k):len(db) - max(0, -k)])
    lag = int(np.argmax(score)) - k_max
    seconds = (len(windows[0][0]) + 1) / rate
    ok = abs(gain - 1) <= GAIN_TOLERANCE and lag == 0
    detail = (f"gain {gain:.6f} (vendor/ours, standard error {se:.1e}, tolerance {GAIN_TOLERANCE:g}) over "
              f"{n_used} channels; lag {lag} samples (searched ±{k_max} over {seconds:g} s)")
    return ok, detail, {"gain": gain, "gain_standard_error": se, "channels": n_used, "lag_samples": lag,
                        "lag_search_samples": k_max}


def compare_annotations(mine: EdfFile, vendor: EdfFile) -> tuple[bool, str, dict]:
    def group(anns):
        g = {}
        for onset, _, text in anns:
            g.setdefault(text, []).append(onset)
        return {t: sorted(o) for t, o in g.items()}
    ours, theirs = group(mine.annotations), group(vendor.annotations)
    matched, worst, only_ours, only_vendor = 0, 0.0, [], []
    for text in sorted(set(ours) | set(theirs)):
        a, b = list(ours.get(text, [])), list(theirs.get(text, []))
        i = k = 0
        while i < len(a) and k < len(b):          # two-pointer match within the tolerance
            d = a[i] - b[k]
            if abs(d) <= ANNOTATION_TOLERANCE_S + 1e-9:
                matched += 1
                worst = max(worst, abs(d))
                i += 1
                k += 1
            elif d < 0:
                only_ours.append((a[i], text))
                i += 1
            else:
                only_vendor.append((b[k], text))
                k += 1
        only_ours += [(o, text) for o in a[i:]]
        only_vendor += [(o, text) for o in b[k:]]
    ok = not only_ours and not only_vendor
    detail = (f"{matched} of {len(vendor.annotations)} vendor annotations matched (onset within "
              f"{ANNOTATION_TOLERANCE_S * 1000:g} ms, largest {worst * 1000:.3f} ms, and text)")
    if only_vendor:
        detail += f"; only in the vendor file: " + ", ".join(f"{o:.3f} s {t!r}" for o, t in sorted(only_vendor)[:5])
    if only_ours:
        detail += f"; only in ours: " + ", ".join(f"{o:.3f} s {t!r}" for o, t in sorted(only_ours)[:5])
    return ok, detail, {"matched": matched, "vendor": len(vendor.annotations), "ours": len(mine.annotations),
                        "largest_difference_ms": worst * 1000,
                        "only_vendor": [{"onset": o, "text": t} for o, t in sorted(only_vendor)],
                        "only_ours": [{"onset": o, "text": t} for o, t in sorted(only_ours)]}


# ------------------------------------------------------------------ the self-test
def run(recording: str | None = None, vendor_edf: str | None = None, *, timezone: str | None = None,
        labels: dict | None = None, highpass: str = "auto", keep_edf: str | None = None, out=print) -> dict:
    """Run the self-test; returns the report (report['verdict'] is 'PASS' or 'FAIL')."""
    report = {"cwelleegread_version": __version__, "kind": "bundled" if recording is None else "user", "checks": []}
    with tempfile.TemporaryDirectory(prefix="cwelleegread-selftest-") as tmp:
        try:
            _run(report, recording, vendor_edf, tmp, timezone, labels, highpass, keep_edf, out)
        except SelfTestError as exc:
            report["stopped"] = str(exc)
            out(f"stopped: {exc}")
    failed = [c["check"] for c in report["checks"] if c["status"] == "FAIL"]
    report["verdict"] = "FAIL" if failed or report.get("stopped") else "PASS"
    if report["verdict"] == "PASS":
        out(f"RESULT: PASS - the vendor-compatible conversion reproduces the Cadwell EDF export "
            f"({sum(c['status'] == 'PASS' for c in report['checks'])} checks passed)")
    else:
        out("RESULT: FAIL - " + (f"failed: {', '.join(failed)}" if failed else "the self-test could not be completed"))
    return report


def _run(report, recording, vendor_edf, tmp, timezone, labels, highpass, keep_edf, out):
    if recording is None:
        out(f"cwelleegread {__version__} self-test on the bundled test recording {BUNDLED_ID} ({BUNDLED_DESCRIPTION})")
        where, bad = materialise_bundled(tmp)
        report["test_data"] = where
        _check(report, out, "bundled files", "FAIL" if bad else "PASS",
               (f"checksum mismatch: {', '.join(bad)}" if bad else f"{len(BUNDLED)} files, SHA-256 verified")
               + f", {where}", files=len(BUNDLED), mismatches=bad)
        if bad:
            raise SelfTestError("the bundled test data are damaged")
        recording, vendor_edf = tmp, os.path.join(tmp, BUNDLED_EDF)
    else:
        out(f"cwelleegread {__version__} self-test on {recording} against {vendor_edf}")
    try:
        rec = open_recording(recording)
    except Exception as exc:
        _check(report, out, "recording", "FAIL", f"cannot open: {exc}")
        raise SelfTestError("no recording to convert") from exc
    try:
        vendor = read_edf(vendor_edf)
    except Exception as exc:
        _check(report, out, "vendor EDF", "FAIL", f"cannot read {vendor_edf}: {exc}")
        raise SelfTestError("no vendor EDF to compare with") from exc

    amp = parse_amp_layout(rec.amp_layout_blob)
    headbox, known = headbox_for(amp["amp_type"])
    supported = rec.schema_version in SUPPORTED_SCHEMA_VERSIONS
    numbers = [fi["number"] for fi in rec.frame_index]
    summary = {"schema_version": rec.schema_version, "schema_supported": supported, "amp_type": amp["amp_type"],
               "headbox": headbox["name"] if known else None, "sample_rate": rec.sample_rate,
               "channels": len(rec.channels), "frames": len(numbers),
               "frame_numbers": [numbers[0], numbers[-1]] if numbers else None, "gaps": len(rec.gaps)}
    report["recording"] = summary
    notes = []
    if not supported:
        notes.append(f"schema {rec.schema_version or 'unknown'} is not a supported version "
                     f"({', '.join(SUPPORTED_SCHEMA_VERSIONS)}): converted anyway for this test")
    if not known:
        notes.append(f"amplifier type {amp['amp_type']} unknown: labels and ranges of the "
                     f"{headbox['name']} table used")
    _check(report, out, "recording", "WARN" if notes else "INFO",
           f"schema {rec.schema_version or '?'} ({'supported' if supported else 'NOT supported'}), "
           f"{headbox['name'] if known else 'unknown'} headbox (amplifier type {amp['amp_type']}), "
           f"{len(rec.channels)} channels, {rec.sample_rate} Hz, frames {numbers[0]}-{numbers[-1]}, "
           f"{len(rec.gaps)} gap(s)" + "".join(f"; {n}" for n in notes), **summary)
    report["vendor_edf"] = {"file": os.path.basename(vendor_edf), "edf_type": vendor.edf_type,
                            "signals": len(vendor.signals), "records": vendor.n_records,
                            "record_duration": vendor.record_duration, "annotations": len(vendor.annotations)}

    try:
        al = align(rec, vendor, timezone)
    except ValueError as exc:
        _check(report, out, "alignment", "FAIL", str(exc))
        raise SelfTestError("cannot align") from exc
    report["alignment"] = al
    cands = al["candidates"]
    if len(cands) != 1:
        if not cands:
            detail = (f"the vendor EDF's start {al['vendor_start_local']} (local), {vendor.n_records} records, "
                      f"matches no frame of this recording (frames {numbers[0]}-{numbers[-1]}"
                      + (f", UTC offset from --timezone {timezone}" if timezone else ", any UTC offset")
                      + "): the EDF belongs to another recording" + (", or --timezone is wrong" if timezone else ""))
        else:
            detail = ("the vendor EDF's start matches frames of this recording at several UTC offsets ("
                      + ", ".join(f"{c['utc_offset']}: frame {c['first_frame']}" for c in cands)
                      + "); give the time zone of the export with --timezone")
        _check(report, out, "alignment", "FAIL", detail)
        raise SelfTestError("cannot align the vendor EDF with the recording")
    first, last = al["first_frame"], al["last_frame"]
    whole = first <= numbers[0] and last >= numbers[-1]
    _check(report, out, "alignment", "PASS",
           f"vendor EDF starts at frame {first} (within {al['residual_us']:g} µs), {al['utc_offset']} "
           f"({al['timezone_source']}{' ' + timezone if timezone else ''}); {vendor.n_records} records = frames "
           f"{first}-{last - 1}, the vendor drops frame {last}" + ("" if whole else "; part of the recording"),
           **{k: al[k] for k in ("first_frame", "last_frame", "residual_us", "utc_offset", "timezone_source")})

    view = rec.frame_range(first, last)
    ours_path = keep_edf or os.path.join(tmp, "selftest-ours.edf")
    try:
        conv = convert(view, ours_path, mode="vendor", timezone=al["timezone"], labels=labels, highpass=highpass,
                       start_at="record-origin" if view.frame_index[0]["number"] > 0 else "first-frame",
                       allow_unsupported=True, patient={"code": "X", "name": "X"})
    except Exception as exc:
        _check(report, out, "conversion", "FAIL", f"{type(exc).__name__}: {exc}")
        raise SelfTestError("the conversion failed") from exc
    report["conversion"] = {k: conv[k] for k in ("mode", "edf_type", "seconds", "highpass_hz", "event_timing",
                                                 "leading_padded_seconds", "frames_used", "timezone", "warnings")}
    report["conversion"]["samples_removed_by_vendor_rule"] = len(conv["samples_removed_by_vendor_rule"])
    if keep_edf:
        report["conversion"]["kept_edf"] = os.path.abspath(keep_edf)
    mine = read_edf(ours_path)

    for name, fn in (("signals", compare_signals), ("start time", compare_start), ("samples", compare_samples),
                     ("gain and lag", compare_gain_lag), ("annotations", compare_annotations)):
        ok, detail, metrics = fn(mine, vendor)
        _check(report, out, name, "PASS" if ok else "FAIL", detail, **metrics)

