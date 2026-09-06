"""元学习技能树 — Meta-Learning Skill Tree Gamification

将"学会如何学习"本身变成一个RPG式的技能成长系统。

设计理念:
  知识技能(学什么) × 学习技能(怎么学) = 真正的学习能力
  每个学习方法都是一棵可升级的技能树。

16个学习技能，每个都有:
  - 熟练度等级 (Lv.1-10)
  - 经验值 (XP)
  - 使用次数追踪
  - 等级奖励 (解锁新能力)
  - 技能组合加成 (同时使用多种方法有combo)
  - 全局元学习等级 (Meta-Learning Level)
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import random

from app.services.state_store import StateStore, MemoryStateStore


# ═══════════════════════════════════════════════════════════
# 1. 学习技能定义 — 16种方法的RPG属性
# ═══════════════════════════════════════════════════════════

class SkillCategory(str, Enum):
    MEMORY = "memory"           # 记忆类
    UNDERSTANDING = "understanding"  # 理解类
    PRACTICE = "practice"       # 练习类
    FOCUS = "focus"             # 专注类
    MINDSET = "mindset"         # 心态类


@dataclass
class LearningSkill:
    """学习技能 — RPG属性"""
    skill_id: str
    name: str
    category: SkillCategory
    icon: str
    level: int = 1                    # 1-10
    xp: int = 0                        # 当前等级经验
    xp_to_next: int = 50               # 升级所需经验
    times_used: int = 0
    unlocked: bool = True              # 是否解锁
    description: str = ""
    # 等级奖励
    level_bonuses: Dict[int, str] = field(default_factory=dict)
    # 前置技能 (必须先解锁某些技能)
    prerequisites: List[str] = field(default_factory=list)


# ─── 16学习技能的完整定义 ─────────────────────

SKILL_DEFINITIONS = [
    # 记忆类 (Memory)
    LearningSkill(
        skill_id="active_recall", name="主动回忆", category=SkillCategory.MEMORY,
        icon="🧠", description="先回忆再看答案的自我测试法",
        level_bonuses={3: "回忆速度+15%", 5: "解锁'闪电回忆'(1秒内回忆)", 7: "记忆提取效率翻倍", 10: "过目不忘——答过的题永不遗忘"},
    ),
    LearningSkill(
        skill_id="spaced_repetition", name="间隔重复", category=SkillCategory.MEMORY,
        icon="⏰", description="在遗忘临界点复习",
        level_bonuses={3: "复习间隔延长20%", 5: "解锁'智能复习'(系统自动最优排期)", 7: "遗忘曲线变平缓", 10: "永久记忆——掌握的知识永不褪色"},
    ),
    LearningSkill(
        skill_id="memory_palace", name="记忆宫殿", category=SkillCategory.MEMORY,
        icon="🏰", prerequisites=["active_recall"],
        description="空间记忆编码——把知识放进虚拟空间",
        level_bonuses={3: "宫殿容量+2", 5: "解锁第二个宫殿", 7: "宫殿之间可以互通", 10: "无限宫殿——随心构建"},
    ),
    LearningSkill(
        skill_id="dual_coding", name="双重编码", category=SkillCategory.MEMORY,
        icon="🖼️", description="文字+图像双通道编码",
        level_bonuses={3: "图像记忆效率+20%", 5: "解锁'思维导图'自动生成", 7: "自动关联题目配图", 10: "过目成画——看到题目就浮现图像"},
    ),
    LearningSkill(
        skill_id="chunking", name="组块化", category=SkillCategory.MEMORY,
        icon="🧩", prerequisites=["active_recall"],
        description="将零散知识点打包成有意义的组块",
        level_bonuses={3: "工作记忆容量+1组块", 5: "自动识别可组块的知识", 7: "组块大小翻倍", 10: "超级组块——一个概念包含整个知识体系"},
    ),
    # 理解类 (Understanding)
    LearningSkill(
        skill_id="feynman", name="费曼技巧", category=SkillCategory.UNDERSTANDING,
        icon="📝", description="用最简单的话解释复杂概念",
        level_bonuses={3: "解释清晰度+20%", 5: "解锁'教给虚拟学生'(AI检测理解)", 7: "理解深度翻倍", 10: "一眼看透——能解释任何概念给任何人"},
    ),
    LearningSkill(
        skill_id="elaborative_rehearsal", name="精细复述", category=SkillCategory.UNDERSTANDING,
        icon="💬", description="用自己的话重新组织知识",
        level_bonuses={3: "复述准确度+20%", 5: "解锁'关联网络'(看到知识之间的联系)", 7: "自动关联5个知识点", 10: "知识元宇宙——所有知识点自动互连"},
    ),
    LearningSkill(
        skill_id="sq3r", name="SQ3R阅读法", category=SkillCategory.UNDERSTANDING,
        icon="📖", prerequisites=["active_recall"],
        description="结构化阅读:浏览→提问→阅读→复述→复习",
        level_bonuses={3: "阅读速度+25%", 5: "自动生成问题引导阅读", 7: "一遍阅读深度理解", 10: "过目成诵"},
    ),
    # 练习类 (Practice)
    LearningSkill(
        skill_id="retrieval_practice", name="检索练习", category=SkillCategory.PRACTICE,
        icon="🔍", description="从记忆中提取而非再认",
        level_bonuses={3: "检索速度+20%", 5: "每道题=一次强化测试", 7: "一次检索=4次阅读效果", 10: "超级检索——做题本身成为最强的学习武器"},
    ),
    LearningSkill(
        skill_id="interleaving", name="交错练习", category=SkillCategory.PRACTICE,
        icon="🔀", prerequisites=["retrieval_practice"],
        description="混合不同题型比集中练效果更好",
        level_bonuses={3: "题型混合度+25%", 5: "自动混合最佳题型组合", 7: "长期记忆效果+43%", 10: "万能解题者——任何题型都能自如应对"},
    ),
    LearningSkill(
        skill_id="testing_effect", name="测试效应", category=SkillCategory.PRACTICE,
        icon="✅", description="把测试当作学习工具而非评价工具",
        level_bonuses={3: "测试记忆效果+30%", 5: "解锁'挑战模式'(高难度自测)", 7: "一次测试=重新学习4次", 10: "测试大师——享受被测试的过程"},
    ),
    # 专注类 (Focus)
    LearningSkill(
        skill_id="pomodoro", name="番茄学习法", category=SkillCategory.FOCUS,
        icon="🍅", description="25分钟深度专注+5分钟科学休息",
        level_bonuses={3: "专注时长+5分钟", 5: "解锁'深度心流'(自动进入心流状态)", 7: "连续专注60分钟不衰减", 10: "永恒心流——随时进入最佳学习状态"},
    ),
    LearningSkill(
        skill_id="deep_work", name="深度工作", category=SkillCategory.FOCUS,
        icon="🔒", prerequisites=["pomodoro"],
        description="不受干扰的高强度认知投入",
        level_bonuses={3: "抗干扰能力+30%", 5: "深度工作期间经验翻倍", 7: "自动屏蔽所有干扰通知", 10: "绝对专注——一小时内完成常人一天的学习量"},
    ),
    # 心态类 (Mindset)
    LearningSkill(
        skill_id="growth_mindset", name="生长型思维", category=SkillCategory.MINDSET,
        icon="🌱", description="相信能力可以通过努力提升",
        level_bonuses={3: "从错误中学习的效率+25%", 5: "挑战接受度+50%", 7: "不再害怕错题——错题='成长信号'", 10: "无敌心态——任何困难都是成长的机会"},
    ),
    LearningSkill(
        skill_id="metacognition", name="元认知", category=SkillCategory.MINDSET,
        icon="🤔", prerequisites=["growth_mindset"],
        description="对自己学习过程的觉察与反思",
        level_bonuses={3: "学习效率感知+20%", 5: "自动识别最佳学习策略", 7: "自我纠偏能力——发现并修正学习误区", 10: "终极学习者——完全掌握自己的学习模式"},
    ),
    LearningSkill(
        skill_id="sleep_mastery", name="睡眠学习法", category=SkillCategory.MINDSET,
        icon="😴", description="利用睡眠巩固记忆——睡前的复习最有效",
        level_bonuses={3: "睡眠记忆巩固+15%", 5: "睡前复习效果翻倍", 7: "在睡觉中自动巩固当天知识", 10: "梦中学习——潜意识在睡眠中继续学习"},
    ),
]


# ═══════════════════════════════════════════════════════════
# 2. 技能树引擎 — 管理所有学习技能
# ═══════════════════════════════════════════════════════════

class SkillTreeEngine:
    """技能树引擎

    管理16个学习技能的升级、解锁、组合加成。
    """

    # 技能树引擎内缓存 —— 显式保持内存语义（MemoryStateStore，不切 default_state_store）
    # 真正的落库已由 progression_repository.save_skill_tree 在 orchestrator 侧承担
    # （DB 模型见 app/models/progression.py:SkillTreeState），此容器仅为进程内缓存。
    # 若也切到 JSON 后端，会出现「内存缓存 + JSON 文件 + DB」三份真相来源，重启后
    # 以哪份为准无法判定，反而制造数据不一致，故刻意保持 MemoryStateStore。
    PLAYER_SKILLS: StateStore = MemoryStateStore()

    @classmethod
    def init_player_skills(cls, user_id: str) -> Dict[str, LearningSkill]:
        """初始化玩家的技能树 — 前4个技能初始解锁"""
        skills = {}
        for defn in SKILL_DEFINITIONS:
            skill = LearningSkill(**{k: v for k, v in defn.__dict__.items()
                                       if not k.startswith('_')})
            # 前5个技能(主动回忆/间隔重复/精细复述/生长型思维/检索练习)初始解锁
            skill.unlocked = not skill.prerequisites or all(
                p in ["active_recall", "spaced_repetition", "elaborative_rehearsal",
                      "growth_mindset", "retrieval_practice"]
                for p in skill.prerequisites
            ) or skill.skill_id in ["active_recall", "spaced_repetition",
                                      "elaborative_rehearsal", "growth_mindset",
                                      "retrieval_practice"]
            # 简化: 无前置技能=已解锁
            skill.unlocked = len(skill.prerequisites) == 0 or skill.skill_id in [
                "active_recall", "spaced_repetition", "elaborative_rehearsal",
                "growth_mindset", "retrieval_practice", "pomodoro", "testing_effect",
                "chunking", "dual_coding", "sq3r", "feynman"
            ]
            # 高难度技能需要前置解锁
            if skill.prerequisites:
                # 检查是否所有前置都在这11个初始解锁中
                all_unlocked = all(p in [
                    "active_recall", "spaced_repetition", "elaborative_rehearsal",
                    "growth_mindset", "retrieval_practice", "pomodoro", "testing_effect",
                    "chunking", "dual_coding", "sq3r", "feynman"
                ] for p in skill.prerequisites)
                skill.unlocked = all_unlocked

            skills[skill.skill_id] = skill
        cls.PLAYER_SKILLS.set(user_id, skills)
        return skills

    @classmethod
    def use_skill(cls, user_id: str, skill_id: str,
                   effectiveness: float = 1.0,
                   db: Optional["AsyncSession"] = None) -> dict:
        """使用某个学习技能 — 获得XP

        ``db`` 为可选参数: 预留给调用方 (learning_orchestrator) 传入会话以便
        自愈式持久化 (PLAYER_SKILLS 为 StateStore 内存后端, 重启即丢)。保持同步签名
        以维持既有调用方兼容; 真正落库由接管的协程负责, 此处仅透传占位。
        """
        skills = cls.PLAYER_SKILLS.get(user_id)
        if not skills:
            skills = cls.init_player_skills(user_id)

        skill = skills.get(skill_id)
        if not skill:
            return {"used": False, "message": "技能不存在"}

        if not skill.unlocked:
            return {"used": False, "message": f"技能 [{skill.name}] 尚未解锁！",
                    "prerequisites": skill.prerequisites}

        skill.times_used += 1

        # XP 计算: 基础10 + 使用频率加成
        xp_gain = int(10 * effectiveness)
        skill.xp += xp_gain

        # 升级检查
        leveled_up = False
        while skill.xp >= skill.xp_to_next and skill.level < 10:
            skill.level += 1
            skill.xp -= skill.xp_to_next
            skill.xp_to_next = int(skill.xp_to_next * 1.6)
            leveled_up = True

        # 检查是否有新技能因前置满足而解锁
        unlocked_skills = cls._check_unlocks(user_id, skills)

        return {
            "used": True,
            "skill": skill.name,
            "icon": skill.icon,
            "level": skill.level,
            "xp_gained": xp_gain,
            "xp_current": skill.xp,
            "xp_to_next": skill.xp_to_next,
            "leveled_up": leveled_up,
            "times_used": skill.times_used,
            "bonus": skill.level_bonuses.get(skill.level, ""),
            "newly_unlocked": unlocked_skills,
        }

    @classmethod
    def _check_unlocks(cls, user_id: str,
                        skills: Dict[str, LearningSkill]) -> List[str]:
        """检查是否有新技能可解锁"""
        newly_unlocked = []
        for skill in skills.values():
            if not skill.unlocked and skill.prerequisites:
                if all(skills[p].level >= 1 for p in skill.prerequisites):
                    skill.unlocked = True
                    newly_unlocked.append(skill.name)
        return newly_unlocked

    @classmethod
    def get_skill_tree(cls, user_id: str) -> dict:
        """获取完整技能树"""
        skills = cls.PLAYER_SKILLS.get(user_id)
        if not skills:
            skills = cls.init_player_skills(user_id)

        meta_level = cls._calculate_meta_level(skills)
        total_times = sum(s.times_used for s in skills.values())

        by_category = {}
        for skill in skills.values():
            cat = skill.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "id": skill.skill_id,
                "name": skill.name,
                "icon": skill.icon,
                "level": skill.level,
                "xp": skill.xp,
                "xp_to_next": skill.xp_to_next,
                "times_used": skill.times_used,
                "unlocked": skill.unlocked,
                "progress_pct": round(skill.xp / skill.xp_to_next * 100),
                "next_bonus": cls._get_next_bonus(skill),
            })

        return {
            "meta_level": meta_level,
            "meta_title": cls._get_meta_title(meta_level),
            "total_times_used": total_times,
            "categories": by_category,
            "combo_bonus": cls._calculate_combo(skills),
        }

    @classmethod
    def _calculate_meta_level(cls, skills: Dict[str, LearningSkill]) -> int:
        total_levels = sum(s.level for s in skills.values())
        return total_levels // 10 + 1

    @classmethod
    def _get_meta_title(cls, level: int) -> str:
        titles = {
            1: "学习新手", 3: "学习方法论者", 5: "高效学习者",
            7: "学习策略家", 10: "元学习大师", 13: "学习哲学家",
            16: "终极学习者",
        }
        for threshold, title in sorted(titles.items(), reverse=True):
            if level >= threshold:
                return title
        return "初学者"

    @classmethod
    def _get_next_bonus(cls, skill: LearningSkill) -> str:
        for lvl in sorted(skill.level_bonuses.keys()):
            if lvl > skill.level:
                return f"Lv.{lvl}: {skill.level_bonuses[lvl]}"
        return "已满级"

    @classmethod
    def _calculate_combo(cls, skills: Dict[str, LearningSkill]) -> dict:
        """技能组合加成

        同时使用多个方法时获得额外加成。
        """
        bonuses = []

        # 主动回忆 + 间隔重复 = 超级记忆
        if skills.get("active_recall") and skills.get("spaced_repetition"):
            ar_lvl = skills["active_recall"].level
            sr_lvl = skills["spaced_repetition"].level
            combo = min(ar_lvl, sr_lvl)
            bonuses.append({"name": "超级记忆", "icon": "🧠⚡",
                            "level": combo, "effect": f"记忆效率+{combo * 5}%"})

        # 费曼 + 精细复述 = 深度理解
        if skills.get("feynman") and skills.get("elaborative_rehearsal"):
            bonuses.append({"name": "深度理解", "icon": "📝💬",
                            "level": min(skills["feynman"].level, skills["elaborative_rehearsal"].level),
                            "effect": "理解深度翻倍"})

        # 番茄 + 深度工作 = 超级专注
        if skills.get("pomodoro") and skills.get("deep_work"):
            bonuses.append({"name": "超级专注", "icon": "🍅🔒",
                            "level": min(skills["pomodoro"].level, skills["deep_work"].level),
                            "effect": "心流时间延长50%"})

        # 生长思维 + 元认知 = 终极学习心态
        if skills.get("growth_mindset") and skills.get("metacognition"):
            bonuses.append({"name": "学习觉醒", "icon": "🌱🤔",
                            "level": min(skills["growth_mindset"].level, skills["metacognition"].level),
                            "effect": "学习效率全局+20%"})

        return {"active_combos": len(bonuses), "bonuses": bonuses}


# ═══════════════════════════════════════════════════════════
# 3. 每日方法任务 — Method Quests
# ═══════════════════════════════════════════════════════════

class MethodQuestEngine:
    """方法任务引擎

    每天给玩家分配"学习方法任务"——使用特定方法完成学习。
    完成任务=经验奖励+技能升级。
    """

    DAILY_QUESTS = [
        {"quest": "用费曼技巧解释今天学到的一个概念", "skill": "feynman", "xp_reward": 30, "action": "explain_concept"},
        {"quest": "用主动回忆法自测3道之前学过的题", "skill": "active_recall", "xp_reward": 25, "action": "self_test"},
        {"quest": "在脑海中走过你的记忆宫殿", "skill": "memory_palace", "xp_reward": 35, "action": "walk_palace"},
        {"quest": "给今天遇到的最难概念画一幅意象图", "skill": "dual_coding", "xp_reward": 25, "action": "draw_image"},
        {"quest": "把今天学的3个知识点组块化——找它们之间的联系", "skill": "chunking", "xp_reward": 30, "action": "chunk_knowledge"},
        {"quest": "用SQ3R法阅读一段题目解析", "skill": "sq3r", "xp_reward": 25, "action": "read_with_sq3r"},
        {"quest": "混合练习3种不同题型的题目", "skill": "interleaving", "xp_reward": 30, "action": "interleave_practice"},
        {"quest": "做一次25分钟的番茄专注学习", "skill": "pomodoro", "xp_reward": 20, "action": "pomodoro_session"},
        {"quest": "对今天每道错题说一句'这让我更强了'", "skill": "growth_mindset", "xp_reward": 15, "action": "reframe_errors"},
        {"quest": "花1分钟反思：今天学得最好的时刻是什么时候？为什么？", "skill": "metacognition", "xp_reward": 25, "action": "daily_reflection"},
    ]

    @staticmethod
    def _stable_user_seed(user_id: str) -> int:
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    @classmethod
    def generate_daily_quests(cls, user_id: str) -> List[dict]:
        """每天生成3个随机方法任务"""
        today = datetime.now(UTC).toordinal()
        seed = today + cls._stable_user_seed(user_id)
        rng = random.Random(seed)
        quests = rng.sample(cls.DAILY_QUESTS, min(3, len(cls.DAILY_QUESTS)))

        return [{
            "quest_id": f"dq_{today}_{i}",
            "quest": q["quest"],
            "skill": q["skill"],
            "xp_reward": q["xp_reward"],
            "action": q["action"],
            "completed": False,
        } for i, q in enumerate(quests)]

    @classmethod
    def complete_quest(cls, user_id: str, quest_id: str) -> dict:
        """完成任务"""
        quests = cls.generate_daily_quests(user_id)
        for q in quests:
            if q["quest_id"] == quest_id:
                # 为对应技能加XP
                skill_result = SkillTreeEngine.use_skill(user_id, q["skill"], 2.0)
                return {
                    "quest_completed": True,
                    "xp_earned": q["xp_reward"],
                    "skill_xp": skill_result.get("xp_gained", 0),
                    "skill_leveled_up": skill_result.get("leveled_up", False),
                    "message": f"✨ 任务完成: {q['quest']}！+{q['xp_reward']} XP",
                }
        return {"quest_completed": False, "message": "任务不存在"}


# ═══════════════════════════════════════════════════════════
# 4. 熟练度等级系统 — Proficiency Tiers
# ═══════════════════════════════════════════════════════════

class ProficiencyEngine:
    """熟练度引擎 — 每个学习方法的熟练段位"""

    PROFICIENCY_TIERS = {
        1: {"name": "学徒", "icon": "🔰", "color": "#999"},
        3: {"name": "熟练者", "icon": "⭐", "color": "#4CAF50"},
        5: {"name": "方法大师", "icon": "🌟", "color": "#2196F3"},
        7: {"name": "策略家", "icon": "💫", "color": "#9C27B0"},
        9: {"name": "宗师", "icon": "👑", "color": "#FF9800"},
        10: {"name": "开悟", "icon": "💎", "color": "#FFD700"},
    }

    @classmethod
    def get_proficiency_badge(cls, skill: LearningSkill) -> dict:
        for tier_lvl, tier_info in sorted(cls.PROFICIENCY_TIERS.items(), reverse=True):
            if skill.level >= tier_lvl:
                return {"tier": tier_info["name"], "icon": tier_info["icon"],
                        "color": tier_info["color"], "skill_level": skill.level}
        return cls.PROFICIENCY_TIERS[1]

    @classmethod
    def get_global_proficiency(cls, skills: Dict[str, LearningSkill]) -> dict:
        """全局熟练度总览"""
        badges = {}
        for skill in skills.values():
            if skill.unlocked and skill.level > 0:
                badges[skill.skill_id] = cls.get_proficiency_badge(skill)

        # 统计
        counts = {}
        for badge in badges.values():
            counts[badge["tier"]] = counts.get(badge["tier"], 0) + 1

        return {
            "badges": badges,
            "summary": counts,
            "total_unlocked": len(badges),
            "total_skills": len(skills),
            "most_used": cls._most_used(skills),
        }

    @classmethod
    def _most_used(cls, skills: Dict[str, LearningSkill]) -> dict:
        best = max(skills.values(), key=lambda s: s.times_used)
        return {"name": best.name, "icon": best.icon, "level": best.level, "times": best.times_used}
