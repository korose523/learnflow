# -*- coding: utf-8 -*-
"""O10：学生级留出验证（补 O7 最大的效度缺口）。

O7 把每道题的作答记录切成互斥的 A/B 两段，但**切的是记录不是学生**——同一学生的多次
作答可能同时落在 A 与 B，两者的误差并不独立，审稿人会据此质疑"泛化"的说法。

O10 按 **uuid 哈希**把 72,758 名学生切成两半：
  * 估计样本 A：只用 A 半学生在该练习上的前 k 条作答（蓄水池，半内 K=250）
  * 判据：只用 B 半学生的**全部**作答算真实难度 1 − ok_B / n_B
A、B 的学生集合互斥 → 估计误差与判据误差来自两批不同的人，是真正的**跨学生泛化**检验。

比较：success_only / fused6（剔除升级率）/ fused7（O5 原配置）
     以及 λ 收缩版，λ 用 O9 已验证的公式 λ*(k)=1/(1+(k/27.3)^0.895)（**不调参**），
     并同时报告折半挑出的经验 λ* 作对照。

输出 results/code/o10_user_holdout.json
"""
import csv, json, random, time, zlib
import numpy as np
from scipy import stats as st


def user_half(uuid):
    """学生分半：用 crc32 而非内置 hash()。

    内置 hash() 对 str 每次进程随机加盐（PYTHONHASHSEED），会导致 A/B 切分
    不可复现——对需要写进论文的留出实验是硬伤。crc32 稳定，且按 uuid 缓存后
    （仅 7 万余个不同学生）开销可忽略。
    """
    h = _HC.get(uuid)
    if h is None:
        h = _HC[uuid] = zlib.crc32(uuid.encode("utf-8")) & 1
    return h


_HC = {}

BASE = "E:/learnflow"
OUT = BASE + "/results/code/o10_user_holdout.json"
HK = 250                       # 每个 (练习, 半) 的蓄水池容量
KS = [10, 25, 50, 100, 200]
REP, SPLITS = 25, 20
LAM = np.round(np.arange(0.0, 1.01, 0.05), 2)
K0, P_EXP = 27.332, 0.895            # O9 样本外拟合值，本脚本不再调参
COLS6 = [0, 1, 2, 3, 5, 6]
DIFF = {"easy": 1, "normal": 2, "hard": 3}

t0 = time.time()
meta = {}
with open(BASE + "/data/junyi/Info_Content.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        meta[row["ucid"]] = row["difficulty"]

# half: (exercise, half) -> accumulators for criterion (half B) and reservoir (both halves)
accB = {}                       # ucid -> [n, ok]          判据：B 半全量
resA = {}                       # ucid -> np.ndarray(7, HK)  A 半蓄水池
cnt = {}
nrow = 0
random.seed(20260913)
with open(BASE + "/data/junyi/Log_Problem.csv", encoding="utf-8", newline="") as f:
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
            a[0] += 1
            a[1] += ok
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

MIN_B = 500
ucids = sorted(u for u, a in accB.items() if a[0] >= MIN_B and cnt.get(u, 0) >= HK)
print("exercises with >=%d B-half rows and full A reservoir:" % MIN_B, len(ucids), flush=True)
m = len(ucids)
idx = {u: i for i, u in enumerate(ucids)}
RA = np.zeros((m, 7, HK), dtype=np.float32)
yB = np.zeros(m)                      # 判据：B 半真实难度 = 1 - ok/n
nA = np.zeros(m, dtype=int)
nB = np.zeros(m, dtype=int)
for i, u in enumerate(ucids):
    RA[i] = resA[u]
    a = accB[u]
    nB[i] = a[0]
    yB[i] = 1.0 - a[1] / a[0]
    nA[i] = min(cnt[u], HK)


def ecdf_logit(v):
    v = np.asarray(v, dtype=float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def k_signals(k, perm):
    S = RA[:, :, perm[:k]].sum(axis=2)
    r = S / float(k)
    return np.column_stack([
        -ecdf_logit(r[:, 0]), ecdf_logit(r[:, 1]), ecdf_logit(r[:, 2]),
        ecdf_logit(r[:, 3]), ecdf_logit(r[:, 4]), ecdf_logit(r[:, 5]),
        ecdf_logit(r[:, 6]),
    ])


rng = np.random.default_rng(20260913)
out = {}
print("\n k  | estimator      | ρ(留存学生判据) | λ̂   | ρ(λ̂)   | 增益")
for k in KS:
    lam_hat = float(1.0 / (1.0 + (k / K0) ** P_EXP))
    acc = {"success": [], "fused6": [], "fused7": [],
           "mix6_hat": [], "mix6_emp": []}
    picks = []
    for rep in range(REP):
        M = k_signals(k, rng.permutation(HK))
        s = M[:, 0]
        f6 = M[:, COLS6].mean(1)
        f7 = M.mean(1)
        acc["success"].append(spear(s, yB))
        acc["fused6"].append(spear(f6, yB))
        acc["fused7"].append(spear(f7, yB))
        acc["mix6_hat"].append(spear((1 - lam_hat) * s + lam_hat * f6, yB))
        for _ in range(SPLITS):
            pm = rng.permutation(m)
            A, B = pm[: m // 2], pm[m // 2:]
            sc = np.array([spear(((1 - l) * s + l * f6)[A], yB[A]) for l in LAM])
            bi = int(np.nanargmax(sc))
            picks.append(float(LAM[bi]))
            acc["mix6_emp"].append(spear(((1 - LAM[bi]) * s + LAM[bi] * f6)[B], yB[B]))
    row = {kk: round(float(np.mean(v)), 4) for kk, v in acc.items()}
    row["lambda_hat"] = round(lam_hat, 3)
    row["lambda_emp_mean"] = round(float(np.mean(picks)), 3)
    row["gain_mix6_hat_pp"] = round((row["mix6_hat"] - row["success"]) * 100, 3)
    row["gain_fused6_raw_pp"] = round((row["fused6"] - row["success"]) * 100, 3)
    out[str(k)] = row
    print("%3d | success        | %.4f          |     |        |" % (k, row["success"]))
    print("    | fused7 (O5)    | %.4f          |     |        | %+.3f pp" % (
        row["fused7"], (row["fused7"] - row["success"]) * 100))
    print("    | fused6         | %.4f          |     |        | %+.3f pp" % (
        row["fused6"], row["gain_fused6_raw_pp"]))
    print("    | mix6 λ̂(公式)  | %.4f          | %.2f |        | %+.3f pp" % (
        row["mix6_hat"], lam_hat, row["gain_mix6_hat_pp"]))
    print("    | mix6 λ*_emp    | %.4f          | %.2f |        |" % (
        row["mix6_emp"], row["lambda_emp_mean"]), flush=True)

json.dump({
    "design": "O10 student-level holdout: users split by uuid hash into disjoint halves; "
              "difficulty estimated from k reservoir rows of half-A students, criterion is "
              "the true difficulty 1-ok/n computed on ALL rows of half-B students",
    "n_exercises": m, "min_B_rows": MIN_B, "reservoir_per_half": HK,
    "k_list": KS, "reps": REP, "splits": SPLITS,
    "lambda_formula": {"k0": K0, "p": P_EXP, "note": "from O9 out-of-sample fit, not retuned here"},
    "results": out,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ->", OUT)
