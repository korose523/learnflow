# -*- coding: utf-8 -*-
"""O9：λ*(k) 收缩公式的样本外检验 + fused6 的池内验证。

O8 给出的 λ*(k)=1/(1+(k/27.4)^0.902) 是**在同一批 k 上既拟合又评估**得来的，
不能直接当作可部署规则使用。本脚本做两件检验：

  Q1 样本外 k：只用 k∈{10,50,200} 的 λ* 拟合出 (k0,p)，再**外推**到没参与拟合的
     k=25 与 k=100，比较三种取法的留出 ρ：
       λ=0（纯成功率，基线） / λ=λ̂(k)（公式外推，无调参） / λ=λ*_emp（折半挑出的经验最优，上界参照）
     若 λ̂(k) 能达到 λ*_emp 的大部分收益，说明公式可部署。
  Q2 池内场景：v3b 只测了 fused7。检验剔除升级率后的 fused6 在池内是否同样改善
     （池内 268 个池，分位瞄准，λ 池间折半验证）。

输出 results/code/o9_lambda_generalization.json
"""
import csv, json
from collections import defaultdict
import numpy as np
from scipy import stats as st
from scipy import optimize as opt

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o9_lambda_generalization.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)
J_res = Z["J_res"]; J_keep = [str(u) for u in Z["J_keep"]]
K = J_res.shape[2]
M_ALL = J_res.shape[0]
B_SIZE, REP, SPLITS = 250, 25, 20
FIT_KS = [10, 50, 200]
OOS_KS = [25, 100]
# O8 实测的 fused6 λ*（用于拟合；注意 OOS_KS 不在其中）
LAM_STAR_FUSED6 = {10: 0.701, 25: 0.524, 50: 0.387, 100: 0.234, 200: 0.125}
COLS6 = [0, 1, 2, 3, 5, 6]        # 剔除 upgrade_rate(索引 4)
COLS7 = list(range(7))


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def signals(pick):
    m = J_res.shape[0]
    k = pick.shape[1]
    p3 = np.broadcast_to(pick[:, None, :], (m, 7, k))
    S = np.take_along_axis(J_res.astype(np.float64), p3, axis=2).sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


# ---------------------------------------------------------------- Q1
ks_fit = np.array(FIT_KS, float)
ls_fit = np.array([LAM_STAR_FUSED6[k] for k in FIT_KS], float)


def model(k, k0, p):
    return 1.0 / (1.0 + np.power(np.asarray(k, float) / k0, p))


sol = opt.least_squares(lambda x: model(ks_fit, *x) - ls_fit, [27.0, 0.9],
                        bounds=([0.1, 0.05], [500.0, 5.0]))
k0, p_exp = float(sol.x[0]), float(sol.x[1])
print("fit on k in %s -> k0=%.3f p=%.3f | fit values %s" % (
    FIT_KS, k0, p_exp, np.round(model(ks_fit, k0, p_exp), 3)), flush=True)

