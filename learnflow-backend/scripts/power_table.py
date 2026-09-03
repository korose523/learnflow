"""每类别功效表 (GAP-2)：对 8 个治理字母，在若干 (mde, icc) 组合下打印 required_n_per_group。

功效数值与类别内容无关（只随 mde / icc / DEFF 变化），因此各字母行相同；
表的价值在于把「整群随机的 DEFF 惩罚」与「各类别所需样本量」并列呈现，
供消融方案取舍。计算复用 experiment_power.plan_experiment。

用法:
    python scripts/power_table.py
    python scripts/power_table.py --mdes 0.3,0.4 --iccs 0.0,0.05 --cluster-size 30
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.experiment_power import plan_experiment


# 8 个治理字母（仅用于表头标识；功效计算与类别内容无关）
LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def main() -> int:
    ap = argparse.ArgumentParser(description="LearnFlow 每类别功效表")
    ap.add_argument("--mdes", default="0.2,0.3,0.4,0.5")
    ap.add_argument("--iccs", default="0.0,0.05,0.10")
    ap.add_argument("--cluster-size", type=int, default=30)
    ap.add_argument("--power", type=float, default=0.80)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    mdes = [float(x) for x in args.mdes.split(",") if x.strip()]
    iccs = [float(x) for x in args.iccs.split(",") if x.strip()]

    print(f"# required_n_per_group  (cluster_size={args.cluster_size}, "
          f"power={args.power}, alpha={args.alpha})")
    print("# 字母仅标识 8 个治理组；功效数值对所有类别一致（取决于 mde/icc/DEFF）")
    for letter in LETTERS:
        print(f"\n## 类别 {letter}")
        print("  mde | " + " | ".join(f"icc={icc}" for icc in iccs))
        for mde in mdes:
            row = f"  {mde:>3} | " + " | ".join(
                str(plan_experiment(
                    effect_size=mde, metric_type="continuous",
                    alpha=args.alpha, power=args.power,
                    cluster_size=args.cluster_size, icc=icc,
                ).required_n_per_group)
                for icc in iccs
            )
            print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
