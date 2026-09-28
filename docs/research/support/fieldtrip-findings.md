> Supporting research note produced 2026-09-28 by an LLM research agent (Claude Code, session `831b87b8-e6bd-4acd-901b-d67180234ee3`, see `llm-logs/`) for `docs/research/eeglab-fieldtrip-cadwell-reader.md`. Claims are tagged [V] verified by reading source, [W] from a web page summary, [I] inferred. Line numbers refer to the commits named in the note.

# FieldTrip findings for a Cadwell `.ezdata` reader (scoping input)

Date: 2026-09-28. FieldTrip master checked at commit `7bcde3ff5ff0222693d433343f7f04db579a64a9`
(committed 2026-09-24). Sparse clone in
`(session scratchpad, not kept)/fieldtrip`
(dirs `fileio`, `utilities`, `forward`, `external/{xdf,mffmatlabio,biosig}`; the two Nicolet
test files were fetched separately into `test/`).

Legend for provenance:
- **[V]** verified by reading the source file locally at the stated line numbers (master).
- **[W]** obtained through a summarising web fetch of a GitHub page (PR pages, website repo); wording
  reliable, but line numbers/counts may be approximate and inline review comments could not be
  retrieved (see 3.5).
- **[I]** inferred / my own conclusion.

---

## 1. The Nervus/Nicolet reader as it exists today

### 1.1 Files and sizes [V]

| File | Lines | Role |
|---|---|---|
| `fileio/private/read_nervus_header.m` | 999 | parses the `.e` container, returns a FieldTrip header |
| `fileio/private/read_nervus_data.m` | 169 | reads one channel of one segment (int16, scaled) |
| `fileio/ft_filetype.m` | 1884 | detection branch at lines 1517-1520 |
| `fileio/ft_read_header.m` | 3120 | `case 'nervus_eeg'` at 1859-1861 |
| `fileio/ft_read_data.m` | 1782 | `case 'nervus_eeg'` at 1074-1108 |
| `fileio/ft_read_event.m` | 2647 | `case 'nervus_eeg'` at 1565-1609 |
| `test/test_nicolet_reading.m` | 155 | regression test (DATA private) |
| `test/private/test_nicolet_reading_onefile.m` | 82 | helper: header/data/ASCII-export comparison |

`ls fileio/private | grep -i -E 'nervus|nicolet'` returns only the two files above; there is no
`read_nicolet_*` file [V]. No other file in `fileio/`, `forward/ft_senstype.m`,
`fileio/ft_chantype.m`, `fileio/ft_chanunit.m`, `fileio/ft_read_sens.m` mentions nervus/nicolet [V].

### 1.2 Structure of `read_nervus_header.m` [V]

Copyright header (lines 1-28): `% Copyright (C) 2016, Jan Brogger and Joost Wagenaar`, GPL-3 boilerplate,
"Based on ieeg-portal/Nicolet-Reader". Main function is lines 1-131; 18 subfunctions follow
(`read_nervus_header_staticpackets` @134, `_Qi` @244, `_Qi2` @256, `_main` @273, `_infoGuids` @300,
`_dynamicpackets` @318, `_patient` @495, `_SignalInfo` @542, `_ChannelInfo` @572, `_TSInfo` @608,
`checkAreAllTSInfosEqual` @631, `_TSInfo_from_static` @652, `_one_TSInfo` @703,
`compareTsInfoPackets` @736, `_Segments` @787, `_events` @823, `_montage` @914,
`_dynamic_montages` @954).

I/O is entirely `fopen_or_error` + `fseek` + `fread` (1 fopen, 32 fseek, 98 fread calls); the header pass
seeks around the index and packet tables, it does not slurp the file. Lines 37-46:

```matlab
h = fopen_or_error(filename,'rb','ieee-le','US-ASCII');
nrvHdr = struct();
nrvHdr.filename = filename;
nrvHdr.misc1 = fread(h,5, 'uint32');
nrvHdr.unknown = fread(h,1,'uint32');
nrvHdr.indexIdx = fread(h,1,'uint32');
if (nrvHdr.indexIdx==0)
  fclose(h);
  ft_error('Unsupported old-style Nicolet file format (pre-ca. 2012)');
end
```

