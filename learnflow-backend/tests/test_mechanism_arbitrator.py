"""三层漏斗干预仲裁器测试 —— 覆盖 健康否决 / 冲突消解 / 干预预算 三层

与治理方案 §3.3 对齐: 本组测试是 Task #11 的交付物, 也是后续把 ``FOMOEngine`` 等
nudge 引擎从「直接下发」改造为「只产出 Effect 候选」的回归基线。
"""
from __future__ import annotations

from app.services.mechanism_arbitrator import (
    ArbitrationTrace,
    BudgetPolicy,
    MechanismArbitrator,
    MemoryBudgetStore,
)
from app.services.mechanism_registry import Effect, EffectType, MechanismContext


def _ctx(user_id: str = "u1", session_id: str = "s1") -> MechanismContext:
    return MechanismContext(user_id=user_id, session_id=session_id)


def _eff(
    mid: str,
    etype: EffectType = EffectType.NUDGE,
    *,
    priority: int = 50,
    cost: float = 1.0,
    user_visible: bool = True,
    health_critical: bool = False,
    direction: str = "neutral",
) -> Effect:
    return Effect(
        mechanism_id=mid,
        effect_type=etype,
        payload={},
        priority=priority,
        cost=cost,
        user_visible=user_visible,
        health_critical=health_critical,
        direction=direction,
    )


# ---------------------------------------------------------------------------
# Layer 1 —— 健康一票否决
# ---------------------------------------------------------------------------

def test_layer1_health_veto_drops_approach_keeps_withdraw():
    """FOMO 拉回 (approach) 与未成年保护 (withdraw/health_critical) 同请求下发时,
    健康否决掉拉回, 仅保留推开方。这是真实合规风险收敛点。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach"),   # FOMO 拉回
        _eff("LF-M52", EffectType.NOTIFICATION, health_critical=True,
             direction="withdraw"),                               # 未成年保护
    ]
    out = arb.arbitrate(_ctx(), effects)
    delivered = {e.mechanism_id for e in out}
    assert delivered == {"LF-M52"}
    # 被否决的应记录到审计轨迹
    trace_and_out = arb.arbitrate(_ctx(), effects)
    # 用 trace_sink 验证
    sinked = []
    arb2 = MechanismArbitrator(trace_sink=lambda t: sinked.append(t))
    out2 = arb2.arbitrate(_ctx(), effects)
    assert sinked[0].vetoed_by_health == ["LF-M07"]
    assert "health_veto" in sinked[0].reason
    assert out2 is not None


def test_layer1_health_veto_drops_neutral_visible_but_keeps_invisible():
    """健康命中时, 普通可见 nudge (neutral) 一并被否决, 但不可见 Effect 仍保留。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M30", EffectType.NUDGE, direction="neutral"),      # 普通可见 nudge
        _eff("LF-M40", EffectType.REMINDER, user_visible=False),    # 不可见埋点
        _eff("LF-M51", EffectType.NOTIFICATION, health_critical=True,
             direction="withdraw"),                                  # 强制休息
    ]
    sinked = []
    arb2 = MechanismArbitrator(trace_sink=lambda t: sinked.append(t))
    out = arb2.arbitrate(_ctx(), effects)
    delivered = {e.mechanism_id for e in out}
    assert delivered == {"LF-M51", "LF-M40"}   # 仅健康 + 不可见
    assert sinked[0].vetoed_by_health == ["LF-M30"]


