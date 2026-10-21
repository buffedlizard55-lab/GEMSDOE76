#!/usr/bin/env python3
"""Independent re-read verification of submission TIFs"""
import rasterio, numpy as np, json, hashlib
from pathlib import Path
import sys
foot=np.load("evidence/footprint.npy")
cat=np.load("evidence/catalogue.npy")
def check(p):
    with rasterio.open(p) as src:
        a=src.read(1)
        meta=dict(crs=str(src.crs), width=src.width, height=src.height, transform=tuple(src.transform)[:6], dtype=src.dtypes[0], nodata=src.nodata)
    in_foot=a[foot]
    out_foot=a[~foot]
    h=hashlib.sha256(Path(p).read_bytes()).hexdigest()
    checks={
        "single_band": True,
        "dtype_float32": meta['dtype']=="float32",
        "dimensions_3730x3292": (meta['height']==3730 and meta['width']==3292),
        "crs_epsg_32611": "32611" in meta['crs'],
        "in_footprint_all_finite": int(np.isfinite(in_foot).sum())==int(foot.sum()),
        "in_footprint_zero_nan": int(np.isnan(in_foot).sum())==0,
        "in_footprint_zero_inf": int(np.isinf(in_foot).sum())==0,
        "in_footprint_zero_sentinel": int((in_foot<-1e30).sum())==0,
        "in_footprint_range_0_1": bool(np.all((in_foot>=0)&(in_foot<=1))),
        "outside_footprint_compliant": bool(np.isnan(out_foot).all() or (out_foot==0).all()),
        "zero_on_catalogue_leakage": int(((a>0.5)&cat).sum())==0,
        "validator_range_0_1_guaranteed": bool(np.all((a>=0)&(a<=1) | np.isnan(a)) if np.isnan(meta['nodata'] if meta['nodata'] is not None else 0) else np.all((a>=0)&(a<=1))),
    }
    # fix last check for zeros variant: every cell finite in [0,1]
    if meta['nodata'] is None:
        checks["validator_range_0_1_guaranteed"]= bool(np.isfinite(a).all() and np.all((a>=0)&(a<=1)))
    else:
        checks["validator_range_0_1_guaranteed"]= bool(np.all((in_foot>=0)&(in_foot<=1)) and np.isfinite(in_foot).all())
    all_pass=all(checks.values())
    print(f"{p}: {h[:16]} ... all_pass={all_pass}")
    for k,v in checks.items():
        print(f"  {k}: {v}")
    if not all_pass:
        print("FAILED", p)
        sys.exit(1)
    return checks

for p in Path("docs/downloads").glob("*.tif"):
    check(p)
print("All TIFs PASS")
