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
%              string, UTC), datenum, joinDb, keyHex)
%   gaps      (struct array: track, startOffset, endOffset, startTime, endTime)
%   clockCorrectionSec  (PcTime - SyncTime of the first PcTimeSync row)
%   originDatenum / originSec / originIso  (first stored frame's time stamp, UTC;
%              originSec = seconds since 2000-01-01, full 100-ns precision)
%   startDatenum  (origin + clock correction = the vendor's EDF start rule)
% Public domain (Unlicense).

    if nargin < 2, backend = ''; end
    db = cadwell_sqlite('open', indexFile, backend);
    c = onCleanup(@() cadwell_sqlite('close', db));
    idx.file = indexFile; idx.dataDir = fileparts(indexFile);
    % media descriptor: u32 tag, u32 0, then three length-prefixed ASCII GUIDs
    idx.recordGuid = ''; idx.patientGuid = ''; idx.authorGuid = '';
    r = cadwell_sqlite('query', db, 'SELECT Value FROM MediaHeader WHERE Key=''MediaDescriptor''');
    if ~isempty(r)
        b = uint8(r{1}); p = 8; g = cell(1, 3);
        for k = 1:3
            n = double(typecast(b(p + (1:4)), 'uint32')); g{k} = char(b(p + 4 + (1:n))); p = p + 4 + n;
        end
        idx.patientGuid = g{1}; idx.recordGuid = g{2}; idx.authorGuid = g{3};
    end
    % amplifier type from the AMPLAYOUT blob (u32 at byte offset 32)
    idx.ampType = [];
    r = cadwell_sqlite('query', db, 'SELECT Value FROM MiscInfo WHERE Key=''AMPLAYOUT'' ORDER BY TimeStamp LIMIT 1');
    if ~isempty(r) && numel(r{1}) >= 36
        b = uint8(r{1});
        if isequal(b(1:4), uint8([11 132 117 87]))                % 0B 84 75 57
            idx.ampType = double(typecast(b(33:36), 'uint32'));
        end
    end
    % channel table
    r = cadwell_sqlite('query', db, 'SELECT Data FROM TrackInfo WHERE Track=0 ORDER BY Offset LIMIT 1');
    if isempty(r) || isempty(r{1}), error('cadwell_read_index:trackinfo', 'no TrackInfo for track 0'); end
    idx.channels = parse_channel_records(uint8(r{1}));
    idx.rate = idx.channels(1).rate;
    idx.ampInputs = sort([idx.channels.ampInput]);
    % frame index (track 0)
    r = cadwell_sqlite('query', db, ['SELECT Offset, TimeStamp, JoinDatabase, hex(FrameKey) FROM FrameInfo ' ...
                                     'WHERE Track=0 ORDER BY Offset']);
    n = size(r, 1);
    idx.frames = repmat(struct('number', 0, 'timestamp', '', 'datenum', 0, 'sec', 0, 'joinDb', '', 'keyHex', ''), n, 1);
    for i = 1:n
        idx.frames(i).number = double(r{i, 1}); idx.frames(i).timestamp = char(r{i, 2});
        idx.frames(i).datenum = cadwell_parse_timestamp(char(r{i, 2}));
        idx.frames(i).sec = cadwell_timestamp_sec(char(r{i, 2}));
        idx.frames(i).joinDb = char(r{i, 3}); idx.frames(i).keyHex = upper(char(r{i, 4}));
    end
    % gaps
    idx.gaps = struct('track', {}, 'startOffset', {}, 'endOffset', {}, 'startTime', {}, 'endTime', {});
    try
        r = cadwell_sqlite('query', db, 'SELECT Track, StartOffset, EndOffset, StartTime, EndTime FROM GapInfo ORDER BY StartTime');
        for i = 1:size(r, 1)
            idx.gaps(end+1) = struct('track', double(r{i,1}), 'startOffset', double(r{i,2}), 'endOffset', double(r{i,3}), ...
                                     'startTime', char(r{i,4}), 'endTime', char(r{i,5}));
        end
    catch
    end
    % clock correction
    idx.clockCorrectionSec = 0;
    try
        r = cadwell_sqlite('query', db, 'SELECT PcTime, SyncTime FROM PcTimeSync ORDER BY PcTime LIMIT 1');
        if ~isempty(r)
            idx.clockCorrectionSec = cadwell_timestamp_sec(char(r{1,1})) - cadwell_timestamp_sec(char(r{1,2}));
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

function ch = parse_channel_records(blob)
    tag = uint8([171 121 33 147 222 66 37 162]);
    pos = strfind(char(blob(:)'), char(tag));
    ch = repmat(struct('channel', 0, 'ampInput', 0, 'rate', 0), 1, numel(pos));
    for k = 1:numel(pos)
        p = pos(k) - 1; u = typecast(blob(p + 8 + (1:64)), 'uint32');
        ch(k).channel = double(u(2)); ch(k).ampInput = double(u(5)); ch(k).rate = double(u(11));
    end
end
