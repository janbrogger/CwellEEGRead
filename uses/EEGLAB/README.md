# uses/EEGLAB - EEGLAB import plugin for Cadwell EEG (and FieldTrip notes)

**Status:** scaffold. The plugin skeleton follows the EEGLAB plugin
conventions (`eegplugin_<name>.m` registering a menu item, `pop_<name>.m`
doing the work and returning a history command). Until the `.ezdata` inner
format is decoded, `pop_cadwell` imports the **EDF produced by
CwellEEGRead** (via the BIOSIG or File-IO plugin) and only inspects the
SQLite outer structure of a `.ezdata` file; the direct reader is a stub that
errors with a clear message. This is enough to build and install the zip
and to develop the menu/GUI side in parallel with the format work. It may
later move to its own GitHub repository.

**Prerequisites**

- MATLAB R2020b or newer with EEGLAB 2021 or newer.
- For reading `.ezdata` directly: Database Toolbox (`sqlite`) **or** the
  free `mksqlite` MEX (https://github.com/a-ma72/mksqlite) on the path;
  `pop_cadwell` uses whichever is available.
- For the EDF path: the EEGLAB BIOSIG plugin (`pop_biosig`) or File-IO
  plugin (`pop_fileio`), installed through the EEGLAB plugin manager.

**Files**

| File | Purpose |
|---|---|
| `cadwellio/eegplugin_cadwellio.m` | plugin entry point: adds *File > Import data > From Cadwell (.ezdata / converted EDF)* |
| `cadwellio/pop_cadwell.m` | importer; GUI when called without arguments, returns `[EEG, com]` |
| `cadwellio/cadwell_sqlite_info.m` | lists tables and row counts of a `.ezdata` file (outer structure) |
| `cadwellio/README.md`, `cadwellio/LICENSE` | shipped inside the zip |
| `make_zip.sh` | builds `cadwellio<version>.zip` for manual install or submission to the EEGLAB plugin list |

**Build and install**

```bash
./make_zip.sh            # -> dist/cadwellio0.1.0.zip
# then: unzip into <eeglab>/plugins/ and restart EEGLAB, or submit at
# http://sccn.ucsd.edu/eeglab/plugin_uploader/upload_form.php
```

**FieldTrip**: the cheapest route is a function `cadwell_sqlite.m` on the
path implementing the three call forms `hdr = f(file)`,
`dat = f(file, hdr, begsample, endsample, chanindx)`, `evt = f(file, hdr)`
and passing `'headerformat','cadwell_sqlite'` (and data/event) to
`ft_read_header/data/event`; upstreaming later means a `ft_filetype` clause
and `case 'cadwell_sqlite'` in the three readers. See
`docs/research/downstream-uses.md`, section C2.
