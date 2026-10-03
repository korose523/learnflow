"""M1 · A1/A2 两类追加判据：可复算骨架 + 门禁（待真实数据外部执行）。

方案与 CSV 模板见 `docs/LearnFlow_研究设计与审阅档案.md`；模板 `results/m1/m1_criteria_template.csv`
（列：item_id, expert_label_1_2_3, behavior_block_A_anchor, criterion_block_B_anchor）。

⚠️ 本文件是**方法学骨架**，不代表已完成的实验。A1/A2 需要真实数据集拟合：
  - A1（能力校正判据）：用判据半区（B 半学生）作答拟合 IRT-1PL 题目参数 b_j，替换原始成功率
    作更干净的「题目内在难度」判据（复用 O10 学生级留出协议）。
  - A2（外生判据）：把 DBE-KT22 专家标签置于判据块 B，仅在拟合块 A 上估计融合权重，消除标签泄漏。

本骨架提供（纯标准库，审稿人 clone 即跑）：
  - ``fit_irt_1pl``：IRT-1PL（Rasch）边际最大似然 + 高斯–埃尔米特式 quadrature EM，难度恢复正确；
  - ``spearman_rho``：秩相关（含并列秩平均，无 scipy）；
  - ``weighted_kappa``：线性加权 κ（有序字段，复用 A4 数学，用于专家标签评分者信度）；
  - ``EXPERIMENTS``：A1/A2 实验登记（name/criterion/split_protocol/dataset/status）；
  - ``__main__`` 自测：IRT 难度恢复 + Spearman 已知值 + 加权 κ 数学，证明方法正确。
  - 可选 ``--results``：载入真实拟合 JSON（外部产出）做结构校验；缺省则打印「外部待补」不阻断。

用法（骨架自测）：
  python results/m1/verify_m1_criteria.py
用法（真实数据拟合后）：
  python results/m1/verify_m1_criteria.py --results results/m1/m1_criteria_results.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
SCHEME_DOC = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "LearnFlow_研究设计与审阅档案.md"))
TEMPLATE_CSV = os.path.join(HERE, "m1_criteria_template.csv")


# ─────────────────────────────────────────────────────────────────────────────
# A1 / A2 实验登记（结构层门禁依据）
# ─────────────────────────────────────────────────────────────────────────────
EXPERIMENTS: Dict[str, Dict[str, str]] = {
    "A1": {
        "name": "能力校正判据（Ability-calibrated criterion）",
        "criterion": "判据半区 B 半学生作答拟合 IRT-1PL 题目难度 b_j（校正学生能力）",
        "split_protocol": "O10 学生级留出：crc32(uuid) 奇偶切 A/B 半；融合权重仅 A 内估计",
        "dataset": "Junyi（B 半每题 ≥500 作答，1,238 题口径）；DBE 信度不足须注明",
        "status": "骨架已备，真实拟合待外部执行",
    },
    "A2": {
        "name": "外生判据（Exogenous criterion）",
        "criterion": "DBE-KT22 专家标签 1/2/3 置于判据块 B；融合权重仅在 A 块行为信号上估计",
        "split_protocol": "O7 题级 A/B 蓄水池留出；专家标签仅作判据、不进拟合",
        "dataset": "DBE-KT22（212 题，含专家难度标注 1/2/3）",
        "status": "骨架已备，真实拟合待外部执行",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 标准库数学工具
# ─────────────────────────────────────────────────────────────────────────────
def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _gauss_grid(n: int = 41, lo: float = -5.0, hi: float = 5.0) -> Tuple[List[float], List[float]]:
    """N(0,1) 上的高斯–埃尔米特式 quadrature 网格（等距 θ + 正态密度权重，已归一）。"""
    theta = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    raw = [math.exp(-0.5 * t * t) for t in theta]
    s = sum(raw)
    w = [r / s for r in raw]
    return theta, w


def fit_irt_1pl(responses: List[Tuple[int, int, int]],
                n_persons: int, n_items: int,
                n_iter: int = 200, n_nodes: int = 21) -> List[float]:
    """IRT-1PL（Rasch）边际最大似然 EM，返回每题难度 b_j（斜率固定为 1）。

    responses: [(person_idx, item_idx, correct(0/1)), ...]
    能力分布假定 θ ~ N(0,1)，经高斯网格 quadrature 边际化。

    实现要点：M-step 仅遍历「在题 j 上有响应的人」（by_item[j]），避免全人遍历，
    使复杂度与响应稀疏度成正比，可扩展至大规模数据集。
    """
    theta, w = _gauss_grid(n_nodes)
    by_person: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    by_item: Dict[int, List[int]] = defaultdict(list)
    for p, j, c in responses:
        by_person[p].append((j, c))
        by_item[j].append(p)
    b = [0.0] * n_items

    for _ in range(n_iter):
        # E-step：每人在各 quadrature 节点的后验 r[p][q]
        r: Dict[int, List[float]] = {}
        for p in range(n_persons):
            items = by_person.get(p, [])
            if not items:
                r[p] = list(w)
                continue
            like = []
            for q in range(n_nodes):
                acc = w[q]
                for j, c in items:
                    p1 = _sigmoid(theta[q] - b[j])
                    acc *= p1 if c == 1 else (1.0 - p1)
                like.append(acc)
            tot = sum(like)
            r[p] = list(w) if tot <= 0 else [lk / tot for lk in like]
        # 预计算 S_j = Σ_p Σ_q r[p][q]·x_pj（观测正确数的后验期望，与 b 无关）
        S = [0.0] * n_items
        for j in range(n_items):
            for p in by_item[j]:
                rp = r[p]
                c = next(cc for jj, cc in by_person[p] if jj == j)
                for q in range(n_nodes):
                    S[j] += rp[q] * c
        # M-step：每题牛顿求 b_j，仅遍历该题响应者
        for j in range(n_items):
            persons_j = by_item[j]
            if not persons_j:
                continue
            bj = b[j]
            for _ in range(25):
                fval = 0.0
                dfval = 0.0
                for p in persons_j:
                    rp = r[p]
                    for q in range(n_nodes):
                        p1 = _sigmoid(theta[q] - bj)
                        fval += rp[q] * p1
                        dfval += rp[q] * p1 * (1.0 - p1)
                fval -= S[j]
                dfval = -dfval
                if abs(dfval) < 1e-12:
                    break
                step = fval / dfval
                if step > 2.0:
                    step = 2.0
                elif step < -2.0:
                    step = -2.0
                bj -= step
                if abs(step) < 1e-6:
                    break
            b[j] = bj
    return b


def _rank_avg(xs: List[float]) -> List[float]:
    n = len(xs)
    order = sorted(range(n), key=lambda i: xs[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(a: List[float], b: List[float]) -> float:
    """Spearman 秩相关（并列秩平均）。a/b 等长。"""
    n = len(a)
    if n < 2:
        return float("nan")
    ra = _rank_avg(a)
    rb = _rank_avg(b)
    ma = sum(ra) / n
    mb = sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = math.sqrt(sum((ra[i] - ma) ** 2 for i in range(n)))
    db = math.sqrt(sum((rb[i] - mb) ** 2 for i in range(n)))
    if da == 0 or db == 0:
        return float("nan")
    return num / (da * db)


def weighted_kappa(a_labels: List[str], b_labels: List[str],
                   order: List[str]) -> float:
    """线性加权 Cohen κ（有序字段，如专家标签 1<2<3）。复用 A4 数学。"""
    n = len(a_labels)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(order)}
    K = max(1, len(order) - 1)

    def _w(x: str, y: str) -> float:
        return 1 - abs(idx.get(x, 0) - idx.get(y, 0)) / K

    po_w = sum(_w(x, y) for x, y in zip(a_labels, b_labels)) / n
    pa: Dict[str, float] = defaultdict(float)
    pb: Dict[str, float] = defaultdict(float)
    for x, y in zip(a_labels, b_labels):
        pa[x] += 1.0
        pb[y] += 1.0
    for k in list(pa):
        pa[k] /= n
    for k in list(pb):
        pb[k] /= n
    cats = set(a_labels) | set(b_labels)
    pe_w = sum(pa.get(x, 0.0) * pb.get(y, 0.0) * _w(x, y)
               for x in cats for y in cats)
    if 1 - pe_w == 0:
        return 1.0 if po_w == 1.0 else 0.0
    return (po_w - pe_w) / (1 - pe_w)


# ─────────────────────────────────────────────────────────────────────────────
# 自测
# ─────────────────────────────────────────────────────────────────────────────
def _self_test_irt() -> bool:
    print("=" * 70)
    print("A1 自测：合成数据 IRT-1PL 难度恢复（已知 b_j + θ~N(0,1)）")
    print("=" * 70)
    rng = random.Random(20260922)
    J, N, R = 15, 1000, 7
    true_b = sorted(rng.uniform(-1.5, 1.5) for _ in range(J))
    responses: List[Tuple[int, int, int]] = []
    for p in range(N):
        theta = rng.gauss(0.0, 1.0)
        for j in rng.sample(range(J), R):
            p1 = _sigmoid(theta - true_b[j])
            c = 1 if rng.random() < p1 else 0
            responses.append((p, j, c))
    rec = fit_irt_1pl(responses, N, J, n_iter=200)
    diffs = [abs(rec[j] - true_b[j]) for j in range(J)]
    mean_diff = sum(diffs) / J
    rho = spearman_rho(true_b, rec)
    print(f"  题数={J} 人={N} 每人均响应={R}")
    print(f"  难度恢复 |b_rec−b_true| 均值 = {mean_diff:.3f}（阈值 < 0.30）")
    print(f"  恢复难度与真值秩相关 ρ = {rho:.3f}（阈值 > 0.95）")
    ok = mean_diff < 0.30 and rho > 0.95
    print("  A1 IRT 恢复:", "PASS" if ok else "FAIL")
    return ok


def _self_test_spearman() -> bool:
    print("-" * 70)
    print("Spearman 已知值自测")
    print("-" * 70)
    mono = list(range(10))
    rev = list(reversed(mono))
    rand = [3, 7, 1, 9, 2, 8, 4, 6, 0, 5]
    r_mono = spearman_rho(mono, mono)
    r_rev = spearman_rho(mono, rev)
    r_rand = spearman_rho(mono, rand)
    print(f"  完全单调 ρ={r_mono:.3f}（期望 1.000）")
    print(f"  完全反单调 ρ={r_rev:.3f}（期望 -1.000）")
    print(f"  随机序列 ρ={r_rand:.3f}（期望 |ρ|<0.3）")
    ok = abs(r_mono - 1.0) < 1e-9 and abs(r_rev + 1.0) < 1e-9 and abs(r_rand) < 0.3
    print("  Spearman:", "PASS" if ok else "FAIL")
    return ok


def _self_test_kappa() -> bool:
    print("-" * 70)
    print("A2 加权 κ 自测（有序专家标签 1<2<3）")
    print("-" * 70)
    order = ["1", "2", "3"]
    synth = [("1", "easy"), ("2", "mid"), ("3", "hard"),
             ("1", "easy"), ("2", "mid")]
    a = {f"item{i}": {"expert_label_1_2_3": lab} for i, (lab, _mid) in enumerate(synth, 1)}
    b = {k: dict(v) for k, v in a.items()}
    k_full = weighted_kappa([a[i]["expert_label_1_2_3"] for i in a],
                            [b[i]["expert_label_1_2_3"] for i in b], order)
    # 一处分歧：item3 由 3 改为 1
    b2 = {k: dict(v) for k, v in a.items()}
    b2["item3"]["expert_label_1_2_3"] = "1"
    k_div = weighted_kappa([a[i]["expert_label_1_2_3"] for i in a],
                           [b2[i]["expert_label_1_2_3"] for i in b2], order)
    print(f"  两编码者完全一致 κ = {k_full:.3f}（期望 1.000）")
    print(f"  含 1 处分歧 κ = {k_div:.3f}（期望 < 1.000）")
    ok = abs(k_full - 1.0) < 1e-9 and k_div < 1.0
    print("  A2 加权 κ:", "PASS" if ok else "FAIL")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# 结构层 / 外部结果校验
# ─────────────────────────────────────────────────────────────────────────────
def _structural_checks() -> List[str]:
    problems: List[str] = []
    for key in ("A1", "A2"):
        exp = EXPERIMENTS.get(key, {})
        for field in ("name", "criterion", "split_protocol", "dataset", "status"):
            if not exp.get(field):
                problems.append(f"EXPERIMENTS[{key}] 缺字段 {field}")
    if not os.path.isfile(SCHEME_DOC):
        problems.append(f"方案文档缺失：{SCHEME_DOC}")
    if not os.path.isfile(TEMPLATE_CSV):
        problems.append(f"CSV 模板缺失：{TEMPLATE_CSV}")
    return problems


def _validate_external_results(path: str) -> List[str]:
    """校验真实拟合 JSON（外部产出）结构；仅做存在性与字段检查。"""
    problems: List[str] = []
    try:
        data = json.loads(open(path, encoding="utf-8").read())
    except (OSError, ValueError) as exc:
        return [f"外部结果 JSON 读取失败：{exc}"]
    for block in ("a1", "a2"):
        if block not in data:
            problems.append(f"外部结果缺块 {block}")
            continue
        blk = data[block] or {}
        for field in ("spearman_fusion", "spearman_success"):
            if field not in blk:
                problems.append(f"外部结果 {block} 缺字段 {field}")
    return problems


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="M1 A1/A2 两类判据骨架门禁")
    ap.add_argument("--results", help="真实拟合结果 JSON（外部产出）路径")
    args = ap.parse_args()

    # 结构层
    sp = _structural_checks()
    if sp:
        for p in sp:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1
    print("结构层: PASS（EXPERIMENTS A1/A2 登记完整；方案文档与 CSV 模板存在）")

    # 自测层
    ok_irt = _self_test_irt()
    ok_spear = _self_test_spearman()
    ok_kappa = _self_test_kappa()
    if not (ok_irt and ok_spear and ok_kappa):
        print("结论: FAIL   退出码 1")
        return 1
    print("自测层: PASS（IRT 难度恢复 / Spearman 已知值 / 加权 κ 数学 全部正确）")

    # 外部结果（可选）
    if args.results:
        rp = _validate_external_results(args.results)
        if rp:
            for p in rp:
                print(f"[FAIL] {p}")
            print("结论: FAIL   退出码 1")
            return 1
        print(f"外部结果校验: PASS（{args.results} 含 a1/a2 双块）")
    else:
        print("⚠ 外部结果 JSON 未提供：A1/A2 真实数据集拟合为外部动作，"
              "须确认 assist09/DBE-KT22/Junyi 可得后由人工执行（状态 🟡）。")

    print("结论: PASS   退出码 0")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError as exc:
        print(f"[M1] 文件缺失：{exc}", file=sys.stderr)
        sys.exit(2)
