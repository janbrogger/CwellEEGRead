> Scoping report produced 2026-09-28 by Claude Code (session `831b87b8-e6bd-4acd-901b-d67180234ee3`, see `llm-logs/`). Two research agents read the FieldTrip and EEGLAB sources; the SQLite-access options were checked by hand, including two small prototypes run on the public test exports. Claims are tagged **[V]** verified by reading source or by running it here, **[W]** from a web page summary or search snippet (MathWorks, sqlite.org and the Octave sites are blocked by the egress proxy), or **[I]** inferred. Treat as a starting point; the transcript records exactly what was fetched.

# Scoping report: reading Cadwell `.ezdata` natively in EEGLAB and FieldTrip

Date: 2026-09-28. For CwellEEGRead (Jan Brogger). Relates to NEED006, REQ016
and the `uses/EEGLAB` scaffold.

## 0. Summary and recommendation

**Recommendation: write one pure-MATLAB/Octave Cadwell reader (no toolbox,
no Java, no MEX) with a small read-only SQLite b-tree parser inside it, and
expose it twice: as an EEGLAB import plugin (`cadwellio`, direct
`pop_cadwell`) and as a FieldTrip external-format function
(`cadwell_ezdata.m`) that also reaches EEGLAB through the File-IO plugin.**

Why this shape:

1. **The Cadwell decoding itself is small.** The Python decoder that is
   verified sample-for-sample against the vendor's text export is 255 lines
   (`cwelleegread/ezdata.py`) plus an 80-line label table; the frame format
   is `fread`/`typecast`/`cumsum` work that ports 1:1 to MATLAB. Everything
   that is hard in this project (vendor high-pass, resampling, EDF+ writing)
   is *not* needed by a reader, which delivers raw samples.
2. **The only real obstacle is getting BLOBs out of SQLite in MATLAB**, and
   every off-the-shelf option has a serious drawback for a distributed
   plugin: the Database Toolbox costs money and its `fetch` does not return
   BLOBs [W]; `sqlite-jdbc` works (verified here under Java 21) but MATLAB
   stopped loading Java by default in R2025a and stops shipping a JRE in
   R2026b [W]; `mksqlite` is MEX and needs binaries per platform and
   MATLAB ABI. A dependency-free reader of the SQLite file format avoids all
   of it. A 115-line Python prototype written for this report walks the
   table b-tree, follows overflow chains, decodes records, and returns every
   frame blob of all three public test exports byte-identically to
   `sqlite3` [V]. The Cadwell files use a 4096-byte page, rollback-journal
   mode (not WAL) and UTF-16LE text [V], all of which the prototype handles.
   The MATLAB port is estimated at 150-250 lines.
3. **FieldTrip's current guidance is exactly the "one function, three call
   forms" pattern**, and its `otherwise` branches call any function on the
   path by name. So the FieldTrip reader can be developed and used entirely
   outside FieldTrip first (`cfg.headerformat = 'cadwell_ezdata'`), then
   upstreamed with a one-clause `ft_filetype` change and a test script.
   Once upstream, EEGLAB's File-IO plugin reads it with no further work
   because `pop_fileio` uses `ft_filetype` autodetection [V].
4. **Pure MATLAB code runs under Octave**, which means the reader can be
   tested in CI on GitHub Actions against reference values produced by the
   Python decoder, without a MATLAB licence. That gives the same
   "proven equivalence" property the Python converter has (NEED003).

Estimated effort (one developer, MATLAB fluent, with the existing Python
reader as the specification): about 2 to 3 weeks of focused work to a
tested v1.0 of both plugins, plus the FieldTrip review cycle (days when a
test and data are supplied, see section 4.3). Details in section 7.

## 1. What a reader has to do (format recap)

All facts in this section are verified on the public test exports and
documented in `cadwell-file-format.md`; the reference implementation is
`cwelleegread/ezdata.py`.

