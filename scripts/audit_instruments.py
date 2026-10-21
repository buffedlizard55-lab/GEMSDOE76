#!/usr/bin/env python3
"""Instrument audit (measurement only, not a modelling experiment).

Scores every hash-verified registry raster on three local instruments and
correlates each instrument with the user-reported live scores:

- A20   : Instrument A point estimate (gems57 hide-and-recover, seed 20).
          Registry rasters were mostly built with full-catalogue knowledge,
          so A20 is NOT fold-honest for them; most also had their near-catalogue
          dots pruned against the full catalogue (incl. withheld truth), which
          structurally deflates A20.  Included to quantify that bias.
- Bprime: SGMC off-catalogue truth (d_cat >= 3 px), catalogue-masked.
- C76   : Bprime restricted to piedmont strata (Exp-1 definition).

Also scores unscored headline files (GEMSDOE70 P9 hero, P8 file, this repo's
Exp-2 candidate) for the selector table.  Live numbers are USER-REPORTED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import holdout, metric  # noqa: E402
from gems57.grid import load_grid  # noqa: E402

REG = ROOT / ".cache" / "registry"
OUT = ROOT / "evidence" / "instrument_audit.json"


def load_dots(path: Path, fp: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(1)
    return (np.isfinite(a) & (a > 0) & fp)


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    fp, cat = grid.footprint, grid.catalogue
    folds, _ = holdout.buffered_component_draw(grid, seed=20, buffer_px=3, boundary_px=12)
    masked_known = folds[0]["masked_known"]

    bprime = np.load(ROOT / ".cache/exp1/truth_bprime.npy")
    c76 = np.load(ROOT / ".cache/exp1/truth_c76.npy")

    ledger = json.loads((REG / "ledger.json").read_text())
    rows = []
    for rec in ledger:
        if not rec.get("sha_match"):
            continue
        rows.append({"file": rec["file"], "live_user_reported": rec["live_user_reported"],
                     "path": str(REG / rec["file"])})
    # unscored headline files from local clones
    sib = Path("/home/user/siblings")
    extra = [
        ("gems70-p5-multiphysics-submodular-37654-20261020.tif", None,
         sib / "GEMSDOE70/docs/downloads/gems70-p5-multiphysics-submodular-37654-20261020.tif"),
        ("gems70-p5-dual-submod300-oof38k-20261020.tif", 0.2478,
         sib / "GEMSDOE70/docs/downloads/gems70-p5-dual-submod300-oof38k-20261020.tif"),
        ("gems70-e2-alluvialstep-38000-20261020T221218Z-zeros.tif", None,
         sib / "GEMSDOE70/docs/downloads/gems70-e2-alluvialstep-38000-20261020T221218Z-zeros-DO-NOT-SUBMIT.tif"),
    ]
    for name, live, p in extra:
        if p.exists():
            rows.append({"file": name, "live_user_reported": live, "path": str(p)})

    # precompute per-fold truth kernel fields for A20 fast scoring
    fold_truths = []
    for f in folds:
        t = f["truth"] & f["region"] & ~masked_known
        fold_truths.append((t, f["region"]))

    results = []
    for row in rows:
        dots = load_dots(Path(row["path"]), fp)
        # A20 pooled point estimate
        tp = fp_ = fn = 0.0
        for t, region in fold_truths:
            active = region & ~masked_known & fp
            r = metric.dti_binary(dots, t, valid=active)
            tp += r["tp"]; fp_ += r["fp"]; fn += r["fn"]
        a20 = tp / (tp + 0.2 * fp_ + 0.8 * fn + 1e-12)
        b = metric.dti_binary(dots, bprime, valid=fp, known=cat)["dti"]
        c = metric.dti_binary(dots, c76, valid=fp, known=cat)["dti"]
        results.append({**row, "n_dots": int(dots.sum()), "A20": float(a20),
                        "Bprime": float(b), "C76pied": float(c)})
        print(f"{row['file'][:64]:64s} live={row['live_user_reported']} A20={a20:.4f} "
              f"B'={b:.4f} C76={c:.4f} dots={int(dots.sum())}", flush=True)

    scored = [r for r in results if r["live_user_reported"] is not None]
    corr = {}
    for inst in ["A20", "Bprime", "C76pied"]:
        x = np.array([r[inst] for r in scored])
        y = np.array([r["live_user_reported"] for r in scored])
        rho, prho = spearmanr(x, y)
        r_, pr = pearsonr(x, y)
        corr[inst] = {"spearman_rho": float(rho), "spearman_p": float(prho),
                      "pearson_r": float(r_), "pearson_p": float(pr), "n": len(scored)}
        print(f"{inst}: Spearman rho={rho:.4f} (p={prho:.2e}), Pearson r={r_:.4f} (p={pr:.2e}), n={len(scored)}")

    # leave-one-out Spearman stability for C76
    x = np.array([r["C76pied"] for r in scored]); y = np.array([r["live_user_reported"] for r in scored])
    loos = []
    for i in range(len(scored)):
        m = np.ones(len(scored), bool); m[i] = False
        loos.append(float(spearmanr(x[m], y[m]).statistic))
    corr["C76pied"]["loo_spearman_min"] = min(loos)
    corr["C76pied"]["loo_spearman_max"] = max(loos)

    OUT.write_text(json.dumps({
        "evidence_class": "INSTRUMENT-AUDIT (local proxies vs USER-REPORTED live scores; "
                          "no organizer receipts)",
        "instruments": {"A20": "gems57 hide-and-recover seed20 pooled point estimate "
                               "(not fold-honest for registry rasters)",
                        "Bprime": f"SGMC off-catalogue d_cat>=3px, n={int(bprime.sum())}",
                        "C76pied": f"Bprime + piedmont strata, n={int(c76.sum())}"},
        "correlations_vs_live_user_reported": corr,
        "rows": results,
    }, indent=1))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
