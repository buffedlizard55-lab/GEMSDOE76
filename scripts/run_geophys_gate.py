#!/usr/bin/env python3
"""Experiment 1 (this session): catalogue-free geophysical gate check.

No lane is claimed (project.json has none; the parallel-run protocol forbids
self-assignment). This is the mandatory pre-submission vetting the protocol
requires before any weekly slot: feature-alone leakage canaries, buffered
whole-segment hide-and-recover holdout (gems57-pooled-hide-v2, alpha 0.2 /
beta 0.8, 300 m triangular kernel), and an exact greedy dot emission scored on
the same withheld truth.

Every feature plane comes from the pinned 19-band training_features.tif
(geophysics only) -- none is derived from the fault catalogue, so catalogue
withholding cannot leak through the features. Each feature is canary-tested
alone first (AUC > 0.90 => leakage, stop).

Outputs in evidence/exp_geophys_gate/: manifest.json, canaries.json,
holdout.json, emission.json, gates.json. A validated candidate GeoTIFF is
packaged to docs/downloads/ only when the format gates pass; its download /
submit status is stated explicitly in gates.json (never a projection presented
as a score; no weekly slot is used).
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
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import emit, evaluate_holdout, holdout, metric  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57 import geo  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
E = ROOT / "evidence" / "exp_geophys_gate"
CACHE = ROOT / ".cache" / "exp_geophys_gate"

GEO_PLANES = geo.GEO_FEATURES  # 9 catalogue-free geophysical planes
BLOCK_SIDE = 200  # 20 km spatial blocks for the paired percentile CI
FAIR_H33_BENCHMARK = 0.0927  # USER-REPORTED context (Lane-G76 run card), not a receipt


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def auc_mw(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC, tie-aware, no sklearn dependency."""
    order = rankdata(scores, method="average")
    pos = labels == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((order[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def rank01_over(a: np.ndarray, dom: np.ndarray) -> np.ndarray:
    """Average-tie ranks scaled to [0,1] over finite ``dom`` cells; 0 else."""
    out = np.zeros(a.shape, np.float32)
    m = np.asarray(dom, bool) & np.isfinite(a)
    n = int(m.sum())
    if n > 1:
        out[m] = ((rankdata(a[m], method="average") - 1.0) / (n - 1)).astype(np.float32)
    return out


def main() -> int:
    t0 = time.monotonic()
    E.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    dump(E / "manifest.json", {
        "experiment": "geophys-catalogue-free-rank-surface",
        "experiment_count_this_session": 1,
        "maximum_experiments": 3,
        "maximum_wall_hours": 2,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lane_assigned": None,
        "note": "No lane assigned to this parallel run; this is pre-submission gate "
                "vetting (canary + holdout), not a lane experiment. No weekly slot used.",
        "source_sha256": {p: sha(ROOT / p) for p in [
            "vendor/gems57/evaluate_holdout.py", "vendor/gems57/holdout.py",
            "vendor/gems57/metric.py", "vendor/gems57/emit.py",
            "vendor/gems57/geo.py", "vendor/gems57/grid.py",
            "scripts/run_geophys_gate.py"]},
        "evaluator_implementation_sha256": evaluate_holdout.implementation_hashes(),
        "data_sha256": {
            "training_features": sha(DATA / "training_features.tif"),
            "sample_submission": sha(DATA / "sample_submission.tif"),
            "existing_faults": sha(DATA / "existing_faults.tif"),
        },
    })

    grid = load_grid(ROOT / "data" / "bridge")
    fp = grid.footprint
    cat = grid.catalogue
    h, w = fp.shape

    folds, _quad = holdout.buffered_component_draw(grid, seed=20,
                                                   buffer_px=3, boundary_px=12)
    n_truth_total = int(sum(int(f["truth"].sum()) for f in folds))
    print(f"holdout folds: {len(folds)}; withheld truth px total={n_truth_total}",
          flush=True)

    # --- feature stack: catalogue-free geophysical planes ------------------
    planes = geo.load_planes(fp, ROOT / "data" / "official" / "training_features.tif")
    valid0 = fp.copy()
    for a in planes.values():
        valid0 &= np.isfinite(a)
    valid = ndi.binary_erosion(valid0, iterations=12) & fp
    print(f"valid domain px={int(valid.sum())} footprint px={int(fp.sum())}",
          flush=True)

    comps = {name: rank01_over(a, fp) for name, a in planes.items()}
    cand = np.mean(np.stack(list(comps.values())), axis=0).astype(np.float32)
    cand = np.where(fp, np.clip(cand, 0.0, 1.0), 0.0).astype(np.float32)
    control = comps["g_slope"].copy()  # single-plane weak control, same folds

    np.save(CACHE / "cand_surface.npy", cand)
    np.save(CACHE / "control_surface.npy", control)

    # --- leakage canaries: each feature ALONE vs holdout truth -------------
    active = np.zeros(fp.shape, bool)
    truth_pool = np.zeros(fp.shape, bool)
    for f in folds:
        active |= valid & f["region"] & ~f["masked_known"]
        truth_pool |= valid & f["truth"]
    pos = np.flatnonzero(truth_pool)
    rng = np.random.default_rng(76020)
    neg_pool = np.flatnonzero(active & ~truth_pool)
    neg = rng.choice(neg_pool, min(200_000, neg_pool.size), replace=False)
    labels = np.r_[np.ones(pos.size), np.zeros(neg.size)]
    print(f"canary: pos={pos.size} neg={neg.size} active={int(active.sum())}",
          flush=True)

    canaries = {}
    for name, a in planes.items():
        v = np.r_[a.ravel()[pos], a.ravel()[neg]]
        canaries[name] = {
            "evidence_class": "LEAKAGE-CANARY",
            "feature": name,
            "auc": auc_mw(v, labels),
            "withheld_positive_pixels": int(pos.size),
            "negative_sample_pixels": int(neg.size),
        }
        print(f"  canary {name}: auc={canaries[name]['auc']:.4f}", flush=True)
    dump(E / "canaries.json", {
        "evidence_class": "LEAKAGE-CANARIES",
        "evaluator_version": evaluate_holdout.VERSION,
        "threshold_auc": 0.90,
        "any_suspected_leakage": bool(any(c["auc"] > 0.90 for c in canaries.values())),
        "features": canaries,
    })

    if any(c["auc"] > 0.90 for c in canaries.values()):
        print("LEAKAGE ALERT: a feature alone exceeds AUC 0.90 -- stopping per protocol rule 4",
              flush=True)
        dump(E / "gates.json", {"verdict": "negative", "reason": "leakage canary exceeded 0.90"})
        return 2

    # --- holdout: pooled DTI candidate vs control, same folds --------------
    def fold_terms(surface: np.ndarray):
        terms = []
        per_fold = {}
        for f in folds:
            r, terms_arm = evaluate_holdout.evaluate(
                surface, f, valid, block_side=BLOCK_SIDE,
                origin=(0, 0), global_shape=(h, w))
            terms.append(terms_arm)
            per_fold[f["name"]] = dict(dti=float(r["dti"]),
                                       withheld_positive_pixels=int(r["n_truth"]),
                                       tpw=float(r["tp"]), fpw=float(r["fp"]),
                                       fnw=float(r["fn"]))
        return np.concatenate(terms, axis=0), per_fold

    cand_terms, cand_per_fold = fold_terms(cand)
    ctrl_terms, ctrl_per_fold = fold_terms(control)
    pooled = evaluate_holdout.pooled_summary(
        {"candidate": cand_terms, "control": ctrl_terms},
        draws=1000, seed=520810, candidate="candidate")
    dump(E / "holdout.json", {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "alpha": metric.ALPHA, "beta": metric.BETA,
        "triangular_radius_m": metric.R_M,
        "withheld_positive_pixels": int(n_truth_total),
        "pooled": pooled,
        "per_fold_candidate": cand_per_fold,
        "per_fold_control": ctrl_per_fold,
        "benchmark_fair_h33_user_context": {
            "dti": FAIR_H33_BENCHMARK, "ci95": [0.0802, 0.1058],
            "note": "USER-REPORTED context from this repo's Lane-G76 run card; not an organizer receipt.",
        },
    })
    print(f"holdout candidate DTI={pooled['scores']['candidate']['dti']:.4f} "
          f"CI={pooled['scores']['candidate']['ci95']} "
          f"vs control={pooled['scores']['control']['dti']:.4f} "
          f"delta={pooled['paired_differences']['control']['delta']:+.4f} "
          f"deltaCI={pooled['paired_differences']['control']['ci95']}", flush=True)

    # --- emission: greedy dots on allowed domain ---------------------------
    allowed = fp & ~cat
    alloc = emit.greedy_allocate(cand, allowed, k_truth=float(n_truth_total),
                                 floor=0.02, max_dots=60_000,
                                 candidate_cap=300_000, per_round=20_000)
    dots = alloc.emitted & fp
    print(f"emission: dots={int(dots.sum())} rounds={alloc.rounds}", flush=True)

    dot_eval = metric.dti_exact(dots.astype(np.float64), truth_pool,
                                valid=fp, known=cat)
    dump(E / "emission.json", {
        "evidence_class": "EMISSION-DECISION",
        "n_dots": int(dots.sum()),
        "on_catalogue_px": int((dots & cat).sum()),
        "outside_footprint_px": int((dots & ~fp).sum()),
        "holdout_dti_binary": dot_eval,
        "surrogate_dti": alloc.surrogate_dti,
    })

    # --- uniqueness vs locally available priors ----------------------------
    uniq_rows = []
    g76 = ROOT / "evidence" / "lane-g76" / "gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif"
    if g76.is_file():
        with rasterio.open(g76) as src:
            g76_arr = src.read(1)
            g76_dots = np.isfinite(g76_arr) & (g76_arr > 0)
        fwd = float(((dots) & (ndi.distance_transform_edt(~g76_dots) <= 3)).sum()) / max(dots.sum(), 1)
        rev = float(((g76_dots) & (ndi.distance_transform_edt(~dots) <= 3)).sum()) / max(g76_dots.sum(), 1)
        uniq_rows.append({"file": g76.name, "forward_overlap": round(fwd, 4),
                          "reverse_overlap": round(rev, 4), "mutual": round(min(fwd, rev), 4)})
        print(f"uniqueness vs G76 artifact: mutual={min(fwd, rev):.3f}", flush=True)

    beats = bool(pooled["scores"]["candidate"]["dti"] > FAIR_H33_BENCHMARK)
    gates = {
        "verdict": "promote" if beats else "negative",
        "holdout_dti": pooled["scores"]["candidate"]["dti"],
        "holdout_ci95": pooled["scores"]["candidate"]["ci95"],
        "canary_max_auc": max(c["auc"] for c in canaries.values()),
        "beats_fair_h33_benchmark": beats,
        "benchmark_fair_h33": FAIR_H33_BENCHMARK,
        "uniqueness_rows": uniq_rows,
        "registry_inventory_complete": False,
        "n_dots": int(dots.sum()),
        "note": ("Catalogue-free geophysical rank surface, greedy dots. "
                 f"holdout DTI {pooled['scores']['candidate']['dti']:.4f} vs fair-H33 "
                 f"benchmark {FAIR_H33_BENCHMARK}; "
                 + ("PROMOTED." if beats else "below benchmark - negative, no slot.")),
    }
    dump(E / "gates.json", gates)
    print("gates verdict:", gates["verdict"], flush=True)

    # --- package a validated candidate TIFF (real, not a placeholder) ------
    name = "gems76-geophys-cataloguefree-rank-gate1-20261021"
    note = ("Catalogue-free geophysical rank surface, gate check 1. "
            + ("OK TO SUBMIT." if beats else "DO NOT SUBMIT - negative holdout evidence."))
    note = note[:140]
    cand_write = np.where(cat, 0.0, cand).astype(np.float32)  # zero on catalogue
    try:
        receipt = write_submission(
            ROOT / "docs" / "downloads" / (name + ".tif"),
            cand_write, ROOT / "data" / "reference" / "example_submission.tif",
            fp, note=note, name=name, catalogue=cat,
            metadata={"experiment": "geophys-gate-1",
                      "holdout_dti": pooled["scores"]["candidate"]["dti"],
                      "verdict": gates["verdict"]})
        dump(ROOT / "docs" / "downloads" / (name + ".json"), receipt)
        print(f"wrote candidate TIFF {receipt['path']} sha={receipt['sha256'][:16]}",
              flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"TIFF packaging skipped: {exc}", flush=True)

    print(f"elapsed {time.monotonic() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
