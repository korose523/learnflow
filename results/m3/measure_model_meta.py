#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""measure_model_meta.py —— 从本机 Ollama /api/show 实测模型身份，追加到 meta 文件。

纪律：params_b / quantization / architecture 一律**实测**，严禁猜测或抄写网页值。
若 /api/show 未返回 parameter_size，则 params_b 记 null（scale_tier 落 UNKNOWN），
由下游 build_matrix_rows.py 据实标注，不得手工补数。

用法：
  python measure_model_meta.py deepseek-r1:1.5b \
      --meta-file results/m3/local_matrix_meta_small.json --family DeepSeek
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:11434/api"


def show(model: str) -> dict:
    req = urllib.request.Request(
        API + "/show",
        data=json.dumps({"name": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_params(text: str | None) -> float | None:
    """'1.8B' -> 1.8 ; '815.0M' -> 0.815 ; None -> None"""
    if not text:
        return None
    t = text.strip().upper().replace(" ", "")
    try:
        if t.endswith("B"):
            return float(t[:-1])
        if t.endswith("M"):
            return round(float(t[:-1]) / 1000.0, 4)
        if t.endswith("K"):
            return round(float(t[:-1]) / 1e6, 6)
    except ValueError:
        return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--meta-file", required=True)
    ap.add_argument("--family", required=True, help="F1_Qwen / F2_Llama / F3_Mistral / F4_DeepSeek 的族名")
    args = ap.parse_args()

    info = show(args.model)
    det = info.get("details") or {}
    size = det.get("parameter_size")
    quant = det.get("quantization_level")
    fam = det.get("family")
    fams = det.get("families") or ([fam] if fam else [])
    arch = "MoE" if any("moe" in str(f).lower() for f in fams) else "dense"
    params_b = parse_params(size)

    entry = {
        "family": args.family,
        "params_b": params_b,
        "quantization": quant or "",
        "architecture": arch,
        "measured_parameter_size": size or "",
        "measured_families": fams,
        "digest": (info.get("digest") or ""),
        "note": ("params_b/quantization measured from /api/show %s; never guessed"
                 % __import__("datetime").date.today().isoformat()),
    }

    path = Path(args.meta_file)
    meta = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    meta[args.model] = entry
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({args.model: entry}, ensure_ascii=False, indent=2))
    print("written -> %s" % path)
    if params_b is None:
        print("⚠ /api/show 未返回 parameter_size：params_b 记 null，scale_tier 将落 UNKNOWN（不得猜测）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
