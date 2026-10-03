#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_batch_remaining.py —— ④b 小模型批次剩余跑批的串行驱动器

职责（不含任何新逻辑，只负责调度与等待）：
  1. 等待当前正在跑的 llama3.2:1b（E1-A + E1-B）结束，避免 VRAM/并发争抢；
  2. 依次等待目标模型在本地 `ollama list` 中出现（拉取完成后自动继续）；
  3. 对每个目标模型串行调用 results/m3/local_matrix_e1ab.py
     --conditions "E1A,E1B"（同一批题目 DBE-212、同一套已审计协议）；
  4. qwen3:1.7b 只有 E1-A，断点续跑会自动只补 E1-B。

纪律：不改写任何协议/统计逻辑；不虚构度量；失败原样记录并继续下一个。
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# 仓库根可用 LEARNFLOW_ROOT 覆盖；默认按本文件位置（results/m3/）推导
BASE = Path(os.environ.get("LEARNFLOW_ROOT", Path(__file__).resolve().parents[2]))
M3 = BASE / "results" / "m3"
PY = os.environ.get("PYTHON", sys.executable)  # 原为硬编码本机解释器路径，已移除
DRIVER = str(M3 / "local_matrix_e1ab.py")
META = "results/m3/local_matrix_meta_small.json"
OUT = "results/m3/local_matrix"
JSONL = str(M3 / "local_matrix.jsonl")
TAGS = "http://127.0.0.1:11434/api/tags"

#: 目标模型（严格串行；已完成的单元格由断点续跑自动跳过）
TARGETS = ["qwen3:1.7b", "llama3.2:1b", "llama3.1:8b", "qwen3:8b",
           "mistral:7b", "deepseek-v2:16b"]


def local_models() -> set:
    try:
        with urllib.request.urlopen(TAGS, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {m["name"] for m in d.get("models", [])}
    except Exception:  # noqa: BLE001
        return set()


def jsonl_condition_count(model: str, cond: str) -> int:
    try:
        with open(JSONL, encoding="utf-8") as f:
            return sum(1 for line in f
                       if f'"{model}"' in line and f'"{cond}"' in line)
    except FileNotFoundError:
        return 0


def wait_current(timeout_s: int = 900) -> bool:
    """等待 Ollama 服务可用（不再以"E1B 记录出现"为完成判据——那会在刚启动时误判）。"""
    print("[wait] 等待 Ollama 服务可用…", flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/version",
                                        timeout=5) as r:
                if r.status == 200:
                    print("[wait] 服务就绪", flush=True)
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10)
    print("[wait] 服务未就绪，放弃", flush=True)
    return False


def run_model(model: str) -> None:
    cmd = [PY, DRIVER, "--models", model, "--meta-file", META,
           "--conditions", "E1A,E1B", "--out", OUT]
    print(f"\n=== 启动 {model} ===", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(BASE), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    # local_matrix.json 每次跑批会被整体覆盖，故按模型留存一份副本，
    # 否则先跑完模型的 ρ/CI 汇总会丢失（build_matrix_rows.py 依赖这些值）。
    try:
        import shutil
        src = str(M3 / "local_matrix.json")
        dst = str(M3 / f"local_matrix__{model.replace(':', '_')}.json")
        if os.path.isfile(src):
            shutil.copyfile(src, dst)
            print(f"[save] 汇总副本 -> {dst}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 汇总副本保存失败：{exc}", flush=True)
    tail = "\n".join((proc.stdout or "").splitlines()[-8:])
    print(tail, flush=True)
    if proc.returncode != 0:
        print(f"[FAIL] {model} 退出码 {proc.returncode}", flush=True)
        print((proc.stderr or "")[-800:], flush=True)
    else:
        print(f"[done] {model} 用时 {(time.time() - t0) / 60:.1f} min", flush=True)


def main() -> int:
    if not wait_current():
        return 1
    for m in TARGETS:
        t0 = time.time()
        while m not in local_models():
            if time.time() - t0 > 5400:
                print(f"[skip] {m} 尚未拉取完成，跳过", flush=True)
                break
            print(f"[wait] {m} 等待拉取…", flush=True)
            time.sleep(30)
        else:
            run_model(m)
    print("\n[ALL] 批次驱动器结束", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
