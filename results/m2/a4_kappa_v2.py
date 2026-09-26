"""A4 双编码 κ —— 通用复算脚本（coderA vs 任意 coderB 版本，人类编码，AI 不代判）。

用法：
  python a4_kappa_v2.py                                  # 默认 coderA vs a4_coderB_v2_template.csv
  python a4_kappa_v2.py --coder-b results/m2/xxx.csv     # 指定 coderB 版本

设计要点（诚实纪律）：
  - 两列均为人类编码，脚本只做「对齐 + 多值收敛 + 数学」，不替任何一方判定语义。
  - 自动识别编码（utf-8 / gbk），避免外部编辑器存盘导致的乱码。
  - 多值单元格（分隔符 `?·?` / ` · ` / ` / ` + 末位 `?`）按预注册规则收敛，
    并给出 κ 的【下界 / 首候选主估 / 上界】区间，绝不伪造单一确定值。
  - 同时输出逐 item 比对表，便于人工核查分歧（尤其独立性可疑处）。
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from external_coding_kappa import (  # noqa: E402
    cohen_kappa, cohen_weighted_kappa, ORDERED_FIELDS, CODEBOOK,
)

SEP = re.compile(r"\?\·\?| · | / ")
FIELDS = ["target_construct", "direction", "channel"]


def read_rows(path: str) -> List[dict]:
    """自动识别编码读取 CSV。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            text = raw.decode(enc)
            return list(csv.DictReader(text.splitlines())), enc
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"[A4] 无法识别编码: {path}")


def candidates(cell: str) -> List[str]:
    if not cell:
        return [""]
    out = []
    for part in SEP.split(cell):
        p = part.strip().rstrip("?？").strip()
        if p:
            out.append(p)
    return out or [""]


def resolve_first(cell: str, _a: str = "") -> str:
    return candidates(cell)[0]


def resolve_upper(cell: str, a: str) -> str:
    cs = candidates(cell)
    return a if a in cs else cs[0]


def resolve_lower(cell: str, a: str) -> str:
    cs = candidates(cell)
    for c in cs:
        if c != a:
            return c
    return cs[0]


def verdict(k: float) -> str:
    if k != k:
        return "N/A"
    if k >= 0.61:
        return "良好(≥0.61)"
    if k >= 0.41:
        return "可接受(0.41–0.60)"
    return "不足(<0.40)"


def to_map(rows: List[dict]) -> Dict[str, dict]:
    return {r["item_id"]: r for r in rows if r.get("item_id")}


def kappa_interval(A: Dict[str, dict], B: Dict[str, dict]):
    common = sorted(set(A) & set(B))
    out, per_item = {}, []
    for fn in (resolve_lower, resolve_first, resolve_upper):
        resB = {}
        for iid in common:
            rb = dict(B[iid])
            for fld in FIELDS:
                rb[fld] = fn(B[iid].get(fld, ""), A[iid].get(fld, ""))
            resB[iid] = rb
        kk = {}
        for fld in CODEBOOK:
            la = [A[i].get(fld, "") for i in common]
            lb = [resB[i].get(fld, "") for i in common]
            kk[fld] = (cohen_weighted_kappa(la, lb, ORDERED_FIELDS[fld])
                       if fld in ORDERED_FIELDS else cohen_kappa(la, lb))
        out[fn.__name__] = kk
        if fn is resolve_first:
            for iid in common:
                per_item.append({
                    "item": iid,
                    "system": B[iid].get("system", ""),
                    "A": {f: A[iid].get(f, "") for f in FIELDS},
                    "B_raw": {f: B[iid].get(f, "") for f in FIELDS},
                    "B_res": {f: resB[iid].get(f, "") for f in FIELDS},
                })
    return out, per_item, common


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder-a", default="E:/learnflow/results/m2/a4_coderA.csv")
    ap.add_argument("--coder-b", default="E:/learnflow/results/m2/a4_coderB_v2_template.csv")
    args = ap.parse_args()

    a_rows, enc_a = read_rows(args.coder_a)
    b_rows, enc_b = read_rows(args.coder_b)
    A, B = to_map(a_rows), to_map(b_rows)
    print(f"coderA: {os.path.basename(args.coder_a)} ({enc_a}, {len(A)} 项)")
    print(f"coderB: {os.path.basename(args.coder_b)} ({enc_b}, {len(B)} 项)")
    print(f"交集: {len(set(A) & set(B))} 项\n")

    ks, per_item, common = kappa_interval(A, B)

    print(f"{'字段':<18}{'下界':>9}{'首候选(主估)':>15}{'上界':>9}   判定(主估)")
    print("-" * 72)
    for fld in CODEBOOK:
        lo, mid, hi = ks["resolve_lower"][fld], ks["resolve_first"][fld], ks["resolve_upper"][fld]
        print(f"{fld:<18}{lo:>9.3f}{mid:>15.3f}{hi:>9.3f}   {verdict(mid)}")

    # 多值格统计
    mv = defaultdict(list)
    for iid in common:
        for fld in FIELDS:
            if len(candidates(B[iid].get(fld, ""))) > 1:
                mv[fld].append(iid)
    print("\n多值单元格（须 coderB 收敛为单标签）：")
    for fld, ids in mv.items():
        print(f"  {fld}: {len(ids)} 格 -> {ids}")
    if not mv:
        print("  无（全部单值）")

    print("\n逐 item 比对：")
    print("-" * 72)
    for it in per_item:
        marks = "".join("✓" if it["A"][f] == it["B_res"][f] else "✗" for f in FIELDS)
        print(f"[{it['item']}] {it['system']:<12} {marks}  (construct/direction/channel)")
        for fld, m in zip(FIELDS, marks):
            flag = " [多值→收敛]" if len(candidates(it["B_raw"][fld])) > 1 else ""
            if m == "✗" or flag:
                print(f"    {fld:<15} A={it['A'][fld]:<14} B={it['B_raw'][fld]}{flag}")

    n_agree = sum(1 for it in per_item
                  if all(it["A"][f] == it["B_res"][f] for f in FIELDS))
    print(f"\n三字段全一致项: {n_agree}/{len(per_item)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
