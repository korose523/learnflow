"""实验功效分析 (Power Analysis) —— 样本量预注册 (§3.4.2 改造 5)

为什么需要这个模块
-----------------------------------------------------------------------------
原 ``ab_test_framework`` 的 ``min_sample_per_group=100`` 是硬编码常量，**无功效分析**；
且整群随机（班级级）的设计效应 DEFF 完全缺失。忽略 DEFF 是最隐蔽的统计错误：
m=30、ρ=0.05 → DEFF=2.45，即样本量需 ×2.45（见治理方案 §3.4.2 与第 1483 行附近表格）。

本模块把「每组所需样本量」变成**由功效分析写入、可复算**的值，支持：
- 连续结局 (Cohen's d)：``required_n_per_group``
- 二分类结局 (两组率差)：``required_n_two_proportion``
- 整群随机设计效应：``design_effect``
- 一键出方案：``plan_experiment`` -> ``PowerPlan``

所有函数纯计算、可单测，不依赖数据库/框架实例。
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from statistics import NormalDist
from typing import Optional


def design_effect(cluster_size: int, icc: float) -> float:
    """整群随机设计效应 DEFF = 1 + (m-1)·ρ。

    m=30, ρ=0.05 → 2.45。单随机（cluster_size=1 或 icc=0）时 DEFF=1。
    """
    if cluster_size < 1:
        return 1.0
    return 1.0 + (cluster_size - 1) * max(0.0, icc)


def required_n_per_group(d: float, alpha: float = 0.05,
                         power: float = 0.80, deff: float = 1.0) -> int:
    """连续结局 (Cohen's d) 每组样本量。

    来源: n = 2·(z_{1-α/2} + z_{1-β})² / d²  (two-sided, equal n)，再乘 DEFF。
    """
    if d <= 0:
        return 0
    nd = NormalDist()
    z_a = nd.inv_cdf(1 - alpha / 2)
    z_b = nd.inv_cdf(power)
    return ceil(2 * (z_a + z_b) ** 2 / (d * d) * deff)


def required_n_two_proportion(p1: float, p2: float, alpha: float = 0.05,
                              power: float = 0.80, deff: float = 1.0) -> int:
    """二分类结局两组率差每组样本量 (Fleiss 法近似)。

    p1=对照组率, p2=实验组率。p̄=(p1+p2)/2。结果乘 DEFF。
    """
    if p1 <= 0 or p1 >= 1 or p2 <= 0 or p2 >= 1:
        raise ValueError("p1/p2 必须落在 (0,1) 区间")
    delta = abs(p2 - p1)
    if delta <= 0:
        return 0
    nd = NormalDist()
    z_a = nd.inv_cdf(1 - alpha / 2)
    z_b = nd.inv_cdf(power)
    p_bar = (p1 + p2) / 2.0
    num = (z_a * sqrt(2 * p_bar * (1 - p_bar))
           + z_b * sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return ceil(num / (delta * delta) * deff)


@dataclass
class PowerPlan:
    """功效分析方案输出（可序列化为实验预注册记录）。"""
    metric_type: str                 # "continuous" | "binary"
    effect_size: float               # Cohen's d 或绝对率差
    alpha: float
    power: float
    icc: float
    cluster_size: int
    deff: float
    required_n_per_group: int
    total_n: int                     # 两组合计（已含 DEFF）
    required_clusters: int           # 整群随机所需最小班级数
    assumptions: str = ""

    def to_dict(self) -> dict:
        return {
            "metric_type": self.metric_type,
            "effect_size": self.effect_size,
            "alpha": self.alpha,
            "power": self.power,
            "icc": self.icc,
            "cluster_size": self.cluster_size,
            "deff": round(self.deff, 4),
            "required_n_per_group": self.required_n_per_group,
            "total_n": self.total_n,
            "required_clusters": self.required_clusters,
            "assumptions": self.assumptions,
        }


def plan_experiment(
    effect_size: float,
    metric_type: str = "continuous",
    baseline_rate: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.80,
    cluster_size: int = 30,
    icc: float = 0.05,
) -> PowerPlan:
    """一键生成实验样本量方案（预注册用）。

    Args:
        effect_size: 连续结局传 Cohen's d；二分类结局传绝对率差 (0<Δ≤1)。
        metric_type: "continuous" 或 "binary"。
        baseline_rate: 二分类结局的对照组基线率 p1。
        alpha/power: 检验水准与功效。
        cluster_size: 整群随机每班人数 m（=1 退化为个体随机）。
        icc: 组内相关系数 ρ。
    """
    deff = design_effect(cluster_size, icc)

    if metric_type == "binary":
        if not (0 < baseline_rate < 1):
            raise ValueError("binary 结局 baseline_rate 必须落在 (0,1)")
        p1 = baseline_rate
        p2 = min(0.999, max(0.001, p1 + effect_size))
        n = required_n_two_proportion(p1, p2, alpha, power, deff)
    else:
        n = required_n_per_group(effect_size, alpha, power, deff)

    total_n = n * 2
    required_clusters = ceil(total_n / cluster_size) if cluster_size >= 1 else 0
    assumptions = (
        f"two-sided α={alpha}, power={power}, "
        f"cluster_size={cluster_size}, icc={icc}, DEFF={deff:.2f}"
    )
    return PowerPlan(
        metric_type=metric_type,
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        icc=icc,
        cluster_size=cluster_size,
        deff=deff,
        required_n_per_group=n,
        total_n=total_n,
        required_clusters=required_clusters,
        assumptions=assumptions,
    )
