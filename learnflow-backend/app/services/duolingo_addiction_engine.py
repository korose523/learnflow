"""多邻国式学习成瘾系统 — Duolingo-Inspired Addiction Layer

深度学习多邻国(Duolingo)的成瘾设计:
1. 连胜 + 连胜保护 (Streak + Freeze)
2. XP系统 + 双倍经验卡 (XP Boost)
3. 联赛排行榜 (League + Leaderboard)
4. 好友任务 (Friend Quests)
5. 早晨/晚间双倍 (Early Bird / Night Owl)
6. 连胜社团 (Streak Society)
7. 被动攻击式提醒 (Passive-Aggressive Reminders)
8. 经验目标选择器 (XP Goal Selector)
9. 宝箱解锁倒计时 (Timed Chest Unlock)
10. 月度挑战 (Monthly Challenge)

设计哲学:
  多邻国 = 连胜 × 社交 × 倒计时 × 排行榜 × 被动攻击
  每一步都在说"你确定今天不学？"
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random

from app.services.state_store import StateStore, MemoryStateStore


# ═══════════════════════════════════════════════════════════
# 1. XP 系统 — 经验引擎
# ═══════════════════════════════════════════════════════════

class XPEventType(str, Enum):
    LESSON_COMPLETE = "lesson_complete"
    PERFECT_LESSON = "perfect_lesson"      # 全对
    HARD_CORRECT = "hard_correct"           # 高难度答对
    STREAK_BONUS = "streak_bonus"          # 连续奖励
    FRIEND_QUEST = "friend_quest"           # 好友任务
    WEEKLY_TOP3 = "weekly_top3"            # 周排行前三
    EARLY_BIRD = "early_bird"              # 早晨学习
    NIGHT_OWL = "night_owl"                # 晚间学习
    COMEBACK = "comeback"                  # 断签后回归


@dataclass
class XPState:
    """经验状态"""
    total_xp: int = 0
    weekly_xp: int = 0
    today_xp: int = 0
    current_boost_multiplier: float = 1.0
    boost_remaining_minutes: int = 0
    boosts_available: int = 3                # 可用双倍经验卡
    xp_level: int = 1
    xp_to_next_level: int = 100


class XPEngine:
    """经验引擎

    多邻国的核心: 每道题 = XP, XP = 排行榜排名, 排名 = 社交压力。
    """

    XP_REWARDS = {
        XPEventType.LESSON_COMPLETE: {"base": 10, "message": "+10 XP"},
        XPEventType.PERFECT_LESSON: {"base": 15, "bonus": 5, "message": "完美！+20 XP"},
        XPEventType.HARD_CORRECT: {"base": 12, "bonus": 8, "message": "高难度！+20 XP"},
        XPEventType.STREAK_BONUS: {"base": 0, "bonus_factor": 2, "message": "连胜加成！"},
        XPEventType.FRIEND_QUEST: {"base": 30, "message": "好友任务完成 +30 XP"},
        XPEventType.WEEKLY_TOP3: {"base": 50, "message": "周榜前三 +50 XP"},
        XPEventType.EARLY_BIRD: {"base": 15, "message": "早起学习者 +15 XP"},
        XPEventType.NIGHT_OWL: {"base": 10, "message": "晚间坚持 +10 XP"},
        XPEventType.COMEBACK: {"base": 5, "bonus": 10, "message": "回归奖励 +15 XP"},
    }

    @classmethod
    def award_xp(cls, state: XPState, event_type: XPEventType,
                  streak: int = 0) -> dict:
        """授予经验"""
        reward = cls.XP_REWARDS.get(event_type, cls.XP_REWARDS[XPEventType.LESSON_COMPLETE])
        xp = reward.get("base", 10) + reward.get("bonus", 0)

        # 连胜加成: 每3天+1 XP
        streak_bonus = min(streak // 3, 10)
        xp += streak_bonus

        # 双倍经验卡
        if state.boost_remaining_minutes > 0:
            xp *= 2

        xp = int(xp * state.current_boost_multiplier)

        state.total_xp += xp
        state.weekly_xp += xp
        state.today_xp += xp

        # 升级检查
        leveled_up = False
        while state.total_xp >= state.xp_to_next_level:
            state.xp_level += 1
            state.xp_to_next_level = int(state.xp_to_next_level * 1.5)
            leveled_up = True

        return {
            "xp_earned": xp,
            "total_xp": state.total_xp,
            "today_xp": state.today_xp,
            "weekly_xp": state.weekly_xp,
            "message": reward["message"].replace(str(reward.get("base", 10)), str(xp)),
            "leveled_up": leveled_up,
            "new_level": state.xp_level if leveled_up else None,
            "has_boost": state.boost_remaining_minutes > 0,
        }

    @classmethod
    def activate_boost(cls, state: XPState, duration_min: int = 15) -> dict:
        """激活双倍经验卡"""
        if state.boosts_available <= 0:
            return {"activated": False, "message": "没有可用的经验卡了！完成更多学习来获取。"}

        state.boosts_available -= 1
        state.boost_remaining_minutes = duration_min
        state.current_boost_multiplier = 2.0

        return {
            "activated": True,
            "duration_minutes": duration_min,
            "multiplier": 2.0,
            "message": f"双倍经验卡已激活！接下来的{duration_min}分钟内，所有经验翻倍！",
            "boosts_remaining": state.boosts_available,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=duration_min)).isoformat(),
        }

    @classmethod
    def tick_boost(cls, state: XPState):
        """每分钟调用 — 减少boost倒计时"""
        if state.boost_remaining_minutes > 0:
            state.boost_remaining_minutes -= 1
        if state.boost_remaining_minutes <= 0:
            state.current_boost_multiplier = 1.0

    @classmethod
    def get_xp_summary(cls, state: XPState) -> dict:
        return {
            "level": state.xp_level,
            "total_xp": state.total_xp,
            "xp_to_next": max(0, state.xp_to_next_level - state.total_xp),
            "progress_pct": round(state.total_xp / max(state.xp_to_next_level, 1) * 100, 1),
            "today_xp": state.today_xp,
            "weekly_xp": state.weekly_xp,
            "boosts_available": state.boosts_available,
            "boost_active": state.boost_remaining_minutes > 0,
        }

    @classmethod
    def _event_for_attempt(cls, attempt) -> XPEventType:
        if attempt.is_correct and getattr(attempt, "hints_used", 0) == 0:
            return XPEventType.PERFECT_LESSON
        if attempt.is_correct and (getattr(attempt, "difficulty_at_time", 0) or 0) >= 7:
            return XPEventType.HARD_CORRECT
        return XPEventType.LESSON_COMPLETE

    @classmethod
    def build_state_from_attempts(cls, attempts: list) -> XPState:
        state = XPState()
        streak = 0
        sorted_attempts = sorted(
            attempts,
            key=lambda a: getattr(a, "created_at", datetime.min) or datetime.min,
        )
        for attempt in sorted_attempts:
            if attempt.is_correct:
                streak += 1
            else:
                streak = 0
            event = cls._event_for_attempt(attempt)
            cls.award_xp(state, event, streak=streak)
        return state


# ═══════════════════════════════════════════════════════════
# 2. 联赛排行榜 — League System
# ═══════════════════════════════════════════════════════════

class LeagueTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    SAPPHIRE = "sapphire"
    RUBY = "ruby"
    EMERALD = "emerald"
    AMETHYST = "amethyst"
    PEARL = "pearl"
    OBSIDIAN = "obsidian"
    DIAMOND = "diamond"


@dataclass
class LeagueState:
    """联赛状态"""
    current_tier: LeagueTier = LeagueTier.BRONZE
    tier_progress_pct: float = 0.0   # 在当前级别中的进度
    weeks_in_current_tier: int = 0
    highest_tier_ever: LeagueTier = LeagueTier.BRONZE
    promotion_count: int = 0
    demotion_count: int = 0
    top3_finishes: int = 0
    tournament_wins: int = 0


class LeagueEngine:
    """联赛引擎

    多邻国的排行榜不是比较"谁更聪明"，而是比较"谁更坚持"。
    每周重置 XP → 每个人都有机会。
    """

    # 每个级别: (升级所需进度%, 降级线%)
    TIER_RULES = {
        LeagueTier.BRONZE:   ({"promote_top": 10, "demote_bottom": 0, "group_size": 10}),
        LeagueTier.SILVER:   ({"promote_top": 10, "demote_bottom": 0, "group_size": 10}),
        LeagueTier.GOLD:     ({"promote_top": 7, "demote_bottom": 0, "group_size": 10}),
        LeagueTier.SAPPHIRE: ({"promote_top": 7, "demote_bottom": 0, "group_size": 10}),
        LeagueTier.RUBY:     ({"promote_top": 5, "demote_bottom": 20, "group_size": 10}),
        LeagueTier.EMERALD:  ({"promote_top": 5, "demote_bottom": 20, "group_size": 10}),
        LeagueTier.AMETHYST: ({"promote_top": 5, "demote_bottom": 20, "group_size": 10}),
        LeagueTier.PEARL:    ({"promote_top": 5, "demote_bottom": 15, "group_size": 10}),
        LeagueTier.OBSIDIAN: ({"promote_top": 5, "demote_bottom": 15, "group_size": 10}),
        LeagueTier.DIAMOND:  ({"promote_top": 0, "demote_bottom": 20, "group_size": 30}),
    }

    @classmethod
    def get_league_standings(cls, user_id: str, weekly_xp: int,
                              all_users_xp: List[Tuple[str, str, int]]) -> dict:
        """获取联赛排名 — 只显示同组人员"""
        sorted_users = sorted(all_users_xp, key=lambda x: x[2], reverse=True)
        user_rank = next((i+1 for i, u in enumerate(sorted_users) if u[0] == user_id), len(sorted_users))

        return {
            "user_rank": user_rank,
            "total_in_league": len(sorted_users),
            "top3": [{"name": u[1], "xp": u[2]} for u in sorted_users[:3]],
            "nearby": [
                {"name": u[1], "xp": u[2], "is_you": u[0] == user_id}
                for u in sorted_users[max(0, user_rank-3):user_rank+2]
            ],
            "xp_to_next_rank": (sorted_users[user_rank-2][2] - weekly_xp) if user_rank > 1 else 0,
            "message": cls._get_ranking_message(user_rank, len(sorted_users)),
        }

    @classmethod
    def process_weekly_promotion(cls, state: LeagueState, rank: int,
                                  total: int) -> dict:
        """处理每周升降级"""
        rules = cls.TIER_RULES.get(state.current_tier, {"promote_top": 5, "demote_bottom": 20, "group_size": 10})
        promote_cutoff = max(1, int(total * rules["promote_top"] / 100))
        demote_cutoff = max(total - int(total * rules["demote_bottom"] / 100), total)

        result = {"promoted": False, "demoted": False}

        if rank <= promote_cutoff and state.current_tier != LeagueTier.DIAMOND:
            tiers = list(LeagueTier)
            current_idx = tiers.index(state.current_tier)
            state.current_tier = tiers[min(current_idx + 1, len(tiers) - 1)]
            state.promotion_count += 1
            if state.current_tier.value > state.highest_tier_ever.value:
                state.highest_tier_ever = state.current_tier
            result["promoted"] = True
            result["new_tier"] = state.current_tier.value
            result["message"] = f"🎉 恭喜晋升到 {state.current_tier.value} 联赛！"

        elif rank >= demote_cutoff and state.current_tier != LeagueTier.BRONZE:
            tiers = list(LeagueTier)
            current_idx = tiers.index(state.current_tier)
            state.current_tier = tiers[max(current_idx - 1, 0)]
            state.demotion_count += 1
            result["demoted"] = True
            result["new_tier"] = state.current_tier.value
            result["message"] = f"降至 {state.current_tier.value} 联赛。下周再战！"

        else:
            result["message"] = f"保持在 {state.current_tier.value} 联赛！"

        if rank <= 3:
            state.top3_finishes += 1

        state.weeks_in_current_tier += 1
        return result

    @classmethod
    def _get_ranking_message(cls, rank: int, total: int) -> str:
        if rank == 1:
            return "🏆 你目前排名第一！"
        elif rank <= 3:
            return f"🌟 你在前三！排名第{rank}/{total}"
        elif rank <= total // 2:
            return f"📈 排名第{rank}/{total}，继续加油！"
        else:
            return f"📉 排名第{rank}/{total}，加把劲！"


# ═══════════════════════════════════════════════════════════
# 3. 连胜强化 — 多邻国式 Streak
# ═══════════════════════════════════════════════════════════

@dataclass
class DuolingoStreakState:
    """多邻国式连胜状态"""
    current_streak: int = 0
    streak_freezes_available: int = 2    # 冻结卡
    streak_freeze_active: bool = False   # 当前是否冻结中
    streak_society_member: bool = False  # 连胜社团成员
    last_lesson_date: Optional[str] = None
    perfect_weeks: int = 0               # 完美周数
    streak_wager_active: bool = False    # 连胜赌注
    streak_wager_days: int = 0


class DuolingoStreakEngine:
    """多邻国式连胜引擎"""

    @classmethod
    def check_in(cls, state: DuolingoStreakState) -> dict:
        """每日签到"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if state.last_lesson_date == today:
            return {"streak_updated": False, "streak": state.current_streak,
                    "message": "今天已经学过了！"}

        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

        if state.last_lesson_date == yesterday:
            # 正常连续
            state.current_streak += 1
            state.last_lesson_date = today
            state.streak_freeze_active = False

            # 连胜社团
            if state.current_streak >= 30:
                state.streak_society_member = True

            return cls._build_streak_result(state, "extended")

        elif state.streak_freezes_available > 0 and state.current_streak > 0:
            # 使用冻结卡
            state.streak_freezes_available -= 1
            state.streak_freeze_active = True
            state.current_streak += 1
            state.last_lesson_date = today

            return cls._build_streak_result(state, "frozen")

        else:
            # 断签
            old = state.current_streak
            state.current_streak = 1
            state.last_lesson_date = today
            state.streak_freeze_active = False
            return {
                "streak_updated": True, "streak": 1,
                "action": "reset", "old_streak": old,
                "message": f"连胜重置了…你之前坚持了{old}天。从头开始吧！",
                "emotion": "sad_owl",
            }

    @classmethod
    def _build_streak_result(cls, state, action) -> dict:
        """构建连胜结果"""
        streak = state.current_streak
        base = {"streak_updated": True, "streak": streak, "action": action}

        if action == "frozen":
            return {**base,
                "message": "连胜冻结卡已使用！你的连胜保住了。",
                "streak_frozen": True,
                "freezes_left": state.streak_freezes_available,
                "emotion": "relieved_owl",
            }

        # 连胜火焰等级
        fire_level = min(streak // 10 + 1, 10)
        fire_icons = ["🔥"] * min(fire_level, 5) + (["💎"] * (fire_level - 5) if fire_level > 5 else [])

        messages = {
            1: "第一天！种子种下了。",
            3: "三天了！火焰开始燃烧。",
            7: "一周了！连胜火焰 🔥",
            10: "十天！你已经超越了大多数人。",
            14: f"两周！{'🔥'*2} 连胜火焰在壮大。",
            30: f"一个月！{'🔥'*3} 连胜社团欢迎你！",
            50: f"50天！{'🔥'*4} 你是传奇。",
            100: f"100天！{'🔥'*5} 连胜俱乐部的精英。",
            365: f"一年！💎 你已经不是原来的你了。",
        }

        msg = messages.get(streak,
            f"{streak}天！{''.join(fire_icons)}" if streak > 30 else f"{streak}天！")

        return {**base,
            "message": msg,
            "fire_level": fire_level,
            "fire_icons": ''.join(fire_icons),
            "streak_society": state.streak_society_member,
            "streak_frozen": False,
            "emotion": "proud_owl" if streak >= 7 else "encouraging_owl",
        }

    @classmethod
    def generate_reminder(cls, state: DuolingoStreakState) -> Optional[dict]:
        """生成多邻国式被动攻击提醒"""
        if state.last_lesson_date == datetime.now(UTC).strftime("%Y-%m-%d"):
            return None

        hour = datetime.now(UTC).hour
        reminders = [
            "这些连胜不会自己维护哦。",
            "小豆注意到你今天还没学习…",
            "你的连胜在等你。",
            "每天坚持一点点，比周末突击效果好很多。",
            "就差今天这一步了！",
        ]

        if hour >= 20:
            reminders = [
                "已经很晚了，但1道题只需要2分钟…",
                "今天的连胜还在等你。睡前做一题？",
                "小豆在等你学完今天的习。",
            ]

        return {
            "should_remind": True,
            "message": random.choice(reminders),
            "type": "passive_aggressive",
            "pet_animation": "looking_at_streak",
            "urgency": "gentle" if hour < 20 else "moderate",
        }


# ═══════════════════════════════════════════════════════════
# 4. 好友任务 — Friend Quests
# ═══════════════════════════════════════════════════════════

@dataclass
class FriendQuest:
    """好友任务"""
    id: str
    participants: List[str]         # 2人
    goal_xp: int = 500              # 共同目标
    current_xp: int = 0
    contribution: Dict[str, int] = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    completed: bool = False
    reward: str = "30 XP + 1 双倍经验卡"


class FriendQuestEngine:
    """好友任务引擎

    双人合作任务 — 你不想拖累朋友，朋友也不想拖累你。
    社交压力 × 合作 = 最强的完成驱动力。
    """

    QUEST_TEMPLATES = [
        {"goal_xp": 300, "duration_days": 2, "name": "周末冲刺", "reward": "15 XP + 1 冻结卡"},
        {"goal_xp": 500, "duration_days": 3, "name": "合作挑战", "reward": "30 XP + 1 双倍经验卡"},
        {"goal_xp": 1000, "duration_days": 7, "name": "一周战友", "reward": "50 XP + 2 双倍经验卡"},
        {"goal_xp": 50, "duration_days": 1, "name": "今日之约", "reward": "10 XP"},
    ]

    # 好友任务容器 —— 迁移到可插拔 StateStore 后端
    # 值为 FriendQuest 且 contribute_xp 就地累加 current_xp/contribution，沿用内存后端。
    # TODO(persist): add asdict serialization for JSONFileStateStore
    ACTIVE_QUESTS: StateStore = MemoryStateStore()

    @classmethod
    def create_quest(cls, user1_id: str, user2_id: str) -> FriendQuest:
        """创建好友任务"""
        template = random.choice(cls.QUEST_TEMPLATES)
        quest_id = f"fq_{len(cls.ACTIVE_QUESTS.keys()) + 1}"
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        end = (datetime.now(UTC) + timedelta(days=template["duration_days"])).strftime("%Y-%m-%d")

        quest = FriendQuest(
            id=quest_id,
            participants=[user1_id, user2_id],
            goal_xp=template["goal_xp"],
            contribution={user1_id: 0, user2_id: 0},
            start_date=today,
            end_date=end,
            reward=template["reward"],
        )
        cls.ACTIVE_QUESTS.set(quest_id, quest)
        return quest

    @classmethod
    def contribute_xp(cls, quest_id: str, user_id: str, xp: int) -> dict:
        """为好友任务贡献经验"""
        quest = cls.ACTIVE_QUESTS.get(quest_id)
        if not quest or quest.completed:
            return {"contributed": False}

        quest.current_xp += xp
        quest.contribution[user_id] = quest.contribution.get(user_id, 0) + xp

        if quest.current_xp >= quest.goal_xp:
            quest.completed = True
            return {
                "contributed": True,
                "completed": True,
                "reward": quest.reward,
                "message": "🎉 好友任务完成！你和你的学习伙伴都获得了奖励！",
                "contributions": quest.contribution,
            }

        progress = quest.current_xp / quest.goal_xp * 100
        partner_id = [p for p in quest.participants if p != user_id][0]
        partner_contrib = quest.contribution.get(partner_id, 0)

        return {
            "contributed": True,
            "completed": False,
            "progress_pct": round(progress),
            "xp_needed": quest.goal_xp - quest.current_xp,
            "your_contribution": quest.contribution.get(user_id, 0),
            "partner_contribution": partner_contrib,
            "nudge": cls._get_nudge(quest.contribution, user_id, partner_contrib),
        }

    @classmethod
    def _get_nudge(cls, contributions: dict, user_id: str, partner_contrib: int) -> str:
        user_contrib = contributions.get(user_id, 0)
        if user_contrib < partner_contrib:
            return "你的学习伙伴比你多完成了一些。加把劲！"
        elif user_contrib > partner_contrib:
            return "你在领跑！继续保持。"
        return "你们并驾齐驱！"


# ═══════════════════════════════════════════════════════════
# 5. 早晨/晚间双倍 — Early Bird & Night Owl
# ═══════════════════════════════════════════════════════════

class TimeBasedBonusEngine:
    """时间段奖励引擎"""

    @classmethod
    def check_time_bonus(cls) -> dict:
        """检查当前时段奖励"""
        hour = datetime.now(UTC).hour

        if 6 <= hour < 9:
            return {
                "bonus_active": True,
                "type": "early_bird",
                "multiplier": 2.0,
                "message": "🌅 早起学习者！接下来的学习获得双倍经验。",
                "xp_bonus": 15,
                "time_remaining": f"{9 - hour}小时",
            }
        elif 9 <= hour < 12:
            return {
                "bonus_active": True,
                "type": "morning_golden",
                "multiplier": 1.5,
                "message": "☀️ 早上好！黄金学习时间。",
                "xp_bonus": 10,
                "time_remaining": f"{12 - hour}小时",
            }
        elif 20 <= hour < 22:
            return {
                "bonus_active": True,
                "type": "night_owl",
                "multiplier": 2.0,
                "message": "🦉 晚间学习者！双倍经验中。",
                "xp_bonus": 10,
                "time_remaining": f"{22 - hour}小时",
            }

        return {"bonus_active": False}


# ═══════════════════════════════════════════════════════════
# 6. 月度挑战 — Monthly Challenge
# ═══════════════════════════════════════════════════════════

class MonthlyChallengeEngine:
    """月度挑战引擎"""

    MONTHLY_CHALLENGES = [
        {"id": "mc_quests", "name": "任务大师", "goal": 20, "unit": "好友任务",
         "reward": "独家月度徽章", "xp_reward": 200},
        {"id": "mc_xp", "name": "经验收集者", "goal": 5000, "unit": "XP",
         "reward": "月度专属头像框", "xp_reward": 300},
        {"id": "mc_perfect", "name": "完美主义者", "goal": 10, "unit": "全对课程",
         "reward": "金色月度徽章", "xp_reward": 250},
        {"id": "mc_streak", "name": "全勤奖", "goal": 28, "unit": "学习天数",
         "reward": "月度全勤徽章", "xp_reward": 500},
    ]

    @classmethod
    def get_current_challenge(cls) -> dict:
        challenge = cls.MONTHLY_CHALLENGES[datetime.now(UTC).month % len(cls.MONTHLY_CHALLENGES)]
        days_left = cls._days_left_in_month()
        return {
            "challenge": challenge,
            "days_left": days_left,
            "message": f"本月挑战: {challenge['name']} — {challenge['goal']}{challenge['unit']}。还剩{days_left}天！",
        }

    @classmethod
    def check_completion(cls, challenge_id: str, current_progress: int) -> dict:
        challenge = next((c for c in cls.MONTHLY_CHALLENGES if c["id"] == challenge_id), None)
        if not challenge:
            return {"completed": False}

        if current_progress >= challenge["goal"]:
            return {
                "completed": True,
                "message": f"🎊 月度挑战完成！获得: {challenge['reward']} + {challenge['xp_reward']} XP",
                "reward": challenge["reward"],
                "xp_reward": challenge["xp_reward"],
            }

        return {
            "completed": False,
            "progress": current_progress,
            "goal": challenge["goal"],
            "progress_pct": round(current_progress / challenge["goal"] * 100),
            "remaining": challenge["goal"] - current_progress,
        }

    @staticmethod
    def _days_left_in_month() -> int:
        now = datetime.now(UTC)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
        return (next_month - now).days


# ═══════════════════════════════════════════════════════════
# 7. 多邻国风格通知引擎
# ═══════════════════════════════════════════════════════════

class DuolingoNotificationEngine:
    """多邻国式通知 — 可爱但被动攻击"""

    NOTIFICATION_TEMPLATES = {
        "streak_reminder": [
            "🔥 这些连胜不会自己维护哦。",
            "小豆在等你的每日学习。",
            "你的连胜火焰要熄灭了…",
            "坚持是最好的学习策略。今天只需要2分钟。",
        ],
        "friend_reminder": [
            "你的学习伙伴刚刚完成了今天的任务。你呢？",
            "别让你的好友任务队友等太久。",
            "你们的好友任务还差一点点！",
        ],
        "league_reminder": [
            "联赛还剩2天！你的排名在下降…",
            "只差50 XP就能超过前面的人了。",
            "保持你的联赛排名！",
        ],
        "weekly_report": [
            "📊 你的周报已生成。看看这周的进步！",
            "本周统计: 你比上周多学了！",
            "一周过去了，你成长了多少？",
        ],
        "new_feature": [
            "🎁 新徽章上线了！来看看你能收集到什么。",
            "新的挑战在等你。",
        ],
    }

    @classmethod
    def generate_notification(cls, notif_type: str,
                               context: dict = None) -> Optional[dict]:
        """生成通知"""
        templates = cls.NOTIFICATION_TEMPLATES.get(notif_type, [])
        if not templates:
            return None

        return {
            "title": "LearnFlow",
            "body": random.choice(templates),
            "type": notif_type,
            "icon": cls._get_icon(notif_type),
            "context": context or {},
        }

    @classmethod
    def _get_icon(cls, notif_type: str) -> str:
        return {
            "streak_reminder": "🔥",
            "friend_reminder": "👥",
            "league_reminder": "🏆",
            "weekly_report": "📊",
            "new_feature": "🎁",
        }.get(notif_type, "💎")


# ═══════════════════════════════════════════════════════════
# 8. 经验目标选择器 — Daily XP Goal
# ═══════════════════════════════════════════════════════════

class DailyXPGoalEngine:
    """每日经验目标 — 多邻国式目标选择器"""

    GOAL_OPTIONS = [
        {"xp": 20, "label": "基础", "time": "约5分钟", "flame": "🔥"},
        {"xp": 50, "label": "日常", "time": "约10分钟", "flame": "🔥🔥"},
        {"xp": 100, "label": "认真", "time": "约20分钟", "flame": "🔥🔥🔥"},
        {"xp": 200, "label": "专注", "time": "约40分钟", "flame": "🔥🔥🔥🔥"},
        {"xp": 500, "label": "狂热", "time": "约60分钟", "flame": "🔥🔥🔥🔥🔥"},
    ]

    @classmethod
    def set_goal(cls, user_id: str, goal_xp: int) -> dict:
        if goal_xp not in [g["xp"] for g in cls.GOAL_OPTIONS]:
            return {"error": "无效目标"}

        return {
            "goal_set": True,
            "daily_xp_goal": goal_xp,
            "message": f"今日目标: {goal_xp} XP。完成时小豆会为你庆祝！",
        }

    @classmethod
    def check_goal_completion(cls, today_xp: int, goal_xp: int) -> dict:
        if today_xp >= goal_xp:
            return {
                "completed": True,
                "message": "🎉 今日目标达成！小豆为你感到骄傲。",
                "overflow_xp": today_xp - goal_xp,
                "reward": "1 双倍经验卡",
            }

        return {
            "completed": False,
            "progress_pct": round(today_xp / goal_xp * 100),
            "remaining_xp": goal_xp - today_xp,
            "message": f"还差 {goal_xp - today_xp} XP 达成今日目标",
            "encouragement": random.choice([
                "快了！", "你正在接近目标。", "坚持住！", "快完成了！"
            ]),
        }
