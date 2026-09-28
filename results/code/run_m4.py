# -*- coding: utf-8 -*-
"""M4 主实验：在 Junyi / DBE-KT22 真实缓存上，把 M4 与既有估计器放在同一协议下比较。

两套协议
--------
**P1（主判据 · 外生标签）**：只用蓄水池的前 k 个槽位估计难度，把全部题目的排序与
**不由日志产生**的难度标签比较——DBE 为**教师标注**（D_y），Junyi 为平台标注（J_y）。
标签 3 级且并列极多 ⇒ 用 **Kendall τ_b**（遵循 R7 的规约）。这一协议回答 K2：留出
错误率与成功率基线是同一统计量，故不能充当"谁更准"的判据。
**P2（同场对照 · 既有留出协议）**：结构对齐 O8/O11（互斥 A/B 槽位块，判据 = B 块
错误率，λ 在题目折半上选、留出半上评）。判据**非外生**，只回答"有没有退化"。

估计器
------
success / fused6_cf / srw7_cf / srw7_rel   既有（及其 O11 变体）
m4_W / m4_WV / m4_full                     M4 消融：A 误差校正权重 → +B 共线校正 → +C 导出 λ
m4_cov                                     +D 每题覆盖率校正的本地信度（部分可观测）
*_emp / *_cv                               只用**折外**信息标定**一个标量 λ** 的公平版本

为什么用 stdlib Mersenne 而不是 numpy PCG64
------------------------------------------
原 O11 用 numpy.random.default_rng(20260913)。本环境无 numpy/scipy，**无法逐位复刻其
抽槽序列**，故本脚本数值不会与 o11_fusion_optimization.json 逐位相同。可比性由两点保证：
(1) 协议结构完全对齐（同 k、B_SIZE、REP、SPLITS、同样的"仅在拟合块内估计"约束）；
(2) 基线与 M4 在**每一次抽样下同源比较**，故"差"可信、"绝对值"不可与旧 JSON 混用。

用法
----
    python results/code/run_m4.py --quick      # 冒烟
    python results/code/run_m4.py              # 完整（默认写入 m4_results.json）
"""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_lib import (  # noqa: E402
    load_cache, ecdf_logit, pearson, spearman, rank_average,
    kendall_tau_b_fast as tau_b, standardize, spearman_brown,
    unit_unreliability_from_half, item_reliability_from_coverage, solve,
)

HERE = Path(__file__).resolve().parent
NPZ = HERE / "difficulty_cache.npz"
OUT = HERE / "m4_results.json"

J_NAMES = ["success", "hint_rate", "duration", "attempt_cnt", "upgrade", "downgrade", "repeat"]
J_DROP = 4                       # O8 fused6：剔除 upgrade_rate
D_NAMES = ["success", "hint_rate", "duration", "self_report", "trust"]
D_MISSING = (2, 3, 4)            # DBE 中这些列以 -1 表示未作答/未反馈
K_SLOTS = 500


def lambda_cf(k):
    return 1.0 / (1.0 + (k / 27.3) ** 0.895)


# ------------------------------------------------------------------ 信号
def item_stats(flat, F, K, i, slots):
    """第 i 题在给定槽位上的逐字段均值与有效计数（-1 = 缺失）。"""
    n = len(slots)
    acc = [0.0] * F
    cnt = [n] * F
    b0 = i * F * K
    for s in slots:
        b = b0 + s
        for j in range(F):
            v = flat[b + j * K]
            if v < 0:
                cnt[j] -= 1
                continue
            acc[j] += v
    return [acc[j] / cnt[j] if cnt[j] > 0 else 0.0 for j in range(F)], cnt


def build(cache, tag, M, F, picks):
    flat = cache[f"{tag}_res"][1]
    means, counts = [], []
    for i in range(M):
        m, c = item_stats(flat, F, K_SLOTS, i, picks[i])
        means.append(m)
        counts.append(c)
    return means, counts


def to_z(means):
    """逐列 ECDF-logit；列 0（成功率，越大越易）取负 ⇒ 统一为越大越难。返回列式列表。"""
    M = len(means)
    F = len(means[0])
    cols = [[means[i][j] for i in range(M)] for j in range(F)]
    Zc = []
    for j in range(F):
        z = ecdf_logit(cols[j])
        if j == 0:
            z = [-x for x in z]
        Zc.append(z)
    return Zc


def orient(a, ref):
    return a if spearman(a, ref) >= 0 else [-x for x in a]


def mix(ref, comp, lam):
    return [(1.0 - lam) * ref[i] + lam * comp[i] for i in range(len(ref))]


