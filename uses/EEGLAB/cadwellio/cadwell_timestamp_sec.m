function sec = cadwell_timestamp_sec(s)
% cadwell_timestamp_sec - '2026-06-12T08:29:10.8442395' (UTC) -> seconds since
% 2000-01-01 00:00:00 UTC as a double, keeping the 100-ns resolution of the
% Cadwell time stamps (datenum differences lose microseconds at these dates).
    v = sscanf(s, '%d-%d-%dT%d:%d:%f');
    if numel(v) < 6, error('cadwell_timestamp_sec:format', 'bad time stamp %s', s); end
    days = datenum(v(1), v(2), v(3)) - datenum(2000, 1, 1);
    sec = days * 86400 + v(4) * 3600 + v(5) * 60 + v(6);
end
