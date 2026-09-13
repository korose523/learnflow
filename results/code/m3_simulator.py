# -*- coding: utf-8 -*-
"""
M3 子设计一：有序动作 bandit + LLM 先验边界 —— 自建自验模拟器
================================================================
自包含、可重跑。仅依赖 numpy + scipy。不依赖任何外部数据或他人结果。

环境（Learner–Item 交互模拟器）
  状态: 真实掌握度 m_t ∈ [0,1]（隐藏）。
  动作: 有序难度 d ∈ {0,...,D-1}（D=10，潜难度 delta_j 递增）。
  成功: p = sigmoid(alpha * (4 m - 2 - delta_j))               （Rasch/1PL 型）
  学习: g = eta * exp(-(p - p*)^2 / (2 sg^2)) * LogNormal(0, s)
        —— "合意难度"核，p*≈0.75 时增益最大（desirable difficulty）。
  遗忘: m_{t+1} = clip( m_t + g - lam * m_t , 0, 1 )
  代价: c_j = c0 + c1 * (delta_j - delta_0)  （越难，单位时间代价越高）
  观测: 智能体仅见 (m̂_t = m_t + N(0,0.05) 的掌握度估计, 动作 j_t, 实现增益 g_t)。

策略（奖励一律按 ETA 归一化到 ~[0,1]，使 UCB bonus 尺度匹配）
  T1 无上下文(忽略次序): eps-greedy、Thompson Sampling、Lipschitz-UCB
  T2 有上下文(m̂ 分箱): Contextual-UCB
  T3 LLM 先验: Contextual-UCB + 正确先验 / 错误先验（演示"先验边界"）
  参照: matched = 模型已知但状态用 m̂ 的匹配难度策略；Oracle = 已知真实 m_t。

指标
  学习曲线、伪遗憾(pseudo-regret)、达目标掌握度轮次、心流区 ∂Φ+ 非退化(边界斜率)。

参数取值来源：均为"合理设定"（量级取自教学系统常识），非拟合真实数据；见 md。

运行: python m3_simulator.py
输出: 控制台 + m3_output.txt + m3_results.json + m3_operating_points.csv
"""
import json
import numpy as np
from scipy import stats

OUTDIR = r"E:/learnflow\results"
LOG = []

# ---------------- 环境参数（合理设定，非拟合） ----------------
D = 10
DELTA = np.linspace(-2.0, 2.0, D)     # 潜难度
ALPHA = 1.5                           # 区分度
PSTAR = 0.75                          # 合意难度对应的成功率
SG = 0.18                             # 合意核宽度
ETA = 0.06                            # 最大单轮学习率
SIG_LOG = 0.20                        # 学习增益乘性噪声
LAM = 0.015                           # 遗忘率
C0, C1 = 1.0, 0.50                    # 代价 c_j = C0 + C1*(delta_j-delta_0)
M0_LO, M0_HI = 0.05, 0.15             # 初始掌握度范围
OBS_NOISE = 0.05                      # 掌握度估计噪声
T = 120                               # 交互轮次
TARGET = 0.90                         # 目标掌握度
N_CTX = 10                            # 上下文(掌握度)分箱数
LIPSCH = 0.10                         # Lipschitz 常数（归一化增益尺度）
PRIOR_LAMBDA = 4.0                    # LLM 先验伪计数强度
SEEDS = 60


def say(s=""):
    print(s)
    LOG.append(str(s))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def p_succ(m, j):
    return float(sigmoid(ALPHA * (4.0 * m - 2.0 - DELTA[j])))


def exp_gain(m, j):
    """无噪声期望增益（原始单位）"""
    p = p_succ(m, j)
    return ETA * float(np.exp(-((p - PSTAR) ** 2) / (2.0 * SG ** 2)))


def oracle_action(m):
    return int(np.argmax([exp_gain(m, j) for j in range(D)]))


def step(m, j, rng):
    p = p_succ(m, j)
    g = exp_gain(m, j) * float(np.exp(rng.normal(0.0, SIG_LOG)))
    m2 = float(np.clip(m + g - LAM * m, 0.0, 1.0))
    return m2, p, g


# ---------------- 策略（update 收到的是归一化奖励 g/ETA） ----------------
class Policy:
    name = "base"

    def select(self, mhat, t):
        raise NotImplementedError

    def update(self, mhat, j, g):
        pass


