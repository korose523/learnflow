"""微反馈服务：即时反馈生成与暗示/引导文案管理

核心原则：
- 多巴胺期待应指向"知识进步的可视化信号"，而非可兑换奖励
- 反馈延迟目标 ≤3秒（维持期待峰值）
- 所有暗示文案透明、可选、可关闭
- 重复成就的刺激逐步衰减，首次突破保持强反馈
"""
import logging
import random
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from app.services.learning_methods_engine import LearningMethodEngine

logger = logging.getLogger(__name__)


class FeedbackCategory(str, Enum):
    CORRECT = "correct"           # 答对
    INCORRECT = "incorrect"       # 答错
    ENCOURAGEMENT = "encouragement"  # 鼓励
    FLOW = "flow"                 # 心流维持
    REST = "rest"                 # 休息提醒
    IDENTITY = "identity"         # 身份强化
    ANTICIPATION = "anticipation"  # 前瞻期待
    RELAXATION = "relaxation"     # 放松引导


@dataclass
class FeedbackContext:
    """反馈生成上下文"""
    is_correct: bool
    student_name: str
    topic: str
    difficulty: int
    success_streak: int = 0       # 连续正确次数
    failure_streak: int = 0       # 连续错误次数
    total_attempts_today: int = 0
    learning_minutes_today: int = 0
    pet_name: str = "小豆"
    is_relaxation_mode: bool = False


# ─── 微反馈文案库 ─────────────────────────────────────────
# 基于文档方案设计，每条文案都有类别、版本标记

CORRECT_FEEDBACKS = [
    "✨ 思路很清晰！你正在强化{concept}的神经回路。",
    "🎯 答对了！这证明你对{concept}的理解又深了一层。",
    "💡 很好！这正是{concept}的核心思维。",
    "🌟 你的推理精准而有力，继续保持！",
    "🏆 {concept}掌握度 +1！你已经超越了昨天的自己。",
    "📈 又答对一题！你的能力曲线在稳步上升。",
]

INCORRECT_FEEDBACKS = [
    "🔍 不错的尝试！差一步，你的大脑现在正在学习如何避免这个错误。",
    "💪 这正是学习发生的时刻——从错误中成长。来看一下关键步骤？",
    "📝 好尝试！{concept}的这个细节很容易忽略。我们一起看看？",
    "🤔 思考方向是对的，只是{concept}的这一步需要调整。再试试？",
    "🌱 错误是最诚实的老师。你的大脑正在重新组织关于{concept}的知识。",
]

FLOW_FEEDBACKS = [
    "🎵 你现在正在心流通道中——难度刚好，状态正好。",
    "⚡ 完美的挑战节奏！大脑在高速学习。",
    "🌊 顺其自然，你正在最佳学习状态。",
    "🎯 难度匹配得刚刚好，这就是持续进步的感觉。",
]

ANTICIPATION_FEEDBACKS = [
    "下一题会让你接近{concept}的新理解水平。准备好了吗？",
    "你已经做过类似的题目并成功了，这次也能。",
    "接下来是一个小挑战——完成后你会感到自己在进步。",
    "深呼吸，下一个知识点正等着你去征服。",
]

IDENTITY_FEEDBACKS = [
    "你正在变成一个更全面的学习者。",
    "每一个小挑战都让你更强——这就是自我实现的样子。",
    "今天的选择和坚持，都在塑造一个更好的自己。",
    "你不是在做题，你是在构建自己的能力版图。",
]

REST_FEEDBACKS = [
    "感觉累了很正常。你的大脑现在在做最深层的整合工作。",
    "短暂的放松能帮助你更好地吸收知识。试试30秒深呼吸？",
    "放松的学习比紧张的学习效果更好。来，用学习本身放松一下。",
    "休息也是学习的一部分——让知识在脑海中安静沉淀。",
]

RELAXATION_GUIDES = [
    "花30秒，跟着呼吸放松。深呼吸，有节奏地吸气…呼气…这会让你更清晰地看见问题。你可以随时跳过。",
    "闭上眼睛，感受呼吸。吸气时想象知识流入，呼气时放下紧张。",
    "放松你的肩膀，松开紧握的手。学习不需要紧张，放松着学效果更好。",
]

# ─── 近战效应 (Near Miss) 反馈 ────────────────────
NEAR_MISS_FEEDBACKS = [
    "🌟 只差{reason}！你的思路完全正确，这是最高效的学习时刻。",
    "💡 几乎对了！{reason} 你的大脑正在建立正确的神经连接。",
    "🎯 {reason} 调整这一步，你就能完全掌握 {concept}！",
    "🔍 近在咫尺！{reason} 这一刻比全对更让 {pet_name} 兴奋。",
    "✨ 差之毫厘 —— {reason}。这就是学习的魔法时刻！",
]


