"""Exp-2 combiner for Lane G76: logistic stack over the lane's own components.

Pre-registered in docs/preregistration-g76-amendment-exp2.md.  The feature list
is exactly the lane family from Exp 1 (LiDAR scarp-dipole components + the
non-LiDAR fallback + a missingness flag); no geophysics and no
catalogue-derived feature is admitted.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

FEATURE_NAMES = ["step_max", "dipole", "dipole_norm", "polarity", "coh100",
                 "ex_mean", "persisted", "fallback", "relief", "has_lidar"]


def assemble_features(lidar: dict, det_elev: np.ndarray, footprint: np.ndarray,
                      persisted: np.ndarray, fallback: np.ndarray) -> dict[str, np.ndarray]:
    fp = np.asarray(footprint, bool)
    has_lidar = fp & np.isfinite(lidar["valid"]) & (lidar["valid"] > 0)
    step = np.nan_to_num(lidar["step_max"])
    dip = np.sqrt(np.maximum(np.nan_to_num(lidar["lapneg_max"]), 0.0)
                  * np.maximum(np.nan_to_num(lidar["lappos_max"]), 0.0)).astype(np.float32)
    exm = np.nan_to_num(lidar["ex_mean"])
    face = np.maximum(np.nan_to_num(lidar["upface_max"]), np.nan_to_num(lidar["downface_max"]))
    cross = np.nan_to_num(lidar["cross_max"])
    relief = lidar["relief"].copy()
    med = float(np.nanmedian(relief[has_lidar])) if has_lidar.any() else 0.0
    relief = np.where(np.isfinite(relief), relief, med).astype(np.float32)
    feats = {
        "step_max": np.where(has_lidar, step, 0).astype(np.float32),
        "dipole": np.where(has_lidar, dip, 0).astype(np.float32),
        "dipole_norm": np.where(has_lidar, dip / (exm + 0.01), 0).astype(np.float32),
        "polarity": np.where(has_lidar, face / (face + cross + 1e-6), 0).astype(np.float32),
        "coh100": np.where(has_lidar, np.nan_to_num(lidar["coh100"]), 0).astype(np.float32),
        "ex_mean": np.where(has_lidar, exm, 0).astype(np.float32),
        "persisted": persisted.astype(np.float32),
        "fallback": fallback.astype(np.float32),
        "relief": relief,
        "has_lidar": has_lidar.astype(np.float32),
    }
    return feats


def _design(feats: dict[str, np.ndarray], idx: np.ndarray) -> np.ndarray:
    return np.column_stack([feats[n].ravel()[idx] for n in FEATURE_NAMES]).astype(np.float64)


def fit_surface(feats: dict[str, np.ndarray], positives_mask: np.ndarray,
                train_domain: np.ndarray, seed: int = 76000,
                neg_ratio: int = 10, neg_cap: int = 600_000) -> tuple[np.ndarray, dict]:
    """Fit the frozen logistic combiner; return (probability surface, receipt)."""
    pos_idx = np.flatnonzero(positives_mask & train_domain)
    neg_pool = np.flatnonzero(train_domain & ~positives_mask)
    rng = np.random.default_rng(seed)
    n_neg = min(neg_cap, neg_ratio * len(pos_idx), len(neg_pool))
    neg_idx = rng.choice(neg_pool, n_neg, replace=False)
    idx = np.r_[pos_idx, neg_idx]
    y = np.r_[np.ones(len(pos_idx)), np.zeros(n_neg)]
    X = _design(feats, idx)
    med = np.median(X, axis=0)
    iqr = np.subtract(*np.percentile(X, [75, 25], axis=0))
    iqr[iqr == 0] = 1.0
    Xs = (X - med) / iqr
    clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    clf.fit(Xs, y)
    # Predict in row blocks to bound memory.
    h, w = positives_mask.shape
    prob = np.zeros(h * w, np.float32)
    flat = {n: feats[n].ravel() for n in FEATURE_NAMES}
    block = 1_000_000
    for lo in range(0, h * w, block):
        hi = min(h * w, lo + block)
        Xb = np.column_stack([flat[n][lo:hi] for n in FEATURE_NAMES]).astype(np.float64)
        prob[lo:hi] = clf.predict_proba((Xb - med) / iqr)[:, 1].astype(np.float32)
    receipt = {
        "features": FEATURE_NAMES,
        "coefficients": {n: float(c) for n, c in zip(FEATURE_NAMES, clf.coef_[0])},
        "intercept": float(clf.intercept_[0]),
        "n_positives": int(len(pos_idx)), "n_negatives": int(n_neg),
        "standardization": "median/IQR over the training sample",
        "model": "sklearn LogisticRegression(C=1.0, lbfgs, max_iter=1000)",
    }
    return prob.reshape(h, w), receipt
