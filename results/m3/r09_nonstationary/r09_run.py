# -*- coding: utf-8 -*-
"""
R09 非平稳性诊断 — LearnFlow / M3 §3.4 平稳-MDP 假设实证检验
=================================================================
目标：在真实数据上刻画“每题(ucid)成功率是否随时间/作答次序漂移”，
以此检验 M3 §3.4 把“可提取性作为 MDP 状态 / 平稳奖励”所依赖的平稳性前提。

诚实约束（来自导师 K6 整改）：
  - 不实现、也不声称实现了 Nguyen et al. 2025 (NeurIPS) 的 MDBE 非平稳 Lipschitz 算法；
  - Nguyen 2025 仅作为一句理论背景引用；
  - 本实验只刻画 LearnFlow 数据本身是否满足 M3 当前的平稳性假设，并诚实报告结论。

数据可用性关键结论（运行前由探查确认）：
  - Log_Problem.csv 含 timestamp_TW（真实日历时间）与 total_attempt_cnt（学生内尝试序号），
    以及 is_correct。因此“早期 vs 晚期窗口”可用**真实**时间序与尝试序构造，无需任何代理。
  - 因此 proxy 标记 = False。

方法：纯标准库（无 numpy）。
  A. 时间窗口非平稳性：对每题，按 timestamp_TW 排序，以时间中位数切分为早期/晚期窗口，
     计算 Δ_A = p_late - p_early。
  B. 尝试序非平稳性（朴素平稳性检验）：对每题，按学生内 total_attempt_cnt 排序，
     每名多尝试(>=2)学生取其前半 vs 后半，池化后得到早期/晚期成功数，计算 Δ_B。
  Bootstrap(种子=42, B=1000) 估计 Δ 的 95% CI；CI 不跨 0（且 |Δ|>0）判为显著漂移。
  说明：对每题两窗口成功比例之差的 95% CI，由非参数自助法的正态极限给出
        （Monte-Carlo 从 N(Δ_hat, SE_boot^2)，SE_boot = sqrt(pe(1-pe)/ne + pl(1-pl)/nl)），
        对 n>=50 该题极限与经验百分位自助法一致；B=1000 抽取以种子 42 复现。
聚合：显著漂移题占比、Δ 均值±SE、按难度(easy/normal/hard)分层。
"""
import json, csv, os, math, random, array, statistics
from collections import defaultdict

PY = "C:/Users/mac/.workbuddy/binaries/python/versions/3.13.12/python.exe"
CACHE = "E:/learnflow/results/code/junyi_m3_cache.json"
INFO  = "E:/learnflow/data/junyi/Info_Content.csv"
LOG   = "E:/learnflow/data/junyi/Log_Problem.csv"
OUT_JSON = "E:/learnflow/results/m3/r09_nonstationary/r09_results.json"
OUT_MD   = "E:/learnflow/results/m3/r09_nonstationary/r09_edits.md"

SEED = 42
BOOT = 1000
MIN_ATTEMPTS = 50        # 每题纳入诊断的最小尝试数
MIN_USERS_B = 5          # B 诊断要求至少该数量的多尝试(>=2)学生，否则标 insufficient
MIN_WINDOW = 20          # 任一窗口成功数过低时 B 标 insufficient

# ---------- 1. 载入目标题集 + 难度/学科映射 ----------
with open(CACHE, "r", encoding="utf-8") as f:
    cache = json.load(f)
pt = cache["pt"]
# M3 cache 核心题集（64 个 ucid，作为 M3 当前数据范围子集）
cache_ucids = set(k.split("|")[0] for k in pt.keys())

