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

纯标准库实现（**不依赖 numpy**：本仓库 venv 无 numpy，同 castleman_hmab.py 约定），
无需重跑 LLM。
输出：exogenous_metrics.json + 控制台表

Ordinal AUC compares only pairs with different teacher labels, with 0.5 credit
for tied model ratings. Kendall tau-b excludes joint ties from one-variable tie counts.
Jaccard@k is omitted because a three-level scale does not identify a unique top-k set.
"""
import json
import math
import statistics
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
    """平均秩（含并列 mid-rank），1-based。纯标准库实现。"""
    a = list(a)
    n = len(a)
    order = sorted(range(n), key=lambda i: a[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearmanr(x, y):
    rx, ry = _rank(x), _rank(y)
    n = len(x)
    xc = [rx[i] - sum(rx) / n for i in range(n)]
    yc = [ry[i] - sum(ry) / n for i in range(n)]
    num = sum(xc[i] * yc[i] for i in range(n))
    den = math.sqrt(sum(v * v for v in xc) * sum(v * v for v in yc))
    return 0.0 if den == 0 else float(num / den)


def kendall_tau_b(x, y):
    x = list(x)
    y = list(y)
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
    cx = Counter(x)
    cy = Counter(y)
    joint = sum(v * (v - 1) // 2 for v in Counter(zip(x, y)).values())
    tx = sum(v * (v - 1) // 2 for v in cx.values()) - joint
    ty = sum(v * (v - 1) // 2 for v in cy.values()) - joint
    denom = math.sqrt((c + d + tx) * (c + d + ty))
    return float("nan") if denom == 0 else (c - d) / denom


def ordinal_auc(x, y):
    """Teacher-different pairs only; model ties receive 0.5 credit."""
    x = list(x)
    y = list(y)
    n = len(x)
    num = den = 0
    for i in range(n):
        for j in range(i + 1, n):
            if y[i] == y[j]:        # 教师标签相同：无顺序可比，跳过（修正点）
                continue
            den += 1
            if x[i] == x[j]:
                num += 0.5
            elif (y[i] < y[j]) == (x[i] < x[j]):
                num += 1
    return float(num / den) if den > 0 else float("nan")


def graded_auc(x, y, positive_labels):
    """把教师 3 级量表按切点转为二分类，报模型评级作为分数的 AUC（Mann-Whitney / 秩）。"""
    x = list(x)
    y = list(y)
    pos_idx = [i for i in range(len(y)) if y[i] in positive_labels]
    neg_idx = [i for i in range(len(y)) if y[i] not in positive_labels]
    n_pos = len(pos_idx)
    n_neg = len(neg_idx)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    r = _rank(x)  # 1-based 平均秩（含并列 mid-rank）
    sum_pos = sum(r[i] for i in pos_idx)
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def kscan(x, y, ks):
    x = list(x)
    y = list(y)
    order_x = sorted(range(len(x)), key=lambda i: -x[i])   # 最难（值最大）在前
    order_y = sorted(range(len(y)), key=lambda i: -y[i])
    out = {}
    for k in ks:
        top_x = set(order_x[:k])
        top_y = set(order_y[:k])
        union = top_x | top_y
        jac = len(top_x & top_y) / len(union) if union else 0.0
        out[k] = round(jac, 4)
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
        x = [v[0] for v in items]   # 模型评级
        y = [v[1] for v in items]    # 教师标签
        rho = spearmanr(x, y)
        tau = kendall_tau_b(x, y)
        oa = ordinal_auc(x, y)
        ga1 = graded_auc(x, y, {2, 3})        # 1-vs-{2,3}
        ga2 = graded_auc(x, y, {3})            # {1,2}-vs-3
        ks = {k: float("nan") for k in KS}
        rows[m] = {"n": len(items), "spearman_rho": round(rho, 4),
                   "kendall_tau_b": round(tau, 4), "ordinal_auc": round(oa, 4),
                   "graded_auc_1_vs_23": round(ga1, 4),
                   "graded_auc_12_vs_3": round(ga2, 4),
                   "jaccard_at_k": None, "jaccard_status": "omitted: top-k not identifiable under rating ties"}
        print(f"{m:18s} {len(items):4d} {rho:8.4f} {tau:8.4f} {oa:8.4f} "
              f"{ga1:12.4f} {ga2:12.4f} | " + " ".join(f"{ks[k]:7.4f}" for k in KS))

    with open("results/m3/exogenous_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"definitions": {"ordinal_auc": "teacher-different pairs; model ties = 0.5", "kendall_tau_b": "joint ties excluded from single-variable tie counts"}, "rows": rows}, f, ensure_ascii=False, indent=2)
    print("\n[已写出] results/m3/exogenous_metrics.json")


if __name__ == "__main__":
    main()
