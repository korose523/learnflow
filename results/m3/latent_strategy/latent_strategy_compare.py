# -*- coding: utf-8 -*-
"""
E3 —— 把 flow_zone / all_easy / all_hard / random 移植进 m3_simulator 的 latent 状态环境
====================================================================================
目的：§5.3 的奖励是即时成功率，而各策略按定义即是在选择难度，故"某策略在即时成功率上更优"
不携带信息（同义反复）。要产出**可辩护的策略优劣证据**，结果变量必须与"对错"独立。

本脚本复用 m3_simulator.py 的全部环境常量与 step()（Rasch/1PL 成功概率 + 合意难度核增益
+ BKT 式遗忘；智能体只见含噪观测 m̂），**不重新调参**。其主指标 final_gain = Σg 直接是潜在
掌握度 m 的累积增量，**与单步对错不同源**。

策略（与 §5.3 同名同义，但作用在 latent 口径）：
  flow_zone_latent : 选使 |p_succ(m̂, j) − 0.75| 最小的题（用含噪观测 m̂，非 oracle m）
  all_easy_latent  : 恒选 DELTA 最小（最易）的题
  all_hard_latent  : 恒选 DELTA 最大（最难）的题
  random_latent    : 均匀随机

参考行（同一环境，已在 m3_simulator 中定义，仅供解释天花板/下限）：
  oracle(已知m)    : 已知真实 m_t 时的贪心最优（本行通过 knows_m=True 拿到真实 m，
                     与 §5.1 表 1 的 oracle 行同定义；其余各行一律只见 m̂）
  matched(模型已知,用m̂) : 模型参数已知、状态用 m̂ 的匹配难度
  ctx+LLM先验(正确) : Contextual-UCB + 正确 LLM 先验（每 seed 一个实例、跨步在线学习）

结果变量（三个，明确区分）：
  (1) final_gain = Σg          —— 主结果变量，与对错独立（latent m 的累积增量）
  (2) immediate_success_rate   —— 仅作行为描述，与 §5.3 口径衔接（mean over steps of p_succ）
  (3) final_m                  —— 终态潜在能力

运行：python latent_strategy_compare.py   （cwd 任意；自动定位 m3_simulator）
输出：latent_strategy_results.json + 控制台表
"""
import os
import sys
import json
import numpy as np

# 定位 m3_simulator（results/code）
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "code")))
import m3_simulator as M  # noqa: E402

OUT = os.path.join(_HERE, "latent_strategy_results.json")
RNG = np.random.default_rng(20260925)


def sim_latent(make_policy, seed, knows_m=False):
    """与 m3_simulator.simulate 同构，但额外返回 final_m 与 mean success prob。

    make_policy(seed) -> 策略实例：每个 seed 新建一个，便于跨步在线累积状态。
    每步顺序与 m3_simulator.simulate 一致：select(x, t) -> step -> update(mhat, j, g/ETA)。
    knows_m=True 时把**真实** m_t 交给 select，否则只给含噪观测 m̂（默认）。
    """
    rng = np.random.default_rng(10000 + seed)
    pol = make_policy(seed)
    m = rng.uniform(M.M0_LO, M.M0_HI)
    cum = 0.0
    sum_p = 0.0
    for t in range(M.T):
        mhat = float(np.clip(m + rng.normal(0.0, M.OBS_NOISE), 0.0, 1.0))
        j = pol.select(m if knows_m else mhat, t)
        m2, p, g = M.step(m, j, rng)
        cum += g
        sum_p += p
        if not knows_m:
            pol.update(mhat, j, g / M.ETA)          # 归一化奖励，同 m3_simulator
        m = m2
    return {"final_m": m, "final_gain": cum, "imm_sr": sum_p / M.T}


class StatelessPolicy:
    """把无状态选择函数 choose(x) 包装成 Policy 接口：忽略时间步 t，不在线学习。"""

    def __init__(self, choose):
        self.choose = choose

    def select(self, x, t):
        return self.choose(x)

    def update(self, mhat, j, g):
        pass


# ---------------- 策略（确定性，除 random） ----------------
def flow_zone(mhat):
    ps = np.array([M.p_succ(mhat, j) for j in range(M.D)])
    return int(np.argmin(np.abs(ps - M.PSTAR)))


def all_easy(mhat):
    return int(np.argmin(M.DELTA))


def all_hard(mhat):
    return int(np.argmax(M.DELTA))


def random_choice(mhat):
    return int(RNG.integers(M.D))


def _greedy_exp_gain(x):
    """合意难度贪心 argmax_j exp_gain(x, j)；与 m3_simulator.oracle_action 同定义。"""
    return int(np.argmax([M.exp_gain(x, j) for j in range(M.D)]))


def oracle_known(m):
    # 真 oracle：入参是**真实** m_t（由 knows_m=True 传入），即 §5.1 表 1 的 oracle 行。
    # 旧实现在此收到的其实是 m̂，导致它退化成 matched（7.08996）。
    return _greedy_exp_gain(m)


def matched_model_known(mhat):
    # 匹配难度：规则与 oracle 完全相同，唯一区别是输入为含噪观测 m̂。
    return _greedy_exp_gain(mhat)


