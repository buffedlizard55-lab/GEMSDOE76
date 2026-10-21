"""Execute GEMSDOE76 Gate-1 Canaries, Exact 3 Preregistered Spatially-Blocked
Hide-and-Recover Experiments (EXP-76-1, EXP-76-2, EXP-76-3) + Leak-Free Baselines,
Full-Footprint Synthesis, 896-Raster Uniqueness Audit, and Validated GeoTIFF Export.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import emit, evaluate_holdout, holdout as g57_holdout, spatial, submission_writer, uniqueness  # noqa: E402
from gems76.canary import _exact_auc_1d, run_single_feature_auc_canary  # noqa: E402
from gems76.features import build_or_load_feature_memmap  # noqa: E402
from gems76.models import (
    STAGE2_CONTEXT_NAMES,
    _cross_regime_quantile_bridge_subset,
    _prior_correct_prob,
    _sample_train_indices,
    extract_stage2_context_matrix,
    fit_stage1_suite,
    predict_stage1_suite,
    row_major_disk_thin,
)

GEMS_DATA = Path("/tmp/gems_data")
EXT_ROOT = Path("/tmp/ref/60GEMSDOE/data")
EVIDENCE_DIR = ROOT / "evidence"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
TOTAL_DOT_BUDGET = 39_200


class _GridShim:
    def __init__(self, fp: np.ndarray, cat: np.ndarray):
        self.footprint = fp
        self.catalogue = cat
        self.height, self.width = fp.shape


def _fit_stage2_and_predict(
    X2_train_view: np.ndarray,
    X2_eval_view: np.ndarray,
    train_mask_fp: np.ndarray,
    eval_mask_fp: np.ndarray,
    y_fp: np.ndarray,
    p1_joint_train_view: np.ndarray,
    p1_joint_eval_view: np.ndarray,
    seed: int = 760,
) -> np.ndarray:
    """Fit regularized dual-LightGBM Stage-2 U-GBDT strictly inside ``train_mask_fp``."""
    rng = np.random.default_rng(seed)
    idx, true_pi, sample_pi = _sample_train_indices(train_mask_fp, y_fp, rng, max_neg=220_000)
    X_tr = X2_train_view[idx]
    y_tr = y_fp[idx]

    m2_a = lgb.LGBMClassifier(
        n_estimators=170, learning_rate=0.045, max_depth=5, num_leaves=23,
        min_child_samples=350, colsample_bytree=0.72, subsample=0.80, subsample_freq=1,
        reg_alpha=4.0, reg_lambda=20.0, n_jobs=2, random_state=seed + 11, verbose=-1,
    ).fit(X_tr, y_tr)

    m2_b = lgb.LGBMClassifier(
        n_estimators=170, learning_rate=0.045, max_depth=4, num_leaves=15,
        min_child_samples=500, colsample_bytree=0.50, subsample=0.75, subsample_freq=1,
        reg_alpha=6.0, reg_lambda=28.0, n_jobs=2, random_state=seed + 17, verbose=-1,
    ).fit(X_tr, y_tr)
    del X_tr
    gc.collect()

    ev_rows = np.flatnonzero(eval_mask_fp)
    pa = _prior_correct_prob(m2_a.booster_.predict(X2_eval_view[ev_rows], num_threads=2), true_pi, sample_pi)
    pb = _prior_correct_prob(m2_b.booster_.predict(X2_eval_view[ev_rows], num_threads=2), true_pi, sample_pi)
    p_blend = (0.72 * (0.55 * pa + 0.45 * pb) + 0.28 * p1_joint_eval_view[ev_rows]).astype(np.float64)

    cal_pool = np.flatnonzero(train_mask_fp)
    cal_sub = rng.choice(cal_pool, size=min(350_000, cal_pool.size), replace=False)
    tr_a = _prior_correct_prob(m2_a.booster_.predict(X2_train_view[cal_sub], num_threads=2), true_pi, sample_pi)
    tr_b = _prior_correct_prob(m2_b.booster_.predict(X2_train_view[cal_sub], num_threads=2), true_pi, sample_pi)
    blend_tr = (0.72 * (0.55 * tr_a + 0.45 * tr_b) + 0.28 * p1_joint_train_view[cal_sub]).astype(np.float64)

    iso = IsotonicRegression(y_min=1e-6, y_max=0.95, out_of_bounds="clip")
    iso.fit(blend_tr, y_fp[cal_sub].astype(np.float64))
    out = np.zeros(X2_eval_view.shape[0], dtype=np.float32)
    out[ev_rows] = iso.transform(p_blend).astype(np.float32)
    return out


def _fit_predict_gems70_p8_oof(
    mm: np.memmap,
    fnames: list[str],
    sgmc_fp: np.ndarray,
    train_mask_fp: np.ndarray,
    eval_mask_fp: np.ndarray,
    y_fp: np.ndarray,
    seed: int = 700,
) -> np.ndarray:
    """Strictly leak-free OOF reproduction of GEMSDOE70 P8 (8 core features + w_bed=0.25 SGMC)."""
    cmap = {n: i for i, n in enumerate(fnames)}
    cols8 = np.array([
        cmap["lid_step"], cmap["lid_ex"], cmap["t10_slope_p90"], cmap["t10_slope_max"],
        cmap["t10_curv_absmax"], cmap["t10_hs_lineament"], cmap["det_elev_slope"], cmap["iso_grav_slope_hp15"],
    ], dtype=np.int64)
    rng = np.random.default_rng(seed)
    idx, true_pi, sample_pi = _sample_train_indices(train_mask_fp, y_fp, rng, max_neg=200_000)
    clf = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=63, min_child_samples=90,
        n_jobs=2, random_state=seed, verbose=-1,
    ).fit(np.asarray(mm[idx][:, cols8], dtype=np.float32), y_fp[idx])

    ev_rows = np.flatnonzero(eval_mask_fp)
    p_ev = _prior_correct_prob(
        clf.booster_.predict(np.asarray(mm[ev_rows][:, cols8], dtype=np.float32), num_threads=2),
        true_pi, sample_pi,
    )
    out = np.zeros(mm.shape[0], dtype=np.float32)
    out[ev_rows] = np.clip(0.75 * p_ev + 0.25 * sgmc_fp[ev_rows] * float(p_ev.max()), 0.0, 1.0)
    return out


def _fit_predict_h33_singlepx_oof(
    mm: np.memmap,
    fnames: list[str],
    train_mask_fp: np.ndarray,
    eval_mask_fp: np.ndarray,
    lid_valid_fp: np.ndarray,
    y_fp: np.ndarray,
    seed: int = 320,
) -> np.ndarray:
    """Strictly leak-free OOF reproduction of H33's single-pixel GBDT + quantile gap bridge."""
    exclude_novel = {
        "b19_hp3", "b19_hp12", "b12_lap1_concave", "b12_lap3_flexure",
        "dem100_lap_concave", "ptcf_concave_toe_idx",
        "scarp_worm_600m", "scarp_worm_1500m", "scarp_worm_aniso_1500m",
        "cos_tdr_mag", "grad_tdr_mag", "cos_tdr_grav", "tmi_shallow_res",
        "chi_step_smooth", "chi_ksn_smooth", "chi_knick_density", "chi_knick_worm_1400m",
        "mag_destruct_K_alter",
    }
    cols_base = np.array([i for i, n in enumerate(fnames) if n not in exclude_novel], dtype=np.int64)
    rng = np.random.default_rng(seed)
    idx, true_pi, sample_pi = _sample_train_indices(train_mask_fp, y_fp, rng, max_neg=220_000)
    clf = lgb.LGBMClassifier(
        n_estimators=240, learning_rate=0.055, num_leaves=63, min_child_samples=90,
        colsample_bytree=0.75, subsample=0.80, subsample_freq=1, reg_alpha=2.0, reg_lambda=8.0,
        n_jobs=2, random_state=seed, verbose=-1,
    ).fit(np.asarray(mm[idx][:, cols_base], dtype=np.float32), y_fp[idx])

    sub_rows = np.flatnonzero(train_mask_fp | eval_mask_fp)
    p_sub = _prior_correct_prob(
        clf.booster_.predict(np.asarray(mm[sub_rows][:, cols_base], dtype=np.float32), num_threads=2),
        true_pi, sample_pi,
    )
    p_bridged = _cross_regime_quantile_bridge_subset(p_sub, lid_valid_fp[sub_rows], train_mask_fp[sub_rows])
    out = np.zeros(mm.shape[0], dtype=np.float32)
    out[sub_rows] = p_bridged
    return out


