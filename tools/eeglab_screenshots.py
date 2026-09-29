"""Screenshots of the EEGLAB plugin in EEGLAB's graphical interface under GNU
Octave (TST018), for manual verification.

    .venv/bin/python tools/eeglab_screenshots.py [OUT_DIR]     # default docs/screenshots/eeglab

Starts a virtual X display (Xvfb), EEGLAB with the plugin copied into a
private plugins/ folder, and chooses File > Import data > Using EEGLAB
functions and plugins > From Cadwell. The dialogs are the real ones and are
operated from outside like a user would (xdotool): the file dialog is
pointed at public export 3 and the .ezdataindex chosen, the options dialog
and EEGLAB's naming dialog are confirmed with OK (defaults). The dataset is
then shown with pop_eegplot, first page, 10 s window. Writes:

    1-file-dialog.png     the file dialog, in the export's CadLink/Data folder
    2-options-dialog.png  the import options dialog (defaults)
    3-naming-dialog.png   EEGLAB's dataset naming dialog
    4-eegplot-10s.png     the EEG, first 10 s of export 3

Needs octave, Xvfb, xdotool, ImageMagick (import), an EEGLAB checkout
(EEGLAB_DIR with eeglab.m and functions/, DIPFIT_DIR) and, on
Debian/Ubuntu, fonts-freefont-otf. Public domain (Unlicense).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "uses" / "EEGLAB" / "cadwellio"
EXPORT = ROOT / "testdata" / "public" / "cadwell-export3"
TOOLS = ("octave", "Xvfb", "xdotool", "import")
SCREEN = (1600, 1000)
FILE_DIALOG = "Import Cadwell EEG"
OPTIONS_DIALOG = "Import Cadwell EEG -- pop_cadwell()"

SCRIPT = r"""
warning('off', 'all');
addpath('{octave_dir}'); addpath('{dipfit}'); cd('{eeglab}');
eeglab;
h = findobj(0, 'type', 'uimenu', 'label', 'From Cadwell (.ezdataindex / converted EDF)');
eval(get(h, 'callback'));
assert(numel(ALLEEG) == 1, 'no dataset stored');
pop_eegplot(EEG, 1, 1, 1, [], 'winlength', 10, 'position', [0 0 {w} {h}]);
drawnow; pause(2); drawnow;
printf('EEGPLOT_READY %s %d ch %g Hz\n', EEG.setname, EEG.nbchan, EEG.srate); fflush(stdout);
pause(600);
"""


def missing():
    need = [t for t in TOOLS if shutil.which(t) is None]
    eeglab = os.environ.get("EEGLAB_DIR", "")
    if not eeglab or not Path(eeglab, "eeglab.m").exists() or not Path(eeglab, "functions").is_dir():
        need.append("EEGLAB_DIR")
    if not Path(dipfit_dir(), "dipfitdefs.m").exists():
        need.append("DIPFIT_DIR")
    if not (EXPORT / "native-export").exists():
        need.append(str(EXPORT))
    return need


def dipfit_dir():
    eeglab = os.environ.get("EEGLAB_DIR", "")
    return os.environ.get("DIPFIT_DIR", os.path.join(eeglab, "plugins", "dipfit") if eeglab else "")


def plugin_version():
    return (PLUGIN / "eegplugin_cadwellio.m").read_text().split("vers = '", 1)[1].split("'", 1)[0]


def build_eeglab(work):
    """A private EEGLAB tree with the plugin in plugins/, as installed from its zip."""
    tree = work / "eeglab"
    tree.mkdir()
    for item in Path(os.environ["EEGLAB_DIR"]).iterdir():
        if item.is_file():
            shutil.copy2(item, tree / item.name)
    shutil.copytree(Path(os.environ["EEGLAB_DIR"], "functions"), tree / "functions")
    (tree / "plugins").mkdir()
    shutil.copytree(PLUGIN, tree / "plugins" / plugin_version(), ignore=shutil.ignore_patterns("lib"))
    return tree


class Screen:
    def __init__(self, env, log):
        self.env, self.log = env, log

    def x(self, *args):
        return subprocess.run(["xdotool", *args], env=self.env, capture_output=True, text=True).stdout.strip()

    def window(self, title, timeout=300, prefix=False):
        """Id of the visible window whose title is `title` (or starts with it)."""
        pattern = "^" + re.escape(title) + ("" if prefix else "$")
        end = time.time() + timeout
        while time.time() < end:
            ids = self.x("search", "--onlyvisible", "--name", pattern).split()
            if ids:
                time.sleep(1.5)                                   # let it finish drawing
                return ids[-1]
            if self.log.poll() is not None:
                raise RuntimeError("Octave exited while waiting for window " + repr(title))
            time.sleep(0.5)
        raise TimeoutError("window not shown: " + repr(title))

    def shoot(self, win, path):
        subprocess.run(["import", "-window", win, str(path)], env=self.env, check=True)
        print("wrote", path)

    def geometry(self, win):
        out = self.x("getwindowgeometry", "--shell", win)
        g = dict(line.split("=") for line in out.splitlines())
        return int(g["X"]), int(g["Y"]), int(g["WIDTH"]), int(g["HEIGHT"])

    def click_ok(self, win, work):
        """Press inputgui's OK button, the rightmost light button in the bottom row."""
        from PIL import Image
        shot = work / "ok.png"
        subprocess.run(["import", "-window", win, str(shot)], env=self.env, check=True)
        img = Image.open(shot).convert("L")
        w, h = img.size
        top = int(h * 0.75)                                     # the button row only
        px = img.load()
        cols = [c for c in range(w) if sum(px[c, r] > 225 for r in range(top, h)) > 10]
        right = cols[-1]
        left = right
        while left - 1 in cols:
            left -= 1
        rows = [r for r in range(top, h) if px[left + 3, r] > 225]
        bottom = rows[-1]                                      # the button: last run of light rows
        first = bottom
        while first - 1 in rows:
            first -= 1
        rows = [first, bottom]
        x, y, _, _ = self.geometry(win)
        cx, cy = x + (left + right) // 2, y + (rows[0] + rows[-1]) // 2
        print("OK button at", cx, cy)
        self.x("mousemove", "--sync", str(cx), str(cy))
        time.sleep(0.3)
        self.x("mousedown", "1")
        time.sleep(0.15)
        self.x("mouseup", "1")

    def type_line(self, win, text):
        self.x("windowactivate", "--sync", win)
        self.x("windowfocus", "--sync", win)
        self.x("type", "--delay", "20", "--window", win, text)
        self.x("key", "--window", win, "Return")


