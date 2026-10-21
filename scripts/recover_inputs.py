#!/usr/bin/env python3
"""Recover hash-pinned public bridge/tool bytes. Does not retrieve private caches.
Requires configured gh; refuses to overwrite bytes that differ from the manifest.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def recover(row):
    path = ROOT / row['path']
    expected = row['sha256']
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Refusing to overwrite modified {path}')
        return
    # URLs are pinned to immutable commits, not moving main branches.
    parts = row['source'].split('/blob/')
    repo = parts[0].removeprefix('https://github.com/')
    ref, remote = parts[1].split('/', 1)
    raw = subprocess.check_output(['gh','api',f'repos/{repo}/contents/{remote}?ref={ref}'])
    meta = json.loads(raw)
    content = meta.get('content')
    if not content:
        content = subprocess.check_output(['gh','api',f'repos/{repo}/git/blobs/{meta["sha"]}', '--jq','.content'])
    data = base64.b64decode(content)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Hash mismatch: {remote}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


if __name__ == '__main__':
    for row in json.loads((ROOT/'evidence/upstream/recovery.json').read_text()):
        recover(row)
    print('Pinned tools and bridge files recovered/verified; feature cache still requires placement.')
