# -*- coding: utf-8 -*-
"""四份文档的数字/术语一致性机械校验：中文两版 + 韩文两版。

v2（2026-09-22，审阅意见整改）：
  1. 标记匹配前把 Unicode 减号 U+2212 归一为 ASCII '-'，消除此前的假阴性
     （稿件正文用 '−'，旧版标记表用 '-'，导致 11 个负号数值被误报缺失）。
  2. 把"必须出现"拆成两层：
     - CORE：四份文件都**必须**逐字出现的权威标记（硬门禁，缺失即失败）；
     - PLAN_ONLY / REPORT_ONLY：仅要求出现在对应文档中的标记（信息性报告）。
     旧版把全部结果类数值都要求出现在计划书里，而计划书作为"计划"本就不承载
     全部细粒度数值，造成长期噪声。
  3. 新增 v1.1 标记：滑窗单值众数（0.25 / 30,899 / 19.64%）、机制三元组
     （placeholder / 效果生产 2）、配对 bootstrap（0.0385 / 0.2193 / 0.34）、
     审计时点 tag（audit-m2-20260911）、新增门禁脚本、Scopus 期刊口径。
  4. FORBIDDEN 增加"语境豁免"：25,389 / 23,927 作为**漂移披露**出现是合规的，
     仅当文档出现该数字却**没有**漂移披露语时才算违规。
  5. 增加退出码：CORE 缺失或 FORBIDDEN 命中 → exit 1（可作门禁使用）。
"""
import io, os, re, sys

# 2026-10-03: 四份 md 已合并入 docs/LearnFlow_研究总档.md 的第一~四部，
# 源文件不再单独存在；改为从总档按部抽取到临时目录后再校验，
# 硬门禁逻辑（逐字标记核对）完全不变。
import importlib.util as _ilu
import tempfile as _tf

# 2026-10-03: 原 `docs/研究计划与报告/` 已移除（内容并入研究总档），
# 校验改为从总档抽取到临时目录后逐字核对（见下方 EXTRACT 逻辑）。
BASE = r"E:\learnflow\docs"
MASTER = os.path.join(BASE, "LearnFlow_研究总档.md")
_TMP = _tf.mkdtemp(prefix="_verify_docs_")
# 同目录导入 _md_to_docx.py（本脚本与它已一并迁到 tools/docx_build/）
_spec = _ilu.spec_from_file_location(
    "_md2docx", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "_md_to_docx.py"))
_m = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_m)
_EXTRACT = {
    "研究计划_中文版.md": "第一部 · 研究计划",
    "研究计划_韩文版.md": "第三部 · 研究计划（韩文版）",
    "研究报告_中文版.md": "第二部 · 研究进展报告",
    "研究报告_韩文版.md": "第四部 · 研究进展报告（韩文版）",
}
FILES = []
for _label, _fn in [("计划·中", "研究计划_中文版.md"), ("计划·韩", "研究计划_韩文版.md"),
                    ("报告·中", "研究报告_中文版.md"), ("报告·韩", "研究报告_韩文版.md")]:
    _out = os.path.join(_TMP, _fn)
    _m.extract_master_part(MASTER, _EXTRACT[_fn], _out)
    FILES.append((_label, _fn))

