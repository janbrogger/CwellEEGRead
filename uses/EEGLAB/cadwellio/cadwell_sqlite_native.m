function out = cadwell_sqlite_native(op, varargin)
% cadwell_sqlite_native - read-only SQLite 3 file reader in plain MATLAB/Octave.
%
%   db    = cadwell_sqlite_native('open', filename)
%   names = cadwell_sqlite_native('tables', db)
%   t     = cadwell_sqlite_native('table', db, name)   % t.columns, t.rows (cell), t.rowids, t.kinds
%
% Implements the parts of the SQLite file format (https://www.sqlite.org/fileformat.html)
% needed to read whole rowid tables: database header, table b-tree interior and
% leaf pages, cell payloads with overflow chains, record headers and serial
% types, INTEGER PRIMARY KEY rowid aliases, and column names parsed from the
% CREATE TABLE text. No SQL, no indexes, no writing. Text encodings UTF-8,
% UTF-16LE (what Cadwell writes) and UTF-16BE are decoded to char.
% The whole file is read into memory (Cadwell files are tens of MB).
% Rows are returned in rowid order. Values: NULL -> [], integers and reals ->
% double, text -> char, blob -> uint8 row vector. t.kinds (uint8, rows x
% columns) keeps the stored storage class: 0 NULL, 1 INTEGER, 2 REAL, 3 TEXT, 4 BLOB.
% Verified byte for byte against Python's sqlite3 on every table of every
% file of the public test exports (cadwell_selftest). Public domain (Unlicense).

    switch lower(op)
        case 'open'
            out = open_db(varargin{1});
        case 'tables'
            out = {varargin{1}.tables.name};
        case 'table'
            out = read_table(varargin{1}, varargin{2});
        otherwise
            error('cadwell_sqlite_native:op', 'unknown operation %s', op);
    end
end

% ------------------------------------------------------------------ open
function db = open_db(file)
    fid = fopen(file, 'rb');
    if fid < 0, error('cadwell_sqlite_native:open', 'cannot open %s', file); end
    bytes = fread(fid, inf, 'uint8=>uint8')'; fclose(fid);
    if numel(bytes) < 100 || ~isequal(bytes(1:16), uint8([double('SQLite format 3') 0]))
        error('cadwell_sqlite_native:magic', '%s is not a SQLite 3 database', file);
    end
    ps = double(bytes(17)) * 256 + double(bytes(18));
    if ps == 1, ps = 65536; end
    db.file = file; db.bytes = bytes; db.pageSize = ps; db.usable = ps - double(bytes(21));
    enc = be32(bytes, 57);                                 % 1 UTF-8, 2 UTF-16LE, 3 UTF-16BE (Cadwell files use 2)
    switch enc
        case {0, 1}, db.charset = 'UTF-8';
        case 2,      db.charset = 'UTF-16LE';
        case 3,      db.charset = 'UTF-16BE';
        otherwise,   error('cadwell_sqlite_native:encoding', 'unknown text encoding %d in %s', enc, file);
    end
    if double(bytes(19)) == 2 && exist([file '-wal'], 'file') == 2
        warning('cadwell_sqlite_native:wal', '%s has a -wal file; changes not yet checkpointed are not read', file);
    end
    m = read_btree(db, 1);                                 % sqlite_master: type, name, tbl_name, rootpage, sql
    db.tables = struct('name', {}, 'rootpage', {}, 'sql', {}, 'columns', {}, 'rowidAlias', {});
    for i = 1:size(m.rows, 1)
        if strcmp(m.rows{i, 1}, 'table')
            [cols, alias] = parse_columns(m.rows{i, 5});
            db.tables(end+1) = struct('name', m.rows{i, 2}, 'rootpage', double(m.rows{i, 4}), 'sql', m.rows{i, 5}, ...
                                      'columns', {cols}, 'rowidAlias', alias);
        end
    end
end

% ------------------------------------------------------------------ table
function t = read_table(db, name)
    k = find(strcmpi({db.tables.name}, name), 1);
    if isempty(k), error('cadwell_sqlite_native:table', 'no table %s in %s', name, db.file); end
    r = read_btree(db, db.tables(k).rootpage);
    cols = db.tables(k).columns; nc = numel(cols); rows = r.rows; kinds = r.kinds;
    if isempty(rows), rows = cell(0, nc); kinds = zeros(0, nc, 'uint8'); end
    if size(rows, 2) < nc
        rows(:, end+1:nc) = {[]}; kinds(:, end+1:nc) = 0;
    elseif size(rows, 2) > nc
        rows = rows(:, 1:nc); kinds = kinds(:, 1:nc);
    end
    a = db.tables(k).rowidAlias;
    if a > 0
        for i = 1:size(rows, 1)
            if isempty(rows{i, a}), rows{i, a} = r.rowids(i); kinds(i, a) = 1; end
        end
    end
    t = struct('columns', {cols}, 'rows', {rows}, 'rowids', r.rowids(:), 'kinds', kinds);
end

% ------------------------------------------------------------------ b-tree walk (depth first, left to right = rowid order)
function r = read_btree(db, root)
    b = db.bytes; ps = db.pageSize; U = db.usable;
    X = U - 35; M = floor((U - 12) * 32 / 255) - 23;
    rows = cell(0, 0); kinds = zeros(0, 0, 'uint8'); rowids = []; nr = 0; stack = root;
    while ~isempty(stack)
        page = stack(end); stack(end) = [];
        off = (page - 1) * ps; hdr = 0; if page == 1, hdr = 100; end
        ptype = double(b(off + hdr + 1));
        ncells = be16(b, off + hdr + 4);
        if ptype == 5                                            % interior table page
            right = be32(b, off + hdr + 9);
            children = zeros(1, ncells);
            for c = 1:ncells
                ptr = be16(b, off + hdr + 13 + 2 * (c - 1));
                children(c) = be32(b, off + ptr + 1);
            end
            stack = [stack, right, fliplr(children)];            % pop order: children left to right, then right-most
        elseif ptype == 13                                       % leaf table page
            q = off + hdr + 9 + 2 * (0:ncells - 1);              % cell pointer array, all at once
            ptrs = double(b(q)) * 256 + double(b(q + 1));
            if nr + ncells > numel(rowids)                       % grow the row store geometrically
                grow = max(ncells, numel(rowids));
                rows(end + grow, 1) = {[]}; kinds(end + grow, 1) = 0; rowids(end + grow) = 0;
            end
            for c = 1:ncells
                i = off + ptrs(c) + 1;
                if b(i) < 128, P = double(b(i)); i = i + 1; else, [P, n] = varint(b, i); i = i + n; end
                if b(i) < 128, rowid = double(b(i)); i = i + 1; else, [rowid, n] = varint(b, i); i = i + n; end
                if P <= X, local = P; else, K = M + mod(P - M, U - 4); if K <= X, local = K; else, local = M; end; end
                payload = b(i:i + local - 1);
                if local < P
                    next = be32(b, i + local); remaining = P - local; chunks = {payload};
                    while remaining > 0 && next > 0
                        poff = (next - 1) * ps; nxt = be32(b, poff + 1);
                        take = min(remaining, U - 4);
                        chunks{end+1} = b(poff + 5:poff + 4 + take); %#ok<AGROW>
                        remaining = remaining - take; next = nxt;
                    end
                    payload = [chunks{:}];
                end
                [vals, kd] = decode_record(payload, db.charset);
                nv = numel(vals); nr = nr + 1;
                if nv > size(rows, 2), rows(:, end+1:nv) = {[]}; kinds(:, end+1:nv) = 0; end
                rows(nr, 1:nv) = vals; kinds(nr, 1:nv) = kd; rowids(nr) = rowid;
            end
        else
            error('cadwell_sqlite_native:page', 'unexpected page type %d on page %d', ptype, page);
        end
    end
    r.rows = rows(1:nr, :); r.rowids = rowids(1:nr); r.kinds = kinds(1:nr, :);
end

% ------------------------------------------------------------------ record format
function [vals, kinds] = decode_record(p, charset)
    if p(1) < 128, H = double(p(1)); pos = 2; else, [H, n] = varint(p, 1); pos = 1 + n; end
    hb = double(p(pos:H));
    if all(hb < 128)                                             % every serial type fits one byte
        types = hb;
    elseif hb(end) < 128 && ~any(conv(double(hb >= 128), ones(1, 8), 'valid') >= 8)
        % multi-byte serial types (text/blob columns over 57 bytes), none 9 bytes long:
        % decode all varints of the header at once
        grp = cumsum([1, hb(1:end - 1) < 128]);                  % varint number of every byte
        ends = find(hb < 128);
        types = accumarray(grp', (bitand(hb, 127) .* 128 .^ (ends(grp) - (1:numel(hb))))')';
    else
        types = zeros(1, 0);
        while pos <= H
            [t, n] = varint(p, pos); types(end+1) = t; pos = pos + n; %#ok<AGROW>
        end
    end
    pos = H + 1; vals = cell(1, numel(types)); kinds = zeros(1, numel(types), 'uint8');
    intLen = [1 2 3 4 6 8];
    for k = 1:numel(types)
        t = types(k);
        switch t
            case 0, vals{k} = []; kinds(k) = 0;
            case 1                                               % one-byte integer, common for flags and small ids
                v = double(p(pos)); if v >= 128, v = v - 256; end
                vals{k} = v; pos = pos + 1; kinds(k) = 1;
            case {2, 3, 4, 5, 6}
                len = intLen(t);
                vals{k} = signed_be(p(pos:pos + len - 1)); pos = pos + len; kinds(k) = 1;
            case 7
                vals{k} = typecast(fliplr(p(pos:pos + 7)), 'double'); pos = pos + 8; kinds(k) = 2;
            case 8, vals{k} = 0; kinds(k) = 1;
            case 9, vals{k} = 1; kinds(k) = 1;
            otherwise
                if t >= 12 && mod(t, 2) == 0
                    len = (t - 12) / 2; vals{k} = p(pos:pos + len - 1); pos = pos + len; kinds(k) = 4;
                elseif t >= 13
                    len = (t - 13) / 2; vals{k} = decode_text(p(pos:pos + len - 1), charset); pos = pos + len; kinds(k) = 3;
                else
                    error('cadwell_sqlite_native:serial', 'unsupported serial type %d', t);
                end
        end
    end
end

function s = decode_text(bytes, charset)
    if isempty(bytes), s = ''; return; end
    switch charset                                               % ASCII-only strings (the usual case) need no conversion
        case 'UTF-8'
            if all(bytes < 128), s = char(bytes); return; end
        case 'UTF-16LE'
            if all(bytes(2:2:end) == 0) && all(bytes(1:2:end) < 128), s = char(bytes(1:2:end)); return; end
        case 'UTF-16BE'
            if all(bytes(1:2:end) == 0) && all(bytes(2:2:end) < 128), s = char(bytes(2:2:end)); return; end
    end
    s = native2unicode(bytes, charset);
    if ~ischar(s), s = char(s); end
    s = reshape(s, 1, []);
end

function v = signed_be(bytes)
    v = 0;
    for k = 1:numel(bytes), v = v * 256 + double(bytes(k)); end
    if v >= 2 ^ (8 * numel(bytes) - 1), v = v - 2 ^ (8 * numel(bytes)); end
end

function [v, n] = varint(b, i)
    if b(i) < 128, v = double(b(i)); n = 1; return; end            % one-byte varint: the common case
    v = uint64(0);
    for k = 1:8
        c = double(b(i + k - 1)); n = k;
        v = bitor(bitshift(v, 7), uint64(bitand(c, 127)));
        if c < 128, v = double(v); return; end
    end
    v = double(bitor(bitshift(v, 8), uint64(double(b(i + 8))))); n = 9;
end

function v = be16(b, i), v = double(b(i)) * 256 + double(b(i + 1)); end
function v = be32(b, i), v = ((double(b(i)) * 256 + double(b(i + 1))) * 256 + double(b(i + 2))) * 256 + double(b(i + 3)); end

% ------------------------------------------------------------------ CREATE TABLE column names
function [cols, alias] = parse_columns(sql)
    cols = {}; alias = 0;
    p1 = find(sql == '(', 1); p2 = find(sql == ')', 1, 'last');
    if isempty(p1) || isempty(p2), return; end
    body = sql(p1 + 1:p2 - 1);
    defs = {}; depth = 0; cur = ''; q = '';
    for ch = body
        if ~isempty(q)
            cur(end+1) = ch; if ch == q, q = ''; end; continue;                 %#ok<AGROW>
        end
        if ch == '[', q = ']'; cur(end+1) = ch; continue; end                     %#ok<AGROW>
        if ch == '"' || ch == '`' || ch == '''', q = ch; cur(end+1) = ch; continue; end %#ok<AGROW>
        if ch == '(', depth = depth + 1; elseif ch == ')', depth = depth - 1; end
        if ch == ',' && depth == 0, defs{end+1} = cur; cur = ''; else, cur(end+1) = ch; end %#ok<AGROW>
    end
    defs{end+1} = cur;
    for k = 1:numel(defs)
        d = strtrim(defs{k}); if isempty(d), continue; end
        up = upper(d);
        if any(strncmp(up, {'CONSTRAINT', 'PRIMARY KEY', 'UNIQUE', 'CHECK', 'FOREIGN'}, [10 11 6 5 7])), continue; end
        if d(1) == '[' || d(1) == '"' || d(1) == '`' || d(1) == ''''
            closer = d(1); if closer == '[', closer = ']'; end
            e = find(d(2:end) == closer, 1) + 1; name = d(2:e - 1); rest = d(e + 1:end);
        else
            tok = regexp(d, '^(\S+)\s*(.*)$', 'tokens', 'once'); name = tok{1}; rest = tok{2};
        end
        cols{end+1} = name; %#ok<AGROW>
        if ~isempty(regexp(upper(rest), '^\s*INTEGER\s.*PRIMARY\s+KEY', 'once')) || ~isempty(regexp(upper(rest), '^\s*INTEGER\s+PRIMARY\s+KEY', 'once'))
            alias = numel(cols);
        end
    end
end
