# Writing events into a Cadwell recording (investigated 2026-09-29)

**Question.** Can we write a Cadwell-format EEG study with new text events
added from an external JSON file (wall-clock time + text), and verify the
result during development by re-converting it to EDF with `cwelleegread`?

**Short answer.** Yes, as far as anything outside the vendor's software can
tell. Events live in their own plain SQLite file (`.ezevents`) with no
triggers, checksums or cross-file references, and Cadwell's own review
station adds and edits rows in it long after the recording. A prototype,
`tools/cadwell_add_events.py`, copies an export and appends `Comment` rows
to the copy. Round-trip checked on the public exports
(`tests/test_add_events_prototype.py`): when every vendor comment of
export 3 is re-added from its local wall-clock time, our tick offsets are
within 0.42 ms of the vendor's own, and re-converting the copy gives an
EDF with byte-identical header and samples, all original annotations
unchanged, and each new annotation on the vendor's onset: within 0.42 ms
in raw mode (tick placement), exactly in vendor mode (stamp placement).
**Not yet known: whether Cadwell Arc itself opens the modified study and
shows the events.** That needs one test on a Cadwell workstation (below)
before anyone relies on it.

## What the files say

`<record>-<ts>.ezevents` (schema 2.5, UTF-16 SQLite, rollback journal) has
`Events`, `syncrowdata`, `synctable`, `MediaHeader`, `SchemaUpdateLog` and a
`MaxUpdateTick` view, and no triggers. Nothing else in the export names it
or holds a digest of it: the `.ezdataindex` has no reference to it, the
Data Integrity Report in export 1 lists only start/stop times and gaps,
and the catalogue databases (`Core.db`, `EEG.db`) are encrypted.

Typed-text events are `EventType` `Comment` (free text, `Priority` 3) and
`UserEvent` (preset buttons such as "Øyne lukket", `Priority` 4); both have
`Display` 7, `EventManipulation` 7, `SourceApplicationId` 0 and, unless a
montage was attached, an empty `Attributes` blob `bb797893 00000000`.
Storage classes as the vendor writes them:

| Column | Stored as | Vendor value for a comment |
|---|---|---|
| `EventID`, `UserID` | 16-byte blob, .NET `Guid` byte order (v4) | new GUID; the logged-in user |
| `Text` | text | the comment |
| `StartTime` = `EndTime` | text `YYYY-MM-DDTHH:MM:SS.fffffff`, UTC, no zone marker | the wall-clock instant |
| `StartOffset` = `EndOffset` | integer, 100-ns ticks from the record origin on the amplifier clock | see below |
| `LastModifiedBy` | text | workstation name |
| `LastUpdateTime`, `WhenEnteredTime` | text as `StartTime` | when typed (seconds after `StartTime`) |
| `Deleted` | 0/1 | deleting keeps the row with 1 |

Each event has a `syncrowdata` row (`SyncTableKey` 1, `PrimaryKey` =
`EventID`, `UpdateTick` = next value of the `MaxUpdateTick` view,
`UpdateTimeStamp` with a `Z`, `UpdateClientID`, `DeletedFlag` 0).

**Precedent for post-hoc writes.** In export 2 the comment "kødder",
typed at 11:01 on 2026-06-12, was edited on 2026-09-15 by a second client
(`UpdateClientID` `7ca5cd63…`, `LastModifiedBy` `PC199725`, `UpdateTick`
414 of 416); the same client added `ReviewedDataEvent` rows hours and
months after both recordings. So Arc itself treats `.ezevents` as a
mutable file written by more than one machine, which is exactly what the
prototype does.

## From a wall-clock time to `StartOffset`

An event's two times are one instant on two clocks (format note, "Two
clocks"). The inverse needed here, wall clock → ticks, is interpolation of
the stored frames' (`TimeStamp`, start tick) pairs, with the nominal rate
(1 s = 10⁷ ticks) before the first and after the last frame. Checked by
predicting `StartOffset` from `StartTime` for every event of the public
exports:

