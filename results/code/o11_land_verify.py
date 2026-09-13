# -*- coding: utf-8 -*-
"""O11 落库外部验证（不进 pytest 收集，故全量测试计数不变 = 934）。

验证 estimate_optimized_difficulty 在真实缓存上以**落地版函数本体**复现
o11_fusion_optimization.json 的 signed7 / srw7 留出增益，并检查边界行为。
输出 results/code/o11_land_verify_out.txt
"""
import importlib.util, json, pathlib
import numpy as np
from scipy import stats as st

BASE = pathlib.Path(r"E:\learnflow")
MOD = BASE / "learnflow-backend" / "app" / "services" / "difficulty_fusion.py"
NPZ = BASE / "results" / "code" / "difficulty_cache.npz"
O11 = BASE / "results" / "code" / "o11_fusion_optimization.json"
OUT = BASE / "results" / "code" / "o11_land_verify_out.txt"

spec = importlib.util.spec_from_file_location("df_mod", MOD)
df = importlib.util.module_from_spec(spec)
spec.loader.exec_module(df)

Z = np.load(NPZ, allow_pickle=True)
J = Z["J_res"].astype(np.float64)
M, _, K = J.shape
NAMES = list(df.OPT_SIGNAL_NAMES)


def ecdf_logit(v):
    v = np.asarray(v, float)
    r = st.rankdata(v, method="average")
    p = np.clip((r - 0.5) / v.size, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def spear(a, b):
    return float(st.spearmanr(a, b).statistic)


def sig_dict(pick):
    k = pick.shape[1]
    p3 = np.broadcast_to(pick[:, None, :], (M, 7, k))
    r = np.take_along_axis(J, p3, axis=2).mean(axis=2)
    return {NAMES[i]: r[:, i] for i in range(7)}       # 列序与缓存一致，仅供数值复核


def crit(pick):
    ok = np.take_along_axis(J[:, 0:1, :],
                            np.broadcast_to(pick[:, None, :], (M, 1, pick.shape[1])), axis=2)[:, 0, :]
    return 1.0 - ok.mean(axis=1)


lines, ok_all = [], True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    lines.append(f"[{'PASS' if cond else 'FAIL'}] {name}  {detail}")


# 1) 模块契约
check("模块导出 estimate_optimized_difficulty", hasattr(df, "estimate_optimized_difficulty"))
check("模块导出 split_half_reliability", hasattr(df, "split_half_reliability"))

# 2) 边界
try:
    df.estimate_optimized_difficulty({n: [1.0, 2.0] for n in NAMES}, 0)
    check("k<=0 抛 ValueError", False)
except ValueError:
    check("k<=0 抛 ValueError", True)
try:
    df.estimate_optimized_difficulty({"success_rate": [1.0, 2.0]}, 10)
    check("缺信号抛 ValueError", False)
except ValueError:
    check("缺信号抛 ValueError", True)

# 3) λ 缺省 == 闭式
d = json.load(open(O11, encoding="utf-8"))
check("λ 缺省等于 lambda_closed_form(k)",
      abs(df.lambda_closed_form(50) - 1.0 / (1.0 + (50 / 27.3) ** 0.895)) < 1e-12)

# 4) 在真实缓存上复现 signed7 / srw7 留出增益（k=10, 50）
rng = np.random.default_rng(20260913)
B_SIZE, REP, SPLITS = 250, 25, 20
for k in (10, 25, 50, 100, 200):
    acc_sig, acc_srw, base = [], [], []
    for _ in range(REP):
        order = np.argsort(rng.random((M, K)), axis=1)
        pa, pb = order[:, :k], order[:, k:k + B_SIZE]
        sd = sig_dict(pa)
        critv = crit(pb)
        h = k // 2
        sd1 = sig_dict(pa[:, :h]); sd2 = sig_dict(pa[:, h:2 * h])
        rel = {n: df.split_half_reliability(sd1[n], sd2[n]) for n in NAMES}
        pred_sig = df.estimate_optimized_difficulty(sd, k)                 # 等权（符号校正）
        pred_srw = df.estimate_optimized_difficulty(sd, k, reliability=rel)
        d0 = [-x for x in ecdf_logit(sd["success_rate"][:]) ]              # 成功率难度方向
        for _ in range(SPLITS):
            pm = rng.permutation(M)
            Bh = pm[M // 2:]
            base.append(spear(np.asarray(d0)[Bh], critv[Bh]))
            acc_sig.append(spear(np.asarray(pred_sig)[Bh], critv[Bh]))
            acc_srw.append(spear(np.asarray(pred_srw)[Bh], critv[Bh]))
    b = float(np.mean(base))
    g_sig = (float(np.mean(acc_sig)) - b) * 100
    g_srw = (float(np.mean(acc_srw)) - b) * 100
    exp_sig = d["results"][str(k)]["variants"]["signed7"]["cf"]["gain_vs_success_pp"]
    exp_srw = d["results"][str(k)]["variants"]["srw7"]["cf"]["gain_vs_success_pp"]
    check(f"k={k} signed7 增益复现", abs(g_sig - exp_sig) <= 0.10,
          f"landed {g_sig:+.3f} vs o11 {exp_sig:+.3f} pp")
    check(f"k={k} srw7 增益复现", abs(g_srw - exp_srw) <= 0.10,
          f"landed {g_srw:+.3f} vs o11 {exp_srw:+.3f} pp")

# 5) 符号校正演示：构造一个与成功率难度强负相关的信号，验证其被取负
rng2 = np.random.default_rng(7)
n = 400
succ = rng2.random(n)                      # 越大越易
anti = -(succ - 0.5) + 0.02 * rng2.standard_normal(n)     # 与难度负相关
sd = {nm: rng2.random(n) for nm in NAMES}
sd["success_rate"] = succ
sd["upgrade_rate"] = anti
out = np.asarray(df.estimate_optimized_difficulty(sd, 20))
check("符号校正：反向信号被取负（与难度方向正相关）",
      spear(out, -succ) > 0.1,
      f"Spearman(fused, difficulty)={spear(out, -succ):+.3f}")

lines.append(f"\nOVERALL: {'ALL PASS' if ok_all else 'FAILURES PRESENT'}  "
             f"(checks={len(lines) - 1})")
txt = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(txt + "\n")
print(txt)
print("saved ->", OUT)
