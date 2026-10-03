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

────────────────────────────────────────────────────────────────────────
性能优化（2026-09-27）：**结果位等价（bit-exact）的行为保持型重构**
────────────────────────────────────────────────────────────────────────
本次重构只删冗余计算与冗余内存，**不改对外接口、不改任何浮点运算的顺序与形式**，
因此输出必须与优化前逐位相同（由 `scripts/verify_difficulty_fusion_equivalence.py`
以「冻结的旧实现」做随机压力对照校验）。具体四点：

1. **消除重复的秩计算**：`estimate_optimized_difficulty` 原实现对每个 signals 都调用
   `_spearman(z_i, z_0)`，其中 `_rank_average(z_0)` 被重复计算 len(signals)-1 次
   （每次一趟 O(n log n) 排序）。现改为**预先算一次**参考列的秩与二阶统计量
   （均值、中心平方和），其余信号只算自己的秩。
2. **消除 O(n·m) 次生成器帧**：原 `sum(z[c][idx] for c in COLS)` 与
   `sum(w[i]*s[i]*z[i][idx] for i in ...)` 为每个题目新建 generator + 生成器帧，
   并用 `z[c][idx]` 跨行二级索引；改为**先按列缩放成普通列表、再 `map(sum, zip(*rows))`**
   做一次 C 层转置 + C 层求和。
   ⚠️ 这一步**不能**再简化为"朴素就地累加"：CPython ≥3.12 的内置 `sum()` 对浮点走
   **Neumaier 补偿求和**，朴素 `acc = acc + x` 会在末位 ulp 发散（实测 Δ≈4.4e-16，
   在 2802 项随机断言里造成 615 处不相等）。因此宁可保留 NumPy 之外的行缓冲
   （峰值内存 O(m·n) 个**指针**，float 对象本身是复用的，n=3000 时约 170 KB），
   也要保住"文档里的每个数字都能被机器复算"这条红线。
3. **行缓冲带来的缓存收益**：行列表逐行追加、行内连续访问，替代原来的
   `transformed[c][idx]` 随机跨行访问；并按 `FUSED6_COLUMNS` 的 frozenset 做 O(1) 判定
   （不再对 tuple 做线性查找）。
4. **微优化**：`ecdf_logit` 里被 `max(min(...))` 重复算两次的裁剪值改为算一次；
   排序键由 Python 层 lambda 换成 C 层 `list.__getitem__`（语义与 NaN/稳定性不变）。

