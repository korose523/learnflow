"""社交成瘾系统 — Social Addiction Architecture

基于三大心理学原理:
1. 昂贵信号理论 (Costly Signaling)     — 展示需要付出努力的成就
2. 社会验证理论 (Social Validation)    — 被同伴认可触发多巴胺
3. 虚荣指标系统 (Vanity Metrics)      — 可量化的身份标记

设计哲学:
  社交≠排行榜排名。社交=相互认可+共同成长+信号传递。
  所有指标都是"你付出了什么"的证明，而非"你比别人强多少"。
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. 名片系统 — Costly Signaling Theory
# ═══════════════════════════════════════════════════════════

@dataclass
class BusinessCard:
    """学习名片 — 昂贵信号载体

    每个学生有一张名片，展示自己最引以为傲的学习成就。
    名片上的每一项都需要真实付出——这就是"昂贵信号"。
    """
    user_id: str
    display_name: str
    title: str = "初学者"                    # 自定义头衔
    level: int = 1
    badges_showcase: List[str] = field(default_factory=list)  # 展示的徽章 (最多6个)
    signature: str = ""                     # 个性签名
    pet_breed: str = "猫"
    pet_name: str = "小豆"
    pet_level: int = 1

    # 昂贵信号 — 需要付出才能展示的
    streak_display: int = 0
    total_mastered_topics: int = 0
    helped_peers_count: int = 0
    longest_streak: int = 0
    rarest_badge: str = ""
    total_hours_learned: float = 0.0

    # 视觉身份
    avatar_frame: str = "default"           # 头像框 (按等级解锁)
    name_color: str = "#666666"             # 名字颜色 (按等级解锁)
    background_theme: str = "default"       # 名片背景
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class BusinessCardEngine:
    """名片引擎

    名片=你的学习身份。每解锁一个成就，名片就更亮眼。
    这是在"展示自己付出的努力"，不是在"炫耀排名"。
    """

    TITLES = {
        "exploring": ["初学者", "好奇宝宝", "探索者"],
        "forming": ["坚持者", "习惯养成中", "日拱一卒"],
        "hooked": ["学习达人", "心流行者", "知识猎人"],
        "automated": ["学习大师", "知者", "终身学习者"],
    }

    AVATAR_FRAMES = {
        1: {"name": "default", "color": "#CCCCCC", "desc": "默认边框"},
        3: {"name": "bronze", "color": "#CD7F32", "desc": "连续学习3天解锁"},
        7: {"name": "silver", "color": "#C0C0C0", "desc": "连续学习7天解锁"},
        14: {"name": "gold", "color": "#FFD700", "desc": "连续学习14天解锁"},
        30: {"name": "diamond", "color": "#B9F2FF", "desc": "连续学习30天解锁"},
        66: {"name": "legendary", "color": "#FF4500", "desc": "习惯自动化达成"},
        100: {"name": "mythic", "color": "#9400D3", "desc": "百日记"},
    }

    @classmethod
    def create_card(cls, user_id: str, display_name: str,
                     stage: str = "exploring") -> BusinessCard:
        title = random.choice(cls.TITLES.get(stage, cls.TITLES["exploring"]))
        return BusinessCard(user_id=user_id, display_name=display_name, title=title)

    @classmethod
    def update_from_stats(cls, card: BusinessCard, stats: dict) -> BusinessCard:
        """根据学习数据更新名片"""
        card.streak_display = stats.get("current_streak", 0)
        card.longest_streak = max(card.longest_streak, stats.get("current_streak", 0))
        card.total_mastered_topics = stats.get("topics_mastered", 0)
        card.helped_peers_count = stats.get("help_others", 0)
        card.total_hours_learned = stats.get("total_minutes", 0) / 60
        card.pet_level = stats.get("pet_level", 1)
        card.level = stats.get("level", 1)

        # 稀有徽章
        badges = stats.get("badges_collected", [])
        rarity_order = {"secret": 5, "legendary": 4, "rare": 3, "uncommon": 2, "common": 1}
        if badges:
            best = max(badges, key=lambda b: rarity_order.get(b.get("rarity", "common"), 0))
            card.rarest_badge = best.get("name", "")
            card.badges_showcase = [b.get("name", "") for b in badges[:6]]

        # 头衔进化
        stage = stats.get("addiction_stage", "exploring")
        titles = cls.TITLES.get(stage, cls.TITLES["exploring"])
        card.title = f"{random.choice(titles)} Lv.{card.level}"

        # 头像框
        for days, frame in sorted(cls.AVATAR_FRAMES.items(), reverse=True):
            if card.streak_display >= days:
                card.avatar_frame = frame["name"]
                break

        card.updated_at = datetime.now(UTC)
        return card

    @classmethod
    def to_display_json(cls, card: BusinessCard) -> dict:
        """转为前端展示用JSON"""
        frame = cls.AVATAR_FRAMES.get(
            next((d for d, f in sorted(cls.AVATAR_FRAMES.items(), reverse=True)
                 if card.streak_display >= d), 1),
            cls.AVATAR_FRAMES[1])

        return {
            "display_name": card.display_name,
            "title": card.title,
            "signature": card.signature or "这个人很懒，什么都没写",
            "pet": {"name": card.pet_name, "breed": card.pet_breed, "level": card.pet_level},
            "signals": {
                "streak": card.streak_display,
                "longest_streak": card.longest_streak,
                "mastered": card.total_mastered_topics,
                "helped": card.helped_peers_count,
                "hours": round(card.total_hours_learned, 1),
                "rarest_badge": card.rarest_badge,
            },
            "visuals": {
                "avatar_frame": card.avatar_frame,
                "frame_color": frame["color"],
                "badges": card.badges_showcase,
            },
        }


# ═══════════════════════════════════════════════════════════
# 2. 社交系统 — Social Validation + Peer Recognition
# ═══════════════════════════════════════════════════════════

@dataclass
class SocialProfile:
    """社交画像"""
    user_id: str
    display_name: str
    friends_count: int = 0
    cheers_received: int = 0          # 收到的鼓励
    cheers_given: int = 0             # 发出的鼓励
    helped_others: int = 0
    was_helped: int = 0
    # 社交信号
    recognition_badges: List[str] = field(default_factory=list)
    social_score: float = 0.0         # 综合社交分


class SocialAddictionEngine:
    """社交成瘾引擎

    三大驱动:
    1. 社会验证: "同学给你的鼓励" → 多巴胺
    2. 互惠原则: "你帮助了ta,ta也会帮助你" → 社交纽带
    3. 信号展示: 名片就是你付出的证明 → 社会地位
    """

    @classmethod
    def cheer_peer(cls, from_user: str, to_user: str,
                    from_profile: SocialProfile,
                    to_profile: SocialProfile,
                    reason: str = "") -> dict:
        """给同学加油

        不是点赞——是"鼓励"。每次鼓励都附带一个具体理由。
        这让你和同学之间建立了具体的社交连接。
        """
        cheers = [
            "为你的坚持鼓掌！",
            "你的进步激励了我！",
            "一起加油！",
            "你昨天的那道题做得太棒了！",
            "看到你的努力，我也想学习了。",
        ]

        message = reason or random.choice(cheers)
        from_profile.cheers_given += 1
        to_profile.cheers_received += 1

        return {
            "action": "cheer_sent",
            "from": from_user,
            "to": to_user,
            "message": message,
            "effect": "对方会收到通知，看到你的鼓励。",
            "social_validation": True,
        }

    @classmethod
    def thank_peer(cls, from_user: str, helped_by: str) -> dict:
        """感谢帮助过你的同学"""
        return {
            "action": "thanks_sent",
            "message": f"感谢已发送！教学相长。",
            "social_bond": "感谢让社交连接更深。",
        }

    @classmethod
    def calculate_social_score(cls, profile: SocialProfile) -> float:
        """计算社交分数 — 虚荣指标 (Vanity Metric)

        这不是排名，是"你在社交中贡献了什么"的量化。
        """
        score = 0.0
        score += min(profile.cheers_received * 2, 50)
        score += min(profile.cheers_given * 3, 50)    # 给予比接受权重更高
        score += min(profile.helped_others * 10, 100)  # 帮助他人是最高权重
        score += min(profile.was_helped * 2, 20)
        score += min(len(profile.recognition_badges) * 15, 60)

        return min(score / 280 * 100, 100)

    @classmethod
    def get_peer_suggestions(cls, current_user: str,
                              all_peers: List[dict],
                              recent_interactions: List[str]) -> List[dict]:
        """智能推荐互动同学

        优先推荐:
        1. 最近没有互动的 (保持新鲜感)
        2. 学习阶段相似的 (有共鸣)
        3. 需要帮助的 (互惠机会)
        """
        suggestions = []
        for peer in all_peers:
            if peer["id"] == current_user:
                continue
            if peer["id"] in recent_interactions:
                continue

            reasons = []
            if peer.get("needs_help"):
                reasons.append("可能需要你的鼓励")
            if peer.get("stage") == peer.get("my_stage"):
                reasons.append("你们在同一学习阶段")
            if peer.get("streak") >= 7:
                reasons.append("坚持达人")

            suggestions.append({
                "peer_id": peer["id"],
                "peer_name": peer.get("name", ""),
                "peer_title": peer.get("title", ""),
                "reasons": reasons,
                "action": "cheer" if not peer.get("needs_help") else "encourage",
            })

        # 最多推荐5人
        random.shuffle(suggestions)
        return suggestions[:5]


# ═══════════════════════════════════════════════════════════
# 3. 家长沟通门户 — Parent Communication Portal
# ═══════════════════════════════════════════════════════════

@dataclass
class ParentMessage:
    """家长消息"""
    id: str
    teacher_id: str
    parent_id: str
    child_id: str
    subject: str
    content: str
    is_read: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reply: Optional[str] = None
    replied_at: Optional[datetime] = None


class ParentPortalEngine:
    """家长沟通门户

    家长不只是"查看报告"，而是"参与学习生态"。
    """

    @classmethod
    def generate_weekly_digest(cls, child_name: str, stats: dict,
                                 pet_name: str = "小豆") -> dict:
        """生成周报 — 家长可读的学习摘要"""
        return {
            "greeting": f"亲爱的{child_name}家长，您好！",
            "summary": cls._build_summary(stats, child_name, pet_name),
            "highlights": cls._build_highlights(stats),
            "areas_of_growth": cls._build_growth(stats),
            "addiction_report": cls._build_addiction_report(stats, child_name),
            "teacher_note": stats.get("teacher_note", ""),
            "parent_action_items": cls._build_parent_actions(stats),
            "next_week_preview": cls._build_next_week(stats),
        }

    @classmethod
    def generate_teacher_message_template(cls, child_name: str,
                                           concern_type: str,
                                           details: dict) -> dict:
        """生成教师消息模板 — 方便教师快速发送"""
        templates = {
            "progress": {
                "subject": f"{child_name}的学习进步报告",
                "template": f"好消息！{child_name}最近在{details.get('topic', '学习')}上取得了明显进步。"
                           f"正确率从{details.get('before', '—')}提升到{details.get('after', '—')}。"
                           f"建议在家也给予正向反馈。",
            },
            "concern": {
                "subject": f"关于{child_name}的学习关注",
                "template": f"我注意到{child_name}最近在{details.get('topic', '学习')}上遇到了一些困难。"
                           f"具体表现为{details.get('symptom', '')}。"
                           f"建议{details.get('advice', '多给予鼓励，不要施压。')}",
            },
            "addiction_good": {
                "subject": f"{child_name}已经爱上学习了！",
                "template": f"一个值得庆祝的消息：{child_name}已经连续{details.get('streak', 0)}天主动学习！"
                           f"学习习惯正在形成。这是非常积极的信号。"
                           f"建议：继续保持这个节奏，但也要确保有充足的休息和户外活动。",
            },
        }
        t = templates.get(concern_type, templates["progress"])
        return {**t, "child_name": child_name, "details": details}

    @classmethod
    def _build_summary(cls, stats, child_name, pet_name) -> str:
        streak = stats.get("current_streak", 0)
        accuracy = stats.get("weekly_accuracy", 0)
        questions = stats.get("weekly_questions", 0)
        addiction_stage = stats.get("addiction_stage", "exploring")

        stage_descriptions = {
            "exploring": f"{child_name}刚开始探索学习的世界。这是最关键的时期——建立积极的第一次学习体验。",
            "forming": f"{child_name}正在形成学习习惯。每天的小进步都在累积。",
            "hooked": f"{child_name}已经爱上了学习！连续{streak}天从未间断。",
            "automated": f"学习已经成为{child_name}的日常习惯，像呼吸一样自然。",
        }

        return (f"本周{child_name}完成了{questions}道题目，正确率{accuracy}%。"
                f"{stage_descriptions.get(addiction_stage, '')}"
                f"学习伙伴{pet_name}也在健康成长。")

    @classmethod
    def _build_highlights(cls, stats) -> List[str]:
        highlights = []
        if stats.get("new_topic_mastered"):
            highlights.append(f"🎉 新掌握了 {stats['new_topic_mastered']}")
        if stats.get("streak_achieved"):
            highlights.append(f"🔥 达到了 {stats['streak_achieved']} 天连续学习")
        if stats.get("helped_peer"):
            highlights.append(f"🤝 帮助了一位同学")
        if stats.get("badge_earned"):
            highlights.append(f"🏅 获得了 {stats['badge_earned']} 徽章")
        if not highlights:
            highlights.append("本周稳步前进中")
        return highlights

    @classmethod
    def _build_growth(cls, stats) -> List[str]:
        growth = []
        weak_topics = stats.get("weak_topics", [])
        if weak_topics:
            growth.append(f"正在加强的领域: {', '.join(weak_topics[:3])}")
        if stats.get("skip_ratio", 0) > 0.3:
            growth.append("遇到难题时有些回避，需要鼓励")
        return growth if growth else ["各领域均衡发展"]

    @classmethod
    def _build_addiction_report(cls, stats, child_name) -> dict:
        return {
            "stage": stats.get("addiction_stage", "exploring"),
            "is_positive": True,
            "message": f"{child_name}对学习的态度是积极的。这不是'上瘾'，这是'热爱'。",
            "usage_healthy": stats.get("daily_minutes", 0) < 120,
            "recommendation": "继续支持孩子的学习热情，同时确保户外活动、社交和睡眠的平衡。",
        }

    @classmethod
    def _build_parent_actions(cls, stats) -> List[str]:
        actions = []
        if stats.get("current_streak", 0) >= 3:
            actions.append("今天可以给孩子一个具体的表扬（不是'你真聪明'，而是'我看到你坚持了3天'）")
        if stats.get("helped_peer"):
            actions.append("问问孩子帮助同学是什么感觉——这是最好的学习反思")
        actions.append("确保孩子每天有至少1小时的户外活动")
        return actions

    @classmethod
    def _build_next_week(cls, stats) -> str:
        if stats.get("addiction_stage") in ("hooked", "automated"):
            return "继续保持节奏！下周可能有新知识领域解锁。"
        return "下周的目标：坚持每天学习一点点。量不重要，连续性重要。"


# ═══════════════════════════════════════════════════════════
# 4. 虚拟礼物系统 — Gift Economy
# ═══════════════════════════════════════════════════════════

class GiftEconomyEngine:
    """虚拟礼物系统

    不是氪金。礼物只能用"学习成果"换取。
    送礼物=消耗自己的一部分学习成果来认可他人。
    这是最昂贵的信号——你为别人付出了真实成本。
    """

    GIFTS = {
        "star": {"name": "学习之星", "cost_streak_days": 1, "icon": "⭐", "message": "认可你的坚持"},
        "flower": {"name": "知识之花", "cost_streak_days": 2, "icon": "🌸", "message": "你的进步让我感动"},
        "trophy": {"name": "榜样奖杯", "cost_streak_days": 5, "icon": "🏆", "message": "你是我的学习榜样"},
        "crystal": {"name": "水晶之心", "cost_streak_days": 10, "icon": "💎",
                     "message": "最珍贵的认可——你付出了真实的学习天数来鼓励ta"},
    }

    @classmethod
    def can_send_gift(cls, sender_streak: int, gift_id: str) -> dict:
        """检查是否有足够的学习成果来送出礼物"""
        gift = cls.GIFTS.get(gift_id)
        if not gift:
            return {"can_send": False, "reason": "礼物不存在"}

        if sender_streak >= gift["cost_streak_days"]:
            cost_pct = gift["cost_streak_days"] / max(sender_streak, 1) * 100
            return {
                "can_send": True,
                "gift": gift,
                "cost": gift["cost_streak_days"],
                "cost_pct": cost_pct,
                "message": f"送出这个礼物将消耗你 {gift['cost_streak_days']} 天的学习成果。这是你对ta的最高认可。",
            }
        else:
            return {
                "can_send": False,
                "gift": gift,
                "need_more": gift["cost_streak_days"] - sender_streak,
                "message": f"还需要坚持学习 {gift['cost_streak_days'] - sender_streak} 天才能送出这个礼物。",
            }

    @classmethod
    def send_gift(cls, sender_name: str, receiver_name: str,
                   gift_id: str) -> dict:
        """送出礼物"""
        gift = cls.GIFTS.get(gift_id, cls.GIFTS["star"])
        return {
            "action": "gift_sent",
            "gift": gift,
            "message": f"{sender_name} 送给 {receiver_name} 一个{gift['icon']}{gift['name']}：{gift['message']}",
            "social_signal": f"这是用{sender_name}的真实学习天数换来的。",
            "receiver_notification": f"{sender_name} 送了你一个{gift['icon']}{gift['name']}！",
        }
