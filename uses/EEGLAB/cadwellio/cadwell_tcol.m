function c = cadwell_tcol(t, name)
% cadwell_tcol - one column (cell, nrows x 1) of a table struct returned by
% cadwell_sqlite('table', ...), looked up by column name (case-insensitive).
    k = find(strcmpi(t.columns, name), 1);
    if isempty(k), error('cadwell_tcol:column', 'no column %s (have: %s)', name, strjoin(t.columns, ', ')); end
    c = t.rows(:, k);
end
