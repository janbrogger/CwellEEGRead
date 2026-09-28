"""Run the EEGLAB importer pop_cadwell under GNU Octave with EEGLAB's own
functions on the path (TST013): the dataset must pass eeg_checkset and a
pop_saveset/pop_loadset round trip, and a recording pause must appear as a
'Recording gap' event (padded) or as one 'boundary' event whose duration is
the number of removed samples (concatenated), with the later events moved up.

Needs octave, the public test exports and an EEGLAB checkout named by the
environment variable EEGLAB_DIR (its functions/ folder is used) plus the
dipfit plugin either under <EEGLAB_DIR>/plugins/dipfit or named by DIPFIT_DIR
(eeg_checkset calls dipfitdefs). Skipped otherwise."""
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

octave = shutil.which("octave-cli") or shutil.which("octave")
pytestmark = pytest.mark.skipif(
    octave is None or not (E3 / "native-export").exists() or not EEGLAB or not Path(EEGLAB, "functions").is_dir()
    or not Path(DIPFIT, "dipfitdefs.m").exists(),
    reason="GNU Octave, public export 3 or an EEGLAB checkout (EEGLAB_DIR, dipfit) is not available")

SCRIPT = r"""
warning('off', 'all');
addpath(genpath(fullfile('{eeglab}', 'functions'))); addpath('{dipfit}'); addpath('{plugin}');
A = pop_cadwell('{export}');
B = pop_cadwell('{export}', 'padgaps', 'off');
gap = A.event(strcmp({{A.event.type}}, 'Recording gap'));
bnd = B.event(strcmp({{B.event.type}}, 'boundary'));
assert(numel(gap) == 1 && numel(bnd) == 1, 'one pause expected');
assert(gap.duration == 10 * A.srate && bnd.duration == 10 * A.srate, 'pause is 10 s');
assert(B.pnts == A.pnts - 10 * A.srate, 'concatenated data shorter by the pause');
assert(all(all(A.data(:, gap.latency + (0:gap.duration - 1)) == 0)), 'padded pause is zeros');
assert(abs(bnd.latency - (gap.latency - 0.5)) < 1e-9, 'boundary at the join');
% every event after the pause moves up by the pause; events inside it land on the join
la = [A.event.latency]; lb = [B.event.latency]; ta = {{A.event.type}}; tb = {{B.event.type}};
assert(isequal(ta(~strcmp(ta, 'Recording gap')), tb(~strcmp(tb, 'boundary'))), 'same events');
la = la(~strcmp(ta, 'Recording gap')); lb = lb(~strcmp(tb, 'boundary'));
after = la >= gap.latency + gap.duration; inside = la > gap.latency & ~after;
assert(all(lb(after) == la(after) - gap.duration) && all(lb(inside) == gap.latency) && all(lb(~after & ~inside) == la(~after & ~inside)), 'latencies');
assert(strcmp(A.chanlocs(3).labels, 'Fp1') && strcmp(A.chanlocs(3).ref, 'Cz') && strcmp(A.ref, 'Cz'), 'labels');
pop_saveset(B, 'filename', 'roundtrip.set', 'filepath', '{tmp}');
C = pop_loadset('filename', 'roundtrip.set', 'filepath', '{tmp}');
assert(C.pnts == B.pnts && numel(C.event) == numel(B.event) && isequal(C.data, B.data), 'set file round trip');
disp('EEGLAB_IMPORT_OK');
"""


def test_pop_cadwell_with_eeglab(tmp_path):
    code = SCRIPT.format(eeglab=EEGLAB, dipfit=DIPFIT, plugin=PLUGIN, export=E3, tmp=tmp_path)
    r = subprocess.run([octave, "--no-gui", "--quiet", "--eval", code], cwd=ROOT, capture_output=True, text=True, timeout=1800)
    print(r.stdout, r.stderr)
    assert r.returncode == 0 and "EEGLAB_IMPORT_OK" in r.stdout, r.stdout + r.stderr
