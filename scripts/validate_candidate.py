#!/usr/bin/env python3
"""Validate a candidate on disk without changing it; this does not authorize a slot."""
import argparse
import json
from pathlib import Path
from project import ROOT, validate_candidate

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate',type=Path)
    ap.add_argument('--sample',type=Path,default=ROOT/'data/reference/example_submission.tif')
    ap.add_argument('--catalogue',type=Path,default=ROOT/'data/reference/existing_faults.tif')
    args=ap.parse_args()
    try:
        result=validate_candidate(args.candidate,args.sample,args.catalogue)
    except (OSError,ValueError) as exc:
        result={'ok':False,'error':str(exc),'approved_for_weekly_slot':False}
    print(json.dumps(result,indent=2,allow_nan=False))
    raise SystemExit(0 if result['ok'] else 1)
