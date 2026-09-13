# -*- coding: utf-8 -*-
"""O12：学生级留出验证（O10 协议）下重跑 O11 优化估计器。

目的：把 O11 在**记录级**（o11_fusion_optimization.py，Junyi，蓄水池槽位 A/B 互斥）
验证出的优化（符号校正 + 可靠性加权，srw7）搬到 **学生级**留出（O10 协议）复核：
  * 学生按 crc32(uuid) 奇偶切成互斥两半；
  * 难度只用 A 半学生在该练习上的 k 条蓄水池作答估计；
  * 判据用 B 半学生**全部**作答的真实难度 1 − ok_B / n_B（≥500 条）。
这样估计误差与判据误差来自两批不同的人，是真正的跨学生泛化检验。

比较：success（基线）/ fused6（O8）/ srw7（O11）
λ 策略：λ_cf(k)=1/(1+(k/27.3)^0.895)（O9 已部署闭式）与 λ_rel=1−ρ_success(A)（可靠性驱动）；
并给出 srw7−fused6 的配对差（500 组 = REP×SPLITS）、胜率与 Wilcoxon 符号秩 p。

所有符号 / 权重 / λ 只在 A 半学生数据内估计，判据只用 B 半学生，杜绝泄漏。
输出 results/code/o12_student_o11.json
"""
import csv, json, random, time, zlib
import numpy as np
from scipy import stats as st

BASE = r"E:\learnflow"
OUT = BASE + r"\results\code\o12_student_o11.json"

HK = 250
KS = [10, 25, 50, 100, 200]
REP, SPLITS = 25, 20
COLS6 = [0, 1, 2, 3, 5, 6]
DIFF = {"easy": 1, "normal": 2, "hard": 3}
MIN_B = 500

_HC = {}


def user_half(uuid):
    h = _HC.get(uuid)
    if h is None:
        h = _HC[uuid] = zlib.crc32(uuid.encode("utf-8")) & 1
    return h


