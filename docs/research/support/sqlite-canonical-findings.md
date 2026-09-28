> Supporting research note produced 2026-09-28 by an LLM research agent (Claude Code, session `831b87b8-e6bd-4acd-901b-d67180234ee3`, see `llm-logs/`) for `docs/research/eeglab-fieldtrip-cadwell-reader.md`. Claims are tagged [V] verified from source or a primary page, [W] from a web-search snippet or page summary, [I] inferred.

# Is there a SQLite reader in canonical MATLAB or EEGLAB that a Cadwell plugin could reuse?

Date: 2026-09-28. Scratchpad: the session scratchpad (not kept) (clones of eeglab,
brainstorm3, mne-matlab, mffmatlabio, thrynae/sqlite3, a-ma72/mksqlite,
ganadist/sqlite4java sources; BioSig files fetched from SourceForge).

Tags: [V] verified from source or primary page, [W] web-search snippet or page
summary (mathworks.com, sccn.ucsd.edu, eeglab.org, undocumentedmatlab.com and
web.archive.org are all blocked from this container), [I] inferred.

## Summary table

| Source | What exists | BLOB support | Licence | Usable by a public-domain plugin? |
|---|---|---|---|---|
| Base MATLAB, native libs | `bin/<arch>/libsqlite3.so.3` (Linux), `bin\win64\libsqlite3.dll`, plus MathWorks wrapper `libmwsqldb` (used by Simulink services) [W]. No MATLAB-level function, undocumented, no header shipped | n/a (C API only; reachable only via `loadlibrary`/MEX) | SQLite public domain; the wrapper is MathWorks proprietary | No as a pure-M path: needs `loadlibrary` (compiler or per-platform thunk binary) or a MEX, and relies on an undocumented private library that can vanish. Not available in Octave |
| Base MATLAB, Java | `java/jarext/sqlite4java/` (sqlite4java.jar + `libsqlite4java-linux-amd64.so`, `sqlite4java-win32-x64.dll`, `libsqlite4java-osx.jnilib`), bundled about R2013a-R2021a, removed in R2021b [W]. Undocumented | yes: `SQLiteStatement.columnBlob(int)` returns `byte[]`, `columnStream` gives an InputStream [V] | Apache-2.0 (wrapper), SQLite public domain [V] | No for current releases (gone since R2021b; R2025a+ no longer starts Java by default). Only as an optional accelerator on old installs |
| Database Toolbox `sqlite` object (R2016a+) | Native "MATLAB Interface to SQLite": `sqlite`, `fetch`, `sqlread`, `sqlwrite` [W] | No for the native interface: fetch returns only double/int64/char; BLOB unsupported per MATLAB Answers 451624 (2019), 1894625 (2022), 1986264 (2023); no release note R2020a-R2026a found that adds BLOB [W]. BLOB -> `uint8` only via the toolbox's JDBC route [W] | MathWorks, paid toolbox | No (paid toolbox, and no BLOBs on the native path) |
| Database Toolbox, JDBC route | Toolbox "ships with drivers for MySQL, PostgreSQL, SQLite, and DuckDB" [W]; `database(...)` with the SQLite JDBC driver | yes, BLOB fetched as `uint8` [W] | MathWorks toolbox; driver Apache-2.0 | No (toolbox required) |
| FEX 68298 "sqlite3" (Rik Wisselink, github.com/thrynae/sqlite3) | `sqlite3.m` wrapper + MEX from rmartinjak/mex-sqlite3 with SQLite 3.36 amalgamation; prebuilt `mexw32`, `mexw64` (v8.02), `mexa64` (v7.14), `mexmaci64` (v9.03); Octave compiles on the fly [V] | No: `get_column()` returns NULL for `SQLITE_BLOB` ("This returns an error later") [V] | CC BY-NC-SA 4.0 [V] | No (NC licence, no BLOBs, stale ABIs, no maca64) |
| FEX 58433 "Using SQLite databases via objects" (Andreas Martin) | Object wrapper on top of mksqlite [W] | via mksqlite | not verified | Only as far as mksqlite is |
| mksqlite (a-ma72/mksqlite, 2.13+) | MEX; the GitHub repo now carries prebuilt `mksqlite.mexw64/.mexa64/.mexmaci64/.mexmaca64` built against SQLite 3.46.0 (mexa64 needs glibc >= 2.29), last commit 2026-08-14 [V] | yes, BLOB -> `uint8` vector (`typedBLOBs` option) [V] | BSD-2-Clause since v2.9, 2020 [V] | Licence-compatible; but a MEX binary per platform and MATLAB ABI, no Octave, and it is not "canonical" (must be shipped or fetched by the plugin) |
| kyamagu/matlab-sqlite3-driver (FEX 57123) | MEX, build yourself | yes | BSD-3 | No (archived 2020 [W]) |
| EEGLAB core + bundled plugins (commit 8ac485f, 2026-09-11) | zero occurrences of `sqlite`, `mksqlite`, `jdbc`, `SQLite format 3` or `.db` in `functions/` and `plugins/` (EEG-BIDS, ICLabel, clean_rawdata, dipfit, firfilt) [V] | none | GPL-2/BSD-3 (EEGLAB) | Nothing to reuse |
| EEGLAB plugin manager list | Not reachable (sccn.ucsd.edu blocked). Compiled-in plugin list in `eeglab.m` and web snippets show no plugin that reads SQLite-based files [V]/[W]; the vendor importers (Nihon Kohden .m00 text, Muse CSV, xdf, MFF, BrainVision, Neuroscan, EEProbe, Snapmaster, EGI legacy) all read non-SQLite formats [I] | none | various | Nothing to reuse |
| BIOSIG (biosig4c++ `t210/sopen_sqlite.c`, 2021) | Optional build with `-DWITH_SQLITE3 -lsqlite3` (system libsqlite3); detects Cadwell by the table set, dumps rows at high verbosity, then errors "Format SQLite: not supported yet." Autoconf check for sqlite3 is commented out, so default builds have no SQLite [V]. `biosig4matlab/sopen.m` has no SQLite branch [V] | via libsqlite3 (`sqlite3_column_blob`) only in the debug dump [V] | GPL-3 | No (GPL, and a stub) |
| FieldTrip `external/` / MFF jar (`MFF-1.2.2-jar-with-dependencies.jar`, mffmatlabio) | No `sqlite` string in the jar listing; it bundles Apache Derby, mysql-connector, jopt-simple, jargs [V] | n/a | Apache/MIT mix | Nothing to reuse |
| Brainstorm (brainstorm3 c1d5957, 2026-09-15) | No SQLite reader; only a commented-out check for a future `protocol.db` in `toolbox/db/db_load_protocol.m`; readers for Nicolet/Micromed/EDF/EEProbe etc. are binary-format parsers; no jar or MEX touching SQLite [V] | none | GPL-3 | Nothing to reuse |
| MNE-MATLAB | FIFF only, no SQLite [V] | none | BSD | Nothing to reuse |