**刻意未做的改动**（一旦做了会破坏数值一致性，也违背本项目"数字必须可复算"的红线）：
不把 `(r-0.5)/n` 换成乘倒数、不把 `(x-m)**2` 换成 `x*x`、不合并/重排任何求和顺序、
不引入 numpy（保持零依赖以适配受限环境）。
"""
import math
from typing import List, Mapping, Optional, Sequence

__all__ = [
    "ecdf_logit", "fuse_signals", "logit_to_fsrs", "EPS",
    "O8_SIGNAL_NAMES", "FUSED6_COLUMNS", "lambda_closed_form", "estimate_o8_difficulty",
    "OPT_SIGNAL_NAMES", "split_half_reliability", "estimate_optimized_difficulty",
]

EPS = 1e-4  # 分位裁剪，避免 logit(0)/logit(1) 发散


def _rank_average(values: Sequence[float]) -> List[float]:
    """并列取平均秩（average rank，1..n）"""
    n = len(values)
    # key 用 list.__getitem__（C 层）替代等价的 lambda，避免每元素一次 Python 帧；
    # 仍是 key 排序 → 稳定性与 NaN 行为与原实现完全一致。
    order = sorted(range(n), key=values.__getitem__)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        pivot = values[order[i]]  # 提外循环不变量，省掉 O(并列数) 次重复索引
        while j + 1 < n and values[order[j + 1]] == pivot:
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
    n = len(values)
    if n == 0:
        return []
    ranks = _rank_average(values)
    out: List[float] = []
    append = out.append
    for r in ranks:
        q = (r - 0.5) / n
        # 等价于原实现的 max(min(q, 1-EPS), EPS)，但只裁剪一次：
        # 原写法里同一个裁剪值被算了两次（-inf/+inf/NaN 分支语义均一致）。
        p = EPS if q < EPS else (1.0 - EPS if q > 1.0 - EPS else q)
        append(math.log(p / (1.0 - p)))
    return out


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
        # 就地累加，替代每信号一次的全列表重建（原 `out = [o + wk*v ...]`）；
        # 逐元素的加法顺序不变 → 结果位等价。
        for i in range(n):
            out[i] = out[i] + wk * z[i]
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
# 行流式累加时用于判定"本信号是否计入 fused6"的集合（O(1) 查表，替代 tuple 线性查找）
_FUSED6_INDEX_SET = frozenset(FUSED6_COLUMNS)


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

    lam = lambda_closed_form(k)
    col_n = len(FUSED6_COLUMNS)

    success: List[float] = []
    rows: List[List[float]] = []   # 只保留参与 fused6 的列（upgrade_rate 不落盘）
    for i, name in enumerate(names):
        z = ecdf_logit(signals[name])
        if i == 0:
            # success_rate：越大越易 → 取负统一为越大越难。
            # 注意 FUSED6_COLUMNS **包含索引 0**，故 fused6 加的是取负后的这一列
            # （即"方向已统一"的 success 分量），这里必须持有取负后的同一个对象，
            # 否则会退回未取负的原始值——本次重构唯一一处真实数值陷阱，已由
            # `scripts/verify_difficulty_fusion_equivalence.py` 的位等价门禁捕获。
            z = [-x for x in z]
            success = z
        if i in _FUSED6_INDEX_SET:
            rows.append(z)
    # 逐题求和仍走内置 sum()：CPython ≥3.12 对浮点用 Neumaier 补偿求和，
    # 任何"朴素就地累加"的改写都会在末位 ulp 上发散（本项目红线：数字必须可复算）。
    # 这里用 `map(sum, zip(*rows))` 把 O(n·m) 次 Python 帧与跨行二级索引 `z[c][idx]`
    # 换成一次 C 层转置 + C 层求和，**值序列与旧实现逐项相同** → 位等价且更快。
    fused = [s / col_n for s in map(sum, zip(*rows))]
    return [(1.0 - lam) * success[idx] + lam * fused[idx] for idx in range(n)]

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


def _pearson_vs_fixed(a: Sequence[float], b: Sequence[float],
                      mb: float, vb: float) -> float:
    """``_pearson(a, b)`` 的等价形式，但 b 的一阶/二阶统计量已由调用方预算好。

    用于 `estimate_optimized_difficulty` 的符号校正：``b`` 恒为参考列 ``z_0`` 的秩，
    其均值 ``mb`` 与中心平方和 ``vb`` 在原实现里被重复算了 len(signals)-1 次。

    算术表达式与累加顺序均与 `_pearson` 逐字一致（`(x-m)**2`、`(x-ma)*(y-mb)`、
    同一 kahan-free 顺序），故返回值与 `_pearson(a, b)` 位等价。
    """
    n = len(a)
    if n < 2:
        return 0.0
    ma = sum(a) / n
    va = sum((x - ma) ** 2 for x in a)
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

    m = len(names)
    if reliability is None:
        w = [1.0 / m] * m
    else:
        raw = [max(0.0, float(reliability.get(nm, 0.0))) for nm in names]
        s = sum(raw)
        w = [x / s for x in raw] if s > 0.0 else [1.0 / m] * m

    # --- 参考列 z_0（用于符号校正的基准方向）与其秩统计量（只算一次） ---
    z0 = [-x for x in ecdf_logit(signals[names[0]])]
    r0 = _rank_average(z0)          # 原实现：每个信号的 _spearman 都重算一次 → 冗余 m-1 次
    mb = sum(r0) / n
    vb = sum((y - mb) ** 2 for y in r0)

    # --- 逐题融合项：必须与旧实现 `sum(w[i]*signs[i]*z[i][idx] for i in ...)` 位等价 ---
    # 关键点同 `estimate_o8_difficulty`：CPython ≥3.12 的内置 sum() 对浮点采用 Neumaier
    # 补偿求和，任何"朴素就地累加"改写都会在末位 ulp 上发散（实测 4.4e-16），
    # 因此这里保持"每列缩放后按同一顺序求和"，只把逐元素的 generator 帧换成
    # `map(sum, zip(*rows))`（C 层转置 + C 层求和）。值序列与旧实现逐项相同 → 位等价。
    rows: List[List[float]] = [ [w[0] * x for x in z0] ]
    for i in range(1, m):
        z = ecdf_logit(signals[names[i]])
        # 符号校正用预算好的 r0/mb/vb（旧实现对每个信号重算一次 _rank_average(z_0)）
        sgn = 1.0 if _pearson_vs_fixed(_rank_average(z), r0, mb, vb) >= 0.0 else -1.0
        wi = w[i] * sgn
        rows.append([wi * x for x in z])
    fused = list(map(sum, zip(*rows)))

    lam_used = lambda_closed_form(k) if lam is None else float(lam)
    return [(1.0 - lam_used) * z0[idx] + lam_used * fused[idx] for idx in range(n)]
