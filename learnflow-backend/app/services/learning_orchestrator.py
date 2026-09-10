"""学习流编排器 —— 将 BKT、DDA、85% 规则、风险监控、学习方法推荐串联到同一事务中
"""
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.pet import PetProfile
from app.models.task import Task, Attempt, SpacedReview, StudentSkillProfile
from app.models.consent import Alert, AlertType, AlertSeverity
from app.services.knowledge_tracing import bkt_engine, KnowledgeState, SkillState
from app.services.dda import dda_engine, DDADirection
from app.services.optimal_difficulty import optimal_difficulty_engine
from app.services.risk_monitor import RiskMonitor, UsageSnapshot, RiskLevel
from app.services.spaced_repetition import SpacedRepetitionService
from app.services.pet_service import PetService
from app.services.feedback_service import FeedbackService, FeedbackContext
from app.services.learning_methods_engine import LearningMethodEngine
from app.services.duolingo_addiction_engine import XPEngine, XPState, XPEventType
from app.services.meta_learning_skilltree import SkillTreeEngine
from app.services.cache import (
    cache_ability, get_ability, invalidate_dashboard, invalidate_ability, ABILITY_TTL,
)
from app.services.audit import write_audit
from app.services import anti_addiction
from app.services.progression_repository import (
    load_xp_state,
    to_xp_state,
    save_xp_state,
    save_skill_tree,
    record_learning_event,
)
from app.services.learning_event_builder import build_submission_events
from app.services import mechanism_registry
from app.services.research_consent import resolve_research_consent
from app.services.mechanism_arbitrator import MechanismArbitrator
from app.services.mechanism_registry import Effect, EffectType, MechanismContext
from app.services.deep_addiction_engine import FOMOEngine
from app.services.deep_addiction_engine import (
    AppointmentEngine,
    AppointmentState,
    CuriosityEngine,
    ScarcityEngine,
    StreakSanctificationEngine,
)
from app.services.duolingo_addiction_engine import (
    MonthlyChallengeEngine,
    TimeBasedBonusEngine,
)
from app.services.addiction_engine_v3 import (
    PeakEndRuleEngine,
    SurpriseDelightEngine,
    ZeigarnikEngine,
)
from app.services.positive_addiction_engine import (
    HabitLoopEngine,
    HabitState,
    HookEngine,
    HookState,
    IdentityEngine,
    InstantGratificationEngine,
    ProgressVisualizationEngine,
    SocialContagionEngine,
    TriggerType,
)
from app.services.gamification_service import (
    CustomizationState,
    GamificationService,
    IKEAEngine,
    ProximalGoals,
)
from app.services.ux_addiction_engine import (
    ColorPsychologyEngine,
    HapticRhythmEngine,
    ProgressiveDisclosureEngine,
    SpatialAnchoringEngine,
)
from app.services.habit_addiction_engine import (
    ImplementationIntentionsEngine,
    SelfRegulationEngine,
    TemptationBundlingEngine,
)
from app.services.social_addiction_engine import (
    GiftEconomyEngine,
    ParentPortalEngine,
)
from app.models.analytics import AbilityEstimate, AuditKind


# ────────────────────────────────────────────────────────────
# 机制治理接线 (Task #10: 注册表驱动流水线)
#
# process_submission 的 11 步机制 + 1 个后置 nudge 仲裁步里, 凡「应用某个游戏化机制」
# 的步骤, 都在此登记其对应的 LF-M ID, 并构造期校验 ID 真实存在于 mechanism_registry。这样:
#   * 每一步对应哪个机制可审计 (论文附表可引用 LF-Mxx);
#   * 机制被 is_enabled(False) 关闭 (消融实验) 时, 对应步骤效果被**真实抑制**;
#   * 默认全部开启 → 运行行为不变 (677 测试不受影响)。
#
# 注意: BKT / 间隔复习 / 技能画像等是**算法**而非机制, 不在此登记。
# 门控一致性 (GAP-6 修复后):
#   健康护栏类机制 (LF-M51 forced_rest 强制休息 / LF-M52 minor_protection 未成年保护
#   / LF-M53 lai_downgrade 风险监控) 按治理策略拥有「一票否决权」, **始终开启、
#   exempt from ablation gating** —— 此处仅登记供审计, 不对其调用 is_enabled 门控。
#   可被 is_enabled 真实门控、从而在消融实验中按需抑制的机制只有三个:
#     * pet_companion  (LF-M22) —— 步骤 6  经 is_enabled 门控;
#     * xp_leveling    (LF-M19) —— 步骤 9  经 is_enabled 门控 (GAP-6 修复, 此前漏掉);
#     * fomo           (LF-M44) —— 步骤 12 经 is_enabled 门控 (经仲裁器下发)。
#   三者默认全部开启 → 运行行为不变; 关闭后对应步骤效果被真实抑制, 消融对照成立。
#
# 步骤 13 —— 孤儿机制评估钩子 (28 机制接线, 2026-09-04):
#   审计矩阵 (scan_mechanism_landing.py) 曾记录 28 个机制「有引擎逻辑、零运行时
#   调用方」(orphan)。本步骤把它们接线: 每个机制经显式 ``is_enabled("<key>")``
#   门控后, **真实调用其注册的引擎函数** (不伪造、不新增行为), 输出冻结进
#   ``decision_snapshot["mechanism_evaluations"]`` 供因果归因, 并随响应返回。
#   * 默认全开 → 仅多一份评估记录, XP/宠物/反馈/风险等主流程行为不变;
#   * 关闭某机制 → 该机制跳过评估 (消融对照成立);
#   * 单一引擎异常被 _mech_output 兜底捕获, 不拖垮整条流水线。
# ────────────────────────────────────────────────────────────

PIPELINE_MECHANISM_MAP: Dict[int, List[str]] = {
    6: ["pet_companion"],                      # LF-M22 虚拟宠物陪伴
    8: ["lai_downgrade", "forced_rest"],       # LF-M53 风险监控 / LF-M51 强制休息
    9: ["xp_leveling", "minor_protection"],     # LF-M19 XP等级 / LF-M52 未成年保护
    12: ["fomo"],                              # LF-M44 错失恐惧 — 经仲裁器下发
    13: [                                      # 孤儿机制评估钩子 (LF-Mxx 升序)
        "variable_ratio_reward",               # LF-M01 变比率奖励（宝箱）
        "instant_gratification",               # LF-M04 即时满足
        "surprise_delight",                    # LF-M05 惊喜与愉悦
        "time_based_bonus",                    # LF-M06 时间限定加成
        "scarcity",                            # LF-M08 稀缺性
        "streak_sanctification",               # LF-M12 连胜神圣化
        "zeigarnik",                           # LF-M13 蔡格尼克效应
        "peak_end",                            # LF-M14 峰终定律
        "goal_gradient",                       # LF-M15 目标梯度
        "daily_challenge",                     # LF-M16 每日/月度挑战
        "ikea_effect",                         # LF-M18 宜家效应
        "progress_visualization",              # LF-M20 进步可视化
        "progressive_disclosure",             # LF-M21 渐进式披露
        "social_contagion",                    # LF-M24 社会传染
        "gift_economy",                        # LF-M29 礼物经济
        "parent_portal",                       # LF-M32 家长门户
        "hook_model",                          # LF-M33 钩子模型
        "habit_loop",                          # LF-M34 习惯回路
        "cue_prompting",                       # LF-M35 情境线索提示
        "temptation_bundling",                 # LF-M37 诱惑捆绑
        "implementation_intentions",          # LF-M38 执行意图
        "self_regulation_goals",               # LF-M39 自我调节目标
        "commitment_device",                   # LF-M41 承诺装置/预约
        "curiosity_gap",                       # LF-M43 好奇心缺口
        "identity_motivation",                 # LF-M46 身份认同动机
        "color_psychology",                    # LF-M48 色彩与情绪
        "spatial_anchoring",                   # LF-M49 空间锚定
        "multisensory_packaging",              # LF-M50 多感官包装
    ],
}

