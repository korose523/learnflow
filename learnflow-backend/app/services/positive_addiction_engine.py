"""正向学习成瘾引擎 — Learning Addiction Engineering

基于行为上瘾研究，将学习设计为具有可持续吸引力的习惯形成活动。

核心原理:
  1. Hook 模型 (Nir Eyal) — Trigger → Action → Variable Reward → Investment
  2. 习惯循环 (Duhigg)   — Cue → Routine → Reward
  3. 身份习惯 (Clear)     — Identity → Process → Outcome
  4. 承诺升级 (Cialdini)  — 微小承诺 → 逐步升级 → 不可逆投入
  5. 社交传染 (Christakis) — 行为在社交网络中传播

设计哲学:
  学习成瘾 = 高频触发 × 低阻力动作 × 不可预测奖励 × 持续投入
  目标: 让"每天学习"像"每天刷牙"一样自动发生。
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. HOOK 模型 — 上瘾四步循环
# ═══════════════════════════════════════════════════════════

class TriggerType(str, Enum):
    EXTERNAL_PUSH = "external_push"       # 推送通知
    EXTERNAL_PET = "external_pet"         # 宠物呼唤
    EXTERNAL_TIME = "external_time"       # 时间触发
    INTERNAL_BOREDOM = "internal_boredom" # "无聊了→学一题"
    INTERNAL_CURIOSITY = "internal_curiosity"  # "想知道下一题是什么"
    SOCIAL_PEER = "social_peer"           # 同学在学


class RewardVariability(str, Enum):
    FIXED = "fixed"           # 固定奖励 (最弱)
    VARIABLE_RATIO = "vr"     # 变比率 (最强)
    VARIABLE_INTERVAL = "vi"  # 变间隔 (中)
    VARIABLE_MAGNITUDE = "vm"  # 变幅度 (中强)


@dataclass
class HookState:
    """用户上瘾状态追踪"""
    user_id: str
    # Hook 循环计数
    total_loops_completed: int = 0
    loops_today: int = 0
    current_phase: str = "idle"  # idle → triggered → acting → rewarded → investing → idle

    # 触发响应率
    trigger_count: int = 0
    trigger_response_count: int = 0  # 触发后实际行动的比率

    # 奖励灵敏度
    last_reward_time: Optional[datetime] = None
    reward_drought_minutes: float = 0.0  # 多久没得到奖励了

    # 投入深度
    total_time_invested_minutes: float = 0.0
    content_created_count: int = 0       # 用户创建了多少内容
    pet_level: int = 1
    identity_strength: float = 0.0       # "我是学习者" 身份强度


class HookEngine:
    """上瘾循环引擎 — 实现 Hook 四步模型"""

    @classmethod
    def trigger(cls, state: HookState, trigger_type: TriggerType,
                context: dict = None) -> dict:
        """步骤1: 触发

        外部触发: 推送、宠物提醒、同学动态
        内部触发: 负面情绪(无聊) → "做一题转换心情"
        """
        state.current_phase = "triggered"
        state.trigger_count += 1
        context = context or {}

        triggers = {
            TriggerType.EXTERNAL_PET: {
                "message": "小豆想你了……来看看今天的新题目？",
                "cta": "来一题",
                "action_cost": "约2分钟",
                "trigger_strength": 0.7,
            },
            TriggerType.EXTERNAL_TIME: {
                "message": "又到学习时间了！昨天的你比前天更强了一点。",
                "cta": "开始学习",
                "action_cost": "自由选择",
                "trigger_strength": 0.5,
            },
            TriggerType.EXTERNAL_PUSH: {
                "message": "你有一道未完成的题目在等你！",
                "cta": "继续完成",
                "action_cost": "续接上次",
                "trigger_strength": 0.6,
            },
            TriggerType.INTERNAL_CURIOSITY: {
                "message": "下一题会是什么呢？",
                "cta": "探索",
                "action_cost": "1题",
                "trigger_strength": 0.8,
            },
            TriggerType.SOCIAL_PEER: {
                "message": f"{context.get('peer_count', 3)}位同学正在学习，要不要一起？",
                "cta": "加入",
                "action_cost": "随时开始",
                "trigger_strength": 0.65,
            },
        }

        return triggers.get(trigger_type, triggers[TriggerType.EXTERNAL_PET])

    @classmethod
    def action(cls, state: HookState) -> dict:
        """步骤2: 行动 — 简化到极致

        原则: BJ Fogg 行为模型 B=MAT
        Behavior = Motivation × Ability × Trigger
        能力最大化 = 把行动门槛降到最低
        """
        state.current_phase = "acting"
        state.trigger_response_count += 1

        return {
            "simplest_action": "做1道题",
            "time_estimate": "1-2分钟",
            "friction_reduction": [
                "已自动登录，无需密码",
                "接续上次进度，无需选择",
                "一键开始，无需菜单导航",
            ],
            "two_minute_rule": "如果不想做，只做1道题就好。1道题也可以。",
            "action_taken": True,
        }

    @classmethod
    def reward(cls, state: HookState, is_correct: bool, streak: int,
               pet_name: str = "小豆") -> dict:
        """步骤3: 变比率奖励 — 成瘾的核心

        三类可变奖励 (Nir Eyal Hook Model):
        1. Tribe Reward (部落): 社交认同、被需要的感觉
        2. Hunt Reward (狩猎): 信息获取、"就差一点"的期待
        3. Self Reward (自我): 掌控感、能力提升的满足
        """
        state.current_phase = "rewarded"
        state.last_reward_time = datetime.now(UTC)
        state.loops_today += 1
        state.total_loops_completed += 1

        # 奖励变异性 — 决定成瘾强度
        reward_pool = []

        # Self Reward: 能力提升信号
        if is_correct and streak >= 3:
            reward_pool.append({"type": "self_mastery", "icon": "🧠",
                "message": f"连续{streak}题正确！你的{pet_name}能力值在增长。",
                "dopamine_peak": 0.7 + streak * 0.03})

        # Hunt Reward: 信息获取期待
        if random.random() < 0.4:
            topics = ["分数运算", "几何图形", "应用题", "代数思维", "概率入门"]
            preview_topic = random.choice(topics)
            reward_pool.append({"type": "hunt_preview", "icon": "🔮",
                "message": f"预告：下一阶段将解锁「{preview_topic}」！",
                "dopamine_peak": 0.6})

        # Tribe Reward: 社交认同
        if random.random() < 0.3:
            reward_pool.append({"type": "tribe_belonging", "icon": "👥",
                "message": f"今天已有{random.randint(8, 35)}位同学完成了学习。你也在这支队伍中。",
                "dopamine_peak": 0.55})

        # Near-Miss Reward: 差一点的期待（最强成瘾触发器）
        if not is_correct and random.random() < 0.5:
            reward_pool.append({"type": "hunt_near_miss", "icon": "💡",
                "message": "差一点就对了！再来一次，你一定能突破。",
                "dopamine_peak": 0.9})

        # 随机超级奖励 (1/15概率)
        if random.random() < 0.067:
            reward_pool.append({"type": "super_reward", "icon": "💎",
                "message": f"🌟 稀有奖励！{pet_name}发现了隐藏的能力宝石！今天所有题目双倍成长！",
                "dopamine_peak": 1.0})

        # 确保至少有一种奖励
        if not reward_pool:
            reward_pool = [{"type": "self_progress", "icon": "📈",
                "message": "又完成了一题！每一次练习都在重塑你的大脑。",
                "dopamine_peak": 0.4}]

        chosen = random.choice(reward_pool)

        # 奖励干旱检测 — 太久没奖励会降低动机
        if state.last_reward_time:
            state.reward_drought_minutes = 0.0
        else:
            state.reward_drought_minutes += 1.0

        return {
            "reward": chosen,
            "all_rewards": reward_pool,
            "variability_type": RewardVariability.VARIABLE_MAGNITUDE,
            "dopamine_peak": chosen["dopamine_peak"],
            "drought_warning": state.reward_drought_minutes > 10,
        }

    @classmethod
    def investment(cls, state: HookState, action: str, data: dict = None) -> dict:
        """步骤4: 投入 — 让用户"存入"一些东西

        投入越多 → 下次回来的可能性越大 (禀赋效应+沉没成本)
        """
        state.current_phase = "investing"
        data = data or {}
        state.total_time_invested_minutes += data.get("minutes", 1)

        investments = []
        if action == "customize_pet":
            investments.append({"type": "pet_personalized", "message": "宠物越来越像你了。",
                                "future_value": "你离开越久，小豆越想你。"})
        elif action == "set_goal":
            goal = data.get("goal", 10)
            investments.append({"type": "goal_committed", "message": f"你承诺每天完成{goal}题。",
                                "future_value": f"这是你自己的约定。完成率会比别人设定的目标高40%。"})
        elif action == "create_note":
            investments.append({"type": "content_created", "message": "你留下了自己的思考笔记。",
                                "future_value": "这些笔记会随着你的成长变得越来越有价值。"})
        elif action == "build_streak":
            streak = data.get("streak", 1)
            if streak >= 7:
                investments.append({"type": "streak_sunk_cost", "message": f"你已经坚持了{streak}天！",
                                    "future_value": f"如果现在放弃，{streak}天的努力就会中断。"})
        else:
            investments.append({"type": "time_invested", "message": "今天的努力是明天的基石。",
                                "future_value": "每次学习都在增强你的知识网络。"})

        return {"investments": investments, "total_time_invested": round(state.total_time_invested_minutes),
                "hook_complete": True}


# ═══════════════════════════════════════════════════════════
# 2. 习惯循环引擎 — Cue → Routine → Reward
# ═══════════════════════════════════════════════════════════

@dataclass
class HabitState:
    """习惯形成状态"""
    target_time: Optional[str] = None     # 目标学习时间 (如 "19:00")
    current_streak_days: int = 0
    best_streak_days: int = 0
    total_days_learned: int = 0
    habit_strength: float = 0.0           # 0-1, 习惯自动化程度
    last_cue_at: Optional[datetime] = None
    cue_effectiveness: float = 0.5        # 触发有效性


class HabitLoopEngine:
    """习惯循环引擎 — 让学习自动化"""

    # 习惯形成所需的平均天数 (Lally et al. 2009)
    HABIT_FORMATION_DAYS = 66

    @classmethod
    def set_habit_cue(cls, state: HabitState, cue_type: str, cue_detail: str) -> dict:
        """设置习惯触发点

        Science: 明确的 "I will [BEHAVIOR] at [TIME] in [LOCATION]" 格式最有效
        """
        if cue_type == "time":
            state.target_time = cue_detail
            return {
                "implementation_intention": f"每天 {cue_detail}，我会打开LearnFlow",
                "cue_type": "time",
                "cue": cue_detail,
                "habit_stacking_tip": "把学习安排在现有的习惯之后，比如'吃完晚饭就学一题'",
            }
        elif cue_type == "after_event":
            return {
                "implementation_intention": f"每次 {cue_detail} 之后，我会打开LearnFlow",
                "cue_type": "after_event",
                "cue": cue_detail,
                "habit_stacking_tip": f"把学习链接到 {cue_detail} 这个已有的习惯上",
            }
        return {"implementation_intention": "每天在固定时间打开LearnFlow", "cue_type": "whenever"}

    @classmethod
    def record_session(cls, state: HabitState) -> dict:
        """记录一次学习会话，更新习惯强度"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        state.total_days_learned += 1

        # 习惯强度: 基于总学习天数 / 习惯形成天数
        state.habit_strength = min(1.0, state.total_days_learned / cls.HABIT_FORMATION_DAYS)

        phase = "initiation" if state.total_days_learned < 7 else \
                "struggling" if state.total_days_learned < 21 else \
                "forming" if state.total_days_learned < cls.HABIT_FORMATION_DAYS else \
                "automated"

        phase_msgs = {
            "initiation": "习惯种子已种下。前7天最关键，坚持住！",
            "struggling": "你在形成新神经通路。有点难是正常的，这是大脑在重组。",
            "forming": f"习惯正在固化！再坚持{cls.HABIT_FORMATION_DAYS - state.total_days_learned}天就自动化了。",
            "automated": "学习已经成为你的自动行为。大脑为学习建立了专用通道。",
        }

        return {
            "habit_strength": round(state.habit_strength, 2),
            "habit_strength_pct": round(state.habit_strength * 100),
            "phase": phase,
            "phase_message": phase_msgs[phase],
            "days_to_automation": max(0, cls.HABIT_FORMATION_DAYS - state.total_days_learned),
            "cue_reminder": f"明天的 {state.target_time or '同一时间'} 见！" if state.target_time else "明天见！",
        }

    @classmethod
    def get_cue_prompt(cls, state: HabitState) -> Optional[dict]:
        """在目标时间临近时生成提示"""
        if not state.target_time:
            return None
        now = datetime.now(UTC)
        try:
            target_h, target_m = map(int, state.target_time.split(":"))
        except (ValueError, AttributeError):
            return None
        current_minutes = now.hour * 60 + now.minute
        target_minutes = target_h * 60 + target_m
        minutes_until = target_minutes - current_minutes

        if 0 <= minutes_until <= 30:
            return {
                "should_notify": True,
                "message": f"快到你的学习时间 ({state.target_time}) 了！小豆已经准备好了。",
                "minutes_until": minutes_until,
            }
        return {"should_notify": False, "minutes_until": minutes_until}


