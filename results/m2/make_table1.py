#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 机制普查表（论文 Table 1 素材）—— 54 机制 × 多维属性，输出 CSV/LaTeX/XLSX。"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(r"E:\learnflow")
BACKEND = REPO / "learnflow-backend"
OUT = Path(r"E:/learnflow\results\m2")
sys.path.insert(0, str(BACKEND))

from app.services import mechanism_registry as MR                      # noqa: E402
from app.services.learning_orchestrator import PIPELINE_MECHANISM_MAP  # noqa: E402
from app.services.mechanism_arbitrator import MechanismArbitrator       # noqa: E402

GOV = REPO / "docs" / "LearnFlow_机制治理与落实方案.md"
text = GOV.read_text(encoding="utf-8")
SEC = re.compile(r"^###\s+([A-H])\.\s*([^（(]*)[（(](\d+)[）)]", re.MULTILINE)
ROW = re.compile(r"^\|\s*(LF-M\d{2})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", re.MULTILINE)
secs = [(m.start(), m.group(1)) for m in SEC.finditer(text)]


def letter(pos):
    cur = None
    for s, l in secs:
        if s <= pos:
            cur = l
        else:
            break
    return cur


gov = {}
for m in ROW.finditer(text):
    gov[m.group(1)] = {"letter": letter(m.start()), "stage_doc": m.group(4).strip(),
                       "cat_doc": m.group(5).strip()}

wired = set(k for ks in PIPELINE_MECHANISM_MAP.values() for k in ks)
gated = set(re.findall(r'is_enabled\("([a-z0-9_]+)"\)', (BACKEND / "app/services/learning_orchestrator.py").read_text(encoding="utf-8")))
DIRV = MechanismArbitrator._DIRECTION

rows = []
for s in MR.all_mechanisms():
    g = gov.get(s.id, {})
    rows.append({
        "id": s.id, "key": s.key, "name_zh": s.name_zh, "name_en": s.name_en,
        "governance_letter": g.get("letter", ""), "gov_category_zh": g.get("cat_doc", ""),
        "registry_category": s.category, "stage": s.stage,
        "disposition": s.disposition, "maturity": s.maturity,
        "direction": DIRV.get(s.id, "unassigned"),
        "step_mapped": "Y" if s.key in wired else "N",
        "is_enabled_gated": "Y" if s.key in gated else "N",
        "impl_ref": s.impl_ref,
    })

OUT.mkdir(parents=True, exist_ok=True)
csv_p = OUT / "table1_mechanism_census.csv"
with csv_p.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# LaTeX（booktabs）
tex = [r"\begin{table}[htbp]", r"\centering",
       r"\caption{LearnFlow 54 个游戏化机制普查（治理类别 × 注册表类别 × 接线强度）}",
       r"\label{tab:m2-census}", r"\small",
       r"\begin{tabular}{lllllcc}", r"\toprule",
       r"ID & 机制 & 治理类别 & 注册表类别 & 阶段 & 步骤映射 & 门控 \\", r"\midrule"]
for r in rows:
    tex.append(f"{r['id']} & {r['name_zh']} & {r['governance_letter']} & "
               f"{r['registry_category']} & {r['stage']} & {r['step_mapped']} & {r['is_enabled_gated']} \\\\")
tex += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
(OUT / "table1_mechanism_census.tex").write_text("\n".join(tex), encoding="utf-8")

try:
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "census"
    ws.append(list(rows[0]))
    for r in rows:
        ws.append(list(r.values()))
    wb.save(OUT / "table1_mechanism_census.xlsx")
    xlsx = "ok"
except ImportError:
    xlsx = "openpyxl 缺失，未生成 xlsx"

summary = {
    "n": len(rows),
    "governance_letter_counts": dict(Counter(r["governance_letter"] for r in rows)),
    "registry_category_counts": dict(Counter(r["registry_category"] for r in rows)),
    "stage_counts": dict(Counter(r["stage"] for r in rows)),
    "maturity_counts": dict(Counter(r["maturity"] for r in rows)),
    "disposition_counts": dict(Counter(r["disposition"] for r in rows)),
    "direction_counts": dict(Counter(r["direction"] for r in rows)),
    "step_mapped": sum(1 for r in rows if r["step_mapped"] == "Y"),
    "is_enabled_gated": sum(1 for r in rows if r["is_enabled_gated"] == "Y"),
    "xlsx": xlsx,
}
(OUT / "table1_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
