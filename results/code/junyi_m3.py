# -*- coding: utf-8 -*-
"""M3-Junyi: replace simulator's linspace(-2,2,10) with real Junyi action space.

Pass A: per-user ability (overall success rate) -> deciles.
Pass B: p(exercise, decile) table + ordered-difficulty transition stats.
Then: curriculum policy comparison on real-calibrated arms (same 8 strategies
as m3_simulator.py), arms = {easy, normal, hard} exercises within a strand.
Outputs results/code/junyi_m3_results.json
"""
import csv, json, math, random, os
from collections import Counter, defaultdict

BASE = "E:/learnflow/data/junyi"
OUT = "E:/learnflow/results/code/junyi_m3_results.json"
CACHE = "E:/learnflow/results/code/junyi_m3_cache.json"
random.seed(42)
DIFFORD = {"easy": 0, "normal": 1, "hard": 2}

meta = {}
with open(os.path.join(BASE, "Info_Content.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = {"diff": row["difficulty"], "strand": row["level3_id"],
                             "stage": row["learning_stage"]}

# ---------- Pass A/B with disk cache ----------
if os.path.exists(CACHE):
    _c = json.load(open(CACHE, encoding="utf-8"))
    user_dec = {u: int(d) for u, d in _c["user_dec"].items()}
    pt = defaultdict(lambda: [0, 0])
    for k, v in _c["pt"].items():
        c, d = k.rsplit("|", 1)
        pt[(c, int(d))] = v
    trans, trans_ok = Counter(), Counter()
    for k, v in _c["trans"].items():
        a, b = k.split("->")
        trans[(a, b)] = v[0]
        trans_ok[(a, b)] = v[1]
    print("cache loaded, skipping passes", flush=True)
else:
    # ---------- Pass A: user ability ----------
    un, uc = Counter(), Counter()
    with open(os.path.join(BASE, "Log_Problem.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            un[row["uuid"]] += 1
            if row["is_correct"] == "True":
                uc[row["uuid"]] += 1
    print("pass A done", len(un), flush=True)

    ability = {u: uc[u] / n for u, n in un.items() if n >= 20}   # reliable-ability users
    srt = sorted(ability.values())
    def decile(x):
        k = 0
        while k < 9 and x > srt[int((k + 1) * len(srt) / 10) - 1]:
            k += 1
        return k

    user_dec = {u: decile(v) for u, v in ability.items()}
    print("users with n>=20:", len(user_dec), flush=True)

    # ---------- Pass B: p(exercise, decile) + transitions ----------
    pt = defaultdict(lambda: [0, 0])          # (ucid, decile) -> [att, cor]
    trans = Counter()                          # (prev_diff, cur_diff) -> count
    trans_ok = Counter()
    with open(os.path.join(BASE, "Log_Problem.csv"), encoding="utf-8") as f:
        last_diff = {}                          # uuid -> last exercise difficulty (within stream order = time order per user)
        for row in csv.DictReader(f):
            u, c = row["uuid"], row["ucid"]
            d = user_dec.get(u)
            if d is not None:
                ok = row["is_correct"] == "True"
                k = (c, d)
                pt[k][0] += 1
                if ok: pt[k][1] += 1
                md = meta.get(c, {}).get("diff", "unset")
                pd = last_diff.get(u)
                if pd is not None and md in DIFFORD and pd in DIFFORD:
                    trans[(pd, md)] += 1
                    if ok: trans_ok[(pd, md)] += 1
                last_diff[u] = md
    print("pass B done", flush=True)
    json.dump({
        "user_dec": user_dec,
        "pt": {f"{c}|{d}": v for (c, d), v in pt.items()},
        "trans": {f"{a}->{b}": [n, trans_ok[(a, b)]] for (a, b), n in trans.items()},
    }, open(CACHE, "w", encoding="utf-8"))
    print("cache saved", flush=True)

# arm pools: exercises with >=500 stratified attempts in a decile, grouped by expert difficulty within strand
def pools(d):
    by = defaultdict(list)                 # (strand, diff) -> [(ucid, p)]
    for (c, dd), (a, k) in pt.items():
        if dd != d or a < 500: continue
        m = meta.get(c)
        if not m or m["diff"] not in DIFFORD: continue
        by[(m["strand"], m["diff"])].append((c, k / a))
    return by

def run_strategy(by_dec, strat, T=40, n_sims=400):
    """Same 8 strategies as m3_simulator, real arms."""
    rew = 0.0
    for _ in range(n_sims):
        d = random.randrange(10)
        by = by_dec[d]
        # only strands offering all three difficulties (no fallback bias)
        all_strands = {s for (s, _) in by.keys()}
        strands = [s for s in all_strands
                   if all(any(k2[0] == s and k2[1] == df and by[k2] for k2 in by) for df in DIFFORD)]
        if not strands: continue
        random.shuffle(strands)
        chosen_strand = strands[0]
        arms = {df: [x[1] for (s, dd), lst in by.items() if s == chosen_strand and dd == df
                     for x in lst] for df in DIFFORD}
        arms = {k: v for k, v in arms.items() if v}
        if not arms: continue
        streak = 0; total = 0.0
        theta = 0.5 + 0.05 * (d - 5)      # user ability proxy from decile
        for t in range(T):
            if strat == "random": df = random.choice(list(arms))
            elif strat == "all_easy": df = "easy"
            elif strat == "all_hard": df = "hard"
            elif strat == "fixed_normal": df = "normal"
            elif strat == "staircase": df = ["easy","normal","hard"][min(t // 13, 2)]
            elif strat == "adaptive": df = "hard" if streak >= 2 else ("normal" if streak >= 0 else "easy")
            elif strat == "llm_correct": df = "hard" if theta > 0.7 else ("normal" if theta > 0.4 else "easy")
            elif strat == "llm_wrong": df = "easy" if theta > 0.7 else ("hard" if theta > 0.4 else "normal")
            p = random.choice(arms[df])
            # p is already decile-conditional empirical success — no extra adjustment
            ok = random.random() < min(max(p, 0.05), 0.98)
            total += ok
            streak = streak + 1 if ok else min(streak - 1, -1)
        rew += total / T
    return rew / n_sims

by_dec = {d: pools(d) for d in range(10)}
strategies = ["random", "all_easy", "all_hard", "fixed_normal", "staircase",
              "adaptive", "llm_correct", "llm_wrong"]
results = {s: run_strategy(by_dec, s) for s in strategies}
print(json.dumps(results, indent=1), flush=True)

# ordered-difficulty transition analysis
trans_res = {}
for (a, b), n in trans.items():
    if n >= 500:
        trans_res[f"{a}->{b}"] = {"n": n, "success": round(trans_ok[(a, b)] / n, 4)}

out = {
    "design": "real Junyi arms (expert-difficulty exercises within strand), ability-decile-calibrated p, 8 strategies x 400 sims x T=40",
    "users_with_ability_ge20": len(user_dec),
    "policy_results": {k: round(v, 4) for k, v in results.items()},
    "best": max(results, key=results.get),
    "ordered_difficulty_transitions": trans_res,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved ->", OUT)