# ═══════════════════════════════════════════════════════════
# 3. 身份强化引擎 — Identity-Based Habits
# ═══════════════════════════════════════════════════════════

class IdentityEngine:
    """身份强化引擎

    James Clear: 真正的行为改变是身份的改变。
    目标不是"每天做10道题"，而是"我是一个学习者"。

    每完成一次学习，系统都会提供微小证据来强化这个身份。
    """

    IDENTITY_TYPES = {
        "persistent": {
            "label": "坚持者",
            "trigger": lambda s: s.get("current_streak", 0) >= 3,
            "affirmation": "你是一个坚持者。困难不能让你停下。",
        },
        "curious": {
            "label": "探索者",
            "trigger": lambda s: s.get("topics_explored", 0) >= 3,
            "affirmation": "你天生好奇。知识的世界因你而展开。",
        },
        "resilient": {
            "label": "韧性者",
            "trigger": lambda s: s.get("failure_recovery", 0) >= 5,
            "affirmation": "错误让你更强。你在从每一次跌倒中学习。",
        },
        "focused": {
            "label": "专注者",
            "trigger": lambda s: s.get("focus_sessions", 0) >= 5,
            "affirmation": "你有深度专注的能力。这比聪明更稀有。",
        },
        "growing": {
            "label": "成长者",
            "trigger": lambda s: s.get("total_attempts", 0) >= 50,
            "affirmation": "你在持续成长。每一天都比昨天更接近你想成为的人。",
        },
        "helper": {
            "label": "分享者",
            "trigger": lambda s: s.get("help_others", 0) >= 1,
            "affirmation": "你乐于帮助他人。教学相长，你的理解也因此更深。",
        },
    }

    @classmethod
    def assess_identity(cls, stats: dict) -> dict:
        """评估并强化学习者身份"""
        active_identities = []
        all_affirmations = []

        for key, identity in cls.IDENTITY_TYPES.items():
            if identity["trigger"](stats):
                active_identities.append(identity["label"])
                all_affirmations.append(identity["affirmation"])

        if not active_identities:
            active_identities = ["初学者"]
            all_affirmations = ["每一位大师都曾是初学者。你正在路上。"]

        identity_statement = " · ".join(active_identities)
        primary_affirmation = random.choice(all_affirmations) if all_affirmations else ""

        return {
            "identity": identity_statement,
            "affirmation": primary_affirmation,
            "identity_count": len(active_identities),
            "identity_message": f"你的学习画像: {identity_statement}",
            "growth_mindset_nudge": "能力不是固定的。每一次练习，你都在变得更强。",
        }