**Bottom line**: there is no documented, redistributable, BLOB-capable SQLite
reader in base MATLAB, in any MathWorks toolbox usable without a paid licence,
in EEGLAB core, in the EEGLAB plugins we could inspect, in BioSig's MATLAB
side, in FieldTrip, Brainstorm or MNE-MATLAB. The closest "canonical" items
are (a) an undocumented `libsqlite3` shared library inside `matlabroot/bin`
(no MATLAB API, no header, may move or disappear) and (b) sqlite4java, which
MathWorks shipped for about eight years and dropped in R2021b. Neither
changes the conclusion of the existing research note: a pure MATLAB/Octave
table-b-tree reader (option G) remains the only dependency-free path, with
mksqlite (BSD-2, now with four prebuilt MEX binaries in its GitHub repo) or
sqlite-jdbc as optional accelerators.

## 1. Base MATLAB (no toolbox)

### 1a. Native SQLite library in the installation [W]

- Several MATLAB Answers threads about `Can't reload .../bin/glnxa64/...`
  print `ldd`-style dependency chains that include
  `/usr/local/MATLAB/R2018a/bin/glnxa64/./libsqlite3.so.3` and, in the
  R2014b case, `libsqlite3.so.3.8.5`, alongside `libmwsqldb.so` and
  `libmwsl_services.so` (Simulink services) [W]:
  - https://www.mathworks.com/matlabcentral/answers/506092-can-t-reload-usr-local-matlab-r2018a-bin-glnxa64-libmwdastudio-so
  - https://www.mathworks.com/matlabcentral/answers/395831-can-t-reload-home-x-programs-matlab-bin-glnxa64-libmwcoder_types-so-when-running-findpeaks
  - https://www.mathworks.com/matlabcentral/answers/361053-can-t-reload-usr-local-matlab-r2017b-bin-glnxa64-libmwdastudio-so
  - A public directory index of a MATLAB `bin/glnxa64` (app.sibcb.ac.cn,
    403 from this container) is reported by the search engine to list
    `libsqlite3.so.3.8.5` and `libmwsqldb.so` [W].
