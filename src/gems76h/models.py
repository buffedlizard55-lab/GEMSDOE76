"""Memory-bounded (`< 1.25 GB` RSS) & CPU-vectorized (`~4 min` total) execution of the
3 preregistered experiments (`E76-1`, `E76-2`, `E76-3`) for Lane H76 (`GEMSDOE76`)."""
from __future__ import annotations

import gc
import heapq
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from gems76h.features import (
    FOLD_MECH_NAMES,
    StaticStack,
    compute_fold_mechanics_2d,
    fill_axial_context_valid,
)

# Exact 25-cell (`5 x 5`) Euclidean < 300 m (`< 3 px`) positive triangular kernel
KERNEL_300M: Tuple[Tuple[int, int, float], ...] = tuple(
    (dy, dx, float(1.0 - np.hypot(dy, dx) / 3.0))
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if np.hypot(dy, dx) < 3.0 - 1e-9
)
assert len(KERNEL_300M) == 25


def _rank01(values: np.ndarray) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    n = v.size
    if n == 0:
        return np.empty(0, dtype=np.float32)
    if np.ptp(v) == 0.0:
        return np.full(n, 0.5, dtype=np.float32)
    return (rankdata(v, method="average") / float(n)).astype(np.float32)


def _logit(p: np.ndarray) -> np.ndarray:
    c = np.clip(p, 1e-5, 1.0 - 1e-5)
    return np.log(c / (1.0 - c)).astype(np.float32)


def sample_terrain_balanced_negatives(
    neg_pool_flat: np.ndarray,
    pos_flat: np.ndarray,
    slope10_flat: np.ndarray,
    n_neg_total: int,
    hard_frac: float = 0.35,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng(76)
    n_neg_total = min(int(n_neg_total), int(neg_pool_flat.size))
    n_hard = int(round(n_neg_total * hard_frac))
    n_unif = n_neg_total - n_hard

    unif = rng.choice(neg_pool_flat, size=n_unif, replace=False)
    slp_pool = slope10_flat[neg_pool_flat]
    p70 = float(np.percentile(slope10_flat[pos_flat], 68.0))
    steep_cand = neg_pool_flat[slp_pool >= p70]
    if steep_cand.size >= n_hard:
        hard = rng.choice(steep_cand, size=n_hard, replace=False)
    else:
        hard = rng.choice(neg_pool_flat, size=n_hard, replace=False)
    return np.unique(np.concatenate([unif, hard]))


def fit_hgb_fast(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    seed: int,
    max_iter: int = 180,
    max_leaf_nodes: int = 47,
    min_samples_leaf: int = 100,
    l2_regularization: float = 5.0,
) -> HistGradientBoostingClassifier:
    clf = HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=max_iter,
        max_leaf_nodes=max_leaf_nodes,
        min_samples_leaf=min_samples_leaf,
        l2_regularization=l2_regularization,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=14,
        random_state=seed,
    )
    clf.fit(X_tr, y_tr)
    return clf


def predict_single_chunked(
    model: HistGradientBoostingClassifier,
    X_source: np.ndarray,
    cols: Sequence[int] | None = None,
    chunk_size: int = 750_000,
) -> np.ndarray:
    n = X_source.shape[0]
    out = np.zeros(n, dtype=np.float32)
    for start in range(0, n, chunk_size):
        end = min(n, start + chunk_size)
        sub = (
            np.asarray(X_source[start:end, cols], dtype=np.float32)
            if cols is not None
            else np.asarray(X_source[start:end], dtype=np.float32)
        )
        out[start:end] = model.predict_proba(sub)[:, 1].astype(np.float32)
    return out


