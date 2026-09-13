# -*- coding: utf-8 -*-
"""O6：融合难度估计器的统计稳健性与样本效率（在 O4/O5 之上的三重加固）。

O6a  样本效率曲线：把每个练习的观测子样本缩到 k 条（模拟冷启动），比较
      "仅成功率" vs "多信号等权融合" 与专家难度标签的 Spearman。
      假设：单信号在小样本下噪声更大 → 融合的样本效率更高。
O6b  统计稳健性：对 O4/O5 头号数字做 bootstrap CI、配对 bootstrap 检验
      （融合 − 单信号）、重复 5 折 CV（10 次重复）、三档二次加权 Kappa。
O6c  判据切换：把 ground truth 从"专家标签"换成"真实表现难度"
      （Junyi 十分位条件下的真实正确率 p），检验融合的增益是否只是
      对专家标签的过拟合 —— 自适应系统真正要预测的是后者。

依赖 build_difficulty_cache.py 产出的 difficulty_cache.npz
输出 results/code/o6_difficulty_stats.json
"""
import json, math
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o6_difficulty_stats.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)

J_full, J_res, J_y = Z["J_full"], Z["J_res"], Z["J_y"]
D_full, D_res, D_y, D_cnt = Z["D_full"], Z["D_res"], Z["D_y"], Z["D_cnt"]
K = J_res.shape[2]
print("cache: junyi", J_full.shape, "| dbe", D_full.shape, "| K =", K, flush=True)


# ----------------------------------------------------------------- 基本工具
def ecdf_logit(v):
    """rank -> ECDF -> logit。单调重参数化不变（O1）。"""
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spearman(a, b):
    return float(st.spearmanr(a, b).statistic)


def qwk(x, y, nbin=3):
    """二次加权 Kappa：把连续估计切成 nbin 档后与 1..nbin 的序数标签比较。"""
    q = np.quantile(x, np.linspace(0, 1, nbin + 1)[1:-1])
    a = np.digitize(x, q)
    b = np.asarray(y, dtype=int)
    if b.min() == 1:
        b = b - 1
        k = nbin
    else:
        k = nbin
    W = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    O = np.zeros((k, k))
    for i, j in zip(a, b):
        O[i, j] += 1
    O /= O.sum()
    m = O.sum(1)
    n = O.sum(0)
    E = np.outer(m, n)
    return float(1 - (W * O).sum() / (W * E).sum())


# ------------------------------------------------------- Junyi 信号构造
JSIG = ["success_inverse", "hint_rate", "duration", "attempts",
        "upgrade_rate", "downgrade_rate", "repeat_session_rate"]
# J_full 列序: n, ok, hint, dur, att, up, down, rep
# J_res  列序: ok, hint, dur, att, up, down, rep


def junyi_signals_from_sums(S, k):
    """S: (m, 7) 求和矩阵 [ok,hint,dur,att,up,down,rep]，k: 样本量。"""
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]),   # 成功率越低越难
        ecdf_logit(r[:, 1]),    # 提示率
        ecdf_logit(r[:, 2]),    # 时长
        ecdf_logit(r[:, 3]),    # 尝试次数
        ecdf_logit(r[:, 4]),    # 升级率
        ecdf_logit(r[:, 5]),    # 降级率
        ecdf_logit(r[:, 6]),    # 重复会话率
    ])


def _junyi_from_rates(r):
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def junyi_k_signals(k, perm):
    """取蓄水池前 k 个 slot（slot 可交换 → 大小 k 的简单随机子样本）。"""
    idx = perm[:k]
    S = J_res[:, :, idx].sum(axis=2)          # (m, 7)
    return junyi_signals_from_sums(S, k)


# ---------------------------------------------------------- DBE 信号构造
DSIG = ["success_inverse", "hint_rate", "difficulty_feedback", "trust_inverse", "duration"]


def dbe_full_signals():
    n = np.maximum(D_full[:, 0], 1.0)
    ok = D_full[:, 1] / n
    hint = D_full[:, 2] / n
    nd = np.maximum(D_cnt[:, 0], 1)
    nf = np.maximum(D_cnt[:, 1], 1)
    nt = np.maximum(D_cnt[:, 2], 1)
    dur = D_full[:, 3] / nd
    dfb = D_full[:, 4] / nf
    tfb = D_full[:, 5] / nt
    return np.column_stack([
        -ecdf_logit(ok), ecdf_logit(hint), ecdf_logit(dfb),
        -ecdf_logit(tfb), ecdf_logit(dur),
    ])


