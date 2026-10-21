#!/usr/bin/env python3
"""Read public GitHub mirrors; never calls DrivenData or spends a slot."""
import concurrent.futures
import datetime as dt
import json
import pathlib
import subprocess

OWNER = 'buffedlizard55-lab'
NAMES = ['GEMSDOE','6GEMSDOE','GEMSDOE3','GEMSDOE2','GEMSDOE4','5GEMSDOE',
         '7GEMSDOE','8GEMSDOE','GEMSDOE9','11GEMSDOE','12GEMSDOE','15GEMSDOE',
         '14GEMSDOE','17GEMSDOE','18GEMSDOE','19GEMSDOE','GEMSDOE10','13GEMSDOE',
         '16GEMSDOE','GEMSDOE21','20GEMSDOE'] + [(str(i)+'GEMSDOE') if 55 <= i <= 62 else ('GEMSDOE'+str(i)) for i in range(22,79)]
ROOT = pathlib.Path(__file__).resolve().parents[1]

def inspect(name):
    endpoint = f'repos/{OWNER}/{name}'
    p = subprocess.run(['gh','api', endpoint], capture_output=True, text=True)
    row = {'repository': name, 'api_url':'https://api.github.com/'+endpoint,
           'checked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
           'claimed_site':'https://'+OWNER+'.github.io/'+name+'/',
           'pages_content_verified': False, 'organizer_receipt_verified':False}
    if p.returncode:
        row.update(status='unavailable', detail=p.stderr.strip()[:500])
    else:
        d=json.loads(p.stdout)
        row.update(status='repository-accessible', url=d['html_url'],
                   default_branch=d['default_branch'], pages_configured=d['has_pages'],
                   archived=d['archived'], pushed_at=d['pushed_at'])
    return row

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(inspect,NAMES))
    path=ROOT/'evidence/source_inventory.json'
    path.write_text(json.dumps({'scope':'Public repository metadata only; not a raster uniqueness scan or live Pages/leaderboard verification.',
                               'sources':rows},indent=2)+'\n')
    print(f'{len(rows)} repositories checked; {sum(r["status"]=="repository-accessible" for r in rows)} accessible')