def calibrate_terrain_prevalence(
    prob_2d: np.ndarray,
    slope10_2d: np.ndarray,
    train_pos_mask: np.ndarray,
    train_domain_mask: np.ndarray,
    fp: np.ndarray,
    blend: float = 0.65,
) -> np.ndarray:
    out = np.where(fp & np.isfinite(prob_2d), prob_2d, 0.0).astype(np.float32)
    slp_dom = slope10_2d[train_domain_mask]
    edges = np.quantile(slp_dom, np.linspace(0.0, 1.0, 9))
    edges[0] = -1e9
    edges[-1] = 1e9

    global_prev = float(np.mean(train_pos_mask[train_domain_mask])) + 1e-8
    global_p99 = float(np.percentile(out[train_domain_mask], 99.0)) + 1e-8

    calibrated = out.copy()
    for b in range(8):
        in_bin_tr = train_domain_mask & (slope10_2d >= edges[b]) & (slope10_2d < edges[b + 1])
        in_bin_all = fp & (slope10_2d >= edges[b]) & (slope10_2d < edges[b + 1])
        if not np.any(in_bin_tr) or not np.any(in_bin_all):
            continue
        bin_prev = float(np.mean(train_pos_mask[in_bin_tr])) + 1e-8
        bin_p99 = float(np.percentile(out[in_bin_tr], 99.0)) + 1e-8
        target_ratio = np.clip(bin_prev / global_prev, 0.55, 1.45)
        current_ratio = bin_p99 / global_p99
        mult = float((target_ratio / max(current_ratio, 1e-4)) ** blend)
        calibrated[in_bin_all] = out[in_bin_all] * mult

    mx = float(np.max(calibrated[fp]))
    if mx > 0.0:
        calibrated = np.clip(calibrated / max(mx, 1.0), 0.0, 1.0)
    return calibrated.astype(np.float32)


def submodular_pack_300m(
    surface_2d: np.ndarray,
    allowed_2d: np.ndarray,
    target_n: int = 37654,
    support_quantile: float = 0.90,
    gamma: float = 2.0,
    max_candidates: int = 320_000,
) -> Tuple[np.ndarray, int]:
    """Exact unblurred 300 m triangular-kernel lazy-greedy submodular dot packer (Minoux 1978)."""
    h, w = surface_2d.shape
    allow = np.asarray(allowed_2d, dtype=bool)
    vals = surface_2d[allow]
    if vals.size < target_n:
        target_n = int(vals.size)

    ranks = _rank01(vals)
    pos = np.clip((ranks - support_quantile) / max(1.0 - support_quantile, 1e-6), 0.0, 1.0)
    weights_allow = (pos ** gamma).astype(np.float32) + (1e-5 * ranks).astype(np.float32)

    pad = 2
    hp, wp = h + 2 * pad, w + 2 * pad
    w_pad = np.zeros((hp, wp), dtype=np.float32)
    ay, ax = np.nonzero(allow)
    w_pad[ay + pad, ax + pad] = weights_allow

    g0 = np.zeros((h, w), dtype=np.float32)
    for dy, dx, k in KERNEL_300M:
        g0 += k * w_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w]

    cand_scores = g0[allow]
    if cand_scores.size > max_candidates:
        part = np.argpartition(cand_scores, -max_candidates)[-max_candidates:]
        part = part[np.argsort(cand_scores[part], kind="mergesort")[::-1]]
    else:
        part = np.argsort(cand_scores, kind="mergesort")[::-1]

    cy = (ay[part] + pad).astype(np.int32)
    cx = (ax[part] + pad).astype(np.int32)
    flat_idx = cy * wp + cx
    init_gains = cand_scores[part]

    heap = [(-float(init_gains[i]), int(flat_idx[i])) for i in range(flat_idx.size)]
    heapq.heapify(heap)

    w_list = w_pad.ravel().tolist()
    cov_list = [0.0] * (hp * wp)
    off_k = tuple((dy * wp + dx, k) for dy, dx, k in KERNEL_300M)

    dots = np.zeros((h, w), dtype=bool)
    picked = 0
    pop = heapq.heappop
    push = heapq.heappush

    while picked < target_n and heap:
        _, idx = pop(heap)
        gain = 0.0
        for off, k in off_k:
            j = idx + off
            wj = w_list[j]
            if wj > 0.0:
                rem = k - cov_list[j]
                if rem > 0.0:
                    gain += wj * rem
        if not heap or gain >= -heap[0][0] - 1e-12:
            y = idx // wp - pad
            x = idx % wp - pad
            if not dots[y, x]:
                dots[y, x] = True
                for off, k in off_k:
                    j = idx + off
                    if k > cov_list[j]:
                        cov_list[j] = k
                picked += 1
        elif gain > 0.0:
            push(heap, (-gain, idx))

    return dots, picked


