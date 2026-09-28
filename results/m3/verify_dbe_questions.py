# -*- coding: utf-8 -*-
"""verify_dbe_questions.py —— 校验新下载的 Questions.csv 与本机既有证据的一致性。

三重校验（全部通过才允许用于 E1 标注）：
  [1] 行数与 ID 集合 = difficulty_cache.npz 的 D_keep（212 个 DBE 题目 ID）
  [2] 每题 difficulty 列   = npz 的 D_y（专家 1/2/3 标签，逐 ID 对齐）
  [3] 每题 difficulty 列   = results/m3/local_matrix.jsonl E1A 记录里的 expert 字段
      （旧机器跑审计协议时随条目落盘的外生标签，多模型应一致）

输出：verify_dbe_questions_out.txt（追加式，便于留档）
退出码：0 = 全部 PASS；1 = 任一 FAIL
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJ = Path("D:/learnflow-main/learnflow-main")
QCSV = PROJ / "data" / "dbe_kt22" / "csv" / "Questions.csv"
NPZ = PROJ / "results" / "code" / "difficulty_cache.npz"
JSL = PROJ / "results" / "m3" / "local_matrix.jsonl"
OUT = PROJ / "results" / "m3" / "verify_dbe_questions_out.txt"

lines = []


def log(s=""):
    print(s)
    lines.append(s)


fails = []

# ---- 读 Questions.csv ----
rows = {}
with open(QCSV, encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        try:
            qid = str(d["id"]).strip()
            diff = int(d["difficulty"])
            rows[qid] = diff
        except (ValueError, TypeError, KeyError):
            continue
log(f"[csv] Questions.csv: {len(rows)} 行可解析（id, difficulty）")
log(f"[csv] 表头字段: id/question_rich_text/question_title/explanation/hint_text/question_text/difficulty")
# 文本非空性
empty_text = 0
with open(QCSV, encoding="utf-8-sig", errors="replace") as f:
    for d in csv.DictReader(f):
        qid = str(d.get("id", "")).strip()
        if qid in rows:
            t = (d.get("question_text") or d.get("question_rich_text") or "").strip()
            if not t:
                empty_text += 1
log(f"[csv] question_text/question_rich_text 皆空的行数: {empty_text}")
if empty_text:
    fails.append(f"empty_text={empty_text}")

# ---- [1][2] 对齐 npz ----
z = np.load(NPZ, allow_pickle=True)
d_keep = [str(x) for x in z["D_keep"]]
d_y = [int(x) for x in z["D_y"]]
npz_map = dict(zip(d_keep, d_y))
log(f"[npz] D_keep: {len(d_keep)} 个 ID；D_y 分布: "
    f"{ {v: d_y.count(v) for v in sorted(set(d_y))} }")

set_csv, set_npz = set(rows), set(d_keep)
if set_csv == set_npz:
    log("[1] ID 集合与 D_keep 完全一致: PASS")
else:
    only_csv, only_npz = set_csv - set_npz, set_npz - set_csv
    log(f"[1] ID 集合不一致: FAIL (仅 csv 有 {sorted(only_csv)[:8]}, 仅 npz 有 {sorted(only_npz)[:8]})")
    fails.append("id_set_mismatch")

mism2 = [q for q in set_csv & set_npz if rows[q] != npz_map[q]]
if not mism2:
    log("[2] difficulty 列与 D_y 逐 ID 一致: PASS")
else:
    log(f"[2] difficulty 不一致 {len(mism2)} 个: FAIL (样例 {mism2[:8]})")
    fails.append(f"difficulty_vs_D_y={len(mism2)}")

# ---- [3] 对齐 local_matrix.jsonl 的 expert ----
exp_by_model = defaultdict(dict)
with open(JSL, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("cond") != "E1A":
            continue
        e = r.get("expert")
        if e is None:
            continue
        exp_by_model[r.get("model")][str(r.get("key"))] = int(e)
log(f"[jsl] local_matrix.jsonl 内带 expert 的模型: {sorted(exp_by_model)}")

ref = None
for m in sorted(exp_by_model):
    lbl = exp_by_model[m]
    if ref is None:
        ref = dict(lbl)
        log(f"[3] 以 {m} 的 expert（{len(ref)} 条）为参照")
    else:
        diffk = [k for k in set(ref) & set(lbl) if ref[k] != lbl[k]]
        log(f"    {m} 与参照不一致 {len(diffk)} 条"
            + (f"（样例 {diffk[:5]}）" if diffk else " —— 各模型 expert 标签互相一致"))
        if diffk:
            fails.append(f"expert_internal_{m}")

if ref is not None:
    common = set(ref) & set(rows)
    mism3 = [q for q in common if ref[q] != rows[q]]
    only_ref = set(ref) - set(rows)
    log(f"    与 csv 共同 ID {len(common)} 个，其中 difficulty 不一致 {len(mism3)} 个"
        f"{'，jsonl 独有 ID ' + str(sorted(only_ref)[:8]) if only_ref else ''}")
    if mism3 or only_ref:
        log("[3] 与 local_matrix.jsonl expert 对齐: FAIL")
        fails.append(f"difficulty_vs_jsonl={len(mism3)}+{len(only_ref)}")
    else:
        log("[3] difficulty 列与 local_matrix.jsonl expert 逐 ID 一致: PASS")

log("-" * 60)
if fails:
    log(f"VERIFY FAIL: {fails}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.exit(1)
log("VERIFY PASS: Questions.csv 可作为 DBE-KT22 212 题的 E1 标注输入")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
sys.exit(0)
