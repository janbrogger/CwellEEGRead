### Table of Contents

 * 1.0 EDF structural validity (TST001)
 * 2.0 Header equivalence with native EDF export (TST002)
 * 3.0 Sample equivalence with native EDF export (TST003)
 * 4.0 Annotation equivalence with native EDF export (TST004)
 * 5.0 Sample equivalence with native CSV/text export (TST005)
 * 6.0 Command-line behaviour (TST006)
 * 7.0 Anonymisation (TST007)
 * 8.0 Test data manifest and graceful skip (TST008)
 * 9.0 Traceability validation (TST009)
 * 10 LLM log integrity (TST010)
 * 11 Environment setup (TST011)
 * 12 Licence compatibility check (TST012)
 * 13 Downstream use scaffolds present (TST013)
 * 14 Supported-version coverage (TST014)
 * 15 Gap handling (TST015)
 * 16 Event timing on the sample clock (TST016)
 * 17 Import through the EEGLAB menu (TST017)
 * 18 EEGLAB plugin screenshots, manually verified (TST018)

# 1.0 EDF structural validity _(TST001)_ {#TST001}

Convert each test recording and open the result with two independent EDF
readers (pyedflib and MNE-Python). Pass if the file is read without header
errors, reports the expected number of channels, records and duration, and
the samples read back equal the decoded samples within the declared
resolution, with both readers. EDF+D files, which EDFlib/pyedflib refuses
and MNE-Python reads as if contiguous, are checked with the test suite's own
record-level reader for the record onsets. Implemented for the public
exports in tests/test_convert_public.py (raw and vendor modes, pyedflib)
and tests/test_edf_formats.py (MNE-Python read-back, plain EDF, EDF+D, the
prefilter field).

*Parent links: DES002, DES010*

# 2.0 Header equivalence with native EDF export _(TST002)_ {#TST002}

For each test recording compare our EDF header with the native Cadwell EDF
export: channel labels (after the documented mapping), sampling rates,
physical dimensions, physical/digital ranges, start date/time, patient and
recording identification. Pass if all match exactly, except fields that the
mapping table documents as intentionally different.

*Parent links: DES003, DES004, DES008*

# 3.0 Sample equivalence with native EDF export _(TST003)_ {#TST003}

For each test recording with an unfiltered vendor text export, prove raw
fidelity against the text export (TST005). For each recording with a
vendor EDF export, convert in vendor-compatible mode with the same start
(first frame, record origin or user time) and compare every sample of
every channel with the native EDF: the sample counts must match and the
maximum absolute difference must not exceed one digital quantisation step
of the native export (a small allowance for the vendor's asymmetric
physical range is documented). Implemented: cadwell-export1 (Apollo,
tests/test_convert_public.py, 11000/11000 samples) and cadwell-export2 and
3-withfilter (Essentia, tests/test_vendor_exports_filtering.py, 480000 and
608500 samples including a padded gap). Report the maximum and mean
difference per channel.

*Parent links: DES003, DES008, DES020*

# 4.0 Annotation equivalence with native EDF export _(TST004)_ {#TST004}

For each test recording compare the EDF+ annotation lists (onset, duration,
text) of our export and the native export. Pass if, in vendor-compatible
mode, the lists are equal after rounding onsets to the millisecond (the
vendor's event policy - deleted events, amplifier bookkeeping types and
the individual photic flashes omitted - is reproduced), and, in raw mode,
the native list is a subset of ours; list every unmatched annotation on
failure. Implemented for cadwell-export1, 2 and 3-withfilter.

*Parent links: DES005, DES008*

# 5.0 Sample equivalence with native CSV/text export _(TST005)_ {#TST005}