# ═══════════════════════════════════════════════════════════
# 4. 承诺升级引擎 — Commitment Escalator
# ═══════════════════════════════════════════════════════════

@dataclass
class CommitmentState:
    """承诺升级状态"""
    public_goal_set: bool = False
    public_goal: Optional[str] = None
    declaration_date: Optional[datetime] = None
    commitment_level: int = 0  # 0-5
    promises_made: List[str] = field(default_factory=list)
    promises_kept: int = 0


class CommitmentEscalator:
    """承诺升级引擎

    Cialdini: 一旦做出小的公开承诺，人们倾向于做出更大的承诺来保持一致。

    阶梯:
    Lv1: "每天做1题"     (微小承诺)
    Lv2: "连续3天"       (时间承诺)
    Lv3: "完成一个主题"  (深度承诺)
    Lv4: "帮助一位同学"  (社交承诺)
    Lv5: "创建自己的学习路径" (创作承诺)
    """

    COMMITMENT_LADDER = [
        {"level": 1, "action": "daily_one", "label": "每天至少做1题", "escalation": "你已经证明可以每天做1题了"},
        {"level": 2, "action": "streak_three", "label": "连续学习3天", "escalation": "3天之后是1周，1周之后是1个月"},
        {"level": 3, "action": "master_topic", "label": "完全掌握一个知识点", "escalation": "掌握一个，你就可以掌握所有"},
        {"level": 4, "action": "help_peer", "label": "帮助一位同学理解一道题", "escalation": "最好的学习方式是教别人"},
        {"level": 5, "action": "create_path", "label": "创建你自己的学习路径", "escalation": "你现在不仅是学习者，也是引导者"},
    ]

    @classmethod
    def offer_next_commitment(cls, state: CommitmentState) -> dict:
        """提供下一个承诺台阶"""
        next_level = state.commitment_level + 1
        if next_level > len(cls.COMMITMENT_LADDER):
            return {"has_next": False, "message": "你已经走完了整个承诺阶梯！你是真正的学习引领者。"}

        step = cls.COMMITMENT_LADDER[next_level - 1]
        return {
            "has_next": True,
            "next_level": step["level"],
            "action": step["action"],
            "label": step["label"],
            "escalation": step["escalation"],
            "commitment_prompt": f"你愿意接受这个挑战吗？一旦接受，你会更可能完成它。",
        }

    @classmethod
    def accept_commitment(cls, state: CommitmentState, level: int, action: str,
                           label: str) -> dict:
        """接受承诺"""
        state.commitment_level = level
        state.promises_made.append(label)
        state.public_goal_set = True
        state.public_goal = label
        state.declaration_date = datetime.now(UTC)

        return {
            "accepted": True,
            "commitment_level": level,
            "label": label,
            # 公开声明的力量
            "public_commitment_message": f"你公开承诺了：{label}。研究表明，公开承诺的完成率提高65%。",
            "consistency_nudge": "你是一个说到做到的人。",
        }

    @classmethod
    def celebrate_fulfillment(cls, state: CommitmentState) -> dict:
        """庆祝承诺兑现"""
        state.promises_kept += 1
        return {
            "celebrated": True,
            "promises_kept": state.promises_kept,
            "total_promises": len(state.promises_made),
            "message": f"你兑现了承诺！你说到做到。",
            "identity_strengthened": "你是一个有信誉的学习者。",
        }


