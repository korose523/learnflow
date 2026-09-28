"""Thompson Sampling（多臂老虎机）最小正确实现 —— 补齐算法透明度声明的「难度推荐」。

背景
----
``app/api/gamification.py`` 的 ``/transparency/explain`` 接口（``algorithm="difficulty"``）
声明难度推荐使用 **Thompson Sampling（多臂老虎机）**，把不同难度级别视为不同的「臂」，
每次推荐选择预期学习收益最大的题目，Beta(α, β) 参数随答题结果更新。但此前运行时代码里
**没有对应的采样实现**——本模块补齐这一缺口。

算法（标准 Thompson Sampling for Bernoulli rewards）
-------------------------------------------------
每个臂 k 维护一个 Beta(α_k, β_k) 后验：
  * 答对（正反馈）⇒ α_k += 1
  * 答错（负反馈）⇒ β_k += 1
每次需要选臂时，从每个臂的后验各采一个样本 θ_k ~ Beta(α_k, β_k)，选 θ 最大的臂。
这就是「把 Beta 后验画成样本再取 argmax」，天然平衡探索（后验方差大→偶尔被选中）与
利用（后验均值高→稳定被选中）。

本模块只提供**纯采样原语**（零第三方依赖，与 difficulty_fusion / difficulty_m4 一致），
不持有运行时后验状态；调用方（难度推荐器）负责维护每个难度臂的 (α, β) 并在答题后更新。

@todo（接入选择逻辑，待难度推荐器调用）
  * 在难度推荐器（``optimal_difficulty.py`` / ``difficulty_fusion.py`` 的选题入口）中，
    为每个候选难度级别维护 ``(alpha, beta)`` 后验计数；
  * 答对后 ``alpha += 1``、答错后 ``beta += 1``（见 ``update_posterior``）；
  * 每题推荐时调用 ``thompson_sample(arms)`` 选出下一个难度臂，而非仅按 85% 心流规则硬选。
  签名：``thompson_sample(arms: Sequence[Tuple[float, float]], rng=None) -> int``
        ``arms`` 为 ``[(alpha_0, beta_0), (alpha_1, beta_1), ...]``，返回选中臂下标。
"""
from __future__ import annotations

import math
import random
from typing import Optional, Sequence, Tuple

__all__ = ["beta_sample", "thompson_sample", "update_posterior"]


def _gamma_sample(shape: float, rng: random.Random) -> float:
    """从 Gamma(shape, scale=1) 采样（Marsaglia & Tsang 2000 方法）。

    shape < 1 时用提升技巧 ``Gamma(a) = Gamma(a+1) * U^(1/a)`` 归约到 shape≥1。
    """
    if shape <= 0.0:
        raise ValueError("shape 必须为正")
    if shape < 1.0:
        # 提升：Gamma(a) = Gamma(a+1) * U^(1/a)
        u = rng.random()
        return _gamma_sample(shape + 1.0, rng) * (u ** (1.0 / shape))
    d = shape - 1.0 / 3.0
    c = 1.0 / math.sqrt(9.0 * d)
    while True:
        # 标准正态（Box–Muller 取一维）
        x = rng.gauss(0.0, 1.0)
        v = (1.0 + c * x) ** 3
        if v <= 0.0:
            continue
        u = rng.random()
        # 接受判据（Marsaglia–Tsang）
        if u < 1.0 - 0.0331 * (x * x) * (x * x):
            return d * v
        if math.log(u) < 0.5 * x * x + d * (1.0 - v + math.log(v)):
            return d * v


def beta_sample(alpha: float, beta: float, rng: Optional[random.Random] = None) -> float:
    """从 Beta(α, β) 采一个样本，范围 (0, 1)。

    用 Beta = Gamma(α)/(Gamma(α)+Gamma(β)) 的恒等式（两个独立 Gamma 采样），
    避免 scipy / numpy 依赖。α, β 必须为正。
    """
    if alpha <= 0.0 or beta <= 0.0:
        raise ValueError("alpha 与 beta 必须为正")
    rng = rng or random._inst
    x = _gamma_sample(alpha, rng)
    y = _gamma_sample(beta, rng)
    return x / (x + y)


def thompson_sample(
    arms: Sequence[Tuple[float, float]],
    rng: Optional[random.Random] = None,
) -> int:
    """Thompson Sampling 选臂：对每个臂从 Beta(α, β) 采一个样本，返回样本最大的臂下标。

    Args:
        arms: 臂列表，每项为 ``(alpha, beta)``；下标即臂编号（如难度级别 0..K-1）。
        rng:  可选 ``random.Random`` 实例（可复现实验用）；缺省用全局随机源。

    Returns:
        选中臂的下标（``argmax_k Beta(α_k, β_k)``）。``arms`` 为空时抛 ``ValueError``。

    这是标准 Bernoulli 奖励 Thompson Sampling 的核心一步；调用方负责在每轮反馈后
    用 ``update_posterior`` 推进各臂后验（见模块 docstring 的 @todo）。
    """
    if not arms:
        raise ValueError("arms 不能为空")
    rng = rng or random._inst
    best_idx = 0
    best_theta = -1.0
    for i, (a, b) in enumerate(arms):
        theta = beta_sample(a, b, rng)
        if theta > best_theta:
            best_theta = theta
            best_idx = i
    return best_idx


def update_posterior(alpha: float, beta: float, success: bool) -> Tuple[float, float]:
    """按一轮反馈推进某臂的 Beta(α, β) 后验。

    success=True（如答对）⇒ α += 1；success=False（如答错）⇒ β += 1。
    返回更新后的 ``(alpha, beta)``。冷启动可用 ``(1.0, 1.0)``（均匀先验）。
    """
    if success:
        return alpha + 1.0, beta
    return alpha, beta + 1.0
