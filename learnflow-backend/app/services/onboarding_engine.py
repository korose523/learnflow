"""新手引导引擎 — Onboarding & Tutorial System

三个角色的完整引导流程:
  学生: 从"做第一道题"到"精通所有功能"
  教师: 从"创建班级"到"AI教学分析"
  家长: 从"绑定孩子"到"周报解读"

引导设计原则:
  - 渐进揭示: 一次只教一件事
  - 即时反馈: 每完成一步立即确认
  - 跳过权利: 任何步骤都可以跳过
  - 游戏化: 完成引导=获得引导徽章
  - 情境化: 在实际界面中教学，不是看文档
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional
import random


# ═══════════════════════════════════════════════════════════
# 1. 引导步骤定义
# ═══════════════════════════════════════════════════════════

@dataclass
class OnboardingStep:
    """引导步骤"""
    step_id: str                  # 唯一标识
    order: int                     # 顺序
    title: str                     # 步骤标题
    description: str               # 详细说明
    target_element: str            # 页面中高亮的元素
    action_required: str           # 用户需要做的操作
    completion_check: str          # 如何判断完成
    tip: str = ""                  # 小贴士
    skip_allowed: bool = True
    duration_estimate: str = "30秒"


# ─── 学生引导 (12步) ─────────────────

STUDENT_ONBOARDING = [
    OnboardingStep(
        step_id="stu_welcome", order=1,
        title="欢迎来到 LearnFlow！",
        description="这是你的学习成瘾实验平台。你会爱上学习的——这是科学，不是魔法。你的学习伙伴「小豆」会陪你走完全程。",
        target_element="welcome_screen",
        action_required="点击「开始」按钮",
        completion_check="welcome_dismissed",
        tip="看到那个宠物蛋了吗？它马上就会孵化了。",
        skip_allowed=False, duration_estimate="10秒",
    ),
    OnboardingStep(
        step_id="stu_first_question", order=2,
        title="你的第一道题",
        description="系统为你准备了一道题。别紧张——答错了反而学得更快！这就是「预习效应」。",
        target_element="question_card",
        action_required="回答这道题（选一个答案）",
        completion_check="first_attempt_submitted",
        tip="不知道答案？随便选一个——你的大脑正在'预热'。",
        skip_allowed=False, duration_estimate="1分钟",
    ),
    OnboardingStep(
        step_id="stu_pet_birth", order=3,
        title="你的学习伙伴出生了！",
        description="这是小豆。它不是积分容器，而是你学习维度的可视化镜像。它的四个属性代表了你的四种学习能力。",
        target_element="pet_card",
        action_required="点击小豆看看它的属性",
        completion_check="pet_card_viewed",
        tip="小豆的每个属性都对应你的真实学习行为。",
        duration_estimate="30秒",
    ),
    OnboardingStep(
        step_id="stu_feedback", order=4,
        title="即时反馈",
        description="每道题答完后，系统会在3秒内给你反馈。答对有庆祝，答错有鼓励——错误是你大脑在学习。",
        target_element="feedback_panel",
        action_required="查看刚才的答题反馈",
        completion_check="feedback_viewed",
        tip="看到那个'为什么？'提示了吗？回答它能让你理解更深。",
        duration_estimate="20秒",
    ),
    OnboardingStep(
        step_id="stu_streak", order=5,
        title="连胜=你的学习日记",
        description="连续学习的天数。不是'你今天必须学'，而是'你今天学了，就点亮了这一天'。",
        target_element="streak_indicator",
        action_required="查看连胜记录",
        completion_check="streak_viewed",
        tip="连胜冻结卡可以在你偶尔忙碌时保护你的连胜。",
        duration_estimate="15秒",
    ),
    OnboardingStep(
        step_id="stu_xp_and_level", order=6,
        title="XP 经验值系统",
        description="每道题都能获得XP。XP攒多了会升级。这和游戏一样——但升级的是你真正的学习能力。",
        target_element="xp_bar",
        action_required="查看XP进度条",
        completion_check="xp_bar_viewed",
        tip="早晨学习有双倍XP哦！早起的人学得更好。",
        duration_estimate="15秒",
    ),
    OnboardingStep(
        step_id="stu_daily_goal", order=7,
        title="设定你的每日目标",
        description="不是系统要求你做多少——是你自己决定今天做多少。自己设定的目标完成率高出40%。",
        target_element="daily_goal_selector",
        action_required="选择一个每日目标",
        completion_check="daily_goal_set",
        tip="刚开始可以从'基础'开始，随时可以调整。",
        duration_estimate="30秒",
    ),
    OnboardingStep(
        step_id="stu_skills", order=8,
        title="学习方法技能树",
        description="你不仅要学知识，还要学「怎么学」。每用一次学习方法，它的等级就提升。Lv.10=学习大师。",
        target_element="skill_tree_button",
        action_required="打开技能树看看",
        completion_check="skill_tree_viewed",
        tip="连击技能可以触发Combo加成。试试主动回忆+间隔重复。",
        duration_estimate="1分钟",
    ),
    OnboardingStep(
        step_id="stu_league", order=9,
        title="联赛排位",
        description="你的学习成果在联赛中排名。不是比谁聪明——是比谁坚持。每周围绕坚持度升降级。",
        target_element="league_panel",
        action_required="查看你的联赛段位",
        completion_check="league_viewed",
        tip="前10%晋级，后20%降级。保持每天学习就不会掉。",
        duration_estimate="20秒",
    ),
    OnboardingStep(
        step_id="stu_team", order=10,
        title="加入或创建战队",
        description="和同学组队学习。战队有内部排名、对抗赛、MVP。你不是一个人在战斗。",
        target_element="team_panel",
        action_required="查看战队列表",
        completion_check="team_list_viewed",
        tip="战队最多10人。找个有活跃成员的战队，互相督促。",
        duration_estimate="30秒",
    ),
    OnboardingStep(
        step_id="stu_social", order=11,
        title="社交名片",
        description="这是你的学习身份。名片上的一切都是你真实付出的证明。每个徽章都有一个故事。",
        target_element="business_card",
        action_required="查看你的名片",
        completion_check="card_viewed",
        tip="头像框会随着你的连胜天数自动升级。",
        duration_estimate="20秒",
    ),
    OnboardingStep(
        step_id="stu_complete", order=12,
        title="引导完成！",
        description="你已经掌握了LearnFlow的核心功能。从现在开始，每一次点击都在让你变得更强大。小豆会一直陪着你。",
        target_element="dashboard",
        action_required="开始你的学习之旅",
        completion_check="onboarding_complete",
        tip="引导徽章已解锁！收集更多徽章让你的名片更亮眼。",
        duration_estimate="完成",
    ),
]


# ─── 教师引导 (10步) ─────────────────

TEACHER_ONBOARDING = [
    OnboardingStep(
        step_id="tchr_welcome", order=1,
        title="欢迎，老师！",
        description="LearnFlow 为教师提供了完整的AI教学助手。你能看到每个学生的学习状况、得到AI建议、一键调整难度。",
        target_element="teacher_dashboard",
        action_required="点击「开始了解」",
        completion_check="welcome_dismissed",
        skip_allowed=False,
    ),
    OnboardingStep(
        step_id="tchr_classroom", order=2,
        title="班级全景仪表盘",
        description="这是你的班级概览。每个学生的掌握度、学习状态、风险等级一目了然。颜色越深=需要关注。",
        target_element="classroom_grid",
        action_required="浏览班级学生列表",
        completion_check="classroom_viewed",
        tip="红色标记的学生需要立即关注。点击进入详情。",
    ),
    OnboardingStep(
        step_id="tchr_ai_analysis", order=3,
        title="AI 学生分析",
        description="点击任意学生，AI会为你生成深度分析报告：掌握度趋势、学习行为、成瘾阶段、推荐教学行动。",
        target_element="student_detail_button",
        action_required="点击一个学生查看AI分析",
        completion_check="student_analysis_viewed",
        tip="AI建议不是命令——你是最终决策者。",
    ),
    OnboardingStep(
        step_id="tchr_difficulty", order=4,
        title="智能难度调节",
        description="一键调整学生难度。系统会根据BKT引擎给出建议，你可以采纳或覆盖。也可以批量调整。",
        target_element="difficulty_panel",
        action_required="查看难度建议面板",
        completion_check="difficulty_panel_viewed",
        tip="批量调整可以一次性处理全班。但AI建议的是个性化的。",
    ),
    OnboardingStep(
        step_id="tchr_intervention", order=5,
        title="教学干预计划",
        description="AI会自动标记需要关注的学生，分为紧急/观察/挑战三组。每组都有具体的行动建议。",
        target_element="intervention_panel",
        action_required="查看干预计划",
        completion_check="intervention_viewed",
        tip="每周一查看干预计划，安排本周的重点关注学生。",
    ),
    OnboardingStep(
        step_id="tchr_suggestions", order=6,
        title="教学建议通知",
        description="当系统检测到学生可能需要帮助时，会自动生成教学建议。包含具体原因和推荐行动。",
        target_element="suggestions_list",
        action_required="查看教学建议列表",
        completion_check="suggestions_viewed",
        tip="绿色=值得表扬，红色=需要干预，黄色=保持观察。",
    ),
    OnboardingStep(
        step_id="tchr_tasks", order=7,
        title="创建和管理题目",
        description="你可以创建自己的题目，指定知识点和难度。题目提交后需要管理员审核，确保质量。",
        target_element="task_creator",
        action_required="试试创建一个题目",
        completion_check="task_created",
        tip="好的题目应该有清晰的解析和分层提示。",
    ),
    OnboardingStep(
        step_id="tchr_alerts", order=8,
        title="告警管理",
        description="当学生出现使用异常（超时、夜间使用、表现下降等）时，系统会自动告警。",
        target_element="alerts_panel",
        action_required="查看告警列表",
        completion_check="alerts_viewed",
        tip="已处理的告警可以标记为'已解决'。",
    ),
    OnboardingStep(
        step_id="tchr_parent_comms", order=9,
        title="家长沟通",
        description="系统提供了家长沟通模板。一键生成周报、进步报告或关注通知。家长会收到结构化的学习摘要。",
        target_element="parent_comm_button",
        action_required="查看家长沟通工具",
        completion_check="parent_comm_viewed",
        tip="周报会自动生成，但你可以添加个性化备注。",
    ),
    OnboardingStep(
        step_id="tchr_complete", order=10,
        title="教师引导完成！",
        description="你已经掌握了教师端的核心功能。AI助手会在你需要时自动出现。你的每个决定都在影响学生的未来。",
        target_element="teacher_dashboard",
        action_required="开始管理你的班级",
        completion_check="onboarding_complete",
    ),
]


# ─── 家长引导 (8步) ─────────────────

PARENT_ONBOARDING = [
    OnboardingStep(
        step_id="par_welcome", order=1,
        title="欢迎，家长！",
        description="LearnFlow 帮助你了解孩子的学习状态——不是看分数，而是看成长。所有的数据都经过隐私保护处理。",
        target_element="parent_dashboard",
        action_required="点击「开始了解」",
        completion_check="welcome_dismissed",
        skip_allowed=False,
    ),
    OnboardingStep(
        step_id="par_bind_child", order=2,
        title="绑定你的孩子",
        description="输入孩子的账号信息来建立亲子关联。绑定后你可以查看学习摘要、接收周报、管理同意设置。",
        target_element="bind_child_form",
        action_required="绑定孩子的账号",
        completion_check="child_bound",
        tip="需要孩子的账号和初始密码。绑定后可以随时解绑。",
        skip_allowed=False,
    ),
    OnboardingStep(
        step_id="par_summary", order=3,
        title="学习摘要",
        description="这是孩子本周的学习概览。注意：我们展示的不是'分数'，而是'努力'——题数、正确率、坚持天数。",
        target_element="child_summary",
        action_required="查看孩子的学习摘要",
        completion_check="summary_viewed",
        tip="绿色文字=积极的信号。关注趋势而不是单次数据。",
    ),
    OnboardingStep(
        step_id="par_weekly_report", order=4,
        title="每周学习报告",
        description="每周你会收到一份自动生成的学习报告。包含：学习概览、高光时刻、成长领域、家长行动建议。",
        target_element="weekly_report",
        action_required="查看最近的周报",
        completion_check="report_viewed",
        tip="周报中的「家长行动建议」告诉你这周可以做一件什么事来支持孩子的学习。",
    ),
    OnboardingStep(
        step_id="par_addiction_report", order=5,
        title="学习热情报告",
        description="我们追踪的不是'是否沉迷'，而是'是否热爱'。这里展示孩子对学习的真实态度和习惯形成进度。",
        target_element="addiction_report",
        action_required="查看学习热情报告",
        completion_check="addiction_report_viewed",
        tip="'学习成瘾'在这里是好事——意味着学习习惯正在形成。",
    ),
    OnboardingStep(
        step_id="par_consent", order=6,
        title="同意管理",
        description="你可以为孩子开启或关闭特定功能。所有需要同意的功能都是可选的，关闭后不会影响学习。",
        target_element="consent_panel",
        action_required="查看并设置同意选项",
        completion_check="consent_viewed",
        tip="默认状态下，所有可选功能都是关闭的。你主动开启的任何功能都可以随时关闭。",
    ),
    OnboardingStep(
        step_id="par_teacher_msg", order=7,
        title="与教师沟通",
        description="教师可以向你发送消息。你也会收到教师的结构化报告。所有的沟通都在平台内完成。",
        target_element="teacher_messages",
        action_required="查看消息中心",
        completion_check="messages_viewed",
        tip="回复教师消息可以加深家校合作。",
    ),
    OnboardingStep(
        step_id="par_complete", order=8,
        title="家长引导完成！",
        description="你现在可以实时了解孩子的学习状态。记住：最好的支持不是监督，而是关注和鼓励。",
        target_element="parent_dashboard",
        action_required="开始查看孩子的学习",
        completion_check="onboarding_complete",
    ),
]


# ═══════════════════════════════════════════════════════════
# 2. 引导引擎
# ═══════════════════════════════════════════════════════════

class OnboardingEngine:
    """新手引导引擎"""

    # 每步完成后的奖励
    STEP_REWARDS = {
        "stu_first_question": {"xp": 20, "badge": "初出茅庐"},
        "stu_pet_birth": {"xp": 10, "unlock": "pet_system"},
        "stu_daily_goal": {"xp": 15, "unlock": "daily_goal"},
        "stu_complete": {"xp": 50, "badge": "引导完成", "unlock": "all_features"},
        "tchr_classroom": {"xp": 20, "unlock": "classroom_view"},
        "tchr_ai_analysis": {"xp": 30, "unlock": "ai_analysis"},
        "tchr_complete": {"xp": 50, "badge": "教师引导完成"},
        "par_bind_child": {"xp": 20, "unlock": "parent_features"},
        "par_complete": {"xp": 30, "badge": "家长引导完成"},
    }

    @classmethod
    def get_onboarding(cls, role: str) -> dict:
        """获取某角色的引导流程"""
        role_map = {
            "student": STUDENT_ONBOARDING,
            "teacher": TEACHER_ONBOARDING,
            "parent": PARENT_ONBOARDING,
        }
        steps = role_map.get(role, STUDENT_ONBOARDING)
        return {
            "role": role,
            "total_steps": len(steps),
            "steps": [
                {
                    "step_id": s.step_id,
                    "order": s.order,
                    "title": s.title,
                    "description": s.description,
                    "target_element": s.target_element,
                    "action_required": s.action_required,
                    "tip": s.tip,
                    "skip_allowed": s.skip_allowed,
                    "duration": s.duration_estimate,
                }
                for s in steps
            ],
            "estimated_total_time": cls._estimate_time(steps),
        }

    @classmethod
    def get_current_step(cls, role: str, completed_steps: List[str]) -> dict:
        """获取当前应该进行的步骤"""
        steps_map = {
            "student": STUDENT_ONBOARDING,
            "teacher": TEACHER_ONBOARDING,
            "parent": PARENT_ONBOARDING,
        }
        steps = steps_map.get(role, STUDENT_ONBOARDING)

        for step in steps:
            if step.step_id not in completed_steps:
                return {
                    "has_next": True,
                    "step_id": step.step_id,
                    "order": step.order,
                    "title": step.title,
                    "description": step.description,
                    "target_element": step.target_element,
                    "action_required": step.action_required,
                    "tip": step.tip,
                    "skip_allowed": step.skip_allowed,
                    "progress": f"{step.order}/{len(steps)}",
                    "progress_pct": round(step.order / len(steps) * 100),
                }

        return {"has_next": False, "message": "引导已完成！"}

    @classmethod
    def complete_step(cls, role: str, step_id: str) -> dict:
        """完成一个引导步骤"""
        reward = cls.STEP_REWARDS.get(step_id, {})
        return {
            "completed": True,
            "step_id": step_id,
            "xp_reward": reward.get("xp", 0),
            "badge": reward.get("badge"),
            "unlock": reward.get("unlock"),
            "message": f"✅ 步骤完成！" + (f" +{reward.get('xp', 0)} XP" if reward.get("xp") else ""),
        }

    @classmethod
    def skip_onboarding(cls, role: str) -> dict:
        """跳过引导"""
        return {
            "skipped": True,
            "message": "引导已跳过。你随时可以在设置中重新开启。",
            "reminder": "如果迷路了，点击页面右上角的「?」可以重新打开引导。",
        }

    @classmethod
    def _estimate_time(cls, steps: List[OnboardingStep]) -> str:
        total_seconds = 0
        for s in steps:
            if "分钟" in s.duration_estimate:
                total_seconds += int(s.duration_estimate.replace("分钟", "")) * 60
            elif "秒" in s.duration_estimate:
                total_seconds += int(s.duration_estimate.replace("秒", ""))
        if total_seconds < 60:
            return f"{total_seconds}秒"
        return f"{total_seconds // 60}分钟"


# ═══════════════════════════════════════════════════════════
# 3. 情境提示引擎 — 在哪里困惑就在哪里帮助
# ═══════════════════════════════════════════════════════════

class ContextualHelpEngine:
    """情境帮助引擎

    不是等用户来找帮助——在用户可能困惑的地方主动出现。
    """

    HELP_TRIGGERS = {
        "first_error": {
            "trigger": "连续错了3题",
            "message": "别担心！连续错误说明题目在挑战你的边界——这是成长最快的时刻。试试点击'看讲解'，或者降低一点难度。",
            "action": "show_explanation_or_lower_difficulty",
            "icon": "💡",
        },
        "idle_30s": {
            "trigger": "在题目页面停留30秒没动",
            "message": "需要帮助吗？你可以点击'提示'获得线索，或者跳过这道题。",
            "action": "show_hints_or_skip",
            "icon": "🤔",
        },
        "feature_unused": {
            "trigger": "有一个功能你已经3天没用了",
            "message": "你知道吗？{feature_name}可以帮助你{benefit}。试试看？",
            "action": "open_feature",
            "icon": "🔔",
        },
        "skip_frequent": {
            "trigger": "跳过了3道题",
            "message": "这些题目是不是太难了？系统可以自动帮你调整难度。",
            "action": "auto_adjust_difficulty",
            "icon": "🎚️",
        },
    }

    @classmethod
    def get_help_for_trigger(cls, trigger: str, context: dict = None) -> Optional[dict]:
        """获取情境帮助"""
        help_info = cls.HELP_TRIGGERS.get(trigger)
        if not help_info:
            return None

        message = help_info["message"]
        if context:
            for k, v in context.items():
                message = message.replace(f"{{{k}}}", str(v))

        return {
            "trigger": trigger,
            "message": message,
            "action": help_info["action"],
            "icon": help_info["icon"],
        }


# ═══════════════════════════════════════════════════════════
# 4. 功能发现引擎 — "你还没试过这个"
# ═══════════════════════════════════════════════════════════

class FeatureDiscoveryEngine:
    """功能发现引擎

    不是一次给完——在用户准备好时才介绍新功能。
    """

    FEATURE_UNLOCK_SCHEDULE = {
        "student": [
            {"after_sessions": 1, "feature": "pet_system", "message": "你的学习伙伴已经孵化！"},
            {"after_sessions": 2, "feature": "streak", "message": "连胜记录已解锁"},
            {"after_sessions": 3, "feature": "daily_goal", "message": "你可以设定自己的每日目标了"},
            {"after_sessions": 5, "feature": "skill_tree", "message": "学习方法技能树已解锁"},
            {"after_sessions": 7, "feature": "league", "message": "联赛排位已解锁"},
            {"after_sessions": 10, "feature": "team", "message": "战队系统已解锁"},
            {"after_sessions": 14, "feature": "godmode", "message": "学神冲刺模式已解锁"},
        ],
        "teacher": [
            {"after_sessions": 1, "feature": "classroom_view", "message": "班级仪表盘已就绪"},
            {"after_sessions": 2, "feature": "ai_analysis", "message": "AI学生分析已激活"},
            {"after_sessions": 3, "feature": "difficulty_control", "message": "难度调节面板已解锁"},
            {"after_sessions": 5, "feature": "intervention_plan", "message": "教学干预计划已生成"},
        ],
        "parent": [
            {"after_sessions": 1, "feature": "child_summary", "message": "学习摘要已生成"},
            {"after_sessions": 2, "feature": "weekly_report", "message": "第一份周报已生成"},
            {"after_sessions": 3, "feature": "addiction_report", "message": "学习热情报告已解锁"},
        ],
    }

    @classmethod
    def check_new_features(cls, role: str, sessions_completed: int) -> List[dict]:
        """检查是否有新功能可解锁"""
        schedule = cls.FEATURE_UNLOCK_SCHEDULE.get(role, [])
        newly_unlocked = []

        for item in schedule:
            if sessions_completed == item["after_sessions"]:
                newly_unlocked.append({
                    "feature": item["feature"],
                    "message": f"🎉 {item['message']}！点击探索新功能。",
                    "celebration": True,
                    "xp_bonus": 10,
                })

        return newly_unlocked
