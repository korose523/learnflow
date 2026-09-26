# -*- coding: utf-8 -*-
"""
R10 -- RL-DKT (Fu 2025, Scientific Reports 15:40202,
DOI 10.1038/s41598-025-23900-4) *policy* head-to-head vs LearnFlow adaptive
strategy, under the EXACT same protocol as M3 section 5.3 v2 / the Castleman
HMAB baseline (castleman_hmab.py).

PURPOSE
-------
Close M3 R10's "dangling citation" (悬空对照): instead of merely asserting
"planning is better", provide a same-protocol empirical head-to-head where an
RL-DKT-style policy (tabular Q-learning over a strand's answer-history state)
is compared to the LearnFlow internal strategies and the Castleman HMAB on the
IDENTICAL immediate-success-rate bandit protocol.

PROTOCOL FIDELITY (must match castleman_hmab.py verbatim)
---------------------------------------------------------
* Same data loading: junyi_m3_cache.json + Info_Content.csv
* Same generate_sims(N=500, T=40, seed=42)
* Same DIFFORD / DLEVEL
* Same clamp([0.05, 0.98])
* Same PYTHONHASHSEED safety: sorted strands in generate_sims
* Reward = IMMEDIATE success rate (1/0 per step), NOT learning gain
* Per-sim problem-choice RNG seeded by crc32(strand|rldkt|decile) exactly like
  run_v2_strategy, so the environment draw distribution is fixed/reproducible.

RL-DKT AS A TABULAR Q-LEARNING AGENT (allowed by the task spec)
---------------------------------------------------------------
State features (the strand's answer-history within a sim):
  * rolling success rate over the last WINDOW attempts  -> 5 bins
  * recent streak (consecutive success - consecutive fail), clipped [-3,3] -> 7 bins
  * current difficulty band one-hot (easy/normal/hard) -> 3
Action = pick next difficulty band {easy, normal, hard}
Reward = immediate success (1/0)
Update = standard Q-learning: Q <- Q + a*(r + g*max_a' Q(s') - Q(s,a))

COLD-START / REAL-TIME INTERPRETATION (honest)
----------------------------------------------
The Q-table is RESET at the start of every sim. This is the faithful reading of
RL-DKT's *"real-time"* claim: a tutor that must adapt online to a fresh student
without pre-training. It is also the strictest fair test against the fixed
decision-rule strategies (flow_zone, llm_correct, ...), which need no training.
A pre-trained variant is NOT used for the headline number, because pre-training
would leak the 500-sim distribution and break apples-to-apples with the
non-learning baselines.

HONESTY CONSTRAINTS (per supervisor review of Fu 2025)
-----------------------------------------------------
* Fu 2025's reward definition is internally contradictory across its text, and
  its "real-time" deployment claim lacks a real deployment trace.
* We therefore do NOT claim "LearnFlow beats RL-DKT on learning gain" -- the
  reward caliber differs (RL-DKT's stated reward is learning gain; ours is
  immediate success). The head-to-head is strictly scoped to the SAME immediate
  success-rate bandit protocol.
* If the RL-DKT policy does not exceed flow_zone, we report that honestly.
"""

import csv
import json
import math
import os
import random
import zlib
from collections import defaultdict
import statistics

BASE = "E:/learnflow"
CACHE = BASE + "/results/code/junyi_m3_cache.json"
INFO = BASE + "/data/junyi/Info_Content.csv"

T = 40                 # horizon, identical to M3 5.3 v2 / castleman_hmab.py
N_SIMS = 500           # identical
SEED = 42              # identical
DIFFORD = ["easy", "normal", "hard"]
DLEVEL = {"easy": 1, "normal": 3, "hard": 5}

# --------------------------------------------------------------------------- #
# Data loading (VERBATIM from castleman_hmab.py)
# --------------------------------------------------------------------------- #
def load():
    meta = {}
    with open(INFO, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["ucid"]] = {"diff": row["difficulty"],
                                 "strand": row["level3_id"]}
    c = json.load(open(CACHE, encoding="utf-8"))
    user_dec = {u: int(d) for u, d in c["user_dec"].items()}
    pt = {}
    for k, v in c["pt"].items():
        ucid, d = k.rsplit("|", 1)
        pt[(ucid, int(d))] = v  # (ucid, decile) -> [attempts, successes]
    return meta, user_dec, pt


meta, user_dec, pt = load()
print("cache loaded: users", len(user_dec), "p-table", len(pt), flush=True)