A CadLink study export holds, under `CadLink/Data/`, per record:
`<record>-<ts>.ezdataindex` (frame index, channel table, gaps, clock sync),
`<record>-<ts>-<n>.ezdata` (the EEG frames; several numbered files for long
recordings, each named in the index's `JoinDatabase` column),
`<record>-<ts>.ezevents` (events) and `.mediadb` files (video, not needed).
All are SQLite 3 files. The reader needs:

| Step | Source | Work in MATLAB |
|---|---|---|
| Find the record | folder or `.ezdataindex` path | `dir('*.ezdataindex')` |
| Channel table | `.ezdataindex` `TrackInfo` blob, track 0: 32 records of 81 bytes tagged `ab792193de4225a2`; fields channel no, amplifier input no, sampling rate | `strfind` for the tag, `typecast` |
| Frame index | `.ezdataindex` `FrameInfo` rows (Offset, TimeStamp text, Track, FrameKey GUID blob, JoinDatabase text) | table scan; keep track 0 |
| Gaps | `.ezdataindex` `GapInfo` | table scan |
| Start time | first frame TimeStamp plus (PcTime - SyncTime) of the first `PcTimeSync` row | text parse |
| Headbox type | `MiscInfo` key `AMPLAYOUT`, u32 at offset 44 (5 = Apollo, 1 = Essentia) | `typecast` |
| Frames | `.ezdata` `FrameInfo(DataKey, FrameKey, Data)`: per frame a 66-byte header then per channel an 81-byte record, a 13-byte sub-header (delta width, length, first sample f32, scale f32) and int8 or int16 deltas; samples = first + cumsum(deltas) * scale | `typecast`, `cumsum` |
| Scale | 0.72998046 µV per unit, constant on both headboxes and rates seen | multiply |
| Labels | not stored; per-headbox table keyed by amplifier input (`cwelleegread/layout.py`), user override allowed | port the table |
| Events | `.ezevents` `Events` (EventType, Text, StartTime, EndTime, Deleted, Priority); onsets = absolute time stamps relative to the first stored frame | text parse |

Things a reader must decide (policy, all already decided for the Python
converter and to be mirrored, see REQ019 and REQ020):

- **Variable samples per frame** (248/250/251 at nominal 250 Hz on the
  Apollo headbox; exactly 500 at 500 Hz on Essentia). Raw fidelity means
  concatenating every sample and declaring the nominal rate; the effective
  rate and drift go into `hdr.orig` / `EEG.etc`.
- **Gaps** (missing frame numbers plus a `GapInfo` row). EDF export pads
  with zeros; for EEGLAB and FieldTrip the natural representation is a
  `boundary` event with a duration (see sections 3.2 and 4.2), with
  zero-padding as an option to stay aligned with the vendor EDF.
- **Trailing partial frame**: the vendor never exports the last frame; the
  reader can keep it (raw) since it does not write fixed-length records.
- **Auxiliary track 1** frames (0 channels, 264-byte blocks, not EEG) are
  skipped.
- **Not needed**: the vendor's 0.16 Hz high-pass, the 1224:1225 resampling,
  the EDF physical-range policy, the event filtering. These exist only to
  match the vendor's EDF export and stay in the Python converter.

Size of the reference: `ezdata.py` 255 lines, `layout.py` 80 lines. The
MATLAB port of the decoding is estimated at 250-350 lines excluding SQLite
access.

## 2. Getting BLOBs out of SQLite in MATLAB and Octave (the crux)

### 2.1 Facts about the Cadwell files that matter here [V]

Measured on all three public exports with a 100-byte header read and
`sqlite3`:

| Property | Value | Consequence |
|---|---|---|
| Page size (header bytes 16-17) | 4096 | frames of 18-35 kB always spill into overflow pages |
| File format write/read version (bytes 18-19) | 1, 1 | rollback-journal mode, **not WAL**; no `-wal`/`-shm` files in the exports; the main file is complete |
| Text encoding (bytes 56-59) | 2 = **UTF-16LE** | text columns (TimeStamp, JoinDatabase, EventType, Text) must be decoded as UTF-16, not UTF-8 |
| `.ezdata` blob sizes | 18071-18692 B (32 ch, 250 Hz); 8463 (aux track) to 34552 B (32 ch, 500 Hz) | 5-9 overflow pages per frame |
| Indexes | `IndexFrameKey` on `FrameInfo(FrameKey)` plus autoindexes | a reader can ignore them and scan the table b-tree, matching frames by key in memory |
| Extra table in export 1 | `FrameInfo-<guid>` (RowId only) | ignore |
| Row counts | 45 / 1922 (961 EEG + 961 aux) frames; 30 MB `.ezdata` for 16 min at 500 Hz | a 24 h recording is about 2.7 GB and 86 400 EEG frames [I] |

### 2.2 Options

| Option | Licence | Needs | Octave | BLOBs | Verified here | Verdict |
|---|---|---|---|---|---|---|
| **A. Database Toolbox `sqlite`** (R2016a+) | MathWorks, paid | Database Toolbox | no | `fetch` returns double/int64/char only, not BLOB (MATLAB Answers 451624, 2019; no later change found) [W] | no (blocked site) | unusable for frames even where the toolbox exists |
| **B. `sqlite-jdbc`** (xerial) 3.53.4.0 | Apache-2.0 / BSD-2 | 12.0 MB jar + `slf4j-api` jar on the Java class path; a JVM | Octave has a `java` package; untested | `ResultSet.getBytes` gives `int8` in MATLAB, `typecast` to `uint8` | **yes**: Java 21, read-only via `open_mode=1`, no `DriverManager` needed (`org.sqlite.JDBC().connect(url, props)`), 1922 frames / 28 MB in 0.03 s [V] | works today, but MATLAB R2025a no longer starts Java by default and R2026b ships no JRE (user installs OpenJDK and runs `jenv`) [W]; EEGLAB plugin install already fails on Octave when plugins call Java [W]. Fine as an *optional* accelerator, wrong as the only path |
| **C. `mksqlite`** 2.13 (2022) | BSD-2-Clause [V] | MEX binary per platform and MATLAB ABI; README claims R13SP1-R2024b and mexw64/mexa64/mexmaci64/mexmaca64, but SourceForge only lists `win64` zips [W] | no | native `uint8` | no | licence fine, distribution painful (plugin would have to build and ship 4 binaries per MATLAB generation); FieldTrip does accept MEX under `external/` (xdf precedent) [V] |
| **D. `matlab-sqlite3-driver`** (kyamagu) | BSD-3 | compile yourself | no | yes | no | archived 2020 [W]; not an option |
| **E. Octave `sqlite` package** 0.1.4 | GPL-3 [W] | Octave 6+, libsqlite | Octave only | not documented [W] | no | irrelevant for MATLAB users; GPL |
| **F. `py.sqlite3`** (R2014b+) | n/a | a Python matching the MATLAB release, `pyenv` | no | `uint8(py.bytes)` | in effect: this is the existing Python reader | fallback only; but note it could call `cwelleegread` itself and hand back arrays, which is a cheap "reuse the verified decoder" mode |
| **G. Pure MATLAB/Octave SQLite table reader** | ours (Unlicense) | nothing | yes | yes | **prototype in Python, 115 lines, byte-exact on all three exports, 0.24 s for 1922 rows** [V] | **recommended primary path** |

### 2.3 What the pure reader has to implement [V, from the prototype]

The prototype (`tools/sqlite_pure_reader.py`)
implements, in order of size:

1. Header: magic `SQLite format 3\0`, page size (u16 big-endian at 16, value
   1 means 65536), reserved bytes per page (byte 20), write/read version at
   18-19 (refuse 2 = WAL unless no `-wal` file exists next to the database),
   text encoding at 56-59.
2. Varints: 1-9 bytes, big-endian 7-bit groups, ninth byte carries 8 bits.
3. Table b-tree pages: type byte 0x05 (interior: 12-byte header with the
   right-most child pointer, cells = child page + rowid) and 0x0D (leaf:
   8-byte header, cells = payload size, rowid, record, optional overflow
   page number). Page 1 carries the 100-byte file header first. Traversal
   in rowid order is a stack walk; no index b-trees needed.
4. Overflow: with usable page size U, X = U - 35, M = ((U - 12) * 32 / 255)
   - 23, K = M + ((P - M) mod (U - 4)); local part is K if K <= X else M;
   then a chain of pages each starting with the next page number.
5. Records: header size varint, serial types (0 NULL; 1-6 signed ints of
   1,2,3,4,6,8 bytes; 7 float64; 8,9 constants 0/1; even >= 12 BLOB of
   (N-12)/2 bytes; odd >= 13 text of (N-13)/2 bytes in the file's encoding).
6. `sqlite_schema` at root page 1 gives each table's root page by name.

Not needed for Cadwell files: index b-trees, freelist, WAL, journal
recovery, non-4096 page sizes (handled anyway by the formulas). The two
sources consulted for the layout were an MIT-licensed Standard ML
implementation (`sjqtentacles/sml-sqlite`, which stops short of overflow
pages) [W] and the DC3 `sqlite-dissect` forensic parser [W]; the prototype
was written from the format description and checked against `sqlite3`.

Performance in MATLAB: the work per frame is one `fseek`/`fread` per page
(6-10 pages) plus varint parsing; 86 400 frames of a 24-hour recording mean
under a million small reads. Reading the whole `.ezdata` with `fread` into
a `uint8` vector (or `memmapfile`) and indexing pages by arithmetic is the
faster variant and costs the file's size in RAM (2.7 GB for 24 h, so do it
per `.ezdata` file, or per range of pages). Frame decoding itself is
vectorised (`typecast` + `cumsum`). A MATLAB timing of the port is the
first milestone of the work plan; a rough expectation from the Python
figures (0.24 s SQLite walk plus 3.6 s decoding for 16 min at 500 Hz) is
tens of seconds for an hour of data in interpreted MATLAB, which is
acceptable for an importer and can be improved later by the optional
Java backend (B) if ever needed.

Risks for G: (1) a future Cadwell version switching the databases to WAL
mode would require reading the `-wal` file too (about 60 more lines, or a
clear error asking the user to open and close the study in Arc so that it
checkpoints); (2) a 65536-byte page or a reserved-bytes value other than 0
is untested; (3) correctness rests on our own tests, so the CI comparison
against `sqlite3`-derived reference data (section 6) is not optional.

## 3. Route A: EEGLAB plugin (`cadwellio`)

### 3.1 What exists

`uses/EEGLAB/cadwellio/` already holds a working skeleton [V]:
`eegplugin_cadwellio.m` (registers *From Cadwell* under *File > Import
data > Using EEGLAB functions and plugins*, the menu tagged `import data`),
`pop_cadwell.m` (GUI when called without arguments, returns `[EEG, com]`,
today imports the EDF written by CwellEEGRead through `pop_biosig` or
`pop_fileio`, and errors on `.ezdata`), `cadwell_sqlite_info.m` (table
listing through Database Toolbox, mksqlite or `py.sqlite3`), README,
LICENSE, and `make_zip.sh` producing `dist/cadwellio0.1.0.zip`.

The plugin contract, re-verified on `sccn/eeglab` develop (2026-09-11) and
on the `bva-io`, `neuroscanio`, `xdfimport` and `mffmatlabio` plugins [V]:

- `eeglab.m` scans one level of `plugins/`, adds each folder to the path,
  calls `vers = eegplugin_<name>(fig, trystrs, catchstrs)` and warns when
  the version in the folder name (`cadwellio1.0.0`; trailing digits, dots
  and underscores are the version) differs from the returned string.
- Import plugins register with `uimenu(findobj(fig, 'tag', 'import data'),
  'label', ..., 'callback', [trystrs.no_check '[EEG LASTCOM] = pop_cadwell;'
  catchstrs.new_non_empty])`; `eeglab_new` in the catch string stores the
  dataset and pushes `LASTCOM` into the history, so the `pop_` function
  only returns `com`. The skeleton's `'try, ...' catchstrs.new_and_hist`
  form (as in `neuroscanio`) is equivalent.
- There is no manifest file (`eegplugin.json` does not exist); the only
  machine-readable metadata is the folder name and the `vers` string.
- EEGLAB core is BSD-2-Clause; its LICENSE states that plugins "may be
  released under different licenses" and the manager lists GPL-2, GPL-3,
  BSD-2 and BSD-3 plugins, so an Unlicense plugin is acceptable [V/I].
- Minimum MATLAB for EEGLAB is 2008b; EEGLAB has supported Octave since
  2021 (best tested on Octave 6.1, "improved Octave 8.4 compatibility" in
  2024.0), plugins must be installed on Octave by unzipping manually, and
  most plugins are untested there; `eeg_checkset` converts double data to
  `single` by default [V].

### 3.2 What changes

1. Replace the `.ezdata` branch of `pop_cadwell` with a call into the
   shared reader (section 5), accepting a folder, a `.ezdataindex` or a
   `.ezdata` path (resolve to the index: same stem without `-<n>`).
2. Fill the EEG structure: `EEG = eeg_emptyset`; `EEG.data` as
   `single`, channels x samples, in µV; `EEG.srate` (nominal); `EEG.nbchan`,
   `EEG.pnts`, `EEG.trials = 1`, `EEG.xmin = 0`; `EEG.chanlocs(i).labels`
   from the headbox table with `.type = 'EEG'` (or `'ECG'`, `'Misc'` for the
   non-EEG inputs) and `EEG.ref = 'Cz'`; run `pop_chanedit` lookup only on
   user request (the labels are 10-20 names, so
   `dipfit/standard_1005.elc` lookup works when the user asks for it).
3. Events: one `EEG.event` per non-deleted event with `type = EventType` (or
   the text for user comments), `latency` in samples, 1-based and allowed
   to be fractional, from the absolute time stamp relative to the first
   stored frame, `duration` in samples, and the full text in an extra field
   (`description`). Keep the vendor's bookkeeping events
   (`AmpConfigurationData`, `ReviewedDataEvent`) out by default with an
   option to include them. Keep `type` homogeneous (all strings).
4. Gaps: EEGLAB never pads; every core function represents a discontinuity
   as an event of type `boundary` placed half a sample after the last
   sample before the gap (`latency = n_before + 0.5`) with `duration` = the
   number of missing samples (`eeg_insertbound.m`, [V]). Do the same by
   default (concatenate the segments, insert the boundary), and offer
   `'gaps', 'pad'` to zero-fill instead so that latencies match the vendor
   EDF and CwellEEGRead's default output.
5. Metadata: `EEG.etc.cadwell` with record/patient GUIDs, schema versions,
   headbox type, start time (UTC and local), clock correction, effective
   sampling rate and drift, samples per frame, gap list, and whether labels
   were inferred, mirroring the JSON report of the Python CLI. EEGLAB has no
   standard start-time field; the only convention read by core code is
   `EEG.etc.T0 = [Y M D h m s.fff]` (set by the BioSig importer, consumed by
   `writeeeg`), and `mffmatlabio` uses `EEG.etc.recordingtime` [V]; fill
   `EEG.etc.T0` and an ISO string.
6. Options for `pop_cadwell(file, 'key', value)`: `'labels'` (file or cell
   array override), `'gaps'` (`'boundary'`|`'pad'`), `'range'` (seconds),
   `'events'` (`'on'`|`'off'`|`'all'`), `'backend'`
   (`'matlab'`|`'java'`|`'python'`, default `'matlab'`), and the usual
   history string `com`.
7. Finish with `eeg_checkset(EEG, 'eventconsistency')` and `'makeur'`, as
   the skeleton already does.

### 3.3 Distribution

Zip named `cadwellio<version>.zip` unpacking to `cadwellio<version>/` with
`eegplugin_cadwellio.m`, `pop_cadwell.m`, the shared reader files, README
and LICENSE at its top level; version identical in the folder name and the
`vers` string. **The web upload form named in `downstream-uses.md` and in
the wiki is closed** ("for security reasons"); the current procedure is
the `sccn/eeglab` issue template *New plugin or plugin update* (plugin
name, current and new version, description, the zip dragged into the issue
or a GitHub-release link named `<name><version>.zip`; recent submissions
also state licence, source repository and a SHA-256), after which an SCCN
admin enters it into the server list that the plugin manager downloads
from [V]. The manager itself only downloads and unzips; there is no
validation and no MATLAB-version field. Because the reader has no MEX,
Java or toolbox dependency, the plugin is one zip for every platform, and
Octave users can use it by unzipping it into `plugins/` themselves.

## 4. Route B: FieldTrip reader (`cadwell_ezdata.m`), reaching EEGLAB via File-IO

### 4.1 How the Nervus reader is wired today [V, FieldTrip master 7bcde3ff, 2026-09-24]

Jan's Nervus reader consists of `fileio/private/read_nervus_header.m` (999
lines, 18 subfunctions, pure `fopen`/`fseek`/`fread`) and
`read_nervus_data.m` (169 lines, seeks per channel and section), a
four-line clause in `ft_filetype.m` (lines 1517-1520: extension `.e` only,
manufacturer Natus), and `case 'nervus_eeg'` blocks in `ft_read_header`
(1859-1861, sets `checkUniqueLabels = false`, which also skips the default
`chantype`/`chanunit` filling), `ft_read_data` (1074-1108: re-reads the
header, reads *all* channels and segments into memory, then slices
`begsample:endsample, chanindx`) and `ft_read_event` (1565-1609: events
from `hdr.orig.Events`, plus a `boundary` event per segment gap with
`duration` in samples, and later events shifted by the gap). The PR #1358
fix for mixed sampling rates keeps only the channels at the most frequent
rate (`mode(samplingRate)`), which Robert Oostenveld endorsed as "consistent
with EDF". Test: `test/test_nicolet_reading.m` with `% MEM`, `% WALLTIME`,
`% DEPENDENCY`, `% DATA private` header lines, `dccnpath(...)` for the data
on the DCCN server, header asserts and a sample-by-sample comparison against
the vendor ASCII export within 0.01, then `ft_preprocessing` and
`ft_databrowser` smoke tests.