def beta_from_q(Zstd, q, ridge=1e-3, R=None):
    """M4-B：β = V^{-1} q。

    V 取**秩相关**矩阵（M4-A：对 ecdf-logit 尾部极值不敏感，且完整保留 M1/O1 的
    "单调重参数化不变性"）；q_k = sign_k · √ρ_k（把符号校正与信度加权**合并为一个参数**，
    因为二者在单因子模型下本就是同一件事的两面）。

    R：预计算的标准化列秩矩阵；为 None 时内部用 `rank_average` 现算。在每题
    （per-item）路径中 Zstd 的秩对所有题目相同，由调用方算一次后透传，避免重复排序
    （见 M4 完整稿第 3.5 节；数值结果与内联计算逐位一致）。
    """
    m = len(Zstd)
    if R is None:
        R = [rank_average(c) for c in Zstd]
    V = [[0.0] * m for _ in range(m)]
    for i in range(m):
        V[i][i] = 1.0 + ridge
        for j in range(i + 1, m):
            v = pearson(R[i], R[j])
            V[i][j] = V[j][i] = v
    beta = solve(V, q)
    if beta is None:
        s = sum(abs(x) for x in q)
        beta = [x / s for x in q] if s > 0 else [1.0 / m] * m
    return beta


# ------------------------------------------------------------------ 估计器
def all_variants(Zc, Z1, Z2, k, drop_idx, counts=None, rho_unit=None):
    """产出全部变体。返回 (scores, comps, diag)。

    scores: {名: 每题分数}；comps: {名: (ref, comp)} 供折外 λ 标定使用。
    全部信息只来自拟合块 A，**不接触任何标签**。
    """
    M = len(Zc[0])
    F = len(Zc)
    ref = Zc[0]
    sgn = [1.0 if spearman(Zc[j], ref) >= 0.0 else -1.0 for j in range(F)]
    sgn[0] = 1.0
    rel = []
    for j in range(F):
        r = spearman(Z1[j], Z2[j])
        rel.append(spearman_brown(r) if r > 0 else 0.0)
    keep = [j for j in range(F) if j != drop_idx] if drop_idx is not None else list(range(F))

    S, C = {}, {}

    S["success"] = list(ref)

    fused6 = [sum(Zc[j][i] for j in keep) / len(keep) for i in range(M)]
    fused6 = orient(fused6, ref)
    S["fused6_cf"] = mix(ref, fused6, lambda_cf(k))
    C["fused6_cf"] = (ref, fused6)

    w = [max(0.0, rel[j]) for j in range(F)]
    sw = sum(w)
    w = [x / sw for x in w] if sw > 0 else [1.0 / F] * F
    srw = [sum(w[j] * sgn[j] * Zc[j][i] for j in range(F)) for i in range(M)]
    srw = orient(srw, ref)
    S["srw7_cf"] = mix(ref, srw, lambda_cf(k))
    C["srw7_cf"] = (ref, srw)
    S["srw7_rel"] = mix(ref, srw, 1.0 - max(0.0, spearman(Z1[0], Z2[0])))
    C["srw7_rel"] = (ref, srw)

    Zstd = standardize(Zc)
    R = [rank_average(c) for c in Zstd]      # item-invariant：全模块只算一次（第 3.5 节）
    wa = []
    for j in range(F):
        rr = min(0.999999, max(0.0, rel[j]))
        wa.append(sgn[j] * math.sqrt(rr) / (1.0 - rr + 1e-9))
    sa = sum(abs(x) for x in wa)
    wa = [x / sa for x in wa] if sa > 0 else [1.0 / F] * F
    mA = [sum(wa[j] * Zstd[j][i] for j in range(F)) for i in range(M)]
    mA = orient(mA, ref)
    S["m4_W"] = mix(ref, mA, lambda_cf(k))
    C["m4_W"] = (ref, mA)

    q = [sgn[j] * math.sqrt(min(0.999999, max(0.0, rel[j]))) for j in range(F)]
    beta = beta_from_q(Zstd, q, R=R)
    mB = [sum(beta[j] * Zstd[j][i] for j in range(F)) for i in range(M)]
    mB = orient(mB, ref)
    S["m4_WV"] = mix(ref, mB, lambda_cf(k))
    C["m4_WV"] = (ref, mB)
    S["m4_full"] = list(mB)                 # M4-C：不再有外部 λ，组合本身即输出
    C["m4_full"] = (ref, mB)

    absb = [abs(x) for x in beta]
    tot = sum(absb)
    diag = {"lambda_derived": round((tot - absb[0]) / tot, 4) if tot > 0 else 0.0}

    # ---- M4-E：残差化（把每个辅助信号对参考列的**冗余**成分剔除，只留增量部分） ----
    # 动机直接来自第 5 节的负结果：ρ_k 随 k 上升 ⟹ M4 给辅助列的权重单调上升，
    # 但辅助列与成功率高度共线 ⟹ 上升的那部分权重买到的是**冗余**而非增量信息，
    # 在外生教师标签上表现为收益随 k 塌缩。残差化把这一结构显式化：
    # 组合项被约束为"成功率之外的增量"，它与参考列正交，故 λ 的含义也随之变干净
    # ——λ 不再是"整体缩放参考列"的旋钮，而是"增量信息值多少"的旋钮。
    eres = {}
    for j in range(1, F):
        if j == drop_idx:
            continue
        rho0 = pearson(R[j], R[0])
        d2 = 1.0 - rho0 * rho0
        if d2 <= 1e-6:                      # 与参考列完全共线 ⟹ 无增量信息，剔除
            continue
        sc = d2 ** 0.5
        eres[j] = [(Zstd[j][i] - rho0 * Zstd[0][i]) / sc for i in range(M)]
    if eres:
        wr = {j: sgn[j] * math.sqrt(min(0.999999, max(0.0, rel[j]))) for j in eres}
        wt = sum(abs(x) for x in wr.values()) or 1.0
        compE = [sum(wr[j] * eres[j][i] for j in eres) / wt for i in range(M)]
        compE = standardize([compE])[0]     # 单位方差 ⟹ λ 的含义与 srw7 口径可比
        # 不调用 orient()：残差列按构造与参考列近正交，与 ref 的相关会退化为一个
        # 由浮点噪声决定符号的数，用它定向等于随机翻转。方向一律继承原始列的 sgn。
        S["m4_E_cf"] = mix(ref, compE, lambda_cf(k))
        C["m4_E_cf"] = (ref, compE)
        lam_rel = 1.0 - max(0.0, spearman(Z1[0], Z2[0]))
        S["m4_E_rel"] = mix(ref, compE, lam_rel)
        C["m4_E_rel"] = (ref, compE)

    if counts is not None and rho_unit:
        per = []
        for i in range(M):
            qi = []
            for j in range(F):
                rho_j = rel[j]
                if j in D_MISSING and j in rho_unit:
                    rho_j = item_reliability_from_coverage(rho_unit[j], counts[i][j])
                qi.append(sgn[j] * math.sqrt(min(0.999999, max(0.0, rho_j))))
            bi = beta_from_q(Zstd, qi, R=R)
            per.append(sum(bi[j] * Zstd[j][i] for j in range(F)))
        per = orient(per, ref)
        S["m4_cov"] = list(per)
        C["m4_cov"] = (ref, per)
    return S, C, diag