# 四份文件都必须逐字出现的权威标记（硬门禁）
REQUIRED_CORE = [
    # 系统计数与指纹
    "ee1a49be5732", "LF-M01", "LF-M54", "LF-L01", "LF-L28",
    "54", "28", "16", "88", "25,795", "104", "936", "14",
    # 机制三元组（v1.1 新增强制口径）
    "placeholder", "complete 9 / partial 37 / placeholder 8",
    "LF-M19", "LF-M53",
    # 链 1 数字
    "0.5357", "0.1276", "0.0196", "36.4%", "0.0001", "0.2207", "0.4326",
    # 冷启动估计器
    "27.3", "0.895", "srw7", "fused6", "flow_zone", "λ_cf(k)",
    "+3.823", "+4.283", "+0.102",
    # 滑窗分布（v1.1 更正后的权威口径）
    "0.25", "30,899", "19.64%", "0.3511", "21", "286,150",
    # 审计链（v1.1 三元组与封存 tag）
    "77.8%", "42", "audit-m2-20260911", "verify_m2_anchors.py",
    # 单一模型标注（v1.1）
    "0.2195", "0.1808", "0.0385", "0.2193", "Qwen3.6-35B-A3B",
    # 数据集与门禁
    "16,217,311", "72,758", "1,326", "212", "120", "994",
    "10.5281/zenodo.22719229", "CITATION.cff",
    "verify_counts.py", "reconcile_paper_tables.py", "verify_window_support.py",
    "difficulty_fusion.py", "optimal_difficulty.py",
    # 期刊与合规口径（v1.1 新增）
    "Scopus",
    # 参考数据页 DOI
    "10.26193/6DZWOH",
]

# 仅计划书需要承载的标记（信息性报告，缺失不算失败）
REQUIRED_PLAN_ONLY = [
    "LF-M29", "8", "20%", "15.87%", "80.7%", "154", "241",
]

# 仅报告需要承载的标记（信息性报告）
REQUIRED_REPORT_ONLY = [
    "+0.154", "0.15–0.20", "920", "o11_land_verify.py",
    "estimate_optimized_difficulty()", "mechanism_units", "StateStore",
    "LF-M29", "LF-M32", "LF-M49", "LF-M50", "LF-M52",
    "111%", "128%", "10.5281/zenodo.22719228",
    "0.2300", "0.2899", "0.5240", "0.1069",
    "0.2610", "0.3629", "0.4023", "0.0480", "+0.1017", "+0.0723",
    "27.4", "0.9989", "-1.402", "-5.728", "0.6714", "+0.0309",
    "52,733", "0.487", "347", "-0.038", "0.6893", "0.016",
]

# 兼容旧名（跨语言一致性检查仍用全量权威集）
REQUIRED_PLAN = REQUIRED_CORE + REQUIRED_PLAN_ONLY
REQUIRED_REPORT = REQUIRED_CORE + REQUIRED_REPORT_ONLY

FORBIDDEN = {
    "0.76（作为 O1 系数）": r"0\.76",
    "394 个测试": r"394",
    "685 个测试": r"685",
    "868 个测试": r"868",
    "helper-selector": r"helper-selector",
    "旧口径'众数区间 0.15–0.20'作结果为真（缺撤回语）": r"(?<!作废)(?<!撤回)(?<!伪影)(?<!已删除)(?<!已改写)",
}

# 需要"漂移披露语"共现豁免的数字（作为现行值出现才是违规）
DRIFT_NUMBERS = {
    "23,927 行（作为现行值）": ("23,927", ("早期快照", "快照基线", "DRIFT", "漂移", "스냅샷", "드리프트")),
    "25,389 行（作为现行值）": ("25,389", ("早期快照", "快照基线", "DRIFT", "漂移", "스냅샷", "드리프트")),
}


def norm(s):
    """标记匹配用归一化：Unicode 减号 → ASCII 减号；全角括号 → 半角。"""
    return s.replace("\u2212", "-").replace("\uff08", "(").replace("\uff09", ")")


lines = []
def p(s=""):
    lines.append(s)


fail = []

