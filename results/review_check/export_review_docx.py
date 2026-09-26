# -*- coding: utf-8 -*-
"""导出《指导教授_审阅意见_20260922_cn.docx》全文为 markdown，供逐条核对。
注：python-docx 仅装在系统 Python 3.11（见项目记忆），须用该解释器运行。
"""
import sys
from pathlib import Path

from docx import Document

SRC = Path(r"C:\Users\mac\Downloads\指导教授_审阅意见_20260922_cn.docx")
OUT = Path(r"E:\learnflow\results\review_check\review_opinion_20260922.md")


def clean(s: str) -> str:
    # 日志/文件写入前净化不可见字符，避免被判为二进制导致 Read 读不出
    return "".join(ch if (0x20 <= ord(ch) <= 0x7E or 0x4E00 <= ord(ch) <= 0x9FFF) else "." for ch in s)


def main():
    if not SRC.exists():
        sys.exit("✗ 源文件不存在: %s" % SRC)
    doc = Document(str(SRC))
    lines = []
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        style = (para.style.name or "").lower()
        if "heading" in style:
            lvl = 1
            for ch in style:
                if ch.isdigit():
                    lvl = int(ch)
                    break
            lines.append("#" * min(lvl + 1, 6) + " " + clean(t))
        else:
            lines.append(clean(t))
    # 表格（若有）
    tables = doc.tables
    if tables:
        lines.append("")
        lines.append("## [表格区]")
        for ti, tb in enumerate(tables, 1):
            lines.append("")
            lines.append(f"### 表 {ti}")
            for row in tb.rows:
                cells = [clean(c.text.strip()) for c in row.cells]
                lines.append("| " + " | ".join(cells) + " |")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(lines), encoding="utf-8")
    print("WROTE", OUT)
    print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables))


if __name__ == "__main__":
    main()
