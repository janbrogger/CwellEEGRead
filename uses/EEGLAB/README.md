# uses/EEGLAB - EEGLAB import plugin for Cadwell EEG (and FieldTrip notes)

**Status:** working, ready to submit to the EEGLAB plugin list. The plugin
`cadwellio` reads a Cadwell Arc CadLink study export directly with plain
MATLAB/Octave code (own SQLite file reader, frame decoder ported from
`cwelleegread/ezdata.py`) and can also load the EDF produced by
CwellEEGRead through the BIOSIG or File-IO plugin. `pop_cadwell` returns a
dataset whose samples equal the Python reader's bit for bit and the
vendor's text export within 0.05 µV (`cadwellio/cadwell_selftest.m`,
run by `tests/test_octave_port.py` under GNU Octave).

What has been verified, and where:

| Check | How |
|---|---|
| decoder, index, events, samples, every SQLite table | `cadwell_selftest` against Python reference dumps, all three public exports |
| dataset structure accepted by EEGLAB | `pop_cadwell` run under Octave 8.4 with EEGLAB's own `functions/` (git `develop`) and dipfit on the path: `eeg_checkset` passes, `pop_saveset`/`pop_loadset` round trip keeps samples and events (`tests/test_eeglab_import.py`, runs when `EEGLAB_DIR` points at an EEGLAB checkout) |
| recording pauses | export 3 (10 s pause): padded read has zeros and a `Recording gap` event at the pause; concatenated read is 5000 samples shorter with a `boundary` event and the later events moved up (self-test check E) |
| the EEGLAB GUI menu item | **not yet**: no MATLAB or EEGLAB GUI in the development container; `eegplugin_cadwellio.m` follows the documented template (`sccn.github.io` tutorials/contribute/design_plugin.md) |

**Recording pauses.** Cadwell numbers frames by the second since the record
origin, so a pause (the vendor's *Stop Recording* / *Start Recording*)
leaves missing frame numbers, confirmed by a `GapInfo` row. With
`'padgaps','on'` (default) the pause is filled with zeros so latencies stay
aligned with wall-clock time and an event of type `Recording gap` with the
pause length in `duration` marks it. With `'padgaps','off'` the segments are
concatenated, the pause becomes a standard EEGLAB `boundary` event
(latency at the join minus 0.5, `duration` = samples removed, as
`eeg_eegrej` writes them, so filtering and epoching respect the
discontinuity) and the latencies of all later events move up by the pause
length; the vendor's own events stamped inside the pause land on the join.
Both modes list the pauses in `EEG.etc.cadwell.gaps` (`startSample`,
`seconds`, `startSec` since the first frame, `padded`). The same rule
applies in the Python converter (REQ019: zeros plus an EDF+ annotation).

**Submitting to the EEGLAB plugin list.** EEGLAB's plugin manager fetches a
zip whose root (or single top-level folder) holds `eegplugin_cadwellio.m`;
the folder name and the `vers` string returned by `eegplugin_cadwellio`
must match (`cadwellio0.2.0`). Steps:

1. `./make_zip.sh` -> `dist/cadwellio0.2.0.zip` (pure MATLAB/Octave; no jar).
2. Test once in a real MATLAB + EEGLAB: unzip into `<eeglab>/plugins/`,
   start EEGLAB, check that *File > Import data > From Cadwell* appears and
   imports a public test export, and that the history command it writes
   replays. This is the one step the container cannot do.
3. Submit with the upload form http://sccn.ucsd.edu/eeglab/plugin_uploader/upload_form.php
   (name `cadwellio`, version `0.2.0`, the zip, a one-paragraph description,
   the GitHub URL, licence Unlicense) or, as recently recommended, open an
   issue on https://github.com/sccn/eeglab with the zip attached. Later
   versions go through http://sccn.ucsd.edu/eeglab/plugin_uploader/version_update.php.

**Prerequisites**

- MATLAB R2016b or newer, or GNU Octave 6 or newer, with EEGLAB 2021 or newer.
  The direct `.ezdataindex` reader needs no toolbox, MEX, Java or Python.
- For the EDF path only: the EEGLAB BIOSIG plugin (`pop_biosig`) or File-IO
  plugin (`pop_fileio`), installed through the EEGLAB plugin manager.

**Files**

| File | Purpose |
|---|---|
| `cadwellio/eegplugin_cadwellio.m` | plugin entry point (version `cadwellio0.2.0`): adds *File > Import data > From Cadwell (.ezdataindex / converted EDF)* |
| `cadwellio/pop_cadwell.m` | importer; GUI when called without arguments, returns `[EEG, com]` |
| `cadwellio/cadwell_read.m`, `cadwell_read_index.m`, `cadwell_read_events.m`, `cadwell_decode_frame.m` | the native reader (port of `cwelleegread/ezdata.py`) |
| `cadwellio/cadwell_sqlite_native.m`, `cadwell_tcol.m` | pure MATLAB/Octave reader of the SQLite 3 file format (default backend), column helper |
| `cadwellio/cadwell_sqlite.m`, `cadwell_get_jdbc.m` | backend switch (`native` default; mksqlite / Database Toolbox / JDBC / py.sqlite3 for cross-checks); JDBC driver download |
| `cadwellio/cadwell_layout.m` | per-headbox channel labels (port of `cwelleegread/layout.py`) |
| `cadwellio/cadwell_selftest.m`, `tools/make_matlab_reference.py`, `tests/test_octave_port.py` | verification of the port against the Python decoder and the vendor text export |
| `cadwellio/README.md`, `cadwellio/LICENSE` | shipped inside the zip |
| `make_zip.sh` | builds `cadwellio<version>.zip` for manual install or submission to the EEGLAB plugin list |

**Build and install**

```bash
./make_zip.sh            # -> dist/cadwellio0.2.0.zip (pure MATLAB/Octave; --with-jdbc bundles the optional driver)
# then: unzip into <eeglab>/plugins/ and restart EEGLAB, or submit it
# through the sccn/eeglab issue template "New plugin or plugin update"
# (the old web upload form is closed)
```

**Design note**: the readers ask the SQLite layer for whole tables
(`cadwell_sqlite('table', db, name)`) and do their filtering and sorting in
MATLAB, so the default backend can be a plain-MATLAB parser of the SQLite
file format with no SQL engine (`cadwell_sqlite_native.m`, about 200 lines:
page b-trees, record serial types, overflow chains, UTF-16). The library
backends implement the same `table` call through `SELECT rowid, *` and exist
to cross-check the native reader; `cadwell_selftest` runs every check
through every available backend and compares the native reader's dump of
every table of every test file byte for byte with Python's sqlite3. The
decoder works on plain `uint8` blobs so it can be tested without any
database at all.

**FieldTrip**: the cheapest route is a function `cadwell_sqlite.m` on the
path implementing the three call forms `hdr = f(file)`,
`dat = f(file, hdr, begsample, endsample, chanindx)`, `evt = f(file, hdr)`
and passing `'headerformat','cadwell_sqlite'` (and data/event) to
`ft_read_header/data/event`; upstreaming later means a `ft_filetype` clause
and `case 'cadwell_sqlite'` in the three readers. See
`docs/research/downstream-uses.md`, section C2.