def dbe_k_signals(k, rng):
    """从蓄水池取每道题的大小 k 随机子样本。

    两个易错点（均已修正）：
      1) DBE 有题目 n < K，蓄水池尾部是补零槽。必须先按 valid=min(n,K)
         把无效槽的排序键设为 +inf 排到队尾，再取前 k 个；若先全局置换再
         按 ar<keff 截断，会把补零槽当成 0 计入求和，系统性虚高小样本结果。
      2) 时长/反馈里的 -1 表示缺失，求均值时要按有效值个数而非 k 归一化。
    """
    m = D_res.shape[0]
    n = D_full[:, 0].astype(int)
    valid = np.minimum(n, K)                        # (m,)
    keff = np.minimum(k, valid)
    noise = rng.random((m, K))
    noise = np.where(np.arange(K)[None, :] >= valid[:, None], np.inf, noise)
    pick = np.argsort(noise, axis=1)[:, :k]         # (m, k) 有效槽随机在前
    used = (np.arange(k)[None, :] < keff[:, None]).astype(np.float64)
    pick3 = np.broadcast_to(pick[:, None, :], (m, D_res.shape[1], k))
    R = np.take_along_axis(D_res.astype(np.float64), pick3, axis=2)   # (m,5,k)

    def masked_mean(field, nonneg=False):
        v = R[:, field, :]
        if nonneg:
            w = used * (v >= 0)
            v = np.where(v >= 0, v, 0.0)
        else:
            w = used
        return (v * w).sum(1) / np.maximum(w.sum(1), 1.0)

    ok = masked_mean(0)
    hint = masked_mean(1)
    dur = masked_mean(2, nonneg=True)
    dfb = masked_mean(3, nonneg=True)
    tfb = masked_mean(4, nonneg=True)
    return np.column_stack([
        -ecdf_logit(ok), ecdf_logit(hint), ecdf_logit(dfb),
        -ecdf_logit(tfb), ecdf_logit(dur),
    ])


def cv_weights(M, y, grid=None):
    """坐标上升：在给定网格上最大化 Spearman（与 O4/O5 同一优化器）。"""
    if grid is None:
        grid = np.array([0.0, 0.05, 0.1, 0.15, 0.25, 0.35, 0.5, 0.75, 1.0])
    p = M.shape[1]
    w = np.full(p, 1.0 / p)
    best = spearman(M @ w, y)
    for _ in range(30):
        imp = False
        for i in range(p):
            for g in grid:
                w2 = w.copy(); w2[i] = g
                s = w2.sum()
                if s <= 0:
                    continue
                r = spearman(M @ (w2 / s), y)
                if r > best + 1e-9:
                    best, w, imp = r, w2 / s, True
        if not imp:
            break
    return w, best


# =====================================================================
# O6a  样本效率曲线
# =====================================================================
print("\n=== O6a sample efficiency ===", flush=True)
rng = np.random.default_rng(20260913)
KS = [10, 25, 50, 100, 250, 500]
REP = 30

Mfull = _junyi_from_rates(J_full[:, 1:8] / np.maximum(J_full[:, 0:1], 1.0))
yJ = J_y.astype(int)
rho_full_success = spearman(Mfull[:, 0], yJ)
rho_full_fused = spearman(Mfull.mean(1), yJ)
print("junyi full-data: success %.4f | fused %.4f" % (rho_full_success, rho_full_fused), flush=True)

eff_j = {}
for k in KS:
    rs, rf = [], []
    for _ in range(REP):
        perm = rng.permutation(K)
        Mk = junyi_k_signals(k, perm)
        rs.append(spearman(Mk[:, 0], yJ))
        rf.append(spearman(Mk.mean(1), yJ))
    eff_j[str(k)] = {
        "success_mean": round(float(np.mean(rs)), 4), "success_sd": round(float(np.std(rs)), 4),
        "fused_mean": round(float(np.mean(rf)), 4), "fused_sd": round(float(np.std(rf)), 4),
        "gain": round(float(np.mean(rf) - np.mean(rs)), 4),
        # 配对差：每次复制用同一个 perm，故逐对可比
        "paired_gain_sd": round(float(np.std(np.array(rf) - np.array(rs))), 4),
        "paired_win_rate": round(float(np.mean(np.array(rf) > np.array(rs))), 4),
    }
    print("  k=%4d success %.4f +- %.4f | fused %.4f +- %.4f | gain %+.4f (win %.2f)" % (
        k, np.mean(rs), np.std(rs), np.mean(rf), np.std(rf),
        np.mean(rf) - np.mean(rs), np.mean(np.array(rf) > np.array(rs))), flush=True)

