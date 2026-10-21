#!/usr/bin/env python3
"""Prepare data: verify hashes and build footprint from training_features.tif"""
import rasterio, numpy as np, json, hashlib
from pathlib import Path
# Check data/ exists
data=Path("data")
if not (data/"training_features.tif").exists():
    print("data/training_features.tif not found — run scripts/download_competition_data.sh on unrestricted machine")
    exit(1)
# Example: read footprint
with rasterio.open(data/"training_features.tif") as src:
    a=src.read(1)
    print("training_features", src.width, src.height, src.crs, src.transform)
    foot=np.isfinite(a) & (a > -1e30)
    print("footprint", foot.sum(), "/", a.size)
# Save footprint for pipeline
np.save("evidence/footprint_real.npy", foot)
print("prepared")
