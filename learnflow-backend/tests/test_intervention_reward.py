"""干预奖励函数单元测试 —— 覆盖伦理约束与边界。

重点守卫:
  * compute_reward 各分支 (掌握度提升为正 / 风险上升为负 / 加权组合 / 信号缺失)
  * ★ 未成年保护阻断 -> reward 恒为 -1.0 (硬约束)
  * ★ 反成瘾守卫: 优化目标里**不得**包含任何时长 / 活跃度 / 答题量 / 连胜类指标
  * 奖励裁剪到 [-1, 1]
  * describe_reward_weights 可被论文/审计引用
"""
from app.services.intervention_reward import (
    BLOCKED_PENALTY,
    CLIP_MAX,
    CLIP_MIN,
    InterventionSignals,
    compute_reward,
    describe_reward_weights,
)


def test_mastery_gain_is_positive():
    r = compute_reward(InterventionSignals(
        mastery_before=0.3, mastery_after=0.6,
        risk_before=0.2, risk_after=0.2,
    ))
    # 0.6 * (0.6 - 0.3) = 0.18
    assert r == 0.18
    assert r > 0


def test_risk_rise_is_negative():
    r = compute_reward(InterventionSignals(
        mastery_before=0.5, mastery_after=0.5,
        risk_before=0.2, risk_after=0.5,
    ))
    # 0.4 * -(0.5 - 0.2) = -0.12
    assert r == -0.12
    assert r < 0


def test_combined_weighted():
    # 掌握度 +0.4 -> +0.24; 风险 -0.3 -> +0.12; 合计 +0.36
    r = compute_reward(InterventionSignals(
        mastery_before=0.2, mastery_after=0.6,
        risk_before=0.8, risk_after=0.5,
    ))
    assert r == 0.36


def test_missing_signal_treated_as_zero():
    # mastery before 缺失 -> mastery 项按 0; 仅风险项生效
    r = compute_reward(InterventionSignals(
        mastery_before=None, mastery_after=0.6,
        risk_before=0.2, risk_after=0.5,
    ))
    assert r == -0.12
    # risk after 缺失 -> risk 项按 0; 仅掌握度项生效
    r2 = compute_reward(InterventionSignals(
        mastery_before=0.3, mastery_after=0.6,
        risk_before=0.2, risk_after=None,
    ))
    assert r2 == 0.18


def test_blocked_by_protection_is_hard_minus_one():
    # 硬约束优先于一切: 即便掌握度大涨, 触发未成年保护阻断仍返回 -1.0
    r = compute_reward(InterventionSignals(
        mastery_before=0.0, mastery_after=1.0,
        risk_before=0.0, risk_after=0.0,
        blocked_by_protection=True,
    ))
    assert r == BLOCKED_PENALTY
    assert r == -1.0


def test_reward_clipped_to_unit_interval():
    # 正向极值: 掌握度 +1 且风险 -1 -> 0.6 + 0.4 = 1.0
    pos = compute_reward(InterventionSignals(
        mastery_before=0.0, mastery_after=1.0,
        risk_before=1.0, risk_after=0.0,
    ))
    assert pos == 1.0
    # 负向极值: 掌握度 -1 且风险 +1 -> -0.6 - 0.4 = -1.0
    neg = compute_reward(InterventionSignals(
        mastery_before=1.0, mastery_after=0.0,
        risk_before=0.0, risk_after=1.0,
    ))
    assert neg == -1.0
    assert CLIP_MIN <= pos <= CLIP_MAX
    assert CLIP_MIN <= neg <= CLIP_MAX


def test_anti_addiction_guard_no_duration_or_stickiness_metric():
    """★ 反成瘾守卫: 优化目标不得包含任何「让人对 App 上瘾」的指标。

    构造「使用时长很长但掌握度没提升」的信号, 断言 reward 不因时长而变高 ——
    因为 compute_reward 根本不接受时长类输入。本测试通过两点锁死这条红线:

      1) InterventionSignals 的字段集里**没有**任何时长 / 活跃度 / 答题量 /
         连胜类字段 (防止后人偷偷加进去);
      2) 在「零掌握度增益、零风险变化」下, reward 恰为 0, 与时长无关。
    """
    _FORBIDDEN_FIELD_SUBSTRINGS = (
        "duration", "stay", "time", "active", "login", "answer_count",
        "drill", "streak", "consecutive", "retention", "engagement",
        "stickiness", "频率", "时长", "活跃", "答题", "连胜", "粘性", "留存",
    )
    fields = set(InterventionSignals.__dataclass_fields__.keys())
    leaked = [f for f in fields if any(s in f.lower() for s in _FORBIDDEN_FIELD_SUBSTRINGS)]
    assert not leaked, f"奖励信号里混入了成瘾化指标字段: {leaked}"

    # 模拟「刷了很久但没学会」: 没有时长字段可填, 掌握度不变, 风险不变
    r = compute_reward(InterventionSignals(
        mastery_before=0.5, mastery_after=0.5,
        risk_before=0.1, risk_after=0.1,
    ))
    assert r == 0.0, "零掌握度增益时奖励必须为 0, 不得被任何时长类信号抬高"


def test_describe_reward_weights_shape():
    w = describe_reward_weights()
    assert w["w_mastery"] == 0.6
    assert w["w_health"] == 0.4
    assert w["clip_min"] == -1.0
    assert w["clip_max"] == 1.0
    # 显式声明禁止项与允许项, 供审计脚本断言
    assert "usage_duration" in w["forbidden_features"]
    assert "streak_length" in w["forbidden_features"]
    assert w["allowed_features"] == ["mastery_gain", "risk_drop"]
