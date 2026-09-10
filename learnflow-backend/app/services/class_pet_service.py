"""班级宠物园服务：行为积分喂养、形态进化与班级聚合

本服务是 LF-M54「班级积分养宠系统」的核心逻辑。它**操作已有的个人宠物
``PetProfile``**（每生一只），因为真实产品里「班级电子养宠」的本质就是：
**每个学生认领一只专属电子宠物，用行为积分喂养它成长、进化形态**；班级层面
只做聚合（排行榜 / 凝聚力 / 每周仪式）。

设计要点（均来自真实实践调研，见 docs/LearnFlow_学习成瘾化研究_补充文献测绘.md 第八节）：

1. 积分 = 口粮。行为加分 → 宠物四维属性（理解/坚持/创造/协作）增益 + 升级；
   行为扣分 → 宠物「饿肚子」（属性微降、情绪变 tired）。
2. 八级形态进化。宠物等级 1–10 映射到 8 个形态阶段（对标真实产品里
   小香猪 1 级闭眼 → 2 级抱奶瓶 → … → 酷炫进化体）。
3. 双刃剑预警。积分养宠本身带有「宠物饿死施压 / 攀比 / 小圈子」的暗黑模式风险，
   因此本服务同时暴露 ``starvation_risk()`` 与 ``connection_quality_feedback()``：
   前者标记 coercive 风险（应被 LAI 引擎 external_reward_dependency 捕获），
   后者把班级凝聚力回灌 LAI 的 connection_quality（Hari C1「连接替代」）。

``MECHANISM_KEY = "class_pet"`` 是本机制的标识字面量，供机制落地扫描识别。
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models.pet import PetProfile, PetMood


# 机制标识（字面量 class_pet 必须出现在本文件，供机制落地扫描识别）
MECHANISM_KEY = "class_pet"


# ──────────────────────────────────────────────────────────
# 形态进化：八级（对标真实产品「小香猪 1 级闭眼 → 2 级抱奶瓶 → … → 酷炫形态」）
# ──────────────────────────────────────────────────────────
MORPHOLOGY_STAGES = [
    "🥚 孵化中",        # 1
    "😴 闭眼打盹",      # 2
    "🍼 抱奶瓶",        # 3
    "🐾 蹒跚学步",      # 4
    "🌟 活泼好动",      # 5
    "🎀 盛装打扮",      # 6
    "👑 神兽觉醒",      # 7
    "✨ 酷炫进化体",    # 8
]

# 行为类型 → 计分维度（积分喂养时如何转化为学习维度增益）
# 真实规则示例：背课文+10口粮、发言+5能量、助人+2、拾金不昧+5
BEHAVIOR_DIM_MAP: Dict[str, tuple] = {
    "homework": ("persistence",),            # 作业/订正 → 坚持力
    "participation": ("understanding",),     # 课堂发言/举手 → 理解力
    "help": ("collaboration",),              # 助人/小组 → 协作力
    "creativity": ("creativity",),           # 创意解法 → 创造力
    "general": ("understanding", "persistence", "creativity", "collaboration"),
}

# 1 积分 ≈ 多少「四维增益点」
FOOD_PER_POINT = 0.8
# 扣分（饥饿）时每分扣减幅度
STARVE_PER_POINT = 0.3
# 宠物「饿肚子」风险阈值（total_score 低于此值视为濒临饥饿，提示 coercive 风险）
STARVATION_THRESHOLD = 30.0


@dataclass
class BehaviorPointEvent:
    """一次老师/班干部加减分触发的宠物喂养事件"""
    student_id: str
    points: float          # 可正可负（加分喂养 / 扣分饥饿）
    behavior: str          # homework/participation/help/creativity/general
    reason: str
    awarded_by: str        # 操作人（老师或班干部）id


class ClassPetService:
    """班级宠物园服务：喂养个体宠物 + 聚合班级视图"""

    @classmethod
    def morphology_stage(cls, level: int) -> int:
        """宠物等级 (1–10) → 形态阶段 (1–8)。"""
        return max(1, min(8, math.ceil(level * 8 / 10)))

    @classmethod
    def morphology_label(cls, level: int) -> str:
        """返回该等级对应的形态描述字符串。"""
        return MORPHOLOGY_STAGES[cls.morphology_stage(level) - 1]

    @classmethod
    def feed_pet_with_points(
        cls,
        pet: PetProfile,
        points: float,
        behavior: str = "general",
    ) -> PetProfile:
        """用行为积分喂养某学生的专属宠物。

        正分 → 按行为类型把增益分配到对应学习维度 + 升级 + 形态进化；
        负分 → 四维等比例微降（「饿肚子」），情绪转为 tired。
        """
        dims = BEHAVIOR_DIM_MAP.get(behavior, BEHAVIOR_DIM_MAP["general"])

        if points >= 0:
            gain = points * FOOD_PER_POINT
            per = gain / len(dims)
            for d in dims:
                setattr(pet, d, cls._clamp(getattr(pet, d) + per))
            pet.mood = PetMood.HAPPY if points > 0 else pet.mood
        else:
            loss = abs(points) * STARVE_PER_POINT
            per = loss / 4.0
            for d in ("understanding", "persistence", "creativity", "collaboration"):
                setattr(pet, d, cls._clamp(getattr(pet, d) - per))
            pet.mood = PetMood.TIRED

        # 等级进化：总分每 +10 升一级（与 pet_service 规则一致）
        new_level = min(10, int(pet.total_score // 10) + 1)
        if new_level > pet.level:
            pet.level = new_level
        return pet

    @classmethod
    def starvation_risk(cls, pet: PetProfile) -> bool:
        """宠物是否濒临「饿肚子」。

        返回 True 表示该学生宠物长期缺乏喂养，对应积分养宠的
        ** coercive 风险**（怕宠物饿死而被迫刷分）。该信号应被 LAI 引擎的
        ``external_reward_dependency`` / 行为控制维度捕获，并由 MechanismArbitrator
        的健康护栏降温，而非放任施压。
        """
        return pet.total_score < STARVATION_THRESHOLD

    @classmethod
    def build_garden_view(
        cls,
        pets: List[PetProfile],
        class_id: str,
        cohesion: float,
        active_ratio: float = 0.7,
        top_n: int = 10,
    ) -> Dict:
        """由班级全部宠物聚合出「班级宠物园」视图（同步，纯计算）。

        聚合指标：排行榜（按等级）、形态分布、平均等级、活跃宠物数、
        班级凝聚力、以及回灌 LAI 的连接质量。
        """
        total = len(pets)
        if total == 0:
            return {
                "class_id": class_id,
                "total_pets": 0,
                "active_pets": 0,
                "average_level": 0.0,
                "cohesion": round(cohesion, 1),
                "connection_quality": round(cls.connection_quality_feedback(cohesion, active_ratio), 3),
                "leaderboard": [],
                "morphology_distribution": {},
            }

        # 排行榜：按等级降序，取前列
        ranked = sorted(pets, key=lambda p: p.level, reverse=True)
        leaderboard = [
            {
                "pet_id": p.id,
                "level": p.level,
                "morphology_stage": cls.morphology_stage(p.level),
                "morphology_label": cls.morphology_label(p.level),
                "total_score": round(p.total_score, 1),
                "starving": cls.starvation_risk(p),
            }
            for p in ranked[:top_n]
        ]

        # 形态分布
        dist: Dict[int, int] = {}
        for p in pets:
            stage = cls.morphology_stage(p.level)
            dist[stage] = dist.get(stage, 0) + 1
        morphology_distribution = {
            str(stage): {
                "count": dist[stage],
                "label": MORPHOLOGY_STAGES[stage - 1],
            }
            for stage in sorted(dist)
        }

        active = sum(1 for p in pets if p.total_score >= 50.0)  # 已喂养（非初始）的宠物
        avg_level = sum(p.level for p in pets) / total

        return {
            "class_id": class_id,
            "total_pets": total,
            "active_pets": active,
            "average_level": round(avg_level, 1),
            "cohesion": round(cohesion, 1),
            "connection_quality": round(cls.connection_quality_feedback(cohesion, active_ratio), 3),
            "leaderboard": leaderboard,
            "morphology_distribution": morphology_distribution,
        }

    @classmethod
    def class_weekly_report(
        cls,
        pets: List[PetProfile],
        class_id: str,
        cohesion: float,
        ritual_due: bool,
        active_ratio: float = 0.7,
    ) -> Dict:
        """每周「喂养时间」报告：在 garden 视图之上补充仪式与风险概览。"""
        view = cls.build_garden_view(pets, class_id, cohesion, active_ratio)
        starving_count = sum(1 for p in pets if cls.starvation_risk(p))
        view.update({
            "ritual_due": ritual_due,
            "starving_pets": starving_count,
            "health_note": (
                "班级宠物园以真实连接替代虚拟刺激；若 starving_pets 偏高，"
                "说明积分施压过重，应下调扣分力度并启用健康护栏。"
                if starving_count else "状态健康：以正向激励为主。"
            ),
        })
        return view

    @classmethod
    def connection_quality_feedback(
        cls,
        cohesion: float,
        active_ratio: float = 0.7,
    ) -> float:
        """返回班级真实社交连接质量 (0..1)，回灌 LAI 引擎 connection_quality。

        Hari (C1)「connection-substitution」：班级凝聚力越高、参与率越高，
        代表现实中的真实连接越强，从而可被 LAI 引擎用来抵消虚拟刺激的成瘾拉力。
        """
        base = max(0.0, min(1.0, cohesion / 100.0))
        return max(0.0, min(1.0, 0.7 * base + 0.3 * active_ratio))

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))
