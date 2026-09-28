function sec = cadwell_timestamp_sec(s)
% cadwell_timestamp_sec - '2026-06-12T08:29:10.8442395' (UTC) -> seconds since
% 2000-01-01 00:00:00 UTC as a double, keeping the 100-ns resolution of the
% Cadwell time stamps (datenum differences lose microseconds at these dates).
% s may be a cell array of stamps; then sec is a column vector.
    v = cadwell_parse_timestamp(s, 'fields');                    % 6 x n: y m d H M S
    days = datenum(v(1, :)', v(2, :)', v(3, :)') - datenum(2000, 1, 1);
    sec = days * 86400 + v(4, :)' * 3600 + v(5, :)' * 60 + v(6, :)';
end
