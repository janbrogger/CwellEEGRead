# Working conventions for this repository

- **Purpose**: convert Cadwell EEG (`.ezdata`, SQLite-based, 2020+) to EDF/EDF+
  with automated equivalence tests against the vendor's own EDF and CSV
  exports. See `README.md` and `docs/traceability/published/REQ.md`.
- **Requirements first**: behaviour changes start as Doorstop items in
  `docs/traceability/` (chain NEED -> REQ -> DES -> TST). Run `.venv/bin/doorstop`
  before committing; keep `docs/traceability/published/*.md` regenerated.
- **LLM provenance**: hooks in `.claude/settings.json` archive every session
  into `llm-logs/<session_id>/`. Never delete or hand-edit files there
  except the `topic` column of `llm-logs/sessions.csv`. If hooks did not
  run, archive manually: `python3 llm-logs/tools/llmlog.py archive
  --session-id <id> --transcript <path>`.
- **Patient data**: test recordings live only under `testdata/private/`
  (gitignored). Never commit EEG files, never paste patient identifiers or
  raw EEG dumps into a session.
- **Python**: everything runs from the gitignored `.venv` created by
  `./setup.sh`; pin new dependencies in `requirements-dev.txt` (tooling)
  or a future `requirements.txt` (runtime).
- **Tests**: `pytest`; data-dependent tests must skip, not fail, when the
  private test data is absent.
- **Licence**: Unlicense. Do not copy code from GPL sources (BioSig) into
  this repo without an explicit relicensing decision recorded in
  `docs/research/`.
