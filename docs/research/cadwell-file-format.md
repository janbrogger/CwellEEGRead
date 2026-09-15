> Research note produced 2026-09-15 by an LLM research agent (Claude Code, session `adede7d2-9fc1-585c-a838-bea822978308`, see `llm-logs/`) from public sources reachable at the time. Claims are tagged as verified from primary sources or as search-engine snippets/inference where the source could not be opened. Treat as a starting point, not as ground truth; the transcript records exactly what was fetched.

# Cadwell (Arc / Easy III) EEG file formats — public-knowledge survey

Date: 2026-09-15. Research agent report for the CwellEEGRead project (Jan Brogger).

## 0. Access caveats (read first)

The egress proxy blocked every host that carries primary documentation: `*.mathworks.com` (all locales, incl. `ww2.mathworks.cn`), `web.archive.org`, `archive.ph`, `r.jina.ai`, `researchgate.net`, `cadwell.com`, `cadwell.support`, `cdn.shopify.com` (Easy III manual PDF), `persyst.com`, `wiki.besa.de`/`besa.de`, `scribd.com`, `manualslib.com`, `neuroimage.usc.edu` (Brainstorm forum), `mne.discourse.group`, `oit.va.gov`, `patents.justia.com`, `accessdata.fda.gov`, `packages.debian.org`, `youtube.com`.

Consequently:

- **The MathWorks thread (section 1) is reconstructed from search-engine snippets only** (several differently-phrased queries, each returning verbatim fragments). Attribution of individual sentences to individual posters is partly inferred and is marked as such. The user (Jan) should verify against the live page.
- Everything in sections 2–3 that *was* read in full comes from: the BioSig source tree (SourceForge git raw + GitHub mirror `EEGKit/BioSig-sf`), the SourceForge BioSig feature request #13, and a public GitHub repo containing a text dump of Cadwell's own **Arc API documentation** plus PowerShell scripts that call it (`aminjalali-research/MRI-DICOM-EEG-EMU`). Local copies are in the scratchpad (`biosig/`, `arcapi/`).

Legend used below: **[V]** verified from a primary source read in full; **[S]** from a search snippet (verbatim fragment but context lost); **[I]** my inference; **[?]** speculation.

---

## 1. The MathWorks thread — "Reading Clinical EEG (.ezdata) file IN MATLAB"

URL: https://www.mathworks.com/matlabcentral/answers/480265-reading-clinical-eeg-ezdata-file-in-matlab (mirrors: `se.`, `uk.`, `de.`, `jp.`, `la.` sub-domains, `ww2.mathworks.cn` — all blocked here). Asked September 2019 [S].

**Question [S]:** the asker records clinical EEG on a **Cadwell Arc Essentia** and gets `.ezdata` files; wants to read them in MATLAB. They note "ezdata appears to be a file created by Cadwell EEG Machines (along with .eas and .ez3)" and that, on inspection, "it is in SQLite format 3, which appears to be a database file". (The .eas/.ez3 remark is a generic statement about Cadwell; .eas and .ez3 are *not* SQLite — see §2.2.)

**Answers/comments [S]** (poster attribution partly inferred):

1. A MathWorks-staff/community answer: "If you have access to the Database Toolbox, you can use `sqlread` to load the data." Generic advice; nothing format-specific.
2. **Jan Brogger's contribution** (identified in the snippet as "the author of a FieldTrip/EEGLAB plugin that reads Nicolet EEG files", who "has the same problem of working with Cadwell Arc .ezdata files and might work on an EEGLAB plugin for Cadwell Arc .ezdata files"). Concrete findings attributed to this contribution:
   - "The .ezdata file can be parsed as a SQLite database, and the EEG data are (likely) in the **FrameInfo** table."
   - Test file: "a test EEG file which is 1199 seconds long (19 min 59 s), about 20 channels at 500 Hz — the FrameInfo table contains **1199 rows**", i.e. **one FrameInfo row per second of recording**.
   - Table/column names quoted in the thread: **`FrameInfo (DataKey, FrameKey, Data)`**, **`MediaHeader (Key, Value)`**, **`TrackInfo (Offset, Track, Data)`**. "The EEG data are stored in the FrameInfo table."
   - "Information about EEG channels is in the **TrackInfo** table as a binary large object (blob)."
   - "Extraction of raw EEG data from Cadwell Arc .ezdata format seems possible, but needs more work." (No decoding of the blob was reported in the thread.)
   - Another snippet from the same thread: "**Data can be exported in EDF format from Arc viewer**" — i.e. someone (asker or Jan) pointed out the native EDF export as the pragmatic route.
