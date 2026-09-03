"""BKT (贝叶斯知识追踪) 引擎

基于标准四参数 BKT 模型，追踪每个知识点的掌握概率。

参数:
- p_learn0: 初始掌握概率 P(L₀) — 学生开始前已掌握的概率
- p_transit: 学习迁移概率 P(T) — 从未掌握到掌握的转移概率
- p_guess: 猜测概率 P(G) — 未掌握但猜对的概率
- p_slip: 滑落概率 P(S) — 已掌握但粗心答错的概率

公式:
  P(Lₙ | correct)   = P(Lₙ₋₁) * (1 - P(S)) / [P(Lₙ₋₁) * (1 - P(S)) + (1 - P(Lₙ₋₁)) * P(G)]
  P(Lₙ | incorrect) = P(Lₙ₋₁) * P(S) / [P(Lₙ₋₁) * P(S) + (1 - P(Lₙ₋₁)) * (1 - P(G))]
  P(Lₙ₊₁) = P(Lₙ | evidence) + (1 - P(Lₙ | evidence)) * P(T)

参考:
- Corbett & Anderson (1995) "Knowledge tracing: Modeling the acquisition of procedural knowledge"
- 85%规则: Wilson et al. (2019) "The Eighty Five Percent Rule for optimal learning"
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class SkillState:
    """单个知识点的 BKT 状态"""
    skill_dim: str
    p_mastery: float = 0.5          # P(L) — 当前掌握概率
    total_attempts: int = 0
    correct_attempts: int = 0

    # BKT 四参数（可针对每个知识点调参）
    p_learn0: float = 0.35          # 初始掌握概率（中小学生偏低）
    p_transit: float = 0.12         # 学习率（每做一题的掌握概率增量）
    p_guess: float = 0.08           # 猜测率（低，因为题目设计避免了纯选择题）
    p_slip: float = 0.10            # 滑落率（粗心错）


@dataclass
class KnowledgeState:
    """学生的整体知识状态"""
    user_id: str
    skills: Dict[str, SkillState] = field(default_factory=dict)
    global_update_count: int = 0


class BKTEngine:
    """贝叶斯知识追踪引擎

    每个知识点独立维护 BKT 四参数模型。
    输出：掌握概率 P(L) → 映射到最优难度 → 维持 85% 心流规则。
    """

    # 默认参数（可通过构造函数覆盖）
    DEFAULT_PARAMS = {
        "p_learn0": 0.35,
        "p_transit": 0.12,
        "p_guess": 0.08,
        "p_slip": 0.10,
    }

    def __init__(self, **param_overrides):
        self.params = {**self.DEFAULT_PARAMS, **param_overrides}

    def get_or_create_skill(self, state: KnowledgeState, skill_dim: str) -> SkillState:
        """获取或创建知识点状态"""
        if skill_dim not in state.skills:
            params = dict(self.params)
            p_learn0 = params.pop("p_learn0")
            state.skills[skill_dim] = SkillState(
                skill_dim=skill_dim,
                p_mastery=p_learn0,
                p_learn0=p_learn0,
                **params,
            )
        return state.skills[skill_dim]

    def update(self, state: KnowledgeState, skill_dim: str, is_correct: bool) -> SkillState:
        """根据答题结果更新知识点掌握概率"""
        skill = self.get_or_create_skill(state, skill_dim)

        # Step 1: 证据更新 — 计算 P(L | evidence)
        if is_correct:
            p_correct_given_learned = 1.0 - skill.p_slip
            p_correct_given_unlearned = skill.p_guess
            numerator = skill.p_mastery * p_correct_given_learned
            denominator = numerator + (1.0 - skill.p_mastery) * p_correct_given_unlearned
        else:
            p_wrong_given_learned = skill.p_slip
            p_wrong_given_unlearned = 1.0 - skill.p_guess
            numerator = skill.p_mastery * p_wrong_given_learned
            denominator = numerator + (1.0 - skill.p_mastery) * p_wrong_given_unlearned

        p_mastery_given_evidence = numerator / max(denominator, 1e-10)

        # Step 2: 学习迁移 — P(Lₙ₊₁) = P(L|evidence) + (1 - P(L|evidence)) * P(T)
        p_mastery_new = p_mastery_given_evidence + (1.0 - p_mastery_given_evidence) * skill.p_transit

        # 更新状态
        skill.p_mastery = min(1.0, max(0.0, p_mastery_new))
        skill.total_attempts += 1
        if is_correct:
            skill.correct_attempts += 1
        state.global_update_count += 1

        return skill

    def batch_update(
        self, state: KnowledgeState, attempts: List[Tuple[str, bool]]
    ) -> KnowledgeState:
        """批量更新多个知识点的答题结果"""
        for skill_dim, is_correct in attempts:
            self.update(state, skill_dim, is_correct)
        return state

    def recommend_difficulty(self, skill: SkillState) -> int:
        """基于掌握概率推荐最优难度等级 (1-10)

        核心原理（85% 规则）:
        - 掌握度低 (< 0.4): 难度应低，让成功率接近预期的 0.75
        - 掌握度中 (0.4-0.7): 心流通道，难度匹配当前水平
        - 掌握度高 (> 0.7): 可适当增加挑战

        映射公式: difficulty = int(p_mastery * 10) + 1
        - p=0.0 → d=1 (最简单)
        - p=0.5 → d=6 (中等)
        - p=0.9 → d=10 (最难)
        """
        # 基础映射
        base_difficulty = int(skill.p_mastery * 10) + 1

        # 根据 85% 规则微调
        target_success = 0.85
        expected_success = skill.p_mastery * (1 - skill.p_slip) + (1 - skill.p_mastery) * skill.p_guess

        if expected_success > target_success + 0.05:
            # 太简单 → 升难度
            base_difficulty = min(10, base_difficulty + 1)
        elif expected_success < target_success - 0.05:
            # 太难 → 降难度
            base_difficulty = max(1, base_difficulty - 1)

        return base_difficulty

    def get_skill_report(self, state: KnowledgeState) -> dict:
        """生成知识掌握报告"""
        skills_report = []
        for dim, skill in state.skills.items():
            skills_report.append({
                "skill": dim,
                "mastery": round(skill.p_mastery, 3),
                "mastery_pct": round(skill.p_mastery * 100, 1),
                "attempts": skill.total_attempts,
                "correct": skill.correct_attempts,
                "recommended_difficulty": self.recommend_difficulty(skill),
                "level": self._mastery_level(skill.p_mastery),
            })

        if state.skills:
            avg_mastery = sum(s.p_mastery for s in state.skills.values()) / len(state.skills)
        else:
            avg_mastery = 0.0

        return {
            "user_id": state.user_id,
            "total_skills": len(state.skills),
            "average_mastery": round(avg_mastery, 3),
            "average_mastery_pct": round(avg_mastery * 100, 1),
            "total_updates": state.global_update_count,
            "skills": sorted(skills_report, key=lambda x: x["mastery"]),
        }

    @staticmethod
    def _mastery_level(p_mastery: float) -> str:
        """掌握度 → 等级标签"""
        if p_mastery >= 0.85:
            return "mastered"
        elif p_mastery >= 0.65:
            return "proficient"
        elif p_mastery >= 0.40:
            return "developing"
        elif p_mastery >= 0.20:
            return "beginner"
        else:
            return "novice"

    def adapt_parameters(self, skill: SkillState):
        """自适应调整 BKT 参数（随着数据增多动态优化）

        根据该知识点的实际表现调整:
        - 如果正确率高但掌握概率低 → 增加 p_guess (可能在猜)
        - 如果正确率低但掌握概率高 → 增加 p_slip (可能在粗心)
        """
        if skill.total_attempts < 10:
            return  # 数据不足，不调整

        observed_accuracy = skill.correct_attempts / max(skill.total_attempts, 1)
        expected_accuracy = skill.p_mastery * (1 - skill.p_slip) + (1 - skill.p_mastery) * skill.p_guess
        gap = observed_accuracy - expected_accuracy

        if abs(gap) < 0.05:
            return  # 模型拟合良好

        # 自适应调整（小步长）
        if gap > 0:
            # 实际比预测好 → 可能 p_transit 被低估，或 p_slip 被高估
            skill.p_transit = min(0.30, skill.p_transit + 0.005)
            skill.p_slip = max(0.02, skill.p_slip - 0.002)
        else:
            # 实际比预测差 → 可能 p_guess 被低估，或 p_transit 被高估
            skill.p_guess = min(0.20, skill.p_guess + 0.002)
            skill.p_transit = max(0.03, skill.p_transit - 0.005)


# 全局单例
bkt_engine = BKTEngine()
