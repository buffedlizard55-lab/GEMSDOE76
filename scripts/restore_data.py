#!/usr/bin/env python3
"""Restore the SHA-256-pinned GEMS data stack from public owner mirrors on GitHub.

Why mirrors: the organizer files live behind a DrivenData login
(https://www.drivendata.org/competitions/306/competition-doe-gems/data/).
The owner mirrors them in public GitHub repos; every byte restored here is
verified against the pins in ``registry/data_manifest.json`` (those pins match
GEMSDOE32's registry and GEMSDOE70's PINS). Mirror integrity is NOT organizer
authentication — see the manifest's provenance note.

Requires the GitHub CLI (``gh``) authenticated, or network access to
github.com / codeload.github.com. Large files land in ``.cache/gems_data``
(git-ignored); the two small bridge files are also copied to ``data/bridge``.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "gems_data"
MANIFEST = ROOT / "registry" / "data_manifest.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gh_raw(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as out:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=out, check=True)
    tmp.replace(dest)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    ok, bad = [], []
    for entry in manifest["files"]:
        dest = CACHE / entry["dest"]
        if not (dest.exists() and sha256(dest) == entry["sha256"]):
            if "parts" in entry:
                part_files = []
                for part in entry["parts"]:
                    pdest = CACHE.parent / "parts" / Path(part).name
                    gh_raw(entry["repo"], entry["ref"], part, pdest)
                    part_files.append(pdest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as out:
                    for pf in part_files:
                        out.write(pf.read_bytes())
            else:
                gh_raw(entry["repo"], entry["ref"], entry["path"], dest)
        digest = sha256(dest)
        (ok if digest == entry["sha256"] else bad).append(entry["id"])
        print(("OK   " if digest == entry["sha256"] else "FAIL ") + entry["id"], digest[:16])
    for name in ("sample_submission.tif", "existing_faults.tif"):
        src, dst = CACHE / name, ROOT / "data" / "bridge" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and not (dst.exists() and sha256(dst) == sha256(src)):
            dst.write_bytes(src.read_bytes())
    print(f"verified {len(ok)} files; failures: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
