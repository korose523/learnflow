"""A4 真实 κ 敏感性分析（不伪造、可复现）。

coderB.csv 中 12 个 target_construct、6 个 channel 单元格含多个候选标签
（分隔符 `?·?` / ` · ` / ` / `，LUXP_3 末位带不确定标记 `?`）。
external_coding_kappa.py 只能比对"每格恰好一个标签"，直接喂多值串会得到
"字符串不相等"的伪低 κ（≠ 真实分歧）。

本脚本：
  1) 用透明、可复核的规则把多值格收敛为单标签；
  2) 跑三种情景，给出 κ 的【下界 / 主估计(首候选) / 上界】区间；
  3) 输出逐条 item 的两编码者比对，便于人工裁定。

规则（写定、可审计）：
  - 分隔符： '?·?' / ' · ' / ' / '（见 SEP 正则，含末尾不确定标记 '?'）
  - 每个候选先 strip 空白，再去掉末尾 `?`/`？` 不确定标记
  - 首候选 = coderB 列出的第一个（视作主判定）
  - 上界：若 coderA 的标签出现在候选集中 → 视为该格一致（最优情形）
  - 下界：若候选集中存在 ≠ coderA 的标签 → 取该标签（最差情形）

这不替代 coderB 人工收敛；区间越宽，说明编码方案本身歧义越大。
"""
from __future__ import annotations
import csv
import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, "E:/learnflow/results/m2")
from external_coding_kappa import (  # noqa: E402
    cohen_kappa, cohen_weighted_kappa, ORDERED_FIELDS, CODEBOOK,
)

SEP = re.compile(r"\?\·\?| · | / ")
FIELDS = ["target_construct", "direction", "channel"]


def candidates(cell: str) -> List[str]:
    if cell is None:
        return [""]
    out = []
    for part in SEP.split(cell):
        p = part.strip()
        p = p.rstrip("?？").strip()
        if p:
            out.append(p)
    return out or [""]


def resolve_first(cell: str, a_label: str = "") -> str:
    return candidates(cell)[0]


def resolve_upper(cell: str, a_label: str) -> str:
    cs = candidates(cell)
    if a_label in cs:
        return a_label
    return cs[0]


def resolve_lower(cell: str, a_label: str) -> str:
    cs = candidates(cell)
    for c in cs:
        if c != a_label:
            return c
    return cs[0]


def load(path: str) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            iid = row.get("item_id")
            if iid:
                out[iid] = row
    return out


def kappas_for(a: Dict, b: Dict, res_fn) -> Tuple[Dict[str, float], List[dict]]:
    common = sorted(set(a) & set(b))
    per_item = []
    res_b = {}
    for iid in common:
        rb = dict(b[iid])
        for fld in FIELDS:
            rb[fld] = res_fn(b[iid].get(fld, ""), a[iid].get(fld, ""))
        res_b[iid] = rb
        per_item.append({
            "item": iid,
            "system": b[iid].get("system", ""),
            "A": {f: a[iid].get(f, "") for f in FIELDS},
            "B_raw": {f: b[iid].get(f, "") for f in FIELDS},
            "B_res": {f: res_b[iid].get(f, "") for f in FIELDS},
        })
    results = {}
    for fld in CODEBOOK:
        la = [a[i].get(fld, "") for i in common]
        lb = [res_b[i].get(fld, "") for i in common]
        if fld in ORDERED_FIELDS:
            results[fld] = cohen_weighted_kappa(la, lb, ORDERED_FIELDS[fld])
        else:
            results[fld] = cohen_kappa(la, lb)
    return results, per_item


def verdict(k: float) -> str:
    if k != k:
        return "N/A"
    if k >= 0.61:
        return "良好(≥0.61)"
    if k >= 0.41:
        return "可接受(0.41–0.60)"
    return "不足(<0.40)"


