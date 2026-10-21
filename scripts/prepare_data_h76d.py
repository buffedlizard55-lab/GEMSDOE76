#!/usr/bin/env python3
"""Build & cache the 54-channel physical + geothermal + Verduzco-tilt + 1m/10m
tectonic-geomorphic feature stack (`gems76_static_v1.f32.mmap`) and run immediate
Rule 4 single-feature AUC leakage canaries (`<= 0.90` ceiling)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid, holdout
from gems76h.features import (
    _load_stress_table,
    build_or_load_static_stack,
    run_leakage_canary_audit,
)

DATA_DIR = ROOT / ".cache" / "data"
EXT_DIR = ROOT / ".cache" / "external"
FEAT_CACHE = ROOT / ".cache" / "features"


def main() -> None:
    t0 = time.time()
    g = grid.load_grid(DATA_DIR)
    print(f"[prepare_data] Loaded canonical Grid ({g.height}x{g.width}), footprint={int(g.footprint.sum()):,} px")

    stack = build_or_load_static_stack(DATA_DIR, EXT_DIR, FEAT_CACHE, g.footprint, force_rebuild=False)
    print(f"[prepare_data] Static stack ready in {time.time() - t0:.1f}s ({len(stack.feature_names)} physical features)")

    folds, _ = holdout.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12)
    stress_df = _load_stress_table(EXT_DIR)
    canary = run_leakage_canary_audit(stack, folds, g.footprint, stress_df, max_allowed_auc=0.90, seed=76)

    out_path = ROOT / "evidence" / "leakage_canary_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(canary, indent=2) + "\n")
    print(
        f"[prepare_data] Rule 4 Leakage Canary PASSED across all {canary['n_features_tested']} features! "
        f"Max symmetric AUC = {canary['max_symmetric_auc']:.5f} ({canary['top_feature']}) <= 0.90"
    )


if __name__ == "__main__":
    main()
