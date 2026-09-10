"""干预冲突仲裁器 —— 三层漏斗: 健康否决 → 冲突消解 → 干预预算

为什么需要这个模块
-----------------------------------------------------------------------------
LearnFlow 有 18 个干预生成点（15 处严格 nudge + 3 处学习提示, 见治理方案 §3.3.1）,
此前**完全没有仲裁**: ``FOMOEngine`` 生成「再学 20 分钟」的拉回文案, 与
``MinorProtectionEngine`` 的时长上限可以在同一次请求里同时下发——这是真实合规风险。

本模块把全部候选 ``Effect`` 收敛到单一决策入口, 用三层漏斗消解冲突:

    Layer 1  健康一票否决 (Health Veto)
            任一 health_critical Effect 命中 → 丢弃全部「拉回型」(approach) Effect,
            仅保留该健康 Effect (+ 不可见 Effect)
    Layer 2  冲突消解 (Conflict Resolution)
            按语义方向: 反方向对立时保留 withdraw (保守偏置, default to safety);
            同方向同 (effect_type, direction) 桶内保留优先级最高者
    Layer 3  干预预算 (Intervention Budget)
            按 priority 降序贪心装箱, 直到会话/日/加权成本上限; 健康类绕过预算

**保守偏置原则**: 反方向冲突时保留「推开」方。可证伪的伦理立场——过度劝退
（少学 10 分钟）的代价远小于过度劝学（未成年人超时）。这一条写进论文。

与机制注册表的关系
-----------------------------------------------------------------------------
``Effect.mechanism_id`` 必须是 ``mechanism_registry`` 中已登记的 LF-M ID; 语义方向
（approach/withdraw）由本模块的 ``_DIRECTION`` 表映射（也可由注册表 stage/category
推导, 此处显式登记以保证可审计）。健康类由 ``Effect.health_critical`` 标记。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from app.services.mechanism_registry import Effect, MechanismContext

if TYPE_CHECKING:  # 避免与 rl_arbitrator 的运行时循环导入
    from app.services.rl_arbitrator import RLArbitrator

logger = logging.getLogger(__name__)


@dataclass
class BudgetPolicy:
    """干预预算。默认值需预注册, 不得在实验中途调整。"""

    max_per_session: int = 3            # 每学习会话最多 3 次可见干预
    max_per_day: int = 6               # 每 24h 最多 6 次推送
    max_cost_per_session: float = 4.0  # 加权成本上限
    min_interval_sec: int = 300        # 同用户两次可见干预最小间隔 5 分钟
    burst_block_after: int = 2         # 连续 2 次被忽略后进入静默期
    silent_hours: Tuple[int, int] = (22, 7)  # 22:00-07:00 静默（仅健康类可穿透）


@dataclass
class ArbitrationTrace:
    """审计轨迹 —— 每次仲裁全量落库, 供实验分析复盘"""

    user_id: str
    session_id: Optional[str]
    candidates: List[str] = field(default_factory=list)
    vetoed_by_health: List[str] = field(default_factory=list)
    dropped_by_conflict: List[str] = field(default_factory=list)
    dropped_by_budget: List[str] = field(default_factory=list)
    dropped_by_risk: List[str] = field(default_factory=list)
    delivered: List[str] = field(default_factory=list)
    reason: str = ""


class MemoryBudgetStore:
    """内存版干预预算计数（默认实现, 测试与单进程可用）。

    生产环境应替换为 Redis 等带 TTL 的计数后端（接口一致: ``incr(scope, key,
    window_sec) -> 当前窗口内计数``）。``record_ignore`` 用于静默期判定。
    """

    def __init__(self) -> None:
        self._hits: Dict[Tuple[str, str], List[float]] = {}
        self._ignored: Dict[str, int] = {}

    def incr(self, scope: str, key: str, window_sec: int = 3600) -> int:
        now = time.time()
        bucket = self._hits.setdefault((scope, key), [])
        bucket.append(now)
        cutoff = now - window_sec
        self._hits[(scope, key)] = [t for t in bucket if t >= cutoff]
        return len(self._hits[(scope, key)])

    def record_ignore(self, user_id: str) -> int:
        self._ignored[user_id] = self._ignored.get(user_id, 0) + 1
        return self._ignored[user_id]

    def ignored_count(self, user_id: str) -> int:
        return self._ignored.get(user_id, 0)


class MechanismArbitrator:
    """三层漏斗干预仲裁器"""

    # 语义方向: approach=拉回加时 / withdraw=推开休息 / neutral
    _DIRECTION: Dict[str, str] = {
        "LF-M07": "approach", "LF-M08": "approach", "LF-M10": "approach",
        "LF-M13": "approach", "LF-M25": "approach", "LF-M26": "approach",
        "LF-M33": "approach", "LF-M35": "approach", "LF-M44": "approach",
        "LF-M51": "withdraw", "LF-M52": "withdraw", "LF-M53": "withdraw",
    }

    # 成瘾化风险权重表 (文献补位: 学习成瘾化研究补充文献测绘)
    #   key = mechanism_id (须为 approach 方向, 见 _DIRECTION)
    #   value = 成瘾化风险权重 (0-1): 越高表示该 nudge 越具成瘾化拉回倾向
    # 依据: LF-M44 FOMO(B4/A4) / LF-M33 Hook(B4) / LF-M08 稀缺性(dark pattern) /
    #       LF-M07 集换收藏(A8 可变奖励) / LF-M35 情境线索(B4 触发返回)
    _ADDICTION_RISK: Dict[str, float] = {
        "LF-M44": 0.9,
        "LF-M33": 0.7,
        "LF-M08": 0.5,
        "LF-M07": 0.4,
        "LF-M35": 0.4,
    }

    def __init__(
        self,
        policy: Optional[BudgetPolicy] = None,
        store: Optional[MemoryBudgetStore] = None,
        trace_sink: Optional[Callable[[ArbitrationTrace], None]] = None,
        rl_arbitrator: Optional["RLArbitrator"] = None,
    ) -> None:
        self.policy = policy or BudgetPolicy()
        self.store = store
        self.trace_sink = trace_sink
        self.rl_arbitrator = rl_arbitrator
        # 在线决策闭环反馈存储: (user_id, session_id) -> {risk_tier, chosen_id}
        #   精确绑定到「某次仲裁由 RL 选中的 approach 机制」, 供 report_lai_feedback 使用
        self._rl_pending: Dict[Tuple[str, Optional[str]], Dict[str, object]] = {}
        self._rl_last: Dict[str, Dict[str, object]] = {}

    def arbitrate(
        self,
        ctx: MechanismContext,
        effects: List[Effect],
        lai_risk: Optional[float] = None,
    ) -> List[Effect]:
        """对一批候选 Effect 做三层漏斗仲裁, 返回最终下发的 Effect 列表。

        Args:
            ctx: 仲裁上下文 (谁/哪个会话/审计轨迹)
            effects: 候选干预 Effect 列表
            lai_risk: 可选, LAI 成瘾风险 (0-1, 越高=成瘾风险越大)。提供时,
                在健康否决之后、冲突消解之前, 额外丢弃「高成瘾化且 approach 方向」
                的机制 (见 ``_ADDICTION_RISK``), 实现文献补位的「风险自适应降权」。
                默认 ``None`` → 行为与旧版完全一致 (向后兼容)。
        """
        trace = ArbitrationTrace(user_id=ctx.user_id, session_id=ctx.session_id)
        trace.candidates = [e.mechanism_id for e in effects]

        # ---------- 第 1 层: 健康一票否决 ----------
        health = [e for e in effects if e.health_critical]
        if health:
            health.sort(key=lambda e: -e.priority)
            winner = health[0]
            survivors = [
                e for e in effects
                if (e.health_critical and e is winner)
                or self._DIRECTION.get(e.mechanism_id) == "withdraw"
                or (not e.user_visible)
            ]
            trace.vetoed_by_health = [e.mechanism_id for e in effects if e not in survivors]
            effects = survivors
            trace.reason = f"health_veto:{winner.mechanism_id}"

        # ---------- 第 1.5 层: LAI 风险自适应降权 (可选) ----------
        if lai_risk is not None:
            dropped = [
                e for e in effects
                if self._DIRECTION.get(e.mechanism_id) == "approach"
                and self._ADDICTION_RISK.get(e.mechanism_id, 0.0) * lai_risk >= 0.4
            ]
            if dropped:
                effects = [e for e in effects if e not in dropped]
                trace.dropped_by_risk = [e.mechanism_id for e in dropped]
                trace.reason += f"|lai_risk_cool(drop={len(dropped)})"
                logger.info(
                    "LAI 风险自适应降权: 丢弃高成瘾化拉回 %s (lai_risk=%.2f)",
                    [e.mechanism_id for e in dropped], lai_risk,
                )

        # ---------- 第 1.7 层: RL 在线决策 (可选, 仅在已训练时生效) ----------
        # 已训练 -> 在当前风险档下, 从候选 approach 机制中由 bandit 选一个收益最高的,
        # 丢弃其余 approach 机制 (保留 withdraw/neutral 不受影响)。未训练 -> 完全跳过,
        # 行为与旧版一致 (向后兼容, 保守偏置兜底)。
        chosen_rl_id: Optional[str] = None
        risk_tier = self._risk_tier(lai_risk) if lai_risk is not None else 0
        if self.rl_arbitrator is not None and self.rl_arbitrator.ready(risk_tier):
            rl_id = self.rl_arbitrator.select_mechanism(ctx, effects, risk_tier)
            if rl_id is not None:
                chosen_rl_id = rl_id
                effects = [
                    e for e in effects
                    if self._DIRECTION.get(e.mechanism_id) != "approach"
                    or e.mechanism_id == rl_id
                ]
                trace.reason += f"|rl_select({rl_id})"
                logger.info("RL 仲裁器在风险档 t%d 选中 %s", risk_tier, rl_id)

        # ---------- 第 2 层: 冲突消解 ----------
        effects = self._resolve_conflicts(ctx, effects, trace)

        # ---------- 第 3 层: 干预预算 ----------
        effects = self._apply_budget(ctx, effects, trace)

        trace.delivered = [e.mechanism_id for e in effects]
        if self.trace_sink is not None:
            self.trace_sink(trace)
        ctx.trace.append(f"ARBITRATE delivered={trace.delivered}")

        # 记录 RL 反馈目标, 供后续 report_lai_feedback / report_reward 回灌奖励。
        #
        # 两种情况, 缺一不可:
        #   1) RL 已接管并选中某 approach 且确实下发 → 记录该机制 (真实 RL 决策目标);
        #   2) 冷启动: RL 尚未在该风险档学够, 本轮由规则层决策 → 记录规则层实际下发的
        #      approach 机制作为**影子目标** (shadow)。
        #
        # 情况 2 是**解除冷启动死锁的关键**。此前只记录情况 1, 而「RL 是否接管」又要求
        # Q 表非空 (trained), Q 却只能由 observe 写入 —— 于是永远不 observe、永远不训练,
        # 整条 AI 决策链路形同虚设。影子学习让冷启动阶段规则层的决策也能被观测,
        # Q 表由此起量, 达到 MIN_OBS_FOR_DECISION 后 RL 才接管决策。
        #
        # 伦理含义: 影子学习只是**观测**规则层的选择, 不干预、不改动本轮下发的任何机制,
        # 因此冷启动期的行为与未接线时完全一致 (保守偏置不变)。
        _feedback_id: Optional[str] = None
        _shadow = False
        if chosen_rl_id is not None and chosen_rl_id in trace.delivered:
            _feedback_id = chosen_rl_id
        elif self.rl_arbitrator is not None:
            # 冷启动影子: 取规则层本轮实际下发的第一个 approach 机制
            _feedback_id = next(
                (
                    mid for mid in trace.delivered
                    if self._DIRECTION.get(mid) == "approach"
                ),
                None,
            )
            _shadow = _feedback_id is not None

        if _feedback_id is not None:
            rec: Dict[str, object] = {
                "risk_tier": risk_tier,
                "chosen_id": _feedback_id,
                "shadow": _shadow,
            }
            self._rl_pending[(ctx.user_id, ctx.session_id)] = rec
            self._rl_last[ctx.user_id] = rec

        return effects

    @staticmethod
    def _risk_tier(lai_risk: float) -> int:
        """把 0-1 成瘾风险映射为 RL 上下文档位 (0-3), 与 TemporalRiskModel 对齐。

        阈值 (0.15/0.35/0.6) 与 :meth:`TemporalRiskModel.risk_tier` 一致, 使规则层
        与 RL 层共享同一风险离散化, 便于复现已训练的 bandit Q 表语义。
        """
        if lai_risk < 0.15:
            return 0
        if lai_risk < 0.35:
            return 1
        if lai_risk < 0.6:
            return 2
        return 3

    def report_lai_feedback(
        self,
        user_id: str,
        lai_before: float,
        lai_after: float,
        session_id: Optional[str] = None,
    ) -> Optional[float]:
        """在线决策闭环: 用 LAI 改善作奖励信号, 回灌给 RL 仲裁器做在线学习。

        奖励 = (lai_after − lai_before) / 100
            LAI 综合分 0-100 (越高越健康), 故 LAI 改善 (after > before) 为正收益,
            恶化则为负收益。奖励被记入此前该用户/会话由 RL 选中的 approach 机制对应的
            (风险档, 机制ID) 状态-动作对。

        安全性 / 向后兼容:
            * RL 仲裁器未注入 (``rl_arbitrator is None``) → 直接返回 ``None``,
              不改动任何状态, 规则仲裁行为完全不变;
            * 若该用户/会话此前没有反馈目标 → 返回 ``None`` (无反馈对象)。

        注意 (曾导致冷启动死锁): 这里**不再**要求 ``rl_arbitrator.trained()``。
        「是否让 RL 接管决策」由 arbitrate 第 1.7 层的 ``ready(risk_tier)`` 把关;
        「是否可以学习」没有门槛 —— 否则 Q 表永远为空, 训练永远无法开始。
        返回实际下发的奖励值 (无目标时返回 None)。
        """
        reward = (lai_after - lai_before) / 100.0
        fed = self.report_reward(user_id, reward, session_id=session_id)
        if fed is None:
            return None
        logger.info(
            "RL 反馈: user=%s mech=%s reward=%.4f (LAI %.1f->%.1f)",
            user_id, fed[1], reward, lai_before, lai_after,
        )
        return reward

    def report_reward(
        self,
        user_id: str,
        reward: float,
        session_id: Optional[str] = None,
    ) -> Optional[Tuple[int, str]]:
        """把一次已算好的奖励回灌给 RL 仲裁器 (通用反馈通道)。

        这是 RL 在线学习的**唯一入口**: :meth:`report_lai_feedback` 是本方法在
        「奖励 = LAI 改善」这一特定口径下的薄封装; 主学习流程里由
        ``intervention_reward.compute_reward`` 综合掌握度增益与健康风险下降后,
        直接调用本方法。避免两条通道各写一份回灌逻辑而产生漂移。

        反馈目标来自 :meth:`arbitrate` 登记的 ``_rl_pending`` / ``_rl_last``,
        可能是 RL 选中的机制, 也可能是冷启动期规则层下发机制的**影子目标**。

        返回 ``(risk_tier, chosen_id)`` 表示本次确实回灌; ``None`` 表示无反馈对象
        (RL 未注入 / 该用户本轮没有 approach 机制被下发), 调用方可据此跳过。
        """
        if self.rl_arbitrator is None:
            return None
        rec = self._rl_pending.pop((user_id, session_id), None)
        if rec is None:                       # 退而求其次: 该用户最近一次反馈目标
            rec = self._rl_last.get(user_id)
        if rec is None:
            return None
        chosen_id = str(rec["chosen_id"])
        risk_tier = int(rec["risk_tier"])  # type: ignore[arg-type]
        self.rl_arbitrator.observe(risk_tier, chosen_id, reward)
        logger.debug(
            "RL observe: user=%s tier=t%d mech=%s reward=%.4f shadow=%s",
            user_id, risk_tier, chosen_id, reward, rec.get("shadow", False),
        )
        return (risk_tier, chosen_id)

    def _resolve_conflicts(
        self, ctx: MechanismContext, effects: List[Effect], trace: ArbitrationTrace
    ) -> List[Effect]:
        visible = [e for e in effects if e.user_visible]
        invisible = [e for e in effects if not e.user_visible]

        directions = {
            d for d in (self._DIRECTION.get(e.mechanism_id) for e in visible) if d
        }
        # 若同时存在 approach 与 withdraw -> 保守偏置: 保留 withdraw, 丢弃 approach
        if "approach" in directions and "withdraw" in directions:
            dropped = [e for e in visible
                       if self._DIRECTION.get(e.mechanism_id) == "approach"]
            visible = [e for e in visible
                       if self._DIRECTION.get(e.mechanism_id) != "approach"]
            trace.dropped_by_conflict = [e.mechanism_id for e in dropped]
            trace.reason += f"|conflict_bias_withdraw(drop={len(dropped)})"
            logger.info("conflict resolved: dropped approach nudges %s",
                        [e.mechanism_id for e in dropped])

        # 同方向: 每个 (effect_type, direction) 桶内保留优先级最高者
        buckets: Dict[Tuple[str, str], Effect] = {}
        for e in sorted(visible, key=lambda x: -x.priority):
            key = (e.effect_type.value, self._DIRECTION.get(e.mechanism_id, "neutral"))
            if key in buckets:
                trace.dropped_by_conflict.append(e.mechanism_id)
            else:
                buckets[key] = e

        return list(buckets.values()) + invisible

    def _apply_budget(
        self, ctx: MechanismContext, effects: List[Effect], trace: ArbitrationTrace
    ) -> List[Effect]:
        p = self.policy
        delivered: List[Effect] = []
        cost = 0.0

        for e in sorted(effects, key=lambda x: (-x.priority, x.cost)):
            if e.health_critical:                 # 健康类绕过预算
                delivered.append(e)
                continue
            if not e.user_visible:                # 不可见不占预算
                delivered.append(e)
                continue

            if self.store is not None:
                n_session = self.store.incr("budget", f"{ctx.user_id}:session", window_sec=3600)
                n_day = self.store.incr("budget", f"{ctx.user_id}:day", window_sec=86400)
            else:
                n_session = len([d for d in delivered if d.user_visible])
                n_day = n_session
            if (len([d for d in delivered if d.user_visible]) >= p.max_per_session
                    or n_session > p.max_per_session
                    or n_day > p.max_per_day
                    or cost + e.cost > p.max_cost_per_session):
                trace.dropped_by_budget.append(e.mechanism_id)
                continue

            delivered.append(e)
            cost += e.cost

        return delivered


def lai_risk_from_overall(overall_score: float) -> float:
    """把 LAI 综合分 (0-100, 越高越健康) 转为成瘾风险 (0-1, 越高越危险)。

    供编排器/调用方在 LAI 评估后直接取 ``lai_risk`` 传入
    :meth:`MechanismArbitrator.arbitrate` 做风险自适应降权。
    """
    return max(0.0, min(1.0, 1.0 - overall_score / 100.0))


__all__ = [
    "BudgetPolicy", "ArbitrationTrace", "MemoryBudgetStore",
    "MechanismArbitrator", "lai_risk_from_overall",
]
