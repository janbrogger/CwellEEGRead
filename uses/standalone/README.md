# CwellEEGRead standalone converter

Converts Cadwell Arc EEG recordings (CadLink exports with `CadLink/Data/*.ezdataindex`)
to EDF/EDF+. One file, `cwelleegread.pyz`; needs Python 3.10+ and `pip install numpy scipy`.

```
python cwelleegread.pyz selftest                     # self-test on the bundled test EEG
python cwelleegread.pyz selftest EXPORT CADWELL.edf  # self-test on your recording + Cadwell's EDF export of it
python cwelleegread.pyz convert EXPORT out.edf --timezone Europe/Oslo
python cwelleegread.pyz batch FOLDER OUTDIR          # every recording below FOLDER
python cwelleegread.pyz COMMAND --help               # all options
```

`selftest` converts as Cadwell's own EDF export does (`--mode vendor`) and compares
signals, start time, every sample (at most one quantisation step), gain, time lag and
annotations with that export; exit code 0 = every check passed. Run it on one recording
per amplifier and Cadwell version you use (EDF exported with all channels and events,
any time range). It prints no patient fields, but may quote annotation texts.

## Known shortcomings

- **Versions**: only storage schema 2.5 (Cadwell Arc, 2025-2026) is verified; others are
  refused unless `--allow-unsupported`. The self-test shows whether yours works.
- **Headboxes**: channel labels are not stored in the files; tables exist for Apollo
  and Essentia only, other headboxes need `--labels`.
- **Scale**: microvolts per amplifier unit is an empirical constant.
- **Timing**: the default raw mode keeps every sample and declares the nominal rate;
  Apollo delivers ~0.08 % extra samples (248-251/s at 250 Hz), so its EDF time drifts
  from the wall clock by up to ~3 s per hour. `--mode vendor` resamples as Cadwell does.
  Events are placed on the sample clock; Cadwell places them by a wall clock that runs
  behind (up to 0.35 s per hour earlier; `--event-timing stamp` to match).
- **Gaps**: recording pauses are filled with zeros and annotated.
- **Filter**: `--mode vendor` applies Cadwell's 0.16 Hz export high-pass on Essentia.
- **Not handled**: choosing a time range, video, typed-text event types. The whole
  recording is held in memory (~1.5 GB per hour at 500 Hz, 32 channels).
- **Platforms**: CI runs the self-test on Linux, Windows and macOS. On Windows, IANA
  time-zone names need `pip install tzdata` (or use e.g. `--timezone UTC+01:00`).

Public domain (Unlicense). Source and documentation: https://github.com/janbrogger/CwellEEGRead
