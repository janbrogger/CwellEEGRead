#!/usr/bin/env python3
"""Merge Morgoth's CSV outputs into one JSON document.

Morgoth writes, per task, an event-level CSV per EDF (one row per window:
``pred`` for binary tasks or ``class_i_prob`` + ``pred_class`` for
multi-class tasks) into ``pred_<TASK>_<step>sStep/<basename>.csv`` and an
EEG-level summary ``pred_EEG_level_<TASK>.csv`` (file_name, probability,
pred_class_p, confidence, pred_class).  This script gathers them.

Usage: morgoth_to_json.py OUT_DIR [--no-windows] > results.json
"""
import csv
import json
import re
import sys
from pathlib import Path


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    out_dir = Path(argv[0])
    with_windows = "--no-windows" not in argv
    result = {"source": str(out_dir), "recordings": {}}
    for summary in sorted(out_dir.glob("pred_EEG_level_*.csv")):
        task = summary.stem.replace("pred_EEG_level_", "")
        for row in read_csv(summary):
            rec = result["recordings"].setdefault(row["file_name"], {"tasks": {}})
            rec["tasks"].setdefault(task, {})["eeg_level"] = {
                k: (float(v) if re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", v or "") else v)
                for k, v in row.items() if k != "file_name"}
    for event_dir in sorted(out_dir.glob("pred_*Step")):
        task = re.sub(r"^pred_|_\d+sStep$", "", event_dir.name)
        for f in sorted(event_dir.glob("*.csv")):
            rows = read_csv(f)
            rec = result["recordings"].setdefault(f.stem, {"tasks": {}})
            entry = rec["tasks"].setdefault(task, {})
            entry["windows"] = len(rows)
            if rows and "pred" in rows[0]:
                vals = [float(r["pred"]) for r in rows]
                entry["mean_pred"] = sum(vals) / len(vals)
            elif rows and "pred_class" in rows[0]:
                counts = {}
                for r in rows:
                    counts[r["pred_class"]] = counts.get(r["pred_class"], 0) + 1
                entry["pred_class_counts"] = counts
            if with_windows:
                entry["window_rows"] = rows
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