class EpsGreedy(Policy):
    name = "eps-greedy"

    def __init__(self, eps=0.10, seed=0):
        self.eps = eps
        self.sum = np.zeros(D)
        self.cnt = np.zeros(D)
        self.rng = np.random.default_rng(seed)

    def select(self, mhat, t):
        if self.rng.random() < self.eps or (self.cnt == 0).all():
            return int(self.rng.integers(D))
        mean = np.where(self.cnt > 0, self.sum / np.maximum(self.cnt, 1), -np.inf)
        return int(np.argmax(mean))

    def update(self, mhat, j, g):
        self.sum[j] += g
        self.cnt[j] += 1


class Thompson(Policy):
    name = "thompson"

    def __init__(self, seed=0, sigma=0.15):
        self.sum = np.zeros(D)
        self.cnt = np.zeros(D)
        self.sigma = sigma
        self.rng = np.random.default_rng(seed)

    def select(self, mhat, t):
        mu = np.where(self.cnt > 0, self.sum / np.maximum(self.cnt, 1), 0.30)
        sd = np.where(self.cnt > 0, self.sigma / np.sqrt(np.maximum(self.cnt, 1)), 0.5)
        return int(np.argmax(self.rng.normal(mu, sd)))

    def update(self, mhat, j, g):
        self.sum[j] += g
        self.cnt[j] += 1


class LipschitzUCB(Policy):
    """有序臂 Lipschitz-UCB：U_j = min_k [ x̄_k + L|j-k| + sqrt(2 ln(t+1)/n_k) ]"""
    name = "lipschitz-ucb"

    def __init__(self, L=LIPSCH):
        self.L = L
        self.sum = np.zeros(D)
        self.cnt = np.zeros(D)

    def select(self, mhat, t):
        idx = np.full(D, np.inf)
        for j in range(D):
            for k in range(D):
                if self.cnt[k] == 0:
                    continue
                bonus = np.sqrt(2.0 * np.log(t + 2.0) / self.cnt[k])
                idx[j] = min(idx[j], self.sum[k] / self.cnt[k] + self.L * abs(j - k) + bonus)
        if not np.isfinite(idx).any():
            return int(np.argmin(self.cnt))
        return int(np.argmax(idx))

    def update(self, mhat, j, g):
        self.sum[j] += g
        self.cnt[j] += 1


class ContextualUCB(Policy):
    """上下文(m̂ 分箱) UCB；可选 LLM 先验初始化（先验形状 over 难度，归一化 [0,1]）"""
    name = "contextual-ucb"

    def __init__(self, prior_shape=None, prior_lambda=0.0):
        self.sum = np.zeros((N_CTX, D))
        self.cnt = np.zeros((N_CTX, D))
        self.prior = prior_shape
        self.plam = prior_lambda

    def _b(self, mhat):
        return min(max(int(mhat * N_CTX), 0), N_CTX - 1)

    def select(self, mhat, t):
        b = self._b(mhat)
        n = self.cnt[b]
        if self.prior is not None:
            mean = (self.sum[b] + self.plam * self.prior[b]) / (n + self.plam)
        else:
            mean = np.where(n > 0, self.sum[b] / np.maximum(n, 1), 0.0)
        bonus = np.sqrt(2.0 * np.log(t + 2.0) / (n + 1.0))
        return int(np.argmax(mean + bonus))

    def update(self, mhat, j, g):
        b = self._b(mhat)
        self.sum[b, j] += g
        self.cnt[b, j] += 1


class MatchedModel(Policy):
    """模型已知（Rasch+合意核参数已知），但学习者状态用含噪估计 m̂ 的匹配难度策略。"""
    name = "matched(模型已知,用m̂)"

    def select(self, mhat, t):
        return int(np.argmax([exp_gain(mhat, j) for j in range(D)]))


def make_llm_prior(shift=0.0, pstar=PSTAR):
    """归一化 LLM 先验（[0,1]）：'最优难度 ≈ 使成功率≈p* 的匹配难度'。
       shift>0 -> 认为学习者更超前 -> 偏好更难（错误先验）。"""
    P = np.zeros((N_CTX, D))
    for b in range(N_CTX):
        mc = (b + 0.5) / N_CTX + shift
        for j in range(D):
            p = p_succ(mc, j)
            P[b, j] = np.exp(-((p - pstar) ** 2) / (2.0 * SG ** 2))
    return P


