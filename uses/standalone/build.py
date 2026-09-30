#!/usr/bin/env python3
"""Build the standalone CwellEEGRead converter (REQ023, DES023).

    python uses/standalone/build.py [--outdir DIR]

writes DIR/cwelleegread.pyz (a Python zip application: the cwelleegread
package, a root __main__.py and the self-test recording) and
DIR/cwelleegread-standalone-<version>.zip (one folder with cwelleegread.pyz,
README.md and LICENSE), DIR defaulting to uses/standalone/dist (gitignored).
Run from a checkout with numpy installed (the self-test file list is read
from cwelleegread.selftest). Public domain (Unlicense).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import zipapp
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from cwelleegread import __version__  # noqa: E402
from cwelleegread.selftest import BUNDLED  # noqa: E402

ENTRY = """\
# Entry point of the standalone program file (uses/standalone/build.py, DES023).
import sys

from cwelleegread.__main__ import main

sys.exit(main())
"""


def build(outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        pkg = stage / "cwelleegread"
        pkg.mkdir(parents=True)
        for src in sorted((ROOT / "cwelleegread").glob("*.py")):
            shutil.copy2(src, pkg / src.name)
        for name, (repo_path, sha) in BUNDLED.items():
            data = (ROOT / repo_path).read_bytes()
            if hashlib.sha256(data).hexdigest() != sha:
                raise SystemExit(f"checksum mismatch for {repo_path}: the self-test data changed")
            target = pkg / "selftest_data" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (stage / "__main__.py").write_text(ENTRY, encoding="utf-8")
        pyz = outdir / "cwelleegread.pyz"
        zipapp.create_archive(stage, pyz, interpreter="/usr/bin/env python3", compressed=True)

    folder = f"cwelleegread-standalone-{__version__}"
    archive = outdir / f"{folder}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pyz, f"{folder}/cwelleegread.pyz")
        z.write(HERE / "README.md", f"{folder}/README.md")
        z.write(ROOT / "LICENSE", f"{folder}/LICENSE")
    return pyz, archive


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--outdir", default=str(HERE / "dist"), help="output folder (default uses/standalone/dist)")
    args = ap.parse_args(argv)
    pyz, archive = build(Path(args.outdir))
    print(f"built {pyz} ({pyz.stat().st_size // 1024} KiB) and {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
