# Test recordings

The equivalence tests (REQ007-REQ009, TST002-TST005, TST008) need, for each
test EEG, three files produced from the **same** recording:

| Key in manifest | What | Produced by |
|---|---|---|
| `cadwell` | the native Cadwell recording (`.ezdata` family; a folder if the study is multi-file) | copied from the Cadwell system |
| `native_edf` | the same recording exported to EDF | the Cadwell application's EDF export |
| `native_csv` | the same recording exported to CSV/text | the Cadwell application's text export |

There are two places for them (REQ007):

- `public/` - recordings **without patient data** (amplifier noise,
  volunteers recorded under a placeholder name). Committed, so every clone
  runs the equivalence tests. Each has a README describing the export.
- `private/` - clinical recordings of real patients. **Never committed**
  (gitignored), supplied out of band.

Every recording, public or private, is described in `manifest.json`, which
**is** committed and contains only names, sizes, checksums, the storage
schema version (`cwelleegread inspect` shows it) and the Cadwell software
version; `location` says which folder the file names are relative to:

```json
{
  "recordings": [
    {
      "id": "eeg01",
      "location": "private",
      "schema_version": "2.5",
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
placing the files; `tests/test_manifest.py` verifies the public ones on
every run, and the `testdata` fixture the private ones when present. When
`private/` is absent, the tests needing it skip with a message instead of
failing (REQ011). A new storage schema version becomes supported only with a
test recording for it (TST014): add the recording, then the version to
`SUPPORTED_SCHEMA_VERSIONS` in `cwelleegread/ezdata.py`.

Please also record, for each export, the export settings you chose in the
Cadwell application (montage/reference, filters on or off, sampling rate,
time range, annotation options): the equivalence tests must compare like
with like, and unfiltered, referential, full-rate exports are the most
useful ground truth.
