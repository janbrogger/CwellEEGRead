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

## `.ezdata` - the EEG frames (decoded 2026-09-15, `cwelleegread/ezdata.py`)

`FrameInfo(DataKey, FrameKey, Data)`, one row per frame; `FrameKey` is the
GUID in the index's `FrameInfo`. Every blob (18-19 kB for 32 ch × 250
samples) has this layout (all little-endian):

| offset | field |
|---|---|
| 0x00 | u32 magic `0x033149bd`, u32 0, u8 1, 8-byte id, f64 1.0, u8 1 |
| 0x1a | u32 payload length (blob length − 55) |
| 0x1e | 8 bytes constant, 8-byte id (same as above) |
| 0x2e | u32 channel count (32) |
| 0x32 | u64 frame start, u64 frame end, in 100-ns ticks from the record origin (frame 0 = 0 .. 10031816) |
| 0x42 | channel blocks, in channel-number order |
| end | 25-byte footer (`00710ac0 …`, frame number, 8-byte id) |

Channel block = the 81-byte channel record known from `TrackInfo`
(8-byte tag `ab792193de4225a2`, 16 × u32 with [1] channel, [4] amplifier
input, [10] rate, [12] f32 0.32909, 8 zero bytes, `01`), then a 13-byte
sub-header: u8 **delta type** (1 = int16 deltas, 2 = int8 deltas), u32
length (8 + delta bytes), f32 **first sample**, f32 scale (1.0), then the
deltas. Samples = first + cumsum(deltas) × scale. This is Cadwell's
"WaveformNonlinearDeltaCompression": per channel and frame the narrowest
delta width that fits is chosen (the constant Cz reference channel takes
1 byte per sample, the noisy inputs 2 bytes).

**Scale**: the samples are in amplifier units; **0.72998046 µV per unit**
converts them to the values of the vendor's text export (all 7755 × 31
samples within the export's 0.05 µV rounding; the rounding bounds the
constant to [0.729980459, 0.729980461]). It is 2.2182 × the 0.32909 stored
in the channel record and no closed form was found; whether it depends on
amplifier model or gain must be checked on other recordings.

**Sample counts**: frame 0 had 248 samples, later frames 250 or 251 (every
fourth), i.e. 11258 samples in 45 frames whose time stamps span
45.0002 s: the amplifier clock runs ~0.08 % faster than the PC frame
clock. The text export keeps every sample (7755 rows for frames 0-30 =
248 + 23 × 250 + 7 × 251). The EDF export writes exactly 250 samples per
second: it resamples by linear interpolation, dropping one sample every
1224 samples (rows 1222-1223, 2446-2447, ... are each the mean of two
neighbouring raw samples, then the stream continues one sample later).
This is why sample-by-sample equivalence against the vendor EDF needs
alignment (REQ008, REQ020) while equivalence against the text export is
exact.

**EDF export facts** (`edf/test.edf`, EDF+C): 32 signals labelled `EEG
<name>-Cz` in amplifier-input order (`EEG 27-2R`, `29-2R`, `31-3R` for
three non-EEG inputs), 250 Hz, physical range ±562500 µV over 16 bits
(**17.17 µV per step** - coarse; the text export at 0.1 µV is the better
ground truth), 44 one-second records, start 14:37:50 local time (the
database time stamps are UTC), patient `test test`, technician `Admin,
CadLink`, equipment GUID, 7 annotations (the events with `Priority` 7 that
fall inside the exported range; the amplifier-configuration and
`Reviewed Data` events are omitted) with onsets in seconds from the frame-0
origin, matching the `.ezevents` tick offsets.

## Remaining unknowns

1. Channel labels (E1, Fp1, ...): not in any readable file; taken from the
   EDF/text export for now. Probably in the encrypted `EEG.db` or implied
   by the amplifier layout name (`LB161EKG` in the montage event).
2. Whether `UNIT_UV` is constant across amplifiers and gains, and what the
   record fields [9] (`0x53673fbf`) and [2] (2028 on one channel) mean.
3. Which time base the vendor uses when resampling for EDF (the 1224:1225
   ratio does not follow directly from the frame ticks); irrelevant if we
   keep raw samples.
4. The 8-byte "id" values (sequential GUID halves) and the frame footer.

---

# Findings from test export 2 and from writing EDF (added 2026-09-15)

