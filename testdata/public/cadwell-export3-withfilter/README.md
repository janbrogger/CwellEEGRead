# cadwell-export3-withfilter - export 3 exported again with a 10-15 Hz viewer filter

The same recording as `cadwell-export3` (native files byte-identical),
exported from Arc Review with the viewer set to high-pass 10 Hz and
low-pass 15 Hz, to find out whether viewer filters reach the exports.

| Path | What |
|---|---|
| `native-export/...` | identical to cadwell-export3 (same MD5 for the three SQLite data files) |
| `text/cadwell3-with-filter.zip` | vendor text export of the whole recording, 10:29:10-10:49:25 local (frames 1-1216, break omitted), 603000 rows (replaces the earlier 30 s file) |
| `export-edf/cadwell3-withfilter.edf` | vendor EDF+C export from the record start (10:29:09.8553533 local = tick 0; frame 0 padded), 1217 records, 72 annotations |

Result (tests in `tests/test_vendor_exports_filtering.py`):

- The **text export is the raw data** to within its 0.05 µV rounding, in
  every frequency band: viewer filters are not applied to it. The full
  text export made with the 10-15 Hz viewer filter is **byte-identical in
  all 603000 data rows** to the one made without; only the header differs,
  because this one was exported without "Anonymize Information" (it shows
  the test patient's name `Testesen, test` and id `123456789`).
- The **EDF export ignores the viewer filter too**: it is identical to the
  unfiltered `cadwell3.edf` on their overlap except the first ~10 s of the
  later-starting file. Both carry the EDF export's own high-pass
  (2nd-order Butterworth, 0.16 Hz), whose start-up differs because each
  export starts it at its own first sample.
- Our vendor mode (`--mode vendor --start-at record-origin`) reproduces
  this file sample for sample within one quantisation step and with the
  same 72 annotations.
