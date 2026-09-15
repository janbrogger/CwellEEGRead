#!/usr/bin/env python3
"""Inventory of a Cadwell Arc "CadLink" study export (read-only, stdlib only).

Usage:  python3 tools/cadwell_inspect.py <export folder or CadLink/Data folder> [--json]

Prints, for every SQLite file in the export (.ezdataindex, .ezevents,
.mediadb, .ezdata):
  - schema version history (SchemaUpdateLog) and table row counts
  - the MediaDescriptor GUIDs (patient / record / author)
  - the EEG track definition (TrackInfo): channel number, amplifier input,
    sampling rate, per-channel scale value
  - the frame index (FrameInfo): tracks, first/last time stamp, frame count,
    gaps, and which "JoinDatabase" files the frames live in and whether
    those files are present
  - the event list (.ezevents)
Findings that this tool relies on are documented in
docs/research/cadwell-file-format.md (section "Findings from test export 1").
"""
import datetime as dt
import glob
import json
import os
import re
import sqlite3
import struct
import sys

TRACK_RECORD_TAG = bytes.fromhex("ab792193de4225a2")   # precedes each channel record in TrackInfo


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def tables(con):
    return [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]


def rowcount(con, name):
    return con.execute(f'select count(*) from "{name}"').fetchone()[0]


def schema_versions(con):
    if "SchemaUpdateLog" not in tables(con):
        return []
    return [f"{o}->{n} ({ts[:10]})" for o, n, ts in
            con.execute("select OldVersion, NewVersion, TimeStamp from SchemaUpdateLog order by TimeStamp")]


def media_descriptor(con):
    """MediaDescriptor = u32 tag, u32 0, then three length-prefixed ASCII GUIDs, then 8 bytes."""
    if "MediaHeader" not in tables(con):
        return None
    row = con.execute("select Value from MediaHeader where Key='MediaDescriptor'").fetchone()
    if not row:
        return None
    b, pos, guids = row[0], 8, []
    for _ in range(3):
        n = struct.unpack_from("<I", b, pos)[0]
        guids.append(b[pos + 4:pos + 4 + n].decode("ascii", "replace"))
        pos += 4 + n
    return {"guid1_patient?": guids[0], "guid2_record": guids[1], "guid3_author?": guids[2],
            "trailer_hex": b[pos:].hex()}


def track_info(con):
    """Decode the 32-channel TrackInfo blob (81-byte records after an 8-byte tag)."""
    if "TrackInfo" not in tables(con):
        return []
    out = []
    for off, track, data in con.execute("select Offset, Track, Data from TrackInfo"):
        if not data:
            continue
        chans = []
        for m in re.finditer(re.escape(TRACK_RECORD_TAG), data):
            rec = data[m.end():m.end() + 65]
            if len(rec) < 65:
                break
            u = struct.unpack("<16I", rec[:64])
            chans.append({"channel": u[1], "amp_input": u[4], "sample_rate": u[10],
                          "scale_f32": round(struct.unpack("<f", rec[48:52])[0], 6),
                          "field2": u[2], "field9_u32": u[9], "flag": rec[64]})
        out.append({"offset": off, "track": track, "blob_bytes": len(data),
                    "header_hex": data[:44].hex(), "channels": chans})
    return out


def frame_index(con, folder):
    if "FrameInfo" not in tables(con):
        return None
    cols = [r[1] for r in con.execute("pragma table_info(FrameInfo)")]
    if "TimeStamp" not in cols:
        # the waveform/AV data table: DataKey + Data blob
        sizes = [r[0] for r in con.execute("select length(Data) from FrameInfo")]
        return {"kind": "data", "frames": len(sizes), "bytes": sum(sizes),
                "min_frame": min(sizes) if sizes else 0, "max_frame": max(sizes) if sizes else 0}
    sel = "TimeStamp, Track" + (", Offset" if "Offset" in cols else ", NULL") + \
          (", JoinDatabase" if "JoinDatabase" in cols else ", NULL") + (", Status" if "Status" in cols else ", NULL")
    per = {}
    for ts, track, off, join, status in con.execute(f"select {sel} from FrameInfo order by Track, TimeStamp"):
        t = per.setdefault(track, {"frames": 0, "first": ts, "last": ts, "join_files": set(), "statuses": set(),
                                   "offsets": []})
        t["frames"] += 1
        t["last"] = ts
        t["join_files"].add(join)
        t["statuses"].add(status)
        if off is not None:
            t["offsets"].append(off)
    for t in per.values():
        offs = t.pop("offsets")
        t["offset_range"] = [min(offs), max(offs)] if offs else None
        t["missing_offsets"] = sorted(set(range(min(offs), max(offs) + 1)) - set(offs)) if offs else []
        t["join_files"] = {f: os.path.exists(os.path.join(folder, f)) for f in t["join_files"]}
        t["statuses"] = sorted(t["statuses"])
    gaps = []
    if "GapInfo" in tables(con):
        gaps = [dict(zip(["track", "start_offset", "end_offset", "start", "end"], r))
                for r in con.execute("select Track, StartOffset, EndOffset, StartTime, EndTime from GapInfo")]
    return {"kind": "index", "tracks": per, "gaps": gaps}


