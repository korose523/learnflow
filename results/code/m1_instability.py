# -*- coding: utf-8 -*-
"""
M1 命题 C1「度量可公度性的不稳定性」数值实验
------------------------------------------------------------
自包含、可重跑。仅依赖 numpy + scipy（纯计算，无外部数据）。

核心命题
  把多源难度/能力量先各自归一化到 [0,1]、再线性加权融合时，
  「有效权重」会随任一源的单源单调重参数化而漂移；而把各源统一
  到 logit/IRT 公制（按分位/经验 CDF 链接）则不漂移。

有效权重定义（边界贡献法，向量和为 1）
  S = Z w ;  pi_k = w_k * Cov(z_k, S) / Var(S)
  由 Cov(Zw,S)=Var(S) 得 sum_k pi_k = 1。当各源正交且离散度相等时 pi=w，
  否则 pi 依赖各源的离散度与相关结构 —— 这正是漂移的来源。

两种公制
  A. 线性 [0,1] 公制：逐列 min-max 后线性加权。
     - 对仿射重参数化 y'=a y+b 严格不变（min-max 吸收，解析恒等）；
     - 对非线性单调重参数化会漂移（分布形状改变 -> 离散度/相关结构变）。
  B. logit/IRT 公制：逐列用经验 CDF（阶跃）链接到 logit 潜尺度。
     - 对 *任意* 严格单调重参数化严格不变（阶跃 CDF 的秩不变性，解析恒等）。

运行:  python m1_instability.py
输出:  控制台 + m1_output.txt + m1_results.json
"""
import json
import numpy as np
from scipy import stats

OUTDIR = r"E:/learnflow\results"
LOG = []
SRC_NAMES = ["BKT掌握度", "间隔重复记忆难度", "Elo能力", "窗口成功率"]


def say(s=""):
    print(s)
    LOG.append(str(s))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def logit(p):
    return np.log(p / (1.0 - p))


def minmax(x):
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi <= lo:
        return np.zeros_like(x, dtype=float)
    return (x - lo) / (hi - lo)


# ----------------------------------------------------------------------
# 1. 数据生成：共同潜变量 theta + 源特异噪声（真实的相关单调关系）
# ----------------------------------------------------------------------
def gen_sources(n, rng):
    """生成四源（均为同一潜能力 theta 的单调函数 + 独立噪声）：
       0 BKT 掌握度        (概率尺度 [0,1])
       1 间隔重复记忆难度   (正尺度, 指数型)
       2 Elo 能力          (宽线性尺度)
       3 窗口成功率        (概率尺度 [0,1])
    """
    th = rng.normal(0.0, 1.0, n)
    e = rng.normal(0.0, 1.0, (n, 4))
    x0 = sigmoid(1.1 * th + 0.2 + 0.30 * e[:, 0])
    x1 = np.exp(0.7 * th + 0.3 + 0.25 * e[:, 1])
    x2 = 1200.0 + 250.0 * th + 40.0 * e[:, 2]
    x3 = sigmoid(0.9 * th - 0.1 + 0.30 * e[:, 3])
    return np.column_stack([x0, x1, x2, x3]), th


# ----------------------------------------------------------------------
# 2. 两种融合公制
# ----------------------------------------------------------------------
def eff_weights(Z, w):
    """pi_k = w_k * Cov(z_k,S)/Var(S),  sum pi = 1"""
    S = Z @ w
    n = len(S)
    csz = Z.T @ (S - S.mean()) / (n - 1)     # Cov(z_k, S)
    vS = np.var(S, ddof=1)
    return w * csz / vS


def lin_metric_pi(X, w):
    """线性 [0,1] 公制：逐列 min-max 后线性加权"""
    Z = np.column_stack([minmax(X[:, k]) for k in range(X.shape[1])])
    return eff_weights(Z, w)


def ecdf_logit(x, cal, eps=1e-6):
    """阶跃经验 CDF 链接到 logit 公制（对任意严格单调变换严格不变）"""
    s = np.sort(cal)
    n = len(s)
    r = np.searchsorted(s, x, side="right")          # = #{cal <= x}
    p = (r + 0.5) / (n + 1.0)
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def logit_metric_pi(X, cal, w):
    P = np.column_stack([ecdf_logit(X[:, k], cal[:, k]) for k in range(X.shape[1])])
    return eff_weights(P, w)