# ═══════════════════════════════════════════════════════════
# 5. 社交传染引擎 — Social Contagion
# ═══════════════════════════════════════════════════════════

class SocialContagionEngine:
    """社交传染引擎

    行为在社交网络中像病毒一样传播。
    Christakis & Fowler: 你的朋友的学习习惯会影响你。
    不使用排名（避免焦虑），使用归属感和积极比较。
    """

    @classmethod
    def get_social_proof_moment(cls, class_data: dict) -> dict:
        """获取社交证明时刻"""
        moments = []

        # 最活跃时段
        if class_data.get("most_active_hour"):
            moments.append({
                "type": "bandwagon",
                "message": f"班级最活跃的时段是 {class_data['most_active_hour']}，大多数同学都在这个时候学习。",
                "nudge": "试试在这个时段加入大家？",
            })

        # 每日进步最快
        if class_data.get("most_improved_topic"):
            moments.append({
                "type": "positive_deviance",
                "message": f"今天最多同学突破的知识点是「{class_data['most_improved_topic']}」。",
                "nudge": "这个知识点你也可以挑战看看！",
            })

        return {"moments": moments, "has_social_context": bool(moments)}

    @classmethod
    def get_friendly_competition_nudge(cls, user_stats: dict,
                                        peer_stats: dict) -> dict:
        """温和的社交竞争推动

        注意: 不暴露具体排名，只提供正向比较。
        不创造"输赢"，创造"一起进步"。
        """
        nudges = []

        if user_stats.get("streak", 0) > 0 and peer_stats.get("max_streak", 0) > user_stats.get("streak", 0):
            nudges.append({
                "type": "streak_inspiration",
                "message": f"班上有同学坚持了 {peer_stats['max_streak']} 天！你们都在变得更好。",
                "emotion": "inspired",
            })

        if user_stats.get("weekly_accuracy", 0) < peer_stats.get("class_avg_accuracy", 0):
            nudges.append({
                "type": "growth_opportunity",
                "message": "你的正确率在稳步提升，每个学习者都有自己的节奏。",
                "emotion": "encouraging",
            })

        peer_count = peer_stats.get("active_peers", 0)
        if peer_count >= 5:
            nudges.append({
                "type": "together_stronger",
                "message": f"今天{peer_count}位同学完成了学习。你们是一个学习共同体。",
                "emotion": "belonging",
            })

        return {"nudges": nudges, "focus": "growth_not_ranking", "message": "学习不是竞赛，但我们可以一起走得更远。"}

    @classmethod
    def get_ripple_effect_message(cls, user_helped_count: int) -> dict:
        """涟漪效应：你的帮助影响了多少人"""
        if user_helped_count == 0:
            return {"show": False}
        return {
            "show": True,
            "message": f"你帮助了 {user_helped_count} 位同学。因为你的帮助，他们多完成了一道题。",
            "ripple": f"你的帮助可能影响了 {user_helped_count * 3} 道额外的题目被完成。",
            "social_value": "你在创造学习涟漪。",
        }


