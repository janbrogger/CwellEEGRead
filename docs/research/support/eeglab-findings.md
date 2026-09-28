> Supporting research note produced 2026-09-28 by an LLM research agent (Claude Code, session `831b87b8-e6bd-4acd-901b-d67180234ee3`, see `llm-logs/`) for `docs/research/eeglab-fieldtrip-cadwell-reader.md`. Claims are tagged [V] verified by reading source, [W] from a web page summary, [I] inferred. Line numbers refer to the commits named in the note.

# EEGLAB import-plugin findings (for the Cadwell `.ezdata` scoping report)

Date: 2026-09-28. Researcher: Claude (subagent). Working copy of sources in
`(session scratchpad, not kept)/`
(nothing under `/home/user/CwellEEGRead` was touched).

Legend for evidence level used throughout:

- **[V]** verified by reading the source file locally (git clone / curl) - line numbers refer to those files.
- **[W]** read via WebFetch (an LLM summary of the page; wording may be paraphrased unless marked verbatim).
- **[I]** inferred / not directly verified.

Local sources cloned (all shallow, `--depth 1`):

| Path (relative to scratchpad/eeglab/) | Upstream | HEAD commit / date |
|---|---|---|
| `eeglab/` | https://github.com/sccn/eeglab (branch `develop`) | `8ac485f6` 2026-09-11 |
| `bva-io/` | https://github.com/sccn/bva-io | `d5fe22f6` 2026-03-30 |
| `neuroscanio/` | https://github.com/sccn/neuroscanio | `5915f10a` 2024-08-05 |
| `xdf-EEGLAB/` | https://github.com/xdf-modules/xdf-EEGLAB (= plugin "xdfimport") | `17009fea` 2025-07-04 |
| `mffmatlabio/` | https://github.com/arnodelorme/mffmatlabio | `fa8dbf19` 2024-05-10 |
| `fileio/` | https://github.com/fieldtrip/fileio (standalone FieldTrip fileio) | `215356f1` 2026-09-24 |
| `ft_*.m` | raw from https://github.com/fieldtrip/fieldtrip/master/fileio/ | fetched 2026-09-28 |
| `wiki/*.md` | raw from https://github.com/sccn/sccn.github.io (source of eeglab.org) | fetched 2026-09-28 |
| `sopen_dzy.m`, `sopen_donnchadh.m` | old GitHub mirrors of BioSig `sopen.m` | see section 4.4 |
| `sopen_cadwell_read.c` | https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4c++/t210/ | see section 4.4 |

Blocked hosts (tried once each): `sccn.ucsd.edu`, `eeglab.org` (EGRESS_BLOCKED by proxy),
`git.ista.ac.at` (403 CONNECT), `api.github.com` (403 for WebFetch; curl gets a proxy error).
`raw.githubusercontent.com`, `github.com` (HTML), `sourceforge.net` work.

---

## 1. The EEGLAB plugin contract

### 1.1 Discovery and the `eegplugin_<name>.m` entry point [V]

`eeglab/eeglab.m` scans `plugins/` at startup (`dir(fullfile(eeglabp, 'plugins'))`). For every
sub-folder it looks for `eegplugin*.m` (line 1050), adds the folder to the path (line 1056), parses
name/version from the folder name (line 1057, `parsepluginname`, defined at line 2243), then calls the
function (lines 1144-1149):

```matlab
vers2 = feval(funcname, gcf, trystrs, catchstrs);
[~, vers2] = parsepluginname(vers2);
```

and warns when the two versions disagree (line 1162, verbatim):

```
WARNING: for plugin "%s" version in the folder name "%s" and in the eegplugin_ file "%s" differ
```

`parsepluginname` (eeglab.m:2243-2262) strips the trailing run of `[0-9._]` characters from the
folder name, so the folder convention is `<name><version>` (e.g. `bva-io1.73`, `MFFMatlabIO5.0`,
`ANTeepimport1.14`, `Fileio250523` - all folder names seen in `eeglab/eeglab.prj` lines 108-147 [V]),
and `_` in the version is turned into `.`. A loose `eegplugin_*.m` directly in `plugins/` is also
accepted (lines 1101-1104). If the call fails EEGLAB prints `EEGLAB: error while adding plugin` and
marks status `'error'` (lines 1150-1156). The plugin list ends up in `global PLUGINLIST`
(eeglab.m:1205).

The wiki (`wiki/design_plugin.md`, source of https://eeglab.org/tutorials/contribute/design_plugin.html,
lines 333-352, verbatim) [V]:

> To create a new EEGLAB extension, simply create a MATLAB function file whose name begins with
> *eegplugin_* and place it in the *plugins* function subdirectory. This function must take three
> arguments ... `>> eegplugin_test (fig, try_strings, catch_strings);` ... The first argument is the
> handle of the main EEGLAB window. The second and third arguments are structures passed by EEGLAB
> that allow the *eegplugin_* function to check parameters, detect errors, etc. ... you can ignore the
> last two parameters (although the *eegplugin_* function *definition* still must list all three
> arguments, or EEGLAB will not be able to call it).

Version string: the wiki example is `vers = 'pca1.00';` (design_plugin.md:461). Real plugins return
either `'<name><version>'` (`'bva_io1.75'`, `'neuroscanio1.8'`, `'xdfimport2.0'`) or a bare version
(`'5.0'` in mffmatlabio) - `parsepluginname` handles both [V].

### 1.2 The `trystrs` / `catchstrs` structures [V]

Defined in `eeglab/eeglab.m` lines 492-556. Verbatim core:

```matlab
e_try             = 'try,';
e_catch           = 'catch, eeglab_error; LASTCOM= ''''; clear EEGTMP ALLEEGTMP STUDYTMP; end;';
check             = ['[EEG LASTCOM] = eeg_checkset(EEG, ''data'');' ret ' eegh(LASTCOM);' e_try];
checkcont         = ['[EEG LASTCOM] = eeg_checkset(EEG, ''contdata'');' ret ' eegh(LASTCOM);' e_try];
...
e_newset   = [e_catch testeegtmp 'eeglab_new;' e_check_study ];
e_store    = [e_catch            'eeglab_new;' ];

trystrs.no_check                 = e_try;
trystrs.check_data               = check;
trystrs.check_ica                = checkica;
trystrs.check_cont               = checkcont;
trystrs.check_epoch              = checkepoch;
trystrs.check_event              = checkevent;
trystrs.check_epoch_ica          = checkepochica;
trystrs.check_chanlocs           = checkplot;
trystrs.check_epoch_chanlocs     = checkepochplot;
trystrs.check_epoch_ica_chanlocs = checkepochicaplot;
trystrs.check_ica_chanlocs       = checkicaplot;
catchstrs.add_to_hist            = e_store;
catchstrs.store_and_hist         = e_store;
catchstrs.new_and_hist           = e_newset;
catchstrs.new_non_empty          = e_newset;
catchstrs.update_study           = e_plot_study;
catchstrs.load_study             = e_load_study;
```

