"""记忆科学引擎 (Memory Science Engine)

整合认知心理学与学习科学最新证据，强化 LearnFlow 的记忆系统：
1. FSRS 风格的间隔重复调度（难度、稳定性、可提取性）
2. 记忆巩固建议（睡眠、运动、BDNF）
3. 记忆术生成（首字母缩略、关键词、挂钩法）
4. 具体例子生成器（抽象概念具象化）
5. 适难性编排器（根据遗忘曲线选择学习方法）

参考：
- FSRS (Free Spaced Repetition Scheduler): https://github.com/open-spaced-repetition
- Piotr Wozniak, SuperMemo/Anki 间隔重复研究
- Walker (2017) Why We Sleep; Ratey (2008) Spark
- Roediger & Karpicke (2006) Test-Enhanced Learning
- Bjork (1994) Desirable Difficulties
"""
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════
# 1. FSRS 风格间隔重复调度器
# ═══════════════════════════════════════════════════════════

@dataclass
class FSRSMemoryState:
    """FSRS 记忆状态：难度(D)、稳定性(S)、可提取性(R)"""
    difficulty: float = 5.0  # 1-10, 5 为默认
    stability: float = 1.0   # 天数，表示半衰期
    elapsed_days: float = 0.0
    review_count: int = 0
    last_review: Optional[datetime] = None


class FSRSSpacedRepetitionEngine:
    """FSRS 风格调度器

    核心公式（简化版）：
    - R = 2^(-elapsed_days / S)   可提取性
    - I = S * (9 / R_target - 1) / D   推荐间隔
    - S_new = S * (1 + feedback_factor * (1 - D/10))
    - D_new = D + 0.3 * (3 - grade)  (grade 1-4)
    """

    GRADE_AGAIN = 1
    GRADE_HARD = 2
    GRADE_GOOD = 3
    GRADE_EASY = 4

    @classmethod
    def retrievability(cls, stability: float, elapsed_days: float) -> float:
        """计算当前可提取性 (0-1)"""
        if stability <= 0:
            return 0.0
        return 2.0 ** (-elapsed_days / stability)

    @classmethod
    def recommended_interval(
        cls,
        stability: float,
        difficulty: float,
        target_retrievability: float = 0.90,
        max_days: int = 365,
    ) -> float:
        """推荐下次复习间隔（天）"""
        difficulty = max(1.0, min(10.0, difficulty))
        # I = S * (9 / R_target - 1) / D
        interval = stability * (9.0 / target_retrievability - 1.0) / (difficulty / 5.0)
        return max(1.0, min(max_days, interval))

    @classmethod
    def update_after_review(
        cls,
        state: FSRSMemoryState,
        grade: int,
        review_time: Optional[datetime] = None,
    ) -> FSRSMemoryState:
        """根据评分更新记忆状态"""
        grade = max(cls.GRADE_AGAIN, min(cls.GRADE_EASY, grade))
        review_time = review_time or datetime.now(UTC)

        if state.last_review:
            elapsed = (review_time - state.last_review).total_seconds() / 86400
        else:
            elapsed = 0.0

        # 可提取性
        r = cls.retrievability(state.stability, elapsed)

        # 稳定性更新：答得好增加，答得差减少
        if grade >= cls.GRADE_GOOD:
            # Easy 时大幅增长，Good 时中等增长，Hard 时小幅增长
            gain = 1.0 + 0.5 * (grade - cls.GRADE_GOOD)
            # 难度越低（越容易），增长越少；难度越高，增长越多
            gain *= (1.0 + (state.difficulty - 5.0) / 20.0)
            new_stability = state.stability * (1.0 + gain)
        else:
            # Again/Hard：重置稳定性，但保留部分经验
            drop = 0.5 if grade == cls.GRADE_HARD else 0.8
            new_stability = max(1.0, state.stability * (1.0 - drop))

        # 难度更新：Again 增加难度，Easy 降低难度
        diff_delta = 0.3 * (cls.GRADE_GOOD - grade)
        new_difficulty = max(1.0, min(10.0, state.difficulty + diff_delta))

        return FSRSMemoryState(
            difficulty=round(new_difficulty, 2),
            stability=round(new_stability, 2),
            elapsed_days=round(elapsed, 2),
            review_count=state.review_count + 1,
            last_review=review_time,
        )

    @classmethod
    def schedule_next(cls, state: FSRSMemoryState, grade: int) -> Dict[str, Any]:
        """完成一次评分后，返回下次复习计划"""
        new_state = cls.update_after_review(state, grade)
        interval = cls.recommended_interval(new_state.stability, new_state.difficulty)
        next_review = new_state.last_review + timedelta(days=interval) if new_state.last_review else datetime.now(UTC)
        return {
            "state": new_state,
            "next_review_date": next_review,
            "next_interval_days": round(interval, 2),
            "retrievability_now": round(cls.retrievability(new_state.stability, 0), 3),
            "difficulty": new_state.difficulty,
            "stability": new_state.stability,
        }


