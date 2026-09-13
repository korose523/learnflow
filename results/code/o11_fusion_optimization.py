# -*- coding: utf-8 -*-
"""O11：难度融合算法的再优化 —— 符号校正 + 可靠性加权 + 可靠性驱动的 λ。

背景（O7/O8/O9 已确立，均在 results/code/）：
  * O7 留出验证：等权 7 信号融合在留出判据下全面劣于仅成功率（A/B 蓄水池槽位互斥，无泄漏）。
  * O8：剔除 upgrade_rate 得 fused6，配 λ(k) 收缩后 k=10 领先成功率 +3.43pp；
    经验 λ*(k)=[0.701,0.524,0.387,0.234,0.125]；闭式 λ_cf(k)=1/(1+(k/27.3)^0.895)。
  * O9：λ_cf 区间内插泛化良好，但**只由 k 驱动**，DBE 上无收益
    → 收缩强度应随"成功率估计自身的可靠性"而变，而非只随样本量。

本脚本（O11）在被 O7/O8 验证过的**同一留出协议**下比较两类优化：

  (A) 融合端（把"等权 6 信号"换掉）
      * sign-corrected：每个信号用**拟合块 A 内**与"成功率难度方向"的秩相关定符号，
        负相关则取负 —— 于是 upgrade_rate 的**信息被保留**，而不是像 O8 那样丢弃。
      * reliability-weighted：权重 = 该信号在 A 内的**折半信度**（取正后归一），
        低信度信号自动降权，直接压低小样本下的融合方差。

  (B) 收缩端（把"只由 k 驱动"的 λ_cf 换掉）
      λ_rel = 1 − ρ_success(A)，ρ_success 为成功率估计在 A 内的折半信度。
      ρ 随 k 上升 → λ 随 k 下降，形状与经验 λ*(k) 一致，且**跨系统自适应**。

严格复用 O8 协议：seed=20260913、REP=25、SPLITS=20、B_SIZE=250、k∈{10,25,50,100,200}；
A/B 为互斥的蓄水池槽位块。所有符号 / 权重 / λ 仅在 A 内估计，判据只取自 B，杜绝泄漏。
输出 results/code/o11_fusion_optimization.json
"""
import json
import numpy as np
from scipy import stats as st

BASE = r"E:\learnflow"
NPZ = BASE + r"\results\code\difficulty_cache.npz"
OUT = BASE + r"\results\code\o11_fusion_optimization.json"

KS = [10, 25, 50, 100, 200]
B_SIZE, REP, SPLITS = 250, 25, 20
COLS6 = [0, 1, 2, 3, 5, 6]          # O8 fused6：剔除 upgrade_rate(index 4)
VARIANTS = ["fused6", "fused7", "signed7", "rw6", "srw7"]
LAM_STRATS = ["cf", "rel", "emp"]

Z = np.load(NPZ, allow_pickle=True)
J_res = Z["J_res"]
M = J_res.shape[0]
K = J_res.shape[2]

Jf = J_res.astype(np.float64)


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def signals(pick):
    """从槽位索引取均值并做 ECDF-logit；列 0 = 成功率取负（越大越难）。"""
    k = pick.shape[1]
    p3 = np.broadcast_to(pick[:, None, :], (M, 7, k))
    r = np.take_along_axis(Jf, p3, axis=2).mean(axis=2)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def crit_from(pick):
    ok = np.take_along_axis(Jf[:, 0:1, :],
                            np.broadcast_to(pick[:, None, :], (M, 1, pick.shape[1])),
                            axis=2)[:, 0, :]
    return 1.0 - ok.mean(axis=1)


def lambda_cf(k):
    return 1.0 / (1.0 + (k / 27.3) ** 0.895)


def halves(pick):
    h = pick.shape[1] // 2
    return pick[:, :h], pick[:, h:2 * h]


def build_variants(Zf, Z1, Z2):
    rel = np.array([spear(Z1[:, i], Z2[:, i]) for i in range(7)])
    d0 = Zf[:, 0]
    sgn = np.array([1.0 if spear(Zf[:, i], d0) >= 0 else -1.0 for i in range(7)])
    sgn[0] = 1.0
    w = np.maximum(rel, 0.0)
    w6 = w[COLS6]
    w6 = w6 / w6.sum() if w6.sum() > 0 else np.ones(6) / 6.0
    w7 = w / w.sum() if w.sum() > 0 else np.ones(7) / 7.0
    return {
        "fused6": Zf[:, COLS6].mean(1),
        "fused7": Zf.mean(1),
        "signed7": (sgn * Zf).mean(1),
        "rw6": (Zf[:, COLS6] * w6).sum(1),
        "srw7": (Zf * (sgn * w7)).sum(1),
    }, rel, sgn