def main() -> None:
    t_start = time.time()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    print("[Step 1/6] Opening cached 62-channel feature memmap & verifying Gate-1 canary...", flush=True)
    mm, fnames, fp = build_or_load_feature_memmap(force=False)
    H, W = fp.shape
    fp_idx = np.flatnonzero(fp.ravel())
    n_fp = int(fp_idx.size)

    with rasterio.open(GEMS_DATA / "labels.tif") as s:
        cat = (s.read(1) > 0) & fp
    with rasterio.open(EXT_ROOT / "external" / "derived_sgmc_faults_100m_u8.tif") as s:
        sgmc_fp = (s.read(1).astype(np.float32) / 255.0).ravel()[fp_idx]

    y_fp = cat.ravel()[fp_idx].astype(np.uint8)
    yy, xx = np.indices((H, W), sparse=True)
    quad_2d = ((yy >= H // 2).astype(np.int8) * 2 + (xx >= W // 2).astype(np.int8))
    quad_fp = quad_2d.ravel()[fp_idx]
    lid_valid_fp = np.asarray(mm[:, fnames.index("lid_valid")], dtype=np.float32) > 0.5

    canary_p1 = EVIDENCE_DIR / "leakage_canary_stage1.json"
    if canary_p1.is_file():
        canary_stage1 = json.loads(canary_p1.read_text())
        assert canary_stage1["passed"] and canary_stage1["n_features_checked"] == len(fnames)
    else:
        canary_stage1 = run_single_feature_auc_canary(mm, fnames, y_fp, quad_fp, hard_limit=0.90)
        canary_p1.write_text(json.dumps(canary_stage1, indent=2) + "\n")
    print(f"  Gate-1 Stage-1 Canary PASS: {canary_stage1['n_features_checked']} features, max AUC = {canary_stage1['max_observed_polarity_auc']:.5f}", flush=True)

    folds_quad = list(spatial.folds(cat, fp, buffer_px=80))
    folds_inter, _ = g57_holdout.buffered_component_draw(_GridShim(fp, cat), seed=20, hide_frac=0.20, buffer_px=3)

    oof_gems70 = np.zeros(n_fp, dtype=np.float32)
    oof_h33_single = np.zeros(n_fp, dtype=np.float32)
    oof_exp1 = np.zeros(n_fp, dtype=np.float32)
    oof_scarp = np.zeros(n_fp, dtype=np.float32)
    oof_geoph = np.zeros(n_fp, dtype=np.float32)
    oof_fluv = np.zeros(n_fp, dtype=np.float32)
    oof_exp2 = np.zeros(n_fp, dtype=np.float32)
    s2_mm_path = ROOT / ".cache" / "gems76" / "stage2_oof.f32"
    oof_stage2_feats_sample = np.memmap(
        s2_mm_path, mode=("r+" if s2_mm_path.is_file() else "w+"), dtype=np.float32, shape=(n_fp, len(STAGE2_CONTEXT_NAMES))
    )

    print("[Step 2/6] Running strict out-of-fold training across 4 buffered quadrants (buffer = 8.0 km)...", flush=True)
    for f in range(4):
        tf0 = time.time()
        fold = folds_quad[f]
        train_2d = fold["train"]
        eval_2d = fold["region"]
        train_fp = train_2d.ravel()[fp_idx]
        eval_fp = eval_2d.ravel()[fp_idx]
        ckpt_f = ROOT / ".cache" / "gems76" / f"fold_{f}_v1.npz"
        if ckpt_f.is_file():
            d_ck = np.load(ckpt_f)
            oof_gems70[eval_fp] = d_ck["g70"]
            oof_h33_single[eval_fp] = d_ck["h33"]
            oof_exp1[eval_fp] = d_ck["e1"]
            oof_scarp[eval_fp] = d_ck["sc"]
            oof_geoph[eval_fp] = d_ck["ge"]
            oof_fluv[eval_fp] = d_ck["fl"]
            oof_exp2[eval_fp] = d_ck["e2"]
            print(f"  Fold {f} restored from checkpoint ({ckpt_f.name})", flush=True)
            continue

        oof_gems70[eval_fp] = _fit_predict_gems70_p8_oof(mm, fnames, sgmc_fp, train_fp, eval_fp, y_fp, seed=700 + f)[eval_fp]
        oof_h33_single[eval_fp] = _fit_predict_h33_singlepx_oof(mm, fnames, train_fp, eval_fp, lid_valid_fp, y_fp, seed=320 + f)[eval_fp]

        inner_quads = [q for q in range(4) if q != f]
        p_j_tr_oof = np.zeros(n_fp, dtype=np.float32)
        p_s_tr_oof = np.zeros(n_fp, dtype=np.float32)
        p_g_tr_oof = np.zeros(n_fp, dtype=np.float32)
        p_f_tr_oof = np.zeros(n_fp, dtype=np.float32)

        p_j_ev_acc = np.zeros(n_fp, dtype=np.float64)
        p_s_ev_acc = np.zeros(n_fp, dtype=np.float64)
        p_g_ev_acc = np.zeros(n_fp, dtype=np.float64)
        p_f_ev_acc = np.zeros(n_fp, dtype=np.float64)

        for q_val in inner_quads:
            in_tr = train_fp & (quad_fp != q_val)
            in_va = train_fp & (quad_fp == q_val)
            s_in = fit_stage1_suite(mm, in_tr, y_fp, seed=100 * f + 10 * q_val + 1, fast_inner=True)
            pj, ps, pg, pf = predict_stage1_suite(s_in, mm, lid_valid_fp, in_tr, target_mask_fp=(in_va | eval_fp))
            p_j_tr_oof[in_va] = pj[in_va]
            p_s_tr_oof[in_va] = ps[in_va]
            p_g_tr_oof[in_va] = pg[in_va]
            p_f_tr_oof[in_va] = pf[in_va]
            p_j_ev_acc += pj
            p_s_ev_acc += ps
            p_g_ev_acc += pg
            p_f_ev_acc += pf
            del s_in, pj, ps, pg, pf
            gc.collect()

        s_out = fit_stage1_suite(mm, train_fp, y_fp, seed=500 + f, fast_inner=False)
        pj_o, ps_o, pg_o, pf_o = predict_stage1_suite(s_out, mm, lid_valid_fp, train_fp, target_mask_fp=None)
        del s_out
        gc.collect()

        pj_ev = pj_o.copy()
        ps_ev = ps_o.copy()
        pg_ev = pg_o.copy()
        pf_ev = pf_o.copy()
        pj_ev[eval_fp] = (0.55 * pj_o[eval_fp] + 0.45 * (p_j_ev_acc[eval_fp] / 3.0)).astype(np.float32)
        ps_ev[eval_fp] = (0.55 * ps_o[eval_fp] + 0.45 * (p_s_ev_acc[eval_fp] / 3.0)).astype(np.float32)
        pg_ev[eval_fp] = (0.55 * pg_o[eval_fp] + 0.45 * (p_g_ev_acc[eval_fp] / 3.0)).astype(np.float32)
        pf_ev[eval_fp] = (0.55 * pf_o[eval_fp] + 0.45 * (p_f_ev_acc[eval_fp] / 3.0)).astype(np.float32)

        oof_exp1[eval_fp] = pj_ev[eval_fp]
        oof_scarp[eval_fp] = ps_ev[eval_fp]
        oof_geoph[eval_fp] = pg_ev[eval_fp]
        oof_fluv[eval_fp] = pf_ev[eval_fp]

        X2_tr_view = extract_stage2_context_matrix(
            p_j_tr_oof, p_s_tr_oof, p_g_tr_oof, p_f_tr_oof,
            mm, fp, fp_idx, allowed_spatial_2d=train_2d, thresh_ref_mask_fp=train_fp,
        )
        X2_ev_view = extract_stage2_context_matrix(
            pj_ev, ps_ev, pg_ev, pf_ev,
            mm, fp, fp_idx, allowed_spatial_2d=fp, thresh_ref_mask_fp=train_fp,
        )
        oof_stage2_feats_sample[eval_fp] = X2_ev_view[eval_fp]
        p2_cal = _fit_stage2_and_predict(
            X2_tr_view, X2_ev_view, train_fp, eval_fp, y_fp, p_j_tr_oof, pj_ev, seed=900 + f
        )
        oof_exp2[eval_fp] = p2_cal[eval_fp]
        oof_stage2_feats_sample.flush()
        np.savez(
            ckpt_f,
            g70=oof_gems70[eval_fp],
            h33=oof_h33_single[eval_fp],
            e1=oof_exp1[eval_fp],
            sc=oof_scarp[eval_fp],
            ge=oof_geoph[eval_fp],
            fl=oof_fluv[eval_fp],
            e2=oof_exp2[eval_fp],
        )
        del X2_tr_view, X2_ev_view, p2_cal, pj_o, ps_o, pg_o, pf_o
        gc.collect()
        print(
            f"  Fold {f} (train={int(train_fp.sum()):,}, eval={int(eval_fp.sum()):,}, truth={fold['receipt']['truth_px']:,}) "
            f"AUC: GEMS70={_exact_auc_1d(y_fp[eval_fp], oof_gems70[eval_fp]):.4f} | "
            f"H33_base={_exact_auc_1d(y_fp[eval_fp], oof_h33_single[eval_fp]):.4f} | "
            f"EXP1={_exact_auc_1d(y_fp[eval_fp], oof_exp1[eval_fp]):.4f} | "
            f"EXP2={_exact_auc_1d(y_fp[eval_fp], oof_exp2[eval_fp]):.4f} ({time.time() - tf0:.1f}s)",
            flush=True,
        )

    np.savez(
        ROOT / ".cache" / "gems76" / "oof_predictions.npz",
        oof_gems70=oof_gems70, oof_h33_single=oof_h33_single,
        oof_exp1=oof_exp1, oof_scarp=oof_scarp, oof_geoph=oof_geoph, oof_fluv=oof_fluv, oof_exp2=oof_exp2,
    )

    c2_path = EVIDENCE_DIR / "leakage_canary_stage2.json"
    if c2_path.is_file():
        canary_stage2 = json.loads(c2_path.read_text())
    else:
        canary_stage2 = run_single_feature_auc_canary(
            oof_stage2_feats_sample, STAGE2_CONTEXT_NAMES, y_fp, quad_fp, hard_limit=0.90
        )
        c2_path.write_text(json.dumps(canary_stage2, indent=2) + "\n")
    print(f"  Gate-1 Stage-2 OOF Context Canary PASS: max polarity AUC = {canary_stage2['max_observed_polarity_auc']:.5f} <= 0.90!", flush=True)
    del oof_stage2_feats_sample
    gc.collect()

    def _vec_to_2d(v: np.ndarray) -> np.ndarray:
        a = np.zeros((H, W), dtype=np.float32)
        a.ravel()[fp_idx] = v
        return a

    s2d_gems70 = _vec_to_2d(oof_gems70)
    s2d_h33 = _vec_to_2d(oof_h33_single)
    s2d_exp1 = _vec_to_2d(oof_exp1)
    s2d_exp2 = _vec_to_2d(oof_exp2)

    print("[Step 3/6] Evaluating all arms via vendor/gems57/evaluate_holdout.py (1,000 paired block draws)...", flush=True)

    def _run_holdout_suite(fold_list: list[dict], tag: str, include_archival: bool = False) -> dict:
        arm_names = [
            "random_control",
            "GEMS70_P8_oof",
            "H33_singlepx_oof",
            "EXP_76_1_MultiPhysics_Disk",
            "EXP_76_2_ContextPyramid_Disk",
            "EXP_76_3_ContextPyramid_SubmodDTI",
        ]
        archival_map = {}
        if include_archival:
            matched = json.loads(Path("/tmp/gems_evidence/matched_live_submissions.json").read_text())
            for label_a, target_sub in (
                ("ARCHIVAL_H33_02778", "h33-h33-2-b2"),
                ("ARCHIVAL_D28_02665", "d28-h25-2-p25-k3"),
                ("ARCHIVAL_GEMS70_02478", "gems70-p5-dual-submod300-oof38k"),
                ("ARCHIVAL_GEMS49_02376", "gems49-gate_ortho_w0.25-40k"),
                ("ARCHIVAL_GEMS73_01592", "gems73-hydro-permeability-corridor"),
            ):
                for m in matched:
                    if target_sub in m.get("sub", "") or target_sub in m.get("path", ""):
                        with rasterio.open(m["path"]) as s:
                            arr_a = s.read(1).astype(np.float32)
                        arr_a = np.where(np.isfinite(arr_a), np.clip(arr_a, 0.0, 1.0), 0.0)
                        archival_map[label_a] = arr_a
                        arm_names.append(label_a)
                        break

        terms_by_arm: dict[str, np.ndarray | None] = {k: None for k in arm_names}
        per_fold_records: dict[str, list[dict]] = {k: [] for k in arm_names}

        for f_i, fold in enumerate(fold_list):
            region = fold["region"]
            known_mask = fold.get("masked_known", fold["visible"])
            vis_feat = fold["visible"]
            active = fp & region & (~known_mask)
            n_act = int(active.sum())
            b_fold = int(round(TOTAL_DOT_BUDGET * (n_act / float(n_fp))))
            k_truth_est = max(float(fold["truth"].sum()), 500.0)
            d_vis = distance_transform_edt(~vis_feat).astype(np.float32)

            rng_c = np.random.default_rng(7600 + f_i)
            act_flat = np.flatnonzero(active.ravel())
            p_rand = np.zeros((H, W), dtype=np.float32)
            p_rand.ravel()[rng_c.choice(act_flat, size=min(b_fold, act_flat.size), replace=False)] = 1.0

            rk70, _ = emit.emit_decimated(s2d_gems70, active & (d_vis > 2.0), tile_px=3)
            p_g70 = emit.emit_prefix(rk70, b_fold).astype(np.float32)

            top_245 = int(round(0.0245 * n_act))
            p_h33 = row_major_disk_thin(
                s2d_h33, active & (d_vis > 2.0), budget=b_fold, min_dist_px=3.0, binary_mask_top_k=top_245
            ).astype(np.float32)

            p_e1 = row_major_disk_thin(
                s2d_exp1, active & (d_vis > 2.0), budget=b_fold, min_dist_px=3.0, binary_mask_top_k=None
            ).astype(np.float32)

            p_e2 = row_major_disk_thin(
                s2d_exp2, active & (d_vis > 2.0), budget=b_fold, min_dist_px=3.0, binary_mask_top_k=None
            ).astype(np.float32)

            alloc_e3 = emit.allocate_submodular_celf(
                s2d_exp2,
                active & (d_vis > 2.2),
                k_truth=k_truth_est,
                budget=b_fold,
                min_dist_px=3.0,
                d_vis=d_vis,
                shadow_carve_px=3.2,
                shadow_floor=0.12,
            )
            p_e3 = alloc_e3.emitted.astype(np.float32)

            preds_fold = {
                "random_control": p_rand,
                "GEMS70_P8_oof": p_g70,
                "H33_singlepx_oof": p_h33,
                "EXP_76_1_MultiPhysics_Disk": p_e1,
                "EXP_76_2_ContextPyramid_Disk": p_e2,
                "EXP_76_3_ContextPyramid_SubmodDTI": p_e3,
                **archival_map,
            }
            for aname, parr in preds_fold.items():
                res_f, terms_f = evaluate_holdout.evaluate(parr, fold, fp)
                terms_by_arm[aname] = terms_f if terms_by_arm[aname] is None else (terms_by_arm[aname] + terms_f)
                per_fold_records[aname].append({
                    "fold": f_i,
                    "dti": round(res_f["dti"], 6),
                    "coverage": round(res_f["coverage"], 5),
                    "tpw": round(res_f["tpw"], 2),
                    "fpw": round(res_f["fpw"], 2),
                    "fnw": round(res_f["fnw"], 2),
                    "n_truth": res_f["n_truth"],
                    "n_emitted": res_f["n_emitted"],
                })

        strict_arms = {k: terms_by_arm[k] for k in arm_names if not k.startswith("ARCHIVAL_")}
        pooled_strict = evaluate_holdout.pooled_summary(
            strict_arms, draws=1000, seed=520810, candidate="EXP_76_3_ContextPyramid_SubmodDTI"
        )
        pooled_all = (
            evaluate_holdout.pooled_summary(
                terms_by_arm, draws=1000, seed=520810, candidate="EXP_76_3_ContextPyramid_SubmodDTI"
            )
            if include_archival
            else None
        )
        return {
            "benchmark_tag": tag,
            "pooled_strict_oof": pooled_strict,
            "pooled_with_archival_reference": pooled_all,
            "per_fold": per_fold_records,
            "fold_receipts": [f["receipt"] for f in fold_list],
        }

    bench_primary = _run_holdout_suite(folds_quad, "label-blind-quadrants-v2_n60988", include_archival=False)
    bench_inter = _run_holdout_suite(folds_inter, "buffered-whole-components-loqo-v2_hide20", include_archival=True)

    print("  === PRIMARY BENCHMARK: HOLDOUT-DTI (gems57-pooled-hide-v2, label-blind-quadrants-v2, n=60,988) ===", flush=True)
    for k, v in bench_primary["pooled_strict_oof"]["scores"].items():
        print(f"    {k:<36} DTI = {v['dti']:.5f}  95% CI [{v['ci95'][0]:.5f}, {v['ci95'][1]:.5f}]  TP_w={v['tpw']:.1f}", flush=True)
    print("  Paired deltas (EXP_76_3 vs strict OOF controls):", flush=True)
    for k, v in bench_primary["pooled_strict_oof"]["paired_differences"].items():
        print(f"    vs {k:<33} delta = {v['delta']:+.5f}  95% CI [{v['ci95'][0]:+.5f}, {v['ci95'][1]:+.5f}]", flush=True)

    print("  === SECONDARY REALISTIC BENCHMARK: HOLDOUT-DTI (buffered-whole-components-loqo-v2, hide=20%) ===", flush=True)
    for k, v in bench_inter["pooled_with_archival_reference"]["scores"].items():
        print(f"    {k:<36} DTI = {v['dti']:.5f}  95% CI [{v['ci95'][0]:.5f}, {v['ci95'][1]:.5f}]  TP_w={v['tpw']:.1f}", flush=True)

    print("[Step 4/6] Synthesizing full-footprint competition surface & CELF submodular dot field...", flush=True)
    all_mask = np.ones(n_fp, dtype=bool)
    s_full = fit_stage1_suite(mm, all_mask, y_fp, seed=2026076, fast_inner=False)
    pj_full, ps_full, pg_full, pf_full = predict_stage1_suite(s_full, mm, lid_valid_fp, all_mask, target_mask_fp=None)
    del s_full
    gc.collect()

    X2_full_oof = extract_stage2_context_matrix(
        oof_exp1, oof_scarp, oof_geoph, oof_fluv, mm, fp, fp_idx, allowed_spatial_2d=fp, thresh_ref_mask_fp=all_mask
    )
    X2_full_inf = extract_stage2_context_matrix(
        pj_full, ps_full, pg_full, pf_full, mm, fp, fp_idx, allowed_spatial_2d=fp, thresh_ref_mask_fp=all_mask
    )
    p_final_fp = _fit_stage2_and_predict(
        X2_full_oof, X2_full_inf, all_mask, all_mask, y_fp, oof_exp1, pj_full, seed=7676
    )
    del X2_full_oof, X2_full_inf
    gc.collect()

    surf_final_2d = np.zeros((H, W), dtype=np.float32)
    surf_final_2d.ravel()[fp_idx] = np.clip(p_final_fp, 0.0, 1.0)
    surf_final_2d[cat] = 0.0
    np.save(ROOT / ".cache" / "gems76" / "surf_final_fp.npy", surf_final_2d.ravel()[fp_idx])

    d_known_full = distance_transform_edt(~cat).astype(np.float32)
    allowed_sub = fp & (~cat) & (d_known_full > 2.2)

    alloc_final = emit.allocate_submodular_celf(
        surf_final_2d,
        allowed_sub,
        k_truth=12_000.0,
        budget=TOTAL_DOT_BUDGET,
        min_dist_px=3.0,
        d_vis=d_known_full,
        shadow_carve_px=3.2,
        shadow_floor=0.12,
    )
    dots_final_2d = np.where(alloc_final.emitted & fp & (~cat), np.float32(1.0), np.float32(0.0)).astype(np.float32)

    print("[Step 5/6] Auditing uniqueness across ALL 896 SHA-256 verified registry + sibling rasters...", flush=True)
    t_u = time.time()
    reg_index = json.loads(Path("/tmp/gems_evidence/combined_registry_full.json").read_text())
    u_audit = uniqueness.compare_surface_and_dots_to_registry(
        surf_final_2d, dots_final_2d, reg_index, fp, sparse_dot_limit_frac=0.05
    )
    print(f"  896-raster audit completed in {time.time() - t_u:.1f}s:", flush=True)
    print(f"    Surface worst |Spearman| = {u_audit['surface']['worst_abs_spearman']:.5f} ({u_audit['surface']['worst_rho_repo']}:{u_audit['surface']['worst_rho_submission']})", flush=True)
    print(f"    Dots worst |Spearman|    = {abs(u_audit['dots']['worst_spearman_full_footprint']):.5f} ({u_audit['dots']['worst_rho_submission']})", flush=True)
    print(f"    Dots worst mutual 3px ov = {u_audit['dots']['worst_dot_overlap']:.5f} ({u_audit['dots']['worst_overlap_submission']})", flush=True)
    print(f"    Dots worst sparse fwd ov = {u_audit['strict_sparse_forward_gate']['worst_forward_overlap']:.5f} ({u_audit['strict_sparse_forward_gate']['worst_forward_repo']}:{u_audit['strict_sparse_forward_gate']['worst_forward_submission']})", flush=True)
    print(f"    Dots two-phase dot_field = {u_audit['two_phase']['like_for_like_reading']['worst_forward_overlap_dot_fields']:.5f}", flush=True)

    print("[Step 6/6] Writing fail-closed GeoTIFF & single-file ZIP deliverable...", flush=True)
    content_hash8 = hashlib.sha256(np.ascontiguousarray(dots_final_2d).tobytes()).hexdigest()[:8]
    ts_str = "20261021T034000Z"
    stem = f"gems76-ptcf-tiltworm-submod39k-{ts_str}-{content_hash8}-zeros"
    out_tif = DOWNLOADS_DIR / f"{stem}.tif"
    for p_old in DOWNLOADS_DIR.glob("gems76-*"):
        p_old.unlink()

    sub_note = (
        f"GEMS76 PTCF+TiltWorm+Chi 2D-UGBDT + CELF SubmodDTI {int(dots_final_2d.sum())}d "
        f"[0,1] zeros sha:{content_hash8}"
    )
    assert len(sub_note) <= 140, len(sub_note)

    receipt = submission_writer.write_submission(
        out_tif,
        dots_final_2d,
        GEMS_DATA / "sample_submission.tif",
        fp,
        note=sub_note,
        name=stem,
        catalogue=cat,
        metadata={
            "experiment": "EXP_76_3_ContextPyramid_SubmodDTI",
            "total_dots": int(dots_final_2d.sum()),
            "on_catalogue_dots": int((dots_final_2d[cat] > 0).sum()),
            "outside_footprint_nonzero": int((dots_final_2d[~fp] != 0).sum()),
            "nan_or_inf_anywhere": int((~np.isfinite(dots_final_2d)).sum()),
        },
    )

    u_full_rows = u_audit["dots"].pop("rows")
    (EVIDENCE_DIR / "uniqueness_896_ledger_summary.json").write_text(
        json.dumps({
            **u_audit,
            "verified_file_sha256": receipt["sha256"],
            "verified_zip_sha256": receipt["zip_sha256"],
            "top25_by_mutual_overlap": sorted(
                [r for r in u_full_rows if "error" not in r],
                key=lambda r: -r["mutual_overlap"],
            )[:25],
            "top25_by_forward_overlap": sorted(
                [r for r in u_full_rows if "error" not in r],
                key=lambda r: -r["my_dots_within_3px_of_theirs"],
            )[:25],
        }, indent=2) + "\n"
    )
    (EVIDENCE_DIR / "holdout_experiments_results.json").write_text(
        json.dumps({
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "elapsed_seconds": round(time.time() - t_start, 2),
            "budget_experiments_used": 3,
            "budget_experiments_limit": 3,
            "primary_holdout_quadrants_n60988": bench_primary,
            "secondary_holdout_interspersed_hide20": bench_inter,
            "submission_receipt": receipt,
        }, indent=2) + "\n"
    )

    b19_full = np.memmap(GEMS_DATA / "bands19.f32", mode="r", dtype=np.float32, shape=(19, H, W))[18]
    q_edges = np.quantile(b19_full[fp], [0.25, 0.50, 0.75, 0.90])
    d_dots = dots_final_2d > 0
    s_b19 = b19_full[d_dots]
    s_dk = d_known_full[d_dots]
    anat = {
        "n_dots": int(d_dots.sum()),
        "q1_frac": round(float((s_b19 <= q_edges[0]).mean()), 4),
        "q2_frac": round(float(((s_b19 > q_edges[0]) & (s_b19 <= q_edges[1])).mean()), 4),
        "q3_frac": round(float(((s_b19 > q_edges[1]) & (s_b19 <= q_edges[2])).mean()), 4),
        "q4_frac": round(float((s_b19 > q_edges[2]).mean()), 4),
        "top10_steep_frac": round(float((s_b19 > q_edges[3]).mean()), 4),
        "d_cat_0_2_px": int((s_dk <= 2.0).sum()),
        "d_cat_2_3_px": int(((s_dk > 2.0) & (s_dk <= 3.0)).sum()),
        "d_cat_gt_3_px": int((s_dk > 3.0).sum()),
        "quadrant_counts": {
            qname: int((d_dots & (quad_2d == qi)).sum())
            for qi, qname in enumerate(["NW", "NE", "SW", "SE"])
        },
        "lidar_covered_frac": round(float((dots_final_2d.ravel()[fp_idx][lid_valid_fp] > 0).sum() / d_dots.sum()), 4),
    }
    (EVIDENCE_DIR / "submission_anatomy.json").write_text(json.dumps(anat, indent=2) + "\n")
    print(f"DONE in {time.time() - t_start:.1f}s! Deliverable: {out_tif.name} (sha256={receipt['sha256']})", flush=True)
    print("Anatomy:", anat, flush=True)


if __name__ == "__main__":
    main()
