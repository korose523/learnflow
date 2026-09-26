#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A4 双编码 κ —— 33 项 / 4 系统口径（v3）。

与 v2 的区别：
  1. 以 `a4_items_all.csv`（33 实例 / 4 系统）为**题项全集**做覆盖检查：
     缺项、超项、系统名不一致都会报出来，绝不静默丢弃。
  2. **闭集校验**：任一编码值不在 §3.1 闭集内即报错并列出（v2 允许任意中文词，
     正是它把 κ 压到 0.346/0.452 的结构性原因）。
  3. 除总体 κ 外，**分系统报告 κ**（A4 的外推性论证需要按系统看，而非只看汇总）。
  4. `--fallback-b`：当 coderB 新卷缺少某些旧题时，可从旧卷补齐（**必须显式指定**，
     并在输出中逐项记录来源，避免悄悄混用两轮数据）。

诚实纪律（不变）：两列均为人类编码；脚本只做对齐 + 数学，不代任何一方判定语义。

用法：
  python a4_kappa_v3.py --coder-a a4_coderA_survey_v2.csv --coder-b a4_coderB_survey_v2.csv
  python a4_kappa_v3.py --selftest        # 用 17 项旧数据复现 0.778/0.595/0.935
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from external_coding_kappa import (  # noqa: E402
    cohen_kappa, cohen_weighted_kappa, ORDERED_FIELDS,
)

UNIVERSE = os.path.join(HERE, "a4_items_all.csv")
FIELDS = ["target_construct", "direction", "channel"]

CLOSED = {
    "target_construct": {
        "IDENTITY_AUTONOMY", "ACHIEVEMENT", "SOCIAL",
        "ENGAGEMENT", "TEMPORAL", "COMPLIANCE",
    },
    "direction": {"withdraw", "neutral", "approach"},
    "channel": {
        "VISUAL_CUSTOMIZATION", "BADGE", "PROGRESS_BAR", "LEADERBOARD",
        "SCORE_PANEL", "TIMER", "CHEATGUARD", "GROUPING", "LEVEL_INFO",
        "NOTIFICATION", "RATE_LIMIT", "RULE_ENGINE", "XP_STATE",
    },
}


def read_csv(path: str) -> Tuple[List[dict], str]:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            text = raw.decode(enc)
            rows = list(csv.DictReader(text.splitlines()))
            if rows and None in rows[0]:
                raise RuntimeError("%s 含多余列（字段内逗号未转义）" % path)
            return rows, enc
        except UnicodeDecodeError:
            continue
    raise SystemExit("[A4] 无法识别编码: %s" % path)


def to_map(rows: List[dict], tag: str) -> Dict[str, dict]:
    out = {}
    for r in rows:
        iid = (r.get("item_id") or "").strip()
        if not iid:
            continue
        if iid in out:
            raise SystemExit("[A4] %s 中 item_id 重复: %s" % (tag, iid))
        out[iid] = r
    return out


def load_universe(path: str) -> Dict[str, str]:
    """item_id -> system（题项全集）。"""
    if not os.path.exists(path):
        return {}
    rows, _ = read_csv(path)
    return {r["item_id"]: r["system"] for r in rows}


def verdict(k: float) -> str:
    if k != k:
        return "N/A"
    if k >= 0.61:
        return "良好(>=0.61)"
    if k >= 0.41:
        return "可接受(0.41-0.60)"
    return "不足(<0.40)"


def kappa_for(ids: List[str], A: Dict[str, dict], B: Dict[str, dict]) -> Dict[str, float]:
    out = {}
    for fld in FIELDS:
        la = [(A[i].get(fld) or "").strip() for i in ids]
        lb = [(B[i].get(fld) or "").strip() for i in ids]
        out[fld] = (cohen_weighted_kappa(la, lb, ORDERED_FIELDS[fld])
                    if fld in ORDERED_FIELDS else cohen_kappa(la, lb))
    return out


