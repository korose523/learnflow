#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_matrix_e1ab.py —— 本地 Ollama 版「已审计协议」标注矩阵驱动脚本
================================================================================

用途
--------------------------------------------------------------------------------
补齐 M3 稿 §8 ④b 的投稿前硬前置：**≥3 模型族 × ≥3 参数规模 × 同一批题目 ×
同一套已通过审计的协议**。

本脚本不发明任何新协议，两个条件（E1-A / E1-B）的提示词、JSON schema、轮数、
批大小、随机种子全部**逐字复制**自审计产物的唯一权威实现：

    results/code/llm_labeling_v2.py   （E1-A 锚定绝对评级 / E1-B 批量排序 + BT）

统计部分（两两约束、Bradley-Terry 拟合、Spearman、题目级重抽样 bootstrap）**逐字
照抄**审计脚本：

    results/code/o13_llm_protocol_audit.py
        _constraints  (L109-128)
        _fit_bt       (L138-156)
        _spearman     (L159-163)
        main() 内的题目级配对 bootstrap (L273-296)

因此：同种子 → 同批构成；同批题目 → 与审计（ρ_E1A=0.2195 / ρ_E1B=0.1808）可直接
对比，且该对比即为「协议保真度」的验证。

输出
--------------------------------------------------------------------------------
    <out>.jsonl      逐条 append、断点续跑（跳过已完成；解析失败条目重试）
    <out>.json       每模型汇总（含 bootstrap CI、模型身份 digest）
    results/m3/local_matrix_rows.csv   仅 EVALUATED 行的矩阵 CSV 片段

纪律
--------------------------------------------------------------------------------
* 缺失 / 失败的测量一律记 null 或 NOT_RUN，**绝不填占位数字**。
* 参数量缺省即 null，scale_tier 记 UNKNOWN，**严禁猜测**。
* 本脚本只读 llm_labeling_v2.py / o13_llm_protocol_audit.py / Questions.csv，
  **不修改任何文档、不修改上述参考实现、不写 m3_model_scale_matrix.csv**。

用法
--------------------------------------------------------------------------------
    python local_matrix_e1ab.py --selftest
    python local_matrix_e1ab.py --models "qwen36:latest" \
        --meta '{"qwen36:latest":{"family":"Qwen","params_b":35,"architecture":"MoE"}}' \
        --conditions E1A --out results/m3/local_matrix
    python local_matrix_e1ab.py --dump-matrix

退出码
--------------------------------------------------------------------------------
    0  正常完成（含 --selftest 全部 PASS）
    1  自测 FAIL
    2  输入缺失 / 参数错误
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import random
import sys
import time
import urllib.request
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as st

# ─────────────────────────── 路径与常量 ───────────────────────────
# 仓库根可用 LEARNFLOW_ROOT 覆盖；默认按本文件位置（results/m3/）推导
BASE = Path(os.environ.get("LEARNFLOW_ROOT", Path(__file__).resolve().parents[2]))
DATA = BASE / "data"
CODE = BASE / "results" / "code"
M3 = BASE / "results" / "m3"

QUESTIONS_CSV = DATA / "dbe_kt22" / "csv" / "Questions.csv"
O13_PATH = CODE / "o13_llm_protocol_audit.py"

API_BASE = "http://127.0.0.1:11434/api"
OLLAMA_EXE = os.environ.get("OLLAMA_BIN", "ollama")  # 原为硬编码本机路径，已移除；默认走 PATH

#: 与审计完全一致的随机种子与批配置（llm_labeling_v2.py L29 / L144）
SEED = 20260912
N_ROUNDS = 3
BATCH = 6

#: bootstrap 重抽样种子（对齐 o13_llm_protocol_audit.py --seed 默认值 20260922）
BOOT_SEED = 20260922

#: 矩阵 CSV 表头（严格照 results/m3/m3_model_scale_matrix.csv）
MATRIX_HEADER = ["model_id", "family", "scale_tier", "params_billions", "architecture",
                 "eval_status", "datasets", "protocol", "parse_rate", "spearman_rho",
                 "accuracy", "cohen_kappa", "reliability_verdict", "source_anchor"]

# ═══════════════════════════════════════════════════════════════════
#  协议（逐字复制自 llm_labeling_v2.py，勿改措辞）
# ═══════════════════════════════════════════════════════════════════

# llm_labeling_v2.py L116-119
RUBRIC3 = ("Rating scale (anchored):\n"
           "1 = routine: single concept, direct application of a definition or a one-step query/statement.\n"
           "2 = medium: requires combining 2+ concepts, multi-step reasoning, or non-obvious formulation.\n"
           "3 = hard: complex design, tricky edge cases, nested/recursive structures, or subtle correctness issues.")

# llm_labeling_v2.py L44-46
SCHEMA_DIFF3 = {"type": "object",
                "properties": {"difficulty": {"type": "integer", "enum": [1, 2, 3]}},
                "required": ["difficulty"], "additionalProperties": False}

# llm_labeling_v2.py L51-55
SCHEMA_RANK = {"type": "object",
               "properties": {"ranking": {"type": "array",
                                          "items": {"type": "string",
                                                    "enum": ["A", "B", "C", "D", "E", "F"]}}},
               "required": ["ranking"], "additionalProperties": False}


def build_e1a_prompt(text: str) -> str:
    """逐字复制 llm_labeling_v2.py L127-129。"""
    return ("You are rating the difficulty of a database-course exercise for university students.\n" + RUBRIC3 +
            "\n\nExercise:\n" + text +
            "\n\nRate the difficulty.")


def build_e1b_prompt(lines: List[str]) -> str:
    """逐字复制 llm_labeling_v2.py L155-158。lines 由调用方按 \'{A|B|...}. {text}\' 生成。"""
    return ("You are ranking database-course exercises by difficulty for university students. "
            "Order them from EASIEST to HARDEST.\n" + RUBRIC3 +
            "\n\nExercises:\n" + "\n\n".join(lines) +
            "\n\nOutput a JSON array of the letters, easiest first, e.g. [\"B\", \"A\", \"C\"].")


# ═══════════════════════════════════════════════════════════════════
#  统计（逐字照抄 o13_llm_protocol_audit.py）
# ═══════════════════════════════════════════════════════════════════

