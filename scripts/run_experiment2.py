#!/usr/bin/env python3
"""Experiment 2 (pre-registered amendment): logistic combiner over Lane-G76 components.

Same instruments, arms structure and gates as Exp 1. One run only.
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
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import emit, evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems76 import features as F  # noqa: E402
from gems76 import model as M  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
E = ROOT / "evidence" / "exp2"
CACHE = ROOT / ".cache" / "exp2"
BUDGET_DOTS = 37_654
SENTINEL = -1e30


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


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
        raise RuntimeError("Exp2 already attempted; inspect evidence/exp2 (no silent reruns).")
    E.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    dump(E / "manifest.json", {
        "experiment": "G76-EXP2-logistic-combiner", "experiment_count_this_session": 2,
        "maximum_experiments": 3,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "preregistration_sha256": sha(ROOT / "docs/preregistration-g76.md"),
        "amendment_sha256": sha(ROOT / "docs/preregistration-g76-amendment-exp2.md"),
        "source_sha256": {p: sha(ROOT / p) for p in
                          ["src/gems76/features.py", "src/gems76/model.py",
                           "scripts/run_experiment2.py"]},
        "evaluator_implementation_sha256": evaluate_holdout.implementation_hashes(),
    })

    grid = load_grid(ROOT / "data" / "bridge")
    fp = grid.footprint
    with rasterio.open(DATA / "training_features.tif") as src:
        raw = {}
        for idx, name in [(12, "det_elev"), (19, "det_elev_slope")]:
            a = src.read(idx).astype(np.float32)
            a[(a <= SENTINEL) | ~np.isfinite(a) | ~fp] = np.nan
            raw[name] = a
    with rasterio.open(DATA / "external/lidar_scarp_features_u8.tif") as src:
        stack = {name: src.read(i + 1) for i, name in enumerate(F.LIDAR_BANDS)}
    lidar = F.decode_lidar(stack)
    del stack

    valid0 = fp & np.isfinite(raw["det_elev"]) & np.isfinite(raw["det_elev_slope"])
    valid = ndi.binary_erosion(valid0, iterations=12)

    folds, _ = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    masked_known = folds[0]["masked_known"]

    # Lane components needed by the combiner (catalogue-free constructions).
    has_lidar = fp & np.isfinite(lidar["valid"]) & (lidar["valid"] > 0)
    base = (np.nan_to_num(lidar["step_max"])
            * np.sqrt(np.maximum(np.nan_to_num(lidar["lapneg_max"]), 0.0)
                      * np.maximum(np.nan_to_num(lidar["lappos_max"]), 0.0))).astype(np.float32)
    persisted = F.strike_persistence(base, lidar["strike"], has_lidar)
    fallback = F.fallback_response(raw["det_elev"], fp & ~has_lidar & np.isfinite(raw["det_elev"]))
    feats = M.assemble_features(lidar, raw["det_elev"], fp, persisted, fallback)

    # Holdout-honest fit: positives = visible catalogue; domain excludes withheld px
    # implicitly because withheld pixels are catalogue pixels and negatives exclude
    # the full catalogue (masked_known | hidden == catalogue).
    train_domain = valid.copy()
    prob, receipt = M.fit_surface(feats, visible, train_domain, seed=76020)
    dump(E / "model_receipt_holdout.json", receipt)
    np.save(CACHE / "prob_holdout.npy", prob)
    print("holdout model coefficients:", json.dumps(receipt["coefficients"], indent=0), flush=True)

    # Canaries incl. fitted probability (in-sample fit seen here is on VISIBLE only;
    # withheld positives were never in training, so this AUC is an honest holdout AUC).
    truth = np.zeros(fp.shape, bool)
    active = np.zeros(fp.shape, bool)
    for f in folds:
        active |= valid & f["region"] & ~f["masked_known"]
        truth |= valid & f["truth"]
    pos = np.flatnonzero(truth)
    rng = np.random.default_rng(76020)
    neg = rng.choice(np.flatnonzero(active & ~truth), 200_000, replace=False)
    labels = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    canaries = {}
    for name in M.FEATURE_NAMES + ["fitted_probability"]:
        a = prob if name == "fitted_probability" else feats[name]
        v = np.r_[a.ravel()[pos], a.ravel()[neg]]
        auc = float(roc_auc_score(labels, v))
        canaries[name] = {"evidence_class": "LEAKAGE-CANARY", "auc": auc,
                          "inverse_auc": 1 - auc,
                          "withheld_positive_pixels": int(len(pos)),
                          "negative_sample_pixels": int(len(neg)),
                          "suspected_leakage": bool(max(auc, 1 - auc) > 0.90)}
        print("canary", name, round(auc, 4), flush=True)
    dump(E / "canaries.json", canaries)
    if any(c["suspected_leakage"] for c in canaries.values()):
        raise RuntimeError("CANARY STOP: AUC > 0.90 — leakage until proven otherwise.")

    allowed_holdout = valid & ~masked_known
    print("greedy #1 (holdout budget arm, cap 600k)…", flush=True)
    t = time.monotonic()
    alloc = emit.greedy_allocate(prob, allowed_holdout, k_truth=1e12,
                                 max_dots=BUDGET_DOTS, candidate_cap=600_000)
    print(f"greedy #1: {alloc.n_dots} dots in {time.monotonic()-t:.1f}s", flush=True)
    cand_dots = alloc.emitted.astype(np.float32)
    np.save(CACHE / "cand_dots_holdout.npy", cand_dots)

    def read_tif(p: Path) -> np.ndarray:
        with rasterio.open(p) as src:
            return src.read(1).astype(np.float32)

    sib = Path("/home/user/siblings")
    d28 = read_tif(sib / "GEMSDOE32/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif")
    h33 = read_tif(sib / "GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    d_vis = ndi.distance_transform_edt(~masked_known)
    fair_h33 = ((d28 > 0) & (d_vis > 2)).astype(np.float32)
    random_dots = np.zeros(fp.shape, np.float32)
    ids = rng.choice(np.flatnonzero(valid & ~masked_known), BUDGET_DOTS, replace=False)
    random_dots.ravel()[ids] = 1.0

    arms = {"candidate_dots": cand_dots,
            "candidate_surface": np.where(valid, prob, 0).astype(np.float32),
            "fair_h33": fair_h33, "random_dots": random_dots}
    arm_dots = {k: int((a > 0).sum()) for k, a in arms.items()}
    print("arm positive counts:", arm_dots, flush=True)
    terms, fold_results = {}, {}
    for name, a in arms.items():
        per_fold = [cropped_eval(f, a, valid) for f in folds]
        terms[name] = sum(tt for _, tt in per_fold)
        fold_results[name] = [r for r, _ in per_fold]
        print(name, "Instrument-A evaluated", flush=True)
    result = evaluate_holdout.pooled_summary(terms, draws=1000, seed=76020,
                                             candidate="candidate_dots")
    result["arm_positive_counts"] = arm_dots
    result["interpretation"] = ("HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20). "
                                "Not an organizer score.")
    dump(E / "holdout_A.json", result)
    dump(E / "holdout_A_folds.json", fold_results)
    for name, s in result["scores"].items():
        print(f"A {name}: DTI={s['dti']:.5f} CI={s['ci95']} n={s['withheld_positive_pixels']}", flush=True)
    for name, d in result["paired_differences"].items():
        print(f"A delta vs {name}: {d['delta']:+.5f} CI={d['ci95']}", flush=True)

    # Final model on the full catalogue + final-style dots; proxy instruments.
    prob_full, receipt_full = M.fit_surface(feats, grid.catalogue, valid, seed=76099)
    dump(E / "model_receipt_full.json", receipt_full)
    np.save(CACHE / "prob_full.npy", prob_full)
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    valid_final = ndi.binary_erosion(valid0, iterations=3)
    allowed_final = valid_final & (d_cat > 2)
    print("greedy #2 (final-style dots)…", flush=True)
    t = time.monotonic()
    alloc2 = emit.greedy_allocate(prob_full, allowed_final, k_truth=1e12,
                                  max_dots=BUDGET_DOTS, candidate_cap=600_000)
    print(f"greedy #2: {alloc2.n_dots} dots in {time.monotonic()-t:.1f}s", flush=True)
    final_dots = alloc2.emitted.astype(np.float32)
    np.save(CACHE / "final_dots.npy", final_dots)

    bprime = np.load(ROOT / ".cache/exp1/truth_bprime.npy")
    c76 = np.load(ROOT / ".cache/exp1/truth_c76.npy")
    proxy_arms = {"candidate_final_dots": final_dots, "h33_ref": np.nan_to_num(h33),
                  "random_dots": random_dots}
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
        for s in summ["scores"].values():
            s["evidence_class"] = "PROXY-DTI"
        dump(E / f"proxy_{iname}.json", summ)
        for name, s in summ["scores"].items():
            print(f"{iname} {name}: DTI={s['dti']:.5f} CI={s['ci95']} n={s['withheld_positive_pixels']}", flush=True)

    print(f"EXP2 DONE in {time.monotonic()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