### 4.2 The current recommended pattern is simpler than what Nervus uses [V]

FieldTrip's `ft_read_header`, `ft_read_data` and `ft_read_event` each end
their format switch with an `otherwise` branch that runs the format name as
a function if it exists on the path:

```matlab
otherwise
  if exist(headerformat, 'file')
    % attempt to run "headerformat" as a function, this allows the user to specify an external reading function
    % this is also used for bids_tsv, biopac_acq, motion_c3d, opensignals_txt, qualisys_tsv, sccn_xdf, and possibly others
    hdr = feval(headerformat, filename);
```

with `dat = feval(dataformat, filename, hdr, begsample, endsample, chanindx)`
and `event = feval(eventformat, filename, hdr)` in the other two. The
website FAQ "dataformat_own" documents the contract: one function, three
call forms distinguished by `nargin` (1, 5, 2). In-tree examples are
`fileio/private/biopac_acq.m`, `snirf.m`, `motion_c3d.m`, `qualisys_tsv.m`,
`sccn_xdf.m`. So:

- **Stage 1 (no FieldTrip change):** ship `cadwell_ezdata.m` with the
  plugin; users set `cfg.headerformat = cfg.dataformat = cfg.eventformat =
  'cadwell_ezdata'` in `ft_preprocessing`, or call `ft_read_header(f,
  'headerformat', 'cadwell_ezdata')`.
