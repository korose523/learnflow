#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_mistral_worker.py —— 自修复 mistral:7b E1B 填充器。

环境会杀掉后台任务，故本 worker 自己负责：
  * 若 Ollama 不在，拉起 `ollama serve`（detached）；
  * 循环调用 local_matrix_e1ab.py 跑 mistral E1B，靠 load_done 断点续跑；
  * 任一次 driver 失败（Ollama 抖动）则等待后重试，直至 mistral E1B 唯一键达 108。
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
JSONL = Path("E:/learnflow/results/m3/local_matrix.jsonl")
TARGET = 108
DEADLINE = time.time() + 8 * 3600
DETACH = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def count():
    u = set()
    try:
        for line in open(JSONL):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("cond") == "E1B" and d.get("model") == "mistral:7b":
                u.add(d.get("key"))
    except Exception:
        pass
    return len(u)


def ollama_up():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version",
                                     timeout=5) as r:
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
    for _ in range(40):
        time.sleep(2)
        if ollama_up():
            print("[worker] Ollama up.", flush=True)
            return True
    return False


def main():
    print("[worker] start; target mistral E1B unique =", TARGET, flush=True)
    while time.time() < DEADLINE:
        n = count()
        print(f"[worker] mistral E1B unique={n}/{TARGET}", flush=True)
        if n >= TARGET:
            print("[worker] DONE.", flush=True)
            sys.exit(0)
        if not ensure_ollama():
            print("[worker] cannot start Ollama; retry in 60s", flush=True)
            time.sleep(60)
            continue
        r = subprocess.run(
            [PYV, DRIVER, "--models", "mistral:7b",
             "--meta-file", "results/m3/local_matrix_meta_small.json",
             "--conditions", "E1B", "--out", "results/m3/local_matrix"],
            cwd="E:/learnflow", capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        tail = "\n".join((r.stdout or "").splitlines()[-6:])
        print(f"[worker] driver rc={r.returncode} count={count()}", flush=True)
        print(tail, flush=True)
        if count() < TARGET:
            print("[worker] not complete; wait 30s then retry", flush=True)
            time.sleep(30)
    print("[worker] TIMEOUT 8h", flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