# ------------------------------------------------------------------ 折外 λ 标定
LAM_GRID = [round(i * 0.05, 2) for i in range(21)]      # 与 O11 的 emp 策略同网格


def cv_lambda(ref, comp, labels, folds, grid, seed):
    """折外（out-of-fold）标定**一个标量** λ：训练折上选、测试折上用。

    刻意只标定一个标量而不标定逐列权重：后者在 212 题规模上会退化为对标签的过拟合，
    也违背本稿"外生标签只用于评价与单个预算标量、结构由未标注侧的信度决定"的原则。
    """
    n = len(labels)
    idx = list(range(n))
    r = random.Random(seed)
    r.shuffle(idx)
    out = [0.0] * n
    chosen = []
    step = max(1, n // folds)
    for f in range(folds):
        te = idx[f * step:(f + 1) * step] if f < folds - 1 else idx[f * step:]
        tr = [i for i in idx if i not in set(te)]
        if not tr or not te:
            continue
        best, bl = -1e9, 0.0
        lab = [labels[i] for i in tr]
        for lam in grid:
            sc = [(1 - lam) * ref[i] + lam * comp[i] for i in tr]
            v = tau_b(sc, lab)
            if v > best:
                best, bl = v, lam
        chosen.append(bl)
        for i in te:
            out[i] = (1.0 - bl) * ref[i] + bl * comp[i]
    return out, chosen


# ------------------------------------------------------------------ 协议
def prepare(cache, tag, which, caps, rng, k):
    M = len(caps)
    F = 7 if which == "J" else 5
    picks = [rng.sample(range(caps[i]), min(caps[i], k)) for i in range(M)]
    means, counts = build(cache, tag, M, F, picks)
    Zc = to_z(means)
    h = max(1, k // 2)
    m1, _ = build(cache, tag, M, F, [p[:h] for p in picks])
    m2, _ = build(cache, tag, M, F, [p[h:2 * h] for p in picks])
    Z1, Z2 = to_z(m1), to_z(m2)
    return Zc, Z1, Z2, counts, F


def paired_stats(deltas):
    n = len(deltas)
    if n == 0:
        return {}
    m = sum(deltas) / n
    sd = (sum((x - m) ** 2 for x in deltas) / (n - 1)) ** 0.5 if n > 1 else 0.0
    wins = sum(1 for x in deltas if x > 0)
    return {"delta": round(m, 4), "sd": round(sd, 4),
            "win_rate": round(wins / n, 3), "n_pairs": n}


def protocol_labels(cache, which, reps, ks, seed, cv_folds=5):
    """P1：k 槽拟合 → 与外生标签的 Kendall τ_b；并给出相对 srw7_cf 的配对统计。"""
    tag = "J" if which == "J" else "D"
    full = cache[f"{tag}_full"][1]
    labels = list(cache[f"{tag}_y"][1])
    M = len(labels)
    ncol = 8 if which == "J" else 6
    caps = [min(int(full[i * ncol]), K_SLOTS) for i in range(M)]
    drop = J_DROP if which == "J" else None
    rng = random.Random(seed)
    out = {}
    for k in ks:
        per_rep, diags = {}, []
        for rep in range(reps):
            Zc, Z1, Z2, counts, F = prepare(cache, tag, which, caps, rng, k)
            rho_unit = None
            if which == "D":
                rho_unit = {j: unit_unreliability_from_half(
                    spearman(Z1[j], Z2[j]), max(1, k // 4)) for j in D_MISSING}
            S, C, diag = all_variants(Zc, Z1, Z2, k, drop, counts, rho_unit)
            diags.append(diag["lambda_derived"])
            for name, vec in S.items():
                per_rep.setdefault(name, []).append(tau_b(vec, labels))
            for name in ("srw7_cf", "m4_full", "m4_cov"):
                if name not in C:
                    continue
                ref, comp = C[name]
                vec, ch = cv_lambda(ref, comp, labels, cv_folds, LAM_GRID, seed + rep)
                per_rep.setdefault(name + "_cv", []).append(tau_b(vec, labels))
                if name == "m4_full" and ch:
                    per_rep.setdefault("_cv_lambda_m4", []).append(round(sum(ch) / len(ch), 4))
        base = per_rep["srw7_cf"]
        row = {"_n_items": M, "_reps": reps,
               "_lambda_derived_mean": round(sum(diags) / max(1, len(diags)), 4)}
        if "_cv_lambda_m4" in per_rep:
            row["_cv_lambda_m4_mean"] = round(
                sum(per_rep["_cv_lambda_m4"]) / len(per_rep["_cv_lambda_m4"]), 4)
        for name, arr in per_rep.items():
            if name.startswith("_"):
                continue
            m = sum(arr) / len(arr)
            row[name] = {"tau_b": round(m, 4),
                         "sd": round((sum((x - m) ** 2 for x in arr) / max(1, len(arr) - 1)) ** 0.5, 4)}
            if name != "srw7_cf":
                row[name].update(paired_stats([arr[i] - base[i] for i in range(len(arr))]))
        out[str(k)] = row
        print(f"  [{tag}] k={k:<4} " + " ".join(
            f"{n}={v['tau_b']:+.4f}" for n, v in row.items() if isinstance(v, dict)), flush=True)
    return out


def protocol_holdout(cache, reps, ks, seed, splits, b_size=250):
    """P2：对齐 O8/O11 的同场对照（判据 = 互斥 B 块错误率；非外生）。"""
    full = cache["J_full"][1]
    M = len(cache["J_y"][1])
    caps = [min(int(full[i * 8]), K_SLOTS) for i in range(M)]
    rng = random.Random(seed)
    out = {}
    for k in ks:
        acc = {}
        for rep in range(reps):
            picks = [rng.sample(range(caps[i]), min(caps[i], k + b_size)) for i in range(M)]
            pa = [p[:k] for p in picks]
            pb = [p[k:k + b_size] for p in picks]
            means, counts = build(cache, "J", M, 7, pa)
            Zc = to_z(means)
            h = max(1, k // 2)
            m1, _ = build(cache, "J", M, 7, [p[:h] for p in pa])
            m2, _ = build(cache, "J", M, 7, [p[h:2 * h] for p in pa])
            Z1, Z2 = to_z(m1), to_z(m2)
            bmeans, _ = build(cache, "J", M, 7, pb)
            crit = [1.0 - bmeans[i][0] for i in range(M)]
            S, C, _ = all_variants(Zc, Z1, Z2, k, J_DROP, counts, None)
            for _ in range(splits):
                perm = list(range(M))
                rng.shuffle(perm)
                A, B = perm[:M // 2], perm[M // 2:]
                cb = [crit[i] for i in B]
                for name, vec in S.items():
                    acc.setdefault(name, []).append(spearman([vec[i] for i in B], cb))
                for name in ("fused6_cf", "srw7_cf", "m4_full"):
                    ref, comp = C[name]
                    ca = [crit[i] for i in A]
                    best, bl = -1e9, 0.0
                    for lam in LAM_GRID:
                        v = spearman([(1 - lam) * ref[i] + lam * comp[i] for i in A], ca)
                        if v > best:
                            best, bl = v, lam
                    acc.setdefault(name + "_emp", []).append(
                        spearman([(1 - bl) * ref[i] + bl * comp[i] for i in B], cb))
        row = {"_reps": reps, "_splits": splits}
        for n, arr in acc.items():
            row[n] = {"mean": round(sum(arr) / len(arr), 4)}
        out[str(k)] = row
        print(f"  [holdout] k={k:<4} " + " ".join(
            f"{n}={v['mean']:+.4f}" for n, v in row.items() if isinstance(v, dict)), flush=True)
    return out


ESTIMATOR_DOC = {
    "success": "仅成功率（基线）",
    "fused6_cf": "既有部署：等权 fused6 + λ_cf(k)",
    "srw7_cf": "既有最优：符号校正 + 信度加权 + λ_cf(k)",
    "srw7_rel": "srw7 + O11 的信度驱动 λ_rel = 1 − ρ_success",
    "m4_W": "消融 A：权重 √ρ/(1−ρ)（无共线校正），保留 λ_cf",
    "m4_WV": "消融 A+B：β = V⁻¹q，保留 λ_cf",
    "m4_full": "M4 完整：β = V⁻¹q，取消外部 λ",
    "m4_E_cf": "M4 + E：辅助列先对参考列残差化（只留增量），再按 λ_cf 混合",
    "m4_E_rel": "M4 + E：残差化 + O11 的信度驱动 λ_rel = 1 − ρ_success",
    "m4_cov": "M4 + D：每题覆盖率校正的本地信度（部分可观测）",
    "_cv": "折外标定**一个标量** λ（标签只用于标定该标量，且严格折外）",
    "_emp": "O11 同口径经验 λ（题目折半上选、留出半上评）",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=20260927)
    args = ap.parse_args()

    KS = [10, 25, 50, 100, 200]
    t0 = time.time()
    cache = load_cache(NPZ)
    print(f"cache loaded ({cache['J_res'][0]}, {cache['D_res'][0]}) in {time.time()-t0:.1f}s",
          flush=True)

    dbe_r = 3 if args.quick else 20
    jun_r = 2 if args.quick else 8
    ho_r, ho_s = (1, 2) if args.quick else (8, 10)

    print("\n=== P1a DBE-KT22 · 外生判据 = 教师难度标签 (Kendall τ_b) ===", flush=True)
    dbe = protocol_labels(cache, "D", dbe_r, KS, args.seed)
    print("\n=== P1b Junyi · 平台难度标签（次要，同一 τ_b）===", flush=True)
    jun = protocol_labels(cache, "J", jun_r, KS, args.seed + 1)
    print("\n=== P2 Junyi · 既有留出协议同场对照（判据非外生，仅对照）===", flush=True)
    ho = protocol_holdout(cache, ho_r, KS, args.seed + 2, ho_s)

    payload = {
        "note": ("M4 vs existing estimators on cached real data, pure-stdlib. "
                 "RNG = random.Random(seed) (NOT numpy PCG64) → absolute values are not "
                 "bit-comparable with o11_fusion_optimization.json; within-run paired "
                 "comparisons are valid."),
        "seed": args.seed, "k_list": KS,
        "lambda_cf_formula": "1/(1+(k/27.3)^0.895)",
        "lambda_grid": LAM_GRID,
        "estimators": ESTIMATOR_DOC,
        "protocols": {"P1_dbe_teacher_labels": dbe,
                      "P1_junyi_platform_labels": jun,
                      "P2_junyi_holdout_errorrate": ho},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nsaved -> {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
