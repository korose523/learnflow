#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 三类冲突静态检测（可复算）—— 只读仓库，输出到 results/m2/。

产出 E1 的第 2/3/4 项：
  * 54 机制 × 8 理论类别（治理文档 A–H）分类
  * 编排器门控映射数 / 仅源码文本引用数 / is_enabled 门控数
  * 三类冲突（效果方向 / 预算竞争 / schema 归类）在注册表内实际检出清单
  * 不可归类比例

所有输入均来自仓库单一事实源，不做人工臆测：
  * app/services/mechanism_registry.py      —— 54 机制规格（category/maturity/stage/...）
  * app/services/mechanism_arbitrator.py    —— _DIRECTION 方向表 + BudgetPolicy
  * app/services/learning_orchestrator.py   —— PIPELINE_MECHANISM_MAP + is_enabled 字面量
  * docs/LearnFlow_机制治理与落实方案.md     —— §2.4 八类别清单表
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(r"E:\learnflow")
BACKEND = REPO / "learnflow-backend"
OUT = Path(r"E:/learnflow\results\m2")
sys.path.insert(0, str(BACKEND))

from app.services import mechanism_registry as MR          # noqa: E402
from app.services.learning_orchestrator import PIPELINE_MECHANISM_MAP  # noqa: E402
from app.services.mechanism_arbitrator import BudgetPolicy  # noqa: E402

GOV_DOC = REPO / "docs" / "LearnFlow_机制治理与落实方案.md"
ORCH = BACKEND / "app" / "services" / "learning_orchestrator.py"
ARB = BACKEND / "app" / "services" / "mechanism_arbitrator.py"

# ── 1. 解析治理文档 §2.4 的 8 类别清单表 ────────────────────────────────
ROW_RE = re.compile(
    r"^\|\s*(LF-M\d{2})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|"
    r"([^|]*)\|([^|]*)\|([^|]*)\|",
    re.MULTILINE,
)
SEC_RE = re.compile(r"^###\s+([A-H])\.\s*([^（(]*)[（(](\d+)[）)]", re.MULTILINE)

text = GOV_DOC.read_text(encoding="utf-8")
# 定位每个 ### 段落起点，便于给行分配 letter
sec_pos = [(m.start(), m.group(1), m.group(2).strip(), int(m.group(3)))
           for m in SEC_RE.finditer(text)]


def letter_of(pos: int) -> str | None:
    cur = None
    for start, letter, _t, _n in sec_pos:
        if start <= pos:
            cur = letter
        else:
            break
    return cur


gov_rows = {}
for m in ROW_RE.finditer(text):
    mid = m.group(1)
    gov_rows[mid] = {
        "name_zh": m.group(2).strip(),
        "stage_doc": m.group(4).strip(),
        "registry_cat_doc": m.group(5).strip(),
        "impl_ref_doc": m.group(7).strip().replace("`", ""),
        "maturity_sym": m.group(8).strip(),
        "disposition_doc": m.group(9).strip(),
        "runtime_doc": m.group(10).strip(),
        "governance_letter": letter_of(m.start()),
    }

gov_letter_counts = Counter(r["governance_letter"] for r in gov_rows.values())

# ── 2. 注册表规格 ───────────────────────────────────────────────────────
specs = {s.id: s for s in MR.all_mechanisms()}
reg_cat_counts = Counter(s.category for s in specs.values())
reg_maturity_counts = Counter(s.maturity for s in specs.values())

# ── 3. 编排器接线强度 ───────────────────────────────────────────────────
wired = set()
for keys in PIPELINE_MECHANISM_MAP.values():
    wired.update(keys)
orch_text = ORCH.read_text(encoding="utf-8")
gated = set(re.findall(r'is_enabled\("([a-z0-9_]+)"\)', orch_text))
key2id = {s.key: s.id for s in specs.values()}
wired_ids = sorted(key2id[k] for k in wired)
gated_ids = sorted(key2id[k] for k in gated)

# ── 4. 方向表 (效果方向冲突的唯一仓库内依据) ────────────────────────────
arb_text = ARB.read_text(encoding="utf-8")
dir_block = re.search(r"_DIRECTION:\s*Dict\[str,\s*str\]\s*=\s*\{(.*?)\}", arb_text, re.S)
direction = dict(re.findall(r'"(LF-M\d{2})":\s*"(approach|withdraw|neutral)"', dir_block.group(1)))
approach = sorted(k for k, v in direction.items() if v == "approach")
withdraw = sorted(k for k, v in direction.items() if v == "withdraw")
risk_block = re.search(r"_ADDICTION_RISK:\s*Dict\[str,\s*float\]\s*=\s*\{(.*?)\}", arb_text, re.S)
addiction_risk = dict(re.findall(r'"(LF-M\d{2})":\s*([\d.]+)', risk_block.group(1)))

bp = BudgetPolicy()