def events(con):
    if "Events" not in tables(con):
        return []
    return [dict(zip(["type", "text", "start", "end", "start_offset_ticks", "end_offset_ticks", "priority", "deleted"], r))
            for r in con.execute("select EventType, Text, StartTime, EndTime, StartOffset, EndOffset, Priority, Deleted "
                                 "from Events order by StartTime")]


def inspect_file(path, folder):
    info = {"file": os.path.basename(path), "bytes": os.path.getsize(path)}
    with open(path, "rb") as f:
        magic = f.read(16)
    if not magic.startswith(b"SQLite format 3"):
        info["note"] = "not a plain SQLite 3 file (encrypted or other format)"
        return info
    con = ro(path)
    info["schema_versions"] = schema_versions(con)
    info["tables"] = {t: rowcount(con, t) for t in tables(con) if not t.startswith("sqlite_")}
    md = media_descriptor(con)
    if md:
        info["media_descriptor"] = md
    ti = track_info(con)
    if ti:
        info["track_info"] = ti
    fi = frame_index(con, folder)
    if fi:
        info["frame_info"] = fi
    ev = events(con)
    if ev:
        info["events"] = ev
    if "MiscInfo" in info["tables"]:
        cols = [r[1] for r in con.execute("pragma table_info(MiscInfo)")]
        vcol = "Value" if "Value" in cols else "DataBlob"
        info["misc_info"] = [{"key": k, "timestamp": ts, "bytes": len(v),
                              "json": (json.loads(v) if isinstance(v, str) and v.startswith("{") else None)}
                             for k, ts, v in con.execute(f"select Key, TimeStamp, {vcol} from MiscInfo")]
    return info


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = argv[0]
    as_json = "--json" in argv
    data_dir = root
    for cand in (root, os.path.join(root, "CadLink", "Data"), os.path.join(root, "Data"),
                 os.path.join(root, "native-export", "CadLink", "Data")):
        if glob.glob(os.path.join(cand, "*.ezdataindex")):
            data_dir = cand
            break
    files = sorted(glob.glob(os.path.join(data_dir, "*")))
    report = {"data_dir": data_dir, "files": [inspect_file(p, data_dir) for p in files if os.path.isfile(p)
                                              and not p.lower().endswith(".pdf")]}
    if as_json:
        json.dump(report, sys.stdout, indent=2, default=str)
        print()
        return 0
    print(f"CadLink data folder: {data_dir}")
    for f in report["files"]:
        print(f"\n=== {f['file']}  ({f['bytes']:,} bytes)")
        if "note" in f:
            print("   ", f["note"])
            continue
        print("    schema:", ", ".join(f["schema_versions"]) or "-")
        print("    tables:", ", ".join(f"{k}={v}" for k, v in f["tables"].items()))
        if "media_descriptor" in f:
            print("    media descriptor:", f["media_descriptor"])
        for ti in f.get("track_info", []):
            print(f"    TrackInfo track {ti['track']}: {len(ti['channels'])} channels; header {ti['header_hex']}")
            for ch in ti["channels"]:
                print(f"       ch {ch['channel']:2d} amp_input {ch['amp_input']:2d} rate {ch['sample_rate']} Hz scale {ch['scale_f32']}"
                      + (f" field2={ch['field2']}" if ch["field2"] else ""))
        fi = f.get("frame_info")
        if fi and fi["kind"] == "index":
            for tr, t in fi["tracks"].items():
                print(f"    track {tr}: {t['frames']} frames {t['first']} .. {t['last']} offsets {t['offset_range']} "
                      f"missing {t['missing_offsets'] or 'none'} status {t['statuses']}")
                for jf, present in t["join_files"].items():
                    print(f"       data in {jf}: {'PRESENT' if present else 'MISSING'}")
            if fi["gaps"]:
                print("    gaps:", fi["gaps"])
        elif fi:
            print(f"    data frames: {fi['frames']} ({fi['bytes']:,} bytes, {fi['min_frame']}..{fi['max_frame']} bytes each)")
        for mi in f.get("misc_info", []):
            j = mi["json"]
            print(f"    MiscInfo {mi['key']} @ {mi['timestamp']} ({mi['bytes']} bytes)"
                  + (f": {j.get('ClassName')} {j.get('Name', '')}" if j else ""))
        for e in f.get("events", []):
            print(f"    event {e['start'][11:23]} {e['type']:<26} {e['text'][:70]!r} offset {e['start_offset_ticks']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
