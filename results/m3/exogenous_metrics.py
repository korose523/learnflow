# -*- coding: utf-8 -*-
"""
C1/C3 —— K2 外生基准的度量增补（τ_b / 分级 AUC / k 扫描）
========================================================================
K2 当前已用 Spearman ρ + Cohen's κ 刻画"模型评级 vs 教师标签"的对齐。
本脚本在本地 Ollama E1A（DBE-212 锚定量表 + 教师 1/2/3 标签）上增补三类更稳健/
更贴合 ordinal 的度量，作为 K2 度量的完备化：

  (1) Kendall τ_b        —— 处理并列（ties）优于 Spearman，ordinal 数据首选
  (2) Ordinal AUC        —— 仅在"教师标签确实不同"的题对上，看模型是否保持同序
                           （pairwise 顺序保持率，比 Spearman 更能区分"顺序 vs 间距"）
  (3) Graded AUC         —— 按 C1 计划的两个切点：1-vs-{2,3} 与 {1,2}-vs-3，
                           把 3 级量表当作两个二分类问题，报模型评级作为分数的 AUC
  (4) k-scan (Jaccard@k) —— 最难的 k 题集合（按教师标签）与模型最难的 k 题集合的重叠
                           ，k 取计划值 {10,25,50,100,200}

纯 numpy 实现，不依赖 scipy。无需重跑 LLM。
输出：exogenous_metrics.json + 控制台表
"""
import json
import numpy as np
from collections import Counter

SRC = "results/m3/local_matrix.jsonl"
MIN_KEYS = 200
KS = [10, 25, 50, 100, 200]


def load():
    recs = {}
    for line in open(SRC, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("cond") != "E1A":
            continue
        llm = d.get("llm")
        exp = d.get("expert")
        if llm is None or exp is None:
            continue
        try:
            li, ei = int(llm), int(exp)
        except (TypeError, ValueError):
            continue
        recs.setdefault(d["model"], {})[d["key"]] = (li, ei)
    return recs


def _rank(a):
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
    rx, ry = _rank(x), _rank(y)
    xc, yc = rx - rx.mean(), ry - ry.mean()
    denom = float(np.sqrt((xc * xc).sum() * (yc * yc).sum()))
    return 0.0 if denom == 0 else float((xc * yc).sum() / denom)


def kendall_tau_b(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    c = d = 0
    for i in range(n):
        xi, yi = x[i], y[i]
        for j in range(i + 1, n):
            dx = xi - x[j]
            dy = yi - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0 or dy == 0:
                continue
            if (dx > 0) == (dy > 0):
                c += 1
            else:
                d += 1
    cx = Counter(x.tolist())
    cy = Counter(y.tolist())
    tx = sum(v * (v - 1) // 2 for v in cx.values())
    ty = sum(v * (v - 1) // 2 for v in cy.values())
    denom = float(np.sqrt((c + d + tx) * (c + d + ty)))
    return 0.0 if denom == 0 else (c - d) / denom


def ordinal_auc(x, y):
    """pairwise 顺序保持率：仅在教师标签不同的题对上比较模型评级是否同序。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    num = den = 0
    for i in range(n):
        for j in range(i + 1, n):
            if x[i] == x[j]:
                continue
            den += 1
            if (x[i] < x[j]) == (y[i] < y[j]):
                num += 1
    return float(num / den) if den > 0 else float("nan")


def graded_auc(x, y, positive_labels):
    """把教师 3 级量表按切点转为二分类，报模型评级作为分数的 AUC（Mann-Whitney / 秩）。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    pos = np.isin(y, list(positive_labels))
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    r = _rank(x)  # 1-based 平均秩（含并列 mid-rank）
    sum_pos = float(r[pos].sum())
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def kscan(x, y, ks):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    order_x = np.argsort(-x)   # 最难（值最大）在前
    order_y = np.argsort(-y)
    out = {}
    for k in ks:
        top_x = set(order_x[:k].tolist())
        top_y = set(order_y[:k].tolist())
        jac = len(top_x & top_y) / len(top_x | top_y)
        out[k] = round(float(jac), 4)
    return out


def main():
    recs = load()
    models = [m for m, c in recs.items() if len(c) >= MIN_KEYS]
    print(f"入选模型（≥{MIN_KEYS} 题）: {models}\n")
    rows = {}
    hdr = (f"{'模型':18s} {'n':>4s} {'ρ':>8s} {'τ_b':>8s} {'ordAUC':>8s} "
           f"{'G-AUC(1|23)':>12s} {'G-AUC(12|3)':>12s} | Jaccard@k")
    print(hdr)
    print(f"{'':18s} {'':>4s} {'':>8s} {'':>8s} {'':>8s} "
          f"{'':>12s} {'':>12s} | " + " ".join(f"{k:>7d}" for k in KS))
    for m in models:
        items = list(recs[m].values())
        x = np.array([v[0] for v in items])   # 模型评级
        y = np.array([v[1] for v in items])    # 教师标签
        rho = spearmanr(x, y)
        tau = kendall_tau_b(x, y)
        oa = ordinal_auc(x, y)
        ga1 = graded_auc(x, y, {2, 3})        # 1-vs-{2,3}
        ga2 = graded_auc(x, y, {3})            # {1,2}-vs-3
        ks = kscan(x, y, KS)
        rows[m] = {"n": len(items), "spearman_rho": round(rho, 4),
                   "kendall_tau_b": round(tau, 4), "ordinal_auc": round(oa, 4),
                   "graded_auc_1_vs_23": round(ga1, 4),
                   "graded_auc_12_vs_3": round(ga2, 4),
                   "jaccard_at_k": {str(k): ks[k] for k in KS}}
        print(f"{m:18s} {len(items):4d} {rho:8.4f} {tau:8.4f} {oa:8.4f} "
              f"{ga1:12.4f} {ga2:12.4f} | " + " ".join(f"{ks[k]:7.4f}" for k in KS))

    with open("results/m3/exogenous_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"ks": KS, "rows": rows}, f, ensure_ascii=False, indent=2)
    print("\n[已写出] results/m3/exogenous_metrics.json")


if __name__ == "__main__":
    main()
