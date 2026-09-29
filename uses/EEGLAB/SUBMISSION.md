# Submitting cadwellio to the EEGLAB plugin list

Where: a new issue on https://github.com/sccn/eeglab using the template
*New plugin or plugin update* (the old upload forms are closed). Before
posting, do the one check the development container cannot: unzip the
release asset into `<eeglab>/plugins/` in MATLAB, start EEGLAB, confirm
that *File > Import data > Using EEGLAB functions and plugins > From
Cadwell* appears, imports a public test export, and that the history line
it writes replays.

Text to paste into the issue (fill the template's fields with it):

---

**Plugin name:** cadwellio

**Current version:** none (new plugin)

**New or revised version:** 0.2.0

**Description of the update:**

Import plugin for Cadwell Arc EEG recordings (CadLink study exports, the
`.ezdataindex` / `.ezdata` / `.ezevents` SQLite files written by Cadwell
Arc systems from about 2020 on). Pure MATLAB/Octave: it parses the SQLite
files and decodes the compressed EEG frames itself, so no toolbox, MEX
file, Java or Python is needed. Adds *File > Import data > From Cadwell*
(`pop_cadwell`), which returns data in microvolts referential to the
recording reference, electrode labels per headbox (Apollo, Essentia),
events on the amplifier's sample clock, and recording pauses as EEGLAB
`boundary` events. It can also load an EDF converted by the companion
Python tool through BIOSIG or File-IO.

The decoder is verified sample for sample against the vendor's own text
and EDF exports of three public test recordings, and the plugin is tested
with EEGLAB's own functions under GNU Octave (`eeg_checkset`,
`pop_saveset`/`pop_loadset`).

Tags: import

Licence: Unlicense (public domain)

Repository: https://github.com/janbrogger/CwellEEGRead (plugin under
`uses/EEGLAB/`, documentation in `uses/EEGLAB/README.md`)

Zip: https://github.com/janbrogger/CwellEEGRead/releases/download/cadwellio-v0.2.0/cadwellio0.2.0.zip
(also attached)

---

Later versions: same template with *Current version* and *New version*
filled in, after pushing a `release/cadwellio-v<version>` branch (or a
`cadwellio-v<version>` tag) so the workflow publishes the new zip.

## 0.3.0 (released, submitted)

Released as GitHub release `cadwellio-v0.3.0` and posted to sccn/eeglab
issue 971 on 2026-09-29 with this text:

**Plugin name:** cadwellio

**Current version:** 0.2.0

**New or revised version:** 0.3.0

**Description of the update:** *File > Import data > From Cadwell* now
shows an import options dialog after the file dialog (events on/off,
recording pauses as `boundary` events or zero padding, event timing on the
amplifier sample clock or by wall-clock stamp), with the options recorded
in the history; EEGLAB's naming dialog follows as usual. Under GNU Octave
the plugin supplies `contains()` (used by `eeglab_new`), and ships a
stand-in for the unset `vers` variable that keeps EEGLAB's main window from
opening under Octave (`eeglab>eeg_mainfig`; to be added to the path in
`~/.octaverc`). The menu and dialogs are tested through EEGLAB's own
interface under Octave on a virtual display.

Zip: https://github.com/janbrogger/CwellEEGRead/releases/download/cadwellio-v0.3.0/cadwellio0.3.0.zip