def build_pools(decile):
    by = defaultdict(list)
    for (c, dd), (a, k) in pt.items():
        if dd != decile or a < 500:
            continue
        m = meta.get(c)
        if not m or m["diff"] not in DIFFORD:
            continue
        by[(m["strand"], m["diff"])].append((c, k / a))
    return by


by_dec = {d: build_pools(d) for d in range(10)}
print("pools built", flush=True)


def clamp(p):
    return min(max(p, 0.05), 0.98)


def generate_sims(n, seed=SEED):
    rng = random.Random(seed)
    sims = []
    while len(sims) < n:
        d = rng.randrange(10)
        by = by_dec[d]
        # PYTHONHASHSEED safety: sorted strands (same pitfall as M3 sec.5.6)
        all_strands = sorted({s for (s, _) in by})
        strands = [s for s in all_strands
                   if all(any(k[0] == s and k[1] == df and by[k]
                              for k in by) for df in DIFFORD)]
        if not strands:
            continue
        s = rng.choice(strands)
        arms = {df: [x[1] for k in by if k[0] == s and k[1] == df
                     for x in by[k]] for df in DIFFORD}
        mean_p = {df: statistics.mean(v) for df, v in arms.items()}
        sims.append({"decile": d, "strand": s, "arms": arms, "mean_p": mean_p})
    return sims


# --------------------------------------------------------------------------- #
# RL-DKT style tabular Q-learning agent (online, cold-start per sim)
# --------------------------------------------------------------------------- #
WINDOW = 10          # rolling-success window
SR_BINS = 5          # 0..4  -> [0,.2),[.2,.4),[.8,1]
STREAK_CLIP = 3      # streak clipped to [-3, 3]
ALPHA = 0.10         # learning rate
GAMMA = 0.90         # discount
EPS0 = 0.20          # initial epsilon (exploration)
EPS_END = 0.05       # final epsilon (decayed over T)


def _sr_bin(sr):
    b = int(sr * SR_BINS)
    return min(b, SR_BINS - 1)


def _streak_bin(streak):
    s = max(-STREAK_CLIP, min(STREAK_CLIP, streak))
    return s + STREAK_CLIP  # map [-3,3] -> [0,6]


def run_rldkt(sims, alpha=ALPHA, gamma=GAMMA, eps0=EPS0, eps_end=EPS_END,
              seed=SEED):
    """Run the RL-DKT-style Q-learning policy on the SAME sims. Q-table is reset
    per sim (cold-start / real-time interpretation). Returns (mean, se)."""
    rates = []
    for sim in sims:
        arms = sim["arms"]
        d = sim["decile"]
        # Per-sim RNG: mirrors run_v2_strategy's crc32 seeding for a fixed,
        # reproducible environment draw (problem choice + exploration).
        rng = random.Random(zlib.crc32(
            f"{sim['strand']}|rldkt|{d}".encode()) & 0xFFFFFFFF)
        Q = {}  # (sr_bin, streak_bin, diff_idx) -> [q_easy, q_normal, q_hard]
        hist = []          # recent success/fail for rolling window
        streak = 0
        cur_diff_idx = 1   # start at 'normal'
        total = 0.0
        for t in range(T):
            # --- build state ---
            if len(hist) == 0:
                sr = 0.5
            else:
                w = hist[-WINDOW:]
                sr = sum(w) / len(w)
            s_key = (_sr_bin(sr), _streak_bin(streak), cur_diff_idx)
            if s_key not in Q:
                Q[s_key] = [0.0, 0.0, 0.0]

            # --- epsilon-greedy action (next difficulty band) ---
            eps = eps0 + (eps_end - eps0) * (t / max(1, T - 1))
            if rng.random() < eps:
                a = rng.randrange(3)
            else:
                qv = Q[s_key]
                best = -1e18
                cand = []
                for i in range(3):
                    if qv[i] > best:
                        best = qv[i]; cand = [i]
                    elif qv[i] == best:
                        cand.append(i)
                a = rng.choice(cand)

            df = DIFFORD[a]
            p = clamp(rng.choice(arms[df]))
            ok = 1.0 if rng.random() < p else 0.0
            total += ok

            # --- next state ---
            hist.append(ok)
            streak = streak + 1 if ok else min(streak - 1, -1)
            cur_diff_idx = a

            if len(hist) == 0:
                sr2 = 0.5
            else:
                w2 = hist[-WINDOW:]
                sr2 = sum(w2) / len(w2)
            s2_key = (_sr_bin(sr2), _streak_bin(streak), cur_diff_idx)
            if s2_key not in Q:
                Q[s2_key] = [0.0, 0.0, 0.0]

            # --- Q-learning update (reward = immediate success) ---
            target = ok + gamma * max(Q[s2_key])
            Q[s_key][a] += alpha * (target - Q[s_key][a])

        rates.append(total / T)
    return statistics.mean(rates), statistics.stdev(rates) / math.sqrt(len(rates))


