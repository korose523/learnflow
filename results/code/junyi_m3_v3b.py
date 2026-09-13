# -*- coding: utf-8 -*-
"""M3-Junyi v3b：池内排序负结果的消融（"融合为何在池内失效、能否救回来"）。

v3.1 发现（同知识点 × 同能力十分位的池内排序任务）：
    k=10  融合 0.578 > 成功率 0.551   ← 融合赢
    k=25+ 成功率单调领先，k=500 时 0.902 vs 0.832  ← 融合输且差距随 k 扩大
这不是泄漏（估计样本只占判据样本的 ~k/1000），而是**饱和差异**：
成功率与判据是同一构念，样本越充足越接近充分统计量；融合额外引入的
信号在小样本时是去噪器，样本充足后变成噪声源。

本脚本三问：
  Q1 单信号消融：7 个信号各自池内排序力如何？是否只有成功率有效？
  Q2 混合权重 score(λ) = (1−λ)·success + λ·fused 是否存在内点最优 λ*？
  Q3 λ* 在同批池上选、同批池上评会过拟合 → 用**池间折半**：A 半选 λ*，
     B 半评估，重复 20 次；同时报告 B 半上 λ=0 与 λ=1 的对照。

输出 results/code/junyi_m3_v3b_results.json
"""
import csv, json
from collections import defaultdict
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/junyi_m3_v3b_results.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)
J_res = Z["J_res"]; J_keep = [str(u) for u in Z["J_keep"]]
K = J_res.shape[2]
DIFFORD = ["easy", "normal", "hard"]
MIN_ATT, MIN_POOL = 500, 6
KS = [10, 25, 50, 100, 250, 500]
LAM = np.round(np.arange(0.0, 1.01, 0.1), 2)
REP, SPLITS = 20, 20
SIG = ["success", "hint", "duration", "attempts", "upgrade", "downgrade", "repeatsess"]

meta = {}
with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = {"diff": row["difficulty"], "strand": row["level3_id"]}
c = json.load(open(BASE + "/results/code/junyi_m3_cache.json", encoding="utf-8"))
pt = {}
for kk, v in c["pt"].items():
    u, d = kk.rsplit("|", 1)
    pt[(u, int(d))] = v

idx_of = {u: i for i, u in enumerate(J_keep)}
usable = [u for u in J_keep if meta.get(u, {}).get("diff") in DIFFORD and u in idx_of]
sel = np.array([idx_of[u] for u in usable])
pos_of_idx = {ix: i for i, ix in enumerate(sel)}

pools = defaultdict(list)
for u in usable:
    s = meta[u]["strand"]
    for d in range(10):
        v = pt.get((u, d))
        if v and v[0] >= MIN_ATT:
            pools[(s, d)].append((idx_of[u], v[1] / v[0]))
pools = {k2: v for k2, v in pools.items() if len(v) >= MIN_POOL}
keys = list(pools.keys())
NP = len(keys)
print("pools:", NP, "| exercises:", len(usable), flush=True)

P_sel, P_tr, P_w = [], [], []
for key in keys:
    items = pools[key]
    P_sel.append(np.array([pos_of_idx[ix] for ix, _ in items]))
    P_tr.append(st.rankdata(1.0 - np.array([p for _, p in items])))
    P_w.append(float(len(items)))
P_w = np.array(P_w)
# 真实难度的中心化秩（预计算，避免重复开销）
P_tc = [t - t.mean() for t in P_tr]
P_tden = np.array([np.sqrt((t * t).sum()) for t in P_tc])


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def k_signals(k, perm):
    S = J_res[sel][:, :, perm[:k]].sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def pool_corr_cols(E):
    """E: (m, J) 候选估计量矩阵 → (NP, J) 池内 Spearman。"""
    J = E.shape[1]
    C = np.full((NP, J), np.nan)
    for pi in range(NP):
        idx = P_sel[pi]; tc = P_tc[pi]; td = P_tden[pi]
        if td <= 0:
            continue
        for j in range(J):
            v = E[idx, j]
            r = st.rankdata(v)
            rc = r - r.mean()
            den = np.sqrt((rc * rc).sum()) * td
            if den > 0:
                C[pi, j] = (rc * tc).sum() / den
    return C