class FeedbackService:
    """微反馈生成服务

    根据答题上下文和学习状态，从文案库中选择最合适的反馈。
    核心设计：
    - 把多巴胺期待指向"知识进步"而非物质奖励
    - 错误被重新框架为"学习机会"
    - 重复小成就反馈衰减
    """

    @classmethod
    def generate_task_feedback(cls, ctx: FeedbackContext) -> dict:
        """生成单题提交后的完整反馈包"""
        if ctx.is_correct:
            return cls._correct_feedback(ctx)
        else:
            return cls._incorrect_feedback(ctx)

    @classmethod
    def _correct_feedback(cls, ctx: FeedbackContext) -> dict:
        """答对反馈"""
        if ctx.success_streak >= 10:
            template = random.choice(CORRECT_FEEDBACKS[:3])
        elif ctx.success_streak == 0:
            template = random.choice(CORRECT_FEEDBACKS[3:])
        else:
            template = random.choice(CORRECT_FEEDBACKS)

        feedback_text = template.format(concept=ctx.topic)

        next_preview = ""
        if ctx.success_streak >= 2:
            next_preview = random.choice(ANTICIPATION_FEEDBACKS).format(concept=ctx.topic)

        # 学习方法提示
        method_tip = cls._get_learning_method_tip(ctx.topic, True)

        return {
            "type": "correct",
            "feedback_text": feedback_text,
            "next_preview": next_preview,
            "pet_reaction": "HAPPY" if ctx.success_streak < 5 else "CONFIDENT",
            "streak_badge": cls._get_streak_badge(ctx.success_streak),
            "learning_method_tip": method_tip,
        }

    @classmethod
    def _incorrect_feedback(cls, ctx: FeedbackContext) -> dict:
        """答错反馈 —— 重新框架为学习机会"""
        template = random.choice(INCORRECT_FEEDBACKS)
        feedback_text = template.format(concept=ctx.topic)

        recovery_options = [
            {"action": "watch_tutorial", "label": "看30秒讲解", "description": "理解关键步骤"},
            {"action": "retry", "label": "再试一次", "description": "题目略有变化"},
            {"action": "skip", "label": "跳过并标记", "description": "加入待突破清单"},
        ]

        method_tip = cls._get_learning_method_tip(ctx.topic, False)

        return {
            "type": "incorrect",
            "feedback_text": feedback_text,
            "recovery_options": recovery_options,
            "pet_reaction": "ENCOURAGING",
            "failure_streak": ctx.failure_streak,
            "encouragement": cls._get_encouragement(ctx.failure_streak),
            "learning_method_tip": method_tip,
        }

    @classmethod
    def generate_session_feedback(cls, ctx: FeedbackContext) -> str:
        """生成学习会话结束时的总结反馈"""
        if ctx.total_attempts_today >= 20:
            completions = [
                f"今天你完成了{ctx.total_attempts_today}道题，{ctx.pet_name}为你骄傲！",
                "每一次尝试都在塑造一个更强的你。",
            ]
        elif ctx.total_attempts_today >= 10:
            completions = [
                f"不错的进展！{ctx.total_attempts_today}道题的积累，{ctx.pet_name}看到了你的努力。",
                "坚持下去，进步会越来越明显。",
            ]
        else:
            completions = [
                f"今天完成了{ctx.total_attempts_today}道题，每一步都算数。",
                "学习不在于多，而在于每天都在前进。",
            ]
        return " ".join(completions)

    @classmethod
    def generate_rest_reminder(cls, learning_minutes: int) -> str:
        """生成休息提醒"""
        if learning_minutes >= 90:
            return "你已经连续学习90分钟了！{pet}也累了，一起休息10分钟吧。大脑需要这段时间来巩固今天学到的知识。"
        elif learning_minutes >= 60:
            return "已经学了一个小时，要不要站起来活动一下？短暂休息能让后续学习更高效。"
        return "感觉怎么样？如果想继续就继续，想休息就休息——都由你决定。"

    @classmethod
    def generate_relaxation_guide(cls) -> str:
        """生成放松引导文案（可选，需同意）"""
        return random.choice(RELAXATION_GUIDES)

    @classmethod
    def generate_identity_reinforcement(
        cls, student_name: str, weekly_progress: dict
    ) -> str:
        """生成周报身份强化文案"""
        lines = [
            f"本周，{student_name}，",
        ]
        if weekly_progress.get("understanding_delta", 0) > 0:
            lines.append(f"✓ 你的分析能力在进步")
        if weekly_progress.get("persistence_delta", 0) > 0:
            lines.append(f"✓ 你有毅力的品质在强化")
        if weekly_progress.get("creativity_delta", 0) > 0:
            lines.append(f"✓ 你的创造性思维在成长")
        if weekly_progress.get("collaboration_delta", 0) > 0:
            lines.append(f"✓ 你是一个乐于分享的人")
        lines.append("\n这些都是自我实现的标记。你正在变成你想成为的样子。")
        return "\n".join(lines)

    @classmethod
    def _get_streak_badge(cls, streak: int) -> Optional[str]:
        """根据连对次数获取徽章"""
        badges = {
            3: "🔥 三连对",
            5: "⭐ 五连对",
            10: "👑 十连对",
            20: "🏆 二十连对",
            50: "💎 五十连对",
        }
        for threshold, badge in sorted(badges.items(), reverse=True):
            if streak >= threshold:
                return badge
        return None

    @classmethod
    def _get_learning_method_tip(cls, topic: str, is_correct: bool) -> dict:
        """获取学习方法提示。

        缺陷修复：原实现在引擎抛异常时返回一个**与真实输出同形**的兜底字典
        ``{"method": "retrieval_practice", ...}``，不带任何标记。该字典会经
        ``build_feedback`` 与编排器直接作为 ``learning_method_tip`` 进入响应体
        与埋点快照。

        后果：学习方法推荐是本项目的**核心实验变量**之一。引擎故障时产生的
        兜底值会被静默混入真实推荐数据，且恒定偏向 ``retrieval_practice``，
        导致该方法的出现频率被系统性高估——而事后无法从数据本身分辨哪些是
        真推荐、哪些是故障兜底。

        现为兜底结果加 ``fallback: True`` 标记并记录日志，使其在数据分析阶段
        可被过滤或单独统计。字段集也与正常路径对齐（补 ``icon``/``action``
        为 None），避免下游因缺键而行为不一致。
        """
        try:
            tip = LearningMethodEngine.get_post_question_tip(topic, is_correct)
            return {
                "method": tip.get("method"),
                "title": tip.get("title"),
                "icon": tip.get("icon"),
                "short": tip.get("short"),
                "action": tip.get("action"),
                "fallback": False,
            }
        except Exception as exc:  # noqa: BLE001 —— 提示不应阻断反馈主流程
            logger.warning(
                "学习方法提示生成失败, 已降级为兜底值 (topic=%r, is_correct=%s): %s",
                topic, is_correct, exc,
            )
            return {
                "method": "retrieval_practice",
                "title": "检索练习",
                "icon": None,
                "short": "做题本身就是学习",
                "action": None,
                "fallback": True,
            }

    @classmethod
    def _get_encouragement(cls, failure_streak: int) -> str:
        """根据连续错误次数获取鼓励"""
        if failure_streak >= 5:
            return "你已经面对了5个困难——这在锻炼你的坚持力。要不要先休息一下，或者看看讲解？"
        elif failure_streak >= 3:
            return "连续遇到挑战说明题目在挑战你的边界——这是成长的信号。"
        return "每一次错误都在帮你找到进步的方向。"

    # ─── 近战效应 ──────────────────────────

    @classmethod
    def generate_near_miss_feedback(cls, reason: str, concept: str, pet_name: str = "小豆") -> dict:
        """生成近战效应反馈（答错但差一步时）"""
        template = random.choice(NEAR_MISS_FEEDBACKS)
        feedback_text = template.format(reason=reason, concept=concept, pet_name=pet_name)

        return {
            "type": "near_miss",
            "feedback_text": feedback_text,
            "pet_reaction": "CURIOUS",
            "recovery_options": [
                {"action": "retry", "label": "再试一次", "description": "你已经很接近了"},
                {"action": "watch_tutorial", "label": "看看关键步骤", "description": "就差这一步"},
            ],
            "near_miss_reason": reason,
        }

    # ─── 多巴胺节律 ────────────────────────

    @classmethod
    def generate_dopamine_rhythm(cls, is_correct: bool, is_near_miss: bool,
                                  topic: str, pet_name: str = "小豆",
                                  streak: int = 0) -> dict:
        """生成三段式多巴胺反馈节律"""
        if is_correct:
            return {
                "phase_1": {"duration_ms": 500, "animation": "sparkle", "sound": "correct_chime"},
                "phase_2": {"duration_ms": 1500, "pet_animation": "happy_dance" if streak >= 5 else "smile",
                            "message": f"{pet_name}为你骄傲！" if streak < 3 else f"{pet_name}兴奋地跳了起来！"},
                "phase_3": {"duration_ms": 1000, "animation": "anticipation_pulse",
                            "message": f"准备好了吗？下一题将检验你的 {topic} 能力"},
            }
        elif is_near_miss:
            return {
                "phase_1": {"duration_ms": 500, "animation": "near_miss_pulse", "sound": "soft_chime"},
                "phase_2": {"duration_ms": 1500, "pet_animation": "think",
                            "message": f"{pet_name}眼睛一亮：就差一点点！"},
                "phase_3": {"duration_ms": 1000, "animation": "encourage_glow",
                            "message": f"调整一下 {topic} 的思路，再试一次？"},
            }
        else:
            return {
                "phase_1": {"duration_ms": 500, "animation": "gentle_shake", "sound": "soft_tap"},
                "phase_2": {"duration_ms": 1500, "pet_animation": "encourage",
                            "message": f"{pet_name}轻轻拍了拍你的肩：没关系"},
                "phase_3": {"duration_ms": 1000, "animation": "explain_highlight",
                            "message": f"看看 {topic} 的关键步骤，你马上就能掌握！"},
            }
