# -*- coding: utf-8 -*-
import io, os
from docx import Document
from docx.oxml.ns import qn

BASE = r"E:\learnflow\docs"
checks = []
for fn in ["研究计划_中文版.docx", "研究计划_韩文版.docx", "研究报告_中文版.docx", "研究报告_韩文版.docx"]:
    doc = Document(os.path.join(BASE, fn))
    # 找包含代码块图的段落
    code_p = None
    for p in doc.paragraphs:
        if "链 4 治理" in p.text or "RQ4" in p.text and "┌" in p.text:
            code_p = p
            break
    nowrap = None
    diagram_ok = False
    if code_p is not None:
        ppr = code_p._element.find(qn("w:pPr"))
        if ppr is not None:
            ww = ppr.find(qn("w:wordWrap"))
            if ww is not None:
                nowrap = ww.get(qn("w:val"))
        full = code_p.text
        diagram_ok = ("研究依托系统 LearnFlow" in full) and ("链 1 测量" in full) and ("────────" in full)
    checks.append("=== %s ===" % fn)
    checks.append("  代码块段落找到=%s  wordWrap=%s  图完整=%s" % (
        code_p is not None, nowrap, diagram_ok))

io.open(r"E:\learnflow\_validate_code.txt", "w", encoding="utf-8", newline="").write("\n".join(checks))
print("\n".join(checks))
