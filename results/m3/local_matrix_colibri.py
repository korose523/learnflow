#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_matrix_colibri.py —— colibri（OpenAI 兼容 /v1/chat/completions）传输层适配器
================================================================================

背景
--------------------------------------------------------------------------------
M3 模型-规模矩阵在旧机器（E:/learnflow，无独立显卡，15.8 GB RAM）上以 ollama 完成
了 8/12 格；F4_DeepSeek S3（deepseek-r1:32b，19 GB 权重）因内存不足被判定不可行
（results/m3/m3_s3_infeasibility_20260927.md）。

本机（D:/learnflow-main，RTX 5080 16 GB + 32 GB RAM）装有 colibri 1.12.1 推理引擎
（纯 C，CUDA sm_120 后端），当前以 int4-gs64 量化常驻 Qwen3.6-35B-A3B（22 GB 权重，
ollama 当时跑的是 IQ3_S）。这使两件事成为可能：

  (1) **同族 S3 格的跨引擎复现性验证**：qwen36:latest（ollama IQ3_S）vs
      qwen3.6-colibri（colibri int4-gs64）——同基座模型、不同推理栈与量化，
      若 ρ 可复现则证明矩阵结论不依赖推理后端；
  (2) 为将来接入 colibri 的 DeepSeek V4 引擎预留同一传输层（本脚本与模型无关）。

协议保真
--------------------------------------------------------------------------------
**本脚本不复制、不改动任何协议或统计代码。** E1-A/E1-B 提示词、JSON schema、轮数、
批大小、种子、Bradley-Terry 拟合、bootstrap——全部经 importlib 直接复用审计产物
local_matrix_e1ab.py 的同一函数对象（单一事实来源）。本脚本只替换三个"传输层"入口：

    e1.ask          ollama /api/generate(约束解码) → colibri /v1/chat/completions
                    + prefill 续写等效约束（qwen36 引擎无 grammar payload，
                    response_format 一律 HTTP 400——详见 colibri_ask 内说明）
    e1.model_show   ollama /api/show → colibri /v1/models（模型身份留痕）
    e1.QUESTIONS_CSV / e1.O13_PATH   旧机器盘符 E: → 本机 D: 路径

运行环境：需要 numpy/scipy（受管 venv）。colibri 服务需已在
http://127.0.0.1:8000/v1 运行（D:\\colibri\\start_qwen36.cmd serve）。

用法
--------------------------------------------------------------------------------
    python local_matrix_colibri.py --selftest
    python local_matrix_colibri.py --models "qwen3.6-colibri" \
        --meta '{"qwen3.6-colibri":{"family":"Qwen","params_b":35,"architecture":"MoE"}}' \
        --conditions E1A --limit 3          # 冒烟
    python local_matrix_colibri.py --models "qwen3.6-colibri" --meta '...' \
        --conditions E1A,E1B --out results/m3/local_matrix_colibri
    python local_matrix_colibri.py --dump-matrix --out results/m3/local_matrix_colibri

退出码：0 正常；1 自测 FAIL；2 输入缺失/参数错误/colibri 不可达
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

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

#: colibri 网关（OpenAI 兼容）
COLIBRI_API_BASE = "http://127.0.0.1:8000/v1"

#: 引擎身份（来自 D:\\colibri\\MODELS.md，用于 model_digest 留痕）
ENGINE_INFO = {
    "engine": "colibri 1.12.1",
    "backend": "CUDA sm_120 (coli_cuda.dll)",
    "api": "OpenAI-compatible /v1/chat/completions",
    "constraint": "自由解码（qwen36 引擎无 grammar payload）+ schema 容器归一化 + enable_thinking=False",
}


# ═══════════════════════════════════════════════════════════════════
#  传输层：colibri chat completions（prefill 续写模式）
# ═══════════════════════════════════════════════════════════════════

