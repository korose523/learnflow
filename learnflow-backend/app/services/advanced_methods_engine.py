"""终极学习方法论引擎 — 第二轮

新增7种科学学习方法 + "学神冲刺"模式。

新增方法:
1.  预习效应 (Pretesting)    — 先做题再学习，错误促进记忆
2.  生成效应 (Generation)     — 自己生成答案比看答案有效
3.  自我解释 (Self-Explanation)— "为什么这样解题？"
4.  类比编码 (Analogy)        — 用已知概念类比新概念
5.  具体例子 (Concrete)       — 抽象→具体
6.  连续重学 (Successive)     — 完全正确→间隔→再测
7.  分布式练习 (Distributed)  — 分散练习比集中好
8.  "学神冲刺" (GodMode)      — 7种方法同时使用的极限学习
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. 新增7种方法
# ═══════════════════════════════════════════════════════════

NEW_METHODS = [
    {
        "method": "pretesting",
        "icon": "🎯",
        "title": "预习效应",
        "short": "先做题再学——答错反而记得更牢。",
        "detail": "系统会先让你做一道{concept}的题目，即使不会也没关系。研究证明：先行测试后，学习效果提升50%——因为你的大脑已经'预热'了。",
        "action": "看到新题不要怕——做错意味着你的大脑正在为学习做准备。",
        "science": "Kornell (2009): 先行测试组的最终成绩高出对照组50%。",
        "difficulty": "beginner",
    },
    {
        "method": "generation",
        "icon": "✍️",
        "title": "生成效应",
        "short": "自己生成答案比直接看答案记忆深3倍。",
        "detail": "系统会给你{concept}的相关提示，让你尝试自己推导答案。即使错了，你也会比直接看答案的人记得更牢。",
        "action": "看到提示后，先自己想一想，不要急着看答案。",
        "science": "Slamecka & Graf (1978): 自己生成的词汇比直接阅读的记忆率高300%。",
        "difficulty": "beginner",
    },
    {
        "method": "self_explanation",
        "icon": "❓",
        "title": "自我解释",
        "short": "边做题边问自己'为什么这样解？'",
        "detail": "每做完一道{concept}题，系统会弹出一个小问题：'这步为什么是对的？'回答这个问题比多做3道题更有效。",
        "action": "遇到'为什么？'时，用30秒想一想，哪怕只说出一个理由。",
        "science": "Chi (1989): 自我解释组的理解深度是对照组的2倍。",
        "difficulty": "intermediate",
    },
    {
        "method": "analogy",
        "icon": "🔄",
        "title": "类比学习",
        "short": "用你熟悉的东西去理解陌生的东西。",
        "detail": "{concept}和你已经学过的某个知识有共同之处。找到这个类比，理解立即翻倍。比如：电流像水流，分数像切披萨。",
        "action": "这道题让你想起了之前学过的什么？",
        "science": "Gentner (1983): 类比推理是人类认知的核心机制。",
        "difficulty": "intermediate",
    },
    {
        "method": "concrete_examples",
        "icon": "🍕",
        "title": "具体例子",
        "short": "用具体的、可视化的例子理解抽象概念。",
        "detail": "抽象的概念{concept}很难记住——但如果你把它变成一个故事或一张图，它就活了。系统会为每个概念提供3个不同角度的具体例子。",
        "action": "把这道题变成一个你能讲给朋友听的小故事。",
        "science": "概念的具体化使学习速度提升40% (Pashler, 2007)。",
        "difficulty": "beginner",
    },
    {
        "method": "successive_relearning",
        "icon": "🔄",
        "title": "连续重学",
        "short": "学到完全正确→间隔→重新测试。",
        "detail": "不是'做一遍就过'——系统会追踪你对{concept}的掌握，在你完全正确后间隔一段时间再重新测试，直到形成永久记忆。",
        "action": "这道题你上次已经做对了。现在是第2次复习——准备好了吗？",
        "science": "Bahrick (1979): 连续重学使长期记忆保持率提升到90%+。",
        "difficulty": "intermediate",
    },
    {
        "method": "distributed_practice",
        "icon": "📅",
        "title": "分布式练习",
        "short": "每天练一点比周末猛练效果好很多。",
        "detail": "与其一天做30道{concept}题，不如每天做5道，分6天。总量相同，效果差3倍。系统已自动为你分配了每日练习节奏。",
        "action": "你已经连续练习{concept}好几天了——这是最科学的学习方式。",
        "science": "分布练习效应是最稳健的学习发现之一 (Cepeda 2006)。",
        "difficulty": "beginner",
    },
]

# 新增到现有方法题库
from app.services.learning_methods_engine import METHOD_TIPS

# 确保不重复添加
existing_methods = {t["method"] for t in METHOD_TIPS}
for m in NEW_METHODS:
    if m["method"] not in existing_methods:
        METHOD_TIPS.append(m)


# ═══════════════════════════════════════════════════════════
# 2. 预习效应引擎 — Pretesting
# ═══════════════════════════════════════════════════════════

class PretestingEngine:
    """预习效应引擎

    在开始学习新主题前，先用一道"不可能答对"的题目激活大脑。
    """

    @classmethod
    def generate_pre_test(cls, topic: str, difficulty: int) -> dict:
        """生成预习测试"""
        return {
            "type": "pretest",
            "message": f"在开始学习{topic}之前，先试试这道题。不会也没关系——做错反而会让你的大脑为学习做好准备。",
            "encouragement": "这道题你可能不会——这正是重点。做错=大脑预热。",
            "after_pretest": "答错了？完美！你的大脑现在已经'激活'，接下来的学习效果会提升50%。",
            "science_note": "这就是'预习效应'——先测试再学习的记忆效果远超直接学习。",
        }

    @classmethod
    def generate_post_pretest_feedback(cls, was_correct: bool) -> dict:
        if was_correct:
            return {"message": "你居然答对了！看来你对这个知识已经有基础了。接下来的学习会巩固你的理解。"}
        return {"message": "答错是好事！你的大脑现在处于最佳学习状态。准备好被知识灌入吧！"}


# ═══════════════════════════════════════════════════════════
# 3. 自我解释引擎 — Self-Explanation
# ═══════════════════════════════════════════════════════════

class SelfExplanationEngine:
    """自我解释引擎

    每道题后随机插入"为什么？"提示。
    """

    WHY_PROMPTS = [
        "为什么这步是对的？想想看。",
        "这题的解题思路可以用在什么别的题目上？",
        "如果用一句话解释这道题的核心原理，是什么？",
        "这道题的解法让你想起了之前学过的什么？",
        "如果让这道题的答案反过来，题目会是什么？",
    ]

    @classmethod
    def should_trigger(cls, questions_since_last: int) -> bool:
        """每3-5题触发一次自我解释"""
        return questions_since_last >= random.randint(3, 5)

    @classmethod
    def generate_prompt(cls, topic: str) -> dict:
        return {
            "type": "self_explanation",
            "question": random.choice(cls.WHY_PROMPTS),
            "topic": topic,
            "prompt": "花10秒钟想一想。不需要写下来——在脑子里过一遍就够了。",
            "xp_reward": 8,
            "skill_boost": "self_explanation",
        }


# ═══════════════════════════════════════════════════════════
# 4. 类比桥接引擎 — Analogy Bridge
# ═══════════════════════════════════════════════════════════

class AnalogyBridgeEngine:
    """类比桥接引擎

    把抽象概念用生活中的事物来表达。
    """

    ANALOGIES = {
        "分数": [
            {"source": "披萨", "mapping": "分子=你吃了多少块, 分母=总共切了几块"},
            {"source": "时间", "mapping": "1/4小时=15分钟, 3/4=45分钟"},
            {"source": "钱", "mapping": "1/2元=5角, 1/4元=2角5分"},
        ],
        "方程": [
            {"source": "天平", "mapping": "等号两边必须平衡, 就像天平两边重量相等"},
            {"source": "侦探", "mapping": "已知条件是线索, 未知数x是你要找的答案"},
        ],
        "几何": [
            {"source": "积木", "mapping": "三角形/正方形/圆形都是基础积木块"},
            {"source": "地图", "mapping": "面积=这片地有多大, 周长=绕一圈要多远"},
        ],
        "百分比": [
            {"source": "折扣", "mapping": "打8折=80%, 半价=50%"},
            {"source": "成绩", "mapping": "85%=优秀, 60%=及格"},
        ],
        "代数": [
            {"source": "编程", "mapping": "x就像一个变量, 给它赋值就解出来了"},
            {"source": "寻宝", "mapping": "x是藏宝地点, 线索是方程式, 解出来就找到宝藏"},
        ],
        "概率": [
            {"source": "天气预报", "mapping": "70%降雨=10次有7次会下雨"},
            {"source": "抽奖", "mapping": "1/100的概率=100次抽中1次"},
        ],
    }

    @classmethod
    def generate_analogy(cls, topic: str) -> Optional[dict]:
        """为主题生成类比"""
        # 模糊匹配topic
        for key, analogies in cls.ANALOGIES.items():
            if key in topic:
                analogy = random.choice(analogies)
                return {
                    "type": "analogy",
                    "topic": topic,
                    "source": analogy["source"],
                    "mapping": analogy["mapping"],
                    "message": f"💡 试试这样理解{topic}: 把它想象成 **{analogy['source']}**。{analogy['mapping']}。",
                    "prompt": f"你还能想到{topic}像什么别的东西吗？",
                }
        return None


# ═══════════════════════════════════════════════════════════
# 5. "学神冲刺"模式 — GodMode Study
# ═══════════════════════════════════════════════════════════

class GodModeEngine:
    """学神冲刺引擎

    同时激活7种高效学习方法的高强度学习模式。
    每天限1次，持续15分钟。
    """

    @classmethod
    def activate_godmode(cls, user_id: str) -> dict:
        """启动学神冲刺"""
        methods = ["pretesting", "active_recall", "spaced_repetition",
                    "self_explanation", "generation", "interleaving", "dual_coding"]

        return {
            "active": True,
            "duration_minutes": 15,
            "methods_active": methods,
            "xp_multiplier": 3.0,
            "message": "⚡ 学神冲刺已激活！15分钟内：7种高效学习法同时运转 + 3倍经验！",
            "countdown": "抓紧这15分钟——这是你一天中最高效的学习时段。",
            "power_ups": [
                f"🧠 {methods[0]}: 新知识预习效应",
                f"🔍 {methods[1]}: 主动回忆加速",
                f"⏰ {methods[2]}: 间隔重复自动排期",
                f"🤔 {methods[3]}: '为什么？'自动触发",
                f"✍️ {methods[4]}: 生成效应加速",
                f"🔀 {methods[5]}: 交错练习自动混合",
                f"🖼️ {methods[6]}: 双重编码自动配图",
            ],
            "post_godmode": "学神冲刺结束！在15分钟内你高效完成了普通人1小时的学习量。明天再来！",
        }

    @classmethod
    def check_godmode_available(cls, last_used_date: str) -> dict:
        """检查今日是否可用"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if last_used_date == today:
            return {"available": False, "message": "学神冲刺今天已经用过了。明天再来！", "next_available": "tomorrow"}
        return {"available": True, "message": "学神冲刺可用！15分钟 = 普通人1小时。"}


