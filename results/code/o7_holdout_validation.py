# -*- coding: utf-8 -*-
"""O7：难度估计器的留出验证（判定 O4/O5 融合增益到底是不是真的）。

问题来源：
  * O4/O5 用"专家难度标签"作判据，融合显著优于单信号（Junyi 0.261→0.363）。
  * O6c 把判据换成"真实表现难度"后结论反转（0.915 vs 0.901），但 O6c 的判据与
    估计量出自同一批数据、且是同一度量（成功率），存在循环性，不能定论。
  * M3 v3.1 的池内结果同样可疑：估计样本与判据样本重叠，k 越大重叠越多，
    系统性偏向"成功率"这个同度量估计量（k=10 时融合还赢，k≥25 后单调输，
    正是泄漏的特征签名）。

设计（O7）：把每道题的蓄水池槽位切成**互斥**的 A、B 两段（大小 k 与 250），
  * 只用 A 段估难度：success_only / fused_equal / 混合 score(λ)
  * 只用 B 段的真实表现作判据：crit = 1 − ok_B / |B|
两段的槽位来自同一蓄水池但互不相交，估计误差与判据误差不再共享样本，
因此这是纯粹的**泛化能力**比较，不含自指泄漏。

λ 的选择同样要防过拟合：在 50% 题目上选 λ，在另 50% 题目上评估（20 次折半）。
输出 results/code/o7_holdout_validation.json
"""
import json, math
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o7_holdout_validation.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)
J_res, J_y = Z["J_res"], Z["J_y"]
D_res, D_y, D_full = Z["D_res"], Z["D_y"], Z["D_full"]
K = J_res.shape[2]
KS = [10, 25, 50, 100, 200]
B_SIZE = 250
REP, SPLITS = 30, 20
LAM = np.round(np.arange(0.0, 1.01, 0.05), 2)
SIG = ["success", "hint", "duration", "attempts", "upgrade", "downgrade", "repeatsess"]


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def valid_slots(R, n_vec):
    """把无效（补零）槽位的排序键设为 +inf，使其排到队尾。"""
    m = R.shape[0]
    noise = np.random.default_rng().random((m, K)) if False else None
    return noise


def make_split(rng, m, n_vec, k, b_size):
    """返回 pick_a (m,k) 与 pick_b (m,b_size)：互斥的有效槽位索引。"""
    valid = np.minimum(n_vec, K)
    noise = rng.random((m, K))
    noise = np.where(np.arange(K)[None, :] >= valid[:, None], np.inf, noise)
    order = np.argsort(noise, axis=1)
    return order[:, :k], order[:, k:k + b_size]


def gather(R, pick):
    m, d, _ = R.shape
    k = pick.shape[1]
    p3 = np.broadcast_to(pick[:, None, :], (m, d, k))
    return np.take_along_axis(R.astype(np.float64), p3, axis=2)


def signals_from(R, pick):
    """Junyi：R 为 (m,7,K)，7 列 = ok,hint,dur,att,up,down,rep。"""
    k = pick.shape[1]
    S = gather(R, pick).sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def signals_from_dbe(R, pick):
    """DBE：R 为 (m,5,K)，5 列 = ok,hint,dur,dfb,tfb；dur/dfb/tfb 用 -1 表示缺失，
    求均值时按有效值个数归一化（不能除以 k，否则缺失被当成 0）。"""
    G = gather(R, pick)                       # (m,5,k)
    k = G.shape[2]
    ok = G[:, 0, :].mean(axis=1)
    hint = G[:, 1, :].mean(axis=1)

    def nm(f):
        v = G[:, f, :]
        w = (v >= 0).astype(float)
        return (np.where(v >= 0, v, 0.0) * w).sum(1) / np.maximum(w.sum(1), 1.0)

    return np.column_stack([
        -ecdf_logit(ok), ecdf_logit(hint), ecdf_logit(nm(3)),
        -ecdf_logit(nm(4)), ecdf_logit(nm(2)),
    ])


def crit_from(R, pick):
    """B 段的真实表现难度 = 1 − 正确率。"""
    ok = gather(R, pick)[:, 0, :]
    return 1.0 - ok.mean(axis=1)


