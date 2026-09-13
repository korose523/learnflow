"""难度信号的秩融合（ECDF-logit 公制）—— LearnFlow 难度估计的公制层

为什么需要这一层（依据 `results/Real_data_实验报告.md` 的实测结论）：

* **O1（公制不变量）**：把异质难度信号直接做线性 min-max 融合时，只要对任一信号做
  单调重参数化（换单位、取对数、换量表），各信号的**有效权重**就会漂移：
  在 assist09（346,860 行 / 994 题）上实测线性融合的权重漂移 **L1 均值 0.5357**、
  排序反转率约 67%；改用「经验 CDF → logit」（分位链接）公制后，漂移降到
  **L1 ≈ 1e-4（纯数值噪声）、反转率 0**。
* **O4（多信号增益，DBE-KT22，212 题）**：只用正确率时与专家标注的 Spearman 为
  0.2207；五行为信号（成功率/提示率/自报难度/信任度/时长）秩融合后等权 0.2899，
  权重优化后 5 折 CV **0.4778**。关键机制：自报难度与信任度的**差分**承载主要信号。
* **O5（跨系统复现，Junyi，1,234 题 / 16M 交互）**：无学生反馈字段的"仅性能信号"
  场景下，成功率基线 0.2610 → 等权融合 **0.3629** → CV 优化 0.3837，
  与 DBE 的相对增益（+31% vs +39%）同量级，说明多信号融合不是单数据集特例。
* **O3（负结果，务必注意）**：知识树深度与难度的相关性仅 ρ=+0.0785 且非单调，
  父子边的难度梯度一致性 0.487 ≈ 抛硬币——**禁止用结构深度充当难度代理**。

本模块只做一件事：把任意数量、任意量纲的"越大越难"信号，变换到**秩（分位）公制**
后线性融合。因为 ECDF-logit 对单调变换不变，融合结果不受各信号单位/量表影响。
"""
import math
from typing import Dict, List, Mapping, Optional, Sequence

__all__ = [
    "ecdf_logit", "fuse_signals", "logit_to_fsrs", "EPS",
    "O8_SIGNAL_NAMES", "FUSED6_COLUMNS", "lambda_closed_form", "estimate_o8_difficulty",
]

EPS = 1e-4  # 分位裁剪，避免 logit(0)/logit(1) 发散


def _rank_average(values: Sequence[float]) -> List[float]:
    """并列取平均秩（average rank，1..n）"""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def ecdf_logit(values: Sequence[float]) -> List[float]:
    """经验 CDF → logit 变换（分位链接）。

    对任意严格单调变换 φ，ecdf_logit(φ(x)) == ecdf_logit(x)（秩不变），
    因此不同量纲/单位的信号可以直接相加比较。

    Args:
        values: 原始信号值（同一信号在多个题目上的取值）

    Returns:
        变换后的值，越大表示该项在组内越"靠难的一端"
    """
    if not values:
        return []
    n = len(values)
    ranks = _rank_average(values)
    return [math.log(max(min((r - 0.5) / n, 1 - EPS), EPS) /
                     (1 - max(min((r - 0.5) / n, 1 - EPS), EPS)))
            for r in ranks]


def fuse_signals(
    signals: Mapping[str, Sequence[float]],
    weights: Optional[Mapping[str, float]] = None,
) -> List[float]:
    """多信号 ECDF-logit 秩融合。

    Args:
        signals: {信号名: 每个题目的取值}，所有信号必须等长且**方向一致（越大越难）**。
                 方向相反的信号（如正确率）请调用方先取负号，与 O4/O5 的口径一致。
        weights: 可选权重；缺省等权。权重会被归一化。

    Returns:
        每个题目的融合难度（logit 公制，越大越难）

    Raises:
        ValueError: 信号为空、长度不一致或权重含未知信号名
    """
    if not signals:
        raise ValueError("signals 不能为空")
    names = list(signals.keys())
    n = len(signals[names[0]])
    if n == 0:
        return []
    if any(len(signals[k]) != n for k in names):
        raise ValueError("所有信号长度必须一致")

    if weights is None:
        w = {k: 1.0 / len(names) for k in names}
    else:
        unknown = set(weights) - set(names)
        if unknown:
            raise ValueError(f"未知信号权重: {unknown}")
        total = sum(float(weights.get(k, 0.0)) for k in names)
        if total <= 0:
            raise ValueError("权重之和必须为正")
        w = {k: float(weights.get(k, 0.0)) / total for k in names}

    out = [0.0] * n
    for k in names:
        z = ecdf_logit(signals[k])
        wk = w[k]
        out = [o + wk * v for o, v in zip(out, z)]
    return out


def logit_to_fsrs(z: Sequence[float], lo: float = 1.0, hi: float = 10.0) -> List[float]:
    """把融合 logit 值线性映射到 FSRS 难度区间 [1, 10]。

    注意：跨批次比较请使用 logit 原值（或统一分位基准）；本映射只保证**批内**
    的单调与可比性，便于落库到 TaskDifficulty.d。
    """
    if not z:
        return []
    zmin, zmax = min(z), max(z)
    if zmax - zmin < 1e-12:
        return [(lo + hi) / 2.0] * len(z)
    return [lo + (v - zmin) / (zmax - zmin) * (hi - lo) for v in z]


