#!/usr/bin/env bash
# Official reproducible data acquisition script for DrivenData DOE GEMS (Competition #306)
# Official competition data page: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#
# Expected SHA-256 digests (verified bit-for-bit across all runs):
#   training_features.tif : 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5
#   existing_faults.tif   : 7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
#   sample_submission.tif : 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[1/2] Restoring & SHA-256 verifying official competition rasters and open federal geoscience layers..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/restore_data.py"

echo "[2/2] Building & verifying the 54-channel physical + geothermal feature stack..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/prepare_data.py"
