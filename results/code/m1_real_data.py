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

from pathlib import Path
BASE = str(Path(__file__).resolve().parents[2])
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
# v2 修复（审阅意见 3.1）：窗宽 W 使错误率只取 k/W（k = 窗口内错误条数，0..W 的整数）
# 这 W+1 个离散支撑点。旧实现用 np.histogram(win_err, bins=np.arange(0, 1.0001, 0.05))，
# 区间边界与支撑点恰好重合，浮点误差（k=4 时 1 − 16/20 = 0.19999999999999996）会把
# 0.15 与 0.20 挤进同一区间、把 0.10 挤到下一区间，"众数区间 0.15–0.20"因此是分箱边界
# 伪影而非分布事实。现改为按整数错误条数 k 直接计数（整数运算、无浮点），支撑点 k/W 精确。
by_user = defaultdict(list)
for oid, uid, pid, c, orig, ms, att in rows:
    by_user[uid].append((oid, c))
W = 20
per_user_hist = []
for uid, seq in by_user.items():
    seq.sort()
    cs = [c for _, c in seq]
    if len(cs) < W:
        continue
    arr = np.asarray(cs, dtype=np.int64)
    csum = np.concatenate([[0], np.cumsum(arr)])
    err_cnt = W - (csum[W:] - csum[:-W])                  # 窗口内错误条数（整数 0..W）
    per_user_hist.append(np.bincount(err_cnt, minlength=W + 1).astype(np.int64))
per_user_hist = np.vstack(per_user_hist)                   # (使用用户数, W+1)
n_users_input = len(by_user)                               # 输入中出现的全部用户数
n_users_used = int(per_user_hist.shape[0])                 # 实际贡献滑窗的用户数（≥W 条作答）
k_counts = per_user_hist.sum(axis=0)                       # 21 个支撑点的精确频数
n_windows = int(k_counts.sum())
support = [round(k / W, 2) for k in range(W + 1)]
shares = [round(float(c) / n_windows, 6) for c in k_counts]
top = int(k_counts.max())
modal_k = [k for k in range(W + 1) if int(k_counts[k]) == top]
mean_err = float((k_counts * np.arange(W + 1)).sum()) / (n_windows * W)
cum = np.cumsum(k_counts) / n_windows
median_k = int(np.searchsorted(cum, 0.5, side="left"))
median_err = median_k / W
share_807 = float(k_counts[4]) / n_windows                 # 0.17 ≤ e ≤ 0.23 只含 0.20 一个支撑点
share_85 = float(k_counts[2:5].sum()) / n_windows          # 0.10 / 0.15 / 0.20 三个支撑点
# 众数的置信集合：离散分布的众数无点估计意义，按“学生（用户）”重抽样做 bootstrap
# 审阅意见 3.3（2026-09-29）：200 次下众数占比 95.5% 的蒙特卡洛标准误约 1.5 个百分点，
#   恰好压在 95% 门槛之上，不足以支撑结论；要求增至 2,000 次以上，且报告对象改为
#   **分布形状**（0.15~0.35 区间的平坦），而非众数位置。故 BOOT 200 -> 2000。
BOOT = 2000
rng = np.random.default_rng(20260922)
boot_argmax = np.zeros((BOOT, W + 1), dtype=np.int64)
for b in range(BOOT):
    pick = rng.integers(0, n_users_used, n_users_used)
    tot = per_user_hist[pick].sum(axis=0)
    boot_argmax[b] = (tot == tot.max()).astype(np.int64)
mode_freq = boot_argmax.mean(axis=0)
acc, ci95 = 0.0, []
for k in np.argsort(-mode_freq):
    if mode_freq[k] <= 0:
        break
    ci95.append(int(k)); acc += float(mode_freq[k])
    if acc >= 0.95:
        break
k_table = [{"k_errors": k, "error_rate": support[k], "success_rate": round(1 - k / W, 2),
            "n_windows": int(k_counts[k]), "share": shares[k],
            "bootstrap_argmax_freq": round(float(mode_freq[k]), 4)} for k in range(W + 1)]
