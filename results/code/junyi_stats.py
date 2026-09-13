# -*- coding: utf-8 -*-
"""Junyi Learning-Activity dataset: scale stats + M3 replay feasibility.

Outputs results/code/junyi_stats.json
Design purpose: replace M3 simulator's linspace(-2,2,10) difficulty assumption
with a real action space (per-exercise empirical difficulty from Junyi logs).
"""
import csv, json, os
from collections import Counter, defaultdict

BASE = "E:/learnflow/data/junyi"
OUT = "E:/learnflow/results/code/junyi_stats.json"

# ---------- 1. exercise metadata ----------
meta = {}          # ucid -> {difficulty, level3, level4, stage, name}
with open(os.path.join(BASE, "Info_Content.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = {
            "name": row["content_pretty_name"],
            "expert_difficulty": row["difficulty"],   # easy/normal/hard/unset
            "level3": row["level3_id"],
            "level4": row["level4_id"],
            "stage": row["learning_stage"],
        }

# ---------- 2. stream Log_Problem.csv ----------
n_rows = 0
users = set()
exer_rows = Counter()          # ucid -> attempts
exer_correct = Counter()       # ucid -> correct
exer_users = defaultdict(set)  # ucid -> distinct users (sampled cap not needed, sets of ids ok memory-wise? 72k users x ... use Counter of (ucid,user) pairs -> too big. Use per-exercise set but cap? We'll use set; 1330 exercises fine.)
user_rows = Counter()          # user -> attempts
hint_used = 0
upgrade = downgrade = 0
correct_total = 0
# sequential order check: per user, count exercises with repeat sessions
repeat_sessions = 0
# difficulty x outcome for expert-difficulty validation
diff_att = Counter()
diff_cor = Counter()

path = os.path.join(BASE, "Log_Problem.csv")
with open(path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        n_rows += 1
        u = row["uuid"]; c = row["ucid"]
        users.add(u)
        ok = row["is_correct"] == "True"
        exer_rows[c] += 1
        user_rows[u] += 1
        if ok:
            exer_correct[c] += 1
            correct_total += 1
        if row["is_hint_used"] == "True":
            hint_used += 1
        if row["is_upgrade"] == "True": upgrade += 1
        if row["is_downgrade"] == "True": downgrade += 1
        if row["exercise_problem_repeat_session"] != "1":
            repeat_sessions += 1
        exer_users[c].add(u)
        d = meta.get(c, {}).get("expert_difficulty", "unset")
        diff_att[d] += 1
        if ok: diff_cor[d] += 1
        if n_rows % 2_000_000 == 0:
            print(f"  ... {n_rows} rows", flush=True)

# ---------- 3. aggregate ----------
per_ex = []
for c, att in exer_rows.items():
    if att < 1000:            # keep exercises with enough data for arms
        continue
    m = meta.get(c, {})
    per_ex.append({
        "ucid": c,
        "attempts": att,
        "users": len(exer_users[c]),
        "success_rate": round(exer_correct[c] / att, 4),
        "expert_difficulty": m.get("expert_difficulty", "unset"),
        "stage": m.get("stage", ""),
    })
per_ex.sort(key=lambda x: -x["attempts"])

users_dist = Counter()
for u, n in user_rows.items():
    users_dist[min(n // 100 * 100, 1000)] += 1  # bucket of 100

res = {
    "dataset": "Junyi Academy Learning Activity (Kaggle, CC-BY-NC-SA-4.0)",
    "log_rows": n_rows,
    "users": len(users),
    "exercises_with_data": len(exer_rows),
    "overall_success_rate": round(correct_total / n_rows, 4),
    "hint_rate": round(hint_used / n_rows, 4),
    "upgrade_rate": round(upgrade / n_rows, 4),
    "downgrade_rate": round(downgrade / n_rows, 4),
    "repeat_session_rows": repeat_sessions,
    "user_attempts_buckets_100": {str(k): v for k, v in sorted(users_dist.items())},
    "expert_difficulty_outcomes": {
        d: {"attempts": diff_att[d], "success": round(diff_cor[d] / diff_att[d], 4)}
        for d in ["easy", "normal", "hard", "unset"] if diff_att[d]
    },
    "top_exercises_min1000_attempts": per_ex[:50],
    "n_exercises_ge1000_attempts": len(per_ex),
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("rows", n_rows, "users", len(users), "saved ->", OUT)
