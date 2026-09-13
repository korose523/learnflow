# -*- coding: utf-8 -*-
"""一次性构建难度实验缓存（Junyi + DBE-KT22）。

动机：O6a（样本效率曲线）需要"每个练习的 k 条随机子样本"，O6b（bootstrap）需要
完整聚合量。反复扫描 2.8GB / 16M 行日志不可行，故一次扫描同时产出：
  * 全量聚合（n / ok / hint / dur / att / up / down / rep）
  * 蓄水池抽样（K=500）的原始行，用于任意 k<=500 的无偏子样本
蓄水池算法保证 slot 之间可交换 → 取前 k 个 slot 即为大小 k 的简单随机子样本。

输出 results/code/difficulty_cache.npz
"""
import csv, json, os, random, sys, time
import numpy as np

BASE = "E:/learnflow"
OUT = BASE + "/results/code/difficulty_cache.npz"
K = 500                       # reservoir size
random.seed(20260913)

# ---------------------------------------------------------------- Junyi
FIELDS = ["ok", "hint", "dur", "att", "up", "down", "rep"]   # 0/1/秒/次数/0/1/0/1
agg = {}          # ucid -> dict(full aggregates)
res = {}          # ucid -> np.ndarray (7, K)


def slot():
    a = {"n": 0, "ok": 0, "hint": 0, "dur": 0.0, "att": 0, "up": 0, "down": 0, "rep": 0}
    return a


t0 = time.time()
cnt = 0
with open(BASE + "/data/junyi/Log_Problem.csv", encoding="utf-8", newline="") as f:
    rd = csv.DictReader(f)
    for row in rd:
        c = row["ucid"]
        a = agg.get(c)
        if a is None:
            a = agg[c] = slot()
        a["n"] += 1
        ok = 1 if row["is_correct"] == "True" else 0
        hint = 1 if row["is_hint_used"] == "True" else 0
        up = 1 if row["is_upgrade"] == "True" else 0
        down = 1 if row["is_downgrade"] == "True" else 0
        rep = 0 if row["exercise_problem_repeat_session"] == "1" else 1
        try:
            dur = float(row["total_sec_taken"])
        except (ValueError, TypeError):
            dur = 0.0
        try:
            att = int(row["total_attempt_cnt"])
        except (ValueError, TypeError):
            att = 1
        a["ok"] += ok
        a["hint"] += hint
        a["dur"] += dur
        a["att"] += att
        a["up"] += up
        a["down"] += down
        a["rep"] += rep

        # ---- reservoir
        n = a["n"]
        r = res.get(c)
        if n <= K:
            if r is None:
                r = res[c] = np.zeros((len(FIELDS), K), dtype=np.float32)
            r[:, n - 1] = (ok, hint, dur, att, up, down, rep)
        else:
            j = random.randrange(n)
            if j < K:
                r[:, j] = (ok, hint, dur, att, up, down, rep)

        cnt += 1
        if cnt % 2_000_000 == 0:
            print("junyi rows", cnt // 1_000_000, "M |", round(time.time() - t0, 1), "s", flush=True)

print("junyi done", cnt, "rows", len(agg), "exercises", round(time.time() - t0, 1), "s", flush=True)

# 只保留有量且有专家难度的练习，压缩保存
meta = {}
with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = row["difficulty"]
DIFF = {"easy": 1, "normal": 2, "hard": 3}

keep = [c for c, a in agg.items() if a["n"] >= 1000 and meta.get(c) in DIFF]
keep.sort()
print("junyi keep", len(keep), flush=True)

nJ = len(keep)
J_full = np.zeros((nJ, len(FIELDS) + 1), dtype=np.float64)      # n + 7 sums
J_res = np.zeros((nJ, len(FIELDS), K), dtype=np.float32)
J_y = np.zeros(nJ, dtype=np.int8)
for i, c in enumerate(keep):
    a = agg[c]
    J_full[i] = [a["n"], a["ok"], a["hint"], a["dur"], a["att"], a["up"], a["down"], a["rep"]]
    J_res[i] = res[c]
    J_y[i] = DIFF[meta[c]]

# ---------------------------------------------------------------- DBE-KT22
import datetime as dt
expert = {}
with open(BASE + "/data/dbe_kt22/csv/Questions.csv", encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            expert[d["id"]] = int(d["difficulty"])
        except (ValueError, TypeError):
            pass

DF = ["n", "ok", "hint", "dur", "dfb", "tfb"]        # 6 fields
dagg = {}
dres = {}
with open(BASE + "/data/dbe_kt22/csv/Transaction.csv", encoding="utf-8-sig", errors="replace") as f:
    for row in csv.DictReader(f):
        q = row["question_id"]
        if q not in expert or row["is_hidden"] == "true":
            continue
        a = dagg.get(q)
        if a is None:
            a = dagg[q] = {"n": 0, "ok": 0, "hint": 0, "dur": 0.0, "dfb": 0.0, "tfb": 0.0,
                           "ndfb": 0, "ntfb": 0, "ndur": 0}
        a["n"] += 1
        ok = 1 if row["answer_state"] == "true" else 0
        hint = 1 if row["hint_used"] == "true" else 0
        try:
            dur = (dt.datetime.strptime(row["end_time"][:19], "%Y-%m-%d %H:%M:%S")
                   - dt.datetime.strptime(row["start_time"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds()
            if not (0 <= dur < 3600):
                dur = -1.0
        except ValueError:
            dur = -1.0
        try:
            dfb = float(row["difficulty_feedback"])
        except (ValueError, TypeError):
            dfb = None
        try:
            tfb = float(row["trust_feedback"])
        except (ValueError, TypeError):
            tfb = None
        a["ok"] += ok
        a["hint"] += hint
        if dur >= 0:
            a["dur"] += dur; a["ndur"] += 1
        if dfb is not None:
            a["dfb"] += dfb; a["ndfb"] += 1
        if tfb is not None:
            a["tfb"] += tfb; a["ntfb"] += 1
        vals = (ok, hint, dur, dfb if dfb is not None else -1.0, tfb if tfb is not None else -1.0)
        n = a["n"]
        r = dres.get(q)
        if n <= K:
            if r is None:
                r = dres[q] = np.zeros((5, K), dtype=np.float32)
            r[:, n - 1] = vals
        else:
            j = random.randrange(n)
            if j < K:
                r[:, j] = vals
print("dbe done", len(dagg), "questions", flush=True)

dkeep = [q for q, a in dagg.items() if a["n"] >= 30 and q in expert]
dkeep.sort()
nD = len(dkeep)
D_full = np.zeros((nD, 6), dtype=np.float64)   # n, ok, hint, dur, dfb, tfb
D_cnt = np.zeros((nD, 3), dtype=np.int32)      # ndur, ndfb, ntfb
D_res = np.zeros((nD, 5, K), dtype=np.float32)
D_y = np.zeros(nD, dtype=np.int8)
for i, q in enumerate(dkeep):
    a = dagg[q]
    D_full[i] = [a["n"], a["ok"], a["hint"], a["dur"], a["dfb"], a["tfb"]]
    D_cnt[i] = [a["ndur"], a["ndfb"], a["ntfb"]]
    D_res[i] = dres[q]
    D_y[i] = expert[q]
print("dbe keep", nD, flush=True)

np.savez_compressed(
    OUT,
    J_full=J_full, J_res=J_res, J_y=J_y, J_keep=np.array(keep),
    D_full=D_full, D_res=D_res, D_y=D_y, D_cnt=D_cnt, D_keep=np.array(dkeep),
)
print("saved ->", OUT, os.path.getsize(OUT) // 1024 // 1024, "MB")