def test_layer1_no_health_passes_through():
    """无 health_critical 时, 第 1 层不改变候选集（交给第 2 层）。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach"),
        _eff("LF-M30", EffectType.NUDGE, direction="neutral"),
    ]
    out = arb.arbitrate(_ctx(), effects)
    assert {e.mechanism_id for e in out} == {"LF-M07", "LF-M30"}


# ---------------------------------------------------------------------------
# Layer 2 —— 冲突消解
# ---------------------------------------------------------------------------

def test_layer2_opposing_directions_keep_withdraw_bias():
    """approach 与 withdraw 反向同现 (无健康), 保守偏置保留 withdraw, 丢弃 approach。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach"),   # 拉回
        _eff("LF-M52", EffectType.NOTIFICATION, direction="withdraw"),  # 推开
    ]
    sinked = []
    arb2 = MechanismArbitrator(trace_sink=lambda t: sinked.append(t))
    out = arb2.arbitrate(_ctx(), effects)
    delivered = {e.mechanism_id for e in out}
    assert delivered == {"LF-M52"}   # approach 被丢弃
    assert sinked[0].dropped_by_conflict == ["LF-M07"]
    assert "conflict_bias_withdraw" in sinked[0].reason


def test_layer2_same_direction_bucket_keeps_highest_priority():
    """同 (effect_type, direction) 桶内只保留优先级最高者。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach", priority=40),
        _eff("LF-M13", EffectType.NUDGE, direction="approach", priority=90),  # 同桶更高优
    ]
    out = arb.arbitrate(_ctx(), effects)
    delivered = [e.mechanism_id for e in out]
    assert delivered == ["LF-M13"]   # 仅保留高优先级的 LF-M13


def test_layer2_different_effect_type_same_direction_both_kept():
    """同方向但不同 effect_type, 不视为同桶, 两份都保留。"""
    arb = MechanismArbitrator()
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach", priority=40),
        _eff("LF-M13", EffectType.REMINDER, direction="approach", priority=90),
    ]
    out = arb.arbitrate(_ctx(), effects)
    delivered = {e.mechanism_id for e in out}
    assert delivered == {"LF-M07", "LF-M13"}


# ---------------------------------------------------------------------------
# Layer 3 —— 干预预算
# ---------------------------------------------------------------------------

def test_layer3_session_budget_caps_visible_interventions():
    """max_per_session 限制可见干预数量, 低优先级被预算截断丢弃。

    注意: 三个 Effect 用不同 effect_type, 避免在第 2 层同桶合并中提前被合并,
    确保预算逻辑真正被触达。
    """
    policy = BudgetPolicy(max_per_session=2, max_per_day=10,
                          max_cost_per_session=100.0)
    arb = MechanismArbitrator(policy=policy)
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach", priority=90),
        _eff("LF-M13", EffectType.REMINDER, direction="approach", priority=80),
        _eff("LF-M25", EffectType.PROMPT, direction="approach", priority=70),  # 超出预算
    ]
    sinked = []
    arb2 = MechanismArbitrator(policy=policy, trace_sink=lambda t: sinked.append(t))
    out = arb2.arbitrate(_ctx(), effects)
    delivered = [e.mechanism_id for e in out]
    assert delivered == ["LF-M07", "LF-M13"]   # 仅前 2 个
    assert sinked[0].dropped_by_budget == ["LF-M25"]


def test_layer3_health_bypasses_budget():
    """health_critical 始终绕过预算, 即便会话预算已被占满也下发。

    设计要点: Layer 1 的 withdraw 存活判定读 ``_DIRECTION`` 表 (按 mechanism_id),
    而非 ``Effect.direction`` 字段 —— 因此健康命中时非健康可见 effect 已在第 1 层被
    否决, 不会与健康 effect 共存到预算层。这里直接调用 ``_apply_budget`` 验证预算层
    的「健康绕过」不变量: 预算已满时健康 effect 仍被下发。
    """
    policy = BudgetPolicy(max_per_session=1, max_per_day=1,
                          max_cost_per_session=100.0)
    arb = MechanismArbitrator(policy=policy)
    ctx = _ctx()
    trace = ArbitrationTrace(user_id=ctx.user_id, session_id=ctx.session_id)
    # 一个已占满预算的非健康可见 nudge
    pre = [_eff("LF-M07", EffectType.NUDGE, direction="approach", priority=90)]
    # 健康类在预算已满后仍应绕过下发
    effects = [_eff("LF-M52", EffectType.NOTIFICATION, health_critical=True,
                    direction="withdraw")]
    out = arb._apply_budget(ctx, pre + effects, trace)
    assert any(e.mechanism_id == "LF-M52" for e in out)
    # 且不应因预算把健康类记到 dropped_by_budget
    assert "LF-M52" not in trace.dropped_by_budget


def test_layer3_invisible_does_not_consume_budget():
    """不可见 Effect 不占预算, 全部下发。"""
    policy = BudgetPolicy(max_per_session=1, max_per_day=1,
                          max_cost_per_session=100.0)
    arb = MechanismArbitrator(policy=policy)
    effects = [
        _eff("LF-M40", EffectType.REMINDER, user_visible=False),
        _eff("LF-M41", EffectType.REMINDER, user_visible=False),
        _eff("LF-M42", EffectType.REMINDER, user_visible=False),
    ]
    out = arb.arbitrate(_ctx(), effects)
    assert {e.mechanism_id for e in out} == {"LF-M40", "LF-M41", "LF-M42"}


def test_layer3_cost_budget_caps_weighted():
    """加权成本上限: 累计 cost 超过 max_cost_per_session 即截断。

    三个 Effect 用不同 effect_type 以避开第 2 层同桶合并; 各 cost=1.0, 上限 2.0,
    故第 3 个 (累计 3.0 > 2.0) 被截断。
    """
    policy = BudgetPolicy(max_per_session=10, max_per_day=10,
                          max_cost_per_session=2.0)
    arb = MechanismArbitrator(policy=policy)
    effects = [
        _eff("LF-M07", EffectType.NUDGE, direction="approach", priority=90, cost=1.0),
        _eff("LF-M13", EffectType.REMINDER, direction="approach", priority=80, cost=1.0),
        _eff("LF-M25", EffectType.PROMPT, direction="approach", priority=70, cost=1.0),
    ]
    sinked = []
    arb2 = MechanismArbitrator(policy=policy, trace_sink=lambda t: sinked.append(t))
    out = arb2.arbitrate(_ctx(), effects)
    delivered = [e.mechanism_id for e in out]
    assert delivered == ["LF-M07", "LF-M13"]   # 累计 3.0 > 2.0, 第 3 个被截
    assert sinked[0].dropped_by_budget == ["LF-M25"]


# ---------------------------------------------------------------------------
# 审计轨迹 / 存储后端
# ---------------------------------------------------------------------------

def test_trace_sink_invoked_with_full_trace():
    """每次仲裁都应调用 trace_sink 并交付完整候选/下发轨迹。"""
    sinked = []
    arb = MechanismArbitrator(trace_sink=lambda t: sinked.append(t))
    effects = [_eff("LF-M07", EffectType.NUDGE, direction="approach")]
    arb.arbitrate(_ctx(), effects)
    assert len(sinked) == 1
    t = sinked[0]
    assert isinstance(t, ArbitrationTrace)
    assert t.candidates == ["LF-M07"]
    assert t.delivered == ["LF-M07"]


def test_memory_store_incr_and_ignore():
    """MemoryBudgetStore 计数后端接口可用。"""
    store = MemoryBudgetStore()
    assert store.incr("budget", "u1:session", window_sec=3600) == 1
    assert store.incr("budget", "u1:session", window_sec=3600) == 2
    assert store.record_ignore("u1") == 1
    assert store.record_ignore("u1") == 2
    assert store.ignored_count("u1") == 2
    assert store.ignored_count("u2") == 0


def test_direction_table_covers_health_and_nudge_ids():
    """_DIRECTION 表必须登记治理方案 §3.3.4 列出的所有 approach/withdraw 机制。"""
    directions = MechanismArbitrator._DIRECTION
    assert all(directions[m] == "approach"
               for m in ["LF-M07", "LF-M08", "LF-M10", "LF-M13", "LF-M25",
                         "LF-M26", "LF-M33", "LF-M35", "LF-M44"])
    assert all(directions[m] == "withdraw"
               for m in ["LF-M51", "LF-M52", "LF-M53"])
