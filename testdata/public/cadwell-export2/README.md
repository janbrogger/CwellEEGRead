# cadwell-export2 - second public test recording (real EEG of a volunteer, not a patient)

A 16-minute, 32-channel, 500 Hz routine-style EEG recorded 2026-06-12 on a
Cadwell Arc system (record `0712d2f4-0d77-4642-88a6-c977aaee4f2a`) with
eyes-closed (`Øyne lukket`), a comment, hyperventilation (3 min + 2 min
post-HV) and photic stimulation (2 to 21 Hz) events, 308 events in all.
Only the native CadLink study export is provided (no vendor EDF or text
export), so it tests the reader on a second amplifier configuration and
exercises event export, not sample equivalence.

| Path | What |
|---|---|
| `native-export/20260612123810.export` | 1-byte export marker |
| `native-export/CadLink/Data/<guid>-2026-06-12-10-38-10.ezdataindex` | index: 961 frames on track 0 (EEG) and 961 on track 1 (auxiliary, 0 channels in TrackInfo) |
| `native-export/CadLink/Data/<guid>-2026-06-12-10-38-10-1.ezdata` | 1922 frame blobs; the EEG frames are 19-35 kB, the track-1 frames 8463 bytes each |
| `native-export/CadLink/Data/<guid>-2026-06-12-10-38-10.ezevents` | 308 events |
| `native-export/CadLink/Databases/Core.db`, `EEG.db` | encrypted catalogue DBs |
| `native-export/CadwellArc DiagnosticLog9.log` | an unhandled-exception log from the CadLink export dialog (a WPF `Window.Owner` error), unrelated to the data |

What it showed (details in `docs/research/cadwell-file-format.md`):

- Every EEG frame has exactly 500 samples (no 251-type surplus at this rate);
  frame time stamps span 959.91 s for 961 frames.
- The channel-number order in the frames differs from export 1 (channels 1-7
  are amplifier inputs 26-32), but the amplifier-input numbering is the same
  physical layout: inputs 20-25 (P3, Pz, P4, P8, O1, O2) carry the highest
  alpha fraction after eyes closed, inputs 1-4 (E1, E2, Fp1, Fp2) the blink
  activity, input 15 (Cz) is identically zero, input 26 is the ECG (68 beats
  per minute, ~0.7 mV).
- Amplitudes with the 0.72998046 µV/unit scale are physiologically plausible
  (referential-to-Cz EEG 4-12 µV rms in 1-30 Hz, DC offsets up to 100 µV).
- Track 1 frames have a shorter header and 32 blocks of 264 bytes; content
  unknown (low-rate per-channel data, probably lead quality/impedance).
