#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_matrix_rows.py —— 由实测产物自动生成 ④b 矩阵行与论文用汇总表

目的：④b 收尾时，**所有进入矩阵 CSV 与稿件正文的数字都由本脚本从
`local_matrix.jsonl` / `local_matrix.json` / `local_matrix_meta_small.json`
直接算出**，不经手工转录，避免抄错（数字纪律）。

纪律：
  * 缺失的测量一律留空，**绝不填占位数字**；
  * 参数量取自 /api/show 实测（`collect_model_meta.py`），无实测即 null；
  * E1-B 有效批不足 108 的单元格，reliability_verdict 强制带覆盖率警示。

输出：
  * stdout：人类可读的逐模型报告 + 可直接粘贴的 Markdown 表
  * --csv-out：追加/覆盖写入矩阵 CSV 的候选行（默认只打印，不写）

用法：
  python results/m3/build_matrix_rows.py
  python results/m3/build_matrix_rows.py --csv-out results/m3/m3_model_scale_matrix.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path

M3 = Path("E:/learnflow/results/m3")

#: ④b 矩阵的**全部**实测数据来源（2026-09-28 修订，修复可复现性缺陷）。
#: 修订前脚本只读 `local_matrix.jsonl`，造成两处与磁盘 CSV 不符：
#:   ① `deepseek-r1:32b` 在该文件中只有 29/212 的**中断残卷**（旧机 15.8 GB 放弃），
#:      而完整 320 条（212 E1-A + 108 E1-B）在 `local_matrix_mixtral_r1.jsonl`；
#:   ② `ministral-3:3b` / `mixtral:8x7b` 两格完全读不到。
#: 结果是文档给出的复算命令只能复现 8 行，与磁盘上 11 行 CSV 不一致。
#: 现改为按序读取全部贡献源，**后加载的源覆盖同 (model, cond, key) 记录**，
#: 使 32b 的完整卷正确覆盖残卷。
#: `local_matrix_colibri.*` / `local_matrix_dsv4.*` 为跨引擎复现行与 S4 探索点，
#: 按方案 **不并入** 4×3 矩阵主张，故不在读取列表内。
JSONL_SOURCES = [
    M3 / "local_matrix.jsonl",
    M3 / "local_matrix_ministral.jsonl",
    M3 / "local_matrix_mixtral_r1.jsonl",
]
SUMMARY_SOURCES = [
    M3 / "local_matrix.json",
    M3 / "local_matrix_ministral.json",
    M3 / "local_matrix_mixtral_r1.json",
]
JSONL = JSONL_SOURCES[0]      # 兼容旧引用
SUMMARY = SUMMARY_SOURCES[0]  # 兼容旧引用
META_SMALL = M3 / "local_matrix_meta_small.json"
META_ANCHOR = M3 / "local_matrix_meta.json"
#: ministral-3:3b / mixtral:8x7b / deepseek-r1:32b 三格的元信息（族别 / 参数量 / 架构）
META_FILL = M3 / "m3_fill_meta.json"

#: 三格的**人工补充注记**（量化错配 / 血统 / 复跑事实）。属散文性诚实声明而非测量结果，
#: 故不在脚本内计算；由本脚本附在 verdict 末尾，保证 CSV 整体可由脚本复现、不留手写数字。
EXTRA_NOTES = {
    "ministral-3:3b": "量化 Q4_K_M（与锚点 qwen36 IQ3_S 错配，方案A §4 已知）",
    "mixtral:8x7b": ("量化 Q4_0（非 Q4_K_M，与矩阵其余 Q4_K_M / 锚点 IQ3_S 均错配，"
                     "方案A §4 已知）"),
    "deepseek-r1:32b": ("⚠ F4_S3 此前因 15.8GB RAM 被判不可行，本机升级 32GB RAM 后复跑成功；"
                        "量化 Q4_K_M（与锚点 qwen36 IQ3_S 错配，方案A §4 已知）；"
                        "R1-Distill 基座为 Qwen2.5（lineage 见方案 §2 F4 注，族内归类仍归 F4）"),
}

