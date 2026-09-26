# -*- coding: utf-8 -*-
"""验证修正后的 fit_irt_1pl_scaled 与骨架 fit_irt_1pl 数学一致（收敛、无 stale 梯度发散）。

判定：
  - spearman_rho(true_b, b_scaled) > 0.95
  - mean|b_scaled - true_b| < 0.30
  - b_scaled 与 b_ref(fit_irt_1pl) 的 spearman/mean-diff 也基本一致（同估计量）
用法：
  python results/m1/_validate_fit_scaled.py
"""
from __future__ import annotations
import random
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_m1_criteria as V
import run_criteria_fit as R


def _gen(J, N, resp_per, seed):
    rng = random.Random(seed)
    true_b = sorted(rng.uniform(-1.5, 1.5) for _ in range(J))
    responses = []
    for p in range(N):
        theta = rng.gauss(0.0, 1.0)
        for j in rng.sample(range(J), resp_per):
            p1 = V._sigmoid(theta - true_b[j])
            c = 1 if rng.random() < p1 else 0
            responses.append((p, j, c))
    return true_b, responses


def _to_arrays(responses, N, J):
    p = []; j = []; c = []
    for (pp, jj, cc) in responses:
        p.append(pp); j.append(jj); c.append(cc)
    return p, j, c


def main() -> int:
    rng_seed = 20260922
    J, N, RESP_PER = 15, 1000, 7
    true_b, responses = _gen(J, N, RESP_PER, rng_seed)
    p, j, c = _to_arrays(responses, N, J)

    # 参考：骨架 fit_irt_1pl（逐响应 product 域，已验证正确）
    b_ref = V.fit_irt_1pl(responses, N, J, n_iter=200)
    # 被测：修正后的 fit_irt_1pl_scaled（规模优化等价版）
    b_scaled = R.fit_irt_1pl_scaled(p, j, c, N, J, n_iter=60)

    rho_ref = V.spearman_rho(true_b, b_ref)
    mdiff_ref = sum(abs(b_ref[k] - true_b[k]) for k in range(J)) / J
    rho_scaled = V.spearman_rho(true_b, b_scaled)
    mdiff_scaled = sum(abs(b_scaled[k] - true_b[k]) for k in range(J)) / J
    rho_between = V.spearman_rho(b_ref, b_scaled)
    mdiff_between = sum(abs(b_scaled[k] - b_ref[k]) for k in range(J)) / J

    print("=" * 70)
    print("修正版 fit_irt_1pl_scaled 验证（合成数据 J=%d N=%d R=%d）" % (J, N, RESP_PER))
    print("=" * 70)
    print(f"  fit_irt_1pl (ref)   : ρ={rho_ref:.4f}  |b−b_true|={mdiff_ref:.4f}")
    print(f"  fit_irt_1pl_scaled  : ρ={rho_scaled:.4f}  |b−b_true|={mdiff_scaled:.4f}")
    print(f"  两实现一致度        : ρ={rho_between:.4f}  |b_scaled−b_ref|={mdiff_between:.4f}")

    ok = (rho_scaled > 0.95 and mdiff_scaled < 0.30
          and rho_ref > 0.95 and mdiff_ref < 0.30
          and rho_between > 0.95 and mdiff_between < 0.15)
    print("  结论:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