**Second recording** (`testdata/public/cadwell-export2`, real EEG, 500 Hz,
16 min): decodes with the same frame layout. Frames hold exactly 500
samples each. `TrackInfo` has a second row for track 1 with 0 channels;
the index lists 961 frames for track 1 too, stored in the same `.ezdata`
file, 8463 bytes each, with a shorter header (u32 magic, u32 track = 1,
u8 0, 8-byte id, f64 1.0, u8 1, u32 length, u32 32, then 32 blocks of 264
bytes whose first bytes look like a 28-byte per-channel record with an
int32 and small constants). Not EEG; the reader uses track 0 only.
The channel-number order in this recording is different (channels 1-7 =
amplifier inputs 26-32) but the amplifier-input numbering maps to the
same electrodes, verified physiologically (see the export's README), so
`cwelleegread/layout.py` keys labels by amplifier input.

**Vendor EDF export rule** (verified on export 1, all 11000 samples within
one EDF step, `tests/test_convert_public.py`):

1. Frames used = all but the last one (the last frame starts after the
   whole-second end of the recording): 44 frames, N_in = 11008 raw samples,
   N_out = 44 × 250 = 11000.
2. Surplus S = N_in − N_out = 8 samples are removed at period
   T = ceil(N_in / (S + 1)) = 1224 in output coordinates: output samples
   T−2 and T−1 (1222, 1223) are the means of raw (1222, 1223) and
   (1223, 1224), raw 1224 is dropped, and so on every T output samples.
   It is a fixed-pattern decimation with two-point smoothing, not a
   constant-ratio interpolation (that was tested and does not match).
3. Start time = frame-0 time stamp + (PcTime − SyncTime) of the first
   `PcTimeSync` row (+341.4 µs here), written as local time (UTC+1) with
   whole seconds in the header and the sub-second part as the first TAL
   of every record (`+0.2766482`, 7 decimals). Annotation onsets are
   absolute offsets from the header second, so the `PaperSpeedEvent` at
   tick 0 appears at `+0.2766482`.
4. Annotations = events with `Priority` 7 whose time lies inside the
   export (montage, paper speed, battery, video on/off); amplifier
   configuration, `Reviewed Data`, `Start/Stop Recording` (outside the
   range here) are not exported. Texts are complete (up to 62 chars seen).
5. Labels `EEG <name>-Cz`, physical range ±562500 µV, digital ±32768,
   transducer `X`, technician `Admin,_CadLink`, equipment = a GUID,
   patient `X X X test_test`.

**Our writer** (`cwelleegread/edfwrite.py`, EDF+C): raw mode keeps every
sample, drops only the trailing partial second, uses a data-driven
symmetric physical range per channel (2 significant digits, ≥ 1 %
margin) so the resolution is ~1/32767 of the peak value, writes UTC by
default (`--timezone` converts), 6-decimal sub-second start in the TALs,
all non-bookkeeping events with their full text (Norwegian characters
are written as UTF-8 in the TAL, which EDF+ allows). Vendor mode applies
rules 1-2 and 5 above. Read-back is verified with pyedflib.

---

# Findings from test export 3 (added 2026-09-15): gaps, headboxes, a filtered vendor EDF

**Frame numbering.** Frame `Offset` n covers ticks [n, n+1) s from the record
origin (the `PaperSpeedEvent` at tick 0). Exports 2 and 3 start at frame 1
(the partial first second is not stored); export 1 started at frame 0 with
248 samples. Our data start is the first stored frame; annotation onsets
are computed from absolute event time stamps relative to that frame's time
stamp, which reproduces the vendor's onsets.

**Gaps.** A stop/restart of the recording leaves frame numbers out
(328-337 here, 10 s) and one `GapInfo` row (`Track 0, StartOffset 328,
EndOffset 338, StartTime/EndTime` = the tick times ± a few ms; `Stop
Recording` at tick 329.97 s and `Start Recording` at 337.19 s show that the
partial frames 328/329 and 337 were discarded). The vendor EDF export
(EDF+C) keeps the time axis continuous and writes **digital zero** for the
missing seconds, exactly at frame boundaries. Our raw mode does the same
and adds a `Recording gap N s (padded with zeros)` annotation (REQ019).

**Headbox identification.** The MiscInfo `AMPLAYOUT` blob starts with tag
`0b847557`, u32 0, a 16-byte layout GUID, tag `736a1a8b`, u32 1, **u32
amplifier type** (5 on the Apollo export 1, 1 on the Essentia exports 2
and 3, repeated at byte 48), tag `026ee873`, then tag `917834bb` and a
record count (36 / 40) of 20-byte records tagged `8b2489c4`. The type
selects the label table in `cwelleegread/layout.py`. Essentia labels
(from the vendor EDF): `E1/Pg1`, `E2/Pg2`, Fp1 ... O2, `1A-1R` ... `7A-7R`;
its vendor EDF range is ±23919 µV = ±32767 amplifier units, whereas the
Apollo export used ±562500 µV. The `MontageEvent` attribute blobs of the
Essentia recordings contain trace names such as `Fp2-E2`, `E1-F7`, so the
electrode names could in future be parsed from the referential montage
instead of a table.

**Scale constant.** The 500 Hz text export bounds the unit to
[0.729980437, 0.729980500] µV, overlapping the 250 Hz bound
[0.729980459, 0.729980461]: one constant, 0.72998046 µV/unit, for both
headboxes and rates. The Essentia vendor EDF's physical maximum 23919.03
/ 32767 = 0.729973 is that constant with the header field truncated.

**Vendor EDF start = user-chosen range.** The export dialog defaults to a
start one frame after the "Reviewed Data" start; the EDF and text exports
of export 3 both begin at frame 30, at frame-30 time stamp + PcTimeSync
offset (+11.114 ms), written as local time with the sub-second in the
first TAL (`+0.8525803`). Our converter exports all frames; a range option
can be added when needed.

**The vendor EDF can be filtered.** Compared with the raw frames the
export-3 EDF has an amplitude ratio of 0.16 below 0.1 Hz, 0.73 at
0.1-0.3 Hz, 0.99 at 0.3-0.7 Hz and 1.00 above: a high-pass of roughly
0.16-0.2 Hz (the Arc viewer's usual low-cut), presumably the display
filter that was active at export time. The export-1 EDF was unfiltered.
Consequences: (1) REQ003's "no filtering" is satisfied by our raw mode, and
the *text* export is the reliable raw reference (TST005); (2) an
equivalence test against a vendor EDF must first establish whether that
EDF is filtered (TST003 now checks the spectral ratio and only compares
samples when it is 1.0 across the band).

---

# What the vendor's exports filter (added 2026-09-15, exports 2, 3 and 3-withfilter)

Export 3 was exported twice: with the viewer unfiltered and with a 10 Hz
high-pass / 15 Hz low-pass viewer filter. Findings:

1. **Text export = raw data.** The full-range text exports of export 3
   (603000 rows, made with and without the 10-15 Hz viewer filter) are
   byte-identical in every data row and equal the decoded frames within
   their 0.05 µV rounding in every band; the export-2 text likewise.
   Viewer filters, montage and sensitivity do not reach the text export.
   Text-export range policy: from the first stored frame (or the dialog's
   start) to the frame before the last one, **gaps omitted** (the 1-second
   time stamps simply jump, here from 10:34:36 to 10:34:47), whereas the
   EDF export pads gaps with zeros. The text dialog defaults to a 30 s
   window from the viewer's current page; the whole recording must be
   selected by hand. "Anonymize Information" only affects the header's
   patient name/id line.
2. **EDF export ignores the viewer filter** but applies its own high-pass.
   The two export-3 EDFs are identical (≤ 1 step) except for the first
   ~10 s of the later-starting one: the filter's start-up.
3. **The EDF high-pass is exactly a 2nd-order Butterworth, 0.16 Hz,
   causal** (transfer-function fit on export 2: order-2 magnitude fit rms
   error 0.0014 at fc = 0.158 Hz; time-domain `scipy.signal.butter(2, 0.16,
   'high', fs=500)` + `lfilter` matches the vendor EDF to 0.52 steps over
   430 000 samples in steady state).
4. **Start-up rule**: the vendor primes the filter by running it over the
   time-reversed beginning of the segment (mirror *including* the first
   sample; ≥ 15 s is converged) and then filters forward - equivalent to a
   filter that has no start-up transient of its own. With that rule the
   whole export-2 EDF (480 000 samples) and the whole export-3-withfilter
   EDF (608 500 samples) are reproduced within 1.04 steps (the 0.04 is the
   vendor's slightly asymmetric physical range −23919.0 / 23919.03 versus
   our symmetric ±23919.27). Zero-state, steady-state-at-first-sample and
   constant-extension start-ups all fail (hundreds to thousands of steps).
5. **Gaps**: the padded gap seconds are exactly digital zero in the vendor
   EDF; after a gap the filter is primed again on the resumed segment
   (mirror rule), not continued through the zeros.
6. **Export range**: the export dialog's start decides the first record:
   record origin (tick 0, frame 0 padded with zeros: export 3-withfilter),
   the first stored frame (export 2), or a user time (export 3, frame 30).
   The EDF start time is that frame's time stamp + the PcTimeSync offset;
   the last frame is never exported.
7. **Annotation policy** (all three Essentia EDFs and the Apollo one):
   events with `Deleted = 1` are dropped; types `AmpConfigurationData`,
   `LiveAmpConfigurationData`, `ReviewedDataEvent`, `ContinuousImpedanceEvent`,
   `BaselineImpedanceEvent` are dropped; of the `PhoticStimEvent`s only the
   "Photic Start N Hz" markers are kept, the individual `Photic Stim`
   flashes (244 here) are not; everything else (montage, paper speed,
   user events, comments, hyperventilation incl. the 10-s increments,
   impedance, recording on/off, battery, video) is kept with its full
   text. Onsets are the events' absolute time stamps relative to the
   export start.
8. **Apollo (export 1)**: its vendor EDF was not high-passed. Whether the
   high-pass depends on the headbox or on the Arc software version (export
   1 was made in Oct 2025, the others in 2026 with Arc 3.2.1097) is not
   known; `--highpass on|off` overrides the automatic choice.

`cwelleegread/edf.py` implements all of this in `--mode vendor`
(`vendor_highpass`, `vendor_resample`, `--start-at record-origin`,
`SKIPPED_EVENT_TYPES/TEXTS`).

---

# Metadata.json of the vendor's EDF export (checked 2026-09-28)

The EDF export writes a `Metadata.json` beside the `.edf` with export
settings, patient fields, `CaseInformation.RecordCreateDate` and an
`Events` list whose `Timestamp`s are 16-digit integers such as
`1781260149854329`. They are **microseconds since 1970-01-01, in local
wall-clock time** (Europe/Oslo: +1 h for export 1 recorded on 2025-10-31,
+2 h for exports 2 and 3 recorded in June), and equal the `.ezevents`
`StartTime` **plus the PcTimeSync clock correction**, rounded to the
microsecond. Over all 143 json events of the three exports the difference
to the predicted value is at most 1 µs (`tests/test_metadata_json.py`):

| export | json minus StartTime | = local offset + clock correction |
|---|---|---|
| 1 | 3 600 000 341–342 µs | 1 h + 341 µs |
| 2 | 7 200 011 198 µs | 2 h + 11 198 µs |
| 3 | 7 200 011 114 µs | 2 h + 11 114 µs |

Consequences:

- They add no precision. The database keeps 100 ns (7 decimals), the EDF+
  annotations written by the same export keep 7 decimals too, the json
  keeps 6. Event timing in this project therefore stays on the `.ezevents`
  stamps (converted the same way: stamp + clock correction, which is also
  the EDF start rule).
- They are not on the amplifier tick clock (`StartOffset`): the tick-based
  prediction differs from the json by several milliseconds with a spread,
  the stamp-based one by a constant.
- The json event list is the EDF export's own selection: deleted events
  and the bookkeeping types (`AmpConfigurationData`,
  `LiveAmpConfigurationData`, `ReviewedDataEvent`,
  `ContinuousImpedanceEvent`, `BaselineImpedanceEvent`) are absent, the
  same rule the converter applies.
- `RecordCreateDate` follows the same local-time convention (export 1:
  7.8 s before the first frame; exports 2 and 3: 20.7 and 112.5 min before,
  i.e. the record was created long before recording started).
- Being local time without a zone marker, the integers are ambiguous
  around the DST change and must not be read as UTC epoch values.

# Two clocks: event time stamps versus sample ticks (found 2026-09-28)

Every event row carries two times: `StartTime`, a wall-clock stamp with
100 ns resolution, and `StartOffset`, ticks (100 ns) from the record origin
on the amplifier's sample clock (frame *k* covers ticks *k*..*k*+1 s
exactly, 500 or 250 samples per frame). The frames carry the same pair
(`TimeStamp` in the index, start/end ticks in the blob). The two clocks do
not run at the same rate:

| export (headbox) | frame stamp increment per frame | stamp clock vs tick clock |
|---|---|---|
| 1 (Apollo, 250 Hz, 45 s) | 1.0000244 s, jittery (std 1.7 ms, a 3 ms step every 4th frame: reception times) | +24 ppm |
| 2 (Essentia, 500 Hz, 16 min) | 0.9999034 s, smooth (std 4 µs: computed, not measured) | −96.6 ppm |
| 3 (Essentia, 500 Hz, 20 min) | 0.9999043 s, smooth (std 4 µs) | −95.7 ppm |

On the Essentia recordings the stamp clock falls behind the tick clock by
96 µs per second: 93 ms over export 2, 116 ms over export 3, about 0.35 s
per hour. The event rows follow the frames exactly: (stamp − ticks) of an
event equals the frame drift curve interpolated at that event plus a
constant 0.42 ms, with 0.3–0.6 ms spread over 620 events. So the two
times of an event carry the same information mapped through one
clock relation; neither is an independent measurement, and the 100 ns
digits do not mean 100 ns accuracy.

Which axis are the samples on? The tick axis by construction (500 samples
per tick-second), so an event must be placed by `StartOffset` to land on
the right sample. The vendor's EDF export places annotations by wall-clock
stamp (onset = stamp − EDF start stamp) on a stream of exactly 500 samples
per record, i.e. it puts them on the tick axis with the stamp clock's
value, and this converter reproduced that until REQ021. The error is the
drift, and its sign is *early*: the stamp clock runs behind the tick clock,
so a stamp-placed event sits before the sample it belongs to by 78 ms at
the photic stimulation of export 2 (13.5 min in), 96 ms at that of export
3 (17 min in), 0.35 s after an hour.

Physiological check (`Photic Stim` flash events, 13 flashes at 2 Hz per
export, O1/O2 average referenced to Cz, baseline −50..0 ms): on the tick
axis the occipital flash response rises at 100 ms and peaks at 110–130 ms
in export 3 (128 ms, +15 µV) and at about 130 ms in export 2, the latency
of a flash VEP; on the stamp axis the identical complex appears 96 ms
(78 ms) later after the (too early) flash marker, peaking at 210–270 ms,
which is not a flash VEP latency. The tick axis is the right one. (The intra-train flash spacing is the same on both
axes, so the test is purely about the absolute offset.)

What this means:

- `Metadata.json` and the EDF+ annotations of the vendor export are
  precise to the microsecond about the wall-clock instant of the event,
  and wrong by the clock drift about which sample it belongs to. Event
  precision was never the problem; the axis is.
- The pause-versus-event offsets measured earlier (data end 0.5–2 s before
  `Stop Recording`, resume 0.8–1 s after `Start Recording`) were computed
  on the tick axis and stand; on the stamp axis they would carry the drift
  in addition.
- Implemented as REQ021/TST016: the converter's `--event-timing
  ticks|stamp|auto` (auto = ticks in raw mode, stamp in vendor mode, so the
  vendor-equivalence tests are untouched) and the EEGLAB plugin's
  `'eventtiming'` option (default ticks). Ticks are mapped through the
  stored frames' tick spans (`event_sample` in `edf.py` and in
  `cadwell_read.m`): linear within a frame, which also absorbs the
  248–251-sample Apollo frames, nominal rate across padded pauses, the
  join for an instant inside a concatenated pause. Durations come from the
  tick offsets too. `tests/test_event_timing.py` checks the drift and the
  flash VEP latency on both axes for exports 2 and 3.
- The absolute EDF start time is unaffected (first frame stamp plus the
  PcTimeSync correction, both wall clock). PcTimeSync itself (two rows per
  record, PC time minus sync time growing 10–30 ppm) is a third relation
  and does not explain the 96 ppm; the frame stamps on Essentia look like
  a computed ratio rather than measured reception times, so which physical
  clock is "true" wall time is not settled by the files alone. For sample
  alignment that does not matter: samples live on the tick axis.

# MATLAB/Octave port (added 2026-09-28)

`uses/EEGLAB/cadwellio/` re-implements the reader natively for EEGLAB users:
`cadwell_decode_frame.m` (frame blob to samples), `cadwell_read_index.m`,
`cadwell_read_events.m`, `cadwell_read.m`, `cadwell_layout.m`. SQLite access
goes through `cadwell_sqlite.m`; its default backend `cadwell_sqlite_native.m`
is a reader of the SQLite 3 file format written in plain MATLAB/Octave
(database header, table b-tree interior/leaf pages, varints, record serial
types, overflow chains, `INTEGER PRIMARY KEY` rowid aliases, column names
from the `CREATE TABLE` text). It reads whole tables in rowid order and the
readers filter and sort in MATLAB, so no SQL engine is needed. Library
backends (mksqlite, Database Toolbox / Octave sqlite package, xerial
sqlite-jdbc, py.sqlite3) remain as optional cross-checks. Two format facts
that matter for such a reader: Cadwell databases use text encoding 2
(UTF-16LE, header byte 56), and all values of all tables fit in doubles
(no integer beyond 2^53 in the public exports; the reader keeps the stored
storage class per value in `t.kinds`).

The frame-numbering pauses versus the vendor's `Stop/Start Recording`
events: the stored data end 0.5-2 s before the Stop event and resume
about 1 s after the Start event on every public export (table in
`uses/EEGLAB/README.md`, "Where the vendor's Stop/Start Recording events
sit relative to the data"); the vendor's EDF export places the events
identically inside its zero padding.

Under GNU Octave 8.4 the port equals the Python decoder bit for bit on the
first 20 frames of all three public exports, reproduces the index, labels,
events and gaps through both the native and the JDBC backend, dumps every
table of every `.ezdataindex`/`.ezdata`/`.ezevents` file of the three
exports (102 tables, 19 000 rows, 68 MB) byte for byte identically to
Python's sqlite3 in a canonical serialization, and equals the vendor text
export of export 1 within 0.05 µV (`cadwell_selftest.m`, run by
`tests/test_octave_port.py`).

Speed (Octave 8.4, one core of a shared cloud container, so absolute
numbers are rough and vary by ±30 % between runs; the ratios are what
matters):

| Read of the whole export | before | after vectorising |
|---|---|---|
| export 1 (32 ch, 45 s at 250 Hz), native / JDBC | 1.7 s / 4.5 s | 0.5 s / 0.5 s |
| export 2 (32 ch, 16 min at 500 Hz), native / JDBC | 39 s / 33 s | 8 s / 10 s |
| export 3 (32 ch, 20 min at 500 Hz, one 10 s pause), native / JDBC | 57 s / 49 s | 9 s / 10 s |

What was slow, in order of cost, and what changed:

1. `containers.Map` keyed by frame key (one insert per frame): Octave's
   implementation re-sorts its key list on every insert, so 2414 inserts
   cost 15 s. Replaced by one `ismember` of the index keys against the
   data-table keys.
2. Per-channel assembly `blk(j, :) = fr.samples{k}'` (38 500 indexed
   assignments): 9 s. The decoder now returns the frame as one
   `[samples x channels]` matrix, placed with one assignment per frame
   into a preallocated output (no `[blocks{:}]` concatenation, which
   allocated a second 155 MB copy).
