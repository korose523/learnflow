# -*- coding: utf-8 -*-
"""
Castleman et al. (2024), "Hierarchical Multi-Armed Bandits for the Concurrent
Intelligent Tutoring Systems" -- faithful-but-pragmatic baseline for the LearnFlow
M3 external-baseline gap (see M3 section 5.6 item 3).

PURPOSE
-------
M3 section 5.3 Table 4 reports an *internal* strategy comparison (no external
baseline). This script closes that gap by implementing Castleman's two-level
hierarchical MAB and reporting its *immediate success rate* under the EXACT same
protocol as M3 section 5.3 v2: Junyi real arms, ability-decile-conditional success
probability p, T=40 steps, 500 simulations, seed 42.

HIERARCHY MAPPING (pragmatic but faithful)
-----------------------------------------
Castleman's hierarchy: a high-level "concept MAB" selects a concept, then a
low-level "problem MAB" selects a specific problem within that concept.
Because M3 section 5.3 fixes a single strand/skill per simulation (one student
practising one skill), the only available two-granularity structure is:
    * Level 1 (concept MAB)  -> difficulty BAND  {easy, normal, hard}
    * Level 2 (problem MAB)   -> a specific problem within the chosen band
This mirrors Castleman's concept -> problem nesting exactly. The difficulty-band
choice is further difficulty-aware per Castleman Eq. 7 (see hmab_castleman).

REWARD (must match section 5.3)
-------------------------------
Reported metric = IMMEDIATE success rate (NOT learning gain). At each step we pick
a difficulty band via the top MAB, then a specific problem via the bottom MAB, and
observe success ~ Bernoulli(p) with p clamped to [0.05, 0.98] (identical clamp to
junyi_m3_v2.py). Both MAB levels use either UCB1 or Thompson sampling.

FAITHFULNESS / SIMPLIFICATIONS (documented for M3 section 5.6 edit)
-------------------------------------------------------------------
Included: two-level hierarchy, UCB1/Thompson per level, Castleman Eq.7 difficulty
adjustment on the concept-level reward (variant hmab_castleman).
Omitted for comparability with section 5.3's immediate-success reward: ZPDES
belief-state mastered/unmastered transitions, the MCM memory-decay model, the Eq.8
initial problem-difficulty Gaussian skew, and the modified-MAPLE transient ranking.
These act on *latent student mastery*; since section 5.3's reward is a fixed
per-problem success rate (no within-sim student learning), they are not operational
here and would otherwise only distort the apples-to-apples reward comparison.

ENVIRONMENT
-----------
Pure stdlib only (random, math, json, csv, statistics, collections). The venv
python at E:/learnflow/learnflow-backend/.venv/Scripts/python.exe has NO numpy,
so numpy is intentionally not used (np.mean/std replaced by statistics).
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
OUT = os.path.join(os.path.dirname(__file__), "results.json")

T = 40                 # horizon, identical to section 5.3 v2
N_SIMS = 500           # identical to section 5.3 v2
SEED = 42              # identical to section 5.3 v2
DIFFORD = ["easy", "normal", "hard"]
# Castleman difficulty scale d in [1,5], centred at 3 (Eq.7)
DLEVEL = {"easy": 1, "normal": 3, "hard": 5}


# --------------------------------------------------------------------------- #
# Data loading (replicates junyi_m3_v2.py exactly)
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
    """Replicates junyi_m3_v2.pools(): group per (strand, expert-diff) the
    ability-decile-conditional success rate p, requiring >=500 attempts."""
    by = defaultdict(list)  # (strand, diff) -> [(ucid, p)]
    for (c, dd), (a, k) in pt.items():
        if dd != decile or a < 500:
            continue
        m = meta.get(c)
        if not m or m["diff"] not in DIFFORD:
            continue
        by[(m["strand"], m["diff"])].append((c, k / a))
    return by


# Pre-build pools per decile (matching v2's by_dec)
by_dec = {d: build_pools(d) for d in range(10)}
print("pools built", flush=True)


def clamp(p):
    return min(max(p, 0.05), 0.98)


def generate_sims(n, seed=SEED):
    """Generate n valid sims. A sim = one student (decile) practising one strand
    that has all three expert difficulties available, exposing arms[diff] = list of
    per-problem success probabilities. Uses the same selection logic as v2 so the
    data distribution matches M3 section 5.3."""
    rng = random.Random(seed)
    sims = []
    while len(sims) < n:
        d = rng.randrange(10)
        by = by_dec[d]
        # NOTE: must sort -- a set of *strings* iterates in a PYTHONHASHSEED-
        # dependent order, which would make results vary per process. (Same
        # hash-seed pitfall M3 sec.5.6 warns about for student splitting.)
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
# M3 section 5.3 v2 strategies (re-implemented in pure stdlib for an
# apples-to-apples comparison on the IDENTICAL sims -> eliminates RNG mismatch).
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
# Castleman hierarchical MAB
# --------------------------------------------------------------------------- #
class UCB:
    """UCB1 arm holder. rewards are Bernoulli; value = mean + c*sqrt(ln N / n)."""
    def __init__(self, n_arms, c=2.0):
        self.n = [0] * n_arms
        self.s = [0.0] * n_arms
        self.c = c

    def choose(self, rng):
        N = sum(self.n)
        best, best_v = 0, -1e18
        for i in range(len(self.n)):
            if self.n[i] == 0:
                return i
            v = self.s[i] / self.n[i] + self.c * math.sqrt(math.log(N) / self.n[i])
            if v > best_v:
                best, best_v = i, v
        return best

    def update(self, i, reward):
        self.n[i] += 1
        self.s[i] += reward


class Thompson:
    """Thompson sampling: Beta(alpha, beta) per arm, sample max."""
    def __init__(self, n_arms, c=2.0):  # c accepted for a uniform sampler interface
        self.a = [1] * n_arms
        self.b = [1] * n_arms

    def choose(self, rng):
        best, best_v = 0, -1.0
        for i in range(len(self.a)):
            x = rng.betavariate(self.a[i], self.b[i])
            if x > best_v:
                best, best_v = i, x
        return best

    def update(self, i, reward):
        self.a[i] += reward
        self.b[i] += (1 - reward)


def diff_mult(d_level):
    """Castleman Eq.7 difficulty multiplier sigma(d-3)+0.5, d in [1,5]."""
    return 1.0 / (1.0 + math.exp(-(d_level - 3))) + 0.5


def run_hmab(sims, sampler_cls, top_diff_adjusted=False, c=2.0, seed=SEED):
    """Two-level hierarchical MAB. Top arms = {easy,normal,hard}; for each top
    arm a bottom MAB over its problems. `top_diff_adjusted` applies Castleman Eq.7
    to the concept-level reward (faithful Castleman difficulty encouragement)."""
    rng = random.Random(seed)
    rew = []
    for sim in sims:
        arms = sim["arms"]
        bottom = {df: sampler_cls(len(arms[df]), c) for df in DIFFORD}
        top = sampler_cls(len(DIFFORD), c)
        total = 0.0
        for _ in range(T):
            bi = top.choose(rng)            # choose difficulty band
            df = DIFFORD[bi]
            pi = bottom[df].choose(rng)     # choose specific problem
            p = clamp(arms[df][pi])
            ok = 1.0 if rng.random() < p else 0.0
            total += ok
            bottom[df].update(pi, ok)
            top_rew = ok * diff_mult(DLEVEL[df]) if top_diff_adjusted else ok
            top.update(bi, top_rew)
        rew.append(total / T)
    return statistics.mean(rew), statistics.stdev(rew) / math.sqrt(len(rew))


# --------------------------------------------------------------------------- #
# Run everything on the SAME sims
# --------------------------------------------------------------------------- #
print("generating", N_SIMS, "sims (seed", SEED, ") ...", flush=True)
sims = generate_sims(N_SIMS, SEED)
print("sims ready; example arm counts:",
      {df: len(sims[0]["arms"][df]) for df in DIFFORD}, flush=True)

results = {}

# --- reproduce M3 section 5.3 v2 internal strategies on identical sims ---
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

# --- Castleman hierarchical MAB variants ---
print("\n[Castleman hierarchical MAB]", flush=True)
m, se = run_hmab(sims, UCB, top_diff_adjusted=False, c=2.0)
results["hmab_ucb"] = {"mean": round(m, 4), "se": round(se, 4)}
print(f"  {'hmab_ucb':14s} {m:.4f} +/- {se:.4f}  (UCB1, immediate-success reward)",
      flush=True)

m, se = run_hmab(sims, UCB, top_diff_adjusted=True, c=2.0)
results["hmab_castleman"] = {"mean": round(m, 4), "se": round(se, 4)}
print(f"  {'hmab_castleman':14s} {m:.4f} +/- {se:.4f}  (UCB1 + Eq.7 diff-adjusted "
      "concept reward)", flush=True)

m, se = run_hmab(sims, Thompson, top_diff_adjusted=False)
results["hmab_thompson"] = {"mean": round(m, 4), "se": round(se, 4)}
print(f"  {'hmab_thompson':14s} {m:.4f} +/- {se:.4f}  (Thompson, immediate-success "
      "reward)", flush=True)

# Sensitivity to exploration strength (UCB c). Lower c -> more greedy exploitation
# of the easy band -> upper bound on what a well-tuned HMAB can reach on this reward.
for cc in (1.0, 0.3):
    m, se = run_hmab(sims, UCB, top_diff_adjusted=False, c=cc)
    key = "hmab_ucb_c" + str(cc).replace(".", "")
    results[key] = {"mean": round(m, 4), "se": round(se, 4), "c": cc}
    print(f"  {key:14s} {m:.4f} +/- {se:.4f}  (UCB c={cc}, immediate-success reward)",
          flush=True)


# --------------------------------------------------------------------------- #
# Reference numbers from M3 section 5.3 v2 (published) for the written comparison
# --------------------------------------------------------------------------- #
M3_V2 = {
    "all_easy": 0.7434, "flow_zone": 0.7119, "llm_correct": 0.7023,
    "adaptive": 0.6898, "random": 0.6835, "all_hard": 0.6498,
}
print("\nReference M3 section 5.3 v2 published means:",
      {k: M3_V2[k] for k in M3_V2}, flush=True)


def cmp_against(name):
    v = results[name]["mean"]
    return [f"{name} - {ref} = {v - M3_V2[ref]:+.4f}" for ref in
            ["all_easy", "flow_zone", "llm_correct", "random"]]


print("\n[HMAB vs internal strategies]", flush=True)
for h in ["hmab_ucb", "hmab_castleman", "hmab_thompson",
          "hmab_ucb_c10", "hmab_ucb_c03"]:
    for line in cmp_against(h):
        print("  ", line, flush=True)


# --------------------------------------------------------------------------- #
# Explicit comparison of HMAB variants to M3 section 5.3 Table 4 (published)
# --------------------------------------------------------------------------- #
HMAB_KEYS = ["hmab_ucb", "hmab_castleman", "hmab_thompson",
             "hmab_ucb_c10", "hmab_ucb_c03"]
comparison = {}
for h in HMAB_KEYS:
    v = results[h]["mean"]
    comparison[h] = {
        "hmab_mean": v,
        "vs_all_easy": round(v - M3_V2["all_easy"], 4),
        "vs_flow_zone": round(v - M3_V2["flow_zone"], 4),
        "vs_llm_correct": round(v - M3_V2["llm_correct"], 4),
        "vs_random": round(v - M3_V2["random"], 4),
    }
print("\n[HMAB vs M3 Table 4 published]", flush=True)
for h, c in comparison.items():
    print(f"  {h:16s} all_easy {c['vs_all_easy']:+.4f} | flow_zone "
          f"{c['vs_flow_zone']:+.4f} | llm_correct {c['vs_llm_correct']:+.4f} | "
          f"random {c['vs_random']:+.4f}", flush=True)


# --------------------------------------------------------------------------- #
# Save results.json
# --------------------------------------------------------------------------- #
out = {
    "protocol": {
        "source": "Castleman et al. (2024), Hierarchical MAB for Concurrent ITS",
        "data": "Junyi real arms, ability-decile conditional p (same as M3 5.3 v2)",
        "horizon_T": T,
        "n_sims": N_SIMS,
        "seed": SEED,
        "reward": "immediate success rate (NOT learning gain) -- matches 5.3",
        "hierarchy": "Level1=difficulty band {easy,normal,hard} (concept MAB), "
                     "Level2=specific problem within band (problem MAB)",
        "samplers": "UCB1 (c=2.0) and Thompson; top reward may use Castleman "
                    "Eq.7 difficulty adjustment (variant hmab_castleman)",
        "omitted_for_comparability": [
            "ZPDES mastered/unmastered belief-state transitions",
            "MCM memory-decay model",
            "Eq.8 initial Gaussian difficulty skew",
            "modified-MAPLE transient difficulty ranking"
        ],
        "note": "All M3 v2 internal strategies are RE-RUN on the identical 500 "
                "sims so the comparison is free of RNG-distribution mismatch. "
                "Reproduced internal means differ slightly from the published "
                "Table 4 because they are an independent 500-sim MC sample of "
                "the same data/protocol; both are reported below."
    },
    "m3_v2_published": M3_V2,
    "results": results,
    "comparison_hmab_vs_table4": comparison,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nSaved ->", OUT, flush=True)
