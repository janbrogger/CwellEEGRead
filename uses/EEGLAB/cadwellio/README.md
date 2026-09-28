cadwellio - EEGLAB import plugin for Cadwell Arc EEG (pure MATLAB/Octave)
==========================================================================

Adds File > Import data > "From Cadwell (.ezdataindex / converted EDF)".
Reads a Cadwell Arc CadLink study export directly, with nothing but plain
MATLAB/Octave code: the SQLite index, waveform and event databases are
parsed by a small reader of the SQLite 3 file format (cadwell_sqlite_native.m)
and the frames are decoded by a MATLAB/Octave port of the CwellEEGRead
decoder (https://github.com/janbrogger/CwellEEGRead). No toolbox, MEX,
Java or Python is needed.

Files
  eegplugin_cadwellio.m     EEGLAB plugin entry point (menu item)
  pop_cadwell.m             importer: [EEG, com] = pop_cadwell(path, ...)
  cadwell_read.m            top-level reader -> struct (data in microvolts, labels, events, gaps)
  cadwell_read_index.m      .ezdataindex: channel table, frame index, gaps, clock correction
  cadwell_read_events.m     .ezevents
  cadwell_decode_frame.m    one frame blob -> per-channel samples
  cadwell_sqlite_native.m   read-only SQLite 3 file reader (b-tree pages, records, overflow, UTF-16)
  cadwell_sqlite.m          backend switch: 'native' (default) or a library for cross-checks
  cadwell_tcol.m            column of a table struct by name
  cadwell_get_jdbc.m        downloads the optional sqlite-jdbc driver into lib/ (cross-check only)
  cadwell_layout.m          channel labels per headbox (Apollo, Essentia)
  cadwell_selftest.m        verification against reference data (see below)

SQLite backends (cadwell_sqlite('backends') lists the available ones)
  native     default, always available: cadwell_sqlite_native.m reads whole
             tables straight from the file (SQLite 3 format: header, table
             b-trees, record serial types, overflow pages, INTEGER PRIMARY
             KEY aliases; text encodings UTF-8/UTF-16LE/UTF-16BE - Cadwell
             files are UTF-16LE). No SQL. Verified byte for byte against
             Python's sqlite3 on every table of every file of the public
             test exports.
  Optional library backends, for cross-checking the native reader and for
  ad-hoc SQL (cadwell_sqlite('query', ...)):
  mksqlite   MEX, MATLAB (https://github.com/a-ma72/mksqlite)
  sqlite     MATLAB Database Toolbox, or the GNU Octave 'sqlite' package
  jdbc       xerial sqlite-jdbc jar in cadwellio/lib (run cadwell_get_jdbc;
             MATLAB, or Octave built with Java)
  python     MATLAB's py.sqlite3 (MATLAB only)

Usage
  >> EEG = pop_cadwell('D:\exports\study1');        % folder with CadLink/Data
  >> rec = cadwell_read('...\record.ezdataindex');  % without EEGLAB
  >> rec = cadwell_read(path, 'Backend', 'jdbc');   % force a library backend

Data are referential to the recording reference (Cz on all recordings
seen so far; EEG.ref is set accordingly). Recording breaks are padded with
zeros by default so that event latencies stay aligned ('padgaps','off' to
concatenate). Channel labels come from a per-headbox table because the
Cadwell files store none.

Verification
  cadwell_selftest(refDir) checks, per public test export, that the decoder
  reproduces the Python decoder bit for bit on stored frames, that the
  read through every available backend (native first) yields the same
  index, labels, events, gaps and samples as the Python reader, that the
  native SQLite reader's canonical dump of every table of every file equals
  the dump written by Python's sqlite3 byte for byte, and that export 1
  equals the vendor's text export within 0.05 uV. tests/test_octave_port.py
  in the repository runs it under GNU Octave.
