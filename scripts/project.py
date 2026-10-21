"""Project-level audit, not a private evaluator or submission writer."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def pinned_files(root=ROOT):
    rows = read_json(root/'evidence/upstream/recovery.json')
    return [{'path':r['path'], 'expected_sha256':r['sha256'],
             'present':(root/r['path']).is_file(),
             'matches':(root/r['path']).is_file() and sha256(root/r['path'])==r['sha256']}
            for r in rows]


def validate_candidate(path, sample, catalogue_path):
    """Reject, never clip/fill. Reuse the shared writer's validation components."""
    import numpy as np
    import rasterio
    from gems57 import gates, grid
    with rasterio.open(sample) as ref:
        grid._check(ref, 'reference sample')
        footprint = np.isfinite(ref.read(1))
    with rasterio.open(catalogue_path) as src:
        grid._check(src, 'reference catalogue')
        catalogue = (src.read(1) > 0) & footprint
    report = gates.format_report(path, sample, footprint=footprint)
    with rasterio.open(path) as src:
        values = src.read(1)
    report['nan_inside_footprint'] = None
    report['catalogue_overlap_pixels'] = None
    if values.shape == footprint.shape:
        report['nan_inside_footprint'] = int((~np.isfinite(values) & footprint).sum())
        report['catalogue_overlap_pixels'] = int(((values > 0) & catalogue).sum())
        if report['catalogue_overlap_pixels']:
            report['problems'].append('positive predictions on visible catalogue pixels')
    report['ok'] = not report['problems']
    report['approved_for_weekly_slot'] = False
    report['warning'] = 'Format validation only: no holdout, leakage, uniqueness or selector approval implied.'
    return report
