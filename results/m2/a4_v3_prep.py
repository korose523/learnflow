"""A4 v3 准备：生成 coderB v3 重编码模板 + coderA channel 归一化对照表 + 闭集归一化后的预期 κ。

设计要点（诚实纪律）：
  - v3 模板 **不展示 coderA 的 channel 值**，保证 coderB 重编码的独立性（v2 曾因选项词间接暴露 A 标签而有瑕疵）。
  - channel 归一化映射为**纯同义归并非语义重判**（头像定制/头像→同一闭集码），对双方对称适用。
  - 归一化映射以"提议"形式出给 coderA 复核；预期 κ 仅为**投影**，须双方确认后方可作为最终值。
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from external_coding_kappa import cohen_kappa  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
A_PATH = os.path.join(HERE, "a4_coderA.csv")
B_PATH = os.path.join(HERE, "a4_coderB_v2.csv")

# §3.1.2 闭集 13 类 channel（与 A4 方案文档一致）
CHANNEL_CLOSED = [
    "VISUAL_CUSTOMIZATION", "BADGE", "PROGRESS_BAR", "LEADERBOARD", "SCORE_PANEL",
    "TIMER", "CHEATGUARD", "GROUPING", "LEVEL_INFO", "NOTIFICATION",
    "RATE_LIMIT", "RULE_ENGINE", "XP_STATE",
]

# coderA 的 channel 原标签 → 提议闭集码（同义归并，供 coderA 复核）
MAP_A = {
    "头像定制": "VISUAL_CUSTOMIZATION",
    "徽章图": "BADGE",
    "进度条": "PROGRESS_BAR",
    "排行榜": "LEADERBOARD",
    "数值面板": "SCORE_PANEL",
    "计时器+扣分": "TIMER",
    "徽章": "BADGE",
    "防作弊拦截": "CHEATGUARD",
    "分组": "GROUPING",
    "进度+等级": "LEVEL_INFO",
    "弹窗通知": "NOTIFICATION",
    "促销横幅": "NOTIFICATION",
    "名次": "LEADERBOARD",
    "限流窗口": "RATE_LIMIT",
    "规则引擎": "RULE_ENGINE",
    "数值": "SCORE_PANEL",  # ⚠️ 歧义：亦可读作 XP_STATE，须 coderA 裁定
}

# coderB v2 的 channel 原标签 → 闭集码（多值格强制收敛为单一码）
MAP_B = {
    "头像": "VISUAL_CUSTOMIZATION",
    "徽章": "BADGE",
    "进度": "PROGRESS_BAR",
    "排行榜": "LEADERBOARD",
    "积分": "SCORE_PANEL",
    "计时器": "TIMER",
    "防作弊拦截": "CHEATGUARD",
    "分组": "GROUPING",
    "课程排行榜": "LEADERBOARD",
    "等级 / 经验信息": "LEVEL_INFO",   # 多值 → 强制收敛
    "升级弹窗": "NOTIFICATION",
    "促销横幅": "NOTIFICATION",
    "名次 / 排行": "LEADERBOARD",      # 多值 → 强制收敛
    "限流窗口": "RATE_LIMIT",
    "规则引擎": "RULE_ENGINE",
    "经验状态": "XP_STATE",
}


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["item_id"]: r for r in csv.DictReader(f)}


def main() -> int:
    A, B = load(A_PATH), load(B_PATH)
    common = sorted(set(A) & set(B))

    # ---- 1) coderB v3 模板（channel 留空；不展示 coderA channel，保证独立） ----
    v3 = os.path.join(HERE, "a4_coderB_v3_template.csv")
    with open(v3, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "item_id", "target_construct", "direction",
                    "channel", "coder", "source_anchor"])
        for iid in common:
            b = B[iid]
            w.writerow([b.get("system", ""), iid,
                        b.get("target_construct", ""), b.get("direction", ""),
                        "", "coderB", b.get("source_anchor", "")])

    # ---- 2) coderA channel 归一化对照表（供 coderA 复核） ----
    norm = os.path.join(HERE, "a4_coderA_channel_norm.csv")
    with open(norm, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "system", "coderA_channel_raw",
                    "proposed_closed_code", "coderA_confirmed_code", "note"])
        for iid in common:
            raw = A[iid].get("channel", "")
            code = MAP_A.get(raw, "")
            note = "⚠️歧义：数值 亦可读作 XP_STATE，须裁定" if raw == "数值" else ""
            w.writerow([iid, A[iid].get("system", ""), raw, code, "", note])

    # ---- 3) 闭集归一化后的预期 channel κ（投影，须双方确认） ----
    la, lb, rows = [], [], []
    for iid in common:
        ra, rb = A[iid].get("channel", ""), B[iid].get("channel", "")
        ca, cb = MAP_A.get(ra, "?"), MAP_B.get(rb, "?")
        la.append(ca)
        lb.append(cb)
        rows.append((iid, ra, ca, rb, cb, "✓" if ca == cb else "✗"))

    k_proj = cohen_kappa(la, lb)
    n_agree = sum(1 for r in rows if r[5] == "✓")

    print("=" * 78)
    print("A4 v3 准备完成")
    print("=" * 78)
    print(f"[1] coderB v3 模板 -> {os.path.basename(v3)}")
    print("    (target_construct/direction 沿用 v2 已定值；channel 留空待填；未展示 coderA channel)")
    print(f"[2] coderA channel 归一化对照 -> {os.path.basename(norm)}")
    print("    (coderA 原标签 → 提议闭集码，留 confirm 列供复核)")
    print()
    print("[3] 闭集归一化后 channel 预期 κ（投影，须双方确认）")
    print(f"    一致项 {n_agree}/{len(rows)}   κ(channel) ≈ {k_proj:.3f}")
    print()
    print("逐项（A原标签→码 vs B原标签→码）：")
    for iid, ra, ca, rb, cb, m in rows:
        mark = "" if m == "✓" else "   <-- 残余分歧"
        print(f"  [{iid:<7}] {m}  A:{ra:<12}->{ca:<22} B:{rb:<14}->{cb:<22}{mark}")
    print()
    print("闭集 13 类 channel：")
    print("  " + " · ".join(CHANNEL_CLOSED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