# ----------------------------------------------------------------------
# 3. 单调变换库（函数签名 func(y, ref)：参数全部取自固定参考 ref=X 列，
#    以保证对测试样本与校准样本施加的是 *同一个* 重参数化）
# ----------------------------------------------------------------------
def affine(a, b):
    return lambda y, ref: a * y + b


def exp_med(y, ref):
    return np.exp(y / float(np.median(ref)))


def probit_std(y, ref):
    mu, sd = float(np.mean(ref)), float(np.std(ref, ddof=0)) + 1e-12
    return stats.norm.cdf((y - mu) / sd)


def logit_minmax(y, ref):
    lo, hi = float(np.min(ref)), float(np.max(ref))
    z = (y - lo) / (hi - lo)
    return logit(np.clip(z, 1e-6, 1.0 - 1e-6))


def build_transforms():
    T = {}
    for a in (0.5, 1.0, 2.0):
        for b in (-0.5, 0.0, 0.5):
            T[f"affine(a={a},b={b})"] = ("affine", affine(a, b))
    T["power2"] = ("nonlinear", lambda y, ref: y ** 2)
    T["power3"] = ("nonlinear", lambda y, ref: y ** 3)
    T["sqrt"] = ("nonlinear", lambda y, ref: np.sqrt(y))
    T["log"] = ("nonlinear", lambda y, ref: np.log(y))
    T["exp_scaled"] = ("nonlinear", exp_med)
    T["probit_std"] = ("nonlinear", probit_std)
    T["logit_minmax"] = ("nonlinear", logit_minmax)
    return T


# ----------------------------------------------------------------------
# 4. 漂移度量
# ----------------------------------------------------------------------
def n_reversals(a, b):
    K = len(a)
    c = 0
    for i in range(K):
        for j in range(i + 1, K):
            if (a[i] - a[j]) * (b[i] - b[j]) < 0:
                c += 1
    return c


def rank_order(v):
    r = np.argsort(np.argsort(-np.asarray(v)))       # 0 = 权重最大
    return [int(x) for x in r]