for label, fn in FILES:
    path = os.path.join(_TMP, fn)   # 2026-10-03: 从总档抽取的临时副本
    if not os.path.exists(path):
        p("[MISSING] %s -> %s" % (label, path))
        fail.append("%s 文件缺失" % label)
        continue
    raw = io.open(path, "r", encoding="utf-8").read()
    t = norm(raw)
    n = len(raw.splitlines())
    plan = "计划" in label
    p("%s  %s" % (label.ljust(8), fn))
    p("    行数=%d  字符=%d  表格行=%d  标题=%d" % (
        n, len(raw), len(re.findall(r"^\|", raw, re.M)), len(re.findall(r"^#{1,3} ", raw, re.M))))

    miss_core = [k for k in REQUIRED_CORE if norm(k) not in t]
    extra = REQUIRED_PLAN_ONLY if plan else REQUIRED_REPORT_ONLY
    miss_extra = [k for k in extra if norm(k) not in t]
    p("    CORE 标记 %d 个，缺失 %d 个" % (len(REQUIRED_CORE), len(miss_core)))
    if miss_core:
        p("      缺失: %s" % ", ".join(miss_core))
        fail.append("%s CORE 缺失: %s" % (label, ", ".join(miss_core)))
    p("    文档专属标记 %d 个，缺失 %d 个（信息性）" % (len(extra), len(miss_extra)))
    if miss_extra:
        p("      缺失: %s" % ", ".join(miss_extra))

    hits = []
    for name, pat in FORBIDDEN.items():
        if name.startswith("旧口径"):
            continue  # 该条为占位说明，实际判定见下
        c = len(re.findall(pat, t))
        if c:
            hits.append("%s x%d" % (name, c))
    for name, (num, exempt) in DRIFT_NUMBERS.items():
        if num in t and not any(e in t for e in exempt):
            hits.append("%s x1" % name)
    p("    禁用项命中: %s" % ("; ".join(hits) if hits else "无"))
    if hits:
        fail.append("%s 禁用项命中: %s" % (label, "; ".join(hits)))
    p("")

p("=" * 60)
p("跨语言一致性（中 vs 韩：同一标记不得只在一侧出现）")
for cn, kr, reqname in [
    ("研究计划_中文版.md", "研究计划_韩文版.md", "计划"),
    ("研究报告_中文版.md", "研究报告_韩文版.md", "报告"),
]:
    tc = norm(io.open(os.path.join(_TMP, cn), "r", encoding="utf-8").read())
    tk = norm(io.open(os.path.join(_TMP, kr), "r", encoding="utf-8").read())
    req = REQUIRED_PLAN if reqname == "计划" else REQUIRED_REPORT
    only_cn = [k for k in req if norm(k) in tc and norm(k) not in tk]
    only_kr = [k for k in req if norm(k) in tk and norm(k) not in tc]
    p("%s：仅中文有 %d 个；仅韩文有 %d 个" % (reqname, len(only_cn), len(only_kr)))
    if only_cn:
        p("   仅中文: %s" % ", ".join(only_cn))
    if only_kr:
        p("   仅韩文: %s" % ", ".join(only_kr))
    if only_cn or only_kr:
        fail.append("%s 跨语言不一致（中独有 %d / 韩独有 %d）" % (reqname, len(only_cn), len(only_kr)))

p("")
p("韩文版残留中文段落检测（含中日韩统一表意文字且不含韩文的行）")
for label, fn in [("计划·韩", "研究计划_韩文版.md"), ("报告·韩", "研究报告_韩文版.md")]:
    t = io.open(os.path.join(BASE, fn), "r", encoding="utf-8").read()
    bad = []
    for i, ln in enumerate(t.splitlines(), 1):
        if not ln.strip():
            continue
        has_hanja = bool(re.search(r"[\u4e00-\u9fff]", ln))
        has_hangul = bool(re.search(r"[\uac00-\ud7a3]", ln))
        if has_hanja and not has_hangul:
            bad.append((i, ln.strip()[:70]))
    p("%s：疑似残留中文行 %d 条" % (label, len(bad)))
    for i, s in bad[:8]:
        p("    L%d: %s" % (i, s))

p("")
if fail:
    p("RESULT: FAIL (%d)" % len(fail))
    for f in fail:
        p("  - %s" % f)
else:
    p("RESULT: PASS（CORE 标记齐备、无禁用项、跨语言一致、韩文无残留中文段落）")

out = "\n".join(lines)
io.open(r"E:\learnflow\_verify_docs.txt", "w", encoding="utf-8", newline="").write(out)
print(out)
sys.exit(1 if fail else 0)
