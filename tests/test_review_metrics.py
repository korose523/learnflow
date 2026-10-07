import importlib.util
from pathlib import Path
import math
import random
import pytest
from scipy.stats import kendalltau

spec = importlib.util.spec_from_file_location('metrics', Path(__file__).resolve().parents[1] / 'results/m3/exogenous_metrics.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_auc_hand_calculation_and_order_invariance():
    # Teacher-different pairs: one tie (0.5), two concordant (1 each).
    x, y = [1, 1, 2], [1, 2, 3]
    assert m.ordinal_auc(x, y) == pytest.approx(5 / 6)
    assert m.ordinal_auc(x[::-1], y[::-1]) == pytest.approx(5 / 6)
    assert m.ordinal_auc([1, 1, 1], y) == 0.5
    assert m.ordinal_auc([3, 2, 1], y) == 0
    assert math.isnan(m.ordinal_auc(x, [1, 1, 1]))

def test_tau_matches_scipy_with_joint_ties():
    rng = random.Random(7)
    for _ in range(50):
        x = [rng.randrange(1, 4) for _ in range(20)]
        y = [rng.randrange(1, 4) for _ in range(20)]
        assert m.kendall_tau_b(x, y) == pytest.approx(kendalltau(x, y).statistic)
    assert math.isnan(m.kendall_tau_b([1, 1], [2, 3]))
