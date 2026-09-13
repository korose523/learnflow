# -*- coding: utf-8 -*-
"""M3 策略优化 v2（Junyi 真实标定，从 junyi_m3_cache.json 加载，秒级）。

v1 发现：hard→easy 成功率 0.7534 > easy→easy 0.7335，easy→hard 仅 0.6302
（爬坡摩擦 ~12pp）。据此新增策略族并检验是否能在真实臂上超越 llm_correct(0.7060)。
新增：flow_zone（瞄准 ~0.75 成功率区）、descent_pair（难→易交替）、adaptive_k（阈值扫描）。
输出 results/code/junyi_m3_v2_results.json
"""
import csv, json, math, os, random
from collections import Counter, defaultdict
import numpy as np
from scipy import stats as st

BASE = "E:/learnflow"
CACHE = BASE + "/results/code/junyi_m3_cache.json"
OUT = BASE + "/results/code/junyi_m3_v2_results.json"
random.seed(42)
DIFFORD = ["easy", "normal", "hard"]


def load():
    meta = {}
    with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["ucid"]] = {"diff": row["difficulty"], "strand": row["level3_id"]}
    c = json.load(open(CACHE, encoding="utf-8"))
    user_dec = {u: int(d) for u, d in c["user_dec"].items()}
    pt = {}
    for k, v in c["pt"].items():
        ucid, d = k.rsplit("|", 1)
        pt[(ucid, int(d))] = v
    trans = {}
    for k, v in c["trans"].items():
        a, b = k.split("->")
        trans[(a, b)] = (v[0], v[1])
    return meta, user_dec, pt, trans


meta, user_dec, pt, trans = load()
print("cache loaded: users", len(user_dec), "p-table", len(pt), flush=True)


def pools(d):
    by = defaultdict(list)                 # (strand, diff) -> [(ucid, p)]
    for (c, dd), (a, k) in pt.items():
        if dd != d or a < 500:
            continue
        m = meta.get(c)
        if not m or m["diff"] not in DIFFORD:
            continue
        by[(m["strand"], m["diff"])].append((c, k / a))
    return by


by_dec = {d: pools(d) for d in range(10)}
print("pools built", flush=True)


def run(strat, T=40, n_sims=500, **kw):
    rew = []
    for _ in range(n_sims):
        d = random.randrange(10)
        by = by_dec[d]
        all_strands = {s for (s, _) in by}
        strands = [s for s in all_strands
                   if all(any(k[0] == s and k[1] == df and by[k] for k in by) for df in DIFFORD)]
        if not strands:
            continue
        s = random.choice(strands)
        arms = {df: [x[1] for k in by if k[0] == s and k[1] == df for x in by[k]] for df in DIFFORD}
        mean_p = {df: float(np.mean(v)) for df, v in arms.items()}
        streak = 0
        total = 0.0
        for t in range(T):
            if strat == "random":
                df = random.choice(DIFFORD)
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
                # choose the difficulty whose decile-conditional success is closest to 0.75
                df = min(DIFFORD, key=lambda x: abs(mean_p[x] - 0.75))
            elif strat == "descent_pair":
                df = "hard" if t % 2 == 0 else "easy"
            p = random.choice(arms[df])
            ok = random.random() < min(max(p, 0.05), 0.98)
            total += ok
            streak = streak + 1 if ok else min(streak - 1, -1)
        rew.append(total / T)
    return float(np.mean(rew)), float(np.std(rew) / math.sqrt(len(rew)))


strategies = [
    ("random", {}), ("all_easy", {}), ("all_hard", {}), ("adaptive", {}),
    ("llm_correct", {}), ("llm_wrong", {}), ("flow_zone", {}), ("descent_pair", {}),
]
for k in (1, 2, 3):
    strategies.append((f"adaptive_k{k}", {"k": k}))

out = {}
for name, kw in strategies:
    m, se = run(name, **kw)
    out[name] = {"mean": round(m, 4), "se": round(se, 4)}
    print(f"{name:14s} {m:.4f} ± {se:.4f}", flush=True)

best = max(out, key=lambda k: out[k]["mean"])
res = {
    "design": "Junyi real arms, ability-decile conditional p, 500 sims x T=40, 11 strategies",
    "n_users_calibrated": len(user_dec),
    "results": out,
    "best": best,
    "v1_reference": {"random": 0.6870, "llm_correct": 0.7060, "llm_wrong": 0.6575, "all_easy": 0.7420},
}
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("best:", best, "saved ->", OUT)
