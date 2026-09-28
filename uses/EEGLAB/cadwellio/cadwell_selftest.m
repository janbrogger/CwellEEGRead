function res = cadwell_selftest(refDir, backend)
% cadwell_selftest - verify the MATLAB/Octave port against reference data
% written by tools/make_matlab_reference.py (one sub-folder per export) and
% against the vendor's text export of cadwell-export1.
%
%   res = cadwell_selftest(refDir [, backend])
%
% Prints one line per check and returns a struct with ok (logical) and the
% individual results. Public domain (Unlicense).

    if nargin < 2, backend = ''; end
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
        % ---- B: full native read through the SQLite backend vs Python metadata
        if isempty(cadwell_sqlite('backends')) && isempty(backend)
            res = check(res, sprintf('%s index/events via SQLite backend (SKIPPED: no backend)', subs(s).name), true); continue;
        end
        try
            rec = cadwell_read(meta.index_path, 'Backend', backend, 'Frames', [meta.frame_numbers(1) meta.frame_numbers(end)]);
            ok = rec.srate == meta.rate && isequal(rec.ampInputs(:)', amp) && isequal(rec.labels(:)', meta.labels(:)') ...
                 && numel(rec.index.frames) == meta.n_index_frames && isequal(rec.index.ampType, meta.amp_type) ...
                 && strcmp(rec.recordGuid, meta.record_guid) && abs(rec.index.clockCorrectionSec * 1e6 - meta.clock_correction_us) < 1 ...
                 && numel(rec.events) == meta.n_events && numel(rec.index.gaps) == numel(meta.gaps) ...
                 && max(max(abs(rec.data - X'))) < 1e-6;
            res = check(res, sprintf('%s native read via ''%s'': index, labels, events, gaps, samples', subs(s).name, rec.index.file(end-12:end)), ok);
        catch err
            res = check(res, sprintf('%s native read failed: %s', subs(s).name, err.message), false);
        end
    end
    % ---- C: vendor text export of export 1 (raw ground truth, 7755 rows)
    txt = fullfile(here, '..', '..', '..', 'testdata', 'public', 'cadwell-export1', 'test', 'test-eeg20251031.txt');
    if exist(txt, 'file') && (~isempty(cadwell_sqlite('backends')) || ~isempty(backend))
        try
            rec = cadwell_read(fullfile(fileparts(fileparts(txt))), 'Backend', backend);
            T = read_text_export(txt); n = size(T, 1);
            dmax = max(max(abs(rec.data(:, 1:n)' - T)));
            res = check(res, sprintf('export1 native read vs vendor text export: %d rows, max |diff| %.4f uV', n, dmax), dmax <= 0.06);
        catch err
            res = check(res, sprintf('export1 text comparison failed: %s', err.message), false);
        end
    end
    if res.ok, fprintf('cadwell_selftest: ALL OK\n'); else fprintf('cadwell_selftest: FAILURES\n'); end
end

function res = check(res, msg, ok)
    res.ok = res.ok && ok; res.checks{end+1} = struct('msg', msg, 'ok', ok);
    if ok, fprintf('  PASS  %s\n', msg); else fprintf('  FAIL  %s\n', msg); end
end

function T = read_text_export(fn)
    lines = strsplit(fileread(fn), '\n'); rows = {};
    for i = 1:numel(lines)
        l = lines{i}; if isempty(l) || l(1) == '%', continue; end
        p = strsplit(strrep(l, ',', '.'), '\t'); rows{end+1} = str2double(p(2:end)); %#ok<AGROW>
    end
    T = vertcat(rows{:}) * 1000;    % mV -> uV
end
