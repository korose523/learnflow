"""习惯化成瘾引擎 (Habit Addiction Engine)

将行为心理学与自我决定理论融入游戏化学习，促进可持续、健康、自主的学习习惯：
1. 习惯叠加 (Habit Stacking) — 把学习附加到已有习惯上
2. 诱惑捆绑 (Temptation Bundling) — 把学习与即时奖励绑定
3. 执行意图 (Implementation Intentions) — if-then 计划
4. 自主性支持 (Autonomy Support) — 选择、理由、认同
5. 自我调节 (Self-Regulation) — 目标、监控、反思

参考：
- Clear (2018) Atomic Habits
- Milkman et al. (2014) Temptation Bundling
- Gollwitzer (1999) Implementation Intentions
- Deci & Ryan (1985) Self-Determination Theory
- Zimmerman (2002) Self-Regulated Learning
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════
# 1. 习惯叠加引擎
# ═══════════════════════════════════════════════════════════

class HabitStackingEngine:
    """习惯叠加引擎：把新学习行为锚定到已有日常习惯"""

    COMMON_ANCHORS = [
        "早餐后",
        "午饭后",
        "晚饭后",
        "刷牙后",
        "洗澡后",
        "到校后",
        "放学回家后",
        "睡前",
    ]

    @staticmethod
    def suggest_stack(user_context: Dict[str, Any]) -> Dict[str, Any]:
        """根据用户日常习惯推荐学习叠加点"""
        anchors = HabitStackingEngine.COMMON_ANCHORS
        preferred = user_context.get("preferred_anchor")
        if preferred and preferred in anchors:
            anchor = preferred
        else:
            anchor = random.choice(anchors)
        return {
            "method": "习惯叠加",
            "anchor": anchor,
            "stack_plan": f"{anchor}，我会立即打开 LearnFlow 完成一个 5 分钟微会话。",
            "science": "习惯叠加利用已有行为线索作为新习惯的触发器，降低启动成本。",
            "action": "把这个计划写在便利贴上，贴在对应场景可见处。",
        }

    @staticmethod
    def build_routine_chain(anchors: List[str], micro_habit: str = "5分钟学习") -> Dict[str, Any]:
        """构建习惯链"""
        chain = []
        for i, anchor in enumerate(anchors):
            chain.append({
                "order": i + 1,
                "trigger": anchor,
                "behavior": micro_habit,
                "reward": "完成即可获得5 XP" if i == 0 else "连胜+1",
            })
        return {
            "method": "习惯链",
            "chain": chain,
            "tip": "从一个最容易的锚点开始，不要一次叠加太多。",
        }


# ═══════════════════════════════════════════════════════════
# 2. 诱惑捆绑引擎
# ═══════════════════════════════════════════════════════════

class TemptationBundlingEngine:
    """诱惑捆绑：把需要努力的学习与即时奖励绑定"""

    TEMPTATIONS = [
        "听一首喜欢的歌",
        "喝一杯奶茶/果汁",
        "看一集短视频",
        "玩一局小游戏",
        "和朋友聊 5 分钟",
    ]

    @staticmethod
    def suggest_bundle(user_context: Dict[str, Any]) -> Dict[str, Any]:
        """推荐诱惑捆绑方案"""
        favorite = user_context.get("favorite_reward")
        reward = favorite if favorite else random.choice(TemptationBundlingEngine.TEMPTATIONS)
        return {
            "method": "诱惑捆绑",
            "reward": reward,
            "rule": f"只有完成一个 25 分钟学习微会话，才能 {reward}。",
            "science": "Milkman et al. (2014): 诱惑捆绑可提升低享受活动的参与率。",
            "action": "现在就把奖励放在学习后，而不是学习前。",
        }


# ═══════════════════════════════════════════════════════════
# 3. 执行意图引擎
# ═══════════════════════════════════════════════════════════

class ImplementationIntentionsEngine:
    """执行意图引擎：生成 if-then 计划"""

    COMMON_SITUATIONS = [
        "感到不想学习时",
        "刷手机停不下来时",
        "作业很多想拖延时",
        "放学回家后",
        "周末早上醒来时",
    ]

    COMMON_RESPONSES = [
        "我会先打开 LearnFlow 做 3 道题，做完再决定要不要继续。",
        "我会把学习内容拆解成 5 分钟小任务，从最简单的一个开始。",
        "我会立即离开手机，坐到书桌前。",
        "我会先复习昨天的 5 个知识点，再开始新内容。",
    ]

    @staticmethod
    def generate_if_then(situation: Optional[str] = None, response: Optional[str] = None) -> Dict[str, Any]:
        """生成 if-then 计划"""
        if not situation:
            situation = random.choice(ImplementationIntentionsEngine.COMMON_SITUATIONS)
        if not response:
            response = random.choice(ImplementationIntentionsEngine.COMMON_RESPONSES)
        return {
            "method": "执行意图",
            "if": situation,
            "then": response,
            "plan": f"如果 {situation}，那么 {response}",
            "science": "Gollwitzer (1999): if-then 计划可把目标意图转化为自动化行为。",
            "action": "大声读三遍这个 if-then 计划，让它成为你的默认反应。",
        }

    @staticmethod
    def generate_setback_recovery_plan(trigger: str, fallback_action: str) -> Dict[str, Any]:
        """为可能的挫折生成恢复计划"""
        return {
            "method": "执行意图 - 挫折恢复",
            "if": trigger,
            "then": fallback_action,
            "plan": f"如果 {trigger}，那么 {fallback_action}",
            "message": "提前为失败做好心理预案，避免一次中断演变成放弃。",
        }


# ═══════════════════════════════════════════════════════════
# 4. 自主性支持引擎
# ═══════════════════════════════════════════════════════════

class AutonomySupportEngine:
    """自主性支持：满足自我决定理论中的自主需求"""

    @staticmethod
    def provide_choice(topic_options: List[str], max_choices: int = 3) -> Dict[str, Any]:
        """提供有限选择，增强自主感"""
        choices = topic_options[:max_choices]
        return {
            "method": "自主性支持",
            "choices": choices,
            "message": "你今天想从哪个主题开始？选择权在你。",
            "science": "Deci & Ryan: 自主性是内在动机的三大支柱之一。",
            "action": "从列表中选择一个，系统会据此生成学习路径。",
        }

    @staticmethod
    def explain_rationale(action: str, reason: str) -> Dict[str, Any]:
        """解释为什么推荐某个行动"""
        return {
            "method": "理由透明化",
            "action": action,
            "reason": reason,
            "message": f"我们推荐你 {action}，因为 {reason}",
            "science": "当学习者理解规则背后的意义时，服从会转化为认同。",
        }

    @staticmethod
    def acknowledge_feelings(barrier: str) -> Dict[str, Any]:
        """情感确认"""
        return {
            "method": "情感确认",
            "barrier": barrier,
            "message": f"感到 {barrier} 是正常的。很多学习者在这一点上都有类似感受。",
            "action": "承认这种情绪，然后只做 3 分钟试试看。",
            "science": "自我同情和情绪确认可降低逃避动机，促进重新投入。",
        }


# ═══════════════════════════════════════════════════════════
# 5. 自我调节引擎
# ═══════════════════════════════════════════════════════════

@dataclass
class SelfRegulationGoal:
    id: str
    user_id: str
    description: str
    target_value: float
    unit: str
    deadline: Optional[datetime] = None
    progress: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SelfRegulationEngine:
    """自我调节学习引擎：目标设定、监控、反思"""

    GOALS: Dict[str, List[SelfRegulationGoal]] = {}

    @classmethod
    def set_goal(cls, user_id: str, goal_id: str, description: str,
                 target_value: float, unit: str, deadline_days: Optional[int] = None) -> Dict[str, Any]:
        deadline = datetime.now(UTC) + timedelta(days=deadline_days) if deadline_days else None
        goal = SelfRegulationGoal(
            id=goal_id, user_id=user_id, description=description,
            target_value=target_value, unit=unit, deadline=deadline,
        )
        cls.GOALS.setdefault(user_id, []).append(goal)
        return {
            "method": "目标设定",
            "goal": {
                "id": goal.id,
                "description": goal.description,
                "target": f"{goal.target_value} {goal.unit}",
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
            },
            "tip": "目标要具体、可衡量、有期限。",
            "science": "Zimmerman: 目标设定是自我调节学习的起点。",
        }

    @classmethod
    def monitor_progress(cls, user_id: str, goal_id: str, current_value: float) -> Dict[str, Any]:
        """更新进度并反馈"""
        goals = cls.GOALS.get(user_id, [])
        goal = next((g for g in goals if g.id == goal_id), None)
        if not goal:
            return {"error": "目标不存在"}
        goal.progress = min(1.0, current_value / goal.target_value)
        remaining = goal.target_value - current_value
        return {
            "method": "进度监控",
            "goal_id": goal_id,
            "progress_pct": round(goal.progress * 100, 1),
            "remaining": max(0, remaining),
            "message": "进度已更新。继续加油！" if goal.progress < 1 else "目标达成！",
            "science": "自我监控可提升目标承诺和行为一致性。",
        }

    @classmethod
    def reflect_on_session(cls, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """会话后反思"""
        questions = [
            "今天的目标是什么？达成了吗？",
            "哪部分最困难？为什么？",
            "下次可以调整什么策略？",
            "今天最值得记住的一个知识点是什么？",
        ]
        return {
            "method": "反思",
            "questions": questions,
            "summary": {
                "duration_min": session_data.get("duration_min", 0),
                "questions_done": session_data.get("questions_done", 0),
                "accuracy": session_data.get("accuracy", 0),
            },
            "action": "用 2 分钟回答以上问题，写在反思日志中。",
            "science": "反思促进元认知和策略迁移，是自我调节学习的关键环节。",
        }


# ═══════════════════════════════════════════════════════════
# 6. 综合编排器
# ═══════════════════════════════════════════════════════════

class HabitAddictionOrchestrator:
    """习惯化成瘾编排器：为学习者生成一套完整的习惯培养方案"""

    @staticmethod
    def build_personal_habit_plan(user_context: Dict[str, Any]) -> Dict[str, Any]:
        """根据用户信息生成个人习惯计划"""
        stack = HabitStackingEngine.suggest_stack(user_context)
        bundle = TemptationBundlingEngine.suggest_bundle(user_context)
        if_then = ImplementationIntentionsEngine.generate_if_then()
        recovery = ImplementationIntentionsEngine.generate_setback_recovery_plan(
            trigger="连胜中断",
            fallback_action="我会把它当作新起点，当天只完成 1 个微会话。",
        )
        autonomy = AutonomySupportEngine.provide_choice(
            user_context.get("topic_options", ["数学", "英语", "科学"])
        )
        rationale = AutonomySupportEngine.explain_rationale(
            action="每天完成一个小目标",
            reason="小成功会积累成自我效能感，让学习从‘必须做’变成‘习惯做’。",
        )
        return {
            "method": "综合习惯培养方案",
            "stack": stack,
            "bundle": bundle,
            "if_then": if_then,
            "recovery": recovery,
            "autonomy": autonomy,
            "rationale": rationale,
            "message": "习惯不是依靠意志力，而是依靠设计好的环境、线索和奖励。",
        }