3. The decoder's per-channel loop: 5 s. The 32 block headers are gathered
   with one index matrix; the delta payloads are gathered per group of
   channels sharing delta type and length (the compressor picks int8 or
   int16 per channel, so a frame usually has two groups) and decoded with
   one `typecast` and one `cumsum` per group.
4. The native SQLite reader (two `FrameInfo` tables of 2414 rows): 2.7 s
   each, now 1.6 s. One-byte varints are inlined, all serial types of a
   record header are decoded with one vectorised expression, ASCII text
   skips `native2unicode`, cell pointers of a page are read at once and
   the row store grows geometrically. What remains is interpreter cost
   per value (about 17 000 values per table). The JDBC backend is not
   faster from Octave: fetching the same table through the Java bridge,
   one `getString`/`getLong`/`getBytes` call per value, takes about 4 s,
   so the pure-MATLAB reader is both dependency-free and the quickest
   of the backends tried here.

The remaining ~9 s for export 3 (20 min, 608 500 samples x 32 channels) split roughly into 3.5 s SQLite (native), 3 s
frame decoding, 1.5 s allocating the 155 MB output (slow in this container)
and 1 s events and index bookkeeping. Two portability lessons: `Class.forName` cannot see jars added
with `javaaddpath`, so the JDBC driver is instantiated with `javaObject`; and
`datenum` differences lose microseconds at 2026 dates, so time differences
are computed from a seconds-since-2000 parser (`cadwell_timestamp_sec.m`).