3. No later comment in the snippets reports a working decoder, the blob layout, sample encoding (int16/float), compression, or the meaning of `DataKey`/`FrameKey`. **Nothing about compression or scaling was found in the thread [S].**

Bottom line from the thread: SQLite container confirmed; three tables named with their columns; 1 frame-row per second; channel metadata in a TrackInfo blob; raw sample encoding **not** resolved publicly.

---

## 2. Everything else publicly known about the layout

### 2.1 File extensions and what they are

| Extension | Product / generation | Nature | Source |
|---|---|---|---|
| `.eas` | Cadwell **EasyWindows / Easy II** (1990s–2000s) | Proprietary binary; header starts `SctHdr\0\0Directory…` with section table ("EEGData" section etc.) | BioSig `biosig.c` type detection + `sopen_cadwell_read.c` [V]; Persyst list "Cadwell EasyWindows `*.eas`" [S] |
| `.ez3` (typically `*-1.ez3`) | **Easy III** (c. 2008–2019) | Proprietary binary; magic string `Easy3File`; block-structured (EasyDCWYAAA sub-blocks, `EEG001`/`EVENT001` blocks) | BioSig [V]; Persyst "`*-1.ez3`" [S]; Easy III manual lists `.ez3` = Easy III data file, `.qv2`/`.ezvideo`/`.ezvideoindex` = video, `.mdh` = archive history [S] |
| `.arc` (also legacy `.flex`) | **Arc** (2016→) | The "external Arc file" that Cadwell's own API opens with `IArcApi.GetRecord(string externalArcFilePath)`; "`.arc` (or `.flex`)" | Arc API docs [V]; Persyst "Cadwell Arc `*.arc`" [S]; Pennsieve `persyst-deidentify` maps `arc`→Cadwell, `ez3`→Cadwell [V] |
| `.ezdata` | **Arc** (Essentia/Apollo/Zenith) | **SQLite 3 database** holding the media container (waveform + video/audio "tracks" as per-second "frames") | MathWorks thread [S]; BioSig `sopen_sqlite.c` table list [V] |
| `.export` | Arc "record export" | A manifest file "usually located in the root folder created by a record export operation", consumed by `IArcApi.ImportRecords(exportFilePath)` (API ≥ 3.2) | Arc API docs [V] |
| `.ezvideo`, `.ezvideoindex`, `.qv2` | Easy III (and probably Arc) video | video containers/indices | Easy III manual snippet [S]; Arc: video is exposed via API as MP4 export; whether Arc stores video in the same SQLite (tracks) or separate `.ezvideo` files is **unknown** [?] |
| `.ezdata3` | — | **No public evidence at all** (no web hits, no GitHub hits). If it exists it is probably a newer schema generation of `.ezdata` [?] |

