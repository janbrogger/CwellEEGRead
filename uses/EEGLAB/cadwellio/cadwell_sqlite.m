function varargout = cadwell_sqlite(op, varargin)
% cadwell_sqlite - read-only SQLite access for Cadwell files with pluggable
% backends, so that no SQLite parsing is hand-rolled in MATLAB/Octave.
%
%   db   = cadwell_sqlite('open', filename)            % auto-detect backend
%   db   = cadwell_sqlite('open', filename, backend)   % force a backend
%   rows = cadwell_sqlite('query', db, sql)            % cell array (nrows x ncols)
%   cadwell_sqlite('close', db)
%   list = cadwell_sqlite('backends')                  % available backends, in order
%
% Backends (first available wins):
%   'mksqlite'  mksqlite MEX (https://github.com/a-ma72/mksqlite), MATLAB
%   'sqlite'    MATLAB Database Toolbox sqlite() or the GNU Octave 'sqlite'
%               package (same call syntax)
%   'jdbc'      xerial sqlite-jdbc jar (Apache-2, natives for all platforms)
%               in this folder's lib/ or already on the Java class path;
%               works in MATLAB and in Octave built with Java
%   'python'    MATLAB's Python interface, py.sqlite3 (MATLAB only)
%
% Cell values: BLOB -> uint8 row vector, TEXT -> char, INTEGER/REAL -> double,
% NULL -> []. Files are opened read-only where the backend allows it.
% Public domain (Unlicense).

    switch lower(op)
        case 'backends'
            varargout{1} = available_backends();
        case 'open'
            filename = varargin{1};
            if ~exist(filename, 'file'), error('cadwell_sqlite:missing', 'file not found: %s', filename); end
            if numel(varargin) >= 2 && ~isempty(varargin{2})
                backend = varargin{2};
            else
                bl = available_backends();
                if isempty(bl)
                    error('cadwell_sqlite:noBackend', ['no SQLite backend available. Install one of: mksqlite (MATLAB), ' ...
                        'the Database Toolbox or Octave sqlite package, the sqlite-jdbc jar in %s, or configure Python in MATLAB.'], ...
                        fullfile(fileparts(mfilename('fullpath')), 'lib'));
                end
                backend = bl{1};
            end
            db = struct('backend', backend, 'file', filename, 'handle', []);
            switch backend
                case 'mksqlite'
                    db.handle = mksqlite('open', filename, 'ro');
                case 'sqlite'
                    db.handle = sqlite(filename, 'readonly');
                case 'jdbc'
                    drv = ensure_jdbc();                                % org.sqlite.JDBC via the dynamic class loader
                    props = javaObject('java.util.Properties');
                    props.setProperty('open_mode', '1');                % 1 = SQLITE_OPEN_READONLY
                    db.handle = drv.connect(['jdbc:sqlite:' strrep(filename, '\', '/')], props);
                    if isempty(db.handle), error('cadwell_sqlite:jdbc', 'sqlite-jdbc could not open %s', filename); end
                case 'python'
                    uri = ['file:' strrep(filename, '\', '/') '?mode=ro&immutable=1'];
                    db.handle = py.sqlite3.connect(uri, pyargs('uri', true));
                otherwise
                    error('cadwell_sqlite:backend', 'unknown backend %s', backend);
            end
            varargout{1} = db;
        case 'query'
            db = varargin{1}; sql = varargin{2};
            varargout{1} = run_query(db, sql);
        case 'close'
            db = varargin{1};
            switch db.backend
                case 'mksqlite', mksqlite(db.handle, 'close');
                case 'sqlite',   close(db.handle);
                case 'jdbc',     db.handle.close();
                case 'python',   db.handle.close();
            end
        otherwise
            error('cadwell_sqlite:op', 'unknown operation %s', op);
    end
end

function bl = available_backends()
    bl = {};
    if exist('mksqlite', 'file') == 3 || exist('mksqlite', 'file') == 2, bl{end+1} = 'mksqlite'; end
    if exist('sqlite', 'file') == 2 || exist('sqlite', 'file') == 3 || exist('sqlite', 'file') == 6, bl{end+1} = 'sqlite'; end
    if jdbc_available(), bl{end+1} = 'jdbc'; end
    if exist('OCTAVE_VERSION', 'builtin') == 0 && exist('pyenv', 'file') == 2
        try
            pe = pyenv();
            if ~isempty(char(pe.Version)), bl{end+1} = 'python'; end
        catch
        end
    end
end

function ok = jdbc_available()
    ok = false;
    try
        if ~usejava('jvm'), return; end
    catch
        return;
    end
    jars = dir(fullfile(fileparts(mfilename('fullpath')), 'lib', 'sqlite-jdbc*.jar'));
    ok = ~isempty(jars);
    if ~ok
        try
            javaObject('org.sqlite.JDBC'); ok = true;
        catch
        end
    end
end

function drv = ensure_jdbc()
    % Class.forName does not see jars added with javaaddpath (dynamic class
    % loader), so the driver is instantiated with javaObject instead.
    try
        drv = javaObject('org.sqlite.JDBC'); return;
    catch
    end
    jars = dir(fullfile(fileparts(mfilename('fullpath')), 'lib', 'sqlite-jdbc*.jar'));
    if isempty(jars)
        error('cadwell_sqlite:jdbc', 'sqlite-jdbc jar not found in %s (run cadwell_get_jdbc)', fullfile(fileparts(mfilename('fullpath')), 'lib'));
    end
    javaaddpath(fullfile(jars(end).folder, jars(end).name));
    drv = javaObject('org.sqlite.JDBC');
end

function rows = run_query(db, sql)
    switch db.backend
        case 'mksqlite'
            res = mksqlite(db.handle, sql);
            if isempty(res), rows = cell(0, 0); return; end
            f = fieldnames(res); rows = cell(numel(res), numel(f));
            for i = 1:numel(res)
                for j = 1:numel(f)
                    rows{i, j} = norm_value(res(i).(f{j}));
                end
            end
        case 'sqlite'
            res = fetch(db.handle, sql);
            if istable(res), res = table2cell(res); end
            rows = cell(size(res));
            for i = 1:numel(res), rows{i} = norm_value(res{i}); end
        case 'jdbc'
            stmt = db.handle.createStatement();
            rs = stmt.executeQuery(sql);
            md = rs.getMetaData(); nc = md.getColumnCount();
            types = zeros(1, nc);
            for j = 1:nc, types(j) = md.getColumnType(j); end        % java.sql.Types
            rows = cell(0, nc); i = 0;
            while rs.next()
                i = i + 1;
                for j = 1:nc
                    t = types(j);
                    if t == 2004 || (t <= -2 && t >= -4)              % BLOB, BINARY, VARBINARY, LONGVARBINARY
                        v = rs.getBytes(j);                            % byte[] -> int8 (MATLAB) or double (Octave)
                        if rs.wasNull(), rows{i, j} = []; else rows{i, j} = typecast(int8(double(v(:)')), 'uint8'); end
                    elseif t == 12 || t == 1 || t == -1 || t == -9 || t == -15 || t == -16 || t == 2005   % char/varchar/longvarchar/clob
                        v = rs.getString(j);
                        if rs.wasNull(), rows{i, j} = []; else rows{i, j} = char(v); end
                    elseif t == 4 || t == -5 || t == 5 || t == -6 || t == -7 || t == 16 || t == 2 || t == 3   % ints, bit, numeric
                        v = rs.getLong(j);
                        if rs.wasNull(), rows{i, j} = []; else rows{i, j} = double(v); end
                    elseif t == 6 || t == 7 || t == 8                  % float, real, double
                        v = rs.getDouble(j);
                        if rs.wasNull(), rows{i, j} = []; else rows{i, j} = double(v); end
                    else                                               % NULL/OTHER (e.g. expressions like hex(x)): decide by the object
                        v = rs.getObject(j);
                        if rs.wasNull() || isempty(v), rows{i, j} = [];
                        elseif ischar(v), rows{i, j} = v;
                        elseif isjava(v) && strcmp(class(v), 'java.lang.String'), rows{i, j} = char(v);
                        elseif isjava(v) && strcmp(class(v), '[B'), rows{i, j} = typecast(int8(double(v(:)')), 'uint8');
                        elseif isnumeric(v) && numel(v) > 1, rows{i, j} = typecast(int8(double(v(:)')), 'uint8');
                        else rows{i, j} = double(v);
                        end
                    end
                end
            end
            rs.close(); stmt.close();
        case 'python'
            cur = db.handle.cursor(); cur.execute(sql); res = cur.fetchall();
            nr = double(py.len(res)); rows = cell(nr, 0);
            for i = 1:nr
                r = res{i}; nc = double(py.len(r));
                for j = 1:nc
                    v = r{j};
                    if isa(v, 'py.bytes'), rows{i, j} = uint8(v);
                    elseif isa(v, 'py.str'), rows{i, j} = char(v);
                    elseif isa(v, 'py.NoneType'), rows{i, j} = [];
                    else rows{i, j} = double(v);
                    end
                end
            end
    end
end

function v = norm_value(v)
    if isa(v, 'int8'), v = typecast(v(:)', 'uint8');
    elseif isa(v, 'uint8'), v = v(:)';
    elseif isstring(v), v = char(v);
    elseif iscell(v) && numel(v) == 1, v = norm_value(v{1});
    elseif isnumeric(v) && ~isa(v, 'uint8'), v = double(v);
    end
end
