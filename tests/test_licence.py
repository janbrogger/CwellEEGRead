"""TST012 / DES015: licence compatibility. The repository and the EEGLAB plugin are
under the Unlicense; every ported third-party file is registered in
docs/research/ported-files.yml with a licence the Unlicense can carry and keeps
its notice; no unregistered source file carries a third-party licence marker."""
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "research" / "ported-files.yml"
PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Zlib", "CC0-1.0", "Unlicense", "public-domain"}
UNLICENSE_FIRST_LINE = "This is free and unencumbered software released into the public domain."
# text that marks a file as carrying someone else's licence (split so this file does not match itself)
MARKERS = re.compile("|".join(["GNU " + "General Public", "GNU " + "Lesser General", r"\bL?GPL" + r"-?[23]",
                               "SPDX-" + "License-Identifier", "Apache " + "License", "MIT " + "License",
                               "Mozilla " + "Public", r"Copyright \(" + r"[cC]\)", "Redistribution and use " + "in source"]))
SOURCE = re.compile(r"\.(py|m|sh|c|h|cpp|js|ts|r|R|jl|java|pyx)$")


def register():
    return yaml.safe_load(REGISTER.read_text(encoding="utf-8"))["ported"] or []


def test_repository_and_plugin_are_unlicense():
    for p in (ROOT / "LICENSE", ROOT / "uses" / "EEGLAB" / "cadwellio" / "LICENSE"):
        assert p.read_text(encoding="utf-8").splitlines()[0].strip() == UNLICENSE_FIRST_LINE, p


def test_registered_ports_are_compatible_and_keep_their_notice():
    for entry in register():
        path = ROOT / entry["path"]
        assert path.is_file(), f"registered port {entry['path']} missing"
        assert entry["licence"] in PERMISSIVE, \
            f"{entry['path']}: {entry['licence']} cannot be carried by the Unlicense without relicensing (REQ015)"
        assert entry["notice"] in path.read_text(encoding="utf-8", errors="replace"), f"{entry['path']}: notice missing"
        assert entry.get("origin"), f"{entry['path']}: origin missing"


def test_no_unregistered_third_party_licence_in_sources():
    try:
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    registered = {e["path"] for e in register()}
    hits = []
    for f in files:
        if not SOURCE.search(f) or f in registered or f.startswith(("llm-logs/", "docs/", "testdata/")):
            continue
        p = ROOT / f
        if p.is_file() and MARKERS.search(p.read_text(encoding="utf-8", errors="replace")):
            hits.append(f)
    assert not hits, f"third-party licence text in unregistered files (add to {REGISTER.name} or remove): {hits}"