# ---------------------------------------------------------------- 扫描原始日志
t0 = time.time()
meta = {}
with open(BASE + r"\data\junyi\Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = row["difficulty"]

accB, resA, cnt = {}, {}, {}
nrow = 0
random.seed(20260913)
with open(BASE + r"\data\junyi\Log_Problem.csv", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        u = row["ucid"]
        if meta.get(u) not in DIFF:
            continue
        half = user_half(row["uuid"])
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
        if half == 1:
            a = accB.get(u)
            if a is None:
                a = accB[u] = [0, 0]
            a[0] += 1; a[1] += ok
        else:
            c = cnt.get(u, 0) + 1
            cnt[u] = c
            r = resA.get(u)
            if c <= HK:
                if r is None:
                    r = resA[u] = np.zeros((7, HK), dtype=np.float32)
                r[:, c - 1] = (ok, hint, dur, att, up, down, rep)
            else:
                j = random.randrange(c)
                if j < HK:
                    r[:, j] = (ok, hint, dur, att, up, down, rep)
        nrow += 1
        if nrow % 4_000_000 == 0:
            print("rows", nrow // 1_000_000, "M |", round(time.time() - t0, 1), "s", flush=True)
print("scan done", nrow, "rows", round(time.time() - t0, 1), "s", flush=True)

ucids = sorted(u for u, a in accB.items() if a[0] >= MIN_B and cnt.get(u, 0) >= HK)
m = len(ucids)
print("exercises with >=%d B-half rows and full A reservoir: %d" % (MIN_B, m), flush=True)
RA = np.zeros((m, 7, HK), dtype=np.float32)
yB = np.zeros(m)
for i, u in enumerate(ucids):
    RA[i] = resA[u]
    a = accB[u]
    yB[i] = 1.0 - a[1] / a[0]


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def k_signals(k, sl):
    r = RA[:, :, sl].sum(axis=2) / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


def lambda_cf(k):
    return 1.0 / (1.0 + (k / 27.3) ** 0.895)


rng = np.random.default_rng(20260913)
out = {}
print("\n k | success | fused6 | srw7@λcf | srw7@λrel | Δ(srw7-fused6) pp | win | p")
for k in KS:
    lam_cf = lambda_cf(k)
    e = {"success": [], "fused6": [], "srw7_cf": [], "srw7_rel": []}
    pair = []
    lam_rel_v = []
    for rp in range(REP):
        perm = rng.permutation(HK)
        M7 = k_signals(k, perm[:k])
        d0 = M7[:, 0]
        h = k // 2
        M1 = k_signals(h, perm[:h])
        M2 = k_signals(h, perm[h:2 * h])
        rel = np.array([spear(M1[:, i], M2[:, i]) for i in range(7)])
        sgn = np.array([1.0 if spear(M7[:, i], d0) >= 0 else -1.0 for i in range(7)])
        sgn[0] = 1.0
        w = np.maximum(rel, 0.0)
        w = w / w.sum() if w.sum() > 0 else np.ones(7) / 7.0
        fused6 = M7[:, COLS6].mean(1)
        srw7 = (M7 * (sgn * w)).sum(1)
        lam_rel = 1.0 - max(0.0, float(spear(M1[:, 0], M2[:, 0])))
        lam_rel_v.append(lam_rel)
        e["success"].append(spear(d0, yB))
        e["fused6"].append(spear(fused6, yB))
        e["srw7_cf"].append(spear((1 - lam_cf) * d0 + lam_cf * srw7, yB))
        e["srw7_rel"].append(spear((1 - lam_rel) * d0 + lam_rel * srw7, yB))
        for _ in range(SPLITS):
            pm = rng.permutation(m)
            B = pm[m // 2:]
            r_s6 = spear((1 - lam_cf) * d0[B] + lam_cf * fused6[B], yB[B])
            r_s7 = spear((1 - lam_cf) * d0[B] + lam_cf * srw7[B], yB[B])
            pair.append(r_s7 - r_s6)
    succ = float(np.mean(e["success"]))
    f6 = float(np.mean(e["fused6"]))
    s7 = float(np.mean(e["srw7_cf"]))
    s7r = float(np.mean(e["srw7_rel"]))
    pair = np.array(pair)
    try:
        pval = float(st.wilcoxon(pair).pvalue)
    except ValueError:
        pval = float("nan")
    out[str(k)] = {
        "success": round(succ, 4), "fused6": round(f6, 4),
        "srw7_lambda_cf": round(s7, 4), "srw7_lambda_rel": round(s7r, 4),
        "gain_fused6_pp": round((f6 - succ) * 100, 3),
        "gain_srw7_cf_pp": round((s7 - succ) * 100, 3),
        "gain_srw7_rel_pp": round((s7r - succ) * 100, 3),
        "srw7_minus_fused6_pp": round(float(pair.mean()) * 100, 3),
        "win_rate": round(float((pair > 0).mean()), 3),
        "wilcoxon_p": pval,
        "lambda_cf": round(lam_cf, 3),
        "lambda_rel_mean": round(float(np.mean(lam_rel_v)), 3),
    }
    print("%3d | %.4f | %.4f | %.4f | %.4f | %+.3f | %.2f | %.2e" % (
        k, succ, f6, s7, s7r, out[str(k)]["srw7_minus_fused6_pp"],
        out[str(k)]["win_rate"], pval), flush=True)

json.dump({
    "design": "O12 student-level holdout (O10 protocol) rerun with O11 estimator srw7 "
              "(sign-corrected + split-half-reliability-weighted fusion, all 7 signals) and "
              "reliability-driven lambda. Users split by crc32(uuid); signs/weights/lambda "
              "estimated on A-half students only.",
    "n_exercises": m, "min_B_rows": MIN_B, "reservoir_per_half": HK,
    "k_list": KS, "reps": REP, "splits": SPLITS,
    "lambda_cf_formula": "1/(1+(k/27.3)^0.895)",
    "lambda_rel_definition": "1 - split_half_reliability_of_success(A)",
    "results": out,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
