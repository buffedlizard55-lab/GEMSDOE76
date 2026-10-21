#!/usr/bin/env python3
"""Reproduce local software checks and write an honest verification receipt.

These are software checks, not model experiments or competition submissions.
Run scripts/audit_inherited.py separately in a checkout with the recorded source
commit available to reproduce the inherited-mask comparisons.
"""
import datetime as dt
import json
import subprocess
import sys
from project import ROOT


def run(command, expected=0):
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    result={'command':command,'exit_code':p.returncode,'expected_exit_code':expected,
            'passed':p.returncode==expected,'stdout':p.stdout,'stderr':p.stderr}
    if not result['passed']:
        print(p.stdout,p.stderr,file=sys.stderr)
    return result


if __name__=='__main__':
    python=sys.executable
    commands=[([python,'scripts/recover_inputs.py'],0),
              ([python,'scripts/preflight.py'],2),
              ([python,'scripts/build_site.py'],0),
              ([python,'scripts/check_site.py'],0),
              ([python,'-m','pytest','-q'],0),
              ([python,'-m','compileall','-q','scripts','tests','vendor'],0),
              (['git','diff','--check'],0)]
    results=[run(cmd,expected) for cmd,expected in commands]
    receipt={'generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
             'evidence_class':'SOFTWARE VERIFICATION - NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED',
             'all_checks_passed':all(r['passed'] for r in results),
             'passes_completed':[
                 'Pass 1: implemented pinned recovery, audits, research proposals, preflight and Pages.',
                 'Pass 2: regression tests; corrected repository-name mapping, affine dependency warning and compatibility commands.',
                 'Pass 3: integrated updated main, independently rejected synthetic candidates, checked preserved bytes and reran full suite.'],
             'results':results,
             'scientific_experiments_run':0,'weekly_slots_used':0,
             'unique_submission_generated':False,'safe_to_submit':False,
             'full_scientific_request_satisfied':False,
             'remaining_blockers':'Lane assignment, pinned cache array bytes, complete scoped raster registry, official authentication, matched baseline/canary/holdout evidence.',
             'warning':'Passing this verification does not satisfy missing scientific prerequisites or authorize a weekly slot.'}
    target=ROOT/'evidence/verification.json'
    target.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    # Publish the receipt only after its commands have really run.
    extra=run([python,'scripts/build_site.py'])
    final=run([python,'scripts/check_site.py'])
    print(json.dumps({k:receipt[k] for k in ('all_checks_passed','unique_submission_generated','safe_to_submit','full_scientific_request_satisfied')},indent=2))
    raise SystemExit(0 if receipt['all_checks_passed'] and extra['passed'] and final['passed'] else 1)
