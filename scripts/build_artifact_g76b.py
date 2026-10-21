#!/usr/bin/env python3
"""Package the (negative) G76B Exp-1 final dots as a validated DO-NOT-SUBMIT artifact.

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

NAME = "gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT"
NOTE = ("G76B patch-context HGB Exp1: HOLDOUT-DTI 0.0187 vs fair-H33 0.0961, below random. "
        "Negative. DO NOT SUBMIT.")


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    dots = np.load(ROOT / ".cache/g76b/final_dots.npy").astype(np.float32)
    pred = np.where(grid.footprint, dots, 0.0).astype(np.float32)
    out = ROOT / "evidence" / "lane-g76b" / f"{NAME}.tif"
    receipt = submission_writer.write_submission(
        out, pred, ROOT / "data/bridge/sample_submission.tif", grid.footprint,
        note=NOTE[:140], name=NAME[:140], catalogue=grid.catalogue,
        metadata={"verdict": "negative", "submit_recommended": False,
                  "lane": "G76B patch-context corroboration (Exp1 HGB head)",
                  "holdout": "HOLDOUT-DTI (gems57-pooled-hide-v2, seed20, n=11321): "
                             "candidate 0.01870 [0.01089,0.02788] vs fair-H33 0.09611 "
                             "[0.08340,0.10930]; below random 0.03407"})
    print("writer receipt:", receipt)
    v = validate.validate(out, footprint=grid.footprint, catalogue=grid.catalogue)
    validate.assert_submittable(v)
    print("independent validation passed:", v["all_checks_passed"], v["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
