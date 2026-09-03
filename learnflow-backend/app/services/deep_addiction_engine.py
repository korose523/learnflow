"""深度行为上瘾引擎 — 第四波

新增7大上瘾机制:
1. 好奇心缺口 (Curiosity Gap) — Loewenstein 信息缺口理论
2. 收藏强迫 (Collection Compulsion) — 全套徽章系统
3. 错失恐惧 (FOMO) — 限时稀有题目/挑战
4. 打卡圣化 (Streak Sanctification) — 仪式化打卡体验
5. 预约动力学 (Appointment Dynamics) — 事先承诺机制
6. 稀缺排他 (Scarcity & Exclusivity) — 限时稀有内容
7. 随机惊喜深化 (Serendipity Engine) — 随机意外的深度

设计原则: 每一轮都让人"还想再来一题"。
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional
import random

from app.services.mechanism_registry import Effect, EffectType


# ═══════════════════════════════════════════════════════════
# 1. 好奇心缺口引擎 — Information Gap Theory
# ═══════════════════════════════════════════════════════════

class CuriosityEngine:
    """好奇心缺口引擎

    Loewenstein (1994): 好奇心源于"已知"与"想知道"之间的缺口。
    适度的信息缺口产生最强的探索动力。

    实现: 在每轮题目之间故意制造知识悬念。
    """

    TEASER_BANK = {
        "math": [
            "你知道吗？有一种方法可以让99%的人算错这道题...",
            "下一题用到了一个连数学家都觉得神奇的性质。",
            "这个技巧你一旦学会，同类题目速度翻倍。",
            "你即将发现的这个方法，是你同桌不知道的。",
        ],
        "science": [
            "为什么冰会浮在水上？答案比你想象的更有趣。",
            "下一个实验解释了为什么天空是蓝色的。",
            "你知道吗？你身体里的原子可能来自一颗爆炸的恒星。",
        ],
        "general": [
            "下一题藏着一个'啊哈！'时刻。",
            "做完这道题，你会忍不住想告诉别人。",
            "这道题的解法会让你会心一笑。",
            "准备好了吗？这道题有点不一样。",
        ],
    }

    @classmethod
    def generate_teaser(cls, topic: str) -> dict:
        """在题目加载前生成好奇心缺口"""
        bank = cls.TEASER_BANK.get(topic, cls.TEASER_BANK["general"])
        teaser = random.choice(bank)

        return {
            "teaser": teaser,
            "mechanism": "information_gap",
            "gap_size": random.choice(["small", "medium"]),
            # 小缺口="马上就知道" / 中等缺口="有点悬念"
            "reveal_timing": "after_answer",
            "curiosity_score": random.randint(60, 95),
        }

    @classmethod
    def generate_mystery_unlock(cls, topics_unlocked: List[str],
                                 topics_locked: List[str]) -> dict:
        """神秘解锁 — 展示被锁定的知识领域"""
        if not topics_locked:
            return {"has_mystery": False}

        mystery_topic = random.choice(topics_locked)
        return {
            "has_mystery": True,
            "mystery_topic": mystery_topic,
            "message": f"「{mystery_topic}」还是一片未知领域。再完成3题就能解锁它。",
            "progress": len(topics_unlocked),
            "total_to_unlock": len(topics_unlocked) + 3,
            "visual": "lock_with_glow",  # 前端渲染发光锁
        }

    @classmethod
    def generate_cliffhanger(cls, topic: str, difficulty: int) -> dict:
        """悬念式结尾 — 让用户期待下一题"""
        cliffhangers = [
            f"下一题将揭示 {topic} 的核心秘密。",
            f"做好准备——难度{difficulty + 1}的挑战在等着你。",
            "接下来的题目会改变你对这个知识点的理解。",
            f"做完下一题，你就是全班前20%了。",
        ]
        return {
            "cliffhanger": random.choice(cliffhangers),
            "action": "continue",
            "urgency": "optional_but_curious",
        }


# ═══════════════════════════════════════════════════════════
# 2. 收藏强迫引擎 — Collection Compulsion
# ═══════════════════════════════════════════════════════════

@dataclass
class CollectionState:
    """收藏品状态"""
    badges_collected: List[str] = field(default_factory=list)
    hidden_badges_found: int = 0
    collection_completeness: float = 0.0
    rarest_item: Optional[str] = None
    last_collected_at: Optional[datetime] = None


class CollectionEngine:
    """收藏强迫引擎

    人类天生有"收集完整套"的本能。
    缺口 + 稀有度 = 最强的收集驱动力。
    """

    # 全部可收集的徽章
    ALL_BADGES = {
        "learning": [
            {"id": "first_blood", "name": "初出茅庐", "desc": "完成第1道题", "rarity": "common", "icon": "🌱"},
            {"id": "century", "name": "百题斩", "desc": "完成100道题", "rarity": "rare", "icon": "⚔️"},
            {"id": "millennium", "name": "千题王", "desc": "完成1000道题", "rarity": "legendary", "icon": "👑"},
            {"id": "myriad", "name": "万题宗师", "desc": "完成10000道题", "rarity": "mythic", "icon": "💎"},
        ],
        "streak": [
            {"id": "streak_3", "name": "三日之约", "desc": "连续3天学习", "rarity": "common", "icon": "🔥"},
            {"id": "streak_7", "name": "一周之星", "desc": "连续7天学习", "rarity": "uncommon", "icon": "⭐"},
            {"id": "streak_30", "name": "月度传说", "desc": "连续30天学习", "rarity": "rare", "icon": "🌟"},
            {"id": "streak_100", "name": "百日记", "desc": "连续100天学习", "rarity": "legendary", "icon": "🏆"},
        ],
        "mastery": [
            {"id": "master_1", "name": "掌握者", "desc": "完全掌握1个知识点", "rarity": "common", "icon": "📚"},
            {"id": "master_5", "name": "博学者", "desc": "掌握5个知识点", "rarity": "rare", "icon": "🎓"},
            {"id": "master_all", "name": "全知者", "desc": "掌握所有知识点", "rarity": "legendary", "icon": "🌌"},
        ],
        "hidden": [
            {"id": "night_owl", "name": "夜猫子", "desc": "在深夜解开一道难题", "rarity": "secret", "icon": "🦉", "hide_until_earned": True},
            {"id": "perfect_day", "name": "完美一日", "desc": "一天内正确率100%且至少10题", "rarity": "secret", "icon": "✨", "hide_until_earned": True},
            {"id": "comeback", "name": "逆转王", "desc": "连续错5题后连续对5题", "rarity": "secret", "icon": "🔄", "hide_until_earned": True},
            {"id": "speed_demon", "name": "速解者", "desc": "1分钟内答对难度8+的题目", "rarity": "secret", "icon": "⚡", "hide_until_earned": True},
            {"id": "early_bird", "name": "晨型人", "desc": "早上6点前完成学习", "rarity": "secret", "icon": "🌅", "hide_until_earned": True},
        ],
    }

    @classmethod
    def check_and_award(cls, state: CollectionState, trigger: str,
                         stats: dict) -> List[dict]:
        """检查并颁发徽章"""
        newly_earned = []

        for category, badges in cls.ALL_BADGES.items():
            for badge in badges:
                if badge["id"] in state.badges_collected:
                    continue

                earned = cls._check_condition(badge["id"], stats)
                if earned:
                    state.badges_collected.append(badge["id"])
                    state.last_collected_at = datetime.now(UTC)
                    if badge.get("hide_until_earned"):
                        state.hidden_badges_found += 1

                    newly_earned.append({
                        "id": badge["id"],
                        "name": badge["name"],
                        "desc": badge["desc"],
                        "rarity": badge["rarity"],
                        "icon": badge["icon"],
                        "is_hidden": badge.get("hide_until_earned", False),
                        "message": f"🏅 获得徽章: {badge['icon']} {badge['name']} — {badge['desc']}",
                    })

        # 更新收藏完整度
        total = sum(len(b) for b in cls.ALL_BADGES.values())
        state.collection_completeness = len(state.badges_collected) / total

        return newly_earned

    @classmethod
    def _check_condition(cls, badge_id: str, stats: dict) -> bool:
        conditions = {
            "first_blood": stats.get("total_attempts", 0) >= 1,
            "century": stats.get("total_attempts", 0) >= 100,
            "millennium": stats.get("total_attempts", 0) >= 1000,
            "myriad": stats.get("total_attempts", 0) >= 10000,
            "streak_3": stats.get("current_streak", 0) >= 3,
            "streak_7": stats.get("current_streak", 0) >= 7,
            "streak_30": stats.get("current_streak", 0) >= 30,
            "streak_100": stats.get("current_streak", 0) >= 100,
            "master_1": stats.get("topics_mastered", 0) >= 1,
            "master_5": stats.get("topics_mastered", 0) >= 5,
            "master_all": stats.get("all_topics_mastered", False),
            "night_owl": stats.get("solved_at_night", False) and stats.get("difficulty", 0) >= 7,
            "perfect_day": stats.get("daily_accuracy", 0) == 100 and stats.get("daily_attempts", 0) >= 10,
            "comeback": stats.get("comeback_achieved", False),
            "speed_demon": stats.get("fast_solve", False),
            "early_bird": stats.get("early_morning", False),
        }
        return conditions.get(badge_id, False)

    @classmethod
    def generate_collection_summary(cls, state: CollectionState) -> dict:
        """生成收藏进度摘要 — 缺口的视觉化让收集欲更强"""
        total = sum(len(b) for b in cls.ALL_BADGES.values())
        collected = len(state.badges_collected)
        missing = total - collected

        rarity_counts = {}
        for badge_list in cls.ALL_BADGES.values():
            for badge in badge_list:
                if badge["id"] in state.badges_collected:
                    r = badge["rarity"]
                    rarity_counts[r] = rarity_counts.get(r, 0) + 1

        return {
            "collected": collected,
            "total": total,
            "completeness": round(state.collection_completeness, 2),
            "completeness_pct": round(state.collection_completeness * 100),
            "missing": missing,
            "hidden_found": state.hidden_badges_found,
            "hidden_total": sum(1 for bl in cls.ALL_BADGES.values() for b in bl if b.get("hide_until_earned")),
            "rarity_breakdown": rarity_counts,
            "collection_nudge": f"还有{missing}个徽章等待发现。有些隐藏得很深...",
        }


# ═══════════════════════════════════════════════════════════
# 3. 错失恐惧引擎 — FOMO
# ═══════════════════════════════════════════════════════════

class FOMOEngine:
    """FOMO (Fear Of Missing Out) 引擎

    限时稀有内容 + 倒计时 = 最强的行动驱动力之一。
    不制造焦虑，制造"趁现在"的合理紧迫感。
    """

    # 限时挑战池
    TIME_LIMITED_CHALLENGES = [
        {"id": "weekend_warrior", "name": "周末勇士", "desc": "周六日完成15题获得双倍经验",
         "window": "weekend", "reward": "2x_xp", "rarity": "weekly"},
        {"id": "streak_saver", "name": "断签救援", "desc": "今天完成5题可获得1个打卡保护盾",
         "window": "daily", "reward": "streak_shield", "rarity": "daily"},
        {"id": "golden_hour", "name": "黄金时刻", "desc": "在班级最活跃的时段完成3题获得稀有宝石",
         "window": "hourly", "reward": "gem", "rarity": "common"},
        {"id": "mystery_challenge", "name": "神秘挑战", "desc": "随机出现的高奖励限时挑战",
         "window": "random", "reward": "random", "rarity": "rare"},
    ]

    @classmethod
    def get_active_challenges(cls) -> List[dict]:
        """获取当前活跃的限时挑战"""
        now = datetime.now(UTC)
        active = []

        for challenge in cls.TIME_LIMITED_CHALLENGES:
            if challenge["window"] == "weekend" and now.weekday() >= 5:
                active.append({**challenge, "time_remaining": "本周末结束"})
            elif challenge["window"] == "daily":
                active.append({**challenge, "time_remaining": "今天结束"})
            elif challenge["window"] == "hourly":
                active.append({**challenge, "time_remaining": "本小时内"})
            elif challenge["window"] == "random" and random.random() < 0.15:
                minutes_left = random.randint(15, 120)
                active.append({**challenge, "time_remaining": f"{minutes_left}分钟后过期", "countdown_minutes": minutes_left})

        return active

    @classmethod
    def generate_fomo_nudge(cls, active_challenges: List[dict]) -> Optional[Effect]:
        """生成FOMO轻推 —— 产出 Effect 候选, 由 MechanismArbitrator 三层漏斗决定下发

        治理 §3.4.2: FOMO (LF-M44) 不再是直接下发的用户可见文案, 而是经仲裁器的
        Effect 候选; 未成年保护 (LF-M52) 命中时, 仲裁器第 1 层健康一票否决会丢弃它。
        """
        if not active_challenges:
            return None

        best = active_challenges[0]
        nudge = {
            "type": "fomo",
            "message": f"⏰ {best['name']}: {best['desc']}（{best.get('time_remaining', '限时')}）",
            "urgency_level": "gentle" if "小时" in best.get("time_remaining", "") else "moderate",
            "action": "start_challenge",
            "challenge_id": best["id"],
        }
        return Effect(
            mechanism_id="LF-M44",
            effect_type=EffectType.NUDGE,
            payload=nudge,
            priority=50,
            cost=1.5,
            user_visible=True,
            health_critical=False,
            direction="approach",
        )

    @classmethod
    def generate_peer_progress_nudge(cls, peer_stats: dict) -> dict:
        """同伴进度FOMO"""
        if peer_stats.get("peers_completed_today", 0) > peer_stats.get("user_completed_today", 0) + 2:
            return {
                "type": "peer_fomo",
                "message": f"今天已经有{peer_stats['peers_completed_today']}位同学完成了学习。",
                "nudge": "加入他们？",
                "fomo_score": 0.6,
            }
        return {"type": "peer_fomo", "fomo_score": 0.0}


# ═══════════════════════════════════════════════════════════
# 4. 打卡圣化引擎 — Streak Sanctification
# ═══════════════════════════════════════════════════════════

class StreakSanctificationEngine:
    """打卡圣化引擎

    把"连续学习"从数字变成仪式。
    祈祷、冥想、每日打卡 — 人类天生对仪式有敬畏。
    你的学习打卡不是一个数字，是一个神圣的承诺。
    """

    STREAK_MILESTONE_RITUALS = {
        1: {"ritual": "种下习惯种子", "message": "第一天。种子已经种下。明天的你会感谢今天的你。", "animation": "seed_planting"},
        3: {"ritual": "三日考验", "message": "三天。你最难的时刻已经过去。习惯在成形。", "animation": "sprout_growing"},
        7: {"ritual": "一周之约", "message": "一周了。这不是偶然，这是你的选择。你已经不是上周的那个你了。", "animation": "tree_blooming"},
        14: {"ritual": "双周纪念", "message": "两周。你的大脑已经开始期待每天的学习时光。", "animation": "forest_expanding"},
        21: {"ritual": "习惯成形", "message": "21天。理论上，一个新的习惯已经深深印在你的神经网络里。", "animation": "neural_pathway"},
        30: {"ritual": "月度传说", "message": "一个月。一个月前的你，和现在的你，已经是不同的人了。", "animation": "mountain_sunrise"},
        66: {"ritual": "自动化达成", "message": "66天！学习对你来说已经像呼吸一样自然。你不再'坚持'，你只是'是'。", "animation": "universe_expansion"},
        100: {"ritual": "百年之约", "message": "100天。你证明了一件事: 学习不是任务，是你的生活方式。", "animation": "century_celebration"},
        365: {"ritual": "一年旅程", "message": "一年了。365天前你决定开始。你做到了。你想成为的那个人，已经是你。", "animation": "galaxy_formation"},
    }

    @classmethod
    def get_daily_ritual(cls, streak: int) -> dict:
        """获取每日打卡仪式"""
        # 检查是否到达里程碑
        if streak in cls.STREAK_MILESTONE_RITUALS:
            ritual = cls.STREAK_MILESTONE_RITUALS[streak]
            return {
                "is_milestone": True,
                "streak": streak,
                "ritual": ritual["ritual"],
                "message": ritual["message"],
                "animation": ritual["animation"],
                "ceremony": cls._generate_ceremony(streak),
            }

        # 非里程碑日的日常仪式
        return {
            "is_milestone": False,
            "streak": streak,
            "message": f"第{streak}天。你正在书写自己的故事。",
            "ceremony": "daily_check_in",
            "completion_sound": "gentle_bell",
        }

    @classmethod
    def _generate_ceremony(cls, streak: int) -> dict:
        """生成里程碑仪式步骤"""
        return {
            "steps": [
                {"order": 1, "action": "深呼吸三次", "duration_sec": 10, "message": "闭上眼睛，感受这一刻。"},
                {"order": 2, "action": "回顾成长", "duration_sec": 5, "message": f"想想{streak}天前的自己和现在的自己。"},
                {"order": 3, "action": "解锁成就", "duration_sec": 3, "message": "仪式完成。"},
            ],
            "reward": f"获得 {streak}天 里程碑专属特效",
        }

    @classmethod
    def generate_streak_worship_message(cls, streak: int) -> str:
        """生成打卡崇拜信息 — 让用户感到自己的坚持是神圣的"""
        if streak >= 100:
            return "你不再需要'坚持学习'——学习已经是你的一部分。你是所有新用户的榜样。"
        elif streak >= 30:
            return "你在做的事，99%的人做不到。这不是自律，这是对自己未来的信仰。"
        elif streak >= 7:
            return "每一次打卡，都是对未来的自己说: 我在乎你。"
        return "今天的选择，是明天的礼物。"


# ═══════════════════════════════════════════════════════════
# 5. 预约动力学引擎 — Appointment Dynamics
# ═══════════════════════════════════════════════════════════

@dataclass
class AppointmentState:
    """预约学习状态"""
    scheduled_sessions: List[dict] = field(default_factory=list)
    completed_appointments: int = 0
    missed_appointments: int = 0


class AppointmentEngine:
    """预约动力学引擎

    事先承诺 (Pre-commitment) 是最强的行为约束之一。
    "我已经预约了明天7点的学习" → 失约=失败。
    """

    @classmethod
    def create_appointment(cls, state: AppointmentState, user_id: str,
                            time_str: str, topic: str = "",
                            duration_min: int = 20) -> dict:
        """创建学习预约"""
        appointment = {
            "id": f"apt_{len(state.scheduled_sessions) + 1}",
            "time": time_str,
            "topic": topic or "自由学习",
            "duration_min": duration_min,
            "created_at": datetime.now(UTC).isoformat(),
            "status": "scheduled",
        }
        state.scheduled_sessions.append(appointment)

        return {
            "appointment": appointment,
            "message": f"已预约 {time_str} 的学习！小豆会准时等你。",
            "pre_commitment": "做出预约的学习者，完成率高出43%。",
            "reminder": "预约前15分钟，小豆会提醒你。",
        }

    @classmethod
    def get_upcoming_appointments(cls, state: AppointmentState) -> List[dict]:
        """获取即将到来的预约"""
        return [a for a in state.scheduled_sessions if a["status"] == "scheduled"]

    @classmethod
    def mark_completed(cls, state: AppointmentState, appointment_id: str) -> dict:
        """标记预约完成"""
        for a in state.scheduled_sessions:
            if a["id"] == appointment_id:
                a["status"] = "completed"
                state.completed_appointments += 1
                return {
                    "message": "预约完成！你是一个守信的学习者。",
                    "reliability_score": round(state.completed_appointments /
                        max(state.completed_appointments + state.missed_appointments, 1) * 100),
                }
        return {"message": "未找到该预约"}

    @classmethod
    def get_appointment_nudge(cls, state: AppointmentState) -> Optional[dict]:
        """预约提醒"""
        upcoming = cls.get_upcoming_appointments(state)
        if not upcoming:
            if state.completed_appointments >= 3:
                return {
                    "should_nudge": True,
                    "message": "你已经完成了多次预约学习。要安排下一次吗？",
                    "action": "schedule_next",
                }
            return None

        next_apt = upcoming[0]
        return {
            "should_nudge": True,
            "message": f"你预约了 {next_apt['time']} 的学习。小豆在等你。",
            "action": "view_appointment",
        }


# ═══════════════════════════════════════════════════════════
# 6. 稀缺排他引擎 — Scarcity & Exclusivity
# ═══════════════════════════════════════════════════════════

class ScarcityEngine:
    """稀缺排他引擎

    Cialdini: 稀缺的东西更被渴望。
    限量的、独家的、只有达成条件才能解锁的。
    """

    EXCLUSIVE_CONTENT = {
        "golden_question": {
            "name": "黄金题目",
            "desc": "由系统精挑细选的'一题通'，做完一道抵三道",
            "unlock_condition": "连续正确5题",
            "rarity": "rare",
            "available_count": "每日3道",
        },
        "diamond_challenge": {
            "name": "钻石挑战",
            "desc": "只有班级前20%能访问的超难题库",
            "unlock_condition": "掌握度>80%",
            "rarity": "legendary",
            "available_count": "每周1次",
        },
        "teachers_pick": {
            "name": "老师精选",
            "desc": "老师认为'每个学生都该做'的题",
            "unlock_condition": "教师推荐",
            "rarity": "special",
            "available_count": "不定期",
        },
    }

    @classmethod
    def check_unlock(cls, content_key: str, stats: dict) -> dict:
        """检查是否解锁稀缺内容"""
        content = cls.EXCLUSIVE_CONTENT.get(content_key)
        if not content:
            return {"unlocked": False}

        conditions = {
            "golden_question": stats.get("current_streak", 0) >= 5,
            "diamond_challenge": stats.get("mastery_pct", 0) >= 80,
            "teachers_pick": stats.get("teacher_recommended", False),
        }

        unlocked = conditions.get(content_key, False)

        if unlocked:
            return {
                "unlocked": True,
                "content": content,
                "message": f"🔓 你解锁了 {content['name']}！{content['desc']}",
                "exclusivity_feel": "这是只有少数人才能看到的题目。",
            }
        else:
            return {
                "unlocked": False,
                "content": content,
                "message": f"🔒 {content['name']}: {content['unlock_condition']}后解锁",
                "exclusivity_feel": "达到条件后，你将获得这个独特的学习资源。",
            }

    @classmethod
    def generate_daily_rarity_drop(cls) -> dict:
        """每日稀有掉落"""
        drops = [
            {"type": "rare_topic", "name": "稀有主题", "desc": "今天可以学习一个不常出现的知识点", "rarity": "rare"},
            {"type": "double_streak", "name": "双倍打卡日", "desc": "今天打卡计为2天", "rarity": "legendary"},
            {"type": "hidden_level", "name": "隐藏关卡", "desc": "一个隐藏的知识挑战被激活了", "rarity": "mythic"},
        ]
        weights = [0.15, 0.05, 0.03]  # rare, legendary, mythic
        if random.random() < sum(weights):
            drop = random.choices(drops, weights=weights, k=1)[0]
            return {"has_drop": True, **drop,
                    "message": f"🎪 稀有发现: {drop['name']} — {drop['desc']}"}
        return {"has_drop": False}


# ═══════════════════════════════════════════════════════════
# 7. 随机惊喜深化引擎 — Serendipity
# ═══════════════════════════════════════════════════════════

class SerendipityEngine:
    """随机惊喜深化引擎

    不可预测性增加多巴胺释放。
    不是"随机奖励"，是"随机意外"——让用户感到幸运。
    """

    SERENDIPITY_EVENTS = [
        {"id": "pet_evolved", "trigger_chance": 0.02, "message": "小豆突然进化了！它学会了一个新技能。",
         "effect": "今天所有题目难度自适应精度提升10%"},
        {"id": "knowledge_surge", "trigger_chance": 0.03, "message": "你触发了'知识涌流'！大脑突然对刚才的题目有了更深的理解。",
         "effect": "当前知识点掌握度+5%"},
        {"id": "lucky_streak", "trigger_chance": 0.04, "message": "幸运之星降临！接下来的3道题，答对获得双倍奖励。",
         "effect": "3题内双倍奖励"},
        {"id": "mystery_visitor", "trigger_chance": 0.01, "message": "一位神秘访客来到了你的学习空间...它留下了一个古老的智慧卷轴。",
         "effect": "解锁一个隐藏知识点的预览"},
        {"id": "time_warp", "trigger_chance": 0.02, "message": "时间扭曲！你的学习效率突然提升。",
         "effect": "下5道题的预计耗时减半"},
        {"id": "echo_of_mastery", "trigger_chance": 0.05, "message": "你听到了'掌握的回声'——一个你已经完全掌握的知识点在你脑海中回响。",
         "effect": "随机已掌握知识点的复习奖励"},
        {"id": "rainbow_question", "trigger_chance": 0.015, "message": "🌈 一道彩虹色的题目出现了！这是极其罕见的'综合性挑战题'。",
         "effect": "跨知识点融合题，完成获得大量奖励"},
        {"id": "nothing_special", "trigger_chance": 0.935, "message": "", "effect": ""},
    ]

    @classmethod
    def roll_serendipity(cls) -> dict:
        """随机惊喜判定"""
        roll = random.random()
        cumulative = 0
        for event in cls.SERENDIPITY_EVENTS:
            cumulative += event["trigger_chance"]
            if roll <= cumulative:
                if event["id"] == "nothing_special":
                    return {"triggered": False}
                return {"triggered": True, "event": event,
                        "message": event["message"],
                        "effect": event["effect"],
                        "celebration": cls._get_celebration(event["id"])}
        return {"triggered": False}

    @classmethod
    def _get_celebration(cls, event_id: str) -> dict:
        celebrations = {
            "pet_evolved": {"animation": "evolution_glow", "sound": "magical_ascend", "duration_ms": 3000},
            "knowledge_surge": {"animation": "brain_sparkle", "sound": "insight_chime", "duration_ms": 2000},
            "lucky_streak": {"animation": "lucky_rain", "sound": "fortune_bell", "duration_ms": 2500},
            "rainbow_question": {"animation": "rainbow_burst", "sound": "epic_reveal", "duration_ms": 3500},
            "mystery_visitor": {"animation": "portal_open", "sound": "mysterious_wind", "duration_ms": 4000},
        }
        return celebrations.get(event_id, {"animation": "sparkle", "sound": "soft_chime", "duration_ms": 1500})
