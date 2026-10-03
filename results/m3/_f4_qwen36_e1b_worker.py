#!/usr/bin/env python3
# 自包含 worker：补全 ④b 矩阵的两个缺口
#   1) qwen36:latest 的 E1-B（108 批 BT）
#   2) F4_DeepSeek: deepseek-v2:16b 的 E1-A + E1-B（新拉权重）
# 跑完重生成 m3_model_scale_matrix.csv 并跑门禁，落盘报告。
import subprocess, sys, time, json, os, urllib.request, shutil

ROOT = r"E:/learnflow/results/m3"
PY = r"C:/Users/mac/.workbuddy/binaries/python/versions/3.13.12/python.exe"
DRIVER = os.path.join(ROOT, "local_matrix_e1ab.py")
BUILD = os.path.join(ROOT, "build_matrix_rows.py")
GATE = os.path.join(ROOT, "verify_m3_matrix.py")
JSONL = os.path.join(ROOT, "local_matrix.jsonl")
CSV = os.path.join(ROOT, "m3_model_scale_matrix.csv")
REPORT = os.path.join(ROOT, "_f4_e1b_out.txt")
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
    return p.returncode, p.stdout

def ollama_health():
    try:
        urllib.request.urlopen(API, timeout=5)
        return True
    except Exception:
        return False

def ensure_ollama():
    for _ in range(3):
        if ollama_health():
            log("[ollama] up")
            return True
        # 先尝试 kill 掉可能卡在 502 的进程
        try:
            subprocess.run(["taskkill", "/f", "/im", "ollama.exe"],
                           capture_output=True, timeout=15)
        except Exception:
            pass
        time.sleep(3)
        # 启动 serve（detach）
        try:
            subprocess.Popen(["ollama", "serve"], cwd=ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log("[ollama] serve start err:", e)
        for _ in range(20):
            time.sleep(3)
            if ollama_health():
                log("[ollama] up after serve")
                return True
    return ollama_health()

def pull(model):
    log(f"[pull] {model} ...")
    for attempt in range(4):
        rc, _ = run(["ollama", "pull", model], timeout=60*60*3)
        if rc == 0:
            log(f"[pull] {model} ok")
            return True
        log(f"[pull] attempt {attempt+1} failed, retry")
        time.sleep(5)
    return False

def main():
    open(REPORT, "w", encoding="utf-8").close()
    log("=== start", time.strftime("%F %T"))
    if not ensure_ollama():
        log("[FATAL] ollama 起不来，退出")
        return
    try:
        # ---- 1) qwen36 E1-B ----
        log("==== STEP1 qwen36 E1-B ====")
        rc, _ = run([PY, DRIVER,
                     "--models", "qwen36:latest",
                     "--conditions", "E1B",
                     "--out", JSONL.replace(".jsonl", ""),
                     "--meta-file", os.path.join(ROOT, "local_matrix_meta.json"),
                     "--retry-rounds", "2"])
        log(f"[STEP1] qwen36 E1B rc={rc}")

        # 卸 qwen36 释放显存，再拉 deepseek
        try:
            subprocess.run(["ollama", "stop", "qwen36:latest"], capture_output=True, timeout=30)
        except Exception:
            pass

        # ---- 2) F4 DeepSeek: deepseek-v2:16b ----
        log("==== STEP2 F4 deepseek-v2:16b ====")
        if not pull("deepseek-v2:16b"):
            log("[WARN] deepseek-v2:16b 拉取失败，跳过 F4；继续生成 CSV")
        else:
            meta = json.dumps({"deepseek-v2:16b": {
                "family": "DeepSeek", "params_b": 15.7, "architecture": "dense"}})
            rc, _ = run([PY, DRIVER,
                         "--models", "deepseek-v2:16b",
                         "--conditions", "E1A,E1B",
                         "--out", JSONL.replace(".jsonl", ""),
                         "--meta", meta,
                         "--retry-rounds", "2"])
            log(f"[STEP2] deepseek E1A+E1B rc={rc}")

        # ---- 3) 重生成 CSV + 门禁 ----
        log("==== STEP3 build CSV + gate ====")
        run([PY, BUILD, "--csv-out", CSV])
        rc, out = run([PY, GATE, "--matrix", CSV])
        log(f"[GATE] exit={rc}")

        # ---- 4) 汇总单元格数 ----
        import csv
        rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
        fams = sorted({r["family"] for r in rows})
        tiers = sorted({r["scale_tier"] for r in rows})
        log(f"[SUMMARY] cells={len(rows)} families={fams} tiers={tiers}")
        for r in rows:
            log(f"   {r['model_id']:18s} {r['family']:10s} {r['scale_tier']:10s} "
                f"ρ={r['spearman_rho']} parse={r['parse_rate']} e1a_usable={r.get('reliability_verdict','')[:40]}")
    except Exception as e:
        log("[EXC]", repr(e))
    log("=== done", time.strftime("%F %T"))

if __name__ == "__main__":
    main()
