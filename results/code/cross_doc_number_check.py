# -*- coding: utf-8 -*-
"""跨文档数字互校（审阅 2026-09-29 §2.1 ③）。

背景：导师指出 verify_asset_numbers.py --doc-check 只读取
docs/LearnFlow_研究总档.md（第五部·期刊论文拆分方案） 一份，计划书·报告·四篇稿件都不在核对范围内，
因此"门禁通过不等于文档正确"。本脚本把提交件的数字汇成一张表相互核对。

用法：
    python results/code/cross_doc_number_check.py            # 打印矩阵
    python results/code/cross_doc_number_check.py --json      # 另存 JSON
    python results/code/cross_doc_number_check.py --md        # 另存 Markdown 表

判定口径：
  * CUR   = 现行值，直接接受。
  * LEGACY= 历史/基线/中间值，**只有同行（±ANNO 字符）出现标注词时才接受**，否则报警。
  * 任一项出现未标注的 LEGACY 值 → 退出码 1（供 CI 使用）。

只做文本核对，不修改任何文档。
"""
from __future__ import annotations
import io, os, re, sys, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANNO = 80

# 标注词：出现即视为"已注明为历史值"
ANNO_WORDS = [
    "基线", "基准", "中间值", "改动前", "변경 전", "기준선", "중간값", "변경전",
    "历史", "旧值", "曾为", "原本", "이전", "과거", "레거시", "封存", "审计时点",
    "opt-in", "路线 A", "경로 A", "不作为结果", "非现行", "不再使用",
    # 迁移/漂移语境：出现即视为"由旧值到新值"的记述，不算裸用旧值
    "→", "->", "=>", "升至", "增至", "增加到", "漂移", "复算", "재계산",
    "하드코딩", "등록표", "硬编码", "登记表", "基础上", "增补", "보강",
]

# ---------------------------------------------------------------- 核对项
# (标签, 上下文正则, 现行值集合, 历史值集合)
CHECKS = [
    ("全量测试数",
     r"(?:全量测试|전체 테스트|tests_collected|tests?\s*passed)[^\n]{0,60}?\b(920|934|936|972)\b",
     {"936"}, {"920", "934", "972"}),

    ("后端 LOC",
     r"(?:python_loc|后端[^\n]{0,10}行|라인)[^\n]{0,40}?\b(25,389|25,795|26,937)\b",
     {"25,795"}, {"25,389", "26,937"}),

    ("后端文件数",
     r"(?:后端|파일)[^\n]{0,20}?\b(88|92)\b[^\n]{0,6}(?:个|개)?\s*(?:文件|파일)?",
     {"88"}, {"92"}),

    ("测试文件数",
     r"\b(54)\b\s*(?:个|개)?\s*(?:测试文件|테스트 파일)",
     {"54"}, set()),

    ("效果生产者",
     r"(?:效果生产者|效果生产|효과 생산자|effect producers?)[^\n]{0,60}?\b(2|14|16|54)\b",
     {"2", "14", "54", "16"}, set()),

    ("成熟度三元组",
     r"(?:complete|partial|placeholder|成熟度)[^\n]{0,60}?\b(9|37|8)\b",
     {"9", "37", "8"}, set()),

    ("滑窗总数",
     r"\b(286,150)\b", {"286,150"}, set()),

    ("bootstrap 学生数",
     r"(?:n_users_used|实际使用[^\n]{0,6}学生|사용 학생)[^\n]{0,40}?\b(2,314|4,217)\b",
     {"2,314", "4,217"}, set()),

    ("众数 0.25 窗数",
     r"0\.25[^\n]{0,20}?(30,899)", {"30,899"}, set()),
    ("0.20 窗数",
     r"0\.20[^\n]{0,20}?\b(30,061|30,074|30,088)\b", {"30,061"}, {"30,074", "30,088"}),
    ("0.15 窗数",
     r"0\.15[^\n]{0,20}?\b(26,151|26,138)\b", {"26,151"}, {"26,138"}),

    ("0.15~0.35 占比",
     r"\b(49\.3)\s*%", {"49.3"}, set()),

    ("DBE 题数",
     r"(?:DBE[^\n]{0,10}|教师标签[^\n]{0,10}|전문가 라벨)\D{0,12}\b(212)\b",
     {"212"}, set()),

    ("A1 Junyi 题数",
     r"(?:A1|Junyi)[^\n]{0,30}?\b(1,274)\b", {"1,274"}, set()),

    ("A1 ρ(成功率/融合)",
     r"\b(0\.963|0\.892)\b", {"0.963", "0.892"}, set()),

    ("A2 ρ(融合/成功率)",
     r"(?:A2|等权融合)[^\n]{0,40}?\b(0\.205|0\.220)\b", {"0.205", "0.220"}, set()),

    ("O4 等权融合 ρ",
     r"(?:O4|第 6 节)[^\n]{0,40}?\b(0\.2899)\b", {"0.2899"}, set()),

    ("M3 最大 ρ",
     r"(?:最大|최대|max)[^\n]{0,30}?\b(0\.2430|0\.2521)\b", {"0.2521"}, {"0.2430"}),

    ("M3 矩阵格数",
     r"\b(7|11)\b[^\n]{0,10}(?:个|개)?[^\n]{0,6}(?:EVALUATED|单元格|칸)",
     {"11"}, {"7"}),

    ("注册表指纹",
     r"\b(ee1a49be5732)\b", {"ee1a49be5732"}, set()),

    ("M2 审计 tag",
     r"\b(audit-m2-20260911)\b", {"audit-m2-20260911"}, set()),
]