rng = np.random.default_rng(20260913)
q1 = {}
for k in OOS_KS:
    lam_hat = float(model(k, k0, p_exp))
    r0, rhat, remp, picks = [], [], [], []
    for rep in range(REP):
        noise = rng.random((M_ALL, K))
        order = np.argsort(noise, axis=1)
        pa, pb = order[:, :k], order[:, k:k + B_SIZE]
        S = signals(pa)
        okb = np.take_along_axis(J_res.astype(np.float64)[:, 0:1, :],
                                 np.broadcast_to(pb[:, None, :], (M_ALL, 1, B_SIZE)),
                                 axis=2)[:, 0, :]
        crit = 1.0 - okb.mean(axis=1)
        s = S[:, 0]; v = S[:, COLS6].mean(1)
        r0.append(spear(s, crit))
        rhat.append(spear((1 - lam_hat) * s + lam_hat * v, crit))
        LAM = np.round(np.arange(0.0, 1.01, 0.05), 2)
        for _ in range(SPLITS):
            pm = rng.permutation(M_ALL)
            A, B = pm[: M_ALL // 2], pm[M_ALL // 2:]
            sc = np.array([spear(((1 - l) * s + l * v)[A], crit[A]) for l in LAM])
            bi = int(np.nanargmax(sc))
            picks.append(float(LAM[bi]))
            remp.append(spear(((1 - LAM[bi]) * s + LAM[bi] * v)[B], crit[B]))
    lam_emp = float(np.mean(picks))
    g_hat = (np.mean(rhat) - np.mean(r0)) * 100
    g_emp = (np.mean(remp) - np.mean(r0)) * 100
    q1[str(k)] = {
        "lambda_hat_from_formula": round(lam_hat, 3),
        "lambda_emp_splithalf": round(lam_emp, 3),
        "rho_lambda_0": round(float(np.mean(r0)), 4),
        "rho_lambda_hat": round(float(np.mean(rhat)), 4),
        "rho_lambda_emp": round(float(np.mean(remp)), 4),
        "gain_hat_pp": round(float(g_hat), 3),
        "gain_emp_pp": round(float(g_emp), 3),
        "retained_fraction": round(float(g_hat / g_emp), 3) if abs(g_emp) > 1e-9 else None,
    }
    print("  k=%3d | λ̂=%.3f (formula) λ*_emp=%.3f | ρ: λ0 %.4f → λ̂ %.4f (%+.3f pp) "
          "| λ*_emp %.4f (%+.3f pp) | 保留 %.0f%%" % (
              k, lam_hat, lam_emp, np.mean(r0), np.mean(rhat), g_hat,
              np.mean(remp), g_emp, 100 * (g_hat / g_emp) if g_emp else 0), flush=True)

# ---------------------------------------------------------------- Q2
DIFFORD = ["easy", "normal", "hard"]
MIN_ATT, MIN_POOL = 500, 6
POOL_KS = [10, 25, 50, 100, 250, 500]
LAM = np.round(np.arange(0.0, 1.01, 0.1), 2)
REP2 = 20

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
keys = list(pools.keys()); NP = len(keys)
P_sel, P_tc, P_tden, P_w = [], [], [], []
for key in keys:
    items = pools[key]
    P_sel.append(np.array([pos_of_idx[ix] for ix, _ in items]))
    t = st.rankdata(1.0 - np.array([p for _, p in items]))
    tc = t - t.mean()
    P_tc.append(tc); P_tden.append(float(np.sqrt((tc * tc).sum()))); P_w.append(float(len(items)))
P_w = np.array(P_w); P_tden = np.array(P_tden)


def pool_corr_cols(E):
    J = E.shape[1]
    C = np.full((NP, J), np.nan)
    for pi in range(NP):
        idx = P_sel[pi]; tc = P_tc[pi]; td = P_tden[pi]
        if td <= 0:
            continue
        for j in range(J):
            v = E[idx, j]
            r = st.rankdata(v); rc = r - r.mean()
            den = np.sqrt((rc * rc).sum()) * td
            if den > 0:
                C[pi, j] = (rc * tc).sum() / den
    return C


def wmean(col, mask):
    m = mask & ~np.isnan(col)
    return float(np.average(col[m], weights=P_w[m])) if m.sum() else float("nan")


def k_signals_pool(k, perm):
    S = J_res[sel][:, :, perm[:k]].sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


print("\n=== Q2 within-pool: fused7 (O5 配置) vs fused6 (剔除升级率) ===", flush=True)
q2 = {}
rng2 = np.random.default_rng(20260913)
for k in POOL_KS:
    row = {}
    for vname, cols in (("fused7", COLS7), ("fused6", COLS6)):
        picks, held, held0 = [], [], []
        for rep in range(REP2):
            Mx = k_signals_pool(k, rng2.permutation(K))
            s = Mx[:, 0]; v = Mx[:, cols].mean(1)
            E = np.column_stack([(1 - l) * s + l * v for l in LAM])
            C = pool_corr_cols(E)
            for _ in range(SPLITS):
                pm = rng2.permutation(NP)
                A = np.zeros(NP, bool); A[pm[: NP // 2]] = True
                B = ~A
                sc = np.array([wmean(C[:, j], A) for j in range(len(LAM))])
                bi = int(np.nanargmax(sc))
                picks.append(float(LAM[bi]))
                held.append(wmean(C[:, bi], B)); held0.append(wmean(C[:, 0], B))
        row[vname] = {
            "lambda_star_mean": round(float(np.mean(picks)), 3),
            "heldout_at_lambda_star": round(float(np.nanmean(held)), 4),
            "heldout_at_lambda_0": round(float(np.nanmean(held0)), 4),
            "gain_pp": round(float(np.nanmean(held) - np.nanmean(held0)) * 100, 3),
        }
    q2[str(k)] = row
    print("  k=%3d | fused7 λ*=%.2f gain %+.3f pp | fused6 λ*=%.2f gain %+.3f pp | Δ %+.3f pp" % (
        k, row["fused7"]["lambda_star_mean"], row["fused7"]["gain_pp"],
        row["fused6"]["lambda_star_mean"], row["fused6"]["gain_pp"],
        row["fused6"]["gain_pp"] - row["fused7"]["gain_pp"]), flush=True)

json.dump({
    "design": "O9 out-of-sample test of the lambda*(k) shrinkage rule + within-pool check of fused6",
    "Q1_out_of_sample_k": {
        "fit_ks": FIT_KS, "oos_ks": OOS_KS,
        "fitted": {"k0": round(k0, 3), "p": round(p_exp, 3)},
        "formula": "lambda*(k) = 1/(1+(k/k0)^p)",
        "results": q1,
    },
    "Q2_within_pool_fused6_vs_fused7": {"n_pools": NP, "k_list": POOL_KS,
                                        "reps": REP2, "splits": SPLITS, "results": q2},
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
