#!/usr/bin/env bash
# Verified competition & open federal geoscience data staging script for GEMSDOE76.
# DrivenData competition files require accepting competition rules at:
#   https://www.drivendata.org/competitions/306/competition-doe-gems/data/
set -euo pipefail

DEST_DIR="${1:-/tmp/gems_data}"
mkdir -p "${DEST_DIR}"

echo "Checking expected SHA-256 checksums in ${DEST_DIR} ..."
python3 - "${DEST_DIR}" << 'PY'
import hashlib, sys
from pathlib import Path

dest = Path(sys.argv[1])
expected = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif":   "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f1f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a4040454d35cbc",
}
for fname, prefix in expected.items():
    p = dest / fname
    if not p.is_file():
        print(f"MISSING: {p} -> download from https://www.drivendata.org/competitions/306/competition-doe-gems/data/")
        sys.exit(1)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    assert h.startswith(prefix[:24]), f"SHA-256 mismatch on {fname}: {h}"
    print(f"  OK {fname}: {h}")
PY