# ═══════════════════════════════════════════════════════════
# 6. 即时满足引擎 — Instant Gratification
# ═══════════════════════════════════════════════════════════

class InstantGratificationEngine:
    """即时满足引擎

    人类大脑天生偏好即时奖励（现时偏差 Present Bias）。
    游戏上瘾的关键: 即时、频繁、可视化的反馈。

    实现: 每道题后 3 秒内给出多维度即时反馈。
    """

    @classmethod
    def generate_instant_feedback(cls, is_correct: bool, topic: str,
                                   pet_name: str = "小豆", streak: int = 0,
                                   session_progress: float = 0.0) -> dict:
        """生成即时多维反馈包"""
        feedback = {
            "timestamp_ms": 0,
            "phases": [],
        }

        if is_correct:
            # 多维度即时反馈
            dimensions = [
                {"label": "正确", "icon": "✅", "animation": "check_pop",
                 "duration_ms": 400},
                {"label": f"+{10 + streak}经验", "icon": "⚡", "animation": "xp_float",
                 "duration_ms": 600},
            ]
            if streak == 0:
                dimensions.append({"label": "新开始！", "icon": "🌱", "animation": "sprout"})
            elif streak >= 5:
                dimensions.append({"label": f"{streak}连对", "icon": "🔥", "animation": "streak_fire"})

            feedback["phases"] = [
                {"name": "instant_visual", "duration_ms": 300, "animation": "correct_flash"},
                {"name": "dimension_drops", "duration_ms": 800, "dimensions": dimensions},
                {"name": "pet_reaction", "duration_ms": 1200,
                 "message": f"{pet_name}为你开心！" if streak < 5 else f"{pet_name}跳起来庆祝！"},
                {"name": "anticipation", "duration_ms": 700,
                 "message": f"下一题将检验 {topic} 的掌握程度"},
            ]
        else:
            feedback["phases"] = [
                {"name": "gentle_indicator", "duration_ms": 300, "animation": "gentle_shake"},
                {"name": "pet_encourage", "duration_ms": 1200,
                 "message": f"{pet_name}: 没关系，这是大脑在建立新连接。"},
                {"name": "recovery_invite", "duration_ms": 700,
                 "message": "看看关键步骤？或者再试一次？"},
            ]

        # 进度脉冲: 接近完成时加速反馈
        if session_progress > 0.8:
            feedback["progress_pulse"] = True
            feedback["progress_message"] = f"快完成了！还差{round((1 - session_progress) * 100)}%"

        return feedback


