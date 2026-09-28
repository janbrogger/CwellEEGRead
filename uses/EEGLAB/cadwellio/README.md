cadwellio - EEGLAB import plugin for Cadwell Arc EEG (native, no Python)
========================================================================

Adds File > Import data > "From Cadwell (.ezdataindex / converted EDF)".
Reads a Cadwell Arc CadLink study export directly: the SQLite index,
waveform and event databases are opened through an existing SQLite
library (no hand-rolled SQLite parsing), and the frames are decoded by
a MATLAB/Octave port of the CwellEEGRead decoder
(https://github.com/janbrogger/CwellEEGRead).

Files
  eegplugin_cadwellio.m   EEGLAB plugin entry point (menu item)
  pop_cadwell.m           importer: [EEG, com] = pop_cadwell(path, ...)
  cadwell_read.m          top-level reader -> struct (data in microvolts, labels, events, gaps)
  cadwell_read_index.m    .ezdataindex: channel table, frame index, gaps, clock correction
  cadwell_read_events.m   .ezevents
  cadwell_decode_frame.m  one frame blob -> per-channel samples
  cadwell_sqlite.m        read-only SQLite access with pluggable backends
  cadwell_get_jdbc.m      downloads the sqlite-jdbc driver into lib/
  cadwell_layout.m        channel labels per headbox (Apollo, Essentia)
  cadwell_selftest.m      verification against reference data (see below)

SQLite backends (first available is used; cadwell_sqlite('backends') lists them)
  mksqlite   MEX, MATLAB (https://github.com/a-ma72/mksqlite)
  sqlite     MATLAB Database Toolbox, or the GNU Octave 'sqlite' package
  jdbc       xerial sqlite-jdbc jar (Apache-2, natives for Windows, macOS and
             Linux bundled) in cadwellio/lib - run cadwell_get_jdbc once, or
             unzip the plugin release which ships it. Works in MATLAB and in
             Octave built with Java. This is the backend the self-test runs on.
  python     MATLAB's py.sqlite3 (MATLAB only)

Usage
  >> EEG = pop_cadwell('D:\exports\study1');        % folder with CadLink/Data
  >> rec = cadwell_read('...\record.ezdataindex');  % without EEGLAB
  >> cadwell_sqlite('backends')

Data are referential to the recording reference (Cz on all recordings
seen so far; EEG.ref is set accordingly). Recording breaks are padded with
zeros by default so that event latencies stay aligned ('padgaps','off' to
concatenate). Channel labels come from a per-headbox table because the
Cadwell files store none.

Verification
  cadwell_selftest(refDir) checks, per public test export, that the decoder
  reproduces the Python decoder bit for bit on stored frames, that the
  native read through the SQLite backend yields the same index, labels,
  events and samples, and that export 1 equals the vendor's text export
  within 0.05 uV. tests/test_octave_port.py in the repository runs it
  under GNU Octave.
