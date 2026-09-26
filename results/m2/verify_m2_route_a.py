"""路线 A · A2/A3 验证门禁：效果生产者 ≥14 + 合成会话分布已产出。

- A2 结构层（必须 PASS，否则 exit 1）：
  * ``route_a_producers.ROUTE_A_PRODUCERS_COUNT >= 14`` 且 ``ROUTE_A_NEW_PRODUCERS_COUNT == 12``；
  * ``route_a_producers.py`` 字面 ``Effect(`` 构造点 ≥ 14（与 verify_counts 审计口径一致）；
  * ``LEARN2_A2_PRODUCERS`` opt-in 注入点存在于编排器源码（不启用不影响 936 测试）。
- A3 运行时层（必须 PASS）：
  * ``a3_synthetic_sessions.json`` 存在，且含 route_a / legacy 两模式；
  * route_a 冲突频率 > 0、legacy 冲突频率 == 0（证明"改造前不可发生 → 改造后可量化"）；
  * 两模式 preempt_violation_rate == 0（安全不变量成立）。

用法：backend venv 下 ``python results/m2/verify_m2_route_a.py``（PYTHONPATH 含 learnflow-backend）。
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.normpath(os.path.join(HERE, "..", "..", "learnflow-backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services import route_a_producers  # noqa: E402


def _structural_checks() -> list:
    problems: list = []
    if route_a_producers.ROUTE_A_PRODUCERS_COUNT < 14:
        problems.append(
            f"ROUTE_A_PRODUCERS_COUNT={route_a_producers.ROUTE_A_PRODUCERS_COUNT} < 14")
    if route_a_producers.ROUTE_A_NEW_PRODUCERS_COUNT != 12:
        problems.append(
            f"ROUTE_A_NEW_PRODUCERS_COUNT={route_a_producers.ROUTE_A_NEW_PRODUCERS_COUNT} != 12")
    # 字面 Effect( 构造点数（审计口径：不同代码位置）
    src = open(os.path.join(BACKEND, "app", "services", "route_a_producers.py"),
               encoding="utf-8").read()
    n_effect = len(re.findall(r"\bEffect\(", src))
    if n_effect < 14:
        problems.append(f"route_a_producers.py 字面 Effect( 构造点={n_effect} < 14")
    # 编排器 opt-in 注入点
    orch = open(os.path.join(BACKEND, "app", "services", "learning_orchestrator.py"),
                encoding="utf-8").read()
    if "LEARN2_A2_PRODUCERS" not in orch or "build_route_a_new_effects" not in orch:
        problems.append("learning_orchestrator.py 未接入 route_a 生产者（opt-in）")
    return problems


def _runtime_checks() -> list:
    problems: list = []
    jpath = os.path.join(HERE, "a3_synthetic_sessions.json")
    if not os.path.isfile(jpath):
        return [f"a3_synthetic_sessions.json 不存在：{jpath}（请先运行 a3_synthetic_sessions.py）"]
    data = json.loads(open(jpath, encoding="utf-8").read())
    route_a = data.get("route_a") or {}
    legacy = data.get("legacy") or {}
    if not route_a or not legacy:
        return ["a3 JSON 缺少 route_a / legacy 双模式"]
    if not (route_a.get("conflict_frequency", 0) > 0):
        problems.append(f"route_a 冲突频率未 > 0：{route_a.get('conflict_frequency')}")
    if legacy.get("conflict_frequency", -1) != 0:
        problems.append(f"legacy 冲突频率应 == 0：{legacy.get('conflict_frequency')}")
    if route_a.get("preempt_violation_rate", 1) != 0:
        problems.append(f"route_a 抢占违规率应 == 0：{route_a.get('preempt_violation_rate')}")
    if legacy.get("preempt_violation_rate", 1) != 0:
        problems.append(f"legacy 抢占违规率应 == 0：{legacy.get('preempt_violation_rate')}")
    return problems


def main() -> int:
    problems = _structural_checks()
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1
    print("A2 结构层: PASS"
          f"（ROUTE_A_PRODUCERS_COUNT={route_a_producers.ROUTE_A_PRODUCERS_COUNT}, "
          f"NEW={route_a_producers.ROUTE_A_NEW_PRODUCERS_COUNT}, "
          f"opt-in 注入点 OK）")

    rproblems = _runtime_checks()
    if rproblems:
        for p in rproblems:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1
    print("A3 运行时层: PASS（a3_synthetic_sessions.json 双模式分布已产出）")
    print("结论: PASS   退出码 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
