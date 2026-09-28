function jarfile = cadwell_get_jdbc(version)
% cadwell_get_jdbc - download the xerial sqlite-jdbc driver (Apache-2 licence,
% natives for Windows/macOS/Linux bundled) into this folder's lib/ so that
% cadwell_sqlite can use the 'jdbc' backend. Needs internet access once.
    if nargin < 1, version = '3.46.1.3'; end
    libdir = fullfile(fileparts(mfilename('fullpath')), 'lib');
    if ~exist(libdir, 'dir'), mkdir(libdir); end
    jarfile = fullfile(libdir, sprintf('sqlite-jdbc-%s.jar', version));
    if exist(jarfile, 'file'), fprintf('already present: %s\n', jarfile); return; end
    url = sprintf('https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/%s/sqlite-jdbc-%s.jar', version, version);
    fprintf('downloading %s\n', url);
    if exist('websave', 'file') == 2
        websave(jarfile, url);
    else
        urlwrite(url, jarfile);
    end
end