def build_stage1_context_matrix(
    p_phys: np.ndarray,
    p_scarp: np.ndarray,
    p_geotherm: np.ndarray,
    p_subsurf: np.ndarray,
    fp: np.ndarray,
    valid_idx: np.ndarray,
) -> np.ndarray:
    """Compact `(len(valid_idx), 20)` `float16` Stage-1 axial-ridge + corroboration matrix."""
    out = np.empty((valid_idx.size, 20), dtype=np.float16)
    out[:, 0] = _logit(p_phys).ravel()[valid_idx].astype(np.float16)
    out[:, 1] = _logit(p_scarp).ravel()[valid_idx].astype(np.float16)
    out[:, 2] = _logit(p_geotherm).ravel()[valid_idx].astype(np.float16)
    out[:, 3] = _logit(p_subsurf).ravel()[valid_idx].astype(np.float16)

    fill_axial_context_valid(out, 4, p_phys, fp, valid_idx)
    blind_blend = (0.55 * p_geotherm + 0.45 * p_subsurf).astype(np.float32)
    fill_axial_context_valid(out, 10, blind_blend, fp, valid_idx)
    del blind_blend
    gc.collect()

    q_s = _rank01(p_scarp[fp])
    q_g = _rank01(p_geotherm[fp])
    q_u = _rank01(p_subsurf[fp])
    tri = np.sort(np.column_stack([q_s, q_g, q_u]), axis=1)
    out[:, 16] = tri[:, 1].astype(np.float16)
    out[:, 17] = np.cbrt(np.maximum(q_s * q_g * q_u, 0.0)).astype(np.float16)
    out[:, 18] = np.sqrt(np.maximum(q_g * q_u, 0.0)).astype(np.float16)
    out[:, 19] = np.sqrt(np.maximum(q_s * np.maximum(q_g, q_u), 0.0)).astype(np.float16)
    del q_s, q_g, q_u, tri
    gc.collect()
    return out


def build_meta_features_from_parts(s1_part: np.ndarray, mech_part: np.ndarray) -> np.ndarray:
    p_logit = s1_part[:, 0]
    ax_r9 = s1_part[:, 4]
    ax_r21 = s1_part[:, 5]
    blind_r21 = s1_part[:, 11]
    q_sec = s1_part[:, 16]

    ray_s = mech_part[:, 0]
    ray_l = mech_part[:, 1]
    bridge = mech_part[:, 3]
    d_cap = mech_part[:, 5]
    deficit = mech_part[:, 7]
    stress = mech_part[:, 8]

    inter = np.column_stack(
        [
            np.maximum(ax_r9, 0.0) * ray_s,
            np.maximum(ax_r21, 0.0) * (ray_l + bridge),
            np.maximum(blind_r21, 0.0) * deficit,
            q_sec * np.exp(-d_cap / 14.0),
            q_sec * (bridge + 0.5 * ray_s),
            (p_logit + 4.0) * stress,
        ]
    ).astype(np.float32)
    return np.hstack([s1_part, mech_part, inter]).astype(np.float32)


