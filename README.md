# CwellEEGRead

Convert clinical EEG recordings from the proprietary Cadwell format
(Cadwell Arc / Easy III, recordings from around 2020 onward, stored as
SQLite `.ezdata` files) to the open EDF/EDF+ format, with automated proof
that the conversion is equivalent to the vendor's own export - so that
clinically recorded EEGs can be analysed with research tools such as
SCORE-AI, the Morgoth foundation model, EEGLAB, FieldTrip and MNE.

**Status: converter working on the public test recordings.**
`cwelleegread convert <export> out.edf` reads a CadLink study export and
writes EDF+ (plain EDF when nothing needs EDF+); `cwelleegread batch <folder>
<outdir>` converts every recording below a folder. The decoder is verified
sample-for-sample against the vendor's text export, and the
vendor-compatible mode reproduces the vendor's own EDF export to within one
quantisation step, including its annotations and start time
(`tests/test_convert_public.py`). Channel labels come from per-headbox tables
(Apollo, Essentia) selected by the amplifier type in the file; other
headboxes need `--labels`. Not yet handled: a user-chosen time range,
anonymisation beyond the header and typed-text event types.

`cwelleegread selftest` proves on the user's own computer that the
vendor-compatible mode reproduces the vendor's EDF export, on the bundled
public recording or, with `selftest <export> <vendor.edf>`, on the user's
own recording and its vendor EDF (any part of the recording), so that
other amplifiers and Cadwell versions can be checked (REQ024). A
**standalone** single-file build, `cwelleegread.pyz` with the self-test
recording inside, needs only Python with numpy and scipy
(`uses/standalone/`, REQ023); the standalone executables for Windows,
macOS and Linux need nothing installed (REQ025).

```bash
./setup.sh && source .venv/bin/activate      # installs the `cwelleegread` command into .venv
cwelleegread inspect testdata/public/cadwell-export2
cwelleegread convert testdata/public/cadwell-export2 out.edf --timezone Europe/Oslo --json out.json
cwelleegread convert testdata/public/cadwell-export1 out.edf --mode vendor --timezone Europe/Oslo
cwelleegread batch /path/to/exports edf-out/ --reports --json edf-out/batch.json
cwelleegread selftest                                       # bundled recording vs its vendor EDF
cwelleegread selftest testdata/public/cadwell-export3 testdata/public/cadwell-export3/export-edf/cadwell3.edf
```

`python -m cwelleegread ...` works too. Exit code 0 means success; batch mode
continues past a failing recording, lists it in the summary and exits 1.

**Supported versions.** Only recordings whose storage schema (the last
`SchemaUpdateLog` entry, shown by `inspect`) has been verified on a test
recording are converted; others are refused unless `--allow-unsupported` is
given (a warning then goes into the report). `selftest` converts any version
and shows whether it reproduces the vendor's EDF export.

| Schema | Cadwell software | Test recordings (`testdata/manifest.json`) |
|---|---|---|
| 2.5 | Arc (version not recorded, 2025); Arc 3.2.1097 (2026) | cadwell-export1 (Apollo, 250 Hz); cadwell-export2, -3, -3-withfilter (Essentia, 500 Hz) |

**Recording gaps.** A gap (recording stopped and restarted) is written as
the vendor does: zeros inside a continuous EDF+C, with a `Recording gap N s
(padded with zeros)` annotation, which every EDF reader handles.
`--gaps discontinuous` (raw mode) writes **EDF+D** instead: the gap
seconds are left out and each data record carries its true onset. EDFbrowser
reads EDF+D correctly, but EDFlib/pyedflib refuses it and MNE-Python (1.13)
reads it as if it were continuous, silently shifting everything after a gap
earlier by the gap length.

**Filters.** The converter applies no filter in raw mode. In `--mode
vendor` on Essentia recordings (or with `--highpass on`) it applies the
high-pass the vendor's EDF export uses (identified as a 2nd-order
Butterworth at 0.16 Hz) and writes `HP: unknown (0.16 Hz?)` into the EDF
prefilter field; the vendor itself leaves that field empty.

