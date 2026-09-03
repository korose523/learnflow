"""入学水平测试 — Adaptive Placement Test

类似 IRT 计算自适应测试 (CAT) 的原理:
  - 从中间难度开始
  - 答对→升难度
  - 答错→降难度
  - 收敛到学生的真实水平
  - 输出: 各知识点的初始难度设置 + 综合等级

设计原则:
  - 不能太长 (控制在8-12题)
  - 不能让学生感到挫败
  - 结果是"起点"而非"标签"
  - 测试过程中保持鼓励和积极框架
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random
import math


# ═══════════════════════════════════════════════════════════
# 1. 自适应测试引擎 — CAT
# ═══════════════════════════════════════════════════════════

class DifficultyLevel(str, Enum):
    VERY_EASY = "very_easy"      # 1-2
    EASY = "easy"                 # 3-4
    MEDIUM = "medium"             # 5-6
    HARD = "hard"                 # 7-8
    VERY_HARD = "very_hard"       # 9-10


@dataclass
class PlacementState:
    """水平测试状态"""
    user_id: str
    # 当前测试的题目索引
    current_question_index: int = 0
    total_questions: int = 10

    # 当前的难度区间
    current_difficulty: int = 5               # 从中间开始
    difficulty_min: int = 1
    difficulty_max: int = 10

    # 每个知识点的测试结果
    topic_results: Dict[str, List[bool]] = field(default_factory=dict)
    # 综合答题记录
    all_results: List[Tuple[int, bool]] = field(default_factory=list)

    # 收敛追踪
    last_three: List[bool] = field(default_factory=list)
    converged: bool = False
    convergence_at_question: int = 0

    # 测试阶段
    phase: str = "welcome"  # welcome → testing → result
    test_started_at: Optional[datetime] = None


class AdaptivePlacementEngine:
    """自适应水平测试引擎

    类似 GRE/GMAT 的 CAT 自适应测试。
    根据每个回答实时调整下一题的难度。
    """

    # 收敛参数: 最近3题中2题正确率在40-60%之间=已找到真实水平
    CONVERGENCE_WINDOW = 3
    MIN_QUESTIONS = 6
    MAX_QUESTIONS = 12

    # 难度调整步长
    INITIAL_STEP = 2    # 前几题大步调
    FINE_STEP = 1       # 后几题微调

    # 测试涉及的Topic
    TEST_TOPICS = ["运算基础", "逻辑推理", "应用理解", "数学思维"]

    # 各topic的测试题数分配
    TOPIC_QUESTIONS = {
        "运算基础": 3,
        "逻辑推理": 3,
        "应用理解": 2,
        "数学思维": 2,
    }

    @classmethod
    def start_test(cls, user_id: str) -> dict:
        """开始水平测试"""
        state = PlacementState(
            user_id=user_id,
            test_started_at=datetime.now(UTC),
            phase="testing",
        )

        return {
            "test_started": True,
            "total_questions": state.total_questions,
            "current_difficulty": state.current_difficulty,
            "message": cls._get_start_message(),
            "encouragement": "这8-12道题帮助系统了解你的当前水平，为你匹配最合适的学习难度。没有'对错好坏'——只有'起点在哪里'。",
        }

    @classmethod
    def _get_start_message(cls) -> str:
        messages = [
            "让我们找到最适合你的起点。不是测试——是为你定制学习路径。",
            "接下来的几分钟，系统会自适应地调整题目难度，找到你的最佳学习区间。",
            "准备好了吗？从难度适中的题目开始，系统会根据你的回答自动调整。",
        ]
        return random.choice(messages)

    @classmethod
    def get_next_question(cls, state: PlacementState,
                           available_topics: List[str] = None) -> dict:
        """获取下一道测试题"""
        if state.converged:
            return {"test_complete": True, "reason": "水平已确定"}

        if state.current_question_index >= cls.MAX_QUESTIONS:
            state.converged = True
            return {"test_complete": True, "reason": "达到最大题数"}

        # 选择topic (确保每个topic都有覆盖)
        topic = cls._select_topic(state)

        # 当前难度
        difficulty = state.current_difficulty

        return {
            "test_complete": False,
            "question_number": state.current_question_index + 1,
            "total_questions": cls.MAX_QUESTIONS,
            "topic": topic,
            "difficulty": difficulty,
            "difficulty_name": cls._difficulty_name(difficulty),
            "progress_pct": round((state.current_question_index) / cls.MAX_QUESTIONS * 100),
            "message": cls._get_question_message(state.current_question_index),
            "remaining": cls.MAX_QUESTIONS - state.current_question_index,
        }

    @classmethod
    def submit_answer(cls, state: PlacementState, is_correct: bool) -> dict:
        """提交答案，调整下一题难度"""
        state.all_results.append((state.current_difficulty, is_correct))
        state.last_three.append(is_correct)
        if len(state.last_three) > cls.CONVERGENCE_WINDOW:
            state.last_three.pop(0)

        state.current_question_index += 1

        # 自适应难度调整
        step = cls.FINE_STEP if state.current_question_index > 3 else cls.INITIAL_STEP

        if is_correct:
            state.current_difficulty = min(10, state.current_difficulty + step)
        else:
            state.current_difficulty = max(1, state.current_difficulty - step)

        # 收敛检测
        if state.current_question_index >= cls.MIN_QUESTIONS:
            state.converged = cls._check_convergence(state)

        return {
            "answered": True,
            "is_correct": is_correct,
            "new_difficulty": state.current_difficulty,
            "converged": state.converged,
            "questions_done": state.current_question_index,
            "adjustment": f"难度{'↑' if is_correct else '↓'}调整为 {state.current_difficulty}",
            "encouragement": cls._get_answer_encouragement(state.current_question_index, is_correct),
        }

    @classmethod
    def _check_convergence(cls, state: PlacementState) -> bool:
        """检查是否收敛: 最近3题中正确率在33%-67%之间"""
        if len(state.last_three) < cls.CONVERGENCE_WINDOW:
            return False
        accuracy = sum(state.last_three) / len(state.last_three)
        if 0.33 <= accuracy <= 0.67:
            state.convergence_at_question = state.current_question_index
            return True
        return False

    @classmethod
    def generate_result(cls, state: PlacementState) -> dict:
        """生成测试结果"""
        # 计算估计能力水平
        total = len(state.all_results)
        if total == 0:
            return {"error": "没有答题记录"}

        correct = sum(1 for _, is_correct in state.all_results if is_correct)
        accuracy = correct / total

        # 加权难度: 近期题目的难度更重要
        weights = [1 + i / total for i in range(total)]
        weighted_difficulty = sum(
            diff * w for (diff, _), w in zip(state.all_results, weights)
        ) / sum(weights)

        # 综合评估
        estimated_level = round(weighted_difficulty)
        estimated_level = max(1, min(10, estimated_level))

        # 级别描述
        level_desc = cls._get_level_description(estimated_level, accuracy)

        # 各topic的估计难度
        topic_difficulties = {}
        topic_results = {}

        return {
            "test_completed": True,
            "total_questions": total,
            "correct": correct,
            "accuracy": round(accuracy * 100),
            "estimated_level": estimated_level,
            "level_name": level_desc["name"],
            "level_description": level_desc["description"],
            "difficulty_range": f"{max(1, estimated_level - 1)}-{min(10, estimated_level + 1)}",
            "recommended_starting_difficulty": estimated_level,
            "growth_potential": cls._get_growth_potential(estimated_level),
            "next_steps": level_desc["next"],
            "message": cls._get_result_message(estimated_level, accuracy),
            "topic_suggestions": {
                "运算基础": max(1, estimated_level - 1),
                "逻辑推理": estimated_level,
                "应用理解": max(1, estimated_level),
                "数学思维": min(10, estimated_level + 1),
            },
        }

    @classmethod
    def _select_topic(cls, state: PlacementState) -> str:
        """选择下一个topic，确保均衡覆盖"""
        covered = set()
        for t in cls.TEST_TOPICS:
            if t in state.topic_results:
                covered.add(t)

        # 优先未覆盖的topic
        uncovered = [t for t in cls.TEST_TOPICS if t not in covered]
        if uncovered:
            return random.choice(uncovered)

        # 轮转已覆盖的topic
        idx = state.current_question_index % len(cls.TEST_TOPICS)
        return cls.TEST_TOPICS[idx]

    @classmethod
    def _difficulty_name(cls, difficulty: int) -> str:
        if difficulty <= 2: return "基础"
        elif difficulty <= 4: return "简单"
        elif difficulty <= 6: return "中等"
        elif difficulty <= 8: return "较难"
        return "挑战"

    @classmethod
    def _get_question_message(cls, index: int) -> str:
        if index == 0: return "从中等难度开始..."
        elif index <= 2: return "系统正在了解你的水平..."
        elif index <= 4: return "差不多找到你的节奏了..."
        return "最后几道题..."

    @classmethod
    def _get_answer_encouragement(cls, question_num: int, is_correct: bool) -> str:
        if is_correct:
            pool = ["答对了！系统正在提升难度。", "很好！", "不错！", "继续加油！"]
        else:
            pool = ["没关系，系统正在找到适合你的难度。", "这道题偏难了——这很正常，系统正在调整。",
                     "答错也是测试的一部分。", "这就是测试的目的——找到最佳起点。"]
        return random.choice(pool)

    @classmethod
    def _get_level_description(cls, level: int, accuracy: float) -> dict:
        descriptions = {
            1: {"name": "探索起步", "description": "你正在建立基础。从基础题开始，稳步前进是最好的策略。",
                "next": "从最简单的基础题开始，每做对一道都是一次胜利。"},
            3: {"name": "基础巩固", "description": "你已经掌握了基础知识，现在需要巩固和扩展。",
                "next": "以中等偏易的题目为主，偶尔挑战一下中等难度。"},
            5: {"name": "稳步前进", "description": "你处于中间水平，这是大多数学生的自然起点。",
                "next": "从难度5开始，根据表现自动调整。这是心流通道的最佳起点。"},
            7: {"name": "学有余力", "description": "你的基础扎实，可以应对较高难度的挑战。",
                "next": "以较难题为主，系统会自动检测是否需要巩固基础。"},
            9: {"name": "尖子水平", "description": "你已经掌握了大部分知识，可以进行高级拓展训练。",
                "next": "从高难度题目开始，系统会为你推送拓展和挑战内容。"},
        }
        # 找到最接近的级别
        levels = sorted(descriptions.keys())
        closest = min(levels, key=lambda l: abs(l - level))
        return descriptions[closest]

    @classmethod
    def _get_growth_potential(cls, level: int) -> str:
        if level <= 3:
            return "你的成长空间很大。从基础开始，每一点进步都会很明显。"
        elif level <= 6:
            return "你正处于学习的黄金区间。适中难度让你进步最快。"
        return "你已经有很好的基础。拓展和深化是接下来的方向。"

    @classmethod
    def _get_result_message(cls, level: int, accuracy: float) -> str:
        if accuracy > 0.8:
            return "你的表现很好！系统会把初始难度设置得稍高一些，让你保持在最佳学习区间。"
        elif accuracy > 0.5:
            return "这正是我们希望看到的——你在测试中遇到了适合和挑战的题目。系统已经确定了你的最佳起点。"
        return "测试中你遇到了一些挑战，这很正常。系统已经找到了适合你的初级难度，从这里开始，每一步都是进步。"


# ═══════════════════════════════════════════════════════════
# 2. 自适应题目选择器 — 根据水平测试结果匹配合适题目
# ═══════════════════════════════════════════════════════════

class AdaptiveQuestionSelector:
    """自适应题目选择器

    根据水平测试结果，从题库中选择第一组最适合的题目。
    """

    @classmethod
    def select_initial_questions(cls, placement_result: dict,
                                  available_count: int = 10) -> dict:
        """根据水平测试结果选择初始题目"""
        level = placement_result.get("estimated_level", 5)
        topic_difficulties = placement_result.get("topic_suggestions", {})

        selections = {}
        for topic, diff in topic_difficulties.items():
            # 每个topic分配题目
            count = max(1, available_count // len(topic_difficulties))
            selections[topic] = {
                "difficulty": diff,
                "difficulty_range": f"{max(1, diff-1)}-{min(10, diff+1)}",
                "count": count,
                "priority": "initial_batch",
            }

        return {
            "placement_level": level,
            "topic_selections": selections,
            "total_questions_queued": sum(s["count"] for s in selections.values()),
            "message": f"已根据你的水平测试结果准备了{sum(s['count'] for s in selections.values())}道入门题目。难度会根据你的表现实时调整。",
            "dda_enabled": True,
            "bkt_initialized": True,
        }


# ═══════════════════════════════════════════════════════════
# 3. 水平测试集成到新手引导
# ═══════════════════════════════════════════════════════════

class PlacementTestGuide:
    """水平测试引导

    将水平测试无缝集成到新手引导的第2步。
    """

    @classmethod
    def get_placement_guide_step(cls) -> dict:
        """获取水平测试的引导步骤信息"""
        return {
            "step_id": "placement_test",
            "title": "测试你的当前水平",
            "description": (
                "在正式开始学习之前，系统想了解你的当前水平。"
                "不是考试——没有分数，没有排名。"
                "这是为你量身定制学习路径的第一步。"
            ),
            "what_to_expect": [
                "8-12道自适应题目",
                "从中等难度开始，根据回答自动调整",
                "答错=系统找到适合你的难度",
                "整个过程约5-8分钟",
            ],
            "consent_message": "测试结果仅用于匹配最适合你的学习难度。你可以选择跳过。",
            "skip_option": "跳过测试，使用默认难度（Lv.5）",
            "skip_message": "如果跳过，系统会从难度5开始，通过答题逐渐找到你的真实水平。",
        }
