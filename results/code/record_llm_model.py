#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record_llm_model.py —— 固化 LLM 标注所用模型的 manifest / digest / 量化 / 基座
=============================================================================

为什么需要这个脚本（审阅意见 4.4 · 5.1）
-----------------------------------------------------------------------------
稿件把标注模型写成「qwen3-6B 量级」，而代码里只有 `MODEL = "qwen36"` 一个标签。
官方 Qwen3 dense 系列（0.6B/1.7B/4B/8B/14B/32B）**没有 6B**，因此仅凭标签无法确定
基座模型、量化与版本 —— 而 M3 的标题与结论是「LLM 难度先验的可靠性边界」这种一般
命题，评审人第一个问题必然是「这是哪个模型的极限」。

本脚本从 Ollama 的模型目录直接读取事实（不依赖 ollama 服务在线）：
  * manifest 文件的 sha256（等价于 ollama 报告的模型 digest）
  * config digest + GGUF 数据层 digest / 字节数
  * config 里的 model_format（gguf）与 file_type（量化类型）
  * GGUF 头部 KV 元数据里的基座模型名 / 组织 / 架构 / 许可证

输出 results/code/llm_model_manifest.json，并把结果登记进 llm_labeling_v2.json。

用法
-----------------------------------------------------------------------------
    python results/code/record_llm_model.py
    python results/code/record_llm_model.py --model qwen36 --out results/code/llm_model_manifest.json

退出码
-----------------------------------------------------------------------------
    0  成功写出模型元数据
    1  模型未在本地 Ollama 目录中找到（如实报告，不编造）
    2  脚本执行失败
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path
from typing import Any, Dict, Optional

BASE = Path(__file__).resolve().parent.parent.parent
CODE = BASE / "results" / "code"

#: GGUF 元数据类型 → 字节宽度（0..12，9=ARRAY 单独处理）
_GGUF_SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
_GGUF_FMT = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "B", 10: "Q", 11: "q", 12: "d"}


def _ollama_models_dir() -> Path:
    env = os.environ.get("OLLAMA_MODELS")
    if env:
        return Path(env)
    return Path.home() / ".ollama" / "models"


def _read_gguf_meta(blob: Path, budget: int = 6_000_000) -> Dict[str, Any]:
    """只读 GGUF 文件头部，取出 general.* 等标量/字符串 KV。数组只记录形状。"""
    with blob.open("rb") as f:
        buf = f.read(budget)
    off = 0

    def u32() -> int:
        nonlocal off
        v = struct.unpack_from("<I", buf, off)[0]; off += 4; return v

    def u64() -> int:
        nonlocal off
        v = struct.unpack_from("<Q", buf, off)[0]; off += 8; return v

    def s() -> str:
        nonlocal off
        n = u64(); v = buf[off:off + n].decode("utf-8", "replace"); off += n; return v

    def val(t: int) -> Any:
        nonlocal off
        if t == 8:
            return s()
        if t == 9:
            et = u32(); n = u64()
            if et == 9:
                return [s() for _ in range(n)]
            off += _GGUF_SIZES.get(et, 0) * n
            return f"<array type={et} n={n}>"
        v = struct.unpack_from("<" + _GGUF_FMT[t], buf, off)[0]
        off += _GGUF_SIZES[t]
        return v

    if buf[:4] != b"GGUF":
        raise ValueError("不是 GGUF 文件（magic 不匹配）")
    off = 4
    gguf_version = u32()
    tensor_count = u64()
    kv_count = u64()
    meta: Dict[str, Any] = {}
    for _ in range(kv_count):
        try:
            k = s(); t = u32(); v = val(t)
        except Exception:  # noqa: BLE001 —— 元数据条目超出读取窗口，到此为止
            break
        if not isinstance(v, list):
            meta[k] = v
    return {
        "gguf_version": gguf_version,
        "tensor_count": tensor_count,
        "metadata_kv_count": kv_count,
        "metadata": meta,
    }


def collect(model: str, tag: str = "latest") -> Optional[Dict[str, Any]]:
    root = _ollama_models_dir()
    manifest = root / "manifests" / "registry.ollama.ai" / "library" / model / tag
    if not manifest.is_file():
        return None
    raw = manifest.read_bytes()
    man = json.loads(raw)

    cfg = man.get("config") or {}
    cfg_digest = cfg.get("digest", "")
    out: Dict[str, Any] = {
        "ollama_tag": f"{model}:{tag}",
        "code_label": model,
        "manifest_path": str(manifest),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "config_digest": cfg_digest,
        "model_format": None,
        "quantization_level": None,
        "layers": [{"mediaType": l.get("mediaType"), "size": l.get("size"),
                    "digest": l.get("digest")} for l in man.get("layers", [])],
    }

    cfg_blob = root / "blobs" / cfg_digest.replace(":", "-") if cfg_digest else None
    if cfg_blob and cfg_blob.is_file():
        c = json.loads(cfg_blob.read_text(encoding="utf-8"))
        out["model_format"] = c.get("model_format")
        out["quantization_level"] = c.get("file_type")
        out["container_architecture"] = c.get("architecture")

    # GGUF 数据层：基座模型与许可证的唯一事实来源
    gguf_layer = next((l for l in out["layers"]
                       if l["mediaType"] == "application/vnd.ollama.image.model"), None)
    if gguf_layer:
        blob = root / "blobs" / gguf_layer["digest"].replace(":", "-")
        if blob.is_file():
            try:
                g = _read_gguf_meta(blob)
                out["gguf"] = g
                md = g["metadata"]
                out["base_model"] = {
                    "name": md.get("general.name"),
                    "size_label": md.get("general.size_label"),
                    "architecture": md.get("general.architecture"),
                    "quantized_by": md.get("general.quantized_by"),
                    "license": md.get("general.license"),
                    "repo_url": md.get("general.base_model.0.repo_url"),
                    "upstream_name": md.get("general.base_model.0.name"),
                    "upstream_organization": md.get("general.base_model.0.organization"),
                }
            except Exception as exc:  # noqa: BLE001
                out["gguf_error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="固化 LLM 标注模型元数据")
    ap.add_argument("--model", default="qwen36", help="Ollama 模型名（代码中的 MODEL 常量）")
    ap.add_argument("--tag", default="latest")
    ap.add_argument("--out", default=str(CODE / "llm_model_manifest.json"))
    args = ap.parse_args()

    try:
        rec = collect(args.model, args.tag)
    except Exception as exc:  # noqa: BLE001
        print(f"[record_llm_model] 执行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if rec is None:
        print(f"[record_llm_model] 未在 {_ollama_models_dir()} 找到模型 {args.model}:{args.tag}；"
              f"不编造元数据。请在有该模型的机器上重跑本脚本。", file=sys.stderr)
        return 1

    rec["_note"] = ("M3 稿件曾把标注模型写为「qwen3-6B 量级」。实测代码标签 qwen36 指向 "
                    "Ollama 上的该模型，基座与量化以本文件的 base_model / quantization_level 为准。")
    Path(args.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bm = rec.get("base_model") or {}
    print(f"model      : {rec['ollama_tag']}")
    print(f"manifest   : sha256:{rec['manifest_sha256']}")
    print(f"format/quant: {rec.get('model_format')} / {rec.get('quantization_level')}")
    print(f"base model : {bm.get('name')} ({bm.get('architecture')}, size_label={bm.get('size_label')})")
    print(f"saved -> {args.out}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