def _constraints(records: List[Dict[str, Any]]) -> Tuple[Dict[Tuple[str, str], float],
                                                         Dict[Tuple[str, str], float]]:
    """o13 L109-128：从排序记录重建两两约束 wins[(harder,easier)] 与 opp[(a,b)]。"""
    wins: Dict[Tuple[str, str], float] = defaultdict(float)
    opp: Dict[Tuple[str, str], float] = defaultdict(float)
    for r in records:
        if not r.get("ok_parse"):
            continue
        seq = r.get("order") or []
        batch = r.get("batch_ids") or []
        for a in range(len(seq)):
            for b in range(a + 1, len(seq)):
                if ord(seq[b]) - 65 >= len(batch) or ord(seq[a]) - 65 >= len(batch):
                    continue
                harder = batch[ord(seq[b]) - 65]
                easier = batch[ord(seq[a]) - 65]
                wins[(harder, easier)] += 1
                opp[(harder, easier)] += 1
                opp[(easier, harder)] += 1
    return wins, opp


def _constraint_counts(wins: Dict[Tuple[str, str], float],
                       opp: Dict[Tuple[str, str], float]) -> Dict[str, int]:
    """o13 L131-135：总比较次数 vs 去重后的题目对数。"""
    keys = [(a, b) for (a, b), w in wins.items() if opp.get((a, b), 0) > 0 and w > 0]
    return {"total_comparisons": int(sum(wins.values())), "unique_item_pairs": len(keys)}


def _fit_bt(wins: Dict[Tuple[str, str], float], opp: Dict[Tuple[str, str], float],
            idx: Dict[str, int], n: int, iters: int = 300) -> np.ndarray:
    """o13 L138-156：logistic-gradient Bradley-Terry 拟合（向量化）。"""
    keys = [(a, b) for (a, b), w in wins.items() if opp.get((a, b), 0) > 0 and w > 0]
    if not keys:
        return np.zeros(n)
    I = np.array([idx[a] for a, _ in keys]); J = np.array([idx[b] for _, b in keys])
    W = np.array([wins[k] for k in keys], dtype=float)
    N = np.array([opp[k] for k in keys], dtype=float)
    S = np.zeros(n)
    for _ in range(iters):
        d = np.clip(S[I] - S[J], -30, 30)
        p = 1.0 / (1.0 + np.exp(-d))
        g = W - N * p
        G = np.bincount(I, g, minlength=n) - np.bincount(J, g, minlength=n)
        h = N * p * (1 - p)
        H = np.bincount(I, h, minlength=n) + np.bincount(J, h, minlength=n)
        S += G / np.maximum(H, 1e-9)
    return S - S.mean()


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """o13 L159-163。"""
    if x.size < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    return float(st.spearmanr(x, y).statistic)


def _r4(x: Any) -> Optional[float]:
    """有限值 → 保留 4 位；NaN/Inf → None（纪律：不把 NaN 当数字写进产物）。"""
    v = float(x)
    return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)


def _r8(x: Any) -> Optional[float]:
    """有限值 → 保留 8 位；NaN/Inf → None。"""
    v = float(x)
    return None if (math.isnan(v) or math.isinf(v)) else round(v, 8)


def bootstrap_e1a(expert: np.ndarray, llm_abs: np.ndarray,
                  reps: int, seed: int) -> Tuple[Optional[List[float]], int]:
    """题目级重抽样 → E1-A Spearman 的 95% CI（与 o13 bootstrap 的 E1-A 支路同构）。"""
    rng = np.random.default_rng(seed)
    n = int(expert.size)
    vals: List[float] = []
    for _ in range(reps):
        pick = rng.integers(0, n, n)
        mult = np.bincount(pick, minlength=n).astype(int)
        r = _spearman(np.repeat(expert, mult), np.repeat(llm_abs, mult))
        if not math.isnan(r):
            vals.append(r)
    if not vals:
        return None, 0
    return [round(float(np.percentile(vals, 2.5)), 4),
            round(float(np.percentile(vals, 97.5)), 4)], len(vals)


def paired_bootstrap_bt(expert: np.ndarray, llm_abs: np.ndarray,
                        wins: Dict[Tuple[str, str], float], opp: Dict[Tuple[str, str], float],
                        idx: Dict[str, int], n_items: int,
                        reps: int, seed: int) -> Dict[str, Any]:
    """题目级配对 bootstrap，**每个重抽样样本内重新拟合 BT**（照抄 o13 L273-296）。

    返回 E1-A / E1-B（BT）各自的 ρ 均值与 CI95，以及 Δ = ρ_abs − ρ_BT 的区间与 p。
    """
    rng = np.random.default_rng(seed)
    keys = [(a, b) for (a, b), w in wins.items() if opp.get((a, b), 0) > 0 and w > 0]
    if not keys:
        return {"reps_used": 0, "error": "无可行两两约束（E1-B 未运行或全部解析失败）"}
    I = np.array([idx[a] for a, _ in keys]); J = np.array([idx[b] for _, b in keys])
    W0 = np.array([wins[k] for k in keys], dtype=float)
    N0 = np.array([opp[k] for k in keys], dtype=float)
    d_abs, d_bt, deltas = [], [], []
    for _ in range(reps):
        pick = rng.integers(0, n_items, n_items)
        mult = np.bincount(pick, minlength=n_items).astype(float)
        ra = _spearman(np.repeat(expert, mult.astype(int)),
                       np.repeat(llm_abs, mult.astype(int)))
        scale = mult[I] * mult[J]
        keep = (I != J) & (scale > 0)
        w_s = {(int(i), int(j)): float(w) for i, j, w in zip(I[keep], J[keep], W0[keep] * scale[keep])}
        o_s = {(int(i), int(j)): float(n) for i, j, n in zip(I[keep], J[keep], N0[keep] * scale[keep])}
        S = _fit_bt(w_s, o_s, {i: i for i in range(n_items)}, n_items)
        rb = _spearman(np.repeat(expert, mult.astype(int)),
                       np.repeat(S, mult.astype(int)))
        if not (math.isnan(ra) or math.isnan(rb)):
            d_abs.append(ra); d_bt.append(rb); deltas.append(ra - rb)
    if not deltas:
        return {"reps_used": 0, "error": "所有重抽样样本的 Spearman 均为 NaN"}
    dl = np.array(deltas)
    lo, hi = np.percentile(dl, [2.5, 97.5])
    p_two = 2 * min(float((dl <= 0).mean()), float((dl >= 0).mean()))
    return {
        "reps_used": len(dl),
        "rho_absolute_mean": round(float(np.mean(d_abs)), 4),
        "rho_absolute_ci95": [round(float(np.percentile(d_abs, 2.5)), 4),
                              round(float(np.percentile(d_abs, 97.5)), 4)],
        "rho_bt_mean": round(float(np.mean(d_bt)), 4),
        "rho_bt_ci95": [round(float(np.percentile(d_bt, 2.5)), 4),
                        round(float(np.percentile(d_bt, 97.5)), 4)],
        "delta_abs_minus_bt_mean": round(float(np.mean(dl)), 4),
        "delta_abs_minus_bt_ci95": [round(float(lo), 4), round(float(hi), 4)],
        "delta_p_two_sided": round(p_two, 4),
        "significant_at_0.05": bool(lo > 0 or hi < 0),
    }


