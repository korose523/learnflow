# -*- coding: utf-8 -*-
"""命题 P1 的数值旁证：**可加分离证据**下，成对 BT 聚合退化为线性组合。

命题（M4 完整稿第 3.1 节，解析证明在正文）
------------------------------------------
设每个信号 k 对题目 i 的（标准化）取值为 z_ki，令 u_i = Σ_k α_k z_ki。若把第 k 个
信号给出的成对证据写成 p_ijk = σ(α_k(z_ki − z_kj))，并按 **对数几率相加** 合成

    y_ij = Σ_k logit(p_ijk) = Σ_k α_k (z_ki − z_kj) = u_i − u_j            (可加分离)

则 Bradley–Terry 模型 P(i≻j)=σ(y_ij) 的极大似然满足 d = u（正规方程残差恒为 0）。
也就是说：**"先做成对比较、再用 BT 聚合"与"直接做加权线性组合"给出同一个排序**，
成对化这个环节本身不产生任何信息增益。

推论：实践中观察到的 pairwise > absolute（Kolesnikova 等，2026）不可能来自"成对"
这一形式，只能来自**违反可加分离性**的两个来源：
    (a) 证据饱和 —— 按**概率域**平均而非 logit 域相加（这是 LLM 评判者实际做的）；
    (b) 逐对可用性不均 —— 不同题对由不同信号子集判定（缺失 / 部分观测）。
本脚本在同一个合成问题上做四路对照（W_ij = σ(Y_ij)，Y_ji = −Y_ij，N_ij ≡ 1）：

    R1 logit-sum   ：Y_ij = Σ_k α_k(z_ki − z_kj)              → 期望 ρ(d, u) = 1
    R2 logit-mean  ：Y_ij = (1/m)Σ_k α_k(z_ki − z_kj)         → 期望 ρ(d, u) = 1（尺度无关）
    R3 prob-mean   ：W_ij = (1/m)Σ_k σ(α_k(z_ki − z_kj))      → 破坏可加分离（LLM 口径）
    R4 partial-obs ：Y_ij = Σ_{k∈S_ij} α_k(z_ki − z_kj)       → 破坏可加分离（缺失口径）

R2/R1 的对照把"平均 vs 求和"这个无关因素剥离掉，证明**起作用的是合成所在的域，
不是聚合算子**；R3/R4 则给出两种真实世界违反源的量化幅度。

同时报告 ρ(d, 真潜变量)：在"所有信号都是同一个潜变量的有噪观测"这一数据生成过程
下，线性恢复本身是充分的，因此该列回答了一个更重要的问题——**违反可加分离性并不
自动带来增益，它带来的是"差异"，收益必须拿外生判据去验**（见 M4 完整稿第 5 节：
DBE 教师标签上 M4 反而下降）。

求解器：Bradley–Terry 对数似然的同伦延拓（homotopy continuation）+ Newton +
Armijo 回溯，并以对数域 Zermelo/MM 定点步作病态兜底；返回 ‖∇ℓ‖_∞ 作为"确实找到
驻点"的收敛凭证。证据饱和时 Newton Hessian 的 σ(1−σ) 大量下溢 ⟹ 数值奇异，而 MM
的线性收敛率在此趋近 1（实测 6 万步仍只有 ‖∇ℓ‖≈5e-5），故必须延拓，否则会把
"没跑到最优点"误读成"命题不成立"。

运行：python results/code/m4_proposition_p1.py
"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_lib import spearman

OUT = Path(__file__).resolve().parent / "m4_proposition_p1.json"

SEED = 20260927
N_TRIALS = 24
SCALES = [0.5, 1.0, 2.0, 4.0]        # α 的强度刻度 c：控制证据饱和程度
RULES = ["logit_sum", "logit_mean", "prob_mean", "partial_obs"]
MISS_PROB = 0.6                       # 每个信号对某题对可用的概率
MAX_ITER = 60
GRAD_TOL = 1e-11
# 同伦调度：s 由小到大，最后一级 s=1 即原问题
HOMOTOPY = [0.02, 0.05, 0.1, 0.2, 0.35, 0.55, 0.75, 0.9, 1.0]


# ---------------------------------------------------------------- 数值基元
def logistic(x):
    if x >= 0.0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def logit_clip(p):
    return math.log(p / (1.0 - p)) if 0.0 < p < 1.0 else (-40.0 if p <= 0.0 else 40.0)


def softplus(t):
    """log(1+exp(t))，稳定版。"""
    if t > 30.0:
        return t
    return math.log1p(math.exp(t))


def log_sigma(x):
    """log σ(x) = −softplus(−x)，稳定版。"""
    return -softplus(-x)


def logsumexp(vals):
    m = max(vals)
    if m in (float("inf"), float("-inf")):
        return m
    return m + math.log(sum(math.exp(v - m) for v in vals))


def logliketah(d, W, n):
    """ℓ(d) = Σ_{i<j} [W_ij log σ(d_i−d_j) + (1−W_ij) log σ(d_j−d_i)]。"""
    tot = 0.0
    for i in range(n):
        di = d[i]
        Wi = W[i]
        for j in range(i + 1, n):
            x = di - d[j]
            wij = Wi[j]
            tot += wij * log_sigma(x) + (1.0 - wij) * log_sigma(-x)
    return tot


def _solve_dense(A, b):
    """解 A δ = −b（Newton 步），部分选主元。奇异返回 None。"""
    m = len(A)
    M = [list(A[r]) + [-b[r]] for r in range(m)]
    for c in range(m):
        piv = max(range(c, m), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-14:
            return None
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(c + 1, m):
            f = M[r][c] / pv
            if f:
                for k in range(c, m + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * m
    for r in range(m - 1, -1, -1):
        acc = M[r][m]
        for k in range(r + 1, m):
            acc -= M[r][k] * x[k]
        x[r] = acc / M[r][r]
    return x


def _mm_step(d, Wsum, n):
    """对数域 Zermelo/MM 定点步（全局收敛，Newton 病态时的兜底）。

    γ_i ← W_i / Σ_{j≠i} (γ_i+γ_j)^{-1}，其中 log(γ_i+γ_j) = d_i + softplus(d_j−d_i)。
    全程在 log 域做 logsumexp，故 |d| 很大时也不会溢出。返回时归一化使 d_0 = 0。
    """
    new = [0.0] * n
    for i in range(n):
        di = d[i]
        terms = []
        for j in range(n):
            if j == i:
                continue
            terms.append(-di - softplus(d[j] - di))
        new[i] = math.log(Wsum[i]) - logsumexp(terms)
    sh = new[0]
    return [new[i] - sh for i in range(n)]


def _grad_hess(cur, W, n):
    g = [0.0] * n
    H = [[0.0] * n for _ in range(n)]
    for i in range(n):
        gi = 0.0
        hii = 0.0
        Hi = H[i]
        Wi = W[i]
        ci = cur[i]
        for j in range(n):
            if j == i:
                continue
            sij = logistic(ci - cur[j])
            wgt = sij * (1.0 - sij)             # N_ij ≡ 1
            gi += Wi[j] - sij
            hii -= wgt
            Hi[j] += wgt
        Hi[i] += hii
        g[i] = gi
    return g, H


def bt_mle(Y, n, step_cap=4.0):
    """Bradley–Terry 极大似然（同伦延拓 + Newton + MM 兜底）。

    Args:
        Y: 反对称的对数几率证据矩阵，W_ij = σ(Y_ij)，Y_ji = −Y_ij ⟹ N_ij ≡ 1。
        n: 题数。

    初值统一为 d ≡ 0，即**不使用任何"已知答案"作起点**——否则"d = u"这条恒等式
    会被起点本身悄悄植入，验证就失去意义。

    Returns: (d, iters, ‖∇ℓ‖_∞)。‖∇ℓ‖_∞ 是"确实找到了驻点"的收敛凭证。
    """
    idx = list(range(1, n))                     # d_0 ≡ 0，消去平移零空间
    if not idx:
        return [0.0] * n, 0, 0.0
    d = [0.0] * n
    state = {"iters": 0}

    def stage(s, budget, tol):
        W = [[0.0] * n for _ in range(n)]
        for i in range(n):
            Wi, Yi = W[i], Y[i]
            for j in range(n):
                if j != i:
                    Wi[j] = logistic(s * Yi[j])
        Wsum = [sum([W[i][j] for j in range(n) if j != i]) for i in range(n)]
        for _ in range(budget):
            state["iters"] += 1
            grad, hess = _grad_hess(d, W, n)
            gnorm = max(abs(grad[p]) for p in idx)
            if gnorm < tol:
                break
            step = _solve_dense([[hess[p][q] for q in idx] for p in idx],
                                [grad[p] for p in idx])
            if step is None:                    # Hessian 病态 → MM 兜底
                d[:] = _mm_step(d, Wsum, n)
                continue
            mx = max(abs(x) for x in step)
            if mx > step_cap:                   # 步长截断，避免跳进饱和区
                step = [x * step_cap / mx for x in step]
            cur_val = logliketah(d, W, n)
            t = 1.0
            accepted = False
            for _ in range(40):
                cand = list(d)
                for p, pp in enumerate(idx):
                    cand[pp] = d[pp] + t * step[p]
                if logliketah(cand, W, n) >= cur_val - 1e-12 * max(1.0, abs(cur_val)):
                    d[:] = cand
                    accepted = True
                    break
                t *= 0.5
            if not accepted:
                d[:] = _mm_step(d, Wsum, n)
        return W

    Wlast = None
    for i, s in enumerate(HOMOTOPY):
        last = (i == len(HOMOTOPY) - 1)
        Wlast = stage(s, MAX_ITER if last else 12, GRAD_TOL if last else 1e-6)
    grad, _ = _grad_hess(d, Wlast, n)
    gnorm = max(abs(grad[p]) for p in idx)
    return d, state["iters"], gnorm


# ---------------------------------------------------------------- 合成问题
def make_instance(n, m, rng):
    """m 个信号是同一潜变量的有噪观测（这是唯一让线性恢复充分的数据生成过程）。

    刻意让各信号的噪声标准差 σ_k 在 0.4–1.6 之间**不等**：这是现实里"不同完善度
    的信号不该等权"的来源，也是后面"精度加权 "诊断得以有分辨率的前提（等方差时
    任何加权都退化为等价）。
    """
    alpha = [rng.uniform(0.3, 1.6) for _ in range(m)]
    latent = [rng.gauss(0.0, 1.0) for _ in range(n)]
    sds = [rng.uniform(0.4, 1.6) for _ in range(m)]
    Z = []
    for k in range(m):
        Z.append([latent[i] + rng.gauss(0.0, sds[k]) for i in range(n)])
    return alpha, Z, latent, sds


def build_evidence(alpha, Z, n, m, rule, avail):
    """按四种规则构造**反对称**的对数几率证据矩阵 Y（W_ij = σ(Y_ij)）。"""
    Y = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if rule == "logit_sum":
                lo = sum(alpha[k] * (Z[k][i] - Z[k][j]) for k in range(m))
            elif rule == "logit_mean":
                lo = sum(alpha[k] * (Z[k][i] - Z[k][j]) for k in range(m)) / m
            elif rule == "prob_mean":
                acc = 0.0
                for k in range(m):
                    acc += logistic(alpha[k] * (Z[k][i] - Z[k][j]))
                lo = 0.0 if abs(acc / m - 0.5) < 1e-15 else logit_clip(acc / m)
            elif rule == "partial_obs":
                S = avail[(i, j)]
                lo = 0.0 if not S else sum(alpha[k] * (Z[k][i] - Z[k][j]) for k in S)
            else:
                raise ValueError(rule)
            Y[i][j] = lo
            Y[j][i] = -lo
    return Y


def main():
    rng = random.Random(SEED)
    rows = []
    for trial in range(N_TRIALS):
        n = rng.choice([20, 24])
        m = rng.choice([3, 4, 5])
        alpha0, Z0, latent, sds = make_instance(n, m, rng)
        prec = [1.0 / (sds[k] * sds[k]) for k in range(m)]   # 精度加权（最优线性恢复）
        # 同一题对**只判一次**，正反两个方向共用同一个可用信号子集，从而保证
        # Y_ij + Y_ji = 0（⟹ N_ij = 1）。若给 (i,j) 与 (j,i) 各自独立抽子集，
        # 一次判定就被拆成了两次互相矛盾的回答，反对称约束失效，Newton 与 MM
        # 的一致性保修随之失效（曾因此出现 ‖∇ℓ‖ 无法归零的伪病态）。
        avail = {}
        for i in range(n):
            for j in range(i + 1, n):
                S = [k for k in range(m) if rng.random() < MISS_PROB]
                avail[(i, j)] = S
                avail[(j, i)] = S
        for c in SCALES:
            alpha = [c * a for a in alpha0]
            u = [sum(alpha[k] * Z0[k][i] for k in range(m)) for i in range(n)]
            row = {"trial": trial, "n_items": n, "n_signals": m, "alpha_scale": c}
            _last_d = {}
            for rule in RULES:
                Y = build_evidence(alpha, Z0, n, m, rule, avail)
                # 反对称自检（O(n²)，成本可忽略，守住上一段那个坑）
                if max(abs(Y[i][j] + Y[j][i]) for i in range(n) for j in range(n)) > 1e-9:
                    raise AssertionError("evidence matrix is not antisymmetric")
                d, its, gnorm = bt_mle(Y, n)
                _last_d[rule] = d
                row["rho_%s_vs_u" % rule] = round(spearman(d, u), 6)
                row["rho_%s_vs_latent" % rule] = round(spearman(d, latent), 6)
                row["iters_%s" % rule] = its
                row["grad_%s" % rule] = round(gnorm, 12)
            row["rho_u_vs_latent"] = round(spearman(u, latent), 6)
            # ---------- 机制诊断：概率平均是不是在偷偷做"精度加权"？ ----------
            u_prec = [sum(prec[k] * Z0[k][i] for k in range(m)) for i in range(n)]
            row["rho_prec_vs_latent"] = round(spearman(u_prec, latent), 6)
            row["rho_u_vs_prec"] = round(spearman(u, u_prec), 6)
            row["rho_prob_mean_vs_prec"] = round(
                spearman(_last_d["prob_mean"], u_prec), 6)
            row["rho_prob_mean_vs_latent"] = row["rho_prob_mean_vs_latent"]  # 已记录
            rows.append(row)
            print("  trial %2d/%d  c=%s  done" % (trial + 1, N_TRIALS, c), flush=True)

    def mean_of(c, key):
        sel = [r[key] for r in rows if r["alpha_scale"] == c]
        return round(sum(sel) / len(sel), 6)

    summary = {
        "note": ("P1 numerical companion. Under additively separable pairwise evidence "
                 "(log-odds combination) the BT aggregate recovers the linear composite "
                 "exactly; violating separability in either of the two ways that occur in "
                 "practice (probability-domain averaging = what LLM judges do; per-pair "
                 "missing signals) breaks the identity. The magnitude of the deviation "
                 "grows monotonically with evidence saturation."),
        "solver": ("homotopy continuation on the evidence logits (s grid) + Newton with "
                   "Armijo backtracking, d_0 fixed at 0, log-domain Zermelo/MM fallback; "
                   "certificate = ||grad l||_inf"),
        "seed": SEED, "trials": N_TRIALS, "alpha_scales": SCALES,
        "miss_prob": MISS_PROB,
        "rho_logit_sum_vs_u_min": round(min(r["rho_logit_sum_vs_u"] for r in rows), 6),
        "rho_logit_mean_vs_u_min": round(min(r["rho_logit_mean_vs_u"] for r in rows), 6),
        "rho_prob_mean_vs_u_max": round(max(r["rho_prob_mean_vs_u"] for r in rows), 6),
        "rho_partial_obs_vs_u_max": round(max(r["rho_partial_obs_vs_u"] for r in rows), 6),
        "grad_inf_max": max(max(r["grad_%s" % rl] for rl in RULES) for r in rows),
        "detail": rows,
    }
    by_scale = {}
    for c in SCALES:
        by_scale[str(c)] = {
            "n": sum(1 for r in rows if r["alpha_scale"] == c),
            "rho_logit_sum_vs_u_min": round(
                min(r["rho_logit_sum_vs_u"] for r in rows if r["alpha_scale"] == c), 6),
            "rho_prob_mean_vs_u_mean": mean_of(c, "rho_prob_mean_vs_u"),
            "rho_prob_mean_vs_u_min": round(
                min(r["rho_prob_mean_vs_u"] for r in rows if r["alpha_scale"] == c), 6),
            "rho_partial_obs_vs_u_mean": mean_of(c, "rho_partial_obs_vs_u"),
            "rho_partial_obs_vs_u_min": round(
                min(r["rho_partial_obs_vs_u"] for r in rows if r["alpha_scale"] == c), 6),
            "rho_prob_mean_vs_latent_mean": mean_of(c, "rho_prob_mean_vs_latent"),
            "rho_partial_obs_vs_latent_mean": mean_of(c, "rho_partial_obs_vs_latent"),
            "rho_u_vs_latent_mean": mean_of(c, "rho_u_vs_latent"),
        }
    summary["rho_prec_vs_latent_mean"] = round(
        sum(r["rho_prec_vs_latent"] for r in rows) / len(rows), 6)
    summary["rho_prob_mean_vs_prec_mean"] = round(
        sum(r["rho_prob_mean_vs_prec"] for r in rows) / len(rows), 6)
    summary["rho_u_vs_prec_mean"] = round(
        sum(r["rho_u_vs_prec"] for r in rows) / len(rows), 6)
    summary["by_alpha_scale"] = by_scale
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nP1 数值旁证（%d 次随机构造 × %d 个强度刻度 = %d 组）"
          % (N_TRIALS, len(SCALES), len(rows)))
    print("  收敛凭证 ‖∇ℓ‖_∞ 最大值        = %.2e" % summary["grad_inf_max"])
    print("  BT(logit-相加) vs u      Spearman 最小 = %s   （期望 1.0）"
          % summary["rho_logit_sum_vs_u_min"])
    print("  BT(logit-平均) vs u      Spearman 最小 = %s   （期望 1.0）"
          % summary["rho_logit_mean_vs_u_min"])
    print("  BT(概率平均)   vs u      Spearman 最大 = %s   （期望 < 1）"
          % summary["rho_prob_mean_vs_u_max"])
    print("  BT(逐对缺失)   vs u      Spearman 最大 = %s   （期望 < 1）"
          % summary["rho_partial_obs_vs_u_max"])
    print("\n  按证据强度分层（c 越大 ⟹ 证据越饱和 ⟹ 越违反可加分离）：")
    print("   %-5s %-9s %-9s %-9s %-9s %-9s %-9s"
          % ("c", "probMean", "(min)", "partObs", "(min)", "vs潜:pm", "vs潜:u"))
    for c in SCALES:
        b = by_scale[str(c)]
        print("   %-5s %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f"
              % (c, b["rho_prob_mean_vs_u_mean"], b["rho_prob_mean_vs_u_min"],
                 b["rho_partial_obs_vs_u_mean"], b["rho_partial_obs_vs_u_min"],
                 b["rho_prob_mean_vs_latent_mean"], b["rho_u_vs_latent_mean"]))
    print("\n  机制诊断：概率平均是否在偷偷做精度加权？")
    print("   ρ(u_α,     精度加权) = %s" % summary["rho_u_vs_prec_mean"])
    print("   ρ(BT概率平均, 精度加权) = %s" % summary["rho_prob_mean_vs_prec_mean"])
    print("   ρ(精度加权,   真潜变量) = %s   ← 三种线性/准线性恢复的上界参考"
          % summary["rho_prec_vs_latent_mean"])
    print("\nsaved -> %s" % OUT)


if __name__ == "__main__":
    main()
