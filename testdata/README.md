# Test recordings (supplied out of band - never committed)

The equivalence tests (REQ007-REQ009, TST002-TST005, TST008) need, for each
test EEG, three files produced from the **same** recording:

| Key in manifest | What | Produced by |
|---|---|---|
| `cadwell` | the native Cadwell recording (`.ezdata` family; a folder if the study is multi-file) | copied from the Cadwell system |
| `native_edf` | the same recording exported to EDF | the Cadwell application's EDF export |
| `native_csv` | the same recording exported to CSV/text | the Cadwell application's text export |

Put them under `testdata/private/` (gitignored - these are clinical
recordings of real patients) and describe them in `testdata/manifest.json`,
which **is** committed and contains only names, sizes, checksums and the
Cadwell software version:

```json
{
  "recordings": [
    {
      "id": "eeg01",
      "cadwell_software_version": "Arc 3.x (fill in from the application's About box)",
      "notes": "routine 20-min EEG, 19 channels + ECG, photic + HV",
      "cadwell":    {"file": "eeg01/eeg01.ezdata", "sha256": "...", "bytes": 0},
      "native_edf": {"file": "eeg01/eeg01.edf",    "sha256": "...", "bytes": 0},
      "native_csv": {"file": "eeg01/eeg01.csv",    "sha256": "...", "bytes": 0}
    }
  ]
}
```

Generate the checksums with `python3 testdata/make_manifest.py` after
placing the files. When the folder is absent, all data-dependent tests skip
with a message instead of failing (REQ011).

Please also record, for each export, the export settings you chose in the
Cadwell application (montage/reference, filters on or off, sampling rate,
time range, annotation options): the equivalence tests must compare like
with like, and unfiltered, referential, full-rate exports are the most
useful ground truth.