Mdfull = dbe_full_signals()
yD = D_y.astype(int)
print("dbe full-data: success %.4f | fused %.4f" % (
    spearman(Mdfull[:, 0], yD), spearman(Mdfull.mean(1), yD)), flush=True)
_dn = D_full[:, 0].astype(int)
print("dbe n per question: min %d  median %d  max %d  | n<K(=%d): %d/%d" % (
    _dn.min(), int(np.median(_dn)), _dn.max(), K, int((_dn < K).sum()), len(_dn)), flush=True)

eff_d = {}
DKS = [10, 25, 50, 100, 250, 500]
for k in DKS:
    rs, rf = [], []
    for _ in range(REP):
        Mk = dbe_k_signals(k, rng)
        rs.append(spearman(Mk[:, 0], yD))
        rf.append(spearman(Mk.mean(1), yD))
    eff_d[str(k)] = {
        "success_mean": round(float(np.mean(rs)), 4), "success_sd": round(float(np.std(rs)), 4),
        "fused_mean": round(float(np.mean(rf)), 4), "fused_sd": round(float(np.std(rf)), 4),
        "gain": round(float(np.mean(rf) - np.mean(rs)), 4),
        "paired_win_rate": round(float(np.mean(np.array(rf) > np.array(rs))), 4),
    }
    print("  k=%4d success %.4f | fused %.4f | gain %+.4f (win %.2f)" % (
        k, np.mean(rs), np.mean(rf), np.mean(rf) - np.mean(rs),
        np.mean(np.array(rf) > np.array(rs))), flush=True)

# =====================================================================
# O6b  bootstrap CI / 配对检验 / 重复 CV / QWK
# =====================================================================
print("\n=== O6b bootstrap & repeated CV ===", flush=True)
B = 2000


def boot(M, y, b=2000, seed=7):
    r = np.random.default_rng(seed)
    n = len(y)
    s_ok = M[:, 0]
    s_fu = M.mean(1)
    ds, df, dd = [], [], []
    for _ in range(b):
        idx = r.integers(0, n, n)
        a = spearman(s_ok[idx], y[idx])
        c = spearman(s_fu[idx], y[idx])
        ds.append(a); df.append(c); dd.append(c - a)
    ds, df, dd = map(np.array, (ds, df, dd))
    return {
        "success_rho": [round(float(np.mean(ds)), 4),
                        round(float(np.percentile(ds, 2.5)), 4), round(float(np.percentile(ds, 97.5)), 4)],
        "fused_rho": [round(float(np.mean(df)), 4),
                      round(float(np.percentile(df, 2.5)), 4), round(float(np.percentile(df, 97.5)), 4)],
        "delta": [round(float(np.mean(dd)), 4),
                  round(float(np.percentile(dd, 2.5)), 4), round(float(np.percentile(dd, 97.5)), 4)],
        "p_one_sided_delta_le_0": round(float(np.mean(dd <= 0)), 4),
    }


bJ = boot(Mfull, yJ, B, seed=7)
bD = boot(Mdfull, yD, B, seed=8)
print("junyi boot:", bJ, flush=True)
print("dbe   boot:", bD, flush=True)

# 重复 5 折 CV × 10
def repeated_cv(M, y, repeats=10, seed=11):
    r = np.random.default_rng(seed)
    n = len(y)
    out = []
    for _ in range(repeats):
        folds = np.array_split(r.permutation(n), 5)
        for te in folds:
            tr = np.setdiff1d(np.arange(n), te)
            w, _ = cv_weights(M[tr], y[tr])
            out.append(spearman(M[te] @ w, y[te]))
    out = np.array(out)
    return {"mean": round(float(out.mean()), 4), "sd": round(float(out.std()), 4),
            "ci95": [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)],
            "n_folds": int(out.size)}


cvJ = repeated_cv(Mfull, yJ)
cvD = repeated_cv(Mdfull, yD)
print("junyi repeated CV(5x10):", cvJ, flush=True)
print("dbe   repeated CV(5x10):", cvD, flush=True)

