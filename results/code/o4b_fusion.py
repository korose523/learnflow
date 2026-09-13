# -*- coding: utf-8 -*-
"""O4b: 特征工程扩展的难度融合（DBE-KT22 212 题）。

在 O4 五信号基础上：
  + differential: z(自报难度) - z(信任度)   ← O4 发现的差分特征显式化
  + dispersion: 每题正确率的样本标准差（区分"稳定中等"与"两极分化"）
  + n_transactions: 作答量（热度代理）
统一 ECDF-logit 公制，贪心权重 + 5 折 CV，与 O4 等权/CV 结果直接对比。
输出 results/code/o4b_fusion_results.json
"""
import csv, json, math, itertools, datetime as dt
from collections import defaultdict
import numpy as np
from scipy import stats as st

BASE = r"E:/learnflow"
OUT = BASE + "/results/code/o4b_fusion_results.json"

expert = {}
with open(BASE + "/data/dbe_kt22/csv/Questions.csv", encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            expert[d["id"]] = int(d["difficulty"])
        except (ValueError, TypeError):
            pass

sig = defaultdict(lambda: {"n": 0, "ok": 0, "hint": 0, "dfb": [], "tfb": [], "dur": []})
with open(BASE + "/data/dbe_kt22/csv/Transaction.csv", encoding="utf-8-sig", errors="replace") as f:
    for row in csv.DictReader(f):
        q = row["question_id"]
        if q not in expert or row["is_hidden"] == "true":
            continue
        s = sig[q]
        s["n"] += 1
        if row["answer_state"] == "true":
            s["ok"] += 1
        if row["hint_used"] == "true":
            s["hint"] += 1
        try:
            s["dfb"].append(int(row["difficulty_feedback"]))
            s["tfb"].append(int(row["trust_feedback"]))
        except ValueError:
            pass
        try:
            a = dt.datetime.strptime(row["start_time"][:19], "%Y-%m-%d %H:%M:%S")
            b = dt.datetime.strptime(row["end_time"][:19], "%Y-%m-%d %H:%M:%S")
            d = (b - a).total_seconds()
            if 0 <= d < 3600:
                s["dur"].append(d)
        except ValueError:
            pass

qids = [q for q, s in sig.items() if s["n"] >= 30 and q in expert]

def ecdf_logit(vals):
    v = np.asarray(vals, dtype=float)
    n = len(v)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / n, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))

# per-question features assembled below from raw transaction aggregates
disp = {}
ok_by_q = defaultdict(list)
with open(BASE + "/data/dbe_kt22/csv/Transaction.csv", encoding="utf-8-sig", errors="replace") as f:
    for row in csv.DictReader(f):
        q = row["question_id"]
        if q in expert and row["is_hidden"] != "true":
            ok_by_q[q].append(1 if row["answer_state"] == "true" else 0)

rows = {n: [] for n in ["success_inverse", "hint_rate", "difficulty_feedback", "trust_inverse",
                         "duration", "differential", "dispersion", "n_transactions"]}
use_q = []
for q in qids:
    s = sig[q]
    if not s["dfb"] or not s["tfb"] or not s["dur"]:
        continue
    rows["success_inverse"].append(-(s["ok"] / s["n"]))
    rows["hint_rate"].append(s["hint"] / s["n"])
    rows["difficulty_feedback"].append(np.mean(s["dfb"]))
    rows["trust_inverse"].append(-np.mean(s["tfb"]))
    rows["duration"].append(np.mean(s["dur"]))
    rows["differential"].append(np.mean(s["dfb"]) - np.mean(s["tfb"]))
    rows["dispersion"].append(np.std(ok_by_q[q]))
    rows["n_transactions"].append(s["n"])
    use_q.append(q)

y = np.array([expert[q] for q in use_q])
Z = np.vstack([ecdf_logit(rows[n]) for n in rows]).T
names = list(rows.keys())
print("n:", len(use_q), "features:", names)

per = {}
for i, n in enumerate(names):
    r = st.spearmanr(Z[:, i], y)
    per[n] = [round(float(r.statistic), 4), round(float(r.pvalue), 8)]
print("per-feature:", per)

w_eq = np.full(len(names), 1 / len(names))
rho_eq = float(st.spearmanr(Z @ w_eq, y).statistic)
print("equal-weight rho:", round(rho_eq, 4))

grid = [0.0, 0.5, 1.0, 1.5, 2.0]
def greedy(mask_idx):
    """coordinate ascent over weights (full 5^8 grid infeasible)"""
    w = np.full(len(names), 1.0 / len(names))
    br = st.spearmanr(Z[mask_idx] @ w, y[mask_idx]).statistic
    for _ in range(3):
        improved = False
        for i in range(len(names)):
            for g in grid:
                w2 = w.copy()
                w2[i] = g
                s = w2.sum()
                if s == 0:
                    continue
                r = st.spearmanr(Z[mask_idx] @ (w2 / s), y[mask_idx]).statistic
                if r > br + 1e-9:
                    br, w, improved = r, w2 / s, True
        if not improved:
            break
    return w, br

bw, br = greedy(np.arange(len(use_q)))
print("in-sample best:", round(br, 4), dict(zip(names, np.round(bw, 2))))

rng = np.random.default_rng(42)
folds = np.array_split(rng.permutation(len(use_q)), 5)
cv = []
for fi, te in enumerate(folds):
    tr = np.concatenate([f for fj, f in enumerate(folds) if fj != fi])
    w_t, _ = greedy(tr)
    cv.append(float(st.spearmanr(Z[te] @ w_t, y[te]).statistic))
    print(f"fold {fi}: test rho {cv[-1]:.4f}", flush=True)
cv_mean = float(np.mean(cv))

# O4-style 2-feature differential-only reference
i_d, i_t = names.index("difficulty_feedback"), names.index("trust_inverse")
z_ref = Z[:, i_d] + Z[:, i_t]
rho_ref = float(st.spearmanr(z_ref, y).statistic)

res = {
    "design": "O4b expanded-feature ECDF-logit fusion, greedy weights, 5-fold CV",
    "n_questions": len(use_q),
    "per_feature_spearman": per,
    "equal_weight_spearman": round(rho_eq, 4),
    "insample_best_spearman": round(float(br), 4),
    "insample_weights": {n: round(float(w), 3) for n, w in zip(names, bw)},
    "cv5_mean_spearman": round(cv_mean, 4),
    "cv5_folds": [round(r, 4) for r in cv],
    "reference_diff_only_spearman": round(rho_ref, 4),
    "baselines": {"O2_irt": 0.2300, "O4_equal": 0.2899, "O4_cv": 0.4778},
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "per_feature_spearman"}, ensure_ascii=False, indent=1))