Mixed sampling rates (the PR #1358 fix), lines 94-118:

```matlab
% Fieldtrip can't handle multiple sampling rates in a data block
% We will return only the data for the most frequent sampling rate
nrvHdr.targetSamplingRate = mode(nrvHdr.Segments(1).samplingRate);
nrvHdr.matchingChannels = find(nrvHdr.Segments(1).samplingRate(:) == nrvHdr.targetSamplingRate);
nrvHdr.excludedChannels = find(nrvHdr.Segments(1).samplingRate(:) ~= nrvHdr.targetSamplingRate);
firstMatchingChannel = nrvHdr.matchingChannels(1);
nrvHdr.targetNumberOfChannels = length(nrvHdr.matchingChannels);
targetSampleCount = 0;
for i = 1:size(nrvHdr.Segments,2)
  targetSampleCount = targetSampleCount + nrvHdr.Segments(i).sampleCount(firstMatchingChannel);
end
nrvHdr.targetSampleCount = targetSampleCount;
newlabels = cell(nrvHdr.targetNumberOfChannels, 1);
j = 1;
for i=1:size(nrvHdr.Segments(1).chName,2)
  if nrvHdr.Segments(1).samplingRate(i) == nrvHdr.targetSamplingRate
  newlabels(j) = nrvHdr.Segments(1).chName(i);
  j = j+1;
  end
end
```

Returned header, lines 120-129 (note `nTrials = 1`: discontinuous segments are concatenated, not
exposed as trials):

```matlab
output = struct();
output.Fs      = nrvHdr.targetSamplingRate;
output.nChans    = nrvHdr.targetNumberOfChannels;
output.label     = newlabels;
output.nSamples  = nrvHdr.targetSampleCount;
output.nSamplesPre = 0;
output.nTrials   = 1; %size(nrvHdr.Segments,2);
output.reference   = nrvHdr.reference;
output.filename  = nrvHdr.filename;
output.orig    = nrvHdr;
```

It does **not** set `hdr.chantype` / `hdr.chanunit`; and because `ft_read_header` sets
`checkUniqueLabels = false` for this format (line 1861), the generic fallback
`hdr.chantype = ft_chantype(hdr)` / `hdr.chanunit = ft_chanunit(hdr)` at lines 2886-2894 is
skipped too (they are guarded by `&& checkUniqueLabels`). So a Nervus header comes back with
no `chantype`/`chanunit` fields at all [V]. (`hdr.label` is still normalised by `fixlabels` at
line 2973 and `Fs`/`nSamples` cast to double at 2979-2980.) [I]: for a Cadwell reader it would be
better to fill `chantype`/`chanunit` (e.g. `'eeg'`/`'uV'`) explicitly, which EEGLAB's `pop_fileio`
uses (see section 6).

Error handling: `ft_error` at lines 46, 618, 647; plain `error(...)` at 83, 86, 89 (segment
consistency checks); **no** `ft_warning` in the file [V]. `ft_read_data.m:1105` uses plain
`warning(...)` for the excluded-channel notice [V].

Other `orig` content used downstream: `Segments(i).samplingRate/sampleCount/duration/date/dateOLE/
chName/refName/scale`, `Events(i).IDStr/label/dateOLE/date/duration/user/GUID`, `TSInfo`,
`StaticPackets`, `MainIndex`, `allIndexIDs`, `PatientInfo`, `MontageInfo`, `MontageInfo2`,
`startDateTime`, `reference` ('common' when the ref name is 'REF', else 'unknown', lines 63-68) [V].

### 1.3 `read_nervus_data.m` [V]

Signature `out = read_nervus_data(nrvHdr, segment, range, chIdx)`; returns samples x channels
doubles. It re-opens the file (`fopen_or_error(nrvHdr.filename,'r','ieee-le')`, line 61), for each
requested channel finds the sections in `nrvHdr.MainIndex` belonging to that channel's static
packet, `fseek`s to `curSec.offset` (lines 125, 139, 148), `fread(h, n, 'int16') * mult` (lines 132,
142, 154) and `fclose` at 165. So it seeks; it does not read the whole file. The per-channel
sampling rate is looked up as `curSF = nrvHdr.Segments(segment).samplingRate(chIdx(i))` and used to
compute the section skip (`skipValues = cSumSegments(segment) * curSF`).

### 1.4 `ft_read_data` branch, lines 1074-1108 [V]

```matlab
case 'nervus_eeg'
  hdr = read_nervus_header(filename);
  ...
  %Fieldtrip can't handle multiple sampling rates in a data block
  %We will get only the data with the most frequent sampling rate
  targetNumberOfChannels = hdr.orig.targetNumberOfChannels;
  targetSampleCount = hdr.orig.targetSampleCount;
  dat = zeros(targetSampleCount,targetNumberOfChannels);
  j = 1;
  for i=1:size(hdr.orig.Segments(1).samplingRate,2)
    if hdr.orig.Segments(1).samplingRate(i) == hdr.Fs
      dataForChannel = [];
      for segment=1:size(hdr.orig.Segments,2)
        range = [1 hdr.orig.Segments(segment).sampleCount];
        datseg = read_nervus_data(hdr.orig, segment, range, i);
        dataForChannel = cat(1,dataForChannel,datseg);
      end
      dat(1:targetSampleCount, j) = dataForChannel;
      j = j+1;
    end
  end
  if targetNumberOfChannels ~= size(hdr.orig.Segments(1).sampleCount, 2)
    excludedChannelLabels = strjoin({hdr.orig.TSInfo(hdr.orig.excludedChannels).label}, ', ');
    warning(['Some channels ignored due to different sampling rates: ' excludedChannelLabels]);
  end
  dimord = 'samples_chans';
  dat = dat(begsample:endsample, chanindx);
```

Important behavioural facts [V]:
- It ignores the `'header'` option and re-reads the header (`hdr = read_nervus_header(filename)`).
- It **always reads all channels and all segments of the whole recording into memory**, then slices
  `begsample:endsample, chanindx`. Every call from `ft_preprocessing` with trials therefore re-reads
  the entire file (ft_read_data has no cache for this format). [I] For a Cadwell reader we should
  honour begsample/endsample/chanindx at the SQL level.
- `dimord = 'samples_chans'` is permuted to `chans_samples` by the common tail (lines 1682-1697:
  `case 'samples_chans'  dat = permute(dat, [2 1]);`).

### 1.5 `ft_read_event` branch, lines 1565-1609 [V]

```matlab
case 'nervus_eeg'
  if isempty(hdr)
    hdr = ft_read_header(filename, 'headerformat', headerformat);
  end
  % construct a event structure from data in the header
  maxSampleRate = max([hdr.orig.Segments.samplingRate]);
  earliestDateTime = min([hdr.orig.Segments.dateOLE]);
  for i=1:length(hdr.orig.Events)
    event(i).type     = hdr.orig.Events(i).IDStr;   % string
    event(i).value    = hdr.orig.Events(i).label;   % number or string
    event(i).offset   = 0;                          % expressed in samples
    event(i).sample   = (hdr.orig.Events(i).dateOLE-earliestDateTime)*3600*24*maxSampleRate;
    if event(i).sample == 0
      event(i).sample = 1;
    elseif event(i).sample > hdr.nSamples
      event(i).sample = hdr.nSamples;
    end
    event(i).duration = hdr.orig.Events(i).duration*maxSampleRate;
  end
  % Add boundary events to indicate segments
  originalEventCount = length(hdr.orig.Events);
  boundaryEventCount = 1;
  for i=1:length(hdr.orig.Segments)
    sampleCountOfchannelsWithSameSampleRate(i,:) = hdr.orig.Segments(i).sampleCount;
  end
  for i=2:length(hdr.orig.Segments)
    event(originalEventCount+boundaryEventCount).type = 'boundary';
    event(originalEventCount+boundaryEventCount).value = 'boundary';
    event(originalEventCount+boundaryEventCount).offset = 0;
    gapDurationSeconds = seconds(hdr.orig.Segments(i).date-hdr.orig.Segments(i-1).date)-hdr.orig.Segments(i-1).duration;
    event(originalEventCount+boundaryEventCount).duration = gapDurationSeconds*maxSampleRate;
    event(originalEventCount+boundaryEventCount).sample = sum(sampleCountOfchannelsWithSameSampleRate(1:(i-1)));
    %move all non-boundary events later than this segment start
    %back by the length of the gap ...
    for j=1:originalEventCount
      if hdr.orig.Events(j).date > hdr.orig.Segments(i).date
        event(j).sample = event(j).sample - gapDurationSeconds*maxSampleRate;
      end
    end
    boundaryEventCount = boundaryEventCount+1;
  end
```

Events are derived entirely from the header (`hdr.orig.Events`); `'boundary'` events with a
`duration` equal to the gap are emitted so EEGLAB shows the pauses (EEGLAB's `pop_fileio` maps
`event.type <- value`, `event.value <- type`, see section 6). [I] Note the sample computed from
`maxSampleRate` rather than `hdr.Fs`, and non-integer samples are not rounded; a Cadwell reader
should compute integer samples at `hdr.Fs`.

### 1.6 How `ft_read_header` uses it, lines 1859-1861 [V]

```matlab
case 'nervus_eeg'
  hdr = read_nervus_header(filename);
  checkUniqueLabels = false;
```

`checkUniqueLabels=false` skips the duplicate-label renaming at 2836-2860 and, as noted, also the
chantype/chanunit defaults at 2886-2894.

---

## 2. How a format is wired into FieldTrip

### 2.1 Detection: `ft_filetype.m` [V]

The function is one long `if/elseif` ladder; each branch sets `type`, `manufacturer`, `content`.
Nervus branch, lines 1517-1520 (extension only, no magic bytes):

```matlab
elseif filetype_check_extension(filename, '.e')
  type = 'nervus_eeg';  % Nervus/Nicolet EEG files
  manufacturer = 'Natus';
  content = 'EEG';
```

Neighbours for comparison: `tmsi_poly5` (1509), `mega_neurone` (directory + two xml files, 1513),
`nihonkohden_m00` (1521). Examples that check magic bytes with `filetype_check_header`: 
`elseif filetype_check_extension(filename, '.xdf') && filetype_check_header(filename, 'XDF')`,
`... '.c3d') && filetype_check_header(filename, [2, 80])`,
`... '.bdf') && filetype_check_header(filename, [255 'BIOSEMI'])` [W, quoted by fetch; the
mechanism is confirmed by the local file]. The help header (line 66) lists
`%  - Nicolet *.e (currently from Natus, formerly Carefusion, Viasys and Taugagreining ...)`.
Unknown fallback near the end: `ft_warning('could not determine filetype of %s', filename)` [W].

There is **no** existing branch mentioning `cadwell`, `ezdata`, `sqlite` or `SQLite` [V, grep].
[I] A Cadwell branch would be
`elseif filetype_check_extension(filename, '.ezdata') && filetype_check_header(filename, 'SQLite format 3')`
placed before any bare-extension checks (website: "most stringent check first"; the ladder is
order-sensitive).

### 2.2 Dispatch in the three readers [V]

- `ft_read_header.m`: options via `ft_getopt` at 188-197; `headerformat = ft_filetype(filename)`
  when empty (205-208); `switch headerformat` at 346; `otherwise` at 2805-2819 (quoted in 4.2);
  common tail 2836-2980 (unique labels, chantype/chanunit defaults, BIDS sidecars, `fixlabels`,
  casting).
- `ft_read_data.m`: `dataformat = ft_getopt(varargin,'dataformat')` (139),
  `headerformat = ft_getopt(varargin,'headerformat', dataformat)` (140),
  autodetect at 154-157; `otherwise` at 1658-1672; dimord permutation 1682-1697; chanunit scaling
  1703-1720.
- `ft_read_event.m`: `eventformat = ft_getopt(varargin,'eventformat')` (164), `headerformat` and
  `dataformat` default to `eventformat` (165-166); autodetect 209-212; `otherwise` 2542-2553;
  after the switch, if `hdr.nTrials>1` and no `'trial'` events exist, one per trial is synthesised
  (2557-2561).
- `ft_read_sens.m`, `ft_chantype.m`, `forward/ft_senstype.m`, `ft_chanunit.m`: nothing format-specific
  is needed for a plain EEG reader. `ft_chantype` falls back on label matching
  (`ft_senslabel('eeg1005')` etc., and a `label2type` table with 'ecg','emg','eog','eeg','trigger')
  and `ft_senstype` decides `eeg1020/eeg1010/eeg1005/ext1020` from label overlap [W].

### 2.3 Minimal file set to add `cadwell_ezdata` [I, based on 2.1-2.2 and section 4]

Option A (in-tree switch cases, like Nervus):
1. `fileio/ft_filetype.m` – one `elseif` branch.
2. `fileio/private/read_cadwell_header.m` + `read_cadwell_data.m` (or one file).
3. `fileio/ft_read_header.m`, `ft_read_data.m`, `ft_read_event.m` – one `case 'cadwell_ezdata'` each.
4. `test/test_cadwell_reading.m` (+ private test data on the DCCN server).
5. Website page `getting_started/eeg/cadwell.md` in `fieldtrip/website` (recommended; asked for in
   PR #1358).

Option B (the currently recommended pattern, see 4.1): only `ft_filetype.m` + one
`fileio/private/cadwell_ezdata.m` implementing header/data/event by `nargin`, plus the test; the
`otherwise` branches dispatch to it automatically because `exist('cadwell_ezdata','file')` is true.
Plus any SQLite library under `external/` with a `ft_hastoolbox` entry (section 5).

---

## 3. Jan Brogger's pull requests on fieldtrip/fieldtrip

(All PR facts are [W] from the GitHub PR pages; the GitHub REST API is not reachable from this
session's proxy - `api.github.com` answers "GitHub access to this repository is not enabled for
this session" - so inline review comment bodies could not be retrieved.)

### 3.1 PR #186 "Reads Nervus/Nicolet files" - https://github.com/fieldtrip/fieldtrip/pull/186
- Opened 2016-07-01, merged 2016-07-06 by robertoostenveld. 1 commit (6c4c887). **5 days.**
- Files: `ft_filetype.m` +8, `ft_read_header.m` +7, `ft_read_data.m` +14, `ft_read_event.m` +37/-2,
  `fileio/private/read_nervus_data.m` +158 (new), `read_nervus_header.m` (new, size not shown).
- Description: reads `.e` without vendor DLLs; creates boundary events for discontinuities that
  work in EEGLAB; based on Joost Wagenaar's ieeg-portal/Nicolet-Reader with e-mail permission
  ("By all means, feel free to port the code to EEGLab/fieldtrip-io").
- No review comments, no test script requested at that time; merged as-is.

### 3.2 PR #266 "Improvements for Nicolet" - https://github.com/fieldtrip/fieldtrip/pull/266
- Commits from 2016-09-03, PR opened 2016-11-22, merged 2016-11-23 by robertoostenveld ("thanks").
- 1 file: `read_nervus_header.m` +126/-10: TSINFO equality check (error if differing packets),
  reading montages from dynamic packets (`MontageInfo2`).
- No review comments.

### 3.3 PR #302 "Fixes read of Nervus data with mixed sampling rates" - https://github.com/fieldtrip/fieldtrip/pull/302
- 22 commits 2016-12-11 .. 2019-06-27; opened ~2017-01; **closed unmerged 2019-07-03** by
  robertoostenveld: "replaced by pull request #1166".
- Files: `ft_read_data.m` +37/-13, `ft_read_event.m` +34/-18, `read_nervus_data.m` +4/-4,
  `read_nervus_header.m` +67/-13, `test/private/test_nicolet_reading/README.txt` +3,
  `test/private/test_nicolet_reading/nicolet-test-data.zip` (+33.5 MB binary!),
  `test/private/test_nicolet_reading_onefile.m` +81.
- Maintainer feedback (robertoostenveld):
  - 2017-01-19: asked for "an example data set and a test script"; noted "picking the most prevalent
    sampling rate is also consistent with EDF".
  - 2017-03-06 Jan: MATLAB "kind of new", asked for a test template. Robert supplied:
    ```
    function test_name
    hdr = ft_read_header(filename)
    evt = ft_read_event(filename)
    dat = ft_read_data(filename)
    assert(size(dat,1)==hdr.nChans)
    ```
  - 2019-06-26: "Without a test script and test data, it is not possible to see whether it all
    works as expected."
  - 2019-06-27 Jan added a test comparing against Nicolet ASCII export and a databrowser test, with a
    hard-coded local Windows path (`C:\Midlertidig_Lagring\...`).
- Lessons: a 33 MB zip in the repo was unacceptable (Robert cherry-picked everything *except* that
  commit into #1166); hard-coded local paths must be replaced by `dccnpath`; two-year stall was
  mostly waiting for test data/script.

### 3.4 PR #1166 (robertoostenveld's rebase of #302) - https://github.com/fieldtrip/fieldtrip/pull/1166
- Opened 2019-07-03 by robertoostenveld; 17 commits; closed 2020-03-23 by schoffelen ("replaced
  by #1358"). Robert: test script failed on his side ("This clearly still needs more work before it
  can be merged"); Jan fixed it in a fork on 2019-07-07; then dormant until 2020.

### 3.5 PR #1358 "Fixes read of Nervus data with mixed sampling rates, and some unreadable EEGs" - https://github.com/fieldtrip/fieldtrip/pull/1358
- Commits 2020-03-21..23 (11 commits: re-implementation, 92% then 100% read rate on 90 clinical
  EEGs 2012-2020, "Fix off-by-one error", "Fixes 2 spaces per tab instead of 4 spaces per tab");
  opened ~2020-03-22, **merged 2020-03-23 by schoffelen** (about one day).
- Files: `ft_read_data.m` +31/-5, `ft_read_event.m` +17/-2, `read_nervus_data.m` +106/-95,
  `read_nervus_header.m`, `test/private/test_nicolet_reading_onefile.m`,
  `test/test_nicolet_reading.m`. Test data in a separate repo
  https://github.com/janbrogger/FieldTripNicoletTestData/ (PR text).
- Review: schoffelen "requested changes" with inline comments on `ft_read_data.m`,
  `read_nervus_data.m` and both test files (bodies not retrievable here), then: "Would it be an idea
  to upgrade the documentation on fieldtriptoolbox.org/getting_started/nicolet/ so that users can
  get some pointers to dll etc. if it does not work for them?" - Jan: "Done." - schoffelen approved:
  "OK, I will merge, and ensure that the test data is downloaded onto our fileserver, I'll adjust
  the path to the test data if needed (uncommenting the relevant line in the test function seems
  enough)."
- Post-merge 2020-03-24 schoffelen: the provided test files "don't work. Neither in Linux, nor on
  Mac", header reading got stuck with unrealistically large `nrIdx` - asked whether Jan was on a PC
  (endianness/OS issue). [I] So: test on Linux/macOS too, not only Windows, before submitting.

### 3.6 Test conventions actually used in master [V]

`test/test_nicolet_reading.m` (lines 1-13):

```matlab
function test_nicolet_reading

% MEM 1gb
% WALLTIME 00:30:00
% DEPENDENCY test_nicolet_reading_onefile read_nervus_header
% DATA private

% function to test reading of Nicolet/Nervus EEG files
% one is a file from 2006 (older Nicolet format)
% one is a file from 2018 (newer Nicolet format)

path_to_load = dccnpath('/project/3031000.02/test/original/eeg/nicolet');
%path_to_load = 'C:\Midlertidig_Lagring\FieldTripNicoletTestData';
```

then `test_nicolet_reading_onefile(path_to_load,file2,file2ascii,256,24,307200,1,datetime(2006,06,09,13,42,41));`
plus a `ft_preprocessing` + `ft_databrowser` smoke test ("Test code requested by Robert"). The
helper asserts `hdr.Fs/nChans/nSamples/nTrials`, `hdr.orig.startDateTime`, `hdr.orig.reference`,
`size(alldata)` and compares every sample with the vendor ASCII export within 0.01 uV. Note the
helper uses `error(...)`/`warning(...)`/`assert` (test scripts are not held to the `ft_error`
convention). The private test data lives at
`/project/3031000.02/test/original/eeg/nicolet` on the DCCN server.

Naming convention in `test/` [V, tree listing]: 410 `test_bug*`, 97 `test_issue*`, 59 `test_pull*`,
206 `test_ft_*`; the Nicolet test is a descriptive name. Website `development/testing.md` [W]:
`test_bugXXX`/`test_issueXXX`/`test_pullXXX` numbered by the tracker item, `inspect_xxx.m` for
interactive tests; header lines `% WALLTIME`, `% MEM`, `% DATA no|public|private`, `% DEPENDENCY`;
private data under `/project/3031000.02/test`, public data under
`/project/3031000.02/external/download` (also on the download server); `dccnpath()` maps the DCCN
path to the local machine and auto-downloads public data.

### 3.7 Process lessons (CLA, style, warnings) [W + V]
- **No CLA**: `.github/CONTRIBUTING.md` (211 lines, based on MRtrix's) mentions no CLA/copyright
  assignment; contributed files simply carry the author's copyright line plus the GPL-3 boilerplate
  (as `read_nervus_header.m` does). Contributions become GPL-3 code inside FieldTrip.
- Style (CONTRIBUTING.md lines 204-207): "2 space indents; indent using spaces and not tabs",
  "No spaces between function name and opening parenthesis", "One space after the comma". The last
  commit of #1358 was literally a re-indent to 2 spaces.
- Commit messages: synopsis < 80 chars, blank line, body; reference issues with `#N`.
- Fixes and enhancements both target `master`; "A unit test or reproducibility test should ideally
  be added ... should fail when executed using the current master code, but pass with the changes".
- Website code guideline [W]: warnings/errors need identifiers, use `ft_warning`/`ft_error`
  (the Nervus code still uses raw `warning`/`error` in places and was merged anyway); avoid nested
  functions; MATLAB back-compat ~5 years (R2015b+ at time of writing); "Functions in subdirectories
  should only call other FieldTrip functions at the same level or lower" (fileio/private code
  must not depend on top-level `ft_*` functions).
- External dependencies: put the library in `fieldtrip/external/<name>` and add an entry in
  `utilities/ft_hastoolbox.m` (URL table around lines 90-205, `dependency = {...}` case around
  222-460; the external path is auto-added at 520-526).

---

## 4. Contribution guidance for new file formats and the external-function mechanism

### 4.1 Website pages [W, verbatim fetches of the `fieldtrip/website` repo]
- `faq/preproc/dataformat/dataformat_own.md` ("How can I import my own data format?"):
  "There is a simple way you can use your own reading functions: make your own function
  `YourFormat.m`. When calling for example ft_preprocessing, you should specify the name of your
  specific function as the 'headerformat', 'dataformat' and 'eventformat' option." Contract:
  ```
  hdr   = YourFormat(filename)
  dat   = YourFormat(filename, hdr, begsample, endsample, chanindx)
  event = YourFormat(filename, hdr)
  ```
  "Depending on the number of input arguments that your function receives (1, 5 or 2), it should
  return the header, the data or the events." Examples named: `biopac_acq.m`, `snirf.m`,
  `motion_c3d.m`, `qualisys_tsv.m`, `liberty_csv.m`. It is "perfectly fine not to add the format to
  the FieldTrip code-base but to only share it inside your lab."
- `faq/preproc/dataformat/fileio_dataformat.md` ("How can I extend the reading functions with a new
  dataformat?"): extend `ft_filetype` (extension, "preferably ... magic bytes at the start of the
  file", or co-presence of files); "Rather than changing the code in ft_read_xxx itself, we
  recommend that you make use of the section `otherwise ... hdr = feval(headerformat, filename)`";
  "If you implement your fileformat as `manufacturer_extension` ... You provide the
  `fieldtrip/fileio/private/manufacturer_extension.m` function"; "If your reading function depends
  on an external library, please add that library to `fieldtrip/external` and use ft_hastoolbox";
  "the FieldTrip reading functions are shared with SPM and EEGLAB, so adding it to FieldTrip also
  makes the new format accessible for those packages."
- `development/module/fileio.md`: header fields `Fs, nChans, label, nSamples, nSamplesPre, nTrials,
  grad, orig`; event fields `type, sample, value, offset, duration`; "the detection sometimes is
  order sensitive: the first match in ft_filetype will be the one returned".
- `development/contribute.md`: considerable contributions must be "in FieldTrip style, ... of broad
  interest (i.e. more than a single lab), must be maintainable and must be documented ... also on
  the website"; self-contained projects may instead be listed as a FieldTrip extension.
- `getting_started/eeg/nicolet.md` (the page Jan updated for #1358): history of Nervus/Nicolet,
  "FieldTrip can read the file format from 2012 through 2020", "Currently FieldTrip only reads the
  channels with the most common sampling rate", "This code also enables EEGLAB users to read the
  Nicolet file format through the FILEIO plugin in EEGLAB", and example code.
- `CONTRIBUTING.md` at repo root does not exist (404); it is at `.github/CONTRIBUTING.md` [V].
- `fileio/README` [V] is only a module description + copyright/GPL notice, no format guidance.

### 4.2 The mechanism in code (master) [V]

`ft_read_header.m` help, lines 17 and 43-46:
```
%   'headerformat'   = name of a MATLAB function that takes the filename as input (default is automatic)
% To use an external reading function, you can specify an external function as the
% 'headerformat' option. This function should take the filename as input argument.
% Please check the code of this function for details, and search for BIDS_TSV as
% example.
```
`ft_read_header.m` lines 2805-2819:
```matlab
otherwise
  if exist(headerformat, 'file')
    % attempt to run "headerformat" as a function, this allows the user to specify an external reading function
    % this is also used for bids_tsv, biopac_acq, motion_c3d, opensignals_txt, qualisys_tsv, sccn_xdf, and possibly others
    hdr = feval(headerformat, filename);
  elseif strcmp(fallback, 'biosig') && ft_hastoolbox('BIOSIG', 1)
    try
      % there is no guarantee that biosig can read it
      hdr = read_biosig_header(filename);
    catch
      ft_error('unsupported header format "%s"', headerformat);
    end
  else
    ft_error('unsupported header format "%s"', headerformat);
  end
```
`ft_read_data.m` help lines 34-37 and code 1658-1672:
```
% To use an external reading function, you can specify an external function as the
% 'dataformat' option. This function should take five input arguments: filename, hdr,
% begsample, endsample, chanindx. ...
```
```matlab
otherwise
  if exist(dataformat, 'file')
    dat = feval(dataformat, filename, hdr, begsample, endsample, chanindx);
  elseif strcmp(fallback, 'biosig') && ft_hastoolbox('BIOSIG', 1)
    try
      dat = read_biosig_data(filename, hdr, begsample, endsample, chanindx);
    catch
      ft_error('unsupported data format "%s"', dataformat);
    end
  else
    ft_error('unsupported data format "%s"', dataformat);
  end
```
`ft_read_event.m` help 48-51 ("This function should take the filename  and the headeras input
arguments" [sic]) and code 2542-2553:
```matlab
otherwise
  if exist(eventformat, 'file')
    % this is also used for bids_tsv, events_tsv, biopac_acq, motion_c3d, opensignals_txt, qualisys_tsv, sccn_xdf, and possibly others
    if isempty(hdr)
      hdr = feval(eventformat, filename);
    end
    event = feval(eventformat, filename, hdr);
  else
    ft_warning('unsupported event format "%s"', eventformat);
    event = [];
  end
```
Notes [V]: the option is a **string** (function name), tested with `exist(...,'file')`; a function
handle is not accepted (`exist` of a handle fails). Any function on the MATLAB path qualifies, so
the reader can live outside FieldTrip. If the function is placed in `fileio/private/` and its name
equals the `ft_filetype` return value (e.g. `cadwell_ezdata`), autodetection works with no switch
cases at all. In-tree examples (all in `fileio/private/`): `bids_tsv.m, biopac_acq.m, events_tsv.m,
liberty_csv.m, motion_c3d.m, openpose_keypoints.m, opensignals_txt.m, qualisys_tsv.m, sccn_xdf.m,
snirf.m, xsens_mvnx.m`. Template (`biopac_acq.m`):

```matlab
function varargout = biopac_acq(filename, hdr, begsample, endsample, chanindx)
% Use as
%   hdr = biopac_acq(filename);
%   dat = biopac_acq(filename, hdr, begsample, endsample, chanindx);
%   evt = biopac_acq(filename, hdr);
persistent acq previous_fullname
ft_hastoolbox('fileexchange', 1);
needhdr = (nargin==1);
needevt = (nargin==2);
needdat = (nargin==5);
...
if needhdr
  hdr.Fs = ...; hdr.nChans = ...; hdr.nSamples = ...; hdr.nSamplesPre = 0; hdr.nTrials = 1;
  hdr.label{i} = ...; hdr.orig = acq.hdr; varargout{1} = hdr;
elseif needevt
  varargout{1} = event;
elseif needdat
  dat = acq.data(begsample:endsample,chanindx)'; varargout{1} = dat;   % chans x samples
end
```
`sccn_xdf.m` shows the external-library pattern: `ft_hastoolbox('xdf', 1);` then `load_xdf(filename)`.

---

## 5. SQLite, Java, Python and licences in FieldTrip

- **SQLite**: no reader, no dependency. The only hit for `sqlite|mksqlite|jdbc` in the checked-out
  parts (`fileio`, `utilities`, `forward`, `external/{biosig,xdf,mffmatlabio}`) is
  `external/biosig/private/getfiletype.m:414-415`, where BioSig merely *recognises* the magic string
  `'SQLite format 3'` and sets `HDR.TYPE = 'SQLite'` [V]. A filename search of the whole tree
  (`git ls-tree -r HEAD`) finds no `*sqlite*`, `*cadwell*`, `*ezdata*`, `*jdbc*` files [V]. Content
  of the non-checked-out directories was not grepped (blob-filtered clone) [I: unlikely to differ].
- **Java**: used by readers via `external/`:
  - `external/mffmatlabio` (EGI MFF, `ft_hastoolbox('mffmatlabio',1)` in `ft_read_header` case
    `{'egi_mff_v3','egi_mff'}`): `mff_path.m:25 javaaddpath(fullfile(p, 'MFF-1.2.2-jar-with-dependencies.jar'))`,
    many `javaObject(...)` calls; licence `LICENSE.txt` = **GPL v3** [V].
  - `external/egi_mff_v2/java/MFF-1.2.jar` [V, tree listing].
  - `ft_read_header.m:1081` (`egi_mff_v1`): `if ~usejava('jvm') ft_error('the xml2struct requires
    MATLAB to be running with the Java virtual machine (JVM)')`; `ft_read_sens.m:403` similar [V].
  - `ft_hastoolbox` executes `<toolbox>_license` on first add (openmeeg, mne, duneuro, artinis) to
    display licence terms [W/V line 524-526].
  [I] Precedent therefore exists for a JAR under `external/` (e.g. `sqlite-jdbc`), added with
  `javaaddpath` inside a `cadwell_setup`/`mff_path`-style helper. JDBC via `java.sql.DriverManager`
  works in MATLAB without the Database Toolbox; Octave has no Java SQL bridge.
- **Python**: no `py.` calls in `fileio/`, `utilities/`, `forward/` [V]. Python appears only in
  `realtime/src/buffer/python/*.py` and `.github/scripts/*.py` [V, tree]. No precedent for a reader
  calling MATLAB's Python interface.
- **MEX**: `external/xdf/load_xdf_innerloop.{c,mexa64,mexmaci64,mexw32,mexw64}` shows precompiled
  MEX binaries are accepted under `external/` [V]. [I] A minimal SQLite MEX (mksqlite is LGPL-2.1+;
  a home-grown one bundling the public-domain sqlite3.c would be simplest licence-wise) would follow
  the same pattern, with `ft_compile_mex` support per the code guidelines.
- **Licence policy for `external/`** [V]: `external/COPYING`: "The external toolboxes are copyright
  their respective author and may not be covered under the same Open Source license as FieldTrip.
  Please look in the respective external toolbox directories for the README and COPYING files."
  `external/README`: "provided here with permission of the original toolbox authors as courtesy to
  the end-users", sometimes "lite" pruned versions. Observed licences: biosig **GPL** (README:
  "All software is published under the free software license GPL"), mffmatlabio **GPL-3**, xdf
  **BSD-2-Clause** (Ojeda & Kothe 2015). So GPL, LGPL-compatible and permissive code all coexist;
  FieldTrip itself is GPL-3 (`README.md`, `fileio/README`). [I] Our own Unlicense code is trivially
  compatible; the constraint runs the other way (no copying GPL BioSig into our repo).
- **Octave** [V/W]: no Octave claim for fileio. `utilities/ft_platform_supports.m` detects Octave
  (`exist('OCTAVE_VERSION','builtin')`, line 303) and gates features; website FAQ
  `faq/matlab/octave.md`: "FieldTrip development primarily aims at MATLAB ... Many of the core
  computations ... can in principle also be performed using Octave ... we don't have precise details
  on what works and what not." Hence a Java-based SQLite reader would be MATLAB-only, which is
  consistent with existing Java readers.

---

## 6. EEGLAB -> FieldTrip fileio (`pop_fileio.m`) [V, sccn/eeglab `develop`, 455 lines]

`ft_read_header.m` itself mentions EEGLAB only as a *source format* (`case 'eeglab_set'` 952,
`'eeglab_erp'` 955, `ft_hastoolbox('eeglab',1)` 2348 for Neuroscan) [V]. The EEGLAB side:

- Line 63-64: `if exist('plugin_askinstall') / if ~plugin_askinstall('Fileio', 'ft_read_data'), return; end`
  - the "Fileio" EEGLAB plugin is a packaged copy of FieldTrip's fileio module (the standalone
  mirror is https://github.com/fieldtrip/fileio, "a subset of the FieldTrip code related to the
  reading and writing of data" [W]); `sccn/fileio` does not exist (404).
- Line 105 / 152: `dat = ft_read_header(filename);` (no format option is passed for the header).
- Line 146 (GUI): `if ~isempty(restag.format), options = { options{:} 'dataformat' formats{restag.format} }; end`
  where `formats` (lines 93-102) is a hard-coded list of FieldTrip dataformat strings (`'auto' '4d'
  ... 'edf' ... 'egi_mff_v2' ... 'neuroscope_bin'`); **it does not include `nervus_eeg`** and would
  not include `cadwell_ezdata` unless EEGLAB is patched, but `'auto'` (default) lets `ft_filetype`
  decide, so autodetection is what makes a format reachable from EEGLAB.
- Lines 172, 180-203, 217:
  ```matlab
  if ~isfield(g, 'dataformat'), g.dataformat = 'auto'; end
  dataopts = {};
  ... (uV conversion) chanunitval(eegchanindx) = {'uV'}; dataopts = { dataopts{:} 'chanunit', chanunitval};
  if ~isempty(g.samples ), dataopts = { dataopts{:} 'begsample', g.samples(1), 'endsample', g.samples(2)}; end
  if ~isempty(g.trials  ), dataopts = { dataopts{:} 'begtrial', g.trials(1), 'endtrial', g.trials(2)}; end
  if ~strcmpi(g.dataformat, 'auto'), dataopts = { dataopts{:} 'dataformat' g.dataformat }; end
      if ~isempty(g.channels), dataopts = { dataopts{:} 'chanindx', g.channels }; end
          alldata = ft_read_data(filename, 'header', dat, dataopts{:});
  ...     alldata(ic,:,:) = ft_read_data(filename, 'header', dat, dataopts{:}, 'chanindx', g.channels(ic));
  ```
  Lines 185-191: EEG channels whose `dat.chanunit` is not `'uV'` are converted via the `'chanunit'`
  option - this only works when the header provides `chantype`/`chanunit`, which the Nervus header
  does not (see 1.2) [I: fill them in the Cadwell header].
- Lines 375, 382: `event = ft_read_event(eventfile, dataopts{:});` / `event = ft_read_event(filename, dataopts{:});`
  - the same `dataopts` (including `'dataformat'`) are forwarded, and since `ft_read_event`
  defaults `eventformat`/`headerformat` from... note: it passes `'dataformat'`, not `'eventformat'`,
  so for a non-auto format the event reader still relies on `ft_filetype` [I].
- Header -> EEG mapping, lines 240-260: `EEG.srate = dat.Fs; EEG.nbchan = dat.nChans;
  EEG.xmin = -dat.nSamplesPre/EEG.srate; EEG.trials = dat.nTrials; EEG.pnts = size(alldata,2)` or
  `dat.nSamples`; `EEG.chanlocs = struct('labels', dat.label)`; electrode positions only if
  `dat.elec` exists.
- Event mapping, lines 397-402:
  ```matlab
  EEG.event(index).type     = event(index).value;
  EEG.event(index).value    = event(index).type;
  EEG.event(index).latency  = event(index).sample+offset+subsample;
  EEG.event(index).duration = event(index).duration;
  ```
  (type/value swapped; `'boundary'` events with a duration are honoured by EEGLAB as gaps).

---

## 7. Summary of what this implies for a `cadwell_ezdata` reader [I]

1. Detection: `.ezdata` + magic `'SQLite format 3'` in `ft_filetype.m`, placed before generic checks.
2. Implementation: prefer a single `fileio/private/cadwell_ezdata.m` with the 1/2/5-argument
   contract (matches the current FAQ and the `biopac_acq`/`sccn_xdf` template); this needs **no**
   edits to `ft_read_header/data/event` and can be developed and shipped outside FieldTrip first
   (`cfg.headerformat = 'cadwell_ezdata'` etc.), then upstreamed with just the `ft_filetype` change.
3. Header: set `Fs, nChans, label (Nx1 cell), nSamples, nSamplesPre=0, nTrials=1, orig`, and also
   `chantype`/`chanunit` (needed for EEGLAB's uV handling); handle mixed sampling rates the "EDF way"
   (most prevalent rate) as the maintainers explicitly endorsed for Nervus.
4. Data: honour `begsample/endsample/chanindx` (SQL `LIMIT/OFFSET` or block indexing) instead of the
   Nervus approach of reading everything; return `chans x samples`.
5. Events: integer samples at `hdr.Fs`; `'boundary'` events with `duration` for pauses, as Nervus does,
   so EEGLAB displays gaps.
6. SQLite access: no precedent in FieldTrip. Options with precedent-compatible packaging: a JAR under
   `external/` loaded via `javaaddpath` (as mffmatlabio does; MATLAB-only), or a MEX under
   `external/` (as xdf does; needs binaries per platform + `ft_compile_mex` source). Add a
   `ft_hastoolbox` entry either way.
7. Tests: `test/test_cadwell_reading.m` with `% MEM`, `% WALLTIME`, `% DEPENDENCY`, `% DATA private`,
   `dccnpath('/project/3031000.02/test/original/eeg/cadwell')`, asserting header values and comparing
   samples with the vendor EDF/CSV export (exactly the approach already accepted for Nicolet); send
   de-identified test data to the maintainers rather than committing it; verify on Linux/macOS.
8. Process: 2-space indents, `ft_error`/`ft_warning`, GPL-3 header with author copyright, no CLA,
   PR against `master`, add a website page `getting_started/eeg/cadwell.md`. Historical turnaround
   was days when a test + data were included (#186, #266, #1358) and years when they were not (#302).