# 构造期不变量: 接线里引用的机制 key 必须真实存在于注册表 (否则说明接线漂移)
for _step, _keys in PIPELINE_MECHANISM_MAP.items():
    for _k in _keys:
        mechanism_registry.get(_k)  # 未注册即抛 KeyError

# FOMO 后置 nudge 仲裁器单例 (LF-M44, 治理 §3.4.2): 引擎只产 Effect 候选,
# 由 MechanismArbitrator 三层漏斗决定下发; LF-M52 命中时在第 1 层丢弃。
_FOMO_ARBITRATOR = MechanismArbitrator()


# ────────────────────────────────────────────────────────────
# 步骤 13: 孤儿机制评估钩子 (28 机制接线)
#
# 设计原则 (数字诚信):
#   * 只调用 mechanism_registry 中已注册、已存在的引擎函数, 不新增/不伪造行为;
#   * 每个机制一条显式 ``is_enabled("<key>")`` 门控 —— scan_mechanism_landing.py
#     以字面量识别编排器接线, 关闭即跳过评估 (消融对照成立);
#   * 引擎输出全部是真实计算结果; 流水线未维护的状态 (预约/习惯线索等)
#     以空状态评估, 输出如实记录 (None/空), 绝不编造数据;
#   * 输出经 JSON 可序列化校验后冻结进 decision_snapshot, 供因果归因。
# ────────────────────────────────────────────────────────────

# 步骤 13 登记的全部机制 key (与 PIPELINE_MECHANISM_MAP[13] 同源)
_SECONDARY_MECHANISM_KEYS: List[str] = PIPELINE_MECHANISM_MAP[13]


@dataclass
class _EvalContext:
    """机制评估钩子的流水线上下文 (从 process_submission 各步汇聚)。"""

    user_id: str
    user_name: str
    topic: str
    difficulty: int
    is_correct: bool
    success_streak: int
    failure_streak: int
    day_streak: int
    attempts_today: int
    xp_earned: int
    pet_name: str


def _mech_output(fn, *args, **kwargs):
    """调用机制引擎并保证输出 JSON 可序列化; 单机制异常仅记录、不中断提交。"""
    try:
        out = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 —— 单机制失败不拖垮整条流水线
        return {"error": type(exc).__name__}
    try:
        json.dumps(out, ensure_ascii=False)
        return out
    except (TypeError, ValueError):
        return {"repr": str(out)[:200]}