Events are placed on the amplifier's sample clock by default (`--event-timing
ticks`); the vendor's EDF export places them by a wall-clock stamp that runs
about 96 ppm behind the sample clock on Essentia recordings, so its
annotations sit early by up to 0.35 s per hour. `--event-timing stamp`
reproduces the vendor's placement and is the default in `--mode vendor`
(REQ021, `docs/research/cadwell-file-format.md`, "Two clocks").

## Releases

The repository holds more than one product, and each is released on its
own through GitHub releases with a product-specific tag prefix. A release
carries only that product's asset (GitHub adds "Source code" archives of the
whole repository to every release, which can be ignored).

| Product | Tag | Asset | Workflow |
|---|---|---|---|
| EEGLAB plugin `cadwellio` | `cadwellio-v<version>` (version = `vers` in `eegplugin_cadwellio.m`) | `cadwellio<version>.zip` | `.github/workflows/release-cadwellio.yml` |
| Python converter `cwelleegread` | `cwelleegread-v<version>` (planned; version = `__version__`) | wheel / sdist | not yet |
| Standalone converter | `cwelleegread-standalone-v<version>` (version = `__version__`; 0.2.0 released) | `cwelleegread-standalone-<version>.zip` (`cwelleegread.pyz`, README, LICENSE) and, from 0.3.0, executables `cwelleegread-<version>-windows-x64.exe`, `-macos-arm64`, `-linux-x64` (REQ025); published only after the self-test passed on each, on its platform | `.github/workflows/release-standalone.yml` |

## Repository layout

| Path | What |
|---|---|
| `docs/traceability/` | Requirements managed with [Doorstop](https://doorstop.readthedocs.io): `needs/` (NEED), `requirements/` (REQ), `design/` (DES, how each requirement is implemented), `tests/` (TST). Readable copies in `docs/traceability/published/*.md`, the whole tree as `docs/traceability/published/CwellEEGRead-traceability.pdf`. |
| `docs/research/` | Research notes: the Cadwell file format, the BioSig toolbox and licensing, downstream uses. |
| `llm-logs/` | Archive of every Claude Code session (prompts, responses, full transcripts) and `sessions.csv`. Filled automatically by hooks in `.claude/`. |
| `cwelleegread/` | the Python package: `ezdata.py` reads a CadLink export (index, frames, events, supported schema versions); `layout.py` amplifier-input labels; `edf.py` conversion policies; `edfwrite.py` EDF / EDF+C / EDF+D writer; `edfread.py` EDF reader and `selftest.py` equivalence self-test; `__main__.py` CLI (`convert`, `batch`, `inspect`, `selftest`). `pyproject.toml` makes it installable with the `cwelleegread` command. |
| `tools/` | `cadwell_inspect.py`: stdlib inventory of a CadLink export. |
| `tests/` | pytest suite, incl. `test_ezdata_public.py` (decoder vs vendor text/EDF export). Private-data tests skip until the recordings are present. Run on every push by `.github/workflows/tests.yml`. |
| `testdata/` | `manifest.json` (every test recording with checksums, schema and Cadwell version), `public/` (non-patient recordings, committed), `private/` (clinical recordings, gitignored). |
| `uses/` | Downstream-use scaffolds: `Morgoth/`, `SCOREAI/`, `EEGLAB/`; `standalone/`: README and build script of the standalone converter. |
| `setup.sh`, `requirements-dev.txt` | One-command developer setup into a gitignored `.venv`. |

## Getting started

```bash
./setup.sh                      # venv + Doorstop + pytest, validates the requirement tree
source .venv/bin/activate
doorstop                        # validate requirements
doorstop publish all docs/traceability/published/html   # browsable HTML (gitignored)
pytest                          # run the tests
```

## Working with requirements

```bash
doorstop add REQ                # new requirement (edit the YAML it creates)
doorstop link TST015 REQ019     # trace a test to a requirement
doorstop review all             # mark reviewed after editing
for d in NEED REQ DES TST; do doorstop publish $d docs/traceability/published/$d.md; done
tools/doorstop_pdf.sh           # the committed PDF of NEED, REQ, DES, TST and the traceability matrix
```

## Licence

Public domain (Unlicense), see `LICENSE`. The BioSig toolbox was examined as
a possible source of a Cadwell reader; it turns out to contain no working
decoder, so nothing is ported and the licence stays as is. See
`docs/research/biosig-cadwell-reader.md` and REQ015.
