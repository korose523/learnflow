"""机制目录种子脚本 —— 从 mechanism_registry 导出 53 机制台账 (§2.4)

用途:
    1. 生成 artifacts/mechanism_catalog.json，作为论文附录「机制台账」的可复算源；
    2. 与治理文档 §2.4 清单交叉校验（ID 集合一致），供 CI 复算；
    3. 为未来 SQLExperimentStore 的 seed 提供结构化输入。

用法:
    python scripts/seed_mechanism_catalog.py [--out artifacts/mechanism_catalog.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.mechanism_registry import all_mechanisms, count, registry_fingerprint


def build_catalog() -> dict:
    rows = []
    for spec in all_mechanisms():
        rows.append({
            "id": spec.id,
            "key": spec.key,
            "name_zh": spec.name_zh,
            "name_en": spec.name_en,
            "stage": spec.stage,
            "category": spec.category,
            "theory_ref": spec.theory_ref,
            "impl_ref": spec.impl_ref,
            "disposition": spec.disposition,
            "maturity": spec.maturity,
            "notes": spec.notes,
        })
    return {
        "count": count(),
        "registry_fingerprint": registry_fingerprint(),
        "mechanisms": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="导出机制目录台账")
    ap.add_argument("--out",
                    default=os.path.join(ROOT, "artifacts", "mechanism_catalog.json"))
    args = ap.parse_args()

    catalog = build_catalog()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"机制目录已导出: {args.out}  (count={catalog['count']}, "
          f"fingerprint={catalog['registry_fingerprint']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
