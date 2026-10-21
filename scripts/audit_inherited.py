#!/usr/bin/env python3
"""Validate quarantined inherited rasters against the real public bridge inputs.
Geometry/format audit only; never a holdout experiment, never an upload candidate.
"""
import io
import json
from pathlib import Path
import subprocess
import numpy as np
import rasterio
from project import ROOT, validate_candidate

COMMIT='ac5594779cc7b1c10794549fbda4105874acf83a'


def audit():
    archived=ROOT/'quarantine/inherited-main-ac55947/docs/downloads'
    reports=[]
    for path in sorted(archived.glob('*.tif')):
        report=validate_candidate(path,ROOT/'data/reference/example_submission.tif',
                                  ROOT/'data/reference/existing_faults.tif')
        reports.append(report)
    # Read large synthetic arrays from immutable Git history, not duplicated working files.
    simulated={}
    for name in ('footprint','catalogue'):
        raw=subprocess.check_output(['git','show',f'{COMMIT}:evidence/{name}.npy'],cwd=ROOT)
        simulated[name]=np.load(io.BytesIO(raw),allow_pickle=False)
    with rasterio.open(ROOT/'data/reference/example_submission.tif') as src:
        footprint=np.isfinite(src.read(1))
    with rasterio.open(ROOT/'data/reference/existing_faults.tif') as src:
        catalogue=(src.read(1)>0)&footprint
    return {'evidence_class':'GEOMETRY / FORMAT MEASUREMENT - not HOLDOUT-DTI or organizer result',
            'source_commit':COMMIT,'reference_origin':'public third-party bridge; official authentication pending',
            'synthetic_footprint_different_pixels':int((simulated['footprint']!=footprint).sum()),
            'synthetic_catalogue_different_pixels':int((simulated['catalogue']!=catalogue).sum()),
            'candidate_reports':reports,'safe_to_submit':False,
            'warning':'Format checks against simulated reference data did not establish scientific validity or catalogue masking.'}


if __name__=='__main__':
    result=audit()
    (ROOT/'evidence/inherited-candidate-validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='candidate_reports'},indent=2))
    for r in result['candidate_reports']:
        print(Path(r['path']).name, 'ok=',r['ok'],'outside=',r.get('mass_outside_footprint'),
              'real_cat_overlap=',r.get('catalogue_overlap_pixels'),'nonfinite_inside=',r.get('nan_inside_footprint'))