**Inference on the study layout [I]:** an Arc study is a folder (or DB record in CadLink's MS-SQL back end) with at least an `.arc` record file plus one or more `.ezdata` SQLite media files; an *exported* study adds an `.export` manifest at the root. Persyst and BESA both open Arc data only through Cadwell's own DLLs ("Cadwell Arc EEG Support Files" for Persyst; "the Cadwell reader requires the Cadwell Arc API installed in the default path on C:" for BESA [S]) — i.e. **no third party has published an independent parser**.

**Confirmed generic facts about Arc storage rates [S]:** Arc Essentia E1 stores at 250/500 Hz; E2 adds 1000/2000 Hz; E3A 1000/2000 Hz; Zenith up to 288 ch. ADC bit depth not found publicly.

### 2.2 The legacy binary formats (for completeness; not SQLite)

BioSig's `sopen_cadwell_read.c` (Alois Schlögl, 2021, GPL) is a reverse-engineering scratchpad, **not** a working reader — every branch ends in `biosigERROR(... "unsupported")` [V]. What it records:

- **EAS**: assumed 16 channels, 250 Hz (comment also says "12 bit ADC? 200 Hz"), header length fields at 0x30/0x34, section directory entries every 0x20 bytes from 0x6c with `SctHdr` blocks chained via 64-bit `curSec/nextSec`; EEGData appears big-endian int16 with 404-byte periodicity.
- **EZ3**: `Easy3File` magic, version string at +21, start date/time as text at 0x5c, directory of 0x30-byte entries, `EasyDCWYAAA` block headers, `EEG001` blocks containing little-endian int16 in sub-blocks of ~308 samples (250 real samples + padding?), `EVENT001` blocks. Nothing on scaling.
- **ARC**: only a stub.

BioSig detects SQLite by the 16-byte header `"SQLite format 3\0"` and then (in `sopen_sqlite.c`) checks for the Cadwell table set — but then returns "Format SQLite: not supported yet" [V]. So **BioSig cannot read .ezdata**; SourceForge feature request #13 (2021-08-27, still open) confirms "Cadwell does not provide the specification". Schlögl estimated (on ResearchGate) "2 weeks to 2 months full-time" to build a basic decoder [S]. He asked for sample `.eas/.ez3/.ezdata` files via a Seafile link; a user uploaded some into an "eas-cadwell-example-files" folder [S].

### 2.3 The `.ezdata` SQLite schema (what is actually known)

**Table set [V]** (BioSig `sopen_sqlite.c` — "Cadwell has these tables"; it uses presence of all 11 as the signature):

```
FrameInfo, MiscInfo, TrackInfoSyncRowData, MaxUpdateTick, MiscInfoSyncRowData,
syncrowdata, MediaHeader, SchemaUpdateLog, synctable, MediaHeaderSyncRowData, TrackInfo
```

**Columns [S]** (MathWorks thread): `FrameInfo(DataKey, FrameKey, Data)`, `MediaHeader(Key, Value)`, `TrackInfo(Offset, Track, Data)`. Columns of `MiscInfo` and the sync tables were not published.

**Interpretation [I], strongly supported by the Arc API object model [V]:**

- Cadwell's runtime namespace is `Cadwell.Core.Media.Domain` (`IMediaFrame` appears in the API docs); the API exposes *media channels* with `VideoTrackNumber`/`AudioTrackNumber`, *frames* with UTC `Time`, and an `EncodingType` enum that mixes video/audio codecs (H264, MJPEG, AAC, PCM …) with two waveform codings: **`WaveformNoCompression`** and **`WaveformNonlinearDeltaCompression`**. So `.ezdata` is a generic **media container**: `MediaHeader` = key/value header, `TrackInfo` = one row per track (EEG waveform track(s), video track(s), audio track(s)) with a blob describing the track (for EEG: channel list, sample period, filters…), `FrameInfo` = one blob per (track, 1-second frame). `DataKey` is probably the track id and `FrameKey` the frame index/time [I].
- The API's `IRecordData.RecordingDuration` doc says "from the start to the last recorded **frame**" and `RecordingStartTime` is "the UTC time of the first **chunk**" [V] — consistent with per-second frames.
- Hence the waveform blob for a 1-s frame of the 500 Hz/20-ch test file should hold 500×20 samples: 20 000 B if int16 uncompressed, 40 000 B if float32, and *smaller and variable* if `WaveformNonlinearDeltaCompression` is in use. **Which encoding Arc actually writes to disk is unknown [?]**; the presence of the delta-compression enum in Cadwell's public API strongly suggests compressed frames should be expected. "Nonlinear delta" most plausibly means variable-length (e.g. small-delta-in-1-byte, escape to 2/4 bytes) differences between consecutive samples, per channel [?]. Row-size statistics from `FrameInfo` (constant vs. varying `length(Data)`) will settle this immediately.
- The API returns samples as **`float[] Data`** per channel per contiguous segment, with per-segment `HighCutFilter`/`LowCutFilter`/`NotchFilter` ("applied to the data channel by hardware; 0 = none"), `SamplePeriod` (an `ITimeInterval` measured in 100-ns **ticks**), `StartOffset/EndOffset`, and UTC `StartTime/EndTime` [V]. Trace display sensitivity is documented in **µV/mm**, so the float samples are almost certainly in **µV** [I]. Whether the on-disk blob is float32 or a scaled integer plus a per-track gain in `TrackInfo` is unknown [?].
- **Gaps**: the API models "discontinuous waveform data" with `GetTimeSegments()` (contiguous blocks) and `Duration` "excludes gaps" vs `RecordingDuration` "does NOT exclude gaps" [V]. Expect missing `FrameKey`s (or empty frames) in `FrameInfo` for paused recordings [I].
- **Sync tables** (`synctable`, `syncrowdata`, `*SyncRowData`, `MaxUpdateTick`, `SchemaUpdateLog`): these names match no public framework (searched Microsoft Sync Framework, Dotmim.Sync, Ampli-Sync, SQLite-Sync); they are most likely Cadwell's own change-tracking for CadLink/remote-review replication and schema migrations [I]. They are irrelevant for decoding but `SchemaUpdateLog` will reveal the schema version — useful for handling `.ezdata` variants across Arc 2.x → 3.x → 4.x.

### 2.4 Events / annotations, montages, impedances, patient data

From the Arc API docs [V] — these entities exist in the record; **where they live on disk (the `.arc` file vs. `.ezdata` `MiscInfo` vs. the CadLink SQL Server DB) is not public [?]**:

- **Events**: `EventID (Guid)`, `EventType (string)`, `Offset`, `Duration`, `Text`, `Priority (-1, 0..4)`, `UserID`, `TraceContainerID`, `IsCreatedByApi`. Default event types: `AmpErrorEvent, AmpLeakageAlarmEvent, AmpSaturation, AmpTemperatureAlarmEvent, AmpTimeSyncErrorEvent, CorticalStimStart/Stop/Suppress, DeviceConnection, LowBatteryEvent, PhoticStimEvent, BaselineImpedanceEvent, CalibrationEvent, UserClipEvent, HyperventilationEvent, IncrementalHyperventilationEvent, ImpedanceEvent, ContinuousImpedanceEvent, LiveReviewCommand, MontageEvent, PaperSpeedEvent, RecordingOnOff, RoomAutoInfo, SnapshotEvent, AutoRestart, SwitchCamera, SwitchUser, TimerEvent, VoiceEvent, TimeRangeSeizureEvent, SpikeEvent, PatientEvent, EventButton, EventAcknowledgedEvent, Annotation, Comment, UserEvent, Persyst Comment, Persyst RhythmicBurst, Persyst SeizureDetected, Persyst Spike, Persyst SpikeBurst`. Annotations have a minimum enforced duration of 1 s.
- **Montages/reference**: `IMontage` (name, `AsViewed` offset, trace containers), `ITrace` (`Active`, `Reference`, `Sensitivity` µV/mm, `Locut`, `Hicut`), `IAverageReferenceInfo` (input name + weight), `ICommonReference` (channel name + offset when applied). So the recording reference can change mid-record and is logged.
- **Impedances**: `IImpedance` (offset, low/high boundary Ω, items with `Channel`, `Ohms`, `KiloOhms`, `IsConnected`).
- **Patient/record fields (PHI)**: `IRecord.Patient.Fields` with default keys `FirstName, LastName, MiddleName, PatientId, OtherId, Birthdate, Age`; record fields `Physician, ReferringPhysician, Comments, History, Medications`; plus `DateRecorded`, `DataAcquisitionMachine`, `StudyType`, `StudyStatus`, `RecordingTimeZoneOffset`. **Expect PHI in `MediaHeader`/`MiscInfo` text or blobs and in the `.arc` file; treat every `.ezdata` as PHI-bearing** [I].
- **Video/audio**: tracks in the same media model; API exports MP4 (`ExportMp4Video`, options Full/Shrink/Split) and returns raw frames.

### 2.5 Other public hits (all dead ends, listed so you don't repeat them)

- `vtciald/ezdata` on GitHub is a survey-data library, unrelated [V]. `epidemicz/EZData`, `mfouesneau/ezdata`, `xuwei95/ezdata`, M5Stack "EzData" are unrelated.
- No GitHub code search hits for `ezdata3`, `Easy3File`, `EasyDCWYAAA`, `syncrowdata`, `MaxUpdateTick`, or a Cadwell SQLite reader; only BioSig and the Arc-API repo above.
- Brainstorm forum requests (May 2021 "EZ3 cadwell file import", July 2023 "EEG files unsupported") and MNE forum "Need help with .EAS file" exist but (per snippets) contain no format details [S].
- EDFbrowser has no Cadwell converter [S]. MNE-Python, Neo and pyedflib have no Cadwell reader (no hits).

---

## 3. What Cadwell's native software can export (ground truth for equivalence tests)

**Verified from the Arc API docs [V]:**

- `IRecordData.ExportToEdf(edfFilePath)` — "Export this record to an EDF file"; and `ExportToEdf(path, startOffset, endOffset)` for a time range (seconds; ≤0 = start/end). This is the same engine the Arc GUI uses (inference [I]). The doc says **EDF**, not EDF+; whether events go into an `EDF Annotations` signal is not stated [?]. In the third-party PowerShell pipeline, events, impedances and metadata were exported **separately to CSV/JSON**, which hints the EDF may not carry annotations [I].
- `GetDiscontinuousWaveformData` / `GetWaveformData` give per-channel `float[]` with per-segment hardware filter values → a programmatic "CSV export" is possible via the API (the public script writes `Time,Ch1,Ch2,…`). Arc GUI "ASCII/CSV export" was **not** documented in anything reachable [?].
- Video: MP4 export; documents: `IAssociatedDocument.Export`.
- Study export/import: Arc "Export" produces a folder with an `.export` manifest reviewable in **Arc Viewer** (Arc 2.2 release notes mention faster export/archive preparation; YouTube "Arc Viewer: Reviewing an Exported Study – Arc 2.2") [S].
- Easy III: the Operator's Manual (Part No. 100840-620, v3.16, Dec 2014) exists as PDF but was unreachable; PSG variant mentions MPEG-4 "Q-Video". Easy III records can be imported into Arc 3.x ("import Cadwell Easy III EEG records for review") — so Easy III `.ez3` data can be re-exported to EDF via Arc [S].

**Known/likely quirks to test (none confirmed publicly — all [I]/[?]):**

1. **Gaps**: EDF is continuous; Arc must either concatenate segments (dropping gaps, changing timing) or pad. Compare `GetTimeSegments()`-style gap positions inferred from `FrameKey`s against the EDF duration.
2. **Hardware filters**: samples in `.ezdata` are post-hardware-filter (the API reports the filter values but the data are what was stored); EDF prefilter field may or may not be populated. Display filters (`Locut`/`Hicut` of traces) should *not* be applied on export, but verify.
3. **Reference**: Arc stores referential channels against a common reference that can change mid-record (`ICommonReference` with offsets). EDF export is probably referential with the recording reference; channel labels may be plain (`Fp1`) or `Fp1-Ref`. Check whether a mid-record reference switch is reflected.
4. **Scaling / quantisation**: if the on-disk blob is float32 (µV) and EDF is 16-bit with physical min/max chosen per export, expect quantisation error ≈ (phys range / 65536); equivalence tests should use a tolerance, not exact equality. If the blob is int16 with a gain, exact equality against EDF digital values is possible.
5. **Sample-rate mixing**: Arc can store non-EEG channels (SpO2, DC, video-sync) at other rates; EDF export may resample or drop them.
6. **Start time / time zone**: `RecordingStartTime` is UTC; `RecordingTimeZoneOffset` is stored separately. EDF start date/time is local — check which one the export writes (and 2-digit-year clipping for the 1985/2084 EDF rule).
7. **Event export**: if EDF+ is produced, check whether Persyst-generated events and amplifier events (`AmpSaturation`, `ImpedanceEvent`…) are included, and whether the 1-s minimum annotation duration is applied.
8. **Channel set**: EDF export may follow a montage/"as recorded" set and may exclude unused amplifier inputs; the `.ezdata` `TrackInfo` will list all acquired inputs.

---

## 4. Recommended approach for a Python reader, and open unknowns

### 4.1 Reader skeleton (stdlib only, no test file needed to start)

1. **Identify**: check `b"SQLite format 3\x00"` at offset 0; open with `sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)` (immutable avoids WAL/journal writes on read-only media). Confirm the 11-table signature; store `SchemaUpdateLog` rows as the schema version.
2. **Header**: `SELECT Key, Value FROM MediaHeader` → dict. Expect strings/ints/GUIDs; may include PHI (patient name/ID), start time (UTC + tz offset), acquisition machine, software version. Log the keys verbatim in the test fixtures.
3. **Tracks**: `SELECT Offset, Track, Data FROM TrackInfo ORDER BY Track, Offset`. Decode `Data` blob: first look for embedded text (UTF-8/UTF-16LE channel labels such as `Fp1`, `Fp2`, `Cz` and unit strings), then fixed-width fields around them (channel count, sample period in 100-ns ticks — e.g. 20 000 ticks = 2 ms = 500 Hz, filter cut-offs as doubles, gain/resolution as float/double, encoding-type enum). `Offset` presumably lets a track definition change mid-record (montage/reference change) — treat as a time-indexed list.
4. **Frames**: `SELECT DataKey, FrameKey, length(Data) FROM FrameInfo` first (cheap): the histogram of `length(Data)` per `DataKey` tells you (a) which DataKey is EEG vs video/audio (video frames are big and variable), (b) whether the EEG frames are fixed-size (uncompressed) or variable (delta-compressed), (c) where gaps are (missing FrameKeys / jumps). Then decode one EEG frame: try `numpy.frombuffer(blob, '<i2')`/`'<f4'` with and without a small per-frame header (compare candidate offsets 0/4/8/16/32 by checking that reshaping to `(n_samples, n_channels)` or `(n_channels, n_samples)` gives smooth, physiologically plausible traces and that consecutive frames join without a step). If sizes vary, implement a delta decoder guided by the `WaveformNonlinearDeltaCompression` hint (per channel: first absolute sample, then variable-length signed deltas with escape codes) — this is the main reverse-engineering risk.
5. **Assembly**: build a `(n_channels, n_samples)` float32 array per contiguous segment, keep the segment start offsets, expose channels, sample rate, filters, events (if found in `MiscInfo`/`.arc`), and write EDF/EDF+ with `pyedflib` or `mne` for cross-checks.
6. **Ground truth**: use the native EDF export (and, if available, the API CSV) of the *same* study; compare per-channel, per-segment, with tolerance = ½ EDF LSB (see §3 quirk 4), and compare event lists.

### 4.2 Unknowns that require test files

- Exact `TrackInfo.Data` and `FrameInfo.Data` blob layouts; per-frame header presence; sample dtype (int16 vs int32 vs float32); byte order (almost certainly little-endian, Windows/.NET); channel-major vs sample-major interleaving.
- Whether frames are `WaveformNoCompression` or `WaveformNonlinearDeltaCompression` on disk (and the delta code definition).
- Physical scaling: µV directly, or digital + gain in TrackInfo.
- Meaning of `FrameInfo.DataKey`/`FrameKey` and `TrackInfo.Offset`; how gaps and mid-record track changes are represented.
- Content of `MiscInfo` (events? impedances? montages? patient fields?) vs. what only lives in the `.arc` file / CadLink DB. **Whether a bare `.ezdata` alone contains everything needed (channel names, start time, events) or whether the `.arc` file is required.**
- Schema evolution across Arc 2.x/3.x/4.x (and whether `.ezdata3` exists) — `SchemaUpdateLog` will tell.
- Video/audio storage location (same SQLite tracks vs. `.ezvideo` sidecars).
- The Easy III `.ez3` block format remains only partially mapped by BioSig; if Easy III support is a goal, separate test files are needed.

### 4.3 Sources

- MathWorks thread (blocked; snippets): https://www.mathworks.com/matlabcentral/answers/480265-reading-clinical-eeg-ezdata-file-in-matlab
- BioSig feature request #13 (read in full): https://sourceforge.net/p/biosig/feature-requests/13/
- BioSig sources (read in full): `sopen_sqlite.c` https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4c%2B%2B/t210/sopen_sqlite.c ; GitHub mirror https://github.com/EEGKit/BioSig-sf/blob/master/biosig4c%2B%2B/t210/sopen_sqlite.c ; `sopen_cadwell_read.c` (same tree); type detection in `biosig.c` (lines ~1740–1750 and ~2053).
- Arc API documentation dump + PowerShell examples (read in full): https://github.com/aminjalali-research/MRI-DICOM-EEG-EMU (`EEGMachine2/API_ARC.txt`, `EEG_EMU.md`).
- Persyst extension→vendor map: https://github.com/Pennsieve/persyst-deidentify/blob/main/main.py ; Persyst supported formats (snippets): https://www.persyst.com/supported-formats-2/ and http://www.persyst.com/wp-content/uploads/2019/02/Supported_Formats_List.pdf
- BESA reader notes (snippets): https://wiki.besa.de/index.php?title=Supported_Data_Formats ; https://www.besa.de/wp-content/uploads/2014/05/BESA-Research-7.1-Reader-Documentation.pdf
- ResearchGate thread (snippets): https://www.researchgate.net/post/I-have-to-convert-a-lot-of-eas-files-generated-by-cadwell-EEG-machine-to-edf-files-or-even-mat-file-Kindly-suggest-an-efficient-method
- Cadwell Arc 3.1 API announcement (snippets): https://www.cadwell.com/eeg/arc-eeg-3-1-software-update/ ; Arc 2.2 release notes: https://www.oit.va.gov/Services/TRM/files/Arc_2_2_Release_Notes.pdf ; Arc Essentia storage rates: https://cadwell.marketing/arc-essentia-eeg/ (snippets)
- Easy III Operator's Manual (blocked): https://cdn.shopify.com/s/files/1/1046/1086/files/Cadwell-Easy-III-Operators-Manual.pdf
- Brainstorm forum requests (snippets): https://neuroimage.usc.edu/forums/t/ez3-cadwell-file-import/28487 ; https://neuroimage.usc.edu/forums/t/eeg-files-unsupported/41226

---

# Findings from test export 1 (added 2026-09-15, verified on the files in `testdata/public/cadwell-export1`)

Everything below was read directly from the files with Python's `sqlite3`
and `struct`; `tools/cadwell_inspect.py` reproduces the inventory.

## What a CadLink study export looks like

```
<name>.export                      1-byte marker file
CadLink/StandAlone.txt             install marker
CadLink/Databases/Core.db, EEG.db, Logging.db     encrypted catalogue DBs (not SQLite-readable)
CadLink/ExternalData/<patient> <date>/<same>.arc, .flex   37-byte text files holding the record GUID
CadLink/Data/<record>-<yyyy-mm-dd-hh-mm-ss>.ezdataindex   frame index + track definition (SQLite)
CadLink/Data/<record>-<yyyy-mm-dd-hh-mm-ss>-1.ezdata      EEG waveform frames (SQLite) <- the data
CadLink/Data/<record>-<yyyy-mm-dd-hh-mm-ss>.ezevents      events (SQLite)
CadLink/Data/<record>.mediadb, <record>-1.mediadb          video/audio frame index + frames (SQLite)
CadLink/Data/Data Integrity Report (...).pdf
```

So the ".ezdata is a SQLite database" statement is right but incomplete:
the study is split into an **index** database, one or more numbered
**data** databases that the index points to by file name
(`FrameInfo.JoinDatabase`), an **events** database and **media**
databases, all SQLite 3, all sharing the same sync/change-tracking
boilerplate (`synctable`, `syncrowdata`, `*SyncRowData`, `SchemaUpdateLog`).
The catalogue databases are encrypted and are not needed.

## `.ezdataindex` (schema 2.5, upgrades dated 2015-2018)

- `MediaHeader`: `MediaDescriptor` = u32 tag `0x015125ca`, u32 0, then
  three length-prefixed ASCII GUIDs (patient id, record id, author/user id -
  the JSON `RecordInfo` in the mediadb names them `PatientId`, `RecordId`,
  `AuthorId`), then 8 bytes. `TrackDefinitionMap` = 32 bytes starting with
  tag `0xbb347891` (the same tag that introduces arrays elsewhere).
- `TrackInfo` (one row, `Offset` 0, `Track` 0, 2628-byte blob): 44-byte
  header (`35be0920 …`, contains a GUID and `0x0a2c` = 2604 = payload
  length, then tag `0xbb347891` and count `0x20` = 32), followed by **32
  channel records of 81 bytes**: 8-byte tag `ab792193de4225a2` + 16 × u32 +
  1 byte. Fields: [1] and [3] = channel number 1..32, [4] = amplifier input
  number (a permutation of 1..32: 4, 2, 9, 11, 16, 10, 22, 17, 3, 1, 7, 5,
  14, 6, 20, 13, 25, 23, 18, 12, 15, 8, 29, 21, 24, 19, 30, 26, 31, 27, 32,
  28), [9] = `0x53673fbf` (constant, meaning unknown), [10] = **250 =
  sampling rate**, [12] = float32 **0.32909** (constant per channel;
  probably the µV-per-LSB resolution or a gain - to be confirmed against
  decoded samples), [2] = 2028 on channel 28 only, others 0. No channel
  labels anywhere in this blob.
- `FrameInfo`: one row per **1-second frame**: `Offset` 0..44 (frame
  number), `TimeStamp` (UTC, 100-ns resolution; frame 0 at
  13:37:50.2763068, later frames drift by a few ms), `Track` 0, `Status` 1,
  `FileIndex` 1, `JoinDatabase` = `<record>-<timestamp>-1.ezdata`, and a
  `FrameKey` GUID that should be the `DataKey` of the blob in the `.ezdata`
  file (the same pairing was verified for the video mediadb).
- `GapInfo`: empty here (`Track, StartOffset, EndOffset, StartTime,
  EndTime, GapVerified`) - this is where recording gaps go (REQ019).
- `PcTimeSync`: PC clock vs. amplifier clock at start and end (sub-ms
  difference here).
- `MiscInfo`: `AMPLAYOUT` (1042 bytes: header with a GUID, then tag
  `0xbb347891`, count 0x24 = 36, then 36 records of 20 bytes tagged
  `0xc489248b`, index 0x50c3 then 1..35 - an input/connector map, no
  labels); `EEGRECORDINFO` twice (588 bytes each, 8 bits/byte entropy,
  i.e. **encrypted**; probably the patient/record fields).

## `.ezevents` (schema 2.5)

`Events(EventID, EventType, UserID, Text, StartTime, EndTime, StartOffset,
EndOffset, LastModifiedBy, Attributes, LastUpdateTime, Priority, Display,
EventManipulation, Deleted, SourceApplicationId, WhenEnteredTime)`.
`StartOffset`/`EndOffset` are **.NET ticks (100 ns) relative to the record
origin** = the time stamp of frame 0 (`PaperSpeedEvent` sits at offset 0 =
13:37:50.2763068; `Start Recording` is at -78850 ticks = 7.9 ms before it;
`Stop Recording` at 460556809 ticks = 46.06 s, matching the 46 s of the
integrity report and 45 frames + 1). Event types seen: `RecordingOnOff`,
`PaperSpeedEvent`, `ReviewedDataEvent`, `MontageEvent`, `BatteryEvent`,
`VideoRecordingOnOff`, `SwitchCamera`, `LiveAmpConfigurationData`,
`AmpConfigurationData` ("32ch 250hz"). `Attributes` blobs are a Cadwell
key/typed-value serialisation (tag `0x937879bb`, count, then
`name`, `.NET type name`, value); the `MontageEvent` blob contains the
montage name and an amp/label-set name (`LB161EKG`) but the trace
definitions are numeric. **Channel labels (E1, Fp1, ...) were not found in
any readable file**; they may live in the encrypted `EEG.db` or be implied
by the amplifier layout name. For now the native EDF/text exports supply
them.

## `.mediadb` (schema 1.2)

`<record>.mediadb` indexes video frames (`FrameInfo(FrameKey, TimeStamp,
Track, Status, JoinDatabase)`, tracks 1 and 3 = the two cameras;
`MiscInfo` JSON: `AVChannelStorageDefinitionMiscInfo`,
`MediaDeviceSettingsMiscInfo`, `RecordInformationMiscInfo`) and
`<record>-1.mediadb` holds the frames (`FrameInfo(DataKey, Data)`, 52
blobs, 70 B to 393 kB, each starting with a 48-byte header `d0ca6245 …`).
The `.ezdata` data file presumably has the same `FrameInfo(DataKey, Data)`
layout with one blob per 1-second EEG frame.

## Open questions that the missing `.ezdata` file will answer

1. Blob layout of an EEG frame: header, sample type (int16/int32/float),
   channel interleaving, and whether `WaveformNonlinearDeltaCompression`
   is used (constant blob size ≈ 250 × 32 × 2 or × 4 bytes + header would
   mean no compression).
2. Physical scaling: does float32 `0.32909` from `TrackInfo` convert raw
   units to µV, and does the result match the text export (mV, 4
   decimals) and the EDF export?
3. Whether the first frame's time stamp or the `Start Recording` event
   defines the EDF start time (7.9 ms apart here).
