"""提取 17 个锚点源码的结构摘要（类/函数/常量/文档注释），用于撰写问卷的"功能描述"。

只读、不修改任何外部仓库；输出紧凑摘要，便于人工/AI 撰写中性描述。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [
    "ludilearn_lang.php", "ludilearn_timer.php",
    "luxp_badge_manager.php", "luxp_cheatguard.php", "luxp_group_division.php",
    "luxp_leaderboard.php", "luxp_levels_info.php", "luxp_levelup_notif.php",
    "luxp_promo.php", "luxp_rank.php", "luxp_limit_spec.php",
    "luxp_the_dictator.php", "luxp_state.php",
]
# Ludilearn lang 文件需按给定行号抽取（锚点指向具体行）
LANG_LINES = {"LUDI_4(ranking)": (125, 140), "LUDI_5/2/3/1(settings)": (183, 206)}
TIMER_LINES = (30, 60)

PAT = re.compile(r"^\s*(abstract |final )?(class|interface|trait|function|const|"
                 r"public|protected|private|static|/\*\*|\*)\b")


def dump(path, rng=None, max_lines=40):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if rng:
        a, b = rng
        return [f"{i+1}: {l}" for i, l in enumerate(lines[a - 1:b]) if l.strip()]
    out, n = [], 0
    for i, l in enumerate(lines):
        if PAT.match(l) or l.strip().startswith("*") or l.strip().startswith("//"):
            out.append(f"{i+1}: {l.rstrip()}")
            n += 1
            if n >= max_lines:
                break
    return out


for name in FILES:
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        print(f"### {name}: MISSING")
        continue
    print(f"\n{'='*70}\n### {name}")
    if name == "ludilearn_lang.php":
        for tag, rng in LANG_LINES.items():
            print(f"--- {tag} (lines {rng[0]}-{rng[1]}) ---")
            print("\n".join(dump(p, rng)))
    elif name == "ludilearn_timer.php":
        print(f"--- lines {TIMER_LINES[0]}-{TIMER_LINES[1]} ---")
        print("\n".join(dump(p, TIMER_LINES)))
    else:
        print("\n".join(dump(p)))
