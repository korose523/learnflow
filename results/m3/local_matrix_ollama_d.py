#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_matrix_ollama_d.py —— ollama 传输层适配器（本机 D: 路径版）
================================================================================

背景
--------------------------------------------------------------------------------
M3 模型-规模矩阵在旧机器（E:/learnflow，无独显，15.8 GB RAM）上以 ollama 完成 8/12 格；
新机器（D:/learnflow-main，RTX 5080 16 GB + 32 GB RAM）沿用同一套已审计协议补齐剩余格。
`local_matrix_e1ab.py` 是协议/统计单一事实来源，但其 `BASE=Path("E:/learnflow")` 在现机不存在。

本适配器与 `local_matrix_colibri.py` 同构，但**保留 ollama 传输层**（不覆盖 e1.ask /
e1.model_show），仅做两件事：
  (1) 把 e1.QUESTIONS_CSV / e1.O13_PATH 从旧 E: 路径补丁到本机 D: 路径；
  (2) 提供 ollama 可达性硬检查（require_ollama）。

协议、统计、档位推导、断点续跑、bootstrap 全部复用 e1 同一函数对象（零改动）。

运行环境：需要 numpy/scipy（受管 venv）。ollama serve 需已在 http://127.0.0.1:11434 运行。

用法
--------------------------------------------------------------------------------
    python local_matrix_ollama_d.py --selftest
    python local_matrix_ollama_d.py --models "ministral-3:3b" \
        --meta '{"ministral-3:3b":{"family":"Mistral","params_b":3,"architecture":"dense"}}' \
        --conditions E1A --limit 3          # 冒烟
    python local_matrix_ollama_d.py --models "ministral-3:3b,mixtral:8x7b,deepseek-r1:32b" \
        --meta-file results/m3/m3_fill_meta.json \
        --conditions E1A,E1B --out results/m3/local_matrix_fill
    python local_matrix_ollama_d.py --dump-matrix --out results/m3/local_matrix_fill

退出码：0 正常；1 自测 FAIL；2 输入缺失/参数错误/ollama 不可达/模型未拉取
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

# ─────────────────────────── 复用审计实现（单一事实来源） ───────────────────────────
HERE = Path(__file__).resolve().parent
E1AB_PATH = HERE / "local_matrix_e1ab.py"

import importlib.util

_spec = importlib.util.spec_from_file_location("local_matrix_e1ab", E1AB_PATH)
if _spec is None or _spec.loader is None:
    raise SystemExit(f"[fatal] 无法加载审计实现：{E1AB_PATH}")
e1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e1)   # 需要 numpy/scipy（受管 venv）

# ─────────────────────────── 本机路径补丁（旧 E: → 本机 D:） ───────────────────────────
PROJ = HERE.parent.parent            # results/m3 → 项目根
e1.QUESTIONS_CSV = PROJ / "data" / "dbe_kt22" / "csv" / "Questions.csv"
e1.O13_PATH = PROJ / "results" / "code" / "o13_llm_protocol_audit.py"

#: ollama 网关（/api/generate + format 约束解码）
OLLAMA_API_BASE = "http://127.0.0.1:11434/api"


def require_ollama(api_base: str, models: List[str], timeout: int = 10) -> None:
    """启动前硬检查：ollama 不可达或任一模型未拉取 → 立即退出（绝不空跑产生假数据）。"""
    try:
        req = urllib.request.Request(api_base.rstrip("/") + "/tags")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        names = {m.get("name") for m in data.get("models", [])}
    except Exception as ex:
        print(f"[fatal] ollama 不可达：{type(ex).__name__}: {str(ex)[:120]}", file=sys.stderr)
        print("        请先启动 ollama serve（ollama serve 或桌面客户端）", file=sys.stderr)
        sys.exit(2)
    missing = [m for m in models if m not in names and (m + ":latest") not in names]
    if missing:
        print(f"[fatal] 以下模型尚未拉取，请先 ollama pull：{missing}", file=sys.stderr)
        sys.exit(2)
    print(f"[ollama] OK: 已加载模型数={len(names)}，待评模型全部就位", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="ollama 版已审计协议标注矩阵驱动脚本（D: 路径适配器）")
    ap.add_argument("--models", type=str, default="")
    ap.add_argument("--meta", type=str, default="")
    ap.add_argument("--meta-file", type=str, default="")
    ap.add_argument("--conditions", type=str, default="E1A,E1B")
    ap.add_argument("--limit", type=int, default=0, help="仅取前 N 题（子集冒烟）")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--api-base", type=str, default=OLLAMA_API_BASE)
    ap.add_argument("--out", type=str, default=str(HERE / "local_matrix_fill"))
    ap.add_argument("--csv-out", type=str, default="")
    ap.add_argument("--retry-rounds", type=int, default=1)
    ap.add_argument("--dump-matrix", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    csv_out = Path(args.csv_out) if args.csv_out else out_base.parent / (out_base.name + "_rows.csv")

    if args.selftest:
        return e1.selftest(reps=min(args.reps, 60) if args.reps else 60)
    if args.dump_matrix:
        return e1.dump_matrix(out_base, csv_out)
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
        if not Path(args.meta_file).is_file():
            print(f"[fatal] --meta-file 不存在：{args.meta_file}", file=sys.stderr)
            return 2
        meta.update(json.loads(Path(args.meta_file).read_text(encoding="utf-8")))
    if args.meta:
        meta.update(json.loads(args.meta))

    # —— 保留 ollama 传输层（不覆盖 e1.ask / e1.model_show） ——
    require_ollama(args.api_base, models)

    qs = e1.load_questions()
    if args.limit and args.limit > 0:
        qs = qs[:args.limit]
    print(f"[data] DBE-KT22 questions: {len(qs)}（{e1.QUESTIONS_CSV}）", flush=True)

    assert "You are rating the difficulty of a database-course exercise" in e1.build_e1a_prompt("X")
    run_cells = e1.run_models(models, meta, conditions, qs, out_base, args.reps,
                              args.api_base, args.timeout, retry_rounds=args.retry_rounds)
    summary = e1.aggregate(models, qs, out_base, args.reps)
    path = e1.write_summary(summary, run_cells, out_base)
    print(f"\n[done] summary -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