| Export | Events | predicted − vendor `StartOffset` |
|---|---|---|
| 2 (Essentia, 500 Hz) | 308 | median +0.425 ms, all within +0.32…+0.62 ms |
| 3 (Essentia, 500 Hz, with a 10 s gap) | 329 | median +0.421 ms, all within +0.23…+0.62 ms |
| 1 (Apollo, 250 Hz) | 14 | median +0.20 ms, max 3.6 ms (the jittery reception-time frame stamps) |

The prototype subtracts the constant 0.42 ms. Two details matter: the
vendor extrapolates events before the first frame at the *nominal* rate
(with the drift slope the impedance check 19 minutes before export 2 came
out 106 ms off, exactly 96 ppm × 1115 s), and interpolation across a gap is
correct because both clocks keep running through it.

## The prototype

```bash
.venv/bin/python tools/cadwell_add_events.py testdata/public/cadwell-export3 events.json /tmp/e3-with-events --timezone Europe/Oslo
.venv/bin/cwelleegread convert /tmp/e3-with-events out.edf --timezone Europe/Oslo
```

```json
[{"time": "2026-06-12T10:32:58.2087572+02:00", "text": "pas smiler"},
 {"time": "2026-06-12T08:33:17.51Z", "text": "stimulus B"}]
```

- ISO 8601 times; without a UTC offset they are read in `--timezone`,
  and without that they are refused (a DST ambiguity must not be guessed).
- The input export is never modified: the whole export is copied to a new
  folder and only the copy's `.ezevents` is written, in one transaction,
  followed by `PRAGMA integrity_check`.
- Events with no stored EEG under them (before the first frame, in a gap,
  after the last) are refused unless `--allow-outside`.
- Rows are marked as ours: `LastModifiedBy` `CWELLEEGREAD` and a fixed
  `UpdateClientID` (uuid5 of the repository URL). `UserID` defaults to the
  user of the latest vendor comment, because the author GUID in
  `MediaDescriptor` is not decoded yet and Arc may not show an event whose
  user it cannot resolve; `--user-id` overrides it.
- `--event-type UserEvent --priority 4` writes the preset-button kind
  instead of `Comment`.

Verifying by re-conversion works because the converter reads exactly the
columns written (`EventType`, `Text`, `StartTime`, `StartOffset`,
`Deleted`, `Priority`). Raw mode places the annotation by ticks (REQ021),
vendor mode by stamp, so the two differ by the clock drift (up to 0.35 s
per hour on Essentia) — expected, not a bug. When checking by eye:
pyedflib's `getStartdatetime()` misreads the EDF+ sub-second start
(14:37:50.027665 for a TAL of `+0.276647`); read the first TAL instead.

## What is not known, and how to find out

1. **Does Arc accept the modified study?** Import the copy of a public
   export with added events into a Cadwell workstation (CadLink import or
   opening the study) and check that the events appear at the right place,
   with the right text and user, and that the study still passes Arc's own
   checks. Try also a re-export to EDF from Arc: it should carry the new
   annotations. This is the one test that turns "structurally valid" into
   "valid". Candidate failure causes: a cached event list or count in the
   encrypted `EEG.db`; an unknown `UpdateClientID` during synchronisation;
   an unresolved `UserID`.
2. **Synchronisation.** The sync tables belong to Arc's multi-station
   replication. An export copy is not synchronised, so we should only ever
   write into export copies, never into a live Arc data store.
3. **External clock.** The JSON times must be on the acquisition PC's
   clock. An external system (stimulus PC, phone app, video) differs from
   it by its NTP error, from milliseconds to seconds. A future version
   should accept a clock offset, or align to a shared marker (for example a
   `Comment` typed at a known external instant), and report it.
4. **Clinical record integrity.** Adding events to a patient's study
   changes a medical record. The tool leaves the original untouched and
   marks its rows, but a site policy on whether modified studies may be
   re-imported into the clinical system is needed before production use.

## If we make it a product feature

Per `CLAUDE.md`, a behaviour change starts as Doorstop items. A plausible
chain, to be decided: a NEED for annotating recordings with events from
external systems; a REQ for `cwelleegread add-events <export> <json> <out>`
(copy-only, JSON schema, zone handling, refusal outside data, provenance
marking); a DES describing the row layout and the wall-clock → tick map
above; a TST that is the round-trip test in
`tests/test_add_events_prototype.py`, plus the Arc acceptance check from
point 1 as a manual verification like TST018.
