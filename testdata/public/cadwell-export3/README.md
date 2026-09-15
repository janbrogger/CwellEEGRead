# cadwell-export3 - third public test recording (volunteer EEG with a recording break)

A 20-minute, 32-channel, 500 Hz EEG recorded 2026-06-12 08:29-08:49 UTC on
a Cadwell Arc "Essentia" headbox (record `fe7c9e3d-e25d-4a80-a0a3-7136dbd7655e`),
with eyes open/closed, comments, hyperventilation and photic stimulation
events (329 events), and a **10-second break**: recording stopped at
08:34:39.785 and restarted at 08:34:47.008.

| Path | What |
|---|---|
| `native-export/CadLink/Data/<guid>-2026-06-12-08-21-39.ezdataindex` | index with frames 1-1217 on tracks 0 and 1, frames 328-337 missing; `GapInfo` row (track 0, offsets 328-338) |
| `native-export/CadLink/Data/<guid>-2026-06-12-08-21-39-1.ezdata` | 2414 frame blobs (1207 EEG + 1207 auxiliary) |
| `native-export/CadLink/Data/<guid>-2026-06-12-08-21-39.ezevents` | 329 events |
| `text/cadwell3.zip` | vendor text export of the **whole recording** (replaces the earlier 30 s file): 10:29:10-10:49:25 local = frames 1-1216, 603000 rows, 32 columns, 4 decimals of mV, 167 MB unzipped; the 10 s break is omitted (time stamps jump from 10:34:36 to 10:34:47), the last frame is not exported |
| `export-edf/cadwell3.edf`, `Metadata.json` | vendor EDF+C export starting 10:29:39.8525803 local (frame 30), 1187 records, ±23919 µV range (one amplifier unit per step), 69 annotations |

What it showed (details in `docs/research/cadwell-file-format.md`):

- The full text export equals the decoder output for all 603000 × 32
  samples within its 0.05 µV rounding, with the same scale constant as the
  250 Hz Apollo recording (the two rounding bounds overlap at
  0.72998046 µV/unit). Frame by frame, across the break, without alignment.
- The break is exactly the missing frame numbers 328-337 (10 s). The vendor
  EDF keeps the time axis continuous by writing digital zero for those
  seconds (EDF+C, no discontinuity), which is what our raw mode now does,
  plus a "Recording gap" annotation.
- The vendor EDF starts at frame 30 (the export dialog's default start,
  the same as the text export) at frame-30 time + the PcTimeSync offset
  (+11.114 ms), confirming the start-time rule found on export 1.
- This vendor EDF is **high-pass filtered** (about 0.16-0.2 Hz; amplitude
  ratio to the raw data 0.16 below 0.1 Hz, 0.73 at 0.1-0.3 Hz, 1.00 above
  0.7 Hz), unlike the export-1 EDF, so sample-by-sample equivalence against
  it is not possible; the text export is the raw reference.
- Essentia labels: `EEG E1/Pg1-Cz`, `EEG E2/Pg2-Cz`, Fp1 ... O2 as before,
  and `EEG 1A-1R` ... `EEG 7A-7R` for the seven non-EEG inputs. The
  amplifier type code 1 in the `AMPLAYOUT` blob (5 on the Apollo export)
  selects the table.