def _evaluate_secondary_mechanisms(c: _EvalContext) -> Dict[str, Any]:
    """评估步骤 13 登记的 28 个机制: 门控 + 真实引擎调用。

    返回 ``{key: {"enabled": bool, "output": <引擎真实输出或 None>}}``。
    关闭的机制 ``output`` 恒为 None (未调用引擎, 无任何伪造输出)。
    """
    ev: Dict[str, Any] = {}

    # LF-M01 变比率奖励（宝箱）: 读取宝箱进度 (纯读, 不开箱不改状态)
    if mechanism_registry.is_enabled("variable_ratio_reward"):
        ev["variable_ratio_reward"] = _mech_output(
            GamificationService.get_box_status_for_user, c.user_id)

    # LF-M04 即时满足: 答后多维即时反馈包
    if mechanism_registry.is_enabled("instant_gratification"):
        ev["instant_gratification"] = _mech_output(
            InstantGratificationEngine.generate_instant_feedback,
            c.is_correct, c.topic, c.pet_name, c.success_streak)

    # LF-M05 惊喜与愉悦: 5% 概率随机惊喜彩蛋
    if mechanism_registry.is_enabled("surprise_delight"):
        ev["surprise_delight"] = _mech_output(SurpriseDelightEngine.roll_surprise)

    # LF-M06 时间限定加成: 当前时段奖励检查
    if mechanism_registry.is_enabled("time_based_bonus"):
        ev["time_based_bonus"] = _mech_output(TimeBasedBonusEngine.check_time_bonus)

    # LF-M08 稀缺性: 黄金题目解锁条件检查
    if mechanism_registry.is_enabled("scarcity"):
        ev["scarcity"] = _mech_output(
            ScarcityEngine.check_unlock, "golden_question",
            {"current_streak": c.success_streak})

    # LF-M12 连胜神圣化: 日连胜仪式 (含里程碑判定)
    if mechanism_registry.is_enabled("streak_sanctification"):
        ev["streak_sanctification"] = _mech_output(
            StreakSanctificationEngine.get_daily_ritual, c.day_streak)

    # LF-M13 蔡格尼克效应: 每日目标进度条张力 (10 题默认目标)
    if mechanism_registry.is_enabled("zeigarnik"):
        ev["zeigarnik"] = _mech_output(
            ZeigarnikEngine.get_progress_bar, c.attempts_today, 10)

    # LF-M14 峰终定律: 会话峰终总结 (高光时刻 + 结束语)
    if mechanism_registry.is_enabled("peak_end"):
        ev["peak_end"] = _mech_output(
            PeakEndRuleEngine.generate_session_end_summary,
            {"xp_earned": c.xp_earned, "max_correct_streak": c.success_streak})

    # LF-M15 目标梯度: 渐近目标进度 (含 80% 脉冲触发)
    if mechanism_registry.is_enabled("goal_gradient"):
        ev["goal_gradient"] = _mech_output(
            GamificationService.get_goal_progress,
            ProximalGoals(
                daily_completed=c.attempts_today, current_streak=c.success_streak))

    # LF-M16 每日/月度挑战: 当月挑战与剩余天数
    if mechanism_registry.is_enabled("daily_challenge"):
        ev["daily_challenge"] = _mech_output(MonthlyChallengeEngine.get_current_challenge)

    # LF-M18 宜家效应: 自主定制所有权摘要 (流水线未维护定制状态, 如实按默认态)
    if mechanism_registry.is_enabled("ikea_effect"):
        ev["ikea_effect"] = _mech_output(
            IKEAEngine.get_ownership_summary, CustomizationState())

    # LF-M20 进步可视化: 每周成长报告
    if mechanism_registry.is_enabled("progress_visualization"):
        ev["progress_visualization"] = _mech_output(
            ProgressVisualizationEngine.generate_weekly_growth_report,
            {"weekly_questions": c.attempts_today, "accuracy_trend": "stable"})

    # LF-M21 渐进式披露: 功能揭示阶梯 (按今日答题数近似会话进度)
    if mechanism_registry.is_enabled("progressive_disclosure"):
        ev["progressive_disclosure"] = _mech_output(
            ProgressiveDisclosureEngine.get_disclosure_state, c.attempts_today)

    # LF-M24 社会传染: 友好比较推动 (班级侧数据流水线未接入, 如实传空, 不伪造)
    if mechanism_registry.is_enabled("social_contagion"):
        ev["social_contagion"] = _mech_output(
            SocialContagionEngine.get_friendly_competition_nudge,
            {"streak": c.success_streak},
            {"max_streak": 0, "class_avg_accuracy": 0, "active_peers": 0})

    # LF-M29 礼物经济: 送礼资格检查 (以日连胜为学习成果余额)
    if mechanism_registry.is_enabled("gift_economy"):
        ev["gift_economy"] = _mech_output(
            GiftEconomyEngine.can_send_gift, c.day_streak, "star")

    # LF-M32 家长门户: 周报摘要生成
    if mechanism_registry.is_enabled("parent_portal"):
        ev["parent_portal"] = _mech_output(
            ParentPortalEngine.generate_weekly_digest,
            c.user_name,
            {"current_streak": c.day_streak, "weekly_questions": c.attempts_today},
        )

    # LF-M33 钩子模型: 内部好奇触发 (临时状态, 评估触发文案)
    if mechanism_registry.is_enabled("hook_model"):
        ev["hook_model"] = _mech_output(
            HookEngine.trigger,
            HookState(user_id=c.user_id), TriggerType.INTERNAL_CURIOSITY)

    # LF-M34 习惯回路: 会话记录 (临时状态, 评估习惯强度/阶段)
    if mechanism_registry.is_enabled("habit_loop"):
        ev["habit_loop"] = _mech_output(HabitLoopEngine.record_session, HabitState())

    # LF-M35 情境线索提示: 目标时间临近提示 (未设目标时引擎如实返回 None)
    if mechanism_registry.is_enabled("cue_prompting"):
        ev["cue_prompting"] = _mech_output(HabitLoopEngine.get_cue_prompt, HabitState())

    # LF-M37 诱惑捆绑: 捆绑方案建议
    if mechanism_registry.is_enabled("temptation_bundling"):
        ev["temptation_bundling"] = _mech_output(TemptationBundlingEngine.suggest_bundle, {})

    # LF-M38 执行意图: if-then 计划生成
    if mechanism_registry.is_enabled("implementation_intentions"):
        ev["implementation_intentions"] = _mech_output(
            ImplementationIntentionsEngine.generate_if_then)

    # LF-M39 自我调节目标: 会话后反思提示
    if mechanism_registry.is_enabled("self_regulation_goals"):
        ev["self_regulation_goals"] = _mech_output(
            SelfRegulationEngine.reflect_on_session,
            c.user_id, {"questions_done": c.attempts_today})

    # LF-M41 承诺装置/预约: 预约提醒 (无预约时引擎如实返回 None)
    if mechanism_registry.is_enabled("commitment_device"):
        ev["commitment_device"] = _mech_output(
            AppointmentEngine.get_appointment_nudge, AppointmentState())

    # LF-M43 好奇心缺口: 下一题悬念式结尾
    if mechanism_registry.is_enabled("curiosity_gap"):
        ev["curiosity_gap"] = _mech_output(
            CuriosityEngine.generate_cliffhanger, c.topic, c.difficulty)

    # LF-M46 身份认同动机: 学习者身份评估与肯定
    if mechanism_registry.is_enabled("identity_motivation"):
        ev["identity_motivation"] = _mech_output(
            IdentityEngine.assess_identity,
            {"current_streak": c.day_streak, "total_attempts": c.attempts_today})

    # LF-M48 色彩心理学: 答题场景色彩主题 (答对=成就/答错=支持)
    if mechanism_registry.is_enabled("color_psychology"):
        ev["color_psychology"] = _mech_output(
            ColorPsychologyEngine.get_theme_for_context,
            "success" if c.is_correct else "encourage")

    # LF-M49 空间锚定: 布局规范 (拇指区优化)
    if mechanism_registry.is_enabled("spatial_anchoring"):
        ev["spatial_anchoring"] = _mech_output(SpatialAnchoringEngine.get_layout_spec)

    # LF-M50 多感官包装: 触觉反馈模式 (答对庆祝/答错温柔提醒)
    if mechanism_registry.is_enabled("multisensory_packaging"):
        ev["multisensory_packaging"] = _mech_output(
            HapticRhythmEngine.get_haptic_for_event,
            "correct_answer" if c.is_correct else "incorrect_answer",
            c.success_streak)

    # 统一输出形状: 开启 → {"enabled": True, "output": 真实输出}; 关闭 → output=None
    return {
        key: (
            {"enabled": True, "output": ev[key]}
            if key in ev else
            {"enabled": False, "output": None}
        )
        for key in _SECONDARY_MECHANISM_KEYS
    }


# ────────────────────────────────────────────────────────────
# 技能树 → 仓储层格式转换 (纯函数, 便于单测)
#
# 本函数是 **双形状适配器**, 同时接受两种入参:
#
#   1) 引擎视图结构 (SkillTreeEngine.get_skill_tree 的返回值):
#      {"meta_level": int, "meta_title": str, "total_times_used": int,
#       "categories": {<cat>: [ {"id": skill_id, "level": int,
#                                "times_used": int, ...}, ... ]},
#       "combo_bonus": ...}
#      —— 需先按 categories 展平, 取每项的 "id" 作为 skill_id。
#
#   2) 扁平结构 (既有调用方与单测使用):
#      {skill_id: {"level": int, "times_used": int}}
#
# progression_repository.save_skill_tree 需要
# {skill_id: {proficiency, level, total_uses}}; proficiency 由 level/10 近似 (0~1)。
#
# 历史缺陷: 早期实现只按 (2) 处理, 却被调用点喂以 (1), 首个键 "meta_level" 的值为
# int, 触发 AttributeError: 'int' object has no attribute 'get' —— 凡 db 非 None
# 的提交路径必崩。此处按 "categories" 键做形状判别以同时兼容两者。
# ────────────────────────────────────────────────────────────

