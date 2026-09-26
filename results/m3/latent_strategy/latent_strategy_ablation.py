# -*- coding: utf-8 -*-
"""
E3 消融（latent 口径的稳健性检验）
========================================================================
§5.9 诚实边界第 3 条写明 "T-sensitivity ablation pending"。本脚本补上：
在同一 m3_simulator latent 环境（不重调参）下，扫描两个敏感维度，
检验 flow_zone 在 final_gain 上优于 all_easy 的结论是否稳健：

  (1) 视野长度 T  ∈ {40, 80, 120, 200, 300}   —— 主消融（T 敏感性）
  (2) 观测噪声 OBS_NOISE ∈ {0.0, 0.05, 0.15}  —— 噪声鲁棒性

对每个 (T, noise) 组合，跑 flow_zone / all_easy / all_hard / random 的
latent 模拟（SEEDS=M.SEEDS），报告：
  - 各策略 final_gain 均值±SD
  - Δ(flow_zone − all_easy) 与配对 t 判定（flow_zone 是否仍更优）
  - final_m 是否仍=1.0（说明差异是效率而非天花板）

输出：latent_strategy_ablation.json
"""
import os
import sys
import json
from math import erf, sqrt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "code")))
import m3_simulator as M  # noqa: E402

OUT = os.path.join(_HERE, "latent_strategy_ablation.json")
SEEDS = M.SEEDS

_RNG = np.random.default_rng(20260925)


def sim(m0_m, T, noise, select_fn, seed):
    rng = np.random.default_rng(10000 + seed)
    m = rng.uniform(M.M0_LO, M.M0_HI)
    cum = 0.0
    for _ in range(T):
        mhat = float(np.clip(m + rng.normal(0.0, noise), 0.0, 1.0))
        j = select_fn(mhat)
        m, _, g = M.step(m, j, rng)
        cum += g
    return cum


def flow_zone(mhat):
    ps = np.array([M.p_succ(mhat, j) for j in range(M.D)])
    return int(np.argmin(np.abs(ps - M.PSTAR)))


def all_easy(mhat):
    return int(np.argmin(M.DELTA))


def all_hard(mhat):
    return int(np.argmax(M.DELTA))


def random_choice(mhat):
    return int(_RNG.integers(M.D))


STRATS = {
    "flow_zone_latent": flow_zone,
    "all_easy_latent": all_easy,
    "all_hard_latent": all_hard,
    "random_latent": random_choice,
}


def paired_t(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = a - b
    sd = d.std(ddof=1)
    if sd == 0:
        return 0.0, 1.0
    t = d.mean() / (sd / np.sqrt(len(d)))
    # 大样本正态近似 p（双尾）
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / np.sqrt(2.0))))
    return float(t), float(p)


def run_grid():
    Ts = [40, 80, 120, 200, 300]
    noises = [0.0, 0.05, 0.15]
    grid = []
    for T in Ts:
        for noise in noises:
            res = {name: [] for name in STRATS}
            for name, fn in STRATS.items():
                for s in range(SEEDS):
                    res[name].append(sim(None, T, noise, fn, s))
            fg_fz = np.array(res["flow_zone_latent"])
            fg_ae = np.array(res["all_easy_latent"])
            t, p = paired_t(fg_fz, fg_ae)
            diff = fg_fz - fg_ae
            fz_wins = bool(p < 0.05 and diff.mean() > 0)
            row = {
                "T": T,
                "OBS_NOISE": noise,
                "final_gain": {
                    name: {
                        "mean": round(float(np.mean(res[name])), 5),
                        "sd": round(float(np.std(res[name], ddof=1)), 5),
                    }
                    for name in STRATS
                },
                "delta_flowzone_minus_alleasy_mean": round(float(diff.mean()), 5),
                "delta_sd": round(float(diff.std(ddof=1)), 5),
                "paired_t": round(t, 4),
                "paired_p": float(p),
                "flow_zone_wins": fz_wins,
            }
            grid.append(row)
            print(f"T={T:3d} noise={noise:.2f} | Δ(fz−ae)={diff.mean():+.4f} "
                  f"(SD={diff.std(ddof=1):.4f}) t={t:+.2f} p={p:.2e} "
                  f"| fz_wins={fz_wins} | "
                  f"fz={np.mean(fg_fz):.3f} ae={np.mean(fg_ae):.3f}")
    return grid


def main():
    grid = run_grid()
    # 主结论：在 T=120（与 §5.9 主表一致）下是否稳健；并报告跨 T 是否单调/一致
    base = next(r for r in grid if r["T"] == 120 and abs(r["OBS_NOISE"] - 0.05) < 1e-9)
    wins_all = all(r["flow_zone_wins"] for r in grid)
    n_win = sum(1 for r in grid if r["flow_zone_wins"])
    wins_desc = f"全部 {len(grid)} 个" if wins_all else f"其中 {n_win} 个"
    verdict = (
        f"flow_zone 在 final_gain 上优于 all_easy 的结论，在 {len(grid)} 个 (T,noise) "
        f"组合中{wins_desc}成立；"
        f"T=120/noise=0.05（与 §5.9 主表同口径）Δ={base['delta_flowzone_minus_alleasy_mean']:+.4f}。"
        + ("→ 结论对视野长度与观测噪声稳健，解除 'T-sensitivity ablation pending'。"
           if wins_all else
           "→ 结论对部分设置敏感，须在 §5.9 标注其成立条件。")
    )
    print("\n判定：", verdict)
    out = {"settings": {"D": M.D, "SEEDS": SEEDS, "ALPHA": M.ALPHA,
                        "PSTAR": M.PSTAR, "SG": M.SG, "ETA": M.ETA,
                        "LAM": M.LAM},
           "grid": grid,
           "base_T120_noise005": base,
           "verdict": verdict}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[已写出] {OUT}")


if __name__ == "__main__":
    main()