def main(out_dir):
    need = missing()
    if need:
        sys.exit("missing: " + ", ".join(need))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = next((EXPORT / "native-export").rglob("*.ezdataindex"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        tree = build_eeglab(work)
        display = ":%d" % (90 + os.getpid() % 100)
        xvfb = subprocess.Popen(["Xvfb", display, "-screen", "0", "%dx%dx24" % SCREEN, "-nolisten", "tcp"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = dict(os.environ, DISPLAY=display, HOME=str(work))
        code = SCRIPT.format(octave_dir=tree / "plugins" / plugin_version() / "octave", dipfit=dipfit_dir(),
                             eeglab=tree, w=SCREEN[0], h=SCREEN[1] - 40)
        logf = open(work / "octave.log", "w+")
        octave = None
        try:
            time.sleep(1)
            octave = subprocess.Popen(["octave", "--no-gui", "--quiet", "--no-init-file", "--eval", code],
                                      cwd=work, env=env, stdout=logf, stderr=subprocess.STDOUT)
            s = Screen(env, octave)
            win = s.window(FILE_DIALOG)
            s.type_line(win, str(index.parent))                 # go to CadLink/Data
            time.sleep(2)
            s.shoot(win, out_dir / "1-file-dialog.png")
            s.type_line(win, index.name)
            win = s.window(OPTIONS_DIALOG)
            s.shoot(win, out_dir / "2-options-dialog.png")
            s.click_ok(win, work)
            win = s.window("Dataset info -- pop_newset()")
            s.shoot(win, out_dir / "3-naming-dialog.png")
            s.click_ok(win, work)
            end = time.time() + 300
            while "EEGPLOT_READY" not in (work / "octave.log").read_text():
                if octave.poll() is not None or time.time() > end:
                    raise RuntimeError("EEG display not shown")
                time.sleep(0.5)
            win = s.window("Scroll channel activities -- eegplot()", prefix=True)
            s.shoot(win, out_dir / "4-eegplot-10s.png")
            print([line for line in (work / "octave.log").read_text().splitlines() if "EEGPLOT_READY" in line][0])
        except Exception:
            subprocess.run(["import", "-window", "root", str(out_dir / "failure-screen.png")], env=env)
            logf.seek(0)
            print("".join(l for l in logf.read().splitlines(True) if not l.startswith("warning"))[-3000:], file=sys.stderr)
            raise
        finally:
            if octave is not None:
                octave.kill()
            xvfb.kill()
            logf.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "screenshots" / "eeglab")