# ═══════════════════════════════════════════════════════════
# 2. 记忆巩固引擎（睡眠、运动、BDNF）
# ═══════════════════════════════════════════════════════════

class MemoryConsolidationEngine:
    """基于神经科学的记忆巩固建议

    睡眠和运动是记忆从海马体向皮层转移的两大助推器。
    """

    @staticmethod
    def get_sleep_recommendation(last_learning_time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取睡眠建议"""
        now = datetime.now(UTC)
        if last_learning_time is None:
            last_learning_time = now
        hours_since_learning = (now - last_learning_time).total_seconds() / 3600

        advice = {
            "priority": "high" if hours_since_learning < 8 else "normal",
            "message": "今晚保证 7-9 小时睡眠，大脑会在睡眠中整理今天学到的知识。",
            "science": "Walker (2017): 睡眠中的慢波振荡帮助海马体记忆重放并转存到皮层。",
            "action": "睡前 30 分钟避免刷手机，让大脑进入巩固模式。",
        }
        if hours_since_learning < 4:
            advice["action"] = "学习结束后 2 小时内小睡 10-20 分钟也能提升记忆 20%。"
        return advice

    @staticmethod
    def get_exercise_recommendation() -> Dict[str, Any]:
        """获取运动建议"""
        return {
            "priority": "medium",
            "message": "学习结束后进行 20-30 分钟有氧运动（快走/慢跑）。",
            "science": "运动后 BDNF 水平上升，促进海马体神经发生和突触可塑性。",
            "action": "今天学完 30 分钟后，出门快走 20 分钟。",
            "best_time": "学习结束后 1-2 小时内",
        }

    @staticmethod
    def consolidation_plan(learned_topics: List[str]) -> Dict[str, Any]:
        """为最近学习内容生成 24 小时巩固计划"""
        return {
            "topics": learned_topics,
            "plan": [
                {"time": "学习结束后 1-2 小时", "action": "进行 20 分钟有氧运动", "why": "提升 BDNF"},
                {"time": "睡前", "action": "避免蓝光，保证 7-9 小时睡眠", "why": "慢波睡眠促进记忆重放"},
                {"time": "明天早晨", "action": "花 5 分钟主动回忆昨天学的知识点", "why": "睡眠后提取可巩固记忆"},
            ],
            "message": "记忆不仅发生在学习时，也发生在睡眠和运动后。",
        }


# ═══════════════════════════════════════════════════════════
# 3. 记忆术引擎
# ═══════════════════════════════════════════════════════════

class MnemonicEngine:
    """生成记忆术辅助"""

    PEG_WORDS = [
        "太阳", "鞋子", "扇子", "伞", "死", "舞", "柳", "妻", "疤", "酒",
    ]

    @staticmethod
    def acronym(items: List[str]) -> Dict[str, Any]:
        """首字母缩写法"""
        first_chars = [item[0] if item else "" for item in items]
        acronym_str = "".join(first_chars).upper()
        return {
            "method": "首字母缩略法",
            "items": items,
            "acronym": acronym_str,
            "tip": f"把 '{acronym_str}' 编成一个词或一句话，帮助回忆顺序。",
        }

    @staticmethod
    def keyword_method(word: str, meaning: str) -> Dict[str, Any]:
        """关键词法（常用于外语词汇）"""
        # 简单用谐音或联想
        return {
            "method": "关键词法",
            "keyword": word,
            "meaning": meaning,
            "prompt": f"找一个与 '{word}' 发音相近的中文词，并把它和 '{meaning}' 画成一幅夸张画面。",
            "example": f"例如把 '{word}' 想象成 '{meaning}' 的某种夸张形象。",
        }

    @staticmethod
    def peg_system(items: List[str]) -> Dict[str, Any]:
        """挂钩法：把要记的内容与固定数字挂钩词关联"""
        pegs = MnemonicEngine.PEG_WORDS[: len(items)]
        associations = []
        for i, (item, peg) in enumerate(zip(items, pegs)):
            associations.append({
                "number": i + 1,
                "peg": peg,
                "item": item,
                "prompt": f"把 '{item}' 和 '{peg}' 画在一起，形成一幅夸张画面。",
            })
        return {
            "method": "挂钩法",
            "associations": associations,
            "tip": "数字挂钩词固定不变，内容随要记的材料变化。",
        }


# ═══════════════════════════════════════════════════════════
# 4. 具体例子生成器
# ═══════════════════════════════════════════════════════════

class ConcreteExamplesEngine:
    """为抽象概念生成具体例子，促进理解迁移"""

    TEMPLATES = [
        "想象你在{scenario}，这个概念就像{analogy}。",
        "如果把{concept}比作一个日常物品，它就像是{analogy}。",
        "在{scenario}中，你会看到{concept}的例子：{example}。",
    ]

    DOMAIN_ANALOGIES = {
        "math": {
            "scenario": "超市买东西",
            "analogies": ["找零钱", "分蛋糕", "按比例调配果汁"],
        },
        "science": {
            "scenario": "厨房做饭",
            "analogies": ["食谱中的化学反应", "冰箱保温", "搅拌加速溶解"],
        },
        "language": {
            "scenario": "和朋友聊天",
            "analogies": ["搭积木", "交通规则", "拼图"],
        },
        "history": {
            "scenario": "班级选举",
            "analogies": ["排队规则", "小组分工", "接力赛"],
        },
        "programming": {
            "scenario": "整理衣柜",
            "analogies": ["分类盒子", "标签系统", "自动化流程"],
        },
    }

    @classmethod
    def generate_example(cls, concept: str, domain: str = "general") -> Dict[str, Any]:
        """为概念生成具体例子"""
        domain_info = cls.DOMAIN_ANALOGIES.get(domain, {
            "scenario": "日常生活",
            "analogies": ["一个常见场景", "一件熟悉物品", "一次真实经历"],
        })
        analogy = random.choice(domain_info["analogies"])
        template = random.choice(cls.TEMPLATES)
        example = template.format(
            concept=concept,
            scenario=domain_info["scenario"],
            analogy=analogy,
            example=f"{analogy}中就体现了{concept}",
        )
        return {
            "method": "具体例子",
            "concept": concept,
            "domain": domain,
            "example": example,
            "action": f"在脑中想象一个关于 '{concept}' 的具体画面或场景。",
            "science": "具体例子激活大脑的感觉和运动皮层，让抽象概念更难忘。",
        }


# ═══════════════════════════════════════════════════════════
# 5. 适难性编排器（Desirable Difficulties）
# ═══════════════════════════════════════════════════════════

class DesirableDifficultiesOrchestrator:
    """根据学习阶段和遗忘曲线推荐最优方法

    核心原则：适度的困难（需要努力但可解决）比轻松学习更促进长期记忆。
    """

    @staticmethod
    def recommend_methods(
        mastery: float,
        days_since_last_review: float,
        correct_streak: int,
        error_rate: float,
    ) -> Dict[str, Any]:
        """推荐学习方法组合"""
        methods = []
        if days_since_last_review >= 1:
            methods.append({
                "method": "主动回忆",
                "reason": "间隔后先尝试回忆，再查看答案，强化提取通路。",
                "priority": 1,
            })
        if mastery < 0.4:
            methods.append({
                "method": "双重编码+具体例子",
                "reason": "低掌握度需要建立多重编码和情境关联。",
                "priority": 2,
            })
        elif mastery < 0.8:
            methods.append({
                "method": "交错练习",
                "reason": "中等掌握度时混合练习可提升迁移和辨别能力。",
                "priority": 2,
            })
        else:
            methods.append({
                "method": "生成效应/精细加工",
                "reason": "高掌握度时通过生成和解释深化理解。",
                "priority": 2,
            })
        if error_rate > 0.4:
            methods.append({
                "method": "错题分析+精细加工",
                "reason": "高错误率需要针对错误类型进行深度加工。",
                "priority": 3,
            })
        if correct_streak >= 5:
            methods.append({
                "method": "间隔拉长",
                "reason": "连续答对说明稳定性高，可适当延长复习间隔。",
                "priority": 4,
            })
        return {
            "recommended": sorted(methods, key=lambda x: x["priority"]),
            "principle": "适难性原则：在略有挑战但可完成的难度下学习效果最好。",
        }

    @staticmethod
    def forgetting_curve_alert(stability: float, elapsed_days: float) -> Dict[str, Any]:
        """基于遗忘曲线提醒复习"""
        r = FSRSSpacedRepetitionEngine.retrievability(stability, elapsed_days)
        if r >= 0.85:
            level = "strong"
            message = "记忆还很牢固，可以按正常节奏复习。"
        elif r >= 0.6:
            level = "moderate"
            message = "记忆开始衰退，建议尽快安排一次主动回忆。"
        else:
            level = "weak"
            message = "记忆已大幅衰退，需要重新学习与提取练习。"
        return {
            "retrievability": round(r, 3),
            "level": level,
            "message": message,
            "elapsed_days": elapsed_days,
            "stability": stability,
        }


class MemoryScienceOrchestrator:
    """记忆科学编排器：整合 FSRS、巩固、记忆术、例子、适难性"""

    @staticmethod
    def get_review_plan(item_states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """为多个知识点生成统一复习计划"""
        plan = []
        for item in item_states:
            state = FSRSMemoryState(
                difficulty=item.get("difficulty", 5.0),
                stability=item.get("stability", 1.0),
                review_count=item.get("review_count", 0),
                last_review=item.get("last_review"),
            )
            elapsed = 0.0
            if state.last_review:
                lr = state.last_review
                # SQLite 读回的 DateTime 为 naive；补齐 UTC 时区后再相减，避免 TypeError。
                if isinstance(lr, datetime) and lr.tzinfo is None:
                    lr = lr.replace(tzinfo=UTC)
                if isinstance(lr, datetime):
                    elapsed = (datetime.now(UTC) - lr).total_seconds() / 86400
            r = FSRSSpacedRepetitionEngine.retrievability(state.stability, elapsed)
            interval = FSRSSpacedRepetitionEngine.recommended_interval(state.stability, state.difficulty)
            plan.append({
                "item_id": item.get("id"),
                "concept": item.get("concept"),
                "difficulty": state.difficulty,
                "stability": state.stability,
                "retrievability": round(r, 3),
                "recommended_interval_days": round(interval, 1),
            })
        plan.sort(key=lambda x: x["retrievability"])
        return {
            "due_items": [p for p in plan if p["retrievability"] < 0.85],
            "strong_items": [p for p in plan if p["retrievability"] >= 0.85],
            "message": "优先复习可提取性低于 85% 的知识点。",
        }

    @staticmethod
    def generate_memory_aid(concept: str, domain: str = "general") -> Dict[str, Any]:
        """为单个知识点生成记忆辅助包"""
        return {
            "concept": concept,
            "domain": domain,
            "concrete_example": ConcreteExamplesEngine.generate_example(concept, domain),
            "mnemonic_acronym": MnemonicEngine.acronym(list(concept)),
            "consolidation": MemoryConsolidationEngine.get_sleep_recommendation(),
        }
