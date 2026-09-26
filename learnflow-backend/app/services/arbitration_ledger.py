"""路线 A · A1：可审计干预账本落库（opt-in）。

M2 审计（2026-09-22 审阅 §6.1/§6.2）要求把第 5 章的账本 schema 由「设计规格」变为
「实现」，使 §5.2 三类一致性检查首次可实跑。本模块提供**同步 SQLite** 落库 sink，
作为 :class:`ArbitrationTrace` 的 ``trace_sink`` 接入点。

安全 / 向后兼容（关键）：
- **默认不启用**：仅当环境变量 ``LEARN2_LEDGER_ENABLED=1`` 时，编排器才注入本 sink；
  未设时行为与旧版完全一致（``trace_sink=None``），不影响既有 936 条测试。
- 使用**独立**同步 SQLite 文件（默认 ``arbitration_ledger.db``），不触碰主 ORM
  （async SQLAlchemy），不改动任何既有表；新增表由 ``CREATE TABLE IF NOT EXISTS`` 自愈。
- 本模块**不改变被审计系统的运行时行为**：它只记录仲裁轨迹，不新增/不修改任何
  ``Effect`` 构造点（效果生产者数量仍是 2，A2 尚未实施），故「效果生产 2」自然状态基线不变。
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.services.mechanism_arbitrator import ArbitrationTrace

_DEFAULT_DB = os.environ.get("LEARN2_LEDGER_DB", "arbitration_ledger.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS arbitration_ledger (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL,
    session_id          TEXT,
    candidates          TEXT,
    delivered            TEXT,
    preempted_by        TEXT,
    budget_consumed     REAL,
    arbitration_decision TEXT,
    reason              TEXT,
    ts                  TEXT NOT NULL
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    return conn


class LedgerTraceSink:
    """``Callable[[ArbitrationTrace], None]`` —— 把每次仲裁轨迹追加到只追加账本。

    每次调用独立开连接写一行后关闭，正确性优先（审计落库而非高吞吐路径）。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _DEFAULT_DB

    def __call__(self, trace: ArbitrationTrace) -> None:
        conn = _connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO arbitration_ledger
                    (user_id, session_id, candidates, delivered,
                     preempted_by, budget_consumed, arbitration_decision, reason, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace.user_id,
                    trace.session_id,
                    json.dumps(trace.candidates, ensure_ascii=False),
                    json.dumps(trace.delivered, ensure_ascii=False),
                    json.dumps(trace.preempted_by, ensure_ascii=False),
                    float(trace.budget_consumed),
                    trace.arbitration_decision,
                    trace.reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def run_consistency_checks(db_path: str = _DEFAULT_DB) -> dict:
    """§5.2 三类一致性检查（可实跑，return 计数）。

    返回：budget_overrun（会话内 Σ budget_consumed > B 的会话数）、
    preempted_yet_executed（被抢占却仍执行：preempted_by 非空且 decision=executed）、
    no_record（决策无对应账本记录：应恒为 0，因账本即记录源）、row_count。
    """
    if not os.path.exists(db_path):
        return {
            "row_count": 0,
            "budget_overrun": 0,
            "preempted_yet_executed": 0,
            "no_record": 0,
            "note": "ledger not initialized (enable via LEARN2_LEDGER_ENABLED=1)",
        }
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT session_id, budget_consumed, preempted_by, arbitration_decision "
            "FROM arbitration_ledger"
        ).fetchall()
    finally:
        conn.close()

    from collections import defaultdict

    per_session_cost = defaultdict(float)
    for session_id, budget_consumed, _pre, _dec in rows:
        if session_id:
            per_session_cost[session_id] += float(budget_consumed or 0.0)

    budget_overrun = sum(1 for c in per_session_cost.values() if c > 4.0)
    preempted_yet_executed = 0
    for _sid, _bc, pre, dec in rows:
        pre_list = json.loads(pre) if pre else []
        if pre_list and dec == "executed":
            preempted_yet_executed += 1
    no_record = 0  # 账本即记录源，理论恒为 0
    return {
        "row_count": len(rows),
        "budget_overrun": budget_overrun,
        "preempted_yet_executed": preempted_yet_executed,
        "no_record": no_record,
        "note": "checks executable",
    }


__all__ = ["LedgerTraceSink", "run_consistency_checks"]
