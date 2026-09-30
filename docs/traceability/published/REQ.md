### Table of Contents

 * 1.0 Input: Cadwell EEG recordings from around 2020 onward (REQ001)
 * 2.0 Output: EDF/EDF+ files (REQ002)
 * 3.0 Signal fidelity (REQ003)
 * 4.0 Recording and patient metadata (REQ004)
 * 5.0 Events and annotations (REQ005)
 * 6.0 Command-line interface (REQ006)
 * 7.0 Test data set supplied out of band (REQ007)
 * 8.0 Proven equivalence with the native EDF export (REQ008)
 * 9.0 Proven equivalence with the native CSV/text export (REQ009)
 * 10 Round-trip self-consistency (REQ010)
 * 11 Automated test execution (REQ011)
 * 12 LLM session provenance (REQ012)
 * 13 Requirements traceability (REQ013)
 * 14 Anonymisation option (REQ014)
 * 15 Licence compatibility (REQ015)
 * 16 Downstream use scaffolds (REQ016)
 * 17 Reproducible development environment (REQ017)
 * 18 Clear failure on unsupported input (REQ018)
 * 19 Recording gaps and discontinuities (REQ019)
 * 20 Sample clock and resampling policy (REQ020)
    * 20.1 Event placement on the sample clock (REQ021)
    * 20.2 EEGLAB plugin import dialog (REQ022)
 * 21 Standalone distribution (REQ023)
    * 21.1 Standalone executables (REQ025)
 * 22 Equivalence self-test (REQ024)

# 1.0 Input: Cadwell EEG recordings from around 2020 onward _(REQ001)_ {#REQ001}

The program shall read EEG recordings produced by Cadwell Arc EEG software
(recordings from around 2020 onward). A recording is a "CadLink" study
export: a folder holding, under `CadLink/Data/`, a set of SQLite 3
databases per record - `<record>-<timestamp>.ezdataindex` (frame index and
track definition), `<record>-<timestamp>-<n>.ezdata` (EEG waveform frames),
`<record>-<timestamp>.ezevents` (events), `<record>.mediadb` and
`<record>-<n>.mediadb` (audio/video frames) - plus encrypted catalogue
databases under `CadLink/Databases/` that the program shall not need. The
outer structure is readable with a standard SQLite library; the inner
waveform encoding is proprietary. The set of supported Cadwell software
versions and storage schema versions (SchemaUpdateLog) shall be documented
and each supported version shall be represented by at least one test
recording.

*Parent links: NEED001*

*Child links: DES001*

# 2.0 Output: EDF/EDF+ files _(REQ002)_ {#REQ002}

The program shall write European Data Format files conforming to the EDF
specification (Kemp et al. 1992) and, when annotations, a sub-second start
time or a discontinuous time axis (EDF+D) require it, to the EDF+
specification (Kemp & Olivan 2003). Output files shall be readable by
at least two independent EDF readers (e.g. EDFbrowser and pyedflib or
MNE-Python) without warnings about header validity. Where a common reader
cannot represent a file correctly (EDF+D), the documentation shall say so.
When the program applies a filter to the signal, the EDF prefilter field
shall say so.

*Parent links: NEED002*

*Child links: DES002*

# 3.0 Signal fidelity _(REQ003)_ {#REQ003}

For every EEG channel in the source recording the program shall preserve:
the channel label, the sampling rate, the physical dimension (microvolts),
the physical and digital minimum/maximum, and every sample value. No
filtering, resampling, re-referencing or truncation shall be applied unless
explicitly requested on the command line, and any such processing shall be
recorded in the EDF header's prefiltering field.

*Parent links: NEED003*

*Child links: DES003*

# 4.0 Recording and patient metadata _(REQ004)_ {#REQ004}