# ---------------- 仿真 ----------------
def simulate(policy, seed, oracle_knows_m=False):
    rng = np.random.default_rng(10000 + seed)
    m = rng.uniform(M0_LO, M0_HI)
    cum = 0.0
    regret = 0.0
    cum_time = 0.0
    err_sum = 0.0
    hit = None
    curve = np.empty(T)
    rcurve = np.empty(T)
    for t in range(T):
        mhat = float(np.clip(m + rng.normal(0.0, OBS_NOISE), 0.0, 1.0))
        r_star = max(exp_gain(m, j) for j in range(D))
        j = oracle_action(m) if oracle_knows_m else policy.select(mhat, t)
        m2, p, g = step(m, j, rng)
        c = C0 + C1 * (DELTA[j] - DELTA[0])
        cum += g
        regret += (r_star - g)
        cum_time += c
        err_sum += (1.0 - p)
        if hit is None and m2 >= TARGET:
            hit = t + 1
        curve[t] = cum
        rcurve[t] = regret
        if not oracle_knows_m:
            policy.update(mhat, j, g / ETA)          # 归一化奖励
        m = m2
    rtt = hit if hit is not None else (T + 1)
    return {"curve": curve, "regret_curve": rcurve, "final_gain": cum,
            "final_regret": regret, "err_rate": err_sum / T, "cum_time": cum_time,
            "rounds_to_target": rtt, "reached": hit is not None}


def pareto_min(points):
    pts = sorted(points, key=lambda z: (z[0], z[1]))
    front = []
    best_err = np.inf
    for c, e in pts:
        if e < best_err - 1e-15:
            front.append((c, e))
            best_err = e
    return front


