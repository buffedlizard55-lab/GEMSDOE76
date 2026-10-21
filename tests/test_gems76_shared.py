"""Comprehensive unit, regression, and deliverable contract tests for GEMSDOE76."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import binary_dilation
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems76c.canary import _exact_auc_1d
from gems76c.features import clean_band
from gems76c import emit_patched as emit, uniqueness_patched as uniqueness
from gems57 import submission_writer


def test_bug_gems57_01_fast_forward_overlap_exact_parity():
    """BUG-GEMS57-01: _fast_forward_overlap matches full binary_dilation to machine precision."""
    rng = np.random.default_rng(7601)
    H, W = 97, 83
    for density in (0.0, 0.002, 0.03, 0.25, 1.0):
        theirs = rng.random((H, W)) < density
        mine = rng.random((H, W)) < 0.04
        # Force explicit boundary/corner points
        mine[0, 0] = True
        mine[0, W - 1] = True
        mine[H - 1, 0] = True
        mine[H - 1, W - 1] = True
        ym, xm = np.nonzero(mine)
        fast = uniqueness._fast_forward_overlap(theirs, ym, xm, 3.0)
        slow = float(uniqueness._near(theirs, 3.0)[mine].mean()) if theirs.any() else 0.0
        assert abs(fast - slow) < 1e-14


def test_bug_gems57_02_surrogate_terms_no_self_credit_and_submodularity():
    """BUG-GEMS57-02: surrogate_terms has zero self-credit on empty posterior and diminishing returns."""
    emitted = np.zeros((40, 40), dtype=bool)
    emitted[20, 20] = True
    zero_post = np.zeros((40, 40), dtype=np.float32)

    terms_zero = emit.surrogate_terms(emitted, zero_post, k_truth=100.0)
    assert terms_zero["T"] == 0.0
    assert terms_zero["M"] == 0.0
    assert terms_zero["surrogate_dti"] == 0.0

    # Diminishing returns (submodularity): f(A u {x}) - f(A) >= f(B u {x}) - f(B) for A subseteq B
    post = np.full((40, 40), 0.25, dtype=np.float32)
    A = np.zeros((40, 40), dtype=bool)
    B = np.zeros((40, 40), dtype=bool)
    B[20, 19] = True  # adjacent within 300 m kernel -> strong overlap!

    Ax = A.copy()
    Ax[20, 20] = True
    Bx = B.copy()
    Bx[20, 20] = True

    gain_A = emit.surrogate_terms(Ax, post, 100.0)["T"] - emit.surrogate_terms(A, post, 100.0)["T"]
    gain_B = emit.surrogate_terms(Bx, post, 100.0)["T"] - emit.surrogate_terms(B, post, 100.0)["T"]
    assert gain_A > gain_B > 0.0


def test_bug_gems57_03_graded_sparse_dot_support():
    """BUG-GEMS57-03: _dots detects graded positive values in (0, 1) as well as binary 1.0."""
    graded = np.array([[0.0, 0.42, np.nan], [0.95, 0.0, 1.0]], dtype=np.float32)
    d = uniqueness._dots(graded)
    expected = np.array([[False, True, False], [True, False, True]])
    assert np.array_equal(d, expected)


def test_bug_gems57_04_and_ir_76_05_clean_band_sentinel_sanitization():
    """BUG-GEMS57-04 / IR-76-05: clean_band sanitizes NaN, +/-Inf, AND float32 -3.4028235e+38 sentinels."""
    fp = np.ones((6, 6), dtype=bool)
    fp[0, :] = False
    raw = np.full((6, 6), 12.0, dtype=np.float32)
    raw[2, 2] = np.nan
    raw[2, 3] = np.inf
    raw[3, 2] = -3.4028235e38  # float32 min finite sentinel present in training_features.tif!
    cleaned, n_bad = clean_band(raw, fp)
    assert n_bad == 3
    assert cleaned.dtype == np.float32
    assert np.isfinite(cleaned).all()
    assert np.max(np.abs(cleaned)) < 1e3
    assert cleaned[2, 2] == pytest.approx(12.0)
    assert cleaned[3, 2] == pytest.approx(12.0)
    assert (cleaned[~fp] == 0.0).all()


def test_bug_gems57_05_two_phase_mutual_consistency_under_covering_lattice():
    """BUG-GEMS57-05: summarize_two_phase does not falsely flag a 5x5 covering lattice as a duplicate."""
    rows = [{
        "submission": "13GEMSDOE:docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
        "repo": "13GEMSDOE",
        "their_dots": 206_895,
        "my_dots_within_3px_of_theirs": 0.99773,
        "their_dots_within_3px_of_mine": 0.12911,
        "mutual_overlap": 0.12911,
        "spearman_full_footprint": 0.00001,
        "jaccard_dot_sets": 0.00642,
    }]
    res = uniqueness.two_phase_summary(rows, footprint_cells=5_167_373, expected_rasters=1)
    assert res["like_for_like_reading"]["duplicate"] is False
    assert res["like_for_like_reading"]["worst_forward_overlap_dot_fields"] == pytest.approx(0.12911)
    assert res["like_for_like_reading"]["worst_raw_oneway_forward_dot_fields"] == pytest.approx(0.99773)


def test_diagnostic_figures_nonempty_and_high_resolution():
    import matplotlib.image as mpimg
    for fname in (
        "fig1_nevada_spatial_overview.png",
        "fig2_holdout_dti_and_fold_auc.png",
        "fig3_canary_and_uniqueness_896.png",
        "fig4_geothermal_physics_zoom.png",
    ):
        p = ROOT / "docs" / "assets" / fname
        assert p.is_file() and p.stat().st_size > 80_000
        img = mpimg.imread(p)
        assert img.shape[0] >= 900 and img.shape[1] >= 2200
        assert float(img[..., :3].std()) > 0.08


def test_exact_auc_1d_matches_sklearn_with_ties_and_inversions():
    rng = np.random.default_rng(76)
    y = (rng.random(5000) < 0.07).astype(np.uint8)
    for x in (
        rng.normal(size=5000).astype(np.float32),
        rng.integers(0, 7, size=5000).astype(np.float32),  # heavy ties
        -rng.normal(size=5000).astype(np.float32),
    ):
        assert abs(_exact_auc_1d(y, x) - roc_auc_score(y, x)) < 1e-12


def test_allocate_submodular_celf_constraints():
    rng = np.random.default_rng(7603)
    surf = rng.uniform(0.0, 1.0, size=(80, 90)).astype(np.float32)
    allowed = np.ones((80, 90), dtype=bool)
    allowed[:8, :] = False
    alloc = emit.allocate_submodular_celf(surf, allowed, k_truth=200.0, budget=45, min_dist_px=3.0)
    assert int(alloc.emitted.sum()) == 45
    assert int(alloc.emitted[~allowed].sum()) == 0
    yy, xx = np.nonzero(alloc.emitted)
    # Pairwise Euclidean distance strictly > 3.0 px
    for i in range(len(yy)):
        d2 = (yy[i + 1:] - yy[i]) ** 2 + (xx[i + 1:] - xx[i]) ** 2
        if d2.size:
            assert float(d2.min()) > 9.0 - 1e-6


def test_shipped_deliverable_end_to_end_drivendata_contract():
    """Verify the actual shipped GeoTIFF, ZIP, sidecar JSON, and all governance gates."""
    h_res = json.loads((ROOT / "evidence" / "holdout_experiments_results.json").read_text())
    u_res = json.loads((ROOT / "evidence" / "uniqueness_896_ledger_summary.json").read_text())
    c1 = json.loads((ROOT / "evidence" / "leakage_canary_stage1.json").read_text())
    c2 = json.loads((ROOT / "evidence" / "leakage_canary_stage2.json").read_text())

    receipt = h_res["submission_receipt"]
    tif_path = ROOT / "docs" / "downloads" / receipt["file"]
    zip_path = ROOT / "docs" / "downloads" / receipt["zip_file"]

    assert tif_path.is_file() and zip_path.is_file()
    assert len(receipt["note"]) <= 140

    # Exact SHA-256 verification on both .tif and .zip
    tif_bytes = tif_path.read_bytes()
    assert hashlib.sha256(tif_bytes).hexdigest() == receipt["sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == receipt["zip_sha256"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [receipt["file"]]
        assert zf.read(names[0]) == tif_bytes

    # Full raster grid, value range [0, 1], footprint & catalogue contract
    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert ds.transform == Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
        arr = ds.read(1)

    assert np.isfinite(arr).all()  # Prevents "Predicted values must be in range [0, 1]" unconditionally!
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    assert ((arr >= 0.0) & (arr <= 1.0)).all()
    assert int((arr > 0).sum()) == 39_200

    if Path("/tmp/gems_data/sample_submission.tif").is_file() and Path("/tmp/gems_data/existing_faults.tif").is_file():
        with rasterio.open("/tmp/gems_data/sample_submission.tif") as ds_ref:
            fp = np.isfinite(ds_ref.read(1))
        with rasterio.open("/tmp/gems_data/existing_faults.tif") as ds_cat:
            cat = np.isfinite(ds_cat.read(1)) & (ds_cat.read(1) > 0)
        assert int((arr[~fp] != 0.0).sum()) == 0
        assert int((arr[cat] != 0.0).sum()) == 0

    rc = json.loads((ROOT / "evidence" / "g76c_run_card.json").read_text())
    assert rc["raster_sha256"] == receipt["sha256"]
    rc_root = json.loads((ROOT / "run_card.json").read_text())
    assert rc_root["verdict"] == "promote"
    assert rc["zip_sha256"] == receipt["zip_sha256"]
    assert rc["submission_name"] == receipt["submission_name"]
    assert rc["submission_note"] == receipt["note"]
    assert len(rc["submission_note"]) <= 140
    assert rc["verdict"] == "promote"

    # Governance gates
    assert c1["passed"] is True and c1["violator_count"] == 0 and c1["max_observed_polarity_auc"] <= 0.90
    assert c2["passed"] is True and c2["violator_count"] == 0 and c2["max_observed_polarity_auc"] <= 0.90
    assert u_res["surface"]["worst_abs_spearman"] <= 0.90
    assert abs(u_res["dots"]["worst_spearman_full_footprint"]) <= 0.90
    assert u_res["dots"]["worst_dot_overlap"] <= 0.70
    assert u_res["dots"]["unique"] is True and u_res["dots"]["duplicate_count"] == 0


def test_pass3_docs_links_and_consistency_audit():
    """Pass 3: Verify every relative link/asset in HTML & README resolves and zero hedging phrases exist."""
    import re
    rc = json.loads((ROOT / "run_card.json").read_text())
    sub_name = rc["submission_name"]
    sub_note = rc["submission_note"]
    sha = rc["raster_sha256"]

    readme_txt = (ROOT / "README.md").read_text()
    assert "## 9. Verbatim User Prompt" in readme_txt
    assert sub_name in readme_txt and sub_note in readme_txt and sha in readme_txt

    for html_name in ("index.html", "executive-summary.html"):
        html_path = ROOT / "docs" / html_name
        txt = html_path.read_text()
        assert sub_name in txt and sub_note in txt and sha in txt
        for ref in re.findall(r'(?:href|src)="([^"]+)"', txt):
            if ref.startswith(("http://", "https://", "#")):
                continue
            target = (ROOT / "docs" / ref).resolve()
            assert target.is_file(), f"Broken link in {html_name}: {ref} -> {target}"
        # Zero hedging outside verbatim quoted prompt
        low = txt.lower()
        assert "i think" not in low
        assert "probably" not in low
