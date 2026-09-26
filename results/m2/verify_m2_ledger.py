"""路线 A · A1 验证门禁：可审计干预账本已落地（结构 + 运行时可实跑）。

- 结构层（必须 PASS，否则 exit 1）：
  * ``ArbitrationTrace`` 含账本字段 budget_consumed / preempted_by / arbitration_decision；
  * ``app.services.arbitration_ledger`` 可导入，且导出 LedgerTraceSink 与 run_consistency_checks；
  * 编排器在 LEARN2_LEDGER_ENABLED=1 时把 LedgerTraceSink 接入仲裁器（源码字面量校验）。
- 运行时层（信息性，不阻断）：若账本 DB 存在则跑 §5.2 三类一致性检查并报告计数；
  当前无运行时日志时 row_count=0，属预期状态。
  【2026-09-25 更正】此处原文写作「A3 待实施」，与仓库现状不符，已更正：A2（效果生产者
  ≥14，opt-in）与 A3（合成会话分布 `a3_synthetic_sessions.json`）**均已实现并通过
  `verify_m2_route_a.py` 门禁**；本账本仍为 0 行的真实原因是**没有真实运行时日志写入
  DB**（A3 产出的是合成分布，不是真实用户会话），并非 A2/A3 未实施。

用法：backend venv 下 ``python results/m2/verify_m2_ledger.py``（PYTHONPATH 含 learnflow-backend）。
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.normpath(os.path.join(HERE, "..", "..", "learnflow-backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services.mechanism_arbitrator import ArbitrationTrace  # noqa: E402
from app.services import arbitration_ledger  # noqa: E402


def _structural_checks() -> list:
    problems: list = []
    trace_fields = set(getattr(ArbitrationTrace, "__dataclass_fields__", {}))
    for f in ("budget_consumed", "preempted_by", "arbitration_decision"):
        if f not in trace_fields:
            problems.append(f"ArbitrationTrace 缺少字段 {f}")
    if not hasattr(arbitration_ledger, "LedgerTraceSink"):
        problems.append("arbitration_ledger 未导出 LedgerTraceSink")
    if not hasattr(arbitration_ledger, "run_consistency_checks"):
        problems.append("arbitration_ledger 未导出 run_consistency_checks")
    # 源码字面量校验：编排器在启用开关时接入 LedgerTraceSink
    orch = os.path.join(BACKEND, "app", "services", "learning_orchestrator.py")
    src = open(orch, encoding="utf-8").read()
    if "LEARN2_LEDGER_ENABLED" not in src or "LedgerTraceSink()" not in src:
        problems.append("learning_orchestrator.py 未接入 LedgerTraceSink（opt-in）")
    return problems


def main() -> int:
    problems = _structural_checks()
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1

    db = os.environ.get("LEARN2_LEDGER_DB", "arbitration_ledger.db")
    res = arbitration_ledger.run_consistency_checks(db)
    print("A1 结构层: PASS（ArbitrationTrace 账本字段 + LedgerTraceSink 接入）")
    print(
        "运行时一致性检查: "
        f"row_count={res['row_count']} budget_overrun={res['budget_overrun']} "
        f"preempted_yet_executed={res['preempted_yet_executed']} "
        f"no_record={res['no_record']} ({res['note']})"
    )
    if res["row_count"] == 0:
        print("说明: 当前无运行时日志（A2/A3 均已实现并通过 verify_m2_route_a 门禁；"
              "账本为 0 行的真实原因是尚无真实运行时日志写入 DB，A3 产出的是合成会话分布），"
              "账本为空属预期；三类检查已可执行。")
    print("结论: PASS   退出码 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
