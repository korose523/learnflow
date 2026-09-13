#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 难度标注 v2 —— 修复 v1 强负结果的算法升级。

v1 负结果诊断（2026-09-12）：
  (1) num_predict=16 截断 thinking 模型的 <think> 块，解析到的数字来自思考文本（标签无效）；
  (2) 绝对评级退化：78% 题被标 1（easy），专家 2/3 级大面积塌缩到 1。

v2 修复：
  * format:json 语法约束解码（实测从第 1 个 token 强制 JSON，机制上消灭 <think> 块；/no_think 软开关实测不稳定）；
  * E1-A: 锚定量表绝对评级（题面 1200 字符）——隔离提示词修复的贡献；
  * E1-B: 批量排序 → 两两约束 → Bradley-Terry 强度（相对判断，绕开绝对校准）——核心升级；
  * E2-X: XES 5 级锚定量表重跑。
输出：results/code/llm_labeling_v2.jsonl（逐条 flush，断点续跑）+ llm_labeling_v2.json
"""
import csv, json, math, os, random, time, urllib.request
from collections import defaultdict, Counter
import numpy as np
from scipy import stats as st

BASE = r"E:/learnflow"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "results", "code")
JSONL = os.path.join(OUT, "llm_labeling_v2.jsonl")
SUMMARY = os.path.join(OUT, "llm_labeling_v2.json")
MODEL = "qwen36"
API = "http://127.0.0.1:11434/api/generate"

random.seed(20260912)


def ask(prompt, num_predict=64, schema=None):
    body = {"model": MODEL, "prompt": prompt, "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": 0, "num_predict": num_predict},
            "keep_alive": "60m"}
    req = urllib.request.Request(API, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("response", "").strip()


SCHEMA_DIFF3 = {"type": "object",
                "properties": {"difficulty": {"type": "integer", "enum": [1, 2, 3]}},
                "required": ["difficulty"], "additionalProperties": False}
SCHEMA_DIFF5 = {"type": "object",
                "properties": {"难度": {"type": "integer", "enum": [1, 2, 3, 4, 5]}},
                "required": ["难度"], "additionalProperties": False}
# array-of-enum: forces stable, parse-safe letter output (string form failed 55% of the time)
SCHEMA_RANK = {"type": "object",
               "properties": {"ranking": {"type": "array",
                                          "items": {"type": "string",
                                                    "enum": ["A", "B", "C", "D", "E", "F"]}}},
               "required": ["ranking"], "additionalProperties": False}


def parse_json_obj(txt):
    try:
        return json.loads(txt)
    except Exception:
        try:
            a, b = txt.index("{"), txt.rindex("}")
            return json.loads(txt[a:b + 1])
        except Exception:
            return {}


def last_digit(txt, valid):
    for ch in reversed(txt):
        if ch.isdigit() and int(ch) in valid:
            return int(ch)
    return None


# ---------- resume infrastructure ----------
def load_done():
    done = set()
    if os.path.exists(JSONL):
        with open(JSONL, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    # failed parses (llm=None / ok_parse=False) get retried on resume
                    if r["cond"] == "E1B":
                        if r.get("ok_parse"):
                            done.add((r["cond"], r["key"]))
                    elif r.get("llm") is not None:
                        done.add((r["cond"], r["key"]))
                except Exception:
                    pass
    return done


DONE = load_done()
print(f"[resume] {len(DONE)} records already present", flush=True)
jout = open(JSONL, "a", encoding="utf-8")


def record(cond, key, payload):
    jout.write(json.dumps({"cond": cond, "key": key, **payload}, ensure_ascii=False) + "\n")
    jout.flush()


# ---------- E1 data ----------
qs = []  # (qid, expert, text)
with open(os.path.join(DATA, "dbe_kt22", "csv", "Questions.csv"), encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            t = (d.get("question_text") or d.get("question_rich_text") or "")
            qs.append((d["id"], int(d["difficulty"]), t[:1200].strip()))
        except (ValueError, TypeError):
            pass
print(f"[E1] DBE questions: {len(qs)}", flush=True)

RUBRIC3 = ("Rating scale (anchored):\n"
           "1 = routine: single concept, direct application of a definition or a one-step query/statement.\n"
           "2 = medium: requires combining 2+ concepts, multi-step reasoning, or non-obvious formulation.\n"
           "3 = hard: complex design, tricky edge cases, nested/recursive structures, or subtle correctness issues.")

# ---------- E1-A: rubric absolute ----------
print("[E1-A] start", flush=True)
t0 = time.time()
for i, (qid, expert, text) in enumerate(qs):
    if ("E1A", qid) in DONE:
        continue
    prompt = ("You are rating the difficulty of a database-course exercise for university students.\n" + RUBRIC3 +
              "\n\nExercise:\n" + text +
              "\n\nRate the difficulty.")
    try:
        raw = ask(prompt, schema=SCHEMA_DIFF3)
    except Exception as ex:
        raw = ""
        print("[E1A ERR]", qid, str(ex)[:80], flush=True)
    lab = last_digit(raw, {1, 2, 3})
    record("E1A", qid, {"expert": expert, "llm": lab, "raw": raw[-40:]})
    if (i + 1) % 25 == 0:
        print(f"[E1-A] {i+1}/{len(qs)} elapsed={time.time()-t0:.0f}s", flush=True)

# ---------- E1-B: batch ranking + Bradley-Terry ----------
print("[E1-B] start", flush=True)
ids = [q[0] for q in qs]
by_id = {q[0]: q for q in qs}
N_ROUNDS, BATCH = 3, 6
parse_fail = 0
for rnd in range(N_ROUNDS):
    order = ids[:]
    random.shuffle(order)
    batches = [order[i:i + BATCH] for i in range(0, len(order), BATCH)]
    for bi, batch in enumerate(batches):
        key = f"r{rnd}b{bi}"
        if ("E1B", key) in DONE:
            continue
        lines = [f"{chr(65 + j)}. {by_id[qid][2]}" for j, qid in enumerate(batch)]
        prompt = ("You are ranking database-course exercises by difficulty for university students. "
                  "Order them from EASIEST to HARDEST.\n" + RUBRIC3 +
                  "\n\nExercises:\n" + "\n\n".join(lines) +
                  "\n\nOutput a JSON array of the letters, easiest first, e.g. [\"B\", \"A\", \"C\"].")
        try:
            raw = ask(prompt, num_predict=60, schema=SCHEMA_RANK)
        except Exception as ex:
            raw = ""
            print("[E1B ERR]", key, str(ex)[:80], flush=True)
        obj = parse_json_obj(raw)
        sr = obj.get("ranking", []) if isinstance(obj, dict) else []
        if isinstance(sr, str):                      # legacy string form
            seq = [ch for ch in sr if ch.isalpha() and ch.isupper()]
        else:
            seq = [str(x).strip().upper()[:1] for x in sr]
        seq = [ch for ch in seq if ch.isalpha() and ord(ch) - 65 < len(batch)]
        ok_parse = len(seq) == len(batch) and len(set(seq)) == len(batch)
        if not ok_parse:
            parse_fail += 1
        record("E1B", key, {"round": rnd, "batch_ids": batch, "order": seq,
                            "ok_parse": ok_parse, "raw": raw[-60:]})
    print(f"[E1-B] round {rnd+1}/{N_ROUNDS} done elapsed={time.time()-t0:.0f}s parse_fail={parse_fail}", flush=True)

# ---------- E2-X: XES rubric absolute ----------
print("[E2-X] start", flush=True)
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
        emp[q] = (math.log((1 - p_) / p_), n)
keys = sorted(emp, key=lambda k: emp[k][0])
quart = np.array_split(keys, 4)
rng = np.random.default_rng(20260912)
sample = []
for gi, g in enumerate(quart):
    idx = rng.choice(len(g), size=min(30, len(g)), replace=False)
    for i in idx:
        sample.append((g[i], gi))
print(f"[E2-X] XES sample: {len(sample)}", flush=True)

RUBRIC5 = ("难度锚定量表：1=直接套公式或一步计算；2=两三步计算；3=需要多步推理或组合两个知识点；"
           "4=需要构造性思路或分类讨论；5=需要巧妙的构造、复杂分类或竞赛级技巧。")
t0e2 = time.time()
for i, (qid, gi) in enumerate(sample):
    if ("E2X", qid) in DONE:
        continue
    m = questions[qid]
    content = (m.get("content") or "")[:1000]
    opts = m.get("options") or []
    opt_txt = (" ".join(o for o in opts if o))[:300] if opts else ""
    prompt = ("你在为小学数学题评定难度。\n" + RUBRIC5 +
              "\n\n题目：" + content + ("\n选项：" + opt_txt if opt_txt else "") +
              "\n\n评定这道题的难度。")
    try:
        raw = ask(prompt, schema=SCHEMA_DIFF5)
    except Exception as ex:
        raw = ""
        print("[E2X ERR]", qid, str(ex)[:80], flush=True)
    lab = last_digit(raw, {1, 2, 3, 4, 5})
    record("E2X", qid, {"emp_quartile": gi, "llm": lab, "raw": raw[-40:]})
    if (i + 1) % 20 == 0:
        print(f"[E2-X] {i+1}/{len(sample)} elapsed={time.time()-t0e2:.0f}s", flush=True)

# ================= aggregation =================
print("[agg] reading back", flush=True)
# dedupe: last record per (cond, key) wins (retries supersede failed attempts)
last = {}
with open(JSONL, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
            last[(r["cond"], r["key"])] = r
        except Exception:
            pass
recs = defaultdict(list)
for (c, k), r in last.items():
    recs[c].append(r)

results = {"model": MODEL, "design": "v2: /no_think + anchored rubric + batch-ranking Bradley-Terry",
           "end": time.strftime("%F %T")}


def e1_metrics(pairs, name):
    ok = [(e, l) for e, l in pairs if l is not None]
    if not ok:
        return {"n": len(pairs), "n_parsed": 0}
    ye = [e for e, _ in ok]; yl = [l for _, l in ok]
    acc = float(np.mean([a == b for a, b in ok]))
    rho = st.spearmanr(ye, yl)
    n = len(ok)
    pe = sum((Counter(ye)[k] / n) * (Counter(yl)[k] / n) for k in set(ye) | set(yl))
    kappa = (acc - pe) / (1 - pe) if pe < 1 else None
    return {"n": n, "n_parsed": n,
            "accuracy": round(acc, 4), "spearman": [round(float(rho.statistic), 4), round(float(rho.pvalue), 8)],
            "cohen_kappa": round(kappa, 4) if kappa is not None else None,
            "llm_dist": {str(k): v for k, v in sorted(Counter(yl).items())},
            "confusion": {f"{k[0]}|{k[1]}": v for k, v in sorted(Counter(ok).items())}}


# E1-A metrics
e1a_pairs = [(r["expert"], r.get("llm")) for r in recs["E1A"]]
results["E1A_rubric_absolute"] = e1_metrics(e1a_pairs, "E1A")

# E1-B: Bradley-Terry from rankings
wins = defaultdict(float)   # (i,j) -> wins of i over j (i harder)
opp = defaultdict(float)
for r in recs["E1B"]:
    if not r.get("ok_parse"):
        continue
    seq = r["order"]          # easiest -> hardest
    batch = r["batch_ids"]
    for a in range(len(seq)):
        for b in range(a + 1, len(seq)):
            harder, easier = batch[ord(seq[b]) - 65], batch[ord(seq[a]) - 65]
            wins[(harder, easier)] += 1
            opp[(harder, easier)] += 1
            opp[(easier, harder)] += 1

# logistic-gradient BT fit
idx = {q: i for i, q in enumerate(ids)}
S = np.zeros(len(ids))
pairs = [(idx[a], idx[b], w, opp[(a, b)]) for (a, b), w in wins.items() if opp[(a, b)] > 0]
for it in range(400):
    G = np.zeros(len(ids)); H = np.zeros(len(ids))
    for i, j, w, n in pairs:
        d = S[i] - S[j]
        p = 1 / (1 + math.exp(-max(min(d, 30), -30)))
        G[i] += w - n * p; G[j] -= w - n * p
        H[i] += n * p * (1 - p); H[j] += n * p * (1 - p)
    S += G / np.maximum(H, 1e-9)
S -= S.mean()
rho_bt = st.spearmanr([by_id[q][1] for q in ids], S)
# discretize BT into tertiles -> 3 levels
t1, t2 = np.percentile(S, [33.3, 66.7])
bt_lab = [1 if s <= t1 else (2 if s <= t2 else 3) for s in S]
results["E1B_batch_ranking_BT"] = {
    "n_ranking_batches": len(recs["E1B"]),
    "parse_fail": sum(1 for r in recs["E1B"] if not r.get("ok_parse")),
    "n_pair_constraints": len(pairs),
    "spearman_BT_vs_expert": [round(float(rho_bt.statistic), 4), round(float(rho_bt.pvalue), 8)],
    "accuracy_tertile": round(float(np.mean([by_id[q][1] == l for q, l in zip(ids, bt_lab)])), 4),
    "cohen_kappa_tertile": None,
}
# kappa for tertile
ye = [by_id[q][1] for q in ids]; yl = bt_lab
po = float(np.mean([a == b for a, b in zip(ye, yl)]))
pe = sum((Counter(ye)[k] / len(ye)) * (Counter(yl)[k] / len(yl)) for k in set(ye) | set(yl))
results["E1B_batch_ranking_BT"]["cohen_kappa_tertile"] = round((po - pe) / (1 - pe), 4) if pe < 1 else None
print("[E1-B] BT spearman", results["E1B_batch_ranking_BT"]["spearman_BT_vs_expert"],
      "acc", results["E1B_batch_ranking_BT"]["accuracy_tertile"], flush=True)

# E2-X metrics
e2 = recs["E2X"]
ok2 = [r for r in e2 if r.get("llm") is not None]
if ok2:
    y_q = [r["emp_quartile"] for r in ok2]; y_l = [r["llm"] - 1 for r in ok2]
    rho2 = st.spearmanr(y_q, y_l)
    results["E2X_rubric_absolute"] = {
        "n": len(e2), "n_parsed": len(ok2),
        "spearman_quartile_vs_llm": [round(float(rho2.statistic), 4), round(float(rho2.pvalue), 8)],
        "within_1_quartile_rate": round(float(np.mean([abs(a - b) <= 1 for a, b in zip(y_q, y_l)])), 4),
        "llm_mean_by_quartile": {str(g): round(float(np.mean([r["llm"] for r in ok2 if r["emp_quartile"] == g])), 3)
                                 for g in range(4)},
    }

with open(SUMMARY, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("DONE ->", SUMMARY, flush=True)
print(json.dumps(results, ensure_ascii=False, indent=1)[:2000], flush=True)
