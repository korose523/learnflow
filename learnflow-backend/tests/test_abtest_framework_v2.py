"""A/B 框架 §3.4.2 改造 单元测试: 机制开关 / 统计修正 / 落库后端 / 注册表指纹"""
import pytest

from app.services.ab_test_framework import (
    ABTestFramework,
    JSONFileExperimentStore,
    ExperimentPhase,
)
from app.services.mechanism_registry import (
    registry_fingerprint,
    ABTestToggleProvider,
)


@pytest.fixture
def fw():
    """每个测试用全新框架实例，避免污染全局单例。"""
    return ABTestFramework()


def test_experiment_carries_new_fields(fw):
    """Experiment 携带机制开关与统计治理字段，to_dict 一并暴露。"""
    exp = fw.create_experiment(
        name="FOMO 消融",
        description="关闭 LF-M44",
        mechanism_toggles={"LF-M44": False},
        primary_metric="retention_rate",
        mde=0.3,
        icc_assumed=0.05,
        cluster_randomized=True,
    )
    assert exp.mechanism_toggles == {"LF-M44": False}
    assert exp.primary_metric == "retention_rate"
    assert exp.mde == 0.3
    d = exp.to_dict()
    assert d["mechanism_toggles"] == {"LF-M44": False}
    assert "required_n_per_group" in d
    assert "registry_fingerprint" in d


def test_get_mechanism_toggles_treatment_only(fw):
    """treatment 用户拿到实验 toggles；control 用户拿不到（合并规则）。"""
    exp = fw.create_experiment(
        name="类别消融",
        description="关闭一整类",
        mechanism_toggles={"LF-M23": False, "LF-M24": False},
    )
    fw.advance_phase(exp.id, force=True)  # canary (5% 流量，保证两组都有样本)

    # 找出分到 treatment 与 control 的用户
    treatment_user = control_user = None
    for uid in [f"user_{i}" for i in range(500)]:
        g = fw.assign_user(exp.id, uid)
        if g == "treatment" and treatment_user is None:
            treatment_user = uid
        if g == "control" and control_user is None:
            control_user = uid
        if treatment_user and control_user:
            break

    assert treatment_user is not None and control_user is not None
    assert fw.get_mechanism_toggles(treatment_user) == {"LF-M23": False, "LF-M24": False}
    assert fw.get_mechanism_toggles(control_user) == {}


def test_is_mechanism_enabled_rules(fw):
    """health_critical 永开; treatment 且被 toggle 关则关; control 恒开。"""
    exp = fw.create_experiment(
        name="单机制消融",
        description="关闭 LF-M44",
        mechanism_toggles={"LF-M44": False},
    )
    fw.advance_phase(exp.id, force=True)  # canary

    treatment_user = next(
        u for u in (f"user_{i}" for i in range(500))
        if fw.assign_user(exp.id, u) == "treatment"
    )
    control_user = next(
        u for u in (f"user_{i}" for i in range(500))
        if fw.assign_user(exp.id, u) == "control"
    )

    # 健康临界机制不被关闭
    assert fw.is_mechanism_enabled(exp.id, treatment_user, "LF-M52",
                                   health_critical=True) is True
    # treatment 下 LF-M44 被关
    assert fw.is_mechanism_enabled(exp.id, treatment_user, "LF-M44") is False
    # control 下 LF-M44 仍开
    assert fw.is_mechanism_enabled(exp.id, control_user, "LF-M44") is True
    # 未显式 toggle 的机制默认开
    assert fw.is_mechanism_enabled(exp.id, treatment_user, "LF-M07") is True


def test_cohens_d_correct_pooled_sd():
    """纠正原框架用控制组 SD 近似 pooled SD 的错误。"""
    control = [1, 2, 3, 4, 5]
    treatment = [2, 3, 4, 5, 6]
    d = ABTestFramework.cohens_d(control, treatment)
    # 手算: m1=3, m2=4, pooled var=2.5, sd=1.5811, d=0.6325
    assert abs(d - 0.6325) < 0.01


def test_cohens_d_small_sample_returns_zero():
    assert ABTestFramework.cohens_d([1], [2]) == 0.0


def test_required_n_per_group_static():
    """静态样本量函数直接可用。"""
    assert ABTestFramework.required_n_per_group(0.5, 0.05, 0.80, 1.0) == 63
    assert ABTestFramework.design_effect(30, 0.05) == 2.45


def test_set_required_n_writes_power_result(fw):
    """功效分析回填样本量到实验。"""
    exp = fw.create_experiment(name="功效回填", description="")
    fw.set_required_n(exp.id, 428, deff=2.45)
    reloaded = fw.get_experiment(exp.id)
    assert reloaded.required_n_per_group == 428
    assert reloaded.deff == 2.45


def test_json_store_round_trip(tmp_path):
    """JSONFileExperimentStore 落库后重开一致（满足 90 天追踪 + 可复现）。"""
    path = str(tmp_path / "experiments.json")
    fw1 = ABTestFramework(store=JSONFileExperimentStore(path))
    exp = fw1.create_experiment(
        name="落库测试",
        description="d",
        mechanism_toggles={"LF-M44": False},
    )
    fw1.advance_phase(exp.id, force=True)
    fw1.record_result(exp.id, "u1", {"exam_score": 80, "risk_score": 30})

    # 新进程/新实例从同一文件载入
    fw2 = ABTestFramework(store=JSONFileExperimentStore(path))
    loaded = fw2.get_experiment(exp.id)
    assert loaded is not None
    assert loaded.name == "落库测试"
    assert loaded.mechanism_toggles == {"LF-M44": False}
    assert loaded.phase == ExperimentPhase.CANARY
    assert len(loaded.results) == 1
    assert loaded.results[0].metrics["exam_score"] == 80


def test_registry_fingerprint_stable_and_anchored():
    """注册表指纹稳定，可写入实验以锚定可复现性。"""
    fp1 = registry_fingerprint()
    fp2 = registry_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 12
    # 写入实验后可读回
    fw2 = ABTestFramework()
    exp = fw2.create_experiment(
        name="指纹锚定", description="", registry_fingerprint=fp1,
    )
    assert exp.registry_fingerprint == fp1


def test_ab_test_toggle_provider_adapter():
    """ABTestToggleProvider 把框架适配为注册表开关入口。"""
    fw3 = ABTestFramework()
    exp = fw3.create_experiment(
        name="适配器", description="",
        mechanism_toggles={"LF-M44": False},
    )
    fw3.advance_phase(exp.id, force=True)  # canary

    provider = ABTestToggleProvider(fw3)
    treatment_user = next(
        u for u in (f"user_{i}" for i in range(500))
        if fw3.assign_user(exp.id, u) == "treatment"
    )
    toggles = provider.get_toggles(treatment_user)
    assert toggles.get("LF-M44") is False
    # 健康机制不被关闭
    assert provider.is_enabled(treatment_user, "LF-M52", health_critical=True) is True
    assert provider.is_enabled(treatment_user, "LF-M44") is False
