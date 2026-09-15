% cadwell_sqlite_info() - list the tables and row counts of a Cadwell .ezdata
%                         (SQLite 3) file, using whichever SQLite access is
%                         available: Database Toolbox sqlite(), mksqlite, or
%                         Python's sqlite3 through the MATLAB-Python interface.
%
% Usage: >> info = cadwell_sqlite_info(filename)
% Output: table with columns Name, Rows (cell/struct on old releases)

function info = cadwell_sqlite_info(filename)
    if ~exist(filename, 'file')
        error('cadwell_sqlite_info:missing', 'File not found: %s', filename);
    end
    fid = fopen(filename, 'r'); magic = fread(fid, 16, 'uint8=>char')'; fclose(fid);
    if ~strncmp(magic, 'SQLite format 3', 15)
        error('cadwell_sqlite_info:notSqlite', '%s is not a SQLite 3 file', filename);
    end
    q = 'SELECT name FROM sqlite_master WHERE type=''table'' ORDER BY name';
    if license('test', 'Database_Toolbox') && exist('sqlite', 'file')
        conn = sqlite(filename, 'readonly');
        names = fetch(conn, q);
        if istable(names), names = names{:, 1}; end
        rows = zeros(numel(names), 1);
        for i = 1:numel(names)
            r = fetch(conn, sprintf('SELECT COUNT(*) FROM "%s"', names{i}));
            if istable(r), r = r{1, 1}; else, r = r{1}; end
            rows(i) = double(r);
        end
        close(conn);
    elseif exist('mksqlite', 'file')
        db = mksqlite('open', filename, 'ro');
        res = mksqlite(db, q);
        names = {res.name}';
        rows = zeros(numel(names), 1);
        for i = 1:numel(names)
            r = mksqlite(db, sprintf('SELECT COUNT(*) AS n FROM "%s"', names{i}));
            rows(i) = double(r.n);
        end
        mksqlite(db, 'close');
    else
        con = py.sqlite3.connect(sprintf('file:%s?mode=ro', filename), pyargs('uri', true));
        res = con.execute(q).fetchall();
        names = cellfun(@(t) char(t{1}), cell(res), 'UniformOutput', false)';
        rows = zeros(numel(names), 1);
        for i = 1:numel(names)
            r = con.execute(sprintf('SELECT COUNT(*) FROM "%s"', names{i})).fetchone();
            rows(i) = double(r{1});
        end
        con.close();
    end
    info = table(names, rows, 'VariableNames', {'Name', 'Rows'});
end
