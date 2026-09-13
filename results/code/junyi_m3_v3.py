# -*- coding: utf-8 -*-
"""M3-Junyi v3：冷启动难度估计驱动的排序（把 O6 的估计器结论接到策略层）。

M3 v2 的局限：策略只在"专家三档臂"里选，等价于假设系统已经知道真实难度。
真实系统必须**先估计难度、再排序**，且估计只用得到 k 条观测（冷启动）。

设计修正（v3.1）：
  初版以"绝对成功率 0.75"为瞄准目标，结果 oracle 标定的目标分位 q*=0.12
  —— 因为池内真实正确率均值仅 0.68，根本够不到 0.75，所有估计器退化成
  "选最简单的"，与 random 无差别，实验失去区分度。故改为**分位瞄准**：
  所有估计器（含 oracle）都在各自排序的同一名义分位 q 上取题，比较的是
  "取到的题的真实难度/正确率"与 oracle 取到的差多少。差异只能来自池内
  排序质量，且 q 对所有估计器共用 → 不是选择效应。

估计器：
  success_only_k —— 只用成功率（O2/O5 基线）
  fused_k        —— 7 信号 ECDF-logit 等权融合（O5 配置）
  random         —— 池内随机（下界）
  oracle         —— 用真实 p 排序（上界，确定性）

指标（对每个 k、每个 q ∈ {0.25, 0.50, 0.75}）：
  regret_pp      —— oracle 取到的真实正确率 − 本估计器取到的（百分点，越小越好）
  rank_error     —— 取到的题在"真实难度"排序上的分位 与 目标分位 q 的偏差
  pool_spearman  —— 池内 估计难度 vs 真实难度(1−p) 的 Spearman，按池大小加权

依赖 build_difficulty_cache.py 的 difficulty_cache.npz + junyi_m3_cache.json
输出 results/code/junyi_m3_v3_results.json
"""
import csv, json, math
from collections import defaultdict
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/junyi_m3_v3_results.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)
J_res = Z["J_res"]; J_keep = [str(u) for u in Z["J_keep"]]
K = J_res.shape[2]
DIFFORD = ["easy", "normal", "hard"]
MIN_ATT = 500
KS = [10, 25, 50, 100, 250, 500]
QS = [0.25, 0.50, 0.75]
REP = 60
MIN_POOL = 6

# ---------------------------------------------------------------- 元数据
meta = {}
with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = {"diff": row["difficulty"], "strand": row["level3_id"]}

c = json.load(open(BASE + "/results/code/junyi_m3_cache.json", encoding="utf-8"))
pt = {}
for kk, v in c["pt"].items():
    ucid, d = kk.rsplit("|", 1)
    pt[(ucid, int(d))] = v

idx_of = {u: i for i, u in enumerate(J_keep)}
usable = [u for u in J_keep if meta.get(u, {}).get("diff") in DIFFORD and u in idx_of]
sel = np.array([idx_of[u] for u in usable])
pos_of_idx = {ix: i for i, ix in enumerate(sel)}
print("usable exercises:", len(usable), flush=True)

pools = defaultdict(list)
for u in usable:
    s = meta[u]["strand"]
    for d in range(10):
        v = pt.get((u, d))
        if v and v[0] >= MIN_ATT:
            pools[(s, d)].append((idx_of[u], v[1] / v[0]))
pools = {k2: v for k2, v in pools.items() if len(v) >= MIN_POOL}
pool_list = list(pools.items())
print("pools (>=%d items):" % MIN_POOL, len(pool_list),
      "| median size", int(np.median([len(v) for _, v in pool_list])), flush=True)

# 每个池：按真实难度 1-p 升序（易→难）得到 oracle 序
pool_ps, pool_true_rank_pct, pool_sel = {}, {}, {}
for key, items in pool_list:
    ps = np.array([p for _, p in items])
    order = np.argsort(1.0 - ps, kind="stable")
    pool_sel[key] = np.array([pos_of_idx[ix] for ix, _ in items])
    pool_ps[key] = ps[order]                       # oracle 序下的真实正确率
    n = len(order)
    rk = np.empty(n)
    rk[order] = np.arange(n) / max(n - 1, 1)       # 每题在真实难度序上的分位
    pool_true_rank_pct[key] = rk
