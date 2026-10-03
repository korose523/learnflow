"""M3 · C 项：≥3 模型族 × ≥3 规模标注矩阵 —— 可复算骨架 + 门禁（待真实多模型评估外部执行）。

方案与 CSV 模板见 `docs/LearnFlow_研究总档.md`；模板 `results/m3/m3_model_scale_matrix.csv`
（列：model_id, family, scale_tier, params_billions, architecture, eval_status, datasets, protocol,
parse_rate, spearman_rho, accuracy, cohen_kappa, reliability_verdict, source_anchor）。

⚠️ 本文件是**矩阵框架骨架**，不代表已完成的实验。C 项需要：
  - ≥ 3 个模型族 × ≥ 3 个参数规模（当前分类法 4 族 × 4 档）的标注矩阵；
  - 每个 EVALUATED 单元格须用**同一批题目（DBE-212 / XES-120）+ 同一套已通过审计的协议
    （E1-A schema 枚举 + 锚定 / E1-B 枚举数组 + BT）**实测，并带题目级配对 bootstrap 95% CI。
  真实多模型评估须外部算力/API 执行，本骨架仅交付分类法 + 标注 schema + 一致性门禁 + 自测。

本骨架提供（纯标准库，审稿人 clone 即跑）：
  - ``MODEL_FAMILIES``（≥3）/ ``SCALE_TIERS``（≥3）分类法；
  - ``load_matrix_csv`` / ``validate_matrix``：校验 ≥3×≥3 覆盖、EVALUATED 单元格必带
    parse_rate + spearman_rho + source_anchor、NOT_EVALUATED 单元格不虚构度量；
  - ``__main__`` 自测：合成矩阵通过 / 族数不足失败 / 字段缺失或误填失败，证明门槛生效。

用法（骨架 + 模板结构校验）：
  python results/m3/verify_m3_matrix.py
用法（真实评估补全 CSV 后）：
  python results/m3/verify_m3_matrix.py --matrix results/m3/m3_model_scale_matrix.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List


HERE = os.path.dirname(os.path.abspath(__file__))
SCHEME_DOC = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "LearnFlow_研究总档.md"))
TEMPLATE_CSV = os.path.join(HERE, "m3_model_scale_matrix.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 模型族 / 规模分类法（审阅要求 ≥3 × ≥3；当前 4 × 4）
# ─────────────────────────────────────────────────────────────────────────────
MODEL_FAMILIES: List[Dict[str, str]] = [
    {"id": "F1", "name": "Qwen 系（Alibaba）", "arch": "dense + MoE"},
    {"id": "F2", "name": "Llama 系（Meta）", "arch": "dense"},
    {"id": "F3", "name": "Mistral / Mixtral 系", "arch": "dense + MoE"},
    {"id": "F4", "name": "DeepSeek 系", "arch": "dense + MoE"},
]
SCALE_TIERS: List[Dict[str, str]] = [
    {"id": "S1", "range": "< 7B", "note": "小模型"},
    {"id": "S2", "range": "7B – 30B", "note": "中模型"},
    {"id": "S3", "range": "30B – 70B", "note": "大模型（qwen36 落此档）"},
    {"id": "S4", "range": "> 70B", "note": "超大模型"},
]

_FAMILY_IDS = {f["id"] for f in MODEL_FAMILIES}
_SCALE_IDS = {s["id"] for s in SCALE_TIERS}


def load_matrix_csv(path: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    with open(path, encoding="utf-8-sig", newline="") as f:  # utf-8-sig 容忍 BOM
        for row in csv.DictReader(f):
            if not row.get("model_id"):
                continue
            out.append(row)
    return out


def validate_matrix(rows: List[Dict[str, str]]) -> List[str]:
    """一致性校验：覆盖 ≥3×≥3、分类法内、EVALUATED 必带字段、NOT_EVALUATED 不虚构。"""
    problems: List[str] = []
    fams = {r["family"] for r in rows if r.get("family")}
    scales = {r["scale_tier"] for r in rows if r.get("scale_tier")}
    for fid in fams:
        if fid.split("_")[0] not in _FAMILY_IDS:
            problems.append(f"单元格 family 不在分类法内：{fid}")
    for sid in scales:
        if sid.split("_")[0] not in _SCALE_IDS:
            problems.append(f"单元格 scale_tier 不在分类法内：{sid}")
    n_eval = 0
    for r in rows:
        status = (r.get("eval_status") or "").strip()
        if status == "EVALUATED":
            n_eval += 1
            for field in ("parse_rate", "spearman_rho", "source_anchor"):
                if not (r.get(field) or "").strip():
                    problems.append(
                        f"EVALUATED 单元格 {r.get('model_id')} 缺必填字段 {field}")
        elif status == "NOT_EVALUATED":
            for field in ("parse_rate", "spearman_rho", "cohen_kappa"):
                if (r.get(field) or "").strip():
                    problems.append(
                        f"NOT_EVALUATED 单元格 {r.get('model_id')} 不应填 {field}（不虚构度量）")
        else:
            problems.append(f"单元格 {r.get('model_id')} eval_status 非法：{status!r}")
    # 覆盖门槛：矩阵触及的族/档各 ≥3
    touched_fam = {r["family"].split("_")[0] for r in rows if r.get("family")}
    touched_scl = {r["scale_tier"].split("_")[0] for r in rows if r.get("scale_tier")}
    if len(touched_fam & _FAMILY_IDS) < 3:
        problems.append(f"矩阵触及模型族数 {len(touched_fam & _FAMILY_IDS)} < 3")
    if len(touched_scl & _SCALE_IDS) < 3:
        problems.append(f"矩阵触及规模档数 {len(touched_scl & _SCALE_IDS)} < 3")
    return problems


# ─────────────────────────────────────────────────────────────────────────────
# 自测
# ─────────────────────────────────────────────────────────────────────────────
def _self_test() -> bool:
    print("=" * 70)
    print("C 项自测：合成矩阵校验逻辑（门槛生效性）")
    print("=" * 70)
    ok = True

    # 1) 合法矩阵：4 族 × 4 档，1 个 EVALUATED + 其余 NOT_EVALUATED
    good = [
        {"model_id": "m1", "family": "F1_Qwen", "scale_tier": "S3_30-70B",
         "eval_status": "EVALUATED", "parse_rate": "1.0", "spearman_rho": "0.2195",
         "source_anchor": "x.json"},
        {"model_id": "m2", "family": "F2_Llama", "scale_tier": "S1_<7B",
         "eval_status": "NOT_EVALUATED", "parse_rate": "", "spearman_rho": "",
         "source_anchor": ""},
        {"model_id": "m3", "family": "F3_Mistral", "scale_tier": "S4_>70B",
         "eval_status": "NOT_EVALUATED", "parse_rate": "", "spearman_rho": "",
         "source_anchor": ""},
        {"model_id": "m4", "family": "F4_DeepSeek", "scale_tier": "S2_7-30B",
         "eval_status": "NOT_EVALUATED", "parse_rate": "", "spearman_rho": "",
         "source_anchor": ""},
    ]
    p1 = validate_matrix(good)
    print(f"  合法矩阵（4 族 × 4 档，1 EVALUATED）：校验问题数 = {len(p1)}（期望 0）")
    if p1:
        ok = False
        for x in p1:
            print(f"    [意外] {x}")

    # 2) 族数不足 → 失败
    few_fam = [
        {"model_id": "m1", "family": "F1_Qwen", "scale_tier": "S1_<7B",
         "eval_status": "EVALUATED", "parse_rate": "1.0", "spearman_rho": "0.2",
         "source_anchor": "x"},
        {"model_id": "m2", "family": "F2_Llama", "scale_tier": "S2_7-30B",
         "eval_status": "NOT_EVALUATED", "parse_rate": "", "spearman_rho": "",
         "source_anchor": ""},
    ]
    p2 = validate_matrix(few_fam)
    print(f"  族数=2 矩阵：校验问题数 = {len(p2)}（期望 ≥1：族数门槛生效）")
    if not p2:
        ok = False
        print("    [意外] 族数不足未触发失败")

    # 3) EVALUATED 缺 spearman_rho → 失败
    miss = [dict(good[0], spearman_rho="")]
    p3 = validate_matrix(miss)
    print(f"  EVALUATED 缺 spearman_rho：校验问题数 = {len(p3)}（期望 ≥1）")
    if not p3:
        ok = False
        print("    [意外] 缺字段未触发失败")

    # 4) NOT_EVALUATED 误填 spearman_rho → 失败
    fake = [dict(good[1], spearman_rho="0.5")]
    p4 = validate_matrix(fake)
    print(f"  NOT_EVALUATED 误填 spearman_rho：校验问题数 = {len(p4)}（期望 ≥1：不虚构度量）")
    if not p4:
        ok = False
        print("    [意外] 误填未触发失败")

    print("  C 项自测:", "PASS" if ok else "FAIL")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
def _structural_checks() -> List[str]:
    problems: List[str] = []
    if len(MODEL_FAMILIES) < 3:
        problems.append(f"MODEL_FAMILIES={len(MODEL_FAMILIES)} < 3")
    if len(SCALE_TIERS) < 3:
        problems.append(f"SCALE_TIERS={len(SCALE_TIERS)} < 3")
    if not os.path.isfile(SCHEME_DOC):
        problems.append(f"方案文档缺失：{SCHEME_DOC}")
    if not os.path.isfile(TEMPLATE_CSV):
        problems.append(f"CSV 模板缺失：{TEMPLATE_CSV}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="M3 C 项 ≥3 模型族×≥3 规模标注矩阵门禁")
    ap.add_argument("--matrix", help="矩阵 CSV 路径（默认用模板）")
    args = ap.parse_args()

    sp = _structural_checks()
    if sp:
        for p in sp:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1
    print(f"结构层: PASS（模型族 {len(MODEL_FAMILIES)} ≥3；规模档 {len(SCALE_TIERS)} ≥3；"
          f"方案文档与模板存在）")

    if not _self_test():
        print("结论: FAIL   退出码 1")
        return 1
    print("自测层: PASS（覆盖门槛 / 字段必填 / 不虚构度量 逻辑均生效）")

    path = args.matrix or TEMPLATE_CSV
    try:
        rows = load_matrix_csv(path)
    except OSError as exc:
        print(f"[FAIL] 矩阵 CSV 读取失败：{exc}")
        print("结论: FAIL   退出码 1")
        return 1
    rp = validate_matrix(rows)
    n_eval = sum(1 for r in rows if (r.get("eval_status") or "").strip() == "EVALUATED")
    if rp:
        for p in rp:
            print(f"[FAIL] {p}")
        print("结论: FAIL   退出码 1")
        return 1
    fams = {r["family"].split("_")[0] for r in rows if r.get("family")} & _FAMILY_IDS
    scales = {r["scale_tier"].split("_")[0] for r in rows if r.get("scale_tier")} & _SCALE_IDS
    print(f"矩阵校验: PASS（单元格 {len(rows)}；触及 {len(fams)} 族 × {len(scales)} 档；"
          f"EVALUATED={n_eval}）")
    if n_eval < len(fams) * len(scales):
        print(f"⚠ 真实多模型评估未全覆盖：当前 {n_eval} 单元格为 EVALUATED，"
              f"距 {len(fams)}×{len(scales)} 全覆盖仍差外部多模型评估（状态 🟡）。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError as exc:
        print(f"[M3] 文件缺失：{exc}", file=sys.stderr)
        sys.exit(2)
