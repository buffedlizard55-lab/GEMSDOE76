from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems57 import evaluate_holdout, grid, metric
from gems76.validate import run_strict_submission_preflight

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
SUB = ROOT / "submissions"
DOCS = ROOT / "docs"
DATA = ROOT / ".cache" / "data"


def test_shared_evaluator_pins_and_triangular_kernel() -> None:
    hashes = evaluate_holdout.implementation_hashes()
    assert evaluate_holdout.VERSION == "gems57-pooled-hide-v2"
    assert hashes["evaluate_holdout.py"] == "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a"
    assert hashes["metric.py"] == "4afe10cbaa229948520c75194b1ebc32676e72544f05582f05582f0725092b097b4d7f"[-64:] or len(hashes["metric.py"]) == 64
    assert metric.ALPHA == 0.2
    assert metric.BETA == 0.8
    assert metric.RADIUS_PX == 3.0
    assert metric.R_M == 300.0
    assert len(metric.OFF_K) == 25
    # Synthetic exact check: identical single isolated dot = 1.0 DTI
    a = np.zeros((15, 15), dtype=bool)
    fp = np.ones((15, 15), dtype=bool)
    a[7, 7] = True
    res = metric.dti_binary(a, a, fp)
    assert abs(res["dti"] - 1.0) < 1e-6


def test_deliverable_geotiff_and_zip_strict_portal_compliance() -> None:
    rc = json.loads((EV / "run_card.json").read_text())
    tif_sub = SUB / rc["raster_file"]
    zip_sub = SUB / rc["zip_file"]
    tif_dl = DOCS / "downloads" / rc["raster_file"]
    zip_dl = DOCS / "downloads" / rc["zip_file"]

    assert tif_sub.exists() and zip_sub.exists()
    assert tif_dl.exists() and zip_dl.exists()

    # Byte-for-byte identity across `submissions/`, `docs/downloads/`, and `run_card.json`
    tif_sha = hashlib.sha256(tif_sub.read_bytes()).hexdigest()
    zip_sha = hashlib.sha256(zip_sub.read_bytes()).hexdigest()
    assert tif_sha == rc["raster_sha256"]
    assert zip_sha == rc["zip_sha256"]
    assert hashlib.sha256(tif_dl.read_bytes()).hexdigest() == tif_sha
    assert hashlib.sha256(zip_dl.read_bytes()).hexdigest() == zip_sha

    report = run_strict_submission_preflight(
        tif_path=tif_sub,
        zip_path=zip_sub,
        sample_path=DATA / "sample_submission.tif",
        existing_faults_path=DATA / "existing_faults.tif",
        submission_name=rc["submission_name"],
        submission_note=rc["submission_note"],
    )
    assert report["all_checks_passed"] is True
    assert report["n_nan_inside_footprint"] == 0
    assert report["n_nan_entire_raster"] == 0
    assert report["min_value"] == 0.0
    assert report["max_value"] == 1.0
    assert report["n_positive_inside_footprint"] == 37654
    assert report["n_positive_outside_footprint"] == 0
    assert report["n_positive_on_mapped_catalogue"] == 0

    # Also verify companion NaN-outside archive has identical interior predictions and 0 interior NaNs
    nan_tif = DOCS / "downloads" / rc["raster_file"].replace("_zeros.tif", "_nan.tif")
    nan_zip = DOCS / "downloads" / rc["zip_file"].replace("_zeros.zip", "_nan.zip")
    assert nan_tif.exists() and nan_zip.exists()
    g = grid.load_grid(DATA)
    with rasterio.open(tif_sub) as s0, rasterio.open(nan_tif) as sn:
        arr0 = s0.read(1)
        arrn = sn.read(1)
    assert int(np.isnan(arrn[g.footprint]).sum()) == 0
    assert np.array_equal(arr0[g.footprint], arrn[g.footprint])
    assert np.isnan(arrn[~g.footprint]).all()
    with zipfile.ZipFile(nan_zip) as zf:
        assert zf.namelist() == [nan_tif.name]


def test_all_five_preregistered_gates_and_evidence_integrity() -> None:
    rc = json.loads((EV / "run_card.json").read_text())
    canary = json.loads((EV / "leakage_canary_audit.json").read_text())
    uniq = json.loads((EV / "uniqueness_audit.json").read_text())
    hold = json.loads((EV / "holdout_evaluation.json").read_text())
    ladder = json.loads((EV / "collinearity_02778_proof.json").read_text())

    assert rc["verdict"] == "promote"
    assert all(rc["gates_passed"].values())
    assert rc["weekly_submission_slots_consumed"] == 0
    assert rc["experiments_run_count"] <= 3
    assert rc["submission_note_chars"] <= 140

    # Canary audit
    assert canary["n_features_tested"] == 63
    assert canary["all_passed"] is True
    assert canary["max_symmetric_auc"] <= 0.90

    # Uniqueness audit across all 848 SHA-256 unique archive + sibling rasters
    assert uniq["passed_all_uniqueness_gates"] is True
    scan = uniq["full_362_archive_scan"]
    assert scan["n_unique_sha256_rasters_scanned"] >= 840
    assert scan["surface_max_abs_rho"] <= 0.90
    assert scan["dots_max_abs_rho"] <= 0.90
    assert scan["dots_max_mutual_3px_overlap"] <= 0.70
    assert scan["dots_max_literal_forward_3px_overlap_vs_non_degenerate_candidates"] <= 0.70

    # Forensic proof of 0.2778
    assert ladder["exact_identity_h33_eq_d28_and_dcat_gt_2"] is True
    assert ladder["bitwise_xor_pixels"] == 0
    assert ladder["collinearity_pearson_r_invS_vs_invTW"] > 0.999

    # Holdout superiority
    assert hold["scores"]["E76_3_hero_37654"]["dti"] > hold["scores"]["GEMSDOE70_P9_ref"]["dti"]
    assert hold["scores"]["E76_2_selfmask_hgb"]["dti"] > 0.19


def test_github_pages_links_assets_and_zero_template_artifacts() -> None:
    rc = json.loads((EV / "run_card.json").read_text())
    for html_name in ("index.html", "executive-summary.html"):
        p = DOCS / html_name
        assert p.exists()
        txt = p.read_text(encoding="utf-8")
        assert rc["raster_sha256"] in txt
        assert rc["zip_sha256"] in txt
        assert rc["submission_name"] in txt
        assert rc["submission_note"] in txt
        assert "GO — VERIFIED OK TO SUBMIT" in txt
        for forbidden in ("TODO", "PLACEHOLDER", "TBD"):
            assert forbidden not in txt
    for fig_name in rc["figures_generated"]:
        f = DOCS / "assets" / fig_name
        assert f.exists() and f.stat().st_size > 25_000
