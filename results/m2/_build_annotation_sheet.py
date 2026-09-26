#!/usr/bin/env python3
# 生成 M2 A4 双编码注释表（coder B 用）。
# 仅抓取源码片段做定位；不替 coder B 判定 target_construct/direction/channel。
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LANG = os.path.join(BASE, "_tmp_format_ludilearn.php")
TIMER = os.path.join(BASE, "_tmp_timer.php")
OUT = os.path.join(BASE, "a4_annotation_sheet.md")

COMMIT = "eb69582fb4def6e4cbb26c2146ceb90435951c53"


def read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def snippet(lines, token, before=6, after=6):
    for i, ln in enumerate(lines):
        if token in ln:
            a = max(0, i - before)
            b = min(len(lines), i + after + 1)
            return i + 1, lines[a:b]
    return None, None


lang = read_lines(LANG)
timer = read_lines(TIMER)

# (item, file_label, token, neutral_fact)
ludilearn = [
    ("LUDI_1", "lang/en/format_ludilearn.php:202", "settings:avatardescription",
     "语言字符串：头像（avatar）游戏元素的描述——学习者随课程进度解锁发型/服饰/配饰等，自定义在课程中的可视化形象。"),
    ("LUDI_2", "lang/en/format_ludilearn.php:194", "settings:badgedescription",
     "语言字符串：徽章（badge）游戏元素的描述文本。"),
    ("LUDI_3", "lang/en/format_ludilearn.php:198", "settings:progressiondescription",
     "语言字符串：进度（progression）游戏元素的描述文本。"),
    ("LUDI_4", "lang/en/format_ludilearn.php:133", "$string['ranking']",
     "语言字符串：排行榜（ranking）元素的标签文本。"),
    ("LUDI_5", "lang/en/format_ludilearn.php:189", "settings:scoredescription",
     "语言字符串：分数（score）游戏元素的描述文本。"),
    ("LUDI_6", "classes/local/gameelements/timer.php", "DEFAULT_PENALTIES = 20",
     "类常量 DEFAULT_PENALTIES = 20，定义计时器（timer）游戏元素每扣 1 分对应的惩罚量；构造时在 sectionparameters 中写入 penalties。"),
]

parts = []
parts.append("# M2 A4 · 双编码注释表（coder B 用）\n")
parts.append("> **用途**：把 `a4_coderB.csv` 里 17 个 `source_anchor` 指向的源码片段抓到一起，供 coder B 定位与判读。\n")
parts.append("> **不含任何判定**：本表不替 coder B 填写 `target_construct` / `direction` / `channel`，那三列由 coder B **独立**判定。\n")
parts.append(f"> **数据来源**：Ludilearn @ commit `{COMMIT}`（已从 GitHub 抓取，行号经核对一致）；Level Up XP @ `danbetcher/moodle-levelup`（**仓库在 GitHub 返回 404，源码不可获取**）。\n")

parts.append("## 一、Ludilearn（6 项，已抓取源码）\n")
for item, flabel, token, fact in ludilearn:
    if token == "DEFAULT_PENALTIES = 20":
        lines = timer
    else:
        lines = lang
    lineno, snip = snippet(lines, token)
    parts.append(f"### {item} · Ludilearn · `{flabel}`\n")
    if lineno and snip:
        parts.append(f"- 锚点命中行：**{lineno}**\n")
        parts.append("```php\n" + "\n".join(snip) + "\n```\n")
    else:
        parts.append(f"- ⚠️ 未在抓取文件中命中锚点 token `{token}`。\n")
    parts.append(f"- 中性说明（仅描述代码本身，非构念判定）：{fact}\n")
    parts.append("- **coder B 请独立判定**：`target_construct` / `direction` / `channel`\n")

parts.append("\n## 二、Level Up XP（11 项，⚠️ 源码不可获取）\n")
parts.append("> 引用的 `danbetcher/moodle-levelup` 仓库在 GitHub 返回 **404**（已更名 / 删除 / 私有）。以下仅列原始锚点；待你提供本地克隆路径或新仓库地址后，我再补抓片段。\n")
parts.append("| item | 原始锚点（coder A 记录） | 状态 |\n|---|---|---|")
luxp = [
    ("LUXP_1", "classes/local/badge/badge_manager.php"),
    ("LUXP_2", "classes/form/cheatguard.php"),
    ("LUXP_3", "classes/local/division/group_division.php"),
    ("LUXP_4", "classes/local/leaderboard/course_user_leaderboard.php"),
    ("LUXP_5", "classes/local/xp/levels_info.php, level.php"),
    ("LUXP_6", "classes/local/notification/course_level_up_notification_service.php"),
    ("LUXP_7", "classes/form/promo.php"),
    ("LUXP_8", "classes/local/xp/rank.php, state_rank.php"),
    ("LUXP_9", "classes/local/ruletype/limit_spec.php（H/D/W/M 窗口 + timesallowed）"),
    ("LUXP_10", "classes/local/rule/the_dictator.php, ruletype/*.php"),
    ("LUXP_11", "classes/local/xp/state.php, user_state.php"),
]
for item, anchor in luxp:
    parts.append(f"| {item} | `{anchor}` | ⚠️ 不可获取（仓库 404） |")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts) + "\n")

print("WROTE", OUT)
print("ludilearn items:", len(ludilearn), "| levelup items flagged:", len(luxp))
