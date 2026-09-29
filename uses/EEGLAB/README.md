# cadwellio - EEGLAB plugin for Cadwell Arc EEG

`cadwellio` imports a Cadwell Arc EEG recording (a CadLink study export,
the folder with `CadLink/Data/*.ezdataindex`) straight into EEGLAB. It
is plain MATLAB/Octave code: it parses the SQLite files itself and decodes
the compressed EEG frames, so no toolbox, MEX file, Java or Python is
needed. It can also load an EDF written by the Python converter in this
repository through the BIOSIG or File-IO plugin.

Version 0.3.0. Public domain (Unlicense). Part of
[CwellEEGRead](https://github.com/janbrogger/CwellEEGRead), whose Python
converter uses the same decoding rules and against which this plugin is
tested.

Status: working; 0.2.0 released (GitHub release `cadwellio-v0.2.0`) and
submitted to the EEGLAB plugin list (sccn/eeglab issue 971); 0.3.0 (import
options dialog, GNU Octave stand-ins) not yet released. Verified under GNU
Octave with EEGLAB's own functions and through EEGLAB's own menu and
dialogs; not yet exercised in MATLAB. Prerequisites are listed
under *Requirements* below.

## Requirements

- MATLAB R2016b or newer, or GNU Octave 6 or newer (for EEGLAB's
  graphical interface under Octave see *GNU Octave* below).
- EEGLAB 2021 or newer.
- For EDF files only: the BIOSIG (`pop_biosig`) or File-IO (`pop_fileio`)
  plugin from the EEGLAB plugin manager.

## Install

From the EEGLAB plugin manager (*File > Manage EEGLAB extensions*) once
the plugin is listed there, or manually:

1. Build or download `cadwellio0.3.0.zip` (see *Building the zip* below).
2. Unzip it into `<eeglab>/plugins/`, giving `<eeglab>/plugins/cadwellio0.3.0/`.
3. Restart EEGLAB. *File > Import data > Using EEGLAB functions and plugins*
   now has *From Cadwell (.ezdataindex / converted EDF)*.

## Use

From the menu: pick the `.ezdataindex` file inside `CadLink/Data/` of the
export (or a converted `.edf`), then choose the import options in the
dialog that follows (screenshot: `docs/screenshots/eeglab/2-options-dialog.png`): *Import events*, *Recording pauses* (join the segments
with a `boundary` event, or fill with zeros) and *Event timing* (amplifier
sample clock, or wall-clock stamps); for an EDF only *Import events*. The
defaults are those of the table below. EEGLAB then asks for the dataset
name as after any import, and the history records the full `pop_cadwell`
call with the options chosen. From the command line (no dialogs when a path
is given):

```matlab
EEG = pop_cadwell('D:\exports\study1');                 % export folder, CadLink/Data folder or .ezdataindex
EEG = pop_cadwell(path, 'padgaps', 'on');               % zero-fill recording pauses instead of concatenating
EEG = pop_cadwell(path, 'eventtiming', 'stamp');        % vendor-style event placement (see below)
rec = cadwell_read(path);                               % the reader alone, without EEGLAB
```

| Option | Values | Default | Meaning |
|---|---|---|---|
| `importevent` | `on`, `off` | `on` | copy the recording's events to `EEG.event` (deleted events and amplifier bookkeeping types are left out, as in the vendor's EDF export) |
| `padgaps` | `off`, `on` | `off` | `off`: the segments around a pause are concatenated and each pause becomes an EEGLAB `boundary` event; `on`: pauses become zeros and a `Recording gap` event |
| `eventtiming` | `ticks`, `stamp` | `ticks` | `ticks`: events on the amplifier's sample clock (accurate); `stamp`: by wall-clock stamp, as the vendor's EDF export does |
| `backend` | `native`, `mksqlite`, `sqlite`, `jdbc`, `python` | `native` | SQLite reader; the library backends exist only to cross-check the native one |

## What you get

- `EEG.data` in microvolts, referential to the recording reference (Cz on
  the recordings seen so far; `EEG.ref` is `'Cz'` and each channel's own
  reference is in `EEG.chanlocs(k).ref`).
