function dn = cadwell_parse_timestamp(s)
% cadwell_parse_timestamp - '2026-06-12T08:29:10.8442395' (UTC, 7 fractional
% digits) -> MATLAB datenum. Works in MATLAB and Octave without datetime.
    v = sscanf(s, '%d-%d-%dT%d:%d:%f');
    if numel(v) < 6, error('cadwell_parse_timestamp:format', 'bad time stamp %s', s); end
    dn = datenum(v(1), v(2), v(3), v(4), v(5), v(6));
end
