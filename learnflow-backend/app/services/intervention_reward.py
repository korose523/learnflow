"""干预奖励函数 —— AI 行为管控链路的在线学习信号 (K12 学习平台 / 博士论文)。

本模块只做一件事: 把「一次干预前后的观测」折算成一个标量奖励,
供 ``RLArbitrator`` (contextual bandit) 在线学习「当前状态下下发哪个机制收益最高」。

═══════════════════════════════════════════════════════════════════════
★★★ 伦理约束 (务必先读): 本项目面向 K12 未成年人, 且是博士论文, 会被审稿人
    以伦理视角审查。本奖励函数定义的是**正向成瘾 (positive addiction)** 的优化目标:
    把游戏化机制激发的动机, 迁移到**学习行为本身**上, 提升学习投入与自我调节能力。

    ❌ 禁止包含任何「让人对 App 上瘾」的指标:
        - 使用时长 / 停留时间
        - 活跃天数 / 登录频次
        - 答题数量 / 刷题量
        - 连胜长度 / 连续登录天数
        - 任何形式的「用户粘性 / 留存 / DAU」指标
    理由 (这是伦理约束, 不是技术偏好): 一旦把这些放进奖励函数, RL 会立刻学到
    「延长用户使用时间 = 高收益」, 那是在训练一台成瘾机器 —— 本项目最大的失败模式。
    评判标准只有一条: 这个设计是在帮用户**学得更好**, 还是在让用户**用得更久**?
    上述所有指标都属于后者, 一律禁止进入奖励。

✅ 奖励函数只许依赖「学习成效」与「健康风险」:
        - 学习成效增益: BKT 掌握度 ``mastery`` 的提升 (越高越好)
        - 健康风险下降: 成瘾风险 ``risk`` / LAI 的下降 (越低越好)
    若本次交互触发了未成年保护阻断、或风险等级上升, 奖励必须是明确的负值
    (``blocked_by_protection=True`` 时直接 -1.0), 让 bandit 学到这类 arm 有害。

    已有护栏 (``mechanism_arbitrator.BudgetPolicy``) 是防「过度打扰」的, 与本奖励正交,
    本模块不改动它们。
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ── 奖励权重 (模块级常量, 可调; 供论文方法与审计脚本引用) ──
# 学习成效增益权重: 掌握度提升是首要优化目标。
W_MASTERY: float = 0.6
# 健康风险下降权重: 成瘾风险下降是次要但不可缺的优化目标。
W_HEALTH: float = 0.4

# 奖励裁剪区间: 任何信号组合都不得溢出 [-1, 1]。
CLIP_MIN: float = -1.0
CLIP_MAX: float = 1.0

# 未成年保护阻断的硬惩罚 (优先于一切)。
BLOCKED_PENALTY: float = -1.0


@dataclass
class InterventionSignals:
    """一次干预前后的观测信号。

    注意: 本结构**刻意不包含**任何时长 / 活跃度 / 答题量 / 连胜类字段。
    这些指标属于「让人对 App 上瘾」的代理, 禁止进入奖励 (见模块 docstring)。
    若某项 before/after 取不到, 传 ``None`` —— 对应项按 0 计, 绝不瞎猜数值。
    """

    mastery_before: Optional[float] = None   # BKT 掌握度 0..1 (干预前)
    mastery_after: Optional[float] = None    # BKT 掌握度 0..1 (干预后)
    risk_before: Optional[float] = None      # 成瘾风险 0..1 (越高越差, 干预前)
    risk_after: Optional[float] = None       # 成瘾风险 0..1 (越高越差, 干预后)
    blocked_by_protection: bool = False      # 是否触发未成年保护阻断 (硬约束)
    answered: bool = True                    # 用户是否有真实作答行为 (信号有效性标记)


def compute_reward(s: InterventionSignals) -> float:
    """把一次干预前后信号折算为标量奖励。

    规则 (优先级从高到低)::

        1. blocked_by_protection=True → 直接返回 -1.0 (硬约束, 优先于一切)。
        2. 主项 = w_m * Δmastery + w_h * (-Δrisk)
             Δmastery = mastery_after - mastery_before   (掌握度提升为正)
             Δrisk    = risk_after  - risk_before        (风险上升则此项为负)
           权重 w_m=0.6, w_h=0.4 (见模块常量, 可调)。
        3. 任一 before/after 为 None → 该项按 0 计 (不瞎猜)。
        4. 最终用 max(-1.0, min(1.0, reward)) 裁剪到 [-1, 1]。

    设计要点:
        * 奖励只依赖「学习成效」与「健康风险」(正向成瘾的合法目标),
          不含任何时长 / 活跃度 / 答题量 / 连胜指标 (伦理红线)。
        * ``answered=False`` 表示没有真实作答行为, 此时不应据此发放正奖励;
          本函数将其视为「掌握度信号缺失」(mastery 项按 0 计), 避免对空信号过度奖励。
    """
    # 硬约束: 未成年保护阻断 → 明确负惩罚, 优先于一切。
    if s.blocked_by_protection:
        return BLOCKED_PENALTY

    # 学习成效增益: 掌握度提升为正。信号缺失 (before/after 任一为 None) 按 0 计。
    if s.mastery_before is None or s.mastery_after is None or not s.answered:
        mastery_term = 0.0
    else:
        delta_mastery = s.mastery_after - s.mastery_before
        mastery_term = W_MASTERY * delta_mastery

    # 健康风险下降: 风险上升 (Δrisk>0) 则该项为负。信号缺失按 0 计。
    if s.risk_before is None or s.risk_after is None:
        health_term = 0.0
    else:
        delta_risk = s.risk_after - s.risk_before
        health_term = W_HEALTH * (-delta_risk)

    reward = mastery_term + health_term
    return max(CLIP_MIN, min(CLIP_MAX, reward))


def describe_reward_weights() -> dict:
    """返回当前奖励权重与裁剪区间, 供论文方法章节与审计脚本引用。

    审核人可用本字典证明: 优化目标里没有任何时长 / 活跃度 / 答题量 / 连胜类指标,
    只有 ``mastery`` (学习成效) 与 ``risk`` (健康风险) 两项。
    """
    return {
        "w_mastery": W_MASTERY,
        "w_health": W_HEALTH,
        "clip_min": CLIP_MIN,
        "clip_max": CLIP_MAX,
        "blocked_penalty": BLOCKED_PENALTY,
        # 显式声明被禁止进入奖励的特征, 便于审计脚本断言。
        "forbidden_features": [
            "usage_duration", "stay_time", "active_days", "login_frequency",
            "answer_count", "drill_volume", "streak_length", "consecutive_days",
            "retention", "engagement", "stickiness",
        ],
        "allowed_features": ["mastery_gain", "risk_drop"],
    }


__all__ = [
    "InterventionSignals",
    "compute_reward",
    "describe_reward_weights",
    "W_MASTERY",
    "W_HEALTH",
    "CLIP_MIN",
    "CLIP_MAX",
    "BLOCKED_PENALTY",
]
