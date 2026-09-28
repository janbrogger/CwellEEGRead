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
    r = cadwell_sqlite('query', db, ['SELECT EventType, Text, StartTime, EndTime, StartOffset, EndOffset, Deleted, Priority ' ...
                                     'FROM Events ORDER BY StartTime']);
    for i = 1:size(r, 1)
        s = cadwell_timestamp_sec(char(r{i, 3})); e = cadwell_timestamp_sec(char(r{i, 4}));
        pr = r{i, 8}; if isempty(pr), pr = NaN; end
        ev(end+1) = struct('type', char(r{i, 1}), 'text', char(r{i, 2}), ...
            'onsetSec', s - originSec, 'durationSec', e - s, ...
            'startTicks', double(r{i, 5}), 'endTicks', double(r{i, 6}), ...
            'deleted', logical(double(r{i, 7})), 'priority', double(pr));
    end
end