For each test recording parse the native CSV/text export, map its column
order (amplifier input order) to EDF channel labels, and compare the
physical values with our decoded samples over the full common range,
sample by sample without any alignment (the text export keeps every raw
sample and omits recording gaps, so compare frame by frame). Pass if the
maximum absolute difference is within the numeric precision of the text
export (0.05 µV for 4 decimals of mV) plus a documented allowance for the
microvolt scale constant, and every column maps to exactly one channel.
Implemented for the public exports: cadwell-export1 (7755 rows),
cadwell-export2 (15500 rows) and the whole of cadwell-export3 (603000
rows, across the break) in tests/test_ezdata_public.py,
tests/test_export3_gap.py and tests/test_vendor_exports_filtering.py.

*Parent links: DES009*

# 6.0 Command-line behaviour _(TST006)_ {#TST006}

Run the CLI on a valid recording, on a non-existent path, on a corrupt
file and on an unsupported version, and run the batch mode on a folder
holding several recordings, one of them unsupported. Pass if the valid run
returns exit code 0 and a valid JSON report when requested; every invalid
run returns a non-zero exit code, prints a one-line diagnostic (no
traceback) and leaves no output file behind; an unsupported version
converts only with `--allow-unsupported`, with a report warning; the batch
converts every other recording, names the outputs after the records, writes
a summary listing the failure and exits non-zero; and the installed
`cwelleegread` command runs. Implemented in tests/test_convert_public.py
(`test_cli_behaviour`) and tests/test_cli.py.

*Parent links: DES006, DES018*

# 7.0 Anonymisation _(TST007)_ {#TST007}

Convert a test recording with the anonymisation option. Pass if the patient
identification fields contain only the supplied or placeholder values, no
annotation contains the original patient name or identifier, and the signal
data is identical to a conversion without the option. Implemented in
tests/test_anonymisation.py on cadwell-export2 (a Comment and a UserEvent
with typed text): the patient GUID and the typed texts appear in the file
and report without the option and nowhere in the EDF bytes or the JSON
report with it, the patient field is `X X X <name>`, and the digital
samples of all 32 signals are identical.

*Parent links: DES014*

# 8.0 Test data manifest and graceful skip _(TST008)_ {#TST008}

Verify that every test recording listed in the manifest matches its
recorded sizes and SHA-256 checksums - the committed public recordings on
every run, the private ones whenever `testdata/private/` is present - and
that when the private folder is absent all tests needing it are reported as
skipped with an explanatory message rather than failing. Implemented in
tests/test_manifest.py (public entries) and the `testdata` fixture in
tests/conftest.py (private entries).

*Parent links: DES007, DES011*

# 9.0 Traceability validation _(TST009)_ {#TST009}

Run `doorstop` on `docs/traceability/`. Pass if it reports no errors, every
normative REQ item links to at least one NEED item, every normative REQ item
has a DES item with non-empty design text linking to it, every DES item is
linked from at least one TST item, so every requirement is covered by a
test through its design, and the committed `published/*.md` equal a fresh
`doorstop publish`. Implemented in tests/test_traceability.py.

*Parent links: DES013*

# 10 LLM log integrity _(TST010)_ {#TST010}

Verify that every session folder under `llm-logs/` contains a transcript
and is listed in `llm-logs/sessions.csv`, that every session in
`sessions.csv` has a folder, and that `llm-logs/tools/llmlog.py index`
regenerates the derived files without error.

*Parent links: DES012*

# 11 Environment setup _(TST011)_ {#TST011}

On a fresh clone run `./setup.sh`. Pass if it completes without error,
`.venv/bin/doorstop --version` prints the pinned version, `.venv` is
ignored by git, the `cwelleegread` command is installed and the test suite
passes in that environment. Automated as the `python` job of
`.github/workflows/tests.yml` (fresh checkout on every push, Python 3.11 and
3.12); the checks that need no fresh clone (ignore rules, Doorstop pin,
`setup.sh` syntax and mode, runtime dependencies of `pyproject.toml` equal
to `requirements.txt`) are in tests/test_environment.py.

*Parent links: DES017*

# 12 Licence compatibility check _(TST012)_ {#TST012}

