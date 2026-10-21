"""Lane G76B model head: fold-honest HistGradientBoosting surface.

Pre-registered in docs/preregistration-g76b.md.  Frozen hyper-parameters; no
tuning after any holdout score is seen.  Training pools exclude the tested
region entirely (with an erosion collar), so no test pixel or its neighbours
contribute to training.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

HGB_PARAMS = dict(max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                  min_samples_leaf=40, l2_regularization=1.0,
                  early_stopping=False)


def fit_hgb(X: np.ndarray, pos_rows: np.ndarray, pool_rows: np.ndarray,
            seed: int, neg_ratio: int = 8, neg_cap: int = 300_000):
    """Fit on positives ``pos_rows`` vs negatives sampled from ``pool_rows``."""
    rng = np.random.default_rng(seed)
    pool_rows = np.setdiff1d(pool_rows, pos_rows, assume_unique=False)
    n_neg = min(neg_cap, neg_ratio * len(pos_rows), len(pool_rows))
    neg_rows = rng.choice(pool_rows, n_neg, replace=False)
    rows = np.r_[pos_rows, neg_rows]
    y = np.r_[np.ones(len(pos_rows), np.int8), np.zeros(n_neg, np.int8)]
    clf = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
    clf.fit(X[rows], y)
    receipt = {"model": "HistGradientBoostingClassifier", "params": HGB_PARAMS,
               "n_positives": int(len(pos_rows)), "n_negatives": int(n_neg),
               "seed": int(seed)}
    return clf, receipt


def predict_full(X: np.ndarray, clf, block: int = 400_000) -> np.ndarray:
    """Blockwise predict_proba over all rows (bounds transient memory)."""
    out = np.empty(X.shape[0], np.float32)
    for lo in range(0, X.shape[0], block):
        hi = min(X.shape[0], lo + block)
        out[lo:hi] = clf.predict_proba(X[lo:hi])[:, 1].astype(np.float32)
    return out


def vec_to_grid(vec: np.ndarray, valid: np.ndarray, fill: float = 0.0) -> np.ndarray:
    """Scatter a length-``n_valid`` vector back onto the full grid."""
    g = np.full(valid.shape, fill, np.float32)
    g[valid] = vec
    return g


def training_pool(valid: np.ndarray, exclude_region: np.ndarray,
                  erosion_px: int = 12) -> np.ndarray:
    """Rows of ``valid`` outside ``exclude_region`` (itself eroded away)."""
    dist = ndi.distance_transform_edt(~exclude_region)
    return valid & (~exclude_region) & (dist > erosion_px)
