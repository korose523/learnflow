# -*- coding: utf-8 -*-
"""
D4 —— 模型间一致性矩阵（R3 Li 等 点名要求的诊断）
========================================================================
R3 指出：除各模型与真值的 ρ 外，应把**模型彼此之间的 ρ** 放进同一张表；
若模型间 ρ 高于各模型与真值的 ρ，说明是**共享模型偏差**而非数据特性。

数据：results/m3/local_matrix.jsonl（cond=='E1A'，DBE-212 锚定量表 + 教师标签）。
无需重跑 LLM。本脚本只做统计。

产出：
  (1) 各模型与教师标签的 Spearman ρ（ρ_i,expert）
  (2) 模型间两两 Spearman ρ 矩阵（ρ_ij）
  (3) 题目级 bootstrap 200 次，对 [mean(ρ_ij) − mean(ρ_i,expert)] 给 95% CI，
      判定"模型共识是否高于数据对齐"
输出：inter_model_agreement.json + 控制台表
"""
import json
import numpy as np
from math import erf, sqrt

SRC = "results/m3/local_matrix.jsonl"


def _rank(a):
    """平均秩（处理并列），对齐 scipy.stats.rankdata 默认 'average'。"""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    sa = a[order]
    n = len(a)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sa[j + 1] == sa[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg
        i = j + 1
    return ranks


def spearmanr(x, y):
    """纯 numpy 实现的 Spearman ρ（秩 Pearson），返回 (rho, 大样本正态近似 p)。"""
    rx, ry = _rank(x), _rank(y)
    xc, yc = rx - rx.mean(), ry - ry.mean()
    denom = float(np.sqrt((xc * xc).sum() * (yc * yc).sum()))
    if denom == 0:
        return 0.0, 1.0
    r = float((xc * yc).sum() / denom)
    n = len(x)
    if n < 3:
        return r, 1.0
    t = r * sqrt((n - 2) / max(1e-12, (1 - r * r)))
    p = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))
    return r, p
B = 200
SEED = 20260922
MIN_KEYS = 200  # 只用已跑满足够题量的模型