# --------------------------------------------------------------------------- #
# Reproduce internal strategies on the SAME sims (for an RNG-safe diff)
# (VERBATIM logic from castleman_hmab.py run_v2_strategy)
# --------------------------------------------------------------------------- #
def run_v2_strategy(strat, sims, **kw):
    rew = []
    for sim in sims:
        arms = sim["arms"]
        mean_p = sim["mean_p"]
        d = sim["decile"]
        rng = random.Random(zlib.crc32(
            f"{sim['strand']}|{strat}|{d}".encode()) & 0xFFFFFFFF)
        streak = 0
        total = 0.0
        for t in range(T):
            if strat == "random":
                df = rng.choice(DIFFORD)
            elif strat == "all_easy":
                df = "easy"
            elif strat == "all_hard":
                df = "hard"
            elif strat == "adaptive":
                df = "hard" if streak >= 2 else ("normal" if streak >= 0 else "easy")
            elif strat.startswith("adaptive_k"):
                k = kw["k"]
                df = "hard" if streak >= k else ("normal" if streak >= 0 else "easy")
            elif strat == "llm_correct":
                df = "hard" if d >= 7 else ("normal" if d >= 3 else "easy")
            elif strat == "llm_wrong":
                df = "easy" if d >= 7 else ("hard" if d >= 3 else "normal")
            elif strat == "flow_zone":
                df = min(DIFFORD, key=lambda x: abs(mean_p[x] - 0.75))
            elif strat == "descent_pair":
                df = "hard" if t % 2 == 0 else "easy"
            else:
                raise ValueError(strat)
            p = rng.choice(arms[df])
            ok = rng.random() < clamp(p)
            total += ok
            streak = streak + 1 if ok else min(streak - 1, -1)
        rew.append(total / T)
    return statistics.mean(rew), statistics.stdev(rew) / math.sqrt(len(rew))


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
print("generating", N_SIMS, "sims (seed", SEED, ") ...", flush=True)
sims = generate_sims(N_SIMS, SEED)
print("sims ready; example arm counts:",
      {df: len(sims[0]["arms"][df]) for df in DIFFORD}, flush=True)

results = {}
v2_strategies = [
    ("random", {}), ("all_easy", {}), ("all_hard", {}), ("adaptive", {}),
    ("llm_correct", {}), ("llm_wrong", {}), ("flow_zone", {}),
    ("descent_pair", {}),
]
for k in (1, 2, 3):
    v2_strategies.append((f"adaptive_k{k}", {"k": k}))

print("\n[M3 section 5.3 v2 internal strategies -- reproduced on same sims]",
      flush=True)
for name, kw in v2_strategies:
    m, se = run_v2_strategy(name, sims, **kw)
    results[name] = {"mean": round(m, 4), "se": round(se, 4)}
    print(f"  {name:14s} {m:.4f} +/- {se:.4f}", flush=True)

# HMAB numbers are taken from castleman_baseline/results.json (already run on the
# identical protocol); we cite them rather than re-run the two-level MAB here.
HMAB = {
    "hmab_ucb": 0.6899, "hmab_castleman": 0.6722, "hmab_thompson": 0.7093,
    "hmab_ucb_c10": 0.6988, "hmab_ucb_c03": 0.7137,
}

print("\n[RL-DKT-style tabular Q-learning agent]", flush=True)
m, se = run_rldkt(sims)
results["rldkt_q"] = {"mean": round(m, 4), "se": round(se, 4)}
print(f"  {'rldkt_q':14s} {m:.4f} +/- {se:.4f}", flush=True)

# Published M3 section 5.3 v2 Table-4 numbers (for the written comparison)
M3_V2_PUB = {
    "all_easy": 0.7434, "flow_zone": 0.7119, "llm_correct": 0.7023,
    "adaptive": 0.6898, "random": 0.6835, "all_hard": 0.6498,
}

# --------------------------------------------------------------------------- #
# Differences: RL-DKT vs internal strategies (same-protocol reproduced) and
# vs HMAB, plus published Table-4 reference
# --------------------------------------------------------------------------- #
rldkt_mean = results["rldkt_q"]["mean"]


