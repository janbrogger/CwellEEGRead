function rec = cadwell_read(pathIn, varargin)
% cadwell_read - read a Cadwell Arc recording (CadLink study export) natively.
%
%   rec = cadwell_read(path)                % export folder, CadLink/Data folder or .ezdataindex file
%   rec = cadwell_read(path, 'PadGaps', true, 'Backend', 'native', 'Frames', [first last], 'EventTiming', 'ticks')
%
% Options
%   'PadGaps'  (default true)  missing frame numbers (recording pauses) become
%                              zeros so that time stays aligned with wall-clock
%                              time; false concatenates the segments and shifts
%                              the event onsets after each pause accordingly
%   'Backend'  (default 'native', pure MATLAB/Octave)  SQLite backend, see cadwell_sqlite
%   'Frames'   (default all)   restrict to frame numbers first..last
%   'EventTiming' 'ticks' (default) places events on the amplifier sample
%              clock (StartOffset ticks through the stored frames' tick spans,
%              REQ021); 'stamp' uses the wall-clock stamp relative to the first
%              frame's stamp as the vendor's EDF export does, which lands early
%              by the drift between the two clocks (about 0.35 s per hour on
%              Essentia recordings, the stamp clock running behind)
%
% Output struct
%   data        [nChannels x nSamples] double, microvolts, referential to the
%               recording reference (Cz on the recordings seen so far)
%   srate       nominal sampling rate
%   labels      1xN cell, 'EEG Fp1-Cz' ... (inferred from the headbox table)
%   ampInputs   1xN amplifier input numbers (data row order)
%   events      struct array from cadwell_read_events; onsetSec is relative to
%               the data start, on the axis chosen by 'EventTiming', and
%               consistent with 'PadGaps' (onsetSecStamp keeps the wall-clock
%               onset relative to the first frame, onsetSecTicks the sample-clock one)
%   frameTicks  [nFrames x 4] start ticks, end ticks (100 ns), first sample (1-based), samples
%   gaps        struct array, one per recording pause (missing frame numbers):
%               startSample (1-based sample in data where the pause starts, or
%               where the segments were joined), seconds, startSec (wall-clock
%               seconds after the first frame), padded (true/false)
%   samplesPerFrame, frameNumbers
%   startDatenum, startIso   data start (UTC) = first frame time + clock correction
%   recordGuid, patientGuid, headbox (struct), unitUv, index (the full index struct)
% Public domain (Unlicense).

    opt = struct('PadGaps', true, 'Backend', '', 'Frames', [], 'EventTiming', 'ticks');
    for k = 1:2:numel(varargin), opt.(varargin{k}) = varargin{k+1}; end
    indexFile = locate_index(pathIn);
    idx = cadwell_read_index(indexFile, opt.Backend);
    frames = idx.frames;
    if ~isempty(opt.Frames)
        frames = frames([frames.number] >= opt.Frames(1) & [frames.number] <= opt.Frames(2));
    end
    if isempty(frames), error('cadwell_read:noFrames', 'no frames selected'); end
    % load the blobs of every data file the index names
    % (all blobs of a file in one table read; frames are matched to blobs by
    % FrameKey with one ismember instead of a containers.Map, which is slow in Octave)
    dbs = unique({frames.joinDb}); blobKeys = {}; blobs = {};
    for d = 1:numel(dbs)
        f = fullfile(idx.dataDir, dbs{d});
        if ~exist(f, 'file'), error('cadwell_read:missingData', 'frame data file missing: %s', f); end
        db = cadwell_sqlite('open', f, opt.Backend);
        t = cadwell_sqlite('table', db, 'FrameInfo');
        cadwell_sqlite('close', db);
        keys = cadwell_tcol(t, 'FrameKey');
        blobKeys = [blobKeys; cellfun(@cadwell_key_hex, keys, 'UniformOutput', false)];   %#ok<AGROW>
        blobs = [blobs; cadwell_tcol(t, 'Data')];                                          %#ok<AGROW>
    end
    [found, where] = ismember({frames.keyHex}, blobKeys);
    if ~all(found)
        i = find(~found, 1);
        error('cadwell_read:missingFrame', 'frame %d (%s) not found in %s', frames(i).number, frames(i).keyHex, frames(i).joinDb);
    end
    nch = numel(idx.ampInputs); amp = idx.ampInputs; rate = idx.rate; nf = numel(frames);
    nums = [frames.number]; unit = cadwell_unit_uv();
    % decode every frame (a [samples x channels] matrix each), then place the
    % blocks into one preallocated output instead of concatenating
    mats = cell(1, nf); spf = zeros(1, nf); ticks = zeros(nf, 2);
    for i = 1:nf
        fr = cadwell_decode_frame(uint8(blobs{where(i)}));
        ticks(i, :) = [fr.startTicks, fr.endTicks];
        if isempty(fr.matrix), fr.matrix = [fr.samples{:}]; end   % channels of unequal length: fails, as it should
        [~, j] = ismember(fr.ampInput, amp);                       % data row of every channel block (0 = not in the layout)
        m = zeros(size(fr.matrix, 1), nch); m(:, j(j > 0)) = fr.matrix(:, j > 0);
        mats{i} = m; spf(i) = size(m, 1);
    end
    gaps = struct('startSample', {}, 'seconds', {}, 'startSec', {}, 'padded', {});
    gapSamples = 0;
    if opt.PadGaps && nf > 1, gapSamples = sum(max(diff(nums) - 1, 0)) * rate; end
    rec.data = zeros(nch, sum(spf) + gapSamples);
    cursor = 0; frameTicks = zeros(nf, 4);
    for i = 1:nf
        if i > 1 && nums(i) > nums(i - 1) + 1                        % recording pause: frame numbers are seconds
            missing = nums(i) - nums(i - 1) - 1;
            gaps(end+1) = struct('startSample', cursor + 1, 'seconds', missing, ...
                                 'startSec', nums(i - 1) + 1 - nums(1), 'padded', logical(opt.PadGaps));
            if opt.PadGaps, cursor = cursor + missing * rate; end   % already zero
        end
        rec.data(:, cursor + (1:spf(i))) = mats{i}' * unit;
        frameTicks(i, :) = [ticks(i, 1), ticks(i, 2), cursor + 1, spf(i)];
        cursor = cursor + spf(i);
    end
    rec.frameTicks = frameTicks;
    rec.srate = rate; rec.ampInputs = amp; rec.unitUv = unit;
    [rec.labels, rec.headbox] = cadwell_layout(amp, idx.ampType);
    rec.samplesPerFrame = spf; rec.frameNumbers = nums; rec.gaps = gaps;
    rec.startDatenum = frames(1).datenum + idx.clockCorrectionSec / 86400;
    rec.startIso = datestr(rec.startDatenum, 'yyyy-mm-ddTHH:MM:SS.FFF');
    rec.recordGuid = idx.recordGuid; rec.patientGuid = idx.patientGuid; rec.index = idx;
    stem = regexprep(indexFile, '\.ezdataindex$', '');
    rec.events = cadwell_read_events([stem '.ezevents'], frames(1).sec, opt.Backend);
    rec.eventTiming = lower(opt.EventTiming);
    for k = 1:numel(rec.events)
        rec.events(k).onsetSecStamp = rec.events(k).onsetSec;                   % wall clock, relative to the first frame's stamp
        rec.events(k).onsetSecTicks = event_sample(rec.events(k).startTicks, frameTicks, rate, opt.PadGaps) / rate;
        rec.events(k).durationSecTicks = (rec.events(k).endTicks - rec.events(k).startTicks) / 1e7;
        rec.events(k).onsetSecOrigin = rec.events(k).onsetSecStamp;            % kept for older callers
    end
    switch rec.eventTiming
        case 'ticks'
            for k = 1:numel(rec.events)
                rec.events(k).onsetSec = rec.events(k).onsetSecTicks; rec.events(k).durationSec = rec.events(k).durationSecTicks;
            end
            % event_sample already maps into the padded or concatenated sample axis
        case 'stamp'
            if ~opt.PadGaps
                % concatenated segments: an event after a pause moves earlier by the
                % pause length; an event stamped inside a pause lands on the join
                for g = numel(gaps):-1:1
                    for k = 1:numel(rec.events)
                        o = rec.events(k).onsetSecStamp;
                        if o >= gaps(g).startSec + gaps(g).seconds
                            rec.events(k).onsetSec = rec.events(k).onsetSec - gaps(g).seconds;
                        elseif o > gaps(g).startSec
                            rec.events(k).onsetSec = rec.events(k).onsetSec - (o - gaps(g).startSec);
                        end
                    end
                end
            end
        otherwise
            error('cadwell_read:eventTiming', 'EventTiming must be ''ticks'' or ''stamp''');
    end