#: 依 schema.required 选择的助手前缀（与 SCHEMA_DIFF3 / SCHEMA_RANK 声明的对象形状一致）。
#: 注意：续写前缀**不能以空白结尾**（网关拒绝：模板会剥离尾部空白，模型将从不同字节处
#: 续写）；空格由模型回复开头携带，raw 重建时拼回。
_PREFILL_BY_REQUIRED = {
    "difficulty": '{"difficulty":',
    "ranking": '{"ranking":[',
}


def _truncate_at_container_end(text: str) -> str:
    """把 raw 截断到 JSON 容器闭合处（回退路径；见 _normalize_prefill_completion）。"""
    brace = text.find("{")
    brack = text.find("[")
    if brace != -1:
        end = text.find("}", brace)
        if end != -1:
            return text[:end + 1]
    if brack != -1:
        end = text.find("]", brack)
        if end != -1:
            return text[:end + 1]
    return text


def _normalize_prefill_completion(prefill: str, content: str) -> str:
    """把续写补全归一化为 ollama format=schema 本会产出的**精确容器形状**。

    实测（2026-09-27，题 219 探针）：Qwen3.6-35B 在前缀 '{"difficulty":' 后先吐标签
    ' 2'，随后**追加 schema 禁止的额外字段**（' , "reasoning": ...'）直至截断。约束
    解码下这些字段会被语法抑制——本函数把传输层归一化做在同一位置：
      E1-A：标签 = 前缀后的首个数字串 → raw = '{"difficulty": <数字>}'；
      E1-B：截到首个 ']' 并补闭合 '}'（数组元素之后的内容一律丢弃）；
      前缀后非数字开头（异常路径）→ 退回容器截断，交还解析器/重试如实记失败。
    归一化只作用于**容器之外/之后**的模型输出，标签 token 本身逐字保留。
    """
    import re
    if prefill == '{"difficulty":':
        m = re.match(r"\s*(\d+)", content)
        if m:
            return '{"difficulty": ' + m.group(1) + "}"
        return _truncate_at_container_end(prefill + content)
    if prefill == '{"ranking":[':
        full = prefill + content
        idx = full.find("]")
        if idx != -1:
            return full[:idx + 1] + "}"
        return _truncate_at_container_end(full)
    return _truncate_at_container_end(prefill + content)