def load():
    recs = {}
    skip = {"none": 0, "bad": 0, "dup": 0}
    for line in open(SRC, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            skip["bad"] += 1
            continue
        if d.get("cond") != "E1A":
            continue
        llm = d.get("llm")
        exp = d.get("expert")
        if llm is None or exp is None:
            skip["none"] += 1
            continue
        try:
            llm_i, exp_i = int(llm), int(exp)
        except (TypeError, ValueError):
            skip["bad"] += 1
            continue
        m, k = d["model"], d["key"]
        if k in recs.setdefault(m, {}):
            skip["dup"] += 1
        recs[m][k] = (llm_i, exp_i)
    print(f"[load] 跳过：None评级={skip['none']} 解析失败={skip['bad']} "
          f"重复键(末值覆盖)={skip['dup']}")
    return recs


def main():
    recs = load()
    models = [m for m, c in recs.items() if len(c) >= MIN_KEYS]
    common = sorted(set.intersection(*[set(recs[m].keys()) for m in models]))
    print(f"入选模型（≥{MIN_KEYS} 题）: {models}")
    print(f"对齐题量（common keys）: {len(common)}")

    data = {m: np.array([recs[m][k][0] for k in common]) for m in models}
    expert = np.array([recs[models[0]][k][1] for k in common])  # 同 key 教师标签唯一

    # (1) 各模型 vs 专家
    rho_expert = {}
    for m in models:
        rho, p = spearmanr(data[m], expert)
        rho_expert[m] = (float(rho), float(p))

    # (2) 模型间两两
    n = len(models)
    pair = np.identity(n)
    for i in range(n):
        for j in range(i + 1, n):
            r, _ = spearmanr(data[models[i]], data[models[j]])
            pair[i, j] = pair[j, i] = r

    # (3) bootstrap
    rng = np.random.default_rng(SEED)
    keys = np.array(common)
    mean_ij_b, mean_ve_b, diff_b = [], [], []
    for _ in range(B):
        idx = rng.integers(0, len(common), len(common))
        sub = [keys[i] for i in idx]
        dsub = {m: np.array([recs[m][k][0] for k in sub]) for m in models}
        esub = np.array([recs[models[0]][k][1] for k in sub])
        pij = []
        for i in range(n):
            for j in range(i + 1, n):
                pij.append(spearmanr(dsub[models[i]], dsub[models[j]])[0])
        ve = [spearmanr(dsub[m], esub)[0] for m in models]
        mean_ij_b.append(float(np.mean(pij)))
        mean_ve_b.append(float(np.mean(ve)))
        diff_b.append(float(np.mean(pij) - np.mean(ve)))

    mean_ij_b = np.array(mean_ij_b)
    mean_ve_b = np.array(mean_ve_b)
    diff_b = np.array(diff_b)

    def ci(a):
        return [round(float(np.percentile(a, 2.5)), 4),
                round(float(np.percentile(a, 97.5)), 4)]

    print("\n=== 各模型 vs 教师标签（ρ, p） ===")
    for m in models:
        print(f"  {m:22s} ρ={rho_expert[m][0]:+.4f}  p={rho_expert[m][1]:.2e}")

    print("\n=== 模型间两两 Spearman ρ 矩阵 ===")
    hdr = "        " + "".join(f"{m.split(':')[0][:6]:>8s}" for m in models)
    print(hdr)
    for i, m in enumerate(models):
        row = f"{m.split(':')[0][:6]:>7s}" + "".join(f"{pair[i,j]:>8.3f}" for j in range(n))
        print(row)

    print("\n=== 判定（预先声明） ===")
    print(f"  mean(ρ_ij)        = {mean_ij_b.mean():+.4f}  95% CI {ci(mean_ij_b)}")
    print(f"  mean(ρ_i,expert)  = {mean_ve_b.mean():+.4f}  95% CI {ci(mean_ve_b)}")
    print(f"  diff = mean(ρ_ij) − mean(ρ_i,expert) = {diff_b.mean():+.4f}  95% CI {ci(diff_b)}")
    if diff_b.mean() > 0 and np.percentile(diff_b, 2.5) > 0:
        verdict = ("模型间一致性**高于**各模型与真值的一致性 → 存在共享模型偏差，"
                   "「题型依赖」结论须收窄为「在共享偏差下的一致反应」，不能读作数据特性。")
    elif diff_b.mean() < 0 and np.percentile(diff_b, 97.5) < 0:
        verdict = ("模型间一致性**低于**各模型与真值的一致性 → 各模型相对独立地捕捉数据信号，"
                   "「题型依赖」结论更可信为数据特性。")
    else:
        verdict = ("模型间一致性与对真值一致性**不可区分**（diff 的 95% CI 含 0）→ "
                   "无法据此判定共享偏差 vs 数据特性，须保守表述。")
    print("  判定结论：", verdict)

    out = {
        "models": models,
        "n_common": len(common),
        "rho_vs_expert": {m: rho_expert[m] for m in models},
        "pairwise_rho": {models[i]: {models[j]: float(pair[i, j]) for j in range(n)} for i in range(n)},
        "bootstrap": {
            "mean_ij_mean": round(float(mean_ij_b.mean()), 4),
            "mean_ij_ci95": ci(mean_ij_b),
            "mean_ve_mean": round(float(mean_ve_b.mean()), 4),
            "mean_ve_ci95": ci(mean_ve_b),
            "diff_mean": round(float(diff_b.mean()), 4),
            "diff_ci95": ci(diff_b),
        },
        "verdict": verdict,
    }
    with open("results/m3/inter_model_agreement.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n[已写出] results/m3/inter_model_agreement.json")


if __name__ == "__main__":
    main()
