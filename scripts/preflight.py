#!/usr/bin/env python3
"""Fail closed before experiments; never generates a placeholder prediction."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from project import ROOT, pinned_files, read_json, sha256


def audit(root=ROOT):
    pins = pinned_files(root)
    blockers=[]
    if not all(r['matches'] for r in pins):
        blockers.append('Pinned recovery files missing or modified; inspect provenance before proceeding.')
    config = read_json(root/'project.json')
    if not isinstance(config.get('method_lane'), str) or not config['method_lane'].strip():
        blockers.append('No single method lane was provided. Do not self-assign during a parallel run.')
    receipt = read_json(root/'evidence/upstream/geomorph_feature_cache.json')
    cache=[]
    for row in receipt['files']:
        # This is the template cache path, not a newly rebuilt substitute.
        path=root/row['file']
        present=path.is_file()
        matches=present and sha256(path)==row['sha256']
        cache.append({'path':row['file'],'present':present,'sha256_matches':matches})
    if not all(r['sha256_matches'] for r in cache):
        blockers.append('Template cached feature stack unavailable or hash mismatch; receipts are not array bytes.')
    registry=root/'registry/raster_inventory.json'
    if not registry.is_file():
        blockers.append('No current complete scoped raster inventory; repository metadata is not a uniqueness clearance.')
    else:
        blockers.append('Registry manifest placed but not yet audited against surface and final dots.')
    blockers.append('No locally reproduced current-best baseline, feature-alone canaries, or candidate holdout comparison.')
    sample=root/'data/reference/example_submission.tif'
    catalogue=root/'data/reference/existing_faults.tif'
    grid_check={'status':'not-run'}
    if sample.is_file() and catalogue.is_file():
        import numpy as np
        import rasterio
        from gems57 import grid
        with rasterio.open(sample) as ref, rasterio.open(catalogue) as cat:
            grid._check(ref,'bridge sample'); grid._check(cat,'bridge catalogue')
            fp=np.isfinite(ref.read(1)); mapped=(cat.read(1)>0)&fp
            grid_check={'status':'pass-bridge-relative', 'crs':str(ref.crs),
                        'shape':list(ref.shape),'transform':list(ref.transform)[:6],
                        'footprint_pixels':int(fp.sum()),'catalogue_pixels':int(mapped.sum()),
                        'official_origin_authenticated':False}
    else:
        blockers.append('Reference bridge files are missing.')
    return {'generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'status':'blocked', 'downloadable_submission':False,'safe_to_submit':False,
            'experiments_run':0,'weekly_slots_used':0,
            'blockers':blockers,'pinned_files':pins,'template_cache':cache,
            'reference_grid':grid_check,
            'external_access':'Only GitHub and package registries reachable; DrivenData, USGS, NLR, GDR and Dropbox unavailable here.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT/'evidence/preflight.json')
    args=ap.parse_args()
    result=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','safe_to_submit','blockers')},indent=2))
    sys.exit(2 if result['status']=='blocked' else 0)
