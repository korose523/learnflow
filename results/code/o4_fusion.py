# -*- coding: utf-8 -*-
"""O4: 多行为信号 ECDF-logit 秩融合难度估计（DBE-KT22，212 题）。

目标：超过 O2 的 IRT-1PL 基线（Spearman vs 专家 = 0.2300）。
方法：每题聚合 K 个行为信号 → 各自 ECDF 变换到 logit 公制（正=难，O1 的抗重参数化公制）
→ 加权融合（等权为主，优化权重为辅并报告过拟合差距）。
输出 results/code/o4_fusion_results.json
"""
import csv, json, math, itertools
from collections import defaultdict
import numpy as np
from scipy import stats as st

BASE = r"E:/learnflow"
OUT = BASE + "/results/code/o4_fusion_results.json"
MINN = 30  # minimum transactions per item (matches D.build(minn=30))

# --- Unified signal construction (review 3.2 ①, 2026-09-29) ---
# Both O4 and the A2 experiment (results/m1/run_a1a2_fit.py) MUST call the same
# builder so the five behavioural signals are constructed identically:
#   * all transactions used (no is_hidden exclusion),
#   * feedback = mean over rows with a feedback value,
#   * duration capped to 0 <= d < 3600 s,
#   * ECDF transform (rank - 0.5)/n.
import dbe_signals as D
q2, M_list, expert_labels = D.build(minn=30)
M = np.array(M_list, dtype=float)          # (n_questions, 5) ECDF-logit signals
y_exp2 = np.array(expert_labels, dtype=float)
names = D.NAMES
print("usable questions:", len(q2), "signals:", names)

# per-signal Spearman
per = {}
for i, n in enumerate(names):
    r = st.spearmanr(M[:, i], y_exp2)
    per[n] = [round(float(r.statistic), 4), round(float(r.pvalue), 8)]
print("per-signal:", per)

def fused(w):
    z = M @ np.asarray(w)
    return z

def spear(w):
    return st.spearmanr(fused(w), y_exp2).statistic

# equal weight
w_eq = [1.0 / len(names)] * len(names)
rho_eq = spear(w_eq)

# greedy weight search on rank metric (coarse grid, report overfit gap)
best_w, best_rho = w_eq[:], rho_eq
grid = [0.0, 0.5, 1.0, 1.5, 2.0]
for combo in itertools.product(grid, repeat=len(names)):
    if sum(combo) == 0:
        continue
    w = [c / sum(combo) for c in combo]
    r = spear(w)
    if r > best_rho:
        best_rho, best_w = r, w
print("equal-weight rho:", round(rho_eq, 4))
print("best rho:", round(best_rho, 4), "weights:", dict(zip(names, [round(w, 2) for w in best_w])))

# leave-one-signal-out stability (equal weight among remaining K-1)
loo = {}
for i, n in enumerate(names):
    Mi = np.delete(M, i, axis=1)
    zi = Mi @ np.full(Mi.shape[1], 1.0 / Mi.shape[1])
    loo[n] = round(float(st.spearmanr(zi, y_exp2).statistic), 4)

# 5-fold CV of the greedy-selected weights (honest generalization estimate)
from collections import OrderedDict
cv_rhos = []
rngcv = np.random.default_rng(42)
fold_idx = rngcv.permutation(len(q2))
folds = np.array_split(fold_idx, 5)
for fi, te in enumerate(folds):
    tr = np.concatenate([f for fj, f in enumerate(folds) if fj != fi])
    # greedy on train only
    bw, br = None, -2
    for combo in itertools.product(grid, repeat=len(names)):
        if sum(combo) == 0:
            continue
        w = np.array([c / sum(combo) for c in combo])
        r = st.spearmanr(M[tr] @ w, y_exp2[tr]).statistic
        if r > br:
            br, bw = r, w
    r_te = st.spearmanr(M[te] @ bw, y_exp2[te]).statistic
    cv_rhos.append(float(r_te))
cv_mean = float(np.mean(cv_rhos))
print("5-fold CV rho of optimized weights:", round(cv_mean, 4), [round(r, 3) for r in cv_rhos])

# tertile metrics for best fusion
z = fused(best_w)
t1, t2 = np.percentile(z, [33.3, 66.7])
lab = [1 if v <= t1 else (2 if v <= t2 else 3) for v in z]
acc = float(np.mean([a == b for a, b in zip(lab, y_exp2)]))
po = acc
pe = sum((list(y_exp2).count(k) / len(y_exp2)) * (lab.count(k) / len(lab)) for k in {1, 2, 3})
kappa = (po - pe) / (1 - pe) if pe < 1 else None

res = {
    "design": "O4 ECDF-logit rank fusion of behavioral signals vs expert 1/2/3 (DBE-KT22)",
    "n_questions": len(q2), "min_transactions": MINN,
    "per_signal_spearman": per,
    "equal_weight_spearman": round(float(rho_eq), 4),
    "optimized_spearman": round(float(best_rho), 4),
    "optimized_weights": {n: round(w, 3) for n, w in zip(names, best_w)},
    "leave_one_signal_out_equal_weight": loo,
    "cv5_mean_spearman_optimized": round(cv_mean, 4),
    "overfit_gap": round(float(best_rho - rho_eq), 4),
    "optimized_tertile_accuracy": round(acc, 4),
    "optimized_tertile_kappa": round(kappa, 4) if kappa else None,
    "baselines": {"raw_success_rate_O2": 0.2207, "irt_1pl_O2": 0.2300},
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
