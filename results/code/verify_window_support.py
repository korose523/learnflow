#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_window_support.py —— assist09 滑窗错误率「离散支撑点」回归门禁
=============================================================================

为什么需要这个脚本（审阅意见 3.1）
-----------------------------------------------------------------------------
M1 8.1 节 / 报告 3.7 节 / 计划书 RQ2 判定规则都依赖一句话：
「assist09 滑窗错误率的众数区间为 0.15~0.20（成功率 80~85%）」。

这句话在旧实现下是**分箱边界伪影**：窗宽 W = 20，错误率只取 k/20 这 21 个离散值，
而直方图用的是 np.histogram(win_err, bins=np.arange(0, 1.0001, 0.05))——区间边界与
离散值恰好重合，浮点误差把 0.15 与 0.20 并进同一区间、把 0.10 挤到下一区间。于是
「众数区间 = 两个离散值之和」被当成分布事实，而单值频数从未被报告过。

修复后口径：按整数错误条数 k 直接计数（整数运算、无浮点），报告 21 个支撑点频数。

本脚本把修复后的事实钉死，任何人把分箱改回去、或改了滑窗口径忘了同步 JSON，
都会被这里拦下。

用法
-----------------------------------------------------------------------------
    python results/code/verify_window_support.py          # 打印报告
    python results/code/verify_window_support.py --quiet  # 只打印一行结论

退出码
-----------------------------------------------------------------------------
    0  支撑点口径与已登记事实一致
    1  不一致（口径漂移 / 旧字段回流）
    2  脚本执行失败（JSON 缺失或结构不符）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parent.parent.parent      # E:\learnflow
CODE = BASE / "results" / "code"
REAL = CODE / "real_data_results.json"
OPT = CODE / "optimized_results.json"

#: 已登记事实（修复后实测值）。改动这些值必须同时改 M1 8.1 / 报告 3.7 / 计划书 RQ2。
REGISTERED: Dict[str, Any] = {
    "window": 20,
    "n_windows": 286150,
    "n_users_input": 4217,        # 输入中出现的全部用户数
    "n_users_used": 2314,         # 实际贡献滑窗的用户数（≥20 条作答）——旧实现误写 4217
    "modal_k_errors": [5],        # 单值众数 k=5 → 错误率 0.25 / 成功率 0.75
    "bootstrap_modal_ci95_k": [5],
    "by_filter_mode": {           # 三种过滤口径的单值众数（旧主张称三者都是 0.15~0.20）
        "all": [5],
        "original_only(main_problem)": [4],
        "no_hint_correction": [3],
    },
    "tutor_mode_test_windows": 0,  # 该口径窗数为 0，不构成独立证据
}

#: 旧实现遗留字段：出现即视为分箱伪影回流
FORBIDDEN_KEYS = ("hist_05bins", "modal_bin_center")


class GateError(RuntimeError):
    pass


def _load(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise GateError(f"产物缺失：{path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check() -> List[Dict[str, Any]]:
    real = _load(REAL)["assist09_window"]
    opt = _load(OPT)["o1_window_sensitivity"]
    rows: List[Dict[str, Any]] = []

    def add(item: str, ok: bool, detail: str) -> None:
        rows.append({"item": item, "ok": ok, "detail": detail})

    for key in ("window", "n_windows", "n_users_input", "n_users_used",
                "modal_k_errors", "bootstrap_modal_ci95_k"):
        want = REGISTERED[key]
        got = real.get(key)
        add(f"real_data_results.assist09_window.{key}", got == want, f"实测={got} 期望={want}")

    for key in FORBIDDEN_KEYS:
        add(f"旧字段已移除: {key}", key not in real, f"仍存在于 real_data_results.json")

    table = real.get("k_frequency_table") or []
    add("k_frequency_table 存在 21 个支撑点", len(table) == 21, f"实测 {len(table)} 条")
    if len(table) == 21:
        add("支撑点精确为 k/20",
            all(abs(r["error_rate"] - r["k_errors"] / 20) < 1e-9 for r in table),
            "存在非 k/20 的支撑点")
        add("频数之和 == n_windows",
            sum(r["n_windows"] for r in table) == real["n_windows"],
            f"合计 {sum(r['n_windows'] for r in table)} vs {real['n_windows']}")
        top = max(r["n_windows"] for r in table)
        modes = [r["k_errors"] for r in table if r["n_windows"] == top]
        add("单值众数 k=5（错误率 0.25）", modes == REGISTERED["modal_k_errors"],
            f"实测众数支撑点={modes}")

    for name, want in REGISTERED["by_filter_mode"].items():
        got = (opt.get(name) or {}).get("modal_k")
        add(f"o1_window_sensitivity[{name}].modal_k", got == want, f"实测={got} 期望={want}")
    add("tutor_mode_test 窗数为 0",
        (opt.get("tutor_mode_test") or {}).get("n_windows") == REGISTERED["tutor_mode_test_windows"],
        f"实测={(opt.get('tutor_mode_test') or {}).get('n_windows')}")

    # 旧主张「三种口径众数区间均为 0.15~0.20」必须已被推翻
    modes = {tuple(v) for v in REGISTERED["by_filter_mode"].values()}
    add("三种口径众数不唯一（旧「稳健」主张已推翻）", len(modes) == 3,
        f"三种口径众数集合={sorted(modes)}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="assist09 滑窗支撑点口径门禁")
    ap.add_argument("--quiet", action="store_true", help="只打印一行结论")
    args = ap.parse_args()

    try:
        rows = check()
    except GateError as exc:
        print(f"[verify_window_support] 执行失败：{exc}", file=sys.stderr)
        return 2

    bad = [r for r in rows if not r["ok"]]
    if args.quiet:
        print(f"verify_window_support: {'verified' if not bad else 'discrepancy'} "
              f"(checked={len(rows)}, failed={len(bad)}) exit={1 if bad else 0}")
        return 1 if bad else 0

    print("=" * 78)
    print("assist09 滑窗错误率 · 离散支撑点口径门禁")
    print("=" * 78)
    for r in rows:
        print(f"  [{'OK  ' if r['ok'] else 'FAIL'}] {r['item']:<52} {r['detail']}")
    print("-" * 78)
    print(f"  结论: {'PASS' if not bad else f'{len(bad)} 项不一致'}   退出码 {1 if bad else 0}")
    return 1 if bad else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
