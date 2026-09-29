# CwellEEGRead

Convert clinical EEG recordings from the proprietary Cadwell format
(Cadwell Arc / Easy III, recordings from around 2020 onward, stored as
SQLite `.ezdata` files) to the open EDF/EDF+ format, with automated proof
that the conversion is equivalent to the vendor's own export - so that
clinically recorded EEGs can be analysed with research tools such as
SCORE-AI, the Morgoth foundation model, EEGLAB, FieldTrip and MNE.

**Status: converter working on the two public test recordings.**
`python -m cwelleegread convert <export> out.edf` reads a CadLink study
export and writes EDF+C. The decoder is verified sample-for-sample against
the vendor's text export, and the vendor-compatible mode reproduces the
vendor's own EDF export to within one quantisation step, including its
annotations and start time (`tests/test_convert_public.py`). Recording
gaps are padded with zeros as the vendor does (export 3). Channel labels
come from per-headbox tables (Apollo, Essentia) selected by the amplifier
type in the file; other headboxes need `--labels`. Not yet handled: a
user-chosen time range, EDF+D output, anonymisation beyond the header.

```bash
./setup.sh && source .venv/bin/activate
python -m cwelleegread inspect testdata/public/cadwell-export2
python -m cwelleegread convert testdata/public/cadwell-export2 out.edf --timezone Europe/Oslo --json out.json
python -m cwelleegread convert testdata/public/cadwell-export1 out.edf --mode vendor --timezone Europe/Oslo
```

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

## Repository layout

| Path | What |
|---|---|
| `docs/traceability/` | Requirements managed with [Doorstop](https://doorstop.readthedocs.io): `needs/` (NEED), `requirements/` (REQ), `tests/` (TST). Readable copies in `docs/traceability/published/*.md`. |
| `docs/research/` | Research notes: the Cadwell file format, the BioSig toolbox and licensing, downstream uses. |
| `llm-logs/` | Archive of every Claude Code session (prompts, responses, full transcripts) and `sessions.csv`. Filled automatically by hooks in `.claude/`. |
| `cwelleegread/` | the Python package: `ezdata.py` reads a CadLink export (index, frames, events); `layout.py` amplifier-input labels; `edf.py` conversion policies; `edfwrite.py` EDF+ writer; `__main__.py` CLI. |
| `tools/` | `cadwell_inspect.py`: stdlib inventory of a CadLink export. |
| `tests/` | pytest suite, incl. `test_ezdata_public.py` (decoder vs vendor text/EDF export). Private-data tests skip until the recordings are present. |
| `testdata/` | Manifest and instructions for the out-of-band test recordings (the recordings themselves are gitignored). |
| `uses/` | Downstream-use scaffolds: `Morgoth/`, `SCOREAI/`, `EEGLAB/`. |
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
for d in NEED REQ TST; do doorstop publish $d docs/traceability/published/$d.md; done
tools/doorstop_pdf.sh           # one PDF of NEED, REQ, TST and the traceability matrix (needs Chromium)
```

## Licence

Public domain (Unlicense), see `LICENSE`. The BioSig toolbox was examined as
a possible source of a Cadwell reader; it turns out to contain no working
decoder, so nothing is ported and the licence stays as is. See
`docs/research/biosig-cadwell-reader.md` and REQ015.
