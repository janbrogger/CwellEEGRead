"""TST009 - Doorstop traceability validation (covers REQ013)."""
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "docs" / "traceability"
DOCS = {"NEED": TRACE / "needs", "REQ": TRACE / "requirements", "TST": TRACE / "tests"}


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


def test_every_requirement_is_covered_by_a_test():
    reqs, tests = load("REQ"), load("TST")
    covered = {l for t in tests.values() for l in links_of(t)}
    missing = [uid for uid, item in reqs.items()
               if item.get("normative", True) and item.get("active", True) and uid not in covered]
    assert not missing, f"requirements without a TST item: {missing}"
