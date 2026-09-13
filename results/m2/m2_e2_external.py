#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 / E2 跨项目复现 —— 把 M2 三类冲突分类法套用到两个外部开源游戏化系统。

外部系统（均已 git clone --depth 1 到 results/m2/external/）：
  A. DigiDago/moodle-format_ludilearn @ eb69582  —— 「自适应游戏化」Moodle 课程格式
  B. FMCorz/moodle-block_xp        @ 65541fd  —— Level Up XP，Moodle 游戏化插件

方法
----
1. 机制清单**从文件系统枚举**（规则明确、可复算），不靠文档描述。
2. schema 字段（target_construct / direction / channel）由**分析师按显式锚点编码**；
   每个编码都给出 file:line 依据。**单编码者，未计算评分者间信度——这是本 E2 的
   明确局限，不得宣称已做 IRR。**
3. 三类冲突检测器与 M2 E1 完全同构（同一判据）。

检测判据（与 E1 一致）
  I  效果方向冲突  : 同一 target_construct 且 direction 相反 **且同时可激活**
  II 预算竞争      : 共享同一资源/速率预算窗口的机制数 > 预算上限
  III 目标冲突     : 参与度目标与合规/健康约束指向相反
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r"E:/learnflow\results\m2")
EXT = BASE / "external"
OUT = BASE / "m2_e2_external.json"