- **Stage 2 (upstream):** add one clause to `ft_filetype.m`, early in the
  ladder because it is order-sensitive:
  `filetype_check_extension(filename, '.ezdata') && filetype_check_header(filename, 'SQLite format 3')`
  with `type = 'cadwell_ezdata'`, `manufacturer = 'Cadwell'`, `content =
  'EEG'` (accept `.ezdataindex` too); put `cadwell_ezdata.m` in
  `fileio/private/`; no edits to the three `ft_read_*` files are needed
  because the type name equals the function name. Add
  `test/test_cadwell_reading.m` in the Nicolet style and a website page
  `getting_started/eeg/cadwell.md`.

Header fields to return: `Fs` (nominal), `nChans`, `label` (N x 1 cell),
`nSamples`, `nSamplesPre = 0`, `nTrials = 1`, `chantype` and `chanunit`
(`'uV'`, which `pop_fileio` uses to keep EEGLAB data in µV [V]), `orig`
(the same metadata block as `EEG.etc.cadwell`). Data: honour
`begsample`/`endsample`/`chanindx` by decoding only the frames covering the
range (frame n covers samples known from the cumulative per-frame counts in
`hdr.orig`), unlike the Nervus reader which decodes everything on every
call. Events: integer `sample` at `hdr.Fs`, `type`/`value`/`duration`/
`offset = 0`, plus events with both `type` and `value` set to `'boundary'`
for gaps with `duration` in samples. `pop_fileio` has no boundary logic of
its own: it copies the FieldTrip `value` into `EEG.event.type`, `type` into
`EEG.event.value`, `sample` into `latency` and `duration` into `duration`
[V], which is why both fields must say `boundary` (as the Nervus reader
does) for `eeg_checkset` to treat the event as a discontinuity.

