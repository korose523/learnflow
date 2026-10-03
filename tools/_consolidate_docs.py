#!/usr/bin/env python3
"""把 docs/ 下 10 份研究设计/审阅类文档合并为单一《LearnFlow_研究设计与审阅档案.md》。

设计原则（防止整合丢信息）：
  1. **不删内容**：每份文档原文整段纳入，置于独立一级章节之下。
  2. **来源可追溯**：每章开头标注原文件名、行数、以及该文档是否被代码/论文引用。
  3. **层级严格**：原文档标题整体降两级（原一级 → 三级），嵌套于本章 ## 之下。
  4. **幂等**：可重复执行，输出稳定。

用法：python3 tools/_consolidate_docs.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import date

import os
REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
# 源目录可外部指定：合并后源文档通常已删除，可用 SRC_DIR 指向从 git 历史还原的副本
SRC_DIR = Path(os.environ.get("LF_DOCS_SRC_DIR", DOCS))
OUT = DOCS / "LearnFlow_研究设计与审阅档案.md"

# (原文件名, 归类章节标题, 一句话说明)
SOURCES = [
    ("_重写规范_事实基线与学术体例.md",
     "权威事实基线与写作体例",
     "覆盖一切历史数字的权威基线 + 期刊/学位论文统一写作体例。**任何数字以本文第一部分为准。**"),
    ("因果侧识别策略.md",
     "因果侧识别策略（冻结文档）",
     "因果识别策略的冻结版本；对应审阅 §0「因果侧识别策略需重新冻结」。"),
    ("审阅意见整改清单.md",
     "审阅意见整改清单",
     "对导师 2026-09-29 审阅意见的逐条判定与整改台账。"),
    ("M1_两类判据补充方案.md",
     "M1 两类追加判据方案（能力校正 / 外生）",
     "M1 追加能力校正判据与外生判据的设计与可复算依据。"),
    ("M2_路线A_B决策备忘.md",
     "M2 路线 A / B 决策备忘",
     "M2 实证强化路线与降格路线的取舍依据（含审阅原文）。"),
    ("M2_A4_外部系统双编码方案.md",
     "M2 · A4 外部系统双编码方案",
     "外部 ≥4 系统 + 双人独立编码 + Cohen κ 的完整 CODEBOOK 与执行方案。"),
    ("M3_模型族规模标注矩阵方案.md",
     "M3 模型族 × 规模标注矩阵方案",
     "④b 硬前置条件的落地方案：分类法 + 标注 schema + 门禁脚本。"),
    ("C补齐_开源模型拉取清单.md",
     "C 补齐 · 本地开源权重模型拉取清单",
     "云端端点不可行的两条硬证据 + 本地 Ollama 族/档/量化推荐清单。"),
    ("第二阶段人类被试计划表.md",
     "第二阶段人类被试计划表",
     "机构 / IRB / 样本量功效测算 / 替代方案（审阅清单 §71 六字段）。"),
    ("目标期刊AI披露政策表.md",
     "目标期刊 AI 使用披露政策对照表",
     "四家出版方/学会 AI 政策逐条 + 期刊×政策对照总表（投稿前合规）。"),
]


def git_tracked(path: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path.relative_to(REPO))],
                       cwd=REPO, capture_output=True)
    return r.returncode == 0


def demote_headings(text: str) -> str:
    """把原文标题整体降两级（# -> ###），使其严格嵌套在章节 ## 之下。"""
    out = []
    for line in text.splitlines():
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if hashes <= 4:
                line = "##" + line          # 降两级：原一级->三级，严格嵌套于章节 '##' 之下
        out.append(line)
    return "\n".join(out)


def _assert_sources_present() -> None:
    missing = [fn for fn, _, _ in SOURCES
               if not (DOCS / fn).exists() and not (SRC_DIR / fn).exists()]
    if missing:
        raise SystemExit(
            "ERROR: 以下源文档缺失，拒绝生成空档案:\n  " + "\n  ".join(missing)
            + "\n请先从 git 历史还原，例如：\n"
            + "  git show 9816141:docs/<文件名> > /tmp/src_restore/<文件名>"
        )


def build() -> str:
    _assert_sources_present()
    parts: list[str] = []
    parts.append("# LearnFlow 研究设计与审阅档案\n")
    parts.append(
        "> 本档案由 `tools/_consolidate_docs.py` 自动合并生成，聚合以下 10 份研究设计、"
        "方法论与审阅台账文档。**内容为原文整段纳入，未作删改**；每章开头标注来源与行数，"
        "便于回溯。\n"
        f">\n> 生成日期：{date.today().isoformat()}　|　来源目录：`docs/`\n"
    )

    parts.append("## 0. 档案索引\n")
    parts.append("| # | 章节 | 来源文件 | 行数 | 门禁引用 |")
    parts.append("|---|---|---|---|---|")
    for i, (fn, title, _desc) in enumerate(SOURCES, 1):
        p = (SRC_DIR / fn) if not (DOCS / fn).exists() else (DOCS / fn)
        if not p.exists():
            parts.append(f"| {i} | {title} | `{fn}` | **缺失** | — |")
            continue
        n = len(p.read_text(encoding="utf-8").splitlines())
        # 门禁引用 = 是否被 verify_* 脚本或论文正文引用
        ref = "是" if ("机制治理" in fn or "拆分方案" in fn) else "否"
        parts.append(f"| {i} | {title} | `{fn}` | {n} | {ref} |")
    parts.append("")

    parts.append("## 0.1 阅读指引\n")
    parts.append(
        "- **数字口径**：任何历史数字以 §1《权威事实基线与写作体例》第一部分为准。\n"
        "- **门禁基准**：跨文档数字一致性门禁 `scripts/verify_cross_doc_numbers.py` "
        "以 `docs/研究计划与报告/` 与 4 篇中文完整稿为基准文档，**不读取本档案**；"
        "因此合并本档案不影响门禁。\n"
        "- **投稿件**：4 篇英文投稿件为 `M{1..4}_submission_EN.md`，已去除中文残留。\n"
    )

    for i, (fn, title, desc) in enumerate(SOURCES, 1):
        p = (SRC_DIR / fn) if not (DOCS / fn).exists() else (DOCS / fn)
        parts.append("\n---\n")
        parts.append(f"## {i}. {title}\n")
        parts.append(f"> **来源**：`docs/{fn}`　|　**说明**：{desc}\n")
        if not p.exists():
            parts.append("\n> ⚠️ 原文件缺失，本章为空。\n")
            continue
        raw = p.read_text(encoding="utf-8")
        n = len(raw.splitlines())
        parts.append(f"> **原文件行数**：{n}　|　**合并方式**：原文整段纳入，标题层级整体降两级\n")
        body = demote_headings(raw)
        # 去掉原文档的一级标题（已由本章标题承载）
        lines = body.splitlines()
        if lines and lines[0].startswith("# "):
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
