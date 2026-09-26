#!/usr/bin/env python3
# 收尾专用：仅补 deepseek-v2:16b 的 E1-B（断点续跑 20/108 -> 108），
# 然后重生成 m3_model_scale_matrix.csv 并跑门禁，落盘报告。
import subprocess, sys, time, os, urllib.request
ROOT = r"E:/learnflow/results/m3"
PY = r"C:/Users/mac/.workbuddy/binaries/python/versions/3.13.12/python.exe"
DRIVER = os.path.join(ROOT, "local_matrix_e1ab.py")
BUILD = os.path.join(ROOT, "build_matrix_rows.py")
GATE = os.path.join(ROOT, "verify_m3_matrix.py")
JSONL = os.path.join(ROOT, "local_matrix.jsonl")
CSV = os.path.join(ROOT, "m3_model_scale_matrix.csv")
REPORT = os.path.join(ROOT, "_resume_deepseek_e1b_out.txt")
API = "http://localhost:11434/api/tags"

def log(*a):
    msg = " ".join(str(x) for x in a)
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, flush=True)

def run(cmd, timeout=60*60*6):
    log(">>>", " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    for line in (p.stdout or "").splitlines():
        log("   ", line)
    if p.stderr:
        for line in p.stderr.splitlines()[-30:]:
            log("  !", line)
    return p.returncode

def ollama_health():
    try:
        urllib.request.urlopen(API, timeout=5)
        return True
    except Exception:
        return False

def main():
    open(REPORT, "w", encoding="utf-8").close()
    log("=== resume start", time.strftime("%F %T"))
    if not ollama_health():
        log("[FATAL] ollama 未起")
        return
    meta = '{"deepseek-v2:16b": {"family":"DeepSeek","params_b":15.7,"architecture":"dense"}}'
    rc = run([PY, DRIVER, "--models", "deepseek-v2:16b", "--conditions", "E1B",
              "--out", JSONL.replace(".jsonl", ""), "--meta", meta, "--retry-rounds", "2"])
    log(f"[deepseek E1B] driver rc={rc}")
    # 重生成 CSV + 门禁
    run([PY, BUILD, "--csv-out", CSV])
    rc, out = run([PY, GATE, "--matrix", CSV])
    log(f"[GATE] exit={rc}")
    # 汇总 deepseek 行
    import csv
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    for r in rows:
        if r["model_id"] == "deepseek-v2:16b":
            log(f"[deepseek] {r}")
    log("=== resume done", time.strftime("%F %T"))

if __name__ == "__main__":
    main()
