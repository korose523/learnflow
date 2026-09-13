#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 难度标注实验（Ollama qwen36）。
E1: DBE-KT22 212 题（英文，专家 1/2/3 难度 = ground truth）
E2: XES3G5M 按经验难度四分位分层抽样 120 题（中文，对比经验难度四分位）
输出：results/code/llm_labeling.jsonl（逐条）+ llm_labeling.json（汇总）"""
import csv
import json
import math
import os
import time
import urllib.request
from collections import defaultdict

import numpy as np

BASE = r"E:/learnflow"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "results", "code")
MODEL = "qwen36"
API = "http://127.0.0.1:11434/api/generate"

def ask(prompt):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 16},
                       "keep_alive": "30m"}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("response", "").strip()

def parse_label(txt, valid):
    for ch in txt:
        if ch.isdigit() and int(ch) in valid:
            return int(ch)
    return None

results = {"model": MODEL, "start": time.strftime("%F %T")}
JSONL = os.path.join(OUT, "llm_labeling.jsonl")

def load_done():
    done = set()
    if os.path.exists(JSONL):
        with open(JSONL, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get("llm") is not None:
                        done.add((r["exp"], r["qid"]))
                except Exception:
                    pass
    return done

DONE = load_done()
print(f"[resume] {len(DONE)} records already labeled", flush=True)

jout = open(JSONL, "a", encoding="utf-8")

def record(rec):
    jout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    jout.flush()

# ---------- E1 DBE-KT22 ----------
qs = []
with open(os.path.join(DATA, "dbe_kt22", "csv", "Questions.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            qs.append((d["id"], int(d["difficulty"]), (d.get("question_text") or d.get("question_rich_text") or "")[:600]))
        except (ValueError, TypeError):
            pass
print(f"[E1] DBE questions: {len(qs)}", flush=True)
e1 = []
t0 = time.time()
for i, (qid, expert, text) in enumerate(qs):
    if ("E1_dbe", qid) in DONE:
        continue
    text = text.replace("<img", " [image] <img").strip()
    prompt = ("You are rating the difficulty of a database-course exercise for university students. "
              "Answer with a single digit only.\n"
              "1 = easy, 2 = medium, 3 = hard.\n\nExercise:\n" + text + "\n\nDifficulty (single digit):")
    try:
        raw = ask(prompt)
    except Exception as ex:
        raw = ""
        print("[E1 ERR]", qid, str(ex)[:80], flush=True)
    lab = parse_label(raw, {1, 2, 3})
    e1.append({"qid": qid, "expert": expert, "llm": lab, "raw": raw[:30]})
    record({"exp": "E1_dbe", **e1[-1]})
    if (i + 1) % 20 == 0:
        print(f"[E1] {i+1}/{len(qs)} elapsed={time.time()-t0:.0f}s", flush=True)
with open(os.path.join(OUT, "llm_labeling.jsonl"), "a", encoding="utf-8") as _:
    pass
# reload ALL E1 records (including resumed) from jsonl for correct aggregation
e1 = []
with open(JSONL, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
            if r["exp"] == "E1_dbe":
                e1.append({"qid": r["qid"], "expert": r["expert"], "llm": r["llm"]})
        except Exception:
            pass
ok = [r for r in e1 if r["llm"] is not None]
from scipy import stats as st
y_exp = [r["expert"] for r in ok]; y_llm = [r["llm"] for r in ok]
acc = float(np.mean([a == b for a, b in zip(y_exp, y_llm)]))
rho = st.spearmanr(y_exp, y_llm)
kappa_pairs = [(a, b) for a, b in zip(y_exp, y_llm)]
from collections import Counter
po = acc
pe = sum((Counter(y_exp)[k] / len(y_exp)) * (Counter(y_llm)[k] / len(y_llm)) for k in set(y_exp) | set(y_llm))
kappa = (po - pe) / (1 - pe) if pe < 1 else None
results["E1_dbe_kt22"] = {
    "n": len(e1), "n_parsed": len(ok), "parse_rate": round(len(ok) / len(e1), 4),
    "accuracy": round(acc, 4), "spearman": [round(float(rho.statistic), 4), round(float(rho.pvalue), 8)],
    "cohen_kappa": round(kappa, 4) if kappa is not None else None,
    "confusion": {str(k): v for k, v in sorted(Counter((a, b) for a, b in kappa_pairs).items())},
    "elapsed_s": round(time.time() - t0, 1),
}
print("[E1] acc=%.4f rho=%.4f kappa=%.4f" % (acc, rho.statistic, kappa), flush=True)

# ---------- E2 XES3G5M ----------
XES = os.path.join(DATA, "xes3g5m", "XES3G5M")
questions = json.load(open(os.path.join(XES, "metadata", "questions.json"), encoding="utf-8"))
per_q = defaultdict(lambda: [0, 0])
with open(os.path.join(XES, "kc_level", "train_valid_sequences.csv"), encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f):
        qsx = (row.get("questions") or "").split(",")
        rs = (row.get("responses") or "").split(",")
        for q, c in zip(qsx, rs):
            if q in ("-1", "", "NaN") or c not in ("0", "1"):
                continue
            e = per_q[q]; e[0] += 1; e[1] += int(c)
emp = {}
for q, (n, nc) in per_q.items():
    if n >= 200 and q in questions and questions[q].get("content"):
        p_ = (nc + 0.5) / (n + 1.0)
        emp[q] = (math.log((1 - p_) / p_), n)   # 难度，正=难
# 按难度四分位分层抽样 4×30
keys = sorted(emp, key=lambda k: emp[k][0])
quart = np.array_split(keys, 4)
rng = np.random.default_rng(20260912)
sample = []
for gi, g in enumerate(quart):
    idx = rng.choice(len(g), size=min(30, len(g)), replace=False)
    for i in idx:
        sample.append((g[i], gi))
print(f"[E2] XES sample: {len(sample)}", flush=True)
e2 = []
t0 = time.time()
for i, (qid, gi) in enumerate(sample):
    if ("E2_xes", qid) in DONE:
        continue
    m = questions[qid]
    content = (m.get("content") or "")[:400]
    opts = m.get("options") or []
    opt_txt = (" ".join(o for o in opts if o))[:200] if opts else ""
    prompt = ("你在为小学数学题评定难度。只回答一个数字：1（很容易）、2（容易）、3（中等）、4（较难）、5（很难）。\n\n题目："
              + content + ("\n选项：" + opt_txt if opt_txt else "") + "\n\n难度（单个数字）：")
    try:
        raw = ask(prompt)
    except Exception as ex:
        raw = ""
        print("[E2 ERR]", qid, str(ex)[:80], flush=True)
    lab = parse_label(raw, {1, 2, 3, 4, 5})
    e2.append({"qid": qid, "emp_quartile": gi, "llm": lab, "raw": raw[:30]})
    record({"exp": "E2_xes", **e2[-1]})
    if (i + 1) % 20 == 0:
        print(f"[E2] {i+1}/{len(sample)} elapsed={time.time()-t0:.0f}s", flush=True)
# reload ALL E2 records for aggregation
e2 = []
with open(JSONL, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
            if r["exp"] == "E2_xes":
                e2.append({"qid": r["qid"], "emp_quartile": r["emp_quartile"], "llm": r["llm"]})
        except Exception:
            pass
ok2 = [r for r in e2 if r["llm"] is not None]
y_q = [r["emp_quartile"] for r in ok2]; y_l = [r["llm"] - 1 for r in ok2]   # 0-4 对齐四分位 0-3
rho2 = st.spearmanr(y_q, y_l)
acc_q = float(np.mean([abs(a - b) <= 1 for a, b in zip(y_q, y_l)]))
results["E2_xes3g5m"] = {
    "n": len(e2), "n_parsed": len(ok2),
    "spearman_quartile_vs_llm": [round(float(rho2.statistic), 4), round(float(rho2.pvalue), 8)],
    "within_1_quartile_rate": round(acc_q, 4),
    "llm_mean_by_quartile": {str(g): round(float(np.mean([r["llm"] for r in ok2 if r["emp_quartile"] == g])), 3)
                             for g in range(4)},
    "elapsed_s": round(time.time() - t0, 1),
}
print("[E2] rho=%.4f within1=%.4f" % (rho2.statistic, acc_q), flush=True)

results["end"] = time.strftime("%F %T")
with open(os.path.join(OUT, "llm_labeling.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("DONE -> results/code/llm_labeling.json", flush=True)
