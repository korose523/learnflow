"""补全实验 (GAP-1 / GAP-7) 单元测试：类别级消融预设 + 真实样本量门槛

镜像 tests/test_abtest_framework_v2.py 的实验搭建方式（独立 ABTestFramework 实例）。
"""
import pytest

from app.services.ab_test_framework import (
    ABTestFramework,
    ExperimentPhase,
    ExperimentResult,
)
from app.services import mechanism_registry


@pytest.fixture
def fw():
    """每个测试用全新框架实例，避免污染全局单例。"""
    return ABTestFramework()


def test_toggles_for_category_returns_all_false_for_category(fw):
    """类别级消融预设：返回该类别**全部**机制 = False，且集合等于 by_category(cat)。"""
    for cat in ["retention", "motivation", "selfreg", "cognition", "health"]:
        toggles = fw.toggles_for_category(cat)
        expected_ids = {spec.id for spec in mechanism_registry.by_category(cat)}
        assert set(toggles.keys()) == expected_ids
        assert all(v is False for v in toggles.values())

    # 治理字母也按映射解析：H → health
    assert set(fw.toggles_for_category("H").keys()) == {
        spec.id for spec in mechanism_registry.by_category("health")
    }
    # 非法输入应报错
    with pytest.raises(ValueError):
        fw.toggles_for_category("Z")


def test_advance_respects_required_n(fw):
    """阶段推进尊重真实样本量门槛 required_n_per_group；--force 才强制推进。"""
    exp = fw.create_experiment(name="门槛测试", description="")
    fw.set_required_n(exp.id, 200, deff=1.0)
    # 推进到 canary（强制）
    fw.advance_phase(exp.id, force=True)
    assert fw.get_experiment(exp.id).phase == ExperimentPhase.CANARY

    # 加入少于 200 个 treatment 结果（直接追加，绕开分配以确定性构造）
    exp = fw.get_experiment(exp.id)
    for i in range(10):
        exp.results.append(ExperimentResult(
            experiment_id=exp.id, user_id=f"u{i}", group="treatment", metrics={},
        ))
    fw._store.save_experiment(exp)

    # 不强制：门槛未达，停留在 CANARY
    assert fw.advance_phase(exp.id, force=False) == ExperimentPhase.CANARY
    assert fw.get_experiment(exp.id).phase == ExperimentPhase.CANARY

    # 强制：跳过门槛推进到 RAMPING
    assert fw.advance_phase(exp.id, force=True) == ExperimentPhase.RAMPING
    assert fw.get_experiment(exp.id).phase == ExperimentPhase.RAMPING
