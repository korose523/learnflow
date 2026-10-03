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
    python scripts/verify_cross_doc_numbers.py --selftest    # prove the gate rejects injected bad numbers

Author: meta-editor (LearnFlow merge team).  No external dependencies.
"""

from __future__ import annotations

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

# (doc key, display label, path) ------------------------------------------------ #
DOCUMENTS = [
    ("plan",   "计划书(计划)",  PLAN_REPORT / "研究计划_中文版.md"),
    ("report", "计划书(报告)",  PLAN_REPORT / "研究报告_中文版.md"),
    # 2026-10-02 补齐盲区：韩文版是正式提交件（导师为韩国教授），此前不在扫描范围内，
    # 导致韩文计划/报告长期停留在 2026-09-22 旧快照（88 文件 / 25,795 行 / 936 测试）
    # 而门禁仍报 PASS——正是审阅 §2.1「门禁通过不等于文档正确」所指的失效模式。
    ("plan_ko",   "계획서(韩)",  PLAN_REPORT / "研究计划_韩文版.md"),
    ("report_ko", "보고서(韩)",  PLAN_REPORT / "研究报告_韩文版.md"),
    ("split",  "拆分方案",      DOCS / "LearnFlow_期刊论文拆分方案.md"),
    ("M1",     "M1 完整稿",     DOCS / "M1_难度可公度性与最优错误率_完整稿.md"),
    ("M2",     "M2 完整稿",     DOCS / "M2_多干预并存学习系统的冲突结构审计_完整稿.md"),
    ("M3",     "M3 完整稿",     DOCS / "M3_有序难度决策与大模型先验边界_完整稿.md"),
    ("M4",     "M4 完整稿",     DOCS / "M4_信度结构化组合难度估计_完整稿.md"),
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
        "plan_ko":   [r"등록\s*(\d+)"],
        "report_ko": [r"메커니즘\s+(\d+)\s*/\s*방법"],
        "split":  [r"(\d{1,3})\s*个唯一机制", r"登记\s*(\d{1,3})\b"],
        "M1":     [r"(\d{1,3})\s*个游戏化干预机制", r"机制\s*\*\*(\d+)"],
        "M2":     [r"登记\s*(\d{1,3})\s*个", r"登记\s*(\d{1,3})\s*/\s*效果生产"],
        "M3":     [r"登记\s*\*\*(\d+)", r"机制计数严格为\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("methods", "学习方法数", "strict", {
        "plan":   [r"学习方法\s*\|\s*\*\*(\d+)"],
        "report": [r"学习方法\s*\|\s*\*\*(\d+)"],
        "report_ko": [r"방법\s+(\d+)\s*/"],
        "split":  [r"(\d{1,3})\s*种学习方法"],
        "M1":     [r"(\d{1,3})\s*种学习方法"],
        "M2":     [r"`learning_methods`[^*\n]*\*\*(\d+)", r"学习方法\s*\*\*(\d+)"],
        "M3":     [r"学习方法\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("effect_producers_audit", "效果生产者(审计时点)", "strict", {
        "plan":   [r"效果生产\s*(\d+)"],
        "report": [r"运行时真实效果生产者\s*\|\s*\*\*(\d+)"],
        "plan_ko":   [r"효과 생산\s*(\d+)"],
        "report_ko": [r"효과 생산자\s*\*\*(\d+)"],
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
        "split":  [r"(\d+)\s*个测试文件"],
        "M1":     [r"(\d{1,3})\s*个测试文件"],
        "M2":     [r"`test_files`\s*\|\s*[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"(\d{1,3})\s*个测试文件"],
        "M4":     [],
    }),
    ("tests_collected", "pytest 收集测试数", "strict", {
        "plan":   [r"个测试文件\s*/\s*(\d+)\s*条通过"],
        "report": [r"个测试文件\s*/\s*(\d+)\s*条通过"],
        "report_ko": [r"(\d+)\s*collected"],
        "split":  [r"测试\s*\|\s*\*\*(\d+)\s*项通过", r"(\d+)\s*项通过"],
        "M1":     [r"凡引用测试数量，本文一律写\s*(\d{3,4})", r"全量测试[^。\n]{0,40}?(\d{3,4})"],
        "M2":     [r"tests_collected[^|]*\|\s*[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"涉及仓库回归测试数量时，一律写\s*\*\*(\d+)\*\*", r"全量测试(?:数)?[^。\n]{0,20}?(\d{3,4})", r"全量测试数[^。\n]{0,12}?\*\*(\d+)"],
        "M4":     [],
    }),
    ("skill_tree_nodes", "技能树节点数", "strict", {
        "plan":   [r"元学习技能树节点\s*\|\s*\*\*(\d+)"],
        "report": [r"元学习技能树节点\s*\|\s*\*\*(\d+)"],
        "report_ko": [r"스킬 트리\s+(\d+)"],
        "split":  [],
        "M1":     [r"技能树节点\s*\*\*(\d+)"],
        "M2":     [r"`skill_tree_nodes`\s*\*\*(\d+)"],
        "M3":     [r"技能树节点\s*\*\*(\d+)"],
        "M4":     [],
    }),
    ("registry_fingerprint", "注册表指纹", "strict", {
        "plan":   [r"机制注册表指纹\s*`([0-9a-f]+)`"],
        "report": [r"机制注册表指纹\s*`([0-9a-f]+)`"],
        "report_ko": [r"지문\s*`([0-9a-f]+)`"],
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
        "report_ko": [r"행수\s*\|\s*(\d{2,3},\d{3})"],
        "split":  [r"(\d{2,3},\d{3})\s*行"],
        "M1":     [],
        "M2":     [r"`python_loc`\s*\|[^|]*\|\s*\*\*(\d{1,3}(?:,\d{3})*)"],
        "M3":     [],
        "M4":     [],
    }),
    ("source_files", "源文件数", "drift", {
        "plan":   [r"(\d{2,3})\s*源文件"],
        "report": [r"(\d{2,3})\s*源文件"],
        "split":  [r"(\d+)\s*个源文件"],
        "M1":     [r"(\d{2,3})\s*源文件"],
        "M2":     [r"`source_files`\s*\|[^|]*\|\s*\*\*(\d+)"],
        "M3":     [r"(\d{2,3})\s*源文件"],
        "M4":     [],
    }),
    ("service_modules", "服务模块数", "drift", {
        "plan":   [r"服务模块\s*\|\s*\*\*(\d+)"],
        "report": [r"服务模块\s*\|\s*\*\*(\d+)"],
        "split":  [r"(\d+)\s*个服务模块"],
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
# Korean-document patterns (keyed by metric key; applied to any doc key ending
# in "_ko").  Kept separate so adding a translated document does not require
# touching every metric entry.  Korean tables use the same shape as the Chinese
# ones, e.g.  | 백엔드 Python | **92개 파일 / 26,782행** | .
# --------------------------------------------------------------------------- #
KO_PATTERNS = {
    "mechanisms":              [r"메커니즘\s*\*\*(\d+)",
                                r"메커니즘\(등록\)\s*\|\s*\*\*?(\d+)"],
    "methods":                 [r"학습 방법\s*\|\s*\*\*(\d+)"],
    "effect_producers_audit":  [r"런타임[^\n|]{0,14}?효과 생산자\s*\|\s*\*\*(\d+)",
                                r"효과를 생성하는 생산자[^\n]{0,14}?(\d+)"],
    "api_routes_reachable":    [r"API 엔드포인트\s*\|\s*\*\*(\d+)"],
    "test_files":              [r"(\d+)개\s*테스트 파일"],
    "tests_collected":         [r"테스트 파일\s*/\s*(\d+)\s*건",
                                r"전체 테스트 수[^\n]{0,30}?(\d{3,4})"],
    "skill_tree_nodes":        [r"스킬 트리 노드\s*\|\s*\*\*(\d+)"],
    "registry_fingerprint":    [r"레지스트리 지문\s*`([0-9a-f]+)`"],
    "python_loc":              [r"(\d{2,3},\d{3})\s*행"],
    "source_files":            [r"\*\*(\d{2,3})개 파일"],
    "service_modules":         [r"서비스 모듈\s*\|\s*\*\*(\d+)"],
    "test_functions":          [r"테스트 함수[^\n|]{0,15}?(\d+)"],
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
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
        is_ko = dkey.endswith("_ko")
        for key, _label, _mode, per_doc in METRICS:
            # Translated documents carry their own table wording.  Ordered
            # chain, first capture wins:
            #   1. KO_PATTERNS[key]  -> shared Korean table wording
            #   2. per_doc[dkey]     -> any document-specific pattern
            # Both lists are concatenated rather than using `or`, so a
            # document-specific pattern still acts as a *fallback* when the
            # shared Korean pattern finds nothing (e.g. a table shaped
            # differently in one of the two Korean documents).  Preferring
            # silence over a miss is what let the Korean drift hide for a week.
            regexes = (KO_PATTERNS.get(key, []) if is_ko else []) + per_doc.get(dkey, [])
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


def _selftest() -> int:
    """Inject a fake STRICT divergence and confirm the gate rejects it."""
    table = extract_all()
    table["mechanisms"]["plan"] = "999"          # inject a bogus value
    ok, problems = evaluate(table, fail_on_drift=False)
    injected_caught = (not ok) and any("机制数" in p for p in problems)
    # and confirm the real table passes
    real_ok, _ = evaluate(extract_all(), fail_on_drift=False)
    print("selftest: 注入 机制数 plan=999 -> 门禁拦截 =", injected_caught)
    print("selftest: 未注入的真实表 PASS =", real_ok)
    return 0 if (injected_caught and real_ok) else 1


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    strict_only = "--strict-only" in argv
    fail_on_drift = "--fail-on-drift" in argv

    if "--selftest" in argv:
        return _selftest()

    print("=" * 78)
    print("LearnFlow 跨文档数字一致性门禁  (审阅意见 §2.1)")
    print("基准 tag: v1.1-submit (由 lead 在最终提交时打; 其后工作不进入提交件)")
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
        print("未发现任何指标分歧。")

    if ok:
        print("门禁结果: PASS (所有 STRICT 指标在已陈述文档间一致)")
        return 0
    else:
        print("门禁结果: FAIL (存在 STRICT 指标分歧，须在提交前修正)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
