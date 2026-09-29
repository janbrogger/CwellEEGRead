#!/usr/bin/env python3
"""Fill in sizes and SHA-256 checksums in testdata/manifest.json (REQ007).

Edit the manifest by hand first (ids, location, file names, software version,
notes), then run this script; it only touches the "sha256" and "bytes" fields.
A recording's "location" is "private" (default: clinical data under
testdata/private/, never committed) or "public" (non-patient data committed
under testdata/public/); file names are relative to that folder. Entries whose
files are absent are left unchanged.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
FILE_KEYS = ("cadwell", "native_edf", "native_csv")


def location_dir(rec):
    return HERE / rec.get("location", "private")


def sha256_of(path):
    h = hashlib.sha256()
    if path.is_dir():                       # multi-file study: hash the sorted file list + contents
        for p in sorted(path.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(path).as_posix().encode())
                h.update(p.read_bytes())
        return h.hexdigest()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def size_of(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.is_dir() else path.stat().st_size


def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for rec in data.get("recordings", []):
        for key in FILE_KEYS:
            entry = rec[key]
            path = location_dir(rec) / entry["file"]
            if not path.exists():
                print(f"missing: {path}")
                continue
            entry["sha256"] = sha256_of(path)
            entry["bytes"] = size_of(path)
            print(f"{rec['id']}/{key}: {entry['bytes']} bytes {entry['sha256'][:12]}…")
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
