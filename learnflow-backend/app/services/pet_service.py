"""宠物系统服务：四维属性更新与进化逻辑

宠物属性反映学生的四个学习维度：
- understanding (理解力): 正确率↑、少用提示、举一反三
- persistence (坚持力): 做困难题、重试错题、不弃题
- creativity (创造力): 解题方式多样、独特解法
- collaboration (协作力): 帮助同学、参加小组、受助
"""
import math
from dataclasses import dataclass
from typing import Optional, Dict

from app.models.pet import PetProfile, PetMood


@dataclass
class PetUpdateEvent:
    """一次学习行为触发的宠物更新"""
    understanding_delta: float = 0.0
    persistence_delta: float = 0.0
    creativity_delta: float = 0.0
    collaboration_delta: float = 0.0
    mood: PetMood = PetMood.HAPPY
    description: str = ""


class PetService:
    """宠物系统服务

    核心原则：宠物成长反映学习维度，而非单纯积分。
    积分只用于虚拟进度，不兑换实物。
    """

    # 各行为的基础分值
    CORRECT_ANSWER_BASE = 2.0       # 答对
    HARD_CORRECT_BONUS = 1.5        # 答对难题额外加分
    NO_HINT_BONUS = 1.0             # 未用提示
    RETRY_SUCCESS = 3.0             # 重试成功（坚持力）
    CREATIVE_SOLUTION = 4.0         # 创造性解法
    HELP_OTHERS = 3.0               # 帮助他人
    RECEIVED_HELP = 1.5             # 接受帮助
    SKIP_PENALTY = -1.0             # 跳过（轻微惩罚）

    # 衰减系数（避免同类型成就刺激无限膨胀）
    REPETITION_DECAY = 0.85  # 每次同类行为递减系数

    @classmethod
    def calculate_correct_answer(
        cls,
        difficulty: int,
        hints_used: int = 0,
        is_retry: bool = False,
        is_creative: bool = False,
        repetition_count: int = 0,
    ) -> PetUpdateEvent:
        """答对题目时的宠物更新"""
        event = PetUpdateEvent(mood=PetMood.HAPPY)

        # 基础理解力
        decay = cls.REPETITION_DECAY ** repetition_count
        event.understanding_delta = cls.CORRECT_ANSWER_BASE * (difficulty / 5) * decay

        # 难度加成
        if difficulty >= 7:
            event.persistence_delta += cls.HARD_CORRECT_BONUS * decay
            event.understanding_delta += 0.5

        # 无提示加成
        if hints_used == 0:
            event.understanding_delta += cls.NO_HINT_BONUS * decay

        # 重试成功 → 坚持力
        if is_retry:
            event.persistence_delta += cls.RETRY_SUCCESS * decay
            event.description = "不放弃，最终成功！坚持力 +"

        # 创造性解法
        if is_creative:
            event.creativity_delta += cls.CREATIVE_SOLUTION * decay
            event.description = "独特的思路！创造力 +"
            event.mood = PetMood.CONFIDENT

        return event

    @classmethod
    def calculate_wrong_answer(
        cls,
        difficulty: int,
        chosen_recovery: str,  # "watch_tutorial" | "retry" | "skip"
        repetition_count: int = 0,
    ) -> PetUpdateEvent:
        """答错题目时的宠物更新（不扣分，而是提供恢复路径）"""
        event = PetUpdateEvent()
        decay = cls.REPETITION_DECAY ** repetition_count

        if chosen_recovery == "watch_tutorial":
            # 看讲解 → 理解力微增，宠物变好奇
            event.understanding_delta = 0.5 * decay
            event.mood = PetMood.CURIOUS
            event.description = "从错误中学习，理解力微增！"

        elif chosen_recovery == "retry":
            # 再试一次 → 坚持力提升
            event.persistence_delta = 1.0 * decay
            event.mood = PetMood.ENCOURAGING
            event.description = "勇于再试！坚持力 +"

        elif chosen_recovery == "skip":
            # 跳过 → 标记待突破
            event.persistence_delta = cls.SKIP_PENALTY * decay
            event.mood = PetMood.TIRED
            event.description = "标记为待突破，下次再来！"

        return event

    @classmethod
    def calculate_collaboration(
        cls,
        action: str,  # "helped_other" | "received_help" | "group_task"
        repetition_count: int = 0,
    ) -> PetUpdateEvent:
        """协作行为更新"""
        event = PetUpdateEvent()
        decay = cls.REPETITION_DECAY ** repetition_count

        if action == "helped_other":
            event.collaboration_delta = cls.HELP_OTHERS * decay
            event.understanding_delta = 1.0 * decay  # 教学相长
            event.mood = PetMood.CONFIDENT
            event.description = "帮助他人，教学相长！"

        elif action == "received_help":
            event.collaboration_delta = cls.RECEIVED_HELP * decay
            event.mood = PetMood.HAPPY
            event.description = "接受帮助，共同进步！"

        elif action == "group_task":
            event.collaboration_delta = 2.0 * decay
            event.mood = PetMood.FOCUSED
            event.description = "团队协作完成！"

        return event

    @classmethod
    def apply_update(cls, pet: PetProfile, event: PetUpdateEvent) -> PetProfile:
        """应用更新到宠物，处理等级进化"""
        pet.understanding = cls._clamp(pet.understanding + event.understanding_delta)
        pet.persistence = cls._clamp(pet.persistence + event.persistence_delta)
        pet.creativity = cls._clamp(pet.creativity + event.creativity_delta)
        pet.collaboration = cls._clamp(pet.collaboration + event.collaboration_delta)
        pet.mood = event.mood

        # 等级进化：总分每 +10 升一级
        new_level = min(10, int(pet.total_score // 10) + 1)
        if new_level > pet.level:
            pet.level = new_level

        return pet

    @classmethod
    def get_weekly_summary(cls, pet: PetProfile) -> Dict:
        """生成周报摘要"""
        return {
            "level": pet.level,
            "total_score": round(pet.total_score, 1),
            "dominant_trait": pet.dominant_trait,
            "dimensions": {
                "understanding": round(pet.understanding, 1),
                "persistence": round(pet.persistence, 1),
                "creativity": round(pet.creativity, 1),
                "collaboration": round(pet.collaboration, 1),
            },
            "mood": pet.mood.value,
            "level_progress": round(pet.get_level_progress(), 1),
        }

    @staticmethod
    def _clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        return max(min_val, min(max_val, value))