The program shall populate the EDF header with the recording start date and
time (frame-0 time stamp corrected by the amplifier/PC clock offset, to the
microsecond via the EDF+ sub-second convention; UTC unless a time zone is
given), the patient identification fields, the recording identification
fields (record identifier, equipment) and per-channel transducer and
prefiltering fields. Channel labels shall follow the EDF+ label convention
(e.g. `EEG Fp1-Cz`). Because the Cadwell files store no channel labels, the
program shall derive them from a documented amplifier-input layout table
(cwelleegread/layout.py, verified on the test recordings), shall allow the
user to override the table, and shall flag inferred labels in the
conversion report.

*Parent links: NEED003, NEED005*

*Child links: DES004*

# 5.0 Events and annotations _(REQ005)_ {#REQ005}

Events stored in the Cadwell recording (technician comments, seizure or
event markers, photic stimulation and hyperventilation markers, montage
or impedance events) shall be exported as EDF+ annotations with onset
times accurate to one sample, and with their text preserved. Event types
that cannot be mapped shall be listed in the conversion report.

*Parent links: NEED002, NEED003*

*Child links: DES005*

# 6.0 Command-line interface _(REQ006)_ {#REQ006}

The program shall provide a command-line interface of the form
`cwelleegread convert <cadwell-input> <output.edf>` that converts a single
recording, plus a batch mode that converts every recording under a folder.
It shall return exit code 0 on success and non-zero on any failure, and
shall optionally emit a machine-readable JSON conversion report (input
identity, channels, duration, events, warnings) for use by downstream
scripts.

*Parent links: NEED001, NEED006*

*Child links: DES006*

# 7.0 Test data set supplied out of band _(REQ007)_ {#REQ007}

Development shall use a small set of test EEGs, each consisting of (a) the
recording in native Cadwell format, (b) the same recording exported to EDF
by the native Cadwell application and (c) the same recording exported to
CSV/text by the native Cadwell application. Recordings of real patients
shall be supplied outside the repository and live only under
`testdata/private/` (gitignored). Recordings that contain no patient data
(synthetic, amplifier noise or consenting volunteers recorded under a
placeholder name) may be committed under `testdata/public/`, so that the
equivalence tests run on every clone. Every test recording, public or
private, shall be listed in `testdata/manifest.json` with its file names,
sizes, SHA-256 checksums, storage schema version and the Cadwell software
version that produced it, and the checksums shall be verified by the tests.

*Parent links: NEED003, NEED005*

*Child links: DES007*

# 8.0 Proven equivalence with the native EDF export _(REQ008)_ {#REQ008}

An automated test shall prove that the program's EDF export is equivalent
to the native Cadwell EDF export of the same recording: (1) the same set of
channels, matched by label after the documented mapping; (2) identical
sampling rate per channel; (3) identical recording start time; (4) the
same set of annotations (onset, duration, text); (5) sample values equal
within one digital quantisation step of the native export. The native EDF
export is not the raw data: it resamples surplus samples (Apollo, 250 Hz),
pads gaps with zeros, applies a 2nd-order 0.16 Hz Butterworth high-pass
primed on the time-reversed segment start (Essentia recordings), starts at
the export dialog's start time and drops the last frame, and applies a
documented event policy. The test shall therefore compare the program's
vendor-compatible mode (REQ020) sample by sample over the whole file, and
the raw-fidelity output only against the vendor's text export (REQ009),
which is the raw data. Any tolerance actually used shall be justified in
the test's documentation.

*Parent links: NEED003*

*Child links: DES008*

# 9.0 Proven equivalence with the native CSV/text export _(REQ009)_ {#REQ009}

An automated test shall prove that the physical sample values in the
program's EDF export are equal, within the precision of the text export,
to the values in the native Cadwell CSV/text export of the same recording,
channel by channel, over the full common time range. The test shall also
verify that the channel names in the text export map one-to-one onto the
EDF channel labels.

*Parent links: NEED003*

*Child links: DES009*

# 10 Round-trip self-consistency _(REQ010)_ {#REQ010}

