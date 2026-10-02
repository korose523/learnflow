"""路线 A · A2 候选生产者声明（opt-in，非生产生产者）。

═══════════════════════════════════════════════════════════════════════════
诚信更正（导师 2026-09-29 审阅意见 5.2）
═══════════════════════════════════════════════════════════════════════════
此前本文件把 12 个固定 ``Effect`` 字面展开，唯一目的是让 ``verify_counts`` 的
「效果生产者」AST 计数从 2 抬到 16——即审阅意见所指「为计数器写的代码」。该口径
不可辩护，已撤销。

现在的口径（与 verify_counts 一致）：
- 「效果生产者」审计口径（``verify_counts.effect_producers``）只统计运行时真正
  构造 ``Effect`` 的代码位置；**本模块被 ``verify_counts`` 显式排除**——它是
  opt-in 候选声明，不是生产引擎。审计时点（封存 tag ``audit-m2-20260911``）的
  真实生产者只有 2 处：``deep_addiction_engine.py`` / ``learning_orchestrator.py``
  （即 LF-M44 / LF-M52）。
- 本模块以**声明式候选集**描述路线 A 设想的 14 个机制（12 新增 + 2 既有），由
  单一工厂函数 ``_build_effect`` 在启用 ``LEARN2_A2_PRODUCERS=1`` 时实例化并注入
  仲裁器候选集。它不是「生产者数量」的来源，也**不计入**效果生产者 AST 审计。
- ``ROUTE_A_PRODUCERS_COUNT`` (=14) = 声明的 opt-in 机制数（含 2 既有）；
  ``ROUTE_A_NEW_PRODUCERS_COUNT`` (=12) = 12 个新增机制数。二者为「声明口径」，
  与「效果生产者 AST 审计口径 (=2)」明确区分，**不再靠形状凑数**。

向后兼容：默认关闭；仅 ``LEARN2_A2_PRODUCERS=1`` 时编排器才注入候选集，不影响
既有 936 测试。

路线 B 状态：路线 A 整体（A2/A3/A4）的产出在路线 B（见 M2 稿 §6.2 / 决策备忘）
下**不作为结果接受**。本模块仅作为「设想的候选集声明」保留，供未来「带真实机制
逻辑的生产者 + 登记盲编流程」时使用，先不宣称任何运行时结论。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.services.mechanism_arbitrator import MechanismArbitrator
from app.services.mechanism_registry import Effect, EffectType

# 路线 A 方向表：扩展仲裁器的 _DIRECTION，使新增候选参与冲突消解
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
# 声明口径：本模块声明的 opt-in 机制总数 = 12 新增 + 2 既有 = 14（A3 用）。
# 注意：这是「声明的候选机制数」，不是 verify_counts 的「效果生产者」AST 审计数（=2）。
ROUTE_A_PRODUCERS_COUNT = 14


def install_route_a_directions(arbitrator: MechanismArbitrator) -> None:
    """把路线 A 方向表并入仲裁器（仅 A2 启用时调用）。"""
    arbitrator._DIRECTION.update(ROUTE_A_DIRECTIONS)


# ─────────────────────────────────────────────────────────────────────────────
# 声明式候选集（纯数据，不在此处字面展开构造 Effect）
#
# 历史错误：此前把 12 个固定 Effect 字面展开，仅为了让 verify_counts 的
# 「效果生产者」AST 站点数从 2 抬到 16（审阅意见 5.2 认定其为「为计数器写的代码」）。
# 现在改为声明式数据 + 单一工厂，构造点只有 _build_effect 一处（工厂，非字面展开），
# 且整模块被 verify_counts 排除出「效果生产者」审计。
# ─────────────────────────────────────────────────────────────────────────────

# 12 个新增机制的候选规格（字段：mechanism_id / effect_type / payload / priority /
# cost / direction / user_visible / health_critical）。
_ROUTE_A_NEW_SPECS: List[Dict[str, object]] = [
    {"mechanism_id": "LF-M01", "effect_type": EffectType.REWARD,
     "payload": {"kind": "variable_ratio_reward"}, "priority": 55, "cost": 1.0,
     "direction": "approach"},
    {"mechanism_id": "LF-M04", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "instant_gratification"}, "priority": 60, "cost": 0.8,
     "direction": "approach"},
    {"mechanism_id": "LF-M05", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "surprise_delight"}, "priority": 50, "cost": 0.6,
     "direction": "approach"},
    {"mechanism_id": "LF-M06", "effect_type": EffectType.REWARD,
     "payload": {"kind": "time_based_bonus"}, "priority": 52, "cost": 0.7,
     "direction": "approach"},
    {"mechanism_id": "LF-M07", "effect_type": EffectType.BADGE,
     "payload": {"kind": "collection"}, "priority": 48, "cost": 0.9,
     "direction": "approach"},
    {"mechanism_id": "LF-M08", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "scarcity"}, "priority": 65, "cost": 1.1,
     "direction": "approach"},
    {"mechanism_id": "LF-M12", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "streak_sanctification"}, "priority": 58, "cost": 0.8,
     "direction": "approach"},
    {"mechanism_id": "LF-M13", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "zeigarnik"}, "priority": 54, "cost": 0.7,
     "direction": "approach"},
    {"mechanism_id": "LF-M15", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "goal_gradient"}, "priority": 56, "cost": 0.8,
     "direction": "approach"},
    {"mechanism_id": "LF-M16", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "daily_challenge"}, "priority": 53, "cost": 0.7,
     "direction": "approach"},
    {"mechanism_id": "LF-M51", "effect_type": EffectType.NOTIFICATION,
     "payload": {"kind": "withdraw_nudge"}, "priority": 80, "cost": 0.0,
     "direction": "withdraw"},
    {"mechanism_id": "LF-M53", "effect_type": EffectType.NOTIFICATION,
     "payload": {"kind": "withdraw_nudge"}, "priority": 85, "cost": 0.0,
     "direction": "withdraw"},
]

# 2 个既有生产者的规格：仅用于 A3 自包含候选集的描述。它们真正的生产位置在各自
# 引擎（deep_addiction_engine.py / learning_orchestrator.py），那里才是
# verify_counts 计入的「效果生产者」AST 站点。
_ROUTE_A_EXISTING_SPECS: List[Dict[str, object]] = [
    {"mechanism_id": "LF-M44", "effect_type": EffectType.NUDGE,
     "payload": {"kind": "fomo"}, "priority": 70, "cost": 1.0,
     "direction": "approach"},
    {"mechanism_id": "LF-M52", "effect_type": EffectType.NOTIFICATION,
     "payload": {"kind": "minor_protection_veto"}, "priority": 100, "cost": 0.0,
     "direction": "withdraw", "user_visible": False, "health_critical": True},
]


def _build_effect(spec: Dict[str, object]) -> Effect:
    """单一工厂：把一条声明式规格实例化为 ``Effect``。

    本函数只有**一处**字面 ``Effect(`` 构造点——这是工厂，不是为计数而字面展开。
    整模块已被 ``verify_counts.count_effect_producers`` 排除出「效果生产者」审计。
    """
    return Effect(
        mechanism_id=str(spec["mechanism_id"]),
        effect_type=spec["effect_type"],  # type: ignore[arg-type]
        payload=dict(spec.get("payload", {}) or {}),  # type: ignore[arg-type]
        priority=float(spec["priority"]),  # type: ignore[arg-type]
        cost=float(spec.get("cost", 0.0)),  # type: ignore[arg-type]
        user_visible=bool(spec.get("user_visible", True)),
        health_critical=bool(spec.get("health_critical", False)),
        direction=str(spec["direction"]),
    )


def build_route_a_new_effects(user_id: str, session_id: Optional[str]) -> List[Effect]:
    """仅路线 A **新增**的 12 个候选（供编排器 opt-in 注入）。

    不含既有 LF-M44/LF-M52（它们由各自引擎/编排器在 FOMO 路径中产出），避免
    运行时候选集出现重复机制。
    """
    return [_build_effect(s) for s in _ROUTE_A_NEW_SPECS]


def build_route_a_effects(user_id: str, session_id: Optional[str]) -> List[Effect]:
    """A3 自包含候选集：12 新增 + 2 既有 = 14 个不同机制候选。

    返回列表即「改造后」的候选干预集合描述；由 A3 直接驱动真实仲裁器统一仲裁。
    注意：这些候选是声明式规格经工厂实例化而来，并非运行时真实机制引擎的产物——
    本模块不参与 verify_counts 的「效果生产者」AST 审计。
    """
    return [_build_effect(s) for s in (*_ROUTE_A_NEW_SPECS, *_ROUTE_A_EXISTING_SPECS)]


__all__ = ["ROUTE_A_DIRECTIONS", "ROUTE_A_NEW_PRODUCERS_COUNT", "ROUTE_A_PRODUCERS_COUNT",
           "install_route_a_directions", "build_route_a_new_effects", "build_route_a_effects"]