### 4.3 Upstreaming: what the maintainers asked for last time [W, GitHub pages; API blocked]

- #186 (2016) and #266 (2016) were merged within a day or five with no
  review comments. #302 (2017-2019) stalled for two and a half years on one
  point: "an example data set and a test script"; a 33.5 MB zip of test
  data committed to the PR was the reason Robert re-based it as #1166 and
  dropped that commit. #1358 (2020) was merged by Jan-Mathijs Schoffelen
  within about a day after inline review, a request to update the website
  page (`getting_started/nicolet`), and a test whose data lives in a
  separate repository (`janbrogger/FieldTripNicoletTestData`) and on the
  DCCN server. The day after the merge the test did not run on Linux or
  macOS (a Windows-only assumption in the header reader), so: test on Linux
  and macOS before submitting.
- Conventions (`.github/CONTRIBUTING.md`, website code guideline) [V/W]:
  no CLA; GPL-3 header with the author's copyright; 2-space indents, no
  space before `(`; `ft_error`/`ft_warning` with identifiers; no nested
  functions; roughly five years of MATLAB back-compatibility; a test script
  under `test/` named `test_pullNNNN.m` or descriptively, with the
  `% MEM`/`% WALLTIME`/`% DATA`/`% DEPENDENCY` header, data sent to the
  maintainers out of band and referenced through `dccnpath`.
