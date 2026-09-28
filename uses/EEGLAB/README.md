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

**Event timing: two clocks.** Every Cadwell event carries a wall-clock
stamp and a sample-clock offset, and the two clocks drift: on the Essentia
recordings the stamp clock runs 96 ppm behind the amplifier's sample
clock, 0.35 s per hour. The vendor's EDF export places events by stamp,
which puts them *early* by the accumulated drift (96 ms at 17 minutes in
export 3); the photic flash response then appears 200 ms or more after the
marker instead of the 100–130 ms of a flash VEP. `pop_cadwell` therefore
places events by their sample-clock offset (`'eventtiming','ticks'`, the
default; `'stamp'` reproduces the vendor). The converter does the same
(`--event-timing`, REQ021). Details and measurements:
`docs/research/cadwell-file-format.md`, "Two clocks".

**Where the vendor's Stop/Start Recording events sit relative to the data.**
The pause markers of the plugin come from the frame numbering, not from
the vendor's `RecordingOnOff` events, because the two do not coincide. The
events are stamped when the button was pressed; the stored data start and
end on whole seconds of the amplifier clock, and some data around each
press is never stored. Measured on the three public exports (frame *k*
holds amplifier-clock second *k*; the event offsets are the events'
`StartOffset` ticks on the same clock):

| Export | Event | Event offset | Nearest stored sample | Data missing |
|---|---|---|---|---|
| 1 (frames 0–44) | Start Recording | −0.008 s | frame 0 starts at 0 s | 0.008 s |
| 1 | Stop Recording | 46.06 s | frame 44 ends at 45 s | 1.06 s before the stop |
| 2 (frames 1–961) | Start Recording | −0.001 s | frame 1 starts at 1 s | 1.00 s after the start |
| 2 | Stop Recording | 962.52 s | frame 961 ends at 962 s | 0.52 s before the stop |
| 3 (frames 1–327, 338–1217) | Start Recording | −0.001 s | frame 1 starts at 1 s | 1.00 s after the start |
| 3, pause | Stop Recording | 329.97 s | frame 327 ends at 328 s | 1.97 s before the stop |
| 3, pause | Start Recording | 337.19 s | frame 338 starts at 338 s | 0.81 s after the start |
| 3 | Stop Recording | 1218.90 s | frame 1217 ends at 1218 s | 0.90 s before the stop |

So in every case the data begin at the first whole amplifier-clock second
after Start Recording (the partial second is dropped; in exports 2 and 3
the whole of second 0 is missing, apparently because the frame in progress
when the button was pressed is discarded together with the partial one) and
end at a whole second between 0.5 and 2 s before Stop Recording (the
partial last second, plus in some cases one complete frame, is discarded).
The vendor's own EDF export shows exactly the same placement: in export 3
its zero-filled run covers record seconds 327–337 while its *Stop Recording*
annotation is 1.94 s into the zeros and *Start Recording* 0.84 s before
the data resume (the *Impedance* event of 7.06 s lies inside the pause).
Consequences for users:

- Do not use the `Stop Recording` / `Start Recording` events to find where
  the data stop and resume; use the `Recording gap` / `boundary` events
  (or `EEG.etc.cadwell.gaps`), which are placed from the frame numbers and
  agree with the vendor's `GapInfo` rows to the millisecond.
- With `'padgaps','on'` the vendor's Stop and Start events lie *inside* the
  zero-filled pause, as in the vendor's EDF. With `'padgaps','off'` they
  are moved onto the join, together with anything else stamped during the
  pause (for export 3: Stop Recording, Impedance, Start Recording, all at
  the boundary latency).
- Up to about 2 s of EEG before each stop and 1 s after each start are not
  in the export at all, so an event stamped in that window (a button press
  right before stopping) has no data under it. The Python converter reports
  the same figures (`inspect --json`, `gaps` and `events`).

**Submitting to the EEGLAB plugin list.** The upload forms that the
tutorial page still links are closed ("for security reasons", says the
sccn/eeglab issue template). Submission is a GitHub issue on
https://github.com/sccn/eeglab using the template *New plugin or plugin
update*, which asks for plugin name, current version, new version, a
description, and the zip dragged into the issue (or linked as a GitHub
release archive). The plugin manager then serves the zip from SCCN's
server; the folder name inside the zip and the `vers` string returned by
`eegplugin_cadwellio` must match (`cadwellio0.2.0`). Survey of how the 177
listed plugins are hosted and released: `docs/research/eeglab-plugin-list-survey.md`.
Steps:

1. `./make_zip.sh` -> `dist/cadwellio0.2.0.zip` (pure MATLAB/Octave; no jar).
2. Test once in a real MATLAB + EEGLAB: unzip into `<eeglab>/plugins/`,
   start EEGLAB, check that *File > Import data > From Cadwell* appears and
   imports a public test export, and that the history command it writes
   replays. This is the one step the container cannot do.
3. Tag a release (`cadwellio-0.2.0`) with the zip attached, so the issue can
   link a stable URL.
4. Open the issue with the template: name `cadwellio`, version `0.2.0`, a
   one-paragraph description (Cadwell Arc CadLink import, own SQLite
   reader, no toolbox/Java/Python, Unlicense), the repository link, the zip.
   Updates use the same template with current and new version.
5. Optionally a pull request on sccn/sccn.github.io adding a line to the
   extensions page (`others/EEGLAB_Extensions.md`) next to biosig and
   neuroscanio.

Checked against the tutorial (eeglab.org/tutorials/contribute/design_plugin.html)
and EEGLAB's own code: `eegplugin_cadwellio(fig, trystrs, catchstrs)` returns
the version string and adds one `uimenu` under the `import data` tag with
the `catchstrs.new_and_hist` callback, exactly as EEGLAB's neuroscanio
importer does; `pop_cadwell` pops up a file dialog without arguments and
returns the history string. Importers take a file name rather than `EEG` as
first argument, like `pop_loadcnt` and `pop_biosig`. The item needs no
`userdata` keywords: `eeglab.m` enables every menu item at startup except
those tagged `startup:off` (the tutorial's table listing `startup` as off
by default describes the keyword, not the code's behaviour), and disables
the whole *Import data* menu while a STUDY is loaded, plugin items included.
The plugin list is not a pull request: the plugin stays in this repository,
and the issue only registers name, version, zip, description and tags with
SCCN's server, which the plugin manager queries
(`functions/adminfunc/plugin_getweb.m`).

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
