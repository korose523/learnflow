"""Experimental rank-based difficulty fusion and residualization heuristics.

This module preserves the existing estimator outputs. The variants are alternatives
for comparison; fused6, signed7 and srw7 are not mathematical special cases.

For positive-definite V=Cov(z) and q=Cov(z,t), a population linear predictor with
maximum squared correlation has beta proportional to V^{-1}q. With independent
single-factor errors, V=qq^T+diag(1-rho), giving weights proportional to
sign*sqrt(rho)/(1-rho). V=I instead gives beta=q. The implemented Spearman matrix,
split-half reliability proxy and ridge are a heuristic and do not establish those
population assumptions, validity, or optimal prediction of teacher difficulty.

The absolute beta share is a diagnostic, not an optimized mixture coefficient.
Residualizing auxiliary columns removes a fitted linear component but does not
prove incremental validity. Coverage extrapolation assumes the Spearman-Brown
model; informative missingness is not corrected by that formula.

Outputs are exploratory scores, not validated student difficulty or learning
benefit. Current corrected methods and all-k results are in
results/m4/m4_correction_evaluation.json and docs/M4_methods_correction_EN.md.
"""
import math
from typing import Dict, List, Mapping, Optional, Sequence

from app.services.difficulty_fusion import ecdf_logit

__all__ = [
    "M4_DEFAULT_SIGNALS", "ranks", "spearman", "standardize_columns",
    "spearman_brown", "unit_reliability_from_half", "coverage_reliability",
    "incremental_columns", "m4_beta", "derived_lambda", "estimate_m4_difficulty",
]

# 与 difficulty_fusion.OPT_SIGNAL_NAMES 同序；本模块允许**只给其中一部分**
# （不同系统的可用列不同，例如 DBE-KT22 没有 upgrade_rate / downgrade / repeat）。
M4_DEFAULT_SIGNALS = (
    "success_rate",   # 参考列：越大越**易**，内部取负
    "hint_rate",
    "attempt_count",
    "self_report",
    "upgrade_rate",
    "trust",
    "duration",
)
_REF = M4_DEFAULT_SIGNALS[0]
_RIDGE = 1e-3        # V 的对角阻尼：常量列 / 全并列列会让 V 接近奇异