So a menu callback string is literally `'try, [EEG LASTCOM] = pop_x; catch, eeglab_error; ... end; eeglab_new;'`.
`eeglab_new` (via `e_newset`) is what stores the new `EEG` into `ALLEEG`, adds `LASTCOM` to the
history and refreshes the GUI. For an **importer** the correct pair is `trystrs.no_check` +
`catchstrs.new_non_empty` (or `new_and_hist`), which is what every import plugin below uses.

### 1.3 Menu registration [V]

The File > Import data menu is built in eeglab.m:761-762 (verbatim):

```matlab
import_m = eegmenu( false,  file_m,   'Label', 'Import data'                             , 'userdata', onnostudy);
neuro_m  = eegmenu( false,  import_m, 'Label', 'Using EEGLAB functions and plugins'      , 'tag', 'import data' , 'userdata', onnostudy);
```

Plugins therefore do `menu = findobj(fig, 'tag', 'import data')` and `uimenu(menu, ...)`. Other tags:
`'import epoch'`, `'import event'`, `'export'`, `'tools'`, `'plot'`, `'filter'`, `'study'`
(eeglab.m:763-770). The menu label appears under
*File > Import data > Using EEGLAB functions and plugins*.

Menu activation is controlled with `userdata` keywords (wiki design_plugin.md:502-566): `epoch`,
`continuous` (default on), `startup`, `study`, `chanloc` (default off), e.g.
`'userdata', 'startup:on;study:on'`. An importer needs `startup:on` if it should be usable with no
dataset loaded; the built-in import submenu already has `userdata onnostudy` so items under it are
enabled at startup [I, from eeglab.m:761 - `onnostudy` is the "enabled unless a STUDY is loaded" flag].

`finputcheck` is not part of the eegplugin contract; it is the option-parsing helper used inside
`pop_*` functions (e.g. `pop_biosig.m:205-214` uses `g = finputcheck(options, { 'blockrange' 'integer' [0 Inf] []; ... })`) [V].

### 1.4 The `pop_<name>.m` contract and history [V]

