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

*Child links: TST014*

# 2.0 Output: EDF/EDF+ files _(REQ002)_ {#REQ002}

The program shall write European Data Format files conforming to the EDF
specification (Kemp et al. 1992) and, when annotations are present, to the
EDF+ specification (Kemp & Olivan 2003). Output files shall be readable by
at least two independent EDF readers (e.g. EDFbrowser and pyedflib or
MNE-Python) without warnings about header validity.

*Parent links: NEED002*

*Child links: TST001*

# 3.0 Signal fidelity _(REQ003)_ {#REQ003}

For every EEG channel in the source recording the program shall preserve:
the channel label, the sampling rate, the physical dimension (microvolts),
the physical and digital minimum/maximum, and every sample value. No
filtering, resampling, re-referencing or truncation shall be applied unless
explicitly requested on the command line, and any such processing shall be
recorded in the EDF header's prefiltering field.

*Parent links: NEED003*

*Child links: TST002, TST003*

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

*Child links: TST002*

# 5.0 Events and annotations _(REQ005)_ {#REQ005}

Events stored in the Cadwell recording (technician comments, seizure or
event markers, photic stimulation and hyperventilation markers, montage
or impedance events) shall be exported as EDF+ annotations with onset
times accurate to one sample, and with their text preserved. Event types
that cannot be mapped shall be listed in the conversion report.

*Parent links: NEED002, NEED003*

*Child links: TST004*

# 6.0 Command-line interface _(REQ006)_ {#REQ006}

The program shall provide a command-line interface of the form
`cwelleegread convert <cadwell-input> <output.edf>` that converts a single
recording, plus a batch mode that converts every recording under a folder.
It shall return exit code 0 on success and non-zero on any failure, and
shall optionally emit a machine-readable JSON conversion report (input
identity, channels, duration, events, warnings) for use by downstream
scripts.

*Parent links: NEED001, NEED006*

*Child links: TST006*

# 7.0 Test data set supplied out of band _(REQ007)_ {#REQ007}

Development shall use a small set of test EEGs supplied outside the
repository, each consisting of (a) the recording in native Cadwell format,
(b) the same recording exported to EDF by the native Cadwell application
and (c) the same recording exported to CSV/text by the native Cadwell
application. The test data shall live under `testdata/private/` (gitignored);
the repository shall contain only a manifest with file names, sizes,
SHA-256 checksums and the Cadwell software version that produced them.

*Parent links: NEED003, NEED005*

*Child links: TST008*

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

*Child links: TST002, TST003, TST004, TST015*

# 9.0 Proven equivalence with the native CSV/text export _(REQ009)_ {#REQ009}

An automated test shall prove that the physical sample values in the
program's EDF export are equal, within the precision of the text export,
to the values in the native Cadwell CSV/text export of the same recording,
channel by channel, over the full common time range. The test shall also
verify that the channel names in the text export map one-to-one onto the
EDF channel labels.

*Parent links: NEED003*

*Child links: TST005*

# 10 Round-trip self-consistency _(REQ010)_ {#REQ010}

The EDF file written by the program shall, when read back by an independent
EDF reader, yield the same channel labels, sampling rates, start time and
sample values (within EDF's 16-bit quantisation) as the data the program
held in memory before writing.

*Parent links: NEED003*

*Child links: TST001*

# 11 Automated test execution _(REQ011)_ {#REQ011}

All equivalence and validity tests shall run under `pytest`. Tests that
need the out-of-band test data shall skip with an explicit message when the
data is absent, so that the remaining tests can run in continuous
integration and on machines without access to patient data.

*Parent links: NEED004*

*Child links: TST008*

# 12 LLM session provenance _(REQ012)_ {#REQ012}

Every Claude Code session that touches the repository shall be archived
automatically into `llm-logs/<session_id>/` (full transcript, prompts as
CSV, prompts and responses as Markdown) and indexed in
`llm-logs/sessions.csv`, without manual steps, so that the complete history
of prompts and responses is available in the repository.

*Parent links: NEED004*

*Child links: TST010*

# 13 Requirements traceability _(REQ013)_ {#REQ013}

Requirements shall be managed with Doorstop in `docs/traceability/` as a
chain NEED -> REQ -> TST. Every normative requirement shall link to at
least one need and shall be covered by at least one test specification, and
`doorstop` validation shall pass with no errors before a release.

*Parent links: NEED004*

*Child links: TST009*

# 14 Anonymisation option _(REQ014)_ {#REQ014}

The program shall offer a command-line option that replaces the patient
identification fields in the EDF header (name, patient code, birth date,
sex) with the values given by the user or with anonymous placeholders, and
that removes patient-identifying text from exported annotations, without
altering the signal data.

*Parent links: NEED005*

*Child links: TST007*

# 15 Licence compatibility _(REQ015)_ {#REQ015}

The repository's licence shall be compatible with every third-party source
ported into it. If code from the BioSig toolbox (GPL-3.0-or-later) is
ported, the repository shall be relicensed under a GPL-compatible licence
and the decision shall be recorded in `docs/research/` and in the LICENSE
file, including attribution of the original authors.

*Parent links: NEED007*

*Child links: TST012*

# 16 Downstream use scaffolds _(REQ016)_ {#REQ016}

The repository shall contain a `uses/` folder with one sub-folder per
downstream use: `uses/Morgoth` (scripts to check out, install and run the
Morgoth foundation model on converted EDF files), `uses/SCOREAI` (scripts
to call an externally supplied SCORE-AI command-line program on converted
EDF files and collect its JSON output) and `uses/EEGLAB` (an EEGLAB reader
plugin that can be packaged as a zip file). Each sub-folder shall have a
README stating its status and prerequisites.

*Parent links: NEED006*

*Child links: TST013*

# 17 Reproducible development environment _(REQ017)_ {#REQ017}

All Python tooling shall be installed into a gitignored virtual environment
from pinned requirement files by a single `setup.sh` script, so that a
fresh checkout can be brought to a working state with one command.

*Parent links: NEED004*

*Child links: TST011*

# 18 Clear failure on unsupported input _(REQ018)_ {#REQ018}

When given a recording it cannot fully convert (an unsupported Cadwell
version, a corrupt or truncated database, an unknown waveform encoding),
the program shall stop with a diagnostic message naming the problem and a
non-zero exit code, and shall not leave a partial EDF file that could be
mistaken for a complete conversion.

*Parent links: NEED003*

*Child links: TST006*

# 19 Recording gaps and discontinuities _(REQ019)_ {#REQ019}

Cadwell recordings can contain gaps (recording stopped and restarted); the
index then lacks the frame numbers of the gap and holds a GapInfo row. The
program shall detect gaps from the frame numbering and represent them in
the EDF output, by default as the vendor's own export does: a continuous
EDF+C file in which the missing seconds are written as digital zero at the
frame boundaries so that the time axis and every annotation stay aligned
with wall-clock time, plus an annotation "Recording gap N s (padded with
zeros)" at the gap start. A discontinuous EDF+D representation may be
offered as an option later. The gaps shall be listed in the conversion
report, and the equivalence tests shall compare segment by segment so that
gap handling differences are explicit rather than hidden.

*Parent links: NEED003*

*Child links: TST015*

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

*Child links: TST003*

