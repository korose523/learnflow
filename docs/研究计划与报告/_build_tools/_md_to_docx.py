# -*- coding: utf-8 -*-
"""Markdown -> Word (.docx) 转换器（确定性，无需 LLM）。
支持：标题(#~#####)、表格、围栏代码块、有序/无序列表(含嵌套)、
引用块(>)、水平线(---)、行内 **粗体**/*斜体*/`代码`/[链接](url)。
中/韩文分别设置正确的东亚字体（微软雅黑 / Malgun Gothic）。
"""
import io, os, re
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

EA_FONT = {"zh": "Microsoft YaHei", "kr": "Malgun Gothic"}
LAT_FONT = "Calibri"
CODE_FONT = "Consolas"
BODY_SIZE = 10.5
HEAD_SIZES = {1: 22, 2: 16, 3: 13.5, 4: 12, 5: 11}
TOC_TITLE = {"zh": "目录", "kr": "목차"}


def set_run_font(run, lang, bold=False, italic=False, code=False, size=None, color=None):
    run.font.name = CODE_FONT if code else LAT_FONT
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    ea = EA_FONT[lang]
    lat = CODE_FONT if code else LAT_FONT
    rfonts.set(qn("w:ascii"), lat)
    rfonts.set(qn("w:hAnsi"), lat)
    rfonts.set(qn("w:eastAsia"), ea)
    rfonts.set(qn("w:cs"), ea)


INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\)")


def populate_inline(paragraph, text, lang, size=None, base_bold=False, base_italic=False):
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            r = paragraph.add_run(text[pos:m.start()])
            set_run_font(r, lang, bold=base_bold, italic=base_italic, size=size)
        if m.group(1) is not None:
            r = paragraph.add_run(m.group(1))
            set_run_font(r, lang, bold=True, italic=base_italic, size=size)
        elif m.group(2) is not None:
            r = paragraph.add_run(m.group(2))
            set_run_font(r, lang, bold=base_bold, italic=True, size=size)
        elif m.group(3) is not None:
            r = paragraph.add_run(m.group(3))
            set_run_font(r, lang, bold=base_bold, italic=base_italic, code=True, size=size)
        elif m.group(4) is not None:
            r = paragraph.add_run("%s (%s)" % (m.group(4), m.group(5)))
            set_run_font(r, lang, bold=base_bold, italic=base_italic, size=size)
        pos = m.end()
    if pos < len(text):
        r = paragraph.add_run(text[pos:])
        set_run_font(r, lang, bold=base_bold, italic=base_italic, size=size)


def add_bottom_border(paragraph):
    ppr = paragraph._element.get_or_add_pPr()
    pbr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "999999")
    pbr.append(bottom)
    ppr.append(pbr)


def add_left_border(paragraph):
    ppr = paragraph._element.get_or_add_pPr()
    pbr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "12")
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), "888888")
    pbr.append(left)
    ppr.append(pbr)


def set_cell_shading(cell, color="DDDDDD"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def set_no_wrap(paragraph):
    ppr = paragraph._element.get_or_add_pPr()
    ww = ppr.find(qn("w:wordWrap"))
    if ww is None:
        ww = OxmlElement("w:wordWrap")
        ppr.append(ww)
    ww.set(qn("w:val"), "false")


def set_para_shading(paragraph, color="F2F2F2"):
    ppr = paragraph._element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    ppr.append(shd)


def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "888888")
        borders.append(e)
    tblPr.append(borders)


def parse_table(rows):
    def split_row(line):
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]

    header = split_row(rows[0])
    alignments = ["left"] * len(header)
    data_start = 1
    if len(rows) > 1 and re.match(r"^[\s|:\-]+$", rows[1]) and "-" in rows[1]:
        sep = split_row(rows[1])
        for i, c in enumerate(sep):
            if c.startswith(":") and c.endswith(":"):
                alignments[i] = "center"
            elif c.endswith(":"):
                alignments[i] = "right"
            elif c.startswith(":"):
                alignments[i] = "left"
        data_start = 2
    data = [split_row(r) for r in rows[data_start:]]
    return header, alignments, data


def prescan_headings(lines):
    out = []
    for ln in lines:
        mm = re.match(r"^(#{2,3})\s+(.*)$", ln)
        if mm:
            out.append((len(mm.group(1)), mm.group(2).strip()))
    return out


