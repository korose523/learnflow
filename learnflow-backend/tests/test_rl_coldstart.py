"""RL 在线学习「冷启动死锁」的回归测试。

═══ 为什么需要这个文件 ═══════════════════════════════════════════════

AI 行为管控链路曾出现过一次**名义接通、实际永远不生效**的缺陷, 而当时 843 个
测试全绿 —— 因为没有任何测试验证过「从零开始能不能学起来」。缺陷链条是:

    1. BanditPolicy.trained() == "Q 表非空", 而 Q 只由 update() 写入;
    2. RLArbitrator.select_mechanism() 在未 trained 时返回 None (用规则决策);
    3. 反馈入口却要求 ``rl_arbitrator.trained()`` 为 True 才 observe。

    → 于是: 不 observe 就永远不 trained, 不 trained 就永远不 observe。
      死锁。整条「AI 管控用户行为」链路等于换个地方继续当死代码。

修复思路是把**两个被混为一谈的门分开**:
    * 学习门 (observe): 无条件 —— 只要拿到有效信号就学。
    * 决策门 (ready): 该风险档下某 arm 已达 MIN_OBS_FOR_DECISION 次观测才放行,
      避免单次噪声主导给未成年人下发什么干预。

并引入**影子学习**: 冷启动期由规则层决策, 但把规则层实际下发的 approach 机制
登记为反馈目标供观测 —— 只观测、不干预, 本轮下发结果与未接线时完全一致。
"""
from __future__ import annotations

import pytest

from app.services.mechanism_arbitrator import MechanismArbitrator, MechanismContext
from app.services.mechanism_registry import Effect, EffectType
from app.services.rl_arbitrator import (
    RLArbitrator,
    BanditPolicy,
    MIN_OBS_FOR_DECISION,
)

# lai_risk=0.4 -> 风险档 t2 (0.35 <= 0.4 < 0.6), 且不触发 1.5 层 LAI 冷却
# (0.9 * 0.4 = 0.36 < 0.4), 从而隔离出纯 RL 行为。
TIER2_RISK = 0.4


def _approach_effects() -> list:
    """两个 approach 机制 (LF-M44 / LF-M33) + 一个 neutral (LF-M19)。"""
    return [
        Effect("LF-M44", EffectType.NUDGE, {}, priority=70),      # approach
        Effect("LF-M33", EffectType.REMINDER, {}, priority=60),   # approach
        Effect("LF-M19", EffectType.BADGE, {}, priority=50),      # neutral
    ]


def _arb_with_rl() -> tuple:
    """返回一个注入了**全新未训练** RL 仲裁器的 MechanismArbitrator。"""
    arb = MechanismArbitrator()
    rl = RLArbitrator(rule_arbitrator=MechanismArbitrator())
    arb.rl_arbitrator = rl
    return arb, rl


def test_coldstart_registered_shadow_target():
    """冷启动 (RL 未学够) 时, 规则层下发的 approach 机制应被登记为影子反馈目标。"""
    arb, rl = _arb_with_rl()
    assert not rl.trained()

    out = arb.arbitrate(
        MechanismContext("u1", session_id="s1"), _approach_effects(), lai_risk=TIER2_RISK
    )
    delivered = [e.mechanism_id for e in out]

    rec = arb._rl_pending.get(("u1", "s1"))
    assert rec is not None, "冷启动期必须登记反馈目标, 否则 Q 表永远起不来"
    assert rec["shadow"] is True
    assert rec["risk_tier"] == 2
    # 影子目标必须是本轮**确实下发**的 approach 机制, 不能凭空捏造
    assert rec["chosen_id"] in delivered
    assert arb._DIRECTION.get(rec["chosen_id"]) == "approach"
    # 冷启动不干预决策: 两个 approach 都还在 (规则层行为不变)
    assert "LF-M44" in delivered and "LF-M33" in delivered


def test_coldstart_observe_breaks_deadlock():
    """★ 核心回归: 冷启动下 report_reward 必须能把奖励写进 Q 表。

    修复前, 反馈入口要求 trained() 为 True, 而 Q 表为空 -> 恒为 False -> 永远
    不 observe -> 永远训练不起来。这条测试直接钉死该行为。
    """
    arb, rl = _arb_with_rl()
    arb.arbitrate(
        MechanismContext("u1", session_id="s1"), _approach_effects(), lai_risk=TIER2_RISK
    )
    assert rl.bandit.Q == {}, "冷启动期 RL 未接管, 此时 Q 表应仍为空"

    fed = arb.report_reward("u1", 0.5, session_id="s1")

    assert fed is not None, "冷启动期必须能回灌奖励 (死锁修复点)"
    tier, mid = fed
    assert tier == 2 and mid
    assert rl.trained(), "observe 之后 Q 表必须有内容, 否则死锁未解除"
    assert rl.bandit.counts["t2"][mid] == 1


