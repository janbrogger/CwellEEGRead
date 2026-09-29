"""Drive the EEGLAB plugin through EEGLAB's own graphical interface under GNU
Octave on a virtual display (TST017): EEGLAB starts with the plugin in its
plugins/ folder, File > Import data > Using EEGLAB functions and plugins >
From Cadwell is present and enabled, and choosing it runs the file dialog,
the import options dialog and EEGLAB's standard dataset naming dialog
(pop_newset). The options chosen in the dialog must reach the dataset and
the history; Cancel in the options dialog must create no dataset.

The dialogs are EEGLAB's real inputgui windows: a stand-in inputgui draws
each one with inputgui's 'plot' mode, fills in the answers by widget tag,
presses OK and collects the values with inputgui's 'getresult' mode, so the
dialogs' layout, tags and value decoding are exercised as a user would.
Only the operating system's file dialog (uigetfile) is replaced.

Also covers the plugin's GNU Octave stand-ins (uses/EEGLAB/cadwellio/octave):
vers.m lets EEGLAB's main window open, contains.m (put on the path by the
plugin when Octave lacks contains) lets eeglab_new store the dataset.

Needs octave with a graphics toolkit, xvfb-run, public export 3 and an
EEGLAB checkout (EEGLAB_DIR with eeglab.m and functions/, dipfit via
DIPFIT_DIR). Skipped otherwise, and when Octave cannot draw text on the
virtual display (Debian/Ubuntu: install fonts-freefont-otf)."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "uses" / "EEGLAB" / "cadwellio"
E3 = ROOT / "testdata" / "public" / "cadwell-export3"
EEGLAB = os.environ.get("EEGLAB_DIR", "")
DIPFIT = os.environ.get("DIPFIT_DIR", os.path.join(EEGLAB, "plugins", "dipfit") if EEGLAB else "")
OPTIONS_TITLE = "Import Cadwell EEG -- pop_cadwell()"

octave = shutil.which("octave")
xvfb = shutil.which("xvfb-run")
pytestmark = pytest.mark.skipif(
    octave is None or xvfb is None or not (E3 / "native-export").exists() or not EEGLAB
    or not Path(EEGLAB, "eeglab.m").exists() or not Path(EEGLAB, "functions").is_dir()
    or not Path(DIPFIT, "dipfitdefs.m").exists(),
    reason="GNU Octave, xvfb-run, public export 3 or an EEGLAB checkout (EEGLAB_DIR with eeglab.m, dipfit) is not available")


def run_octave(code, home, timeout):
    env = dict(os.environ, HOME=str(home))
    return subprocess.run([xvfb, "-a", octave, "--no-gui", "--quiet", "--no-init-file", "--eval", code],
                          cwd=home, env=env, capture_output=True, text=True, timeout=timeout)


def plugin_version():
    text = (PLUGIN / "eegplugin_cadwellio.m").read_text()
    return text.split("vers = '", 1)[1].split("'", 1)[0]


# Stand-in for inputgui: draws the real dialog, answers it, returns its values.
INPUTGUI = r"""
function [result, userdat, strhalt, resstruct] = inputgui(varargin)
    global GUITEST
    result = {}; userdat = []; strhalt = ''; resstruct = [];
    here = fileparts(mfilename('fullpath'));
    rmpath(here); restore = onCleanup(@() addpath(here, '-begin'));
    k = numel(GUITEST.titles) + 1;
    it = find(strcmp(varargin(1:2:end), 'title'));
    GUITEST.titles{k} = ''; if ~isempty(it), GUITEST.titles{k} = varargin{2 * it}; end
    old = findobj(0, 'type', 'figure');
    inputgui(varargin{:}, 'mode', 'plot');
    fig = setdiff(findobj(0, 'type', 'figure'), old);
    assert(numel(fig) == 1, 'inputgui drew no dialog');
    popups = findobj(fig, 'style', 'popupmenu'); items = struct();
    for h = popups(:)', s = get(h, 'string'); if ischar(s), s = strsplit(strjoin(cellstr(s)', '|'), '|'); end; items.(get(h, 'tag')) = numel(s); end
    GUITEST.popupitems{k} = items;
    answer = GUITEST.answers{k};
    if ischar(answer) && strcmp(answer, 'cancel'), close(fig); return; end
    for f = fieldnames(answer)'
        h = findobj(fig, 'tag', f{1});
        assert(numel(h) == 1, sprintf('no widget tagged %s in "%s"', f{1}, GUITEST.titles{k}));
        if strcmp(get(h, 'style'), 'edit'), set(h, 'string', answer.(f{1})); else, set(h, 'value', answer.(f{1})); end
    end
    set(findobj(fig, 'tag', 'ok'), 'userdata', 'retuninginputui');
    [result, userdat, strhalt, resstruct] = inputgui('getresult', fig);
    close(fig);
end
"""

UIGETFILE = r"""
function [f, p] = uigetfile(varargin)
    global GUITEST
    [p, n, e] = fileparts(GUITEST.file); f = [n e]; p = [p filesep];
end
"""

EEGLAB_ERROR = r"""
function eeglab_error
    global GUITEST
    e = lasterror(); GUITEST.errors{end+1} = e.message;
    printf('EEGLAB_ERROR: %s\n', e.message);
    for k = 1:numel(e.stack), printf('  %s:%d\n', e.stack(k).name, e.stack(k).line); end
