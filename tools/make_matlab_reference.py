#!/usr/bin/env python3
"""Write reference data for the MATLAB/Octave port tests (tests/test_octave_port.py).

For an export folder, writes into OUT_DIR:
  frames.bin        first N frame blobs, each as u32 length + bytes (little-endian)
  expected.bin      float64 matrix (samples x channels, column-major = MATLAB order) in microvolts,
                    the Python decoder's output for those frames, columns in amplifier-input order
  meta.json         rate, amp_inputs, per-frame sample counts, frame numbers, start ticks, labels,
                    gaps, first/last event, record guid, amp type, clock correction
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cwelleegread import open_recording                      # noqa: E402
from cwelleegread.ezdata import UNIT_UV                       # noqa: E402
from cwelleegread.layout import default_labels, parse_amp_layout  # noqa: E402


def main(export, out_dir, n_frames=20):
    rec = open_recording(export)
    os.makedirs(out_dir, exist_ok=True)
    import sqlite3
    blobs = {}
    for fi in rec.frame_index[:n_frames]:
        path = os.path.join(rec.data_dir, fi["join_db"])
        con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
        blobs[fi["key"]] = con.execute("select Data from FrameInfo where hex(FrameKey)=?", (fi["key"],)).fetchone()[0]
    with open(os.path.join(out_dir, "frames.bin"), "wb") as f:
        for fi in rec.frame_index[:n_frames]:
            b = blobs[fi["key"]]
            f.write(struct.pack("<I", len(b))); f.write(b)
    frames = []
    for fr in rec.frames():
        frames.append(fr)
        if len(frames) == n_frames:
            break
    cols = [np.concatenate([fr.samples[a] for fr in frames]) * UNIT_UV for a in rec.amp_inputs]
    X = np.column_stack(cols)
    X.astype("<f8").T.tofile(os.path.join(out_dir, "expected.bin"))          # column-major for MATLAB fread
    amp = parse_amp_layout(rec.amp_layout_blob)
    ev = rec.events()
    meta = {
        "export": os.path.abspath(export), "index_path": os.path.abspath(rec.index_path),
        "rate": rec.sample_rate, "amp_inputs": rec.amp_inputs, "n_frames": n_frames,
        "samples_per_frame": [len(fr.samples[rec.amp_inputs[0]]) for fr in frames],
        "frame_numbers": [fr.number for fr in frames], "start_ticks": [fr.start_ticks for fr in frames],
        "shape": list(X.shape), "unit_uv": UNIT_UV,
        "labels": [default_labels(rec.amp_inputs, amp["amp_type"])[a] for a in rec.amp_inputs],
        "amp_type": amp["amp_type"], "record_guid": rec.record_guid, "patient_guid": rec.patient_guid,
        "n_index_frames": len(rec.frame_index), "gaps": [{"start_offset": g["start_offset"], "end_offset": g["end_offset"]} for g in rec.gaps],
        "clock_correction_us": rec.clock_correction.total_seconds() * 1e6,
        "origin_iso": rec.origin.isoformat(),
        "n_events": len(ev), "first_event": [ev[0].type, ev[0].text, ev[0].start_ticks] if ev else None,
        "n_events_not_deleted": sum(1 for e in ev if not e.deleted),
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, default=str)
    print(f"wrote {out_dir}: {n_frames} frames, expected {X.shape}")


def dump_tables(export, out_file):
    """Canonical dump of every table of every SQLite file of an export, for
    verifying the native MATLAB/Octave SQLite reader byte for byte.

    Stream: for each file (sorted name) and each table (sqlite_master order):
      u8 0xFF, u32 len + file name, u32 len + table name, u32 nrows, u32 ncols,
      then ncols x (u32 len + column name), then rows in rowid order:
        i64 rowid, then per value: u8 type (0 null, 1 int, 2 real, 3 text, 4 blob),
        int -> i64, real -> f64, text -> u32 len + utf8, blob -> u32 len + bytes."""
    import glob
    import sqlite3
    rec = open_recording(export)
    files = sorted(glob.glob(os.path.join(rec.data_dir, "*.ez*")))
    with open(out_file, "wb") as out:
        for path in files:
            con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
            for (name,) in con.execute("select name from sqlite_master where type='table' order by rowid"):
                cur = con.execute(f'select rowid, * from "{name}" order by rowid')
                cols = [d[0] for d in cur.description][1:]
                rows = cur.fetchall()
                out.write(b"\xff")
                for s in (os.path.basename(path), name):
                    e = s.encode("utf-8"); out.write(struct.pack("<I", len(e)) + e)
                out.write(struct.pack("<II", len(rows), len(cols)))
                for c in cols:
                    e = c.encode("utf-8"); out.write(struct.pack("<I", len(e)) + e)
                for row in rows:
                    out.write(struct.pack("<q", row[0]))
                    for v in row[1:]:
                        if v is None: out.write(b"\x00")
                        elif isinstance(v, int): out.write(b"\x01" + struct.pack("<q", v))
                        elif isinstance(v, float): out.write(b"\x02" + struct.pack("<d", v))
                        elif isinstance(v, str):
                            e = v.encode("utf-8"); out.write(b"\x03" + struct.pack("<I", len(e)) + e)
                        else:
                            out.write(b"\x04" + struct.pack("<I", len(v)) + bytes(v))
    print(f"wrote {out_file}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20)
    if "--tables" in sys.argv:
        dump_tables(sys.argv[1], os.path.join(sys.argv[2], "tables.bin"))