- Licence note: contributing `cadwell_ezdata.m` to FieldTrip means
  releasing that copy under GPL-3 with our copyright, which the Unlicense
  permits; the copy in this repository stays public domain [I].
- External dependencies would go under `fieldtrip/external/<name>` with an
  `ft_hastoolbox` entry (jar precedent: `external/mffmatlabio`, GPL-3, uses
  `javaaddpath`; MEX precedent: `external/xdf`, BSD-2) [V]. The pure
  reader needs none, which removes the most likely review objection.

### 4.4 EEGLAB through File-IO

`pop_fileio.m` (455 lines) calls `ft_read_header(filename)` with no format
option, `ft_read_data(filename, 'header', hdr, ...)` with `'dataformat'`
only when the user picked one from a hard-coded list (which does not contain
`nervus_eeg` either), and `ft_read_event(filename, dataopts{:})` [V]. So a
Cadwell reader becomes visible in *File > Import data > Using the FILE-IO
interface* exactly when `ft_filetype` recognises the file, i.e. after Stage
2 is merged *and* the EEGLAB "Fileio" plugin has been refreshed. That
plugin is a dated snapshot of FieldTrip's fileio module (the current one is
`Fileio250523`, i.e. 2025-05-23, listed in `eeglab.prj`; the standalone
mirror `github.com/fieldtrip/fileio` is synchronised with FieldTrip master
but the EEGLAB zip is repackaged by SCCN around each release) [V/I], so the
lag from a FieldTrip merge to plugin-manager users is months to a year
unless they run FieldTrip itself. That lag is outside our control and is
one reason to keep Route A as the primary EEGLAB delivery. A middle way
used by `mffmatlabio` is to ship FieldTrip-style reader functions inside
the EEGLAB plugin (`mff_fileio_read_header.m` etc.) so that FieldTrip users
can call them by name before anything is upstream; `cadwell_ezdata.m` in
the plugin folder is exactly that.

## 5. Proposed architecture: one shared reader, two front ends

```
uses/EEGLAB/cadwellio/                 (later: its own repository, e.g. janbrogger/cadwellio)
  eegplugin_cadwellio.m                EEGLAB registration (exists)
  pop_cadwell.m                        EEGLAB front end (exists, to be completed)
  cadwell_ezdata.m                     FieldTrip front end: hdr / dat / evt by nargin
  cadwell_read.m                       library: rec = cadwell_read(path, opts) -> struct with
                                         channels, frames, gaps, start time, events, labels,
                                         and data(nchan x nsamples) or a per-frame decoder
  cadwell_decode_frame.m               one .ezdata blob -> samples per channel (port of decode_frame)
  cadwell_labels.m                     headbox tables (port of layout.py) + user override
  sqlite_table_read.m                  pure-MATLAB SQLite: rows = f(file, tablename) with
                                         BLOBs as uint8, text decoded per the file encoding
  sqlite_backend_java.m (optional)     same signature through sqlite-jdbc when a JVM is present
  private/ or +cadwell/ package        to keep the EEGLAB path clean
  README.md, LICENSE (Unlicense), CHANGELOG
  tests/                               MATLAB/Octave tests (section 6)
```

Design points:

