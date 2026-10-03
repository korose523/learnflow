#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_mistral_targeted.py —— ④b 定向加速器（仅 mistral:7b）

目的：主批次驱动器 run_batch_remaining.py(FCtlR6) 串行跑全部 6 模型且对已完成模型
重跑 E1B 多轮批次，要轮到 mistral 还需先爬完 llama3.1/qwen3:8b 的重跑。但 ④b 硬约束
只需 ≥3 族（F1/F2/F3），**不要求 deepseek(F4)**。mistral E1B 当前仅 3/108，
补满即可解锁 D1/D2/D3。故本脚本只跑 mistral:7b，并行于旧驱动、互不冲突：
  * JSONL 追加写，无竞争；
  * 断点续跑跳过已完成的 cell（mistral E1A 212 已完成、E1B 仅 3 个）；
  * 不涉及 16B 模型，无内存峰值风险；
  * 旧驱动最终仍会补 deepseek（作为第 4 族加分），与本脚本不重复冲突。

纪律：不改写任何协议/统计逻辑；失败原样记录并继续。
"""
import json
import os
import shutil
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
TARGETS = ["mistral:7b"]


def local_models() -> set:
    try:
        with urllib.request.urlopen(TAGS, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {m["name"] for m in d.get("models", [])}
    except Exception:  # noqa: BLE001
        return set()


def wait_current(timeout_s: int = 900) -> bool:
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
    print(f"\n=== 启动 {model}（定向加速）===", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(BASE), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    try:
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
    print("\n[ALL] 定向驱动器结束", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