def spearman(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return 1.0
    return float(stats.spearmanr(a, b).statistic)


# ----------------------------------------------------------------------
# 5. 主实验
# ----------------------------------------------------------------------
def main():
    R = 200          # 重复次数
    N = 500          # 每个重复的样本量
    NCAL = 500       # 校准样本量

    configs = {
        "4源(0.40/0.30/0.20/0.10)": (np.array([0.40, 0.30, 0.20, 0.10]), [0, 1, 2, 3]),
        "3源(0.45/0.35/0.20)": (np.array([0.45, 0.35, 0.20]), [0, 1, 2]),
    }
    T = build_transforms()

    results = {}
    counterexamples = {}

    for cname, (w, cols) in configs.items():
        K = len(cols)
        rec = {}
        lin_ind = {}
        commondev = {}
        base_pi_lin, base_pi_log = [], []
        logit_common_maxdev = 0.0

        for r in range(R):
            rng = np.random.default_rng(902000 + r)
            Xfull, _ = gen_sources(N, rng)
            Calfull, _ = gen_sources(NCAL, rng)
            X = Xfull[:, cols]
            Cal = Calfull[:, cols]

            pi0_lin = lin_metric_pi(X, w)
            pi0_log = logit_metric_pi(X, Cal, w)
            base_pi_lin.append(pi0_lin)
            base_pi_log.append(pi0_log)

            for k in range(K):
                for tname, (fam, tf) in T.items():
                    # ---- (A) 线性 [0,1] 公制 ----
                    Xp = X.copy()
                    Xp[:, k] = tf(X[:, k], X[:, k])
                    pip_lin = lin_metric_pi(Xp, w)
                    L1 = float(np.sum(np.abs(pip_lin - pi0_lin)))
                    rev = int(n_reversals(pi0_lin, pip_lin))
                    sp = spearman(pi0_lin, pip_lin)
                    key = (cols[k], tname)
                    rec.setdefault(key, {"fam": fam, "L1": [], "rev": [], "sp": []})
                    rec[key]["L1"].append(L1)
                    rec[key]["rev"].append(rev)
                    rec[key]["sp"].append(sp)

                    # ---- (B1) logit 公制，同校准、同一变换同步作用于 cal（应严格=0）----
                    Pc = np.column_stack([
                        ecdf_logit((tf(X[:, j], X[:, j]) if j == k else X[:, j]),
                                   (tf(Cal[:, j], X[:, k]) if j == k else Cal[:, j]))
                        for j in range(K)])
                    pi_c = eff_weights(Pc, w)
                    dcommon = float(np.max(np.abs(pi_c - pi0_log)))
                    logit_common_maxdev = max(logit_common_maxdev, dcommon)
                    ckey = (cols[k], tname)
                    commondev[ckey] = max(commondev.get(ckey, 0.0), dcommon)

                    # ---- (B2) logit 公制，独立校准样本（仅链接抽样误差）----
                    Cal2full, _ = gen_sources(NCAL, rng)
                    Cal2 = Cal2full[:, cols]
                    Pind = np.column_stack([
                        ecdf_logit((tf(X[:, j], X[:, j]) if j == k else X[:, j]),
                                   (tf(Cal2[:, j], X[:, k]) if j == k else Cal2[:, j]))
                        for j in range(K)])
                    pi_ind = eff_weights(Pind, w)
                    L1g = float(np.sum(np.abs(pi_ind - pi0_log)))
                    revg = int(n_reversals(pi0_log, pi_ind))
                    lin_ind.setdefault(key, {"fam": fam, "L1": [], "rev": []})
                    lin_ind[key]["L1"].append(L1g)
                    lin_ind[key]["rev"].append(revg)

                    # ---- 反例记录：线性发生排序反转 ----
                    if rev >= 1:
                        if tname not in counterexamples:
                            counterexamples[tname] = {
                                "config": cname,
                                "rep": int(r),
                                "source_index": int(cols[k]),
                                "source_name": SRC_NAMES[cols[k]],
                                "transform": tname, "family": fam,
                                "pi_baseline": [round(float(v), 6) for v in pi0_lin],
                                "pi_transformed": [round(float(v), 6) for v in pip_lin],
                                "rank_baseline": rank_order(pi0_lin),
                                "rank_transformed": rank_order(pip_lin),
                                "L1": round(L1, 6),
                                "n_reversals": rev,
                                "spearman": round(sp, 6),
                                "logit_same_transform_max_abs_dev": round(
                                    float(np.max(np.abs(pi_c - pi0_log))), 15),
                            }

        base_pi_lin = np.array(base_pi_lin)
        base_pi_log = np.array(base_pi_log)

        def agg_sub(d):
            return {
                "family": d["fam"],
                "L1_mean": round(float(np.mean(d["L1"])), 6),
                "L1_sd": round(float(np.std(d["L1"], ddof=1)), 6),
                "L1_ci95": [round(float(np.percentile(d["L1"], 2.5)), 6),
                            round(float(np.percentile(d["L1"], 97.5)), 6)],
                "rev_mean": round(float(np.mean(d["rev"])), 4),
                "rev_any_frac": round(float(np.mean(np.array(d["rev"]) > 0)), 4),
                "spearman_mean": round(float(np.mean(d["sp"])), 6) if "sp" in d else None,
            }

        per_t = {f"src{key[0]}|{key[1]}": agg_sub(d) for key, d in rec.items()}
        per_t_logit = {f"src{key[0]}|{key[1]}": agg_sub(d) for key, d in lin_ind.items()}

        results[cname] = {
            "nominal_w": w.tolist(),
            "baseline_pi_linear_mean": [round(float(v), 6) for v in base_pi_lin.mean(0)],
            "baseline_pi_linear_sd": [round(float(v), 6) for v in base_pi_lin.std(0, ddof=1)],
            "baseline_pi_logit_mean": [round(float(v), 6) for v in base_pi_log.mean(0)],
            "baseline_pi_logit_sd": [round(float(v), 6) for v in base_pi_log.std(0, ddof=1)],
            "logit_common_cal_maxdev_overall": logit_common_maxdev,
            "logit_common_cal_maxdev_worstkey": (
                f"src{max(commondev, key=commondev.get)[0]}|"
                f"{max(commondev, key=commondev.get)[1]}" if commondev else None),
            "per_transform_linear": per_t,
            "per_transform_logit_indepcal": per_t_logit,
        }

    # ---------- 控制台报告 ----------
    say("=" * 84)
    say("M1 命题 C1 不稳定性数值实验   重复 R=200, N=500, 校准 NCAL=500")
    say("=" * 84)

    def fam_agg(rows, family):
        sub = [v for v in rows.values() if v["family"] == family]
        sps = [v["spearman_mean"] for v in sub if v.get("spearman_mean") is not None]
        spm = float(np.mean(sps)) if sps else float("nan")
        return (np.mean([v["L1_mean"] for v in sub]),
                np.mean([v["L1_sd"] for v in sub]),
                np.mean([v["rev_mean"] for v in sub]),
                np.mean([v["rev_any_frac"] for v in sub]),
                spm)

    for cname, agg in results.items():
        say("")
        say(f"[配置 {cname}]  名义权重 w = {agg['nominal_w']}")
        say(f"  线性[0,1]融合 基准有效权重 均值 = {agg['baseline_pi_linear_mean']}  "
            f"(SD={agg['baseline_pi_linear_sd']})")
        say(f"    -> 基准有效权重已 != 名义权重（相关结构+异方差）")
        say(f"  logit 公制    基准有效权重 均值 = {agg['baseline_pi_logit_mean']}  "
            f"(SD={agg['baseline_pi_logit_sd']})")
        say(f"  logit 公制 同校准同步变换 最大|Δpi| = "
            f"{agg['logit_common_cal_maxdev_overall']:.3e}  "
            f"(最差组合={agg['logit_common_cal_maxdev_worstkey']}; 严格单调变换下应为0)")
        say("")
        say("  --- (A) 线性[0,1]公制：有效权重漂移（对全部 源×变换 平均）---")
        for fam, lab in (("affine", "仿射 affine (9种)"), ("nonlinear", "非线性单调 (7种)")):
            L1, sd, rev, anyf, sp = fam_agg(agg["per_transform_linear"], fam)
            say(f"   {lab:20s} L1均={L1:.6f} (SD≈{sd:.6f}) | 平均反转={rev:.3f} | "
                f"出现反转比例={anyf:.3f} | Spearman={sp:.4f}")
        non = [v for v in agg["per_transform_linear"].values() if v["family"] == "nonlinear"]
        worstL1 = max(non, key=lambda v: v["L1_mean"])
        say(f"   非线性最严重: L1={worstL1['L1_mean']:.5f} 95%CI={worstL1['L1_ci95']} "
            f"反转={worstL1['rev_mean']:.3f} Spearman={worstL1['spearman_mean']:.4f}")
        say("")
        say("  --- (B) logit 公制（独立校准，仅链接抽样误差）：同样的漂移度量 ---")
        for fam, lab in (("affine", "仿射 affine (9种)"), ("nonlinear", "非线性单调 (7种)")):
            L1, sd, rev, anyf, sp = fam_agg(agg["per_transform_logit_indepcal"], fam)
            say(f"   {lab:20s} L1均={L1:.6f} (SD≈{sd:.6f}) | 平均反转={rev:.3f} | "
                f"出现反转比例={anyf:.3f} | Spearman={sp:.4f}")

    say("")
    say("=" * 84)
    say("反例（线性融合排序反转；同一变换下统一 logit 公制 |Δpi|=0，无反转）")
    say("=" * 84)
    show = [k for k in ("logit_minmax", "probit_std", "power3", "power2", "sqrt")
            if k in counterexamples]
    for k in show[:3]:
        say(json.dumps(counterexamples[k], ensure_ascii=False, indent=2))
    if not counterexamples:
        say("未找到反转（如实报告）")

    with open(OUTDIR + r"\code\m1_results.json", "w", encoding="utf-8") as f:
        json.dump({"config": results, "counterexamples": counterexamples,
                   "settings": {"R": R, "N": N, "NCAL": NCAL}},
                  f, ensure_ascii=False, indent=2)
    with open(OUTDIR + r"\code\m1_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))
    say("")
    say("[已写出] m1_results.json / m1_output.txt")


if __name__ == "__main__":
    main()