qwk_res = {
    "junyi_success": round(qwk(Mfull[:, 0], yJ), 4),
    "junyi_fused": round(qwk(Mfull.mean(1), yJ), 4),
    "dbe_success": round(qwk(Mdfull[:, 0], yD), 4),
    "dbe_fused": round(qwk(Mdfull.mean(1), yD), 4),
}
print("QWK:", qwk_res, flush=True)

# =====================================================================
# O6c  判据切换：以"真实表现难度"为 ground truth（Junyi 十分位条件 p）
# =====================================================================
print("\n=== O6c criterion switch: real performance difficulty ===", flush=True)
CACHE = BASE + "/results/code/junyi_m3_cache.json"
try:
    c = json.load(open(CACHE, encoding="utf-8"))
    pt = {}
    for kk, v in c["pt"].items():
        ucid, d = kk.rsplit("|", 1)
        pt[(ucid, int(d))] = v
    ucids = [str(u) for u in Z["J_keep"]]
    # 以十分位 5（中位数能力）为参照，构造"真实表现难度"= 1 - p(ucid, decile 5)
    DEC = 5
    pvec, mask = [], []
    for i, u in enumerate(ucids):
        v = pt.get((u, DEC))
        if v and v[0] >= 500:
            pvec.append(v[1] / v[0]); mask.append(i)
        else:
            pvec.append(np.nan); mask.append(-1)
    pvec = np.array(pvec)
    sel = np.array([i for i in mask if i >= 0], dtype=int)
    ytrue = 1.0 - pvec[sel]          # 越大越难
    print("criterion-switch sample:", len(sel), flush=True)

    crit = {}
    Msub_full = Mfull[sel]
    crit["full_success"] = round(spearman(Msub_full[:, 0], ytrue), 4)
    crit["full_fused"] = round(spearman(Msub_full.mean(1), ytrue), 4)
    print("  full-data: success %.4f | fused %.4f" % (crit["full_success"], crit["full_fused"]), flush=True)

    crit["by_k"] = {}
    for k in KS:
        rs, rf = [], []
        for _ in range(REP):
            perm = rng.permutation(K)
            Mk = junyi_k_signals(k, perm)[sel]
            rs.append(spearman(Mk[:, 0], ytrue))
            rf.append(spearman(Mk.mean(1), ytrue))
        crit["by_k"][str(k)] = {
            "success_mean": round(float(np.mean(rs)), 4),
            "fused_mean": round(float(np.mean(rf)), 4),
            "gain": round(float(np.mean(rf) - np.mean(rs)), 4),
            "paired_win_rate": round(float(np.mean(np.array(rf) > np.array(rs))), 4),
        }
        print("  k=%4d success %.4f | fused %.4f | gain %+.4f (win %.2f)" % (
            k, np.mean(rs), np.mean(rf), np.mean(rf) - np.mean(rs),
            np.mean(np.array(rf) > np.array(rs))), flush=True)
    # 专家标签 vs 真实表现难度的吻合度（关键诊断）
    crit["expert_vs_performance_spearman"] = round(
        spearman(yJ[sel].astype(float), ytrue), 4)
except Exception as e:
    crit = {"error": repr(e)}
    print("O6c failed:", e, flush=True)

res = {
    "design": "O6 robustness & sample efficiency of the fused difficulty estimator "
              "(extends O4 DBE / O5 Junyi)",
    "n_junyi": int(len(yJ)), "n_dbe": int(len(yD)), "reservoir_K": int(K),
    "O6a_sample_efficiency_junyi": {"reps": REP, "k_list": KS,
                                    "full_data_success": round(rho_full_success, 4),
                                    "full_data_fused": round(rho_full_fused, 4),
                                    "by_k": eff_j},
    "O6a_sample_efficiency_dbe": {"reps": REP, "k_list": DKS,
                                  "full_data_success": round(spearman(Mdfull[:, 0], yD), 4),
                                  "full_data_fused": round(spearman(Mdfull.mean(1), yD), 4),
                                  "by_k": eff_d},
    "O6b_bootstrap": {"B": B, "junyi": bJ, "dbe": bD},
    "O6b_repeated_cv5x10": {"junyi": cvJ, "dbe": cvD},
    "O6b_qwk_tertile": qwk_res,
    "O6c_criterion_switch_performance_difficulty": crit,
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nsaved ->", OUT)
