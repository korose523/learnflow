"""难度公制层回归测试 —— 对应 results/Real_data_实验报告.md 的 O1/O4/O5

覆盖三条实测结论：
1. O1：ECDF-logit 公制对单调重参数化不变（线性 min-max 会漂移 L1=0.5357）。
2. O4/O5：多信号秩融合优于单一正确率信号（DBE 0.2207→0.2899+；Junyi 0.2610→0.3629）。
3. O1 修复：题目难度更新对耗时连续单调，不再有 180s 硬跳变。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
import pytest


class TestEcdfLogitInvariance:
    """O1：分位链接公制必须在单调重参数化下不变"""

    def test_monotone_transform_keeps_values(self):
        from app.services.difficulty_fusion import ecdf_logit
        xs = [0.3, 0.9, 0.15, 0.77, 0.5, 0.05, 0.62]
        base = ecdf_logit(xs)
        # 单调递增变换：对数（需平移保证正数）
        logged = ecdf_logit([math.log(x + 1.0) for x in xs])
        # 立方
        cubed = ecdf_logit([x ** 3 for x in xs])
        # 仿射 + 缩放
        affine = ecdf_logit([17.0 * x - 4.0 for x in xs])
        for a, b in ((base, logged), (base, cubed), (base, affine)):
            assert all(abs(p - q) < 1e-9 for p, q in zip(a, b))

    def test_rank_order_preserved(self):
        from app.services.difficulty_fusion import ecdf_logit
        xs = [5.0, 1.0, 9.0, 3.0]
        z = ecdf_logit(xs)
        # 越大 → logit 越大
        assert z[2] > z[0] > z[3] > z[1]

    def test_constant_signal_is_flat(self):
        from app.services.difficulty_fusion import ecdf_logit
        z = ecdf_logit([0.5] * 6)
        assert all(abs(v - z[0]) < 1e-9 for v in z)

    def test_empty_safe(self):
        from app.services.difficulty_fusion import ecdf_logit
        assert ecdf_logit([]) == []


class TestFuseSignals:
    """多信号秩融合"""

    def test_fusion_improves_over_single_signal(self):
        """O4/O5 的方向性验证：多信号融合的相关性应高于任一单信号"""
        from app.services.difficulty_fusion import fuse_signals
        import random
        rng = random.Random(20260913)
        n = 400
        truth = [rng.random() for _ in range(n)]

        def noisy(scale):
            # 约定：所有信号都必须是"越大越难"，方向由调用方负责统一
            # （实测：混入反向信号会直接抵消融合收益，见 O4/O5 的符号纪律）
            return [t + scale * rng.gauss(0, 1) for t in truth]

        # 三个相互独立的"越大越难"弱信号（含噪声）
        s_success = noisy(1.0)   # 已由调用方取负：正确率 → 难度
        s_time = noisy(1.0)
        s_hint = noisy(1.0)

        def spearman(a, b):
            ra = _ranks(a); rb = _ranks(b)
            ma, mb = sum(ra) / n, sum(rb) / n
            num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
            da = math.sqrt(sum((x - ma) ** 2 for x in ra))
            db = math.sqrt(sum((y - mb) ** 2 for y in rb))
            return num / (da * db)

        single = max(spearman(s, truth) for s in (s_success, s_time, s_hint))
        fused = spearman(fuse_signals({"s": s_success, "t": s_time, "h": s_hint}), truth)
        assert fused > single, f"fused={fused:.3f} single_best={single:.3f}"

    def test_weight_drift_zero_under_reparameterization(self):
        """融合权重在信号单调重参数化下零漂移（O1 的 L1≈1e-4 结论）"""
        from app.services.difficulty_fusion import fuse_signals
        xs = [0.2, 0.8, 0.35, 0.9, 0.1, 0.55]
        ys = [12.0, 3.0, 9.0, 1.0, 15.0, 6.0]
        w = {"x": 0.4, "y": 0.6}
        base = fuse_signals({"x": xs, "y": ys}, w)
        # 对 y 做单调变换（换单位：ms、对数、平方）
        for trans in (lambda v: v * 1000.0, lambda v: math.log(v), lambda v: v ** 2):
            alt = fuse_signals({"x": xs, "y": [trans(v) for v in ys]}, w)
            assert max(abs(p - q) for p, q in zip(base, alt)) < 1e-9

    def test_weights_normalized_and_validated(self):
        from app.services.difficulty_fusion import fuse_signals
        xs, ys = [1.0, 2.0, 3.0], [3.0, 1.0, 2.0]
        a = fuse_signals({"x": xs, "y": ys})
        b = fuse_signals({"x": xs, "y": ys}, {"x": 5.0, "y": 5.0})
        assert all(abs(p - q) < 1e-9 for p, q in zip(a, b))
        with pytest.raises(ValueError):
            fuse_signals({"x": xs, "y": ys}, {"z": 1.0})
        with pytest.raises(ValueError):
            fuse_signals({"x": xs, "y": [1.0, 2.0]})

    def test_logit_to_fsrs_bounds(self):
        from app.services.difficulty_fusion import fuse_signals, logit_to_fsrs
        z = fuse_signals({"a": [1.0, 5.0, 3.0], "b": [2.0, 2.0, 9.0]})
        d = logit_to_fsrs(z)
        assert all(1.0 <= v <= 10.0 for v in d)
        # 保持单调
        order = sorted(range(3), key=lambda i: z[i])
        assert d[order[0]] < d[order[-1]]


class TestTaskDifficultyUpdateSmoothness:
    """O1 修复：耗时不再走硬阈值"""

    def _score(self, correct, seconds, hint=False):
        from app.services.optimal_difficulty import OptimalDifficultyEngine
        return OptimalDifficultyEngine._evidence_score(correct, seconds, hint)

    def test_monotone_in_time(self):
        # 答对：越慢 → 证据分越低（题目越难）
        fast = self._score(True, 10)
        mid = self._score(True, 120)
        slow = self._score(True, 900)
        assert fast > mid > slow >= 3.0
        # 答错：越慢 → 证据分越低（越难），区间 [1,2]
        assert self._score(False, 10) > self._score(False, 900) >= 1.0

    def test_no_jump_at_legacy_threshold(self):
        """旧实现在 180s 处有 4.0→3.0 的跳变；新实现必须连续"""
        a = self._score(True, 179)
        b = self._score(True, 181)
        assert abs(a - b) < 0.02, f"179s={a:.3f} 181s={b:.3f} 存在跳变"

    def test_hint_penalty(self):
        assert self._score(True, 30, hint=True) < self._score(True, 30)

    def test_missing_time_is_neutral(self):
        from app.services.optimal_difficulty import OptimalDifficultyEngine as E
        assert abs(E._slowness(None) - 0.5) < 1e-9
        assert 1.0 <= self._score(True, None) <= 4.0

    def test_evidence_score_in_bounds(self):
        for secs in (0.0, 1.0, 30.0, 180.0, 3600.0, None):
            for ok in (True, False):
                for hint in (True, False):
                    s = self._score(ok, secs, hint)
                    assert 1.0 <= s <= 4.0

    def test_engine_update_direction_preserved(self):
        from app.services.optimal_difficulty import (
            optimal_difficulty_engine as eng, TaskDifficulty,
        )
        t = TaskDifficulty(d=5.0)
        t = eng.update_task_difficulty(t, was_correct=True, time_spent_seconds=30)
        assert t.d < 5.0                     # 快速答对 → 更简单（与旧契约一致）
        t2 = TaskDifficulty(d=5.0)
        t2 = eng.update_task_difficulty(t2, was_correct=False, time_spent_seconds=600)
        assert t2.d > 5.0                    # 慢速答错 → 更难


def _ranks(values):
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r
