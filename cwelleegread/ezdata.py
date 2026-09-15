"""Reader for Cadwell Arc CadLink study exports (SQLite `.ezdataindex`,
`.ezdata`, `.ezevents`).

Format knowledge (reverse-engineered from testdata/public/cadwell-export1,
documented in docs/research/cadwell-file-format.md):

* ``<record>-<ts>.ezdataindex``: ``FrameInfo`` = one row per ~1 s frame
  (Offset = frame number, TimeStamp UTC, Track, FrameKey GUID, JoinDatabase
  = name of the ``.ezdata`` file holding the frame); ``TrackInfo`` = channel
  table; ``GapInfo`` = recording gaps; ``MediaHeader.MediaDescriptor`` =
  patient / record / author GUIDs.
* ``<record>-<ts>-<n>.ezdata``: ``FrameInfo(DataKey, FrameKey, Data)``; each
  ``Data`` blob is one frame::

      0x00 u32 tag 0x033149bd, u32 0, u8 1, 8-byte id, f64 1.0, u8 1,
      0x1a u32 payload length, 8 bytes const, 8-byte id (again),
      0x2e u32 channel count, u64 start ticks, u64 end ticks   (100 ns from record origin)
      0x42 channel blocks, one per channel:
           8-byte tag ab792193de4225a2, 16 x u32 record (same as TrackInfo:
           [1] channel no, [4] amplifier input no, [10] sampling rate,
           [12] f32 0.32909), 8 zero bytes, u8 1,
           u8 delta_type (1 = int16 deltas, 2 = int8 deltas),
           u32 length (= 8 + delta bytes), f32 first sample, f32 scale (1.0),
           deltas...
      25-byte footer

  Samples of a block = first + cumsum(deltas) * scale, in amplifier units.
  ``UNIT_UV`` (0.72998046 µV/unit) converts to microvolts; it was fitted
  against the vendor's text export, which pins it to [0.729980459,
  0.729980461] (every sample then agrees within the export's 0.05 µV
  rounding). It is 2.2182 x the float 0.32909 stored in the channel record;
  no closed form was found. Whether it is constant across amplifiers and
  gain settings is unknown - see the research note.
* The channel blocks are ordered by channel number; the amplifier input
  number (record field 4) gives the order used by the vendor's EDF/text
  exports, and channel *labels* are not stored in these files.
* Frames contain 250 samples nominally, but 248 (first frame) and 251
  occur; the text export keeps every sample, the EDF export resamples to
  exactly 250/s (see ``docs/research/cadwell-file-format.md``).

Only the Python standard library plus numpy is used.
"""
from __future__ import annotations

import datetime as dt
import glob
import os
import re
import sqlite3
import struct
from dataclasses import dataclass, field

import numpy as np

CHANNEL_TAG = bytes.fromhex("ab792193de4225a2")
FRAME_MAGIC = 0x033149BD
UNIT_UV = 0.72998046          # microvolts per amplifier unit (empirical, see module doc)
TICKS_PER_SECOND = 10_000_000


def _ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def parse_timestamp(s: str) -> dt.datetime:
    """'2025-10-31T13:37:50.2763068' (7 fractional digits, UTC) -> aware datetime."""
    main, _, frac = s.partition(".")
    micro = int((frac + "000000")[:6]) if frac else 0
    return dt.datetime.strptime(main, "%Y-%m-%dT%H:%M:%S").replace(microsecond=micro, tzinfo=dt.timezone.utc)


@dataclass
class ChannelRecord:
    channel: int          # 1-based channel number (block order in a frame)
    amp_input: int        # amplifier input number (export column order)
    sample_rate: int
    scale_f32: float
    raw: tuple


@dataclass
class Frame:
    number: int
    timestamp: dt.datetime
    start_ticks: int
    end_ticks: int
    samples: dict = field(default_factory=dict)   # amp_input -> np.ndarray (units)


@dataclass
class Event:
    type: str
    text: str
    start: dt.datetime
    end: dt.datetime
    start_ticks: int
    end_ticks: int
    deleted: bool


def parse_channel_record(buf: bytes, pos: int) -> ChannelRecord:
    u = struct.unpack_from("<16I", buf, pos + 8)
    return ChannelRecord(channel=u[1], amp_input=u[4], sample_rate=u[10],
                         scale_f32=struct.unpack_from("<f", buf, pos + 8 + 48)[0], raw=u)


def parse_track_info(blob: bytes) -> list[ChannelRecord]:
    return [parse_channel_record(blob, m.start()) for m in re.finditer(re.escape(CHANNEL_TAG), blob)]


def decode_frame(blob: bytes) -> tuple[int, int, dict[int, np.ndarray], list[ChannelRecord]]:
    """Return (start_ticks, end_ticks, {amp_input: samples in units}, channel records)."""
    magic = struct.unpack_from("<I", blob, 0)[0]
    if magic != FRAME_MAGIC:
        raise ValueError(f"unexpected frame magic 0x{magic:08x}")
    nch = struct.unpack_from("<I", blob, 0x2E)[0]
    start_ticks, end_ticks = struct.unpack_from("<QQ", blob, 0x32)
    positions = [m.start() for m in re.finditer(re.escape(CHANNEL_TAG), blob)]
    if len(positions) != nch:
        raise ValueError(f"frame says {nch} channels but has {len(positions)} channel blocks")
    samples, records = {}, []
    for p in positions:
        rec = parse_channel_record(blob, p)
        records.append(rec)
        delta_type = blob[p + 81]
        length = struct.unpack_from("<I", blob, p + 82)[0]
        first, scale = struct.unpack_from("<ff", blob, p + 86)
        payload = blob[p + 94:p + 94 + length - 8]
        if delta_type == 1:
            deltas = np.frombuffer(payload, dtype="<i2")
        elif delta_type == 2:
            deltas = np.frombuffer(payload, dtype="<i1")
        else:
            raise ValueError(f"unknown delta type {delta_type} for channel {rec.channel}")
        x = np.empty(len(deltas) + 1, dtype=np.float64)
        x[0] = first
        x[1:] = first + np.cumsum(deltas.astype(np.int64)) * scale
        samples[rec.amp_input] = x
    return start_ticks, end_ticks, samples, records


