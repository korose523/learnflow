# -*- coding: utf-8 -*-
"""compare_cross_engine.py —— 同基座模型跨推理引擎复现性对比（M3 S3 格稳健性检验）
================================================================================

背景
--------------------------------------------------------------------------------
M3 模型-规模矩阵的 F1_Qwen S3_30-70B 格原有两条独立证据可对照：
    ollama 侧：qwen36:latest（Qwen3.6-35B-A3B，IQ3_S 量化，ollama 约束解码，CPU 推理）
    colibri 侧：qwen3.6-colibri（同基座，int4-gs64 量化，prefill 续写等效约束，CUDA 推理）
两者用**同一批题目（212）、同一协议（E1-A/E1-B 逐字复用）、同一种子（20260912）、
同一批构成**，唯一变量是推理栈（引擎 + 量化 + 解码通道 + 硬件）。若两引擎的
ρ 及题目级标签高度一致，则矩阵结论不依赖推理后端——这是对整个 M3 方法学
（LLM-as-judge 难度标注）的一次系统级稳健性检验。

方法
--------------------------------------------------------------------------------
[E1-A] 题目级（212 题，同 key 对齐）：
    - 两引擎标签的原始一致率 + Cohen's κ（3 级）
    - 引擎间 Spearman（标签向量互相关）
    - 各自 vs 专家的 Spearman（并排报告，含各自动态的 CI 引用自汇总 JSON）
    - 3×3 混淆表（引擎 A 标签 × 引擎 B 标签）
[E1-B] 两两约束级（BT 输入）：
    - 两引擎各自从排序记录重建 wins 集，对比**共同题目对**上的方向一致率
    - 各自 BT 分数的 Spearman（共同题目）

输出
--------------------------------------------------------------------------------
    results/m3/cross_engine_compare.json（全部数字）
    控制台表
退出码：0 正常；2 输入缺失/对齐不足（不硬凑结论）
"""
from __future__ import annotations

import json
import sys
import importlib.util
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
OLD_JSONL = HERE / "local_matrix.jsonl"          # ollama 侧（旧机器产物，随仓库迁移）
NEW_JSONL = HERE / "local_matrix_colibri.jsonl"  # colibri 侧（本机产物）
OLD_SUM = HERE / "local_matrix.json"             # ollama 侧汇总（ρ/CI 权威值）
NEW_SUM = HERE / "local_matrix_colibri.json"     # colibri 侧汇总
OUT_JSON = HERE / "cross_engine_compare.json"

OLD_MODEL = "qwen36:latest"
NEW_MODEL = "qwen3.6-colibri"