def build_docx(md_path, docx_path, lang):
    text = io.open(md_path, "r", encoding="utf-8").read()
    lines = text.split("\n")
    all_headings = prescan_headings(lines)

    doc = Document()

    # 文档属性（审阅意见 §2.5）：此前作者/修改者字段为空，易被读成"匿名署名"。
    # 此处显式写入作者与标题，避免生成方式造成的属性缺失被误读。
    cp = doc.core_properties
    cp.author = "Zexiao Weng"
    cp.last_modified_by = "Zexiao Weng"
    cp.title = os.path.splitext(os.path.basename(md_path))[0]
    cp.subject = ("博士学位论文研究计划书 / 研究进展报告 — 适应性学习中难度的可测量化与可治理化"
                  if lang == "zh" else
                  "박사학위논문 연구계획서 / 연구진행보고서 — 적응형 학습에서 난이도의 측정가능화와 거버넌스화")
    cp.comments = ("LearnFlow artifact 配套文档；数字口径由 learnflow-backend/scripts/ 下门禁脚本复算。"
                   "本文件由 Markdown 源经 _build_tools/_md_to_docx.py 确定性生成。")

    sec = doc.sections[0]
    sec.page_width = Pt(842)
    sec.page_height = Pt(1191)
    for mg in (sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin):
        mg.width = Pt(70)

    normal = doc.styles["Normal"]
    normal.font.name = LAT_FONT
    normal.font.size = Pt(BODY_SIZE)
    npr = normal.element.get_or_add_rPr()
    nf = npr.find(qn("w:rFonts"))
    if nf is None:
        nf = OxmlElement("w:rFonts")
        npr.append(nf)
    nf.set(qn("w:ascii"), LAT_FONT)
    nf.set(qn("w:hAnsi"), LAT_FONT)
    nf.set(qn("w:eastAsia"), EA_FONT[lang])
    nf.set(qn("w:cs"), EA_FONT[lang])

    toc_inserted = [False]
    first_h1_done = [False]
    first_h2_seen = [False]

    def ensure_toc():
        if toc_inserted[0]:
            return
        toc_inserted[0] = True
        t = doc.add_paragraph()
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = t.add_run(TOC_TITLE[lang])
        set_run_font(r, lang, bold=True, size=15)
        for lvl, htext in all_headings:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18 if lvl == 2 else 36)
            p.paragraph_format.space_after = Pt(2)
            populate_inline(p, htext, lang, size=10.5)
        doc.add_paragraph()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(12)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            set_para_shading(p)
            set_no_wrap(p)
            for j, cl in enumerate(code_lines):
                run = p.add_run(cl if j == 0 else "\n" + cl)
                set_run_font(run, lang, code=True, size=9)
            continue

        if stripped.startswith("|") and i + 1 < n and lines[i + 1].strip().startswith("|"):
            tbl_rows = []
            while i < n and lines[i].strip().startswith("|"):
                tbl_rows.append(lines[i])
                i += 1
            header, aligns, data = parse_table(tbl_rows)
            t = doc.add_table(rows=1, cols=max(len(header), 1))
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            set_table_borders(t)
            hdr = t.rows[0].cells
            for c, htext in enumerate(header):
                hdr[c].paragraphs[0].text = ""
                populate_inline(hdr[c].paragraphs[0], htext, lang, size=9.5)
                for rr in hdr[c].paragraphs[0].runs:
                    rr.font.bold = True
                set_cell_shading(hdr[c], "DDDDDD")
                if aligns[c] == "center":
                    hdr[c].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif aligns[c] == "right":
                    hdr[c].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for drow in data:
                cells = t.add_row().cells
                for c, ctext in enumerate(drow):
                    cells[c].paragraphs[0].text = ""
                    populate_inline(cells[c].paragraphs[0], ctext, lang, size=9.5)
                    if aligns[c] == "center":
                        cells[c].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    elif aligns[c] == "right":
                        cells[c].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            doc.add_paragraph()
            continue

        if stripped in ("---", "***", "___") and set(stripped) == set(stripped[0]):
            i += 1
            hr = doc.add_paragraph()
            add_bottom_border(hr)
            hr.paragraph_format.space_after = Pt(2)
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            htext = m.group(2).strip()
            if level == 1 and not first_h1_done[0]:
                first_h1_done[0] = True
                p = doc.add_paragraph(style="Title")
                populate_inline(p, htext, lang, size=HEAD_SIZES[1])
                doc.add_paragraph()
                i += 1
                continue
            if level >= 2 and not first_h2_seen[0]:
                first_h2_seen[0] = True
                ensure_toc()
            style_map = {2: "Heading 1", 3: "Heading 2", 4: "Heading 3", 5: "Heading 4"}
            p = doc.add_paragraph(style=style_map.get(level, "Heading 4"))
            sz = HEAD_SIZES.get(level, 11)
            populate_inline(p, htext, lang, size=sz)
            p.paragraph_format.space_before = Pt(10 if level <= 2 else 6)
            p.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        if stripped.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            qp = doc.add_paragraph()
            qp.paragraph_format.left_indent = Pt(18)
            qp.paragraph_format.space_before = Pt(2)
            qp.paragraph_format.space_after = Pt(2)
            add_left_border(qp)
            full = " ".join(quote_lines)
            populate_inline(qp, full, lang, size=9.5)
            for rr in qp.runs:
                rr.font.italic = True
                rr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            continue

        list_m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if list_m:
            list_block = []
            while i < n:
                lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not lm:
                    if lines[i].strip() == "":
                        break
                    if list_block:
                        list_block[-1] = (list_block[-1][0], list_block[-1][1],
                                          list_block[-1][2] + " " + lines[i].strip())
                        i += 1
                        continue
                    break
                indent = len(lm.group(1))
                marker = lm.group(2)
                content = lm.group(3).strip()
                list_block.append((indent, marker, content))
                i += 1
            for indent, marker, content in list_block:
                lvl = indent // 2
                if re.match(r"\d+\.", marker):
                    style = "List Number" if lvl == 0 else "List Number %d" % min(lvl + 1, 3)
                else:
                    style = "List Bullet" if lvl == 0 else "List Bullet %d" % min(lvl + 1, 3)
                p = doc.add_paragraph(style=style)
                p.paragraph_format.space_after = Pt(2)
                populate_inline(p, content, lang, size=10.5)
            continue

        if stripped == "":
            i += 1
            continue

        para_lines = [stripped]
        i += 1
        while i < n and lines[i].strip() != "" and not re.match(r"^(#{1,6})\s", lines[i]) \
                and not lines[i].strip().startswith("|") and not lines[i].strip().startswith(">") \
                and not lines[i].strip().startswith("```") and not re.match(r"^(\s*)([-*]|\d+\.)\s", lines[i]) \
                and lines[i].strip() not in ("---", "***", "___"):
            para_lines.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        populate_inline(p, " ".join(para_lines), lang, size=BODY_SIZE)
        p.paragraph_format.space_after = Pt(6)

    doc.save(docx_path)
    return len(doc.paragraphs), len(doc.tables)