class CtxLLMPriorPolicy:
    """Contextual-UCB + 正确 LLM 先验：每个 seed 一个实例、跨步复用（计数器在线累积），
    并把真实步数 t 传给 select。旧实现每步新建实例且 t 恒为 0，探索项退化为常数，
    等于完全没有在线学习。"""

    def __init__(self):
        self.pol = M.ContextualUCB(M.make_llm_prior(0.0), M.PRIOR_LAMBDA)

    def select(self, mhat, t):
        return self.pol.select(mhat, t)

    def update(self, mhat, j, g):
        self.pol.update(mhat, j, g)


STRATEGIES = {
    "flow_zone_latent": lambda seed: StatelessPolicy(flow_zone),
    "all_easy_latent": lambda seed: StatelessPolicy(all_easy),
    "all_hard_latent": lambda seed: StatelessPolicy(all_hard),
    "random_latent": lambda seed: StatelessPolicy(random_choice),
    # 参考行
    "oracle(已知m)": lambda seed: StatelessPolicy(oracle_known),
    "matched(模型已知,用m̂)": lambda seed: StatelessPolicy(matched_model_known),
    "ctx+LLM先验(正确)": lambda seed: CtxLLMPriorPolicy(),
}

# 唯一能看见真实状态 m 的行。其余 6 行一律只用含噪观测 m̂。
KNOWS_M = {"oracle(已知m)"}

COMPARABLE = ["flow_zone_latent", "all_easy_latent", "all_hard_latent", "random_latent"]


def main():
    results = {name: {"final_gain": [], "imm_sr": [], "final_m": []}
               for name in STRATEGIES}
    for name, make in STRATEGIES.items():
        knows_m = name in KNOWS_M
        for s in range(M.SEEDS):
            out = sim_latent(make, s, knows_m=knows_m)
            results[name]["final_gain"].append(out["final_gain"])
            results[name]["imm_sr"].append(out["imm_sr"])
            results[name]["final_m"].append(out["final_m"])

    print("=" * 92)
    print(f"E3 latent 策略比较（D={M.D}, T={M.T}, SEEDS={M.SEEDS}; 环境同 m3_simulator，未重调参）")
    print(f"主结果变量 final_gain = Σg（与对错独立）；imm_sr = 平均成功概率（行为描述）")
    print("=" * 92)
    hdr = f"{'策略':24s} {'final_gain(均值±SD)':>22s} {'imm_sr':>8s} {'final_m':>8s}"
    print(hdr)
    summary = {}
    for name in STRATEGIES:
        fg = np.array(results[name]["final_gain"])
        sr = np.array(results[name]["imm_sr"])
        fm = np.array(results[name]["final_m"])
        summary[name] = {
            "final_gain_mean": round(float(fg.mean()), 5),
            "final_gain_sd": round(float(fg.std(ddof=1)), 5),
            "imm_sr_mean": round(float(sr.mean()), 5),
            "final_m_mean": round(float(fm.mean()), 5),
            "comparable": name in COMPARABLE,
        }
        tag = " *" if name in COMPARABLE else "  "
        print(f"{name+tag:26s} {fg.mean():.5f}±{fg.std(ddof=1):.4f} {sr.mean():>8.4f} {fm.mean():>8.4f}")

    # 关键判定：flow_zone_latent 是否在 final_gain 上优于 all_easy_latent
    fg_fz = np.array(results["flow_zone_latent"]["final_gain"])
    fg_ae = np.array(results["all_easy_latent"]["final_gain"])
    diff = fg_fz - fg_ae
    from scipy import stats as _st
    tt = _st.ttest_rel(fg_fz, fg_ae)
    print("")
    print(f"判定（预先声明）：flow_zone_latent − all_easy_latent  Δ(final_gain) = "
          f"{diff.mean():+.5f} (SD={diff.std(ddof=1):.5f}), 配对 t p={tt.pvalue:.3e}")
    if tt.pvalue < 0.05 and diff.mean() > 0:
        verdict = ("flow_zone 在独立结果变量(final_gain)上优于 all_easy —— "
                   "§5.3 可从'策略行为的模拟比较'升级为'策略优劣的模拟比较'。")
    elif tt.pvalue < 0.05 and diff.mean() < 0:
        verdict = ("flow_zone 在 final_gain 上反而劣于 all_easy —— 负结果："
                   "'瞄准 0.75 成功率在即时成功率口径下最优，但在学习增益口径下并非最优'。")
    else:
        verdict = ("flow_zone 与 all_easy 在 final_gain 上不可区分 —— 两种口径结论一致，不支持任一方向。")
    print("判定结论：", verdict)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"settings": {"D": M.D, "T": M.T, "SEEDS": M.SEEDS,
                                "ALPHA": M.ALPHA, "PSTAR": M.PSTAR, "SG": M.SG,
                                "ETA": M.ETA, "LAM": M.LAM, "OBS_NOISE": M.OBS_NOISE},
                   "summary": summary, "verdict": verdict},
                  f, ensure_ascii=False, indent=2)
    print("")
    print(f"[已写出] {OUT}")


if __name__ == "__main__":
    main()
