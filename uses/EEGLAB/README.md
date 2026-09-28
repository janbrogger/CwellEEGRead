# cadwellio - EEGLAB plugin for Cadwell Arc EEG

`cadwellio` imports a Cadwell Arc EEG recording (a CadLink study export,
the folder with `CadLink/Data/*.ezdataindex`) straight into EEGLAB. It
is plain MATLAB/Octave code: it parses the SQLite files itself and decodes
the compressed EEG frames, so no toolbox, MEX file, Java or Python is
needed. It can also load an EDF written by the Python converter in this
repository through the BIOSIG or File-IO plugin.

Version 0.2.0. Public domain (Unlicense). Part of
[CwellEEGRead](https://github.com/janbrogger/CwellEEGRead), whose Python
converter uses the same decoding rules and against which this plugin is
tested.

## Requirements

- MATLAB R2016b or newer, or GNU Octave 6 or newer.
- EEGLAB 2021 or newer.
- For EDF files only: the BIOSIG (`pop_biosig`) or File-IO (`pop_fileio`)
  plugin from the EEGLAB plugin manager.

## Install

From the EEGLAB plugin manager (*File > Manage EEGLAB extensions*) once
the plugin is listed there, or manually:

1. Build or download `cadwellio0.2.0.zip` (see *Building the zip* below).
2. Unzip it into `<eeglab>/plugins/`, giving `<eeglab>/plugins/cadwellio0.2.0/`.
3. Restart EEGLAB. *File > Import data > Using EEGLAB functions and plugins*
   now has *From Cadwell (.ezdataindex / converted EDF)*.

## Use

From the menu: pick the `.ezdataindex` file inside `CadLink/Data/` of the
export (or a converted `.edf`). From the command line:

```matlab
EEG = pop_cadwell('D:\exports\study1');                 % export folder, CadLink/Data folder or .ezdataindex
EEG = pop_cadwell(path, 'padgaps', 'off');              % concatenate recording pauses instead of zero-filling
EEG = pop_cadwell(path, 'eventtiming', 'stamp');        % vendor-style event placement (see below)
rec = cadwell_read(path);                               % the reader alone, without EEGLAB
```

| Option | Values | Default | Meaning |
|---|---|---|---|
| `importevent` | `on`, `off` | `on` | copy the recording's events to `EEG.event` (deleted events and amplifier bookkeeping types are left out, as in the vendor's EDF export) |
| `padgaps` | `on`, `off` | `on` | `on`: recording pauses become zeros and a `Recording gap` event; `off`: the segments are concatenated and each pause becomes an EEGLAB `boundary` event |
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
seconds in the frame numbering. With `padgaps` on, the pause is filled with
zeros so latencies stay aligned with wall-clock time, and an event of type
`Recording gap` with the pause length as `duration` marks it. With
`padgaps` off, the segments are joined, the pause becomes a standard EEGLAB
`boundary` event (`duration` = samples removed, as `eeg_eegrej` writes them,
so filtering and epoching respect the discontinuity) and later events move
up accordingly; events the vendor stamped inside the pause land on the join.

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
when `EEGLAB_DIR` names an EEGLAB checkout. Not yet exercised: the menu
item in the MATLAB GUI itself.

## Building the zip

```bash
cd uses/EEGLAB
./make_zip.sh                 # -> dist/cadwellio0.2.0.zip
./make_zip.sh --with-jdbc     # also bundles the optional sqlite-jdbc driver
```

The version in the folder name and the `vers` string returned by
`eegplugin_cadwellio` must match; `make_zip.sh` reads it from there.

## Submitting to the EEGLAB plugin list

Submission is a GitHub issue on https://github.com/sccn/eeglab with the
template *New plugin or plugin update* (plugin name, version, description,
the zip attached or linked as a release asset); the old upload forms are
closed. Before submitting, test once in MATLAB with EEGLAB: unzip into
`plugins/`, check that the menu item appears and imports a public test
export, and that the history line it writes replays. How the other listed
plugins are hosted and released, and how this plugin meets the plugin
tutorial's rules: `docs/research/eeglab-plugin-list-survey.md`.

## Files

| File | Purpose |
|---|---|
| `cadwellio/eegplugin_cadwellio.m` | plugin entry point: menu item and version string |
| `cadwellio/pop_cadwell.m` | importer; file dialog when called without arguments, returns `[EEG, com]` |
| `cadwellio/cadwell_read.m` | reader: data, labels, events, pauses, frame table |
| `cadwellio/cadwell_read_index.m`, `cadwell_read_events.m` | the `.ezdataindex` and `.ezevents` tables |
| `cadwellio/cadwell_decode_frame.m` | one EEG frame blob to samples (vectorised) |
| `cadwellio/cadwell_sqlite_native.m`, `cadwell_sqlite.m`, `cadwell_tcol.m`, `cadwell_get_jdbc.m` | SQLite 3 file reader, backend switch, column helper, optional JDBC download |
| `cadwellio/cadwell_layout.m`, `cadwell_unit_uv.m` | channel labels per headbox, microvolts per unit |
| `cadwellio/cadwell_parse_timestamp.m`, `cadwell_timestamp_sec.m`, `cadwell_key_hex.m` | small helpers |
| `cadwellio/cadwell_selftest.m` | verification against the Python reference dumps |
| `cadwellio/README.md`, `cadwellio/LICENSE` | shipped inside the zip |
| `make_zip.sh` | builds the plugin zip |

## FieldTrip

Not implemented. The cheapest route is a function on the path with the
three `ft_read_header` / `ft_read_data` / `ft_read_event` call forms,
wrapping `cadwell_read`; see `docs/research/downstream-uses.md`, section C2.