- Windows: DLL-catalogue sites list `libsqlite3.dll` in
  `C:\Program Files\MATLAB\R2019b\bin\win64\` and attribute it to MathWorks
  since R2009a [W, low-quality sources: exefiles.com, dll-files.com].
- `libmwsqldb` is described (snippet) as a MathWorks library exposing a
  `SqlDatabaseInterface` class and appearing in Simulink crash logs
  (R2014a-R2018a) [W]. The owner is therefore MATLAB/Simulink internals
  (probably the Simulink Data Dictionary and project metadata; Undocumented
  Matlab only speculates that `.sldd` is "an embedded database along the
  lines of SQLite") [W]/[I]. It is not a Database Toolbox artefact: the
  threads above come from machines running signal-processing or image
  functions, not database code [I].
- No evidence for current releases (R2023-R2026) either way: searches for
  `R2024 bin/glnxa64/libsqlite3` return nothing [W]. Given that `libmwsqldb`
  is a MathWorks core library, the SQLite library is most likely still
  present, but that is an inference [I].
- No public MATLAB API wraps it. Reaching it would need `loadlibrary`
  (which requires a C compiler on 64-bit to build the thunk, or shipping a
  pre-generated prototype `.m` plus a `*_thunk_<arch>` binary per platform,
  per MathWorks docs and Answers 32271/140020/297503 [W]) or a MEX file that
  links against it. Both are binaries again, undocumented, absent in
  Octave, and would break if MathWorks renames or hides the library.
  Verdict: not a reuse path.

### 1b. Undocumented Java: sqlite4java [W]/[V]

- Yair Altman, "Using SQLite in Matlab" (undocumentedmatlab.com, blocked; all
  facts below are from search snippets of that article and its comments):
  sqlite4java by ALM Works "is bundled with Matlab for the past several
  years (in the %matlabroot%/java/jarext/sqlite4java/ folder)"; MathWorks
  "has never created a documented wrapper function" for it; and, from a
  later comment, "Matlab stopped including sqlite4java in R2021b (it was
  still included in 21a)" [W].
  https://undocumentedmatlab.com/articles/using-sqlite-in-matlab
- Independent confirmation that the jar and native library are loaded by
  MATLAB itself at startup: "Java error on starting MATLAB R2013a"
  (Answers 80942) and "Java error when opening fig files" (Answers 164527)
  show `libsqlite4java` being loaded from
  `/Applications/MATLAB_R2013a.app/java/jarext/sqlite4java/` on macOS, and a
  QuickFIX/J demo lists `C:\Program Files\MATLAB\R2014b\java\jarext\sqlite4java\sqlite4java.jar`
  on the static class path [W]. So the owner is base MATLAB (it is on the
  static Java class path of a plain installation), not a toolbox [I].
- Native library file names (snippet): `libsqlite4java-osx.jnilib`,
  `libsqlite4java-linux-amd64.so`, `sqlite4java-win32-x64.dll` [W].
- API verified in the sqlite4java source (ganadist/sqlite4java mirror of the
  ALM Works repo) [V]:
  `public byte[] columnBlob(int column)` (SQLiteStatement.java:1028),
  `public InputStream columnStream(int column)` (:1055),
  `public Object columnValue(int column)` (:1127); the native library is
  located via the `sqlite4java.library.path` system property or
  `System.loadLibrary` (Internal.java:97-356). Licence Apache-2.0; bundled
  SQLite public domain [V, README].
  https://github.com/ganadist/sqlite4java
- MathWorks' third-party licence PDF for MATLAB Mobile lists sqlite4java
  [W]; the desktop `thirdpartylicenseagreementsR20xx.pdf` files are on
  mathworks.com and could not be read.
- Verdict: the one thing MathWorks ever shipped that returns BLOBs byte-exact
  from plain MATLAB without a toolbox, but it has been gone for five
  release years (R2021b-R2026b), and R2025a+ does not start the JVM by
  default. Only worth a `try` block for users on R2016a-R2021a [I].

### 1c. Other base-MATLAB entry points

- `sqlread`, `sqlwrite`, `fetch`, `sqlite`, `databaseDatastore` are all
  Database Toolbox functions (their doc URLs are under `/help/database/`)
  [W]. Base `matlab.io.datastore` has file datastores only; no SQLite
  datastore without the toolbox [I, consistent with the doc tree].
- No hit for `matlab.internal.*sqlite*`, `matlab.io.internal.sqlite`,
  `sqlitemex` or `libmwsqlite` in any search [W, negative]. The internal
  wrapper that exists is `libmwsqldb`, a C++ library, not an M-package.
- `py.sqlite3` (R2014b+) works only when a compatible CPython is installed
  (already covered as option F in the existing note).

## 2. Database Toolbox `sqlite` object

- Introduced: "MATLAB Interface to SQLite" in R2016a ("Since MATLAB version
  2016a there is a sqlite(...) function", mksqlite README [V]; Database
  Toolbox release notes and doc URLs `/help/database/ug/sqlite.html` [W]).
  It is a Database Toolbox feature; the toolbox "ships with drivers for
  MySQL, PostgreSQL, SQLite, and DuckDB" [W, product page snippet]. Without
  the toolbox, `sqlite` is simply undefined.
- BLOB status of the native interface, chronologically [W]:
  - 2019, Answers 451624 "how to fetch splite3 blob data": "The sqlite() and
    fetch() function only works for one of these data types: double, int64,
    or char, but not for blob binary data chunk"; workaround is the JDBC
    driver.
  - 2020b docs mirror snippet: "The MATLAB interface to SQLite has
    limitations, supporting only DOUBLE, INT64, and CHAR data types".
  - R2022a release note: `fetch` now returns a table instead of a cell
    array (behaviour change only; nothing about BLOB).
  - 2022, Answers 1894625 "Converting Blob from an sqlite file to image":
    same limitation restated; the answers use JDBC (`uint8` result).
  - 2023, Answers 1986264 "write a blob inside a cell of sqlite database":
    "MATLAB doesn't consist methods for BLOB data processing with its
    standard functions ... sqlwrite() and fetch() ... do not support BLOB";
    recommendations are JDBC or mksqlite.
  - Searches of the Database Toolbox release notes for R2023a-R2026a with
    "SQLite" + "BLOB"/"uint8" return no new-feature item [W, negative].
    The release-notes page itself is blocked, so a quiet change cannot be
    excluded; treat as "no evidence of BLOB support through R2026a".
  https://www.mathworks.com/matlabcentral/answers/451624-how-to-fetch-splite3-blob-data
  https://www.mathworks.com/matlabcentral/answers/1894625-converting-blob-from-an-sqlite-file-to-image
  https://www.mathworks.com/matlabcentral/answers/1986264-write-a-blob-inside-a-cell-of-sqlite-database
  https://www.mathworks.com/help/database/release-notes.html
- JDBC route inside the toolbox: "when you fetch a BLOB you will always get
  your result as byte array of type uint8" (Answers 243412, 94080) [W].
  So a Database Toolbox user can read Cadwell frames, but only through the
  toolbox's JDBC path, not the `sqlite` object.
- Verdict unchanged from the existing note: unusable as the plugin's
  primary path (paid toolbox; native path has no BLOBs).

## 3. File Exchange and other add-ons

### FEX 68298 "sqlite3" (Rik Wisselink-Bal, github.com/thrynae/sqlite3) [V]

- Wrapper `sqlite3.m` (275 kB) around a MEX derived from
  rmartinjak/mex-sqlite3 plus SQLite 3.36.0 amalgamation; ships
  `sqlite3_mex_v3.1.0/`: `sqlite3_MATLAB_v06_05_PCWIN.dll`,
  `..._v07_01_PCWIN.mexw32`, `..._v07_14_GLNXA64.mexa64`,
  `..._v08_02_PCWIN64.mexw64`, `..._v09_03_MACI64.mexmaci64`; Octave
  downloads and compiles the sources.
- BLOB: `sqlite3_interface_strict.c` `get_column()`:
  `else if (type == SQLITE_BLOB) { /* This returns an error later. */ return NULL; }`.
  The M-file lists supported types as double, single, char, logical and
  integers only. So no BLOB reading at all.
- Licence: README says "Licence: CC by-nc-sa 4.0" (non-commercial,
  share-alike) - incompatible with an Unlicense plugin and with clinical
  use.
  https://github.com/thrynae/sqlite3 ,
  https://www.mathworks.com/matlabcentral/fileexchange/68298-sqlite3

### FEX 58433 "Using SQLite databases via objects" (Andreas Martin) [W]

- Object-oriented wrapper by the mksqlite author on top of mksqlite; licence
  not visible in snippets. Adds nothing beyond mksqlite.
  https://www.mathworks.com/matlabcentral/fileexchange/58433-using-sqlite-databases-via-objects

### mksqlite (a-ma72/mksqlite) [V] - update to the existing note

- The existing note said SourceForge only offers win64 zips. That is still
  true for SourceForge (`mksqlite-2.11-win64.zip`, 2021-02-02 and older
  1.x zips) [V], but the GitHub repository itself now contains prebuilt
  `mksqlite.mexw64` (1.9 MB), `mksqlite.mexa64` (3.9 MB, needs glibc
  >= 2.29, links libmex/libmx/libut only), `mksqlite.mexmaci64` (3.6 MB) and
  `mksqlite.mexmaca64` (1.5 MB), embedding SQLite 3.46.0; last commit
  b43c43b, 2026-08-14 [V]. README: tested "R13SP1 .. R2024b"; macOS build
  instructions via CMake [V].
- BLOB: "Non-scalar values are treated as a BLOB (uint8)"; "BLOBs are always
  stored as a vector of uint8 values"; optional `typedBLOBs` [V,
  mksqlite_en.m]. Byte-exact `uint8` is exactly what the Cadwell reader
  needs.
- Licence: BSD-2-Clause (LICENSE, Copyright 2024 Andreas Martin; changed
  from earlier licence in v2.9, 2020) [V].
- Still not canonical: the plugin would redistribute four MEX files (or
  download them at install time), and Octave is not supported. It is,
  however, the least painful binary accelerator, now that all four MATLAB
  platforms are prebuilt upstream.
  https://github.com/a-ma72/mksqlite , https://sourceforge.net/projects/mksqlite/files/

### kyamagu/matlab-sqlite3-driver (FEX 57123)

- BSD-3, compile yourself, repository archived (GitHub page returns 403
  here; archive status from the existing note) [W]. Not an option.

### MathWorks-authored SQLite add-ons

- None found. Searches for "SQLite for MATLAB" by MathWorks staff or a
  `matlab-sqlite` GitHub project return only the Database Toolbox pages
  [W, negative].

## 4. EEGLAB

### Core and bundled plugins [V]

- Shallow clone of sccn/eeglab at 8ac485f654d6 (2026-09-11) with submodules
  EEG-BIDS, ICLabel (+matconvnet, viewprops), clean_rawdata (+manopt),
  dipfit, firfilt.
- `grep -rIl -E "sqlite|mksqlite|jdbc"` over the whole tree: 0 files.
  `SQLite format 3`: 0. `'.db'`/`*.db`: 0. The only binaries are JSONio and
  matconvnet MEX files.
- `eeglab.m` lines 940-1010 (plugins linked into the compiled EEGLAB):
  eepimport, iclabel, VisEd, eegbids, bva_io, clean_rawdata, dipfit,
  egilegacy, firfilt, iirfilt, musedirect, musemonitor, neuroscanio, scd,
  snapmaster, xdfimport, mffmatlabio. None of these formats is SQLite-based
  (Muse Direct/Monitor export CSV; xdf is a chunked binary; MFF is XML +
  binary; the rest are vendor binary/text formats) [I].
- `functions/adminfunc/plugin_getweb.m` fetches the plugin list from
  `http://sccn.ucsd.edu/eeglab/plugin_uploader/plugin_getcountall_nowiki_json.php`
  [V]; that host is blocked here, so the full manager list could not be
  read.