def _skilltree_repo_format(tree: dict) -> Dict[str, Dict[str, Any]]:
    if not tree:
        return {}

    def _pack(level: Any, times_used: Any) -> Dict[str, Any]:
        lvl = int(level) if level is not None else 1
        return {
            "proficiency": round(lvl / 10.0, 3),
            "level": lvl,
            "total_uses": int(times_used or 0),
        }

    # 形状 (1): 引擎视图结构 —— 按 categories 展平
    categories = tree.get("categories")
    if isinstance(categories, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for entries in categories.values():
            if not isinstance(entries, (list, tuple)):
                continue
            for s in entries:
                if not isinstance(s, dict):
                    continue
                sid = s.get("id") or s.get("skill_id")
                if not sid:
                    continue
                out[str(sid)] = _pack(s.get("level", 1), s.get("times_used", 0))
        return out

    # 形状 (2): 扁平结构
    out2: Dict[str, Dict[str, Any]] = {}
    for sid, s in tree.items():
        if not isinstance(s, dict):
            continue
        out2[str(sid)] = _pack(s.get("level", 1), s.get("times_used", 0))
    return out2


class LearningOrchestrator:
    """核心学习流编排器

    负责：
    - build_next_task: 生成下一题（融合 BKT / DDA / 85% 规则 / 风险 / 学习方法）
    - process_submission: 处理答题提交（答题记录、BKT 更新、间隔复习、宠物成长、风险告警、XP、方法 XP）
    """

    # 难度融合权重
    BKT_WEIGHT = 0.45
    DDA_WEIGHT = 0.35
    OPTIMAL_WEIGHT = 0.20

    @classmethod
    async def build_next_task(
        cls,
        user: User,
        topic: Optional[str],
        db: AsyncSession,
    ) -> dict:
        """获取下一题

        Returns:
            {
                "task": TaskOut,
                "dda": DDAResponse,
                "bkt": BKTResponse,
                "learning_tip": dict,
                "risk": dict,
            }
        """
        # 1. 最近 20 次答题记录（全主题，用于 DDA 和 BKT 全局状态）
        attempts_query = await db.execute(
            select(Attempt)
            .where(Attempt.user_id == user.id)
            .order_by(Attempt.created_at.desc())
            .limit(20)
        )
        recent_attempts = list(reversed(attempts_query.scalars().all()))
        recent_results = [a.is_correct for a in recent_attempts]

        # 2. 当前主题技能画像
        skill: Optional[StudentSkillProfile] = None
        if topic:
            skill_query = await db.execute(
                select(StudentSkillProfile).where(
                    StudentSkillProfile.user_id == user.id,
                    StudentSkillProfile.skill_dim == topic,
                )
            )
            skill = skill_query.scalar_one_or_none()

        current_difficulty = int((skill.score or 50) / 10) if skill else 5

        # 年龄学段（用于反成瘾分层）
        age_band = anti_addiction.infer_age_band(user)

        # 3. 能力估计：优先读缓存/库，缺失或超 TTL 才历史重算（AC2）
        recent_rate = sum(recent_results) / max(len(recent_results), 1) if recent_results else 0.0
        total_attempts = len(recent_attempts)
        theta: float = 1500.0
        sigma: float = 350.0
        cached = await cls._load_ability(user, db)
        if cached is not None:
            theta, sigma = cached
            bkt_mastery = max(0.0, min(1.0, (theta - 800) / 1400))
            bkt_recommended = int(max(1, min(10, round(bkt_mastery * 9 + 1))))
            bkt_skill = None
        else:
            bkt_state = await cls._build_bkt_state(user.id, topic, db)
            bkt_skill = bkt_state.skills.get(topic) if topic else None
            if bkt_skill is None and bkt_state.skills:
                # 无指定主题时取平均掌握度最高的技能
                bkt_skill = max(bkt_state.skills.values(), key=lambda s: s.p_mastery)
            bkt_mastery = bkt_skill.p_mastery if bkt_skill else 0.5
            bkt_recommended = bkt_engine.recommend_difficulty(bkt_skill) if bkt_skill else 5
            theta = 800 + bkt_mastery * 1400  # 映射到 Elo 量纲
            sigma = 350 - min(325, total_attempts * 6)

        # 4. 85% 规则 / 最优难度
        optimal_result = optimal_difficulty_engine.compute_optimal_difficulty(
            student_theta=theta,
            student_sigma=sigma,
            recent_success_rate=recent_rate,
            n_total_attempts=total_attempts,
        )
        optimal_d = int(round(optimal_result.optimal_d))

        # 5. DDA 计算
        dda_result = dda_engine.calculate(recent_results, current_difficulty)

        # 6. 融合难度
        fused_difficulty = cls._compute_fused_difficulty(
            bkt_recommended, dda_result.difficulty, optimal_d
        )

        # 7. 查找题目
        task_query = await db.execute(
            select(Task)
            .where(Task.difficulty == fused_difficulty, Task.is_approved == True)
            .order_by(func.random())
            .limit(1)
        )
        task = task_query.scalar_one_or_none()

        if not task:
            # 回退：找附近难度
            task_query = await db.execute(
                select(Task)
                .where(
                    Task.difficulty.between(
                        max(1, fused_difficulty - 1),
                        min(10, fused_difficulty + 1),
                    ),
                    Task.is_approved == True,
                )
                .order_by(func.random())
                .limit(1)
            )
            task = task_query.scalar_one_or_none()

        if not task:
            raise Exception("暂无匹配难度的题目")

        # 8. 风险监控
        risk_snapshot = await cls._build_risk_snapshot(user, db)
        risk_signals = RiskMonitor.check_consecutive_failure(risk_snapshot.consecutive_failures)
        risk_signals.update(RiskMonitor.check_repeated_skill(risk_snapshot.repeated_skill_attempts))

        # 8b. 反成瘾：会话超时难度重置标记（Spec P0 / AC9）
        reset_decision = anti_addiction.session_reset_decision(risk_snapshot.total_minutes, age_band)
        if reset_decision["should_reset_difficulty"]:
            await write_audit(
                db, AuditKind.RISK, user_id=str(user.id),
                input_json={"session_minutes": reset_decision["session_minutes"]},
                output_json={"reset_marker": reset_decision["reset_marker"], "rest_minutes": reset_decision["rest_minutes"]},
                subject=topic, age_band=age_band,
            )

        # 9. 学习方法推荐
        learning_tip = LearningMethodEngine.get_post_question_tip(
            current_topic=topic or task.topic,
            is_correct=True,  # 预览时默认推荐正确场景的方法
        )

        # 10. 持久化能力估计（仅在本次发生了全历史重算时）+ 难度决策审计
        if cached is None:
            await cls._save_ability(user, theta, sigma, db)
            await write_audit(
                db, AuditKind.DIFFICULTY, user_id=str(user.id),
                input_json={"topic": topic, "recent_rate": round(recent_rate, 3), "total_attempts": total_attempts},
                output_json={
                    "fused_difficulty": fused_difficulty,
                    "theta": round(theta, 1),
                    "sigma": round(sigma, 1),
                    "bkt_mastery": round(bkt_mastery, 3),
                },
                subject=topic, age_band=age_band,
            )

        return {
            "task": cls._task_to_dict(task),
            "challenge_band": {
                "current": int(task.difficulty * 10),  # 难度 1–10 → 0–100
                "low": 75,
                "high": 85,
            },
            "dda": {
                "direction": dda_result.direction.value,
                "pet_reaction": dda_result.pet_reaction.value,
                "feedback_text": dda_result.feedback_text,
                "success_rate": round(dda_result.success_rate * 100, 1),
            },
            "bkt": {
                "mastery": round(bkt_mastery, 3),
                "mastery_pct": round(bkt_mastery * 100, 1),
                "recommended_difficulty": bkt_recommended,
                "level": bkt_engine._mastery_level(bkt_mastery),
            },
            "learning_tip": {
                "method": learning_tip.get("method"),
                "title": learning_tip.get("title"),
                "icon": learning_tip.get("icon"),
                "short": learning_tip.get("short"),
                "detail": learning_tip.get("detail"),
                "action": learning_tip.get("action"),
            },
            "risk": {
                "consecutive_failures": risk_snapshot.consecutive_failures,
                "should_reduce_difficulty": risk_signals.get("should_reduce_difficulty", False),
                "should_switch_topic": risk_signals.get("should_switch", False),
                "message": risk_signals.get("message", ""),
            },
            "anti_addiction": {
                "session_minutes": reset_decision["session_minutes"],
                "should_reset_difficulty": reset_decision["should_reset_difficulty"],
                "reset_marker": reset_decision["reset_marker"],
                "rest_minutes": reset_decision["rest_minutes"],
                "age_band": age_band,
            },
        }

    @classmethod
    async def process_submission(
        cls,
        user: User,
        task: Task,
        req: dict,
        db: AsyncSession,
    ) -> dict:
        """处理答题提交

        Args:
            user: 当前用户
            task: 题目对象
            req: {
                "answer": str,
                "time_spent": int | None,
                "hints_used": int,
                "is_retry": bool,
                "is_creative": bool,
            }

        Returns:
            完整提交响应
        """
        answer = req.get("answer", "")
        time_spent = req.get("time_spent")
        hints_used = req.get("hints_used", 0) or 0
        is_retry = req.get("is_retry", False)
        is_creative = req.get("is_creative", False)

        # 年龄学段（反成瘾分层）
        age_band = anti_addiction.infer_age_band(user)

        # 1. 判断对错
        is_correct = cls._compare_answer(answer, task.correct_answer)

        # 会话标识: 前端可传入 session_id 串联同一学习会话; 否则回退到用户级 id
        session_id = req.get("session_id") or f"u{user.id}"

        # 2. 创建答题记录
        attempt = Attempt(
            user_id=user.id,
            task_id=task.id,
            answer=answer,
            is_correct=is_correct,
            time_spent=time_spent,
            hints_used=hints_used,
            difficulty_at_time=task.difficulty,
        )
        db.add(attempt)
        await db.flush()

        # 3. 更新技能画像
        skill = await cls._ensure_skill_profile(user.id, task.topic, db)
        skill.total_attempts += 1
        if is_correct:
            skill.correct_attempts += 1
        skill.score = (skill.success_rate or 0) * 100
        await db.flush()

        # 4. 更新 BKT
        bkt_state = await cls._build_bkt_state(user.id, task.topic, db)
        updated_skill = bkt_engine.update(bkt_state, task.topic, is_correct)
        skill.mastery = updated_skill.p_mastery
        await db.flush()

        # 5. 间隔复习计划
        existing_review = await db.execute(
            select(SpacedReview)
            .where(SpacedReview.user_id == user.id, SpacedReview.task_id == task.id)
            .order_by(SpacedReview.review_number.desc())
            .limit(1)
        )
        last_review = existing_review.scalar_one_or_none()
        review_number = last_review.review_number if last_review else 0
        current_interval = last_review.next_interval_days if last_review else None

        next_review = SpacedRepetitionService.calculate_next_review(
            review_number=review_number,
            was_correct=is_correct,
            current_interval=current_interval,
        )
        spaced_review = SpacedReview(
            user_id=user.id,
            task_id=task.id,
            review_number=next_review["next_review_number"],
            scheduled_date=next_review["next_review_date"],
            next_interval_days=next_review["next_interval_days"],
            result=is_correct,
        )
        db.add(spaced_review)
        await db.flush()

        # 6. 宠物更新 (LF-M22 虚拟宠物陪伴)
        #    注册表门控: 该机制被 is_enabled(False) 关闭 (消融实验) 时跳过成长更新,
        #    默认开启 → 行为不变。
        pet = await cls._ensure_pet(user, db)
        if pet and mechanism_registry.is_enabled("pet_companion"):
            if is_correct:
                pet_event = PetService.calculate_correct_answer(
                    difficulty=task.difficulty,
                    hints_used=hints_used,
                    is_retry=is_retry,
                    is_creative=is_creative,
                )
            else:
                pet_event = PetService.calculate_wrong_answer(
                    difficulty=task.difficulty,
                    chosen_recovery="pending",
                )
            PetService.apply_update(pet, pet_event)
            await db.flush()

        # 7. 生成反馈（含学习方法提示）
        streak_attempts = await db.execute(
            select(Attempt)
            .where(Attempt.user_id == user.id)
            .order_by(Attempt.created_at.desc())
            .limit(20)
        )
        streak_list = list(streak_attempts.scalars().all())
        success_streak = 0
        for a in streak_list:
            if a.is_correct:
                success_streak += 1
            else:
                break
        failure_streak = 0
        for a in streak_list:
            if not a.is_correct:
                failure_streak += 1
            else:
                break

        # 决策快照: 冻结本次提交涉及的机制决策输入, 供因果归因 (论文可复现性)。
        # success_streak / failure_streak 在 step 7 才计算, 故快照在此处构造;
        # risk_level / xp_suppressed 在 step 8 / step 9 之后回填。
        decision_snapshot = {
            "is_correct": is_correct,
            "risk_level": None,
            "xp_suppressed": False,
            "success_streak": success_streak,
            "failure_streak": failure_streak,
            "mechanism_toggles": {},
        }

        ctx = FeedbackContext(
            is_correct=is_correct,
            student_name=user.name,
            topic=task.topic,
            difficulty=task.difficulty,
            success_streak=success_streak,
            failure_streak=failure_streak,
            total_attempts_today=len(streak_list),
            pet_name=pet.name if pet else "小豆",
        )
        feedback = FeedbackService.generate_task_feedback(ctx)

        # 8. 风险监控与告警
        risk_snapshot = await cls._build_risk_snapshot(user, db)
        risk_assessment = RiskMonitor.assess([risk_snapshot])
        risk_alert = None
        if risk_assessment.level >= RiskLevel.WARNING:
            alert = Alert(
                user_id=user.id,
                alert_type=AlertType.CONSECUTIVE_FAILURE if risk_snapshot.consecutive_failures >= 5 else AlertType.PERFORMANCE_DROP,
                severity=AlertSeverity.RED if risk_assessment.level == RiskLevel.INTERVENTION else AlertSeverity.YELLOW,
                title="学习风险提醒" if risk_assessment.level == RiskLevel.WARNING else "需要休息",
                description="; ".join(risk_assessment.alerts) if risk_assessment.alerts else "系统检测到学习状态异常",
                data_snapshot={
                    "consecutive_failures": risk_snapshot.consecutive_failures,
                    "total_minutes": risk_snapshot.total_minutes,
                    "skip_ratio": risk_snapshot.skip_ratio,
                },
            )
            db.add(alert)
            await db.flush()
            await write_audit(
                db, AuditKind.RISK, user_id=str(user.id),
                input_json={"consecutive_failures": risk_snapshot.consecutive_failures, "total_minutes": risk_snapshot.total_minutes},
                output_json={"level": risk_assessment.zone.value, "title": alert.title},
                subject=task.topic, age_band=age_band,
            )
            risk_alert = {
                "level": risk_assessment.zone.value,
                "title": alert.title,
                "description": alert.description,
                "should_rest": risk_assessment.should_force_rest,
            }

        # 回填风险等级到决策快照 (即使未触发告警, 也记录评估等级用于因果归因)
        decision_snapshot["risk_level"] = risk_assessment.level.value

        # 8b. 未成年保护合规校验 (LF-M52)。
        #
        # 治理审计发现的历史缺陷：机制注册表把 LF-M52 的 impl_ref 指向
        # anti_addiction_compliance.MinorProtectionEngine，但该引擎在生产代码中
        # **零调用方**——编排器此前只使用 anti_addiction 的粗粒度规则（25 分钟会话
        # 重置），缺少「每日时长上限」与「夜间禁用」两项合规硬要求，形成
        # "注册表宣称已落地、实现从未运行" 的可证伪缺口。
        #
        # 现经 anti_addiction.minor_protection_decision 门面委托真实引擎执行三级
        # 校验。健康护栏类机制按治理策略 exempt，不受消融门控影响。
        minor_protection = anti_addiction.minor_protection_decision(
            user_id=str(user.id),
            age_band=age_band,
            daily_minutes=risk_snapshot.total_minutes,
            # 无真实会话时钟，以当日累计值兜底 —— 局限见门面 docstring
            consecutive_minutes=None,
        )
        decision_snapshot["minor_protection"] = minor_protection

        # 9. XP 奖励
        #    修复伪持久化：原先此处 `XPState()` 每次请求从零构造，结果只写进
        #    响应体、从不落库，导致用户 XP/等级/连胜在每次提交后归零。
        #    现改为从数据库载入持久状态，计算后回写。
        xp_row = await load_xp_state(db, str(user.id))
        xp_state = to_xp_state(xp_row)

        # 9b. 反成瘾：未成年奖励冷却（Spec P0 / AC10）
        #    必须在 award_xp 之前判定抑制：XPEngine.award_xp 会就地修改
        #    XPState（累加 total/weekly/today 并可能升级），若沿用旧写法
        #    "先授予、再清零响应字典"，被抑制的奖励仍会写入持久状态。
        reward_decision = anti_addiction.reward_cooldown_decision(None, age_band)
        reward_suppressed = False
        if anti_addiction.is_minor(age_band):
            # 变比率触发：仅在概率内给予强奖励，否则冷却（不重复强奖励）
            if random.random() > reward_decision["trigger_probability"]:
                reward_suppressed = True

        # 8b 续：合规校验判定阻断（夜间禁用 / 每日上限 / 连续超限）时同样抑制奖励。
        # 设计取舍 —— 不拦截"提交"本身：答题记录与 BKT 更新必须完成，否则会污染
        # 学习记录与能力估计；被抑制的是**投入型反馈**（XP、FOMO nudge），即成瘾
        # 机制的驱动端。这与既有 reward_suppressed 的语义一致。
        if minor_protection["should_block"]:
            reward_suppressed = True

        # GAP-6 修复：xp_leveling (LF-M19) 消融门控。
        # 该机制被 is_enabled(False) 关闭（消融实验）时，跳过 award_xp，产出零化的
        # xp_result，使「关闭 LF-M19」能真正抑制等级成长；默认开启 → 行为不变。
        # 注意：健康护栏 (LF-M51/52/53) 按治理策略始终开启、不受此门控（exempt）。
        xp_leveling_enabled = mechanism_registry.is_enabled("xp_leveling")

        # event_type 在任一分支都可能用于审计，统一在此计算
        event_type = XPEventType.PERFECT_LESSON if is_correct and hints_used == 0 else (
            XPEventType.HARD_CORRECT if is_correct and task.difficulty >= 7 else
            XPEventType.LESSON_COMPLETE
        )

        if reward_suppressed:
            # 不调用 award_xp，状态原样保留（仅更新连胜后由下方 save 统一回写）
            xp_result = {
                "xp_earned": 0,
                "total_xp": xp_state.total_xp,
                "today_xp": xp_state.today_xp,
                "weekly_xp": xp_state.weekly_xp,
                "leveled_up": False,
                "new_level": None,
                "has_boost": xp_state.boost_remaining_minutes > 0,
                "message": "休息一下，知识已经在你脑中沉淀。",
            }
        elif not xp_leveling_enabled:
            # 机制已关闭（消融实验对照）：跳过 award_xp，状态原样保留
            xp_result = {
                "xp_earned": 0,
                "total_xp": xp_state.total_xp,
                "today_xp": xp_state.today_xp,
                "weekly_xp": xp_state.weekly_xp,
                "leveled_up": False,
                "new_level": None,
                "has_boost": xp_state.boost_remaining_minutes > 0,
                "message": "（机制已关闭）实验对照",
            }
        else:
            xp_result = XPEngine.award_xp(xp_state, event_type, streak=success_streak)

        # 回填奖励抑制标记到决策快照（未成年冷却 或 xp_leveling 关闭 均视为 XP 被抑制）
        xp_suppressed_effective = reward_suppressed or not xp_leveling_enabled
        decision_snapshot["xp_suppressed"] = xp_suppressed_effective

        # 12. FOMO 后置 nudge 仲裁 (LF-M44, 治理 §3.4.2): 引擎只产 Effect 候选,
        # 由 MechanismArbitrator 三层漏斗决定下发; 未成年保护 (LF-M52) 命中时在第 1 层丢弃。
        fomo_effects: List[Effect] = []
        if mechanism_registry.is_enabled("fomo"):
            _fomo_cand = FOMOEngine.generate_fomo_nudge(FOMOEngine.get_active_challenges())
            if _fomo_cand is not None:
                fomo_effects.append(_fomo_cand)
        # 未成年保护作为健康一票否决方: 由 8b 的真实合规引擎结论驱动。
        # 原实现仅凭 `is_minor(age_band)` 这一粗粒度学段布尔值构造 Effect，
        # 未使用 LF-M52 声明的实现（MinorProtectionEngine）。现改为：
        #   - 确为未成年 **且** 合规校验判定阻断 → 构造健康 Effect，
        #     触发 Layer1 把全部 approach（含 FOMO）丢弃；
        #   - 未成年但未触发阻断 → 不否决，避免过度抑制正常学习。
        # payload 携带真实状态与文案，便于离线审计与论文归因。
        if minor_protection["is_minor"] and minor_protection["should_block"]:
            fomo_effects.append(Effect(
                mechanism_id="LF-M52",
                effect_type=EffectType.NOTIFICATION,
                payload={
                    "reason": "minor_protection_veto",
                    "status": minor_protection["status"],
                    "age_group": minor_protection["age_group"],
                    "message": minor_protection["message"],
                    "rest_minutes": minor_protection["rest_minutes"],
                },
                priority=100,
                cost=0.0,
                user_visible=False,
                health_critical=True,
                direction="withdraw",
            ))
        _fomo_ctx = MechanismContext(user_id=str(user.id), session_id=session_id)
        _fomo_delivered = _FOMO_ARBITRATOR.arbitrate(_fomo_ctx, fomo_effects)
        _fomo_nudge = next(
            (e.payload for e in _fomo_delivered if e.mechanism_id == "LF-M44"), None
        )

        # 连胜维护（v1 中 success_streak 为临时计算，同样不落库）
        if is_correct:
            xp_row.current_streak = (xp_row.current_streak or 0) + 1
            xp_row.longest_streak = max(xp_row.longest_streak or 0, xp_row.current_streak)
        else:
            xp_row.current_streak = 0

        # 回写持久状态（抑制时 xp_state 未被修改，回写等价于仅更新连胜）
        await save_xp_state(db, xp_row, xp_state)
        await write_audit(
            db, AuditKind.REWARD, user_id=str(user.id),
            input_json={"is_correct": is_correct, "difficulty": task.difficulty, "event_type": event_type.value if hasattr(event_type, "value") else str(event_type)},
            output_json={
                "xp_earned": xp_result.get("xp_earned"),
                "suppressed": xp_suppressed_effective,
                "trigger_probability": reward_decision["trigger_probability"],
            },
            subject=task.topic, age_band=age_band,
        )

        # 13. 孤儿机制评估钩子 (28 机制接线): 每个机制经 is_enabled 门控后
        #     真实调用其注册引擎函数, 输出冻结进决策快照 (因果归因) 并随响应返回。
        #     默认全开 → 仅多一份评估记录, 主流程行为不变; 关闭 → 跳过评估。
        mechanism_evaluations = _evaluate_secondary_mechanisms(_EvalContext(
            user_id=str(user.id),
            user_name=user.name or "同学",
            topic=task.topic,
            difficulty=task.difficulty,
            is_correct=is_correct,
            success_streak=success_streak,
            failure_streak=failure_streak,
            day_streak=xp_row.current_streak or 0,
            attempts_today=len(streak_list),
            xp_earned=xp_result.get("xp_earned", 0),
            pet_name=pet.name if pet else "小豆",
        ))
        decision_snapshot["mechanism_evaluations"] = mechanism_evaluations

        # 10. 学习方法 XP
        method_tip = LearningMethodEngine.get_post_question_tip(
            current_topic=task.topic,
            is_correct=is_correct,
        )
        method_result = SkillTreeEngine.use_skill(
            str(user.id), method_tip.get("method", "retrieval_practice"), effectiveness=1.0, db=db
        )

        # 自愈式技能树持久化: use_skill 保持同步且不落库, 此处接管的协程把
        # 最新技能树 upsert 到 user_skill_tree (db 为 None 时跳过, 兼容无 DB 路径)。
        if db is not None:
            tree = SkillTreeEngine.get_skill_tree(str(user.id))
            await save_skill_tree(db, str(user.id), _skilltree_repo_format(tree))

        await db.flush()

        # 学习事件埋点: 把本次提交拆解为 attempt / risk_assessment / xp_award /
        # method_xp 四类事件并落库 (record_learning_event 此前从未被调用)。
        # 仅当 db 可用时执行; decision_snapshot 已含风险等级与奖励抑制标记,
        # 以及 success/failure 连胜, 供因果归因冻结决策输入。
        if db is not None:
            # 研究知情同意标记（博士论文伦理合规，标记式不阻断）：
            # 每次提交只查一次同意状态，复用至本次提交产生的全部事件。
            # 未取得同意时事件照样写入，仅标记为 False/None——绝不拦截提交。
            # 若 db/user 异常，resolve_research_consent 返回 None（容错），
            # 事件以未知标记写入，不影响主流程。
            consent_status = await resolve_research_consent(db, user)
            events = build_submission_events(
                str(user.id),
                session_id,
                str(task.id),
                is_correct,
                risk_level=decision_snapshot.get("risk_level"),
                xp_suppressed=decision_snapshot["xp_suppressed"],
                success_streak=success_streak,
                failure_streak=failure_streak,
                method_skill=method_tip.get("method"),
                decision_snapshot=decision_snapshot,
            )
            for ev in events:
                ev["research_consented"] = consent_status.consented
                await record_learning_event(db, **ev)

        # 11. 提交作答后失效相关缓存键（看板 + 能力估计）
        await invalidate_dashboard(user.id)
        await invalidate_ability(user.id)

        return {
            "is_correct": is_correct,
            "correct_answer": task.correct_answer if not is_correct else None,
            "explanation": task.explanation if not is_correct else None,
            "feedback": feedback,
            "pet_update": {
                "understanding": round(pet.understanding, 1) if pet else 50.0,
                "persistence": round(pet.persistence, 1) if pet else 50.0,
                "creativity": round(pet.creativity, 1) if pet else 50.0,
                "collaboration": round(pet.collaboration, 1) if pet else 50.0,
                "mood": pet.mood.value if pet else "happy",
                "level": pet.level if pet else 1,
            } if pet else None,
            "spaced_review": {
                "scheduled_date": spaced_review.scheduled_date.isoformat(),
                "next_interval_days": spaced_review.next_interval_days,
                "review_number": spaced_review.review_number,
            },
            "xp_update": {
                "xp_earned": xp_result["xp_earned"],
                "total_xp": xp_result["total_xp"],
                "leveled_up": xp_result["leveled_up"],
                "message": xp_result["message"],
            },
            "risk_alert": risk_alert,
            "method_xp": method_result,
            "fomo_nudge": _fomo_nudge,  # None 或经仲裁下发的 FOMO payload
            "mechanism_evaluations": mechanism_evaluations,  # 步骤 13: 28 机制评估记录
            "minor_protection": minor_protection,  # 步骤 8b: LF-M52 合规校验结论
            "learning_method_tip": method_tip,
        }

    @classmethod
    async def _load_ability(cls, user: User, db: AsyncSession):
        """读取能力估计：先 Redis 缓存，命中返回；否则查 DB AbilityEstimate，未超 TTL 也命中。"""
        cached = await get_ability(user.id)
        if cached is not None:
            return cached
        res = await db.execute(select(AbilityEstimate).where(AbilityEstimate.user_id == user.id))
        row = res.scalar_one_or_none()
        if row is not None and row.updated_at is not None:
            age = (datetime.now(UTC) - row.updated_at).total_seconds()
            if age < ABILITY_TTL:
                await cache_ability(user.id, row.theta, row.sigma)
                return (row.theta, row.sigma)
        return None

    @classmethod
    async def _save_ability(cls, user: User, theta: float, sigma: float, db: AsyncSession) -> None:
        """upsert 能力估计：同时写 Redis 缓存与 DB AbilityEstimate"""
        await cache_ability(user.id, theta, sigma)
        res = await db.execute(select(AbilityEstimate).where(AbilityEstimate.user_id == user.id))
        row = res.scalar_one_or_none()
        if row is None:
            db.add(AbilityEstimate(user_id=user.id, theta=theta, sigma=sigma))
        else:
            row.theta = theta
            row.sigma = sigma
        await db.flush()

    @classmethod
    def _compute_fused_difficulty(cls, bkt_d: int, dda_d: int, optimal_d: int) -> int:
        """融合 BKT、DDA、85% 规则推荐难度"""
        fused = round(
            bkt_d * cls.BKT_WEIGHT + dda_d * cls.DDA_WEIGHT + optimal_d * cls.OPTIMAL_WEIGHT
        )
        return max(1, min(10, fused))

    @classmethod
    async def _build_risk_snapshot(cls, user: User, db: AsyncSession) -> UsageSnapshot:
        """基于真实数据构建风险快照"""
        from datetime import timedelta

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # 今日答题
        today_attempts = await db.execute(
            select(Attempt)
            .options(selectinload(Attempt.task))
            .where(
                Attempt.user_id == user.id,
                Attempt.created_at >= today_start,
            )
            .order_by(Attempt.created_at.desc())
        )
        today_list = list(today_attempts.scalars().all())

        # 总答题
        all_attempts_query = await db.execute(
            select(Attempt)
            .options(selectinload(Attempt.task))
            .where(Attempt.user_id == user.id)
            .order_by(Attempt.created_at.desc())
            .limit(100)
        )
        all_list = list(all_attempts_query.scalars().all())

        # 计算连续失败
        consecutive_failures = 0
        for a in all_list:
            if not a.is_correct:
                consecutive_failures += 1
            else:
                break

        # 重复技能练习统计
        skill_counts = {}
        for a in all_list:
            if a.task and a.task.topic:
                skill_counts[a.task.topic] = skill_counts.get(a.task.topic, 0) + 1

        # 跳过率：没有 skip 字段，用 recovery 模式近似：答错且未重试视为跳过
        total = len(all_list)
        skip_count = sum(1 for a in all_list if not a.is_correct)
        skip_ratio = skip_count / max(total, 1)

        # 高难度比例
        hard_count = sum(1 for a in all_list if (a.difficulty_at_time or 5) >= 7)
        hard_ratio = hard_count / max(total, 1)

        # 夜间答题分钟（按每次 3 分钟估算）
        night_minutes = sum(3 for a in today_list if a.created_at and a.created_at.hour >= 22 or (a.created_at and a.created_at.hour < 6))
        total_minutes = len(today_list) * 3

        return UsageSnapshot(
            user_id=str(user.id),
            date=now,
            total_minutes=float(total_minutes),
            standard_minutes=float(total_minutes - night_minutes),
            night_minutes=float(night_minutes),
            total_attempts=total,
            correct_attempts=sum(1 for a in all_list if a.is_correct),
            hard_task_ratio=hard_ratio,
            skip_ratio=skip_ratio,
            retry_ratio=0.0,
            repeated_skill_attempts=skill_counts,
            consecutive_failures=consecutive_failures,
        )

    @classmethod
    async def _build_bkt_state(cls, user_id: str, topic: Optional[str], db: AsyncSession) -> KnowledgeState:
        """基于历史答题记录构建 BKT 状态"""
        state = KnowledgeState(user_id=user_id)
        attempts = await db.execute(
            select(Attempt)
            .options(selectinload(Attempt.task))
            .where(Attempt.user_id == user_id)
            .order_by(Attempt.created_at.asc())
        )
        for attempt in attempts.scalars().all():
            skill_dim = attempt.task.topic if attempt.task else (topic or "general")
            bkt_engine.update(state, skill_dim, attempt.is_correct)
        return state

    @classmethod
    async def _ensure_skill_profile(
        cls, user_id: str, topic: str, db: AsyncSession
    ) -> StudentSkillProfile:
        """确保存在指定主题的技能画像"""
        result = await db.execute(
            select(StudentSkillProfile).where(
                StudentSkillProfile.user_id == user_id,
                StudentSkillProfile.skill_dim == topic,
            )
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            skill = StudentSkillProfile(
                user_id=user_id,
                skill_dim=topic,
                score=50.0,
                confidence=0.5,
                total_attempts=0,
                correct_attempts=0,
            )
            db.add(skill)
            await db.flush()
        return skill

    @classmethod
    async def _ensure_pet(cls, user: User, db: AsyncSession) -> Optional[PetProfile]:
        """确保用户拥有宠物"""
        from app.services.onboarding_service import OnboardingService
        return await OnboardingService.ensure_default_pet(user, db)

    @classmethod
    def _compare_answer(cls, user_answer: str, correct_answer: str) -> bool:
        """标准化答案后比较"""
        def normalize(ans: str) -> str:
            a = str(ans).strip().lower().replace(" ", "").replace(",", ".")
            if "/" in a:
                try:
                    parts = a.split("/")
                    if len(parts) == 2:
                        num, den = float(parts[0]), float(parts[1])
                        if den != 0:
                            a = str(round(num / den, 4))
                except (ValueError, ZeroDivisionError):
                    pass
            return a

        return normalize(user_answer) == normalize(correct_answer)

    @classmethod
    def _task_to_dict(cls, task: Task) -> dict:
        """Task -> dict（含前端 LearnPage 所需字段）"""
        return {
            "id": str(task.id),
            "content": task.content,
            "content_type": task.content_type,
            "topic": task.topic,
            "subject": task.topic,
            "difficulty": task.difficulty,
            "time_estimate": task.time_estimate,
        }
