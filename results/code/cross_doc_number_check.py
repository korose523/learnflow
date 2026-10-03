# -*- coding: utf-8 -*-
"""跨文档数字互校（审阅 2026-09-29 §2.1 ③）。

背景：导师指出 verify_asset_numbers.py --doc-check 只读取
docs/LearnFlow_期刊论文拆分方案.md 一份，计划书·报告·四篇稿件都不在核对范围内，
因此"门禁通过不等于文档正确"。本脚本把提交件的数字汇成一张表相互核对。

与姊妹门禁的分工（两个门禁互补，作用域不同，勿混为一谈）：
    * 本脚本（results/code/cross_doc_number_check.py）—— **宽口径**，21 项指标 × 11 份文档，
      额外覆盖论文内部结果量（A1/A2 ρ、滑窗频数、DBE 题数、M3 最大 ρ、矩阵格数等）。
    * scripts/verify_cross_doc_numbers.py —— **严口径**，12 项资产类指标 × 7 份文档，
      STRICT 分歧即 exit 1，且区分 STRICT 与 DRIFT（审计时点漂移）。
    两者都须为 exit 0。任一报警都不得以"另一个门禁 PASS"为由忽略。

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
#
# 2026-10-02 边界修正：原先数字两侧用 `\b`，但 Python 的 `\w` 含谚文/汉字，
# 因此「972건」「25,795행」「54개」这类**韩文/中文后缀紧邻数字**的写法下
# `\b` 两侧都不成立，整条规则静默失效——韩文计划书长期只显示 934 而漏掉 972
# 就是由此而来（由 ko-sync 实测发现）。
#
# 两侧边界因此改为「禁 ASCII 字母/数字/下划线/点/千分位逗号，但**放行 CJK 后缀**」：
#   * 972건 / 54개 / 25,795행  → 后接谚文，NE 放行 → 正确命中
#   * qwen3:1.7b 单元格        → 7 前后是 "." 与 ASCII 字母 b，NB/NE 双双拦下
#     （第一版曾把它放宽成 (?<![\d,])…(?![\d,])，结果 1.7b 的 7 被误捕成
#      「M3 矩阵格数 = 7」，故收紧了 ASCII 部分。）
NB = r"(?<![\dA-Za-z_.])"   # number begin
NE = r"(?![\dA-Za-z_])"     # number end
CHECKS = [
    ("全量测试数",
     r"(?:全量测试|전체 테스트|tests_collected|tests?\s*passed)[^\n]{0,60}?" + NB + r"(920|934|936|972)" + NE,
     {"972"}, {"920", "934", "936"}),

    # 2026-10-02 补齐韩文上下文前缀：原先只写 `라인`，漏掉韩文实际使用的三种形态，
    # 导致韩文报告里的 26,782 全部漏显（由 ko-sync 人工核验发现：韩文报告 5 处、
    # 韩文计划 3 处 26,782，与中文一一配对却只剩 25,389 被捕获）。实测三种形态：
    #   | 백엔드 Python | **92개 파일 / 26,782행** |
    #   | 백엔드 코드 행수 | 26,782 |
    #   …실측값 **26,782행 / 59개 서비스 모듈…
    ("后端 LOC",
     r"(?:python_loc|后端[^\n]{0,10}行|라인|백엔드|행수|실측값)[^\n]{0,45}?" + NB + r"(25,389|25,795|26,107|26,782|26,937)" + NE,
     {"26,782"}, {"25,389", "25,795", "26,107", "26,937"}),

    ("后端文件数",
     r"(?:后端|파일)[^\n]{0,20}?" + NB + r"(88|92)" + NE + r"[^\n]{0,6}(?:个|개)?\s*(?:文件|파일)?",
     {"92"}, {"88"}),

    ("测试文件数",
     NB + r"(54|56)" + NE + r"\s*(?:个|개)?\s*(?:测试文件|테스트 파일)",
     {"56"}, {"54"}),

    ("效果生产者",
     r"(?:效果生产者|效果生产|효과 생산자|effect producers?)[^\n]{0,60}?" + NB + r"(2|14|16|54)" + NE,
     {"2", "14", "54"}, {"16"}),

    ("成熟度三元组",
     r"(?:complete|partial|placeholder|成熟度)[^\n]{0,60}?" + NB + r"(9|37|8)" + NE,
     {"9", "37", "8"}, set()),

    ("滑窗总数",
     NB + r"(286,150)" + NE, {"286,150"}, set()),

    ("bootstrap 学生数",
     r"(?:n_users_used|实际使用[^\n]{0,6}学生|사용 학생)[^\n]{0,40}?" + NB + r"(2,314|4,217)" + NE,
     {"2,314", "4,217"}, set()),

    ("众数 0.25 窗数",
     r"0\.25[^\n]{0,20}?(30,899)", {"30,899"}, set()),
    ("0.20 窗数",
     r"0\.20[^\n]{0,20}?" + NB + r"(30,061|30,074|30,088)" + NE, {"30,061"}, {"30,074", "30,088"}),
    ("0.15 窗数",
     r"0\.15[^\n]{0,20}?" + NB + r"(26,151|26,138)" + NE, {"26,151"}, {"26,138"}),

    ("0.15~0.35 占比",
     NB + r"(49\.3)\s*%", {"49.3"}, set()),

    ("DBE 题数",
     r"(?:DBE[^\n]{0,10}|教师标签[^\n]{0,10}|전문가 라벨)\D{0,12}" + NB + r"(212)" + NE,
     {"212"}, set()),

    ("A1 Junyi 题数",
     r"(?:A1|Junyi)[^\n]{0,30}?" + NB + r"(1,274)" + NE, {"1,274"}, set()),

    # 2026-10-02 按 M1 §3.1/§3.2 重跑值更正：A1 基线与融合同置 A 半（旧 0.963 受同半泄漏、
    # 已作废），A2 与 O4 统一信号构造后同为 0.2918。旧值移入 legacy 集。
    ("A1 ρ(成功率/融合)",
     NB + r"(0\.9541|0\.8923|0\.963|0\.892)" + NE,
     {"0.9541", "0.8923"}, {"0.963", "0.892"}),

    ("A2 ρ(融合/成功率)",
     r"(?:A2|等权融合)[^\n]{0,40}?" + NB + r"(0\.2918|0\.2204|0\.205|0\.220)" + NE,
     {"0.2918", "0.2204"}, {"0.205", "0.220"}),

    ("O4 等权融合 ρ",
     r"(?:O4|第 6 节)[^\n]{0,40}?" + NB + r"(0\.2918|0\.2899)" + NE, {"0.2918"}, {"0.2899"}),

    ("M3 最大 ρ",
     r"(?:最大|최대|max)[^\n]{0,30}?" + NB + r"(0\.2430|0\.2521)" + NE, {"0.2521"}, {"0.2430"}),

    ("M3 矩阵格数",
     NB + r"(7|11)" + NE + r"[^\n]{0,10}(?:个|개)?[^\n]{0,6}(?:EVALUATED|单元格|칸)",
     {"11"}, {"7"}),

    ("注册表指纹",
     NB + r"(ee1a49be5732)" + NE, {"ee1a49be5732"}, set()),

    ("M2 审计 tag",
     NB + r"(audit-m2-20260911)" + NE, {"audit-m2-20260911"}, set()),
]

DOCS = [
    ("计划书·中", "docs/研究计划与报告/研究计划_中文版.md"),
    ("计划书·韩", "docs/研究计划与报告/研究计划_韩文版.md"),
    ("报告·中", "docs/研究计划与报告/研究报告_中文版.md"),
    ("报告·韩", "docs/研究计划与报告/研究报告_韩文版.md"),
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
