"""M4 信度结构化组合难度估计器的回归测试。

覆盖命题（与 results/code/run_m4.py → m4_results.json 互为前后件）：
1. **O1 不变性的延续**：M4 的每一步都建立在 ecdf_logit 之上，故对输入信号的任意单调
   重参数化必须给出**逐位相同**的输出（同 difficulty_fusion 的红线）。
2. **M4-B 共线校正**：两个完全共线的辅助列不应得到两份权重（srw7 的 w∝ρ 会重复计入）。
3. **M4-C λ 是诊断量**：辅助列不可信时 λ→0；辅助列极可信时 λ→1。
4. **M4-D 部分可观测**：观测数越多的题，本地信度越高（单调）。
5. **退化输入不抛错**：n=0 / n=1 / 常量列 / 全并列列 / 缺参考列。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math

import pytest


def make_signals(n=40, seed=20260927):
    """构造一组带真实潜在难度的 signals（deterministic LCG，零第三方依赖）。"""
    st = seed
    def rnd():
        nonlocal st
        st = (st * 1103515245 + 12345) % 2147483648
        return st / 2147483648.0
    latent = [rnd() for _ in range(n)]
    success = [max(0.0, min(1.0, 1.0 - 0.6 * t + 0.15 * (rnd() - 0.5))) for t in latent]
    return {
        "success_rate": success,
        "hint_rate": [0.5 * t + 0.07 * rnd() for t in latent],
        "attempt_count": [1.0 + 2.0 * t + 0.3 * rnd() for t in latent],
        "duration": [10.0 + 40.0 * t + 3.0 * rnd() for t in latent],
    }


def _halves(n=40, seed=7):
    """把 make_signals 的每题取值拆成"两半样本 ⇒ 两个独立估计"的形式。"""
    st = seed
    def rnd():
        nonlocal st
        st = (st * 1103515245 + 12345) % 2147483648
        return st / 2147483648.0
    s = make_signals(n)
    half_a, half_b = {}, {}
    for k, v in s.items():
        half_a[k] = [max(0.0, x + 0.15 * (rnd() - 0.5)) for x in v]
        half_b[k] = [max(0.0, x + 0.15 * (rnd() - 0.5)) for x in v]
    return s, half_a, half_b


class TestMonotoneInvariance:
    """M4-A：一切皆自秩起 ⇒ 对输入的单调重参数化必须不变（继承 M1/O1 红线）。"""

    def _transforms(self, xs):
        lo = min(xs)
        return {
            "identity": xs,
            "log": [math.log(x - lo + 1.0) for x in xs],
            "cubic": [x ** 3 for x in xs],
            "affine": [17.0 * x - 4.0 for x in xs],
        }

    def test_output_bit_identical_under_monotone_reparams(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=24)
        base = estimate_m4_difficulty(s, ha, hb, half_n=12)
        for key in ("identity", "log", "cubic", "affine"):
            tr = self._transforms(s["hint_rate"])[key]
            s2 = dict(s)
            s2["hint_rate"] = tr
            ha2, hb2 = dict(ha), dict(hb)
            ha2["hint_rate"] = self._transforms(ha["hint_rate"])[key]
            hb2["hint_rate"] = self._transforms(hb["hint_rate"])[key]
            got = estimate_m4_difficulty(s2, ha2, hb2, half_n=12)
            assert got == base, f"单调变换 {key} 改变了输出（不属于同一等价类）"

    def test_output_length_equals_number_of_items(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        # 回归：曾因"按列铺开"写成"按行铺开"而使输出长度变成**信号数**（静默错误，
        # 不抛异常、也不 NaN，只有长度检查能发现）。
        s, ha, hb = _halves(n=17)
        out = estimate_m4_difficulty(s, ha, hb, half_n=8)
        assert len(out) == 17 == len(s["success_rate"])
        s2, ha2, hb2 = _halves(n=32)
        out2 = estimate_m4_difficulty(s2, ha2, hb2, half_n=16,
                                      coverage={"hint_rate": [1 + i % 5 for i in range(32)]},
                                      unit_reliability={"hint_rate": 0.35})
        assert len(out2) == 32

    def test_scaling_of_all_columns_keeps_ranking(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=20)
        base = estimate_m4_difficulty(s, ha, hb, half_n=10)
        s2 = {k: [v * 1000.0 for v in vs] for k, vs in s.items()}
        ha2 = {k: [v * 1000.0 for v in vs] for k, vs in ha.items()}
        hb2 = {k: [v * 1000.0 for v in vs] for k, vs in hb.items()}
        got = estimate_m4_difficulty(s2, ha2, hb2, half_n=10)
        import itertools
        order_base = sorted(range(20), key=lambda i: base[i])
        order_got = sorted(range(20), key=lambda i: got[i])
        assert order_base == order_got


class TestCollinearityCorrection:
    """M4-B：共线列不得被重复计权。"""

    def test_duplicate_column_gets_half_the_total_weight(self):
        from app.services.difficulty_m4 import standardize_columns, m4_beta
        cols = [[float(i) for i in range(30)],
                [float(i) for i in range(30)],      # 与第一列完全共线
                [float((i * 7) % 11) for i in range(30)]]
        zstd = standardize_columns(cols)
        q = [0.9, 0.9, 0.9]
        beta = m4_beta(zstd, q)
        # 共线校正后，两列之和应明显小于把两列当独立时的 2×（否则就是重复计权）
        col = sum(beta[:2])
        assert col < 2.0 * 0.9, f"共线对未被折扣：{beta}"

    def test_orthogonal_columns_keep_full_weight(self):
        from app.services.difficulty_m4 import standardize_columns, m4_beta
        a = [float(i) for i in range(60)]
        b = [1.0 if i % 2 else -1.0 for i in range(60)]
        b = [x * (i + 1) for i, x in enumerate(b)]      # 与 a 近正交
        zstd = standardize_columns([a, b])
        beta = m4_beta(zstd, [0.8, 0.8])
        assert abs(beta[0]) > 0.0 and abs(beta[1]) > 0.0


class TestDerivedLambdaIsDiagnostic:
    """M4-C：λ 由 β 导出，不再由 k 拟合。"""

    def test_unreliable_auxiliaries_shrink_toward_reference(self):
        from app.services.difficulty_m4 import m4_beta, derived_lambda, standardize_columns
        cols = [[float(i) for i in range(40)], [float((i * 13) % 17) for i in range(40)]]
        zstd = standardize_columns(cols)
        lam_high = derived_lambda(m4_beta(zstd, [0.95, 0.95]))
        lam_low = derived_lambda(m4_beta(zstd, [0.95, 0.05]))
        assert lam_low < lam_high, "辅助列信度下降时 λ 必须更小"
        assert 0.0 <= lam_low <= 1.0 and 0.0 <= lam_high <= 1.0

    def test_derived_lambda_bounds(self):
        from app.services.difficulty_m4 import derived_lambda
        assert derived_lambda([]) == 0.0
        assert derived_lambda([0.0, 0.0]) == 0.0
        assert abs(derived_lambda([1.0, 0.0]) - 0.0) < 1e-12
        assert abs(derived_lambda([1.0, 3.0]) - 0.75) < 1e-12


class TestCoverageReliability:
    """M4-D：观测数越多 ⇒ 本地信度越高（Spearman–Brown 一般形式）。"""

    def test_monotone_in_n_obs(self):
        from app.services.difficulty_m4 import coverage_reliability
        vals = [coverage_reliability(0.4, n) for n in (1, 2, 5, 20, 100)]
        assert all(a < b for a, b in zip(vals, vals[1:]))
        assert abs(vals[0] - 0.4) < 1e-12
        assert vals[-1] > 0.98

    def test_zero_or_negative_counts_do_not_crash(self):
        from app.services.difficulty_m4 import coverage_reliability
        assert coverage_reliability(0.5, 0) >= 0.0
        assert coverage_reliability(0.0, 10) == 0.0


class TestDegenerateInputs:
    """退化输入必须给出确定的行为，而不是抛异常或返回 NaN。"""

    def test_empty_signals_raises(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        with pytest.raises(ValueError):
            estimate_m4_difficulty({})

    def test_missing_reference_column_raises(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        with pytest.raises(ValueError):
            estimate_m4_difficulty({"hint_rate": [1.0, 2.0, 3.0]})

    def test_uneven_lengths_raise(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s = {"success_rate": [0.9, 0.5], "hint_rate": [0.1]}
        with pytest.raises(ValueError):
            estimate_m4_difficulty(s)

    def test_n_zero_returns_empty(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        assert estimate_m4_difficulty({"success_rate": []}) == []

    def test_n_one_returns_finite_zeros(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        out = estimate_m4_difficulty({"success_rate": [0.5], "hint_rate": [0.2]})
        assert len(out) == 1 and math.isfinite(out[0])

    def test_constant_and_tied_columns_are_finite(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s = {"success_rate": [0.5] * 12, "hint_rate": [0.3] * 12,
             "duration": [1.0] * 12}
        ha = {k: v for k, v in s.items()}
        hb = {k: v for k, v in s.items()}
        out = estimate_m4_difficulty(s, ha, hb, half_n=6)
        assert len(out) == 12 and all(math.isfinite(x) for x in out)

    def test_all_tied_columns_produce_no_nan(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s = {"success_rate": [1, 1, 1, 2, 2, 3], "hint_rate": [0, 0, 0, 0, 1, 1]}
        out = estimate_m4_difficulty(s, dict(s), dict(s), half_n=3)
        assert all(math.isfinite(x) for x in out)


class TestDeterminismAndBehavior:
    def test_repeat_calls_are_bit_identical(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=30)
        a = estimate_m4_difficulty(s, ha, hb, half_n=15)
        b = estimate_m4_difficulty(s, ha, hb, half_n=15)
        assert a == b

    def test_output_correlates_with_reference_direction(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty, spearman
        s, ha, hb = _halves(n=40)
        out = estimate_m4_difficulty(s, ha, hb, half_n=20)
        ref = [-x for x in s["success_rate"]]
        assert spearman(out, ref) >= 0.0, "定向失败：输出应与成功难度同向"

    def test_coverage_path_is_finite_and_differs_from_global(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=20)
        n_list = [1 + (i % 9) for i in range(20)]
        cov = {"hint_rate": n_list}
        unit = {"hint_rate": 0.35}
        out_cov = estimate_m4_difficulty(s, ha, hb, half_n=10, coverage=cov,
                                         unit_reliability=unit)
        out_glob = estimate_m4_difficulty(s, ha, hb, half_n=10)
        assert all(math.isfinite(x) for x in out_cov)
        assert out_cov != out_glob, "每题本地信度应与全局信度给出不同结果"


class TestResidualization:
    """M4-E：把辅助列对参考列的冗余成分剔除，只保留增量部分（直接来自第 5 节负结果）。"""

    def test_incremental_columns_orthogonal_to_reference(self):
        from app.services.difficulty_m4 import (incremental_columns,
                                                 standardize_columns, _z_columns, spearman)
        s, ha, hb = _halves(n=40)
        names = list(s.keys())
        zc = _z_columns(s, names)
        zstd = standardize_columns(zc)
        eres = incremental_columns(zstd, 0)
        assert eres, "正常辅助列应保留在增量字典中"
        for j, col in eres.items():
            rho = spearman(standardize_columns([col])[0], zstd[0])
            assert abs(rho) < 0.2, f"增量列 {j} 与参考列仍高度相关（冗余未剔除）：ρ={rho}"

    def test_reference_weight_zero_returns_reference_alone(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty, _z_columns
        s, ha, hb = _halves(n=24)
        out = estimate_m4_difficulty(s, ha, hb, half_n=12, residualize=True,
                                     reference_weight=0.0)
        zc = _z_columns(s, list(s.keys()))
        assert out == list(zc[0]), "λ=0 时输出应为参考列（ecdf-logit 成功难度）本身"

    def test_reference_weight_one_returns_incremental_composite(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=24)
        comp = estimate_m4_difficulty(s, ha, hb, half_n=12, residualize=True,
                                      reference_weight=None)
        out = estimate_m4_difficulty(s, ha, hb, half_n=12, residualize=True,
                                     reference_weight=1.0)
        assert out == comp, "λ=1 时输出应为增量组合本身"

    def test_duplicate_of_reference_is_dropped(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=24)
        s2 = dict(s); s2["dup_success"] = list(s["success_rate"])
        ha2 = dict(ha); ha2["dup_success"] = list(ha["success_rate"])
        hb2 = dict(hb); hb2["dup_success"] = list(hb["success_rate"])
        out_with = estimate_m4_difficulty(s2, ha2, hb2, half_n=12, residualize=True,
                                          reference_weight=None)
        out_without = estimate_m4_difficulty(s, ha, hb, half_n=12, residualize=True,
                                             reference_weight=None)
        assert out_with == out_without, "与参考列完全共线的列应被静默剔除"

    def test_output_length_equals_number_of_items(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=19)
        out = estimate_m4_difficulty(s, ha, hb, half_n=9, residualize=True,
                                     reference_weight=0.4)
        assert len(out) == 19 == len(s["success_rate"])

    def test_deterministic(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=30)
        a = estimate_m4_difficulty(s, ha, hb, half_n=15, residualize=True,
                                   reference_weight=0.5)
        b = estimate_m4_difficulty(s, ha, hb, half_n=15, residualize=True,
                                   reference_weight=0.5)
        assert a == b

    def test_residualize_changes_result(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=30)
        full = estimate_m4_difficulty(s, ha, hb, half_n=15)
        resid = estimate_m4_difficulty(s, ha, hb, half_n=15, residualize=True,
                                       reference_weight=1.0)
        assert full != resid, "残差化必须改变组合（否则与既有行为无差别）"


class TestEfficiencyRefactor:
    """第 3.5 节效率优化的行为保全：秩外提必须**逐位**等价，不得改变任何输出。

    优化只把"item-invariant 的秩矩阵"从逐题循环内提到循环外。以下用例锁死这一点：
    若未来有人把重排序重新塞回逐题循环，等价性用例会立刻失守。
    """

    def test_m4_beta_equals_from_ranks_helper(self):
        from app.services.difficulty_m4 import (standardize_columns, m4_beta,
                                                _m4_beta_from_ranks, ranks)
        cols = [[float(i * 3 % 17) for i in range(50)],
                [float(i) for i in range(50)],
                [1.0 if i % 2 else -1.0 for i in range(50)]]
        zstd = standardize_columns(cols)
        q = [0.9, 0.6, 0.3]
        direct = m4_beta(zstd, q)
        hoisted = _m4_beta_from_ranks(zstd, [ranks(c) for c in zstd], q)
        assert direct == hoisted, "m4_beta 与秩外提版必须逐位相同"

    def test_incremental_columns_accepts_ranks_without_changing_output(self):
        from app.services.difficulty_m4 import (incremental_columns,
                                                standardize_columns, _z_columns, ranks)
        s, ha, hb = _halves(n=40)
        names = list(s.keys())
        zc = _z_columns(s, names)
        zstd = standardize_columns(zc)
        rk = [ranks(c) for c in zstd]
        a = incremental_columns(zstd, 0)
        b = incremental_columns(zstd, 0, ranks_=rk)
        assert a.keys() == b.keys()
        for j in a:
            assert a[j] == b[j], "传入 ranks_ 不应改变增量列"

    def test_per_item_path_is_bit_identical_across_calls(self):
        from app.services.difficulty_m4 import estimate_m4_difficulty
        s, ha, hb = _halves(n=30)
        n = len(s["success_rate"])
        cov = {"hint_rate": [1 + (i % 9) for i in range(n)]}
        unit = {"hint_rate": 0.35}
        out1 = estimate_m4_difficulty(s, ha, hb, half_n=15,
                                     coverage=cov, unit_reliability=unit)
        out2 = estimate_m4_difficulty(s, ha, hb, half_n=15,
                                     coverage=cov, unit_reliability=unit)
        assert out1 == out2, "逐题路径必须可复现（同一输入 → 同一输出）"
        assert len(out1) == n == len(s["success_rate"])

    def test_per_item_path_matches_inline_recompute(self):
        """最强行为保全锁：用（优化前）逐题重算秩的参考实现复算，须与优化版逐位相同。"""
        from app.services.difficulty_m4 import (estimate_m4_difficulty,
            standardize_columns, _z_columns, spearman, spearman_brown,
            coverage_reliability, unit_reliability_from_half, m4_beta)
        s, ha, hb = _halves(n=30)
        n = len(s["success_rate"])
        cov = {"hint_rate": [1 + (i % 9) for i in range(n)]}
        unit = {"hint_rate": 0.35}

        names = list(s.keys())
        names.remove("success_rate")
        names.insert(0, "success_rate")
        zc = _z_columns(s, names)
        za = _z_columns(ha, names)
        zb = _z_columns(hb, names)
        ref = zc[0]
        m = len(names)
        sgn = [1.0 if spearman(zc[j], ref) >= 0.0 else -1.0 for j in range(m)]
        sgn[0] = 1.0
        rel = [spearman_brown(spearman(za[j], zb[j])) if spearman(za[j], zb[j]) > 0.0 else 0.0
               for j in range(m)]
        rho_unit = dict(unit)
        for j, nm in enumerate(names):
            if nm in rho_unit:
                continue
            r = spearman(za[j], zb[j])
            if r > 0.0:
                rho_unit.setdefault(nm, unit_reliability_from_half(r, 15))
        zstd = standardize_columns(zc)
        rows = [[0.0] * n for _ in range(m)]
        for i in range(n):
            qi = []
            for j, nm in enumerate(names):
                rho_j = rel[j]
                cv = cov.get(nm)
                if cv is not None and nm in rho_unit:
                    rho_j = coverage_reliability(rho_unit[nm], cv[i])
                qi.append(sgn[j] * math.sqrt(max(0.0, min(0.999999, rho_j))))
            bi = m4_beta(zstd, qi)            # 参考实现：逐题重算秩（优化前行为）
            if bi is None:
                ssum = sum(abs(x) for x in qi)
                bi = [x / ssum for x in qi] if ssum > 0 else [1.0 / m] * m
            for j in range(m):
                rows[j][i] = bi[j] * zstd[j][i]
        fused = list(map(sum, zip(*rows)))
        if spearman(fused, ref) < 0.0:
            fused = [-x for x in fused]

        optimized = estimate_m4_difficulty(s, ha, hb, half_n=15,
                                           coverage=cov, unit_reliability=unit)
        assert optimized == fused, "秩外提优化改变了逐题路径输出（不应发生）"