spec = importlib.util.spec_from_file_location("adapter", HERE / "local_matrix_colibri.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)
e1 = ad.e1   # 复用 _constraints / _fit_bt / 统计（scipy）


def load_last(jsonl: Path, model: str, cond: str):
    last = {}
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("model") == model and r.get("cond") == cond:
                last[r.get("key")] = r
    return last


def main() -> int:
    for p in (OLD_JSONL, NEW_JSONL, OLD_SUM, NEW_SUM):
        if not p.is_file():
            print(f"[fatal] 缺少产物：{p}", file=sys.stderr)
            return 2

    old_sum = json.loads(OLD_SUM.read_text(encoding="utf-8"))
    new_sum = json.loads(NEW_SUM.read_text(encoding="utf-8"))
    old_blk = old_sum["models"].get(OLD_MODEL, {})
    new_blk = new_sum["models"].get(NEW_MODEL, {})

    out: dict = {
        "comparison": "F1_Qwen S3 格跨引擎复现性（ollama qwen36:latest vs colibri qwen3.6-colibri）",
        "base_model": "Qwen3.6-35B-A3B",
        "variables": {
            "engine": "ollama vs colibri 1.12.1",
            "quantization": "IQ3_S vs int4-gs64",
            "decoding": "format=schema 约束解码 vs prefill 续写等效约束",
            "hardware": "旧机器 CPU vs RTX 5080 CUDA",
            "protocol": "E1-A/E1-B 逐字同一（同种子同批构成）",
        },
    }

    # ---------- E1-A ----------
    old_a = load_last(OLD_JSONL, OLD_MODEL, "E1A")
    new_a = load_last(NEW_JSONL, NEW_MODEL, "E1A")
    common = sorted(set(old_a) & set(new_a), key=lambda q: int(q))
    out["e1a"] = {"n_old": len(old_a), "n_new": len(new_a), "n_common": len(common)}
    if len(common) < 50:
        print(f"[fatal] E1-A 共同题目仅 {len(common)}，不足以支撑对比结论", file=sys.stderr)
        return 2

    ye, yo, yn = [], [], []
    for q in common:
        ro, rn = old_a[q], new_a[q]
        if ro.get("expert") is not None:
            ye.append(int(ro["expert"]))
        else:
            ye.append(int(rn["expert"]))
        yo.append(int(ro["llm"]))
        yn.append(int(rn["llm"]))
    ye, yo, yn = map(lambda v: np.array(v, dtype=float), (ye, yo, yn))

    agree = float(np.mean(yo == yn))
    n = len(ye)
    ce = defaultdict(int)
    for a, b in zip(yo.astype(int), yn.astype(int)):
        ce[(a, b)] += 1
    pe = sum((sum(1 for v in yo if v == k) / n) * (sum(1 for v in yn if v == k) / n)
             for k in set(yo.astype(int)) | set(yn.astype(int)))
    kappa = (agree - pe) / (1 - pe) if pe < 1 else None
    rho_eng = e1._spearman(yo, yn)
    rho_old = e1._spearman(ye, yo)
    rho_new = e1._spearman(ye, yn)

    # 两侧行的权威 ρ+CI 一律由本脚本从 JSONL 现算（bootstrap 同审计种子）：
    # local_matrix.json 每次跑批会被整体覆盖，不能作为 ollama 侧引用来源。
    from scipy import stats as _st
    import math as _math
    ci_old = e1.bootstrap_e1a(ye, yo, 200, e1.BOOT_SEED)[0]
    ci_new = e1.bootstrap_e1a(ye, yn, 200, e1.BOOT_SEED)[0]

    labels = [1, 2, 3]
    conf = [[ce.get((a, b), 0) for b in labels] for a in labels]
    out["e1a"].update({
        "raw_agreement": round(agree, 4),
        "cohen_kappa": None if kappa is None else round(kappa, 4),
        "spearman_engine_vs_engine": e1._r4(rho_eng),
        "spearman_vs_expert_ollama": e1._r4(rho_old),
        "spearman_vs_expert_colibri": e1._r4(rho_new),
        "ci_vs_expert_ollama_recomputed": ci_old,
        "ci_vs_expert_colibri_recomputed": ci_new,
        "confusion_ollama_rows_x_colibri_cols": conf,
        "summary_reference": {
            "ollama": {k: old_blk.get(k) for k in
                       ("e1a_spearman", "e1a_spearman_ci95", "e1a_parse_rate",
                        "e1a_cohen_kappa", "e1a_accuracy")},
            "colibri": {k: new_blk.get(k) for k in
                        ("e1a_spearman", "e1a_spearman_ci95", "e1a_parse_rate",
                         "e1a_cohen_kappa", "e1a_accuracy")},
            "note": "ollama 侧汇总 JSON 已被后续批次覆盖（只剩 deepseek-r1:1.5b），"
                    "故两侧行引用值以本文件 recomputed 字段为准",
        },
    })

    # ---------- E1-B ----------
    old_b = load_last(OLD_JSONL, OLD_MODEL, "E1B")
    new_b = load_last(NEW_JSONL, NEW_MODEL, "E1B")
    eb = {"n_batches_old": len(old_b), "n_batches_new": len(new_b)}
    if old_b and new_b:
        wins_o, opp_o = e1._constraints(list(old_b.values()))
        wins_n, opp_n = e1._constraints(list(new_b.values()))
        pairs_o = {(a, b) for (a, b), w in wins_o.items() if w > 0}
        pairs_n = {(a, b) for (a, b), w in wins_n.items() if w > 0}
        common_pairs = pairs_o & pairs_n
        # 方向一致：同一 (harder, easier) 对在两引擎都判为该方向
        same_dir = len(common_pairs)
        contra = len({(b, a) for (a, b) in common_pairs} & pairs_o & pairs_n)
        eb.update({
            "n_pair_constraints_old": len(pairs_o),
            "n_pair_constraints_new": len(pairs_n),
            "n_common_pairs": len(common_pairs),
            "direction_agreement_pairs": same_dir - contra,
            "direction_contradictions": contra,
        })
        if common_pairs:
            ids = sorted(set().union(*[set(r.get("batch_ids") or []) for r in old_b.values()]),
                         key=lambda q: int(q))
            idx = {q: i for i, q in enumerate(ids)}
            S_o = e1._fit_bt(wins_o, opp_o, idx, len(ids))
            S_n = e1._fit_bt(wins_n, opp_n, idx, len(ids))
            so = np.array([S_o[idx[q]] for q in ids])
            sn = np.array([S_n[idx[q]] for q in ids])
            eb["bt_score_spearman"] = e1._r4(e1._spearman(so, sn))
            # 各侧 BT 分数 vs 专家的 ρ（自算，权威；两侧行引用不再依赖被覆盖的汇总）
            exp_map = {}
            for src in (old_a, new_a):
                for q, r in src.items():
                    if r.get("expert") is not None:
                        exp_map[q] = int(r["expert"])
            if all(q in exp_map for q in ids):
                ye_b = np.array([exp_map[q] for q in ids], dtype=float)
                eb["spearman_vs_expert_ollama"] = e1._r4(e1._spearman(ye_b, so))
                eb["spearman_vs_expert_colibri"] = e1._r4(e1._spearman(ye_b, sn))
        eb["summary_reference"] = {
            "ollama": {"e1b_spearman": old_blk.get("e1b_spearman"),
                       "e1b_spearman_ci95": old_blk.get("e1b_spearman_ci95"),
                       "e1b_parse_fail": old_blk.get("e1b_parse_fail")},
            "colibri": {"e1b_spearman": new_blk.get("e1b_spearman"),
                        "e1b_spearman_ci95": new_blk.get("e1b_spearman_ci95"),
                        "e1b_parse_fail": new_blk.get("e1b_parse_fail")},
        }
    out["e1b"] = eb

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------- 控制台 ----------
    print("=" * 74)
    print("跨引擎复现性对比：Qwen3.6-35B-A3B（S3 格）")
    print("  ollama qwen36:latest (IQ3_S, 约束解码, CPU)  vs  colibri qwen3.6-colibri")
    print("  (int4-gs64, prefill 等效约束, CUDA) — 同题/同协议/同种子")
    print("=" * 74)
    a = out["e1a"]
    print(f"[E1-A] 共同题目 {a['n_common']}（ollama {a['n_old']} / colibri {a['n_new']}）")
    print(f"  标签原始一致率   : {a['raw_agreement']}")
    print(f"  Cohen's κ        : {a['cohen_kappa']}")
    print(f"  引擎间 Spearman  : {a['spearman_engine_vs_engine']}")
    print(f"  ρ vs 专家 ollama : {a['spearman_vs_expert_ollama']} CI{a['ci_vs_expert_ollama_recomputed']}"
          f"   colibri: {a['spearman_vs_expert_colibri']} CI{a['ci_vs_expert_colibri_recomputed']}")
    print(f"  混淆表(行=ollama 1/2/3, 列=colibri 1/2/3): {a['confusion_ollama_rows_x_colibri_cols']}")
    b = out.get("e1b", {})
    if b:
        print(f"[E1-B] 批 ollama {b.get('n_batches_old')} / colibri {b.get('n_batches_new')}"
              f"；共同题目对 {b.get('n_common_pairs')}")
        print(f"  方向一致对 {b.get('direction_agreement_pairs')}，矛盾对 {b.get('direction_contradictions')}")
        print(f"  BT 分数 Spearman: {b.get('bt_score_spearman')}")
        print(f"  ρ_E1B ollama {b.get('summary_reference', {}).get('ollama', {}).get('e1b_spearman')}"
              f"  colibri {b.get('summary_reference', {}).get('colibri', {}).get('e1b_spearman')}")
    print(f"\n[done] -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
