# uses/ - downstream uses of the converted EDF files

Each sub-folder is a self-contained scaffold for one way of using the EDF
files that CwellEEGRead produces (REQ016). Status and prerequisites are in
each README. Background: `docs/research/downstream-uses.md`.

| Folder | Use | Status |
|---|---|---|
| `Morgoth/` | Check out, install and run the Morgoth EEG foundation model (bdsp-core/morgoth) on EDF files; convert its CSV output to JSON | scaffold: scripts written from the public repository, not yet run (model weights need BDSP credentialed access) |
| `SCOREAI/` | Call an externally supplied SCORE-AI command-line program on EDF files and normalise its output to JSON | scaffold: wrapper with input checks and a pluggable command template; no SCORE-AI program is public |
| `standalone/` | The converter as one file, `cwelleegread.pyz` (Python + numpy + scipy), with its equivalence self-test and the bundled test recording; README with the known shortcomings (REQ023, REQ024) | built by `build.py`; self-test run on Linux, Windows and macOS in CI; release workflow `release-standalone.yml`, not yet released |
| `EEGLAB/` | EEGLAB import plugin `cadwellio`: pure MATLAB/Octave reader of CadLink exports (own reader of the SQLite 3 file format, frame decoder ported from Python; library SQLite backends only for cross-checks), plus a zip builder; notes for a FieldTrip reader | reader verified under Octave against the Python decoder, Python's sqlite3 (byte for byte on every table) and the vendor text export; not yet exercised inside MATLAB/EEGLAB |
