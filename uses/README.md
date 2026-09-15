# uses/ - downstream uses of the converted EDF files

Each sub-folder is a self-contained scaffold for one way of using the EDF
files that CwellEEGRead produces (REQ016). Status and prerequisites are in
each README. Background: `docs/research/downstream-uses.md`.

| Folder | Use | Status |
|---|---|---|
| `Morgoth/` | Check out, install and run the Morgoth EEG foundation model (bdsp-core/morgoth) on EDF files; convert its CSV output to JSON | scaffold: scripts written from the public repository, not yet run (model weights need BDSP credentialed access) |
| `SCOREAI/` | Call an externally supplied SCORE-AI command-line program on EDF files and normalise its output to JSON | scaffold: wrapper with input checks and a pluggable command template; no SCORE-AI program is public |
| `EEGLAB/` | EEGLAB import plugin (`eegplugin_cadwellio.m`, `pop_cadwell.m`) and a script to build the plugin zip; notes for a FieldTrip reader | scaffold: menu wiring and EDF-based import path; direct `.ezdata` reading waits on the format work |