def check_closed(A: Dict[str, dict], B: Dict[str, dict], ids: List[str]) -> List[str]:
    bad = []
    for iid in ids:
        for src, M in (("coderA", A), ("coderB", B)):
            for fld in FIELDS:
                v = (M[iid].get(fld) or "").strip()
                if not v:
                    bad.append("%s/%s/%s: 空值" % (src, iid, fld))
                elif v not in CLOSED[fld]:
                    bad.append("%s/%s/%s: 非闭集值 %r" % (src, iid, fld, v))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder-a", default=os.path.join(HERE, "a4_coderA_survey_v2.csv"))
    ap.add_argument("--coder-b", default=os.path.join(HERE, "a4_coderB_survey_v2.csv"))
    ap.add_argument("--fallback-b", default="",
                    help="coderB 旧卷路径；仅用于补齐新卷缺失的题项（须显式指定）")
    ap.add_argument("--selftest", action="store_true",
                    help="用 17 项闭集旧数据复现 0.778/0.595/0.935")
    args = ap.parse_args()

    if args.selftest:
        args.coder_a = os.path.join(HERE, "a4_coderA_closed.csv")
        args.coder_b = os.path.join(HERE, "a4_coderB_survey.csv")

    uni = load_universe(UNIVERSE)
    a_rows, enc_a = read_csv(args.coder_a)
    b_rows, enc_b = read_csv(args.coder_b)
    A, B = to_map(a_rows, "coderA"), to_map(b_rows, "coderB")

    print("coderA: %s (%s, %d 项)" % (os.path.basename(args.coder_a), enc_a, len(A)))
    print("coderB: %s (%s, %d 项)" % (os.path.basename(args.coder_b), enc_b, len(B)))

    filled = []
    if args.fallback_b:
        fb_rows, _ = read_csv(args.fallback_b)
        FB = to_map(fb_rows, "fallback")
        for iid, row in FB.items():
            if iid not in B:
                B[iid] = row
                filled.append(iid)
        print("从旧卷补齐 %d 项: %s" % (len(filled), sorted(filled)))

    if uni:
        missing_a = sorted(set(uni) - set(A))
        missing_b = sorted(set(uni) - set(B))
        extra = sorted((set(A) | set(B)) - set(uni))
        print("题项全集 %d 项；coderA 缺 %d、coderB 缺 %d、越界 %d"
              % (len(uni), len(missing_a), len(missing_b), len(extra)))
        if missing_a:
            print("  coderA 缺: %s" % missing_a)
        if missing_b:
            print("  coderB 缺: %s" % missing_b)
        if extra:
            print("  越界项: %s" % extra)
        sysmap = {}
        for iid, s in uni.items():
            sysmap[iid] = s
        for iid in set(A) | set(B):
            if iid in uni:
                for M, tag in ((A, "coderA"), (B, "coderB")):
                    if iid in M and (M[iid].get("system") or "").strip() \
                            and M[iid]["system"].strip() != uni[iid]:
                        print("  ⚠ %s 的 %s 系统名 %r != 全集 %r"
                              % (tag, iid, M[iid]["system"], uni[iid]))
    else:
        sysmap = {i: (A.get(i, {}).get("system") or B.get(i, {}).get("system") or "")
                  for i in set(A) | set(B)}
        print("（未找到题项全集 %s，跳过覆盖检查）" % UNIVERSE)

    common = sorted(set(A) & set(B))
    print("可比项: %d\n" % len(common))
    if not common:
        print("无可比项，终止。")
        return 1

    bad = check_closed(A, B, common)
    if bad:
        print("⚠ 闭集校验失败 %d 处：" % len(bad))
        for x in bad[:30]:
            print("   " + x)
        print("  （闭集外的取值会让 κ 失去意义，须回填为 §3.1 闭集码后重算）")
    else:
        print("闭集校验: 全部通过（%d 项 × 3 字段 × 2 编码者）" % len(common))

    overall = kappa_for(common, A, B)
    print("\n【总体 κ】(n=%d)" % len(common))
    print("%-18s%10s   %s" % ("字段", "κ", "判定"))
    print("-" * 52)
    for fld in FIELDS:
        k = overall[fld]
        kind = "加权" if fld in ORDERED_FIELDS else "简单"
        print("%-18s%10.3f   %s (%s)" % (fld, k, verdict(k), kind))

    by_sys = defaultdict(list)
    for iid in common:
        by_sys[sysmap.get(iid, "?")].append(iid)
    print("\n【分系统 κ】")
    print("%-14s%6s %10s %10s %10s" % ("系统", "n", "construct", "direction", "channel"))
    print("-" * 56)
    for s in sorted(by_sys):
        ids = sorted(by_sys[s])
        ks = kappa_for(ids, A, B)
        print("%-14s%6d %10.3f %10.3f %10.3f" % (
            s, len(ids), ks["target_construct"], ks["direction"], ks["channel"]))

    print("\n【逐项分歧】（仅列不一致项）")
    n_dis = 0
    for iid in common:
        diffs = [f for f in FIELDS
                 if (A[iid].get(f) or "").strip() != (B[iid].get(f) or "").strip()]
        if not diffs:
            continue
        n_dis += 1
        print("  [%s] %s" % (iid, sysmap.get(iid, "?")))
        for f in diffs:
            print("      %-16s A=%-22s B=%s" % (
                f, (A[iid].get(f) or "").strip(), (B[iid].get(f) or "").strip()))
    print("  一致 %d / %d，分歧 %d" % (len(common) - n_dis, len(common), n_dis))

    n_all = sum(1 for i in common
                if all((A[i].get(f) or "").strip() == (B[i].get(f) or "").strip()
                       for f in FIELDS))
    print("三字段全一致项: %d/%d" % (n_all, len(common)))

    if args.selftest:
        exp = {"target_construct": 0.778, "direction": 0.595, "channel": 0.935}
        print("\n【自检】与已知 17 项闭集值比对：")
        ok = True
        for f, v in exp.items():
            got = overall[f]
            same = abs(got - v) < 0.001
            ok = ok and same
            print("  %-18s 期望 %.3f  实得 %.3f  %s" % (f, v, got, "OK" if same else "MISMATCH"))
        print("  自检%s" % ("通过" if ok else "失败"))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