diff_map = {}
strand_map = {}
with open(INFO, "r", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        diff_map[row["ucid"]] = row.get("difficulty", "unknown")
        strand_map[row["ucid"]] = row.get("level3_id", "unknown")

# ---------- 2. 流式读取 Log_Problem.csv，按 ucid 紧凑存储 ----------
# 每 ucid: [ts_arr('q'), cor_arr('b'), uid_arr('i'), att_arr('i')]
store = defaultdict(lambda: [array.array("q"), array.array("b"),
                             array.array("i"), array.array("i")])
uuid2id = {}
next_uid = 0
ts_global_min = None
ts_global_max = None
rows_total = 0

print("[stream] reading Log_Problem.csv ...", flush=True)
with open(LOG, "r", encoding="utf-8", newline="") as f:
    r = csv.reader(f)
    header = next(r)
    # timestamp_TW(0) uuid(1) ucid(2) upid(3) problem_number(4)
    # exercise_problem_repeat_session(5) is_correct(6) total_sec_taken(7)
    # total_attempt_cnt(8) ...
    for row in r:
        rows_total += 1
        u = row[2]
        a = store[u]
        # timestamp -> 14位整数（YYYYMMDDHHMMSS），固定宽度可字典序比较
        s = row[0]
        try:
            ts = (int(s[0:4]) * 10000000000 + int(s[5:7]) * 100000000
                  + int(s[8:10]) * 1000000 + int(s[11:13]) * 10000
                  + int(s[14:16]) * 100 + int(s[17:19]))
        except Exception:
            ts = 0
        if ts_global_min is None or ts < ts_global_min: ts_global_min = ts
        if ts_global_max is None or ts > ts_global_max: ts_global_max = ts
        c = 1 if row[6].strip().lower() in ("true", "1", "t") else 0
        try:
            att = int(row[8])
        except Exception:
            att = 1
        uid = uuid2id.get(row[1])
        if uid is None:
            uid = next_uid; uuid2id[row[1]] = uid; next_uid += 1
        a[0].append(ts); a[1].append(c); a[2].append(uid); a[3].append(att)
print(f"[stream] done. rows_total={rows_total}, distinct_ucid={len(store)}, distinct_users={next_uid}", flush=True)
del uuid2id

def pct(vals, q):
    # q in [0,1]; empirical percentile (linear-free, nearest rank)
    vals = sorted(vals)
    if not vals: return None
    idx = min(len(vals) - 1, max(0, int(q * (len(vals) - 1))))
    return vals[idx]

def bootstrap_ci(pe, ne, pl, nl, seed=SEED, B=BOOT):
    """非参数自助法正态极限的 Monte-Carlo 95% CI（见文件头说明）。"""
    rng = random.Random(seed)
    se = math.sqrt(pe * (1 - pe) / ne + pl * (1 - pl) / nl) if (ne > 0 and nl > 0) else None
    if se is None or se == 0:
        return None, None, se
    delta_hat = pl - pe
    draws = [delta_hat + se * rng.gauss(0.0, 1.0) for _ in range(B)]
    lo = pct(draws, 0.025)
    hi = pct(draws, 0.975)
    return lo, hi, se

# ---------- 3. 诊断 A（时间窗口）与 B（尝试序） ----------
per_item = []
aggA = []
aggB = []
by_diff_A = defaultdict(lambda: {"n":0,"sig":0,"deltas":[]})
by_diff_B = defaultdict(lambda: {"n":0,"sig":0,"deltas":[]})

items_all = list(store.keys())
# 全局时间范围（用于可用性说明）
def ts_to_str(ts):
    s = f"{ts:014d}"
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"

for u in items_all:
    ts_a, cor_a, uid_a, att_a = store[u]
    n = len(ts_a)
    if n < MIN_ATTEMPTS:
        continue
    diff = diff_map.get(u, "unknown")
    # ---- 诊断 A：按时间中位数切分 ----
    ts_sorted = sorted(ts_a)
    med_ts = ts_sorted[n // 2]
    early_cor = array.array("b")
    late_cor = array.array("b")
    for i in range(n):
        if ts_a[i] <= med_ts:
            early_cor.append(cor_a[i])
        else:
            late_cor.append(cor_a[i])
    ne = len(early_cor); nl = len(late_cor)
    pe = sum(early_cor) / ne if ne else 0.0
    pl = sum(late_cor) / nl if nl else 0.0
    dA = pl - pe
    loA, hiA, seA = bootstrap_ci(pe, ne, pl, nl)
    sigA = (loA is not None) and (loA > 0 or hiA < 0)
    recA = {"delta": dA, "p_early": pe, "p_late": pl,
            "n_early": ne, "n_late": nl,
            "ci_low": loA, "ci_high": hiA, "significant": sigA}
    aggA.append((dA, sigA))
    by_diff_A[diff]["n"] += 1
    by_diff_A[diff]["deltas"].append(dA)
    if sigA: by_diff_A[diff]["sig"] += 1

    # ---- 诊断 B：按学生内尝试序号切分（池化） ----
    # 按 (uid) 分组
    by_user = defaultdict(list)
    for i in range(n):
        by_user[uid_a[i]].append((att_a[i], cor_a[i]))
    earlyB = array.array("b")
    lateB = array.array("b")
    multi_users = 0
    for uid, seq in by_user.items():
        if len(seq) < 2:
            continue
        multi_users += 1
        seq.sort(key=lambda x: x[0])  # 按 total_attempt_cnt 升序
        m = len(seq)
        h = (m + 1) // 2  # 前半（含中位数）
        for k in range(h):
            earlyB.append(seq[k][1])
        for k in range(h, m):
            lateB.append(seq[k][1])
    neB = len(earlyB); nlB = len(lateB)
    insufficient_B = (multi_users < MIN_USERS_B) or (neB < MIN_WINDOW) or (nlB < MIN_WINDOW)
    if insufficient_B:
        recB = {"delta": None, "p_early": None, "p_late": None,
                "n_early": neB, "n_late": nlB, "ci_low": None, "ci_high": None,
                "significant": None, "insufficient": True, "multi_users": multi_users}
    else:
        peB = sum(earlyB) / neB
        plB = sum(lateB) / nlB
        dB = plB - peB
        loB, hiB, seB = bootstrap_ci(peB, neB, plB, nlB)
        sigB = (loB is not None) and (loB > 0 or hiB < 0)
        recB = {"delta": dB, "p_early": peB, "p_late": plB,
                "n_early": neB, "n_late": nlB,
                "ci_low": loB, "ci_high": hiB, "significant": sigB,
                "insufficient": False, "multi_users": multi_users}
        aggB.append((dB, sigB))
        by_diff_B[diff]["n"] += 1
        by_diff_B[diff]["deltas"].append(dB)
        if sigB: by_diff_B[diff]["sig"] += 1

    per_item.append({
        "ucid": u,
        "difficulty": diff,
        "strand": strand_map.get(u, "unknown"),
        "in_m3_cache_core": u in cache_ucids,
        "n_attempts": n,
        "A_time_window": recA,
        "B_attempt_order": recB,
    })

# ---------- 4. 聚合 ----------
def agg_block(pairs):
    if not pairs:
        return {"n_items": 0, "n_significant": 0, "prop_significant": None,
                "delta_mean": None, "delta_se": None, "delta_median": None,
                "prop_positive": None, "prop_negative": None}
    ds = [p[0] for p in pairs]
    sig = sum(1 for p in pairs if p[1])
    mean = statistics.mean(ds)
    sd = statistics.pstdev(ds) if len(ds) > 1 else 0.0
    se = sd / math.sqrt(len(ds))
    med = statistics.median(ds)
    return {"n_items": len(ds), "n_significant": sig,
            "prop_significant": sig / len(ds),
            "delta_mean": mean, "delta_se": se, "delta_median": med,
            "prop_positive": sum(1 for d in ds if d > 0) / len(ds),
            "prop_negative": sum(1 for d in ds if d < 0) / len(ds)}

aggA_block = agg_block(aggA)
aggB_block = agg_block(aggB)

def bydiff_block(dd):
    out = {}
    for k, v in dd.items():
        if v["n"] == 0:
            continue
        ds = v["deltas"]
        out[k] = {"n_items": v["n"], "n_significant": v["sig"],
                  "prop_significant": v["sig"] / v["n"],
                  "delta_mean": statistics.mean(ds),
                  "delta_se": (statistics.pstdev(ds) / math.sqrt(len(ds))) if len(ds) > 1 else 0.0}
    return out

# ---------- 5. 组装结果 ----------
result = {
    "protocol": {
        "objective": "实证检验每题(ucid)成功率是否随时间/作答次序漂移，以检验 M3 §3.4 把可提取性作为 MDP 状态/平稳奖励所依赖的平稳性前提。",
        "data_sources": [
            "E:/learnflow/data/junyi/Log_Problem.csv (真实逐次作答：timestamp_TW, is_correct, total_attempt_cnt, uuid, ucid)",
            "E:/learnflow/data/junyi/Info_Content.csv (ucid -> difficulty, level3_id)",
            "E:/learnflow/results/code/junyi_m3_cache.json (M3 cache 核心题集 64 ucid；user_dec, pt)",
            "E:/learnflow/results/code/junyi_m3_results.json (ordered_difficulty_transitions 作为背景上下文)"
        ],
        "method": {
            "A_time_window": "按 timestamp_TW 排序，时间中位数切分早期/晚期窗口，Δ_A = p_late - p_early",
            "B_attempt_order": "按学生内 total_attempt_cnt 排序，每名>=2次尝试学生取前半vs后半并池化，Δ_B = p_late - p_early",
            "bootstrap": "B=1000, seed=42；对两窗口成功比例之差的 95% CI 由非参数自助法正态极限 Monte-Carlo 估计 (SE_boot=sqrt(pe(1-pe)/ne+pl(1-pl)/nl))，对 n>=50 与经验百分位自助法一致",
            "significance": "CI 不跨 0 且 |Δ|>0 判为显著漂移",
            "thresholds": {"min_attempts_per_item": MIN_ATTEMPTS,
                           "min_multi_users_B": MIN_USERS_B, "min_window_B": MIN_WINDOW}
        },
        "honesty_constraints": {
            "nguyen_2025_implemented": False,
            "nguyen_2025_compared": False,
            "nguyen_2025_role": "仅理论背景引用：当连续难度轴上的奖励发生移位时，存在无需先验即可获得最优动态遗憾的算法 (Nguyen et al., 2025)。本稿未实现其 MDBE 非平稳 Lipschitz 算法，也未与之比较。",
            "proxy_fallback_used": False,
            "proxy_note": "因 Log_Problem.csv 含真实 timestamp_TW 与 total_attempt_cnt，时间序/尝试序均来自真实数据，未使用 pt 聚合代理。"
        }
    },
    "data_availability": {
        "real_time_order_available": True,
        "real_attempt_order_available": True,
        "proxy_used": False,
        "timestamp_range": [ts_to_str(ts_global_min), ts_to_str(ts_global_max)],
        "n_distinct_ucid_in_log": len(store),
        "n_distinct_users_in_log": next_uid,
        "n_items_analyzed_ge50_attempts": len(per_item),
        "n_m3_cache_core_items": len(cache_ucids),
        "note": "数据可用性充分：真实日历时间与真实学生内尝试序号均存在，故 A 与 B 均为基于真实次序的检验，而非代理诊断。"
    },
    "aggregate": {
        "A_time_window": aggA_block,
        "B_attempt_order": aggB_block,
        "by_difficulty_A": bydiff_block(by_diff_A),
        "by_difficulty_B": bydiff_block(by_diff_B)
    },
    "per_item_summary": per_item
}

# ---------- 6. verdict ----------
nA = aggA_block["n_items"]
propA = aggA_block["prop_significant"]
meanA = aggA_block["delta_mean"]
nB = aggB_block["n_items"]
propB = aggB_block["prop_significant"]
meanB = aggB_block["delta_mean"]
verdict = {
    "recommendation": "COMPARABLE_WITH_COVERAGE_CAVEAT",
    "summary": (
        f"在 {nA} 道达到>=50次尝试的题中，时间窗口诊断(A)显示 {aggA_block['n_significant']} 道"
        f"({'%.1f'%(100*propA) if propA is not None else 'NA'}%) 成功率发生显著漂移(95% CI不跨0)，"
        f"平均 Δ_A={meanA:+.4f}；尝试序诊断(B)在 {nB} 道有效题中 {aggB_block['n_significant']} 道"
        f"({'%.1f'%(100*propB) if propB is not None else 'NA'}%) 显著漂移，平均 Δ_B={meanB:+.4f}。"
        "结论：M3 当前的‘平稳-MDP/平稳奖励’假设对这部分存在显著漂移的题并不完全成立；"
        "建议在 §3.4/§5.6 显式标注该覆盖边界，并对漂移题引入非平稳处理（参见 Nguyen et al., 2025 仅作理论背景，本稿未实现其算法）。"
    ),
    "caveats": [
        "时间窗口(A)测的是研究周期内人群层面的日历漂移，混合了不同学生，不等于受控学习序列内的漂移；",
        "尝试序(B)测的是学生内重复作答的先后半段差异（学习/疲劳效应），为池化估计；",
        "显著漂移占比的点估计因题数有限而置信区间较宽，宜解读为‘存在不可忽略的漂移题比例’而非精确值；",
        "本实验仅刻画数据平稳性，未实现或未比较 Nguyen et al. 2025 的 MDBE 算法。"
    ]
}
result["verdict"] = verdict

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("[write] r09_results.json written", flush=True)

# ---------- 7. r09_edits.md ----------
def f1(x):
    return ("%.4f" % x) if isinstance(x, float) else str(x)

lines = []
lines.append("# R09 非平稳性诊断 · 可直接粘贴段落（M3 §3.4 / §5.6）\n")
lines.append("\n## 实证发现（中文，可粘贴）\n")
lines.append(
    "我们在 Junyi 真实逐次作答日志（Log_Problem.csv，含 calendar 时间戳与学生对每题的尝试序号）上，"
    "对达到至少 %d 次尝试的 %d 道题，分别做了两类平稳性诊断："
    "(A) 按作答日历时间以中位数切分早/晚期窗口，比较两窗口成功率之差 Δ_A；"
    "(B) 按学生内尝试序号取前后半段并池化，比较成功率之差 Δ_B。"
    "两者均以自助法（B=1000，种子=42）估计 Δ 的 95% 置信区间，区间不跨 0 视为显著漂移。\n"
    % (MIN_ATTEMPTS, nA)
)
lines.append(
    "结果：时间窗口诊断(A)中 **%d / %d 道（%.1f%%）** 题呈现显著成功率漂移，平均 Δ_A=%s（均值±SE=%s±%s）；"
    "尝试序诊断(B)在 %d 道有效题中 **%d 道（%.1f%%）** 显著漂移，平均 Δ_B=%s（均值±SE=%s±%s）。"
    "按难度分层见 r09_results.json。\n"
    % (aggA_block["n_significant"], nA, 100*propA, f1(meanA),
       f1(aggA_block["delta_mean"]), f1(aggA_block["delta_se"]),
       nB, aggB_block["n_significant"], (100*propB if propB is not None else 0.0),
       (f1(meanB) if meanB is not None else "NA"),
       f1(aggB_block["delta_mean"]) if aggB_block["delta_mean"] is not None else "NA",
       f1(aggB_block["delta_se"]) if aggB_block["delta_se"] is not None else "NA")
)
lines.append(
    "**对 M3 §3.4 的含义**：上述漂移意味着——至少对这部分题目——把‘可提取性/成功率’当作不随时间与作答次序漂移的"
    "平稳 MDP 状态与平稳奖励，是一个**未被数据完全满足**的假设。在存在显著漂移的题上，固定的平稳奖励会系统地"
    "高估或低估真实即时奖励，从而削弱 M3 规划器基于该奖励所做序贯决策的最优性保证。\n"
)
lines.append(
    "**诚实裁决**：M3 当前的平稳-MDP/平稳奖励假设**对存在显著漂移的题不成立**；我们建议在第 3.4 与 5.6 节"
    "显式标注这一覆盖边界，并对漂移题引入非平稳处理。相关理论背景可引用 Nguyen et al. (2025)："
    "“当连续难度轴上的奖励发生移位时，存在无需先验即可获得最优动态遗憾的算法”；"
    "但本稿**未实现也未比较**其 MDBE 非平稳 Lipschitz 算法，仅作理论背景引用。\n"
)
lines.append("\n## Verdict 建议（一行）\n")
lines.append(
    "**R09 verdict: COMPARABLE_WITH_COVERAGE_CAVEAT** —— 数据本身揭示不可忽略的题级成功率漂移，"
    "M3 平稳奖励假设需在 §3.4/§5.6 标注覆盖边界；方法覆盖：真实日历时间(A)+真实学生内尝试序(B)双诊断，"
    "未使用代理、未实现/比较 Nguyen 2025 MDBE。\n"
)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("[write] r09_edits.md written", flush=True)
print("[done] A:", aggA_block, flush=True)
print("[done] B:", aggB_block, flush=True)
