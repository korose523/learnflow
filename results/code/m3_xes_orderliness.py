#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XES3G5M 有序性检验：KC 树深度 / KC 路径长度 vs 经验难度（M3 有序动作空间的现实依据）。"""
import csv
import json
import math
import os
from collections import defaultdict

import numpy as np
from scipy import stats

BASE = r"E:/learnflow"
XES = os.path.join(BASE, "data", "xes3g5m", "XES3G5M")
OUT = os.path.join(BASE, "results", "code")

# 1) 题目元数据：KC 路径深度
with open(os.path.join(XES, "metadata", "questions.json"), encoding="utf-8") as f:
    questions = json.load(f)
q_depth, q_text_avail = {}, 0
for qid, meta in questions.items():
    routes = meta.get("kc_routes") or []
    depth = max((r.count("----") + 1) for r in routes) if routes else 0
    q_depth[qid] = depth
    if meta.get("content"):
        q_text_avail += 1
print(f"questions: {len(questions)}, with text: {q_text_avail}")

# 2) 交互聚合（train_valid_sequences.csv：questions/responses 两列序列）
per_q = defaultdict(lambda: [0, 0])
p = os.path.join(XES, "kc_level", "train_valid_sequences.csv")
with open(p, encoding="utf-8", errors="replace") as f:
    r = csv.DictReader(f)
    for row in r:
        qs = (row.get("questions") or "").split(",")
        rs = (row.get("responses") or "").split(",")
        for q, c in zip(qs, rs):
            if q in ("-1", "", "NaN") or c not in ("0", "1"):
                continue
            e = per_q[q]
            e[0] += 1
            e[1] += int(c)
print(f"questions with interactions: {len(per_q)}")

# 3) 难度 vs 深度
depths, diffs, succs = [], [], []
for q, (n, nc) in per_q.items():
    if n < 100 or q not in q_depth or q_depth[q] == 0:
        continue
    ph = (nc + 0.5) / (n + 1.0)
    depths.append(q_depth[q])
    diffs.append(math.log((1 - ph) / ph))   # 正 = 难
    succs.append(ph)
depths, diffs, succs = map(np.asarray, (depths, diffs, succs))
print(f"eval questions (n>=100, has KC route): {len(depths)}")
rho = stats.spearmanr(depths, diffs)
by = {}
for d in sorted(set(depths.tolist())):
    m = depths == d
    by[int(d)] = {"n_q": int(m.sum()), "mean_diff": round(float(diffs[m].mean()), 4),
                  "mean_success": round(float(succs[m].mean()), 4)}
res = {
    "n_questions_total": len(questions), "n_with_text": q_text_avail,
    "n_eval": len(depths), "min_attempts": 100,
    "spearman_depth_vs_difficulty": [round(rho.statistic, 4), round(float(rho.pvalue), 8)],
    "groups_by_kc_depth": by,
}
print("spearman depth~difficulty = %.4f (p=%.2e)" % (rho.statistic, rho.pvalue))
for d, v in by.items():
    print(f"  depth {d}: {v['n_q']} q, diff={v['mean_diff']}, success={v['mean_success']}")
with open(os.path.join(OUT, "xes3g5m_orderliness.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print("saved -> results/code/xes3g5m_orderliness.json")
