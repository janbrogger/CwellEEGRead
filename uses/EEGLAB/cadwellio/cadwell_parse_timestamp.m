function dn = cadwell_parse_timestamp(s, mode)
% cadwell_parse_timestamp - '2026-06-12T08:29:10.8442395' (UTC, 7 fractional
% digits) -> MATLAB datenum. Works in MATLAB and Octave without datetime.
% s may be a cell array of stamps (one sscanf for all of them; dn is then a
% column vector). cadwell_parse_timestamp(s, 'fields') returns the 6 x n
% matrix [year; month; day; hour; minute; second] instead.
    if iscell(s), n = numel(s); s = sprintf('%s ', s{:}); else, n = 1; end
    v = sscanf(s, '%d-%d-%dT%d:%d:%f ');
    if numel(v) ~= 6 * n, error('cadwell_parse_timestamp:format', 'bad time stamp in %s', s); end
    v = reshape(v, 6, n);
    if nargin > 1 && strcmp(mode, 'fields'), dn = v; return; end
    dn = datenum(v(1, :)', v(2, :)', v(3, :)', v(4, :)', v(5, :)', v(6, :)');
end
