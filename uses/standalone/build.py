#!/usr/bin/env python3
"""Build the standalone CwellEEGRead converter (REQ023, DES023).

    python uses/standalone/build.py [--outdir DIR]         # program file + zip
    python uses/standalone/build.py --exe [--outdir DIR]   # executable (REQ025, DES025)

writes DIR/cwelleegread.pyz (a Python zip application: the cwelleegread
package, a root __main__.py and the self-test recording) and
DIR/cwelleegread-standalone-<version>.zip (one folder with cwelleegread.pyz,
README.md and LICENSE); with --exe instead a PyInstaller one-file executable
DIR/cwelleegread-<version>-<platform>-<arch>[.exe] for the platform it runs on.
DIR defaults to uses/standalone/dist (gitignored). Run from a checkout with
numpy installed (the self-test file list is read from cwelleegread.selftest);
--exe also needs scipy, PyInstaller and tzdata. Public domain (Unlicense).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
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


def stage(stage_dir: Path) -> Path:
    """The package sources, the self-test files (checksums verified) and the root __main__.py."""
    pkg = stage_dir / "cwelleegread"
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
    (stage_dir / "__main__.py").write_text(ENTRY, encoding="utf-8")
    return stage_dir


def build(outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        app = stage(Path(tmp) / "app")
        pyz = outdir / "cwelleegread.pyz"
        zipapp.create_archive(app, pyz, interpreter="/usr/bin/env python3", compressed=True)

    folder = f"cwelleegread-standalone-{__version__}"
    archive = outdir / f"{folder}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pyz, f"{folder}/cwelleegread.pyz")
        z.write(HERE / "README.md", f"{folder}/README.md")
        z.write(ROOT / "LICENSE", f"{folder}/LICENSE")
    return pyz, archive


def platform_tag() -> str:
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), platform.system().lower())
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    return f"{system}-{arch}"


def build_exe(outdir: Path) -> Path:
    """PyInstaller one-file executable for this platform (PyInstaller cannot cross-compile)."""
    import importlib.util
    import PyInstaller.__main__
    # IANA time zones for --timezone: Windows has no system database, so bundle the tzdata package
    tz = ["--collect-data", "tzdata", "--hidden-import", "tzdata"] if importlib.util.find_spec("tzdata") else []
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    name = f"cwelleegread-{__version__}-{platform_tag()}"
    with tempfile.TemporaryDirectory() as tmp:
        app = stage(Path(tmp) / "app")
        PyInstaller.__main__.run([
            str(app / "__main__.py"), "--onefile", "--name", name, "--noconfirm", "--clean", "--log-level", "WARN",
            "--paths", str(app), "--hidden-import", "cwelleegread.__main__",
            "--add-data", f"{app / 'cwelleegread' / 'selftest_data'}{os.pathsep}cwelleegread/selftest_data",
            "--exclude-module", "tkinter", *tz,
            "--distpath", str(outdir), "--workpath", str(Path(tmp) / "work"), "--specpath", str(Path(tmp) / "spec"),
        ])
    exe = outdir / (name + (".exe" if platform.system() == "Windows" else ""))
    if not exe.is_file():
        raise SystemExit(f"PyInstaller did not produce {exe}")
    return exe


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--outdir", default=str(HERE / "dist"), help="output folder (default uses/standalone/dist)")
    ap.add_argument("--exe", action="store_true", help="build the executable for this platform with PyInstaller")
    args = ap.parse_args(argv)
    if args.exe:
        exe = build_exe(Path(args.outdir))
        print(f"built {exe} ({exe.stat().st_size // (1024 * 1024)} MiB)")
        return 0
    pyz, archive = build(Path(args.outdir))
    print(f"built {pyz} ({pyz.stat().st_size // 1024} KiB) and {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
