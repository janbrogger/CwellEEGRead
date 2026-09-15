# CwellEEGRead

Convert clinical EEG recordings from the proprietary Cadwell format
(Cadwell Arc / Easy III, recordings from around 2020 onward, stored as
SQLite `.ezdata` files) to the open EDF/EDF+ format, with automated proof
that the conversion is equivalent to the vendor's own export - so that
clinically recorded EEGs can be analysed with research tools such as
SCORE-AI, the Morgoth foundation model, EEGLAB, FieldTrip and MNE.

**Status: reader working, writer not started.** `cwelleegread/ezdata.py`
decodes the Cadwell frame format (verified sample-for-sample against the
vendor's text export on `testdata/public/cadwell-export1`); EDF writing and
the command line are next. `tools/cadwell_inspect.py` prints an inventory
of any CadLink export.

## Repository layout

| Path | What |
|---|---|
| `docs/traceability/` | Requirements managed with [Doorstop](https://doorstop.readthedocs.io): `needs/` (NEED), `requirements/` (REQ), `tests/` (TST). Readable copies in `docs/traceability/published/*.md`. |
| `docs/research/` | Research notes: the Cadwell file format, the BioSig toolbox and licensing, downstream uses. |
| `llm-logs/` | Archive of every Claude Code session (prompts, responses, full transcripts) and `sessions.csv`. Filled automatically by hooks in `.claude/`. |
| `cwelleegread/` | the Python package: `ezdata.py` reads a CadLink export (index, frames, events) into numpy arrays in µV. |
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
```

## Licence

Public domain (Unlicense), see `LICENSE`. The BioSig toolbox was examined as
a possible source of a Cadwell reader; it turns out to contain no working
decoder, so nothing is ported and the licence stays as is. See
`docs/research/biosig-cadwell-reader.md` and REQ015.