def run(R, n_vec, name, sigfn, ks=KS):
    m = R.shape[0]
    rng = np.random.default_rng(20260913)
    out = {}
    for k in ks:
        if k + B_SIZE > int(np.min(np.minimum(n_vec, K))):
            out[str(k)] = {"skipped": "k + B_SIZE exceeds smallest valid reservoir"}
            continue
        rs, rf, rl = [], [], {float(l): [] for l in LAM}
        picks, held, held0, held1 = [], [], [], []
        for rep in range(REP):
            pa, pb = make_split(rng, m, n_vec, k, B_SIZE)
            M = sigfn(R, pa)
            crit = crit_from(R, pb)
            s, f = M[:, 0], M.mean(1)
            rs.append(spear(s, crit)); rf.append(spear(f, crit))
            for l in LAM:
                rl[float(l)].append(spear((1 - l) * s + l * f, crit))
            # 题目级折半：一半题目选 λ，另一半评估
            for _ in range(SPLITS):
                pm = rng.permutation(m)
                A, B = pm[: m // 2], pm[m // 2:]
                sc = np.array([spear(((1 - l) * s + l * f)[A], crit[A]) for l in LAM])
                bi = int(np.nanargmax(sc))
                picks.append(float(LAM[bi]))
                ls = LAM[bi]
                held.append(spear(((1 - ls) * s + ls * f)[B], crit[B]))
                held0.append(spear(s[B], crit[B]))
                held1.append(spear(f[B], crit[B]))
        rs, rf = np.array(rs), np.array(rf)
        out[str(k)] = {
            "success_mean": round(float(rs.mean()), 4), "success_sd": round(float(rs.std()), 4),
            "fused_mean": round(float(rf.mean()), 4), "fused_sd": round(float(rf.std()), 4),
            "gain_fused_minus_success": round(float((rf - rs).mean()), 4),
            "paired_win_rate_fused": round(float((rf > rs).mean()), 3),
            "lambda_curve": {str(l): round(float(np.mean(v)), 4) for l, v in rl.items()},
            "argmax_lambda_insample": float(max(rl, key=lambda x: np.mean(rl[x]))),
            "split_half": {
                "lambda_star_mean": round(float(np.mean(picks)), 3),
                "heldout_at_lambda_star": round(float(np.mean(held)), 4),
                "heldout_at_lambda_0": round(float(np.mean(held0)), 4),
                "heldout_at_lambda_1": round(float(np.mean(held1)), 4),
            },
        }
        sh = out[str(k)]["split_half"]
        print("  [%s k=%3d] success %.4f | fused %.4f | gain %+.4f (win %.2f) "
              "| λ* %.2f held-out %.4f (λ0 %.4f / λ1 %.4f)" % (
                  name, k, rs.mean(), rf.mean(), (rf - rs).mean(), (rf > rs).mean(),
                  sh["lambda_star_mean"], sh["heldout_at_lambda_star"],
                  sh["heldout_at_lambda_0"], sh["heldout_at_lambda_1"]), flush=True)
    return out


nJ = np.full(J_res.shape[0], 10 ** 6, dtype=int)      # Junyi 全部 n >= 1000 > K
print("=== O7 Junyi (n=%d exercises) ===" % J_res.shape[0], flush=True)
resJ = run(J_res, nJ, "junyi", signals_from)

nD = D_full[:, 0].astype(int)
print("=== O7 DBE (n=%d questions) ===" % D_res.shape[0], flush=True)
resD = run(D_res, nD, "dbe", signals_from_dbe)

res = {
    "design": "O7 held-out validation of difficulty estimators: disjoint reservoir "
              "slot blocks A (fit, size k) and B (criterion, size 250); no sample overlap",
    "B_SIZE": B_SIZE, "reps": REP, "splits": SPLITS, "k_list": KS, "signals": SIG,
    "junyi": {"n_exercises": int(J_res.shape[0]), "by_k": resJ},
    "dbe": {"n_questions": int(D_res.shape[0]), "by_k": resD},
    "reference": {
        "O5_expert_label_junyi_success": 0.2610, "O5_expert_label_junyi_fused": 0.3629,
        "O4_expert_label_dbe_success": 0.2170, "O4_expert_label_dbe_fused": 0.2899,
        "O6c_shared_sample_performance_success": 0.9151, "O6c_shared_sample_performance_fused": 0.9009,
    },
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
