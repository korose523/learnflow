"""路线 A · A3：合成会话通过编排器，产出运行时分布（实证强化核心增量）。

M2 审计（2026-09-22）的核心批评："类型 II 运行时竞争 = 0" 与 "冲突稀少 vs 不可发生"
不可区分，因为效果生产者仅 2 处。A3 用路线 A 的 ≥14 生产者集合驱动**真实**
``MechanismArbitrator``，跑合成会话，产出三个分布：
  - 运行时冲突频率（出现 approach×withdraw 同场、被冲突消解层丢弃的步占比）
  - 竞争率（补充指标：被健康否决或冲突消解丢弃的步占比，直接回答"竞争是否发生"）
  - 预算耗竭率（会话内因干预预算上限而至少丢弃 1 个可见干预的会话占比）
  - 抢占违规率（preempted_by 非空却仍下发的步占比，预期 ≈0，为安全不变量校验）

并额外跑 **legacy 基线**（仅 2 既有生产者）作对照：按设计 legacy 下冲突频率 ≈0
（LF-M52 为健康一票否决方，触发 Layer-1 而非 Layer-2 冲突），从而干净地呈现
"2 → 14 生产者"使运行时冲突由"不可能"变为"可观测、可量化"。

方法论修正（相对初版）：
- **每会话重置 MemoryBudgetStore**：初版共享 store 按 "synthetic" 用户累计、永不重置，
  预算指标失真。现每会话新建 store，符合 BudgetPolicy 的"per-session"语义。
- **随机激活、不强制 withdraw**：初版强制每步 withdraw 存在 → 冲突频率被钉在 ~100%。
  现按参与度 engagement 独立随机激活各生产者，approach×withdraw 同场自然发生，
  冲突频率为真实可解释的率值（非退化 100%）。
- **抢占违规判定修正**：初版把"正常丢弃一些、下发另一些"误判为违规。正确不变量是
  ``preempted_by ∩ delivered == ∅``（被抢占的机制绝不出现于下发集），预期 0。
- **预算耗竭率定义修正**：初版阈值 ``> 4.0`` 因预算检查阻止超额而恒为 0。现定义为
  "会话内至少一步发生 dropped_by_budget 的会话占比"，反映多机制并存时用户预算被打满的频率。

设计：
- 不修改生产代码：直接构造 MechanismArbitrator + MemoryBudgetStore + 内存 trace sink，
  用 route_a_producers.build_route_a_effects 提供候选，调用真实 arbitrate。
- 结果写 results/m2/a3_synthetic_sessions.json，并打印分布摘要与 before/after 对比。

用法（backend venv）：
  python results/m2/a3_synthetic_sessions.py                # 默认 2000 会话 × 40 步（两模式）
  N_SESSIONS=10000 STEPS=40 python results/m2/a3_synthetic_sessions.py
  LEGACY_ONLY=1 python results/m2/a3_synthetic_sessions.py  # 仅跑 legacy 基线
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.normpath(os.path.join(HERE, "..", "..", "learnflow-backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services.mechanism_arbitrator import (  # noqa: E402
    ArbitrationTrace, MechanismArbitrator, MemoryBudgetStore,
)
from app.services.mechanism_registry import Effect, EffectType, MechanismContext  # noqa: E402
from app.services.route_a_producers import (  # noqa: E402
    ROUTE_A_DIRECTIONS, ROUTE_A_PRODUCERS_COUNT, build_route_a_effects,
    install_route_a_directions,
)


def _legacy_effects() -> list:
    """仅 2 个既有生产者（改造前基线）：LF-M44(approach) + LF-M52(withdraw, 健康)。

    复用 route_a_producers.build_route_a_effects 并过滤，避免本脚本另写字面 Effect(
    （本脚本在 results/ 下，不参与 verify_counts 的 app/ 扫描，但保持单一真源更清晰）。
    """
    full = build_route_a_effects("synthetic", None)
    return [e for e in full if e.mechanism_id in ("LF-M44", "LF-M52")]


def _active_subset(rng: random.Random, engagement: float, legacy_mode: bool) -> list:
    """按参与度随机激活子集（不强制任何方向，使冲突自然发生）。

    engagement∈[0,1] 越高，激活生产者越多（模拟"高投入学习者被更多机制包围"）。
    每个生产者独立以 p_act 概率激活；approach 与 withdraw 同场与否完全由随机性决定，
    从而冲突频率为真实可解释的率值。
    """
    base = _legacy_effects() if legacy_mode else build_route_a_effects("synthetic", None)
    p_act = 0.25 + 0.55 * engagement
    return [e for e in base if rng.random() < p_act]


def run(n_sessions: int, steps: int, seed: int = 20260922, legacy_mode: bool = False) -> dict:
    rng = random.Random(seed)
    arb = MechanismArbitrator(policy=None, store=MemoryBudgetStore())
    if not legacy_mode:
        install_route_a_directions(arb)  # legacy 模式用仲裁器默认 _DIRECTION 即可

    traces: list = []

    def _sink(t: ArbitrationTrace) -> None:
        traces.append(t)

    arb.trace_sink = _sink

    conflict_steps = 0
    competition_steps = 0
    preempt_violation_steps = 0
    total_steps = 0
    delivered_per_step: list = []
    sessions_with_budget_drop = 0

    for s in range(n_sessions):
        session_id = f"sess-{s:06d}"
        # 每会话重置预算：MemoryBudgetStore 按 (user, session/day) 窗口计数，
        # 新实例使每会话从 0 开始，符合 BudgetPolicy 的 per-session 语义。
        arb.store = MemoryBudgetStore()
        engagement = rng.random()
        lai_risk = rng.random()
        had_budget_drop = False
        for _ in range(steps):
            total_steps += 1
            effects = _active_subset(rng, engagement, legacy_mode)
            if not effects:
                delivered_per_step.append(0)
                continue
            ctx = MechanismContext(user_id="synthetic", session_id=session_id)
            delivered = arb.arbitrate(ctx, effects, lai_risk=lai_risk)
            t = traces[-1]
            if t.dropped_by_conflict:
                conflict_steps += 1
            if t.dropped_by_conflict or t.vetoed_by_health:
                competition_steps += 1
            # 安全不变量：被抢占（冲突/预算丢弃）的机制绝不出现于下发集
            if set(t.preempted_by) & set(t.delivered):
                preempt_violation_steps += 1
            if t.dropped_by_budget:
                had_budget_drop = True
            delivered_per_step.append(len(delivered))
        if had_budget_drop:
            sessions_with_budget_drop += 1

    return {
        "mode": "legacy_2_producers" if legacy_mode else "route_a_14_producers",
        "n_sessions": n_sessions,
        "steps": steps,
        "total_steps": total_steps,
        "producers_route_a": ROUTE_A_PRODUCERS_COUNT,
        "producers_active": 2 if legacy_mode else 14,
        "conflict_frequency": conflict_steps / max(1, total_steps),
        "competition_rate": competition_steps / max(1, total_steps),
        "budget_exhaustion_rate": sessions_with_budget_drop / max(1, n_sessions),
        "preempt_violation_rate": preempt_violation_steps / max(1, total_steps),
        "mean_delivered_per_step": sum(delivered_per_step) / max(1, len(delivered_per_step)),
        "note": ("改造前（2 生产者）基线" if legacy_mode
                 else "改造后（≥14 生产者）运行时分布；对比封存时点（2 生产者）冲突频率≈0"),
    }


def main() -> int:
    n = int(os.environ.get("N_SESSIONS", "2000"))
    steps = int(os.environ.get("STEPS", "40"))

    if os.environ.get("LEGACY_ONLY") == "1":
        res = run(n, steps, legacy_mode=True)
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "legacy": res}
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        route_a = run(n, steps, legacy_mode=False)
        legacy = run(n, steps, legacy_mode=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "route_a": route_a,
            "legacy": legacy,
            "delta_conflict_frequency": route_a["conflict_frequency"]
            - legacy["conflict_frequency"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    out = os.path.join(HERE, "a3_synthetic_sessions.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n结果已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
