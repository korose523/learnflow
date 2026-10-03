#!/usr/bin/env python3
"""把 docs/ 下 5 份主文档合并为单一《LearnFlow_研究总档.md》。

设计原则（针对门禁依赖的关键处理）
----------------------------------
`verify_counts.py` / `verify_asset_numbers.py` / `verify_cross_doc_numbers.py`
以**行级正则**扫描这些文档（LF-M 编号表、类别标题、资产规模陈述等）。
因此合并时必须保证：

1. **原内容逐字保留**：不删、不改写、不"优化"任何正文，仅重排标题层级。
2. **锚点表格原样留存**：`### A. 类别（n）` 与 `| LF-M01 | … |` 表格必须保持
   行首格式，否则 `_ROW_RE` / `_CAT_RE` / `_SUBTOTAL_RE` 失配 → 门禁崩溃。
3. **来源可回溯**：每部分开头标注原文件与行数。
4. **标题层级**：各源文档的一级标题降为 `## <部名> <原一级标题>`，其下原
   二/三级标题依次降两级，保证不与部名撞层级。
5. **幂等 + 源缺失即报错**（沿用档案生成器的做法）。

用法：
    python3 tools/_build_master_doc.py
    LF_DOCS_SRC_DIR=/tmp/restore python3 tools/_build_master_doc.py   # 从 git 历史还原源
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
# 源目录可外部指定：合并后源文档通常已删除，可用 SRC_DIR 指向从 git 历史还原的副本
SRC_DIR = Path(os.environ.get("LF_DOCS_SRC_DIR", DOCS))

OUT = DOCS / "LearnFlow_研究总档.md"

# (源文件相对路径, 部名, 一句话说明)
SOURCES = [
    ("研究计划与报告/研究计划_中文版.md",
     "第一部 · 研究计划",
     "博士学位论文研究计划（v1.1）。**跨文档数字一致性门禁的基准文档之一**"
     "（`verify_cross_doc_numbers.py` 的 `plan` 列）。"),
    ("研究计划与报告/研究报告_中文版.md",
     "第二部 · 研究进展报告",
     "测量侧与静态侧已完成、因果侧待执行。**门禁基准文档之一**"
     "（`verify_cross_doc_numbers.py` 的 `report` 列）。"),
    ("LearnFlow_期刊论文拆分方案.md",
     "第三部 · 期刊论文拆分方案",
     "四篇论文的拆分设计与资产口径。**`verify_asset_numbers.py` 的 `SPLIT_DOC`"
     "（运行时解析后端源码行数等）**。"),
    ("LearnFlow_机制治理与落实方案.md",
     "第四部 · 机制治理与落实方案",
     "54 个游戏化干预机制的权威清单。**`verify_counts.py` 的 `GOVERNANCE_DOC`"
     "（正则扫描 LF-M 编号表）与 `mechanism_registry.py` 的来源**。"
     "⚠️ 本部 §4.2 的编号表与类别标题是门禁解析锚点，格式勿改。"),
    ("LearnFlow_研究设计与审阅档案.md",
     "第五部 · 研究设计与审阅档案",
     "10 份研究设计/方法论/审阅台账的合并档（权威事实基线、因果侧识别策略、"
     "审阅意见整改清单、M1/M2/M3 方法论方案、人类被试计划、AI 披露政策表）。"),
]

# 门禁锚点：这些行必须保持行首格式（正则依赖）
ANCHOR_WARNING = (
    "以下内容为门禁运行时解析锚点，**格式不可更改**（行首 `| LF-M01 |`、"
    "`### A. 类别（n）`、`**小计** … = **n**` 均被正则匹配）："
)


def _assert_sources_present() -> None:
    missing = [fn for fn, _, _ in SOURCES
               if not (DOCS / fn).exists() and not (SRC_DIR / fn).exists()]
    if missing:
        raise SystemExit(
            "ERROR: 以下源文档缺失，拒绝生成残缺总档:\n  " + "\n  ".join(missing)
            + "\n请先从 git 历史还原，例如："
            + "\n  git show 9d843cf:docs/<路径> > /tmp/restore/<路径>"
        )


def _resolve(fn: str) -> Path:
    p = DOCS / fn
    return p if p.exists() else SRC_DIR / fn


def demote(text: str, levels: int = 2) -> str:
    """标题整体降 `levels` 级，避免与部名 ## 撞层级。"""
    out = []
    for line in text.splitlines():
        if line.startswith("#"):
            n = len(line) - len(line.lstrip("#"))
            if n <= 6 - levels:
                line = "#" * levels + line
        out.append(line)
    return "\n".join(out)


