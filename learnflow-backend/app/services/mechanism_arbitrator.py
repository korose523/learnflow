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
from typing import Callable, Dict, List, Optional, Tuple

from app.services.mechanism_registry import Effect, MechanismContext

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

    def __init__(
        self,
        policy: Optional[BudgetPolicy] = None,
        store: Optional[MemoryBudgetStore] = None,
        trace_sink: Optional[Callable[[ArbitrationTrace], None]] = None,
    ) -> None:
        self.policy = policy or BudgetPolicy()
        self.store = store
        self.trace_sink = trace_sink

    def arbitrate(self, ctx: MechanismContext, effects: List[Effect]) -> List[Effect]:
        """对一批候选 Effect 做三层漏斗仲裁, 返回最终下发的 Effect 列表。"""
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

        # ---------- 第 2 层: 冲突消解 ----------
        effects = self._resolve_conflicts(ctx, effects, trace)

        # ---------- 第 3 层: 干预预算 ----------
        effects = self._apply_budget(ctx, effects, trace)

        trace.delivered = [e.mechanism_id for e in effects]
        if self.trace_sink is not None:
            self.trace_sink(trace)
        ctx.trace.append(f"ARBITRATE delivered={trace.delivered}")
        return effects

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


__all__ = [
    "BudgetPolicy", "ArbitrationTrace", "MemoryBudgetStore",
    "MechanismArbitrator",
]
