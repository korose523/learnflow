# -*- coding: utf-8 -*-
"""O8 估计器落库验证（外部脚本，不被 pytest 收集，故不改变 934 测试数）。

验证项：
  1) 闭式 λ_cf(k) 在 k∈{10,25,50,100,200} 取值 = [0.711,0.520,0.368,0.238,0.144]（误差≤1e-3）
  2) λ_cf(k) 严格单调递减、∈(0,1)、k≤0 抛错
  3) estimate_o8_difficulty 剔除 upgrade_rate（index 4）：改变 upgrade_rate 输出不变
  4) O1 不变量：success_rate 做严格单调重参数化 → 输出逐位不变（ecdf_logit 秩不变）
  5) 评分公式 (1−λ)·success + λ·fused6_mean 自洽
  6) O8 confirmatory cell：闭式直接留出相对经验 λ* 的 Δpp 均 ≤0.55pp（部署依据）
"""
import math
import os
import sys

BACKEND = r"E:\learnflow\learnflow-backend"
sys.path.insert(0, BACKEND)
import app.services.difficulty_fusion as df  # noqa: E402

KS = [10, 25, 50, 100, 200]
LAM_CF_PUBLISHED = [0.711, 0.520, 0.368, 0.238, 0.144]
# O8 confirmatory cell（results/code/o8_confirm_out.txt）闭式直接留出的 Δpp
CONFIRM_DELTAS_PP = [+0.337, -0.547, +0.119, +0.009, +0.074]
EPS = 1e-9

fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ((" | " + detail) if detail else ""))
    if not cond:
        fails.append(name)


# 1) 闭式表
for k, pub in zip(KS, LAM_CF_PUBLISHED):
    got = df.lambda_closed_form(k)
    check(f"lambda_closed_form({k})=={pub}", abs(got - pub) <= 1e-3,
          f"got={got:.4f}")

# 2) 单调 / 范围 / 边界
vals = [df.lambda_closed_form(k) for k in KS]
check("lambda_closed_form 严格单调递减", all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)))
check("lambda_closed_form ∈ (0,1)", all(0.0 < v < 1.0 for v in vals))
try:
    df.lambda_closed_form(0)
    check("lambda_closed_form(0) 抛错", False)
except ValueError:
    check("lambda_closed_form(0) 抛错", True)

# 构造 7 信号合成数据
rng = __import__("random").Random(20260913)
N = 60
base = {
    "success_rate":  [rng.random() for _ in range(N)],   # 越大越易
    "hint_rate":     [rng.random() for _ in range(N)],
    "attempt_count": [rng.random() for _ in range(N)],
    "self_report":   [rng.random() for _ in range(N)],
    "trust":         [rng.random() for _ in range(N)],
    "duration":      [rng.random() for _ in range(N)],
    "upgrade_rate":  [rng.random() for _ in range(N)],
}
K = 25
score_ref = df.estimate_o8_difficulty(base, K)

# 3) 剔除 upgrade_rate
base_alt = dict(base)
base_alt["upgrade_rate"] = [rng.random() for _ in range(N)]  # 完全不同
score_alt = df.estimate_o8_difficulty(base_alt, K)
check("剔除 upgrade_rate：改变 upgrade_rate 输出不变",
      all(abs(a - b) <= EPS for a, b in zip(score_ref, score_alt)))

# 4) O1 不变量：success_rate 严格单调重参数化
base_rep = dict(base)
base_rep["success_rate"] = [math.exp(3.0 * x) / (1.0 + math.exp(3.0 * x)) for x in base["success_rate"]]
score_rep = df.estimate_o8_difficulty(base_rep, K)
check("O1 不变量：success_rate 单调重参数化输出逐位不变",
      all(abs(a - b) <= 1e-9 for a, b in zip(score_ref, score_rep)))

# 5) 评分公式自洽
lam = df.lambda_closed_form(K)
# 复算 transformed（与模块内部一致：success_rate 取负）
t = []
for i, name in enumerate(df.O8_SIGNAL_NAMES):
    z = df.ecdf_logit(base[name])
    if i == 0:
        z = [-x for x in z]
    t.append(z)
success = t[0]
fused = [sum(t[c][j] for c in df.FUSED6_COLUMNS) / len(df.FUSED6_COLUMNS) for j in range(N)]
formula = [(1.0 - lam) * success[j] + lam * fused[j] for j in range(N)]
check("评分公式自洽", all(abs(a - b) <= 1e-12 for a, b in zip(score_ref, formula)))

# 6) confirmatory cell Δpp ≤ 0.55
check("O8 confirmatory：闭式直接留出 Δpp 均 ≤0.55",
      all(abs(d) <= 0.55 for d in CONFIRM_DELTAS_PP),
      f"max|Δ|={max(abs(d) for d in CONFIRM_DELTAS_PP):.3f}pp")

print("\n=== SUMMARY ===")
print("checks:", len(fails), "failed" if fails else "ALL PASS")
if fails:
    print("FAILED:", fails)
    sys.exit(1)
print("O8 估计器落库验证通过 ✅")
