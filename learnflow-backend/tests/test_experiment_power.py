"""实验功效分析单元测试 —— 样本量预注册 (§3.4.2 改造 5)"""
from app.services.experiment_power import (
    design_effect,
    required_n_per_group,
    required_n_two_proportion,
    plan_experiment,
    PowerPlan,
)


def test_design_effect_known_value():
    """m=30, ρ=0.05 → DEFF=2.45 (治理方案明确给出的数值)。"""
    assert design_effect(30, 0.05) == 2.45


def test_design_effect_individual_randomization():
    """个体随机 (cluster_size=1) 或 icc=0 时 DEFF=1。"""
    assert design_effect(1, 0.05) == 1.0
    assert design_effect(30, 0.0) == 1.0


def test_design_effect_monotonic():
    """DEFF 随班级规模与 ICC 单调不减。"""
    assert design_effect(40, 0.05) > design_effect(30, 0.05)
    assert design_effect(30, 0.10) > design_effect(30, 0.05)


def test_required_n_per_group_known_d():
    """d=0.5, α=0.05, power=0.80, 无 DEFF → n=63 (标准两样本公式)。"""
    assert required_n_per_group(0.5, 0.05, 0.80, 1.0) == 63


def test_required_n_per_group_scales_with_deff():
    """整群随机使样本量按 DEFF 放大。"""
    base = required_n_per_group(0.5, 0.05, 0.80, 1.0)
    clustered = required_n_per_group(0.5, 0.05, 0.80, 2.45)
    # 154 = ceil(63 * 2.45) 附近
    assert clustered >= base
    assert 150 <= clustered <= 160


def test_required_n_two_proportion_monotonic():
    """率差越大所需样本越小。"""
    n_small = required_n_two_proportion(0.5, 0.6, 0.05, 0.80, 1.0)
    n_large = required_n_two_proportion(0.5, 0.7, 0.05, 0.80, 1.0)
    assert n_small > 0 and n_large > 0
    assert n_small > n_large


def test_plan_experiment_continuous_consistency():
    """plan_experiment 的 continuous 路径与底层函数一致。"""
    plan: PowerPlan = plan_experiment(
        effect_size=0.3, metric_type="continuous",
        cluster_size=30, icc=0.05,
    )
    assert plan.deff == 2.45
    assert plan.required_n_per_group == required_n_per_group(0.3, 0.05, 0.80, 2.45)
    assert plan.total_n == plan.required_n_per_group * 2
    assert plan.required_clusters == (plan.total_n + 29) // 30  # ceil(total/30)


def test_plan_experiment_binary_uses_baseline():
    """binary 路径以 baseline_rate 为对照组率构造率差。"""
    plan = plan_experiment(
        effect_size=0.1, metric_type="binary",
        baseline_rate=0.5, cluster_size=1, icc=0.0,
    )
    assert plan.deff == 1.0
    assert plan.required_n_per_group == required_n_two_proportion(0.5, 0.6, 0.05, 0.80, 1.0)


def test_plan_experiment_rejects_bad_baseline():
    import pytest
    with pytest.raises(ValueError):
        plan_experiment(effect_size=0.1, metric_type="binary", baseline_rate=1.0)
