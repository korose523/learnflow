# -*- coding: utf-8 -*-
"""Generic ENGLISH manuscript Markdown -> academic-paper HTML converter.

Parametrized variant of md2academic_en.py:
  --src   input markdown (English)
  --out   output html
  --title document title (for <title> and pdf metadata)
  --lang  html lang attribute (default en)

Handles: Latin fonts (Times New Roman), English caption detection
(Table/Figure), author-block / affiliation / AI-disclosure handling
(centered, no indent), English Abstract/References detection, Contents
TOC. Output feeds the same html_to_docx (S3) converter.
"""
import re
import html as htmlmod
import argparse


def inline(text):
    s = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    s = re.sub(r"\[\^([^\]]+)\]", r"<sup>[\1]</sup>", s)
    s = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def split_long(text, limit=900):
    if len(text) <= limit:
        return [text]
    parts = re.split(r"(?<=[。！？；.!?])\s+", text)
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) <= limit:
            cur += p
        else:
            if cur:
                chunks.append(cur)
            if len(p) > limit:
                for i in range(0, len(p), limit):
                    chunks.append(p[i:i + limit])
                cur = ""
            else:
                cur = p
    if cur:
        chunks.append(cur)
    return chunks


def para_html(raw, cls=None, indent=True, lead=None):
    out = []
    for ch in split_long(raw):
        c = ch
        if lead:
            c = lead + c
        style = ""
        if cls:
            style = ' class="%s"' % cls
        attrs = style
        out.append("<p%s>%s</p>" % (attrs, inline(c)))
    return "\n".join(out)


def is_special(line):
    s = line.strip()
    if s.startswith("#"):
        return True
    if s.startswith(">"):
        return True
    if s.startswith("|") and s.endswith("|"):
        return True
    if s in ("---", "***", "___"):
        return True
    if re.match(r"^[-*]\s", s) or re.match(r"^\d+\.\s", s):
        return True
    return False


def parse_blocks(lines):
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if s == "":
            i += 1
            continue
        if s in ("---", "***", "___"):
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append({"t": "code", "lines": buf})
            continue
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            blocks.append({"t": "h", "lvl": lvl, "text": s[lvl:].strip()})
            i += 1
            continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                content = lines[i].strip()[1:].strip()
                if content != "":
                    buf.append(content)
                i += 1
            blocks.append({"t": "quote", "paras": buf})
            continue
        if s.startswith("|") and s.endswith("|"):
            buf = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                buf.append(lines[i].strip())
                i += 1
            blocks.append({"t": "table", "rows": buf})
            continue
        if re.match(r"^[-*]\s", s) or re.match(r"^\d+\.\s", s):
            buf = []
            while i < n and (re.match(r"^[-*]\s", lines[i].strip())
                             or re.match(r"^\d+\.\s", lines[i].strip())
                             or (lines[i].startswith(" ") and buf)):
                buf.append(lines[i].rstrip())
                i += 1
            blocks.append({"t": "list", "lines": buf})
            continue
        buf = []
        while i < n and lines[i].strip() != "" and not is_special(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        blocks.append({"t": "p", "text": " ".join(buf)})
    return blocks


def strip_star(t):
    return t.strip().lstrip("*").rstrip("*").strip()


def is_caption(t):
    c = strip_star(t)
    return ((c.startswith("表") or c.startswith("图")
             or c.startswith("Table") or c.startswith("Figure"))
            and len(c) < 160)


def parse_table(rows):
    data = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        data.append(cells)
    sep_idx = None
    for idx, cells in enumerate(data):
        joined = "".join(cells)
        if joined != "" and all(ch in "-|: " for ch in joined) and set(joined) & set("-"):
            sep_idx = idx
            break
    if sep_idx is None:
        header = data[0]
        body = data[1:]
    else:
        header = data[sep_idx - 1] if sep_idx - 1 >= 0 else data[0]
        body = data[sep_idx + 1:]
    html = ['<table class="three-line-table">']
    html.append("<thead><tr>")
    for c in header:
        html.append("<th>%s</th>" % inline(c))
    html.append("</tr></thead>")
    html.append("<tbody>")
    for r in body:
        html.append("<tr>")
        for c in r:
            html.append("<td>%s</td>" % inline(c))
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)


def render_list(lines):
    first = lines[0].strip()
    ordered = re.match(r"^\d+\.\s", first) is not None
    tag = "ol" if ordered else "ul"
    out = ["<%s>" % tag]
    for ln in lines:
        m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", ln.strip())
        if m:
            out.append("<li>%s</li>" % inline(m.group(1)))
        else:
            out.append("<li>%s</li>" % inline(ln.strip()))
    out.append("</%s>" % tag)
    return "\n".join(out)


