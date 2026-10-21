"""Single-feature out-of-fold ROC AUC leakage canary (Gate 1).

Required BEFORE trusting any model result: computes exact ROC AUC on both
polarities ``max(AUC, 1 - AUC)`` across all active footprint cells (and per
spatial fold) for every feature. Any ``max(AUC, 1 - AUC) > 0.90`` raises
``RuntimeError`` immediately.
"""
from __future__ import annotations

import gc
import numpy as np


def _exact_auc_1d(y: np.ndarray, scores: np.ndarray) -> float:
    """Memory-lean exact ROC AUC with tie handling in O(N log N) using ~45 MB peak RAM."""
    if float(np.ptp(scores)) <= 1e-12:
        return 0.5
    n1 = float(y.sum(dtype=np.int64))
    n0 = float(y.size) - n1
    if n1 <= 0.0 or n0 <= 0.0:
        return 0.5
    order = np.argsort(scores, kind="quicksort")
    s_sorted = scores[order]
    y_sorted = y[order]
    del order
    # Exact tie handling via run boundaries
    diff = np.empty(y_sorted.size + 1, dtype=bool)
    diff[0] = True
    diff[-1] = True
    diff[1:-1] = s_sorted[1:] != s_sorted[:-1]
    del s_sorted
    idx = np.flatnonzero(diff)
    del diff
    csum_y = np.empty(y_sorted.size + 1, dtype=np.int64)
    csum_y[0] = 0
    np.cumsum(y_sorted, dtype=np.int64, out=csum_y[1:])
    del y_sorted
    pos_in_group = np.diff(csum_y[idx]).astype(np.float64)
    mid_ranks = 0.5 * (idx[:-1] + idx[1:] + 1.0)
    rank_sum_pos = float(np.dot(pos_in_group, mid_ranks))
    return float((rank_sum_pos - 0.5 * n1 * (n1 + 1.0)) / (n0 * n1))


def run_single_feature_auc_canary(
    mm: np.memmap,
    feature_names: list[str],
    y_fp: np.ndarray,
    quad_fp: np.ndarray,
    *,
    hard_limit: float = 0.90,
) -> dict:
    """Compute exact full-footprint and per-quadrant single-feature ROC AUC."""
    y = np.asarray(y_fp, dtype=np.uint8)
    quad_masks = [quad_fp == q for q in range(4)]
    y_quads = [y[m] for m in quad_masks]
    rows = []
    violators = []
    for col_idx, name in enumerate(feature_names):
        vals = np.array(mm[:, col_idx], dtype=np.float32, copy=True)
        if not np.isfinite(vals).all():
            raise ValueError(f"Non-finite values in feature {name}")
        auc_raw = _exact_auc_1d(y, vals)
        auc_sym = max(auc_raw, 1.0 - auc_raw)
        fold_aucs = []
        for qm, yq in zip(quad_masks, y_quads):
            fa = _exact_auc_1d(yq, vals[qm])
            fold_aucs.append(round(max(fa, 1.0 - fa), 5))
        del vals
        if col_idx % 8 == 7:
            gc.collect()
        entry = {
            "index": col_idx,
            "feature": name,
            "signed_auc": round(auc_raw, 5),
            "max_polarity_auc": round(auc_sym, 5),
            "fold_max_polarity_aucs": fold_aucs,
            "worst_fold_auc": max(fold_aucs),
            "leakage_flag": bool(auc_sym > hard_limit or max(fold_aucs) > hard_limit),
        }
        if entry["leakage_flag"]:
            violators.append(entry)
        rows.append(entry)

    rows_sorted = sorted(rows, key=lambda r: -r["max_polarity_auc"])
    report = {
        "gate": "single_feature_leakage_canary_v1",
        "hard_auc_limit": hard_limit,
        "n_pixels": int(y.size),
        "n_positives": int(y.sum()),
        "n_features_checked": len(feature_names),
        "max_observed_polarity_auc": rows_sorted[0]["max_polarity_auc"] if rows_sorted else 0.5,
        "max_observed_feature": rows_sorted[0]["feature"] if rows_sorted else None,
        "violator_count": len(violators),
        "passed": len(violators) == 0,
        "violators": violators,
        "features_ranked_by_signal": rows_sorted,
    }
    if violators:
        raise RuntimeError(f"LEAKAGE CANARY TRIPPED (> {hard_limit}): {violators}")
    return report
