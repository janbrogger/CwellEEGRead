"""TST009 - Doorstop traceability validation (covers REQ013 through DES013): the chain NEED -> REQ -> DES -> TST is complete."""
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "docs" / "traceability"
DOCS = {"NEED": TRACE / "needs", "REQ": TRACE / "requirements", "DES": TRACE / "design", "TST": TRACE / "tests"}


def load(doc):
    items = {}
    for p in sorted(DOCS[doc].glob(f"{doc}*.yml")):
        items[p.stem] = yaml.safe_load(p.read_text(encoding="utf-8"))
    return items


def links_of(item):
    out = []
    for link in item.get("links") or []:
        out.append(next(iter(link)) if isinstance(link, dict) else str(link))
    return out


def test_doorstop_validates():
    exe = ROOT / ".venv" / "bin" / "doorstop"
    cmd = [str(exe)] if exe.exists() else [sys.executable, "-m", "doorstop"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "ERROR" not in res.stderr.upper().replace("ERRORS: 0", "")


def test_every_requirement_links_to_a_need():
    reqs, needs = load("REQ"), load("NEED")
    for uid, item in reqs.items():
        if not item.get("normative", True) or not item.get("active", True):
            continue
        parents = [l for l in links_of(item) if l in needs]
        assert parents, f"{uid} has no link to a NEED item"


def active(items):
    return {uid: it for uid, it in items.items() if it.get("normative", True) and it.get("active", True)}


def test_every_requirement_has_a_design():
    reqs, designs = active(load("REQ")), load("DES")
    designed = {l for d in designs.values() for l in links_of(d)}
    missing = [uid for uid in reqs if uid not in designed]
    assert not missing, f"requirements without a DES item: {missing}"


def test_every_design_links_to_a_requirement_and_has_text():
    reqs, designs = load("REQ"), active(load("DES"))
    for uid, item in designs.items():
        parents = [l for l in links_of(item) if l in reqs]
        assert parents, f"{uid} has no link to a REQ item"
        assert (item.get("text") or "").strip(), f"{uid} has no design text"


def test_every_design_is_covered_by_a_test():
    designs, tests = active(load("DES")), load("TST")
    covered = {l for t in tests.values() for l in links_of(t)}
    missing = [uid for uid in designs if uid not in covered]
    assert not missing, f"design items without a TST item: {missing}"


def test_every_requirement_is_covered_by_a_test_through_its_design():
    reqs, designs, tests = active(load("REQ")), load("DES"), load("TST")
    tested_designs = {l for t in tests.values() for l in links_of(t)}
    covered = {l for uid, d in designs.items() if uid in tested_designs for l in links_of(d)}
    missing = [uid for uid in reqs if uid not in covered]
    assert not missing, f"requirements without a TST item (through DES): {missing}"
