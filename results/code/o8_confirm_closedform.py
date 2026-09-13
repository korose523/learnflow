# -*- coding: utf-8 -*-
"""O8 闭式 λ(k) 直接留出验证（confirmatory cell）。

O8 主脚本只在"经验 λ* 收缩"（留一 k + 题目折半选 λ、留出半评）下验证了 fused6。
本脚本补一个确认单元：直接把章节闭式 λ_cf(k)=1/(1+(k/27.3)^0.895) 当作固定 λ
代入同一套留出协议（A=拟合 k 题、B=判据 250 题；λ 在半上选、另半上评），
看闭式本身在留出半上的表现是否与经验 λ* 相当。

严格复用 O8 的随机协议（seed=20260913、REP=25、SPLITS=20、B_SIZE=250），
仅把"在 A 半上选出的经验 λ*"替换为"闭式固定 λ_cf(k)"，再在 B 半（留出）上评估。
这样与 o8_fusion_variants.json 的 fused6_drop_upgrade.heldout_at_lambda_star 是苹果对苹果。
"""
import json
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
NPZ = BASE + "/results/code/difficulty_cache.npz"
JSON = BASE + "/results/code/o8_fusion_variants.json"
OUT = BASE + "/results/code/o8_confirm_closedform.txt"

Z = np.load(NPZ, allow_pickle=True)
J_res = Z["J_res"]
M = J_res.shape[0]
K = J_res.shape[2]
KS = [10, 25, 50, 100, 200]
B_SIZE, REP, SPLITS = 250, 25, 20
COLS = [0, 1, 2, 3, 5, 6]  # fused6_drop_upgrade：剔除 upgrade_rate(index 4)


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


def lambda_cf(k):
    return 1.0 / (1.0 + (k / 27.3) ** 0.895)


d = json.load(open(JSON, encoding="utf-8"))
emp = d["results"]["fused6_drop_upgrade"]

rng = np.random.default_rng(20260913)
lines = []
lines.append("=== O8 闭式 λ(k) 直接留出验证（fused6 = 剔除 upgrade_rate）===")
lines.append(f"{'k':>4}  {'λ_cf':>6}  {'heldout@λ_cf':>13}  {'heldout@λ*_emp':>14}  {'Δpp':>7}  deploy_ok")
for k in KS:
    lc = lambda_cf(k)
    held_cf = []
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
        v = S[:, COLS].mean(1)
        score_cf = (1.0 - lc) * s + lc * v
        for _ in range(SPLITS):
            pm = rng.permutation(M)
            B = pm[M // 2:]
            held_cf.append(spear(score_cf[B], crit[B]))
    hc = float(np.mean(held_cf))
    he = emp[str(k)]["heldout_at_lambda_star"]
    delta = round((hc - he) * 100, 3)
    ok = "YES" if abs(delta) <= 0.5 else "REVIEW"
    lines.append(f"{k:>4}  {lc:>6.3f}  {hc:>13.4f}  {he:>14.4f}  {delta:>+7.3f}  {ok}")
    lines.append(f"      (fused6 经验λ*={emp[str(k)]['lambda_star_mean']:.3f}; "
                f"闭式λ_cf={lc:.3f})")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
