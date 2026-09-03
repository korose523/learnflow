"""学习方法论引擎 — Metacognition & Memory Techniques

让学习者在学习过程中学会"如何学习"。

核心方法:
1.  记忆宫殿 (Memory Palace) — 空间记忆编码
2.  费曼技巧 (Feynman Technique) — 教是最好的学
3.  间隔重复 (Spaced Repetition) — 已有引擎，此处整合教学
4.  交错练习 (Interleaving) — 混合不同题型
5.  精细复述 (Elaborative Rehearsal) — 用自己的话解释
6.  组块化 (Chunking) — 将信息打包成有意义的单元
7.  双重编码 (Dual Coding) — 文字+图像同时编码
8.  主动回忆 (Active Recall) — 先想再看的自测
9.  检索练习 (Retrieval Practice) — 从记忆中提取而非再认
10. 元认知反思 (Metacognition) — 反思"我学到了什么"

设计哲学:
  最好的教育产品不仅要教知识，还要教"如何学习"。
  每次加载等待 = 一次学习方法的微型课程。
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. 学习方法知识库 — Loading Screen Tips
# ═══════════════════════════════════════════════════════════

METHOD_TIPS = [
    # 记忆宫殿
    {
        "method": "memory_palace",
        "icon": "🏰",
        "title": "记忆宫殿",
        "short": "把要记的知识放进你熟悉的空间里。",
        "detail": "闭上眼睛，想象你从小到大的家。把今天学的{concept}放进去——放在门口、沙发、床头。下次回忆时，在脑海中走过那个家。",
        "action": "试试现在就把这道题的解法放进你的卧室里。",
        "science": "2500年前的古希腊人发明，现代fMRI证明激活了大脑的空间记忆区。",
        "difficulty": "advanced",
    },
    {
        "method": "memory_palace",
        "icon": "🚪",
        "title": "记忆宫殿起步",
        "short": "选一个你熟悉的地方作为你的第一个宫殿。",
        "detail": "推荐从你的卧室开始。给每个知识点一个位置：{concept}放在书桌上，另一个概念放在衣柜里。走过这个房间，每个位置就是一个知识锚点。",
        "action": "现在，在这道题旁边想象一个具体的画面。",
        "science": "空间记忆是人类进化出的最强记忆系统。你永远不会忘记你的卧室长什么样。",
        "difficulty": "beginner",
    },
    # 费曼技巧
    {
        "method": "feynman",
        "icon": "📝",
        "title": "费曼技巧",
        "short": "用最简单的话解释给别人听。",
        "detail": "假装你在给一个完全不懂{concept}的人讲解。你必须用最简单的语言，举最直观的例子。如果卡住了——那正是你需要复习的地方。",
        "action": "试着自己讲一遍这道题的解法。讲不出来？回头看讲解。",
        "science": "诺贝尔物理学奖得主费曼的学习方法：教=最好的学。",
        "difficulty": "beginner",
    },
    # 间隔重复
    {
        "method": "spaced_repetition",
        "icon": "⏰",
        "title": "间隔重复",
        "short": "遗忘是正常的。在即将遗忘时复习最有效。",
        "detail": "你不会一次就记住{concept}——没有人会。系统会在你即将遗忘的时候自动安排复习。你只需要每天来。",
        "action": "系统已自动为你安排了{concept}的复习计划。",
        "science": "艾宾浩斯遗忘曲线：24小时后遗忘70%。间隔复习让记忆曲线重新上升。",
        "difficulty": "beginner",
    },
    # 交错练习
    {
        "method": "interleaving",
        "icon": "🔀",
        "title": "交错练习",
        "short": "不要集中练一种题。混合练效果更好。",
        "detail": "与其连续做10道{concept}题，不如把不同知识点混在一起练。短期感觉更难，但长期记得更牢。",
        "action": "做完这道题，系统会给你换一种知识点。",
        "science": "Bjork (1992): 交错练习比集中练习的长期记忆效果高出43%。",
        "difficulty": "intermediate",
    },
    # 精细复述
    {
        "method": "elaborative_rehearsal",
        "icon": "💬",
        "title": "精细复述",
        "short": "不要重复读。用自己的话重新组织。",
        "detail": "读3遍不如用自己的话说1遍。看完{concept}的解析后，在脑子里用你自己的语言重新解释一遍。",
        "action": "现在：用你自己的话说一遍这道题的解题思路。",
        "science": "Craik & Lockhart: 加工层次越深，记忆越牢固。",
        "difficulty": "beginner",
    },
    # 组块化
    {
        "method": "chunking",
        "icon": "🧩",
        "title": "组块化",
        "short": "把零散的知识打包成有意义的大块。",
        "detail": "与其记3.1415926535这10个数字，不如记'圆周率是3.14'这一个概念。{concept}也可以打包——找找它和其他知识的联系。",
        "action": "{concept}和你之前学过的什么知识有关系？",
        "science": "工作记忆只能同时处理4±1个组块。组块化让你处理更多信息。",
        "difficulty": "beginner",
    },
    # 双重编码
    {
        "method": "dual_coding",
        "icon": "🖼️",
        "title": "双重编码",
        "short": "文字+图像=双倍记忆。",
        "detail": "在脑海中为{concept}画一幅图。不一定要真的画——想象一个画面就可以。视觉记忆和语言记忆是两条独立的通道。",
        "action": "闭上眼睛，为这道题的答案画一幅想象的图。",
        "science": "Paivio的双重编码理论：两个通道同时编码，回忆概率翻倍。",
        "difficulty": "beginner",
    },
    # 主动回忆
    {
        "method": "active_recall",
        "icon": "🧠",
        "title": "主动回忆",
        "short": "先回忆，再看答案。",
        "detail": "在做下一道{concept}题之前，先闭上眼睛回忆：上道题的关键步骤是什么？这种'先想后看'比直接看答案有效3倍。",
        "action": "现在闭眼5秒：回忆上道题的解法。",
        "science": "Karpicke & Roediger: 主动回忆是最有效的学习方法之一。",
        "difficulty": "beginner",
    },
    # 检索练习
    {
        "method": "retrieval_practice",
        "icon": "🔍",
        "title": "检索练习",
        "short": "做题本身就是最好的学习。",
        "detail": "测试不是为了评价你——测试本身就是学习。每次你从记忆中提取{concept}的知识，这个记忆就被强化了一次。",
        "action": "你刚才做的这道题，已经强化了{concept}的神经通路。",
        "science": "测试效应(Testing Effect): 做一次测试的记忆效果相当于重新学习4次。",
        "difficulty": "beginner",
    },
    # 元认知
    {
        "method": "metacognition",
        "icon": "🤔",
        "title": "元认知反思",
        "short": "花30秒想一想：刚才学到了什么？",
        "detail": "做完5道题，停下来问问自己：我对{concept}的理解变深了吗？哪道题最难？为什么难？这个反思比多做5道题更有效。",
        "action": "现在：用一句话总结你刚才学到了什么。",
        "science": "Flavell: 元认知能力是学生成绩的最佳预测指标之一。",
        "difficulty": "intermediate",
    },
    # 番茄工作法
    {
        "method": "pomodoro",
        "icon": "🍅",
        "title": "番茄学习法",
        "short": "专注25分钟，休息5分钟。",
        "detail": "你的注意力是有限的。每25分钟的专注学习后，大脑需要5分钟的休息来重新充电。系统会在25分钟时提醒你。",
        "action": "你已进入专注状态。系统会帮你记录时间。",
        "science": "注意力在25分钟后开始显著下降。短休息能让后续的注意力恢复。",
        "difficulty": "beginner",
    },
    # SQ3R 阅读法
    {
        "method": "sq3r",
        "icon": "📖",
        "title": "SQ3R阅读法",
        "short": "浏览→提问→阅读→复述→复习",
        "detail": "遇到{concept}的长篇解析时：先快速浏览(Survey)→提出3个问题(Question)→仔细阅读找答案(Read)→用自己的话复述(Recite)→24小时后复习(Review)。",
        "action": "看完这道题的解析后，用自己的话复述一遍。",
        "science": "Robinson (1946): 结构化阅读比被动阅读的效率高4倍。",
        "difficulty": "intermediate",
    },
    # 生长思维
    {
        "method": "growth_mindset",
        "icon": "🌱",
        "title": "生长型思维",
        "short": "做错题不是'你不行'，是'你正在变强'。",
        "detail": "每次答错{concept}的题目，你的大脑都在重新组织关于这个概念的知识。错误不是能力的证明——错误是学习正在发生的信号。",
        "action": "这道题如果你错了：恭喜，你的大脑正在变强。",
        "science": "Dweck: 相信智力可成长的学生比相信智力固定的学生成绩高30%。",
        "difficulty": "beginner",
    },
    # 睡眠记忆
    {
        "method": "sleep_memory",
        "icon": "😴",
        "title": "睡眠巩固记忆",
        "short": "你睡着的时候，大脑在整理今天学的知识。",
        "detail": "今天学的{concept}，在你今晚睡觉时会从海马体转移到大脑皮层。睡眠不是浪费时间——睡眠是记忆巩固的关键阶段。",
        "action": "今晚好好睡觉。你的大脑会帮你整理今天的{concept}。",
        "science": "Walker (2017): 睡眠中，海马体将短期记忆'重放'到皮层，实现长期巩固。",
        "difficulty": "beginner",
    },
    # 运动记忆
    {
        "method": "exercise_memory",
        "icon": "🏃",
        "title": "运动增强记忆",
        "short": "学习后运动20分钟，记忆力提升20%。",
        "detail": "学完{concept}后如果去跑跑步或走一走，你的记忆效果会更好。运动增加大脑的BDNF(脑源性神经营养因子)——这是一种'大脑肥料'。",
        "action": "今天学习结束后去走一走。",
        "science": "运动后BDNF水平上升，促进海马体神经生成。运动=大脑肥料。",
        "difficulty": "beginner",
    },
]


# ────────────────────────────────────────────────────────────
# 知识点代入（topic grounding）
#
# 部分 tip 模板（如 pomodoro）本身不含 {concept} 占位符，直接
# .format() 会把当前知识点静默丢弃，导致提示与学习内容脱节——
# 这既是 test_loading_tip 随机失败的根因，也让"学习方法落地"
# 流于形式。此处统一保证输出始终锚定当前知识点。
# ────────────────────────────────────────────────────────────

_CONCEPT_PLACEHOLDER = "{concept}"
_TOPIC_TAIL = "把它用到今天学的「{topic}」上试试。"


def ground_topic(template: str, topic: str) -> str:
    """把知识点代入模板；模板无占位符时追加锚定句。

    Args:
        template: 含或不含 ``{concept}`` 的文案模板
        topic: 当前知识点（为空时回退为通用文案）

    Returns:
        保证包含当前知识点的文案
    """
    safe_topic = topic or "当前知识点"
    text = template.format(concept=safe_topic)
    if _CONCEPT_PLACEHOLDER not in template:
        text = f"{text}{_TOPIC_TAIL.format(topic=safe_topic)}"
    return text


# ═══════════════════════════════════════════════════════════
# 2. 学习方法引擎 — 整合到学习流程中
# ═══════════════════════════════════════════════════════════

class LearningMethodEngine:
    """学习方法引擎

    三个使用场景:
    1. Loading/等待时的知识点
    2. 做题完成后的方法提示
    3. 阶段性反思触发器
    """

    @classmethod
    def _ground(cls, tip: dict, current_topic: str) -> dict:
        """把当前知识点代入 tip 的 detail / action

        所有对外输出 tip 文案的入口都必须经过这里 —— 直接
        ``tip["detail"].format(...)`` 会在模板不含 ``{concept}`` 时把知识点
        静默丢弃 (pomodoro 就是唯一没有占位符的那条)。
        """
        return {
            **tip,
            "detail": ground_topic(tip["detail"], current_topic),
            "action": ground_topic(tip["action"], current_topic),
        }

    @classmethod
    def render_tip(cls, method_key: str, topic: str = "",
                   difficulty: Optional[str] = None,
                   scene: str = "generic") -> dict:
        """按方法 key 渲染一条学习方法提示

        供 ``app.services.method_registry.render`` 统一调度层使用: 注册表负责
        选方法与变体, 这里负责复用既有 tip 渲染路径 (因而必然经过
        ``ground_topic`` 做知识点代入)。

        Args:
            method_key: 学习方法的 snake_case key
            topic: 当前知识点
            difficulty: 指定难度变体; 该变体不存在时回退到任意一条
            scene: 埋点用场景名

        Raises:
            KeyError: METHOD_TIPS 中没有该方法
        """
        candidates = [t for t in METHOD_TIPS if t["method"] == method_key]
        if not candidates:
            raise KeyError(f"METHOD_TIPS 中没有学习方法: {method_key!r}")

        tip = candidates[0]
        if difficulty:
            tip = next((t for t in candidates if t["difficulty"] == difficulty), tip)
        return {**cls._ground(tip, topic), "scene": scene}

    @classmethod
    def get_loading_tip(cls, current_topic: str = "",
                          user_level: str = "beginner") -> dict:
        """获取加载等待期间的学习方法提示"""
        tips = [t for t in METHOD_TIPS if t["difficulty"] in ("beginner", "intermediate")]
        tip = random.choice(tips)

        return {
            **cls._ground(tip, current_topic),
            "scene": "loading",
            "duration_ms": max(len(tip["detail"]) * 40, 3000),
        }

    @classmethod
    def get_post_question_tip(cls, current_topic: str, is_correct: bool,
                               method_used: Optional[str] = None) -> dict:
        """做完一道题后的学习方法提示"""
        if is_correct:
            pool = ["active_recall", "retrieval_practice", "elaborative_rehearsal",
                     "dual_coding", "chunking"]
        else:
            pool = ["growth_mindset", "elaborative_rehearsal", "feynman",
                     "spaced_repetition", "memory_palace"]

        if method_used:
            pool = [method_used]

        # 安全选择: 从池中取一个方法作为目标
        target = random.choice(pool)
        matching = [t for t in METHOD_TIPS if t["method"] == target]
        if not matching:
            # 回退到任意tip
            tip = random.choice(METHOD_TIPS)
        else:
            tip = random.choice(matching)
        return {
            **cls._ground(tip, current_topic),
            "scene": "post_question",
            "trigger": "correct" if is_correct else "incorrect",
        }

    @classmethod
    def get_reflection_trigger(cls, questions_since_last: int,
                                 topic: str) -> Optional[dict]:
        """每N题触发一次元认知反思"""
        if questions_since_last < 5:
            return None

        return {
            "type": "metacognition_reflection",
            "questions": [
                f"用一句话总结：{topic}的核心是什么？",
                f"今天学{topic}和之前学的有什么联系？",
                "哪道题让你觉得最难？为什么？",
                "如果让你教别人{topic}，你会怎么讲？",
            ],
            "prompt": "花30秒想一想。这不是考试——这是帮你学得更好。",
            "duration_seconds": 30,
        }

    @classmethod
    def get_daily_method_challenge(cls, user_id: str) -> dict:
        """每日学习方法挑战 — 每天介绍一种新方法

        两处历史缺陷已修复:

        1. 方法池取自 ``set(t["method"] for t in METHOD_TIPS)``, 而 v3 的思维导图
           根本没有 tip 条目, 因此它永远进不了每日挑战 —— 实际只在 22 个里转。
           现改为从注册表取全量 23 个。
        2. 对 ``set`` 转 ``list`` 的结果取模。set 的迭代顺序取决于哈希与插入历史,
           同一天在不同进程里可能给出不同方法, "每日挑战"不可复现 —— 论文的可
           复现性要求无法成立。现改为对**排序后的** key 列表取模。
        """
        # 延迟导入: method_registry 会反向 import 本模块, 放在函数级以避开循环依赖
        from app.services.method_registry import get, keys, render

        all_keys = keys()  # 已按字典序排序 -> 取模结果稳定可复现
        today_index = datetime.now(UTC).toordinal() % len(all_keys)
        spec = get(all_keys[today_index])

        payload = render(spec.key, "今天学习的内容")
        return {
            "challenge_type": "learning_method",
            "method": spec.key,
            # 新增埋点字段 (原有字段签名保持不变)
            "method_id": spec.id,
            "method_key": spec.key,
            "title": f"📚 今天的学习方法: {payload.get('title') or spec.name_zh}",
            "description": payload.get("short") or payload.get("description", ""),
            "how_to": payload.get("detail") or payload.get("tip", ""),
            "try_it": payload.get("action") or payload.get("prompt", ""),
            "science": payload.get("science") or spec.evidence_ref,
            "xp_reward": 10,
            "message": f"今日学习方法挑战: {spec.name_zh}。完成后获得额外XP！",
        }


# ═══════════════════════════════════════════════════════════
# 3. 记忆宫殿引导引擎 — 互动式记忆训练
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryPalace:
    """记忆宫殿"""
    user_id: str
    name: str
    locations: List[dict] = field(default_factory=list)  # [{name, item, image_prompt}]
    total_items: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MemoryPalaceEngine:
    """记忆宫殿引导引擎

    引导学生在做题过程中构建个人记忆宫殿。
    不是一次性教完——而是在每次遇到新知识点时逐步构建。
    """

    PALACES: Dict[str, MemoryPalace] = {}
    PALACE_TEMPLATES = [
        {"name": "我的卧室", "locations": ["门口", "书桌", "床", "衣柜", "窗户", "书架"]},
        {"name": "从家到学校的路", "locations": ["家门口", "公交站", "十字路口", "便利店", "校门口", "教室"]},
        {"name": "我的学校", "locations": ["操场", "图书馆", "教室", "食堂", "实验室", "楼梯"]},
    ]

    @classmethod
    def create_palace(cls, user_id: str, template_index: int = 0) -> MemoryPalace:
        """创建记忆宫殿"""
        template = cls.PALACE_TEMPLATES[template_index % len(cls.PALACE_TEMPLATES)]
        palace = MemoryPalace(
            user_id=user_id,
            name=template["name"],
            locations=[{"name": loc, "item": "", "image_prompt": ""} for loc in template["locations"]],
        )
        cls.PALACES[user_id] = palace
        return palace

    @classmethod
    def place_knowledge(cls, user_id: str, concept: str, description: str) -> dict:
        """在宫殿中放置一条知识"""
        palace = cls.PALACES.get(user_id)
        if not palace:
            palace = cls.create_palace(user_id)

        # 找一个空位置
        empty_slot = next((loc for loc in palace.locations if not loc["item"]), None)
        if not empty_slot:
            # 宫殿满了，创建新的
            return {"placed": False, "message": "你的记忆宫殿满了！试试创建新的宫殿来存放更多知识。"}

        empty_slot["item"] = concept
        empty_slot["image_prompt"] = f"想象 {concept}: {description}"
        empty_slot["placed_at"] = datetime.now(UTC).isoformat()
        palace.total_items += 1

        return {
            "placed": True,
            "location": empty_slot["name"],
            "concept": concept,
            "image_prompt": empty_slot["image_prompt"],
            "message": f"🏰 {concept} 已放置在 {empty_slot['name']}！下次走过这里时会想起它。",
            "walkthrough": cls._generate_walkthrough(palace),
        }

    @classmethod
    def recall_walkthrough(cls, user_id: str) -> dict:
        """在脑海中走过记忆宫殿"""
        palace = cls.PALACES.get(user_id)
        if not palace or not palace.total_items:
            return {"has_palace": False, "message": "还没有记忆宫殿。做完这道题后系统会帮你创建第一个。"}

        return {
            "has_palace": True,
            "palace_name": palace.name,
            "items": [
                {"step": i+1, "location": loc["name"], "item": loc["item"],
                 "prompt": loc["image_prompt"]}
                for i, loc in enumerate(palace.locations) if loc["item"]
            ],
            "total_knowledge_stored": palace.total_items,
            "message": f"你已经在记忆宫殿中存放了{palace.total_items}条知识。每次回忆时，在脑海中走过{palace.name}。",
        }

    @classmethod
    def _generate_walkthrough(cls, palace: MemoryPalace) -> str:
        items = [loc["name"] for loc in palace.locations if loc["item"]]
        if not items:
            return "宫殿还空着。"
        return " → ".join(items[:5])


# ═══════════════════════════════════════════════════════════
# 4. 学习统计 — 元认知仪表盘
# ═══════════════════════════════════════════════════════════

class MetacognitionDashboard:
    """元认知仪表盘

    帮助学生了解自己的学习模式。
    不是"你对了多少"，而是"你是怎么学的"。
    """

    @classmethod
    def generate_learning_profile(cls, stats: dict) -> dict:
        """生成学习画像"""
        return {
            "best_time_of_day": stats.get("best_time", "未知"),
            "avg_focus_duration_min": stats.get("avg_focus", 0),
            "preferred_difficulty": stats.get("pref_difficulty", 5),
            "strongest_method": cls._detect_best_method(stats),
            "methods_tried": stats.get("methods_tried", []),
            "methods_to_try": [
                m for m in ["memory_palace", "feynman", "interleaving", "dual_coding"]
                if m not in stats.get("methods_tried", [])
            ],
            "insight": cls._generate_insight(stats),
        }

    @classmethod
    def _detect_best_method(cls, stats: dict) -> str:
        method_scores = stats.get("method_performance", {})
        if not method_scores:
            return "active_recall"
        return max(method_scores, key=method_scores.get)

    @classmethod
    def _generate_insight(cls, stats: dict) -> str:
        insights = []
        if stats.get("morning_accuracy", 0) > stats.get("evening_accuracy", 0) + 10:
            insights.append("你的早晨学习效果比晚上好。试试早上多学一点？")
        if stats.get("avg_focus", 0) > 30:
            insights.append("你有很强的专注力。利用这个优势深入攻克难点。")
        if len(stats.get("methods_tried", [])) < 3:
            insights.append("你只尝试了很少的学习方法。每天解锁一种新方法试试看。")
        return random.choice(insights) if insights else "继续探索你的最佳学习方式！"


# ═══════════════════════════════════════════════════════════
# 5. 学习技巧小测验 — 测测你学到了什么方法
# ═══════════════════════════════════════════════════════════

class MethodQuizEngine:
    """学习方法小测验

    在学习了新方法后，通过小问题确认理解。
    """

    QUIZZES = {
        "memory_palace": [
            {"q": "记忆宫殿的原理是什么？", "options": ["把知识放在虚拟空间里", "反复抄写100遍", "死记硬背"], "answer": 0},
        ],
        "feynman": [
            {"q": "费曼技巧的核心是什么？", "options": ["用最简单的话解释给别人听", "用复杂的术语炫耀", "只看不动手"], "answer": 0},
        ],
        "active_recall": [
            {"q": "主动回忆的关键是什么？", "options": ["先回忆再看答案", "一直看答案直到记住", "边看边抄"], "answer": 0},
        ],
        "spaced_repetition": [
            {"q": "什么时候复习效果最好？", "options": ["即将遗忘时", "刚学完立刻", "从不复习"], "answer": 0},
        ],
        "interleaving": [
            {"q": "交错练习是什么意思？", "options": ["混合不同题型练习", "一直练同一题型", "不练习"], "answer": 0},
        ],
    }

    @classmethod
    def generate_quiz(cls, method: str) -> Optional[dict]:
        quiz_data = cls.QUIZZES.get(method)
        if not quiz_data:
            return None
        question = random.choice(quiz_data)
        return {
            "method": method,
            "question": question["q"],
            "options": question["options"],
            "xp_reward": 5,
        }

    @classmethod
    def check_answer(cls, method: str, chosen_index: int) -> dict:
        quiz_data = cls.QUIZZES.get(method)
        if not quiz_data or not quiz_data:
            return {"correct": False}
        correct = chosen_index == quiz_data[0]["answer"]
        return {
            "correct": correct,
            "message": "完美！你已经掌握了这种学习方法。" if correct else "再看看？这个方法是这样的...",
            "xp_reward": 5 if correct else 0,
        }