Inspect the LICENSE file and the headers of every ported third-party source
file. Pass if the repository licence permits every ported file's licence
and each ported file carries its original copyright and licence notice.
Implemented in tests/test_licence.py: the root and plugin `LICENSE` files
are the Unlicense; every file registered in
`docs/research/ported-files.yml` exists, has a licence the Unlicense can
carry and contains its notice; and no unregistered tracked source file
contains third-party licence text (GPL, LGPL, Apache, MIT, BSD, MPL,
SPDX or copyright notices).

*Parent links: DES015*

# 13 Downstream use scaffolds present _(TST013)_ {#TST013}

Check that `uses/Morgoth`, `uses/SCOREAI` and `uses/EEGLAB` exist, each with
a README that states status and prerequisites, and that each provided
script runs its `--help` or dry-run mode without error. For the EEGLAB
plugin additionally run its self-test under GNU Octave when available
(tests/test_octave_port.py): the MATLAB/Octave frame decoder must equal
the Python decoder bit for bit on stored frames of every public export,
the read through every available SQLite backend (always the pure
MATLAB/Octave reader `cadwell_sqlite_native.m`) must yield the same index,
labels, events, gaps and samples as the Python reader, the native SQLite
reader's canonical dump of every table of every file must equal the dump
written by Python's sqlite3 byte for byte, for a recording with a pause
the padded and concatenated reads must agree (zeros at the pause, pause
position and length, event onsets after the pause shifted by its length),
and export 1 must equal the vendor's text export within 0.05 µV. The
importer's dataset must pass EEGLAB's `eeg_checkset` and a
`pop_saveset`/`pop_loadset` round trip with EEGLAB's functions on the
Octave path; with `'padgaps','off'` exactly one `boundary` event per
pause must be present, with duration equal to the removed samples.

*Parent links: DES016*

# 14 Supported-version coverage _(TST014)_ {#TST014}

Check that the documented list of supported Cadwell storage schema versions
(`cwelleegread/ezdata.py: SUPPORTED_SCHEMA_VERSIONS`) is non-empty, that
every listed version is represented by at least one recording in the test
data manifest, and that each public manifest recording's data carries the
schema version the manifest states. Implemented in tests/test_manifest.py;
the refusal of other versions is tested under TST006.

*Parent links: DES001*

# 15 Gap handling _(TST015)_ {#TST015}

Using a test recording that contains at least one acquisition gap
(cadwell-export3: 10 s), convert in raw mode with the default gap handling.
Pass if the file is EDF+C, the number of EDF records equals the
frame-number span, the padded seconds read back as digital zero at exactly
the missing frame numbers, the samples on both sides of the gap are
unchanged, the gap annotation and the vendor's Stop/Start Recording events
appear at the correct offsets, and the conversion report lists the gap.
Convert it again with `--gaps discontinuous`. Pass if the file is EDF+D,
the record onsets skip exactly the gap seconds, the samples equal the
padded file's without the gap records, and the gap and Stop/Start Recording
annotations are present. Implemented in tests/test_export3_gap.py and
tests/test_edf_formats.py.

*Parent links: DES008, DES019*

# 16 Event timing on the sample clock _(TST016)_ {#TST016}

Using a recording with photic stimulation (cadwell-export2 and 3: 244
`Photic Stim` flash events each), convert in raw mode with every event
exported, once with `--event-timing ticks` and once with `stamp`. Pass if:
the difference between the two onsets of every flash equals the drift
between the frame time stamps and the frame ticks at that point of the
recording within 1 ms (78 ms at 13.5 min in export 2, 96 ms at 17 min in
export 3); the flash-locked average of O1 and O2 (referenced to Cz)
peaks before 150 ms after the flash with `ticks` (a flash VEP) and
later than 170 ms with `stamp` (the stamp-placed flash is early, so the
response appears late); the report states the placement; and
vendor-mode annotations are unchanged (the existing equivalence tests
against the vendor EDF, TST003/TST005, keep passing). In vendor mode with
`ticks` (cadwell-export1), pass if the map from raw to resampled sample
positions reproduces the resampled data exactly and every onset lies
within one sample of its raw tick position minus the samples removed
before it. For the EEGLAB plugin the self-test checks that `EventTiming`
ticks and stamp differ by the drift the frames show at each event
(tolerance 5 ms, widened by the stamp jitter on Apollo recordings).
Implemented in tests/test_event_timing.py and cadwell_selftest check F.