def test_decision_gate_requires_min_observations():
    """决策门比学习门严格: 学过的档位也要攒够 MIN_OBS_FOR_DECISION 次才放行。"""
    rl = RLArbitrator()
    rl.observe(2, "LF-M44", 1.0)

    # 已「学到过东西」, 但只有 1 次观测 —— 不足以接管决策
    assert rl.trained() is True
    assert rl.ready(2) is False, "单次观测就接管决策会让噪声主导机制选择"

    for _ in range(MIN_OBS_FOR_DECISION - 1):
        rl.observe(2, "LF-M44", 1.0)
    assert rl.ready(2) is True
    # 风险档是分档授权的: 在 t2 学够了不代表能管 t0
    assert rl.ready(0) is False


def test_rl_takes_over_after_shadow_warmup():
    """端到端: 冷启动影子预热若干轮后, RL 应接管该风险档的决策。"""
    arb, rl = _arb_with_rl()
    rl.bandit.epsilon = 0.0  # 测试确定性: 永远选 Q 最大者

    # 影子预热: 每轮规则层决策 + 观测。LF-M44 给高奖励, LF-M33 给低奖励。
    for i in range(MIN_OBS_FOR_DECISION + 2):
        out = arb.arbitrate(
            MechanismContext("u1", session_id=f"s{i}"),
            _approach_effects(),
            lai_risk=TIER2_RISK,
        )
        delivered = [e.mechanism_id for e in out]
        rec = arb._rl_pending[("u1", f"s{i}")]
        reward = 1.0 if rec["chosen_id"] == "LF-M44" else 0.0
        arb.report_reward("u1", reward, session_id=f"s{i}")

    assert rl.ready(2) is True, "影子预热后应达到接管门槛"

    out = arb.arbitrate(
        MechanismContext("u1", session_id="final"), _approach_effects(), lai_risk=TIER2_RISK
    )
    delivered = [e.mechanism_id for e in out]
    approach_delivered = [m for m in delivered if arb._DIRECTION.get(m) == "approach"]

    # RL 接管: approach 只剩它选中的那一个; neutral 不受影响
    assert approach_delivered == ["LF-M44"], (
        f"RL 应选中高奖励的 LF-M44 并丢弃其余 approach, 实际 {approach_delivered}"
    )
    assert "LF-M19" in delivered
    # 此时不再是影子, 而是 RL 的真实决策
    assert arb._rl_pending[("u1", "final")]["shadow"] is False


def test_shadow_learning_does_not_alter_delivery():
    """影子学习只观测、不干预: 冷启动期下发结果必须与未注入 RL 时完全一致。"""
    effects_a = _approach_effects()
    effects_b = _approach_effects()

    plain = MechanismArbitrator()
    out_plain = [e.mechanism_id for e in
                 plain.arbitrate(MechanismContext("u"), effects_a, lai_risk=TIER2_RISK)]

    arb, rl = _arb_with_rl()
    out_shadow = [e.mechanism_id for e in
                  arb.arbitrate(MechanismContext("u"), effects_b, lai_risk=TIER2_RISK)]

    assert out_plain == out_shadow, "影子学习不得改动任何下发结果 (保守偏置不变)"
    # 但确实留下了可供学习的目标
    assert arb._rl_last["u"]["shadow"] is True


def test_report_reward_none_when_no_target():
    """无反馈对象时返回 None, 调用方据此跳过 (不写脏数据)。"""
    arb = MechanismArbitrator()  # 未注入 rl_arbitrator
    assert arb.report_reward("u", 1.0) is None

    arb2, rl = _arb_with_rl()
    # 注入了 RL 但该用户从未仲裁过 -> 无目标
    assert arb2.report_reward("nobody", 1.0) is None
    assert not rl.trained()


def test_bandit_ready_vs_trained_semantics():
    """钉死 trained()/ready() 的语义区分, 防止后人又把二者混为一谈。"""
    b = BanditPolicy(seed=7)
    assert not b.trained() and not b.ready("t1")

    b.update("t1", "A", 1.0)
    # trained 只要「学到过」就为真; ready 要求学够
    assert b.trained()
    assert not b.ready("t1")

    for _ in range(MIN_OBS_FOR_DECISION - 1):
        b.update("t1", "A", 1.0)
    assert b.ready("t1")


@pytest.mark.parametrize("reward", [-1.0, -0.3, 0.0, 0.4, 1.0])
def test_negative_reward_pushes_q_down(reward):
    """负奖励 (如未成年保护阻断) 必须真的把 Q 拉低, bandit 才学得会避开有害 arm。"""
    b = BanditPolicy(seed=3)
    b.epsilon = 0.0
    b.update("t3", "BAD", reward)
    assert b.Q["t3"]["BAD"] == pytest.approx(0.1 * reward)
    if reward < 0:
        assert b.Q["t3"]["BAD"] < 0
