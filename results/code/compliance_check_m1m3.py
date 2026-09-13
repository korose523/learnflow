# -*- coding: utf-8 -*-
"""LearnFlow 论文数字诚信红线检查器（可复用于每轮定稿）。

检查对象：`E:/learnflow/docs/` 下的三篇定稿（M1/M2/M3）。
用法：
    python results/code/compliance_check_m1m3.py                 # 默认扫 docs/
    python results/code/compliance_check_m1m3.py <目录> [<目录>…]  # 指定目录

设计要点（踩过的坑）：
  * 行数一律用 `len(text.splitlines())`；**不要**用 `text.count("\\n") + 1`，
    文件以换行结尾时会多算 1 行（曾把 difficulty_fusion.py 记成 339 行，实为 338）。
  * 裸 `0.76` 是红线违规（O1 系数只允许 0.5357）。
  * 「预测力提升」只允许出现在已收回/否定语境，因此把上下文一起打印出来人工复核。
  * `920` / `76` 允许出现，但必须在"改动前 / 登记基线 / PRD 自相矛盾"语境，
    故同样打印上下文，不做正则一刀切。
"""
import os
import re
import sys

BASE = r"E:/learnflow"
DEFAULT_DIR = os.path.join(BASE, "docs")
FILES = [
    "M1_难度可公度性与最优错误率_完整稿.md",
    "M2_多干预并存学习系统的冲突结构审计_完整稿.md",
    "M3_有序难度决策与大模型先验边界_完整稿.md",
]

FINGERPRINT = "ee1a49be5732"
# 禁用措辞（无源断言 / 博客腔）
BANNED_PHRASES = ["众所周知", "研究表明", "显然", "业界公认", "结论先行", "一句话结论"]
# 作语义载体的 emoji
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\u2b50\u2705\u26a0\u274c\u26d4\u2139\u2714\u2716\ufe0f]")


def ctx(text, pattern, before=30, after=8, limit=12):
    out = []
    for m in list(re.finditer(pattern, text))[:limit]:
        seg = text[max(0, m.start() - before):m.end() + after].replace("\n", " ")
        out.append(seg)
    return out


def check(path):
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()          # 正确口径
    rep = []
    add = rep.append

    add("==== %s ====" % os.path.basename(path))
    add("  行数 = %d   （正确口径 splitlines）" % len(lines))
    add("  字符数 = %d" % len(text))

    n76 = len(re.findall(r"0\.76\b", text))
    add("  [红线] 裸 '0.76'            = %d  %s" % (n76, "" if n76 == 0 else "*** 违规 ***"))
    add("  [红线] '0.5357'（O1 正确值） = %d" % text.count("0.5357"))

    add("  [红线] '934'（全量测试）     = %d" % text.count("934"))
    c920 = text.count("920")
    add("  [须核对语境] '920'          = %d" % c920)
    for c in ctx(text, r"920"):
        add("       920 ctx: %s" % c)

    add("  [红线] 指纹 %s      = %d" % (FINGERPRINT, text.count(FINGERPRINT)))

    c76 = text.count("76")
    add("  [须核对语境] '76'           = %d（仅允许 PRD 自相矛盾语境，且须同处给出 69）" % c76)
    for c in ctx(text, r"\b76\b", limit=6):
        add("        76 ctx: %s" % c)

    add("  '54' = %d, '28' = %d, LF-M 引用 = %d"
        % (len(re.findall(r"\b54\b", text)), len(re.findall(r"\b28\b", text)),
           len(re.findall(r"LF-M\d\d", text))))

    yql = ctx(text, r"预测力提升", before=35, limit=20)
    add("  [诚信] '预测力提升' 出现 %d 次（须全部为否定/已收回语境）" % len(yql))
    for c in yql:
        add("        ctx: %s" % c)

    emo = EMOJI_RE.findall(text)
    add("  [体例] emoji 作语义载体 = %d  %s" % (len(emo), sorted(set(emo))[:10] if emo else ""))

    bad = [p for p in BANNED_PHRASES if p in text]
    add("  [体例] 无源/博客腔措辞 = %s" % (bad if bad else "无"))

    idx = text.count("25,795")
    add("  [数字] '25,795'（python_loc 真值）= %d" % idx)

    add("")
    return rep


def main(argv):
    dirs = argv[1:] or [DEFAULT_DIR]
    report = []
    checked = 0
    for d in dirs:
        for fn in FILES:
            p = os.path.join(d, fn)
            if os.path.exists(p):
                report.extend(check(p))
                checked += 1
            else:
                report.append("==== [缺失] %s ====\n" % p)
    out = "\n".join(report)
    # 报告只写项目内固定位置；同时打印
    dst = os.path.join(BASE, "results", "code", "compliance_m1m3.txt")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(out)
    print("已检查 %d 个文件；报告 -> %s" % (checked, dst))


if __name__ == "__main__":
    main(sys.argv)