- `cadwell_read` returns amplifier-unit samples times `UNIT_UV`, in
  amplifier-input order, exactly like `CadwellRecording.read_signals`, so
  the Python package's JSON report can serve as the oracle in tests.
- The frame decoder works per blob so that `ft_read_data` can decode a
  sample range without touching other frames, and so that a long recording
  can be read in chunks.
- The SQLite layer exposes a single function with the table name and an
  optional row filter (needed for `FrameInfo` in multi-file recordings);
  backends are interchangeable behind it.
- Keep the FieldTrip front end free of EEGLAB calls and vice versa, so that
  the same folder can be shipped as an EEGLAB zip and dropped into
  `fieldtrip/fileio/private/` (only `cadwell_ezdata.m` and the library
  files go upstream; the FieldTrip copy could inline the library into one
  file if the maintainers prefer, as `read_nervus_header.m` does).

## 6. Testing strategy (the project's "proven equivalence" carried over)

1. **Oracle data from Python.** A script in `tests/` (or `tools/`) runs
   `cwelleegread` on the public test exports and writes, per export, the
   channel labels, amplifier inputs, samples per frame, start time, gap
   list, event list and the first and last N samples per channel (or a
   SHA-256 of the full float32 array) to JSON. Public exports only; private
   recordings never leave `testdata/private/`.
2. **MATLAB tests** (`runtests` style, `assert`-based so that they also run
   in Octave): SQLite layer against a JSON dump of `FrameInfo` keys and blob
   hashes made with Python's `sqlite3`; frame decoder against the oracle
   samples; header/events/gaps against the oracle metadata; full-file read
   equal to the oracle array within float32 rounding; `pop_cadwell` and
   `cadwell_ezdata` smoke tests (EEGLAB and FieldTrip functions stubbed or
   optional).
3. **CI without MATLAB.** GitHub Actions with `apt-get install octave`
   running the same tests; MATLAB proper on a developer machine (or the
   `matlab-actions/run-tests` action if a licence is available later).
4. **FieldTrip upstream test** (`test/test_cadwell_reading.m`): header
   asserts, a sample comparison against the vendor text export of a
   de-identified recording delivered to the DCCN server, `ft_preprocessing`
   and `ft_databrowser` smoke test, following `test_nicolet_reading.m`.
5. **Doorstop**: add requirements for the MATLAB reader (proposed: REQ021
   "MATLAB/Octave reader equivalent to the Python decoder", REQ022 "EEGLAB
   plugin dataset contents", REQ023 "FieldTrip reader contract and
   autodetection") with tests TST016-TST018, linked to NEED006 and NEED003.

## 7. Work plan and estimates

| Phase | Deliverable | Estimate |
|---|---|---|
| 1. SQLite layer | `sqlite_table_read.m` ported from the Python prototype, UTF-16 text, overflow chains, WAL detection with a clear error; timed on export 2 in MATLAB and Octave; tests vs Python `sqlite3` dumps | 2-3 days |
| 2. Cadwell decoding | `cadwell_read`, `cadwell_decode_frame`, `cadwell_labels`; equal to the oracle on the three public exports | 2-3 days |
| 3. EEGLAB front end | `pop_cadwell` complete (options, events, boundaries, `EEG.etc`), GUI, history; manual test in EEGLAB; zip built | 2 days |
| 4. FieldTrip front end | `cadwell_ezdata.m` with the 1/2/5-argument contract, range-limited decoding; manual test with `ft_preprocessing` and `ft_databrowser` | 1-2 days |
| 5. Test harness and CI | oracle exporter, MATLAB/Octave tests, GitHub Actions with Octave; Doorstop items and published docs | 2 days |
| 6. Docs and release | READMEs, plugin submission to EEGLAB, version 1.0.0 zip; own repository if wanted | 1 day |
| 7. FieldTrip PR | `ft_filetype` clause, `fileio/private/cadwell_ezdata.m`, `test/test_cadwell_reading.m`, website page, de-identified test data to the maintainers; Linux/macOS run before submitting | 1-2 days plus review turnaround |
| Optional | Java backend via `sqlite-jdbc` (two jars, `usejava('jvm')` guard); Python backend calling `cwelleegread`; long-recording chunked reading and a `'range'` option; label parsing from the `MontageEvent` blobs to replace the headbox table | 1-2 days each |

Total for phases 1-7: roughly 12-16 working days.

## 8. Open questions and risks

1. **Scale constant and labels on other headboxes.** The 0.72998046 µV/unit
   constant is verified for Apollo and Essentia only, and labels come from
   two tables; both remain assumptions for other amplifier types (REQ004).
   The reader should flag inferred labels and unknown headbox types the way
   the Python CLI does.
2. **WAL mode.** Not seen in any export; the reader must detect it and fail
   clearly rather than read stale pages.
3. **Recording length.** Reading a 24-hour study into `EEG.data` needs
   about 2.7 GB of `single` data at 32 channels and 500 Hz before anything
   else; a `'range'` option and FieldTrip's `begsample`/`endsample` handle
   this, and EEGLAB users of long-term monitoring will need the range
   dialog.
4. **MATLAB Java policy.** Java-based backends are on a declining path in
   MATLAB (off by default from R2025a, not bundled from R2026b [W]); the
   report therefore treats Java as optional, and any code that uses it must
   guard with `usejava('jvm')`.
5. **Fileio plugin lag** for the File-IO route in EEGLAB (section 4.4).
6. **Licensing of the FieldTrip copy** (GPL-3 for the contributed file,
   Unlicense here) should be recorded in `docs/research/README.md` when
   the PR is made, in the same way the BioSig decision was recorded.
7. **EEGLAB's own test infrastructure** (`sccn/eeglab_tests`, MATLAB CI on
   R2021b and R2025a with anonymised binary test files) is for core;
   plugins in the manager have no CI at all [V]. Our Octave-based CI is
   therefore ahead of the norm, and a test case could be offered to
   `eeglab_tests` once a de-identified recording exists.