# ── 5. 运行时 Effect 生产者 (谁真的进仲裁器) ────────────────────────────
effect_producers = {}
for f in (BACKEND / "app").rglob("*.py"):
    src = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"Effect\((.*?)\)", src, re.S):
        mid = re.search(r'mechanism_id="(LF-M\d{2})"', m.group(1))
        if mid:
            vis = re.search(r"user_visible=(\w+)", m.group(1))
            hc = re.search(r"health_critical=(\w+)", m.group(1))
            cost = re.search(r"cost=([\d.]+)", m.group(1))
            prio = re.search(r"priority=(\d+)", m.group(1))
            effect_producers.setdefault(mid.group(1), []).append({
                "file": str(f.relative_to(BACKEND)).replace("\\", "/"),
                "user_visible": vis.group(1) if vis else "?",
                "health_critical": hc.group(1) if hc else "?",
                "cost": float(cost.group(1)) if cost else None,
                "priority": int(prio.group(1)) if prio else None,
            })

# ── 6. 冲突检测 ─────────────────────────────────────────────────────────
# 6a. 效果方向冲突: approach × withdraw (可能对消)
dir_pairs_loose = [(a, w) for a in approach for w in withdraw]
# 文档锚定的同 target_construct(=时长) 子集
canonical_target_shi = {"LF-M44": "时长", "LF-M51": "时长", "LF-M52": "时长"}
canonical_pairs = [("LF-M44", "LF-M51"), ("LF-M44", "LF-M52")]

# 6b. 预算竞争: 进仲裁器且 user_visible 且非 health 的候选共享同一预算
budget_competing = sorted(
    mid for mid, rows in effect_producers.items()
    if any(r["user_visible"] == "True" and r["health_critical"] == "False" for r in rows)
)
budget_pairs = [(a, b) for i, a in enumerate(budget_competing)
                for b in budget_competing[i + 1:]]

# 6c. schema 归类冲突: 治理文档 8 类别字母 → 注册表 5 类别 是否多对多
letter_to_regcat = defaultdict(set)
for mid, r in gov_rows.items():
    if mid in specs:
        letter_to_regcat[r["governance_letter"]].add(specs[mid].category)
ambiguous_letters = {k: sorted(v) for k, v in letter_to_regcat.items() if len(v) > 1}

# 6d. 不可归类比例
no_direction = sorted(set(specs) - set(direction))
no_governance = sorted(set(specs) - set(gov_rows))

result = {
    "git_commit": __import__("subprocess").run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True
    ).stdout.strip(),
    "1_registry": {
        "count": MR.count(),
        "fingerprint": MR.registry_fingerprint(),
        "id_range": [MR.ids()[0], MR.ids()[-1]],
        "registry_category_counts": dict(reg_cat_counts),
        "registry_maturity_counts": dict(reg_maturity_counts),
        "governance_letter_counts": dict(sorted(gov_letter_counts.items())),
        "registry_category_vs_governance_letter": {
            letter: {mid: specs[mid].category for mid in sorted(gov_rows)
                     if gov_rows[mid]["governance_letter"] == letter and mid in specs}
            for letter in sorted(letter_to_regcat)
        },
    },
    "2_wiring": {
        "step_mapped_total": len(wired_ids),
        "step_mapped_ids": wired_ids,
        "is_enabled_gated_total": len(gated_ids),
        "is_enabled_gated_ids": gated_ids,
        "step_map_detail": {str(k): v for k, v in PIPELINE_MECHANISM_MAP.items()},
        "not_step_mapped_total": 54 - len(wired_ids),
        "not_step_mapped_ids": sorted(set(specs) - set(wired_ids)),
    },
    "3_conflicts": {
        "type_I_direction": {
            "approach_ids": approach,
            "withdraw_ids": withdraw,
            "direction_table_coverage": f"{len(direction)}/54",
            "potential_pairs_upper_bound": len(dir_pairs_loose),
            "potential_pairs_list": dir_pairs_loose,
            "doc_pinned_same_target_pairs": canonical_pairs,
            "runtime_detectable": "见 3_runtime",
        },
        "type_II_budget": {
            "budget_policy": {
                "max_per_session": bp.max_per_session,
                "max_per_day": bp.max_per_day,
                "max_cost_per_session": bp.max_cost_per_session,
                "min_interval_sec": bp.min_interval_sec,
            },
            "runtime_visible_candidates": budget_competing,
            "competing_pairs": budget_pairs,
            "step13_mechanisms_bypass_arbitration": len(PIPELINE_MECHANISM_MAP[13]),
        },
        "type_III_schema": {
            "ambiguous_governance_letters": ambiguous_letters,
            "letter_to_registry_categories": {k: sorted(v) for k, v in letter_to_regcat.items()},
        },
    },
    "4_unclassifiable": {
        "no_direction_annotation": len(no_direction),
        "no_direction_ratio": round(len(no_direction) / 54, 4),
        "no_direction_ids": no_direction,
        "no_governance_row": len(no_governance),
        "registry_categories_count": len(MR.CATEGORIES),
        "governance_letters_count": len(gov_letter_counts),
    },
    "5_runtime_producers": effect_producers,
    "6_addiction_risk": addiction_risk,
    "7_governance_vs_registry_maturity": {
        "registry": dict(reg_maturity_counts),
        "gov_symbol_counts": dict(Counter(r["maturity_sym"] for r in gov_rows.values())),
    },
}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "m2_conflict_analysis.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(result, ensure_ascii=False, indent=2))
