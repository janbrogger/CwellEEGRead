function res = cadwell_selftest(refDir, backends)
% cadwell_selftest - verify the MATLAB/Octave port against reference data
% written by tools/make_matlab_reference.py --tables (one sub-folder per
% export) and against the vendor's text export of cadwell-export1.
%
%   res = cadwell_selftest(refDir [, backends])
%
% backends: cell array of SQLite backends to run the read checks through
% (default: every available one, cadwell_sqlite('backends'); 'native' first).
% Checks per export:
%   A  frame decoder vs Python on the stored frame blobs (no SQLite involved)
%   B  full read through each backend vs Python metadata and samples
%   D  native SQLite reader: every table of every file, dumped in the same
%      canonical serialization as tools/make_matlab_reference.py, must equal
%      tables.bin byte for byte
%   E  exports with a recording pause: padded and concatenated reads agree
%      (data, pause position and length, event onsets shifted by the pause)
%   F  event timing (REQ021): the tick-clock and stamp-clock onsets of every
%      event differ by the drift the frames show at that point, within 5 ms,
%      and 'EventTiming' 'stamp' reproduces the old stamp placement
% and C: export 1 through each backend vs the vendor's text export.
% Prints one line per check and returns a struct with ok (logical) and the
% individual results. Public domain (Unlicense).

    if nargin < 2 || isempty(backends), backends = cadwell_sqlite('backends'); end
    if ischar(backends), backends = {backends}; end
    res.ok = true; res.checks = {};
    here = fileparts(mfilename('fullpath'));
    subs = dir(refDir); subs = subs([subs.isdir] & ~ismember({subs.name}, {'.', '..'}));
    for s = 1:numel(subs)
        d = fullfile(refDir, subs(s).name);
        meta = jsondecode(fileread(fullfile(d, 'meta.json')));
        % ---- A: decoder vs Python on stored frame blobs (no SQLite involved)
        fid = fopen(fullfile(d, 'frames.bin'), 'rb'); blobs = {};
        while true
            n = fread(fid, 1, 'uint32=>double'); if isempty(n), break; end
            blobs{end+1} = fread(fid, n, 'uint8=>uint8')'; %#ok<AGROW>
        end
        fclose(fid);
        fid = fopen(fullfile(d, 'expected.bin'), 'rb'); expected = fread(fid, [meta.shape(1), meta.shape(2)], 'double'); fclose(fid);
        amp = meta.amp_inputs(:)'; blocks = {}; spf = []; ticks = [];
        for i = 1:numel(blobs)
            fr = cadwell_decode_frame(blobs{i}); n = numel(fr.samples{1}); blk = zeros(numel(amp), n);
            for k = 1:numel(fr.ampInput), blk(amp == fr.ampInput(k), :) = fr.samples{k}'; end
            blocks{end+1} = blk; spf(end+1) = n; ticks(end+1) = fr.startTicks; %#ok<AGROW>
        end
        X = ([blocks{:}] * cadwell_unit_uv())';
        res = check(res, sprintf('%s decoder: samples equal Python (max |diff| %.2e uV)', subs(s).name, max(abs(X(:) - expected(:)))), ...
                    isequal(size(X), size(expected)) && max(abs(X(:) - expected(:))) < 1e-6);
        res = check(res, sprintf('%s decoder: samples per frame and start ticks', subs(s).name), ...
                    isequal(spf, meta.samples_per_frame(:)') && isequal(ticks, meta.start_ticks(:)'));
        % ---- B: full read through each SQLite backend vs Python metadata
        for b = 1:numel(backends)
            try
                rec = cadwell_read(meta.index_path, 'Backend', backends{b}, 'Frames', [meta.frame_numbers(1) meta.frame_numbers(end)]);
                ok = rec.srate == meta.rate && isequal(rec.ampInputs(:)', amp) && isequal(rec.labels(:)', meta.labels(:)') ...
                     && numel(rec.index.frames) == meta.n_index_frames && isequal(rec.index.ampType, meta.amp_type) ...
                     && strcmp(rec.recordGuid, meta.record_guid) && abs(rec.index.clockCorrectionSec * 1e6 - meta.clock_correction_us) < 1 ...
                     && numel(rec.events) == meta.n_events && numel(rec.index.gaps) == numel(meta.gaps) ...
                     && max(max(abs(rec.data - X'))) < 1e-6;
                res = check(res, sprintf('%s read via ''%s'': index, labels, events, gaps, samples', subs(s).name, backends{b}), ok);
            catch err
                res = check(res, sprintf('%s read via ''%s'' failed: %s', subs(s).name, backends{b}, err.message), false);
            end
        end
        % ---- E: recording pauses (exports whose index skips frame numbers)
        if ~isempty(meta.gaps)
            try
                res = check(res, sprintf('%s recording pause: padded and concatenated reads consistent', subs(s).name), ...
                            check_gaps(meta.index_path));
            catch err
                res = check(res, sprintf('%s recording pause check failed: %s', subs(s).name, err.message), false);
            end
        end
        % ---- F: event timing, ticks versus stamps against the frame drift
        % (Essentia frame stamps are smooth to a few us; Apollo stamps are reception
        % times with a few ms of jitter, so the tolerance follows the stamp jitter)
        try
            [worst, tol] = check_timing(meta.index_path);
            res = check(res, sprintf('%s event timing: tick-clock onsets = stamp onsets + frame drift (max |resid| %.2f ms, tolerance %.0f ms)', subs(s).name, worst, tol), worst < tol);
        catch err
            res = check(res, sprintf('%s event timing check failed: %s', subs(s).name, err.message), false);
        end
        % ---- D: native SQLite reader, every table of every file, byte for byte
        tb = fullfile(d, 'tables.bin');
        if exist(tb, 'file')
            try
                [ok, msg] = compare_tables(fileparts(meta.index_path), tb);
                res = check(res, sprintf('%s native SQLite reader vs Python sqlite3, all tables of all files: %s', subs(s).name, msg), ok);
            catch err
                res = check(res, sprintf('%s native SQLite reader table dump failed: %s', subs(s).name, err.message), false);
            end
        else
            res = check(res, sprintf('%s native SQLite reader tables check (SKIPPED: no tables.bin, rerun make_matlab_reference.py --tables)', subs(s).name), true);
        end
    end
    % ---- C: vendor text export of export 1 (raw ground truth, 7755 rows)
    txt = fullfile(here, '..', '..', '..', 'testdata', 'public', 'cadwell-export1', 'test', 'test-eeg20251031.txt');
    if exist(txt, 'file')
        for b = 1:numel(backends)
            try
                rec = cadwell_read(fullfile(fileparts(fileparts(txt))), 'Backend', backends{b});
                T = read_text_export(txt); n = size(T, 1);
                dmax = max(max(abs(rec.data(:, 1:n)' - T)));
                res = check(res, sprintf('export1 read via ''%s'' vs vendor text export: %d rows, max |diff| %.4f uV', backends{b}, n, dmax), dmax <= 0.06);
            catch err
                res = check(res, sprintf('export1 text comparison via ''%s'' failed: %s', backends{b}, err.message), false);
            end
        end
    end
    if res.ok, fprintf('cadwell_selftest: ALL OK\n'); else fprintf('cadwell_selftest: FAILURES\n'); end
end

function [worst, tol] = check_timing(indexPath)
    % largest residual (ms) of (onsetSecTicks - onsetSecStamp) against the frame
    % drift (frame stamp seconds minus frame tick seconds) interpolated at the event
    r = cadwell_read(indexPath, 'EventTiming', 'ticks'); s = cadwell_read(indexPath, 'EventTiming', 'stamp');
    f = r.index.frames; ft = r.frameTicks;
    stampSec = [f.sec] - f(1).sec; tickSec = (ft(:, 1)' - ft(1, 1)) / 1e7; drift = stampSec - tickSec;   % stamp clock minus tick clock
    % Essentia frames span exactly one tick-second; Apollo frames have measured
    % spans (about 1.003 s for 248-251 samples), so a sub-frame position is
    % uncertain by that irregularity: widen the tolerance accordingly
    jitter = 1e3 * max(abs((ft(:, 2) - ft(:, 1)) / 1e7 - ft(:, 4) / r.srate));   % ms
    tol = 5; if jitter > 1, tol = 5 + 5 * jitter; end
    worst = 0;
    for k = 1:numel(r.events)
        e = r.events(k); t = (e.startTicks - ft(1, 1)) / 1e7;
        if t < tickSec(1) || t > tickSec(end), continue; end
        expected = -interp1(tickSec, drift, t);                    % ticks onset - stamp onset
        resid = 1e3 * abs((e.onsetSecTicks - e.onsetSecStamp) - expected);
        worst = max(worst, resid);
        if abs(s.events(k).onsetSec - e.onsetSecStamp) > 1e-9, worst = inf; end
    end
end

function ok = check_gaps(indexPath)
    a = cadwell_read(indexPath, 'PadGaps', true); b = cadwell_read(indexPath, 'PadGaps', false);
    ok = numel(a.gaps) == numel(b.gaps) && numel(a.gaps) >= 1 && all([a.gaps.padded]) && ~any([b.gaps.padded]);
    removed = 0;
    for g = 1:numel(a.gaps)
        ns = a.gaps(g).seconds * a.srate;
        ok = ok && a.gaps(g).seconds == b.gaps(g).seconds && a.gaps(g).startSec == b.gaps(g).startSec ...
             && b.gaps(g).startSample == a.gaps(g).startSample - removed ...
             && all(all(a.data(:, a.gaps(g).startSample + (0:ns - 1)) == 0));          % the pause is zeros when padded
        removed = removed + ns;
    end
    ok = ok && size(b.data, 2) == size(a.data, 2) - removed;
    keep = true(1, size(a.data, 2));                                                    % dropping the pauses gives the concatenated data
    for g = 1:numel(a.gaps), keep(a.gaps(g).startSample + (0:a.gaps(g).seconds * a.srate - 1)) = false; end
    ok = ok && isequal(a.data(:, keep), b.data);
    for k = 1:numel(a.events)                                                           % onsets: unchanged before, shifted after
        o = a.events(k).onsetSec; shift = 0; inside = false;
        for g = 1:numel(a.gaps)
            if o >= a.gaps(g).startSec + a.gaps(g).seconds, shift = shift + a.gaps(g).seconds;
            elseif o > a.gaps(g).startSec, inside = true; end
        end
        ok = ok && (inside || abs(b.events(k).onsetSec - (o - shift)) < 1e-9);
    end
end

function res = check(res, msg, ok)
    res.ok = res.ok && ok; res.checks{end+1} = struct('msg', msg, 'ok', ok);
    if ok, fprintf('  PASS  %s\n', msg); else fprintf('  FAIL  %s\n', msg); end
end

function [ok, msg] = compare_tables(dataDir, refFile)
    % Serialize every table of every *.ez* file exactly as dump_tables in
    % tools/make_matlab_reference.py does and compare with the reference stream.
    fid = fopen(refFile, 'rb'); ref = fread(fid, inf, 'uint8=>uint8')'; fclose(fid);
    files = dir(fullfile(dataDir, '*.ez*')); names = sort({files.name});
    pos = 1; ntab = 0; nrow = 0;
    for f = 1:numel(names)
        db = cadwell_sqlite_native('open', fullfile(dataDir, names{f}));
        tables = cadwell_sqlite_native('tables', db);
        for k = 1:numel(tables)
            t = cadwell_sqlite_native('table', db, tables{k});
            chunk = serialize_table(names{f}, tables{k}, t);
            n = numel(chunk); ntab = ntab + 1; nrow = nrow + size(t.rows, 1);
            if pos + n - 1 > numel(ref) || ~isequal(chunk, ref(pos:pos + n - 1))
                bad = find(chunk ~= ref(pos:min(pos + n - 1, numel(ref))), 1);
                if isempty(bad), bad = min(n, numel(ref) - pos + 2); end
                ok = false; msg = sprintf('MISMATCH in %s table %s at byte %d of its dump', names{f}, tables{k}, bad); return;
            end
            pos = pos + n;
        end
    end
    ok = pos == numel(ref) + 1;
    msg = sprintf('%d files, %d tables, %d rows, %d bytes identical', numel(names), ntab, nrow, pos - 1);
    if ~ok, msg = sprintf('reference has %d bytes left after %d tables', numel(ref) - pos + 1, ntab); end
end

function out = serialize_table(fileName, tableName, t)
    parts = {uint8(255), lstr(fileName), lstr(tableName), u32(size(t.rows, 1)), u32(numel(t.columns))};
    for k = 1:numel(t.columns), parts{end+1} = lstr(t.columns{k}); end %#ok<AGROW>
    for i = 1:size(t.rows, 1)
        parts{end+1} = i64(t.rowids(i)); %#ok<AGROW>
        for k = 1:numel(t.columns)
            v = t.rows{i, k};
            switch t.kinds(i, k)                                       % storage class as stored in the file
                case 0, parts{end+1} = uint8(0);                                          %#ok<AGROW>
                case 1, parts{end+1} = [uint8(1), i64(v)];                                %#ok<AGROW>
                case 2, parts{end+1} = [uint8(2), typecast(double(v), 'uint8')];          %#ok<AGROW>
                case 3, parts{end+1} = [uint8(3), lstr(v)];                               %#ok<AGROW>
                case 4, parts{end+1} = [uint8(4), u32(numel(v)), reshape(v, 1, [])];      %#ok<AGROW>
            end
        end
    end
    out = [parts{:}];
end

function b = lstr(s)
    e = unicode2native(s, 'UTF-8'); b = [u32(numel(e)), reshape(uint8(e), 1, [])];
end

function b = u32(v), b = typecast(uint32(v), 'uint8'); end
function b = i64(v), b = typecast(int64(v), 'uint8'); end

function T = read_text_export(fn)
    lines = strsplit(fileread(fn), '\n'); rows = {};
    for i = 1:numel(lines)
        l = lines{i}; if isempty(l) || l(1) == '%', continue; end
        p = strsplit(strrep(l, ',', '.'), '\t'); rows{end+1} = str2double(p(2:end)); %#ok<AGROW>
    end
    T = vertcat(rows{:}) * 1000;    % mV -> uV
end
