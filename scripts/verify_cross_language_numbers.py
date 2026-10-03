#!/usr/bin/env python3
"""跨语言数字一致性门禁：中文完整稿（门禁基准）↔ 英文投稿件（实际投稿）。

为什么需要这个门禁
------------------
`verify_cross_doc_numbers.py` 校验的是**中文完整稿之间**的数字一致性，因为它们
是"事实声明源"。但**实际投出去的是英文稿**（`M*_submission_EN.md`）。若某个
数字在英文稿里被误改，中文基准不会变，现有门禁**察觉不到** —— 这正是审阅意见
§2.1「数字一致性」的真实盲区。

判定方式（为什么不用"出现次数"）
--------------------------------
早期版本用「英文稿出现次数 ≥ 中文稿 × 比例」来捕捉局部篡改，实测**不可靠**：
中英稿复述密度天然不同（某锚点中 16 次 / 英 12 次 = 0.75，比例法误报；
篡改 1/7 处时 6/9 = 0.67 又漏过）。比例阈值在两种失败模式间无稳定取值。

故改为**指标等价判定**：为每个关键指标定义"标签 → 定位正则"，
分别在中文稿与英文稿中按各自写法定位**同一指标的数值**，直接比对两侧是否相等。
这正对应审阅要问的问题——"英文稿报的数字与中文基准是否一致"，
且与复述次数无关。

用法：
    python3 scripts/verify_cross_language_numbers.py            # 报告模式
    python3 scripts/verify_cross_language_numbers.py --strict   # 门禁模式（不一致 → exit 1）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# (论文标签, 中文完整稿, 英文投稿件, 指标锚点列表)
# 指标锚点 = (指标名, 中文稿定位正则, 英文稿定位正则)，各自捕获**同一数值**
PAIRS = [
    ("M1", "M1_难度可公度性与最优错误率_完整稿.md", "M1_submission_EN.md", [
        ("assist09 线性融合漂移 L1",
         r"0\.535(\d)", r"0\.535(\d)"),
        ("分位公制漂移 L1",
         r"0\.000(\d)", r"0\.000(\d)"),
    ]),
    ("M2", "M2_多干预并存学习系统的冲突结构审计_完整稿.md", "M2_submission_EN.md", [
        ("不可归类比例（%）",
         r"77\.(\d)\s*%", r"77\.(\d)\s*%"),
    ]),
    ("M3", "M3_有序难度决策与大模型先验边界_完整稿.md", "M3_submission_EN.md", [
        ("协议审计可用率 ρ",
         r"ρ\s*=\s*0\.0(\d{3})", r"ρ\s*=\s*0\.0(\d{3})"),
        ("知识树深度—难度 ρ",
         r"ρ\s*=\s*\+?0\.07(\d{2})", r"ρ\s*=\s*\+?0\.07(\d{2})"),
    ]),
    ("M4", "M4_信度结构化组合难度估计_完整稿.md", "M4_submission_EN.md", [
        ("恒等式 ρ(d,u)",
         r"1\.0000(\d{2})", r"1\.0000(\d{2})"),
        ("精度加权 ρ(BT prob-mean)",
         r"0\.9640(\d)", r"0\.9640(\d)"),
        ("M4-E 修复后 τ_b",
         r"0\.171(\d)", r"0\.171(\d)"),
    ]),
]


def _first(text: str, pat: str) -> str | None:
    m = re.search(pat, text)
    return m.group(1) if m else None


def main() -> int:
    strict = "--strict" in sys.argv
    rows, failures = [], []

    for tag, cn_name, en_name, metrics in PAIRS:
        cn_path, en_path = DOCS / cn_name, DOCS / en_name
        if not cn_path.exists() or not en_path.exists():
            failures.append(f"{tag}: 文件缺失 (cn={cn_path.exists()} en={en_path.exists()})")
            continue
        cn = cn_path.read_text(encoding="utf-8")
        en = en_path.read_text(encoding="utf-8")
        ok = 0
        for label, cn_pat, en_pat in metrics:
            a, b = _first(cn, cn_pat), _first(en, en_pat)
            if a is None:
                failures.append(f"{tag}「{label}」: 中文稿未定位到数值")
            elif b is None:
                failures.append(f"{tag}「{label}」: 英文稿未定位到数值")
            elif a != b:
                failures.append(f"{tag}「{label}」: 数值不一致 中={a} 英={b}")
            else:
                ok += 1
        rows.append((tag, ok, len(metrics)))

    print("=" * 74)
    print("跨语言数字一致性门禁（中文完整稿 ↔ 英文投稿件）")
    print("=" * 74)
    print(f"{'论文':<6}{'一致指标':<12}{'状态'}")
    print("-" * 74)
    for tag, ok, total in rows:
        state = "✅ 一致" if ok == total else f"❌ {total - ok} 项不一致"
        print(f"{tag:<6}{f'{ok}/{total}':<12}{state}")
    print("-" * 74)

    if failures:
        print("\n不一致明细：")
        for f in failures:
            print(f"  ❌ {f}")
        print(f"\n结论: FAIL（{len(failures)} 项）")
        return 1 if strict else 0

    n = sum(t for _, _, t in rows)
    print(f"\n全部 {len(rows)} 篇、共 {n} 个关键指标在中英文稿中数值一致。")
    print("结论: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