Wiki (design_plugin.md, "Associated pop_ functions", section at line 60, summarised via [W] and [V]):
a pop function takes the EEG structure (or nothing for an importer), pops up a GUI when arguments are
missing, and returns `[EEG, com]` where `com` is the string that re-creates the call. From
`eeglab/AGENTS.md` (the repo's own agent guidance, verbatim) [V]:

> **`pop_*` functions** (`functions/popfunc/`): GUI wrappers that show dialogs, call processing
> functions, return `[EEG, LASTCOM]`. Entry points from menus.
> ... Always call `eeg_checkset(EEG)` after modifying the structure to validate and recompute derived fields.

History mechanism `eegh` (`eeglab/functions/adminfunc/eegh.m` header, verbatim):

```
% EEGH - history function.
%   - arg is a string:   with a string argument it pulls the command onto the stack.
%   - arg1 is a string and arg2 is a structure, also add the history to
%     the structure in filed 'history'.
% Global variables used:
%   LASTCOM   - last command
%   ALLCOM    - all the commands
```

The callback strings above call `eegh(LASTCOM)` and `eeglab_new`; the `e_newset`/`storenewcall`
sequence does `EEG = eegh(LASTCOM, EEG); [ALLEEG EEG CURRENTSET LASTCOM] = pop_newset(...)`
(eeglab.m:525). The plugin itself never calls `eegh`; it only returns `com`.

### 1.5 Compact real examples

**bva-io** (`bva-io/eegplugin_bva_io.m`, GPL-2+, 3120 bytes) [V] - core, verbatim:

```matlab
function vers = eegplugin_bva_io(fig, trystrs, catchstrs)
    vers = 'bva_io1.75';
    if nargin < 3
        error('eegplugin_bva_io requires 3 arguments');
    end;
    % add folder to path
    if ~exist('eegplugin_bva_io')
        p = which('eegplugin_bva_io.m');
        p = p(1:findstr(p,'eegplugin_bva_io.m')-1);
        addpath( p );
    end;
    % find import data menu
    menui = findobj(fig, 'tag', 'import data');
    menuo = findobj(fig, 'tag', 'export');
    ...
    comcnt1 = [ trystrs.no_check '[EEG LASTCOM] = pop_loadbv;'  catchstrs.new_non_empty ];
    comcnt3 = [ trystrs.no_check 'LASTCOM = pop_writebva(EEG);'  catchstrs.add_to_hist ];
    uimenu( menui, 'label', 'From Brain Vis. Rec. .vhdr or .ahdr file',  'callback', comcnt1, 'separator', 'on' );
    uimenu( menuo, 'label', 'Write Brain Vis. exchange format file',  'callback', comcnt3, 'separator', 'on' );
```

`bva-io/pop_loadbv.m` [V]: signature line 59 `function [EEG, com] = pop_loadbv(path, hdrfile, srange, chans, metadata)`;
GUI branch lines 63-90 (`uigetfile2({'*.vhdr' '*.ahdr'}, ...)` then `inputgui(uigeom, uilist, 'pophelp(''pop_loadbv'')', ...)`);
`EEG = eeg_emptyset;` (line 91); `EEG.srate = 1000000 / str2double(hdr.commoninfos.samplinginterval);` (96);
`EEG.chanlocs(chan).labels = ...` (121-129); data read directly as `float32` (`fread(IN, [EEG.nbchan, EEG.pnts], [binformat '=>float32'])`, 243);
`EEG.trials = 1; EEG.xmin = 0; EEG.xmax = (EEG.pnts - 1) / EEG.srate;` (359-361); per-channel scaling to the
header unit (369-375); markers via `parsebvmrk` (398); `EEG.urevent = rmfield(EEG.event, 'urevent');` (411);
end: `try EEG = eeg_checkset(EEG); catch end` and

```matlab
if nargout == 2
    com = sprintf('EEG = pop_loadbv(''%s'', ''%s'', %s, %s);', path, hdrfile, mat2str(srange), mat2str(chans));
end
```

**neuroscanio** (`neuroscanio/eegplugin_neuroscanio.m`, GPL-2+ header, LICENSE file GPL-3) [V], verbatim body:

```matlab
function vers = eegplugin_neuroscanio(fig, trystrs, catchstrs)
vers = 'neuroscanio1.8';
if nargin < 3
    error('eegplugin_neuroscanio requires 3 arguments');
end
neuro_m = findobj(fig, 'tag', 'import data');
event_m = findobj(fig, 'tag', 'import event');
epoch_m = findobj(fig, 'tag', 'import epoch');
cb_loadcnt     = [ 'try, [EEG LASTCOM] = pop_loadcnt;'      catchstrs.new_and_hist ];
cb_loadeeg     = [ 'try, [EEG LASTCOM] = pop_loadeeg;'      catchstrs.new_and_hist ];
cb_loaddat     = [ trystrs.check_epoch '[EEG LASTCOM]= pop_loaddat(EEG);'    catchstrs.store_and_hist ];
cb_importev2   = [ trystrs.check_data  '[EEG LASTCOM]= pop_importev2(EEG);'  catchstrs.store_and_hist ];
uimenu( neuro_m, 'Label', 'From Neuroscan .CNT file', 'CallBack', cb_loadcnt,    'Separator', 'on');
uimenu( neuro_m, 'Label', 'From Neuroscan .EEG file', 'CallBack', cb_loadeeg);
uimenu( epoch_m, 'Label', 'From Neuroscan .DAT file', 'CallBack', cb_loaddat);
uimenu( event_m, 'Label', 'From Neuroscan .DAT file', 'CallBack', cb_loaddat2);
uimenu( event_m, 'Label', 'From Neuroscan .ev2 file', 'CallBack', cb_importev2);
```

**xdfimport** (`xdf-EEGLAB/eegplugin_xdfimport.m`, GPL-2; repo LICENSE says BSD-2 [W]) [V]:

```matlab
function vers = eegplugin_xdfimport(fig, trystrs, catchstrs)
    vers = 'xdfimport2.0';
    if nargin < 3, error('eegplugin_xdfimport requires 3 arguments'); end
    if ~exist('load_xdf','file')
        p = which('eegplugin_xdfimport.m');
        p = p(1:findstr(p,'eegplugin_xdfimport.m')-1);
        addpath( p );
        addpath( fullfile(p, 'xdf') );
    end
    menu = findobj(fig, 'tag', 'import data');
    comcnt = [ trystrs.no_check '[EEG LASTCOM] = pop_loadxdf;' catchstrs.new_non_empty ];
    uimenu( menu, 'label', 'From .XDF or .XDFZ file', 'callback', comcnt, 'separator', 'on');
```

`xdf-EEGLAB/pop_loadxdf.m` [V]: `function [EEG, command]=pop_loadxdf(filename, varargin);` (line 63 area),
GUI at `if nargin < 1` -> `uigetfile('*.xdf;*.xdfz', 'Choose an XDF file -- pop_loadxdf()')` (70),
`EEG = eeg_checkset(EEG);` (145), then

```matlab
command = sprintf('EEG = pop_loadxdf(''%s'', %s);',fullFileName, vararg2str(options));  % or without options
```

The actual reader `xdf-EEGLAB/eeg_load_xdf.m` is a clean minimal template of the fields to fill [V] (lines 163-233):

```matlab
raw = eeg_emptyset;
raw.data = stream.time_series;
[raw.nbchan,raw.pnts,raw.trials] = size(raw.data);
raw.srate = ...;                      % effective or nominal rate
raw.xmin = 0;
raw.xmax = (raw.pnts-1)/raw.srate;
raw.event = struct('type', 'sync', 'latency', latencies);   % later replaced by marker-stream events
raw.chanlocs = chanlocs;              % struct array with .labels (and .type)
raw.chaninfo.nosedir = '+Y';
raw.etc.desc = stream.info.desc;
raw.etc.info = rmfield(stream.info,'desc');
```

**mffmatlabio** (`mffmatlabio/eegplugin_mffmatlabio.m`, GPL-3+) [V]: `versionstr = '5.0';`, same
pattern with `comload = [ trystrs.no_check '[EEG, LASTCOM] = pop_mffimport;' catchstrs.new_non_empty ];`
and `uimenu( menui, 'Label', 'Import Magstim/EGI .mff file', 'separator', 'on', 'CallBack', comload);`
(the comment in the file warns "CHANGING THESE MENUS AFFECTS THE MAIN eeglab.m FUNCTION" because
eeglab.m:1211-1215 adds a placeholder menu of the same label that triggers `plugin_askinstall`).

### 1.6 File layout of the examined import plugins [V]

| Plugin | Root files | Extras | License | Tests / CI |
|---|---|---|---|---|
| sccn/bva-io | `eegplugin_bva_io.m`, `pop_loadbv.m`, `pop_loadbva.m`, `pop_writebva.m`, `pop_copybv.m`, `readbvconf.m`, `parsebvmrk.m`, `loadbvef.m`, `README.md`, `backup/` | none | GPL-2+ in file headers, **no LICENSE file** | none |
| sccn/neuroscanio | `eegplugin_neuroscanio.m`, `pop_loadcnt.m`, `pop_loadeeg.m`, `pop_loaddat.m`, `pop_importev2.m`, `loadcnt.m`, `loadeeg.m`, `loaddat.m`, `loadavg.m`, `writecnt.m`, `adjustlocs.m`, `README.md`, `LICENSE` (GPL-3), `data/`, `example_locs/` | `test_response_alignement.m` | GPL | manual test script, no CI |
| xdf-modules/xdf-EEGLAB ("xdfimport") | `eegplugin_xdfimport.m`, `pop_loadxdf.m`, `eeg_load_xdf.m`, `readme.md`, `LICENSE`, `.gitmodules` | `xdf/` = git submodule xdf-modules/xdf-Matlab (`load_xdf.m` + `load_xdf_innerloop.c` + `.mexw64/.mexa64/.mexmaci64/.mexmaca64` [W]); `test/compare_matlab_python.m`, `test/validate_stream_merging.py` | BSD-2 (repo) / GPL-2 (file headers) | test scripts, no CI |
| arnodelorme/mffmatlabio | `eegplugin_mffmatlabio.m`, `pop_mffimport.m`, `pop_mffexport.m`, `mff_import.m`, `mff_export.m`, ~30 `mff_*.m`, `mff_fileio_read_header.m` / `_read_data.m` / `_read_event.m` / `_write.m`, `MFF-1.2.2-jar-with-dependencies.jar` (4.6 MB), `README.md`, `LICENSE.txt` (GPL-3), `mff_import.prj`, `private/` (bundled copies of `eeg_checkset.m`, `eeg_emptyset.m`, ... for standalone use) | `test_mff_files.m`, `test_single_fileio_file.m` | GPL-3+ | manual test scripts, no CI |

There is **no `eegplugin.json`** or any manifest file in any of these plugins or in EEGLAB's loader;
metadata (description, tags, size, rating, download count) lives only in the SCCN server database
(see section 2). The only machine-readable metadata a plugin carries is the folder name and the
`vers` return value [V].

---

## 2. Plugin distribution (plugin manager)

### 2.1 How the manager works [V]

`eeglab/functions/adminfunc/plugin_getweb.m` line 51/53 fetches the list from
`http://sccn.ucsd.edu/eeglab/plugin_uploader/plugin_getcountall_nowiki_json.php?type=<type>&upload=<0|1>`
and parses these record fields: `name` (from `plugin`), `downloads` (from `count`), `version` (from
`curversion`), `zip` (from `link`), `tags` (comma-delimited, e.g. `import`), `numrating`, `rating`,
`critical`, `removed`, `size`, plus a `webrating` URL
`https://sccn.ucsd.edu/eeglab/plugin_uploader/simplestar.php?plugin=<name>&version=<version>` [W+V].
`plugin_menu.m` lines 128-137 offer filters `Filter by import|export|artifact|ica|preprocessing|erp|source|study|time-freq|other`
and show `Tags:`, `Status:`, `Description of the plugin:` and an `Install/Update` button [V].

`plugin_install.m` [W]: downloads `zip`, unzips into `fullfile(<eeglab>/plugins, [name version])`,
then pings `plugin_increment.php?plugin=<name>&version=<version>`; it does **not** validate that an
`eegplugin_*.m` exists. `plugin_askinstall(pluginName, pluginFunc, force)` (full text read [W]) is the
programmatic installer used by core code, e.g. `plugin_askinstall('Fileio', 'ft_read_data')`.

Consequence: the zip must unpack so that `eegplugin_<x>.m` is at the top of `plugins/<name><version>/`
(or one level deeper - eeglab.m only searches the immediate sub-folder, line 1050) and the folder
name the server assigns is `<name><version>`.

### 2.2 The documented submission procedure

Wiki `wiki/EEGLAB_Extensions.md` lines 70-86 and `wiki/design_plugin.md` lines 574-580 still say
(verbatim) [V]:

> To contribute a new plugin ... See the simple instructions under How to contribute to EEGLAB to create
> EEGLAB compatible code. Then, you may add your extension to the list above so that EEGLAB users can
> download it automatically from within EEGLAB. To do this, use [this form](http://sccn.ucsd.edu/eeglab/plugin_uploader/upload_form.php).
> If you want to upload a new version of your plugin, you can use [this simplified form](http://sccn.ucsd.edu/eeglab/plugin_uploader/version_update.php).

**However the web form has been closed.** The current procedure is the GitHub issue template
`eeglab/.github/ISSUE_TEMPLATE/new-plugin-or-plugin-update.md` (verbatim, full file) [V]:

```
---
name: New plugin or plugin update
about: Submit or update an EEGLAB plugin. Provide plugin name, version information,
  and attach the ZIP file. The previous submission system was closed for security
  reasons.
---
## Plugin submission
Please provide the following information:
**Plugin name:**
**Current version:**
**New or revised version:**
**Description of the update:**
(Briefly describe changes, fixes, or additions)
---
### Upload instructions
Drag and drop the ZIP file of your plugin directly into this issue.
---
**Note:** The previous submission page has been closed due to security concerns.
```

WebSearch snippet of the (blocked) upload_form.php page confirms it now redirects to this ("create an
issue on the EEGLAB GitHub repository and attach your plugin by dragging and dropping the ZIP file") [W].
Recent real submissions in https://github.com/sccn/eeglab/issues (Sep 2026) [W]: #970 "New plugin to
Load and analyze multimodal data ... from the Galea headset" (body gives plugin name, version v1.7.1
and a GitHub **release zip URL** `.../releases/download/v1.7.1/galea1.7.1.zip`), #965 "Plugin update:
ERPLAB 13.10", #964 "Plugin Update: CountSheepPSG", #954 "New plugin: LEEGibilityAtlas 1.0.0" (body
adds License BSD-3-Clause, source repo, DOI, zip filename `LEEGibilityAtlas1.0.0.zip`, SHA-256).
So in practice: name, version, description, a zip (attached or linked from a GitHub release whose
zip is named `<name><version>.zip`), optionally license/tags; an SCCN admin then enters it into the
server DB (the wiki's "Administrators ... Pending plugin requests / Edit plugin information" pages).
There is no automated GitHub-based publishing; the manager always downloads a zip from the URL stored
server-side [V for mechanism, I for the admin step].

Required metadata beyond name/version/description/zip: none is enforced by code. Tags (import/export/...)
and description are set server-side. No MATLAB-version field exists in the parsed JSON [V]. The wiki
`Compiled_EEGLAB.md` shows how core devs install the bundled set
(`plugin_askinstall('Fileio', 'ft_read_data', true);` etc., lines 217-234) [V].

### 2.3 Licensing expectations [V]

- EEGLAB core: `eeglab/LICENSE` is **BSD 2-Clause**, first lines verbatim: "This is the license for
  the core for the eeglab.m function and the source code in the "functions" folder. EEGLAB plugins
  (in the "plugins" folder) may be released under different licenses." (The README.md still says
  "all released under the Gnu public license (see eeglablicence.txt)" - stale text.)
- Wiki `Contributing_to_EEGLAB.md` lines 82-92 (verbatim): "EEGLAB is distributed under the BSD
  license. Any contributed functions we add to EEGLAB will be made available for free commercial and
  non-commercial use under this license. ... Consider writing an *extension* or *plugin* ... The
  authors also retain all commercial rights to the functions they write."
- Plugins in the manager use GPL-2+ (bva-io, xdfimport headers), GPL-3 (neuroscanio, mffmatlabio,
  FieldTrip/Fileio), BSD-2 (xdf-EEGLAB repo), BSD-3 (LEEGibilityAtlas submission). No license
  restriction is stated anywhere for plugins; the compiled EEGLAB page notes some bundled plugins are
  not commercial-use compatible (Compiled_EEGLAB.md:159-160). **An Unlicense/public-domain plugin is
  therefore acceptable** by the documented policy [I - no explicit statement either way; nothing found
  that would forbid it, and the plugin list is not license-filtered].

---

## 3. EEG structure fields an importer must fill

### 3.1 Authoritative field list [V]

`eeglab/functions/popfunc/eeg_emptyset.m` (complete, verbatim, comments removed):

```matlab
EEG.setname = ''; EEG.filename = ''; EEG.filepath = ''; EEG.subject = ''; EEG.group = '';
EEG.condition = ''; EEG.session = []; EEG.comments = '';
EEG.nbchan = 0; EEG.trials = 0; EEG.pnts = 0; EEG.srate = 1; EEG.xmin = 0; EEG.xmax = 0;
EEG.times = []; EEG.data = [];
EEG.icaact = []; EEG.icawinv = []; EEG.icasphere = []; EEG.icaweights = []; EEG.icachansind = [];
EEG.chanlocs = []; EEG.urchanlocs = []; EEG.chaninfo = []; EEG.ref = [];
EEG.event = []; EEG.urevent = []; EEG.eventdescription = {}; EEG.epoch = []; EEG.epochdescription = {};
EEG.reject = []; EEG.stats = []; EEG.specdata = []; EEG.specicaact = [];
EEG.splinefile = ''; EEG.icasplinefile = ''; EEG.dipfit = []; EEG.history = ''; EEG.saved = 'no'; EEG.etc = [];
```

`eeglab/functions/adminfunc/eeg_checkset.m` header (lines 44-90) documents them; key lines verbatim:

```
%   EEG.trials       - number of epochs (or trials) in the dataset. If data are continuous, this number is 1.
%   EEG.pnts         - number of time points (or data frames) per trial (epoch). If data are continuous (trials=1), the total number of time points
%   EEG.nbchan       - number of channels
%   EEG.srate        - data sampling rate (in Hz)
%   EEG.xmin         - epoch start latency|time (in sec. relative to the time-locking event at time 0)
%   EEG.xmax         - epoch end latency|time (in seconds)
%   EEG.times        - vector of latencies|times in milliseconds (one per time point)
%   EEG.ref          - ['common'|'averef'|integer] reference channel type or number
%   EEG.etc          - miscellaneous (technical or temporary) dataset information
%   EEG.saved        - ['yes'|'no'] 'no' flags need to save dataset changes before exit
%   EEG.data         - two-dimensional continuous data array (chans, frames) ELSE, three-dim. epoched data array (chans, frames, epochs)
%   EEG.chanlocs     - structure array containing names and locations
%   EEG.chaninfo     - structure containing additional channel info
%   EEG.event        - event structure containing times and nature of experimental events ...
%   EEG.urevent      - original (ur) event structure containing all experimental events recorded ... (before data rejection)
%   EEG.subject / EEG.group / EEG.condition / EEG.run / EEG.session - studyset codes
```

What `eeg_checkset(EEG)` fixes up automatically [V]: `EEG.nbchan = size(EEG.data,1)` (797);
`EEG.pnts`/`EEG.trials` from data size (804-833); `if EEG.trials == 1 && EEG.xmin ~= 0, EEG.xmin = 0` (841);
`EEG.xmax = (EEG.pnts-1)/EEG.srate+EEG.xmin` (854); `EEG.times = linspace(EEG.xmin*1000, EEG.xmax*1000, EEG.pnts)` (1249);
defaults `EEG.saved='no'`, `EEG.subject=''`, `EEG.urevent=[]`, `EEG.ref='common'` (1256-1270);
`EEG.etc.eeglabvers` stamp; `if isa(EEG.data,'double') && option_single, EEG.data = single(EEG.data)` (777-779,
`option_single = 1` by default in `eeg_optionsbackup.m:13`). So: an importer should fill `data`
(double or single; single is the in-memory norm), `srate`, `nbchan`, `pnts`, `trials=1`, `xmin=0`,
`chanlocs(i).labels`, `event`, `setname`, `comments`, optionally `filename/filepath`, `ref`, `subject`,
`etc.*`, and then call `eeg_checkset(EEG)` (plus `'eventconsistency'` and/or `'makeur'` if events
were added). Minimal working example is `eeg_load_xdf.m` quoted in 1.5.

`eeg_checkset` keyword options (header lines 12-36, verbatim excerpt): `'makeur' - remake the
EEG.urevent structure`, `'checkur'`, `'eventconsistency' - check whether EEG.event information are
consistent; rebuild event* subfields of the 'EEG.epoch' structure`, `'chanlocs_homogeneous'`,
`'loaddata'`, `'contdata'`, `'epoch'`, `'event'` [V]. Note pop_fileio calls
`eeg_checkset(EEG, 'eventconsistency')` then `eeg_checkset(EEG,'makeur')` (pop_fileio.m:409-420) [V].

### 3.2 Channel labels, types, positions [V]

`readlocs.m` header lists chanlocs fields: `labels` (no spaces), `theta`, `radius`, `X`, `Y`, `Z`,
`sph_theta`, `sph_phi`, `sph_radius`, `type` ("channel type: 'EEG', 'MEG', 'EMG', 'ECG', others"),
`urchan`, `ref`; `eeg_checkset` syncs `EEG.ref` with `EEG.chanlocs(1).ref` (1105-1110). 10-20 positions:
`pop_chanedit(EEG, 'lookup', <file>)` (help line 110: "look-up channel numbers for standard locations
in the channel location file given as input"; example line 130 `EEG = pop_chanedit(EEG, 'lookup','Standard-10-5-Cap385.sfp');`).
The lookup GUI defaults to the dipfit BEM template when dipfit is installed (lines 899-911,
`defaulttemplate = min(2, length(chantemplate)); % BEM model when DIPFIT is available`); aliases
`standard-10-5-cap385.elp`, `standard_1005.elc`, `standard_1005.ced` are remapped to
`template_models(1|2).chanfile` (984-997). Files exist at `plugins/dipfit/standard_BEM/elec/standard_1005.elc`
(also `standard_1020.elc`, `standard_1005.ced`, ...) and `plugins/dipfit/standard_BESA/standard-10-5-cap385.elp`
(eeglab.prj:139,143; dipfit tree [W]). EEGLAB also ships `sample_locs/Standard-10-20-Cap19.ced|.locs`,
`Standard-10-20-Cap25`, `Standard-10-10-Cap33/47`, `Standard-10-20-Cap81` [V]. Lookup is by exact label
match, so labels like `Fp1`, `F7`, `T3` (old names T3/T4/T5/T6 are present in standard_1005 as well
[I]) will resolve. Positions are not needed for import itself; an importer can either leave chanlocs
as labels-only (bva-io, xdfimport, fileio do that) or call `pop_chanedit(EEG,'lookup',...)` itself.

Units: EEGLAB has no unit field on the dataset, but everything (filters, scales, `pop_reref`,
topoplots, `eegplot` default 'spacing') assumes microvolts. `pop_fileio.m:185-194` explicitly forces
FieldTrip EEG channels to `uV` ("Forcing EEG channel units to 'uV'"); pop_loadbv scales by the
header's per-channel `scale` (359-375); `EEG.chaninfo.unit` exists only as a FieldTrip pass-through
(pop_fileio.m:311). So: **convert to microvolts before filling `EEG.data`** [V for the behaviour, I
for "assumes"].

### 3.3 Events, boundaries, gaps [V]

Event fields: `EEG.event(i).type` (string or number - keep types homogeneous), `.latency` in
**samples, 1-based, may be fractional** (eeg_insertbound.m header: "a latency of 2000.3 means 0.3
samples ... after the 2001st data frame (since first frame has latency 0)"), `.duration` (samples),
`.urevent` (index into `EEG.urevent`, created by `eeg_checkset(EEG,'makeur')`), `.epoch` for epoched
data. `eeg_checkset` forces numeric event fields to double (537-560) and removes events with
`latency < 0.5` or `> pnts*trials+1` (429-432).

Discontinuities: represented by an event whose type is `'boundary'` (or numeric `-99` when
`option_boundary99` is on and event types are numeric; `eeg_boundarytype.m`, `eeg_isboundary.m`).
`eeg_insertbound.m` (functions/popfunc) lines 115-117 verbatim show the canonical construction:

```matlab
eventin(end+1).type   = eeg_boundarytype(eventin);
eventin(end).latency  = regions(iRegion,1)-sum(lengths(1:iRegion-1))-0.5;
eventin(end).duration = lengths(iRegion,1)+addlength;
```

i.e. the boundary sits at a half-sample position between the last sample before the gap and the
first sample after it, and `duration` = number of samples removed (0 or `NaN` when unknown; bva-io sets
`EEG.event(boundaries(index)).duration = NaN` for 'New Segment' markers, pop_loadbv.m:437-439).
`eeg_checkset` merges duplicate boundaries (adding durations) and drops a boundary beyond the data end
(521-545). **Recommended representation for a recording gap**: concatenate the data without padding
and insert `type='boundary'`, `latency=<samples before gap>+0.5`, `duration=<missing samples>`;
`urevent` latencies then stay in "original" coordinates. Zero padding is *not* what EEGLAB does
anywhere (`eeg_eegrej`, `pop_mergeset`, FieldTrip import all use boundaries); zero-padding would
break filtering/ICA and misrepresent the record [V for EEGLAB conventions; I for the recommendation].

What EEGLAB's own EDF importers do:

- `pop_biosig.m` -> `biosig2eeglab.m` -> `biosig2eeglabevent.m` (functions/sigprocfunc) [V]:
  `event(index).latency = EVENT.POS(index)`; `.duration = EVENT.DUR(index)`; type is `EVENT.TYP` and,
  with `importannot`/`importEDFplus` on and `eType > 255`, the text from `eventcodes.txt`
  (`EVT.EVENT.CodeDesc`), with **EDF+ codes 32766/32767 mapped to boundary events**
  (lines 77-80: `if eType == 32766 || eType == 32767, event(index).edfplustype = event(index).type; event(index).type = eeg_boundarytype(event);`).
  pop_biosig additionally appends `dat.EDFplus.*` annotation vectors as extra data channels
  (pop_biosig.m:257-268) and calls `eeg_checkset(EEG,'eventconsistency')` (297). BioSig does not
  itself split discontinuous EDF+ records; discontinuities only appear if the file carries the
  32766/32767 codes [I].
- `pop_fileio.m` (functions/popfunc) [V]: `EEG.event(index).type = event(index).value;
  .value = event(index).type; .latency = event(index).sample+offset+subsample; .duration = event(index).duration`
  (395-407), then removes `sample/value/offset`. **No boundary handling at all** ("No boundary
  event handling present" - verified, grep shows none). For EDF+, FieldTrip's `ft_read_event.m`
  case `'edf'` (lines 743-783) parses the TAL annotation channel (`read_edf` + `tokenize(char(evt), char(0))`)
  into events with `value` = annotation text; discontinuous EDF+D is not turned into boundaries [I].
- `readedf.m` (functions/sigprocfunc) is the legacy plain-EDF reader (no annotations) [V, not read in detail].

### 3.4 Recording start date/time - is there a standard field? [V]

There is **no standard field** in `eeg_emptyset`/`eeg_checkset`. Conventions found:

- `biosig2eeglab.m:109-111`: `if isfield(dat,'T0'), EEG.etc.T0 = dat.T0; % added sjo end` where
  BioSig `T0` is `[YYYY MM DD hh mm ss.ccc]` (see `writeeeg.m:43` `'T0' - recording time [YYYY MM DD hh mm ss.ccc]`).
  `writeeeg.m` (EEGLAB's EDF/BDF/GDF writer) uses `HDR.T0` and defaults to `clock` (line 136).
- `mffmatlabio/mff_import.m` ~line 100: `EEG.etc.recordingtime = info.recordtimematlab; EEG.etc.timezone = info.timezone;` [W].
- `pop_fileio.m:343`: `EEG.etc.fileio_dat = dat;` (whole FieldTrip header incl. `hdr.orig`).
- `pop_loadbv.m`, `eeg_load_xdf.m`: nothing.
- grep of `functions/` and `plugins/` for `recordingtime|etc.T0|etc.starttime` finds only the two
  lines above [V]. EEG-BIDS export does not read any of them [W].
- The CountingSheepPSG plugin puts the start time as an event of type `'yyyy-MM-dd HH:mm:ss.SSS'` [W, search snippet].

Recommendation: populate `EEG.etc.T0 = [Y M D h m s.fff]` (the BioSig/writeeeg convention, the only
one consumed by core code) plus a human-readable `EEG.etc.recordingtime`/ISO string in `EEG.comments`
[I].

---

## 4. The File-IO path (FieldTrip) and BioSig

### 4.1 Where pop_fileio lives and what it calls [V]

`pop_fileio.m` is **core EEGLAB** (`eeglab/functions/popfunc/pop_fileio.m`, BSD-2), not part of the
plugin. Header verbatim (lines 1-27 excerpt):

```
% POP_FILEIO - import data files into EEGLAB using FileIO
%   >> OUTEEG = pop_fileio; % pop up window
%   >> OUTEEG = pop_fileio( filename );
%   >> OUTEEG = pop_fileio( header, dat, evt );
%   'dataformat' - [string] data format. Default is automatic. Available choices are available in ft_read_data
% Note: FILEIO toolbox must be installed.
```

Flow: `if ~plugin_askinstall('Fileio', 'ft_read_data'), return; end` (64) ->
`dat = ft_read_header(filename);` (105 GUI path, 152 scripted path - **no `headerformat` option is
passed, so header detection is purely `ft_filetype`**) -> `dataopts` gets `'dataformat', g.dataformat`
only if not `'auto'` (199) -> `alldata = ft_read_data(filename, 'header', dat, dataopts{:});` (203) ->
`event = ft_read_event(filename, dataopts{:});` (382). The GUI popup lists ~100 hard-coded format
names (`formats = { 'auto' '4d' ... 'edf' ... 'neuroscope_bin' }`, lines 91-100). Fields filled:
`EEG.srate = dat.Fs; EEG.nbchan = dat.nChans; EEG.data = alldata; EEG.setname = ''; EEG.comments = ['Original file: ' filename]; EEG.xmin = -dat.nSamplesPre/EEG.srate; EEG.trials = dat.nTrials;`
(240-246), `EEG.chanlocs = struct('labels', dat.label)` + `.type` from `dat.chantype`, `X/Y/Z` from
`dat.elec.chanpos` when present (258-345), `EEG.etc.fileio_dat = dat` (343).

### 4.2 The "Fileio" plugin: what it is, how it is updated [V/I]

The plugin named `Fileio` in the manager is a dated snapshot of FieldTrip's `fileio` module. Evidence:
`eeglab/eeglab.prj` (the MATLAB Compiler project for the compiled EEGLAB) lists
`${PROJECT_ROOT}/plugins/Fileio250523` and `${PROJECT_ROOT}/plugins/Fieldtrip-lite250523` (lines 123-130),
i.e. snapshots dated 2025-05-23, plus `Fieldtrip-lite250523/external/biosig` [V]. eeglab.m has special
path handling for folders containing `fieldtrip` (adds `compat`, `forward`, `utilities`, `plotting`
and removes `external/*`) and sets `pluginVersion = 'ersion unknowned'` for `fieldtrip`/`fileio`
folders lacking a numeric version (lines 1059-1091, 1116-1121) [V]. The wiki lists
"**FileIO** (https://github.com/fieldtrip/fileio): Toolbox allowing data import in multiple data
formats" (EEGLAB_Extensions.md:136) [V]. The standalone https://github.com/fieldtrip/fileio repo
contains exactly the `fileio` module (`ft_read_header.m`, `ft_read_data.m`, `ft_read_event.m`,
`ft_filetype.m`, `private/`, GPL-3 `COPYING`), and its commit log is a stream of "synchronized with
main FieldTrip repository" commits (last ten: 2026-06-24 .. 2026-09-24) [V + W]. Who re-packages it
for the EEGLAB manager is not documented; the naming `Fileio<yymmdd>` and the compile script in
`Compiled_EEGLAB.md` ("Do not use the GIT version of FieldTrip ... Instead get the latest plugin",
lines 210-219) indicate SCCN (Arnaud Delorme) uploads a fresh snapshot around each EEGLAB release
[I]. Lag: the snapshot in the 2025 compiled release is 2025-05-23; releases are roughly annual
(revision history: 2025.1.0, 2025.0.0, 2024.x ...), so the lag from a FieldTrip merge to EEGLAB
users who rely on the manager is **months to about a year**, unless the user installs FieldTrip
itself (eeglab.m accepts any folder whose name contains `fieldtrip`) [I].

### 4.3 Would a FieldTrip-side Cadwell reader appear in EEGLAB automatically? [V]

Only if `ft_filetype` recognises the file, because pop_fileio calls `ft_read_header(filename)` with
no `headerformat`. `ft_read_header.m` line 17 documents the alternative:
`'headerformat' = name of a MATLAB function that takes the filename as input (default is automatic)`
and line 44: "To use an external reading function, you can specify an external function as the
'headerformat' option ... search for BIDS_TSV as example"; `ft_read_data` (line 34) and
`ft_read_event` accept `dataformat`/`eventformat` function names likewise. mffmatlabio uses exactly
this hook (`mff_fileio_read_header.m`, `mff_fileio_read_data.m`, `mff_fileio_read_event.m`) so that
FieldTrip users can call `ft_read_header(file, 'headerformat', 'mff_fileio_read_header')` [V]. But
pop_fileio only forwards `'dataformat'` to `ft_read_data`/`ft_read_event`, never `headerformat`, so
the GUI path needs `ft_filetype` support. `ft_filetype.m` (master, 2026-09-28) has **no** `cadwell`,
`ezdata` or `sqlite` detection (grep: only `.easy` -> `neuroelectrics_easy`, line 1290) [V]. Adding
Cadwell support therefore means a FieldTrip PR touching `ft_filetype.m` (extension `.ezdata` /
`.ezdataindex` / directory detection), `ft_read_header.m`, `ft_read_data.m`, `ft_read_event.m` and a
`private/read_cadwell_*.m`; a MATLAB SQLite dependency (`sqlite()` needs the Database Toolbox in
R2022a+, or the `mksqlite` MEX) would be a first for fileio [I]. Also note ft_read_header's
`'fallback' = 'biosig'` option (line 12) [V].

### 4.4 BioSig and Cadwell [V]

`pop_biosig.m` -> `sopen`/`sread` from the `Biosig` plugin (eeglab.m:1095-1099 adds
`<Biosig>/biosig/t200_FileAccess` to the path). The MATLAB `sopen.m` (two GitHub mirrors, 494-506 kB:
`sopen_donnchadh.m`, `sopen_dzy.m`) contains **no** `cadwell`/`ezdata`/`EASY` string at all [V; these
mirrors are older snapshots, the current GitLab source at git.ista.ac.at was blocked]. The C library
biosig4c++ has `t210/sopen_cadwell_read.c` (Copyright 2021 Alois Schloegl, GPL-3), header comment
"read CADWELL file formats (EAS, EZ3, ARC)"; all three branches end in
`biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format EAS(Cadwell): unsupported ")` / `EZ3` / `ARC`
(lines 92, 287, 291) - it is a reverse-engineering stub, not a working reader; there is also a sibling
`sopen_sqlite.c` [V]. SourceForge feature request #13 "Support for AES, EZ3, and ARC fiile formats"
(opened 2021-08-27 by Schloegl, still open; comment 2021-09-30: "sopen_cadwell.c and
sopen_sqlite.c are used to develop tools for reverse engineering") [W]. Nothing about `.ezdata`
(the 2020+ SQLite format) anywhere in BioSig. So BioSig's `mexSLOAD`/`sopen` cannot read Cadwell
today, and `ft_read_header(..., 'fallback','biosig')` would not help.

---

## 5. MATLAB / Octave compatibility

- Stated minimum MATLAB: wiki `Contributing_to_EEGLAB.md:69` "MATLAB version 2008b or later is
  required; We recommend using the latest version of MATLAB." `eeglab.m:204-220` refuses `vers < 7`
  and warns for `< 7.06` ("older than 7.6 (2008a) ... Some of the EEGLAB functions might not be
  functional"); it also special-cases `str2double(ver(1:2)) > 24` (MATLAB Copilot buttons) [V]. No
  separate minimum is stated for plugins; mffmatlabio's README states its own ("will not work with
  version of Matlab older than 2014a as the Java JAR file cannot be properly interfaced") [V].
- Octave: `wiki/Running_EEGLAB_on_Octave.md` (full text read) [V]: "As of 2021, we are supporting the
  Octave MATLAB-compatible open-source environment (both command line calls and graphic interface)";
  "EEGLAB on Octave is not as stable ... first choice MATLAB, second the compiled version, third
  Octave"; "best tested using Octave 6.1 on Windows"; "**Plug-ins need to be installed manually**
  (downloaded as zip files and uncompressed in the EEGLAB plugins folder). Most plugins (including
  SIFT and LIMO) have not been tested on Octave and will likely not be functional"; ICLabel ran on
  Octave 8.4 but "15+ hours ... compared to 10 seconds on MATLAB". eeglab.m disables
  `Octave:abbreviated-property-match` and `pkg load statistics` when `~ismatlab`; the plugin-install
  menus are only added `if ismatlab && ~nouiflag` (eeglab.m:1210) [V]. The CI (see section 6) runs an
  Octave smoke test on every push. bva-io contains an explicit "Octave compatible code below"
  fallback for `strread` (pop_loadbv.m:122) [V]. Revision history: "Improved Octave 8.4
  compatibility" (2024.x), "Full Octave compatibility from the command line" (2019) [V].
- MEX / Java in the manager: no guidance on the wiki (design_plugin.md, EEGLAB_Extensions.md and
  Contributing_to_EEGLAB.md contain no "mex"/"Java" text) [V]. Practice: **ANTeepimport1.14** ships
  `eepv4_read.mexa64 / .mexmaci64 / .mexw32 / .mexw64` (+ `_info`, `_version`) side by side in the
  plugin root (eeglab.prj:109-120) [V]; **xdfimport** ships `load_xdf_innerloop.c` plus
  `.mexw64/.mexa64/.mexmaci64/.mexmaca64` in the `xdf/` sub-folder and readme "version 1.19 includes
  MATLAB binaries" [V+W]; **mffmatlabio** ships a 4.6 MB jar and does `javaaddpath(fullfile(p,
  'MFF-1.2.2-jar-with-dependencies.jar'))` in `mff_path.m` [V]; **Biosig** plugin bundles the
  `mexSLOAD` binaries (pop_biosig `'importmex'` option) [V]. The manager just unzips, so binaries for
  all platforms must be pre-built and committed; no build step runs at install. The compiled EEGLAB
  cannot add plugins at all (Compiled_EEGLAB.md:132-134) [V]. For a Cadwell reader the practical
  choices are: pure-MATLAB SQLite (none exists in base MATLAB; `sqlite()` is Database Toolbox
  R2022a+), a bundled `mksqlite` MEX for 4 platforms, or Java `sqlite-jdbc` via `javaaddpath` (works
  in MATLAB, not Octave) [I].

---

## 6. Testing conventions

- **Core repo CI** `eeglab/.github/workflows/test.yml` (full text read) [V]: on push/PR to
  `master`/`develop`: job `octave-smoke` (ubuntu, `apt-get install octave`, runs
  `eeglab('nogui'); EEG = pop_loadset(...'eeglab_data.set'...); EEG = eeg_checkset(EEG); assert(EEG.nbchan == size(EEG.data,1)); assert(EEG.pnts == size(EEG.data,2));`)
  and `matlab-smoke` (`matlab-actions/setup-matlab@v2` release R2024b, same commands, skipped when
  `MATLAB_BATCH_TOKEN` secret is absent). Also `claude.yml` / `claude-code-review.yml` (Claude Code
  bot on `@claude` mentions by owners/members) [V]. The repo has **no `test/` directory** [V].
- **Test-case repos** [W]: https://github.com/sccn/eeglab_tests (README verbatim: "tests to validate
  correct behavior of EEGLAB. This repository uses ... MATLAB Projects, MATLAB Unit Testing, Git LFS,
  Git submodules and GitHub Actions"; `unittesting_*` folders incl. `unittesting_binary` for file
  readers; `*wrapperTest.m` wrap legacy function tests; `.github/workflows/ci.yml` uses
  `matlab-actions/setup-matlab@v2` with matrix `release: [R2021b,R2025a]`, `matlab-actions/run-tests@v2`,
  codecov, dorny/test-reporter [V from raw ci.yml]) and the older https://github.com/sccn/eeglab-testcases
  (git-annex, `runtest.m`). Wiki `EEGLAB_test_cases.md`: "~5,000 test cases cover about 10% of all
  possible function call variations"; `unittesting_binary` "contains test cases for reading binary
  data files in several formats ... anonymized binary test data files (500 MB)" [V].
- **Plugins**: none of bva-io, neuroscanio, xdf-EEGLAB, mffmatlabio, firfilt, clean_rawdata,
  ICLabel, EEG-BIDS has a `.github/workflows` directory (the last three return 404 for that path)
  [V/W]. Convention is a hand-run `test_*.m` script in the repo root (`test_mff_files.m`,
  `test_response_alignement.m`, `test/compare_matlab_python.m`) [V]. `CONTRIBUTING.md` asks core PRs
  to "provide test scripts", "run existing test cases", and "add the test case to the EEGLAB test
  case repository" (Contributing_to_EEGLAB.md:191-192) [V].

---

## 7. Implications for a Cadwell `.ezdata` importer (summary)

1. Minimal deliverable = a zip `cadwellio<ver>.zip` unpacking to `cadwellio<ver>/` with
   `eegplugin_cadwellio.m` (returns `'cadwellio<ver>'`, `findobj(fig,'tag','import data')`,
   `uimenu(..., 'callback', [trystrs.no_check '[EEG LASTCOM] = pop_loadcadwell;' catchstrs.new_non_empty])`),
   `pop_loadcadwell.m` (`[EEG, com] = pop_loadcadwell(filename, 'key', val)`; `uigetfile('*.ezdataindex;*.ezdata')`
   + `inputgui` when `nargin < 1`; `com = sprintf('EEG = pop_loadcadwell(''%s''%s);', ...)`), a reader
   that returns `eeg_emptyset` filled with `data` (uV, chans x samples, single), `srate`, `nbchan`,
   `pnts`, `trials=1`, `xmin=0`, `chanlocs(i).labels/.type`, `event(i).type/.latency/.duration`,
   `'boundary'` events with `duration` for gaps, `setname`, `comments`, `etc.T0`, `etc.cadwell.*`,
   then `EEG = eeg_checkset(EEG,'eventconsistency'); EEG = eeg_checkset(EEG,'makeur');`, plus
   README and a license file. Submit via the "New plugin or plugin update" GitHub issue with the zip.
2. Via FieldTrip instead: needs a fieldtrip PR (`ft_filetype` + `ft_read_*` + `private/`) and
   arrives in EEGLAB's *File > Import data > Using the FILE-IO interface* only with the next
   `Fileio<yymmdd>` snapshot (months). An EEGLAB plugin can *also* expose `cadwell_fileio_read_header`
   etc. for FieldTrip users the way mffmatlabio does, without waiting.
3. SQLite access is the hard dependency decision (Database Toolbox `sqlite()` vs. bundled MEX vs. Java
   JDBC); it determines Octave support and the platform-binary burden.
4. BioSig offers nothing for `.ezdata` (only an unsupported stub for EAS/EZ3/ARC).

## URL index

- https://github.com/sccn/eeglab (eeglab.m, functions/adminfunc/eeg_checkset.m, functions/popfunc/{eeg_emptyset,eeg_insertbound,eeg_boundarytype,eeg_isboundary,pop_fileio,pop_biosig,pop_chanedit}.m, functions/sigprocfunc/{biosig2eeglab,biosig2eeglabevent,readlocs,writeeeg}.m, functions/adminfunc/{plugin_getweb,plugin_install,plugin_askinstall,plugin_menu,eegh}.m, .github/ISSUE_TEMPLATE/new-plugin-or-plugin-update.md, .github/workflows/test.yml, eeglab.prj, LICENSE, CONTRIBUTING.md, AGENTS.md)
- https://github.com/sccn/sccn.github.io (tutorials/contribute/design_plugin.md, tutorials/contribute/Contributing_to_EEGLAB.md, others/EEGLAB_Extensions.md, others/Running_EEGLAB_on_Octave.md, others/EEGLAB_test_cases.md, others/Compiled_EEGLAB.md, others/EEGLAB_revision_history.md) = https://eeglab.org/...
- https://github.com/sccn/bva-io, https://github.com/sccn/neuroscanio, https://github.com/xdf-modules/xdf-EEGLAB, https://github.com/xdf-modules/xdf-Matlab, https://github.com/arnodelorme/mffmatlabio
- https://github.com/fieldtrip/fileio, https://github.com/fieldtrip/fieldtrip (fileio/ft_filetype.m, ft_read_header.m, ft_read_data.m, ft_read_event.m)
- https://github.com/sccn/eeglab_tests, https://github.com/sccn/eeglab-testcases
- https://github.com/sccn/eeglab/issues/970, /954, /965, /964 (recent plugin submissions)
- https://sourceforge.net/p/biosig/code/ci/master/tree/biosig4c++/t210/sopen_cadwell_read.c, https://sourceforge.net/p/biosig/feature-requests/13/
- Blocked but referenced by the wiki: http://sccn.ucsd.edu/eeglab/plugin_uploader/upload_form.php, https://sccn.ucsd.edu/eeglab/plugin_uploader/plugin_list_all.php, http://sccn.ucsd.edu/eeglab/plugin_uploader/plugin_getcountall_nowiki_json.php