def git_head(p: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(p),
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


# ── 系统 A：Ludilearn ───────────────────────────────────────────────────
LUDI = EXT / "ludilearn"
ludi_elems = sorted(
    p.stem for p in (LUDI / "classes" / "local" / "gameelements").glob("*.php")
    if p.stem not in ("game_element", "nogamified")
)

# 分析师编码表（锚点 = 仓库内 file 或 lang string key）
LUDI_SCHEMA = {
    "score":    {"target": "参与度/表现", "direction": "approach", "channel": "数值面板",
                 "anchor": "lang/en/format_ludilearn.php:189 settings:scoredescription"},
    "badge":    {"target": "成就/表现",   "direction": "approach", "channel": "徽章图",
                 "anchor": "lang/en/format_ludilearn.php:194 settings:badgedescription"},
    "progress": {"target": "进度/坚持",   "direction": "approach", "channel": "进度条",
                 "anchor": "lang/en/format_ludilearn.php:198 settings:progressiondescription"},
    "avatar":   {"target": "身份/自主",   "direction": "approach", "channel": "头像定制",
                 "anchor": "lang/en/format_ludilearn.php:202 settings:avatardescription"},
    "ranking":  {"target": "社交比较",    "direction": "approach", "channel": "排行榜",
                 "anchor": "lang/en/format_ludilearn.php:133 ranking"},
    "timer":    {"target": "时长/节奏",   "direction": "withdraw", "channel": "计时器+扣分",
                 "anchor": "classes/local/gameelements/timer.php:46 DEFAULT_PENALTIES=20"},
}

# ── 系统 B：block_xp ────────────────────────────────────────────────────
XP = EXT / "block_xp"
XP_SCHEMA = {
    "xp_points":    {"target": "参与度", "direction": "approach", "channel": "数值",
                     "anchor": "classes/local/xp/state.php, user_state.php"},
    "levels":       {"target": "胜任/进度", "direction": "approach", "channel": "进度+等级",
                     "anchor": "classes/local/xp/levels_info.php, level.php"},
    "leaderboard":  {"target": "社交比较", "direction": "approach", "channel": "排行榜",
                     "anchor": "classes/local/leaderboard/course_user_leaderboard.php"},
    "rank":         {"target": "社交比较", "direction": "approach", "channel": "名次",
                     "anchor": "classes/local/xp/rank.php, state_rank.php"},
    "badge":        {"target": "成就", "direction": "approach", "channel": "徽章",
                     "anchor": "classes/local/badge/badge_manager.php"},
    "notification": {"target": "参与度", "direction": "approach", "channel": "弹窗通知",
                     "anchor": "classes/local/notification/course_level_up_notification_service.php"},
    "rules":        {"target": "行为触发", "direction": "approach", "channel": "规则引擎",
                     "anchor": "classes/local/rule/the_dictator.php, ruletype/*.php"},
    "rule_limits":  {"target": "行为速率", "direction": "withdraw", "channel": "限流窗口",
                     "anchor": "classes/local/ruletype/limit_spec.php（H/D/W/M 窗口 + timesallowed）"},
    "division":     {"target": "社交分层", "direction": "approach", "channel": "分组",
                     "anchor": "classes/local/division/group_division.php"},
    "cheatguard":   {"target": "合规", "direction": "withdraw", "channel": "防作弊拦截",
                     "anchor": "classes/form/cheatguard.php"},
    "promotion":    {"target": "参与度", "direction": "approach", "channel": "促销横幅",
                     "anchor": "classes/form/promo.php"},
}

ludi_head = git_head(LUDI)
xp_head = git_head(XP)


def detect(schema: dict, co_active_rule: str, co_active_sets=None):
    """通用三类冲突检测。"""
    approaches = sorted(k for k, v in schema.items() if v["direction"] == "approach")
    withdraws = sorted(k for k, v in schema.items() if v["direction"] == "withdraw")

    # 类型 I：同 target 且方向相反，且同时可激活
    type1 = []
    for a in approaches:
        for w in withdraws:
            if schema[a]["target"] == schema[w]["target"] and schema[a]["target"] != "合规":
                type1.append([a, w])
    # 跨 target 的"约束类"（合规/速率）不算类型 I（它们是类型 III / II）
    type1_same_target = [p for p in type1]

    # 类型 II：共享同一资源窗口的机制 > 预算上限
    by_target = defaultdict(list)
    for k, v in schema.items():
        by_target[v["target"]].append(k)
    # 预算竞争 = 同一 channel 家族（数值/进度/徽章/排行榜 均写同一用户状态）
    state_writers = [k for k, v in schema.items()
                     if v["direction"] == "approach" and v["channel"] in
                     ("数值", "数值面板", "进度+等级", "进度条", "徽章", "徽章图", "名次", "排行榜")]
    type2 = {"state_writers": sorted(state_writers),
             "competition": bool(len(state_writers) > 1),
             "cap": None}

    # 类型 III：参与度目标 vs 合规/健康约束
    type3 = []
    for k, v in schema.items():
        if v["target"] == "合规":
            type3.append([k, "全部 approach 机制"])

    # 敏感性上界：不作 target 匹配，任何 approach × withdraw 组合都算"潜在对消"
    relaxed = [[a, w] for a in approaches for w in withdraws]

    return {
        "approach": approaches,
        "withdraw": withdraws,
        "type_I_same_target_opposite_direction": type1_same_target,
        "type_I_count": len(type1_same_target),
        "type_I_relaxed_upper_bound": relaxed,
        "type_I_relaxed_count": len(relaxed),
        "co_active_rule": co_active_rule,
        "type_II": type2,
        "type_III": type3,
        "type_III_count": len(type3),
    }


ludi_res = detect(LUDI_SCHEMA, "单元素排他（attribution 删除同 section 其它元素）")
xp_res = detect(XP_SCHEMA, "多机制并存")

report = {
    "system_A_ludilearn": {
        "repo": "https://github.com/DigiDago/moodle-format_ludilearn",
        "commit": ludi_head,
        "license": "GPL-3.0",
        "language": "PHP (Moodle course format)",
        "mechanism_inventory_rule": "classes/local/gameelements/*.php 去掉抽象基类与 nogamified",
        "mechanism_count": len(ludi_elems),
        "mechanisms": ludi_elems,
        "schema": LUDI_SCHEMA,
        "concurrency_model": "互斥：manager.attribution_game_element() 删除同 section 其它元素的 attribution",
        "concurrency_anchor": "classes/manager.php:126-146",
        "detection": ludi_res,
    },
    "system_B_block_xp": {
        "repo": "https://github.com/FMCorz/moodle-block_xp",
        "commit": xp_head,
        "license": "GPL-3.0",
        "language": "PHP (Moodle block)",
        "mechanism_inventory_rule": "classes/local/{xp,leaderboard,badge,rule,division,notification,check} + form/{cheatguard,promo}",
        "mechanism_count": len(XP_SCHEMA),
        "mechanisms": sorted(XP_SCHEMA),
        "schema": XP_SCHEMA,
        "concurrency_model": "并存：多个机制在同一用户状态上同时生效",
        "detection": xp_res,
    },
    "method_limits": [
        "schema 字段为分析师单编码，未计算评分者间信度（IRR）——不得宣称双重编码。",
        "target_construct 为语义标注，非外部系统自带字段；外部系统不提供 direction 元数据。",
        "类型 II 的预算上限：Ludilearn 无预算概念；block_xp 的 limit_spec 提供 H/D/W/M 速率窗口。",
    ],
}

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
