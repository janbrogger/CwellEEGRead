# uses/Morgoth - run the Morgoth EEG foundation model on converted EDF files

**Status:** scaffold. `install.sh` and `run.sh` were written from the public
repository (https://github.com/bdsp-core/morgoth, checked 2026-09-15) and
have not yet been executed end to end here, because the model weights
require credentialed access. Expect to adjust package pins.

**Prerequisites**

- A BDSP account with credentialed access to `morgoth1`
  (https://bdsp.io/content/morgoth1/1.0.0/): CITI training, signed data use
  agreement, AWS account id registered, then `aws s3 sync
  s3://bdsp-opendata-credentialed/morgoth1/models/ checkpoints/ --profile
  bdsp-credentialed`.
- Linux with conda (Miniforge is fine); a CUDA 12.4 GPU is recommended, CPU
  works but is slow.
- EDF files with the 19 standard 10-20 channels (Fp1, F3, C3, P3, F7, T3/T7,
  T5/P7, O1, Fz, Cz, Pz, Fp2, F4, C4, P4, F8, T4/T8, T6/P8, O2) in µV.
  Morgoth itself resamples to 200 Hz, filters 0.5-70 Hz, notches 50/60 Hz
  and applies a common-average montage.
- Licence: Morgoth is CC BY-NC 4.0 (no commercial use).

**Files**

| File | Purpose |
|---|---|
| `install.sh` | clone the repository into `morgoth/` (gitignored), create the conda env `morgoth`, install requirements |
| `run.sh` | run event-level and EEG-level prediction for one task on a folder of EDF files; `--dry-run` prints the commands |
| `morgoth_to_json.py` | merge Morgoth's CSV outputs for one EDF into a single JSON document |

**Usage**

```bash
./install.sh                                  # once
# copy the credentialed checkpoints into morgoth/checkpoints/
./run.sh --task NORMAL --edf-dir ../../out/edf --out out/            # GPU
./run.sh --task NORMAL --edf-dir ../../out/edf --out out/ --cpu      # CPU
python3 morgoth_to_json.py out/ > out/morgoth-results.json
```

Tasks: `NORMAL`, `BS` (burst suppression), `SPIKES`, `FOC_GEN_SPIKES`,
`SLOWING`, `IIIC`, `MGBSLEEP3stages`, `SLEEPPSG`. Each needs its
`checkpoints/<TASK>.pth` and, for the EEG-level summary, `<TASK>_EEGlevel.pth`.
Recordings longer than about 10 minutes should be segmented first with
Morgoth's `segment_long_eeg.py` (see its README); `run.sh --segment` does this.