end

function s = event_sample(t, frameTicks, rate, padGaps)
    % 0-based fractional sample of an amplifier-clock instant t (100 ns ticks):
    % linear within the stored frame that holds it, nominal rate across padded
    % pauses and beyond the stored range; with concatenated pauses an instant
    % inside a pause lands on the join (REQ021).
    k = find(frameTicks(:, 1) <= t, 1, 'last');
    if isempty(k)
        s = (frameTicks(1, 3) - 1) - (frameTicks(1, 1) - t) / 1e7 * rate; return;
    end
    st = frameTicks(k, 1); en = frameTicks(k, 2); first = frameTicks(k, 3) - 1; n = frameTicks(k, 4);
    if t < en && en > st
        s = first + (t - st) / (en - st) * n;
    elseif ~padGaps && k < size(frameTicks, 1) && t < frameTicks(k + 1, 1)
        s = first + n;                                              % inside a concatenated pause: the join
    else
        s = first + n + (t - en) / 1e7 * rate;
    end
end

function f = locate_index(p)
    if exist(p, 'file') == 2, f = p; return; end
    cands = {p, fullfile(p, 'native-export', 'CadLink', 'Data'), fullfile(p, 'CadLink', 'Data'), fullfile(p, 'Data')};
    for k = 1:numel(cands)
        d = dir(fullfile(cands{k}, '*.ezdataindex'));
        if numel(d) == 1, f = fullfile(cands{k}, d(1).name); return; end
        if numel(d) > 1, error('cadwell_read:many', '%s holds %d records; pass the .ezdataindex file', cands{k}, numel(d)); end
    end
    error('cadwell_read:notFound', 'no .ezdataindex under %s', p);
end