def main():
    base = r"E:\learnflow\docs\研究计划与报告"
    out_dir = r"E:\learnflow\docs"
    # 2026-10-03: 中文版计划/报告已合并入 docs/LearnFlow_研究总档.md 第一/二部，
    # 源 md 不再单独存在；韩文版仍是独立文件。中文版改为从总档按部抽取后构建。
    MASTER = os.path.join(out_dir, "LearnFlow_研究总档.md")
    jobs = [
        (r"@MASTER:第一部 · 研究计划", "研究计划_中文版.docx", "zh"),
        (r"@MASTER:第三部 · 研究计划（韩文版）", "研究计划_韩文版.docx", "kr"),
        (r"@MASTER:第二部 · 研究进展报告", "研究报告_中文版.docx", "zh"),
        (r"@MASTER:第四部 · 研究进展报告（韩文版）", "研究报告_韩文版.docx", "kr"),
    ]
    log = []
    tmpdir = os.path.join(out_dir, "_master_extract")
    os.makedirs(tmpdir, exist_ok=True)
    for src, dst, lang in jobs:
        if src.startswith("@MASTER:"):
            part = src.split(":", 1)[1]
            sp = os.path.join(tmpdir, dst.replace(".docx", ".md"))
            extract_master_part(MASTER, part, sp)
        else:
            sp = os.path.join(base, src)
        dp = os.path.join(out_dir, dst)
        try:
            np_, nt_ = build_docx(sp, dp, lang)
            log.append("OK  %s -> %s  (段落=%d, 表格=%d)" % (src, dst, np_, nt_))
        except Exception as e:
            log.append("ERR %s : %s" % (src, repr(e)))
    io.open(r"E:\learnflow\_docx_build.txt", "w", encoding="utf-8", newline="").write("\n".join(log))
    print("\n".join(log))


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────────────────────────────────────
# 2026-10-03: 从《LearnFlow_研究总档.md》抽取指定部为独立 md（供 docx 构建）
# ─────────────────────────────────────────────────────────────────────────────
_PART_RE_CACHE = {}


def extract_master_part(master_path, part_title, out_path):
    """把总档中 `## <部名>` 到下一个 `## ` 之间的内容抽成独立 md。

    总档的部标题形如 `## 第一部 · 研究计划`；抽取时保留部标题本身，
    使 docx 产物仍带有可识别的章节名。
    """
    import re as _re
    with open(master_path, encoding="utf-8") as fh:
        text = fh.read()
    pat = _re.compile(r"^## " + _re.escape(part_title) + r"\s*$.*?(?=^## |\Z)",
                      _re.MULTILINE | _re.DOTALL)
    m = pat.search(text)
    if not m:
        raise SystemExit("ERROR: 总档中未找到部标题: %s" % part_title)
    body = m.group(0)
    # 去掉注入的来源说明块（> **来源** … 及其后的空行）
    # 去掉注入的来源说明块（以 '> **来源**' 开头的一组连续引用行）
    lines = body.splitlines()
    # 跳过合档注入的元信息：部标题行 + 连续的 '>' 引用行 + 空行
    i = 0
    if i < len(lines) and lines[i].startswith("## "):
        i += 1
    while i < len(lines) and (lines[i].startswith(">") or not lines[i].strip()):
        i += 1
    lines = lines[i:]
    # 还原大标题层级：合档时降了两级（# -> ###），此处把首个标题还原为 '# '
    for j, ln in enumerate(lines):
        if ln.lstrip("#").strip():
            m = _re.match(r"^(#{3,6})\s+(.*)$", ln)
            if m:
                lines[j] = "# " + m.group(2)
            break
    body = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
    return out_path