def build() -> str:
    _assert_sources_present()
    parts: list[str] = []

    parts.append("# LearnFlow 研究总档\n")
    parts.append(
        "> **本档由 `tools/_build_master_doc.py` 自动合并生成**，聚合 5 份主文档："
        "研究计划、研究进展报告、期刊论文拆分方案、机制治理与落实方案、研究设计与审阅档案。\n"
        ">\n"
        "> **内容为原文逐字纳入，未作删改或改写**；仅重排标题层级并标注来源。"
        "各部分开头标注原文件与行数，便于回溯。\n"
        f">\n> 生成日期：{date.today().isoformat()}　|　来源目录：`docs/`\n"
    )

    # ── 目录 ────────────────────────────────────────────────────────────
    parts.append("## 目录与门禁锚点对照\n")
    parts.append("| 部 | 标题 | 来源文件 | 行数 | 门禁角色 |")
    parts.append("|---|---|---|---|---|")
    for i, (fn, part, desc) in enumerate(SOURCES, 1):
        p = _resolve(fn)
        n = len(p.read_text(encoding="utf-8").splitlines())
        if "计划" in fn and "研究" in fn:
            role = "跨文档门禁基准（plan）"
        elif "报告" in fn:
            role = "跨文档门禁基准（report）"
        elif "拆分" in fn:
            role = "**asset 门禁 SPLIT_DOC**"
        elif "治理" in fn:
            role = "**counts 门禁 GOVERNANCE_DOC** + registry 来源"
        else:
            role = "6 个复算脚本引用"
        parts.append(f"| {i} | {part} | `{fn}` | {n} | {role} |")
    parts.append("")
    parts.append(
        "> **门禁锚点说明**：`verify_counts.py`（`_ROW_RE` / `_CAT_RE` / `_SUBTOTAL_RE`）、"
        "`verify_asset_numbers.py`、`verify_cross_doc_numbers.py` 以**行级正则**扫描本档内容。"
        f"{ANCHOR_WARNING}\n>\n"
        "> 上述四个脚本的路径常量已指向本档；如修改本档 §4.2 的编号表格式，"
        "门禁将解析失败并报「未能从治理文档解析出任何类别标题」。\n"
    )

    # ── 正文 ────────────────────────────────────────────────────────────
    for i, (fn, part, desc) in enumerate(SOURCES, 1):
        p = _resolve(fn)
        raw = p.read_text(encoding="utf-8")
        n = len(raw.splitlines())
        parts.append("\n---\n")
        parts.append(f"## {part}\n")
        parts.append(f"> **来源**：`docs/{fn}`　|　**原文件行数**：{n}\n>\n> {desc}\n")
        if "治理" in fn:
            parts.append(f"> ⚠️ {ANCHOR_WARNING}\n")
        # 治理方案例外：其 `### A. 类别（n）` 被 _CAT_RE 硬编码匹配，
        # 降级会使门禁解析失败，故整篇不降级（部名改用分隔线承载）
        if "治理" in fn:
            body = raw
        else:
            body = demote(raw, levels=2)
        lines = body.splitlines()
        if lines and lines[0].lstrip("#").strip():
            pass
        elif lines and lines[0].startswith("##"):
            lines = lines[1:]
        # 若首行是降级后的原一级标题(###)，一并去掉
        if lines and lines[0].startswith("### ") and not lines[0].startswith("####"):
            lines = lines[1:]
        parts.append("\n".join(lines).strip() + "\n")

    return "\n".join(parts)


def main() -> None:
    md = build()
    OUT.write_text(md, encoding="utf-8")
    print(f"written: {OUT.relative_to(REPO)}  ({len(md.splitlines())} lines, "
          f"{len(md.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
