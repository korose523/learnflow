import json, os, time, subprocess, sys
from pathlib import Path
# 仓库根可用 LEARNFLOW_ROOT 覆盖；默认按本文件位置（results/m3/）推导
BASE = Path(os.environ.get("LEARNFLOW_ROOT", Path(__file__).resolve().parents[2]))
M3 = BASE / "results" / "m3"
JSONL = M3 / "local_matrix.jsonl"
PYV = os.environ.get("PYTHON", sys.executable)  # 原为硬编码本机解释器路径，已移除
BUILD = str(M3 / "build_matrix_rows.py")
CSV = str(M3 / "m3_model_scale_matrix.csv")
TARGET = 108
deadline = time.time() + 4*3600
prev = 0
while time.time() < deadline:
    uniq = set()
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
                uniq.add(d.get("key"))
    except Exception:
        pass
    n = len(uniq)
    if n != prev:
        print(f"[monitor] mistral E1B unique={n}/{TARGET}", flush=True)
        prev = n
    if n >= TARGET:
        print("[monitor] 108 reached, settling 60s...", flush=True)
        time.sleep(60)
        uniq2 = set()
        for line in open(JSONL):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("cond") == "E1B" and d.get("model") == "mistral:7b":
                uniq2.add(d.get("key"))
        if len(uniq2) >= TARGET:
            print("[monitor] stable; running build_matrix_rows.py --csv-out", flush=True)
            r = subprocess.run([PYV, BUILD, "--csv-out", CSV], cwd=str(BASE),
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            sys.stdout.write(r.stdout)
            sys.stdout.flush()
            sys.stderr.write("=== build stderr (tail) ===\n")
            sys.stderr.write(r.stderr[-1500:])
            sys.stderr.flush()
            sys.exit(0)
        else:
            print(f"[monitor] count dropped to {len(uniq2)}, continuing", flush=True)
    time.sleep(30)
print("[monitor] TIMEOUT: 108 not reached within 4h", flush=True)
sys.exit(2)
