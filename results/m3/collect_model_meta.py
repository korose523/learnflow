#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_model_meta.py —— 小模型批次元数据实测采集
从运行中的 Ollama /api/show 实测每个模型的 family / parameter_size /
quantization_level，写入 results/m3/local_matrix_meta_small.json。
纪律：params_b 一律取实测值，绝不猜测；取不到的记 null。
"""
import json
import sys
import urllib.request

MODELS = [
    "qwen3:1.7b",
    "qwen3:8b",
    "llama3.2:1b",
    "llama3.1:8b",
    "mistral:7b",
    "deepseek-v2:16b",
]

FAMILY_DISPLAY = {
    "qwen3": "Qwen",
    "llama": "Llama",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
}

#: 分类法按「发布方」定族，不用 /api/show 的 family 字段——该字段反映**架构谱系**
#: （Mistral 基于 Llama 架构，实测返回 family=llama；DeepSeek-V2 返回 deepseek2），
#: 直接采用会把 Mistral 误并入 F2_Llama、虚增族覆盖数。
#: 依据：`docs/LearnFlow_研究总档.md` 的 F1–F4 划分（Qwen / Llama / Mistral / DeepSeek）。
TAG_TAXONOMY = {
    "qwen3:1.7b": "Qwen",
    "qwen3:8b": "Qwen",
    "llama3.2:1b": "Llama",
    "llama3.1:8b": "Llama",
    "mistral:7b": "Mistral",
    "deepseek-v2:16b": "DeepSeek",
}

API = "http://127.0.0.1:11434/api/show"


def measure(model: str) -> dict:
    req = urllib.request.Request(
        API, data=json.dumps({"model": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "family": None, "params_b": None,
                "quantization": None, "architecture": None}
    det = d.get("details", {}) or {}
    fam_raw = det.get("family") or ""
    base_fam = fam_raw.split("Model")[0].lower()
    # 分类法按发布方（TAG_TAXONOMY），架构谱系字段仅作留痕
    display = TAG_TAXONOMY.get(model) or FAMILY_DISPLAY.get(base_fam, fam_raw or None)
    ps = det.get("parameter_size") or ""
    try:
        params_b = float(ps.replace("B", "").strip()) if ps.endswith("B") else None
    except ValueError:
        params_b = None
    return {
        "family": display,
        "params_b": params_b,
        "quantization": det.get("quantization_level"),
        "architecture": ("MoE" if "moe" in json.dumps(d.get("model_info", {})).lower()
                         else "dense"),
        "measured_parameter_size": ps,
        "measured_families": det.get("families"),
        "digest": d.get("digest", "")[:16],
        "note": ("params_b/quantization measured from /api/show 2026-09-24; "
                 "never guessed"),
    }


def main() -> int:
    out = {}
    for m in MODELS:
        meta = measure(m)
        if "error" in meta:
            print(f"[skip] {m}: {meta['error']}", file=sys.stderr)
            continue
        out[m] = meta
        print(f"[ok]   {m}: family={meta['family']} params_b={meta['params_b']} "
              f"quant={meta['quantization']} arch={meta['architecture']}")
    path = "E:/learnflow/results/m3/local_matrix_meta_small.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"written: {path} ({len(out)} models)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