results["assist09_window"] = {
    "window": W, "n_windows": n_windows,
    "n_users_input": n_users_input,      # 输入中出现的全部用户数（旧字段 n_users_used 误用此值）
    "n_users_used": n_users_used,        # 实际贡献滑窗的用户数（≥W 条作答）
    "mean_error_rate": round(mean_err, 4), "median_error_rate": round(median_err, 2),
    "modal_k_errors": modal_k,
    "modal_error_rate": [round(k / W, 2) for k in modal_k],
    "modal_error_rate_center": round(float(np.mean(modal_k)) / W, 4),
    "bootstrap_modal_ci95_k": ci95,
    "bootstrap_reps": BOOT,
    "bootstrap_seed": 20260922,
    "bootstrap_argmax_freq": {str(k): round(float(mode_freq[k]), 4) for k in range(W + 1)},
    # 审阅意见 3.3：报告分布形状，而非众数。plateau = 错误率 0.15~0.35（k=3..7）的窗占比。
    "plateau_0p15_0p35_share": round(float(k_counts[3:8].sum()) / n_windows, 4),
    "plateau_0p15_0p35_n_windows": int(k_counts[3:8].sum()),
    # 第一名与第二名的差距（审阅 3.3：0.25 与 0.20 只差 838 窗，占 0.29%）
    "top2_gap_windows": int(k_counts.max() - int(np.sort(k_counts)[-2])),
    "top2_gap_share": round(float(k_counts.max() - int(np.sort(k_counts)[-2])) / n_windows, 6),
    "k_frequency_table": k_table,
    "share_err_in_17_23pct": round(share_807, 4),
    "share_err_in_10_20pct": round(share_85, 4),
}
print("window: n_windows=%d users_used=%d/%d mean_err=%.4f median=%.2f modal_k=%s (err=%s) boot95_k=%s" %
      (n_windows, n_users_used, n_users_input, mean_err, median_err, modal_k,
       [round(k / W, 2) for k in modal_k], ci95))

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
# v2 修复（审阅意见 3.4）：本块使用 min-max 归一化 + π_k = w_k·Cov(z_k,S)/Var(S) 的旧符号口径，
# 与最终稿件口径不一致（L1_mean = 0.7597 已作废，稿件的 0.5357 出自 optimized_results.json）。
# 旧数字不再留在主产物里，迁到 deprecated/ 并显式标注，避免复现者先撞上废弃口径。
STALE = {
    "weights_nominal": w3.tolist(), "pi_baseline": [round(v, 4) for v in pi0],
    "transforms": drift,
    "L1_mean": round(float(np.mean(l1s)), 4), "L1_max": round(float(np.max(l1s)), 4),
    "reversal_rate": round(float(np.mean([1 if r > 0 else 0 for r in revs])), 4),
}
DEPRECATED = os.path.join(OUT, "deprecated")
os.makedirs(DEPRECATED, exist_ok=True)
with open(os.path.join(DEPRECATED, "assist09_drift_v1_sign_mixed.json"), "w", encoding="utf-8") as f:
    json.dump({
        "_deprecated": True,
        "_deprecated_on": "2026-09-22",
        "_reason": ("旧符号口径：min-max 归一化 + π_k = w_k·Cov(z_k,S)/Var(S)，与最终稿件的"
                    "漂移口径不一致，L1_mean = 0.7597 已作废，禁止引用。"),
        "_superseded_by": "results/code/optimized_results.json（assist09 漂移 L1_mean = 0.5357）",
        "_origin": "results/code/m1_real_data.py 旧版 A3 块",
        "payload": STALE,
    }, f, ensure_ascii=False, indent=2)
results["assist09_drift_deprecated"] = {
    "_deprecated": True,
    "_reason": "旧符号口径 L1_mean = 0.7597 已作废，禁止引用。",
    "_superseded_by": "results/code/optimized_results.json",
    "_moved_to": "results/code/deprecated/assist09_drift_v1_sign_mixed.json",
}
print("drift(OLD SIGN, deprecated): L1_mean=%.4f L1_max=%.4f reversal_rate=%.2f -> deprecated/" %
      (STALE["L1_mean"], STALE["L1_max"], STALE["reversal_rate"]))

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
