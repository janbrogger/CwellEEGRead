function idx = cadwell_read_index(indexFile, backend)
% cadwell_read_index - read a Cadwell <record>-<timestamp>.ezdataindex file.
%
%   idx = cadwell_read_index(indexFile [, backend])
%
% Returns a struct with fields
%   file, dataDir, recordGuid, patientGuid, authorGuid, ampType, rate,
%   channels  (struct array: channel, ampInput, rate)  from TrackInfo track 0
%   ampInputs (sorted amplifier input numbers = export column order)
%   frames    (struct array, track 0, in frame order: number, timestamp (ISO
%              string, UTC), datenum, sec, joinDb, keyHex)
%   gaps      (struct array: track, startOffset, endOffset, startTime, endTime)
%   clockCorrectionSec  (PcTime - SyncTime of the first PcTimeSync row)
%   originDatenum / originSec / originIso  (first stored frame's time stamp, UTC;
%              originSec = seconds since 2000-01-01, full 100-ns precision)
%   startDatenum  (origin + clock correction = the vendor's EDF start rule)
% backend: '' (default, the native reader) or one of cadwell_sqlite('backends').
% Public domain (Unlicense).

    if nargin < 2, backend = ''; end
    db = cadwell_sqlite('open', indexFile, backend);
    c = onCleanup(@() cadwell_sqlite('close', db));
    idx.file = indexFile; idx.dataDir = fileparts(indexFile);
    % media descriptor: u32 tag, u32 0, then three length-prefixed ASCII GUIDs
    idx.recordGuid = ''; idx.patientGuid = ''; idx.authorGuid = '';
    t = cadwell_sqlite('table', db, 'MediaHeader');
    v = pick(t, strcmp(cadwell_tcol(t, 'Key'), 'MediaDescriptor'), 'Value');
    if ~isempty(v)
        b = uint8(v{1}); p = 8; g = cell(1, 3);
        for k = 1:3
            n = double(typecast(b(p + (1:4)), 'uint32')); g{k} = char(b(p + 4 + (1:n))); p = p + 4 + n;
        end
        idx.patientGuid = g{1}; idx.recordGuid = g{2}; idx.authorGuid = g{3};
    end
    % amplifier type from the AMPLAYOUT blob (u32 at byte offset 32), earliest row
    idx.ampType = [];
    t = sort_rows(cadwell_sqlite('table', db, 'MiscInfo'), 'TimeStamp');
    v = pick(t, strcmp(cadwell_tcol(t, 'Key'), 'AMPLAYOUT'), 'Value');
    if ~isempty(v) && numel(v{1}) >= 36
        b = uint8(v{1});
        if isequal(b(1:4), uint8([11 132 117 87]))                % 0B 84 75 57
            idx.ampType = double(typecast(b(33:36), 'uint32'));
        end
    end
    % channel table: TrackInfo, track 0, lowest offset
    t = sort_rows(cadwell_sqlite('table', db, 'TrackInfo'), 'Offset');
    v = pick(t, num(cadwell_tcol(t, 'Track')) == 0, 'Data');
    if isempty(v) || isempty(v{1}), error('cadwell_read_index:trackinfo', 'no TrackInfo for track 0'); end
    idx.channels = parse_channel_records(uint8(v{1}));
    idx.rate = idx.channels(1).rate;
    idx.ampInputs = sort([idx.channels.ampInput]);
    % frame index (track 0, by offset = frame number)
    t = sort_rows(cadwell_sqlite('table', db, 'FrameInfo'), 'Offset');
    t.rows = t.rows(num(cadwell_tcol(t, 'Track')) == 0, :);
    off = cadwell_tcol(t, 'Offset'); ts = cadwell_tcol(t, 'TimeStamp'); jd = cadwell_tcol(t, 'JoinDatabase'); fk = cadwell_tcol(t, 'FrameKey');
    n = numel(off);
    idx.frames = repmat(struct('number', 0, 'timestamp', '', 'datenum', 0, 'sec', 0, 'joinDb', '', 'keyHex', ''), n, 1);
    for i = 1:n
        idx.frames(i).number = double(off{i}); idx.frames(i).timestamp = char(ts{i});
        idx.frames(i).datenum = cadwell_parse_timestamp(char(ts{i}));
        idx.frames(i).sec = cadwell_timestamp_sec(char(ts{i}));
        idx.frames(i).joinDb = char(jd{i}); idx.frames(i).keyHex = cadwell_key_hex(fk{i});
    end
    % gaps
    idx.gaps = struct('track', {}, 'startOffset', {}, 'endOffset', {}, 'startTime', {}, 'endTime', {});
    try
        t = sort_rows(cadwell_sqlite('table', db, 'GapInfo'), 'StartTime');
        tr = cadwell_tcol(t, 'Track'); so = cadwell_tcol(t, 'StartOffset'); eo = cadwell_tcol(t, 'EndOffset');
        st = cadwell_tcol(t, 'StartTime'); et = cadwell_tcol(t, 'EndTime');
        for i = 1:numel(tr)
            idx.gaps(end+1) = struct('track', double(tr{i}), 'startOffset', double(so{i}), 'endOffset', double(eo{i}), ...
                                     'startTime', char(st{i}), 'endTime', char(et{i}));
        end
    catch
    end
    % clock correction: earliest PcTimeSync row
    idx.clockCorrectionSec = 0;
    try
        t = sort_rows(cadwell_sqlite('table', db, 'PcTimeSync'), 'PcTime');
        if ~isempty(t.rows)
            pc = cadwell_tcol(t, 'PcTime'); sy = cadwell_tcol(t, 'SyncTime');
            idx.clockCorrectionSec = cadwell_timestamp_sec(char(pc{1})) - cadwell_timestamp_sec(char(sy{1}));
        end
    catch
    end
    if n > 0
        idx.originIso = idx.frames(1).timestamp; idx.originDatenum = idx.frames(1).datenum; idx.originSec = idx.frames(1).sec;
        idx.startDatenum = idx.originDatenum + idx.clockCorrectionSec / 86400;
    else
        idx.originIso = ''; idx.originDatenum = NaN; idx.originSec = NaN; idx.startDatenum = NaN;
    end
end

function v = pick(t, mask, col)
    c = cadwell_tcol(t, col); v = c(mask);
end

function x = num(c)
    x = zeros(numel(c), 1);
    for i = 1:numel(c), if ~isempty(c{i}), x(i) = double(c{i}); end, end
end

function t = sort_rows(t, col)
    c = cadwell_tcol(t, col);
    if isempty(c), return; end
    if ischar(c{1}), [~, o] = sort(c); else [~, o] = sort(num(c)); end
    t.rows = t.rows(o, :); t.rowids = t.rowids(o);
end

function ch = parse_channel_records(blob)
    tag = uint8([171 121 33 147 222 66 37 162]);
    pos = strfind(char(blob(:)'), char(tag));
    ch = repmat(struct('channel', 0, 'ampInput', 0, 'rate', 0), 1, numel(pos));
    for k = 1:numel(pos)
        p = pos(k) - 1; u = typecast(blob(p + 8 + (1:64)), 'uint32');
        ch(k).channel = double(u(2)); ch(k).ampInput = double(u(5)); ch(k).rate = double(u(11));
    end
end