The EDF file written by the program shall, when read back by an independent
EDF reader, yield the same channel labels, sampling rates, start time and
sample values (within EDF's 16-bit quantisation) as the data the program
held in memory before writing.

*Parent links: NEED003*

*Child links: DES010*

# 11 Automated test execution _(REQ011)_ {#REQ011}

All equivalence and validity tests shall run under `pytest`. Tests that
need the out-of-band test data shall skip with an explicit message when the
data is absent, so that the remaining tests can run in continuous
integration and on machines without access to patient data. A continuous
integration workflow shall run the test suite on every push and pull
request.

*Parent links: NEED004*

*Child links: DES011*

# 12 LLM session provenance _(REQ012)_ {#REQ012}

Every Claude Code session that touches the repository shall be archived
automatically into `llm-logs/<session_id>/` (full transcript, prompts as
CSV, prompts and responses as Markdown) and indexed in
`llm-logs/sessions.csv`, without manual steps, so that the complete history
of prompts and responses is available in the repository.

*Parent links: NEED004*

*Child links: DES012*

# 13 Requirements traceability _(REQ013)_ {#REQ013}

Requirements shall be managed with Doorstop in `docs/traceability/` as a
chain NEED -> REQ -> DES -> TST. Every normative requirement shall link to
at least one need and shall have a design item (DES) stating how it is
implemented; every design item shall be covered by at least one test
specification, and `doorstop` validation shall pass with no errors before
a release. The published tree (Markdown per document and one PDF of the
whole tree with the traceability matrix) shall be kept in the repository.

*Parent links: NEED004*

*Child links: DES013*

# 14 Anonymisation option _(REQ014)_ {#REQ014}

The program shall offer a command-line option that replaces the patient
identification fields in the EDF header (name, patient code, birth date,
sex) with the values given by the user or with anonymous placeholders, and
that removes patient-identifying text from exported annotations, without
altering the signal data.

*Parent links: NEED005*

*Child links: DES014*

# 15 Licence compatibility _(REQ015)_ {#REQ015}

The repository's licence shall be compatible with every third-party source
ported into it. If code from the BioSig toolbox (GPL-3.0-or-later) is
ported, the repository shall be relicensed under a GPL-compatible licence
and the decision shall be recorded in `docs/research/` and in the LICENSE
file, including attribution of the original authors.

*Parent links: NEED007*

*Child links: DES015*

# 16 Downstream use scaffolds _(REQ016)_ {#REQ016}

The repository shall contain a `uses/` folder with one sub-folder per
downstream use: `uses/Morgoth` (scripts to check out, install and run the
Morgoth foundation model on converted EDF files), `uses/SCOREAI` (scripts
to call an externally supplied SCORE-AI command-line program on converted
EDF files and collect its JSON output) and `uses/EEGLAB` (an EEGLAB reader
plugin that can be packaged as a zip file). Each sub-folder shall have a
README stating its status and prerequisites.

The EEGLAB plugin shall represent recording pauses (REQ019) as events:
when the pause is padded with zeros, an event of type `Recording gap`
with the pause length as duration at the start of the padding; when the
segments are concatenated, a standard EEGLAB `boundary` event with the
number of removed samples as duration at the join, with the latencies of
all later events reduced by the pause length. The pauses shall also be
listed in `EEG.etc.cadwell.gaps` in both modes.

*Parent links: NEED006*

*Child links: DES016*

# 17 Reproducible development environment _(REQ017)_ {#REQ017}

All Python tooling shall be installed into a gitignored virtual environment
from pinned requirement files by a single `setup.sh` script, so that a
fresh checkout can be brought to a working state with one command.

*Parent links: NEED004*

*Child links: DES017*

# 18 Clear failure on unsupported input _(REQ018)_ {#REQ018}

When given a recording it cannot fully convert (an unsupported Cadwell
version, a corrupt or truncated database, an unknown waveform encoding),
the program shall stop with a diagnostic message naming the problem and a
non-zero exit code, and shall not leave a partial EDF file that could be
mistaken for a complete conversion.

*Parent links: NEED003*

*Child links: DES018*

# 19 Recording gaps and discontinuities _(REQ019)_ {#REQ019}

Cadwell recordings can contain gaps (recording stopped and restarted); the
index then lacks the frame numbers of the gap and holds a GapInfo row. The
program shall detect gaps from the frame numbering and represent them in
the EDF output, by default as the vendor's own export does: a continuous
EDF+C file in which the missing seconds are written as digital zero at the
frame boundaries so that the time axis and every annotation stay aligned
with wall-clock time, plus an annotation "Recording gap N s (padded with
zeros)" at the gap start. This default is chosen because common EDF readers
(EDFlib/pyedflib, MNE-Python) do not handle discontinuous files correctly.
As an option outside the vendor-compatible mode, the program shall write a
discontinuous EDF+D file whose data records carry their true onsets, so
that the gap seconds are left out, with an annotation "Recording gap N s".
The gaps shall be listed in the conversion report, and the equivalence tests
shall compare segment by segment so that gap handling differences are
explicit rather than hidden.

