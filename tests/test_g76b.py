"""Lane G76B software tests: synthetic fixtures only, never geological results.

Checks the lane's feature/context helpers, the fold-isolation property of the
training pool, the frozen HGB head's interface, and the integrity of the
session's evidence files (they must match the numbers cited in the site/README).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems76b import features as FB  # noqa: E402
from gems76b import model as MB  # noqa: E402


def test_directional_persistence_prefers_lines_over_isolated_dots():
    rng = np.random.default_rng(0)
    dom = np.ones((40, 40), bool)
    blob = rng.random((40, 40)).astype(np.float32) * 0.1
    blob[15:25, 15:25] = 1.0
    line = np.zeros((40, 40), np.float32)
    line[18:22, 2:38] = 1.0
    dot = np.zeros((40, 40), np.float32)
    dot[5, 5] = 1.0
    p_blob = FB.directional_persistence(blob, dom)
    p_line = FB.directional_persistence(line, dom)
    p_dot = FB.directional_persistence(dot, dom)
    # a coherent 36-px line persists; an isolated dot barely does; clean background is zero
    assert p_line[20, 20] == pytest.approx(1.0, abs=0.01)
    assert p_dot[5, 5] < 0.35 * p_line[20, 20]
    assert p_dot[0, 0] == 0.0 and p_line[0, 0] == 0.0
    assert p_line[20, 20] >= p_blob[20, 20] - 1e-6  # blob interior also contains lines


def test_support_density_is_local_mean_of_rank():
    dom = np.ones((12, 12), bool)
    r = np.zeros((12, 12), np.float32)
    r[6, 6] = 1.0
    s = FB.support_density(r, dom)
    assert s[6, 6] > 0
    assert s[0, 0] == pytest.approx(0.0, abs=1e-6)  # far from the single spike
    assert s.max() <= 1.0 + 1e-6


def test_decode_u8_roundtrip_sqrt_and_linear():
    q = np.array([[0, 1, 128, 255]], dtype=np.uint8)
    lin = FB._decode_u8(q, "coh100")          # xmax=1, linear
    sqrt = FB._decode_u8(q, "step_max")       # xmax=1, sqrt
    assert np.isnan(lin[0, 0]) and np.isnan(sqrt[0, 0])
    assert lin[0, 3] == pytest.approx(1.0)
    assert sqrt[0, 3] == pytest.approx(1.0)
    # midpoint of the sqrt scale is the square of the linear midpoint
    assert sqrt[0, 2] == pytest.approx(lin[0, 2] ** 2, abs=1e-6)


def test_training_pool_excludes_test_region_with_collar():
    valid = np.zeros((60, 60), bool)
    valid[5:55, 5:55] = True
    region = np.zeros((60, 60), bool)
    region[30:60, 30:60] = True
    pool = MB.training_pool(valid, region, erosion_px=12)
    assert not (pool & region).any()
    dist = MB.training_pool.__wrapped__ if hasattr(MB.training_pool, "__wrapped__") else None
    from scipy import ndimage as ndi
    d = ndi.distance_transform_edt(~region)
    assert not (pool & (d <= 12)).any()
    assert pool[10, 10]  # far inside the non-test side


def test_fit_hgb_predicts_in_unit_interval_and_reports_receipt():
    rng = np.random.default_rng(1)
    X = rng.random((6000, 4), np.float32)
    pos = np.flatnonzero(X[:, 0] > 0.75)
    pool = np.arange(6000)
    clf, rec = MB.fit_hgb(X, pos, pool, seed=3, neg_ratio=2, neg_cap=2000)
    p = MB.predict_full(X, clf)
    assert p.min() >= 0.0 and p.max() <= 1.0
    assert rec["n_positives"] == len(pos)
    # the model must rank its training signal
    assert p[X[:, 0] > 0.9].mean() > p[X[:, 0] < 0.1].mean()
    assert MB.HGB_PARAMS["max_iter"] == 250  # frozen; change requires preregistration amendment


def test_vec_to_grid_scatter_roundtrip():
    valid = np.zeros((8, 9), bool)
    valid[2:6, 3:7] = True
    vec = np.arange(valid.sum(), dtype=np.float32)
    g = MB.vec_to_grid(vec, valid, fill=-1.0)
    assert g.shape == valid.shape
    assert np.array_equal(g[valid], vec)
    assert (g[~valid] == -1.0).all()


def test_evidence_files_exist_and_match_cited_numbers():
    ev = ROOT / "evidence" / "g76b-exp1"
    for name in ["manifest.json", "holdout_split.json", "canaries.json",
                 "fit_receipts.json", "holdout_A.json", "holdout_A_folds.json",
                 "fit_receipts_production.json", "proxy_Bprime.json",
                 "proxy_C76pied.json", "diagnostics.json"]:
        assert (ev / name).is_file(), name
    import json
    a = json.loads((ev / "holdout_A.json").read_text())
    assert a["evaluator_version"] == "gems57-pooled-hide-v2"
    assert a["scores"]["candidate_dots"]["withheld_positive_pixels"] == 11321
    assert a["scores"]["candidate_dots"]["dti"] == pytest.approx(0.01870, abs=5e-5)
    assert a["scores"]["fair_h33"]["dti"] == pytest.approx(0.09611, abs=5e-5)
    assert a["paired_differences"]["fair_h33"]["ci95"][1] < 0  # gate failure is decisive
    card = json.loads((ROOT / "evidence" / "g76b_run_card.json").read_text())
    assert card["verdict"] == "negative" and card["safe_to_submit"] is False
    assert card["weekly_slots_used"] == 0
    assert len(card["submission_note_max140"]) <= 140
    uniq = json.loads((ROOT / "evidence" / "g76b-uniqueness.json").read_text())
    assert uniq["gate_mutual_le_0.70"] and uniq["gate_abs_rho_le_0.90"]
    assert uniq["worst_mutual"]["mutual_overlap"] <= 0.70


def test_preregistration_precedes_manifest():
    """The preregistration file must be older than (or equal to) the run manifest."""
    pre = ROOT / "docs" / "preregistration-g76b.md"
    man = ROOT / "evidence" / "g76b-exp1" / "manifest.json"
    assert pre.is_file() and man.is_file()
    import json
    m = json.loads(man.read_text())
    assert m["preregistration_sha256"] == __import__("hashlib").sha256(pre.read_bytes()).hexdigest()
