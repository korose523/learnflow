# -*- coding: utf-8 -*-
"""
E3 补充消融（LS-target / LS-prior）
========================================================================
§5.9 消融表已实跑 LS-obs 与 LS-horizon（T-sensitivity 解除）。本脚本补上另两项：

  LS-target：flow_zone 的瞄准点 T* ∈ {0.60, 0.70, 0.75, 0.80, 0.90}，
             检验"瞄准 0.75"是否确为最优瞄准点，以及 flow_zone 对 all_easy 的优势
             是否依赖该特定瞄准点（同一 latent 环境，不重调参）。
  LS-prior ：ctx+LLM 先验策略的先验偏移 shift ∈ {0.0 正确, +0.18 偏难, −0.18 偏易}，
             检验 §5.1 的"先验符号"结论在 latent（final_gain）口径下是否保持——
             正确先验是否仍优于错误先验。

复用 m3_simulator 全部常量与 step()；策略逐 sim 新建（ctx+LLM 的 UCB 策略不在种子间泄漏）。
输出：latent_strategy_ls_target_prior.json
"""
import os
import sys
import json
from math import erf, sqrt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "code")))
import m3_simulator as M  # noqa: E402

OUT = os.path.join(_HERE, "latent_strategy_ls_target_prior.json")
SEEDS = M.SEEDS


def make_act(kind, param=None):
    """无状态策略的选择函数 choose(mhat)（all_easy / flow_zone_target）。

    ctx_llm 需要跨步在线学习，无法用纯函数表达，改由 make_policy 返回策略实例工厂。
    """
    if kind == "all_easy":
        return lambda mhat: int(np.argmin(M.DELTA))
    if kind == "flow_zone_target":
        target = float(param)
        return lambda mhat: int(np.argmin(
            np.abs(np.array([M.p_succ(mhat, j) for j in range(M.D)]) - target)))
    raise ValueError(kind)


class StatelessPolicy:
    """把无状态选择函数 choose(mhat) 包装成 Policy 接口：忽略 t，不在线学习。"""

    def __init__(self, choose):
        self.choose = choose

    def select(self, mhat, t):
        return self.choose(mhat)

    def update(self, mhat, j, g):
        pass


class CtxLLMPriorPolicy:
    """Contextual-UCB + LLM 先验（含偏移 shift）。

    每个 seed 一个实例、跨步复用（先验均值与计数在线累积）；select 传入**真实步数** t
    使 ln(t+2) 探索项生效；每步按 m3_simulator 的口径用归一化奖励 g/ETA 调用 update。
    旧实现 t 恒为 0 且从不 update，等于完全没有在线学习。
    """

    def __init__(self, shift):
        self.pol = M.ContextualUCB(M.make_llm_prior(float(shift)), M.PRIOR_LAMBDA)

    def select(self, mhat, t):
        return self.pol.select(mhat, t)

    def update(self, mhat, j, g):
        self.pol.update(mhat, j, g)


def make_policy(kind, param=None):
    """返回 make(seed) -> 策略实例；每个 seed 新建一个实例，避免跨种子状态泄漏。"""
    if kind == "ctx_llm":
        return lambda seed: CtxLLMPriorPolicy(param)
    return lambda seed: StatelessPolicy(make_act(kind, param))


def sim(make_pol, seed):
    """与 m3_simulator.simulate 同构：select(mhat, t) -> step -> update(mhat, j, g/ETA)。"""
    rng = np.random.default_rng(10000 + seed)
    pol = make_pol(seed)
    m = rng.uniform(M.M0_LO, M.M0_HI)
    cum = 0.0
    for t in range(M.T):
        mhat = float(np.clip(m + rng.normal(0.0, M.OBS_NOISE), 0.0, 1.0))
        j = pol.select(mhat, t)
        m, _, g = M.step(m, j, rng)
        cum += g
        pol.update(mhat, j, g / M.ETA)
    return cum


def paired_t(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = a - b
    sd = d.std(ddof=1)
    if sd == 0:
        return 0.0, 1.0
    t = d.mean() / (sd / np.sqrt(len(d)))
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))
    return float(t), float(p)


def main():
    # ---------- LS-target ----------
    targets = [0.60, 0.70, 0.75, 0.80, 0.90]
    ae = np.array([sim(make_policy("all_easy"), s) for s in range(SEEDS)])
    print("=== LS-target：flow_zone(T*) vs all_easy ===")
    ls_target = []
    for T_ in targets:
        fz = np.array([sim(make_policy("flow_zone_target", T_), s) for s in range(SEEDS)])
        t, p = paired_t(fz, ae)
        wins = bool(p < 0.05 and (fz.mean() - ae.mean()) > 0)
        ls_target.append({"target": T_, "fz_mean": round(float(fz.mean()), 5),
                          "ae_mean": round(float(ae.mean()), 5),
                          "delta": round(float(fz.mean() - ae.mean()), 5),
                          "paired_t": round(t, 3), "paired_p": float(p),
                          "fz_wins": wins})
        print(f"  T*={T_:.2f} | fz={fz.mean():.4f} ae={ae.mean():.4f} "
              f"Δ={fz.mean()-ae.mean():+.4f} t={t:+.2f} p={p:.2e} wins={wins}")
    best = max(ls_target, key=lambda r: r["fz_mean"])
    print(f"  → flow_zone 自身 final_gain 最高的瞄准点 = {best['target']:.2f} "
          f"(final_gain={best['fz_mean']:.4f})")

    # ---------- LS-prior ----------
    shifts = [0.0, 0.18, -0.18]
    print("\n=== LS-prior：ctx+LLM 先验偏移 shift ===")
    ls_prior = []
    for sh in shifts:
        cl = np.array([sim(make_policy("ctx_llm", sh), s) for s in range(SEEDS)])
        ls_prior.append({"shift": sh, "final_gain_mean": round(float(cl.mean()), 5),
                         "final_gain_sd": round(float(cl.std(ddof=1)), 5)})
        print(f"  shift={sh:+.2f} | final_gain={cl.mean():.4f}±{cl.std(ddof=1):.4f}")

    # verdict
    correct = next(r for r in ls_prior if r["shift"] == 0.0)["final_gain_mean"]
    biased = [r for r in ls_prior if r["shift"] != 0.0]
    if all(correct > b["final_gain_mean"] for b in biased):
        pv = ("正确先验(shift=0)的 final_gain 高于偏难/偏易先验 → "
              "§5.1 的『先验符号』结论在 latent(final_gain)口径下保持：先验方向仍决定增益大小。")
    else:
        pv = ("正确先验未一致高于偏移先验 → §5.1 先验符号结论在 latent 口径下不完全保持，须标注。")
    print("\n  判定：", pv)

    out = {"settings": {"D": M.D, "T": M.T, "SEEDS": SEEDS, "PSTAR": M.PSTAR,
                        "SG": M.SG, "ETA": M.ETA, "LAM": M.LAM, "OBS_NOISE": M.OBS_NOISE},
           "ls_target": ls_target, "ls_prior": ls_prior, "verdict": pv}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[已写出] {OUT}")


if __name__ == "__main__":
    main()
