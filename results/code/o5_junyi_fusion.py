# -*- coding: utf-8 -*-
"""O5: 融合估计器的跨系统复现（Junyi 1,326 练习，专家难度 easy/normal/hard）。

与 O4 的关键差异：Junyi 没有学生自报反馈（trust/difficulty feedback），
因此属"仅性能信号"regime，对应 O4 的等权下界情景（DBE 上为 0.2899）。
信号：成功率(反)、提示率、平均时长、平均尝试次数、升级率、降级率、重复会话率。
评估：Spearman vs 专家三档（序数 1/2/3），与"仅成功率"基线对比；5 折 CV。
输出 results/code/o5_junyi_fusion.json
"""
import csv, json, os, time
from collections import defaultdict
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o5_junyi_fusion.json"
DIFF = {"easy": 1, "normal": 2, "hard": 3}

meta = {}
with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = row["difficulty"]

agg = defaultdict(lambda: {"n": 0, "ok": 0, "hint": 0, "dur": 0.0, "att": 0,
                           "up": 0, "down": 0, "rep": 0})
t0 = time.time()
with open(BASE + "/data/junyi/Log_Problem.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        c = row["ucid"]
        a = agg[c]
        a["n"] += 1
        if row["is_correct"] == "True":
            a["ok"] += 1
        if row["is_hint_used"] == "True":
            a["hint"] += 1
        if row["is_upgrade"] == "True":
            a["up"] += 1
        if row["is_downgrade"] == "True":
            a["down"] += 1
        if row["exercise_problem_repeat_session"] != "1":
            a["rep"] += 1
        try:
            a["dur"] += float(row["total_sec_taken"])
            a["att"] += int(row["total_attempt_cnt"])
        except (ValueError, TypeError):
            pass
print("pass done", round(time.time() - t0, 1), "s; exercises:", len(agg), flush=True)

qids = [q for q, a in agg.items() if a["n"] >= 1000 and meta.get(q) in DIFF]
print("usable:", len(qids), flush=True)

def ecdf_logit(vals):
    v = np.asarray(vals, dtype=float)
    n = len(v)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / n, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))

S = {}
S["success_inverse"] = -ecdf_logit([agg[q]["ok"] / agg[q]["n"] for q in qids])
S["hint_rate"] = ecdf_logit([agg[q]["hint"] / agg[q]["n"] for q in qids])
S["duration"] = ecdf_logit([agg[q]["dur"] / agg[q]["n"] for q in qids])
S["attempts"] = ecdf_logit([agg[q]["att"] / agg[q]["n"] for q in qids])
S["upgrade_rate"] = ecdf_logit([agg[q]["up"] / agg[q]["n"] for q in qids])
S["downgrade_rate"] = ecdf_logit([agg[q]["down"] / agg[q]["n"] for q in qids])
S["repeat_session_rate"] = ecdf_logit([agg[q]["rep"] / agg[q]["n"] for q in qids])
y = np.array([DIFF[meta[q]] for q in qids])
names = list(S.keys())
M = np.vstack([S[n] for n in names]).T

per = {}
for i, n in enumerate(names):
    r = st.spearmanr(M[:, i], y)
    per[n] = [round(float(r.statistic), 4), round(float(r.pvalue), 8)]
print("per-signal:", per, flush=True)

w_eq = np.full(len(names), 1 / len(names))
rho_eq = float(st.spearmanr(M @ w_eq, y).statistic)
rho_success = float(st.spearmanr(M[:, 0], y).statistic)
print("success-only:", round(rho_success, 4), "| equal-weight:", round(rho_eq, 4), flush=True)

grid = [0.0, 0.5, 1.0, 1.5, 2.0]
def greedy(idx):
    w = w_eq.copy()
    br = st.spearmanr(M[idx] @ w, y[idx]).statistic
    for _ in range(3):
        imp = False
        for i in range(len(names)):
            for g in grid:
                w2 = w.copy(); w2[i] = g
                s = w2.sum()
                if s == 0: continue
                r = st.spearmanr(M[idx] @ (w2 / s), y[idx]).statistic
                if r > br + 1e-9:
                    br, w, imp = r, w2 / s, True
        if not imp: break
    return w, br

bw, br = greedy(np.arange(len(qids)))
rng = np.random.default_rng(42)
folds = np.array_split(rng.permutation(len(qids)), 5)
cv = []
for te in folds:
    tr = np.concatenate([f for fj, f in enumerate(folds) if not np.array_equal(f, te)])
    w_t, _ = greedy(tr)
    cv.append(float(st.spearmanr(M[te] @ w_t, y[te]).statistic))
cv_mean = float(np.mean(cv))
print("in-sample best:", round(float(br), 4), "| CV5:", round(cv_mean, 4), [round(r, 3) for r in cv], flush=True)

res = {
    "design": "O5 cross-system replication of fusion estimator (Junyi, performance signals only)",
    "n_exercises": len(qids),
    "per_signal_spearman": per,
    "success_only_spearman": round(rho_success, 4),
    "equal_weight_spearman": round(rho_eq, 4),
    "insample_best_spearman": round(float(br), 4),
    "cv5_mean_spearman": round(cv_mean, 4),
    "cv5_folds": [round(r, 4) for r in cv],
    "cv5_weights": {n: round(float(w), 3) for n, w in zip(names, bw)},
    "db_reference": {"O4_equal_weight_DBE": 0.2899, "O4_cv_DBE": 0.4778},
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