# ═══════════════════════════════════════════════════════════
# 7. 成长可视化引擎 — Progress Visualization
# ═══════════════════════════════════════════════════════════

class ProgressVisualizationEngine:
    """成长可视化引擎

    Dweck: 看到进步本身是最强的内在激励。
    让看不见的成长变得可见、具体、可触摸。
    """

    @classmethod
    def generate_weekly_growth_report(cls, stats: dict) -> dict:
        """生成每周成长报告"""
        report = {
            "skills_unlocked": stats.get("new_skills", 0),
            "total_questions": stats.get("weekly_questions", 0),
            "accuracy_trend": stats.get("accuracy_trend", "stable"),
            "growth_moments": [],
            "one_percent_better": True,
        }

        # 1% 进步哲学
        if stats.get("accuracy_improved"):
            report["growth_moments"].append({
                "type": "accuracy_growth",
                "message": "你的正确率比上周提升了。每天进步1%，一年后你会强大37倍。",
            })

        if stats.get("new_topic_mastered"):
            report["growth_moments"].append({
                "type": "new_domain",
                "message": f"你征服了一个全新的知识领域: {stats['new_topic_mastered']}",
            })

        if stats.get("hardest_solved"):
            report["growth_moments"].append({
                "type": "challenge_overcome",
                "message": f"你完成了本周最难的题目之一: 难度{stats['hardest_difficulty']}",
            })

        report["identity_anchor"] = "你不是在做题。你在构建自己的知识体系。每一题都是这个体系的一块砖。"

        return report

    @classmethod
    def generate_knowledge_map(cls, skills: Dict[str, float]) -> dict:
        """生成知识地图 — 让学生看到自己的知识版图在扩张"""
        nodes = []
        for skill_name, mastery in skills.items():
            nodes.append({
                "name": skill_name,
                "mastery": round(mastery, 2),
                "mastery_pct": round(mastery * 100),
                "size": max(5, round(mastery * 100)),
                "status": "mastered" if mastery > 0.8 else "developing" if mastery > 0.4 else "exploring",
            })

        mastered_count = sum(1 for n in nodes if n["status"] == "mastered")

        return {
            "nodes": nodes,
            "total_skills": len(nodes),
            "mastered": mastered_count,
            "completeness_pct": round(mastered_count / max(len(nodes), 1) * 100),
            "map_message": "这是你的知识版图。每一个点都是你亲自点亮的。",
        }
