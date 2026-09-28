#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""四份完整稿的**双向**参考文献一致性门禁。

为什么需要（2026-09-27 的教训）
------------------------------
M3 稿曾自述"参考文献表编号连续、无悬空引用（2026-09-25 复核）"，但该复核只核对了
**表 → 正文**一个方向（"表内每个条目是否都有正文引用点"），从未反查
**正文 → 表**（"正文引用的文献是否都在表内"）。结果漏检了两处真实的反向悬空引用：
§5 借 R5（Kolesnikova 等 2026）确立的解析成功率必报规约、§5.4 借 R11（Razavi &
Powers 2026, r=.87）锚定的增益路径 —— 二者均以"作者（年份）"裸引用出现在正文，
而参考文献表中没有条目。M1 同样存在两处：Al-Fawakhiri 等 2023、Yeung 2019。

本脚本把两个方向都变成机械门禁：

* **A 结构检查**：编号 [1]..[N] 必须连续、不重复、不缺号。
* **B 正向（表→正文）**：每条参考文献的第一作者姓氏必须出现在正文（参考文献表之外），
  否则是"表里有、正文没引"的悬空条目。
* **C 反向（正文→表）**：正文里所有 `姓氏（年份）` / `姓氏 等（年份）` / `姓氏 (YYYY)`
  中文献式引用，其姓氏必须能在参考文献表中找到；否则是"正文引了、表里没有"的悬空引用
  —— 这正是 2026-09-27 补录的 4 条。

反向检查必然会报出一批需人工判定的候选（例如正文中作为背景提及、但其文献已在别处以
编号引用的情况），因此**默认以 max-1 报告**，由作者逐条确认；若某姓氏确属"正文提及但
不引用"，请把它加进 `KNOWN_NON_REFERENCES` 白名单并在行内注明理由。

用法
----
    python docs/check_reference_consistency.py            # 报告模式（默认，exit 0）
    python docs/check_reference_consistency.py --strict   # 门禁模式（任何 FAIL → exit 1）

