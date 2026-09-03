"""DDA（动态难度调节）算法

基于最近 N 题窗口的表现，自动调整下题的难度，维持心流通道。
目标成功率区间: 0.75–0.85（基于 Csikszentmihalyi 心流理论）

核心原理：
- 成功率 > 85%：太简单 → 升难度
- 成功率 < 50%：太难 → 降难度
- 50%-85%：心流通道 → 维持或微调
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class DDADirection(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"
    MICRO_ADJUST = "micro_adjust"


class PetReaction(str, Enum):
    CONFIDENT = "CONFIDENT"     # 太容易，自信
    ENCOURAGING = "ENCOURAGING"  # 太难，鼓励
    FOCUSED = "FOCUSED"          # 心流，专注
    CURIOUS = "CURIOUS"          # 微调，好奇


@dataclass
class DDAResult:
    """DDA 计算结果"""
    difficulty: int
    direction: DDADirection
    pet_reaction: PetReaction
    feedback_text: str
    success_rate: float
    confidence: float


class DDAEngine:
    """动态难度调节引擎

    根据文档设计，基于最近10题的表现滚动评估并微调难度。
    """

    def __init__(
        self,
        window_size: int = 10,
        target_min: float = 0.75,
        target_max: float = 0.85,
    ):
        self.window_size = window_size
        self.target_min = target_min
        self.target_max = target_max

    def calculate(
        self,
        recent_results: List[bool],  # True=正确, False=错误
        current_difficulty: int,
        difficulty_range: tuple = (1, 10),
    ) -> DDAResult:
        """根据最近表现计算下题难度

        Args:
            recent_results: 最近N题的答题结果（按时间倒序，最新在最后）
            current_difficulty: 当前难度等级 (1-10)
            difficulty_range: 难度范围 (min, max)

        Returns:
            DDAResult: 包含新难度、方向、宠物反应等
        """
        if not recent_results:
            return DDAResult(
                difficulty=current_difficulty,
                direction=DDADirection.MAINTAIN,
                pet_reaction=PetReaction.FOCUSED,
                feedback_text="让我们开始吧！",
                success_rate=0.0,
                confidence=0.5,
            )

        # 取最近 window_size 条记录
        window = recent_results[-self.window_size:]
        success_rate = sum(window) / len(window)

        min_diff, max_diff = difficulty_range
        new_difficulty = current_difficulty

        if success_rate > self.target_max:
            # 太容易了 → 升难度
            new_difficulty = min(current_difficulty + 1, max_diff)
            direction = DDADirection.INCREASE
            pet_reaction = PetReaction.CONFIDENT
            feedback_text = "你已经掌握得不错，我们升级难度！"

        elif success_rate < self.target_min:
            # 太难了 → 降难度
            new_difficulty = max(current_difficulty - 1, min_diff)
            direction = DDADirection.DECREASE
            pet_reaction = PetReaction.ENCOURAGING
            feedback_text = "让我们回到舒适的难度，巩固基础。"

        elif self.target_min <= success_rate <= self.target_max:
            # 心流通道
            direction = DDADirection.MAINTAIN
            pet_reaction = PetReaction.FOCUSED
            feedback_text = "完美的挑战难度，继续加油！"

            # 微调：在接近边界时做小幅调整
            if success_rate > 0.82 and current_difficulty < max_diff:
                new_difficulty = current_difficulty + 1
                direction = DDADirection.MICRO_ADJUST
                pet_reaction = PetReaction.CURIOUS
                feedback_text = "准备好接受新挑战了吗？"
            elif success_rate < 0.78 and current_difficulty > min_diff:
                new_difficulty = current_difficulty - 1
                direction = DDADirection.MICRO_ADJUST
                pet_reaction = PetReaction.CURIOUS
                feedback_text = "微调一下，让你更舒适。"

        else:
            new_difficulty = current_difficulty
            direction = DDADirection.MAINTAIN
            pet_reaction = PetReaction.FOCUSED
            feedback_text = "保持当前节奏，做得很好！"

        confidence = min(1.0, max(0.1, len(window) / self.window_size))

        return DDAResult(
            difficulty=new_difficulty,
            direction=direction,
            pet_reaction=pet_reaction,
            feedback_text=feedback_text,
            success_rate=success_rate,
            confidence=confidence,
        )

    def calculate_with_time(
        self,
        recent_results: List[bool],
        recent_times: List[float],  # 每题耗时（秒）
        current_difficulty: int,
        difficulty_range: tuple = (1, 10),
    ) -> DDAResult:
        """考虑耗时的高级 DDA

        如果正确率高但耗时异常长，说明难度可能偏高（学生在挣扎）；
        如果正确率低但耗时很短，说明学生可能在随机猜测。
        """
        result = self.calculate(recent_results, current_difficulty, difficulty_range)

        if not recent_times or len(recent_times) < 3:
            return result

        # 分析耗时趋势
        avg_time = sum(recent_times[-self.window_size:]) / min(len(recent_times), self.window_size)

        # 耗时辅助判断
        if result.success_rate > self.target_max and avg_time > 180:
            # 虽然对了但很慢 → 可能仍需巩固
            result.direction = DDADirection.MAINTAIN
            result.pet_reaction = PetReaction.FOCUSED
            result.feedback_text = "虽然都对了，但让我们在这个级别多练练，让速度也跟上来！"

        return result


# 全局单例
dda_engine = DDAEngine()