# ═══════════════════════════════════════════════════════════
# 6. 学习方法组合推荐引擎 — Learning Strategy Recommender
# ═══════════════════════════════════════════════════════════

class StrategyRecommender:
    """学习策略推荐引擎

    根据当前学习状态，推荐最佳的方法组合。
    """

    @classmethod
    def recommend_for_topic(cls, topic: str, mastery: float,
                             attempts: int) -> dict:
        """根据掌握度和尝试次数推荐方法"""
        if attempts < 3:
            strategies = ["pretesting", "active_recall"]
            reason = "新知识点：先用预习效应预热，再主动回忆加强。"
        elif mastery < 0.3:
            strategies = ["feynman", "concrete_examples", "analogy"]
            reason = "掌握度低：用费曼技巧+具体例子+类比来建立基础理解。"
        elif mastery < 0.6:
            strategies = ["self_explanation", "interleaving", "dual_coding"]
            reason = "掌握度中等：用自我解释深化理解，交错练习巩固。"
        elif mastery < 0.8:
            strategies = ["generation", "retrieval_practice", "successive_relearning"]
            reason = "接近掌握：用生成效应和检索练习把知识刻进长期记忆。"
        else:
            strategies = ["spaced_repetition", "distributed_practice", "chunking"]
            reason = "已掌握：间隔复习+分布式练习维持永久记忆。"

        return {
            "topic": topic,
            "mastery": round(mastery * 100),
            "recommended_strategies": strategies,
            "reason": reason,
            "message": f"💡 根据你对{topic}的掌握情况({round(mastery*100)}%)，推荐使用: {' + '.join(strategies)}",
        }
