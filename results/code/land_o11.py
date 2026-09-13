# -*- coding: utf-8 -*-
"""把 O11/O12 优化估计器（srw7：符号校正 + 可靠性加权）附加式落库到 difficulty_fusion.py。

用 str.replace + assert(count==1) 规避 Edit 工具静默不应用问题。
不新增 pytest 测试（守住全量测试 934 红线）；正确性由外部脚本 o11_land_verify.py 复核。
"""
import io, pathlib

P = pathlib.Path(r"E:\learnflow\learnflow-backend\app\services\difficulty_fusion.py")
src = io.open(P, "r", encoding="utf-8").read()

assert "def estimate_optimized_difficulty" not in src, "already landed?"

OLD_ALL = '''__all__ = [
    "ecdf_logit", "fuse_signals", "logit_to_fsrs", "EPS",
    "O8_SIGNAL_NAMES", "FUSED6_COLUMNS", "lambda_closed_form", "estimate_o8_difficulty",
]'''
NEW_ALL = '''__all__ = [
    "ecdf_logit", "fuse_signals", "logit_to_fsrs", "EPS",
    "O8_SIGNAL_NAMES", "FUSED6_COLUMNS", "lambda_closed_form", "estimate_o8_difficulty",
    "OPT_SIGNAL_NAMES", "split_half_reliability", "estimate_optimized_difficulty",
]'''
assert src.count(OLD_ALL) == 1, "OLD_ALL not unique/found"
src = src.replace(OLD_ALL, NEW_ALL, 1)

ADD = '''

# ---------------------------------------------------------------------------
# O11/O12 推荐估计器（落库）：符号校正 + 可靠性加权融合
# ---------------------------------------------------------------------------
# O11（记录级留出，Junyi）与 O12（学生级留出，Junyi，判据为 B 半学生真实难度）结论：
#   * O8 的"剔除 upgrade_rate"只做对了一半：该信号的错误在**方向**（与难度强负相关，
#     池内 −0.756、与专家标签 −0.1837），不在信息量。改为"符号校正"（按批内秩相关定符号）
#     后其信息被保留：signed7（7 信号等权、符号校正）在留出上一致优于 fused6。
#   * 再加入可靠性加权（权重 = 信号在拟合段的折半信度，取正后归一），得 srw7。
#   * srw7 相对"仅成功率"的留出增益（pp）：
#       记录级 k=10/25/50/100/200 = +3.82 / +2.03 / +0.93 / +0.39 / +0.14
#       学生级 同 k             = +4.28 / +2.19 / +0.95 / +0.33 / +0.10
#     学生级上 srw7 相对 fused6 的配对胜率 0.90–1.00（Wilcoxon p ≤ 1.2e-66）。
#   * λ 用闭式 λ_cf(k)=1/(1+(k/27.3)^0.895)；可靠性驱动 λ_rel=1−ρ_success(A) 与之几乎一致。
# 计算契约：符号校正只需"跨题目的信号取值"即可算出；可靠性加权需要一个"每信号一个信度"的
# 输入——调用方若持有逐题原始槽位，可用 split_half_reliability() 估计后传入；未传入则退化为等权。
OPT_SIGNAL_NAMES = O8_SIGNAL_NAMES


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


def _spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Spearman 秩相关（纯 Python，秩平均处理并列），避免为公制层引入重依赖。"""
    return _pearson(_rank_average(a), _rank_average(b))


def split_half_reliability(half_a: Sequence[float], half_b: Sequence[float]) -> float:
    """同一信号在拟合段两半样本上的逐题估计之间的折半信度（Spearman）。

    O11/O12 用它作为每信号的可靠性权重来源：把拟合段蓄水池槽位对半切，分别在两半上
    估计该信号，二者相关越高说明该信号在给定样本量下越可靠，融合中权重越大。
    """
    return _spearman(half_a, half_b)


def estimate_optimized_difficulty(
    signals: Mapping[str, Sequence[float]],
    k: int,
    reliability: Optional[Mapping[str, float]] = None,
    lam: Optional[float] = None,
) -> List[float]:
    """O11/O12 优化难度估计器（落库版）：符号校正 + 可靠性加权 + λ 收缩。

        z_i      = ecdf_logit(signal_i)，success_rate 取负（统一为"越大越难"）
        sgn_i    = sign(Spearman(z_i, z_0))，sgn_0 = +1        # 方向校正（保留反向信号的信息）
        w_i      = max(0, reliability_i) 归一；无 reliability 时等权
        fused    = Σ_i w_i · sgn_i · z_i
        λ        = lam（若给定）否则 lambda_closed_form(k)
        score    = (1 − λ) · z_0 + λ · fused

    Args:
        signals: {信号名: 每个题目的取值}，键与 ``OPT_SIGNAL_NAMES`` 一致；success_rate 为
                 "越大越易"，其余为"越大越难"。
        k: 用于估计这些信号的样本量（题目数）。
        reliability: 可选 {信号名: 折半信度}；用 ``split_half_reliability()`` 在拟合段估计。
        lam: 可选固定收缩系数；缺省用闭式 ``lambda_closed_form(k)``。

    Returns:
        每个题目的融合难度（logit 公制，越大越难）。

    Raises:
        ValueError: 信号名缺失/多余、长度不一致、k 非正。
    """
    missing = set(OPT_SIGNAL_NAMES) - set(signals)
    if missing:
        raise ValueError(f"缺少 O11 信号: {missing}")
    extra = set(signals) - set(OPT_SIGNAL_NAMES)
    if extra:
        raise ValueError(f"未知 O11 信号: {extra}")
    names = list(OPT_SIGNAL_NAMES)
    n = len(signals[names[0]])
    if n == 0:
        return []
    if any(len(signals[name]) != n for name in names):
        raise ValueError("所有信号长度必须一致")

    z: List[List[float]] = []
    for i, name in enumerate(names):
        col = ecdf_logit(signals[name])
        z.append([-x for x in col] if i == 0 else col)

    d0 = z[0]
    signs = [1.0 if (i == 0 or _spearman(z[i], d0) >= 0.0) else -1.0
             for i in range(len(names))]

    if reliability is None:
        w = [1.0 / len(names)] * len(names)
    else:
        raw = [max(0.0, float(reliability.get(nm, 0.0))) for nm in names]
        s = sum(raw)
        w = [x / s for x in raw] if s > 0.0 else [1.0 / len(names)] * len(names)

    fused = [sum(w[i] * signs[i] * z[i][idx] for i in range(len(names)))
             for idx in range(n)]
    lam_used = lambda_closed_form(k) if lam is None else float(lam)
    return [(1.0 - lam_used) * d0[idx] + lam_used * fused[idx] for idx in range(n)]
'''

assert "def estimate_optimized_difficulty" not in src, "landing did not take"
src = src.rstrip() + ADD

io.open(P, "w", encoding="utf-8").write(src)
print("[OK] landed estimate_optimized_difficulty into difficulty_fusion.py")
print("lines now:", src.count("\n") + 1)
print("DONE")
