#!/usr/bin/env python3
"""Package the (negative) Exp-2 final dots as a validated DO-NOT-SUBMIT artifact.

Uses the shared template writer (vendor/gems57/submission_writer.py), which
fails closed: it refuses non-finite/out-of-range input and re-validates the
bytes on disk.  The file name itself carries the verdict so it cannot be
mistaken for an approved submission.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import submission_writer, validate  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

NAME = "gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT"
NOTE = ("G76 piedmont-dipole logistic Exp2: HOLDOUT-DTI 0.0218 vs fair-H33 0.0927 "
        "(negative, below random). DO NOT SUBMIT.")


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    dots = np.load(ROOT / ".cache/exp2/final_dots.npy").astype(np.float32)
    pred = np.where(grid.footprint, dots, 0.0).astype(np.float32)
    out = ROOT / "docs/downloads" / f"{NAME}.tif"
    receipt = submission_writer.write_submission(
        out, pred, ROOT / "data/bridge/sample_submission.tif", grid.footprint,
        note=NOTE[:140], name=NAME[:140], catalogue=grid.catalogue,
        metadata={"verdict": "negative", "submit_recommended": False,
                  "lane": "G76 piedmont scarp-dipole (Exp2 logistic combiner)",
                  "holdout": "HOLDOUT-DTI (gems57-pooled-hide-v2, seed20, n=11321): "
                             "candidate 0.02180 [0.01448,0.03027] vs fair-H33 0.09269"})
    print("writer receipt:", receipt)
    v = validate.validate(out, footprint=grid.footprint, catalogue=grid.catalogue)
    validate.assert_submittable(v)
    print("independent validation passed:", v["all_checks_passed"], v["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