8. **BioSig** still has nothing for `.ezdata`: the `biosig4c++`
   `sopen_cadwell_read.c` stub ends in "unsupported" for EAS, EZ3 and ARC
   and the MATLAB `sopen.m` has no Cadwell branch [V]; the EEGLAB BioSig
   plugin is not a route.

## 9. Sources

- This repository: `docs/research/cadwell-file-format.md`,
  `docs/research/downstream-uses.md` (section C), `cwelleegread/ezdata.py`,
  `cwelleegread/layout.py`, `uses/EEGLAB/`.
- FieldTrip master 7bcde3ff (2026-09-24), read locally by the research
  agent: `fileio/ft_filetype.m`, `ft_read_header.m`, `ft_read_data.m`,
  `ft_read_event.m`, `fileio/private/read_nervus_header.m`,
  `read_nervus_data.m`, `biopac_acq.m`, `sccn_xdf.m`,
  `test/test_nicolet_reading.m`, `external/COPYING`, `external/README`,
  `external/mffmatlabio/mff_path.m`, `.github/CONTRIBUTING.md`; website
  sources `faq/preproc/dataformat/dataformat_own.md`,
  `fileio_dataformat.md`, `development/module/fileio.md`,
  `getting_started/eeg/nicolet.md` (github.com/fieldtrip/website).
- Jan Brogger's pull requests: fieldtrip/fieldtrip #186, #266, #302, #1166,
  #1358 (GitHub pages; the API was blocked so inline review bodies were
  not read).
- EEGLAB develop 8ac485f6 (2026-09-11), read locally by the research
  agent: `eeglab.m` (plugin discovery, `trystrs`/`catchstrs`, menu tags),
  `functions/popfunc/eeg_emptyset.m`, `pop_fileio.m`, `pop_biosig.m`,
  `eeg_insertbound.m`, `pop_chanedit.m`, `functions/adminfunc/eeg_checkset.m`,
  `plugin_getweb.m`, `plugin_install.m`, `plugin_askinstall.m`,
  `functions/sigprocfunc/biosig2eeglab.m`, `biosig2eeglabevent.m`,
  `readlocs.m`, `writeeeg.m`, `.github/ISSUE_TEMPLATE/new-plugin-or-plugin-update.md`,
  `.github/workflows/test.yml`, `eeglab.prj`, `LICENSE`; wiki sources in
  `sccn/sccn.github.io` (`design_plugin.md`, `Contributing_to_EEGLAB.md`,
  `EEGLAB_Extensions.md`, `Running_EEGLAB_on_Octave.md`,
  `Compiled_EEGLAB.md`, `EEGLAB_test_cases.md`); plugins `sccn/bva-io`,
  `sccn/neuroscanio`, `xdf-modules/xdf-EEGLAB`, `arnodelorme/mffmatlabio`;
  `sccn/eeglab_tests`; issues sccn/eeglab #63, #240 (Octave) and #954,
  #964, #965, #970 (recent plugin submissions).
- SQLite access: xerial/sqlite-jdbc README and the 3.53.4.0 jar manifest
  (`Java-Version: 8`, natives for Windows x86/x86_64/aarch64, macOS
  x86_64/aarch64, Linux glibc and musl, FreeBSD) [V]; a-ma72/mksqlite
  README, LICENSE and SourceForge file list; kyamagu/matlab-sqlite3-driver
  (archived); gnu-octave/octave-sqlite README; MATLAB Answers 451624 (BLOB
  not returned by `fetch`), 2179665 (enabling Java in R2025a and newer) and
  the R2026b release highlights (Java no longer included), all via search
  snippets because mathworks.com is blocked; sjqtentacles/sml-sqlite and
  dod-cyber-crime-center/sqlite-dissect as pure-language SQLite parsers.
- Prototypes run here: `tools/sqlite_pure_reader.py` (115 lines, kept in
  the repository; all three exports match `sqlite3`), and a 20-line
  `JdbcTest.java` with sqlite-jdbc 3.53.4.0 under OpenJDK 21 (1922 rows,
  28.5 MB, 0.03 s), kept only in the session transcript under `llm-logs/`.
