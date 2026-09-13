# -*- coding: utf-8 -*-
"""O8：融合变体的留出验证 —— 融合的失败是"信号选择"问题还是"融合本身"问题？

O7 显示等权 7 信号融合在留出判据下全面劣于仅成功率（k=200 时 0.829 vs 0.951）。
但 M3 v3b 的 Q1 发现 upgrade_rate 在池内是**强负相关**（k=500 时 −0.756），
而 O5 早已报告它与专家标签的相关为 −0.1837 —— 也就是说这个反向信号在 O5 里
就被坐标上升优化器给了 +0.154 的正权重，是明确的错误配置。

本脚本在 O7 的留出框架下比较以下变体（Junyi，k ∈ {10,25,50,100,200}）：
  success      仅成功率（基线）
  fused7       O5 原始 7 信号等权
  fused6       剔除 upgrade_rate（依据 O5 已发表的负相关，非本次挑 cherry）
  fused3       仅 success + hint + attempts（v3b Q1 中池内最强的三个）
  各变体的 λ 收缩版 score = (1−λ)·success + λ·variant，λ 在题目折半上选、
  留出半上评，杜绝 λ 过拟合。

输出 results/code/o8_fusion_variants.json
"""
import json
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o8_fusion_variants.json"
Z = np.load(BASE + "/results/code/difficulty_cache.npz", allow_pickle=True)
J_res = Z["J_res"]
K = J_res.shape[2]
KS = [10, 25, 50, 100, 200]
B_SIZE, REP, SPLITS = 250, 25, 20
LAM = np.round(np.arange(0.0, 1.01, 0.05), 2)
M = J_res.shape[0]
n_vec = np.full(M, 10 ** 6, dtype=int)

VARIANTS = {
    "fused7": [0, 1, 2, 3, 4, 5, 6],
    "fused6_drop_upgrade": [0, 1, 2, 3, 5, 6],
    "fused3_success_hint_attempts": [0, 1, 3],
}


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def signals(pick):
    k = pick.shape[1]
    p3 = np.broadcast_to(pick[:, None, :], (M, 7, k))
    S = np.take_along_axis(J_res.astype(np.float64), p3, axis=2).sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


rng = np.random.default_rng(20260913)
res = {}
print("variant                       k   raw(succ / var)        λ*   held-out(λ* / λ0)")
for vname, cols in VARIANTS.items():
    res[vname] = {}
    for k in KS:
        raw_s, raw_v = [], []
        picks, held, held0, held1 = [], [], [], []
        for rep in range(REP):
            noise = rng.random((M, K))
            order = np.argsort(noise, axis=1)
            pa, pb = order[:, :k], order[:, k:k + B_SIZE]
            S = signals(pa)
            okb = np.take_along_axis(J_res.astype(np.float64)[:, 0:1, :],
                                     np.broadcast_to(pb[:, None, :], (M, 1, B_SIZE)),
                                     axis=2)[:, 0, :]
            crit = 1.0 - okb.mean(axis=1)
            s = S[:, 0]
            v = S[:, cols].mean(1)
            raw_s.append(spear(s, crit)); raw_v.append(spear(v, crit))
            for _ in range(SPLITS):
                pm = rng.permutation(M)
                A, B = pm[: M // 2], pm[M // 2:]
                sc = np.array([spear(((1 - l) * s + l * v)[A], crit[A]) for l in LAM])
                bi = int(np.nanargmax(sc))
                ls = float(LAM[bi])
                picks.append(ls)
                held.append(spear(((1 - ls) * s + ls * v)[B], crit[B]))
                held0.append(spear(s[B], crit[B]))
                held1.append(spear(v[B], crit[B]))
        res[vname][str(k)] = {
            "success_raw": round(float(np.mean(raw_s)), 4),
            "variant_raw": round(float(np.mean(raw_v)), 4),
            "delta_raw": round(float(np.mean(raw_v) - np.mean(raw_s)), 4),
            "lambda_star_mean": round(float(np.mean(picks)), 3),
            "heldout_at_lambda_star": round(float(np.mean(held)), 4),
            "heldout_at_lambda_0": round(float(np.mean(held0)), 4),
            "heldout_at_lambda_1": round(float(np.mean(held1)), 4),
            "gain_vs_success_pp": round(float(np.mean(held) - np.mean(held0)) * 100, 3),
        }
        r = res[vname][str(k)]
        print("%-28s %3d  %.4f / %.4f (%+.4f)   %.2f  %.4f / %.4f  (%+.3f pp)" % (
            vname, k, r["success_raw"], r["variant_raw"], r["delta_raw"],
            r["lambda_star_mean"], r["heldout_at_lambda_star"], r["heldout_at_lambda_0"],
            r["gain_vs_success_pp"]), flush=True)

json.dump({
    "design": "O8 held-out validation of fusion variants (disjoint reservoir blocks "
              "A=fitsize k, B=criterion 250), lambda chosen on a random half of exercises "
              "and evaluated on the held-out half",
    "variants": VARIANTS, "k_list": KS, "B_SIZE": B_SIZE, "reps": REP, "splits": SPLITS,
    "results": res,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
