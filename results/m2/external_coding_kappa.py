"""路线 A · A4 骨架：外部 ≥4 系统 + 双人独立编码 + Cohen κ（待外部/人工执行）。

方案与 CODEBOOK 细则见 `docs/M2_A4_外部系统双编码方案.md`；CSV 模板见
`results/m2/a4_coding_template.csv`（列：system,item_id,target_construct,direction,channel,coder,source_anchor）。

⚠️ 本文件是**方法学骨架**，不代表已完成的实验。A4 需要：
  1) 对 **≥ 4 个**外部游戏化/自适应学习系统作逐文件编码（路线 A 要求从 E2 的 2 个
     扩到 ≥ 4 个）；
  2) **两名独立编码者**对同一批机制实例各自编码（双编码 / 双人独立编码）；
  3) 报告各字段的 **评分者间信度 Cohen κ**（含加权 κ 适用有序字段）。

本骨架提供：
  - 纯标准库实现的 ``cohen_kappa`` / ``cohen_weighted_kappa``（无第三方依赖，审稿人
     clone 即可运行）；
  - ``SYSTEMS`` 占位（当前 2 个已编码 + 2 个待补，凑齐 ≥4）；
  - ``CODEBOOK`` 编码字段（target_construct / direction / channel，与 M2 稿 §6 一致，
    每个编码须带 ``file:line`` 锚点）；
  - 双编码 CSV 载入与逐字段 κ 计算；
  - ``__main__`` 自测：用一份合成"两编码者完全一致"的数据跑通 κ=1.0，证明数学正确，
    并打印明确提示——真实数据需两名人类编码者就 ≥4 系统产出。

数据格式（双编码 CSV，每个编码者一个文件，UTF-8）：
  system,item_id,target_construct,direction,channel,coder,source_anchor
  Ludilearn,M1,reward,approach,notification,coderA,classes/local/gameelements/score.php:42
  ...

用法（骨架自测）：
  python results/m2/external_coding_kappa.py
用法（真实双编码后）：
  python results/m2/external_coding_kappa.py --coder-a coderA.csv --coder-b coderB.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 外部系统清单（路线 A 要求 ≥ 4 个；当前 2 已编码 + 2 待补）
# ─────────────────────────────────────────────────────────────────────────────
SYSTEMS: List[Dict[str, str]] = [
    {"name": "Ludilearn", "repo": "DigiDago/moodle-format_ludilearn",
     "status": "已编码（E2，6 个机制）；A4 须升级为双编码", "n_mechanisms": "6"},
    {"name": "Level Up XP", "repo": "danbetcher/moodle-levelup",
     "status": "已编码（E2，11 个机制）；A4 须升级为双编码", "n_mechanisms": "11"},
    {"name": "Habitica（候选，待 clone 复核）", "repo": "HabitRPG/habitica",
     "status": "候选（开源 gamified 任务管理，替换待导师/编码者确认）", "n_mechanisms": "?"},
    {"name": "Khan Academy 练习系统（候选，待 clone 复核）", "repo": "Khan/khan-exercises",
     "status": "候选（mastery/练习系统，替换待导师/编码者确认）", "n_mechanisms": "?"},
]

# 编码字段（与 M2 稿 §6 一致）。有序字段（direction）用加权 κ。
CODEBOOK: List[str] = ["target_construct", "direction", "channel"]
ORDERED_FIELDS: Dict[str, List[str]] = {
    # direction 有序：withdraw < neutral < approach（保守偏置方向）
    "direction": ["withdraw", "neutral", "approach"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Cohen κ（纯标准库）
# ─────────────────────────────────────────────────────────────────────────────
def _marginal(a_labels: List[str], b_labels: List[str]) -> Tuple[Dict[str, float], Dict[str, float], List[str]]:
    cats = sorted(set(a_labels) | set(b_labels))
    n = len(a_labels)
    pa = defaultdict(float)
    pb = defaultdict(float)
    for a, b in zip(a_labels, b_labels):
        pa[a] += 1.0
        pb[b] += 1.0
    for k in pa:
        pa[k] /= n
    for k in pb:
        pb[k] /= n
    return pa, pb, cats


def cohen_kappa(a_labels: List[str], b_labels: List[str]) -> float:
    """简单 Cohen κ（名义字段）。κ = (Po - Pe) / (1 - Pe)。"""
    n = len(a_labels)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a_labels, b_labels) if x == y) / n
    pa, pb, _ = _marginal(a_labels, b_labels)
    pe = sum(pa[c] * pb[c] for c in pa)
    if 1 - pe == 0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def cohen_weighted_kappa(a_labels: List[str], b_labels: List[str],
                         order: List[str]) -> float:
    """线性加权 Cohen κ（有序字段，如 direction）。"""
    n = len(a_labels)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(order)}
    K = max(1, len(order) - 1)

    def _w(x: str, y: str) -> float:
        return 1 - abs(idx.get(x, 0) - idx.get(y, 0)) / K

    # 观测加权一致：逐对实际标签的权重均值
    po_w = sum(_w(x, y) for x, y in zip(a_labels, b_labels)) / n
    # 边际分布（期望加权一致用）
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
# 双编码载入与逐字段 κ
# ─────────────────────────────────────────────────────────────────────────────
def load_coder_csv(path: str) -> Dict[str, Dict[str, str]]:
    """载入一个编码者的 CSV，返回 {item_id: {field: value, 'coder':..., 'source_anchor':...}}。"""
    out: Dict[str, Dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            item_id = row.get("item_id")
            if not item_id:
                continue
            out[item_id] = row
    return out


def compute_field_kappas(a: Dict[str, Dict[str, str]],
                         b: Dict[str, Dict[str, str]]) -> Dict[str, float]:
    """对 CODEBOOK 各字段计算 κ；有序字段用加权 κ。"""
    common = sorted(set(a) & set(b))
    if not common:
        return {f: float("nan") for f in CODEBOOK}
    results: Dict[str, float] = {}
    for field in CODEBOOK:
        la = [a[i].get(field, "") for i in common]
        lb = [b[i].get(field, "") for i in common]
        if field in ORDERED_FIELDS:
            results[field] = cohen_weighted_kappa(la, lb, ORDERED_FIELDS[field])
        else:
            results[field] = cohen_kappa(la, lb)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 自测：合成"两编码者完全一致"数据，跑通 κ=1.0，证明数学正确
# ─────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    print("=" * 70)
    print("A4 骨架自测：合成双编码（两编码者完全一致）→ 期望 κ=1.0")
    print("=" * 70)
    synth = [
        ("M1", "reward", "approach", "notification"),
        ("M2", "nudge", "neutral", "badge"),
        ("M3", "reminder", "withdraw", "notification"),
        ("M4", "reward", "approach", "badge"),
        ("M5", "nudge", "withdraw", "notification"),
    ]
    a = {f"item{i}": {"target_construct": c, "direction": d, "channel": ch}
         for i, (_mid, c, d, ch) in enumerate(synth, 1)}
    b = {k: dict(v) for k, v in a.items()}  # 完全一致
    kappas = compute_field_kappas(a, b)
    ok = True
    for f, k in kappas.items():
        print(f"  κ({f}) = {k:.3f}")
        if abs(k - 1.0) > 1e-9:
            ok = False
    # 制造一处分歧看 κ 下降
    b2 = {k: dict(v) for k, v in a.items()}
    b2["item3"]["direction"] = "approach"  # 与 a 的 withdraw 分歧
    k2 = compute_field_kappas(a, b2)["direction"]
    print(f"  κ(direction, 含 1 处分歧) = {k2:.3f}  （应 < 1.0）")
    print()
    print("⚠️ 以上为骨架数学自测。真实 A4 需要：")
    print("   1) ≥ 4 个外部系统（当前 SYSTEMS 仅 2 已编码 + 2 待补）；")
    print("   2) 两名独立人类编码者就同一批机制实例编码（带 file:line 锚点）；")
    print("   3) 用 --coder-a / --coder-b 载入真实 CSV 复算各字段 κ。")
    print("结论:", "SELF_TEST PASS" if ok else "SELF_TEST FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="A4 外部系统双编码 Cohen κ 骨架")
    ap.add_argument("--coder-a", help="编码者 A 的 CSV 路径")
    ap.add_argument("--coder-b", help="编码者 B 的 CSV 路径")
    args = ap.parse_args()

    if not args.coder_a or not args.coder_b:
        return _self_test()

    a = load_coder_csv(args.coder_a)
    b = load_coder_csv(args.coder_b)
    kappas = compute_field_kappas(a, b)
    common = len(set(a) & set(b))
    print(f"双编码项目数（交集）: {common}")
    print("逐字段 Cohen κ:")
    for f, k in kappas.items():
        kind = "weighted" if f in ORDERED_FIELDS else "simple"
        print(f"  {f} ({kind}): {k:.3f}")
    # 报告阈值提示（经验：κ ≥ 0.61 实质一致，0.41–0.60 中等，<0.40 较差）
    weak = [f for f, k in kappas.items() if k != k or k < 0.41]
    if weak:
        print(f"⚠ 以下字段 κ < 0.41（信度不足，须复核编码方案或重编码）：{weak}")
    else:
        print("✓ 所有字段 κ ≥ 0.41（达到可报告信度门槛）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError as exc:
        print(f"[A4] 文件缺失：{exc}", file=sys.stderr)
        sys.exit(2)
