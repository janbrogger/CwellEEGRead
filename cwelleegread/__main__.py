"""Command line: python -m cwelleegread convert|inspect ...  (REQ006)"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

from . import __version__
from .ezdata import open_recording


def cmd_inspect(args):
    rec = open_recording(args.input)
    print(f"record {rec.record_guid}  patient {rec.patient_guid}  schema {rec.schema_versions[-1] if rec.schema_versions else '?'}")
    print(f"start (UTC) {rec.start_time}  rate {rec.sample_rate} Hz  channels {len(rec.channels)}  "
          f"frames {len(rec.frame_index)}  tracks {rec.tracks}  gaps {len(rec.gaps)}")
    for c in rec.channels:
        print(f"  ch {c.channel:2d} amp_input {c.amp_input:2d} rate {c.sample_rate}")
    ev = rec.events()
    print(f"events: {len(ev)}")
    for e in ev[: args.max_events]:
        print(f"  {e.start.strftime('%H:%M:%S.%f')[:-3]} {e.type:<28} {e.text[:60]!r}")
    return 0


def cmd_convert(args):
    from .edf import convert
    from .layout import load_labels_file
    if os.path.exists(args.output) and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 1
    rec = open_recording(args.input)
    labels = load_labels_file(args.labels) if args.labels else None
    tmp = args.output + ".part"
    try:
        report = convert(rec, tmp, mode=args.mode, labels=labels, timezone=args.timezone,
                         anonymize=args.anonymize, report_path=None, all_events=args.all_events,
                         highpass=args.highpass, start_at=args.start_at, event_timing=args.event_timing,
                         patient={"name": args.patient_name} if args.patient_name else None)
        os.replace(tmp, args.output)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    report["output"] = os.path.abspath(args.output)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
            f.write("\n")
    print(f"wrote {args.output}: {report['seconds']} s, {len(report['channels'])} channels, "
          f"{report['annotations_written']} annotations, mode {report['mode']}")
    for wmsg in report["warnings"]:
        print("warning:", wmsg)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cwelleegread", description="Convert Cadwell Arc EEG (CadLink export) to EDF+.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect", help="print record, channels and events")
    i.add_argument("input"); i.add_argument("--max-events", type=int, default=40)
    c = sub.add_parser("convert", help="convert one recording to EDF+")
    c.add_argument("input", help="export folder, CadLink/Data folder or .ezdataindex file")
    c.add_argument("output", help="EDF file to write")
    c.add_argument("--mode", choices=["raw", "vendor"], default="raw",
                   help="raw = keep every sample (default); vendor = mimic the Cadwell EDF export")
    c.add_argument("--timezone", help="IANA zone for the EDF start time, e.g. Europe/Oslo (default UTC)")
    c.add_argument("--labels", help="file with 'amp_input label' lines overriding the default layout")
    c.add_argument("--anonymize", action="store_true", help="no patient GUID; comment/user event texts replaced by type")
    c.add_argument("--patient-name", help="patient name field (default X)")
    c.add_argument("--all-events", action="store_true", help="also export amplifier bookkeeping events")
    c.add_argument("--highpass", choices=["auto", "on", "off"], default="auto",
                   help="vendor EDF-export high-pass (2nd-order Butterworth 0.16 Hz): auto = in vendor mode for Essentia")
    c.add_argument("--start-at", choices=["first-frame", "record-origin"], default="first-frame",
                   help="data start: first stored frame (default) or the record origin with leading zeros")
    c.add_argument("--event-timing", choices=["auto", "ticks", "stamp"], default="auto",
                   help="place annotations on the sample clock (ticks, accurate) or by wall-clock stamp as the vendor does "
                        "(stamp, early by the clock drift, ~0.35 s/h on Essentia); auto = ticks in raw mode, stamp in vendor mode")
    c.add_argument("--json", help="write a JSON conversion report here")
    c.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = ap.parse_args(argv)
    try:
        return {"inspect": cmd_inspect, "convert": cmd_convert}[args.cmd](args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
