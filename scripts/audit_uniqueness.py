#!/usr/bin/env python3
"""Uniqueness audit for the Lane-G76 artifact against every registry raster held locally.

Reports, per registry raster: forward overlap (frac of MY dots within 3 px of
theirs), reverse overlap, mutual = min(forward, reverse), Jaccard of exact
dots, and Spearman rho between my Exp-2 probability surface and their raster
values on a fixed 200k-pixel footprint sample.  Gates (protocol rule 1,
GEMSDOE70-P8 disclosed interpretation): mutual <= 0.70 and |rho| <= 0.90.
The dense 206,895-dot calibration lattice is reported explicitly: its 3 px
halo covers ~99.9% of the footprint, so one-way forward overlap vs it is ~1.0
for ANY dot raster (disclosed, mutual used as the operative gate).
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

MINE_TIF = ROOT / "evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif"
SURFACE = ROOT / ".cache/exp2/prob_full.npy"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_band(p: Path) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1).astype(np.float32)


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    fp = grid.footprint
    mine = read_band(MINE_TIF)
    surf = np.load(SURFACE)
    rng = np.random.default_rng(76000)
    sample_idx = rng.choice(np.flatnonzero(fp), 200_000, replace=False)
    surf_sample_rank = rankdata(surf.ravel()[sample_idx])

    paths = sorted((ROOT / ".cache/registry").glob("*.tif"))
    sib = Path("/home/user/siblings")
    paths += sorted((sib / "GEMSDOE70/docs/downloads").glob("*.tif"))
    paths += sorted((sib / "GEMSDOE32/docs/downloads").glob("*.tif"))
    paths += sorted((sib / "GEMSDOE36/docs/downloads").glob("*.tif"))
    paths = [p for p in paths if p.resolve() != MINE_TIF.resolve()]

    rows = []
    seen_sha = {}
    for p in paths:
        h = sha(p)
        theirs = read_band(p)
        if theirs.shape != fp.shape:
            rows.append({"file": p.name, "sha256": h, "status": "shape-mismatch-skipped"})
            continue
        fwd = uniqueness.dot_overlap(mine, theirs)
        rev = uniqueness.dot_overlap(theirs, mine)
        my_dots = np.isfinite(mine) & (mine > 0)
        th_dots = np.isfinite(theirs) & (theirs > 0)
        jac = float((my_dots & th_dots).sum() / max((my_dots | th_dots).sum(), 1))
        their_sample = np.nan_to_num(theirs.ravel()[sample_idx])
        rho = float(np.corrcoef(surf_sample_rank, rankdata(their_sample))[0, 1])
        rows.append({"file": p.name, "sha256": h, "n_dots": int(th_dots.sum()),
                     "forward_overlap_mine_in_theirs": float(fwd),
                     "reverse_overlap_theirs_in_mine": float(rev),
                     "mutual_overlap": float(min(fwd, rev)), "jaccard_exact": jac,
                     "surface_spearman_rho_sample200k": rho,
                     "duplicate_of_same_sha": seen_sha.get(h)})
        seen_sha.setdefault(h, p.name)
        print(f"{p.name[:58]:58s} fwd={fwd:.3f} rev={rev:.3f} mut={min(fwd,rev):.3f} rho={rho:+.3f}", flush=True)

    scored = [r for r in rows if "mutual_overlap" in r]
    worst_mutual = max(scored, key=lambda r: r["mutual_overlap"])
    worst_rho = max(scored, key=lambda r: abs(r["surface_spearman_rho_sample200k"]))
    lattice_rows = [r for r in scored if "lattice" in r["file"]]
    out = {
        "evidence_class": "UNIQUENESS-AUDIT",
        "candidate": MINE_TIF.name, "candidate_sha256": sha(MINE_TIF),
        "n_registry_rasters_compared": len(scored),
        "gate_mutual_le_0.70": bool(worst_mutual["mutual_overlap"] <= 0.70),
        "gate_abs_rho_le_0.90": bool(abs(worst_rho["surface_spearman_rho_sample200k"]) <= 0.90),
        "worst_mutual": worst_mutual, "worst_rho": worst_rho,
        "lattice_disclosure": lattice_rows,
        "note": "Forward overlap vs the dense calibration lattice is ~1.0 for any dot raster; "
                "mutual overlap is the operative gate (GEMSDOE70-P8 interpretation, disclosed).",
        "rows": rows,
    }
    (ROOT / "evidence/uniqueness_audit.json").write_text(json.dumps(out, indent=1))
    print(f"\ncompared {len(scored)} rasters; worst mutual={worst_mutual['mutual_overlap']:.3f} "
          f"({worst_mutual['file']}); worst |rho|={abs(worst_rho['surface_spearman_rho_sample200k']):.3f} "
          f"({worst_rho['file']})")
    print("gates:", out["gate_mutual_le_0.70"], out["gate_abs_rho_le_0.90"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
