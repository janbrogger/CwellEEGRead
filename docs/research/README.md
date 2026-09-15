# Research notes

| Note | Question | Short answer |
|---|---|---|
| [`cadwell-file-format.md`](cadwell-file-format.md) | What are modern Cadwell EEG files, really? | `.ezdata` is a SQLite 3 media container: `MediaHeader` (key/value), `TrackInfo` (per-track descriptor blobs, incl. channel info), `FrameInfo` (one blob per track per ~1 s frame), plus `MiscInfo` and sync/change-tracking tables. Cadwell's own Arc API lists waveform encodings `WaveformNoCompression` and `WaveformNonlinearDeltaCompression`, returns waveforms as `float[]` per channel with per-segment hardware filter settings and 100-ns sample periods, and models gaps explicitly. The blob layouts are undocumented and must be reverse-engineered from test files. Older `.eas` (Easy II) and `.ez3` (Easy III) are binary, not SQLite. |
| [`biosig-cadwell-reader.md`](biosig-cadwell-reader.md) | Can we port the BioSig Cadwell reader? | No, there is nothing to port. `sopen_cadwell_read.c` and `sopen_sqlite.c` (2021, unchanged since) only detect the formats and dump bytes; every path ends in "unsupported", and the SQLite path is not even compiled by default. Useful facts: magic strings, the 11-table SQLite signature, partial `.ez3` block notes. BioSig is GPL-3.0-or-later. |
| [`downstream-uses.md`](downstream-uses.md) | What do Morgoth, SCORE-AI and EEGLAB/FieldTrip need from us? | Morgoth (bdsp-core/morgoth, CC BY-NC 4.0, credentialed weights on BDSP) reads EDF via MNE, wants 19 standard 10-20 channels in µV, resamples to 200 Hz itself, writes CSV. SCORE-AI/autoSCORE has no public program; a wrapper must assume an externally supplied command and a full 10-20 + ECG referential routine EEG. EEGLAB plugins are `eegplugin_*.m` + `pop_*.m` in a versioned folder zipped at the root; FieldTrip readers plug into `ft_read_header/data/event`. |

## Licensing decision (REQ015)

The repository stays under the Unlicense. BioSig contains no working Cadwell
decoder, so no GPL code is ported. Format facts learned from BioSig (magic
bytes, table names) are not copyrightable and are cited in the notes above.
Our reader will be a clean-room implementation from our own analysis of the
test recordings. Should a working GPL decoder ever be ported after all, the
repository must be relicensed to GPL-3.0-or-later first, and that decision
recorded here.

Note that the Morgoth model itself is CC BY-NC 4.0 (non-commercial); this
constrains use of `uses/Morgoth`, not this repository's code.

## What the notes imply for the next step

1. Done: the first public export (`testdata/public/cadwell-export1`) is
   decoded by `cwelleegread/ezdata.py` and matches the vendor's text export
   exactly. See the "Findings from test export 1" section of the format
   note.
2. Done: EDF+ writer and CLI (`python -m cwelleegread convert`); vendor
   mode reproduces the Cadwell EDF export of export 1 within one step.
   Export 2 (real EEG, 500 Hz, events) converts; its labels and scale are
   plausible but unverified for lack of a vendor export of that recording.
   Next: a recording with a gap, and a vendor EDF or text export of a
   500 Hz recording to confirm the scale at that rate.
3. Decide gap handling for EDF+ (EDF+D vs padded EDF+C) once a recording
   with a gap is available (REQ019).
