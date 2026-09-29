"""TST007 / DES014: --anonymize keeps patient identifiers and free text out of the
EDF and the JSON report and leaves the signal unchanged. Export 2 has a Comment
and a UserEvent with typed text."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pyedflib = pytest.importorskip("pyedflib")
from cwelleegread import open_recording
from cwelleegread.edf import ANONYMIZED_EVENT_TYPES

ROOT = Path(__file__).resolve().parents[1]
E2 = ROOT / "testdata" / "public" / "cadwell-export2"

pytestmark = pytest.mark.skipif(not (E2 / "native-export").exists(), reason="public test export 2 missing")


def run(tmp_path, name, *extra):
    out, rep = tmp_path / f"{name}.edf", tmp_path / f"{name}.json"
    r = subprocess.run([sys.executable, "-m", "cwelleegread", "convert", str(E2), str(out), "--all-events",
                        "--json", str(rep), *extra], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out, json.loads(rep.read_text()), rep.read_text()


def test_anonymize(tmp_path):
    rec = open_recording(str(E2))
    free = [e for e in rec.events() if e.type in ANONYMIZED_EVENT_TYPES]
    assert {"Comment", "UserEvent"} <= {e.type for e in free}
    free_texts = {e.text for e in free if e.text and e.text != e.type}
    assert free_texts

    plain, rep_p, _ = run(tmp_path, "plain")
    anon, rep_a, rep_a_text = run(tmp_path, "anon", "--anonymize", "--patient-name", "Anon Ymous")
    plain_bytes, anon_bytes = plain.read_bytes(), anon.read_bytes()

    # without the option the identifiers are there (so the test below is not vacuous)
    assert rec.patient_guid.encode() in plain_bytes and rep_p["patient_guid"] == rec.patient_guid
    assert any(t.encode("utf-8") in plain_bytes for t in free_texts)

    # patient identification: placeholder code, the supplied name, sex and birth date X
    with pyedflib.EdfReader(str(anon)) as f:
        hdr = f.getHeader()
        assert hdr["patientname"] == "Anon Ymous"      # pyedflib turns the EDF+ "_" back into a space
        anon_ann = list(zip(*f.readAnnotations()))
        anon_sig = [f.readSignal(i, digital=True) for i in range(f.signals_in_file)]
    assert anon_bytes[8:88].decode().strip() == "X X X Anon_Ymous"    # EDF+ code sex birthdate name
    assert rec.patient_guid.encode() not in anon_bytes
    assert rep_a["patient_guid"] is None and rec.patient_guid not in rep_a_text

    # free text: written as the event type, nowhere in the EDF or the report
    for t in free_texts:
        assert t.encode("utf-8") not in anon_bytes and t not in rep_a_text, "free text leaked"
    texts = [t for _, _, t in anon_ann]
    assert texts.count("Comment") >= 1 and texts.count("UserEvent") >= 1
    assert len(anon_ann) == rep_a["annotations_written"] == rep_p["annotations_written"]

    # the signal is unchanged
    with pyedflib.EdfReader(str(plain)) as f:
        plain_sig = [f.readSignal(i, digital=True) for i in range(f.signals_in_file)]
    assert len(plain_sig) == len(anon_sig) == 32
    assert all(np.array_equal(a, b) for a, b in zip(plain_sig, anon_sig))