### Plugin manager list, via search [W]/[I]

- Searches "eeglab plugin sqlite", "eegplugin_ sqlite", "eeglab plugin .db
  import" and site:eeglab.org queries surface no plugin that opens a
  SQLite file. Hits are eegDb (a preprocessing bookkeeping plugin, not a
  file importer), SMimport (SM format), xdf-EEGLAB, Mentalab, nwbio,
  bidslab [W].
- Vendor importers named in the task and their on-disk formats: Nihon
  Kohden plugin reads `.m00` text exports (EEGLAB Extensions page) [W];
  Persyst (`.lay`+`.dat`), NeuroOne (XML + binary), Natus/Nicolet (`.e`,
  read by FieldTrip's Nervus reader), Neuroelectrics `.easy`/`.nedf`
  (text/binary), OpenBCI (text), Emotiv (EDF/CSV), Brain Products
  (`.vhdr/.vmrk/.eeg`), CountingSheepPSG and SleepTrip (scoring tools, not
  importers) - none SQLite [I, from format knowledge; not re-verified
  here]. No Cadwell importer exists for EEGLAB [W, negative search].

### BIOSIG [V]

- `biosig4c++/t210/sopen_sqlite.c` (Copyright 2021 Alois Schloegl, GPL),
  fetched from SourceForge master:
  - `#ifdef WITH_SQLITE3 / #include <sqlite3.h>`; `Makefile.in` line 280-282:
    `ifeq (1,@HAVE_SQLITE3@) DEFINES += -DWITH_SQLITE3=1 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION; LDLIBS += -lsqlite3`
    - it links the system libsqlite3, it does not embed a parser.
  - `configure.ac` line 28: `# AC_CHECK_LIB([sqlite3], [sqlite3_open], AC_SUBST(HAVE_SQLITE3, "1") )`
    is commented out, so a default build has `HAVE_SQLITE3` unset and hits
    the `#else` branch: "SOPEN(SQLite): - sqlite format not supported -
    libbiosig need to be recompiled with libsqlite3 support."
  - With SQLite enabled it opens the file with `sqlite3_open`, runs
    `SELECT COUNT(*) ... FROM FrameInfo; MiscInfo; TrackInfoSyncRowData;
    MaxUpdateTick; MiscInfoSyncRowData; syncrowdata; MediaHeader;
    SchemaUpdateLog; synctable; MediaHeaderSyncRowData; TrackInfo` to decide
    "most likely a Cadwell file", then for each table prepares
    `SELECT * FROM <table>` and, only when `VERBOSE_LEVEL>7/8`, prints up to
    10 rows, hex-dumping `sqlite3_column_blob()` output. It never fills the
    header or data; it ends with
    `biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format SQLite: not supported yet.")`
    and a TODO list ("fill in HDRstruct* hdr", "extract data samples").
  - `biosig.c` line 2053 detects the type from the 16-byte magic
    `SQLite format 3\0` plus header bytes 21-23 == 64,32,32 and sets
    `hdr->TYPE = SQLite`.
- `biosig4matlab/t200_FileAccess/sopen.m` (10 909 lines): no occurrence of
  `sqlite` or `jdbc` [V]. The EEGLAB Biosig plugin therefore has nothing for
  SQLite files on the MATLAB side either.
- Verdict: a GPL stub that would, if ever completed, depend on libsqlite3;
  nothing reusable, and licence-incompatible anyway.

## 5. FieldTrip external jars (MFF) [V]

- `MFF-1.2.2-jar-with-dependencies.jar` from arnodelorme/mffmatlabio
  (4.6 MB): `unzip -l | grep -i sqlite` -> 0 entries. Top-level packages:
  `com/egi`, `com/mysql` (MySQL Connector/J), `org/apache/derby` (Apache
  Derby embedded DB, incl. `EmbedBlob.class`), `jargs`, `joptsimple`. No
  SQLite engine and no JDBC driver for SQLite hides in it.

## 6. Brainstorm and MNE-MATLAB [V]

- brainstorm3 (c1d5957c, 2026-09-15): `grep -rIil "sqlite|mksqlite|jdbc"`
  -> nothing. `grep -i sql` -> `toolbox/db/db_load_protocol.m` lines 49-61,
  a commented-out block checking for a future `protocol.db` next to
  `protocol.mat` ("This protocol seems to have been created with a newer
  version of the software"), and a changelog line about the website's MySQL
  log table. `in_fopen.m` dispatches Nicolet `.e`, Micromed `.trc`, EDF,
  BrainVision, EEProbe, Plexon etc. to hand-written binary parsers; the
  only `.db` string is `'Curry BEM (*.db*;*.s0*)'`, a Curry geometry file.
  Java: only `java/RiverLayout.jar`. MEX: bst_meanvar, direct_pac_mex,
  eeprobe, plexon, spm - none SQLite.
- mne-matlab: `matlab/fiff_*.m` only; no SQLite, no Java.

## What this means for the Cadwell plugin

1. Nothing "canonical" can be relied on in R2021b-R2026b MATLAB without a
   toolbox: the only in-box SQLite code paths are an undocumented private
   C library (`libsqlite3` behind `libmwsqldb`) and, until R2021a, an
   undocumented Java jar. The Database Toolbox's own documented SQLite
   object still cannot return BLOBs, and its JDBC path needs the toolbox.
2. EEGLAB (core, bundled plugins, compiled plugin set, Biosig plugin),
   FieldTrip, Brainstorm and MNE-MATLAB contain no SQLite reader at all,
   so a Cadwell plugin would be the first one in that ecosystem.
3. Consequently the plan in `docs/research/eeglab-fieldtrip-cadwell-reader.md`
   stands: ship the pure MATLAB/Octave b-tree reader (option G) as the
   primary path. Two refinements from this pass:
   - mksqlite is a better optional accelerator than the note assumed:
     BSD-2, BLOB -> uint8, and its GitHub repo now includes prebuilt MEX
     files for win64, glnxa64, maci64 and maca64 (SQLite 3.46.0) [V].
   - sqlite4java can be probed with `exist('com.almworks.sqlite4java.SQLiteConnection','class')`
     on R2016a-R2021a installs, but it is not worth code; the JDBC path
     already covers Java-capable installs.
4. BioSig's `sopen_sqlite.c` confirms independently that the vendor's
   table set (`FrameInfo`, `TrackInfo`, `MediaHeader`, ...) is the right
   fingerprint for `.ezdata`, but it must not be copied (GPL).

## Sources (URLs)

- https://undocumentedmatlab.com/articles/using-sqlite-in-matlab (blocked; snippets)
- https://www.mathworks.com/matlabcentral/answers/80942-java-error-on-starting-matlab-r2013a
- https://www.mathworks.com/matlabcentral/answers/164527-java-error-when-opening-fig-files
- https://github.com/ganadist/sqlite4java (SQLiteStatement.java, Internal.java, README)
- https://www.mathworks.com/matlabcentral/answers/506092-can-t-reload-usr-local-matlab-r2018a-bin-glnxa64-libmwdastudio-so
- https://www.mathworks.com/matlabcentral/answers/395831-can-t-reload-home-x-programs-matlab-bin-glnxa64-libmwcoder_types-so-when-running-findpeaks
- http://app.sibcb.ac.cn/data1/service/workflow/test1/package/matlab/bin/glnxa64/ (403 here)
- https://www.mathworks.com/matlabcentral/answers/451624-how-to-fetch-splite3-blob-data
- https://www.mathworks.com/matlabcentral/answers/1894625-converting-blob-from-an-sqlite-file-to-image
- https://www.mathworks.com/matlabcentral/answers/1986264-write-a-blob-inside-a-cell-of-sqlite-database
- https://www.mathworks.com/matlabcentral/answers/243412-blob-and-clob-using-sql-query
- https://www.mathworks.com/help/database/release-notes.html (blocked)
- https://www.mathworks.com/help/database/ug/sqlite.fetch.html (blocked)
- https://www.mathworks.com/matlabcentral/answers/32271-possible-to-distribute-shared-dll-without-requiring-end-users-to-have-c-compiler
- https://github.com/thrynae/sqlite3 ; https://www.mathworks.com/matlabcentral/fileexchange/68298-sqlite3
- https://www.mathworks.com/matlabcentral/fileexchange/58433-using-sqlite-databases-via-objects
- https://github.com/a-ma72/mksqlite ; https://sourceforge.net/projects/mksqlite/files/
- https://github.com/kyamagu/matlab-sqlite3-driver
- https://github.com/sccn/eeglab (8ac485f6) and submodules
- https://eeglab.org/others/EEGLAB_Extensions.html ; https://eeglab.org/plugins/ (blocked)
- https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4c%2B%2B/t210/sopen_sqlite.c
- https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4c%2B%2B/Makefile.in
- https://sourceforge.net/p/biosig/code/ci/master/tree/configure.ac
- https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4matlab/t200_FileAccess/sopen.m
- https://github.com/arnodelorme/mffmatlabio (MFF-1.2.2-jar-with-dependencies.jar)
- https://github.com/brainstorm-tools/brainstorm3 (c1d5957c)
- https://github.com/mne-tools/mne-matlab