pool_size = np.array([len(v) for _, v in pool_list], dtype=float)


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def k_sample_signals(k, perm):
    S = J_res[sel][:, :, perm[:k]].sum(axis=2)     # (m,7)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def within_pool_spearman(est):
    rs, ws = [], []
    for key, _ in pool_list:
        e = est[pool_sel[key]]
        t = 1.0 - np.array([p for _, p in pools[key]])
        if len(e) < 3 or np.allclose(e.std(), 0):
            continue
        rs.append(st.spearmanr(e, t).statistic); ws.append(len(e))
    rs, ws = np.array(rs), np.array(ws, dtype=float)
    return float(np.average(rs, weights=ws)), int(rs.size)


rng = np.random.default_rng(20260913)
res = {"by_k": {}}
print("\n%4s | %-13s | %s" % ("k", "estimator", "  ".join(
    "q=%.2f regret/rankerr" % q for q in QS)), flush=True)

for k in KS:
    agg = {name: {q: [] for q in QS} for name in ["random", "success_only", "fused"]}
    reg = {name: {q: [] for q in QS} for name in ["random", "success_only", "fused"]}
    rkerr = {name: {q: [] for q in QS} for name in ["random", "success_only", "fused"]}
    sp_s, sp_f = [], []
    for rep in range(REP):
        perm = rng.permutation(K)
        M = k_sample_signals(k, perm)
        est_s, est_f = M[:, 0], M.mean(1)
        sp_s.append(within_pool_spearman(est_s)[0])
        sp_f.append(within_pool_spearman(est_f)[0])
        for key, _ in pool_list:
            ps_ord = pool_ps[key]
            nn = len(ps_ord)
            sel_idx = pool_sel[key]
            rkmap = pool_true_rank_pct[key]
            for q in QS:
                pos_o = int(round(q * (nn - 1)))
                p_oracle = ps_ord[pos_o]
                for name, est in (("success_only", est_s), ("fused", est_f)):
                    vals = est[sel_idx]
                    pos = int(np.argsort(vals, kind="stable")[int(round(q * (nn - 1)))])
                    agg[name][q].append(ps_ord[pos])
                    reg[name][q].append(p_oracle - ps_ord[pos])
                    rkerr[name][q].append(abs(rkmap[pos] - q))
                j = rng.integers(0, nn)
                agg["random"][q].append(ps_ord[j])
                reg["random"][q].append(p_oracle - ps_ord[j])
                rkerr["random"][q].append(abs(rkmap[j] - q))

    out = {}
    for name in ["random", "success_only", "fused"]:
        out[name] = {}
        for q in QS:
            a = np.array(agg[name][q]); r = np.array(reg[name][q]); e = np.array(rkerr[name][q])
            out[name]["q_%.2f" % q] = {
                "mean_p": round(float(a.mean()), 4),
                "regret_pp": round(float(r.mean()) * 100, 3),
                "regret_pp_se": round(float(r.std(ddof=1) / math.sqrt(REP)) * 100, 3),
                "rank_error": round(float(e.mean()), 4),
            }
    out["oracle"] = {
        "q_%.2f" % q: {"mean_p": round(float(np.mean([pool_ps[key][int(round(q * (len(pool_ps[key]) - 1)))]
                                                      for key, _ in pool_list])), 4),
                       "regret_pp": 0.0, "rank_error": 0.0}
        for q in QS}
    out["pool_spearman_success"] = round(float(np.mean(sp_s)), 4)
    out["pool_spearman_fused"] = round(float(np.mean(sp_f)), 4)
    out["pool_spearman_gain"] = round(float(np.mean(sp_f) - np.mean(sp_s)), 4)
    res["by_k"][str(k)] = out
    for name in ["random", "success_only", "fused"]:
        print("%4d | %-13s | %s" % (k, name, "  ".join(
            "%+7.3fpp/%.3f" % (out[name]["q_%.2f" % q]["regret_pp"],
                               out[name]["q_%.2f" % q]["rank_error"]) for q in QS)), flush=True)
    print("      pool spearman: success %.4f | fused %.4f | gain %+.4f" % (
        out["pool_spearman_success"], out["pool_spearman_fused"], out["pool_spearman_gain"]), flush=True)

res.update({
    "design": "M3-Junyi v3.1 cold-start difficulty-estimator-driven sequencing; "
              "quantile targeting with a shared target quantile q, regret measured against oracle",
    "n_exercises": len(usable), "n_pools": len(pool_list), "min_pool": MIN_POOL,
    "min_attempts_per_arm": MIN_ATT, "target_quantiles": QS,
    "reps": REP, "k_list": KS,
    "pool_size_median": int(np.median(pool_size)),
    "why_quantile_targeting": "absolute 0.75 targeting is unreachable inside pools "
                              "(pool mean p = 0.68, oracle q* degenerates to 0.12); "
                              "quantile targeting keeps all estimators comparable",
})
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
