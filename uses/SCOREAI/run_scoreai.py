#!/usr/bin/env python3
"""Wrapper that runs an externally supplied SCORE-AI program on EDF files
and normalises the result to JSON.  See README.md.

Usage:
  run_scoreai.py [--check-only] [--dry-run] [--out FILE] recording.edf
  run_scoreai.py [--check-only] [--dry-run] --batch DIR

The program is given by the environment variable SCOREAI_CMD, a shell
template with the placeholders {edf} and {json}, e.g.
  SCOREAI_CMD='/opt/scoreai/scoreai --input {edf} --output {json}'
"""
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

REQUIRED_1020 = ["FP1", "F3", "C3", "P3", "F7", "T3", "T5", "O1", "FZ", "CZ", "PZ",
                 "FP2", "F4", "C4", "P4", "F8", "T4", "T6", "O2"]
ALIASES = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}
NORMALISED_KEYS = ["normal", "abnormal", "epileptiform_focal", "epileptiform_generalized",
                   "nonepileptiform_focal", "nonepileptiform_diffuse"]


def norm_label(label):
    lab = label.upper().replace("EEG", "").replace("POL", "").strip()
    lab = re.sub(r"\(.*?\)", "", lab)
    lab = lab.split("-")[0].strip()
    return ALIASES.get(lab, lab)


def check_edf(path):
    """Return (ok, list of check messages) for the published SCORE-AI input assumptions."""
    checks, ok = [], True
    try:
        import pyedflib
    except ImportError:
        return True, ["pyedflib not installed - input checks skipped"]
    with pyedflib.EdfReader(str(path)) as f:
        labels = [norm_label(l) for l in f.getSignalLabels()]
        dur = f.getFileDuration()
        srates = sorted({int(round(f.getSampleFrequency(i))) for i in range(f.signals_in_file)})
        units = {f.getPhysicalDimension(i).strip() for i in range(f.signals_in_file)}
    missing = [c for c in REQUIRED_1020 if c not in labels]
    if missing:
        ok = False
        checks.append(f"missing 10-20 electrodes: {missing}")
    else:
        checks.append("all 19 10-20 electrodes present")
    if not any(l.startswith(("ECG", "EKG")) for l in labels):
        checks.append("warning: no ECG/EKG channel found")
    if dur < 15 * 60:
        checks.append(f"warning: recording is only {dur / 60:.1f} min (routine EEG expected ~20-30 min)")
    checks.append(f"sampling rates: {srates} Hz; physical units: {sorted(units)}")
    if not any(u.lower() in ("uv", "µv") for u in units):
        checks.append("warning: no channel in uV")
    return ok, checks


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run_one(edf, out, dry_run=False, check_only=False):
    edf, out = Path(edf), Path(out)
    ok, checks = check_edf(edf)
    result = {"input": {"file": str(edf), "sha256": sha256(edf), "checks": checks, "ok": ok}}
    if check_only:
        print(json.dumps(result, indent=2))
        return 0 if ok else 1
    template = os.environ.get("SCOREAI_CMD")
    if not template:
        sys.stderr.write("SCOREAI_CMD is not set - see README.md\n")
        return 2
    tmp_json = out.with_suffix(".program.json")
    cmd = template.format(edf=shlex.quote(str(edf)), json=shlex.quote(str(tmp_json)))
    result["provenance"] = {"command": cmd, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    if dry_run:
        print(cmd)
        return 0
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    result["provenance"]["exit_code"] = proc.returncode
    result["provenance"]["stderr_tail"] = proc.stderr[-2000:]
    raw = {}
    if tmp_json.exists():
        try:
            raw = json.loads(tmp_json.read_text(encoding="utf-8"))
        except Exception as exc:
            result["provenance"]["parse_error"] = str(exc)
    elif proc.stdout.strip().startswith("{"):
        try:
            raw = json.loads(proc.stdout)
        except Exception as exc:
            result["provenance"]["parse_error"] = str(exc)
    result["raw"] = raw
    result["scoreai"] = {k: raw[k] for k in NORMALISED_KEYS if isinstance(raw, dict) and k in raw}
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0 if proc.returncode == 0 else 1


def main(argv):
    if not argv or "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    dry = "--dry-run" in argv
    check_only = "--check-only" in argv
    args = [a for a in argv if a not in ("--dry-run", "--check-only")]
    out = None
    if "--out" in args:
        i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
    if "--batch" in args:
        folder = Path(args[args.index("--batch") + 1])
        rc = 0
        for edf in sorted(folder.rglob("*.edf")):
            rc |= run_one(edf, edf.with_suffix(".scoreai.json"), dry, check_only)
        return rc
    edf = Path(args[0])
    return run_one(edf, out or edf.with_suffix(".scoreai.json"), dry, check_only)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
