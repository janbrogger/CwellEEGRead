function rec = cadwell_read(pathIn, varargin)
% cadwell_read - read a Cadwell Arc recording (CadLink study export) natively.
%
%   rec = cadwell_read(path)                % export folder, CadLink/Data folder or .ezdataindex file
%   rec = cadwell_read(path, 'PadGaps', true, 'Backend', 'native', 'Frames', [first last])
%
% Options
%   'PadGaps'  (default true)  missing frame numbers (recording breaks) become
%                              zeros so that time stays aligned with the events
%   'Backend'  (default 'native', pure MATLAB/Octave)  SQLite backend, see cadwell_sqlite
%   'Frames'   (default all)   restrict to frame numbers first..last
%
% Output struct
%   data        [nChannels x nSamples] double, microvolts, referential to the
%               recording reference (Cz on the recordings seen so far)
%   srate       nominal sampling rate
%   labels      1xN cell, 'EEG Fp1-Cz' ... (inferred from the headbox table)
%   ampInputs   1xN amplifier input numbers (data row order)
%   events      struct array from cadwell_read_events (onsetSec relative to data start)
%   gaps        struct array: startSample (1-based), seconds
%   samplesPerFrame, frameNumbers
%   startDatenum, startIso   data start (UTC) = first frame time + clock correction
%   recordGuid, patientGuid, headbox (struct), unitUv, index (the full index struct)
% Public domain (Unlicense).

    opt = struct('PadGaps', true, 'Backend', '', 'Frames', []);
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
    mats = cell(1, nf); spf = zeros(1, nf);
    for i = 1:nf
        fr = cadwell_decode_frame(uint8(blobs{where(i)}));
        if isempty(fr.matrix), fr.matrix = [fr.samples{:}]; end   % channels of unequal length: fails, as it should
        [~, j] = ismember(fr.ampInput, amp);                       % data row of every channel block (0 = not in the layout)
        m = zeros(size(fr.matrix, 1), nch); m(:, j(j > 0)) = fr.matrix(:, j > 0);
        mats{i} = m; spf(i) = size(m, 1);
    end
    padded = struct('startSample', {}, 'seconds', {});
    gapSamples = 0;
    if opt.PadGaps && nf > 1, gapSamples = sum(max(diff(nums) - 1, 0)) * rate; end
    rec.data = zeros(nch, sum(spf) + gapSamples);
    cursor = 0;
    for i = 1:nf
        if opt.PadGaps && i > 1 && nums(i) > nums(i - 1) + 1
            missing = nums(i) - nums(i - 1) - 1;
            padded(end+1) = struct('startSample', cursor + 1, 'seconds', missing);
            cursor = cursor + missing * rate;                       % already zero
        end
        rec.data(:, cursor + (1:spf(i))) = mats{i}' * unit;
        cursor = cursor + spf(i);
    end
    rec.srate = rate; rec.ampInputs = amp; rec.unitUv = unit;
    [rec.labels, rec.headbox] = cadwell_layout(amp, idx.ampType);
    rec.samplesPerFrame = spf; rec.frameNumbers = nums; rec.gaps = padded;
    rec.startDatenum = frames(1).datenum + idx.clockCorrectionSec / 86400;
    rec.startIso = datestr(rec.startDatenum, 'yyyy-mm-ddTHH:MM:SS.FFF');
    rec.recordGuid = idx.recordGuid; rec.patientGuid = idx.patientGuid; rec.index = idx;
    stem = regexprep(indexFile, '\.ezdataindex$', '');
    rec.events = cadwell_read_events([stem '.ezevents'], frames(1).sec, opt.Backend);
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
