# uses/SCOREAI - run SCORE-AI on converted EDF files

**Status:** scaffold. SCORE-AI (Tveit J, Aurlien H, Plis S, et al. *Automated
interpretation of clinical electroencephalograms using artificial
intelligence.* JAMA Neurol 2023;80:805-812) is commercialised as autoSCORE
inside Natus software; no public command-line program, API or weights exist.
This folder therefore contains a wrapper for a SCORE-AI program **supplied
elsewhere**, plus input checks based on what is published about the model.

**Prerequisites**

- A SCORE-AI command-line program obtained separately, invoked through the
  command template in `SCOREAI_CMD` (see below).
- Python 3.9+ and `pyedflib` (for the input checks; `pip install pyedflib`).
- Input EDF/EDF+ files that meet the published input assumptions: routine
  EEG of roughly 20-30 minutes, referential, all 19 electrodes of the
  10-20 system (T3/T4/T5/T6 or T7/T8/P7/P8 naming) plus one ECG channel,
  signals in µV, patients older than 3 months.

**Usage**

```bash
export SCOREAI_CMD='/opt/scoreai/scoreai --input {edf} --output {json}'   # your program
python3 run_scoreai.py recording.edf                # writes recording.scoreai.json
python3 run_scoreai.py --check-only recording.edf   # only validate the input
python3 run_scoreai.py --dry-run recording.edf      # print the command that would run
python3 run_scoreai.py --batch ../../out/edf/       # all EDFs in a folder
```

`{edf}` and `{json}` in the template are replaced with the input path and
the output path. The program's JSON output is stored verbatim under
`"raw"`; if it contains the well-known fields, they are copied to a
normalised block:

```json
{
  "input": {"file": "...", "sha256": "...", "checks": [...]},
  "scoreai": {"normal": 0.12, "abnormal": 0.88,
              "epileptiform_focal": 0.71, "epileptiform_generalized": 0.03,
              "nonepileptiform_focal": 0.10, "nonepileptiform_diffuse": 0.05},
  "raw": {...}, "provenance": {"command": "...", "started_utc": "...", "exit_code": 0}
}
```