# ---------------------------------------------------------------- 基础统计
def ranks(values: Sequence[float]) -> List[float]:
    """并列取平均秩（1..n）。"""
    n = len(values)
    order = sorted(range(n), key=values.__getitem__)
    out = [0.0] * n
    i = 0
    while i < n:
        j = i
        pivot = values[order[i]]
        while j + 1 < n and values[order[j + 1]] == pivot:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            out[order[t]] = avg
        i = j + 1
    return out


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    ma = sum(a) / n
    mb = sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0.0 or vb <= 0.0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Spearman ρ（平均秩上的 Pearson）。告警：**对 NaN 未定义**，调用方须先行清洗。"""
    return _pearson(ranks(a), ranks(b))


def standardize_columns(cols: List[Sequence[float]]) -> List[List[float]]:
    """逐列去均值除标准差（值为 0 的列退化为全 0 列，不抛错）。"""
    out = []
    for c in cols:
        n = len(c)
        if n == 0:
            out.append([])
            continue
        m = sum(c) / n
        var = sum((x - m) ** 2 for x in c) / n
        s = math.sqrt(var) if var > 0.0 else 1.0
        out.append([(x - m) / s for x in c])
    return out


def spearman_brown(r_half: float) -> float:
    """Spearman–Brown：折半信度 → 全长信度 ρ = 2r/(1+r)（r≤0 按 0 处理）。"""
    r = max(0.0, min(0.999999, float(r_half)))
    return 2.0 * r / (1.0 + r)


def unit_reliability_from_half(r_half: float, half_n: int) -> float:
    """由半长样本信度反解**单次观测**信度 ρ₁：ρ(h)=hρ₁/(1+(h−1)ρ₁) ⇒ ρ₁=r/(h−(h−1)r)。"""
    r = max(0.0, min(0.999999, float(r_half)))
    h = max(1.0, float(half_n))
    den = h - (h - 1.0) * r
    return r / den if den > 0.0 else 0.0


def coverage_reliability(rho_unit: float, n_obs: int) -> float:
    """Spearman–Brown 一般形式：给定单次观测信度，返回 n 次观测后的信度。"""
    n = max(1, int(n_obs))
    rho = max(0.0, min(0.999999, float(rho_unit)))
    return n * rho / (1.0 + (n - 1) * rho)


# ---------------------------------------------------------------- M4 核心
def _rank_covariance(rk: Sequence[Sequence[float]], ridge: float = _RIDGE) -> List[List[float]]:
    """由**已算好的秩矩阵** rk 构造秩相关协方差 V（M4-A）。

    秩矩阵 rk 只依赖标准化列、与题目无关（item-invariant），故可由调用方在逐题
    循环外预先算一次并复用，避免每次求解都重排所有列（见 `_m4_beta_from_ranks`
    与 `estimate_m4_difficulty` 的 per-item 路径优化，第 3.5 节）。
    """
    m = len(rk)
    V = [[0.0] * m for _ in range(m)]
    for i in range(m):
        V[i][i] = 1.0 + ridge
        for j in range(i + 1, m):
            v = _pearson(rk[i], rk[j])
            V[i][j] = v
            V[j][i] = v
    return V


def _m4_beta_from_ranks(
    zstd: Sequence[Sequence[float]],
    rk: Sequence[Sequence[float]],
    q: Sequence[float],
    ridge: float = _RIDGE,
) -> List[float]:
    """M4-B：信度结构化、共线校正的组合权重 β = V^{-1} q（接受预处理秩矩阵 rk）。

    与 `m4_beta` 等价，但当 rk 已由调用方算好时省去对全部列的重排序——在
    `estimate_m4_difficulty` 的逐题（per-item）路径中，zstd 的秩对所有题目相同，
    这样把 O(n·m·n·log n) 的重复排序压成一次 O(m·n·log n)：结果**逐位相同**
    （rk 由同一 `ranks` 函数算得，V 与 `_solve` 完全不变，见第 3.5 节）。
    """
    m = len(zstd)
    if m == 0:
        return []
    return _solve(_rank_covariance(rk, ridge), list(q))


def m4_beta(
    zstd: Sequence[Sequence[float]],
    q: Sequence[float],
    ridge: float = _RIDGE,
) -> List[float]:
    """M4-B：信度结构化、共线校正的组合权重 β = V^{-1} q。

    Args:
        zstd: 已标准化的指示列（每行一道题，每列一个信号）。
        q:    载荷向量；``q_k = sgn_k · sqrt(ρ_k)``（符号与信度合并为一个参数）。
        ridge: V 的对角阻尼。

    Returns:
        β（未归一）。V 奇异时用 |q| 归一兜底——常量列情况下这是唯一安全的选择。

    Note:
        等价于 `_m4_beta_from_ranks(zstd, [ranks(c) for c in zstd], q)`；后者供
        `estimate_m4_difficulty` 在逐题路径中复用预处理秩（见第 3.5 节）。
    """
    m = len(zstd)
    if m == 0:
        return []
    return _m4_beta_from_ranks(zstd, [ranks(c) for c in zstd], q, ridge)


def _solve(A: List[List[float]], b: List[float]) -> List[float]:
    """高斯消元（部分选主元）。奇异时返回 None，由调用方兜底。"""
    m = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(m):
        piv = max(range(c, m), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            return None
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        for r in range(c + 1, m):
            f = M[r][c] / pv
            if f:
                for t in range(c, m + 1):
                    M[r][t] -= f * M[c][t]
    x = [0.0] * m
    for r in range(m - 1, -1, -1):
        acc = M[r][m]
        for t in range(r + 1, m):
            acc -= M[r][t] * x[t]
        x[r] = acc / M[r][r]
    return x


def derived_lambda(beta: Sequence[float], ref: int = 0) -> float:
    """M4-C：把组合权重换算成"辅助信号占比" λ ∈ [0,1]，作为**诊断量**返回。

    λ→0 表示辅助列整体不可信，估算器事实上退回纯成功率；λ→1 表示几乎完全依赖辅助列。
    """
    m = len(beta)
    if m == 0:
        return 0.0
    absb = [abs(x) for x in beta]
    tot = sum(absb)
    if tot <= 0.0:
        return 0.0
    ref = max(0, min(m - 1, ref))
    return (tot - absb[ref]) / tot


def _z_columns(signals: Mapping[str, Sequence[float]], names: Sequence[str]) -> List[List[float]]:
    """逐列 ECDF-logit；参考列（success_rate）取负，统一为"越大越难"。"""
    cols = []
    for name in names:
        z = ecdf_logit(signals[name])
        if name == _REF:
            z = [-x for x in z]
        cols.append(z)
    return cols


def incremental_columns(
    zstd: Sequence[Sequence[float]],
    ref: int = 0,
    skip: Optional[Sequence[int]] = None,
    ranks_: Optional[Sequence[Sequence[float]]] = None,
) -> Dict[int, List[float]]:
    """M4-E：把每个辅助列对**参考列**的冗余成分剔除，返回单位方差的"增量列"。

    动机直接来自第 3.2 / 第 5 节的负结果：辅助信号与成功率高度共线 ⟹ 单纯提高辅助
    列信度（ρ_k 随 k 上升）只会买到**冗余**而非增量信息，在外生教师标签上表现为收益
    随 k 塌缩。残差化把这一结构显式化：组合项被约束为"成功率之外的增量"，它与参考列
    **秩相关意义上正交**，于是 λ 的含义从"整体缩放参考列"变为"增量信息值多少"。

    实现与 ``results/code/run_m4.py`` 的 M4-E 完全一致：用**秩相关**系数 ρ 做去除，
    但在**标准化值空间**做残差（与实验同口径，便于复算）；随后除以 √(1−ρ²) 使其单位
    方差。注意：因残差与参考列近正交，"与参考列定向"在此无意义，调用方不应再调 orient。

    Args:
        zstd: 已标准化的指示列。
        ref:  参考列下标（默认 0）。
        skip: 需要整列剔除的下标集合（与 run_m4 的 J_DROP 对应）。

    Returns:
        {列下标: 增量列}；完全共线的列自动不进字典。
    """
    m = len(zstd)
    if m == 0:
        return {}
    rk = ranks_ if ranks_ is not None else [ranks(c) for c in zstd]
    n = len(zstd[ref])
    out: Dict[int, List[float]] = {}
    for j in range(m):
        if j == ref or (skip and j in set(skip)):
            continue
        rho = _pearson(rk[j], rk[ref])
        d2 = 1.0 - rho * rho
        if d2 <= 1e-6:                      # 与参考列完全共线 ⟹ 无增量信息，剔除
            continue
        s = math.sqrt(d2)
        out[j] = [(zstd[j][i] - rho * zstd[ref][i]) / s for i in range(n)]
    return out


def estimate_m4_difficulty(
    signals: Mapping[str, Sequence[float]],
    half_a: Optional[Mapping[str, Sequence[float]]] = None,
    half_b: Optional[Mapping[str, Sequence[float]]] = None,
    half_n: Optional[int] = None,
    coverage: Optional[Mapping[str, Sequence[int]]] = None,
    unit_reliability: Optional[Mapping[str, float]] = None,
    orient_to_reference: bool = True,
    residualize: bool = False,
    reference_weight: Optional[float] = None,
    drop: Optional[Sequence[str]] = None,
) -> List[float]:
    """M4 组合式难度估计。返回每题一个实数（越大越难，仅保证**排序**有意义）。

    Args:
        signals: {信号名: 每题取值}。必须含 ``success_rate``（参考列，越大越易）；
                 其余列可用任意一个，不要求与 ``M4_DEFAULT_SIGNALS`` 完全对齐。
        half_a / half_b: 拟合段两半互不重叠的同类 signals，用于估计逐列折半信度。
                 **两者都必须给出**，否则退化为"符号校正 + 等权"（等价于 signed7），
                 并在文档层面明确这不是 M4 的可用配置。
        half_n:   每半的样本量，用于把折半信度外推到单次观测信度（M4-D 需要）。
        coverage: {信号名: 每题有效观测数}；与 unit_reliability 同列给出时才生效。
        unit_reliability: {信号名: 单次观测信度 ρ₁}。
        orient_to_reference: 输出是否定向为与参考列正相关（默认 True）。

    Returns:
        每题分数列表；空输入返回空列表；n<2 时返回全 0（信度无从估计）。

    Raises:
        ValueError: signals 为空 / 缺参考列 / 各列长度不一致 / coverage 长度不符。
    """
    if not signals:
        raise ValueError("signals 不能为空")
    if _REF not in signals:
        raise ValueError(f"缺少参考列 {_REF}（M4 需要它来统一方向与定义 λ 的分母）")
    names = list(signals.keys())
    # 参考列固定排在第 0 位（derived_lambda 与评测脚本都按此约定）
    if _REF in names:
        names.remove(_REF)
        names.insert(0, _REF)
    # 整列剔除（与 run_m4 的 J_DROP 对应，例如 Junyi 的 upgrade_rate 不进组合）
    drop_set = set(drop or [])
    names = [nm for nm in names if nm not in drop_set]
    n = len(signals[names[0]])
    for nm in names:
        if len(signals[nm]) != n:
            raise ValueError("所有信号长度必须一致")
    if n == 0:
        return []
    if n < 2 or half_a is None or half_b is None:
        # 退化路径：没有信度信息 ⇒ 只做符号校正 + 等权（= signed7），明确记录不推荐。
        zc = _z_columns(signals, names)
        ref = zc[0]
        rows = []
        for j, col in enumerate(zc):
            sgn = 1.0 if spearman(col, ref) >= 0.0 else -1.0
            rows.append([sgn * x / len(zc) for x in col])
        fused = list(map(sum, zip(*rows)))
        return fused if spearman(fused, ref) >= 0 or not orient_to_reference else [-x for x in fused]

    m = len(names)
    zc = _z_columns(signals, names)
    za = _z_columns(half_a, names)
    zb = _z_columns(half_b, names)
    ref = zc[0]

    sgn = [1.0 if spearman(zc[j], ref) >= 0.0 else -1.0 for j in range(m)]
    sgn[0] = 1.0
    rel = []
    for j in range(m):
        r = spearman(za[j], zb[j])
        rel.append(spearman_brown(r) if r > 0.0 else 0.0)

    rho_unit = dict(unit_reliability or {})
    if half_n and half_n > 0:
        for j, nm in enumerate(names):
            if nm in rho_unit:
                continue
            r = spearman(za[j], zb[j])
            if r > 0.0:
                rho_unit.setdefault(nm, unit_reliability_from_half(r, half_n))

    zstd = standardize_columns(zc)
    # 秩矩阵 item-invariant：在所有逐题求解之外预计算一次并复用（第 3.5 节效率优化）。
    rk_zstd = [ranks(c) for c in zstd]

    # ------------------------------------------------------------ M4-E：残差化分支
    if residualize:
        eres = incremental_columns(zstd, 0, ranks_=rk_zstd)
        if eres:
            wr = {j: sgn[j] * math.sqrt(max(0.0, min(0.999999, rel[j]))) for j in eres}
            wt = sum(abs(x) for x in wr.values()) or 1.0
            comp = [sum(wr[j] * eres[j][i] for j in eres) / wt for i in range(n)]
            comp = standardize_columns([comp])[0]
        else:
            comp = [0.0] * n
        if reference_weight is None:
            return comp
        w = min(1.0, max(0.0, float(reference_weight)))
        # 用原始 ecdf-logit 参考列 zc[0] 混合（与 run_m4 的 mix 同口径），
        # 既不调用 orient：残差列与参考列近正交，定向会退化为浮点噪声决定。
        return [(1.0 - w) * zc[0][i] + w * comp[i] for i in range(n)]

    need_per_item = bool(coverage) and bool(rho_unit)
    rows: List[List[float]] = []
    if need_per_item:
        # 每题一套 β ⇒ 先算出 n 份 β，再按**列**铺开，保持与 difficulty_fusion
        # 相同的 "rows[j] 长度为 n" 布局（行˜列写反会让输出长度变成 m 而不是 n，
        # 这是一个静默错误：不抛异常，只看长度才发现，故在此显式记一笔）。
        betas: List[List[float]] = []
        for i in range(n):
            qi = []
            for j, nm in enumerate(names):
                rho_j = rel[j]
                cv = coverage.get(nm)
                if cv is not None and nm in rho_unit:
                    rho_j = coverage_reliability(rho_unit[nm], cv[i])
                qi.append(sgn[j] * math.sqrt(max(0.0, min(0.999999, rho_j))))
            beta_i = _m4_beta_from_ranks(zstd, rk_zstd, qi)
            if beta_i is None:
                s = sum(abs(x) for x in qi)
                beta_i = [x / s for x in qi] if s > 0 else [1.0 / m] * m
            betas.append(beta_i)
        rows = [[betas[i][j] * zstd[j][i] for i in range(n)] for j in range(m)]
    else:
        q = [sgn[j] * math.sqrt(max(0.0, min(0.999999, rel[j]))) for j in range(m)]
        beta = m4_beta(zstd, q)
        if beta is None:
            s = sum(abs(x) for x in q)
            beta = [x / s for x in q] if s > 0 else [1.0 / m] * m
        rows = [[beta[j] * x for x in zstd[j]] for j in range(m)]
    # 逐题求和走内置 sum()：Neumaier 补偿求和，末位可复算（见模块 docstring 红线 2）
    fused = list(map(sum, zip(*rows)))
    if orient_to_reference and spearman(fused, ref) < 0.0:
        fused = [-x for x in fused]
    return fused