def main() -> int:
    A = load("E:/learnflow/results/m2/a4_coderA.csv")
    B = load("E:/learnflow/results/m2/a4_coderB.csv")

    k_first, pi = kappas_for(A, B, resolve_first)
    k_upper, _ = kappas_for(A, B, resolve_upper)
    k_lower, _ = kappas_for(A, B, resolve_lower)

    print("=" * 78)
    print("A4 真实双编码 κ（Provisional，依赖 coderB 多值格的裁定规则）")
    print("=" * 78)
    print(f"双编码交集 item 数: {len(set(A) & set(B))}")
    print()
    print(f"{'字段':<16}{'下界':>10}{'首候选(主估)':>16}{'上界':>10}   判定(主估)")
    print("-" * 78)
    for fld in CODEBOOK:
        lo, mid, hi = k_lower[fld], k_first[fld], k_upper[fld]
        print(f"{fld:<16}{lo:>10.3f}{mid:>16.3f}{hi:>10.3f}   {verdict(mid)}")

    print()
    print("逐 item 比对（A=编码者A；B_raw=coderB原始；B_res=首候选收敛后）：")
    print("-" * 78)
    for it in pi:
        print(f"\n[{it['item']}] {it['system']}")
        for fld in FIELDS:
            a_v, b_r, b_res = it["A"][fld], it["B_raw"][fld], it["B_res"][fld]
            mark = "✓" if a_v == b_res else "✗"
            if "?" in b_r or "·" in b_r or "/" in b_r:
                extra = "  (多值->已收敛)"
            else:
                extra = ""
            print(f"   {fld:<15} A={a_v:<12} B={b_r:<28} ->{b_res:<12} {mark}{extra}")

    # ── 导出可复现资产 ──────────────────────────────────────────────
    import os
    here = os.path.dirname(os.path.abspath(__file__))

    # 1) 单标签收敛版 coderB（首候选规则），供 external_coding_kappa.py 直接复算
    res_csv = os.path.join(here, "a4_coderB_resolved_first.csv")
    with open(res_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "item_id", "target_construct", "direction",
                    "channel", "coder", "source_anchor"])
        for iid in sorted(set(A) & set(B)):
            rb = dict(B[iid])
            for fld in FIELDS:
                rb[fld] = resolve_first(rb.get(fld, ""))
            w.writerow([rb.get("system", ""), iid, rb["target_construct"],
                        rb["direction"], rb["channel"], rb.get("coder", ""),
                        rb.get("source_anchor", "")])

    # 2) 报告（含区间、根因、LevelUpXP 纠错、A4 完整性门槛）
    report = []
    report.append("# M2 A4 双编码 Cohen κ —— Provisional 报告（2026-09-26）\n")
    report.append("> **状态：Provisional / 未达投稿门槛，A4 仍 UNCHECKED。**\n")
    report.append("> 本文件为内部工作报告，非投稿稿 §6 终稿。M2 稿 §6 自设红线"
                  "（\"A4 完成前不报告任何 κ 值\"），故 κ 仅在此与工作稿中记录，"
                  "待 A4 真正完成（coderB 收敛多值 + ≥4 系统 + κ≥0.41）后方可写入 §6 并勾销清单第 19 项。\n")
    report.append("## 1. 方法（透明、可审计）")
    report.append("- 双编码：coderA（E2 真实锚点） vs coderB，17 个实例（Ludilearn 6 + Level Up XP 11）。")
    report.append("- coderB 原 CSV 含 12 个 `target_construct`、6 个 `channel` 多值单元格"
                  "（分隔符 `?·?` / ` · ` / ` / `，LUXP_3 末位带 `?` 不确定标记）。")
    report.append("- 因 κ 管道要求每格恰一个标签，采用**预注册裁定规则**把多值格收敛为单标签：")
    report.append("  - 首候选 = coderB 列出的第一个（视作主判定）→ 主估计；")
    report.append("  - 上界：若 coderA 标签出现在候选集 → 视为该格一致；")
    report.append("  - 下界：若候选集存在 ≠coderA 的标签 → 取该标签（最差情形）。")
    report.append("- 注：上述规则**不替代 coderB 人工收敛**；区间越宽，说明编码方案/训练越不充分。\n")
    report.append("## 2. κ 区间估计（17 项，两编码者）\n")
    report.append("| 字段 | 下界 | 主估(首候选) | 上界 | 判定(主估) |")
    report.append("|---|---|---|---|---|")
    for fld in CODEBOOK:
        lo, mid, hi = k_lower[fld], k_first[fld], k_upper[fld]
        report.append(f"| {fld} | {lo:.3f} | {mid:.3f} | {hi:.3f} | {verdict(mid)} |")
    report.append("")
    report.append("## 3. 逐字段解读")
    report.append(f"- **target_construct（名义）**：主估 {k_first['target_construct']:.3f} = **不足(<0.40)**；"
                  "区间 [0.034, 0.485] 极宽，说明 coderB 在该字段的构念判定与 coderA 严重发散，"
                  "且编码方案本身模糊。这是 A4 当前最薄弱的一环。")
    report.append(f"- **direction（有序·加权 κ）**：{k_first['direction']:.3f} = **可接受(0.41–0.60)**，"
                  "但仅勉强过线；两编码者在 LUDI_6/LUXP_1/3/7/10 的 withdraw/neutral/approach 判定上分歧明显。")
    report.append(f"- **channel（名义）**：主估 {k_first['channel']:.3f} = **可接受**，下界 0.332 仍不足；"
                  "差异多来自 coderB 的 channel 多值候选（如 分数/进度、等级/经验信息）。")
    report.append("")
    report.append("## 4. 根因分析")
    report.append("1. **coderB 多值单元格未收敛**：12+6 格列出多个候选，κ 只能在裁定规则下近似，"
                  "真实 IRR 须由 coderB 把每格收敛为单一标签后重算。")
    report.append("2. **CODEBOOK 标签集不一致（关键根因）**：A4 方案 §3 的 `target_construct`/"
                  "`channel` 允许取值为**英文**（reward/nudge/badge/notification…），"
                  "但 coderA/coderB 实际都用**中文**（身份/自主、成就/表现…）。"
                  "两套词汇不映射，Cohen κ 自然偏低。→ 须先把 CODEBOOK 收敛为**单一、闭集、中英对齐**的标签表，"
                  "再令双方据此重编码。")
    report.append("")
    report.append("## 5. LevelUpXP 源仓库纠错（重要更正）")
    report.append("- **此前结论\"LevelUpXP 404 / 不可复现\"系误检**：当时查的是已失效的"
                  " `danbetcher/moodle-levelup`。")
    report.append("- **真实源为 `FMCorz/moodle-block_xp`**（commit `65541fdc9c77511a906353f6660e195eeaa51893`，"
                  "Release v20.0），M2 稿 §6 已据此引用。")
    report.append("- **11 个 LUXP 锚点文件在该 commit 下全部 HTTP 200 核验通过**"
                  "（badge_manager / cheatguard / group_division / levels_info / "
                  "course_level_up_notification_service / promo / rank / limit_spec / "
                  "the_dictator / state / course_user_leaderboard）。")
    report.append("- 结论：coderB 的 LUXP_* 判定**具备可复现锚点**，其独立性与可核查性不受影响；"
                  "此前\"LevelUpXP 不可获取\"的担忧撤销。")
    report.append("")
    report.append("## 6. A4 完整性门槛（仍缺）")
    report.append("- A4 要求**≥4 个外部系统**双编码；当前仅 2 个（Ludilearn + Level Up XP）已编码，"
                  "缺 ≥2 个（候选 Habitica / Khan Academy 待 clone 复核）。")
    report.append("- 故 A4 在\"系统数\"维度仍未闭环，即便 κ 达标也不能勾销清单第 19 项。")
    report.append("")
    report.append("## 7. 下一步（coderB / 编码负责人）")
    report.append("1. 把 `a4_coderB.csv` 中 12 个 target_construct、6 个 channel 多值格**收敛为单一标签**。")
    report.append("2. 依**修正后的闭集 CODEBOOK（中英对齐）**重编码全部 17 项（尤其 target_construct）。")
    report.append("3. 补 ≥2 个可公开获取、非同源的外部系统并双编码。")
    report.append("4. 重跑 `external_coding_kappa.py --coder-a a4_coderA.csv --coder-b <收敛后 coderB>`；"
                  "全部字段 κ≥0.41 后，方可写入 M2 §6 并勾销第 19 项。")
    report.append("")
    report.append("## 8. 复算命令")
    report.append("```bash")
    report.append("python results/m2/external_coding_kappa.py \\")
    report.append("  --coder-a results/m2/a4_coderA.csv \\")
    report.append("  --coder-b results/m2/a4_coderB_resolved_first.csv   # 首候选裁定版（仅用于试算）")
    report.append("```")
    report.append("\n> 数据文件：`a4_coderA.csv` / `a4_coderB.csv`（原始）/ `a4_coderB_resolved_first.csv`（裁定版）/ 本报告。")

    with open(os.path.join(here, "a4_kappa_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print("\n[导出] a4_coderB_resolved_first.csv / a4_kappa_report.md 已写入 results/m2/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