- Channel labels are electrode names (`Fp1` ... `O2`, `E1/Pg1`, `1A` ...)
  from a table per headbox (Apollo, Essentia), since the Cadwell files store
  none; the EDF-style names (`EEG Fp1-Cz`) are in `EEG.etc.cadwell.edfLabels`.
- `EEG.event` with the technician's comments and the system's markers, with
  `duration` and the Cadwell event type in `cadwelltype`.
- `EEG.etc.cadwell` with the index, headbox, frame table and the list of
  recording pauses (`gaps`: `startSample`, `seconds`, `startSec`, `padded`).

### Recording pauses

A pause (the vendor's *Stop Recording* / *Start Recording*) leaves missing
seconds in the frame numbering. By default (`padgaps` off) the segments are
joined, the pause becomes a standard EEGLAB `boundary` event (`duration` =
samples removed, as `eeg_eegrej` writes them, so filtering and epoching
respect the discontinuity) and later events move up accordingly; events
the vendor stamped inside the pause land on the join. With `padgaps` on,
the pause is filled with zeros instead so latencies stay aligned with
wall-clock time, and an event of type `Recording gap` with the pause length
as `duration` marks it.

Do not use the *Stop Recording* / *Start Recording* events to find the
data edges: the recorder drops the partial second around each press, so
the stored data end 0.5-2 s before the Stop event and begin about 1 s after
the Start event. The `Recording gap` / `boundary` events come from the
frame numbering and are exact. Measurements: `docs/research/cadwell-file-format.md`.

### Event timing

Every Cadwell event carries a wall-clock stamp and an offset on the
amplifier's sample clock, and the two clocks drift (about 96 ppm, 0.35 s
per hour, on Essentia recordings; the stamp clock runs behind). The
vendor's EDF export places events by stamp, which puts them early by the
accumulated drift: a photic flash marker then sits 100 ms before the
sample it belongs to after 17 minutes of recording. `cadwellio` uses the
sample-clock offset by default (`eventtiming`, `ticks`), which puts the
occipital flash response at the 100-130 ms of a normal flash VEP.
`stamp` reproduces the vendor's placement. Details: the "Two clocks"
section of `docs/research/cadwell-file-format.md`.

## Verification

`cadwellio/cadwell_selftest.m` checks, against reference dumps written by
the Python reader (`tools/make_matlab_reference.py`), that the frame
decoder equals the Python decoder bit for bit, that the read through every
available SQLite backend yields the same index, labels, events and samples,
that the native SQLite reader's dump of every table of every test file
equals Python's sqlite3 byte for byte, that padded and concatenated reads
of a recording with a pause agree, that tick- and stamp-based event onsets
differ by exactly the clocks' drift, and that the first public export equals
the vendor's text export within 0.05 uV. `tests/test_octave_port.py` runs
it under GNU Octave; `tests/test_eeglab_import.py` runs `pop_cadwell` with
EEGLAB's own functions on the Octave path (`eeg_checkset`, a
`pop_saveset`/`pop_loadset` round trip, one `boundary` event per pause)
when `EEGLAB_DIR` names an EEGLAB checkout. `tests/test_eeglab_gui.py`
starts EEGLAB's graphical interface under Octave on a virtual display
(xvfb) with the plugin in `plugins/`, chooses the menu item and answers
EEGLAB's real dialogs (only the system file dialog is replaced): the
options chosen must reach the dataset and its history, EEGLAB's naming
dialog must follow, and Cancel must create no dataset.
`tools/eeglab_screenshots.py` takes screenshots of the file dialog, the
options dialog, the naming dialog and the imported EEG (export 3, first
10 s); they are in `docs/screenshots/eeglab/` with a checklist for the
manual verification (TST018). Not yet exercised: the plugin in MATLAB.

## GNU Octave

EEGLAB's graphical interface has two problems under GNU Octave (8.4, EEGLAB
of September 2026) that have nothing to do with this plugin; the folder
`cadwellio/octave/` holds stand-ins for both:

