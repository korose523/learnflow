# -*- coding: utf-8 -*-
"""Unified DBE-KT22 five-signal equal-weight fusion signal construction.

Single source of truth for the A2 experiment (results/m1/run_a1a2_fit.py) and
the O4 experiment (results/code/o4_fusion.py), per review 3.2 ① (2026-09-29).
Both consumers MUST call :func:`build` so that the two scripts can no longer
diverge in how they construct the behavioural signals.

Unified signal definition (the four points called out in review 3.2 ①):
  * ALL transactions are used — ``is_hidden`` rows are NOT excluded. Signals use
    the full transaction log ("信号使用全部交易", consistent with run_a2()).
  * ``difficulty_feedback`` / ``trust_feedback``: mean over rows that carry a
    feedback value (rows without feedback contribute nothing to the mean).
  * ``duration``: only rows with 0 <= d < 3600 seconds are retained for the mean.
  * ECDF -> logit transform: ``(rank - 0.5) / n`` (average-rank tie handling),
    clipped to [1e-4, 1 - 1e-4].

Five signals, all with positive direction = harder, each ECDF-logit transformed:
  1. success_inverse : -ecdf_logit(ok / n)         # low success -> hard
  2. hint_rate       : +ecdf_logit(hint / n)        # more hints -> hard
  3. difficulty_fb    : +ecdf_logit(mean difficulty_feedback over rows w/ value)
  4. trust_inverse   : -ecdf_logit(mean trust_feedback over rows w/ value)
  5. duration        : +ecdf_logit(mean duration over valid rows)

Returns aligned ``(qids, M, expert)`` where ``M`` is an ``n_items x 5`` list of
lists (the ECDF-logit transformed signals) with NaN rows and under-supported
items already dropped, and ``expert`` is the integer 1/2/3 teacher label.
"""
import csv
import math
import zipfile
from collections import defaultdict

BASE = r"E:/learnflow"
ZIP_PATH = BASE + "/data/dbe_kt22/2_DBE_KT22_datafiles_100102_csv.zip"
NAMES = ["success_inverse", "hint_rate", "difficulty_fb", "trust_inverse", "duration"]


def _num(s):
    try:
        return float(s)
    except (ValueError, AttributeError):
        return 0.0


def _ecdf_logit(values):
    """(rank - 0.5)/n -> logit, average-rank tie handling, clipped. Returns a list."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    out = []
    for r in ranks:
        p = (r - 0.5) / n
        p = min(max(p, 1e-4), 1.0 - 1e-4)
        out.append(math.log(p / (1.0 - p)))
    return out


def build(minn=30, zip_path=ZIP_PATH):
    """Build the unified aligned (qids, M, expert) for DBE-KT22."""
    expert = {}
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Questions.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines())
    hq = next(reader)
    ix_id = hq.index("id")
    ix_diff = hq.index("difficulty")
    for row in reader:
        if not row:
            continue
        qid = row[ix_id].strip()
        dv = row[ix_diff].strip()
        try:
            expert[qid] = int(float(dv))
        except ValueError:
            continue

    agg = defaultdict(lambda: [0, 0, 0, [], [], []])  # n, ok, hint, dfb, tfb, dur
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Transaction.csv") as f:
            text = f.read().decode("utf-8")
    reader = csv.reader(text.splitlines())
    ht = next(reader)
    ix_qid = ht.index("question_id")
    ix_ans = ht.index("answer_state")
    ix_hint = ht.index("hint_used")
    ix_self = ht.index("difficulty_feedback")
    ix_trust = ht.index("trust_feedback")
    ix_st = ht.index("start_time")
    ix_et = ht.index("end_time")
    for row in reader:
        if not row:
            continue
        qid = row[ix_qid].strip()
        if qid not in expert:
            continue
        a = agg[qid]
        a[0] += 1
        a[1] += 1 if row[ix_ans].strip().lower() == "true" else 0
        a[2] += 1 if row[ix_hint].strip().lower() == "true" else 0
        try:
            a[3].append(int(row[ix_self]))
        except ValueError:
            pass
        try:
            a[4].append(int(row[ix_trust]))
        except ValueError:
            pass
        try:
            st = row[ix_st].strip()[:19]
            et = row[ix_et].strip()[:19]
            import datetime as dt
            d = (dt.datetime.strptime(et, "%Y-%m-%d %H:%M:%S")
                 - dt.datetime.strptime(st, "%Y-%m-%d %H:%M:%S")).total_seconds()
            if 0 <= d < 3600:
                a[5].append(d)
        except (ValueError, TypeError):
            pass

    # keep items with enough transactions AND non-empty feedback/duration means
    kept = []
    for q, a in agg.items():
        if q not in expert:
            continue
        n, ok, hint, dfb, tfb, dur = a
        if n < minn:
            continue
        if not dfb or not tfb or not dur:
            continue
        # store the SUCCESS rate (ok/n); the signal is its negated ECDF-logit so that
        # low success -> high value -> "harder" (positive direction, review 3.2 ①).
        kept.append((q, ok / n, hint / n,
                     sum(dfb) / len(dfb), sum(tfb) / len(tfb), sum(dur) / len(dur)))

    qids = [k[0] for k in kept]
    success_raw = [k[1] for k in kept]
    hint_raw = [k[2] for k in kept]
    dfb_raw = [k[3] for k in kept]
    tfb_raw = [k[4] for k in kept]
    dur_raw = [k[5] for k in kept]

    e_success = _ecdf_logit(success_raw)
    e_hint = _ecdf_logit(hint_raw)
    e_dfb = _ecdf_logit(dfb_raw)
    e_tfb = _ecdf_logit(tfb_raw)
    e_dur = _ecdf_logit(dur_raw)

    M = []
    for i in range(len(qids)):
        M.append([
            -e_success[i],   # success_inverse
            e_hint[i],       # hint_rate
            e_dfb[i],        # difficulty_fb
            -e_tfb[i],       # trust_inverse
            e_dur[i],        # duration
        ])
    expert_vec = [expert[q] for q in qids]
    return qids, M, expert_vec


if __name__ == "__main__":
    qids, M, expert = build()
    print("n_items:", len(qids))
    print("names:", NAMES)