# ---------------------------------------------------------------------------
# O8 推荐估计器（落库）：fused6 信号集 + 闭式 λ(k) 收缩
# ---------------------------------------------------------------------------
# O8 留出验证（Junyi，k∈{10,25,50,100,200}）结论：
#   * 7 信号等权融合在留出判据下全面劣于仅成功率（O7）。根因是 upgrade_rate 在池内
#     强负相关（k=500 时 −0.756），而 O5 已发表其与专家标签相关 −0.1837 —— 该反向
#     信号被坐标上升优化器错误给了正权重。剔除后得 fused6。
#   * fused6 相对 fused7 在 k=10/25/50/100/200 的 held-out 增益
#     = +1.21/+1.45/+0.30/+0.16/−0.02 pp。
#   * 收缩 score = (1−λ)·success + λ·fused6 的 λ 在题目折半上选、留出半上评；
#     逐 k 经验 λ*(k) = [0.701, 0.524, 0.387, 0.234, 0.125]。
#   * 闭式 λ_cf(k) = 1 / (1 + (k / 27.3) ** 0.895) 直接代入同一留出协议，其在 k 各点
#     的留出 Spearman 与经验 λ* 版本差距均 ≤0.55pp（O8 confirmatory cell），故部署
#     直接用闭式，无需逐 k 拟合 λ。
# 信号方向约定（与 O4/O5 一致）：success_rate 为"越大越易"，其余 6 个为"越大越难"。
# 本层只做秩融合，方向由本函数内部统一（success_rate 取负）。
O8_SIGNAL_NAMES = (
    "success_rate",   # 0 — 越大越易（内部取负）
    "hint_rate",      # 1 — 越大越难
    "attempt_count",  # 2 — 越大越难
    "self_report",    # 3 — 越大越难
    "upgrade_rate",   # 4 — 越大越难（O8：fused6 剔除该强负相关反向信号，对应研究 J_res 列 4）
    "trust",          # 5 — 越大越难
    "duration",       # 6 — 越大越难
)
# O8 结论：upgrade_rate 在池内强负相关（k=500 时 −0.756），且 O5 已发表其与专家标签
# 相关 −0.1837，是被坐标上升优化器错误赋予正权重的反向信号。fused6 通过"按信号名剔除
# upgrade_rate"构造融合列集，避免依赖硬编码列索引（防止重排 O8_SIGNAL_NAMES 时漏剔）。
_O8_DROP_SIGNALS = ("upgrade_rate",)
FUSED6_COLUMNS = tuple(
    i for i, name in enumerate(O8_SIGNAL_NAMES) if name not in _O8_DROP_SIGNALS
)
_UPGRADE_RATE_INDEX = O8_SIGNAL_NAMES.index("upgrade_rate")


def lambda_closed_form(k: float) -> float:
    """O8 部署用闭式样本量收缩系数。

    λ_cf(k) = 1 / (1 + (k / 27.3) ** 0.895)
    在 k∈{10,25,50,100,200} 取值 [0.711, 0.520, 0.368, 0.238, 0.144]，
    与逐 k 经验 λ* 的留出 Spearman 差距均 ≤0.55pp，可直接部署。
    """
    if k <= 0:
        raise ValueError("k（样本量）必须为正")
    return 1.0 / (1.0 + (float(k) / 27.3) ** 0.895)


def estimate_o8_difficulty(
    signals: Mapping[str, Sequence[float]],
    k: int,
) -> List[float]:
    """O8 推荐难度估计器（落库版）。

    输入 7 个原始信号（键见 ``O8_SIGNAL_NAMES``），输出每个题目的融合难度
    （logit 公制，越大越难）：

        transformed[i] = ecdf_logit(signal_i)，success_rate 取负（统一方向）
        success  = transformed[0]
        fused6   = mean(transformed[c] for c in FUSED6_COLUMNS)
        λ        = lambda_closed_form(k)
        score_i  = (1 − λ) · success_i + λ · fused6_i

    Args:
        signals: {信号名: 每个题目的取值}，长度须一致；success_rate 为"越大越易"，
                 其余为"越大越难"。
        k: 用于估计这些信号的样本量（题目数），决定闭式收缩系数。

    Returns:
        每个题目的融合难度（logit 公制，越大越难）。

    Raises:
        ValueError: 信号名缺失/多余、长度不一致、k 非正。
    """
    missing = set(O8_SIGNAL_NAMES) - set(signals)
    if missing:
        raise ValueError(f"缺少 O8 信号: {missing}")
    extra = set(signals) - set(O8_SIGNAL_NAMES)
    if extra:
        raise ValueError(f"未知 O8 信号: {extra}")
    names = list(O8_SIGNAL_NAMES)
    n = len(signals[names[0]])
    if n == 0:
        return []
    if any(len(signals[name]) != n for name in names):
        raise ValueError("所有信号长度必须一致")

    transformed: List[List[float]] = []
    for i, name in enumerate(names):
        z = ecdf_logit(signals[name])
        if i == 0:  # success_rate：越大越易 → 取负统一为越大越难
            z = [-x for x in z]
        transformed.append(z)

    lam = lambda_closed_form(k)
    success = transformed[0]
    col_n = len(FUSED6_COLUMNS)
    fused = [
        sum(transformed[c][idx] for c in FUSED6_COLUMNS) / col_n
        for idx in range(n)
    ]
    return [(1.0 - lam) * success[idx] + lam * fused[idx] for idx in range(n)]
