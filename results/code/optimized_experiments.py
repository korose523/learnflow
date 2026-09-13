#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""优化版实验（O1-O3）：针对第一批真实结果暴露的三个弱点做算法优化后重做。
O1 assist09：min-max 线性融合 → 分位数/logit 公制融合（对单调重参数化严格不变）
O2 DBE-KT22：原始正确率 → 联合 IRT-1PL（学生能力 + 题目难度联合梯度上升）
O3 XES3G5M：树深度代理 → KC 级难度沿树边的一致性检验（相邻节点难度梯度）
附带 assist09 滑窗敏感性（tutor_mode / original 过滤）。
全部确定性，产物：results/code/optimized_results.json"""
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
R = {}

# ================= O1 assist09：公制优化 =================
rows = []
with open(os.path.join(DATA, "assist09_corrected.csv"), encoding="utf-8", errors="replace") as f:
    for d in csv.DictReader(f):
        if d.get("correct") in ("0", "1"):
            rows.append(d)
print("assist09 rows:", len(rows))

def window_stats(sub, W=20):
    by_user = defaultdict(list)
    for d in sub:
        by_user[d["user_id"]].append((int(d["order_id"]), int(d["correct"])))
    out = []
    for uid, seq in by_user.items():
        seq.sort()
        cs = [c for _, c in seq]
        if len(cs) < W:
            continue
        arr = np.asarray(cs, float)
        csu = np.concatenate([[0], np.cumsum(arr)])
        out.append(1.0 - (csu[W:] - csu[:-W]) / W)
    if not out:
        return {"n_windows": 0, "mean_err": None, "median_err": None,
                "modal_bin": None, "share_success_77_83": None}
    a = np.concatenate(out)
    hist, edges = np.histogram(a, bins=np.arange(0, 1.0001, 0.05))
    return {"n_windows": int(a.size), "mean_err": round(float(a.mean()), 4),
            "median_err": round(float(np.median(a)), 4),
            "modal_bin": [round(float(edges[hist.argmax()]), 2), round(float(edges[hist.argmax() + 1]), 2)],
            "share_success_77_83": round(float(((a >= 0.17) & (a <= 0.23)).mean()), 4)}

R["o1_window_sensitivity"] = {
    "all": window_stats(rows),
    "original_only(main_problem)": window_stats([d for d in rows if d["original"] == "1"]),
    "tutor_mode_test": window_stats([d for d in rows if d.get("tutor_mode") == "test"]),
    "no_hint_correction": window_stats([d for d in rows if d.get("hint_count", "0") in ("0", "")]),
}
for k, v in R["o1_window_sensitivity"].items():
    print(f"[O1] {k}: mean={v['mean_err']} mode={v['modal_bin']}")

# 难度源（复用第一批口径）
per_prob = defaultdict(lambda: [0, 0, [], []])
for d in rows:
    if d["original"] != "1":
        continue
    e = per_prob[d["problem_id"]]
    e[0] += 1; e[1] += int(d["correct"])
    try: e[2].append(float(d["ms_first_response"]))
    except ValueError: pass
    try: e[3].append(float(d["attempt_count"]))
    except ValueError: pass
probs, S_p, S_t, S_a = [], [], [], []
for pid, (n, nc, ms, att) in per_prob.items():
    if n < 50 or not ms or not att:
        continue
    ph = (nc + 0.5) / (n + 1.0)
    probs.append(pid)
    S_p.append(math.log((1 - ph) / ph))       # 难度（正=难）
    S_t.append(float(np.median(ms))); S_a.append(float(np.mean(att)))
S_p, S_t, S_a = map(np.asarray, (S_p, S_t, S_a))

def minmax(x):
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)

def ecdf_logit(x):
    """经验 CDF → logit（对任意严格单调变换严格不变）"""
    order = np.argsort(np.argsort(x))          # 秩
    u = (order + 0.5) / len(x)                 # 分位数
    u = np.clip(u, 1e-4, 1 - 1e-4)
    return np.log(u / (1 - u))

def eff_weights(Z, w):
    S = Z @ w
    vS = S.var()
    return np.array([w[k] * np.cov(Z[:, k], S)[0, 1] / vS for k in range(Z.shape[1])])

def t_logit_minmax(x):
    z = minmax(x); z = np.clip(z, 1e-4, 1 - 1e-4); return np.log(z / (1 - z))
def t_probit(x):
    z = (x - x.mean()) / (x.std() + 1e-12); return stats.norm.cdf(z)
def t_log(x):
    return np.log(x - x.min() + 1e-6)

w3 = np.array([0.4, 0.3, 0.3])
TRANSFORMS = [("logit_minmax", t_logit_minmax), ("probit_std", t_probit), ("log", t_log)]
KEY = {"irt": 0, "time": 1, "attempts": 2}

def drift_experiment(metric):
    """metric: 'minmax' 或 'ecdf_logit' —— 各源先变换再融合"""
    def prep(x):
        return minmax(x) if metric == "minmax" else ecdf_logit(x)
    Z0 = np.column_stack([prep(S_p), prep(S_t), prep(S_a)])
    pi0 = eff_weights(Z0, w3)
    l1s, revs = [], []
    for name, src in [("irt", S_p), ("time", S_t), ("attempts", S_a)]:
        for tname, tf in TRANSFORMS:
            cols = [prep(S_p), prep(S_t), prep(S_a)]
            cols[KEY[name]] = prep(tf(src))
            pi = eff_weights(np.column_stack(cols), w3)
            l1 = float(np.abs(pi - pi0).sum())
            rev = int(sum(1 for i in range(3) for j in range(i + 1, 3)
                          if (pi0[i] - pi0[j]) * (pi[i] - pi[j]) < 0))
            l1s.append(l1); revs.append(rev)
    return {"pi_baseline": [round(v, 4) for v in pi0],
            "L1_mean": round(float(np.mean(l1s)), 4), "L1_max": round(float(np.max(l1s)), 4),
            "reversal_rate": round(float(np.mean([1 if r > 0 else 0 for r in revs])), 4)}

R["o1_metric_comparison"] = {
    "A_minmax_linear": drift_experiment("minmax"),
    "B_ecdf_logit": drift_experiment("ecdf_logit"),
}
print("[O1] A minmax:", R["o1_metric_comparison"]["A_minmax_linear"]["L1_mean"],
      "| B ecdf_logit:", R["o1_metric_comparison"]["B_ecdf_logit"]["L1_mean"])

# ================= O2 DBE-KT22：IRT-1PL 优化难度估计 =================
qdiff = {}
with open(os.path.join(DATA, "dbe_kt22", "csv", "Questions.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try: qdiff[d["id"]] = int(d["difficulty"])
        except (ValueError, TypeError): pass
tx = []
with open(os.path.join(DATA, "dbe_kt22", "csv", "Transaction.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        a = (d.get("answer_state") or "").strip().lower()
        if a in ("true", "false"):
            tx.append((d["student_id"], d["question_id"], 1 if a == "true" else 0))
sids = sorted({s for s, _, _ in tx}); qids = sorted({q for _, q, _ in tx if q in qdiff})
si = {s: i for i, s in enumerate(sids)}; qi = {q: i for i, q in enumerate(qids)}
S, Q, Y = [], [], []
for s, q, c in tx:
    if q in qi:
        S.append(si[s]); Q.append(qi[q]); Y.append(c)
S, Q, Y = map(np.asarray, (S, Q, Y))
print("[O2] students:", len(sids), "questions:", len(qids), "obs:", len(Y))

def irt1pl(S, Q, Y, n_iter=300, lr=0.05):
    nS, nQ = S.max() + 1, Q.max() + 1
    theta = np.zeros(nS); b = np.zeros(nQ)   # p = sigma(theta - b)
    for it in range(n_iter):
        z = theta[S] - b[Q]
        p = 1 / (1 + np.exp(-z))
        e = Y - p
        gt = np.bincount(S, weights=e, minlength=nS)
        gb = -np.bincount(Q, weights=e, minlength=nQ)
        theta += lr * gt / (np.bincount(S, minlength=nS) ** 0.5 + 1e-9)
        b += lr * gb / (np.bincount(Q, minlength=nQ) ** 0.5 + 1e-9)
        theta -= 0.001 * theta               # 弱正则
        b -= 0.001 * b
    return theta, b

theta, b = irt1pl(S, Q, Y)
lvl = np.array([qdiff[qids[j]] for j in range(len(qids))])
rho_irt = stats.spearmanr(lvl, b)
# 基线：原始正确率难度
cnt = np.bincount(Q, minlength=len(qids)).astype(float)
cor = np.bincount(Q, weights=Y.astype(float), minlength=len(qids))
ph = (cor + 0.5) / (cnt + 1.0)
b_raw = np.log((1 - ph) / ph)
mask = cnt >= 20
rho_raw = stats.spearmanr(lvl[mask], b_raw[mask])
# IRT 版同样过滤
rho_irt_m = stats.spearmanr(lvl[mask], b[mask])
R["o2_dbe_irt"] = {
    "n_questions_eval": int(mask.sum()),
    "baseline_raw_rate_spearman": [round(rho_raw.statistic, 4), round(float(rho_raw.pvalue), 8)],
    "optimized_irt1pl_spearman": [round(rho_irt_m.statistic, 4), round(float(rho_irt_m.pvalue), 8)],
    "irt_group_means_by_level": {int(g): round(float(b[mask & (lvl == g)].mean()), 4) for g in sorted(set(lvl[mask].tolist()))},
}
print(f"[O2] rho raw={rho_raw.statistic:.4f} -> IRT={rho_irt_m.statistic:.4f}")
print("[O2] IRT b by level:", R["o2_dbe_irt"]["irt_group_means_by_level"])

# ================= O3 XES3G5M：KC 级难度沿树边梯度 =================
XES = os.path.join(DATA, "xes3g5m", "XES3G5M")
questions = json.load(open(os.path.join(XES, "metadata", "questions.json"), encoding="utf-8"))
per_q = defaultdict(lambda: [0, 0])
with open(os.path.join(XES, "kc_level", "train_valid_sequences.csv"), encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f):
        qs = (row.get("questions") or "").split(",")
        rs = (row.get("responses") or "").split(",")
        for q, c in zip(qs, rs):
            if q in ("-1", "", "NaN") or c not in ("0", "1"):
                continue
            e = per_q[q]; e[0] += 1; e[1] += int(c)
qdiff_x = {}
for q, (n, nc) in per_q.items():
    if n >= 100 and q in questions:
        p_ = (nc + 0.5) / (n + 1.0)
        qdiff_x[q] = math.log((1 - p_) / p_)
# 节点 = 全路径；叶子题挂到路径各级（每题贡献给它路径上的每个前缀）
node_stats = defaultdict(lambda: [0, 0.0, 0])   # 直挂题数、难度和、（备用）
for q, bval in qdiff_x.items():
    route = (questions[q].get("kc_routes") or [""])[0]
    parts = route.split("----") if route else []
    leaf = "----".join(parts)
    for d in range(1, len(parts) + 1):
        node = "----".join(parts[:d])
        e = node_stats[node]
        e[0] += 1; e[1] += bval
node_diff = {k: v[1] / v[0] for k, v in node_stats.items() if v[0] >= 10}
# 树边一致性：父节点难度 < 子节点难度（越深越难的假设）
consistent, total, pairs = 0, 0, []
nodes = list(node_diff.keys())
node_set = set(nodes)
for node in nodes:
    if "----" not in node:
        continue
    parent = node.rsplit("----", 1)[0]
    if parent in node_diff and node in node_diff:
        total += 1
        ok = node_diff[node] > node_diff[parent]
        consistent += int(ok)
        pairs.append((parent.split("----")[-1], node.split("----")[-1],
                      round(node_diff[parent], 3), round(node_diff[node], 3), ok))
R["o3_xes_tree_gradient"] = {
    "n_nodes_eval": len(node_diff), "n_edges": total,
    "edge_consistency_rate": round(consistent / total, 4) if total else None,
    "interpretation": "0.5=无梯度；>0.5=树边方向与难度递增一致",
    "sample_edges": pairs[:12],
}
print(f"[O3] edges={total} consistency={R['o3_xes_tree_gradient']['edge_consistency_rate']}")

with open(os.path.join(OUT, "optimized_results.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print("saved -> results/code/optimized_results.json")
