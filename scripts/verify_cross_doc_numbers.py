#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_cross_doc_numbers.py
===========================

Cross-document numeric-consistency gate for the LearnFlow submission package
(审阅意见 §2.1: 统一时点 + cross-doc 数字一致性门禁).

It extracts a fixed set of "headline asset / count" numbers from the dissertation
proposal, the research report, the journal-split plan, and the four full paper
drafts, prints a single consistency table, and:

  * exits with code 0  when every STRICT (review-critical) metric agrees across
    all documents that state it;
  * exits with code 1  when a STRICT metric is stated with *different* values in
    two or more documents (a real inconsistency that must be fixed before
    submission);
  * prints DRIFT metrics (volatile asset sizes) for human review but does NOT
    fail the build on them, because the audit paper (M2) deliberately documents
    asset drift relative to its sealed audit-time tag `audit-m2-20260911`
    (see M2 §4.4). Those numbers are explicitly *not* part of any audit
    conclusion, so divergence there is expected and tracked, not gated.

Extraction is purely regex-based. If a document does not state a given metric,
the cell is marked "缺失" (missing) rather than raising an error.

Usage:
    python scripts/verify_cross_doc_numbers.py
    python scripts/verify_cross_doc_numbers.py --strict-only   # only print strict rows
    python scripts/verify_cross_doc_numbers.py --fail-on-drift # also fail on drift

Author: meta-editor (LearnFlow merge team).  No external dependencies.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Repository layout
# --------------------------------------------------------------------------- #
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DOCS = REPO_ROOT / "docs"
PLAN_REPORT = DOCS / "研究计划与报告"
MASTER = DOCS / "LearnFlow_研究总档.md"  # Historical index only.
DOCUMENTS = [
    ("plan", "计划书中文", PLAN_REPORT / "研究计划_中文版.md"),
    ("plan_ko", "计划书韩文", PLAN_REPORT / "研究计划_韩文版.md"),
    ("report", "报告中文", PLAN_REPORT / "研究报告_中文版.md"),
    ("report_ko", "报告韩文", PLAN_REPORT / "研究报告_韩文版.md"),
    ("M1",     "M1 投稿主稿",     DOCS / "M1_submission_EN_compressed.md"),
    ("M2",     "M2 路线B章",     DOCS / "M2_路线B_内部静态审计章.md"),
    ("M3",     "M3 投稿主稿",     DOCS / "M3_submission_EN_compressed.md"),
]

