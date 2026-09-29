"""Command line: cwelleegread convert|batch|inspect ...  (REQ006)"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
import traceback

from . import __version__
from .ezdata import open_recording


def cmd_inspect(args):
    rec = open_recording(args.input)
    from .ezdata import SUPPORTED_SCHEMA_VERSIONS
    support = "supported" if rec.schema_version in SUPPORTED_SCHEMA_VERSIONS else "NOT SUPPORTED"
    print(f"record {rec.record_guid}  patient {rec.patient_guid}  schema {rec.schema_version or '?'} ({support})")
    print(f"start (UTC) {rec.start_time}  rate {rec.sample_rate} Hz  channels {len(rec.channels)}  "
          f"frames {len(rec.frame_index)}  tracks {rec.tracks}  gaps {len(rec.gaps)}")
    for c in rec.channels:
        print(f"  ch {c.channel:2d} amp_input {c.amp_input:2d} rate {c.sample_rate}")
    ev = rec.events()
    print(f"events: {len(ev)}")
    for e in ev[: args.max_events]:
        print(f"  {e.start.strftime('%H:%M:%S.%f')[:-3]} {e.type:<28} {e.text[:60]!r}")
    return 0


CONVERT_OPTIONS = ("mode", "timezone", "anonymize", "all_events", "highpass", "start_at", "event_timing",
                   "gaps", "allow_unsupported")


def convert_one(args, input_path, output):
    """Convert one recording to `output` via `<output>.part` (no partial file on failure).
    Returns the conversion report."""
    from .edf import convert
    from .layout import load_labels_file
    rec = open_recording(input_path)
    labels = load_labels_file(args.labels) if args.labels else None
    tmp = output + ".part"
    try:
        report = convert(rec, tmp, labels=labels, report_path=None, edf_format=args.format,
                         patient={"name": args.patient_name} if args.patient_name else None,
                         **{k: getattr(args, k) for k in CONVERT_OPTIONS})
        os.replace(tmp, output)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    report["output"] = os.path.abspath(output)
    return report


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
        f.write("\n")


def print_summary(output, report):
    print(f"wrote {output}: {report['seconds']} s, {len(report['channels'])} channels, "
          f"{report['annotations_written']} annotations, {report['edf_type']}, mode {report['mode']}")
    for wmsg in report["warnings"]:
        print("warning:", wmsg)


def cmd_convert(args):
    if os.path.exists(args.output) and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 1
    report = convert_one(args, args.input, args.output)
    if args.json:
        write_json(args.json, report)
    print_summary(args.output, report)
    return 0


def find_recordings(folder):
    """Every .ezdataindex below folder, sorted."""
    return sorted(glob.glob(os.path.join(glob.escape(folder), "**", "*.ezdataindex"), recursive=True))


def cmd_batch(args):
    inputs = find_recordings(args.input)
    if not inputs:
        print(f"error: no .ezdataindex under {args.input}", file=sys.stderr)
        return 1
    os.makedirs(args.outdir, exist_ok=True)
    results, used = [], set()
    for path in inputs:
        stem = os.path.basename(path)[:-len(".ezdataindex")]
        name, n = stem, 1
        while name in used:                   # the same record exported twice: -2, -3, ...
            n += 1
            name = f"{stem}-{n}"
        used.add(name)
        output = os.path.join(args.outdir, name + ".edf")
        entry = {"input": os.path.abspath(path), "output": os.path.abspath(output)}
        try:
            if os.path.exists(output) and not args.force:
                raise FileExistsError(f"{output} exists (use --force)")
            report = convert_one(args, path, output)
            if args.reports:
                write_json(os.path.join(args.outdir, name + ".json"), report)
            print_summary(output, report)
            entry.update(status="ok", seconds=report["seconds"], edf_type=report["edf_type"],
                         warnings=report["warnings"])
        except Exception as exc:              # keep going; the summary and exit code report it
            print(f"error: {path}: {exc}", file=sys.stderr)
            entry.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        results.append(entry)
    failed = sum(r["status"] != "ok" for r in results)
    print(f"batch: {len(results) - failed} converted, {failed} failed")
    if args.json:
        write_json(args.json, {"input": os.path.abspath(args.input), "converted": len(results) - failed,
                               "failed": failed, "recordings": results})
    return 1 if failed else 0


def add_convert_options(c):
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
    c.add_argument("--gaps", choices=["auto", "pad", "discontinuous"], default="auto",
                   help="recording gaps: discontinuous = EDF+D without the gap seconds (raw mode only); pad = zeros in a "
                        "continuous EDF+C as the vendor does; auto = discontinuous in raw mode if there are gaps, else pad")
    c.add_argument("--format", choices=["auto", "edf+", "edf"], default="auto",
                   help="auto = plain EDF when nothing needs EDF+ (no annotations, no gaps left out, start on a whole "
                        "second), else EDF+; edf+ = always EDF+; edf = plain EDF (annotations dropped, start truncated)")
    c.add_argument("--allow-unsupported", action="store_true",
                   help="convert even if the Cadwell storage schema version is not a supported one (with a warning)")
    c.add_argument("--force", action="store_true", help="overwrite existing output files")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cwelleegread", description="Convert Cadwell Arc EEG (CadLink export) to EDF/EDF+.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect", help="print record, channels and events")
    i.add_argument("input"); i.add_argument("--max-events", type=int, default=40)
    c = sub.add_parser("convert", help="convert one recording to EDF/EDF+")
    c.add_argument("input", help="export folder, CadLink/Data folder or .ezdataindex file")
    c.add_argument("output", help="EDF file to write")
    add_convert_options(c)
    c.add_argument("--json", help="write a JSON conversion report here")
    b = sub.add_parser("batch", help="convert every recording (.ezdataindex) below a folder")
    b.add_argument("input", help="folder searched recursively for .ezdataindex files")
    b.add_argument("outdir", help="folder for the EDF files, named <record>-<timestamp>.edf")
    add_convert_options(b)
    b.add_argument("--reports", action="store_true", help="also write <record>-<timestamp>.json conversion reports")
    b.add_argument("--json", help="write a JSON batch summary here")
    args = ap.parse_args(argv)
    try:
        return {"inspect": cmd_inspect, "convert": cmd_convert, "batch": cmd_batch}[args.cmd](args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.DatabaseError as exc:        # corrupt or truncated SQLite file
        print(f"error: unreadable Cadwell database: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:                     # e.g. `cwelleegread inspect ... | head`
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
