function ev = cadwell_read_events(eventsFile, originSec, backend)
% cadwell_read_events - read a Cadwell .ezevents file.
%
%   ev = cadwell_read_events(eventsFile, originSec [, backend])
%
% Returns a struct array (in time order) with fields type, text, onsetSec
% (event StartTime relative to originSec, the first stored frame's time in
% seconds from cadwell_timestamp_sec, as the
% vendor's EDF export places annotations), durationSec, startTicks,
% endTicks (100-ns ticks from the record origin), deleted, priority.
% Public domain (Unlicense).

    if nargin < 3, backend = ''; end
    ev = struct('type', {}, 'text', {}, 'onsetSec', {}, 'durationSec', {}, 'startTicks', {}, 'endTicks', {}, 'deleted', {}, 'priority', {});
    if ~exist(eventsFile, 'file'), return; end
    db = cadwell_sqlite('open', eventsFile, backend);
    c = onCleanup(@() cadwell_sqlite('close', db));
    t = cadwell_sqlite('table', db, 'Events');
    [~, o] = sort(cadwell_tcol(t, 'StartTime')); t.rows = t.rows(o, :);
    col = @(name) cadwell_tcol(t, name);
    ty = col('EventType'); tx = col('Text'); st = col('StartTime'); et = col('EndTime');
    so = col('StartOffset'); eo = col('EndOffset'); dl = col('Deleted'); pr = col('Priority');
    for i = 1:size(t.rows, 1)
        s = cadwell_timestamp_sec(char(st{i})); e = cadwell_timestamp_sec(char(et{i}));
        p = pr{i}; if isempty(p), p = NaN; end
        d = dl{i}; if isempty(d), d = 0; end
        ev(end+1) = struct('type', char(ty{i}), 'text', char(tx{i}), ...
            'onsetSec', s - originSec, 'durationSec', e - s, ...
            'startTicks', double(so{i}), 'endTicks', double(eo{i}), ...
            'deleted', logical(double(d)), 'priority', double(p));
    end
end