def colibri_ask(model: str, prompt: str, num_predict: int = 64,
                schema: Optional[dict] = None, api_base: str = COLIBRI_API_BASE,
                timeout: int = 600) -> str:
    """与 e1.ask 同签名：temperature=0 + **prefill 续写**实现与 ollama 约束解码的等价。

    约束机制的诚实说明（2026-09-27 实测与源码考据）：
    - colibri 的 qwen36 引擎子进程只讲 6 字段 SUBMIT 头，不带 grammar payload
      扩展（family capabilities.grammar_payload=False），response_format 一律 HTTP 400；
    - 但网关支持**尾随 assistant 续写**（resolve_generation_prompt 默认开启，
      openai_server.py:2503-2523；qwen 渲染分支 :1444-1453 以预闭合 <think></think>
      + 前缀文本、去终止符的方式渲染开放回合）；
    - 因此：把 schema 声明的容器前缀（如 '{"difficulty": '）作为 assistant 前缀，
      模型在 greedy 下续写标签——条件分布 P(label | prompt, 前缀) 与 ollama
      format=schema 逐 token 强制**同条件**（被强制生成的容器 token 不改变
      标签的条件分布），stop=["\\n"] 截去容器外的任何附加文本；
    - 显式 enable_thinking=False（qwen36 默认即 False，openai_server.py:5185）。
    提示词、schema 定义、解析、统计全部不变（复用 e1 同一函数对象）。
    """
    prefill = ""
    if schema is not None and isinstance(schema, dict):
        for req_key in (schema.get("required") or []):
            if req_key in _PREFILL_BY_REQUIRED:
                prefill = _PREFILL_BY_REQUIRED[req_key]
                break
    messages = [{"role": "user", "content": prompt}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})
    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": num_predict,
        "stream": False,
        "enable_thinking": False,
        "stop": ["\n"],
    }
    req = urllib.request.Request(
        api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        detail = ""
        try:
            detail = ex.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {ex.code}: {detail}") from None
    choice = (d.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    if "</think>" in content:                     # 防御：网关已剥，双保险
        content = content.split("</think>", 1)[1]
    # 服务器续写请求只返回**新增** token；若实现返回了含前缀的完整文本则去重
    if prefill and content.lstrip().startswith(prefill.strip()):
        raw = content
    else:
        raw = prefill + content
    if prefill:
        raw = _normalize_prefill_completion(prefill, raw[len(prefill):]
                                            if raw.startswith(prefill) else content)
    raw = e1._sanitize(raw.strip())
    return raw


def colibri_model_show(model: str, api_base: str = COLIBRI_API_BASE,
                       timeout: int = 30) -> Dict[str, Any]:
    """与 e1.model_show 同签名：/v1/models 实测身份 + 引擎留痕。"""
    try:
        with urllib.request.urlopen(api_base.rstrip("/") + "/models", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        ids = [m.get("id") for m in data.get("data", [])]
        hit = model if model in ids else next((i for i in ids if i and i.startswith(model)), None)
        return {
            "digest": hit,
            "digest_source": "colibri/v1/models",
            "served_model_ids": ids,
            "model_info_subset": dict(ENGINE_INFO),
            "raw_top_keys": sorted(data.keys()),
        }
    except Exception as ex:
        return {"error": f"{type(ex).__name__}: {str(ex)[:120]}"}


def require_server(api_base: str, model: str, timeout: int = 10) -> None:
    """启动前硬检查：colibri 不可达或模型未加载 → 立即退出（绝不空跑产生假数据）。"""
    info = colibri_model_show(model, api_base=api_base, timeout=timeout)
    if info.get("error"):
        print(f"[fatal] colibri 不可达：{info['error']}", file=sys.stderr)
        print("        请先在 D:\\colibri 运行 start_qwen36.cmd serve", file=sys.stderr)
        sys.exit(2)
    if not info.get("digest"):
        print(f"[fatal] colibri 已运行但未加载模型 {model}；在线模型：{info.get('served_model_ids')}",
              file=sys.stderr)
        sys.exit(2)
    print(f"[colibri] OK: served={info.get('served_model_ids')} engine={ENGINE_INFO['engine']}",
          flush=True)


# ═══════════════════════════════════════════════════════════════════
#  CLI（镜像原脚本参数；--api-base/--out 默认值改为 colibri 语义）
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="colibri 版已审计协议标注矩阵驱动脚本（传输层适配器）")
    ap.add_argument("--models", type=str, default="")
    ap.add_argument("--meta", type=str, default="")
    ap.add_argument("--meta-file", type=str, default="")
    ap.add_argument("--conditions", type=str, default="E1A,E1B")
    ap.add_argument("--limit", type=int, default=0, help="仅取前 N 题（子集冒烟）")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--api-base", type=str, default=COLIBRI_API_BASE)
    ap.add_argument("--out", type=str, default=str(HERE / "local_matrix_colibri"))
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

    # —— 传输层补丁（协议/统计代码零改动，仅换传输） ——
    e1.ask = colibri_ask
    e1.model_show = colibri_model_show

    require_server(args.api_base, models[0])

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

    for model in models:
        b = summary["models"].get(model, {})
        print(f"  {model}: E1A ρ(listwise)={b.get('e1a_spearman')} "
              f"CI={b.get('e1a_spearman_ci95')} | "
              f"E1A ρ(none_as_zero)={b.get('e1a_spearman_none_as_zero')} | "
              f"parsed={b.get('e1a_n_parsed')}/{b.get('e1a_n_total')} | "
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
