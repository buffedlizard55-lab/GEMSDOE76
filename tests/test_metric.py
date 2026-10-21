"""Verify the vendored shared metric against the official definition.

Official definition: DrivenData competition 306, problem-description page —
distance-weighted Tversky, triangular kernel k(d)=max(1-d/R,0), R=300 m
(3 px), alpha=0.2, beta=0.8; TPw uses per-truth-pixel max of p*k, FPw uses
p*(1-max_g k), FNw = |G|-TPw.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from gems57 import metric  # noqa: E402


def test_hand_example_dot_at_100m():
    truth = np.zeros((11, 11), bool); truth[5, 5] = True
    pred = np.zeros((11, 11)); pred[5, 6] = 1.0
    r = metric.dti_exact(pred, truth)
    assert r["tp"] == pytest.approx(2 / 3)
    assert r["fp"] == pytest.approx(1 / 3)
    assert r["fn"] == pytest.approx(1 / 3)
    assert r["dti"] == pytest.approx(2 / 3)


def test_dot_on_truth_and_at_300m():
    truth = np.zeros((11, 11), bool); truth[5, 5] = True
    on = np.zeros((11, 11)); on[5, 5] = 1.0
    assert metric.dti_exact(on, truth)["dti"] == pytest.approx(1.0)
    far = np.zeros((11, 11)); far[5, 8] = 1.0  # d = 3 px -> k = 0
    assert metric.dti_exact(far, truth)["dti"] == pytest.approx(0.0)


def test_exact_matches_bruteforce_random():
    rng = np.random.default_rng(76)
    for _ in range(25):
        truth = rng.random((14, 13)) < 0.08
        pred = np.where(rng.random((14, 13)) < 0.15, rng.random((14, 13)), 0.0)
        if not truth.any():
            continue
        a = metric.dti_exact(pred, truth)
        b = metric.dti_bruteforce(pred, truth)
        assert a["tp"] == pytest.approx(b["tp"], abs=1e-9)
        assert a["fp"] == pytest.approx(b["fp"], abs=1e-9)
        assert a["fn"] == pytest.approx(b["fn"], abs=1e-9)
        assert a["dti"] == pytest.approx(b["dti"], abs=1e-9)


def test_binary_matches_exact():
    rng = np.random.default_rng(7)
    truth = rng.random((20, 19)) < 0.06
    dots = rng.random((20, 19)) < 0.05
    a = metric.dti_binary(dots, truth)
    b = metric.dti_exact(dots.astype(float), truth)
    assert a["dti"] == pytest.approx(b["dti"], abs=1e-9)


def test_marginal_bar_algebra():
    # Official-example arithmetic from the competition page: TPw=3, FPw=1.89,
    # FNw=2 -> DTI = 3/(3+0.2*1.89+0.8*2) = 0.6028... (page rounds to 0.60).
    assert metric.dti_from_components(3.0, 1.89, 2.0) == pytest.approx(0.6028, abs=1e-3)
    # Marginal bar for a non-redundant unit dot: k > alpha * DTI.
    assert metric.marginal_inclusion_threshold(0.2778) == pytest.approx(0.05556)
