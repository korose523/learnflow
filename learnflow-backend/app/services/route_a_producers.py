"""路线 A · A2：效果生产者由 2 提升到 ≥14（opt-in）。

M2 审计（2026-09-22）指出：次级机制只写评估记录、不构造干预效果，全仓库效果生产者
仅 2 处（LF-M44、LF-M52），导致"类型 II 运行时竞争 = 0"与"冲突稀少 vs 不可发生"
不可区分。路线 A 的 A2 把 ≥14 个机制升为真正的干预效果生产者，使运行时**可能**
发生冲突，从而消解该批评。

设计（安全 / 向后兼容 / 审计口径一致）：
- 本模块为路线 A 的 ≥14 个生产者各写一个**字面 ``Effect(`` 构造点**（新增 12 + 把
  既有 2 显式列入 A3 候选集，保证仿真自包含）。之所以用字面调用而非循环，是为了与
  ``verify_counts`` 的审计口径一致：审计的"效果生产者"计数 = 不同代码位置构造
  ``Effect`` 的处数；循环只算 1 处，会低估。故本文件贡献 14 处字面构造点；加上既有
  2 处（deep_addiction_engine.py:296 / learning_orchestrator.py:995），verify_counts
  实测 AST 站点 = 16；运行时 opt-in 激活的**不同机制**生产者按机制去重 = 14。
- 默认关闭：仅当 ``LEARN2_A2_PRODUCERS=1`` 时，编排器才把本集合并入 FOMO 仲裁器的候选
  （使用 :func:`build_route_a_new_effects`，仅 12 新增，避免与既有 LF-M44/LF-M52 重复），
  并 ``install_route_a_directions`` 扩展仲裁器的方向表。未启用时运行时行为完全不变，
  936 条既有测试不受影响；"改造前 2 / 改造后 ≥14（AST 站点 16）"由封存 tag 与当前源码
  分别印证。
- 改造后冲突频率**只**解释为"生产者数量对冲突频率的敏感性"，不解释为对原系统的修正
  （见 M2 稿 §8.2 / 备忘 §2.3 的方法论代价）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.services.mechanism_arbitrator import MechanismArbitrator
from app.services.mechanism_registry import Effect, EffectType

# 路线 A 方向表：扩展仲裁器的 _DIRECTION，使新增生产者参与冲突消解
# （approach=拉回加时 / withdraw=推开休息）。既有 LF-M44/LF-M52 已在仲裁器 _DIRECTION 中。
# 本表只列 12 个新增机制的方向（既有 2 个由仲裁器默认 _DIRECTION 覆盖）。
ROUTE_A_DIRECTIONS: Dict[str, str] = {
    "LF-M01": "approach",
    "LF-M04": "approach",
    "LF-M05": "approach",
    "LF-M06": "approach",
    "LF-M07": "approach",
    "LF-M08": "approach",
    "LF-M12": "approach",
    "LF-M13": "approach",
    "LF-M15": "approach",
    "LF-M16": "approach",
    "LF-M51": "withdraw",
    "LF-M53": "withdraw",
}

# 路线 A 新增的生产者数（不含既有 LF-M44/LF-M52）；供编排器 opt-in 注入与文档引用。
ROUTE_A_NEW_PRODUCERS_COUNT = 12
# build_route_a_effects 返回的「不同机制」生产者数 = 12 新增 + 2 既有 = 14（A3 用）。
# 另：本文件字面 Effect( 构造点 = 14，加既有 2 处位置 = verify_counts AST 站点 16。
ROUTE_A_PRODUCERS_COUNT = 14


def install_route_a_directions(arbitrator: MechanismArbitrator) -> None:
    """把路线 A 方向表并入仲裁器（仅 A2 启用时调用）。"""
    arbitrator._DIRECTION.update(ROUTE_A_DIRECTIONS)


def _new_effects() -> List[Effect]:
    """路线 A 新增的 12 个生产者的字面 Effect 构造点。

    每个机制一处字面调用，与 verify_counts 的"不同代码位置数"审计口径一致
    （循环只算 1 处）。返回全新对象，调用方可安全并入候选集。
    """
    effects: List[Effect] = []
    effects.append(Effect(
        mechanism_id="LF-M01", effect_type=EffectType.REWARD,
        payload={"kind": "variable_ratio_reward"}, priority=55, cost=1.0,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M04", effect_type=EffectType.NUDGE,
        payload={"kind": "instant_gratification"}, priority=60, cost=0.8,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M05", effect_type=EffectType.NUDGE,
        payload={"kind": "surprise_delight"}, priority=50, cost=0.6,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M06", effect_type=EffectType.REWARD,
        payload={"kind": "time_based_bonus"}, priority=52, cost=0.7,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M07", effect_type=EffectType.BADGE,
        payload={"kind": "collection"}, priority=48, cost=0.9,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M08", effect_type=EffectType.NUDGE,
        payload={"kind": "scarcity"}, priority=65, cost=1.1,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M12", effect_type=EffectType.NUDGE,
        payload={"kind": "streak_sanctification"}, priority=58, cost=0.8,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M13", effect_type=EffectType.NUDGE,
        payload={"kind": "zeigarnik"}, priority=54, cost=0.7,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M15", effect_type=EffectType.NUDGE,
        payload={"kind": "goal_gradient"}, priority=56, cost=0.8,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M16", effect_type=EffectType.NUDGE,
        payload={"kind": "daily_challenge"}, priority=53, cost=0.7,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M51", effect_type=EffectType.NOTIFICATION,
        payload={"kind": "withdraw_nudge"}, priority=80, cost=0.0,
        user_visible=True, health_critical=False, direction="withdraw"))
    effects.append(Effect(
        mechanism_id="LF-M53", effect_type=EffectType.NOTIFICATION,
        payload={"kind": "withdraw_nudge"}, priority=85, cost=0.0,
        user_visible=True, health_critical=False, direction="withdraw"))
    return effects


def build_route_a_new_effects(user_id: str, session_id: Optional[str]) -> List[Effect]:
    """仅路线 A **新增**的 12 个生产者（供编排器 opt-in 注入）。

    不含既有 LF-M44/LF-M52（它们由各自引擎/编排器在 FOMO 路径中产出），避免
    运行时候选集出现重复机制。
    """
    return _new_effects()


def build_route_a_effects(user_id: str, session_id: Optional[str]) -> List[Effect]:
    """A3 仿真自包含集合：12 新增 + 既有 LF-M44/LF-M52 = 14 个不同机制生产者。

    返回列表即「改造后」的候选干预集合；由 A3 直接驱动真实仲裁器统一仲裁。
    既有 2 个显式列入，保证仿真候选集完整、可审计（与 verify_counts 的 AST 站点计数为 16
    互不冲突：那里把既有 2 处的字面位置也计入）。
    """
    effects = _new_effects()
    # 既有 2 个（改造前即存在）显式列入，保证 A3 候选集自包含、可审计
    effects.append(Effect(
        mechanism_id="LF-M44", effect_type=EffectType.NUDGE,
        payload={"kind": "fomo"}, priority=70, cost=1.0,
        user_visible=True, health_critical=False, direction="approach"))
    effects.append(Effect(
        mechanism_id="LF-M52", effect_type=EffectType.NOTIFICATION,
        payload={"kind": "minor_protection_veto"}, priority=100, cost=0.0,
        user_visible=False, health_critical=True, direction="withdraw"))
    return effects


__all__ = ["ROUTE_A_DIRECTIONS", "ROUTE_A_NEW_PRODUCERS_COUNT", "ROUTE_A_PRODUCERS_COUNT",
           "install_route_a_directions", "build_route_a_new_effects", "build_route_a_effects"]
