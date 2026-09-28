"""K1 · Thompson Sampling 最小正确实现的自测（不依赖第三方库）。"""
import math
import random

from app.services.thompson_sampling import (
    beta_sample,
    thompson_sample,
    update_posterior,
)


def test_beta_sample_range_and_mean():
    rng = random.Random(0)
    samples = [beta_sample(2.0, 5.0, rng) for _ in range(4000)]
    assert all(0.0 < s < 1.0 for s in samples)
    # Beta(2,5) 均值 = 2/7 ≈ 0.2857；大样本应接近
    mean = sum(samples) / len(samples)
    assert abs(mean - 2.0 / 7.0) < 0.03


def test_thompson_favors_dominant_arm():
    # 臂0 后验强（α=50, β=1）应几乎总被选中；臂1 弱（α=1, β=50）。
    # 采用统计断言：极端 Gamma 样本在 <0.5% 概率下可能翻转胜者，故要求 >=99.5% 选臂0。
    rng = random.Random(42)
    wins = sum(
        1 for _ in range(2000)
        if thompson_sample([(50.0, 1.0), (1.0, 50.0)], rng) == 0
    )
    assert wins >= 1990  # 压倒性偏好臂 0（>=99.5%）


def test_thompson_balances_when_priors_equal():
    # 两臂对称先验 ⇒ 选中下标不应恒为某一侧（探索生效）
    rng = random.Random(7)
    picks = [thompson_sample([(1.0, 1.0), (1.0, 1.0)], rng) for _ in range(500)]
    assert set(picks) == {0, 1}


def test_thompson_deterministic_with_seed():
    a = thompson_sample([(3.0, 2.0), (2.0, 3.0)], random.Random(123))
    b = thompson_sample([(3.0, 2.0), (2.0, 3.0)], random.Random(123))
    assert a == b


def test_update_posterior():
    assert update_posterior(1.0, 1.0, success=True) == (2.0, 1.0)
    assert update_posterior(1.0, 1.0, success=False) == (1.0, 2.0)


def test_empty_arms_raises():
    import pytest

    with pytest.raises(ValueError):
        thompson_sample([])
