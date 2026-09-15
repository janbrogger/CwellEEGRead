# cadwell-export1 - first public test recording (synthetic noise, no patient)

A 46-second, 32-channel, 250 Hz recording made on a Cadwell Arc system on
2025-10-31 with no electrodes attached (amplifier noise), patient "test,
test", then exported three ways from Arc Review / CadLink. Everything here
is committed on purpose: it contains no real patient data.

| Path | What | Notes |
|---|---|---|
| `export-screen1..9.png` | screenshots of the export dialogs | text export: unit mV, header "Channel Name", anonymise on, 14:37:50-14:38:20; EDF+ export: all 32 channels, anonymise off, 14:37:50-14:38:34; study export: EEG data only, video unchecked, integrity report included |
| `edf/Metadata.json` | side-car written by the EDF+ export | `EDFType: EDFPlusContinuous`, events included, patient info included, `AssociatedFiles: ["test.edf"]`, times as microseconds since the Unix epoch (UTC) |
| `edf/test.edf` | the native EDF+C export, 32 signals, 44 s, 17.17 µV/step | resampled to exactly 250/s (see research note) |
| `test/test-eeg20251031.txt` | native tab-delimited text export | see below |
| `native-export/test-eeg311025.export` | 1-byte manifest ("A") that Arc uses to recognise an export folder | |
| `native-export/CadLink/StandAlone.txt` | three base64/hex tokens and `True` | CadLink stand-alone install marker; not needed |
| `native-export/CadLink/ExternalData/<patient> <date>/*.arc`, `*.flex` | 37-byte text files containing only the record GUID | pointers, no data |
| `native-export/CadLink/Databases/Core.db`, `EEG.db`, `Logging.db` | CadLink catalogue databases | **encrypted** (8.0 bits/byte entropy, not SQLite-readable); not needed for waveform data |
| `native-export/CadLink/Data/<guid>-2025-10-31-13-37-42.ezdataindex` | SQLite: frame index, track definition, amp layout | see `docs/research/cadwell-file-format.md` |
| `native-export/CadLink/Data/<guid>-2025-10-31-13-37-42.ezevents` | SQLite: 14 events | |
| `native-export/CadLink/Data/<guid>-2025-10-31-13-37-42-1.ezdata` | SQLite: the 45 EEG waveform frames (delta-compressed) | decoded by `cwelleegread/ezdata.py`; `tests/test_ezdata_public.py` proves equality with the text export |
| `native-export/CadLink/Data/<guid>.mediadb`, `<guid>-1.mediadb` | SQLite: video frame index and 52 video frames (4.9 MB) from the two Hikvision cameras | present although "Video" was unchecked in the export dialog |
| `native-export/CadLink/Data/Data Integrity Report (...).pdf` | one-page report: 46 s elapsed, start 14:37, stop 14:38 | |

Record GUID: `56659ea9-99fd-4d8d-a85c-7502a29229e6`. Times inside the
databases are UTC (13:37:50); the Arc user interface and the text export
show local time (14:37:50, UTC+1).

## Text export facts (ground truth for TST005)

- 13 header lines starting with `%`, then one row per sample, tab-separated,
  decimal comma (Norwegian locale), 4 decimals, unit mV (so 0.1 µV
  resolution).
- Column 1 is a wall-clock time stamp with 1-second resolution; 7755 rows
  over 31 time stamps (248 rows in the first second, 250 or 251 in the
  others), so the row count, not the time stamp, gives the sample index.
- 32 data columns, but the `% Date.Time` header line lists 35 labels
  (`E1 E2 Fp1 Fp2 T1 F7 F3 Fz F4 F8 T2 A1 T7 C3 Cz C4 T8 A2 P7 P3 Pz P4 P8 O1
  O2 27 27 29 29 31 31 26 28 30 32`): the label line is unreliable for the
  seven non-EEG inputs. The export dialog lists the 32 channels as
  `1-E1 ... 25-O2, 26-27, 27-29, 28-31, 29-26, 30-28, 31-30, 32-32`.
- Column 15 (`Cz`) is identically 0.0000: the data are referential to Cz.
- The `% Patient's Name` line is a random pseudonym (anonymise was on).
