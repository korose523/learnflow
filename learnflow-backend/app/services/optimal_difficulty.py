"""最优难度计算引擎 —— LearnFlow 核心算法

理论基础（四层模型）：
  1. **85% 规则** (Wilson, Shenhav et al., 2019, Nature Communications)
     — 基于梯度下降的学习算法在错误率≈15.87%时学习速度最快
  2. **FSRS 难度模型** (Jarrett Ye / open-spaced-repetition)
     — 从记忆复习中估计题目/知识点内在难度 D ∈ [1,10]
  3. **Elo 评分系统** (Arpad Elo, 1960)
     — 将学生能力 θ 和题目难度 d 映射到统一量纲
  4. **心流通道** (Csikszentmihalyi, 1990)
     — 最优成功率区间 [0.75, 0.85] 对应心流状态

输出：给定学生能力 θ，推荐难度 d* 使 P(correct | θ, d*) ≈ 0.85
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


# ═════════════════════════════════════════════════════════
# 核心数据结构
# ═════════════════════════════════════════════════════════

class DifficultyZone(str, Enum):
    """学习难度区域"""
    BOREDOM = "boredom"       # 太简单 (success > 90%)
    FLOW = "flow"             # 心流区 (75-90%)
    STRETCH = "stretch"       # 拉伸区 (50-75%)
    ANXIETY = "anxiety"       # 焦虑区 (success < 50%)


@dataclass
class StudentAbility:
    """学生能力估计（Elo 风格）"""
    theta: float = 1500.0        # 初始 Elo 分
    sigma: float = 350.0         # 不确定性（Glicko 风格评级偏差）
    total_attempts: int = 0
    last_updated: Optional[float] = None

    @property
    def confidence(self) -> float:
        """对能力估计的置信度 (0-1)，随答题数增加"""
        return min(1.0, self.total_attempts / 50)


@dataclass
class TaskDifficulty:
    """题目/知识点难度估计"""
    d: float = 5.0              # FSRS 内在难度 [1, 10]
    discrimination: float = 1.0  # IRT 区分度参数 a，默认 1.0
    guessing: float = 0.0        # IRT 猜测参数 c，默认 0（主观题）

    @property
    def elo_difficulty(self) -> float:
        """将 FSRS 难度 [1,10] 映射到 Elo 量纲 [800, 2200]"""
        return 800.0 + (self.d - 1.0) / 9.0 * 1400.0


@dataclass
class DifficultyResult:
    """难度计算结果"""
    optimal_d: float                # 推荐的内在难度值 [1, 10]
    expected_success: float         # 预期成功率 (0-1)
    zone: DifficultyZone            # 当前区域
    student_theta: float            # 当前能力估计
    student_sigma: float            # 能力不确定性
    learning_rate_factor: float     # 当前学习速率因子 K_f
    explanation: str                # 人类可读解释


# ═════════════════════════════════════════════════════════
# 第一层：85% 规则模型
# ═════════════════════════════════════════════════════════

class EightyFivePercentRule:
    """Wilson et al. (2019) 85% 规则的数学实现

    核心公式（高斯噪声假设）：
      ER* = 0.5 * (1 - erf(1/√2)) ≈ 0.1587
      即最优成功率 = 1 - ER* ≈ 84.13%

    学习速率因子 K_f：
      K_f = -F⁻¹(ER_f) · p(F⁻¹(ER_f))
      在 ER* 处：K_f = p(-1) = 1/√(2π) · e^{-1/2} ≈ 0.2420
    """

    OPTIMAL_ERROR_RATE = 0.1587          # 15.87%
    OPTIMAL_SUCCESS_RATE = 0.8413        # 84.13%
    MAX_LEARNING_RATE = 0.2420           # p(-1) for Gaussian

    # 不同噪声分布的最优成功率
    DISTRIBUTION_TARGETS = {
        "gaussian": 0.8413,    # 高斯：84.13%
        "laplacian": 0.8161,   # 拉普拉斯：81.61%
        "cauchy": 0.7500,      # 柯西：75.00%
    }

    @classmethod
    def learning_rate_factor(cls, success_rate: float) -> float:
        """计算给定成功率下的学习速率 K_f

        公式：K_f = Δ · p(Δ)，其中 Δ = F⁻¹(1 - success_rate)

        在高斯噪声下：
          Δ = √2 · erf⁻¹(1 - 2 · ER)
          p(Δ) = e^{-Δ²/2} / √(2π)
          K_f = Δ · p(Δ)
        """
        error_rate = 1.0 - success_rate
        # 数值稳定：限制范围
        error_rate = max(0.001, min(0.999, error_rate))

        # Δ = √2 · erf⁻¹(1 - 2·ER)
        delta = math.sqrt(2) * cls._erfinv(1.0 - 2.0 * error_rate)

        # p(Δ) = e^{-Δ²/2} / √(2π)
        p_delta = math.exp(-delta * delta / 2.0) / math.sqrt(2.0 * math.pi)

        k_f = delta * p_delta
        return k_f

    @classmethod
    def optimal_difficulty_signal(cls, success_rate: float) -> float:
        """难度调整信号 [-1, 1]

        正值 = 太容易（需要升难度）
        负值 = 太难（需要降难度）
        0 = 最优
        """
        optimal = cls.OPTIMAL_SUCCESS_RATE
        if success_rate > optimal:
            # 太容易 → 正信号
            return (success_rate - optimal) / (1.0 - optimal)
        else:
            # 太难 → 负信号
            return (success_rate - optimal) / optimal

    @staticmethod
    def _erfinv(x: float) -> float:
        """误差函数反函数（近似实现）

        使用 Winitzki 近似（最大误差 ~0.00012）：
          erf⁻¹(x) ≈ sign(x) · √( √( (2/(πa) + ln(1-x²)/2 )² - ln(1-x²)/a ) - (2/(πa) + ln(1-x²)/2) )
          其中 a = 0.147
        """
        if abs(x) >= 1.0:
            return math.copysign(float('inf'), x)
        a = 0.147
        sign = 1.0 if x >= 0 else -1.0
        x_abs = abs(x)

        ln_1_x2 = math.log(1.0 - x_abs * x_abs)
        term1 = 2.0 / (math.pi * a) + ln_1_x2 / 2.0
        term2 = ln_1_x2 / a

        result = math.sqrt(math.sqrt(term1 * term1 - term2) - term1)
        return sign * result


# ═════════════════════════════════════════════════════════
# 第二层：FSRS 难度模型（适配学习场景）
# ═════════════════════════════════════════════════════════

class FSRSStyleDifficulty:
    """FSRS 风格的题目内在难度估计

    从答题记录中估计题目的内在难度 D ∈ [1, 10]

    初始难度：
      D_init = clamp(D₀ - w₅ * (r - 3), 1, 10)
      其中 r 是评分 (1-4: 1=很难, 2=难, 3=中等, 4=简单)

    难度更新（均值回归）：
      D_new = clamp(w₇ * D₀ + (1-w₇) * (D - w₆ * (r - 3)), 1, 10)

    参数说明（参考 FSRS v4 默认值）：
      D₀ = 5.0  初始难度（中等）
      w₅ = 1.0  初始难度受评分影响的程度
      w₆ = 0.2  难度更新速率
      w₇ = 0.2  均值回归强度（0=无回归，1=完全回归初始值）
    """

    D_MIN = 1.0
    D_MAX = 10.0

    def __init__(
        self, d0: float = 5.0, w5: float = 1.0,
        w6: float = 0.2, w7_reversion: float = 0.2,
    ):
        self.d0 = d0          # 初始难度基准
        self.w5 = w5          # 评分→初始难度灵敏度
        self.w6 = w6          # 难度更新速率
        self.w7 = w7_reversion  # 均值回归强度

    def initial_difficulty(self, first_score: float, score_max: float = 4.0) -> float:
        """根据首次评分计算初始难度

        first_score: 归一化评分 (1-4)
        返回：内在难度 D ∈ [1, 10]

        高分(4) → 题目容易 → D 降低
        低分(1) → 题目难 → D 升高
        """
        # 映射到 FSRS 量纲
        r = first_score  # 1-4
        d = self.d0 - self.w5 * (r - 3.0)
        return max(self.D_MIN, min(self.D_MAX, d))

    def update_difficulty(
        self, current_d: float, score: float,
        score_max: float = 4.0,
    ) -> float:
        """根据新答题结果更新难度估计

        均值回归公式：
          d_raw = current_d - w₆ * (r - 3)
          d_new = clamp(w₇ * D₀ + (1-w₇) * d_raw, 1, 10)
        """
        d_raw = current_d - self.w6 * (score - 3.0)
        d_new = self.w7 * self.d0 + (1.0 - self.w7) * d_raw
        return max(self.D_MIN, min(self.D_MAX, d_new))


# ═════════════════════════════════════════════════════════
# 第三层：Elo 评分系统
# ═════════════════════════════════════════════════════════

class EloRating:
    """Elo 评分系统 —— 将学生能力与题目难度对齐

    核心公式：
      E = 1 / (1 + 10^((d_elo - θ) / 400))
      θ_new = θ + K * (actual - E)

    参数：
      K 值：初始阶段高（快速收敛），稳定后降低
      K = max(K_min, K_base / sqrt(1 + n_attempts / K_decay))
    """

    DEFAULT_THETA = 1500.0
    DEFAULT_SIGMA = 350.0  # Glicko RD

    def __init__(
        self, k_base: float = 32.0, k_min: float = 8.0,
        k_decay: float = 5.0,
    ):
        self.k_base = k_base
        self.k_min = k_min
        self.k_decay = k_decay

    def expected_score(self, theta: float, difficulty_elo: float) -> float:
        """计算期望得分 E"""
        exponent = (difficulty_elo - theta) / 400.0
        return 1.0 / (1.0 + 10.0 ** exponent)

    def k_factor(self, n_attempts: int) -> float:
        """动态 K 值：早期大，后期小"""
        return max(self.k_min, self.k_base / math.sqrt(1.0 + n_attempts / self.k_decay))

    def update(
        self, theta: float, n_attempts: int,
        actual_score: float, difficulty_elo: float,
    ) -> Tuple[float, float]:
        """更新学生能力估计

        Returns: (new_theta, new_sigma)
        """
        e = self.expected_score(theta, difficulty_elo)
        k = self.k_factor(n_attempts)

        new_theta = theta + k * (actual_score - e)

        # Glicko 风格：RD 随答题数减小
        # σ_new = sqrt(max(σ²_old - σ²_old * (1 - e) * e * (k² / σ²_old), 25²))
        rd_factor = (1.0 - e) * e * k * k
        new_sigma = math.sqrt(max(
            25.0,  # 最小 RD
            self.DEFAULT_SIGMA * self.DEFAULT_SIGMA - rd_factor
        ))

        return new_theta, new_sigma


# ═════════════════════════════════════════════════════════
# 第四层：心流通道模型
# ═════════════════════════════════════════════════════════

class FlowChannel:
    """心流通道 —— 确定学生的 ZPD 和最优难度区间

    基于 Csikszentmihalyi 心流理论和 85% 规则：

    心流区：P(success) ∈ [0.75, 0.90]
    最优线：P(success) = 0.85（85% 规则）

    对应到 Elo 量纲：
      学生能力 = θ
      推荐难度 Elo = θ + Δ
      其中 Δ = 400 · log₁₀((1-P)/P)
      - P=0.85 → Δ ≈ -301（题目难度略低于能力）
      - P=0.75 → Δ ≈ -191
      - P=0.90 → Δ ≈ -381
    """

    FLOW_LOW = 0.75   # 心流下界（再容易就无聊）
    FLOW_HIGH = 0.90  # 心流上界（再难就焦虑）
    OPTIMAL = 0.85    # 85% 规则最优线

    @classmethod
    def success_to_elo_delta(cls, target_success: float) -> float:
        """目标成功率 → Elo 难度-能力差值

        P = 1/(1+10^((d-θ)/400))
        → d - θ = 400 · log₁₀((1-P)/P)
        """
        ratio = (1.0 - target_success) / max(target_success, 0.001)
        return 400.0 * math.log10(max(ratio, 0.001))

    @classmethod
    def optimal_difficulty_elo(cls, theta: float) -> float:
        """给定学生能力 θ，返回最优 Elo 难度"""
        delta = cls.success_to_elo_delta(cls.OPTIMAL)
        return theta + delta

    @classmethod
    def classify_zone(cls, expected_success: float) -> DifficultyZone:
        """根据预期成功率判断学习区域"""
        if expected_success > cls.FLOW_HIGH:
            return DifficultyZone.BOREDOM
        elif expected_success >= cls.FLOW_LOW:
            return DifficultyZone.FLOW
        elif expected_success >= 0.50:
            return DifficultyZone.STRETCH
        else:
            return DifficultyZone.ANXIETY

    @classmethod
    def get_zone_boundaries_elo(cls, theta: float) -> dict:
        """返回各区域的 Elo 难度边界"""
        return {
            "boredom_ceiling": theta + cls.success_to_elo_delta(cls.FLOW_HIGH),
            "flow_upper": theta + cls.success_to_elo_delta(cls.FLOW_HIGH),
            "flow_lower": theta + cls.success_to_elo_delta(cls.FLOW_LOW),
            "stretch_lower": theta + cls.success_to_elo_delta(0.50),
            "optimal": theta + cls.success_to_elo_delta(cls.OPTIMAL),
        }


# ═════════════════════════════════════════════════════════
# 统一引擎：OptimalDifficultyEngine
# ═════════════════════════════════════════════════════════

class OptimalDifficultyEngine:
    """最优难度计算引擎 —— 融合四层模型

    使用示例：
        engine = OptimalDifficultyEngine()

        # 获取最优难度
        result = engine.compute_optimal_difficulty(
            student_theta=1550.0,
            recent_success_rate=0.82,
        )
        print(f"推荐难度: {result.optimal_d:.1f}")
        print(f"预期成功率: {result.expected_success:.2%}")
        print(f"当前区域: {result.zone.value}")

        # 更新学生能力
        new_theta, new_sigma = engine.elo.update(
            theta=1500, n_attempts=10, actual_score=1.0, difficulty_elo=1600
        )

        # 更新题目难度
        new_d = engine.fsrs.update_difficulty(current_d=5.0, score=3.0)
    """

    def __init__(
        self,
        target_success: float = 0.85,
        elo_k_base: float = 32.0,
        elo_k_min: float = 8.0,
        fsrs_d0: float = 5.0,
        fsrs_w5: float = 1.0,
        fsrs_w6: float = 0.2,
        fsrs_w7: float = 0.2,
    ):
        self.target_success = target_success
        self.rule85 = EightyFivePercentRule()
        self.elo = EloRating(k_base=elo_k_base, k_min=elo_k_min)
        self.fsrs = FSRSStyleDifficulty(
            d0=fsrs_d0, w5=fsrs_w5, w6=fsrs_w6, w7_reversion=fsrs_w7,
        )
        self.flow = FlowChannel()

    # ─── 主计算：最优难度 ───────────────────────────────

    def compute_optimal_difficulty(
        self,
        student_theta: float = 1500.0,
        student_sigma: float = 350.0,
        recent_success_rate: Optional[float] = None,
        n_total_attempts: int = 0,
    ) -> DifficultyResult:
        """计算给定学生的最优题目难度

        Args:
            student_theta: 学生 Elo 能力分
            student_sigma: 能力不确定性 (Glicko RD)
            recent_success_rate: 最近成功率（可选，用于精细调整）
            n_total_attempts: 总答题数

        Returns:
            DifficultyResult: 包含推荐难度和解释
        """
        # Step 1: 基本目标始终是85%
        target = self.target_success

        # Step 2: 从心流通道计算目标 Elo 难度
        target_elo_delta = self.flow.success_to_elo_delta(target)
        target_elo = student_theta + target_elo_delta

        # Step 3: 根据最近成功率直接调整 Elo 难度
        # 如果最近太容易（>85%）：增加 Elo 难度（更难）
        # 如果最近太难（<85%）：降低 Elo 难度（更简单）
        if recent_success_rate is not None and n_total_attempts >= 5:
            actual_delta = self.flow.success_to_elo_delta(recent_success_rate)
            actual_elo = student_theta + actual_delta
            # PID-like correction: 朝向85%调整
            # correction = (target_elo - actual_elo) * gain
            # 当 recent > 85%: actual_elo < target_elo → correction > 0 → 升难度
            # 当 recent < 85%: actual_elo > target_elo → correction < 0 → 降难度
            correction = (target_elo - actual_elo) * 0.3
            target_elo += correction

        # Step 4: 将 Elo 难度映射到 FSRS 难度
        optimal_d = self._elo_to_fsrs_difficulty(target_elo)

        # Step 4: 不确定性越大，向中等难度回归越多
        # 高不确定性（新用户）→ 用更保守的中等难度
        # 低不确定性（老用户）→ 信任计算值
        uncertainty = max(0.0, min(1.0, (student_sigma - 25.0) / 325.0))
        mid_d = 5.0
        regression_weight = uncertainty * 0.2  # 最多20%回归
        optimal_d = optimal_d * (1.0 - regression_weight) + mid_d * regression_weight

        optimal_d = max(1.0, min(10.0, optimal_d))

        # Step 5: 计算期望成功率
        optimal_elo = self._fsrs_to_elo_difficulty(optimal_d)
        expected_success = self.elo.expected_score(student_theta, optimal_elo)

        # Step 6: 分类区域
        zone = self.flow.classify_zone(expected_success)

        # Step 7: 学习速率因子
        lr_factor = self.rule85.learning_rate_factor(expected_success)

        # Step 8: 生成解释
        explanation = self._generate_explanation(zone, expected_success, lr_factor)

        return DifficultyResult(
            optimal_d=round(optimal_d, 1),
            expected_success=round(expected_success, 4),
            zone=zone,
            student_theta=student_theta,
            student_sigma=student_sigma,
            learning_rate_factor=round(lr_factor, 4),
            explanation=explanation,
        )

    # ─── 学生能力更新 ──────────────────────────────────

    def update_student_ability(
        self, student: StudentAbility,
        success: bool, difficulty_elo: float,
    ) -> StudentAbility:
        """根据答题结果更新学生能力"""
        actual = 1.0 if success else 0.0
        student.total_attempts += 1

        new_theta, new_sigma = self.elo.update(
            theta=student.theta,
            n_attempts=student.total_attempts,
            actual_score=actual,
            difficulty_elo=difficulty_elo,
        )
        student.theta = new_theta
        student.sigma = new_sigma
        return student

    # ─── 题目难度更新 ──────────────────────────────────

    # 耗时→"偏慢"程度的软性判据（O1 修复：不再使用硬阈值）
    TIME_REF_SECONDS: float = 60.0   # log-time 中心（秒）
    TIME_SLOPE: float = 0.8          # log-time 陡峭度
    HINT_PENALTY: float = 0.5        # 使用提示的证据惩罚（O5：提示率是有效难度信号）

    def update_task_difficulty(
        self, task: TaskDifficulty,
        was_correct: bool, time_spent_seconds: Optional[float] = None,
        hint_used: bool = False,
    ) -> TaskDifficulty:
        """根据答题结果更新题目难度估计。

        改动依据（results/Real_data_实验报告.md O1）：
        原实现对耗时使用 `>180s` 的**硬阈值**分档——这类把连续信号按任意切点离散化
        再与其他信号（正确性）手工合并的做法，在量表/单位变化（单调重参数化）下会
        产生有效权重漂移（实测线性融合 L1=0.5357、排序反转 ~67%）。
        现改为 log-time 上的连续单调项：耗时越长 → 证据越偏向"难"，且无跳变点。

        证据分数（FSRS r ∈ [1,4]，3=中性）：
          * 答对：r = 3 + (1 - s)  → 快速答对≈4（简单），慢速答对→3（中等）
          * 答错：r = 1 + (1 - s)  → 慢速答错≈1（很难），快速答错→2（疑似粗心）
          * 使用提示：r -= 0.5（更吃力 ⇒ 更难的证据）
        其中 s = σ(ln(t / 60s) / 0.8) ∈ (0,1) 为"偏慢"程度。
        """
        score = self._evidence_score(was_correct, time_spent_seconds, hint_used)
        task.d = self.fsrs.update_difficulty(task.d, score)
        return task

    @classmethod
    def _slowness(cls, time_spent_seconds: Optional[float]) -> float:
        """耗时 → 偏慢程度 s ∈ (0,1)；缺失耗时时取中性 0.5"""
        if time_spent_seconds is None:
            return 0.5
        t = max(float(time_spent_seconds), 1.0)
        x = math.log(t / cls.TIME_REF_SECONDS) / cls.TIME_SLOPE
        return 1.0 / (1.0 + math.exp(-x))

    @classmethod
    def _evidence_score(
        cls, was_correct: bool,
        time_spent_seconds: Optional[float] = None,
        hint_used: bool = False,
    ) -> float:
        """把 (正确性, 耗时, 提示) 合并为 FSRS 证据分 r ∈ [1,4]"""
        s = cls._slowness(time_spent_seconds)
        score = (3.0 + (1.0 - s)) if was_correct else (1.0 + (1.0 - s))
        if hint_used:
            score -= cls.HINT_PENALTY
        return max(1.0, min(4.0, score))

    # ─── 批量题目的最优选择 ────────────────────────────

    def rank_tasks(
        self, student_theta: float,
        tasks: List[Tuple[str, float]],  # [(task_id, fsrs_difficulty), ...]
    ) -> List[Tuple[str, float, float]]:
        """从候选题目中排序最优选择

        Returns: [(task_id, score, expected_success), ...] 按匹配度降序
        """
        optimal_elo = self.flow.optimal_difficulty_elo(student_theta)
        ranked = []

        for task_id, fsrs_d in tasks:
            task_elo = self._fsrs_to_elo_difficulty(fsrs_d)
            expected = self.elo.expected_score(student_theta, task_elo)
            # 匹配度得分：越接近目标成功率越好
            match_score = 1.0 - abs(expected - self.target_success)
            ranked.append((task_id, round(match_score, 4), round(expected, 4)))

        return sorted(ranked, key=lambda x: x[1], reverse=True)

    # ─── 辅助方法 ──────────────────────────────────────

    def _elo_to_fsrs_difficulty(self, elo: float) -> float:
        """Elo 难度 [800, 2200] → FSRS 难度 [1, 10]"""
        return 1.0 + (elo - 800.0) / 1400.0 * 9.0

    def _fsrs_to_elo_difficulty(self, fsrs_d: float) -> float:
        """FSRS 难度 [1, 10] → Elo 难度 [800, 2200]"""
        return 800.0 + (fsrs_d - 1.0) / 9.0 * 1400.0

    def _generate_explanation(
        self, zone: DifficultyZone, expected: float, lr_factor: float,
    ) -> str:
        """生成人类可读解释"""
        lr_pct = lr_factor / EightyFivePercentRule.MAX_LEARNING_RATE * 100

        zone_messages = {
            DifficultyZone.BOREDOM:
                f"太容易（预期成功率{expected:.0%}），学习效率仅{lr_pct:.0f}%。建议升级难度。",
            DifficultyZone.FLOW:
                f"心流状态（预期成功率{expected:.0%}），学习效率{lr_pct:.0f}%。当前难度最优。",
            DifficultyZone.STRETCH:
                f"拉伸区（预期成功率{expected:.0%}），学习效率{lr_pct:.0f}%。建议稍降难度。",
            DifficultyZone.ANXIETY:
                f"过难（预期成功率{expected:.0%}），学习效率仅{lr_pct:.0f}%。建议大幅降难度。",
        }
        return zone_messages.get(zone, "")


# 全局单例
optimal_difficulty_engine = OptimalDifficultyEngine()
