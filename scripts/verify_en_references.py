#!/usr/bin/env python3
"""英文投稿件参考文献门禁：校验 4 篇英文稿的文献表能在 references.bib 中定位。

为什么需要这个门禁
------------------
`docs/check_reference_consistency.py` 只校验**中文完整稿**的文献表，而实际投稿
的是**英文稿**（`M*_submission_EN.md`）。若英文稿的某条文献在 bib 中定位不到，
投稿时会出现"参考文献缺失/对不上"，编辑阶段才会发现。

三种引用格式（本门禁需同时支持）
------------------------------
- M1 / M2 / M3：编号制 `[N] 作者… (年份). …`（不同期刊要求不同，属正常）
- M4：bibkey 制 `- 作者… (年份). … [`key`]`（键直接可校验，最严格）

本脚本对编号制采用"第一作者姓氏 + 年份"在 bib 中定位，因此必须先做
**LaTeX 转义还原**——bib 里存在以下写法，直接字符串比较会漏判（实测 5 条）：

| bib 中的写法 | 还原后 |
|---|---|
| `Dudi{\\'i}k` / `Dud{\\'i}k` | `Dudík` |
| `Massart, Fr{\\'e}d{\\'e}ric` | `Massart, Frédéric` |
| `{DigiDago}`（花括号包裹） | `DigiDago` |
| `吴艳`（中文名，英文稿用拼音 Wu, Y.） | 需按姓氏拼音匹配 |

用法：
    python3 scripts/verify_en_references.py            # 报告模式
    python3 scripts/verify_en_references.py --strict   # 门禁模式（有问题 → exit 1）
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
BIB = DOCS / "references.bib"

# 每篇英文稿的参考文献条数基线（首次成功运行时自动写入并纳入版本控制）。
# 用途：检测「误删文献条目」——仅靠"表→bib"单向校验无法发现缺条，
# 因为删掉某条后剩余条目仍都能在 bib 中定位，门禁会误报 PASS。
BASELINE = REPO / "scripts" / "en_refs_baseline.json"

PAPERS = [
    ("M1", "M1_submission_EN.md"),
    ("M2", "M2_submission_EN.md"),
    ("M3", "M3_submission_EN.md"),
    ("M4", "M4_submission_EN.md"),
]


def _detex(s: str) -> str:
    """还原 bib 的 LaTeX 转义与花括号包裹，便于与英文稿的作者名比较。"""
    s = s.replace("\\'", "").replace("`", "").replace("~", " ")
    s = s.replace("{", "").replace("}", "")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def parse_bib() -> dict[str, tuple[str, str]]:
    """返回 {key: (第一作者姓, 年份)}。"""
    txt = BIB.read_text(encoding="utf-8")
    out: dict[str, tuple[str, str]] = {}
    for m in re.finditer(r"@\w+\{([^,]+),", txt):
        key = m.group(1).strip()
        nxt = re.search(r"\n@", txt[m.end():])
        body = txt[m.end(): m.end() + (nxt.start() if nxt else len(txt))]
        au = re.search(r"author\s*=\s*\{(.*?)\}\s*,\s*\n", body, re.S)
        yr = re.search(r"year\s*=\s*\{?(\d{4})", body)
        if not au:
            continue
        # 第一作者：形如 "Surname, Given and Surname2, ..." 或 "Name and Name2"
        first = re.split(r"\s+and\s+|,", au.group(1).strip())[0].strip()
        out[key] = (_detex(first), yr.group(1) if yr else "")
    return out


def _name_variants(au: str) -> set[str]:
    """从作者串提取可用于匹配的姓氏候选。

    投稿文献表里同一作者可能有两种写法，须都支持：
      · 姓在前：``Wu, Y.`` / ``Massart, Frédéric``  → 姓 = 逗号前
      · 名在前：``Frédéric Massart`` / ``DigiDago``   → 姓 = 末词
    单名作者（``DigiDago``）两种规则都返回自身。
    """
    au = au.strip().rstrip(".,")
    if not au:
        return set()
    out = set()
    if "," in au:                       # 姓, 名 —— 取逗号前
        out.add(_detex(au.split(",")[0]))
    # 去掉括注（如 "(FMCorz)"）后再分词，否则会把它误判为末词
    bare = re.sub(r"\([^)]*\)", " ", au)
    toks = [x for x in _detex(bare).split() if x]
    if toks:
        out.add(toks[0])                 # "Massart, Frederic" → 首词
        out.add(toks[-1])                # "Frederic Massart" → 末词
    return {x for x in out if x}


def main() -> int:
    strict = "--strict" in sys.argv
    bib = parse_bib()
    rows, failures = [], []

    for tag, fname in PAPERS:
        fp = DOCS / fname
        if not fp.exists():
            failures.append(f"{tag}: 文件缺失 {fp}")
            continue
        text = fp.read_text(encoding="utf-8")
        i = text.find("## References")
        if i < 0:
            failures.append(f"{tag}: 未找到 '## References' 段")
            continue
        seg = text[i:]

        # 形态 A：bibkey 制（M4）——键直接校验，零歧义
        keyed = re.findall(r"\[`([A-Za-z][\w:+-]*)`\]", seg)
        # 形态 B：编号制（M1–M3）——按 [N] 作者姓氏 + 年份定位
        numbered = re.findall(r"^\[(\d+)\]\s+(.+?)\((\d{4})\)", seg, re.M)

        ok = 0
        total = 0
        for k in keyed:
            total += 1
            if k not in bib:
                failures.append(f"{tag}: bibkey `{k}` 不在 references.bib")
            elif k not in text[:i]:
                # 文献表列出的键在正文中从未被引用 -> 疑似键被调包替换
                failures.append(
                    f"{tag}: bibkey `{k}` 仅出现在文献表、正文从未引用 —— "
                    f"疑似键被误改（请核对原文引用处的键）")
            else:
                ok += 1
        for n, au, yr in numbered:
            total += 1
            cands = _name_variants(au)
            if not any(s in cands and y == yr for s, y in bib.values()):
                failures.append(
                    f"{tag}: 文献 [{n}] 「{au.strip()[:32]} ({yr})」"
                    f"无法在 references.bib 中按姓氏+年份定位")
            else:
                ok += 1
        mode = "bibkey" if keyed and not numbered else ("编号" if numbered else "空")
        rows.append((tag, mode, ok, total, len(numbered) + len(keyed)))

        # ── 缺条检测：与基线条数比对 ──
        import json
        base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        cur = len(numbered) + len(keyed)
        if tag in base:
            if cur < base[tag]:
                failures.append(
                    f"{tag}: 文献条数 {cur} < 基线 {base[tag]}，疑似误删 "
                    f"{base[tag] - cur} 条（若确为有意删减，请同步更新 "
                    f"{BASELINE.name}）")
        else:
            base[tag] = cur
            BASELINE.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            print(f"（已写入 {BASELINE.name} 基线：{tag} = {cur} 条）")

        # ── 编号连续性：投稿要求文献表编号从 1 起连续（缺号=引用对不上）──
        if numbered:
            nums = sorted(int(n) for n, _, _ in numbered)
            expect = list(range(1, len(nums) + 1))
            if nums != expect:
                gaps = sorted(set(expect) - set(nums))
                dups = sorted({x for x in nums if nums.count(x) > 1})
                failures.append(
                    f"{tag}: 文献表编号不连续（缺号 {gaps[:8]}"
                    f"{'，重复 ' + str(dups) if dups else ''}）——"
                    f"投稿时引用编号会对不上，须重排为 1..{len(nums)}")
            # 正文 [N] 引用不得指向不存在的编号
            body = text[:i]
            listed = set(nums)
            dangling = sorted({int(x) for x in re.findall(r"\[(\d+)\]", body)} - listed)
            if dangling:
                failures.append(
                    f"{tag}: 正文引用了文献表中不存在的编号 {dangling[:8]}")

    print("=" * 74)
    print("英文投稿件参考文献门禁（4 篇 ↔ references.bib）")
    print("=" * 74)
    print(f"{'论文':<6}{'引用形态':<8}{'可定位':<10}{'条数':<8}{'状态'}")
    print("-" * 74)
    for tag, mode, ok, total, _n in rows:
        state = "✅ 全部可定位" if ok == total else f"❌ {total - ok} 条定位不到"
        print(f"{tag:<6}{mode:<8}{f'{ok}/{total}':<10}{_n:<8}{state}")
    print("-" * 74)

    if failures:
        print("\n问题明细：")
        for f in failures:
            print(f"  ❌ {f}")
        print(f"\n结论: FAIL（{len(failures)} 项）")
        return 1 if strict else 0

    n = sum(r[2] for r in rows)
    print(f"\n全部 {len(rows)} 篇、共 {n} 条参考文献均可在 references.bib 中定位。")
    print("结论: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