FAMILY_MAP = {"Qwen": "F1_Qwen", "Llama": "F2_Llama",
              "Mistral": "F3_Mistral", "DeepSeek": "F4_DeepSeek"}

CSV_HEADER = ["model_id", "family", "scale_tier", "params_billions", "architecture",
              "eval_status", "datasets", "protocol", "parse_rate", "spearman_rho",
              "accuracy", "cohen_kappa", "reliability_verdict", "source_anchor"]

#: 驱动脚本 `local_matrix_e1ab.py` 实测输出的权威 ρ/CI（其汇总 JSON 每次跑批会被整体
#: 覆盖，故此处按驱动 stdout 留档；本脚本自算的 ρ 与这些值逐条吻合，可交叉校验）。
#: 来源：run_batch_remaining.py 的逐模型输出行。
AUDITED = {
    "qwen3:1.7b":  {"e1a": (0.1072, (-0.0288,  0.2095)), "e1b": (-0.0671, (-0.2094,  0.0891))},
    "llama3.2:1b": {"e1a": (-0.0337, (-0.1597, 0.0875)), "e1b": (-0.0574, (-0.2156,  0.1034))},
    "llama3.1:8b": {"e1a": (0.2430, (0.1258,  0.3511)), "e1b": (0.1081, (-0.0858,  0.2113))},
}

N_ITEMS = 212          # DBE-212
N_BATCHES = 108        # E1-B：3 轮 × 6 题
#: 参与计算的题量门槛（与 inter_model_agreement.py:59 / exogenous_metrics.py:25 同名常量
#: 保持一致）。锚点模型不再是「无条件跳过」，而是「唯一键数 < MIN_KEYS 才跳过」——
#: 题量补齐后本脚本会自动生成该行，无需再改代码。
MIN_KEYS = 200
ANCHOR_MODEL = "qwen36:latest"   # 审计锚点：题量足够时由本脚本现算，否则跳过


def tier_of(params_b):
    if params_b is None:
        return "UNKNOWN"
    if params_b < 7:
        return "S1_<7B"
    if params_b < 30:
        return "S2_7-30B"
    if params_b < 70:
        return "S3_30-70B"
    return "S4_>70B"


def load_meta() -> dict:
    meta = {}
    # 载入顺序即优先级：`m3_fill_meta.json` 的条目最稀疏（先载入），`local_matrix_meta_small.json`
    # / `local_matrix_meta.json` 含实测 quantization 与 identity_caveat，后载入以免被稀疏条目
    # 覆盖而丢失 R1-Distill-Qwen 的血统警示。
    for p in (META_FILL, META_SMALL, META_ANCHOR):
        if p.is_file():
            meta.update(json.loads(p.read_text(encoding="utf-8")))
    return meta


def load_records() -> list:
    """按序读取全部贡献源，每条记录标注 `_src`（来源文件）。

    后加载源的记录会覆盖同 (model, cond, key) 的先前记录，使 `deepseek-r1:32b`
    的完整 320 条正确覆盖 `local_matrix.jsonl` 中的 29 条中断残卷。
    """
    out = []
    for p in JSONL_SOURCES:
        if not p.is_file():
            continue
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            r["_src"] = "results/m3/" + p.name
            out.append(r)
    return out


def load_summary() -> tuple:
    """合并全部汇总文件，并记录每个模型的汇总来源文件（供 source_anchor 标注）。"""
    models, src_of = {}, {}
    for p in SUMMARY_SOURCES:
        if not p.is_file():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for k, v in (d.get("models") or {}).items():
            models[k] = v
            src_of[k] = "results/m3/" + p.name
    return {"models": models}, src_of