class CadwellRecording:
    """One record of a CadLink export (one `.ezdataindex` and its data files)."""

    def __init__(self, index_path: str):
        self.index_path = index_path
        self.data_dir = os.path.dirname(index_path)
        with _ro(index_path) as con:
            self.schema_versions = [f"{o}->{n}" for o, n in con.execute(
                "select OldVersion, NewVersion from SchemaUpdateLog order by TimeStamp")]
            row = con.execute("select Value from MediaHeader where Key='MediaDescriptor'").fetchone()
            self.patient_guid = self.record_guid = self.author_guid = None
            if row:
                b, pos, guids = row[0], 8, []
                for _ in range(3):
                    n = struct.unpack_from("<I", b, pos)[0]
                    guids.append(b[pos + 4:pos + 4 + n].decode("ascii", "replace"))
                    pos += 4 + n
                self.patient_guid, self.record_guid, self.author_guid = guids
            ti = con.execute("select Data from TrackInfo where Track=0 order by Offset limit 1").fetchone()
            self.channels: list[ChannelRecord] = parse_track_info(ti[0]) if ti and ti[0] else []
            self.frame_index = [dict(number=off, timestamp=parse_timestamp(ts), track=tr, status=st,
                                     join_db=jd, key=key)
                                for off, ts, tr, st, jd, key in con.execute(
                                    "select Offset, TimeStamp, Track, Status, JoinDatabase, hex(FrameKey) "
                                    "from FrameInfo where Track=0 order by Offset")]
            self.gaps = [dict(track=t, start_offset=so, end_offset=eo, start=parse_timestamp(s), end=parse_timestamp(e))
                         for t, so, eo, s, e in con.execute(
                             "select Track, StartOffset, EndOffset, StartTime, EndTime from GapInfo")]
        self.sample_rate = self.channels[0].sample_rate if self.channels else None
        self.origin = self.frame_index[0]["timestamp"] if self.frame_index else None
        # export column order = amplifier input order
        self.amp_inputs = sorted(c.amp_input for c in self.channels)

    # ------------------------------------------------------------------ events
    def events(self) -> list[Event]:
        stem = re.sub(r"\.ezdataindex$", "", self.index_path)
        path = stem + ".ezevents"
        if not os.path.exists(path):
            return []
        with _ro(path) as con:
            return [Event(t, x, parse_timestamp(s), parse_timestamp(e), so, eo, bool(d))
                    for t, x, s, e, so, eo, d in con.execute(
                        "select EventType, Text, StartTime, EndTime, StartOffset, EndOffset, Deleted "
                        "from Events order by StartTime")]

    # ------------------------------------------------------------------ frames
    def frames(self):
        """Yield Frame objects in order, decoding every data file the index names."""
        by_db: dict[str, list] = {}
        for fi in self.frame_index:
            by_db.setdefault(fi["join_db"], []).append(fi)
        blobs: dict[str, bytes] = {}
        for db in by_db:
            path = os.path.join(self.data_dir, db)
            if not os.path.exists(path):
                raise FileNotFoundError(f"frame data file missing: {path}")
            with _ro(path) as con:
                for key, data in con.execute("select hex(FrameKey), Data from FrameInfo"):
                    blobs[key] = data
        for fi in self.frame_index:
            blob = blobs.get(fi["key"])
            if blob is None:
                raise KeyError(f"frame {fi['number']} ({fi['key']}) not found in {fi['join_db']}")
            start_ticks, end_ticks, samples, _ = decode_frame(blob)
            yield Frame(fi["number"], fi["timestamp"], start_ticks, end_ticks, samples)

    def read_signals(self, unit_uv: float = UNIT_UV) -> tuple[np.ndarray, list[int], list[int]]:
        """All frames concatenated -> (samples[n, channels] in µV, amp_input order, samples per frame)."""
        cols = {a: [] for a in self.amp_inputs}
        per_frame = []
        for fr in self.frames():
            n = None
            for a in self.amp_inputs:
                x = fr.samples[a]
                cols[a].append(x)
                n = len(x) if n is None else n
            per_frame.append(n)
        data = np.column_stack([np.concatenate(cols[a]) for a in self.amp_inputs]) * unit_uv
        return data, self.amp_inputs, per_frame


def open_recording(path: str) -> CadwellRecording:
    """Accept an export folder, a CadLink/Data folder or an .ezdataindex file."""
    if os.path.isfile(path):
        return CadwellRecording(path)
    for cand in (path, os.path.join(path, "native-export", "CadLink", "Data"),
                 os.path.join(path, "CadLink", "Data"), os.path.join(path, "Data")):
        hits = sorted(glob.glob(os.path.join(cand, "*.ezdataindex")))
        if hits:
            if len(hits) > 1:
                raise ValueError(f"{cand} holds {len(hits)} records; pass the .ezdataindex file")
            return CadwellRecording(hits[0])
    raise FileNotFoundError(f"no .ezdataindex under {path}")