end
"""

SCRIPT = r"""
warning('off', 'all');
global GUITEST
GUITEST = struct('file', '{file}', 'titles', {{{{}}}}, 'popupitems', {{{{}}}}, 'errors', {{{{}}}});
GUITEST.answers = {{ struct('importevent', 1, 'padgaps', 2, 'eventtiming', 2), ...  % options: pad pauses, stamp timing
                    struct('namenew', 'Cadwell GUI test'), ...                     % EEGLAB's naming dialog
                    'cancel' }};                                                   % options dialog of the second import
native_contains = exist('contains') > 0;
addpath('{dipfit}'); addpath('{stubs}', '-begin'); cd('{eeglab}');
eeglab;
addpath('{stubs}', '-begin');
h = findobj(0, 'type', 'uimenu', 'label', 'From Cadwell (.ezdataindex / converted EDF)');
assert(numel(h) == 1, 'menu item missing');
assert(strcmp(get(get(h, 'parent'), 'label'), 'Using EEGLAB functions and plugins'), 'menu item in the wrong menu');
assert(strcmp(get(h, 'enable'), 'on'), 'menu item disabled');
if ~native_contains
    assert(strcmp(fileparts(which('contains')), fullfile(fileparts(which('eegplugin_cadwellio')), 'octave')), 'plugin did not add its contains() stand-in');
end

eval(get(h, 'callback'));                        % first import: answer both dialogs
assert(isempty(GUITEST.errors), 'errors during import');
assert(numel(GUITEST.titles) == 2 && strcmp(GUITEST.titles{{1}}, '{title}'), 'options dialog not shown first');
assert(~isempty(strfind(lower(GUITEST.titles{{2}}), 'dataset')), 'EEGLAB naming dialog not shown');
assert(GUITEST.popupitems{{1}}.padgaps == 2 && GUITEST.popupitems{{1}}.eventtiming == 2, 'popup menus need two choices each');
assert(numel(ALLEEG) == 1 && CURRENTSET == 1, 'dataset not stored');
assert(strcmp(EEG.setname, 'Cadwell GUI test'), 'name from the naming dialog not applied');
gap = EEG.event(strcmp({{EEG.event.type}}, 'Recording gap'));
assert(numel(gap) == 1 && gap.duration == 10 * EEG.srate, 'padded pause expected (padgaps on)');
assert(~any(strcmp({{EEG.event.type}}, 'boundary')), 'no boundary event with padded pauses');
assert(strcmp(EEG.etc.cadwell.eventTiming, 'stamp'), 'event timing from the dialog not applied');
hist = EEG.history;
assert(~isempty(strfind(hist, 'pop_cadwell(')) && ~isempty(strfind(hist, '''padgaps'', ''on''')) ...
       && ~isempty(strfind(hist, '''eventtiming'', ''stamp''')), 'history does not record the options');

eval(get(h, 'callback'));                        % second import: Cancel in the options dialog
assert(isempty(GUITEST.errors), 'errors after Cancel');
assert(numel(GUITEST.titles) == 3 && strcmp(GUITEST.titles{{3}}, '{title}'), 'options dialog expected');
assert(numel(ALLEEG) == 1, 'Cancel must not create a dataset');
disp('EEGLAB_GUI_OK');
"""


def build_eeglab(tmp_path):
    """A private EEGLAB tree with the plugin in plugins/."""
    tree = tmp_path / "eeglab"
    tree.mkdir()
    for item in Path(EEGLAB).iterdir():
        if item.is_file():
            shutil.copy2(item, tree / item.name)
    # copies, not links: EEGLAB finds its own folder (and so plugins/) from
    # the resolved paths of functions/, and its plugin scan skips links
    shutil.copytree(Path(EEGLAB, "functions"), tree / "functions")
    (tree / "plugins").mkdir()
    # the plugin as from its zip; dipfit, which eeg_checkset needs, only goes on the path
    shutil.copytree(PLUGIN, tree / "plugins" / plugin_version(), ignore=shutil.ignore_patterns("lib"))
    return tree


def test_import_through_the_eeglab_menu(tmp_path):
    probe = run_octave("f = figure('visible', 'off'); "
                       "axes('parent', f); text(0, 0, 'x'); drawnow; disp('DRAW_OK');", tmp_path, 300)
    if "DRAW_OK" not in probe.stdout:
        pytest.skip("Octave cannot draw on the virtual display: " + (probe.stderr.strip().splitlines() or ["?"])[-1])
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "inputgui.m").write_text(INPUTGUI)
    (stubs / "uigetfile.m").write_text(UIGETFILE)
    (stubs / "eeglab_error.m").write_text(EEGLAB_ERROR)
    # vers.m must precede EEGLAB's start (as ~/.octaverc would put it); contains.m
    # is left for the plugin to add
    shutil.copy2(PLUGIN / "octave" / "vers.m", stubs / "vers.m")
    tree = build_eeglab(tmp_path)
    index = next((E3 / "native-export").rglob("*.ezdataindex"))
    code = SCRIPT.format(file=index, stubs=stubs, eeglab=tree, dipfit=DIPFIT, title=OPTIONS_TITLE)
    r = run_octave(code, tmp_path, 1800)
    print(r.stdout, r.stderr)
    assert r.returncode == 0 and "EEGLAB_GUI_OK" in r.stdout, r.stdout[-4000:] + r.stderr[-4000:]
