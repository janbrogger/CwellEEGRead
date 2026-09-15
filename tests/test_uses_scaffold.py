"""TST013 - downstream use scaffolds present (covers REQ016)."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["Morgoth", "SCOREAI", "EEGLAB"])
def test_use_folder_has_readme_with_status(name):
    readme = ROOT / "uses" / name / "README.md"
    assert readme.exists(), f"uses/{name}/README.md missing"
    text = readme.read_text(encoding="utf-8").lower()
    assert "status" in text and "prerequisite" in text