设计约束：路径一律由 `__file__` 推导，**不硬编码 `E:\\learnflow`**（此前多个脚本因此
在其它机器上直接不可用）；零第三方依赖，标准库即可跑。
"""
import argparse
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent

PAPERS = [
    "M1_难度可公度性与最优错误率_完整稿.md",
    "M2_多干预并存学习系统的冲突结构审计_完整稿.md",
    "M3_有序难度决策与大模型先验边界_完整稿.md",
    "M4_信度结构化组合难度估计_完整稿.md",
]

# 正文提及但不构成引用的姓氏/词（例如指 MCPL名胜、作者自称、数据集名）
KNOWN_NON_REFERENCES = {
    "Oxenham",  # 节拍感知经典(Jules?) 若出现在背景句中且另有编号引用时用
}

# 反向引用的正则：(1) 中文语境 姓（2023） / 姓 等（2023） / 姓 与 X（2023）
#                 (2) 英文语境 Surname (2023) / Surname et al. (2023) / Surname and X (2023)
CN_CITE = re.compile(
    r"(?<![\w\u4e00-\u9fff])([A-Z][A-Za-z\u00C0-\u024F'\-]{2,30})"
    r"(?:\s*(?:等|和|与|、)\s*[^\s，。）\)]{0,40})?"
    r"\s*[（(]\s*(19|20)\d{2}\s*[)）]"
)
EN_CITE = re.compile(
    r"(?<![\w])([A-Z][A-Za-z\u00C0-\u024F'\-]{2,30})"
    r"(?:\s+(?:et\s+al\.|and|&)\s+[A-Z][A-Za-z'\-]+)?"
    r"\s*\(\s*(19|20)\d{2}\s*\)"
)

REF_ENTRY = re.compile(r"(?m)^\[(\d+)\]\s+(.{0,120})")

# BibTeX 键（被反引号包裹，例如 `li2026canllms`）。用于 M4 等采用键式参考文献的稿件：
# 该稿件不写 [n] 编号，而把引用键放在正文/参考文献表的反引号里。
BIBKEY = re.compile(r"`([A-Za-z0-9_:]+)`")

_BIB_KEYS_CACHE = None


def load_bib_keys():
    """从 references.bib 抽取全部 @type{key, 条目的键（缓存一次）。"""
    global _BIB_KEYS_CACHE
    if _BIB_KEYS_CACHE is not None:
        return _BIB_KEYS_CACHE
    bib = (DOCS / "references.bib").read_text(encoding="utf-8", errors="replace")
    _BIB_KEYS_CACHE = set(re.findall(r"@[A-Za-z]+\{\s*([A-Za-z0-9_:]+)\s*,", bib))
    return _BIB_KEYS_CACHE


_INITIAL_TOKEN = re.compile(r"^(?:[A-Z]\.?(?:\s*[.\-]?\s*[A-Z]?\.?){0,3})$")


def surnames_from_entry(text: str) -> list:
    """从一条参考文献抽出**全部**作者姓氏（2026-09-27 修正）。

    首版只取第一作者，导致多处误报：`Baillifard, Belardi & Martarelli (2025)`
    被记为只有 Baillifard，于是正文写 "Baillifard、Belardi 与 Martarelli（2025）"
    时 Belardi 被判为悬空；Weber/Spinath、Dai/Xing、Feng/Heffernan 同理。
    英文条目格式 `Surname, G. F., Other, R. R., & Third, K. (2025). ...`，
    逗号交替给出"姓 / 名缩写"，故按逗号切分后剔除纯缩写 token 即得姓氏序列；
    中文条目格式 `张三, 李四, 王五. (2010). ...`，逗号前整体即姓氏。
    """
    # 作者区 = 第一个 "(YYYY" 之前
    m = re.search(r"[(（]\s*(19|20)\d{2}", text)
    head = text[:m.start()] if m else text[:80]
    head = head.replace("&", ",").replace("和", ",").replace("与", ",")
    out = []
    for tok in head.split(","):
        tok = tok.strip(" .;")
        if not tok:
            continue
        if re.match(r"^[A-Za-z\u00C0-\u024F'.\- ]+$", tok):
            # 英文：剔除名缩写（G. F. / G.F. /申报 PhD 之类），保留姓
            if _INITIAL_TOKEN.match(tok.replace(" ", "")):
                continue
            tok = tok.split()[0]
        out.append(tok)
    # 若整体没有一个逗号（极简格式），至少保留首 token
    if not out and text.strip():
        out = [text.strip().split()[0].strip(" .,;")]
    return out


def check_paper(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.split("\n")

    # ---- 定位参考文献表起点 ----
    ref_start = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{2,3}\s*参考文献", ln):
            ref_start = i
            break
    body_text = "\n".join(lines[:ref_start]) if ref_start is not None else raw
    ref_text = "\n".join(lines[ref_start:]) if ref_start is not None else ""

    problems = []
    info = {}

    # ---- A 编号连续性 ----
    nums = [int(m.group(1)) for m in REF_ENTRY.finditer(raw)]
    info["refs"] = len(nums)
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        problems.append(("FAIL", "A 结构", f"编号重复: {dup}"))
    if nums:
        if sorted(nums) != list(range(min(nums), max(nums) + 1)):
            missing = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
            problems.append(("FAIL", "A 结构", f"编号不连续，缺: {missing}"))
        if min(nums) != 1:
            problems.append(("WARN", "A 结构", f"起始编号为 {min(nums)}，不是 1"))
    elif BIBKEY.search(ref_text):
        # 键式参考文献稿件（如 M4）：不要求 [n] 编号，改为校验反引号键存在于 bib。
        # 仅扫描**参考文献表**区域内的反引号键：从「参考文献」标题切到下一个标题
        # （避免其后的「附录 A 结果可复算清单」里的代码标识符被误判为引用键）。
        end = len(lines)
        for j in range(ref_start + 1, len(lines)):
            if re.match(r"^#{1,3}\s", lines[j]):
                end = j
                break
        ref_region = "\n".join(lines[ref_start:end])
        ref_keys = sorted(set(BIBKEY.findall(ref_region)))
        info["refs"] = len(ref_keys)
        info["cited_inline"] = 0  # 键式稿件不统计作者-年份姓氏
        bib_keys = load_bib_keys()
        missing = sorted(k for k in ref_keys if k not in bib_keys)
        if missing:
            problems.append(("FAIL", "C 反向/键",
                             "参考文献表使用了但 references.bib 无条目的键: " + ", ".join(missing)))
        body_keys = set(BIBKEY.findall(body_text))
        for k in ref_keys:
            if k not in body_keys:
                problems.append(("WARN", "B 正向",
                                 f"[{k}] 该 BibTeX 键未在正文出现（表内有、正文似未引）"))
        return info, problems
    else:
        problems.append(("FAIL", "A 结构", "未找到任何 [n] 形式的参考文献条目"))

    # ---- B 正向：表内条目必须在正文被提及 ----
    ref_surnames = set()
    for m in REF_ENTRY.finditer(ref_text):
        names = surnames_from_entry(m.group(2))
        ref_surnames.update(names)
        # 语义：**任一**作者姓氏在正文出现即视为该条目已被引用。
        # （不能要求全部作者都出现——正文惯例是"第一作者 等（年份）"，
        #   要求全出现会把大量正常条目误报为悬空。）
        if names and not any(re.search(re.escape(s), body_text) for s in names):
            problems.append(("WARN", "B 正向",
                             f"[{m.group(1)}] {names[0]} 等：整条未在正文出现（表内有、正文似未引）"))

    # ---- C 反向：正文作者-年份引用必须在表内 ----
    cited = set()
    for pat in (CN_CITE, EN_CITE):
        for m in pat.finditer(body_text):
            cited.add(m.group(1))
    missing_forward = sorted(s for s in cited
                             if s not in ref_surnames and s not in KNOWN_NON_REFERENCES)
    info["cited_inline"] = len(cited)
    if missing_forward:
        problems.append(("FAIL", "C 反向",
                         "正文引用了但参考文献表无条目: " + ", ".join(missing_forward)))

    return info, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="四稿双向参考文献一致性门禁")
    ap.add_argument("--strict", action="store_true",
                    help="门禁模式：出现任何 FAIL/WARN 均以 exit 1 退出")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("LearnFlow · 四稿双向参考文献一致性门禁")
    print("  A 结构编号连续 | B 表→正文 | C 正文→表（反向，2026-09-27 新增）")
    print("=" * 78)

    n_fail = n_warn = 0
    for name in PAPERS:
        path = DOCS / name
        print(f"\n【{name}】")
        if not path.exists():
            print("  ✗ FAIL 文件不存在")
            n_fail += 1
            continue
        info, problems = check_paper(path)
        print(f"  参考文献 {info['refs']} 条 | 正文检出作者-年份引用 {info['cited_inline']} 个姓氏")
        if not problems:
            print("  ✅ 三项检查全部通过（编号连续、无正向悬空、无反向悬空）")
            continue
        for level, cat, msg in problems:
            mark = "✗ FAIL" if level == "FAIL" else "⚠ WARN"
            print(f"  {mark} [{cat}] {msg}")
            n_fail += level == "FAIL"
            n_warn += level == "WARN"

    print("\n" + "=" * 78)
    verdict = "✅ PASS" if n_fail == 0 else "❌ FAIL"
    print(f"{verdict}：FAIL {n_fail} 项 / WARN {n_warn} 项")
    if n_fail == 0 and n_warn:
        print("  说明：WARN 多为 '表内有而正文未明确引' 的条目，需作者确认是否保留。")
    print("=" * 78)
    if args.strict:
        return 1 if (n_fail or n_warn) else 0
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