rng = np.random.default_rng(20260913)
res = {}
print("k    variant  " + "  ".join(f"{s:>22}" for s in LAM_STRATS) +
      "   (held-out gain vs success, pp)")
for k in KS:
    buckets = {v: {s: [] for s in LAM_STRATS} for v in VARIANTS}
    luck = {s: [] for s in LAM_STRATS}
    base = []
    lam_cf_v, lam_rel_v, lam_emp_v = [], [], []
    for rep in range(REP):
        noise = rng.random((M, K))
        order = np.argsort(noise, axis=1)
        pa, pb = order[:, :k], order[:, k:k + B_SIZE]
        Zf = signals(pa)
        pa1, pa2 = halves(pa)
        Z1, Z2 = signals(pa1), signals(pa2)
        V, rel, sgn = build_variants(Zf, Z1, Z2)
        crit = crit_from(pb)
        d0 = Zf[:, 0]
        lam_cf = lambda_cf(k)
        lam_rel = 1.0 - max(0.0, float(spear(Z1[:, 0], Z2[:, 0])))
        lam_cf_v.append(lam_cf); lam_rel_v.append(lam_rel)
        for _ in range(SPLITS):
            pm = rng.permutation(M)
            B = pm[M // 2:]
            base.append(spear(d0[B], crit[B]))
            for v in VARIANTS:
                for sname, lam in (("cf", lam_cf), ("rel", lam_rel)):
                    sc = (1 - lam) * d0 + lam * V[v]
                    buckets[v][sname].append(spear(sc[B], crit[B]))
                # 经验 λ*（仅在题目折半上选，留出半评，与 O8 对齐）
                A = pm[: M // 2]
                cand = [spear(((1 - l) * d0 + l * V[v])[A], crit[A])
                        for l in np.round(np.arange(0, 1.01, 0.05), 2)]
                lstar = float(np.round(np.arange(0, 1.01, 0.05), 2)[int(np.nanargmax(cand))])
                buckets[v]["emp"].append(spear(((1 - lstar) * d0 + lstar * V[v])[B], crit[B]))
                if v == "fused6":
                    lam_emp_v.append(lstar)
    b = float(np.mean(base))
    entry = {
        "success_heldout": round(b, 4),
        "lambda_cf_mean": round(float(np.mean(lam_cf_v)), 4),
        "lambda_rel_mean": round(float(np.mean(lam_rel_v)), 4),
        "lambda_star_emp_mean": round(float(np.mean(lam_emp_v)), 4),
        "variants": {},
    }
    for v in VARIANTS:
        entry["variants"][v] = {}
        for s in LAM_STRATS:
            h = float(np.mean(buckets[v][s]))
            entry["variants"][v][s] = {
                "heldout": round(h, 4),
                "gain_vs_success_pp": round((h - b) * 100, 3),
            }
    res[str(k)] = entry
    for v in VARIANTS:
        row = "  ".join(f"{entry['variants'][v][s]['gain_vs_success_pp']:>+22.3f}" for s in LAM_STRATS)
        print(f"{k:>4} {v:<8} {row}", flush=True)

json.dump({
    "design": "O11 optimization of difficulty fusion: sign-corrected + split-half-reliability-"
              "weighted fusion, and reliability-driven lambda. Identical O7/O8 held-out protocol "
              "(disjoint reservoir blocks A=fit k, B=criterion 250); all signs/weights/lambda "
              "estimated inside A only.",
    "k_list": KS, "B_SIZE": B_SIZE, "reps": REP, "splits": SPLITS,
    "variants": VARIANTS, "lambda_strategies": LAM_STRATS,
    "cols6_drop_upgrade": COLS6,
    "lambda_cf_formula": "1/(1+(k/27.3)^0.895)",
    "lambda_rel_definition": "1 - split_half_reliability_of_success(A)",
    "results": res,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