DOCS = [
    ("计划书·中", "docs/LearnFlow_研究总档.md"),
    ("计划书·韩", "docs/LearnFlow_研究总档.md"),
    ("报告·中", "docs/LearnFlow_研究总档.md"),
    ("报告·韩", "docs/LearnFlow_研究总档.md"),
    ("README", "README.md"),
    ("CITATION", "CITATION.cff"),
    (".zenodo", ".zenodo.json"),
]


def collect_docs():
    out = list(DOCS)
    for pat, label in [
        ("docs/M1_*完整稿.md", "M1"),
        ("docs/M2_*完整稿.md", "M2"),
        ("docs/M3_*完整稿.md", "M3"),
        ("docs/M4_*完整稿.md", "M4"),
    ]:
        hits = sorted(glob.glob(os.path.join(ROOT, pat)))
        for h in hits:
            out.append((label + ("" if len(hits) == 1 else "·" + os.path.basename(h)[:3]),
                        os.path.relpath(h, ROOT)))
    return out


def annotated(line: str, pos: int) -> bool:
    lo = max(0, pos - ANNO)
    hi = min(len(line), pos + ANNO)
    seg = line[lo:hi]
    return any(w in seg for w in ANNO_WORDS)


def main():
    docs = collect_docs()
    present = [(lab, os.path.join(ROOT, rel)) for lab, rel in docs if os.path.exists(os.path.join(ROOT, rel))]
    texts = {}
    for lab, path in present:
        texts[lab] = io.open(path, encoding="utf-8", errors="ignore").read()

    rows, alerts = [], []
    for label, ctx, cur, legacy in CHECKS:
        rx = re.compile(ctx)
        per = {}
        for lab, txt in texts.items():
            vals = set()
            for m in rx.finditer(txt):
                v = m.group(1)
                if v in legacy and not annotated(txt, m.start()):
                    alerts.append((lab, label, v, txt[max(0, m.start() - 40):m.start() + 40].replace("\n", " ")))
                vals.add(v)
            per[lab] = vals
        rows.append((label, cur, per))

    labs = [lab for lab, _ in present]
    print("\n=== 跨文档数字互校矩阵（审阅 §2.1 ③）===\n")
    hdr = "| 量 | 现行值 | " + " | ".join(labs) + " |"
    print(hdr)
    print("|" + "---|" * (len(labs) + 2))
    for label, cur, per in rows:
        cells = []
        for lab in labs:
            v = per.get(lab) or set()
            cells.append(", ".join(sorted(v)) if v else "—")
        print("| %s | %s | %s |" % (label, ", ".join(sorted(cur)), " | ".join(cells)))

    print("\n=== 未标注的历史值（须人工确认）===")
    if not alerts:
        print("无。")
    else:
        for lab, key, v, snip in alerts:
            print("  [%s] %s = %s   …%s…" % (lab, key, v, snip.strip()))

    if "--json" in sys.argv:
        io.open(os.path.join(ROOT, "results/cross_doc_number_matrix.json"), "w", encoding="utf-8").write(
            json.dumps({"docs": labs,
                        "rows": [{"key": k, "current": sorted(c), "found": {d: sorted(p.get(d, [])) for d in labs}}
                                 for k, c, p in rows],
                        "alerts": [{"doc": a, "key": b, "value": c, "snippet": d} for a, b, c, d in alerts]},
                       ensure_ascii=False, indent=2))
        print("\nwrote results/cross_doc_number_matrix.json")

    if "--md" in sys.argv:
        out = ["# 跨文档数字互校表（审阅 §2.1 ③）\n", hdr, "|" + "---|" * (len(labs) + 2)]
        for label, cur, per in rows:
            cells = [(", ".join(sorted(per.get(l, set()))) or "—") for l in labs]
            out.append("| %s | %s | %s |" % (label, ", ".join(sorted(cur)), " | ".join(cells)))
        out.append("\n## 未标注的历史值\n")
        out += ["- [%s] %s = %s — …%s…" % (a, b, c, d.strip()) for a, b, c, d in alerts] or ["- 无"]
        io.open(os.path.join(ROOT, "results/cross_doc_number_matrix.md"), "w", encoding="utf-8").write("\n".join(out))
        print("wrote results/cross_doc_number_matrix.md")

    print("\nchecked=%d  docs=%d  alerts=%d" % (len(CHECKS), len(present), len(alerts)))
    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