def main():
    policies = [
        ("eps-greedy", lambda s: EpsGreedy(seed=s)),
        ("thompson", lambda s: Thompson(seed=s)),
        ("lipschitz-ucb", lambda s: LipschitzUCB()),
        ("contextual-ucb", lambda s: ContextualUCB()),
        ("ctx+LLM先验(正确)", lambda s: ContextualUCB(make_llm_prior(0.0), PRIOR_LAMBDA)),
        ("ctx+LLM先验(错误,偏难)", lambda s: ContextualUCB(make_llm_prior(0.18), PRIOR_LAMBDA)),
        ("matched(模型已知,用m̂)", lambda s: MatchedModel()),
    ]

    curves, summary, op_points = {}, {}, []
    per_seed_gain = {}

    def collect(pname, out, s):
        op_points.append((pname, s, out["err_rate"], out["rounds_to_target"],
                          out["cum_time"], out["final_gain"], out["final_regret"]))

    for pname, mk in policies:
        C = np.zeros((SEEDS, T))
        R = np.zeros((SEEDS, T))
        fg, fr, er, ct, rtt = [], [], [], [], []
        for s in range(SEEDS):
            out = simulate(mk(s), s)
            C[s], R[s] = out["curve"], out["regret_curve"]
            fg.append(out["final_gain"]); fr.append(out["final_regret"])
            er.append(out["err_rate"]); ct.append(out["cum_time"])
            rtt.append(out["rounds_to_target"]); collect(pname, out, s)
        curves[pname] = {"gain_mean": C.mean(0).tolist(),
                         "gain_se": (C.std(0, ddof=1) / np.sqrt(SEEDS)).tolist(),
                         "regret_mean": R.mean(0).tolist()}
        summary[pname] = summarize(fg, fr, er, ct, rtt)
        per_seed_gain[pname] = np.array(fg)

    # Oracle
    fg, fr, er, ct, rtt = [], [], [], [], []
    for s in range(SEEDS):
        out = simulate(None, s, oracle_knows_m=True)
        fg.append(out["final_gain"]); fr.append(out["final_regret"])
        er.append(out["err_rate"]); ct.append(out["cum_time"]); rtt.append(out["rounds_to_target"])
        collect("oracle", out, s)
    summary["oracle"] = summarize(fg, fr, er, ct, rtt)
    per_seed_gain["oracle"] = np.array(fg)

    # 固定难度扫描
    fixed = {}
    for j in range(D):
        pol = Policy()

        def mkselect(jj):
            return lambda mhat, t: jj
        pol.select = mkselect(j)
        pol.update = lambda mhat, jj, g: None
        fg2, er2, rtt2, ct2 = [], [], [], []
        for s in range(SEEDS):
            out = simulate(pol, s)
            fg2.append(out["final_gain"]); er2.append(out["err_rate"])
            rtt2.append(out["rounds_to_target"]); ct2.append(out["cum_time"])
            collect(f"fixed-d{j}", out, s)
        fixed[f"fixed-d{j}"] = {
            "delta": round(float(DELTA[j]), 4),
            "final_gain_mean": round(float(np.mean(fg2)), 5),
            "err_rate_mean": round(float(np.mean(er2)), 5),
            "rounds_to_target_mean": round(float(np.mean(rtt2)), 3),
            "cum_time_mean": round(float(np.mean(ct2)), 4)}

    # 心流区 ∂Φ+ 非退化
    flow = {}
    for cost_name, idx in (("rounds_to_target", 3), ("cum_time", 4)):
        pts = [(p[idx], p[2]) for p in op_points]
        front = pareto_min(pts)
        entry = {"n_op_points": len(pts), "n_front_points": len(front),
                 "front": [[round(float(a), 5), round(float(b), 5)] for a, b in front]}
        if len(front) >= 2:
            x = np.array([f[0] for f in front], float)
            y = np.array([f[1] for f in front], float)
            ols = float(np.polyfit(x, y, 1)[0])
            ts = (float(stats.theilslopes(y, x)[0]) if len(np.unique(x)) >= 2 else None)
            rng = np.random.default_rng(7)
            bs = []
            for _ in range(2000):
                k = rng.integers(0, len(x), len(x))
                if len(np.unique(x[k])) < 2:
                    continue
                bs.append(np.polyfit(x[k], y[k], 1)[0])
            bs = np.array(bs) if bs else np.array([0.0])
            entry.update({
                "cost_range": [round(float(x.min()), 4), round(float(x.max()), 4)],
                "ols_slope": round(ols, 6), "theilsen_slope": (round(ts, 6) if ts else None),
                "bootstrap_slope_ci95": [round(float(np.percentile(bs, 2.5)), 6),
                                         round(float(np.percentile(bs, 97.5)), 6)],
                "p_slope_ge0": round(float(np.mean(bs >= 0)), 5),
                "nondegenerate": bool(len(front) >= 3 and (x.max() - x.min()) > 1e-9
                                      and np.percentile(bs, 97.5) < 0)})
        else:
            entry.update({"cost_range": None, "ols_slope": None,
                          "nondegenerate": False,
                          "note": "操作点全部共线/退化，无法定义边界斜率"})
        flow[cost_name] = entry

    # ---------- 报告 ----------
    say("=" * 92)
    say(f"M3 自建模拟器：有序动作 bandit + LLM 先验边界   (D={D}, T={T}, SEEDS={SEEDS})")
    say("环境参数: alpha=%.2f p*=%.2f sg=%.2f eta=%.3f lam=%.3f 观测噪声=%.2f"
        % (ALPHA, PSTAR, SG, ETA, LAM, OBS_NOISE))
    say("=" * 92)
    say("")
    say(f"表1  策略表现（{SEEDS} 种子；均值±SD；奖励按 ETA 归一化训练，增益为原始单位）")
    say(f"{'策略':24s} {'期末累积增益':>16s} {'期末伪遗憾':>11s} "
        f"{'平均错误率':>9s} {'达标轮次':>8s} {'达标率':>7s}")
    order = [p[0] for p in policies] + ["oracle"]
    for pn in order:
        s = summary[pn]
        say(f"{pn:24s} {s['final_gain_mean']:.5f}±{s['final_gain_sd']:.4f} "
            f"{s['final_regret_mean']:>11.5f} {s['err_rate_mean']:>9.4f} "
            f"{s['rounds_to_target_mean']:>8.2f} {s['reached_frac']:>7.3f}")
    say("")
    say("表2  学习曲线关键节点 累积增益（均值）")
    cps = [9, 29, 59, 119]
    say(f"{'策略':24s} " + "  ".join(f"t={c+1:<4d}" for c in cps))
    for pn in order:
        if pn in curves:
            say(f"{pn:24s} " + "  ".join(f"{curves[pn]['gain_mean'][c]:.4f}" for c in cps))
    say("")
    say("表3  固定难度扫描（考察「过易无聊/过难挫败」两端）")
    say(f"{'难度档':9s} {'delta':>7s} {'期末增益':>10s} {'错误率':>8s} "
        f"{'达标轮次':>9s} {'累计时间':>9s}")
    for j in range(D):
        f = fixed[f"fixed-d{j}"]
        say(f"{'d'+str(j):9s} {f['delta']:>7.2f} {f['final_gain_mean']:>10.5f} "
            f"{f['err_rate_mean']:>8.4f} {f['rounds_to_target_mean']:>9.2f} "
            f"{f['cum_time_mean']:>9.3f}")
    say("")
    say("表4  心流区 ∂Φ+ 非退化检验（非支配边界：错误率 vs 代价）")
    for cn, fl in flow.items():
        if fl.get("ols_slope") is None:
            say(f"  代价={cn}: 边界点={fl['n_front_points']} -> 退化，无法定义斜率")
            continue
        say(f"  代价={cn}: 操作点={fl['n_op_points']} 边界点={fl['n_front_points']} "
            f"代价范围={fl['cost_range']}")
        say(f"      OLS斜率={fl['ols_slope']:.5f}  Theil-Sen={fl['theilsen_slope']:.5f} "
            f"bootstrap95%CI={fl['bootstrap_slope_ci95']} P(斜率>=0)={fl['p_slope_ge0']:.4f} "
            f"非退化={fl['nondegenerate']}")
        say(f"      边界点(代价,错误率)={fl['front']}")

    say("")
    say("表5  配对比较（同一种子，期末累积增益之差 Δ；配对 t 检验；Cohen dz=均值/SD）")
    pairs = [("ctx+LLM先验(正确)", "contextual-ucb"),
             ("ctx+LLM先验(错误,偏难)", "contextual-ucb"),
             ("contextual-ucb", "thompson"),
             ("lipschitz-ucb", "eps-greedy"),
             ("matched(模型已知,用m̂)", "ctx+LLM先验(正确)")]
    for a, b in pairs:
        d = per_seed_gain[a] - per_seed_gain[b]
        tt = stats.ttest_rel(per_seed_gain[a], per_seed_gain[b])
        try:
            w = stats.wilcoxon(per_seed_gain[a], per_seed_gain[b])
            wp = float(w.pvalue)
        except Exception:
            wp = float("nan")
        dz = float(np.mean(d) / (np.std(d, ddof=1) + 1e-12))
        say(f"   {a} - {b}: Δ={np.mean(d):+.5f} (SD={np.std(d, ddof=1):.5f}) "
            f"dz={dz:+.2f}  t检验 p={tt.pvalue:.3e}  Wilcoxon p={wp:.3e}")
    say("")
    say("=" * 92)

    with open(OUTDIR + r"\code\m3_operating_points.csv", "w", encoding="utf-8") as f:
        f.write("policy,seed,err_rate,rounds_to_target,cum_time,final_gain,final_regret\n")
        for p in op_points:
            f.write(f"{p[0]},{p[1]},{p[2]:.6f},{p[3]},{p[4]:.6f},{p[5]:.6f},{p[6]:.6f}\n")

    with open(OUTDIR + r"\code\m3_results.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "fixed_difficulty": fixed, "flow": flow,
                   "settings": {"D": D, "T": T, "SEEDS": SEEDS, "ALPHA": ALPHA,
                                "PSTAR": PSTAR, "SG": SG, "ETA": ETA, "LAM": LAM,
                                "OBS_NOISE": OBS_NOISE, "LIPSCH": LIPSCH,
                                "PRIOR_LAMBDA": PRIOR_LAMBDA, "N_CTX": N_CTX},
                   "curves": {k: {"gain_mean": v["gain_mean"], "gain_se": v["gain_se"]}
                              for k, v in curves.items()}},
                  f, ensure_ascii=False, indent=2)
    with open(OUTDIR + r"\code\m3_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))
    say("")
    say("[已写出] m3_results.json / m3_output.txt / m3_operating_points.csv")


def summarize(fg, fr, er, ct, rtt):
    return {
        "final_gain_mean": round(float(np.mean(fg)), 5),
        "final_gain_sd": round(float(np.std(fg, ddof=1)), 5),
        "final_gain_ci95": [round(float(np.percentile(fg, 2.5)), 5),
                            round(float(np.percentile(fg, 97.5)), 5)],
        "final_regret_mean": round(float(np.mean(fr)), 5),
        "final_regret_sd": round(float(np.std(fr, ddof=1)), 5),
        "err_rate_mean": round(float(np.mean(er)), 5),
        "cum_time_mean": round(float(np.mean(ct)), 4),
        "rounds_to_target_mean": round(float(np.mean(rtt)), 3),
        "reached_frac": round(float(np.mean(np.array(rtt) <= T)), 4)}


if __name__ == "__main__":
    main()
