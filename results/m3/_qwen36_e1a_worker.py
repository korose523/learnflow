#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_qwen36_e1a_worker.py —— qwen36:latest E1-A 缺口补齐器（关闭 ④b 的 S3 规模档）。

背景（2026-09-26 诊断）：
  * 门禁 verify_m3_matrix.py 报「矩阵触及规模档数 2 < 3」→ FAIL。
  * 根因：local_matrix.jsonl 中 qwen36:latest 只有 142 条**唯一** E1-A 键（181 条记录里 39 条重复），
    低于 build_matrix_rows.py 的 ≥200 题门槛，故该 S3(30–70B) 单元格被静默排除，
    CSV 只剩 S1 + S2 两档。
  * qwen36:latest = 34.7B / MoE / IQ3_S → 落在 S3 档；补齐到 212 唯一键即可让 CSV 触及 S1/S2/S3 三档，
    使门禁从 FAIL 转为 PASS（这是 ④b「≥3 参数规模档」的唯一可行闭合路径——
    盘上唯一 S3+ 模型就是它，deepseek-v2:16b 仅 15.7B 属 S2，补它不会增加规模档）。

环境会杀掉后台任务，故本 worker 自己负责：
  * 若 Ollama 不在，拉起 `ollama serve`（detached）；
  * 循环调用 local_matrix_e1ab.py 跑 qwen36 E1-A，靠 load_done 断点续跑；
  * 任一次 driver 失败（Ollama 抖动）则等待后重试，直至唯一键达 212。

数字纪律：不手写任何统计量，全部由驱动脚本与 build_matrix_rows.py 产出。
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA = r"C:/Users/mac/AppData/Local/Programs/Ollama/ollama.exe"
PYV = r"C:/Users/mac/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
DRIVER = r"E:/learnflow/results/m3/local_matrix_e1ab.py"
META = "results/m3/local_matrix_meta.json"
JSONL = Path("E:/learnflow/results/m3/local_matrix.jsonl")
MODEL = "qwen36:latest"
COND = "E1A"
TARGET = 212
DEADLINE = time.time() + 14 * 3600
DETACH = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def count_unique():
    """统计该模型 E1-A 的唯一键数量。"""
    u = set()
    try:
        for line in open(JSONL, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("cond") == COND and d.get("model") == MODEL:
                k = d.get("key")
                if k is not None:
                    u.add(k)
    except Exception:
        pass
    return len(u)


def ollama_up():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_ollama():
    if ollama_up():
        return True
    print("[worker] Ollama down; starting serve...", flush=True)
    try:
        subprocess.Popen(
            [OLLAMA, "serve"],
            cwd="E:/learnflow",
            stdout=open("E:/learnflow/results/m3/_ollama_serve_worker.log", "ab"),
            stderr=subprocess.STDOUT,
            creationflags=DETACH,
        )
    except Exception as exc:  # noqa: BLE001
        print("[worker] failed to start ollama:", exc, flush=True)
    for _ in range(60):
        time.sleep(2)
        if ollama_up():
            print("[worker] Ollama up.", flush=True)
            return True
    return False


def main():
    start = count_unique()
    print(f"[worker] start; {MODEL} {COND} unique={start}/{TARGET}, need {max(0, TARGET - start)} more",
          flush=True)
    while time.time() < DEADLINE:
        n = count_unique()
        print(f"[worker] {MODEL} {COND} unique={n}/{TARGET}", flush=True)
        if n >= TARGET:
            print("[worker] DONE: reached 212 unique E1-A keys.", flush=True)
            sys.exit(0)
        if not ensure_ollama():
            print("[worker] cannot start Ollama; retry in 60s", flush=True)
            time.sleep(60)
            continue
        r = subprocess.run(
            [PYV, DRIVER, "--models", MODEL,
             "--meta-file", META,
             "--conditions", COND, "--out", "results/m3/local_matrix"],
            cwd="E:/learnflow", capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        tail = "\n".join((r.stdout or "").splitlines()[-8:])
        err = "\n".join((r.stderr or "").splitlines()[-5:])
        print(f"[worker] driver rc={r.returncode} count={count_unique()}", flush=True)
        if tail:
            print(tail, flush=True)
        if err:
            print("[worker] stderr:", err, flush=True)
        if count_unique() < TARGET:
            print("[worker] not complete; wait 45s then retry", flush=True)
            time.sleep(45)
    print("[worker] TIMEOUT 14h; final =", count_unique(), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
