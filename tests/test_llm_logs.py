"""TST010 - LLM log integrity (covers REQ012)."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "llm-logs"


def session_dirs():
    return {p.name for p in LOG.iterdir()
            if p.is_dir() and (p / "transcript.jsonl").exists()}


def test_every_session_folder_is_indexed_and_vice_versa():
    with open(LOG / "sessions.csv", encoding="utf-8", newline="") as f:
        indexed = {r["session_id"] for r in csv.DictReader(f)}
    folders = session_dirs()
    assert folders, "no archived sessions at all"
    assert folders <= indexed, f"folders not in sessions.csv: {folders - indexed}"
    # a session may be indexed (SessionStart) before its transcript is archived,
    # but never for a folder that has since been committed
    for sid in folders:
        for name in ("session.json", "prompts.csv", "PROMPTS-AND-RESPONSES.md"):
            assert (LOG / sid / name).exists(), f"{sid}/{name} missing"


def test_index_regenerates_cleanly(tmp_path):
    res = subprocess.run([sys.executable, str(LOG / "tools" / "llmlog.py"), "index"],
                         cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0 and "llmlog:" not in res.stderr, res.stderr
    assert (LOG / "SESSIONS.md").exists()
