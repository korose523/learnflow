import json, time, subprocess, sys
from pathlib import Path
JSONL = Path("E:/learnflow/results/m3/local_matrix.jsonl")
PYV = r"C:/Users/mac/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
BUILD = r"E:/learnflow/results/m3/build_matrix_rows.py"
CSV = r"E:/learnflow/results/m3/m3_model_scale_matrix.csv"
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
            r = subprocess.run([PYV, BUILD, "--csv-out", CSV], cwd="E:/learnflow",
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
