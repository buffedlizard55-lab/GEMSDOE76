#!/usr/bin/env python3
"""Uniqueness audit for a G76B candidate against every registry raster held locally.

Reports, per registry raster: forward overlap (frac of MY dots within 3 px of
theirs), reverse overlap, mutual = min(forward, reverse), Jaccard of exact
dots, and Spearman rho between my probability surface and their raster values
on a fixed 200k-pixel footprint sample.  Gates (protocol rule 1,
GEMSDOE70-P8 disclosed interpretation): mutual <= 0.70 and |rho| <= 0.90.
The dense calibration lattice is reported explicitly (forward ~1.0 for any dot
raster — disclosed, mutual is the operative gate).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.grid import load_grid  # noqa: E402
from gems57 import uniqueness  # noqa: E402

import argparse

ap = argparse.ArgumentParser()
ap.add_argument("candidate", type=Path)
ap.add_argument("--surface", type=Path, default=ROOT / ".cache/g76b/prob_full.npy")
ap.add_argument("--out", type=Path, default=ROOT / "evidence/g76b-uniqueness.json")
args = ap.parse_args()

REG = ROOT / ".cache" / "registry"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_band(p: Path) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1).astype(np.float32)


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    fp = grid.footprint
    mine = read_band(args.candidate)
    mine_dots = np.nan_to_num(mine) > 0.5
    surf = np.load(args.surface)
    rng = np.random.default_rng(76000)
    sample_idx = rng.choice(np.flatnonzero(fp), 200_000, replace=False)
    surf_rank = rankdata(surf.ravel()[sample_idx])

    # my dot halo (3 px) for reverse overlap
    mine_halo = ndi.binary_dilation(mine_dots, iterations=3)

    rows = []
    files = sorted(REG.glob("*.tif"))
    for p in files:
        try:
            theirs = read_band(p)
        except Exception as exc:  # unreadable raster: report, never crash the audit
            rows.append({"file": p.name, "error": str(exc)})
            continue
        th_dots = np.isfinite(theirs) & (theirs > 0.5)
        n_mine, n_theirs = int(mine_dots.sum()), int(th_dots.sum())
        if n_mine == 0 or n_theirs == 0:
            forward = reverse = mutual = jaccard = 0.0
        else:
            th_halo = ndi.binary_dilation(th_dots, iterations=3)
            forward = float((mine_dots & th_halo).sum()) / n_mine
            reverse = float((th_dots & mine_halo).sum()) / n_theirs
            mutual = min(forward, reverse)
            inter = int((mine_dots & th_dots).sum())
            jaccard = inter / (n_mine + n_theirs - inter)
        v = np.nan_to_num(theirs.ravel()[sample_idx])
        rho = float(np.corrcoef(surf_rank, rankdata(v))[0, 1]) if np.std(v) > 0 else 0.0
        rows.append({"file": p.name, "sha256": sha(p), "n_dots": n_theirs,
                     "forward_overlap_mine_in_theirs": forward,
                     "reverse_overlap_theirs_in_mine": reverse,
                     "mutual_overlap": mutual,
                     "jaccard_exact": jaccard,
                     "surface_spearman_rho_sample200k": rho,
                     "duplicate_of_same_sha": bool(sha(p) == sha(args.candidate))})

    ok_mutual = [r for r in rows if r.get("mutual_overlap", 0) > 0]
    worst_mutual = max(rows, key=lambda r: r.get("mutual_overlap", 0))
    worst_rho = max(rows, key=lambda r: abs(r.get("surface_spearman_rho_sample200k", 0)))
    lattice = [r for r in rows if "r13-lattice" in r["file"]]
    report = {
        "evidence_class": "UNIQUENESS-AUDIT",
        "candidate": str(args.candidate),
        "candidate_sha256": sha(args.candidate),
        "n_registry_rasters_compared": len([r for r in rows if "error" not in r]),
        "n_registry_rasters_unreadable": len([r for r in rows if "error" in r]),
        "gate_mutual_le_0.70": bool(worst_mutual.get("mutual_overlap", 0) <= 0.70),
        "gate_abs_rho_le_0.90": bool(abs(worst_rho.get("surface_spearman_rho_sample200k", 0)) <= 0.90),
        "worst_mutual": worst_mutual,
        "worst_rho": worst_rho,
        "lattice_disclosure": lattice,
        "note": ("Forward overlap vs the dense calibration lattice is ~1.0 for any dot raster; "
                 "mutual overlap is the operative gate (GEMSDOE70-P8 interpretation, disclosed). "
                 "Coverage: every raster held locally under .cache/registry (76 hash-verified "
                 "scored rasters + GEMSDOE70/GEMSDOE77 published artifacts); the 60GEMSDOE "
                 "historical index lists 862 rasters total — bytes not held here are not compared."),
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1))
    print("worst mutual:", worst_mutual["file"], round(worst_mutual.get("mutual_overlap", 0), 4))
    print("worst |rho|:", worst_rho["file"], round(abs(worst_rho.get("surface_spearman_rho_sample200k", 0)), 4))
    print("gate mutual<=0.70:", report["gate_mutual_le_0.70"], " gate |rho|<=0.90:", report["gate_abs_rho_le_0.90"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
