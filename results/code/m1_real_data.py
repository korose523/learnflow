#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1 真实数据实验：assist09（最优错误率 + 难度源漂移）与 DBE-KT22（专家 vs 经验难度）。
纯 stdlib + numpy/scipy，确定性输出，原始 JSON 落盘 results/code/。"""
import csv
import json
import math
import os
from collections import defaultdict

import numpy as np
from scipy import stats

BASE = r"E:/learnflow"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "results", "code")
os.makedirs(OUT, exist_ok=True)

results = {}

# ============================== E-A: assist09 ==============================
print("=" * 60)
print("E-A assist09")
p = os.path.join(DATA, "assist09_corrected.csv")
rows = []
with open(p, encoding="utf-8", errors="replace") as f:
    r = csv.DictReader(f)
    for d in r:
        c = d.get("correct")
        if c in ("0", "1"):
            rows.append((int(d["order_id"]), d["user_id"], d["problem_id"],
                         int(c), d["original"], d["ms_first_response"], d["attempt_count"]))
print("valid rows:", len(rows))

# --- A1 滑窗最优错误率 ---
by_user = defaultdict(list)
for oid, uid, pid, c, orig, ms, att in rows:
    by_user[uid].append((oid, c))
win_err = []
W = 20
for uid, seq in by_user.items():
    seq.sort()
    cs = [c for _, c in seq]
    if len(cs) < W:
        continue
    arr = np.asarray(cs, dtype=float)
    csum = np.concatenate([[0], np.cumsum(arr)])
    werr = 1.0 - (csum[W:] - csum[:-W]) / W
    win_err.append(werr)
win_err = np.concatenate(win_err)
mean_err = float(win_err.mean()); med_err = float(np.median(win_err))
hist, edges = np.histogram(win_err, bins=np.arange(0, 1.0001, 0.05))
mode_bin = float((edges[hist.argmax()] + edges[hist.argmax() + 1]) / 2)
share_807 = float(((win_err >= 0.17) & (win_err <= 0.23)).mean())   # 错误率 17–23% ≈ 成功率 77–83%
share_85 = float(((win_err >= 0.10) & (win_err <= 0.20)).mean())    # 成功率 80–90%
results["assist09_window"] = {
    "window": W, "n_windows": int(win_err.size), "n_users_used": len(by_user),
    "mean_error_rate": round(mean_err, 4), "median_error_rate": round(med_err, 4),
    "modal_bin_center": round(mode_bin, 2),
    "share_err_in_17_23pct": round(share_807, 4),
    "share_err_in_10_20pct": round(share_85, 4),
    "hist_05bins": hist.tolist(),
}
print("window: mean_err=%.4f median=%.4f mode_bin=%.2f share(77-83%%)=%.4f" %
      (mean_err, med_err, mode_bin, share_807))

# --- A2 难度源一致性（3 源）---
per_prob = defaultdict(lambda: [0, 0, [], []])   # n, ncorrect, ms, att
for oid, uid, pid, c, orig, ms, att in rows:
    if orig != "1":
        continue
    e = per_prob[pid]
    e[0] += 1; e[1] += c
    try:
        e[2].append(float(ms))
    except ValueError:
        pass
    try:
        e[3].append(float(att))
    except ValueError:
        pass
probs, S_p, S_t, S_a = [], [], [], []
for pid, (n, nc, ms, att) in per_prob.items():
    if n < 50 or not ms or not att:
        continue
    ph = (nc + 0.5) / (n + 1.0)          # Laplace 平滑
    b = math.log(ph / (1 - ph))          # IRT-1PL 难度（越大越难）
    probs.append(pid); S_p.append(b); S_t.append(float(np.median(ms))); S_a.append(float(np.mean(att)))
S_p, S_t, S_a = map(np.asarray, (S_p, S_t, S_a))
print("problems used:", len(probs))
rho_pt = stats.spearmanr(S_p, S_t); rho_pa = stats.spearmanr(S_p, S_a); rho_ta = stats.spearmanr(S_t, S_a)
results["assist09_sources"] = {
    "n_problems": len(probs), "min_attempts": 50,
    "spearman_irt_vs_time": [round(rho_pt.statistic, 4), round(float(rho_pt.pvalue), 6)],
    "spearman_irt_vs_attempts": [round(rho_pa.statistic, 4), round(float(rho_pa.pvalue), 6)],
    "spearman_time_vs_attempts": [round(rho_ta.statistic, 4), round(float(rho_ta.pvalue), 6)],
}
print("spearman irt~time=%.4f irt~att=%.4f time~att=%.4f" %
      (rho_pt.statistic, rho_pa.statistic, rho_ta.statistic))

# --- A3 有效权重漂移（真实数据版 m1_instability）---
def minmax(x):
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)

def eff_weights(Z, w):
    S = Z @ w
    vS = S.var()
    return np.array([w[k] * np.cov(Z[:, k], S)[0, 1] / vS for k in range(Z.shape[1])])

w3 = np.array([0.4, 0.3, 0.3])
Z0 = np.column_stack([minmax(S_p), minmax(S_t), minmax(S_a)])
pi0 = eff_weights(Z0, w3)

def t_logit_minmax(x):
    z = minmax(x); z = np.clip(z, 1e-4, 1 - 1e-4); return np.log(z / (1 - z))

def t_probit(x):
    z = (x - x.mean()) / (x.std() + 1e-12); return stats.norm.cdf(z)

def t_log(x):
    return np.log(x - x.min() + 1e-6)

drift = {}
for name, src in [("irt", S_p), ("time", S_t), ("attempts", S_a)]:
    for tname, tf in [("logit_minmax", t_logit_minmax), ("probit_std", t_probit), ("log", t_log)]:
        try:
            cols = [minmax(S_p), minmax(S_t), minmax(S_a)]
            k = {"irt": 0, "time": 1, "attempts": 2}[name]
            cols[k] = minmax(tf(src))
            Z = np.column_stack(cols)
            pi = eff_weights(Z, w3)
            l1 = float(np.abs(pi - pi0).sum())
            rev = int(sum(1 for i in range(3) for j in range(i + 1, 3)
                          if (pi0[i] - pi0[j]) * (pi[i] - pi[j]) < 0))
            drift[f"{name}|{tname}"] = {"L1": round(l1, 4), "rank_reversals": rev,
                                        "pi": [round(v, 4) for v in pi]}
        except Exception as ex:
            drift[f"{name}|{tname}"] = {"error": str(ex)[:80]}
l1s = [v["L1"] for v in drift.values() if "L1" in v]
revs = [v["rank_reversals"] for v in drift.values() if "rank_reversals" in v]
results["assist09_drift"] = {
    "weights_nominal": w3.tolist(), "pi_baseline": [round(v, 4) for v in pi0],
    "transforms": drift,
    "L1_mean": round(float(np.mean(l1s)), 4), "L1_max": round(float(np.max(l1s)), 4),
    "reversal_rate": round(float(np.mean([1 if r > 0 else 0 for r in revs])), 4),
}
print("drift: L1_mean=%.4f L1_max=%.4f reversal_rate=%.2f" %
      (results["assist09_drift"]["L1_mean"], results["assist09_drift"]["L1_max"],
       results["assist09_drift"]["reversal_rate"]))

# ============================== E-B: DBE-KT22 ==============================
print("=" * 60)
print("E-B DBE-KT22")
qdiff = {}
with open(os.path.join(DATA, "dbe_kt22", "csv", "Questions.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            qdiff[d["id"]] = int(d["difficulty"])
        except (ValueError, TypeError):
            pass
tx = []
with open(os.path.join(DATA, "dbe_kt22", "csv", "Transaction.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        a = d.get("answer_state", "").strip().lower()
        if a in ("true", "false"):
            tx.append((d["student_id"], d["question_id"], 1 if a == "true" else 0,
                       d.get("difficulty_feedback", ""), d.get("trust_feedback", "")))
print("transactions:", len(tx), "| questions with difficulty:", len(qdiff))

per_q = defaultdict(lambda: [0, 0])
self_fb = defaultdict(lambda: defaultdict(int))   # q -> fb -> count
for sid, qid, c, dfb, tfb in tx:
    e = per_q[qid]; e[0] += 1; e[1] += c
    if dfb in ("1", "2", "3", "4", "5"):
        self_fb[qid][dfb] += 1

qs, emp, succ, lvl = [], [], [], []
for qid, (n, nc) in per_q.items():
    if qid not in qdiff or n < 20:
        continue
    ph = (nc + 0.5) / (n + 1.0)
    qs.append(qid); succ.append(ph); lvl.append(qdiff[qid])
    # 经验难度：logit((1-ph)/ph)，正值 = 更难（避免"越大越容易"的符号歧义）
    emp.append(math.log((1 - ph) / ph))
emp, lvl = np.asarray(emp), np.asarray(lvl)
succ = np.asarray(succ)
rho = stats.spearmanr(lvl, emp)
groups = {int(g): {"n_q": int((lvl == g).sum()),
                   "mean_emp_difficulty": round(float(emp[lvl == g].mean()), 4),
                   "mean_success": round(float(succ[lvl == g].mean()), 4)}
          for g in sorted(set(lvl.tolist()))}
results["dbe_kt22"] = {
    "n_transactions": len(tx), "n_questions_eval": len(qs), "min_attempts": 20,
    "spearman_expert_vs_empirical": [round(rho.statistic, 4), round(float(rho.pvalue), 6)],
    "groups_by_expert_difficulty": groups,
}
print("spearman expert~empirical = %.4f (p=%.2e)" % (rho.statistic, rho.pvalue))
for g, v in groups.items():
    print("  level %d: %d questions, mean_emp_diff=%.3f (success≈%.3f)" %
          (g, v["n_q"], v["mean_emp_difficulty"], v["mean_success"]))

with open(os.path.join(OUT, "real_data_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("saved -> results/code/real_data_results.json")