# --------------------------------------------------------------------------- #
# Metric definitions
#   mode:
#     "strict"  -> divergence across docs => exit code 1
#     "drift"   -> reported for review, never fails the build
#   Each doc key maps to an ordered list of regexes; the first capture wins.
#   Capture group 1 is the value (commas allowed for integers; hex for fingerprint).
# --------------------------------------------------------------------------- #
METRICS = [
    # ---- STRICT (review-critical, must agree everywhere stated) -------------- #
    ("mechanisms", "机制数(登记)", "strict", {
        "plan":   [r"游戏化干预机制（登记）\s*\|\s*\*\*(\d+)"],
        "report": [r"游戏化干预机制（登记）\s*\|\s*\*\*(\d+)"],
        "split":  [r"(\d{1,3})\s*个唯一机制", r"登记\s*(\d{1,3})\b"],
        "M1":     [r"(\d{1,3})\s*个游戏化干预机制", r"机制\s*\*\*(\d+)"],
        "M2":     [r"登记\s*(\d{1,3})\s*个", r"登记\s*(\d{1,3})\s*/\s*效果生产"],
        "M3":     [r"登记\s*\*\*(\d+)", r"机制计数严格为\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("methods", "学习方法数", "strict", {
        "plan":   [r"学习方法\s*\|\s*\*\*(\d+)"],
        "report": [r"学习方法\s*\|\s*\*\*(\d+)"],
        "split":  [r"(\d{1,3})\s*种学习方法"],
        "M1":     [r"(\d{1,3})\s*种学习方法"],
        "M2":     [r"`learning_methods`[^*\n]*\*\*(\d+)", r"学习方法\s*\*\*(\d+)"],
        "M3":     [r"学习方法\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("effect_producers_audit", "效果生产者(审计时点)", "strict", {
        "plan":   [r"效果生产\s*(\d+)"],
        "report": [r"运行时真实效果生产者\s*\|\s*\*\*(\d+)"],
        "split":  [r"效果生产(?:者)?[^。\n]{0,30}?(\d+)"],
        "M1":     [r"效果生产\s*(\d+)"],
        "M2":     [r"效果生产\s*(\d+)\s*个"],
        "M3":     [r"效果生产\s*(\d+)"],
        "M4":     [],
    }),
    ("api_routes_reachable", "可达 API 端点", "strict", {
        "plan":   [r"可及 API 端点\s*\|\s*\*\*(\d+)"],
        "report": [r"可及 API 端点\s*\|\s*\*\*(\d+)"],
        "split":  [r"API 端点\s*\|\s*\*\*(\d+)", r"(\d+)\s*个 API 端点"],
        "M1":     [r"API 端点[^*\n]{0,20}?(\d+)"],
        "M2":     [r"api_routes_reachable\s*\|\s*(\d+)"],
        "M3":     [r"API 端点[^*\n]{0,20}?(\d+)"],
        "M4":     [],
    }),
    ("test_files", "测试文件数", "strict", {
        "plan":   [r"全量测试\s*\|\s*\*\*(\d+)\s*个测试文件"],
        "report": [r"全量测试\s*\|\s*\*\*(\d+)\s*个测试文件"],
        "split":  [],
        "M1":     [r"(\d{1,3})\s*个测试文件"],
        "M2":     [r"`test_files`\s*\|\s*[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"(\d{1,3})\s*个测试文件"],
        "M4":     [],
    }),
    ("tests_collected", "pytest 收集测试数", "strict", {
        "plan":   [r"个测试文件\s*/\s*(\d+)\s*条通过"],
        "report": [r"个测试文件\s*/\s*(\d+)\s*条通过"],
        "split":  [],
        "M1":     [r"凡引用测试数量，本文一律写\s*(\d{3,4})", r"全量测试[^。\n]{0,40}?(\d{3,4})"],
        "M2":     [r"tests_collected[^|]*\|\s*[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"涉及仓库回归测试数量时，一律写\s*\*\*(\d+)\*\*", r"全量测试(?:数)?[^。\n]{0,20}?(\d{3,4})", r"全量测试数[^。\n]{0,12}?\*\*(\d+)"],
        "M4":     [],
    }),
    ("skill_tree_nodes", "技能树节点数", "strict", {
        "plan":   [r"元学习技能树节点\s*\|\s*\*\*(\d+)"],
        "report": [r"元学习技能树节点\s*\|\s*\*\*(\d+)"],
        "split":  [],
        "M1":     [r"技能树节点\s*\*\*(\d+)"],
        "M2":     [r"`skill_tree_nodes`\s*\*\*(\d+)"],
        "M3":     [r"技能树节点\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("registry_fingerprint", "注册表指纹", "strict", {
        "plan":   [r"机制注册表指纹\s*`([0-9a-f]+)`"],
        "report": [r"机制注册表指纹\s*`([0-9a-f]+)`"],
        "split":  [r"注册表指纹\s*`([0-9a-f]+)`"],
        "M1":     [r"注册表指纹\s*`([0-9a-f]+)`"],
        "M2":     [r"注册表指纹\s*`([0-9a-f]+)`"],
        "M3":     [r"注册表指纹\s*`([0-9a-f]+)`"],
        "M4":     [],
    }),
    # ---- DRIFT (volatile asset sizes; documented drift in M2, not gated) ----- #
    ("python_loc", "Python 代码行数", "drift", {
        "plan":   [r"(\d{2,3},\d{3})\s*行"],
        "report": [r"(\d{2,3},\d{3})\s*行"],
        "split":  [],
        "M1":     [],
        "M2":     [r"`python_loc`\s*\|[^|]*\|\s*\*\*(\d{1,3}(?:,\d{3})*)"],
        "M3":     [],
        "M4":     [],
    }),
    ("source_files", "源文件数", "drift", {
        "plan":   [r"(\d{2,3})\s*源文件"],
        "report": [r"(\d{2,3})\s*源文件"],
        "split":  [],
        "M1":     [r"(\d{2,3})\s*源文件"],
        "M2":     [r"`source_files`\s*\|[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"(\d{2,3})\s*源文件"],
        "M4":     [],
    }),
    ("service_modules", "服务模块数", "drift", {
        "plan":   [r"服务模块\s*\|\s*\*\*(\d+)"],
        "report": [r"服务模块\s*\|\s*\*\*(\d+)"],
        "split":  [],
        "M1":     [r"服务模块\s*\*\*\s*(\d+)"],
        "M2":     [r"`service_modules`\s*\|[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"服务模块\s*\*\*\s*(\d+)"],
        "M4":     [],
    }),
    ("test_functions", "测试函数数", "drift", {
        "plan":   [],
        "report": [r"测试函数[^。\n]{0,15}?(\d+)"],
        "split":  [],
        "M1":     [],
        "M2":     [r"`test_functions`\s*\|[^|]*\|\s*\*\*(\d+)"],
        "M3":     [],
        "M4":     [],
    }),
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
# Only the existing count metrics are checked here; missing cells remain explicit.
for metric_key, _, _, patterns in METRICS:
    for doc_key in ("plan", "plan_ko", "report", "report_ko", "M2"):
        if metric_key == "mechanisms":
            patterns[doc_key] = [r"(?:登记|등록)\s*(\d+)"]
        elif metric_key == "effect_producers_audit":
            patterns[doc_key] = [r"(?:效果生产者?|효과\s*생산자)\s*(\d+)"]

def _clean(value: str) -> str:
    """Normalise an extracted token for comparison (strip thousands separators)."""
    if value is None:
        return "缺失"
    return value.replace(",", "").strip()


def extract_all() -> dict:
    """Build {metric_key: {doc_key: value}}."""
    table: dict[str, dict[str, str]] = {}
    for key, _label, _mode, _per in METRICS:
        table[key] = {}

    for dkey, _dlabel, dpath in DOCUMENTS:
        text = ""
        if not dpath.exists():
            for key, _l, _m, _p in METRICS:
                table[key][dkey] = "缺失(文件)"
            continue
        try:
            text = dpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            for key, _l, _m, _p in METRICS:
                table[key][dkey] = "缺失(读错)"
            continue
        for key, _label, _mode, per_doc in METRICS:
            regexes = per_doc.get(dkey, [])
            found = "缺失"
            for rx in regexes:
                m = re.search(rx, text)
                if m:
                    found = m.group(1)
                    break
            table[key][dkey] = found
    return table


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _fmt_cell(value: str) -> str:
    if value.startswith("缺失"):
        return "-"
    return value


def print_table(table: dict, strict_only: bool) -> None:
    headers = [label for _k, label, _p in DOCUMENTS]  # doc labels
    metric_rows = [(k, l, m) for k, l, m, _p in METRICS if (not strict_only or m == "strict")]

    # column widths
    doc_labels = [label for _k, label, _p in DOCUMENTS]
    col_w = [max(10, len(lbl)) for lbl in doc_labels]
    name_w = max(len("指标(mode)") , max(len(l) + 4 for _k, l, _m in metric_rows))

    # header
    line = "指标(mode)".ljust(name_w) + " | " + " | ".join(
        lbl.ljust(w) for lbl, w in zip(doc_labels, col_w)
    )
    print(line)
    print("-" * len(line))

    for key, label, mode in metric_rows:
        row_vals = table[key]
        cells = []
        for dkey, w in zip([k for k, _l, _p in DOCUMENTS], col_w):
            cells.append(_fmt_cell(row_vals.get(dkey, "缺失")).ljust(w))
        mode_tag = "STRICT" if mode == "strict" else "drift "
        print(f"{label}({mode_tag})".ljust(name_w) + " | " + " | ".join(cells))
    print()


def evaluate(table: dict, fail_on_drift: bool) -> tuple[bool, list[str]]:
    """Return (ok, messages). ok=False when a STRICT metric diverges, or when
    fail_on_drift and a DRIFT metric diverges."""
    problems: list[str] = []
    for key, label, mode, _per in METRICS:
        values = table[key]
        present = {k: _clean(v) for k, v in values.items()
                   if not str(v).startswith("缺失") and v not in ("", None)}
        distinct = sorted(set(present.values()))
        is_problem = (len(distinct) > 1)
        if not is_problem:
            continue
        if mode == "strict" or fail_on_drift:
            problems.append(
                f"  [INCONSISTENT] {label}: "
                + ", ".join(f"{k}={v}" for k, v in present.items())
            )
        else:
            problems.append(
                f"  [DRIFT/ok] {label}: "
                + ", ".join(f"{k}={v}" for k, v in present.items())
                + "  (M2 文档化漂移，不阻断门禁)"
            )
    ok = all("INCONSISTENT" not in p for p in problems)
    return ok, problems


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    strict_only = "--strict-only" in argv
    fail_on_drift = "--fail-on-drift" in argv

    print("=" * 78)
    print("LearnFlow 跨文档数字一致性门禁  (审阅意见 §2.1)")
    print("工作稿检查：尚未冻结；v1.1-submit 是历史审阅基线，不代表当前修改")
    print("=" * 78)
    print()

    table = extract_all()
    print_table(table, strict_only)

    ok, problems = evaluate(table, fail_on_drift)
    print("-" * 78)
    if problems:
        print("发现项：")
        for p in problems:
            print(p)
        print("-" * 78)
    else:
        print("未发现非缺失计数间的分歧；缺失项未验证，研究指标仍需人工与原始结果核对。")

    if ok:
        print("门禁结果: PASS (有限计数检查；缺失项不代表已验证)")
        return 0
    else:
        print("门禁结果: FAIL (存在 STRICT 指标分歧，须在提交前修正)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