# ═══════════════════════════════════════════════════════════════════
#  数据加载（逐字复制 llm_labeling_v2.py L106-114）
# ═══════════════════════════════════════════════════════════════════

def load_questions() -> List[Tuple[str, int, str]]:
    qs: List[Tuple[str, int, str]] = []
    if not QUESTIONS_CSV.is_file():
        raise SystemExit(f"[fatal] 缺少题库：{QUESTIONS_CSV}")
    with open(QUESTIONS_CSV, encoding="utf-8-sig", errors="replace") as f:
        for d in csv.DictReader(f):
            try:
                t = (d.get("question_text") or d.get("question_rich_text") or "")
                qs.append((d["id"], int(d["difficulty"]), t[:1200].strip()))
            except (ValueError, TypeError):
                pass
    return qs


# ═══════════════════════════════════════════════════════════════════
#  Ollama 访问
# ═══════════════════════════════════════════════════════════════════

def _sanitize(s: str) -> str:
    """去除不可见控制字符，避免产物被判为二进制。"""
    return "".join(ch for ch in (s or "") if ch == "\t" or ord(ch) >= 32)


def ask(model: str, prompt: str, num_predict: int = 64, schema: Optional[dict] = None,
        api_base: str = API_BASE, timeout: int = 600) -> str:
    """对齐 llm_labeling_v2.py 的 ask()：format 语法约束解码 + temperature=0。"""
    body = {"model": model, "prompt": prompt, "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": 0, "num_predict": num_predict},
            "keep_alive": "60m"}
    req = urllib.request.Request(api_base + "/generate",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    return _sanitize(d.get("response", "").strip())


def model_show(model: str, api_base: str = API_BASE, timeout: int = 30) -> Dict[str, Any]:
    """/api/show 取**真实返回值**：digest / quantization / parameter_size 等。

    部分 Ollama 版本的 /api/show 不返回顶层 digest，此时回退到 /api/tags 的实测 digest。
    """
    body = {"model": model}
    req = urllib.request.Request(api_base + "/show",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    details = d.get("details") or {}
    info = d.get("model_info") or {}
    picked_info = {k: v for k, v in info.items()
                   if any(tok in k.lower() for tok in ("parameter", "arch", "context", "expert", "block"))}
    digest = d.get("digest")
    size = None
    digest_source = "api/show"
    if digest is None:  # 回退：/api/tags 的实测 digest（真实返回值，非猜测）
        try:
            treq = urllib.request.Request(api_base + "/tags")
            with urllib.request.urlopen(treq, timeout=timeout) as tr:
                tags = json.loads(tr.read().decode("utf-8")).get("models", [])
            cand = {m.get("name"): m for m in tags}
            hit = cand.get(model) or cand.get(model + ":latest") or cand.get(model.split(":")[0] + ":latest")
            if hit:
                digest = hit.get("digest")
                size = hit.get("size")
                digest_source = "api/tags"
        except Exception:
            digest_source = "unavailable"
    return {
        "digest": digest,
        "digest_source": digest_source,
        "size_bytes": size,
        "modified_at": d.get("modified_at"),
        "family": details.get("family"),
        "parameter_size": details.get("parameter_size"),
        "quantization_level": details.get("quantization_level"),
        "format": details.get("format"),
        "model_info_subset": picked_info,
        "raw_top_keys": sorted(d.keys()),
    }


def parse_json_obj(txt: str) -> Any:
    try:
        return json.loads(txt)
    except Exception:
        try:
            a, b = txt.index("{"), txt.rindex("}")
            return json.loads(txt[a:b + 1])
        except Exception:
            return {}


def last_digit(txt: str, valid: set) -> Optional[int]:
    for ch in reversed(txt):
        if ch.isdigit() and int(ch) in valid:
            return int(ch)
    return None


def parse_rank_seq(raw: str, n_batch: int) -> Tuple[List[str], bool]:
    """解析一次排序标注（逐字对齐 llm_labeling_v2.py L164-171），返回 (seq, ok_parse)。"""
    obj = parse_json_obj(raw)
    sr = obj.get("ranking", []) if isinstance(obj, dict) else []
    if isinstance(sr, str):                      # legacy string form
        seq = [ch for ch in sr if ch.isalpha() and ch.isupper()]
    else:
        seq = [str(x).strip().upper()[:1] for x in sr]
    seq = [ch for ch in seq if ch.isalpha() and ord(ch) - 65 < n_batch]
    ok = len(seq) == n_batch and len(set(seq)) == n_batch
    return seq, ok


# ═══════════════════════════════════════════════════════════════════
#  断点续跑
# ═══════════════════════════════════════════════════════════════════

def load_done(jsonl: Path) -> set:
    """对齐 llm_labeling_v2.py L77-92：E1-A 无 llm / E1-B ok_parse=False 的条目重试。"""
    done = set()
    if jsonl.is_file():
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                model, cond, key = r.get("model"), r.get("cond"), r.get("key")
                if model is None or cond is None or key is None:
                    continue
                if cond == "E1B":
                    if r.get("ok_parse"):
                        done.add((model, cond, key))
                elif r.get("llm") is not None:
                    done.add((model, cond, key))
    return done


# ═══════════════════════════════════════════════════════════════════
#  运行
# ═══════════════════════════════════════════════════════════════════

def _scale_tier(params_b: Optional[float]) -> str:
    """按 m3_model_scale_matrix.csv 采用的档位边界从**给定**参数量推导；缺则 UNKNOWN。"""
    if params_b is None:
        return "UNKNOWN"
    p = float(params_b)
    if p < 7:
        return "S1_<7B"
    if p <= 30:
        return "S2_7-30B"
    if p <= 70:
        return "S3_30-70B"
    return "S4_>70B"


def run_models(models: List[str], meta: Dict[str, Any], conditions: List[str],
               qs: List[Tuple[str, int, str]], out_base: Path, reps: int,
               api_base: str, timeout: int, retry_rounds: int = 1) -> Dict[str, Any]:
    jsonl = out_base.with_suffix(".jsonl")
    done = load_done(jsonl)
    print(f"[resume] {len(done)} records already present -> {jsonl}", flush=True)
    jout = open(jsonl, "a", encoding="utf-8")

    def record(model: str, cond: str, key: str, payload: Dict[str, Any]) -> None:
        jout.write(json.dumps({"model": model, "cond": cond, "key": key, **payload},
                              ensure_ascii=False) + "\n")
        jout.flush()

    ids = [q[0] for q in qs]
    by_id = {q[0]: q for q in qs}
    n_items = len(qs)
    summary: Dict[str, Any] = {"n_items": n_items, "conditions": conditions,
                               "seed": SEED, "n_rounds": N_ROUNDS, "batch": BATCH,
                               "models": {}}

    # 预生成 E1-B 批构成：**先 seed 再 shuffle**，与审计同种子同批（llm_labeling_v2 L146-149）。
    random.seed(SEED)
    batches_all: List[Tuple[int, int, List[str]]] = []
    for rnd in range(N_ROUNDS):
        order = ids[:]
        random.shuffle(order)
        for bi in range(0, len(order), BATCH):
            batches_all.append((rnd, bi // BATCH, order[bi:bi + BATCH]))
    n_batches = len(batches_all)
    print(f"[E1-B] 批构成：{N_ROUNDS} 轮 × {BATCH} 题 = {n_batches} 批（seed={SEED}）", flush=True)

    for model in models:
        m = meta.get(model, {}) or {}
        params_b = m.get("params_b") if isinstance(m.get("params_b"), (int, float)) else None
        cell: Dict[str, Any] = {
            "model_id": model,
            "family": m.get("family") or "UNKNOWN",
            "architecture": m.get("architecture") or "UNKNOWN",
            "params_billions": params_b,
            "scale_tier": m.get("scale_tier") or _scale_tier(params_b),
        }
        t0 = time.time()
        print(f"\n=== model={model} ===", flush=True)

        try:
            cell["model_digest"] = model_show(model, api_base=api_base)
        except Exception as ex:
            cell["model_digest"] = {"error": f"{type(ex).__name__}: {str(ex)[:120]}"}
            print(f"[warn] /api/show 失败：{cell['model_digest']['error']}", flush=True)

        # ---------- E1-A ----------
        if "E1A" in conditions:
            t0a = time.time()
            n_ok = 0
            n_new = 0
            for i, (qid, expert, text) in enumerate(qs):
                if (model, "E1A", qid) in done:
                    continue
                n_new += 1
                prompt = build_e1a_prompt(text)
                try:
                    raw = ask(model, prompt, num_predict=64, schema=SCHEMA_DIFF3,
                              api_base=api_base, timeout=timeout)
                except Exception as ex:
                    raw = ""
                    print(f"[E1A ERR] {qid} {str(ex)[:80]}", flush=True)
                lab = last_digit(raw, {1, 2, 3})
                if lab is not None:
                    n_ok += 1
                record(model, "E1A", qid, {"expert": expert, "llm": lab, "raw": raw[-40:]})
                if (i + 1) % 25 == 0:
                    print(f"[E1-A] {i+1}/{n_items} elapsed={time.time()-t0a:.0f}s", flush=True)
            cell["e1a_new_records"] = n_new
            # 本次调用若全部命中已存记录（resume），则不虚报耗时，记 null
            cell["e1a_wall_seconds"] = round(time.time() - t0a, 1) if n_new else None

        # ---------- E1-B ----------
        if "E1B" in conditions:
            t0b = time.time()
            n_new_b = 0
            for rnd, bi, batch in batches_all:
                key = f"r{rnd}b{bi}"
                if (model, "E1B", key) in done:
                    continue
                n_new_b += 1
                lines = [f"{chr(65 + j)}. {by_id[qid][2]}" for j, qid in enumerate(batch)]
                prompt = build_e1b_prompt(lines)
                try:
                    raw = ask(model, prompt, num_predict=60, schema=SCHEMA_RANK,
                              api_base=api_base, timeout=timeout)
                except Exception as ex:
                    raw = ""
                    print(f"[E1B ERR] {key} {str(ex)[:80]}", flush=True)
                seq, ok_parse = parse_rank_seq(raw, len(batch))
                record(model, "E1B", key,
                       {"round": rnd, "batch_ids": batch, "order": seq,
                        "ok_parse": ok_parse, "raw": raw[-60:]})
            cell["e1b_new_records"] = n_new_b
            # 与 e1a_wall_seconds 对称：本次若无新请求（全部 resume 跳过）记 null，不虚报
            cell["e1b_wall_seconds"] = round(time.time() - t0b, 1) if n_new_b else None

        cell["wall_seconds"] = round(time.time() - t0, 1)
        summary["models"][model] = cell
        print(f"[{model}] done in {cell['wall_seconds']}s "
              f"({n_ok if 'E1A' in conditions else '-'} E1-A parsed)", flush=True)

    # ---------- 同进程内对失败条目重试（Fix 4）----------
    if retry_rounds > 0 and ("E1A" in conditions or "E1B" in conditions):
        _retry_failed(models, conditions, qs, jsonl, api_base, timeout,
                      retry_rounds, record)

    jout.close()
    return summary


def _collect_failures(jsonl: Path, models: List[str],
                      conditions: List[str]) -> Tuple[List[Tuple[str, str]],
                                                      List[Tuple[str, str, Dict[str, Any]]]]:
    """从 jsonl（同 key 末条胜出）收集失败条目：E1A llm=None / E1B ok_parse=False。"""
    last: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    if jsonl.is_file():
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                last[(r.get("model"), r.get("cond"), r.get("key"))] = r
    fa: List[Tuple[str, str]] = []
    fb: List[Tuple[str, str, Dict[str, Any]]] = []
    for (mo, cond, key), r in last.items():
        if mo not in models:
            continue
        if cond == "E1A" and "E1A" in conditions and r.get("llm") is None:
            fa.append((mo, key))
        elif cond == "E1B" and "E1B" in conditions and not r.get("ok_parse"):
            fb.append((mo, key, r))
    return fa, fb


def _retry_failed(models: List[str], conditions: List[str],
                  qs: List[Tuple[str, int, str]], jsonl: Path,
                  api_base: str, timeout: int, retry_rounds: int, record) -> None:
    """同一进程内对失败条目重试（最多 retry_rounds 轮，轮间 sleep 2s）。

    不覆盖原失败记录：jsonl 仍为 append，聚合取末条（成功条目自然顶掉失败条目）。
    """
    by_id = {q[0]: q for q in qs}
    for attempt in range(retry_rounds):
        fa, fb = _collect_failures(jsonl, models, conditions)
        if not fa and not fb:
            print("[retry] 无失败条目，跳过重试", flush=True)
            break
        print(f"[retry] 重试轮 {attempt+1}/{retry_rounds}："
              f"E1-A {len(fa)} 条, E1-B {len(fb)} 条", flush=True)
        fixed_a = fixed_b = 0
        for mo, qid in fa:
            if qid not in by_id:
                continue
            try:
                raw = ask(mo, build_e1a_prompt(by_id[qid][2]), num_predict=64,
                          schema=SCHEMA_DIFF3, api_base=api_base, timeout=timeout)
            except Exception as ex:
                raw = ""
                print(f"[retry E1A ERR] {mo}/{qid} {str(ex)[:80]}", flush=True)
            lab = last_digit(raw, {1, 2, 3})
            if lab is not None:
                fixed_a += 1
            record(mo, "E1A", qid, {"expert": by_id[qid][1], "llm": lab,
                                    "raw": raw[-40:], "retry": attempt + 1})
        for mo, key, prev in fb:
            batch = prev.get("batch_ids") or []
            if not batch or any(q not in by_id for q in batch):
                continue
            lines = [f"{chr(65 + j)}. {by_id[q][2]}" for j, q in enumerate(batch)]
            try:
                raw = ask(mo, build_e1b_prompt(lines), num_predict=60,
                          schema=SCHEMA_RANK, api_base=api_base, timeout=timeout)
            except Exception as ex:
                raw = ""
                print(f"[retry E1B ERR] {mo}/{key} {str(ex)[:80]}", flush=True)
            seq, ok_parse = parse_rank_seq(raw, len(batch))
            if ok_parse:
                fixed_b += 1
            record(mo, "E1B", key, {"round": prev.get("round"),
                                    "batch_ids": batch, "order": seq,
                                    "ok_parse": ok_parse, "raw": raw[-60:],
                                    "retry": attempt + 1})
        print(f"[retry] 重试轮 {attempt+1} 修复：E1-A {fixed_a}/{len(fa)}, "
              f"E1-B {fixed_b}/{len(fb)}", flush=True)
        if fixed_a == 0 and fixed_b == 0:
            print("[retry] 本轮零修复，停止重试", flush=True)
            break
        if attempt + 1 < retry_rounds:
            time.sleep(2)


def aggregate(models: List[str], qs: List[Tuple[str, int, str]], out_base: Path,
              reps: int) -> Dict[str, Any]:
    """读回 jsonl（同 key 末条胜出），算每模型的 E1-A / E1-B 指标与 bootstrap。"""
    jsonl = out_base.with_suffix(".jsonl")
    last: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            last[(r.get("model"), r.get("cond"), r.get("key"))] = r

    # 统计口径对齐 o13（其 main() 用 sorted(by_id, key=lambda q: int(q)) 作为题目全集）
    by_id = {q[0]: q for q in qs}
    ids = sorted([q[0] for q in qs], key=lambda q: int(q))
    idx = {q: i for i, q in enumerate(ids)}
    n_items = len(qs)
    expert_all = np.array([by_id[q][1] for q in ids], dtype=float)

    out: Dict[str, Any] = {"generated_by": "results/m3/local_matrix_e1ab.py",
                           "n_items": n_items, "reps": reps, "seed": SEED, "boot_seed": BOOT_SEED,
                           "source_questions": str(QUESTIONS_CSV),
                           "protocol_source": "results/code/llm_labeling_v2.py",
                           "stats_source": "results/code/o13_llm_protocol_audit.py",
                           "models": {}}

    for model in models:
        e1a = [r for (mo, c, _k), r in last.items() if mo == model and c == "E1A"]
        e1b = [r for (mo, c, _k), r in last.items() if mo == model and c == "E1B"]
        blk: Dict[str, Any] = {"n_items": n_items}

        # E1-A：**两种解析口径并报**（分母显式写出，避免不可比）
        #   口径 primary = "listwise"：llm=None 的题整条剔除（本脚本原有语义，保持不变）
        #   口径 "none_as_zero"    ：None→0 计入全量（对齐 o13_llm_protocol_audit.py L184
        #                            `float((...).get("llm") or 0)`）
        lbl_map = {r["key"]: r.get("llm") for r in e1a}
        blk["e1a_n_records"] = len(e1a)
        blk["e1a_n_total"] = n_items
        blk["e1a_n_parsed"] = int(sum(1 for q in ids if lbl_map.get(q) is not None))
        blk["e1a_parse_rate"] = round(blk["e1a_n_parsed"] / n_items, 4) if n_items else None
        blk["e1a_parse_convention_primary"] = "listwise"

        # ---- 口径 A：listwise（主口径）----
        keep = [q for q in ids if lbl_map.get(q) is not None]
        if keep:
            ye = np.array([by_id[q][1] for q in keep], dtype=float)
            yl = np.array([int(lbl_map[q]) for q in keep], dtype=float)
            rho = st.spearmanr(ye, yl)
            blk["e1a_spearman"] = _r4(rho.statistic)
            blk["e1a_spearman_p"] = _r8(rho.pvalue)
            n = len(keep)
            acc = float(np.mean([a == b for a, b in zip(ye, yl)]))
            ce = Counter(ye.astype(int).tolist()); cl = Counter(yl.astype(int).tolist())
            pe = sum((ce[k] / n) * (cl[k] / n) for k in set(ce) | set(cl))
            blk["e1a_accuracy"] = round(acc, 4)
            blk["e1a_cohen_kappa"] = round((acc - pe) / (1 - pe), 4) if pe < 1 else None
            blk["e1a_llm_dist"] = {str(k): v for k, v in sorted(cl.items())}
            ci, used = bootstrap_e1a(ye, yl, reps, BOOT_SEED)
            blk["e1a_spearman_ci95"] = ci
            blk["e1a_bootstrap_reps_used"] = used
        else:
            blk["e1a_spearman"] = None
            blk["e1a_spearman_ci95"] = None
            blk["e1a_accuracy"] = None
            blk["e1a_cohen_kappa"] = None
            blk["e1a_bootstrap_reps_used"] = 0

        # ---- 口径 B：none_as_zero（对齐 o13；None 当 0 参与全量 212 题）----
        if e1a:
            ll0 = np.array([(lbl_map[q] if lbl_map.get(q) is not None else 0)
                            for q in ids], dtype=float)
            rho0 = st.spearmanr(expert_all, ll0)
            blk["e1a_spearman_none_as_zero"] = _r4(rho0.statistic)
            blk["e1a_spearman_none_as_zero_p"] = _r8(rho0.pvalue)
            ci0, used0 = bootstrap_e1a(expert_all, ll0, reps, BOOT_SEED)
            blk["e1a_spearman_none_as_zero_ci95"] = ci0
            blk["e1a_spearman_none_as_zero_reps_used"] = used0
        else:
            blk["e1a_spearman_none_as_zero"] = None
            blk["e1a_spearman_none_as_zero_ci95"] = None

        # E1-B：BT
        blk["e1b_n_batches"] = len(e1b)
        blk["e1b_parse_fail"] = int(sum(1 for r in e1b if not r.get("ok_parse")))
        if e1b:
            wins, opp = _constraints(e1b)
            cc = _constraint_counts(wins, opp)
            blk["e1b_n_pair_constraints"] = cc["unique_item_pairs"]
            blk["e1b_n_total_comparisons"] = cc["total_comparisons"]
            if cc["unique_item_pairs"] > 0:
                S = _fit_bt(wins, opp, idx, n_items)
                rho_bt = st.spearmanr(expert_all, S)
                blk["e1b_spearman"] = _r4(rho_bt.statistic)
                blk["e1b_spearman_p"] = _r8(rho_bt.pvalue)
            else:
                blk["e1b_spearman"] = None
                blk["e1b_spearman_ci95"] = None
        else:
            blk["e1b_spearman"] = None
            blk["e1b_spearman_ci95"] = None

        # 联合 bootstrap（含 BT 重拟合）→ E1-B CI 与 Δ
        if e1a and e1b and blk.get("e1b_n_pair_constraints"):
            ok_ids = [q for q in ids if lbl_map.get(q) is not None]
            # 配对 bootstrap 需 E1-A 与 E1-B 共用同一题目全集；E1-A 有解析失败时
            # 两条件题目集不一致，故如实标记「不适用」而非硬凑
            if len(ok_ids) == n_items:
                wins, opp = _constraints(e1b)
                boot = paired_bootstrap_bt(expert_all, np.array(
                    [lbl_map[q] for q in ids], dtype=float), wins, opp, idx, n_items, reps, BOOT_SEED)
                blk["paired_bootstrap"] = boot
                blk["e1b_spearman_ci95"] = boot.get("rho_bt_ci95")
                blk["e1a_spearman_ci95"] = boot.get("rho_absolute_ci95") or blk.get("e1a_spearman_ci95")
            else:
                blk["paired_bootstrap"] = {
                    "skipped": True,
                    "reason": f"E1-A 未全解析（{len(ok_ids)}/{n_items}），配对 bootstrap 不适用"}

        out["models"][model] = blk

    return out


def write_summary(summary: Dict[str, Any], run_cells: Dict[str, Any], out_base: Path) -> Path:
    merged = dict(summary)
    merged["run_cells"] = run_cells.get("models", {})
    p = out_base.with_suffix(".json")
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def dump_matrix(out_base: Path, csv_out: Path) -> int:
    """把 EVALUATED 行写成矩阵 CSV 片段（列名照 m3_model_scale_matrix.csv）。"""
    jpath = out_base.with_suffix(".json")
    if not jpath.is_file():
        print(f"[dump-matrix] 缺少汇总产物：{jpath}", file=sys.stderr)
        return 2
    data = json.loads(jpath.read_text(encoding="utf-8"))
    models = data.get("models", {})
    run_cells = data.get("run_cells", {})
    rows: List[List[Any]] = []
    for model_id, blk in models.items():
        c = run_cells.get(model_id, {})
        rho = blk.get("e1a_spearman")
        if rho is None and blk.get("e1b_spearman") is None:
            continue  # 无任何可靠测量，不产出 EVALUATED 行
        prot = "E1-A(schema enum+锚定)"
        if blk.get("e1b_n_batches"):
            prot += "/E1-B(枚举数组+BT)"
        verdict_bits = []
        if blk.get("e1a_parse_rate") is not None:
            verdict_bits.append(f"E1-A parse_rate={blk['e1a_parse_rate']} "
                                f"({blk.get('e1a_n_parsed')}/{blk.get('e1a_n_total')})")
        if blk.get("e1b_n_batches"):
            verdict_bits.append(f"E1-B {blk.get('e1b_n_pair_constraints')} 约束 / "
                                f"{blk.get('e1b_parse_fail')} 失败")
        if blk.get("e1a_spearman") is not None:
            verdict_bits.append(f"ρ_E1A_listwise={blk['e1a_spearman']}")
        if blk.get("e1a_spearman_none_as_zero") is not None:
            verdict_bits.append(f"ρ_E1A_none_as_zero={blk['e1a_spearman_none_as_zero']}")
        if blk.get("e1b_spearman") is not None:
            verdict_bits.append(f"ρ_E1B={blk['e1b_spearman']}")
        rows.append([
            model_id,
            c.get("family", "UNKNOWN"),
            c.get("scale_tier", "UNKNOWN"),
            "" if c.get("params_billions") is None else c.get("params_billions"),
            c.get("architecture", "UNKNOWN"),
            "EVALUATED",
            "DBE-KT22",
            prot,
            blk.get("e1a_parse_rate"),
            rho if rho is not None else blk.get("e1b_spearman"),
            blk.get("e1a_accuracy"),
            blk.get("e1a_cohen_kappa"),
            "; ".join(verdict_bits),
            f"results/m3/{out_base.name}.json#/models/{model_id}",
        ])
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(MATRIX_HEADER)
        w.writerows(rows)
    print(f"[dump-matrix] {len(rows)} EVALUATED 行 -> {csv_out}")
    return 0


# ═══════════════════════════════════════════════════════════════════
#  自测（--selftest，不联网）
# ═══════════════════════════════════════════════════════════════════

def _load_o13():
    spec = importlib.util.spec_from_file_location("o13_audit", O13_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[selftest] 无法加载 {O13_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def selftest(reps: int = 60) -> int:
    print("=" * 78)
    print("local_matrix_e1ab --selftest（合成数据，不联网；对照 o13_llm_protocol_audit.py）")
    print("=" * 78)
    if not O13_PATH.is_file():
        print(f"FAIL: 缺少对照模块 {O13_PATH}")
        return 1
    o13 = _load_o13()
    rng = np.random.default_rng(12345)
    n = 212
    fails: List[str] = []

    # --- 合成 E1-A：专家标签 + 有相关性的 LLM 标签 ---
    expert = rng.integers(1, 4, n).astype(float)
    noise = rng.normal(0, 1.0, n)
    llm = np.clip(np.round(expert * 0.6 + noise * 0.8), 1, 3).astype(float)

    # --- 合成 E1-B：按真值难度排序的批记录（含少量解析失败） ---
    ids = [str(i) for i in range(n)]
    idx = {q: i for i, q in enumerate(ids)}
    recs: List[Dict[str, Any]] = []
    order_full = sorted(range(n), key=lambda i: expert[i])
    pos = {item: r for r, item in enumerate(order_full)}
    for rnd in range(3):
        perm = rng.permutation(n)
        for b0 in range(0, n, 6):
            batch = perm[b0:b0 + 6]
            if len(batch) < 2:
                continue
            ranked = sorted(batch, key=lambda x: pos[x])
            # 约 12% 制造解析失败
            ok = rng.random() > 0.12
            seq = ([chr(65 + k) for k in range(len(ranked))] if ok else [])
            recs.append({"ok_parse": ok,
                         "order": seq,
                         "batch_ids": [ids[x] for x in ranked]})

    wins_m, opp_m = _constraints(recs)
    wins_o, opp_o = o13._constraints(recs)

    # 1) _constraints 一致性
    same = (dict(wins_m) == dict(wins_o)) and (dict(opp_m) == dict(opp_o))
    print(f"[1] _constraints 对照 o13 : {'PASS' if same else 'FAIL'} "
          f"(pairs={len(wins_m)}, comparisons={int(sum(wins_m.values()))})")
    if not same:
        fails.append("_constraints")

    # 2) _fit_bt 一致性
    S_m = _fit_bt(wins_m, opp_m, idx, n)
    S_o = o13._fit_bt(wins_o, opp_o, idx, n)
    dmax = float(np.max(np.abs(S_m - S_o)))
    ok_bt = np.allclose(S_m, S_o, atol=1e-9)
    rho_m = _spearman(np.array([expert[i] for i in range(n)]), S_m)
    rho_o = float(st.spearmanr([expert[i] for i in range(n)], S_o).statistic)
    print(f"[2] _fit_bt 对照 o13       : {'PASS' if ok_bt else 'FAIL'} "
          f"(max|ΔS|={dmax:.2e}, ρ={rho_m:.4f} vs {rho_o:.4f})")
    if not ok_bt:
        fails.append("_fit_bt")

    # 3) _spearman 一致性（含退化输入）
    cases = [
        (expert, llm),
        (np.ones(n), llm),
        (expert, np.ones(n)),
        (np.arange(5.0), np.array([1.0, 2.0, 3.0, 4.0, 5.0])),
    ]
    ok_sp = True
    for cx, cy in cases:
        a, b = _spearman(cx, cy), o13._spearman(cx, cy)
        if not ((math.isnan(a) and math.isnan(b)) or abs(a - b) < 1e-12):
            ok_sp = False
    print(f"[3] _spearman 对照 o13     : {'PASS' if ok_sp else 'FAIL'}（含 NaN 退化输入）")
    if not ok_sp:
        fails.append("_spearman")

    # 4) 题目级配对 bootstrap 一致性（本脚本 vs 照抄 o13 L274-296 的参考循环，同 seed）
    def ref_bootstrap(reps_: int, seed_: int):
        r2 = np.random.default_rng(seed_)
        keys = [(a, b) for (a, b), w in wins_o.items() if opp_o.get((a, b), 0) > 0 and w > 0]
        I = np.array([idx[a] for a, _ in keys]); J = np.array([idx[b] for _, b in keys])
        W0 = np.array([wins_o[k] for k in keys], dtype=float)
        N0 = np.array([opp_o[k] for k in keys], dtype=float)
        d_abs, d_bt, dl_ = [], [], []
        for _ in range(reps_):
            pick = r2.integers(0, n, n)
            mult = np.bincount(pick, minlength=n).astype(float)
            ra = o13._spearman(np.repeat(expert, mult.astype(int)),
                               np.repeat(llm, mult.astype(int)))
            scale = mult[I] * mult[J]
            keep = (I != J) & (scale > 0)
            w_s = {(int(i), int(j)): float(w) for i, j, w in zip(I[keep], J[keep], W0[keep] * scale[keep])}
            o_s = {(int(i), int(j)): float(v) for i, j, v in zip(I[keep], J[keep], N0[keep] * scale[keep])}
            S = o13._fit_bt(w_s, o_s, {i: i for i in range(n)}, n)
            rb = o13._spearman(np.repeat(expert, mult.astype(int)), np.repeat(S, mult.astype(int)))
            if not (math.isnan(ra) or math.isnan(rb)):
                d_abs.append(ra); d_bt.append(rb); dl_.append(ra - rb)
        return d_abs, d_bt, dl_

    boot_m = paired_bootstrap_bt(expert, llm, wins_m, opp_m, idx, n, reps, 777)
    d_abs_o, d_bt_o, dl_o = ref_bootstrap(reps, 777)
    ok_boot = True
    if dl_o and boot_m.get("reps_used", 0) == len(dl_o):
        ci_m = boot_m["delta_abs_minus_bt_ci95"]
        ci_o = [round(float(np.percentile(dl_o, 2.5)), 4), round(float(np.percentile(dl_o, 97.5)), 4)]
        ok_boot = (ci_m == ci_o and
                   abs(boot_m["delta_abs_minus_bt_mean"] - round(float(np.mean(dl_o)), 4)) < 1e-9 and
                   boot_m["rho_absolute_ci95"] ==
                   [round(float(np.percentile(d_abs_o, 2.5)), 4),
                    round(float(np.percentile(d_abs_o, 97.5)), 4)] and
                   boot_m["rho_bt_ci95"] ==
                   [round(float(np.percentile(d_bt_o, 2.5)), 4),
                    round(float(np.percentile(d_bt_o, 97.5)), 4)])
        print(f"[4] 配对 bootstrap 对照 o13: {'PASS' if ok_boot else 'FAIL'} "
              f"(reps={boot_m['reps_used']}, ΔCI={ci_m} vs {ci_o})")
    else:
        ok_boot = bool(boot_m.get("reps_used", 0)) == bool(dl_o) and not dl_o
        print(f"[4] 配对 bootstrap 对照 o13: {'PASS' if ok_boot else 'FAIL'} "
              f"(reps_m={boot_m.get('reps_used')}, reps_o={len(dl_o)})")
    if not ok_boot:
        fails.append("paired_bootstrap")

    print("-" * 78)
    if fails:
        print(f"SELFTEST FAIL: {fails}")
        return 1
    print("SELFTEST PASS: 4/4 与 o13_llm_protocol_audit.py 一致")
    return 0


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="本地 Ollama 版已审计协议标注矩阵驱动脚本")
    ap.add_argument("--models", type=str, default="",
                    help='逗号分隔，如 "qwen36:latest,llama3.2:3b"')
    ap.add_argument("--meta", type=str, default="",
                    help='JSON 字符串：{"qwen36:latest":{"family":"Qwen","params_b":35,"architecture":"MoE"}}')
    ap.add_argument("--meta-file", type=str, default="", help="--meta 的 JSON 文件版本")
    ap.add_argument("--conditions", type=str, default="E1A,E1B", help="E1A / E1B，逗号分隔")
    ap.add_argument("--limit", type=int, default=0, help="仅取前 N 题（子集冒烟）")
    ap.add_argument("--reps", type=int, default=200, help="bootstrap 重抽样次数")
    ap.add_argument("--timeout", type=int, default=600, help="单次请求超时（秒）")
    ap.add_argument("--api-base", type=str, default=API_BASE)
    ap.add_argument("--out", type=str, default=str(M3 / "local_matrix"),
                    help="产物基名（生成 <out>.jsonl / <out>.json）")
    ap.add_argument("--csv-out", type=str, default="",
                    help="矩阵 CSV 片段输出路径（默认 <out>_rows.csv，即与 --out 同目录）")
    ap.add_argument("--retry-rounds", type=int, default=1,
                    help="同进程内对失败条目的最大重试轮数（默认 1，轮间 sleep 2s）")
    ap.add_argument("--dump-matrix", action="store_true", help="写 EVALUATED 行到 <out>_rows.csv")
    ap.add_argument("--selftest", action="store_true", help="合成数据自测（不联网）")
    args = ap.parse_args()

    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    # Fix 3：默认与 --out 同目录派生，避免写死到 results/m3/ 污染并发产物目录
    csv_out = Path(args.csv_out) if args.csv_out else out_base.parent / (out_base.name + "_rows.csv")

    if args.selftest:
        return selftest(reps=min(args.reps, 60) if args.reps else 60)

    if args.dump_matrix:
        return dump_matrix(out_base, csv_out)

    if not args.models:
        print("[fatal] 需要 --models（或用 --selftest / --dump-matrix）", file=sys.stderr)
        return 2

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    conditions = [c.strip().upper() for c in args.conditions.split(",") if c.strip()]
    for c in conditions:
        if c not in ("E1A", "E1B"):
            print(f"[fatal] 未知条件 {c}", file=sys.stderr)
            return 2

    meta: Dict[str, Any] = {}
    if args.meta_file:
        if not os.path.isfile(args.meta_file):
            print(f"[fatal] --meta-file 不存在：{args.meta_file}", file=sys.stderr)
            return 2
        meta.update(json.loads(Path(args.meta_file).read_text(encoding="utf-8")))
    if args.meta:
        meta.update(json.loads(args.meta))

    qs = load_questions()
    if args.limit and args.limit > 0:
        qs = qs[:args.limit]
    print(f"[data] DBE-KT22 questions: {len(qs)}", flush=True)

    assert "You are rating the difficulty of a database-course exercise" in build_e1a_prompt("X")
    run_cells = run_models(models, meta, conditions, qs, out_base, args.reps,
                           args.api_base, args.timeout, retry_rounds=args.retry_rounds)
    summary = aggregate(models, qs, out_base, args.reps)
    path = write_summary(summary, run_cells, out_base)
    print(f"\n[done] summary -> {path}", flush=True)

    for model in models:
        b = summary["models"].get(model, {})
        print(f"  {model}: E1A ρ(listwise)={b.get('e1a_spearman')} "
              f"CI={b.get('e1a_spearman_ci95')} | "
              f"E1A ρ(none_as_zero)={b.get('e1a_spearman_none_as_zero')} "
              f"CI={b.get('e1a_spearman_none_as_zero_ci95')} | "
              f"parsed={b.get('e1a_n_parsed')}/{b.get('e1a_n_total')} "
              f"({b.get('e1a_parse_convention_primary')}) | "
              f"E1B ρ={b.get('e1b_spearman')} CI={b.get('e1b_spearman_ci95')} "
              f"fail={b.get('e1b_parse_fail')}/{b.get('e1b_n_batches')}", flush=True)
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