def wmean(col, mask):
    m = mask & ~np.isnan(col)
    if m.sum() == 0:
        return float("nan")
    return float(np.average(col[m], weights=P_w[m]))


rng = np.random.default_rng(20260913)
out = {"per_signal": {}, "lambda_mix": {}}

print("\n=== Q1 per-signal within-pool Spearman ===", flush=True)
for k in [10, 50, 100, 500]:
    acc = defaultdict(list)
    for rep in range(REP):
        M = k_signals(k, rng.permutation(K))
        E = np.column_stack([M, M.mean(1)])           # 7 信号 + 等权融合
        C = pool_corr_cols(E)
        for j, nm in enumerate(SIG + ["fused_equal"]):
            acc[nm].append(wmean(C[:, j], np.ones(NP, bool)))
    row = {nm: round(float(np.nanmean(v)), 4) for nm, v in acc.items()}
    out["per_signal"]["k=%d" % k] = row
    print(" k=%3d " % k + " ".join("%s=%.3f" % (nm[:8], v) for nm, v in row.items()), flush=True)

print("\n=== Q2/Q3 mixture lambda (split-pool validated) ===", flush=True)
for k in KS:
    curve = defaultdict(list)
    picks, held, held0, held1 = [], [], [], []
    for rep in range(REP):
        M = k_signals(k, rng.permutation(K))
        s, f = M[:, 0], M.mean(1)
        E = np.column_stack([(1 - l) * s + l * f for l in LAM])
        C = pool_corr_cols(E)                          # (NP, n_lam)
        for j, l in enumerate(LAM):
            curve[float(l)].append(wmean(C[:, j], np.ones(NP, bool)))
        for _ in range(SPLITS):
            pm = rng.permutation(NP)
            A = np.zeros(NP, bool); A[pm[: NP // 2]] = True
            B = ~A
            sc = np.array([wmean(C[:, j], A) for j in range(len(LAM))])
            bi = int(np.nanargmax(sc))
            picks.append(float(LAM[bi]))
            held.append(wmean(C[:, bi], B))
            held0.append(wmean(C[:, 0], B))
            held1.append(wmean(C[:, len(LAM) - 1], B))
    cur = {str(l): round(float(np.nanmean(v)), 4) for l, v in curve.items()}
    out["lambda_mix"]["k=%d" % k] = {
        "curve": cur,
        "argmax_lambda_insample": float(max(cur, key=lambda x: cur[x])),
        "split_pool": {
            "lambda_star_mean": round(float(np.mean(picks)), 3),
            "lambda_star_sd": round(float(np.std(picks)), 3),
            "heldout_at_lambda_star": round(float(np.nanmean(held)), 4),
            "heldout_at_lambda_0": round(float(np.nanmean(held0)), 4),
            "heldout_at_lambda_1": round(float(np.nanmean(held1)), 4),
            "gain_vs_lambda0_pp": round(float(np.nanmean(held) - np.nanmean(held0)) * 100, 3),
        },
    }
    sp = out["lambda_mix"]["k=%d" % k]["split_pool"]
    print("  k=%3d | λ* %.2f (sd %.2f) | held-out λ*=%.4f  λ0=%.4f  λ1=%.4f | gain %+.3f pp"
          % (k, sp["lambda_star_mean"], sp["lambda_star_sd"], sp["heldout_at_lambda_star"],
             sp["heldout_at_lambda_0"], sp["heldout_at_lambda_1"], sp["gain_vs_lambda0_pp"]), flush=True)

out.update({
    "design": "M3-Junyi v3b ablation of the within-pool negative result: per-signal "
              "within-pool ordering power + shrinkage mixture (1-lambda)*success + "
              "lambda*fused, lambda chosen on half the pools and evaluated on the rest",
    "n_pools": NP, "n_exercises": len(usable), "min_pool": MIN_POOL,
    "k_list": KS, "lambda_grid": [float(x) for x in LAM], "reps": REP, "splits": SPLITS,
    "signals": SIG,
    "leakage_note": "estimator sample (~k rows per exercise) overlaps the criterion sample "
                    "(>=500 attempts within the ability decile) by roughly k/1000, "
                    "so the k-trend is a saturation effect, not leakage",
})
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