*Parent links: NEED003*

*Child links: DES019*

# 20 Sample clock and resampling policy _(REQ020)_ {#REQ020}

The Cadwell amplifier delivers a variable number of samples per one-second
frame (248, 250 or 251 observed at a nominal 250 Hz; exactly 500 at 500 Hz),
i.e. its sample clock can run about 0.08 % fast relative to the frame time
stamps. By default the program shall preserve every raw sample unchanged
("raw fidelity": no filtering, no resampling, the nominal sampling rate in
the EDF header, only a trailing partial second dropped) and report the
effective rate and drift in the conversion report. A command-line option
shall alternatively reproduce the vendor's EDF export ("vendor-compatible"):
all frames but the last, surplus samples removed at evenly spaced positions
with two-point smoothing, gaps and (optionally) the leading missing frames
padded with digital zero, the vendor's 2nd-order 0.16 Hz Butterworth
high-pass primed on the time-reversed segment start where the vendor
applies it (Essentia headbox; overridable), the vendor's physical range
and event policy - so that the output matches the native EDF export sample
by sample. The chosen policy shall be recorded in the EDF header's
recording-additional field and in the conversion report.

*Parent links: NEED002, NEED003*

*Child links: DES020*

## 20.1 Event placement on the sample clock _(REQ021)_ {#REQ021}

Cadwell events carry two times: a wall-clock stamp (`StartTime`, 100 ns
resolution) and an offset on the amplifier sample clock (`StartOffset`
ticks from the record origin). The stored frames carry the same pair, and
the two clocks drift relative to each other (about 96 ppm on the Essentia
recordings seen, 0.35 s per hour). The samples are on the tick clock.

The program shall by default place events on the sample clock: the onset
of an event is derived from its tick offset through the tick spans of the
stored frames (linear within a frame, nominal rate across padded gaps and
beyond the stored range), so that an event lands on the sample it
belongs to regardless of recording length. Placement by wall-clock stamp,
which the vendor's EDF export uses and which lands early by the
accumulated drift (the stamp clock runs behind the sample clock), shall
remain available as an option (`--event-timing
stamp`) and shall be the default in vendor-compatible mode so that the
equivalence tests against the vendor's export (REQ008, REQ020) still
hold. The conversion report shall state which placement was used. The
EEGLAB plugin shall offer the same choice with the same default.

*Parent links: NEED002, NEED003*

*Child links: DES021*

## 20.2 EEGLAB plugin import dialog _(REQ022)_ {#REQ022}

Chosen from EEGLAB's menu, the EEGLAB plugin shall, after the file dialog,
show a dialog for its import options: whether to import events, how to
represent recording pauses (concatenated with `boundary` events, or padded
with zeros, REQ016) and the event placement (sample clock or wall-clock
stamps, REQ021), with the command-line defaults preselected; for an EDF
file only the event choice. The options chosen shall reach the dataset and
be recorded in the EEGLAB history as a complete `pop_cadwell` call. After
the import, EEGLAB's standard dataset naming dialog (`pop_newset`) shall
follow as for any other importer. Cancel in the options dialog shall create
no dataset. Called with a path, the importer shall show no dialog.