def _build_self_masked_training_dataset(
    stack: StaticStack,
    inv_map: np.ndarray,
    vis_train_domain: np.ndarray,
    full_vis_fold: np.ndarray,
    fp: np.ndarray,
    stress_df: pd.DataFrame | None,
    stage1_context_valid: np.ndarray,
    n_subfolds: int = 3,
    seed: int = 7600,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    vis_in_dom = full_vis_fold & vis_train_domain
    comp_lbl, n_comp = ndi.label(vis_in_dom, structure=np.ones((3, 3), dtype=int))
    comp_ids = np.arange(1, n_comp + 1)
    rng.shuffle(comp_ids)
    buckets = np.array_split(comp_ids, n_subfolds)

    slp_flat = stack.slope10_full.ravel()
    X_base_list = []
    X_meta_list = []
    y_list = []

    for cid_part in buckets:
        hide_mask = np.isin(comp_lbl, cid_part)
        if not np.any(hide_mask):
            continue
        hide_buf = ndi.binary_dilation(hide_mask, iterations=3)
        sub_vis = full_vis_fold & (~hide_buf)
        d_sub = ndi.distance_transform_edt(~sub_vis)

        pos_mask = hide_mask & vis_train_domain & (d_sub > 2.15)
        pos_flat = np.flatnonzero(pos_mask)
        if pos_flat.size < 50:
            continue

        neg_mask = vis_train_domain & (~full_vis_fold) & (d_sub > 2.15)
        neg_pool = np.flatnonzero(neg_mask)
        neg_flat = sample_terrain_balanced_negatives(
            neg_pool, pos_flat, slp_flat, n_neg_total=4 * int(pos_flat.size), hard_frac=0.35, rng=rng
        )
        del d_sub

        mech_full = compute_fold_mechanics_2d(
            sub_vis, fp, stack.best_strike_full, stack.tect_bg_full, stress_df
        ).reshape(-1, len(FOLD_MECH_NAMES))
        samp_flat = np.concatenate([pos_flat, neg_flat])
        m_part = mech_full[samp_flat].copy()
        del mech_full
        gc.collect()

        y_sub = np.concatenate(
            [np.ones(pos_flat.size, dtype=np.int8), np.zeros(neg_flat.size, dtype=np.int8)]
        )
        rows = inv_map[samp_flat]
        Xb = np.hstack([np.asarray(stack.X_mmap[rows], dtype=np.float32), m_part])
        Xm = build_meta_features_from_parts(
            np.asarray(stage1_context_valid[rows], dtype=np.float32), m_part
        )
        X_base_list.append(Xb)
        X_meta_list.append(Xm)
        y_list.append(y_sub)

    return np.vstack(X_base_list), np.vstack(X_meta_list), np.concatenate(y_list)


def run_three_preregistered_experiments(
    stack: StaticStack,
    folds: List[dict],
    quad: np.ndarray,
    cat_full: np.ndarray,
    fp: np.ndarray,
    stress_df: pd.DataFrame | None,
    cache_dir: Path | None = None,
    seed: int = 76,
) -> dict:
    s2_ckpt = Path(cache_dir) / "stage2_surfaces_v1.npz" if cache_dir is not None else None
    if s2_ckpt is not None and s2_ckpt.exists():
        print("  [Stage 1+2 Cache] Loading pre-computed Stage 1 + Stage 2 surfaces...")
        z2 = np.load(s2_ckpt)
        return {k: z2[k] for k in z2.files}

    H, W = fp.shape
    inv_map = np.full(fp.size, -1, dtype=np.int64)
    inv_map[stack.valid_idx] = np.arange(stack.valid_idx.size, dtype=np.int64)
    slp_flat = stack.slope10_full.ravel()

    any_hidden = np.zeros((H, W), dtype=bool)
    for f in folds:
        any_hidden |= f["hidden_all"]
    hidden_guard = ndi.binary_dilation(any_hidden, iterations=6)

    t0 = time.time()
    rng = np.random.default_rng(seed)
    s1_ckpt = (cache_dir / "stage1_surfaces_v1.npz") if cache_dir is not None else None

    if s1_ckpt is not None and s1_ckpt.exists():
        z = np.load(s1_ckpt)
        p_phys_oof = z["p_phys_oof"]
        p_scarp_oof = z["p_scarp_oof"]
        p_geoth_oof = z["p_geoth_oof"]
        p_subsf_oof = z["p_subsf_oof"]
        p_phys_prod = z["p_phys_prod"]
        p_scarp_prod = z["p_scarp_prod"]
        p_geoth_prod = z["p_geoth_prod"]
        p_subsf_prod = z["p_subsf_prod"]
        e1_cal_oof = z["e1_cal_oof"]
        e1_prod_surface = z["e1_prod_surface"]
        print(f"  [Stage 1] Loaded checkpointed OOF + Prod physical surfaces in {time.time() - t0:.1f}s")
    else:
        p_phys_oof = np.zeros((H, W), dtype=np.float32)
        p_scarp_oof = np.zeros((H, W), dtype=np.float32)
        p_geoth_oof = np.zeros((H, W), dtype=np.float32)
        p_subsf_oof = np.zeros((H, W), dtype=np.float32)
        e1_cal_oof = np.zeros((H, W), dtype=np.float32)

        for k, f in enumerate(folds):
            test_q = (quad == k) & fp
            q_buf = ndi.binary_dilation(test_q, iterations=24)
            tr_dom = fp & (~q_buf) & (~hidden_guard)

            pos_flat = np.flatnonzero(f["visible"] & tr_dom)
            d_vis_tr = ndi.distance_transform_edt(~(f["visible"] & tr_dom))
            neg_pool = np.flatnonzero(tr_dom & (~f["visible"]) & (d_vis_tr > 2.5))
            del d_vis_tr
            neg_flat = sample_terrain_balanced_negatives(
                neg_pool, pos_flat, slp_flat, n_neg_total=min(130_000, 3 * int(pos_flat.size)), hard_frac=0.35, rng=rng
            )
            samp = np.concatenate([pos_flat, neg_flat])
            y_tr = np.concatenate(
                [np.ones(pos_flat.size, dtype=np.int8), np.zeros(neg_flat.size, dtype=np.int8)]
            )
            X_tr = np.asarray(stack.X_mmap[inv_map[samp]], dtype=np.float32)

            m_phys = fit_hgb_fast(X_tr, y_tr, seed=seed + 10 * k, max_iter=175, max_leaf_nodes=47)
            m_scarp = fit_hgb_fast(X_tr[:, 0:20], y_tr, seed=seed + 10 * k + 1, max_iter=150, max_leaf_nodes=35)
            m_geoth = fit_hgb_fast(X_tr[:, 20:38], y_tr, seed=seed + 10 * k + 2, max_iter=150, max_leaf_nodes=35)
            m_subsf = fit_hgb_fast(X_tr[:, 38:54], y_tr, seed=seed + 10 * k + 3, max_iter=150, max_leaf_nodes=35)
            del X_tr

            tq_flat = np.flatnonzero(test_q)
            X_tq = np.asarray(stack.X_mmap[inv_map[tq_flat]], dtype=np.float32)
            p_phys_oof.ravel()[tq_flat] = m_phys.predict_proba(X_tq)[:, 1].astype(np.float32)
            p_scarp_oof.ravel()[tq_flat] = m_scarp.predict_proba(X_tq[:, 0:20])[:, 1].astype(np.float32)
            p_geoth_oof.ravel()[tq_flat] = m_geoth.predict_proba(X_tq[:, 20:38])[:, 1].astype(np.float32)
            p_subsf_oof.ravel()[tq_flat] = m_subsf.predict_proba(X_tq[:, 38:54])[:, 1].astype(np.float32)
            del X_tq, m_phys, m_scarp, m_geoth, m_subsf
            gc.collect()

            cal_tmp = calibrate_terrain_prevalence(p_phys_oof, stack.slope10_full, f["visible"], tr_dom, fp)
            e1_cal_oof[test_q] = cal_tmp[test_q]
            print(f"  [Stage 1 Fold {f['name']}] OOF complete ({time.time() - t0:.1f}s)")

        # Fit single clean full-footprint physical expert quartet on `cat_full` (~55s total!)
        pos_all = np.flatnonzero(cat_full & fp)
        d_cat = ndi.distance_transform_edt(~cat_full)
        neg_pool_all = np.flatnonzero(fp & (~cat_full) & (d_cat > 2.5))
        del d_cat
        neg_all = sample_terrain_balanced_negatives(
            neg_pool_all, pos_all, slp_flat, n_neg_total=210_000, hard_frac=0.35, rng=rng
        )
        samp_all = np.concatenate([pos_all, neg_all])
        y_all = np.concatenate(
            [np.ones(pos_all.size, dtype=np.int8), np.zeros(neg_all.size, dtype=np.int8)]
        )
        X_all_tr = np.asarray(stack.X_mmap[inv_map[samp_all]], dtype=np.float32)
        mp_phys = fit_hgb_fast(X_all_tr, y_all, seed=seed + 90, max_iter=185, max_leaf_nodes=47)
        mp_scarp = fit_hgb_fast(X_all_tr[:, 0:20], y_all, seed=seed + 91, max_iter=155, max_leaf_nodes=35)
        mp_geoth = fit_hgb_fast(X_all_tr[:, 20:38], y_all, seed=seed + 92, max_iter=155, max_leaf_nodes=35)
        mp_subsf = fit_hgb_fast(X_all_tr[:, 38:54], y_all, seed=seed + 93, max_iter=155, max_leaf_nodes=35)
        del X_all_tr
        gc.collect()

        p_phys_prod = np.zeros((H, W), dtype=np.float32)
        p_scarp_prod = np.zeros((H, W), dtype=np.float32)
        p_geoth_prod = np.zeros((H, W), dtype=np.float32)
        p_subsf_prod = np.zeros((H, W), dtype=np.float32)
        p_phys_prod.ravel()[stack.valid_idx] = predict_single_chunked(mp_phys, stack.X_mmap)
        p_scarp_prod.ravel()[stack.valid_idx] = predict_single_chunked(mp_scarp, stack.X_mmap, cols=range(0, 20))
        p_geoth_prod.ravel()[stack.valid_idx] = predict_single_chunked(mp_geoth, stack.X_mmap, cols=range(20, 38))
        p_subsf_prod.ravel()[stack.valid_idx] = predict_single_chunked(mp_subsf, stack.X_mmap, cols=range(38, 54))
        del mp_phys, mp_scarp, mp_geoth, mp_subsf
        gc.collect()

        e1_prod_surface = calibrate_terrain_prevalence(
            p_phys_prod, stack.slope10_full, cat_full, fp, fp
        )
        if s1_ckpt is not None:
            np.savez(
                s1_ckpt,
                p_phys_oof=p_phys_oof,
                p_scarp_oof=p_scarp_oof,
                p_geoth_oof=p_geoth_oof,
                p_subsf_oof=p_subsf_oof,
                p_phys_prod=p_phys_prod,
                p_scarp_prod=p_scarp_prod,
                p_geoth_prod=p_geoth_prod,
                p_subsf_prod=p_subsf_prod,
                e1_cal_oof=e1_cal_oof,
                e1_prod_surface=e1_prod_surface,
            )
        print(f"  [Stage 1 Complete] Saved OOF + Prod physical surfaces ({time.time() - t0:.1f}s)")

    # Build OOF Stage-1 context matrix (`206 MB` `float16`) and immediately free OOF expert maps!
    s1_ctx_oof = build_stage1_context_matrix(
        p_phys_oof, p_scarp_oof, p_geoth_oof, p_subsf_oof, fp, stack.valid_idx
    )
    del p_phys_oof, p_scarp_oof, p_geoth_oof, p_subsf_oof
    gc.collect()
    print(f"  [Axial Context OOF] Ready ({time.time() - t0:.1f}s)")

    # ── STAGE 2: Self-Masked Continuation (`E76-2`) & Multi-Expert Axial Stacker (`E76-3`) ──
    e2_oof_raw = np.zeros((H, W), dtype=np.float32)
    e3_oof_raw = np.zeros((H, W), dtype=np.float32)
    e2_cal_oof = np.zeros((H, W), dtype=np.float32)
    e3_cal_oof = np.zeros((H, W), dtype=np.float32)

    m_e2_folds = []
    m_e3_folds = []

    for k, f in enumerate(folds):
        test_q = (quad == k) & fp
        q_buf = ndi.binary_dilation(test_q, iterations=24)
        tr_dom = fp & (~q_buf) & (~hidden_guard)

        Xb_tr, Xm_tr, y_tr = _build_self_masked_training_dataset(
            stack=stack,
            inv_map=inv_map,
            vis_train_domain=tr_dom,
            full_vis_fold=f["visible"],
            fp=fp,
            stress_df=stress_df,
            stage1_context_valid=s1_ctx_oof,
            n_subfolds=3,
            seed=seed + 500 + 37 * k,
        )

        m_e2 = fit_hgb_fast(Xb_tr, y_tr, seed=seed + 200 + 10 * k, max_iter=195, max_leaf_nodes=55)
        del Xb_tr

        m_e3_hgb = fit_hgb_fast(
            Xm_tr, y_tr, seed=seed + 300 + 10 * k, max_iter=195, max_leaf_nodes=39, min_samples_leaf=120, l2_regularization=6.0
        )
        Xm_tr_clean = np.nan_to_num(Xm_tr, nan=0.0)
        mlp = make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=(48, 24),
                alpha=0.5,
                max_iter=35,
                early_stopping=True,
                random_state=seed + 400 + k,
            ),
        )
        mlp.fit(Xm_tr_clean, y_tr)
        lr_cal = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=200))
        lr_cal.fit(Xm_tr_clean, y_tr)
        del Xm_tr, Xm_tr_clean, y_tr
        gc.collect()

        m_e2_folds.append(m_e2)
        m_e3_folds.append((m_e3_hgb, mlp, lr_cal))

        # Predict strictly on `test_q` (~1.29M rows -> ~3.5s per fold!) using `f["visible"]`
        tq_flat = np.flatnonzero(test_q)
        tq_rows = inv_map[tq_flat]
        mech_fold_q = compute_fold_mechanics_2d(
            f["visible"], fp, stack.best_strike_full, stack.tect_bg_full, stress_df
        ).reshape(-1, len(FOLD_MECH_NAMES))[tq_flat]

        xb_q = np.hstack([np.asarray(stack.X_mmap[tq_rows], dtype=np.float32), mech_fold_q])
        p2_q = m_e2.predict_proba(xb_q)[:, 1].astype(np.float32)
        del xb_q

        xm_q = build_meta_features_from_parts(
            np.asarray(s1_ctx_oof[tq_rows], dtype=np.float32), mech_fold_q
        )
        del mech_fold_q
        xm_q0 = np.nan_to_num(xm_q, nan=0.0)
        p3_q = (
            0.68 * m_e3_hgb.predict_proba(xm_q)[:, 1]
            + 0.22 * mlp.predict_proba(xm_q0)[:, 1]
            + 0.10 * lr_cal.predict_proba(xm_q0)[:, 1]
        ).astype(np.float32)
        del xm_q, xm_q0
        gc.collect()

        e2_oof_raw.ravel()[tq_flat] = p2_q
        e3_oof_raw.ravel()[tq_flat] = p3_q
        e2_cal_oof[test_q] = calibrate_terrain_prevalence(
            e2_oof_raw, stack.slope10_full, f["visible"], tr_dom, fp, blend=0.50
        )[test_q]
        e3_cal_oof[test_q] = calibrate_terrain_prevalence(
            e3_oof_raw, stack.slope10_full, f["visible"], tr_dom, fp, blend=0.50
        )[test_q]
        print(f"  [Stage 2 Fold {f['name']}] E76-2 + E76-3 OOF complete ({time.time() - t0:.1f}s)")

    # Free OOF axial matrix BEFORE computing Production axial matrix (`peak RSS stays < 1.1 GB`!)
    del s1_ctx_oof, e2_oof_raw, e3_oof_raw
    gc.collect()

    s1_ctx_prod = build_stage1_context_matrix(
        p_phys_prod, p_scarp_prod, p_geoth_prod, p_subsf_prod, fp, stack.valid_idx
    )
    mech_prod_valid = compute_fold_mechanics_2d(
        cat_full, fp, stack.best_strike_full, stack.tect_bg_full, stress_df
    ).reshape(-1, len(FOLD_MECH_NAMES))[stack.valid_idx].astype(np.float16)
    gc.collect()

    n_val = stack.valid_idx.size
    e2_prod_val = np.zeros(n_val, dtype=np.float64)
    e3_prod_val = np.zeros(n_val, dtype=np.float64)
    chunk = 650_000
    for st in range(0, n_val, chunk):
        en = min(n_val, st + chunk)
        mp_chunk = np.asarray(mech_prod_valid[st:en], dtype=np.float32)
        xb_p = np.hstack([np.asarray(stack.X_mmap[st:en], dtype=np.float32), mp_chunk])
        for m_e2 in m_e2_folds:
            e2_prod_val[st:en] += 0.25 * m_e2.predict_proba(xb_p)[:, 1]
        del xb_p

        xm_p = build_meta_features_from_parts(
            np.asarray(s1_ctx_prod[st:en], dtype=np.float32), mp_chunk
        )
        xm_p0 = np.nan_to_num(xm_p, nan=0.0)
        for m_hgb, m_mlp, m_lr in m_e3_folds:
            e3_prod_val[st:en] += 0.25 * (
                0.68 * m_hgb.predict_proba(xm_p)[:, 1]
                + 0.22 * m_mlp.predict_proba(xm_p0)[:, 1]
                + 0.10 * m_lr.predict_proba(xm_p0)[:, 1]
            )
        del xm_p, xm_p0, mp_chunk
    del s1_ctx_prod, mech_prod_valid
    gc.collect()

    e2_prod_raw = np.zeros((H, W), dtype=np.float32)
    e3_prod_raw = np.zeros((H, W), dtype=np.float32)
    e2_prod_raw.ravel()[stack.valid_idx] = e2_prod_val.astype(np.float32)
    e3_prod_raw.ravel()[stack.valid_idx] = e3_prod_val.astype(np.float32)
    del e2_prod_val, e3_prod_val

    e2_prod_surface = calibrate_terrain_prevalence(
        e2_prod_raw, stack.slope10_full, cat_full, fp, fp, blend=0.50
    )
    e3_prod_surface = calibrate_terrain_prevalence(
        e3_prod_raw, stack.slope10_full, cat_full, fp, fp, blend=0.50
    )
    del e2_prod_raw, e3_prod_raw, p_scarp_prod, p_geoth_prod, p_subsf_prod, inv_map
    gc.collect()
    out_dict = {
        "e1_oof_surface": e1_cal_oof,
        "e1_prod_surface": e1_prod_surface,
        "e2_oof_surface": e2_cal_oof,
        "e2_prod_surface": e2_prod_surface,
        "e3_oof_surface": e3_cal_oof,
        "e3_prod_surface": e3_prod_surface,
    }
    if s2_ckpt is not None:
        np.savez(s2_ckpt, **out_dict)
    print(f"  [Stage 2 Prod] Full-footprint surfaces ready & checkpointed ({time.time() - t0:.1f}s)")
    return out_dict
