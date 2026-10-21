"""Synthetic software fixtures only; not geological experiment results."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from affine import Affine
from gems57 import evaluate_holdout, gates, grid, metric, submission_writer, uniqueness
from preflight import audit
from project import ROOT, pinned_files, validate_candidate


def write_fixture(path, values, *, transform=None, crs='EPSG:32611'):
    with rasterio.open(path,'w',driver='GTiff',height=values.shape[0],width=values.shape[1],
                       count=1,dtype=values.dtype,crs=crs,
                       transform=transform or grid.TRANSFORM,compress='deflate') as dst:
        dst.write(values,1)


def test_recovered_bytes_match_pins():
    assert all(r['matches'] for r in pinned_files())


def test_shared_constants_and_reference_grid():
    import rasterio
    for name in ['example_submission.tif','existing_faults.tif']:
        with rasterio.open(ROOT/'data/reference'/name) as src:
            grid._check(src,name)
    assert metric.ALPHA==0.2 and metric.BETA==0.8
    assert metric.R_M==300 and evaluate_holdout.VERSION=='gems57-pooled-hide-v2'


def test_current_preflight_blocks_without_fake_raster():
    report=audit()
    assert report['status']=='blocked'
    assert not report['safe_to_submit'] and not report['downloadable_submission']
    assert report['experiments_run']==0 and report['weekly_slots_used']==0
    assert report['reference_grid']['status']=='pass-bridge-relative'
    assert all(row['matches'] for row in report['pinned_files'])
    assert not list((ROOT/'docs/downloads').glob('*.tif'))


def test_modified_pin_is_detected(tmp_path):
    (tmp_path/'evidence/upstream').mkdir(parents=True)
    (tmp_path/'tool.py').write_text('altered')
    (tmp_path/'evidence/upstream/recovery.json').write_text(json.dumps([
        {'path':'tool.py','sha256':hashlib.sha256(b'original').hexdigest()}]))
    assert pinned_files(tmp_path)[0]['matches'] is False


@pytest.mark.parametrize('bad',[np.nan,np.inf,-np.inf,-0.001,1.001])
def test_shared_writer_rejects_unscaled_or_nonfinite_before_io(tmp_path,bad):
    a=np.zeros((5,5),np.float32);a[2,2]=bad
    with pytest.raises(ValueError,match='normalized, finite'):
        submission_writer.write_submission(tmp_path/'not-a-submission.tif',a,tmp_path/'missing.tif',
            np.ones(a.shape,bool),note='synthetic test',name='synthetic test')
    assert not list(tmp_path.iterdir())


def test_shared_writer_rejects_catalogue_and_exterior(tmp_path):
    a=np.ones((4,4),np.float32);fp=np.ones(a.shape,bool)
    cat=np.zeros(a.shape,bool);cat[0,0]=True
    with pytest.raises(ValueError,match='mapped catalogue'):
        submission_writer.write_submission(tmp_path/'fixture.tif',a,tmp_path/'missing',fp,
            catalogue=cat,note='synthetic',name='synthetic')
    fp[0,0]=False
    with pytest.raises(ValueError,match='outside'):
        submission_writer.write_submission(tmp_path/'fixture.tif',a,tmp_path/'missing',fp,
            note='synthetic',name='synthetic')


def test_shared_writer_note_limit(tmp_path):
    with pytest.raises(ValueError,match='note'):
        submission_writer.write_submission(tmp_path/'fixture.tif',np.zeros((2,2)),tmp_path/'missing',
            np.ones((2,2),bool),note='x'*141,name='synthetic')


def test_shared_disk_validator_small_fixture(tmp_path):
    a=np.zeros((8,9),np.float32)
    write_fixture(tmp_path/'reference.tif',a)
    for value,expected in [(0.,True),(1.,True),(-1.,False),(2.,False),(np.nan,False),(np.inf,False)]:
        a[1,1]=value
        write_fixture(tmp_path/'candidate.tif',a)
        r=gates.format_report(tmp_path/'candidate.tif',tmp_path/'reference.tif')
        assert r['ok'] is expected
    a[:]=0
    write_fixture(tmp_path/'candidate.tif',a,transform=Affine(100,0,243351,0,-100,4508550))
    assert not gates.format_report(tmp_path/'candidate.tif',tmp_path/'reference.tif')['ok']
    write_fixture(tmp_path/'candidate.tif',a,crs='EPSG:4326')
    assert not gates.format_report(tmp_path/'candidate.tif',tmp_path/'reference.tif')['ok']
    write_fixture(tmp_path/'candidate.tif',a[:4])
    assert not gates.format_report(tmp_path/'candidate.tif',tmp_path/'reference.tif')['ok']


def test_shared_metric_matches_brute_force():
    rng=np.random.default_rng(76)
    for _ in range(6):
        truth=rng.random((12,14))<0.1
        p=rng.random(truth.shape)*(rng.random(truth.shape)<0.1)
        fast=metric.dti_exact(p,truth)
        brute=metric.dti_bruteforce(p,truth)
        assert fast['dti']==pytest.approx(brute['dti'],abs=1e-12)


def test_pooled_evaluator_visible_mask_and_ci():
    valid=np.ones((16,16),bool)
    truth=np.zeros_like(valid);truth[4,4]=True;truth[12,12]=True
    visible=np.zeros_like(valid);visible[6,6]=True
    fold={'region':valid,'visible':visible,'truth':truth}
    p=truth.astype(float);p[6,6]=1
    result,terms=evaluate_holdout.evaluate(p,fold,valid,block_side=8)
    assert result['n_emitted']==2
    assert result['n_truth']==2
    summary=evaluate_holdout.pooled_summary({'candidate':terms,'control':terms},candidate='candidate',draws=20)
    assert summary['scores']['candidate']['withheld_positive_pixels']==2
    assert summary['paired_differences']['control']['delta']==0
    assert summary['paired_differences']['control']['ci95']==[0.,0.]
    with pytest.raises(ValueError,match='same integer truth count'):
        changed=terms.copy();changed[0,3]+=1
        evaluate_holdout.pooled_summary({'candidate':terms,'control':changed},candidate='candidate',draws=20)


def test_literal_forward_overlap_no_dense_exemption():
    dense=np.ones((12,12),float);sparse=np.zeros_like(dense);sparse[6,6]=1
    assert uniqueness.dot_overlap(sparse,dense)==1
    assert uniqueness.dot_overlap(dense,sparse)<0.70
    meta={'my_dots':1,'candidate_rank_variation':True}
    row={'submission':'fixture','duplicate_by_overlap':True,
         'my_dots_within_3px_of_theirs':1.,'jaccard_dot_sets':0.01}
    r=uniqueness.summarize_registry_rows([row],registry_rasters_expected=1,
        complete_accessible_scan=True,source_errors=[],candidate_meta=meta,scope='synthetic fixture')
    assert r['stop_required'] and not r['unique']
    r=uniqueness.summarize_registry_rows([],registry_rasters_expected=1,
        complete_accessible_scan=False,source_errors=[],candidate_meta=meta,scope='synthetic fixture')
    assert r['stop_required'] and not r['unique']


def test_source_inventory_correct_prefix_names():
    rows=json.loads((ROOT/'evidence/source_inventory.json').read_text())['sources']
    assert len(rows)==78 and len({r['repository'] for r in rows})==78
    names={r['repository'] for r in rows}
    assert '55GEMSDOE' in names and 'GEMSDOE55' not in names
    assert all(r['organizer_receipt_verified'] is False for r in rows)


def test_shared_writer_roundtrip_stays_unapproved(tmp_path):
    """All-zero temporary serialization fixture, NEVER a scientific candidate."""
    import zipfile
    with rasterio.open(ROOT/'data/reference/example_submission.tif') as src:
        fp=np.isfinite(src.read(1))
    zeros=np.zeros(grid.SHAPE,np.float32)
    target=tmp_path/'synthetic-zero-fixture.tif'
    receipt=submission_writer.write_submission(target,zeros,ROOT/'data/reference/example_submission.tif',
        fp,note='SOFTWARE TEST ONLY - not a submission',name='synthetic zero fixture')
    assert receipt['template_report']['ok'] and receipt['validator']['min']==0
    assert receipt['approved_for_weekly_slot'] is False and receipt['promoted'] is False
    with zipfile.ZipFile(target.with_suffix('.zip')) as z:
        assert z.namelist()==[target.name]
        assert hashlib.sha256(z.read(target.name)).hexdigest()==receipt['sha256']
    with pytest.raises(FileExistsError):
        submission_writer.write_submission(target,zeros,ROOT/'data/reference/example_submission.tif',fp,
            note='SOFTWARE TEST ONLY',name='test')


def test_rendered_site_links_and_card():
    from check_site import check_site
    assert check_site()==[]


def test_candidate_validator_rejects_non_grid_fixture(tmp_path):
    """Shared format report returns failure, not a fabricated grid match."""
    candidate=tmp_path/'small-not-a-submission.tif'
    write_fixture(candidate,np.zeros((4,4),np.float32))
    report=validate_candidate(candidate,ROOT/'data/reference/example_submission.tif',
                              ROOT/'data/reference/existing_faults.tif')
    assert report['ok'] is False
    assert report['approved_for_weekly_slot'] is False
    assert report['nan_inside_footprint'] is None
    assert any('shape' in p for p in report['problems'])


def test_withdrawn_generator_cannot_publish(tmp_path):
    import subprocess,sys
    p=subprocess.run([sys.executable,str(ROOT/'scripts/generate_submission.py')],
                     cwd=tmp_path,capture_output=True,text=True)
    assert p.returncode==2 and 'BLOCKED / DO NOT SUBMIT' in p.stderr
    assert not list(tmp_path.iterdir())


def test_archived_originals_preserved_byte_exact():
    manifest=json.loads((ROOT/'evidence/inherited-main-manifest.json').read_text())
    for row in manifest['files']:
        if row['archive_path']:
            path=ROOT/row['archive_path']
            assert path.is_file(),str(path)
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        else:
            assert row['path'].endswith('.npy')
            assert manifest['source_commit'] in row['source_url']


def test_inherited_candidates_are_withdrawn_against_bridge():
    receipt=json.loads((ROOT/'evidence/inherited-candidate-validation.json').read_text())
    assert receipt['safe_to_submit'] is False
    assert receipt['synthetic_footprint_different_pixels']>0
    assert receipt['synthetic_catalogue_different_pixels']>0
    assert len(receipt['candidate_reports'])==6
    for report in receipt['candidate_reports']:
        assert report['ok'] is False
        assert report['approved_for_weekly_slot'] is False
        assert report['mass_outside_footprint']>0
        assert report['catalogue_overlap_pixels']>0
    assert not (ROOT/'evidence/footprint.npy').exists()
    assert not (ROOT/'evidence/catalogue.npy').exists()
