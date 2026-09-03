"""游戏化激励服务

集成7大游戏化学习引擎:
1. 近战效应 (Near Miss) — 差一步反馈
2. 目标梯度 (Goal Gradient) — 越近越有动力
3. 变比率奖励 (Variable Ratio) — 惊喜宝箱
4. 多巴胺节律 (Dopamine Rhythm) — 三段式反馈
5. 禀赋效应 (Endowed Progress) — 预填进度
6. 损失厌恶 (Loss Aversion) — 打卡保护
7. 渐近性目标 (Proximal Goals) — 微/小/中/大

设计原则:
- 把多巴胺期待指向"知识进步"，而非物质奖励
- 所有奖励透明、可解释
- 游戏化服务于学习，而非学习为游戏服务
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.services.state_store import StateStore, MemoryStateStore


# ─── 奖励类型 ───────────────────────────────────────

class RewardType(str, Enum):
    KNOWLEDGE_PREVIEW = "knowledge_preview"   # 新知识点解锁预览
    PET_COSMETIC = "pet_cosmetic"             # 宠物表情/装饰
    DOUBLE_SCORE = "double_score"              # 下一题得分翻倍
    STREAK_SHIELD = "streak_shield"            # 打卡保护盾
    RELAXATION_CARD = "relaxation_card"        # 休息卡（免惩罚休息）
    THEME_UNLOCK = "theme_unlock"              # 主题解锁


# ─── 奖励池 ───────────────────────────────────────

TREASURE_REWARDS = {
    RewardType.KNOWLEDGE_PREVIEW: {
        "weight": 35,
        "icon": "📖",
        "title_templates": [
            "新知识大门打开！即将解锁：{topic}",
            "你的{pet_name}发现了一扇知识之门：{topic}",
            "下一站预告：{topic}！准备好了吗？",
        ],
    },
    RewardType.PET_COSMETIC: {
        "weight": 25,
        "icon": "🎀",
        "title_templates": [
            "{pet_name}获得了一个新表情！{emoji}",
            "宝箱里飞出了一个装饰！{emoji}",
            "{pet_name}学会了新动作！{emoji}",
        ],
        "cosmetics": ["🌟", "🎩", "🦋", "🔥", "💎", "🌈", "🎪", "👑"],
    },
    RewardType.DOUBLE_SCORE: {
        "weight": 15,
        "icon": "⚡",
        "title_templates": [
            "学习加速卡！下一题宠物成长翻倍",
            "双倍经验卡已激活！下一题效果 x2",
            "{pet_name}为你注入了双倍能量！",
        ],
    },
    RewardType.STREAK_SHIELD: {
        "weight": 10,
        "icon": "🛡️",
        "title_templates": [
            "打卡保护盾！明天不学也不会断签",
            "获得一张断签保护卡（下次生效）",
        ],
    },
    RewardType.RELAXATION_CARD: {
        "weight": 10,
        "icon": "☕",
        "title_templates": [
            "休息卡！随时可以休息10分钟，不算中断",
            "{pet_name}为你准备了休息礼券",
        ],
    },
    RewardType.THEME_UNLOCK: {
        "weight": 5,
        "icon": "🎨",
        "title_templates": [
            "新主题解锁！学习界面换了新皮肤",
            "你发现了一个隐藏主题！",
        ],
    },
}


# ─── 目标体系 ───────────────────────────────────────

@dataclass
class ProximalGoals:
    """渐近性目标状态"""
    # 微型目标: 每道题
    current_streak: int = 0
    best_streak: int = 0

    # 小目标: 每5题
    mini_goal_progress: int = 0     # 0-5
    mini_goals_completed: int = 0

    # 中目标: 每日
    daily_target: int = 10          # 每日目标题数
    daily_completed: int = 0
    daily_date: Optional[str] = None

    # 大目标: 每周
    weekly_target: int = 50
    weekly_completed: int = 0
    weekly_start_date: Optional[str] = None


@dataclass
class StreakState:
    """打卡状态"""
    current_streak: int = 0         # 连续学习天数
    best_streak: int = 0
    last_active_date: Optional[str] = None
    streak_shields: int = 0         # 保护盾数量
    shield_used_this_week: bool = False


@dataclass
class TreasureBoxState:
    """宝箱状态"""
    questions_since_last_box: int = 0
    next_box_at: int = 3           # 下次宝箱在第几题（随机）
    total_boxes_opened: int = 0
    rewards_collected: Dict[str, int] = field(default_factory=dict)
    active_double_score: bool = False  # 双倍经验卡是否激活


# ─── 近战效应检测 ───────────────────────────────────

class NearMissDetector:
    """检测答案是否属于"近战效应"范畴"""

    @staticmethod
    def is_near_miss(user_answer: str, correct_answer: str) -> Tuple[bool, str]:
        """判断是否差一步就对了

        Returns:
            (is_near_miss, reason)
        """
        ua = user_answer.strip().lower()
        ca = correct_answer.strip().lower()

        if ua == ca:
            return False, ""

        # 数值类: 差1-2个单位
        try:
            ua_num = float(ua)
            ca_num = float(ca)
            if abs(ua_num - ca_num) <= 2.0:
                return True, f"答案只差{abs(ua_num - ca_num)}，非常接近了！"
            # 数值差太大，不是近战效应
            return False, ""
        except (ValueError, TypeError):
            pass

        # 分数类: 分子分母调换
        if "/" in ua and "/" in ca:
            try:
                un, ud = ua.split("/")
                cn, cd = ca.split("/")
                if un.strip() == cd.strip() and ud.strip() == cn.strip():
                    return True, "你交换了分子和分母，差一步！"
            except (ValueError, TypeError):
                pass

        # 字符串类: 差一个字符
        if len(ua) > 0 and len(ca) > 0:
            if abs(len(ua) - len(ca)) <= 2:
                # 检查字符差异
                if len(ua) == len(ca):
                    diff_count = sum(1 for a, b in zip(ua, ca) if a != b)
                    if diff_count == 1:
                        return True, "只差一个字符，思路完全正确！"
                elif abs(len(ua) - len(ca)) == 1:
                    # 差一个字符（如 "4" vs "x=4"）
                    shorter = ua if len(ua) < len(ca) else ca
                    longer = ca if len(ua) < len(ca) else ua
                    if shorter in longer:
                        return True, "答案的核心部分是正确的，差一步！"

        return False, ""


# ─── 游戏化激励服务 ──────────────────────────────────

class GamificationService:
    """游戏化激励总服务

    整合所有7大引擎的后端逻辑。
    """

    # 宝箱状态容器 —— 迁移到可插拔 StateStore 后端 (LF-M01 示范)
    # 默认 MemoryStateStore 与改造前行为一致；生产可注入 JSONFileStateStore / SQL。
    BOX_STATES: StateStore = MemoryStateStore()

    @classmethod
    def get_box_state_for_user(cls, user_id: str) -> TreasureBoxState:
        state = cls.BOX_STATES.get(user_id)
        if state is None:
            state = TreasureBoxState()
            cls.BOX_STATES.set(user_id, state)
        return state

    @classmethod
    def open_box_for_user(cls, user_id: str, pet_name: str = "小豆", current_topic: str = "") -> dict:
        state = cls.get_box_state_for_user(user_id)
        return cls.open_box(state, pet_name=pet_name, current_topic=current_topic)

    @classmethod
    def get_box_status_for_user(cls, user_id: str) -> dict:
        state = cls.get_box_state_for_user(user_id)
        return {
            "questions_since_last_box": state.questions_since_last_box,
            "next_box_at": state.next_box_at,
            "total_boxes_opened": state.total_boxes_opened,
            "active_double_score": state.active_double_score,
            "rewards_collected": state.rewards_collected,
        }

    # ─── 1. 变比率宝箱 ─────────────────────

    @staticmethod
    def should_open_box(state: TreasureBoxState) -> bool:
        """判断是否该开宝箱"""
        state.questions_since_last_box += 1
        if state.questions_since_last_box >= state.next_box_at:
            return True
        return False

    @staticmethod
    def open_box(
        state: TreasureBoxState,
        pet_name: str = "小豆",
        current_topic: str = "",
    ) -> dict:
        """开宝箱！返回随机奖励

        概率分布:
        - 70%: 知识预览 / 宠物装饰
        - 20%: 双倍经验卡
        - 10%: 保护盾 / 休息卡 / 主题
        """
        # 选择奖励类型（按权重）
        _, reward_type = GamificationService._weighted_choice(TREASURE_REWARDS)
        reward_config = TREASURE_REWARDS[reward_type]

        # 生成奖励内容
        title_template = random.choice(reward_config["title_templates"])

        if reward_type == RewardType.PET_COSMETIC:
            cosmetic = random.choice(reward_config["cosmetics"])
            title = title_template.format(pet_name=pet_name, emoji=cosmetic)
            data = {"cosmetic": cosmetic}
        elif reward_type == RewardType.KNOWLEDGE_PREVIEW:
            title = title_template.format(pet_name=pet_name, topic=current_topic or "新知识")
            data = {"topic": current_topic}
        else:
            title = title_template.format(pet_name=pet_name)
            data = {}

        # 更新状态
        state.questions_since_last_box = 0
        state.next_box_at = random.randint(3, 10)  # 3-10题后下次宝箱
        state.total_boxes_opened += 1
        state.rewards_collected[reward_type.value] = (
            state.rewards_collected.get(reward_type.value, 0) + 1
        )

        if reward_type == RewardType.DOUBLE_SCORE:
            state.active_double_score = True

        return {
            "type": reward_type.value,
            "icon": reward_config["icon"],
            "title": title,
            "data": data,
            "boxes_opened": state.total_boxes_opened,
            "next_box_in": state.next_box_at,
        }

    # ─── 2. 目标梯度 ────────────────────────

    @staticmethod
    def get_goal_progress(goals: ProximalGoals) -> dict:
        """获取目标进度（用于前端脉冲动画）"""
        daily_pct = min(100, round(goals.daily_completed / max(goals.daily_target, 1) * 100))
        weekly_pct = min(100, round(goals.weekly_completed / max(goals.weekly_target, 1) * 100))
        mini_pct = min(100, round(goals.mini_goal_progress / 5 * 100))

        return {
            "daily": {"completed": goals.daily_completed, "target": goals.daily_target, "pct": daily_pct},
            "weekly": {"completed": goals.weekly_completed, "target": goals.weekly_target, "pct": weekly_pct},
            "mini": {"progress": goals.mini_goal_progress, "target": 5, "pct": mini_pct},
            # 接近完成时触发脉冲（>80%）
            "pulse_daily": daily_pct >= 80 and daily_pct < 100,
            "pulse_weekly": weekly_pct >= 80 and weekly_pct < 100,
            "pulse_mini": mini_pct >= 80 and mini_pct < 100,
        }

    @staticmethod
    def record_question_completion(goals: ProximalGoals):
        """记录一题完成，更新所有目标"""
        goals.current_streak += 1
        goals.best_streak = max(goals.best_streak, goals.current_streak)

        # 小目标 (每5题)
        goals.mini_goal_progress += 1
        mini_completed = False
        if goals.mini_goal_progress >= 5:
            goals.mini_goals_completed += 1
            goals.mini_goal_progress = 0
            mini_completed = True

        # 中目标 (每日)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if goals.daily_date != today:
            goals.daily_date = today
            goals.daily_completed = 0
        goals.daily_completed += 1
        daily_completed = goals.daily_completed >= goals.daily_target

        # 大目标 (每周)
        if goals.weekly_start_date is None:
            goals.weekly_start_date = today
        weekly_date = datetime.strptime(goals.weekly_start_date, "%Y-%m-%d")
        if (datetime.now(UTC) - weekly_date.replace(tzinfo=UTC)).days >= 7:
            goals.weekly_completed = 0
            goals.weekly_start_date = today
        goals.weekly_completed += 1

        return {
            "mini_completed": mini_completed,
            "daily_completed": daily_completed,
            "streak_badge": GamificationService._get_proximal_badge(goals.mini_goals_completed),
        }

    # ─── 3. 禀赋效应 ────────────────────────

    @staticmethod
    def get_endowed_progress(goals: ProximalGoals) -> dict:
        """获取禀赋效应数据（每周一赠送2题）"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        is_monday = datetime.now(UTC).weekday() == 0

        if goals.weekly_start_date is None or goals.weekly_start_date != today:
            if is_monday:
                # 周一：赠送2题
                goals.weekly_completed = 2
                goals.weekly_start_date = today
                return {
                    "gifted": True,
                    "gifted_amount": 2,
                    "message": "新的一周！系统已为你点亮前2题，好的开始！",
                    "weekly_completed": 2,
                    "weekly_target": goals.weekly_target,
                }

        return {
            "gifted": False,
            "gifted_amount": 0,
            "message": "",
            "weekly_completed": goals.weekly_completed,
            "weekly_target": goals.weekly_target,
        }

    # ─── 4. 损失厌恶 ────────────────────────

    @staticmethod
    def update_streak(streak: StreakState) -> dict:
        """更新学习打卡状态"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if streak.last_active_date == today:
            return {"streak": streak.current_streak, "changed": False, "message": ""}

        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

        if streak.last_active_date == yesterday:
            # 连续打卡
            streak.current_streak += 1
            streak.best_streak = max(streak.best_streak, streak.current_streak)
            streak.last_active_date = today
            changed = True

            if streak.current_streak >= 3:
                message = f"🔥 已经连续学习 {streak.current_streak} 天了，明天断了就会归零哦！"
            else:
                message = f"连续学习 {streak.current_streak} 天"
        else:
            # 断签
            if streak.streak_shields > 0 and streak.current_streak > 0:
                # 使用保护盾
                streak.streak_shields -= 1
                streak.shield_used_this_week = True
                streak.current_streak += 1
                streak.last_active_date = today
                changed = True
                message = f"🛡️ 打卡保护盾生效！连续学习 {streak.current_streak} 天"
            else:
                old_streak = streak.current_streak
                streak.current_streak = 1
                streak.last_active_date = today
                changed = True
                if old_streak >= 3:
                    message = f"断签了… 之前坚持了 {old_streak} 天，重新开始吧！"
                else:
                    message = "新的一天，开始学习吧！"

        streak.shield_used_this_week = False  # 每周重置
        return {"streak": streak.current_streak, "best": streak.best_streak, "changed": changed, "message": message}

    @staticmethod
    def get_loss_aversion_nudge(streak: StreakState) -> Optional[str]:
        """获取损失厌恶提示语"""
        if streak.current_streak >= 3:
            return f"你已经连续学习 {streak.current_streak} 天了，明天如果不学习，天数将重置为0"
        return None

    # ─── 5. 渐近性目标 ─────────────────────

    @staticmethod
    def _get_proximal_badge(mini_completed: int) -> Optional[str]:
        """根据小微目标完成数获取徽章"""
        badges = {
            1: "⭐ 首个5题组",
            3: "🌟 3组达成",
            5: "💫 5组达成",
            10: "👑 10组达成",
            20: "🏆 20组霸主",
        }
        for threshold, badge in sorted(badges.items(), reverse=True):
            if mini_completed >= threshold:
                return badge
        return None

    # ─── 辅助方法 ──────────────────────────

    @staticmethod
    def _weighted_choice(items: dict) -> Tuple[float, any]:
        """按权重随机选择"""
        total = sum(v["weight"] for v in items.values())
        r = random.uniform(0, total)
        cumulative = 0
        for key, config in items.items():
            cumulative += config["weight"]
            if r <= cumulative:
                return cumulative, key
        return total, list(items.keys())[-1]


# ─── 多巴胺节律反馈结构 ──────────────────────────────

@dataclass
class DopamineRhythm:
    """多巴胺节律 — 三段式反馈"""
    phase_1: str  # 0-0.5s 判定动画
    phase_2: str  # 0.5-2s 宠物反应 + 反馈文案
    phase_3: str  # 2-3s 下一题预告

    @staticmethod
    def for_correct(topic: str, pet_name: str, streak: int) -> "DopamineRhythm":
        """答对时的节律"""
        return DopamineRhythm(
            phase_1="correct_sparkle",  # 前端播放闪光动画
            phase_2=f"{pet_name}为你骄傲！" if streak < 3 else f"{pet_name}兴奋地跳了起来！",
            phase_3=f"下一题将检验你的 {topic} 能力，准备好了吗？",
        )

    @staticmethod
    def for_incorrect(topic: str, pet_name: str, is_near_miss: bool) -> "DopamineRhythm":
        """答错时的节律"""
        if is_near_miss:
            return DopamineRhythm(
                phase_1="near_miss_pulse",
                phase_2=f"{pet_name}眼睛一亮：差一点点！",
                phase_3=f"调整一下 {topic} 的思路，再试一次？",
            )
        return DopamineRhythm(
            phase_1="gentle_shake",
            phase_2=f"{pet_name}轻轻拍了拍你的肩",
            phase_3=f"让我们看看 {topic} 的关键步骤，你马上就能掌握！",
        )


# ═══════════════════════════════════════════════════
# 第二波游戏化引擎 — 峰终/蔡格尼克/宜家/社会认同/自主
# ═══════════════════════════════════════════════════

# ─── 8. 峰终定律 (Peak-End Rule) ────────────────

@dataclass
class SessionMemory:
    session_start: datetime
    peak_positive: Optional[str] = None
    peak_positive_score: float = 0.0
    peak_difficult: Optional[str] = None
    total_correct: int = 0
    total_attempts: int = 0


class PeakEndEngine:
    _active_sessions: Dict[str, SessionMemory] = {}

    @classmethod
    def start_session(cls, user_id: str) -> SessionMemory:
        mem = SessionMemory(session_start=datetime.now(UTC))
        cls._active_sessions[user_id] = mem
        return mem

    @classmethod
    def record_answer(cls, user_id: str, is_correct: bool, topic: str,
                       difficulty: int, streak: int, pet_name: str = "小豆"):
        mem = cls._active_sessions.get(user_id)
        if not mem:
            return
        mem.total_attempts += 1
        if is_correct:
            mem.total_correct += 1
        if is_correct and difficulty >= 7:
            score = difficulty + streak * 0.5
            if score > mem.peak_positive_score:
                mem.peak_positive_score = score
                mem.peak_positive = f"在难度{difficulty}的{topic}上连对{streak}题"
        if is_correct and streak >= 5:
            score = streak * 2
            if score > mem.peak_positive_score:
                mem.peak_positive_score = score
                mem.peak_positive = f"连续答对{streak}题，{pet_name}为你欢呼！"

    @classmethod
    def end_session(cls, user_id: str, pet_name: str = "小豆") -> dict:
        mem = cls._active_sessions.pop(user_id, None)
        if not mem or mem.total_attempts == 0:
            return {"has_session": False}
        accuracy = round(mem.total_correct / max(mem.total_attempts, 1) * 100)
        if accuracy >= 80:
            end_feeling, end_msg = "太棒了", f"{pet_name}为你今天骄傲！正确率{accuracy}%。"
        elif accuracy >= 50:
            end_feeling, end_msg = "不错", f"正确率{accuracy}%，{pet_name}看到了你的努力。"
        else:
            end_feeling, end_msg = "有挑战", f"每次错误都是进步的阶梯。{pet_name}明天继续陪你！"
        return {
            "has_session": True, "total_attempts": mem.total_attempts,
            "total_correct": mem.total_correct, "accuracy": accuracy,
            "peak_moment": mem.peak_positive or "认真完成了每一道题",
            "peak_score": mem.peak_positive_score,
            "end_feeling": end_feeling, "end_message": end_msg,
            "highlight": f"🏆 高光时刻: {mem.peak_positive}" if mem.peak_positive else "💪 坚持完成了学习任务",
        }


# ─── 9. 蔡格尼克效应 (Zeigarnik) ──────────────

@dataclass
class UnfinishedTask:
    task_id: str
    topic: str
    difficulty: int
    started_at: datetime
    reason: str = "session_ended"
    reminder_count: int = 0
    last_reminded_at: Optional[datetime] = None

    def should_remind(self) -> bool:
        if self.reminder_count >= 3:
            return False
        if self.last_reminded_at:
            return (datetime.now(UTC) - self.last_reminded_at).total_seconds() / 3600 >= 6
        return True


class ZeigarnikEngine:
    _unfinished: Dict[str, UnfinishedTask] = {}

    @classmethod
    def save_unfinished(cls, user_id: str, task_id: str, topic: str,
                         difficulty: int, reason: str = "session_ended"):
        existing = cls._unfinished.get(user_id)
        if existing and existing.task_id == task_id:
            return
        cls._unfinished[user_id] = UnfinishedTask(
            task_id=task_id, topic=topic, difficulty=difficulty,
            started_at=datetime.now(UTC), reason=reason)

    @classmethod
    def get_reminder(cls, user_id: str, pet_name: str = "小豆") -> Optional[dict]:
        task = cls._unfinished.get(user_id)
        if not task or not task.should_remind():
            return None
        task.reminder_count += 1
        task.last_reminded_at = datetime.now(UTC)
        return {
            "has_unfinished": True, "topic": task.topic,
            "difficulty": task.difficulty, "task_id": task.task_id,
            "message": f"上次 {task.topic} 的那道题还没做完…{pet_name}一直惦记着。要继续吗？",
            "action": "continue_unfinished",
        }

    @classmethod
    def clear_unfinished(cls, user_id: str, task_id: str):
        existing = cls._unfinished.get(user_id)
        if existing and existing.task_id == task_id:
            del cls._unfinished[user_id]


# ─── 10. 宜家效应 (IKEA Effect) ───────────────

@dataclass
class CustomizationState:
    pet_name_customized: bool = False
    learning_goal_set: bool = False
    daily_target_custom: Optional[int] = None
    theme_selected: str = "default"
    custom_paths_created: int = 0


class IKEAEngine:
    @classmethod
    def customize_pet_name(cls, old_name: str, new_name: str) -> dict:
        return {
            "message": f"你为学习伙伴取名为「{new_name}」！{new_name}将陪你一起成长。",
            "ownership_bonus": True,
        }

    @classmethod
    def set_personal_goal(cls, daily_target: int) -> dict:
        return {
            "daily_target": daily_target,
            "message": f"你自己设定了每天{daily_target}题的目标！这是你自己的承诺。",
            "commitment_nudge": "自己设定的目标完成率高出40%。",
        }

    @classmethod
    def get_ownership_summary(cls, state: CustomizationState) -> dict:
        score = 0
        details = []
        if state.pet_name_customized:
            score += 25; details.append("为宠物取了名字")
        if state.learning_goal_set:
            score += 25; details.append("设定了自己的学习目标")
        if state.daily_target_custom:
            score += 20; details.append("自定义了每日题数")
        if state.theme_selected != "default":
            score += 15; details.append("选择了学习主题")
        if state.custom_paths_created > 0:
            score += 15; details.append(f"创建了{state.custom_paths_created}个学习路径")
        return {"ownership_score": score, "details": details,
                "level": "creator" if score >= 70 else "customizer" if score >= 35 else "explorer"}


# ─── 11. 社会认同 (Social Proof) ──────────────

class SocialProofEngine:
    @classmethod
    def get_class_mastery_nudge(cls, skill_dim: str, class_pct: float, user_pct: float) -> dict:
        if class_pct > 60 and user_pct < class_pct - 10:
            return {"type": "encourage", "message": f"班级 {class_pct:.0f}% 的同学已掌握 {skill_dim}，你也能！"}
        elif user_pct > class_pct + 10:
            return {"type": "pride", "message": f"你在 {skill_dim} 领先班级！要不要帮助其他同学？"}
        return {"type": "none", "message": ""}

    @classmethod
    def get_active_learners_nudge(cls, active_count: int) -> dict:
        if active_count >= 5:
            return {"show": True, "message": f"现在{active_count}位同学和你一起学习"}
        return {"show": False, "message": ""}

    @classmethod
    def get_help_prompt(cls, skill_dim: str, help_count: int) -> dict:
        if help_count == 0:
            return {"message": f"有同学在 {skill_dim} 上卡住了，你的提示可能帮大忙。", "action": "offer_help"}
        return {"message": f"你已帮了{help_count}位同学！教学相长。", "action": "continue"}


# ─── 12. 自主支持 (Autonomy Support) ──────────

class AutonomyEngine:
    RATIONALES = {
        "rest": "休息是学习的一部分。大脑在休息时整合知识效率最高。",
        "difficulty_down": "降低难度是为了让你在最佳心流状态学习。这是高效学习的关键。",
        "night_block": "好的睡眠让知识在脑海中扎根，明天你会理解得更深。",
    }

    @classmethod
    def offer_choice(cls, choice_type: str) -> dict:
        choices = {
            "difficulty": {
                "title": "选择你的挑战级别",
                "options": [
                    {"value": "comfort", "label": "舒适模式", "desc": "巩固基础"},
                    {"value": "balanced", "label": "平衡模式（推荐）", "desc": "心流体验"},
                    {"value": "challenge", "label": "挑战模式", "desc": "突破自我"},
                ],
            },
            "session_goal": {
                "title": "今天想完成多少题？",
                "options": [
                    {"value": "5", "label": "快速5题", "desc": "约10分钟"},
                    {"value": "10", "label": "标准10题", "desc": "约20分钟"},
                    {"value": "20", "label": "加练20题", "desc": "约40分钟"},
                    {"value": "free", "label": "不限数量", "desc": "学够为止"},
                ],
            },
        }
        template = choices.get(choice_type, {})
        return {"choice_type": choice_type, **template,
                "autonomy_msg": "选择权在你。自主选择提高40%的学习效果。"}

    @classmethod
    def provide_rationale(cls, requirement: str) -> str:
        return cls.RATIONALES.get(requirement, "这是为了让你学得更好、更长久。")