def diffs_against(ref_means, label):
    out = {}
    for k, v in ref_means.items():
        out[k] = round(rldkt_mean - v, 4)
    return out


same_protocol = {k: results[k]["mean"] for k in results}
diffs_same = diffs_against(same_protocol, "same-protocol")
diffs_pub = diffs_against(M3_V2_PUB, "published-table4")
diffs_hmab = diffs_against(HMAB, "hmab")

print("\n[RL-DKT vs internal strategies -- same-protocol reproduced]", flush=True)
for k in ["all_easy", "flow_zone", "llm_correct", "adaptive", "random",
          "all_hard"]:
    print(f"  rldkt - {k:11s} = {diffs_same[k]:+.4f}", flush=True)
print("\n[RL-DKT vs internal strategies -- published Table-4]", flush=True)
for k in M3_V2_PUB:
    print(f"  rldkt - {k:11s} = {diffs_pub[k]:+.4f}", flush=True)
print("\n[RL-DKT vs Castleman HMAB]", flush=True)
for k in HMAB:
    print(f"  rldkt - {k:14s} = {diffs_hmab[k]:+.4f}", flush=True)

beats_flow = rldkt_mean > results["flow_zone"]["mean"]
beats_flow_pub = rldkt_mean > M3_V2_PUB["flow_zone"]

out = {
    "protocol": {
        "source": "M3 section 5.3 v2 / Castleman HMAB baseline (castleman_hmab.py), "
                  "reused verbatim",
        "data": "Junyi real arms, ability-decile conditional p "
                "(junyi_m3_cache.json + Info_Content.csv)",
        "horizon_T": T,
        "n_sims": N_SIMS,
        "seed": SEED,
        "reward": "immediate success rate (1/0 per step), NOT learning gain -- "
                  "matches M3 5.3",
        "clamp": "[0.05, 0.98]",
        "pythonhashseed_safety": "sorted strands in generate_sims; per-sim RNG "
                                 "seeded by crc32(strand|rldkt|decile)",
        "note": "RL-DKT *policy* implemented as tabular Q-learning over a strand "
                "answer-history state; Q-table RESET per sim (cold-start / "
                "real-time interpretation). Same 500 sims as Castleman baseline "
                "(generate_sims is deterministic in seed=42)."
    },
    "rldkt_hyperparams": {
        "agent": "tabular Q-learning (epsilon-greedy)",
        "state_features": [
            "rolling success rate over last WINDOW attempts (5 bins)",
            "recent streak clipped to [-3,3] (7 bins)",
            "current difficulty band one-hot {easy,normal,hard}"
        ],
        "WINDOW": WINDOW,
        "SR_BINS": SR_BINS,
        "STREAK_CLIP": STREAK_CLIP,
        "actions": DIFFORD,
        "alpha": ALPHA,
        "gamma": GAMMA,
        "eps0": EPS0,
        "eps_end": EPS_END,
        "q_table_reset_per_sim": True,
        "reward": "immediate success 1/0"
    },
    "rldkt_q": {
        "mean": round(m, 4),
        "se": round(se, 4),
        "beats_flow_zone_same_protocol": beats_flow,
        "beats_flow_zone_published": beats_flow_pub
    },
    "internal_same_protocol_reproduced": {k: results[k] for k in results},
    "internal_published_table4": M3_V2_PUB,
    "hmab_cited_from_castleman_results": HMAB,
    "diffs_rldkt_vs_same_protocol": diffs_same,
    "diffs_rldkt_vs_published_table4": diffs_pub,
    "diffs_rldkt_vs_hmab": diffs_hmab,
    "honesty_constraints": {
        "no_learning_gain_claim": True,
        "scope": "Strictly scoped to the SAME immediate-success-rate bandit "
                 "protocol. We do NOT claim LearnFlow beats RL-DKT on learning "
                 "gain (reward caliber differs).",
        "rldkt_internal_contradiction": "Fu 2025's reward definition is "
                 "internally contradictory across its text (learning-gain vs "
                 "immediate-success framings), and its 'real-time' deployment "
                 "claim lacks a verifiable real deployment trace. This is a "
                 "differentiation asset for LearnFlow, not a defeated baseline."
    }
}

OUT = os.path.join(os.path.dirname(__file__), "r10_results.json")
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nSaved ->", OUT, flush=True)
print("\nSUMMARY: rldkt_q = %.4f +/- %.4f | beats flow_zone (same-protocol)=%s "
      "| beats flow_zone (published)=%s" %
      (m, se, beats_flow, beats_flow_pub), flush=True)
