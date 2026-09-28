function rec = cadwell_read(pathIn, varargin)
% cadwell_read - read a Cadwell Arc recording (CadLink study export) natively.
%
%   rec = cadwell_read(path)                % export folder, CadLink/Data folder or .ezdataindex file
%   rec = cadwell_read(path, 'PadGaps', true, 'Backend', 'jdbc', 'Frames', [first last])
%
% Options
%   'PadGaps'  (default true)  missing frame numbers (recording breaks) become
%                              zeros so that time stays aligned with the events
%   'Backend'  (default auto)  SQLite backend, see cadwell_sqlite
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
    dbs = unique({frames.joinDb});
    blobs = containers.Map('KeyType', 'char', 'ValueType', 'any');
    for d = 1:numel(dbs)
        f = fullfile(idx.dataDir, dbs{d});
        if ~exist(f, 'file'), error('cadwell_read:missingData', 'frame data file missing: %s', f); end
        db = cadwell_sqlite('open', f, opt.Backend);
        r = cadwell_sqlite('query', db, 'SELECT hex(FrameKey), Data FROM FrameInfo');
        cadwell_sqlite('close', db);
        for i = 1:size(r, 1), blobs(upper(char(r{i, 1}))) = uint8(r{i, 2}); end
    end
    nch = numel(idx.ampInputs); amp = idx.ampInputs; rate = idx.rate;
    cols = cell(1, numel(frames)); spf = zeros(1, numel(frames)); nums = [frames.number];
    padded = struct('startSample', {}, 'seconds', {});
    blocks = {}; cursor = 0; prev = [];
    for i = 1:numel(frames)
        if ~isKey(blobs, frames(i).keyHex)
            error('cadwell_read:missingFrame', 'frame %d (%s) not found in %s', frames(i).number, frames(i).keyHex, frames(i).joinDb);
        end
        if opt.PadGaps && ~isempty(prev) && frames(i).number > prev + 1
            missing = frames(i).number - prev - 1;
            blocks{end+1} = zeros(nch, missing * rate);
            padded(end+1) = struct('startSample', cursor + 1, 'seconds', missing);
            cursor = cursor + missing * rate;
        end
        fr = cadwell_decode_frame(blobs(frames(i).keyHex));
        n = numel(fr.samples{1}); blk = zeros(nch, n);
        for k = 1:numel(fr.ampInput)
            j = find(amp == fr.ampInput(k), 1);
            if ~isempty(j), blk(j, :) = fr.samples{k}'; end
        end
        blocks{end+1} = blk; spf(i) = n; cursor = cursor + n; prev = frames(i).number;
    end
    rec.data = [blocks{:}] * cadwell_unit_uv();
    rec.srate = rate; rec.ampInputs = amp; rec.unitUv = cadwell_unit_uv();
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