- The main window does not open: *'vers' undefined* in `eeglab>eeg_mainfig`.
  `eeglab.m` (since August 2025) reads a variable it only sets when
  `computer()` starts with GLN, MAC or PCW, which Octave's never does.
  `octave/vers.m` answers in its place. It has to be on the path before
  EEGLAB starts, for instance in `~/.octaverc`:
  `addpath('<eeglab>/plugins/cadwellio0.3.0/octave')`.
  The fix belongs in EEGLAB (define `vers` before that `if`).
- The dataset from any import is not stored: *'contains' undefined* in
  `eeglab_new`. Octave has no `contains`; `octave/contains.m` provides it,
  and the plugin puts the folder on the path by itself under Octave when
  `contains` is missing.

On Debian/Ubuntu Octave also needs the package `fonts-freefont-otf` to draw
any EEGLAB window (*ft_text_renderer: invalid bounding box* otherwise).
Neither stand-in is used under MATLAB: EEGLAB adds only the plugin's own
folder to the path, not its sub-folders.

## Building the zip

```bash
cd uses/EEGLAB
./make_zip.sh                 # -> dist/cadwellio0.3.0.zip
./make_zip.sh --with-jdbc     # also bundles the optional sqlite-jdbc driver
```

The version in the folder name and the `vers` string returned by
`eegplugin_cadwellio` must match; `make_zip.sh` reads it from there.

## Releasing

The plugin is released on its own, independently of the Python converter:
pushing a tag `cadwellio-v<version>` runs
`.github/workflows/release-cadwellio.yml`, which checks that the tag
matches `vers`, builds the zip and publishes a GitHub release named
`cadwellio <version>` with the zip as its only asset. The asset URL is
stable and is what the EEGLAB plugin manager can point at:

```bash
# after bumping vers in cadwellio/eegplugin_cadwellio.m and committing
git tag cadwellio-v0.3.0 && git push origin cadwellio-v0.3.0
# -> https://github.com/janbrogger/CwellEEGRead/releases/download/cadwellio-v0.3.0/cadwellio0.3.0.zip
```

The same workflow also runs when a branch `release/cadwellio-v<version>`
is pushed, or by hand (GitHub: *Actions > release-cadwellio > Run
workflow*, input the version); in both cases it creates the tag itself at
that commit. The branch route is for environments that may push branches
but not tags; the branch can be deleted once the release exists.

GitHub always adds "Source code" archives of the whole repository to every
release; they can be ignored, the plugin is the zip asset.

## Files

| File | Purpose |
|---|---|
| `cadwellio/eegplugin_cadwellio.m` | plugin entry point: menu item and version string |
| `cadwellio/pop_cadwell.m` | importer; file dialog and options dialog when called without arguments, returns `[EEG, com]` |
| `cadwellio/octave/` | GNU Octave stand-ins for EEGLAB's interface (`vers.m`, `contains.m`, `README.txt`) |
| `cadwellio/cadwell_read.m` | reader: data, labels, events, pauses, frame table |
| `cadwellio/cadwell_read_index.m`, `cadwell_read_events.m` | the `.ezdataindex` and `.ezevents` tables |
| `cadwellio/cadwell_decode_frame.m` | one EEG frame blob to samples (vectorised) |
| `cadwellio/cadwell_sqlite_native.m`, `cadwell_sqlite.m`, `cadwell_tcol.m`, `cadwell_get_jdbc.m` | SQLite 3 file reader, backend switch, column helper, optional JDBC download |
| `cadwellio/cadwell_layout.m`, `cadwell_unit_uv.m` | channel labels per headbox, microvolts per unit |
| `cadwellio/cadwell_parse_timestamp.m`, `cadwell_timestamp_sec.m`, `cadwell_key_hex.m` | small helpers |
| `cadwellio/cadwell_selftest.m` | verification against the Python reference dumps |
| `cadwellio/README.md`, `cadwellio/LICENSE` | shipped inside the zip |
| `make_zip.sh` | builds the plugin zip |
