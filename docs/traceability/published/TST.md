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

# 1.0 EDF structural validity _(TST001)_ {#TST001}

Convert each test recording and open the result with two independent EDF
readers (pyedflib and MNE-Python). Pass if both read the file without
header warnings and report the expected number of channels and duration.

*Parent links: REQ002, REQ010*

# 2.0 Header equivalence with native EDF export _(TST002)_ {#TST002}

For each test recording compare our EDF header with the native Cadwell EDF
export: channel labels (after the documented mapping), sampling rates,
physical dimensions, physical/digital ranges, start date/time, patient and
recording identification. Pass if all match exactly, except fields that the
mapping table documents as intentionally different.

*Parent links: REQ003, REQ004, REQ008*

# 3.0 Sample equivalence with native EDF export _(TST003)_ {#TST003}

For each test recording and each channel compare all physical sample values
of our EDF export with the native EDF export. Pass if the number of samples
matches (within the documented edge tolerance) and the maximum absolute
difference does not exceed one digital quantisation step of the native
export. Report the maximum and mean difference per channel.

*Parent links: REQ003, REQ008*

# 4.0 Annotation equivalence with native EDF export _(TST004)_ {#TST004}

For each test recording compare the EDF+ annotation lists (onset, duration,
text) of our export and the native export. Pass if the sets are equal after
normalising whitespace; list every unmatched annotation on failure.

*Parent links: REQ005, REQ008*

# 5.0 Sample equivalence with native CSV/text export _(TST005)_ {#TST005}

For each test recording parse the native CSV/text export, map its column
names to EDF channel labels, and compare the physical values with our EDF
export over the common time range. Pass if the maximum absolute difference
is within the numeric precision of the text export and every column maps to
exactly one channel.

*Parent links: REQ009*

# 6.0 Command-line behaviour _(TST006)_ {#TST006}

Run the CLI on a valid recording, on a non-existent path, on a corrupt
file and on an unsupported version. Pass if the valid run returns exit
code 0 and a valid JSON report when requested, and every invalid run
returns a non-zero exit code, prints a diagnostic and leaves no output
file behind.

*Parent links: REQ006, REQ018*

# 7.0 Anonymisation _(TST007)_ {#TST007}

Convert a test recording with the anonymisation option. Pass if the patient
identification fields contain only the supplied or placeholder values, no
annotation contains the original patient name or identifier, and the signal
data is identical to a conversion without the option.

*Parent links: REQ014*

# 8.0 Test data manifest and graceful skip _(TST008)_ {#TST008}

Verify that every file under `testdata/private/` listed in the manifest
matches its recorded SHA-256 checksum, and that when the folder is absent
all data-dependent tests are reported as skipped with an explanatory
message rather than failing.

*Parent links: REQ007, REQ011*

# 9.0 Traceability validation _(TST009)_ {#TST009}

Run `doorstop` on `docs/traceability/`. Pass if it reports no errors, every
normative REQ item links to at least one NEED item, and every normative REQ
item is linked from at least one TST item.

*Parent links: REQ013*

# 10 LLM log integrity _(TST010)_ {#TST010}

Verify that every session folder under `llm-logs/` contains a transcript
and is listed in `llm-logs/sessions.csv`, that every session in
`sessions.csv` has a folder, and that `llm-logs/tools/llmlog.py index`
regenerates the derived files without error.

*Parent links: REQ012*

# 11 Environment setup _(TST011)_ {#TST011}

On a fresh clone run `./setup.sh`. Pass if it completes without error,
`.venv/bin/doorstop --version` prints the pinned version, and `.venv` is
ignored by git.

*Parent links: REQ017*

# 12 Licence compatibility check _(TST012)_ {#TST012}

Inspect the LICENSE file and the headers of every ported third-party source
file. Pass if the repository licence permits every ported file's licence
and each ported file carries its original copyright and licence notice.

*Parent links: REQ015*

# 13 Downstream use scaffolds present _(TST013)_ {#TST013}

Check that `uses/Morgoth`, `uses/SCOREAI` and `uses/EEGLAB` exist, each with
a README that states status and prerequisites, and that each provided
script runs its `--help` or dry-run mode without error.

*Parent links: REQ016*

# 14 Supported-version coverage _(TST014)_ {#TST014}

Check that the documented list of supported Cadwell software versions is
non-empty and that every listed version is represented by at least one
recording in the test data manifest.

*Parent links: REQ001*

# 15 Gap handling _(TST015)_ {#TST015}

Using a test recording that contains at least one acquisition gap (or a
recording with an artificially introduced gap if none is available),
convert with both the discontinuous and the padded option. Pass if the
segment boundaries match the native export's time segments, padded samples
carry the documented fill value and a gap annotation, and the per-segment
sample equivalence test (TST003) passes for every segment.

*Parent links: REQ008, REQ019*