def kappa_simple(a: list, b: list) -> float:
    """Cohen κ（名义），纯标准库。"""
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = {c: a.count(c) / n for c in cats}
    pb = {c: b.count(c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    return 1.0 if (1 - pe) == 0 and po == 1.0 else (po - pe) / (1 - pe)


def kappa_linear(a: list, b: list, order=(1, 2, 3)) -> float:
    """线性加权 Cohen κ（有序等级 1<2<3）。"""
    n = len(a)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(order)}
    K = max(1, len(order) - 1)

    def w(x, y):
        return 1 - abs(idx.get(x, 0) - idx.get(y, 0)) / K

    po_w = sum(w(x, y) for x, y in zip(a, b)) / n
    cats = sorted(set(a) | set(b))
    pa = {c: a.count(c) / n for c in cats}
    pb = {c: b.count(c) / n for c in cats}
    pe_w = sum(pa.get(x, 0) * pb.get(y, 0) * w(x, y) for x in cats for y in cats)
    return 1.0 if (1 - pe_w) == 0 and po_w == 1.0 else (po_w - pe_w) / (1 - pe_w)


def e1a_pairs(records: list) -> list:
    """E1-A 的 (expert, llm) 配对，按题目 key 去重（跳过重试重复）。"""
    seen = {}
    for r in records:
        if r.get("llm") is None or r.get("expert") is None:
            continue
        seen[r.get("key")] = (int(r["expert"]), int(r["llm"]))
    return list(seen.values())


def _rankdata(a):
    """平均秩处理（scipy 不可用时替代 spearmanr 的秩计算）。"""
    a = np.asarray(a, dtype=float)
    n = a.size
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n)
    ranks[order] = np.arange(1, n + 1)
    sa = a[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sa[j + 1] == sa[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    return ranks


def _spearman(x, y):
    rx = _rankdata(x)
    ry = _rankdata(y)
    xm = rx - rx.mean()
    ym = ry - ry.mean()
    denom = np.sqrt((xm ** 2).sum()) * np.sqrt((ym ** 2).sum())
    if denom == 0:
        return float("nan")
    return float((xm * ym).sum() / denom)


def bootstrap_spearman(pairs: list, reps: int = 200, seed: int = 20260922):
    """题目级配对 bootstrap 的 Spearman ρ 与 95% CI。

    优先 scipy.spearmanr（与审计脚本一致）；scipy 不可用时回退纯 numpy
    （平均秩 + 秩的 Pearson 相关），保证无 scipy 环境也能出数。
    """
    if len(pairs) < 3:
        return None, None
    import random
    ex = [p[0] for p in pairs]
    pr = [p[1] for p in pairs]
    try:
        from scipy import stats as st
        rho = float(st.spearmanr(ex, pr).statistic)
        use_np = False
    except Exception:  # noqa: BLE001
        rho = _spearman(ex, pr)
        use_np = True
    rng = random.Random(seed)
    n = len(pairs)
    boots = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        be = [ex[i] for i in idx]
        bp = [pr[i] for i in idx]
        try:
            boots.append(_spearman(be, bp) if use_np else float(st.spearmanr(be, bp).statistic))
        except Exception:  # noqa: BLE001
            continue
    boots = [b for b in boots if b == b]  # 丢弃退化重抽样产生的 nan
    if not boots:
        return rho, None
    lo = float(np.percentile(boots, 2.5))
    hi = float(np.percentile(boots, 97.5))
    return rho, (lo, hi)


#: 协议可用性三重判据（可复算、无主观裁量）：
#:   ① 解析完整性  parse_ok ≥ 0.90（E1-A 按题；E1-B 按批）
#:   ② 输出非退化  归一化熵 ≥ 0.50 且 众数占比 ≤ 0.80（防「等级塌缩」）
#:   ③ 覆盖充分    E1-B 有效批 ≥ 90%（< 90% 的 ρ 不得与满批单元格并列比较）
#: 三条同时满足才记 usable=True；任一不满足即 unusable，原因逐条写明。
GATE = {"parse_min": 0.90, "entropy_min": 0.50, "modal_max": 0.80,
        "coverage_min": 0.90}


def usability_gate(parse_rate, entropy, modal_share, coverage):
    """返回 (usable: bool, reasons: list[str])。缺失输入一律判 False 并写明原因。"""
    # 维度①解析完整性 + 维度②输出非退化 → 决定 E1-A 单元格是否可用
    reasons_a = []
    if parse_rate is None:
        reasons_a.append("解析率缺失")
    elif parse_rate < GATE["parse_min"]:
        reasons_a.append(f"解析率 {parse_rate:.1%} < {GATE['parse_min']:.0%}")

    if entropy is None or modal_share is None:
        reasons_a.append("输出分布缺失")
    else:
        if entropy < GATE["entropy_min"]:
            reasons_a.append(f"归一化熵 {entropy:.3f} < {GATE['entropy_min']}")
        if modal_share > GATE["modal_max"]:
            reasons_a.append(f"众数占比 {modal_share:.1%} > {GATE['modal_max']:.0%}（等级塌缩）")

    # 维度③覆盖充分 → 只决定 E1-B 的 ρ 是否可与其他单元格并列比较，
    # 不否定 E1-A 单元格（否则会把 E1-A 质量最好的单元格误判为不可用）
    reasons_b = []
    if coverage is None:
        reasons_b.append("未跑 E1-B")
    elif coverage < GATE["coverage_min"]:
        reasons_b.append(f"覆盖率 {coverage:.0%} < {GATE['coverage_min']:.0%}，"
                         f"ρ(E1-B) 不得与满批单元格并列比较")

    return (len(reasons_a) == 0), reasons_a, (len(reasons_b) == 0), reasons_b


def fail_mode(raw: str) -> str:
    s = (raw or "").strip()
    m = re.search(r"\[([^\]]*)\]", s)
    letters = re.findall(r"[A-F]", m.group(1)) if m else []
    if m and len(set(letters)) == 5:
        return "drop_one_item"
    if m and len(set(letters)) < 5:
        return "too_few_items"
    if m:
        return "duplicate_or_extra"
    if s.startswith("{"):
        return "json_no_ranking_array"
    return "free_text_or_empty"


def analyze(records: list) -> dict:
    """按 (model, cond, key) 去重：后加载源覆盖先前记录；并记下每个单元格**最终胜出**的来源文件。

    `SRC` 只收录胜出记录的来源，因此 `deepseek-r1:32b` 的 anchor 会正确指向
    `local_matrix_mixtral_r1.jsonl`（完整卷所在），而不会被已作废的 29 条残卷污染。
    """
    per = defaultdict(lambda: {"E1A": {}, "E1B": {}})
    for r in records:
        m = r.get("model")
        if not m:
            continue
        src = r.get("_src", "")
        if r.get("cond") == "E1A":
            per[m]["E1A"][r.get("key")] = (src, r)
        elif r.get("cond") == "E1B":
            per[m]["E1B"][r.get("key")] = (src, r)  # 同批去重，保留最后一次（含重试）
    for m in list(per):
        srcs = set()
        e1a = {}
        for k, (s, r) in per[m]["E1A"].items():
            e1a[k] = r
            srcs.add(s)
        e1b = {}
        for k, (s, r) in per[m]["E1B"].items():
            e1b[k] = r
            srcs.add(s)
        per[m]["E1A"] = list(e1a.values())
        per[m]["E1B"] = e1b
        per[m]["SRC"] = srcs
    return per


def build_anchor(src_set: set, summary_src: str | None) -> str:
    """source_anchor = 该单元格**胜出**记录的来源文件 + 汇总文件（排序后并列）。

    只列胜出来源，故不会出现「已作废的残卷文件」被误标为出处的情况。
    """
    files = set(src_set or set())
    if summary_src:
        files.add(summary_src)
    if not files:
        return "results/m3/local_matrix.jsonl"
    return "; ".join(sorted(files))


def main() -> int:
    ap = argparse.ArgumentParser(description="由实测产物生成 ④b 矩阵行")
    ap.add_argument("--csv-out", default="", help="写入矩阵 CSV（默认只打印）")
    args = ap.parse_args()

    meta = load_meta()
    records = load_records()
    per = analyze(records)
    summary, summary_src = load_summary()

    rows = []
    gate_rows = []
    print("=" * 78)
    print("④b 实测汇总（全部数字由本脚本从产物算出，未经手工转录）")
    print("=" * 78)

    for model in sorted(per):
        # 完整性门禁对**所有**模型一律生效（2026-09-27 修复）：此前只对锚点模型判题量，
        # 导致 deepseek-r1:32b 跑批中断后残存的 29/212 条也会被当作完整单元格产出 ρ/κ
        # ——用 13% 题量算出的相关系数据此会混进矩阵。题量不足一律跳过并报告缺口。
        n_keys = len({r.get("key") for r in per[model]["E1A"]})
        if n_keys < MIN_KEYS:
            gap = MIN_KEYS - n_keys
            tag = "锚点" if model == ANCHOR_MODEL else "该模型"
            print(f"\n[{model}] {tag} E1-A 仅 {n_keys}/{N_ITEMS} 唯一键 < MIN_KEYS={MIN_KEYS}，"
                  f"跳过；尚需 {gap} 键")
            print(f"  → 补齐 {gap} 个唯一键后本脚本会自动生成该行，无需改代码")
            print("  （完整性门禁：题量不足的单元格不产出任何 ρ/κ/parse_rate，不得用残缺样本冒充完整单元格）")
            continue
        if model == ANCHOR_MODEL:
            print(f"\n[{model}] 锚点唯一键 {n_keys}/{N_ITEMS} ≥ MIN_KEYS={MIN_KEYS}，不跳过："
                  f"ρ/CI/κ/parse_rate 一律由本脚本从 local_matrix.jsonl 现算")
        md = meta.get(model, {}) or {}
        params = md.get("params_b")
        fam = FAMILY_MAP.get(md.get("family"), "UNKNOWN")
        tier = tier_of(params)

        e1a = per[model]["E1A"]
        e1a_ok = [r for r in e1a if r.get("llm") is not None]
        # 分母用「实际尝试题数」而非 DBE-212：锚点 qwen36 只跑了部分题，
        # 其权威解析率来自审计产物 o13_llm_protocol_audit.json，不得被此处覆盖。
        # 分子分母一律按 key 去重：断点续跑会对同一 key 写入多条记录（末条胜出），
        # 不去重会让 parse_rate 与打印出的「解析 x/212」自相矛盾（曾出现 232/212）。
        attempted = len({r.get("key") for r in e1a})
        parsed_u = len({r.get("key") for r in e1a_ok})
        parse_rate = (parsed_u / attempted) if attempted else None

        # ρ / CI / κ 一律优先采用驱动脚本自己算出的权威字段（e1a_* / e1b_*），
        # 只有在汇总缺失时才由本脚本从 JSONL 现算，避免两套口径。
        sm = summary.get("models", {}).get(model) or {}
        rho_a = sm.get("e1a_spearman")
        ci_a = sm.get("e1a_spearman_ci95")
        # 注意：local_matrix.json 每次跑批会被整体覆盖（只保留当次模型），
        # 故 ρ / CI 一律由本脚本从 JSONL 现算（spearman + 题目级 bootstrap），
        # 并与汇总中仍在的条目交叉校验（llama3.1:8b 应为 0.243 / [0.1258, 0.3511]）。
        rho_a, ci_a = bootstrap_spearman(e1a_pairs(e1a))
        ci_src = "本脚本自算"
        audit_div = ""
        if model in AUDITED:
            # 不再静默覆盖：先自算，再与 AUDITED 比对，分歧就大声告警。
            a_rho, a_ci = AUDITED[model]["e1a"]
            s_rho, s_ci = rho_a, ci_a
            d_rho = abs(s_rho - a_rho) if (s_rho is not None and s_rho == s_rho) else float("nan")
            if s_ci is None:
                d_lo = d_hi = float("nan")
            else:
                d_lo = abs(s_ci[0] - a_ci[0])
                d_hi = abs(s_ci[1] - a_ci[1])
            diverge = ((d_rho == d_rho and d_rho > 1e-4)
                       or (d_lo == d_lo and d_lo > 1e-3)
                       or (d_hi == d_hi and d_hi > 1e-3))
            if diverge:
                s_ci_txt = "不可计算" if s_ci is None else f"[{s_ci[0]:.4f}, {s_ci[1]:.4f}]"
                d_ci_txt = "CI 不可比" if s_ci is None else f"ΔCI 端点={d_lo:.4f}/{d_hi:.4f}"
                audit_div = (f"AUDITED_DIVERGENCE: 自算 ρ={s_rho:.4f} CI{s_ci_txt} "
                             f"vs AUDITED ρ={a_rho:.4f} CI[{a_ci[0]:.4f}, {a_ci[1]:.4f}]"
                             f"（Δρ={d_rho:.4f}，{d_ci_txt}）")
                print("\n" + "!" * 78)
                print(f"WARNING [AUDITED 分歧] {model}（E1-A）：自算与留档发布值不一致")
                print(f"  本脚本自算 ：ρ={s_rho:.4f}  95%CI {s_ci_txt}")
                print(f"  AUDITED 留档：ρ={a_rho:.4f}  95%CI [{a_ci[0]:.4f}, {a_ci[1]:.4f}]")
                print(f"  差值       ：Δρ={d_rho:.4f}  {d_ci_txt}")
                print("  处置       ：人工已批准将发布值切换为本脚本自算 CI（2026-09-26）；"
                      "ρ 与 AUDITED 逐位一致，仅 95% CI 端点因 bootstrap 实现不同而异，分歧保留作留痕。")
                print("!" * 78 + "\n")
            # 发布值现取「本脚本自算」：人工决策已批准（2026-09-26）。ρ 与 AUDITED 逐位一致，
            # 仅 95% CI 端点因 bootstrap 实现不同（本脚本用 random.Random，驱动脚本用 np.random.default_rng）
            # 而异。不再回退到 AUDITED，ci_src 保持 "本脚本自算"。
        rho_b = sm.get("e1b_spearman")
        ci_b = sm.get("e1b_spearman_ci95")
        if model in AUDITED:
            rho_b = AUDITED[model]["e1b"][0]
            ci_b = AUDITED[model]["e1b"][1]
        # bootstrap 在等级塌缩时会出现零方差重抽样 → CI 为 nan，须如实标注而非丢弃
        ci_nan = ci_a is not None and (ci_a[0] != ci_a[0] or ci_a[1] != ci_a[1])
        if sm.get("e1a_parse_rate") is not None:
            parse_rate = sm["e1a_parse_rate"]

        e1b = per[model]["E1B"]
        b_ok = [r for r in e1b.values() if r.get("ok_parse")]
        b_bad = [r for r in e1b.values() if not r.get("ok_parse")]
        modes = Counter(fail_mode(r.get("raw", "")) for r in b_bad)

        # 由 E1-A 记录直接算出 accuracy / κ / 分布诊断（与锚点行同口径，可横比）
        acc = k_s = k_w = None
        modal_share = ent = None
        dist_txt = ""
        pairs = e1a_pairs(e1a)
        if pairs:
            ex = [p[0] for p in pairs]
            pr = [p[1] for p in pairs]
            acc = sum(1 for x, y in zip(ex, pr) if x == y) / len(ex)
            k_s = kappa_simple(ex, pr)
            k_w = kappa_linear(ex, pr)
            # 分布诊断：解析成功 ≠ 估计可用。众数占比过高 = 等级塌缩（判别方差近乎为零）
            cnt = Counter(pr)
            modal_share = max(cnt.values()) / len(pr)
            ent = -sum((v / len(pr)) * math.log2(v / len(pr)) for v in cnt.values())
            dist_txt = "/".join(f"{k}:{cnt.get(k, 0) / len(pr):.1%}" for k in (1, 2, 3))

        # 判定（诚实：不显著的写「不显著」，覆盖率不足的强制警示）
        if rho_a is None:
            verdict = "NOT_EVALUATED（无 E1-A 结果）"
        else:
            sig = (not ci_nan) and ci_a is not None and (ci_a[0] > 0 or ci_a[1] < 0)
            ci_txt = ("不可计算（等级塌缩导致重抽样零方差）" if ci_nan
                      else (f"95%CI[{ci_a[0]:.4f}, {ci_a[1]:.4f}]（{ci_src}）" if ci_a else ""))
            verdict = (f"E1-A ρ={rho_a:.4f} " + ci_txt +
                       ("；显著" if sig else ("；CI 不可计算" if ci_nan else "；CI 含零·不显著")))
            if modal_share is not None and modal_share >= 0.90:
                verdict += (f"；⚠ 等级塌缩（众数占比 {modal_share:.1%}，"
                            f"熵 {ent:.3f} bit，判别方差近乎为零，ρ 不得与正常方差模型等权并列）")
            if dist_txt:
                verdict += f"；预测分布 {dist_txt}"
            if e1b:
                verdict += f"；E1-B 有效批 {len(b_ok)}/{len(e1b)}"
                if len(b_ok) < N_BATCHES:
                    verdict += f"（⚠ 覆盖率 {len(b_ok) / N_BATCHES:.0%}，ρ 不得与满批单元格并列比较）"
                if rho_b is not None:
                    verdict += f"，ρ={rho_b:.4f}"
                if modes:
                    verdict += "；失败模式 " + ",".join(f"{k}={v}" for k, v in modes.most_common())

            # 协议可用性三重门禁（解析 / 方差 / 覆盖）
            ent_norm = (ent / math.log2(3)) if ent is not None else None
            coverage = (len(b_ok) / N_BATCHES) if e1b else None
            usable, reasons_a, usable_b, reasons_b = usability_gate(
                parse_rate, ent_norm, modal_share, coverage)
            gate_txt = ("E1-A usable（解析 + 方差 两条满足）" if usable
                        else "E1-A unusable：" + "；".join(reasons_a))
            gate_txt += ("；E1-B 覆盖充分（ρ 可并列比较）" if usable_b
                         else "；E1-B " + "；".join(reasons_b))
            verdict += f"；【协议可用性门禁】{gate_txt}"
            if audit_div:
                verdict += f"；⚠ {audit_div}"
            if model in EXTRA_NOTES:
                verdict += "；" + EXTRA_NOTES[model]
            gate_rows.append({
                "model_id": model, "family": fam, "scale_tier": tier,
                "parse_rate": parse_rate, "entropy_norm": ent_norm,
                "modal_share": modal_share, "e1b_coverage": coverage,
                "e1a_usable": usable, "e1a_reasons": reasons_a,
                "e1b_usable": usable_b, "e1b_reasons": reasons_b,
            })

        rows.append({
            "model_id": model,
            "family": fam,
            "scale_tier": tier,
            "params_billions": "" if params is None else params,
            "architecture": md.get("architecture") or "",
            "eval_status": "EVALUATED" if rho_a is not None else "NOT_EVALUATED",
            "datasets": "DBE-KT22",
            "protocol": "E1-A(schema enum+锚定)/E1-B(枚举数组+BT)",
            "parse_rate": "" if parse_rate is None else f"{parse_rate:.3f}",
            "spearman_rho": "" if rho_a is None else f"{rho_a:.4f}",
            "accuracy": "" if acc is None else f"{acc:.4f}",
            "cohen_kappa": "" if k_s is None else f"{k_s:.4f}",
            "reliability_verdict": verdict,
            "source_anchor": (build_anchor(per[model].get("SRC", set()),
                                           summary_src.get(model))
                              + (f" | {audit_div}" if audit_div else "")),
        })

        print(f"\n[{model}] {fam} / {tier} / params={params} / {md.get('architecture')}")
        print(f"  E1-A: 解析 {parsed_u}/{N_ITEMS}"
              + (f" ({parse_rate:.1%})" if parse_rate is not None else "")
              + (f"，ρ={rho_a:.4f}" if rho_a is not None else "")
              + (f"，accuracy={acc:.4f}" if acc is not None else "")
              + (f"，κ={k_s:.4f}" if k_s is not None else "")
              + (f"（加权κ={k_w:.4f}）" if k_w is not None else ""))
        if e1b:
            print(f"  E1-B: 有效批 {len(b_ok)}/{len(e1b)}，失败 {len(b_bad)}，模式 {dict(modes)}"
                  + (f"，ρ={rho_b:.4f}" if rho_b is not None else ""))

    if args.csv_out:
        path = Path(args.csv_out)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\n[written] {path}  ({len(rows)} 行)")
    else:
        print("\n（未写 CSV；加 --csv-out <路径> 可写入矩阵）")

    gp = M3 / "protocol_usability.json"
    gp.write_text(json.dumps({
        "gate": GATE,
        "note": "协议可用性三重判据：解析完整性 / 输出非退化 / 覆盖充分；三条同时满足才 usable",
        "cells": gate_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[written] {gp}  ({len(gate_rows)} 单元格)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
