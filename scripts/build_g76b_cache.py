#!/usr/bin/env python3
"""Build the G76B feature-matrix cache once (setup, not an experiment).

Caches X (n_valid x F float32), feature names, decoded LiDAR relief and
basement depth to .cache/g76b/ so the pre-registered experiment script and any
confirmation run consume identical bytes.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems76b import features as FB  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
CACHE = ROOT / ".cache" / "g76b"
SENTINEL = -1e30


def main() -> int:
    t0 = time.monotonic()
    CACHE.mkdir(parents=True, exist_ok=True)
    with rasterio.open(DATA / "training_features.tif") as src:
        de = src.read(12).astype(np.float32)
        sl = src.read(19).astype(np.float32)
    fp_finite = np.isfinite(de) & np.isfinite(sl) & (de > SENTINEL) & (sl > SENTINEL)
    # footprint from the bridge sample
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        sub = src.read(1)
    fp = np.isfinite(sub)
    valid = ndi.binary_erosion(fp & fp_finite, iterations=12)
    print(f"valid={int(valid.sum())}", flush=True)
    X, names, aux = FB.build_feature_matrix(valid, DATA)
    np.save(CACHE / "X.npy", X)
    (CACHE / "names.json").write_text(json.dumps(names))
    np.save(CACHE / "relief.npy", aux["relief_decoded"])
    np.save(CACHE / "depth.npy", aux["depth"])
    print(f"features={len(names)} X={X.shape} in {time.monotonic()-t0:.1f}s", flush=True)
    for j, n in enumerate(names):
        col = X[:, j]
        print(f"  {n:22s} min={np.nanmin(col):+.4g} max={np.nanmax(col):+.4g} "
              f"mean={np.nanmean(col):+.4g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