STYLE = """<style>
  @page { margin: 2.5cm; @bottom-center { content: counter(page); } }
  :root {
    --typography-fontFamily-heading: "Times New Roman", serif;
    --typography-fontFamily-body: "Times New Roman", serif;
    --typography-fontFamily-bodyLatin: "Times New Roman", serif;
    --typography-fontFamily-caption: "Times New Roman", serif;
    --typography-fontFamily-code: "Courier New", Consolas, monospace;
    --typography-fontSize-title: 18pt;
    --typography-fontSize-h1: 15pt;
    --typography-fontSize-h2: 14pt;
    --typography-fontSize-h3: 12pt;
    --typography-fontSize-body: 11pt;
    --typography-fontSize-abstract: 10.5pt;
    --typography-fontSize-caption: 9.5pt;
    --typography-fontSize-footnote: 9pt;
    --typography-lineHeight-body: 1.5;
    --typography-lineHeight-abstract: 1.25;
    --typography-lineHeight-heading: 1.5;
    --typography-fontWeight-heading: bold;
    --typography-fontWeight-body: normal;
    --color-primary: #000000;
    --color-text: #000000;
    --color-heading: #000000;
    --color-link: #0000EE;
    --color-tableHeaderBg: #f0f0f0;
    --color-tableBorder: #000000;
    --color-background: #ffffff;
    --color-info: #01579b;
    --color-muted: #666666;
    --spacing-paragraph: 0.5em;
    --spacing-paragraphAfter: 0.5em;
    --spacing-indent: 1.5em;
    --spacing-sectionGap: 1.2em;
    --spacing-abstractIndent: 3em;
    --sp-toc-indent: 1.5em;
    --sp-tight: 0.3em;
    --sp-list-indent: 2em;
    --layout-marginTop: 2.5cm;
    --layout-marginBottom: 2.5cm;
    --layout-marginLeft: 2.5cm;
    --layout-marginRight: 2.5cm;
    --layout-pageSize: A4;
    --page-content-width: 16.0cm;
    --fs-title: var(--typography-fontSize-title);
    --fs-h1: var(--typography-fontSize-h1);
    --fs-h2: var(--typography-fontSize-h2);
    --fs-h3: var(--typography-fontSize-h3);
    --fs-body: var(--typography-fontSize-body);
    --fs-abstract: var(--typography-fontSize-abstract);
    --fs-caption: var(--typography-fontSize-caption);
    --fs-footnote: var(--typography-fontSize-footnote);
    --ff-heading: var(--typography-fontFamily-heading);
    --ff-body: var(--typography-fontFamily-body);
    --ff-body-latin: var(--typography-fontFamily-bodyLatin);
    --ff-caption: var(--typography-fontFamily-caption);
    --ff-code: var(--typography-fontFamily-code);
    --lh-body: var(--typography-lineHeight-body);
    --lh-abstract: var(--typography-lineHeight-abstract);
    --lh-heading: var(--typography-lineHeight-heading);
    --fw-bold: var(--typography-fontWeight-heading);
    --fw-normal: var(--typography-fontWeight-body);
    --clr-primary: var(--color-primary);
    --clr-text: var(--color-text);
    --clr-heading: var(--color-heading);
    --clr-link: var(--color-link);
    --clr-tableHeaderBg: var(--color-tableHeaderBg);
    --clr-tableBorder: var(--color-tableBorder);
    --clr-bg: var(--color-background);
    --clr-info: var(--color-info);
    --clr-muted: var(--color-muted);
    --sp-paragraph: var(--spacing-paragraph);
    --sp-paragraphAfter: var(--spacing-paragraphAfter);
    --sp-indent: var(--spacing-indent);
    --sp-sectionGap: var(--spacing-sectionGap);
    --sp-abstractIndent: var(--spacing-abstractIndent);
    --margin-page-top: var(--layout-marginTop);
    --margin-page-bottom: var(--layout-marginBottom);
    --margin-page-left: var(--layout-marginLeft);
    --margin-page-right: var(--layout-marginRight);
    --page-size: var(--layout-pageSize);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--ff-body);
    font-size: var(--fs-body);
    line-height: var(--lh-body);
    color: var(--clr-text);
    background: var(--clr-bg);
    padding: var(--margin-page-top) var(--margin-page-right) var(--margin-page-bottom) var(--margin-page-left);
    max-width: var(--page-content-width);
    margin-left: auto; margin-right: auto;
  }
  h1, h2, h3, h4 { font-family: var(--ff-heading); font-weight: var(--fw-bold); color: var(--clr-heading); }
  h1 { font-size: var(--fs-h1); margin-top: var(--sp-sectionGap); margin-bottom: var(--sp-paragraph); text-align: center; }
  h2 { font-size: var(--fs-h2); margin-top: var(--sp-sectionGap); margin-bottom: var(--sp-paragraph); }
  h3 { font-size: var(--fs-h3); margin-top: var(--sp-paragraph); margin-bottom: var(--sp-paragraph); }
  h4 { font-size: var(--fs-body); margin-top: var(--sp-paragraph); margin-bottom: var(--sp-paragraph); }
  p { margin-bottom: var(--sp-paragraph); text-align: justify; text-indent: var(--sp-indent); }
  .doc-title { font-size: var(--fs-title); text-align: center; margin-top: var(--sp-sectionGap); margin-bottom: var(--sp-paragraph); }
  .subtitle { text-align: center; font-size: var(--fs-h3); font-style: italic; margin-top: var(--sp-paragraph); margin-bottom: var(--sp-sectionGap); text-indent: 0; }
  .subtitle-en { text-align: center; font-size: var(--fs-abstract); font-style: italic; color: var(--clr-muted); margin-top: var(--sp-paragraph); margin-bottom: var(--sp-sectionGap); text-indent: 0; }
  .author-line { text-align: center; text-indent: 0; margin-bottom: 0.2em; font-size: var(--fs-body); }
  .abstract { margin-top: var(--sp-sectionGap); margin-bottom: var(--sp-sectionGap); padding: var(--sp-paragraph); border-left: 3px solid var(--clr-info); }
  .abstract-heading { font-weight: var(--fw-bold); font-size: var(--fs-h3); margin-bottom: var(--sp-paragraph); text-indent: 0; }
  .abstract-text { font-size: var(--fs-abstract); line-height: var(--lh-abstract); text-indent: 0; margin-bottom: var(--sp-paragraph); }
  .keywords { font-size: var(--fs-abstract); margin-top: var(--sp-paragraph); text-indent: 0; }
  .frontmatter { border-left: 3px solid var(--clr-info); padding: var(--sp-paragraph); margin-bottom: var(--sp-sectionGap); }
  .frontmatter p { text-indent: 0; margin-bottom: var(--sp-paragraph); }
  .doc-toc { margin-top: var(--sp-sectionGap); margin-bottom: var(--sp-sectionGap); }
  .toc-title { font-weight: var(--fw-bold); text-align: center; font-size: var(--fs-h2); margin-bottom: var(--sp-paragraph); text-indent: 0; }
  .toc-list, .toc-list ol, .toc-list ul { list-style: none; list-style-type: none; padding-left: var(--sp-toc-indent); }
  .toc-list li { margin-bottom: var(--sp-tight); text-indent: 0; }
  .toc-list a { color: var(--clr-link); text-decoration: none; }
  .three-line-table { border-collapse: collapse; width: 100%; margin-top: var(--sp-paragraph); margin-bottom: var(--sp-paragraph); }
  .three-line-table caption { font-size: var(--fs-caption); margin-bottom: var(--sp-paragraph); text-align: center; }
  .three-line-table thead tr:first-child { border-top: 2px solid var(--clr-tableBorder); }
  .three-line-table thead tr:last-child { border-bottom: 1px solid var(--clr-tableBorder); }
  .three-line-table tbody tr:last-child { border-bottom: 2px solid var(--clr-tableBorder); }
  .three-line-table td, .three-line-table th { padding: var(--sp-paragraph) var(--sp-paragraph); text-align: left; font-size: var(--fs-body); }
  .three-line-table th { font-weight: var(--fw-bold); background: var(--clr-tableHeaderBg); }
  figure { margin: var(--sp-paragraph) 0; text-align: center; }
  figcaption { font-size: var(--fs-caption); color: var(--clr-muted); margin-top: var(--sp-paragraph); }
  blockquote { margin-bottom: var(--sp-paragraph); }
  .references { margin-top: var(--sp-sectionGap); }
  .reference-list { padding-left: var(--sp-list-indent); }
  .reference-item { margin-bottom: var(--sp-paragraph); font-size: var(--fs-caption); }
  code { font-family: var(--ff-code); font-size: var(--fs-body); }
  .code-block { font-family: var(--ff-code); font-size: var(--fs-caption); background: var(--clr-tableHeaderBg); padding: var(--sp-paragraph); margin-bottom: var(--sp-paragraph); white-space: pre-wrap; }
  ul, ol { margin-bottom: var(--sp-paragraph); padding-left: var(--sp-list-indent); }
  li { margin-bottom: var(--sp-paragraph); text-align: justify; }
  sup { font-size: var(--fs-footnote); }
</style>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--lang", default="en")
    args = ap.parse_args()

    with open(args.src, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    blocks = parse_blocks(lines)

    for i in range(1, len(blocks)):
        if blocks[i]["t"] == "table" and blocks[i - 1]["t"] == "p" and is_caption(blocks[i - 1]["text"]):
            blocks[i]["caption"] = strip_star(blocks[i - 1]["text"])
            blocks[i - 1]["suppress"] = True

    toc_items = []
    sec_counter = 0
    body = []
    in_abstract = False
    in_references = False
    toc_html = None
    title_done = False
    emitted_toc = False

    def emit_toc():
        if not toc_items:
            return ""
        parts = ['<nav class="doc-toc" aria-label="Contents">',
                 '<p class="toc-title">Contents</p>',
                 '<ol class="toc-list">']
        for cid, ctitle in toc_items:
            parts.append('<li><a href="#%s">%s</a></li>' % (cid, inline(ctitle)))
        parts.append("</ol></nav>")
        return "\n".join(parts)

    for idx, b in enumerate(blocks):
        t = b["t"]
        if t == "p":
            if b.get("suppress"):
                continue
            txt = b["text"]
            if txt.startswith("**English Title") or txt.startswith("English Title"):
                body.append('<p class="subtitle-en">%s</p>' % inline(txt))
                continue
            if (txt.startswith("Zexiao Weng") or "Youngsan University" in txt
                    or "Corresponding author" in txt or txt.startswith("AI-Assisted")):
                body.append(para_html(txt, cls="author-line"))
                continue
            if in_references:
                body.append("<li>%s</li>" % inline(txt))
                continue
            if in_abstract:
                body.append(para_html(txt, cls="abstract-text"))
            else:
                body.append(para_html(txt))
            continue
        if t == "h":
            lvl = b["lvl"]
            txt = b["text"]
            if lvl == 1:
                body.append('<h1 class="doc-title">%s</h1>' % inline(txt))
                title_done = True
                continue
            if lvl == 2:
                if txt in ("摘要", "Abstract"):
                    if not in_abstract:
                        if not emitted_toc:
                            body.append(emit_toc())
                            emitted_toc = True
                        body.append('<div class="abstract" aria-label="Abstract">')
                        in_abstract = True
                    body.append('<p class="abstract-heading">%s</p>' % inline(txt))
                    continue
                if in_abstract:
                    body.append("</div>")
                    in_abstract = False
                if in_references:
                    body.append("</ol></div>")
                    in_references = False
                if txt.startswith("——"):
                    body.append('<p class="subtitle">%s</p>' % inline(txt))
                    continue
                if txt.startswith("参考文献") or txt.startswith("Reference") or txt.startswith("References"):
                    in_references = True
                    body.append('<div class="references" aria-label="References">')
                    body.append('<h2>%s</h2>' % inline(txt))
                    body.append('<ol class="reference-list">')
                    continue
                sec_counter += 1
                cid = "section-%d" % sec_counter
                toc_items.append((cid, txt))
                body.append('<h2 id="%s">%s</h2>' % (cid, inline(txt)))
                continue
            if lvl == 3:
                body.append("<h3>%s</h3>" % inline(txt))
                continue
            if lvl == 4:
                body.append("<h4>%s</h4>" % inline(txt))
                continue
            body.append("<h%d>%s</h%d>" % (lvl, inline(txt), lvl))
            continue
        if t == "quote":
            parts = ['<blockquote class="frontmatter">']
            for para in b["paras"]:
                parts.append(para_html(para, lead="&nbsp;&nbsp;"))
            parts.append("</blockquote>")
            body.append("\n".join(parts))
            continue
        if t == "code":
            code = "\n".join(b["lines"])
            code = htmlmod.escape(code)
            body.append('<pre class="code-block"><code>%s</code></pre>' % code)
            continue
        if t == "list":
            if in_references:
                for ln in b["lines"]:
                    m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", ln.strip())
                    content = m.group(1) if m else ln.strip()
                    body.append("<li>%s</li>" % inline(content))
            else:
                body.append(render_list(b["lines"]))
            continue
        if t == "table":
            tbl = parse_table(b["rows"])
            if b.get("caption"):
                tbl = tbl.replace("<table class=\"three-line-table\">",
                                  '<table class="three-line-table"><caption>%s</caption>' % inline(b["caption"]), 1)
            body.append(tbl)
            continue

    if in_abstract:
        body.append("</div>")
    if in_references:
        body.append("</ol></div>")

    if not emitted_toc:
        body.insert(0, emit_toc())
        emitted_toc = True

    body_html = "\n".join(body)

    doc = """<!DOCTYPE html>
<html lang="%s">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="docx-page-size" content="A4">
<title>%s</title>
%s
</head>
<body>
<section role="body" data-page-restart="1">
%s
</section>
</body>
</html>""" % (args.lang, args.title, STYLE, body_html)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("WROTE", args.out, "bytes=", len(doc.encode("utf-8")))
    print("toc_items=", len(toc_items))


if __name__ == "__main__":
    main()