Under GNU Octave, the plugin shall supply what EEGLAB's graphical interface
needs from Octave and Octave lacks, as far as this can be done without
changing EEGLAB: stand-ins that are never on the path under MATLAB, and
documented steps for what the plugin cannot do by itself.

*Parent links: NEED006*

*Child links: DES022*

# 21 Standalone distribution _(REQ023)_ {#REQ023}

The converter shall also be released as a standalone product, built from
`uses/standalone/`: one archive holding a single self-contained program
file that runs with Python 3.10 or newer and the numerical libraries numpy
and scipy, on Linux, Windows and macOS, without installing the package and
without a copy of this repository, and that offers the same commands as the
installed `cwelleegread` (REQ006) plus the self-test (REQ024).

The archive shall contain one public test recording without patient data
(REQ007): its native Cadwell files and the vendor's EDF export of it, as
the reference for the self-test. It shall contain a README that is as short
as possible: how to run the program and the self-test, and the known
shortcomings - the Cadwell storage schema versions and headboxes verified,
the empirical microvolt scale, the sample-clock and event-timing
behaviour, recording gaps, the vendor-mode filter, what is not handled,
and on which platforms it was tested.

The standalone product shall be released on its own tag prefix (as the
other products, see the root README), and a release shall be published
only when the self-test passes on the built program file on every platform
above. Continuous integration shall build the program file and run its
self-test on the three platforms on every push.

*Parent links: NEED001, NEED006*

*Child links: DES023*

## 21.1 Standalone executables _(REQ025)_ {#REQ025}

For users without Python, the standalone converter (REQ023) shall also be
released as one executable file per platform - Windows x64, macOS on
Apple silicon and Linux x64 - that runs without any installation and
offers the same commands as the program file, the self-test on the
bundled test recording included (REQ024). Each executable shall be built
on its own platform from the same package sources, and a release shall
carry an executable only if the self-test passed on that executable on
its own platform. The README shall name the platforms and what users must
do because the executables are not code-signed.

*Parent links: NEED001, NEED006*

*Child links: DES025*

# 22 Equivalence self-test _(REQ024)_ {#REQ024}

The program shall offer a self-test (command `selftest`) that proves on the
user's own computer, with the user's own installation, that the program
reproduces the vendor's EDF export:

1. without arguments, on the test recording bundled with the program
   (REQ023) or, in a repository checkout, on the same public recording,
   after verifying the SHA-256 checksum of every bundled file;
2. given a native Cadwell recording and the vendor's EDF export of it, on
   the user's data, so that users can check recordings made with other
   amplifiers or Cadwell software versions. The recording shall be
   converted even if its storage schema version is not a supported one
   (REQ018); the self-test then reports this as a warning.

The self-test shall convert in vendor-compatible mode (REQ020) over the
vendor export's own time range: it shall identify the frames the export
covers from its start time and record count (the export may cover only
part of the recording) and the UTC offset of its start time (given by the
user, or inferred when only one offset matches a frame), and it shall
say so, rather than compare, when the EDF file does not match the
recording. It shall read the vendor's file with its own EDF reader and
compare, reporting each as a check that passes or fails:

- the signals: number, labels, sampling rates, physical and digital
  ranges; the record duration and the number of records;
- the start date and time, to 1 ms;
- every sample, as digital value: pass if none differs by more than one
  quantisation step; the share of bit-identical samples shall be reported;
- the gain (least-squares ratio of the vendor's samples to the program's)
  and the time lag (the shift, in samples, that best aligns the two), so
  that scale and timing errors too small to exceed one quantisation step
  are also found;
- the annotations: onset to 1 ms and text.

It shall print one line per check and an overall verdict, return exit
code 0 only if every check passes, and optionally write a JSON report and
keep its own EDF file. It shall not print or store the patient
identification fields of either file.

*Parent links: NEED001, NEED003*

*Child links: DES024*

