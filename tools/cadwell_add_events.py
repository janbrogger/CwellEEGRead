#!/usr/bin/env python3
"""Research prototype: copy a CadLink study export and add text events to the
copy's ``.ezevents`` database from a JSON file of wall-clock times.

    python tools/cadwell_add_events.py <export> <events.json> <out-export> [--timezone Europe/Oslo]

``events.json`` is a list (or ``{"events": [...]}``) of objects::

    {"time": "2026-06-12T10:32:58.2087572+02:00", "text": "pas smiler"}

``time`` is ISO 8601; without a UTC offset it is read in ``--timezone``.
The input export is never modified: the whole export is copied to
``<out-export>`` (which must not exist) and only the copy's ``.ezevents``
is written, in one transaction. Verify by converting the copy with
``cwelleegread convert``. Findings and open questions:
``docs/research/writing-events.md``.

How a row is built (all taken from the vendor's own ``Comment`` rows in
testdata/public/cadwell-export2 and -3, schema 2.5):

* ``StartTime`` = the wall-clock instant in UTC, no zone marker, 7 fraction
  digits (the acquisition PC clock the frame ``TimeStamp`` values use).
* ``StartOffset`` = amplifier ticks (100 ns) from the record origin, found
  by interpolating the stored frames' (``TimeStamp``, start tick) pairs;
  before the first and after the last frame at the nominal rate. This
  reproduces the vendor's own offsets to within 0.62 ms on every event of
  exports 2 and 3 (median 0.42 ms, which is subtracted).
* ``EventType`` ``Comment``, ``Priority`` 3, ``Display`` 7,
  ``EventManipulation`` 7, empty ``Attributes`` (tag ``0x937879bb``, count 0),
  plus a ``syncrowdata`` row with the next ``UpdateTick`` - as the vendor's
  review station does when it edits an event after the recording.
  ``LastModifiedBy`` = ``CWELLEEGREAD`` and ``UpdateClientID`` = a fixed
  GUID of this tool mark the added rows.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import json
import os
import shutil
import sqlite3
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from cwelleegread.ezdata import open_recording  # noqa: E402

TICKS_PER_SECOND = 10_000_000
EMPTY_ATTRIBUTES = bytes.fromhex("bb79789300000000")
# median (vendor stamp -> interpolated ticks) - vendor StartOffset on exports 2 and 3
STAMP_TICK_LAG = 4_230      # 0.423 ms in ticks
# Events.LastModifiedBy (the vendor writes the workstation name there): marks rows added by this tool
MODIFIED_BY = "CWELLEEGREAD"
# fixed client id of this tool in syncrowdata.UpdateClientID (uuid5 of the repo name)
CLIENT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/janbrogger/CwellEEGRead")


def dotnet_timestamp(t: dt.datetime) -> str:
    """UTC datetime -> '2026-06-12T08:32:58.2087572' (the column format; 100-ns digits)."""
    t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0"


def parse_time(s: str, tz: str | None) -> dt.datetime:
    """ISO 8601 with up to 7 fraction digits -> aware UTC datetime (100-ns digit dropped)."""
    head, _, frac = s.partition(".")
    zone = ""
    if frac:
        i = next((k for k, ch in enumerate(frac) if not ch.isdigit()), len(frac))
        frac, zone = frac[:i], frac[i:]
        s = f"{head}.{frac[:6].ljust(6, '0')}{zone}"
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        if not tz:
            raise ValueError(f"time {s!r} has no UTC offset; pass --timezone")
        from zoneinfo import ZoneInfo
        t = t.replace(tzinfo=ZoneInfo(tz))
    return t.astimezone(dt.timezone.utc)


class ClockMap:
    """Wall clock (frame TimeStamp axis, UTC) -> amplifier ticks from the record origin."""

    def __init__(self, rec):
        pairs = [(fr.timestamp, fr.start_ticks, fr.end_ticks) for fr in rec.frames()]
        self.origin = rec.origin
        self.stamps = [(p[0] - rec.origin).total_seconds() for p in pairs]
        self.ticks = [p[1] for p in pairs]
        self.first_tick, self.last_tick = pairs[0][1], pairs[-1][2]
        # stored data spans, for "is there EEG under this event"
        self.spans = [(p[1], p[2]) for p in pairs]

    def ticks_at(self, t: dt.datetime) -> int:
        s = (t - self.origin).total_seconds()
        st, tk = self.stamps, self.ticks
        if s <= st[0]:
            x = tk[0] + (s - st[0]) * TICKS_PER_SECOND
        elif s >= st[-1]:
            x = tk[-1] + (s - st[-1]) * TICKS_PER_SECOND
        else:
            k = bisect.bisect_right(st, s) - 1
            x = tk[k] + (s - st[k]) / (st[k + 1] - st[k]) * (tk[k + 1] - tk[k])
        return round(x) - STAMP_TICK_LAG

    def has_data(self, ticks: int) -> bool:
        k = bisect.bisect_right([a for a, _ in self.spans], ticks) - 1
        return k >= 0 and ticks < self.spans[k][1]


def load_events(path: str, tz: str | None) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    items = obj["events"] if isinstance(obj, dict) else obj
    out = []
    for i, e in enumerate(items):
        text = str(e["text"]).strip()
        if not text:
            raise ValueError(f"event {i}: empty text")
        out.append({"time": parse_time(e["time"], tz), "text": text, "source": e["time"]})
    return out


def add_events(export: str, events_json: str, out: str, *, timezone: str | None = None,
               event_type: str = "Comment", priority: int = 3, user_id: str | None = None,
               allow_outside: bool = False, now: dt.datetime | None = None) -> dict:
    if os.path.exists(out):
        raise FileExistsError(f"{out} exists; the output must be a new folder")
    rec = open_recording(export)
    rec.check_supported()
    events = load_events(events_json, timezone)
    cmap = ClockMap(rec)
    rows, report = [], []
    for e in events:
        ticks = cmap.ticks_at(e["time"])
        inside = cmap.has_data(ticks)
        report.append({"text": e["text"], "time": e["source"], "start_offset": ticks,
                       "seconds_from_origin": ticks / TICKS_PER_SECOND, "over_stored_data": inside})
        if not inside and not allow_outside:
            raise ValueError(f"{e['source']} {e['text']!r}: no stored EEG at that instant "
                             f"({ticks / TICKS_PER_SECOND:.3f} s from origin); use --allow-outside")
        rows.append((e, ticks))

    shutil.copytree(export, out)
    rec_out = open_recording(out)
    path = rec_out.index_path[: -len(".ezdataindex")] + ".ezevents"
    now = (now or dt.datetime.now(dt.timezone.utc))
    stamp = dotnet_timestamp(now)
    con = sqlite3.connect(path, isolation_level=None)
    try:
        con.execute("begin immediate")
        if user_id:
            uid = uuid.UUID(user_id).bytes_le
        else:   # the recording's author (MediaDescriptor AuthorId) is not decoded yet: reuse the
                # user of the latest vendor Comment/UserEvent, else of any event
            r = con.execute("select UserID from Events where EventType in ('Comment','UserEvent') "
                            "order by LastUpdateTime desc limit 1").fetchone() or \
                con.execute("select UserID from Events order by LastUpdateTime desc limit 1").fetchone()
            uid = r[0]
        tick = con.execute("select UpdateTick from MaxUpdateTick").fetchone()[0] or 0
        for (e, ticks), rep in zip(rows, report):
            eid = uuid.uuid4().bytes_le            # .NET Guid byte order, as the vendor's EventIDs
            t = dotnet_timestamp(e["time"])
            con.execute(
                "insert into Events (EventID, EventType, UserID, Text, StartTime, EndTime, StartOffset, "
                "EndOffset, LastModifiedBy, Attributes, LastUpdateTime, Priority, Display, "
                "EventManipulation, Deleted, SourceApplicationId, WhenEnteredTime) "
                "values (?,?,?,?,?,?,?,?,?,?,?,?,7,7,0,0,?)",
                (eid, event_type, uid, e["text"], t, t, ticks, ticks, MODIFIED_BY, EMPTY_ATTRIBUTES,
                 stamp, priority, stamp))
            tick += 1
            con.execute("insert into syncrowdata (SyncTableKey, PrimaryKey, UpdateTick, UpdateTimeStamp, "
                        "UpdateClientID, DeletedFlag) values (1,?,?,?,?,0)",
                        (eid, tick, stamp + "Z", CLIENT_ID.bytes_le))
            rep["event_id"] = str(uuid.UUID(bytes_le=eid))
        con.execute("commit")
        ok = con.execute("pragma integrity_check").fetchone()[0]
    except BaseException:
        con.execute("rollback") if con.in_transaction else None
        raise
    finally:
        con.close()
    return {"input": os.path.abspath(export), "output": os.path.abspath(out), "ezevents": path,
            "integrity_check": ok, "events": report}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("export")
    ap.add_argument("events_json")
    ap.add_argument("out")
    ap.add_argument("--timezone", help="IANA zone for times without a UTC offset, e.g. Europe/Oslo")
    ap.add_argument("--event-type", default="Comment", help="Events.EventType (default Comment)")
    ap.add_argument("--priority", type=int, default=3, help="Events.Priority (Comment 3, UserEvent 4)")
    ap.add_argument("--user-id", help="GUID for Events.UserID (default: user of the latest vendor comment)")
    ap.add_argument("--allow-outside", action="store_true", help="accept events with no stored EEG under them")
    a = ap.parse_args(argv)
    rep = add_events(a.export, a.events_json, a.out, timezone=a.timezone, event_type=a.event_type,
                     priority=a.priority, user_id=a.user_id, allow_outside=a.allow_outside)
    json.dump(rep, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
