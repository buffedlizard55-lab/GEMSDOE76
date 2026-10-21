#!/usr/bin/env python3
"""Experiment 1 (pre-registered): Lane G76B patch-context corroboration.

Instruments, arms, controls and gates are frozen in docs/preregistration-g76b.md
(written before this run).  One run only; no silent reruns.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata  # noqa: F401  (kept for parity with G76 receipts)
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import emit, evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems76b import features as FB  # noqa: E402
from gems76b import model as MB  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
REG = ROOT / ".cache" / "registry"
E = ROOT / "evidence" / "g76b-exp1"
CACHE = ROOT / ".cache" / "g76b"
BUDGET_DOTS = 37_654
SENTINEL = -1e30

D28 = REG / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-allfinite.tif"
H33 = REG / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
P8 = REG / "gems70-p5-dual-submod300-oof38k-20261020.tif"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def read_tif(p: Path) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1).astype(np.float32)


def cropped_eval(fold, p, valid):
    y, x = np.nonzero(fold["region"])
    y0, x0 = max(0, int(y.min()) - 6), max(0, int(x.min()) - 6)
    y1, x1 = min(p.shape[0], int(y.max()) + 7), min(p.shape[1], int(x.max()) + 7)
    sl = np.s_[y0:y1, x0:x1]
    sub = {k: v[sl] for k, v in fold.items() if isinstance(v, np.ndarray) and v.shape == p.shape}
    return evaluate_holdout.evaluate(p[sl], sub, valid[sl], origin=(y0, x0), global_shape=p.shape)


def main() -> int:
    t0 = time.monotonic()
    if (E / "manifest.json").exists():
        raise RuntimeError("G76B Exp1 already attempted; inspect evidence/g76b-exp1 (no silent reruns).")
    E.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    dump(E / "manifest.json", {
        "experiment": "G76B-EXP1-patch-context-corroboration",
        "experiment_count_this_session": 1,
        "maximum_experiments": 3,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "preregistration_sha256": sha(ROOT / "docs/preregistration-g76b.md"),
        "source_sha256": {p: sha(ROOT / p) for p in
                          ["src/gems76b/features.py", "src/gems76b/model.py",
                           "scripts/run_experiment_g76b.py"]},
        "evaluator_implementation_sha256": evaluate_holdout.implementation_hashes(),
        "control_rasters_sha256": {"d28": sha(D28), "h33": sha(H33), "p8": sha(P8)},
    })

    # ---------- grid, valid domain (identical construction to G76 session) ----------
    grid = load_grid(ROOT / "data" / "bridge")
    fp = grid.footprint
    with rasterio.open(DATA / "training_features.tif") as src:
        raw = {}
        for idx, name in [(12, "det_elev"), (19, "det_elev_slope")]:
            a = src.read(idx).astype(np.float32)
            a[(a <= SENTINEL) | ~np.isfinite(a) | ~fp] = np.nan
            raw[name] = a
    valid = ndi.binary_erosion(
        fp & np.isfinite(raw["det_elev"]) & np.isfinite(raw["det_elev_slope"]), iterations=12)
    del raw
    print(f"[{time.monotonic()-t0:7.1f}s] valid={int(valid.sum())}", flush=True)

    # ---------- feature matrix (cached; identical bytes across experiments) ----------
    xc = CACHE / "X.npy"
    if xc.is_file():
        X = np.load(xc)
        names = json.loads((CACHE / "names.json").read_text())
        relief = np.load(CACHE / "relief.npy")
        depth = np.load(CACHE / "depth.npy")
        with rasterio.open(DATA / "training_features.tif") as src:
            slope = src.read(19).astype(np.float32)
            slope[(slope <= SENTINEL) | ~np.isfinite(slope) | ~fp] = np.nan
    else:
        X, names, aux = FB.build_feature_matrix(valid, DATA)
        np.save(xc, X)
        (CACHE / "names.json").write_text(json.dumps(names))
        np.save(CACHE / "relief.npy", aux["relief_decoded"])
        np.save(CACHE / "depth.npy", aux["depth"])
        relief, depth = aux["relief_decoded"], aux["depth"]
        with rasterio.open(DATA / "training_features.tif") as src:
            slope = src.read(19).astype(np.float32)
            slope[(slope <= SENTINEL) | ~np.isfinite(slope) | ~fp] = np.nan
        del aux
    print(f"[{time.monotonic()-t0:7.1f}s] X={X.shape} features={len(names)}", flush=True)

    folds, quad_ids = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    dump(E / "holdout_split.json", {"folds": [f["receipt"] for f in folds],
                                    "evaluator": "gems57-pooled-hide-v2 seed 20"})

    # ---------- leakage canaries: features alone + fold-honest fitted prob ----------
    truth = np.zeros(fp.shape, bool)
    active = np.zeros(fp.shape, bool)
    for f in folds:
        active |= valid & f["region"] & ~f["masked_known"]
        truth |= valid & f["truth"]
    # map full-grid flat indices -> X row indices (X is valid-domain ordered)
    row_of = np.full(fp.size, -1, np.int64)
    row_of[np.flatnonzero(valid.ravel())] = np.arange(X.shape[0])

    def xrows(mask: np.ndarray) -> np.ndarray:
        return row_of[np.flatnonzero(mask.ravel())]

    pos_flat = np.flatnonzero((valid & truth).ravel())
    rng = np.random.default_rng(76020)
    neg_flat = rng.choice(np.flatnonzero((valid & active & ~truth).ravel()),
                          200_000, replace=False)
    pos_x, neg_x = row_of[pos_flat], row_of[neg_flat]
    labels = np.r_[np.ones(len(pos_x)), np.zeros(len(neg_x))]
    canaries = {}
    for j, name in enumerate(names):
        v = np.r_[X[pos_x, j], X[neg_x, j]]
        auc = float(roc_auc_score(labels, v))
        canaries[name] = {"evidence_class": "LEAKAGE-CANARY", "auc": auc,
                          "inverse_auc": 1 - auc,
                          "withheld_positive_pixels": int(len(pos_x)),
                          "negative_sample_pixels": int(len(neg_x)),
                          "suspected_leakage": bool(max(auc, 1 - auc) > 0.90)}
        print(f"canary {name}: {auc:.4f}", flush=True)
    dump(E / "canaries.json", canaries)

    # ---------- per-fold fold-honest fits, emissions and evaluation ----------
    d28 = read_tif(D28)
    h33 = read_tif(H33)
    p8 = read_tif(P8)
    random_dots = np.zeros(fp.shape, np.float32)
    ids = rng.choice(np.flatnonzero((valid & ~grid.catalogue).ravel()), BUDGET_DOTS, replace=False)
    random_dots.ravel()[ids] = 1.0

    arms = ["candidate_dots", "candidate_surface", "fair_h33", "fair_p8",
            "d28_reference", "random_dots"]
    terms = {a: None for a in arms}
    fold_results = {a: [] for a in arms}
    fit_receipts = []

    for k, f in enumerate(folds):
        region, visible = f["region"], f["visible"]
        pool_mask = MB.training_pool(valid, region)
        pos_mask = pool_mask & visible
        clf, rec = MB.fit_hgb(X, xrows(pos_mask), xrows(pool_mask), seed=76030 + k)
        rec["fold"] = k
        fit_receipts.append(rec)
        prob_vec = MB.predict_full(X, clf)
        prob = MB.vec_to_grid(prob_vec, valid)
        # fold-honest fitted-prob canary sample (this fold's truth only)
        auc_fit = float(roc_auc_score(
            np.r_[np.ones(len(xrows(valid & f["truth"]))), np.zeros(len(neg_x))],
            np.r_[prob_vec[xrows(valid & f["truth"])], prob_vec[neg_x]]))
        print(f"[fold {k}] fitted-prob canary AUC={auc_fit:.4f} "
              f"(pos={int(pos_mask.sum())})", flush=True)
        fit_receipts[-1]["fold_truth_auc_fitted_prob"] = auc_fit
        del prob_vec

        d_vis = ndi.distance_transform_edt(~visible)
        allowed = valid & (d_vis > 2)
        t = time.monotonic()
        alloc = emit.greedy_allocate(prob, allowed, k_truth=1e12,
                                     max_dots=BUDGET_DOTS, candidate_cap=600_000)
        print(f"[fold {k}] greedy: {alloc.n_dots} dots in {time.monotonic()-t:.1f}s", flush=True)
        cand_dots = alloc.emitted.astype(np.float32)
        np.save(CACHE / f"cand_dots_fold{k}.npy", cand_dots)
        np.save(CACHE / f"prob_fold{k}.npy", prob)

        fold_arms = {
            "candidate_dots": cand_dots,
            "candidate_surface": prob,
            "fair_h33": ((d28 > 0.5) & (d_vis > 2)).astype(np.float32),
            "fair_p8": ((p8 > 0.5) & (d_vis > 2)).astype(np.float32),
            "d28_reference": (d28 > 0.5).astype(np.float32),
            "random_dots": random_dots,
        }
        for name, a in fold_arms.items():
            r, tt = cropped_eval(f, a, valid)
            terms[name] = tt if terms[name] is None else terms[name] + tt
            fold_results[name].append(r)
        print(f"[fold {k}] DTI: " + " ".join(
            f"{n}={fold_results[n][-1]['dti']:.5f}" for n in arms), flush=True)
        del prob, cand_dots, fold_arms, alloc, d_vis, allowed

    # ---------- pooled fold-honest fitted-prob canary ----------
    # Each fold's model never saw its own tested quadrant, so scoring every
    # fold's truth rows with that fold's own surface is an honest holdout AUC.
    pooled_pos_vals, pooled_neg_vals = [], []
    for k, f in enumerate(folds):
        pf = np.load(CACHE / f"prob_fold{k}.npy")
        pooled_pos_vals.append(pf.ravel()[np.flatnonzero((valid & f["truth"]).ravel())])
        pooled_neg_vals.append(pf.ravel()[neg_flat])
        del pf
    auc_pooled_fit = float(roc_auc_score(
        np.r_[np.ones(sum(len(v) for v in pooled_pos_vals)),
              np.zeros(len(neg_flat) * len(folds))],
        np.r_[np.concatenate(pooled_pos_vals), np.concatenate(pooled_neg_vals)]))
    canaries["fitted_probability_fold_honest"] = {
        "evidence_class": "LEAKAGE-CANARY", "auc": auc_pooled_fit,
        "inverse_auc": 1 - auc_pooled_fit,
        "withheld_positive_pixels": int(sum(len(v) for v in pooled_pos_vals)),
        "negative_sample_pixels": int(len(neg_flat) * len(folds)),
        "suspected_leakage": bool(max(auc_pooled_fit, 1 - auc_pooled_fit) > 0.90)}
    print(f"pooled fold-honest fitted-prob canary AUC={auc_pooled_fit:.4f}", flush=True)
    dump(E / "canaries.json", canaries)
    dump(E / "fit_receipts.json", fit_receipts)
    if any(c["suspected_leakage"] for c in canaries.values()):
        dump(E / "STOP.json", {"reason": "CANARY STOP: AUC > 0.90",
                               "max_auc": max(max(c["auc"], c["inverse_auc"])
                                              for c in canaries.values())})
        raise RuntimeError("CANARY STOP: AUC > 0.90 — leakage until proven otherwise.")

    result = evaluate_holdout.pooled_summary(terms, draws=1000, seed=76020,
                                             candidate="candidate_dots")
    result["arm_positive_counts"] = {a: int(sum(r["n_emitted"] for r in fold_results[a])) for a in arms}
    result["interpretation"] = ("HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20). "
                                "Not an organizer score.")
    dump(E / "holdout_A.json", result)
    dump(E / "holdout_A_folds.json", fold_results)
    for name, s in result["scores"].items():
        print(f"A {name}: DTI={s['dti']:.5f} CI={s['ci95']} n={s['withheld_positive_pixels']}", flush=True)
    for name, d in result["paired_differences"].items():
        print(f"A delta vs {name}: {d['delta']:+.5f} CI={d['ci95']}", flush=True)

    # ---------- production LOQO surface + final dots ----------
    quad = holdout.quadrant_ids(fp)
    prob_full = np.zeros(fp.shape, np.float32)
    prod_receipts = []
    for q in range(4):
        region = quad == q
        pool_mask = MB.training_pool(valid, region)
        pos_mask = pool_mask & grid.catalogue
        clf, rec = MB.fit_hgb(X, xrows(pos_mask), xrows(pool_mask), seed=76090 + q)
        rec["quadrant"] = q
        prod_receipts.append(rec)
        pv = MB.predict_full(X, clf)
        g = MB.vec_to_grid(pv, valid)
        prob_full[valid & region] = g[valid & region]
        del pv, g
        print(f"[prod q{q}] fitted (pos={int(pos_mask.sum())})", flush=True)
    dump(E / "fit_receipts_production.json", prod_receipts)
    np.save(CACHE / "prob_full.npy", prob_full)

    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    allowed_final = valid & (d_cat > 2)
    t = time.monotonic()
    alloc2 = emit.greedy_allocate(prob_full, allowed_final, k_truth=1e12,
                                  max_dots=BUDGET_DOTS, candidate_cap=600_000)
    print(f"final greedy: {alloc2.n_dots} dots in {time.monotonic()-t:.1f}s", flush=True)
    final_dots = alloc2.emitted.astype(np.float32)
    np.save(CACHE / "final_dots.npy", final_dots)

    # ---------- proxy instruments B' and C76-pied ----------
    with rasterio.open(DATA / "external/derived_sgmc_faults_100m_u8.tif") as src:
        sgmc = src.read(1) > 0
    cat_relief = grid.catalogue & np.isfinite(relief)
    relief_p75_cat = float(np.quantile(relief[cat_relief], 0.75))
    cat_slope = grid.catalogue & np.isfinite(slope)
    slope_p80_cat = float(np.quantile(slope[cat_slope], 0.80))
    bprime = sgmc & fp & (d_cat >= 3)
    c76 = (bprime & np.isfinite(depth) & (depth >= 250)
           & np.isfinite(slope) & (slope <= slope_p80_cat)
           & (~np.isfinite(relief) | (relief <= relief_p75_cat)))
    print(f"B' truth={int(bprime.sum())}  C76 truth={int(c76.sum())} "
          f"(relief_p75={relief_p75_cat:.1f}, slope_p80={slope_p80_cat:.4f})", flush=True)
    np.save(CACHE / "truth_bprime.npy", bprime)
    np.save(CACHE / "truth_c76.npy", c76)

    proxy_arms = {"candidate_final_dots": final_dots, "h33_ref": np.nan_to_num(h33),
                  "p8_ref": np.nan_to_num(p8), "random_dots": random_dots}
    for iname, truth_arr in [("Bprime", bprime), ("C76pied", c76)]:
        fold = {"region": fp, "truth": truth_arr, "masked_known": grid.catalogue,
                "visible": grid.catalogue}
        pterms = {}
        for name, a in proxy_arms.items():
            _, tt = evaluate_holdout.evaluate(a, fold, fp)
            pterms[name] = tt
        summ = evaluate_holdout.pooled_summary(pterms, draws=1000, seed=76021,
                                               candidate="candidate_final_dots")
        summ["evidence_class"] = "PROXY-DTI"
        summ["instrument"] = iname
        summ["truth_definition"] = ("SGMC off-catalogue (d_cat>=3px)"
                                    + (" + piedmont strata (depth>=250m, slope<=cat p80, "
                                       "relief<=cat p75 where LiDAR)" if iname == "C76pied" else ""))
        for s in summ["scores"].values():
            s["evidence_class"] = "PROXY-DTI"
        dump(E / f"proxy_{iname}.json", summ)
        for name, s in summ["scores"].items():
            print(f"{iname} {name}: DTI={s['dti']:.5f} CI={s['ci95']} n={s['withheld_positive_pixels']}", flush=True)

    print(f"EXP1 DONE in {time.monotonic()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