*Parent links: DES005, DES021*

# 17 Import through the EEGLAB menu _(TST017)_ {#TST017}

Start EEGLAB's graphical interface under GNU Octave on a virtual display
(xvfb) from a private EEGLAB tree with the plugin copied into `plugins/`,
with `octave/vers.m` on the path beforehand as documented. Replace only the
system file dialog (`uigetfile`, returning public export 3) and wrap
EEGLAB's `inputgui` so that each dialog is drawn by the real `inputgui`
('plot' mode), answered by widget tag and read back with 'getresult'.
Pass if: the plugin is loaded, *From Cadwell (.ezdataindex / converted
EDF)* is present under *Using EEGLAB functions and plugins* and enabled
before any dataset exists; under an Octave without `contains` the plugin
has put its stand-in on the path; choosing the item shows the options
dialog, with two choices in each popup menu, and then EEGLAB's naming
dialog; with *Fill each pause with zeros* and *Wall-clock stamps* chosen
and a name typed, exactly one dataset is stored under that name, with one
`Recording gap` event of 10 s and no `boundary` event, stamp event timing,
and a history containing the `pop_cadwell` call with `'padgaps', 'on'` and
`'eventtiming', 'stamp'`; no EEGLAB error is raised; and choosing the item
again and pressing Cancel in the options dialog stores no further dataset.
Skipped when Octave, xvfb, EEGLAB or the export is missing, or Octave cannot
draw text on the virtual display.

*Parent links: DES022*

# 18 EEGLAB plugin screenshots, manually verified _(TST018)_ {#TST018}

Screenshots with manual verification. Automated part: run
`tools/eeglab_screenshots.py`, which starts EEGLAB's graphical interface under
GNU Octave on a virtual display (Xvfb) with the plugin installed in
`plugins/` as from its zip. It chooses *From Cadwell* in the menu and works
the real dialogs from outside with xdotool: it types public export 3's
`CadLink/Data` folder and `.ezdataindex` into the file dialog, and presses
*Ok* in the options dialog and in EEGLAB's naming dialog, keeping the
defaults. It then shows the dataset with `pop_eegplot`, first page, 10 s
window. Pass if four screenshots are written (the file dialog, the options
dialog, the naming dialog and the EEG), each at least the expected size and
not blank (`tests/test_eeglab_screenshots.py`; CI keeps them as the
artifact `eeglab-screenshots`).

Manual part: a reviewer checks the committed screenshots in
`docs/screenshots/eeglab/` against the checklist in
`docs/screenshots/eeglab/README.md` and records date, reviewer and result
there. Pass if:
- the file dialog shows export 3's `CadLink/Data` folder with its
  `.ezdataindex`;
- the options dialog shows that file, *Import events* ticked, the
  concatenating pause choice and the sample-clock timing as defaults, and
  Help/Cancel/Ok buttons, all readable;
- EEGLAB's naming dialog follows, with the recording GUID as the name;
- the EEG page shows the 32 channels in the vendor EDF's order (E1/Pg1 …
  O2, 1A … 7A), a 0-10 s axis, Cz flat (the recording reference), one
  *Øyne lukket* event at 4.6 s, and plausible EEG without import
  artefacts (steps, clipping, zero blocks, repeated segments).

Repeat the manual part whenever the plugin's dialogs or data path change.

*Parent links: DES016, DES022*

