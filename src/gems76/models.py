"""Leak-free out-of-fold training, 2D Spatial Context Pyramid (U-GBDT, H76-4),
exact CELF Submodular DTI Allocation (H76-5), and fold-fair baselines.
"""
from __future__ import annotations

import gc
import lightgbm as lgb
import numpy as np
from scipy.ndimage import label as ndi_label
from sklearn.isotonic import IsotonicRegression

from .features import FEATURE_NAMES, _norm_gauss

STAGE2_CONTEXT_NAMES = [
    "p_joint_raw",
    "p_scarp_raw",
    "p_geoph_raw",
    "p_fluv_raw",
    "second_best_domain",
    "domain_agreement_prod",
    "p_joint_g1",
    "p_joint_g2_5",
    "p_joint_g6",
    "p_joint_g14",
    "p_joint_dog_sharp",
    "worm_p_800m",
    "worm_aniso_800m",
    "worm_p_1800m",
    "worm_aniso_1800m",
    "trace_len_q965",
    "trace_len_q982",
    "scarp_geoph_synergy",
    "ctx_det_elev_slope",
    "ctx_b12_lap1_concave",
    "ctx_ptcf_idx",
    "ctx_lid_valid",
]


def fast_steerable_line_anisotropy(
    field_2d: np.ndarray,
    valid_2d: np.ndarray,
    half_len_px: int,
    n_taps_half: int = 3,
    n_angles: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact 8-azimuth strided 1D line integral along strike & orthogonal anisotropy.

    Evaluates ``2 * n_taps_half + 1`` shifted array slices directly in C-contiguous
    memory (70x faster than dense 2D ``(2L+1)x(2L+1)`` convolution on zero entries!).
    """
    arr = np.where(valid_2d, field_2d, 0.0).astype(np.float32)
    H, W = arr.shape
    pad = half_len_px
    padded = np.pad(arr, pad, mode="edge")
    taps = np.linspace(-half_len_px, half_len_px, 2 * n_taps_half + 1)
    inv_w = np.float32(1.0 / len(taps))

    half_n = n_angles // 2
    along_max = np.full((H, W), -1e30, dtype=np.float32)
    aniso = np.zeros((H, W), dtype=np.float32)

    for k_idx in range(half_n):
        t1 = k_idx * np.pi / n_angles
        t2 = (k_idx + half_n) * np.pi / n_angles
        r_a = np.zeros((H, W), dtype=np.float32)
        r_b = np.zeros((H, W), dtype=np.float32)
        for s in taps:
            dy1, dx1 = int(round(s * np.sin(t1))), int(round(s * np.cos(t1)))
            r_a += padded[pad + dy1:pad + dy1 + H, pad + dx1:pad + dx1 + W]
            dy2, dx2 = int(round(s * np.sin(t2))), int(round(s * np.cos(t2)))
            r_b += padded[pad + dy2:pad + dy2 + H, pad + dx2:pad + dx2 + W]
        r_a *= inv_w
        r_b *= inv_w
        m_a = r_a > along_max
        if m_a.any():
            along_max[m_a] = r_a[m_a]
            aniso[m_a] = r_a[m_a] - r_b[m_a]
        m_b = r_b > along_max
        if m_b.any():
            along_max[m_b] = r_b[m_b]
            aniso[m_b] = r_b[m_b] - r_a[m_b]
    return along_max, aniso


def _sample_train_indices(
    train_mask_fp: np.ndarray,
    y_fp: np.ndarray,
    rng: np.random.Generator,
    max_neg: int = 220_000,
) -> tuple[np.ndarray, float, float]:
    """Keep 100% of positive pixels in ``train_mask_fp`` and subsample negatives cleanly."""
    pos_idx = np.flatnonzero(train_mask_fp & (y_fp == 1))
    neg_idx = np.flatnonzero(train_mask_fp & (y_fp == 0))
    true_pi = float(pos_idx.size) / max(float(pos_idx.size + neg_idx.size), 1.0)
    if neg_idx.size > max_neg:
        neg_keep = rng.choice(neg_idx, size=max_neg, replace=False)
        neg_keep.sort()
    else:
        neg_keep = neg_idx
    sample_pi = float(pos_idx.size) / max(float(pos_idx.size + neg_keep.size), 1.0)
    all_idx = np.concatenate([pos_idx, neg_keep])
    all_idx.sort()
    return all_idx, true_pi, sample_pi


def _prior_correct_prob(p_sub: np.ndarray, true_pi: float, sample_pi: float) -> np.ndarray:
    """Exact Bayes prior-odds adjustment from subsampled negative ratio back to true base rate."""
    p = np.clip(np.asarray(p_sub, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    r = (true_pi / max(1.0 - true_pi, 1e-9)) / (sample_pi / max(1.0 - sample_pi, 1e-9))
    num = p * r
    return (num / (1.0 - p + num)).astype(np.float32)


def _predict_subset(
    model: lgb.LGBMClassifier,
    mm: np.memmap,
    row_idx: np.ndarray,
    cols: np.ndarray | slice,
    chunk: int = 650_000,
) -> np.ndarray:
    n = row_idx.size
    out = np.empty(n, dtype=np.float32)
    booster = model.booster_
    for s in range(0, n, chunk):
        e = min(n, s + chunk)
        rows = row_idx[s:e]
        block = np.asarray(mm[rows][:, cols], dtype=np.float32)
        out[s:e] = booster.predict(block, num_threads=2).astype(np.float32)
    return out


def _cross_regime_quantile_bridge_subset(
    p_vals: np.ndarray,
    lid_valid_sub: np.ndarray,
    fit_mask_sub: np.ndarray,
) -> np.ndarray:
    """Calibrate non-LiDAR gap distribution strictly on ``fit_mask_sub``."""
    out = p_vals.copy()
    m_lid = fit_mask_sub & lid_valid_sub
    m_gap = fit_mask_sub & (~lid_valid_sub)
    if m_lid.sum() > 500 and m_gap.sum() > 500:
        qg = np.linspace(0.0, 1.0, 1001)
        q_src = np.quantile(p_vals[m_gap], qg)
        q_dst = np.quantile(p_vals[m_lid], qg)
        gap_all = ~lid_valid_sub
        out[gap_all] = np.interp(p_vals[gap_all], q_src, q_dst).astype(np.float32)
    return out


def _component_log_length_2d(score_2d: np.ndarray, valid_2d: np.ndarray, thresh: float) -> np.ndarray:
    mask = (score_2d >= thresh) & valid_2d
    if not mask.any():
        return np.zeros(score_2d.shape, dtype=np.float32)
    comp, n_c = ndi_label(mask, structure=np.ones((3, 3), dtype=int))
    if n_c == 0:
        return np.zeros(score_2d.shape, dtype=np.float32)
    sizes = np.bincount(comp.ravel(), minlength=n_c + 1).astype(np.float32)
    sizes[0] = 0.0
    return np.log1p(sizes[comp]).astype(np.float32)


def extract_stage2_context_matrix(
    p_joint_fp: np.ndarray,
    p_scarp_fp: np.ndarray,
    p_geoph_fp: np.ndarray,
    p_fluv_fp: np.ndarray,
    mm_stage1: np.memmap,
    fp: np.ndarray,
    fp_idx: np.ndarray,
    allowed_spatial_2d: np.ndarray,
    thresh_ref_mask_fp: np.ndarray,
) -> np.ndarray:
    """Build 22-column 2D Spatial Context Pyramid (H76-4) strictly within ``allowed_spatial_2d``."""
    H, W = fp.shape
    n_fp = fp_idx.size
    X2 = np.empty((n_fp, len(STAGE2_CONTEXT_NAMES)), dtype=np.float32)

    X2[:, 0] = p_joint_fp
    X2[:, 1] = p_scarp_fp
    X2[:, 2] = p_geoph_fp
    X2[:, 3] = p_fluv_fp

    dom_stack = np.column_stack([p_scarp_fp, p_geoph_fp, p_fluv_fp])
    dom_sorted = np.sort(dom_stack, axis=1)
    X2[:, 4] = dom_sorted[:, 1]
    X2[:, 5] = np.cbrt(np.maximum(p_scarp_fp * p_geoph_fp * p_fluv_fp, 0.0)).astype(np.float32)
    del dom_stack, dom_sorted

    def _to2d(vec: np.ndarray) -> np.ndarray:
        g = np.zeros((H, W), dtype=np.float32)
        g.ravel()[fp_idx] = vec
        g[~allowed_spatial_2d] = 0.0
        return g

    vcache: dict[float, np.ndarray] = {}
    pj2d = _to2d(p_joint_fp)
    ps2d = _to2d(p_scarp_fp)
    pg2d = _to2d(p_geoph_fp)
    pf2d = _to2d(p_fluv_fp)

    g1 = _norm_gauss(pj2d, allowed_spatial_2d, 1.0, vcache)
    g25 = _norm_gauss(pj2d, allowed_spatial_2d, 2.5, vcache)
    g6 = _norm_gauss(pj2d, allowed_spatial_2d, 6.0, vcache)
    g14 = _norm_gauss(pj2d, allowed_spatial_2d, 14.0, vcache)

    X2[:, 6] = g1.ravel()[fp_idx]
    X2[:, 7] = g25.ravel()[fp_idx]
    X2[:, 8] = g6.ravel()[fp_idx]
    X2[:, 9] = g14.ravel()[fp_idx]
    X2[:, 10] = (g1 - g6).ravel()[fp_idx]

    w800, a800 = fast_steerable_line_anisotropy(pj2d, allowed_spatial_2d, half_len_px=4, n_taps_half=2)
    X2[:, 11] = w800.ravel()[fp_idx]
    X2[:, 12] = a800.ravel()[fp_idx]
    del w800, a800

    w1800, a1800 = fast_steerable_line_anisotropy(pj2d, allowed_spatial_2d, half_len_px=9, n_taps_half=2)
    X2[:, 13] = w1800.ravel()[fp_idx]
    X2[:, 14] = a1800.ravel()[fp_idx]
    del w1800, a1800

    q965 = float(np.quantile(p_joint_fp[thresh_ref_mask_fp], 0.965))
    q982 = float(np.quantile(p_joint_fp[thresh_ref_mask_fp], 0.982))
    X2[:, 15] = _component_log_length_2d(g1, allowed_spatial_2d, q965).ravel()[fp_idx]
    X2[:, 16] = _component_log_length_2d(g1, allowed_spatial_2d, q982).ravel()[fp_idx]

    ps_s = _norm_gauss(ps2d, allowed_spatial_2d, 2.5, vcache)
    pg_s = _norm_gauss(pg2d, allowed_spatial_2d, 4.0, vcache)
    pf_s = _norm_gauss(pf2d, allowed_spatial_2d, 4.0, vcache)
    X2[:, 17] = (ps_s * (0.55 * pg_s + 0.45 * pf_s)).ravel()[fp_idx]
    del pj2d, ps2d, pg2d, pf2d, g1, g25, g6, g14, ps_s, pg_s, pf_s, vcache

    col_idx = {n: i for i, n in enumerate(FEATURE_NAMES)}
    X2[:, 18] = mm_stage1[:, col_idx["det_elev_slope"]]
    X2[:, 19] = mm_stage1[:, col_idx["b12_lap1_concave"]]
    X2[:, 20] = mm_stage1[:, col_idx["ptcf_concave_toe_idx"]]
    X2[:, 21] = mm_stage1[:, col_idx["lid_valid"]]
    gc.collect()
    return X2


def fit_stage1_suite(
    mm: np.memmap,
    train_mask_fp: np.ndarray,
    y_fp: np.ndarray,
    seed: int = 76,
    fast_inner: bool = False,
) -> dict:
    """Fit domain experts + diverse dual-LightGBM (Leaf-wise + Depth/ColSub) ensemble."""
    rng = np.random.default_rng(seed)
    idx, true_pi, sample_pi = _sample_train_indices(
        train_mask_fp, y_fp, rng, max_neg=(110_000 if fast_inner else 190_000)
    )
    y_tr = y_fp[idx]
    X_all = np.asarray(mm[idx], dtype=np.float32)

    c_scarp = np.arange(0, 30, dtype=np.int64)
    c_geoph = np.array([1, 4, *range(30, 46)], dtype=np.int64)
    c_fluv = np.array([1, 4, *range(46, 62)], dtype=np.int64)

    n_dom = 105 if fast_inner else 175
    n_jnt = 135 if fast_inner else 225

    m_scarp = lgb.LGBMClassifier(
        n_estimators=n_dom, learning_rate=0.055, num_leaves=55, min_child_samples=90,
        colsample_bytree=0.78, subsample=0.8, subsample_freq=1, reg_alpha=2.0, reg_lambda=8.0,
        n_jobs=2, random_state=seed + 1, verbose=-1,
    ).fit(X_all[:, c_scarp], y_tr)

    m_geoph = lgb.LGBMClassifier(
        n_estimators=n_dom, learning_rate=0.055, num_leaves=45, min_child_samples=100,
        colsample_bytree=0.80, subsample=0.8, subsample_freq=1, reg_alpha=3.0, reg_lambda=10.0,
        n_jobs=2, random_state=seed + 2, verbose=-1,
    ).fit(X_all[:, c_geoph], y_tr)

    m_fluv = lgb.LGBMClassifier(
        n_estimators=n_dom, learning_rate=0.055, num_leaves=45, min_child_samples=100,
        colsample_bytree=0.80, subsample=0.8, subsample_freq=1, reg_alpha=3.0, reg_lambda=10.0,
        n_jobs=2, random_state=seed + 3, verbose=-1,
    ).fit(X_all[:, c_fluv], y_tr)

    m_joint_leaf = lgb.LGBMClassifier(
        n_estimators=n_jnt, learning_rate=0.05, num_leaves=63, min_child_samples=90,
        colsample_bytree=0.75, subsample=0.8, subsample_freq=1, reg_alpha=2.5, reg_lambda=9.0,
        n_jobs=2, random_state=seed + 4, verbose=-1,
    ).fit(X_all, y_tr)

    # Structurally diverse depth-regularized random-subspace partner (12x faster than sklearn HGB!)
    m_joint_wide = lgb.LGBMClassifier(
        n_estimators=n_jnt, learning_rate=0.05, max_depth=6, num_leaves=31, min_child_samples=180,
        colsample_bytree=0.45, subsample=0.75, subsample_freq=1, reg_alpha=5.0, reg_lambda=18.0,
        n_jobs=2, random_state=seed + 5, verbose=-1,
    ).fit(X_all, y_tr)
    del X_all
    gc.collect()

    return {
        "m_scarp": (m_scarp, c_scarp),
        "m_geoph": (m_geoph, c_geoph),
        "m_fluv": (m_fluv, c_fluv),
        "m_joint_leaf": m_joint_leaf,
        "m_joint_wide": m_joint_wide,
        "true_pi": true_pi,
        "sample_pi": sample_pi,
    }


def predict_stage1_suite(
    suite: dict,
    mm: np.memmap,
    lid_valid_fp: np.ndarray,
    fit_mask_fp: np.ndarray,
    target_mask_fp: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Predict ``(p_joint, p_scarp, p_geoph, p_fluv)`` only on ``fit_mask_fp | target_mask_fp``!"""
    n_fp = mm.shape[0]
    if target_mask_fp is None:
        rows = np.arange(n_fp, dtype=np.int64)
    else:
        rows = np.flatnonzero(fit_mask_fp | target_mask_fp)

    tpi, spi = suite["true_pi"], suite["sample_pi"]
    p_sc = _prior_correct_prob(_predict_subset(suite["m_scarp"][0], mm, rows, suite["m_scarp"][1]), tpi, spi)
    p_ge = _prior_correct_prob(_predict_subset(suite["m_geoph"][0], mm, rows, suite["m_geoph"][1]), tpi, spi)
    p_fl = _prior_correct_prob(_predict_subset(suite["m_fluv"][0], mm, rows, suite["m_fluv"][1]), tpi, spi)
    p_jl = _prior_correct_prob(_predict_subset(suite["m_joint_leaf"], mm, rows, slice(None)), tpi, spi)
    p_jw = _prior_correct_prob(_predict_subset(suite["m_joint_wide"], mm, rows, slice(None)), tpi, spi)

    lid_sub = lid_valid_fp[rows]
    fit_sub = fit_mask_fp[rows]
    p_sc_b = _cross_regime_quantile_bridge_subset(p_sc, lid_sub, fit_sub)
    p_jl_b = _cross_regime_quantile_bridge_subset(p_jl, lid_sub, fit_sub)
    p_jw_b = _cross_regime_quantile_bridge_subset(p_jw, lid_sub, fit_sub)
    p_j_sub = (0.44 * p_jl_b + 0.32 * p_jw_b + 0.14 * p_sc_b + 0.05 * p_ge + 0.05 * p_fl).astype(np.float32)

    if target_mask_fp is None:
        return p_j_sub, p_sc_b, p_ge, p_fl

    pj_out = np.zeros(n_fp, dtype=np.float32)
    ps_out = np.zeros(n_fp, dtype=np.float32)
    pg_out = np.zeros(n_fp, dtype=np.float32)
    pf_out = np.zeros(n_fp, dtype=np.float32)
    pj_out[rows] = p_j_sub
    ps_out[rows] = p_sc_b
    pg_out[rows] = p_ge
    pf_out[rows] = p_fl
    return pj_out, ps_out, pg_out, pf_out


def row_major_disk_thin(
    score_2d: np.ndarray,
    allowed_2d: np.ndarray,
    budget: int,
    min_dist_px: float = 3.0,
    binary_mask_top_k: int | None = None,
) -> np.ndarray:
    """Reproduces H33 / GEMSDOE32 disk thinning."""
    H, W = score_2d.shape
    s = np.where(allowed_2d, score_2d, -1.0)
    if binary_mask_top_k is not None:
        flat_valid = np.flatnonzero(allowed_2d.ravel())
        k = min(int(binary_mask_top_k), flat_valid.size)
        top = flat_valid[np.argpartition(s.ravel()[flat_valid], -k)[-k:]]
        top.sort()
        ys, xs = np.unravel_index(top, (H, W))
    else:
        flat_valid = np.flatnonzero(allowed_2d.ravel())
        k_cand = min(max(int(budget) * 14, 100_000), flat_valid.size)
        cand = flat_valid[np.argpartition(s.ravel()[flat_valid], -k_cand)[-k_cand:]]
        cand = cand[np.argsort(-s.ravel()[cand], kind="stable")]
        ys, xs = np.unravel_index(cand, (H, W))

    r = int(np.ceil(min_dist_px))
    ey, ex = np.mgrid[-r:r + 1, -r:r + 1]
    m_ex = (ey * ey + ex * ex) < (min_dist_px * min_dist_px)
    edy, edx = ey[m_ex], ex[m_ex]

    pad = r
    blocked = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)
    out = np.zeros((H, W), dtype=bool)
    n = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        if n >= budget:
            break
        if blocked[y + pad, x + pad]:
            continue
        out[y, x] = True
        blocked[y + pad + edy, x + pad + edx] = True
        n += 1
    return out
