"""学生端游戏化 API：连胜、XP、排行榜、战队、技能树、宝箱、记忆宫殿、LAI仪表盘、A/B测试"""
from datetime import datetime, UTC, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.pet import PetProfile
from app.models.task import Attempt, StudentSkillProfile
from app.services.gamification_service import GamificationService
from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState, XPEngine, XPState, XPEventType
from app.services.team_competition_engine import TeamManagementEngine, TeamLeagueEngine, SoloRankEngine, SubjectRank, RankTier, RankDivision
from app.services.meta_learning_skilltree import SkillTreeEngine, MethodQuestEngine
from app.services.learning_methods_engine import LearningMethodEngine
from app.services.memory_science_engine import (
    MemoryConsolidationEngine,
    MemoryScienceOrchestrator,
    MnemonicEngine,
    ConcreteExamplesEngine,
    DesirableDifficultiesOrchestrator,
)
from app.services.habit_addiction_engine import HabitAddictionOrchestrator
from app.services.learning_addiction_index import (
    LearningAddictionIndex, lai_engine, LAIAssessment,
)
from app.services.ab_test_framework import ab_test_framework, ExperimentPhase

router = APIRouter(prefix="/api/v1/student/gamification", tags=["游戏化"])


class CreateTeamRequest(BaseModel):
    name: str
    tag: str
    description: str | None = None


class JoinTeamRequest(BaseModel):
    team_id: str


class UpdatePetRequest(BaseModel):
    name: str | None = None
    visuals_state: dict | None = None


class CompleteQuestRequest(BaseModel):
    quest_id: str


# ─── 连胜 ─────────────────────────────────────

@router.get("/streak")
async def get_streak(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前连胜状态（根据历史答题记录计算）"""
    from app.services.duolingo_addiction_engine import DuolingoStreakState
    from datetime import datetime, UTC, timedelta

    state = DuolingoStreakState()

    try:
        attempts = await db.execute(
            select(Attempt.created_at).where(Attempt.user_id == user.id)
        )
        # fetchall -> list[tuple], 每项第0位为 created_at
        rows = attempts.fetchall()
        dates = [r[0].date() for r in rows if r[0]]
    except Exception:
        return {
            "current_streak": state.current_streak,
            "best_streak": state.current_streak,
            "streak_freezes_available": state.streak_freezes_available,
            "streak_society": state.streak_society_member,
            "message": "目前暂无学习记录",
            "fire_level": 1,
            "fire_icons": "🔥",
        }

    if not dates:
        return {
            "current_streak": 0,
            "best_streak": 0,
            "streak_freezes_available": state.streak_freezes_available,
            "streak_society": state.streak_society_member,
            "message": "目前暂无学习记录",
            "fire_level": 0,
            "fire_icons": "",
        }

    unique_dates = sorted(set(dates))

    today = datetime.now(UTC).date()
    cur = 0
    check = today
    date_set = set(unique_dates)
    while check in date_set:
        cur += 1
        check = check - timedelta(days=1)

    # 计算历史最长连胜
    best = 0
    streak = 0
    prev = None
    for d in unique_dates:
        if prev is None:
            streak = 1
        else:
            if (d - prev).days == 1:
                streak += 1
            else:
                streak = 1
        best = max(best, streak)
        prev = d

    fire_level = min(max(1, cur // 10 + 1), 10) if cur > 0 else 0
    fire_icons = "🔥" * min(fire_level, 5)

    return {
        "current_streak": cur,
        "best_streak": best,
        "streak_freezes_available": state.streak_freezes_available,
        "streak_society": state.streak_society_member,
        "message": f"连续学习 {cur} 天",
        "fire_level": fire_level,
        "fire_icons": fire_icons,
    }


@router.get("/xp")
async def get_xp(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 XP 与联赛状态"""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    result = await db.execute(
        select(Attempt)
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.asc())
        .options(selectinload(Attempt.task))
    )
    attempts = result.scalars().all()

    # 处理数据库中可能存在的带/不带时区的 datetime，统一比较为 UTC aware
    def _to_utc_aware(dt):
        if dt is None:
            return None
        try:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            return dt

    today_start_utc = today_start.replace(tzinfo=UTC)
    week_ago_utc = week_ago if (week_ago.tzinfo is not None) else week_ago.replace(tzinfo=UTC)

    total_state = XPEngine.build_state_from_attempts(attempts)
    today_state = XPEngine.build_state_from_attempts(
        [a for a in attempts if a.created_at and _to_utc_aware(a.created_at) >= today_start_utc]
    )
    weekly_state = XPEngine.build_state_from_attempts(
        [a for a in attempts if a.created_at and _to_utc_aware(a.created_at) >= week_ago_utc]
    )

    return {
        "level": total_state.xp_level,
        "total_xp": total_state.total_xp,
        "today_xp": today_state.total_xp,
        "weekly_xp": weekly_state.weekly_xp,
        "xp_to_next": max(0, total_state.xp_to_next_level - total_state.total_xp),
        "progress_pct": round(total_state.total_xp / max(total_state.xp_to_next_level, 1) * 100, 1),
        "boosts_available": total_state.boosts_available,
        "boost_active": total_state.boost_remaining_minutes > 0,
        "league": (
            "gold" if weekly_state.weekly_xp >= 200 else
            "silver" if weekly_state.weekly_xp >= 100 else
            "bronze"
        ),
        "message": (
            "本周表现优异，继续保持！" if weekly_state.weekly_xp >= 100 else
            "坚持完成任务，XP 会逐步提升。"
        ),
    }


@router.get("/leaderboard")
async def get_leaderboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取排行榜（班级/全站）"""
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)

    students_q = await db.execute(
        select(User.id, User.name).where(User.role == UserRole.STUDENT, User.is_active == True)
    )
    students = students_q.all()
    if not students:
        return {
            "league": "bronze",
            "user_rank": 0,
            "total_in_league": 0,
            "top3": [],
            "nearby": [],
            "xp_to_next_rank": 0,
            "message": "暂无排行榜数据",
        }

    student_ids = [s[0] for s in students]
    attempts_q = await db.execute(
        select(Attempt)
        .where(Attempt.user_id.in_(student_ids), Attempt.created_at >= week_ago)
        .order_by(Attempt.user_id.asc(), Attempt.created_at.asc())
        .options(selectinload(Attempt.task))
    )
    recent_attempts = attempts_q.scalars().all()

    attempts_by_user: dict[str, list] = defaultdict(list)
    for attempt in recent_attempts:
        attempts_by_user[attempt.user_id].append(attempt)

    leaderboard = []
    for student_id, student_name in students:
        state = XPEngine.build_state_from_attempts(attempts_by_user.get(student_id, []))
        leaderboard.append({
            "user_id": student_id,
            "name": student_name,
            "weekly_xp": state.weekly_xp,
            "level": state.xp_level,
            "progress_pct": round(state.total_xp / max(state.xp_to_next_level, 1) * 100, 1),
        })

    leaderboard.sort(key=lambda item: item["weekly_xp"], reverse=True)

    user_entry = next((item for item in leaderboard if item["user_id"] == user.id), None)
    if not user_entry:
        user_entry = {"user_id": user.id, "name": user.name, "weekly_xp": 0, "level": 1, "progress_pct": 0.0}
        leaderboard.append(user_entry)
        leaderboard.sort(key=lambda item: item["weekly_xp"], reverse=True)

    user_rank = next((i + 1 for i, item in enumerate(leaderboard) if item["user_id"] == user.id), len(leaderboard))
    xp_to_next_rank = 0
    if user_rank > 1:
        prev_xp = leaderboard[user_rank - 2]["weekly_xp"]
        xp_to_next_rank = max(prev_xp - user_entry["weekly_xp"], 0)

    top3 = [
        {"name": item["name"], "xp": item["weekly_xp"]}
        for item in leaderboard[:3]
    ]

    nearby_start = max(0, user_rank - 2)
    nearby_end = min(len(leaderboard), user_rank + 1)
    nearby = [
        {"name": item["name"], "xp": item["weekly_xp"], "is_you": item["user_id"] == user.id}
        for item in leaderboard[nearby_start:nearby_end]
    ]

    league = (
        "gold" if user_entry["weekly_xp"] >= 200 else
        "silver" if user_entry["weekly_xp"] >= 100 else
        "bronze"
    )

    return {
        "league": league,
        "user_rank": user_rank,
        "total_in_league": len(leaderboard),
        "top3": top3,
        "nearby": nearby,
        "xp_to_next_rank": xp_to_next_rank,
        "message": (
            "🏆 你目前排名第一！" if user_rank == 1 else
            f"继续努力，超越上一名还差 {xp_to_next_rank} XP"
        ),
    }


# ─── 战队 ─────────────────────────────────────

@router.get("/team")
async def get_team(
    user: User = Depends(get_current_user),
):
    """获取当前战队信息"""
    team_id = TeamManagementEngine.PLAYER_TEAMS.get(str(user.id))
    if not team_id:
        return {
            "has_team": False,
            "message": "你还没有加入战队",
            "public_teams": TeamManagementEngine.list_teams(1, 10),
        }
    team = TeamManagementEngine.TEAMS.get(team_id)
    return {
        "has_team": True,
        "team": TeamManagementEngine.get_team_info(team) if team else None,
    }


@router.post("/team")
async def create_team(
    req: CreateTeamRequest,
    user: User = Depends(get_current_user),
):
    """创建战队"""
    try:
        team = TeamManagementEngine.create_team(req.name, req.tag, str(user.id), user.name)
        return {
            "success": True,
            "team": TeamManagementEngine.get_team_info(team),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/team/join")
async def join_team(
    req: JoinTeamRequest,
    user: User = Depends(get_current_user),
):
    """加入战队"""
    result = TeamManagementEngine.join_team(req.team_id, str(user.id), user.name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/team/leave")
async def leave_team(
    user: User = Depends(get_current_user),
):
    """离开战队"""
    result = TeamManagementEngine.leave_team(str(user.id))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/team/leaderboard")
async def team_leaderboard(
    user: User = Depends(get_current_user),
):
    """战队排行榜"""
    team_id = TeamManagementEngine.PLAYER_TEAMS.get(str(user.id))
    team = TeamManagementEngine.TEAMS.get(team_id) if team_id else None
    global_board = TeamLeagueEngine.get_global_leaderboard()

    return {
        "your_team": TeamManagementEngine.get_team_info(team) if team else None,
        "is_in_team": bool(team),
        "global_leaderboard": global_board["rankings"],
        "message": (
            "你所在战队当前的排名已更新" if team else "你还未加入战队，先创建或加入一个战队吧！"
        ),
    }


# ─── 技能树 ───────────────────────────────────

@router.get("/skill-tree")
async def get_skill_tree(
    user: User = Depends(get_current_user),
):
    """获取学习技能树"""
    return SkillTreeEngine.get_skill_tree(str(user.id))


@router.get("/daily-quests")
async def get_daily_quests(
    user: User = Depends(get_current_user),
):
    """获取今日学习方法任务"""
    return {
        "quests": MethodQuestEngine.generate_daily_quests(str(user.id)),
    }


@router.post("/complete-quest")
async def complete_quest(
    req: CompleteQuestRequest,
    user: User = Depends(get_current_user),
):
    """完成学习方法任务"""
    return MethodQuestEngine.complete_quest(str(user.id), req.quest_id)


# ─── 宝箱与记忆宫殿 ───────────────────────────

@router.post("/open-box")
async def open_box(
    user: User = Depends(get_current_user),
):
    """开宝箱"""
    reward = GamificationService.open_box_for_user(
        str(user.id), pet_name=user.name or "小豆", current_topic="数学"
    )
    box_status = GamificationService.get_box_status_for_user(str(user.id))
    return {
        "reward": reward,
        "box_status": box_status,
    }


@router.get("/memory-palace")
async def memory_palace(
    topic: str | None = None,
    user: User = Depends(get_current_user),
):
    """记忆宫殿提示"""
    tip = LearningMethodEngine.get_post_question_tip(
        current_topic=topic or "学习",
        is_correct=True,
        method_used="memory_palace",
    )
    return {
        "topic": topic or "学习",
        "tip": tip,
        "message": "把这道题的解法放进你熟悉的空间里，比如卧室书桌。",
    }


# ─── 宠物装扮 ───────────────────────────────────

@router.post("/pet")
async def update_pet(
    req: UpdatePetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新宠物名称/装扮"""
    result = await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))
    pet = result.scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="宠物不存在")

    if req.name:
        pet.name = req.name
    if req.visuals_state is not None:
        pet.visuals_state = {**(pet.visuals_state or {}), **req.visuals_state}

    await db.flush()
    return {
        "message": "宠物已更新",
        "pet": {
            "id": str(pet.id),
            "name": pet.name,
            "breed": pet.breed.value,
            "level": pet.level,
            "mood": pet.mood.value,
            "visuals_state": pet.visuals_state,
        },
    }


# ─── 记忆科学新引擎 ───────────────────────────

@router.get("/memory-science/review-plan")
async def memory_science_review_plan(
    user: User = Depends(get_current_user),
):
    """基于 FSRS 的知识点复习计划"""
    # 演示数据：实际应从数据库读取用户各知识点的记忆状态
    from datetime import datetime, timedelta, UTC
    now = datetime.now(UTC)
    item_states = [
        {"id": "1", "concept": "分数加减", "difficulty": 5.0, "stability": 1.0, "review_count": 0, "last_review": now - timedelta(days=2)},
        {"id": "2", "concept": "一元一次方程", "difficulty": 4.0, "stability": 10.0, "review_count": 2, "last_review": now - timedelta(days=1)},
    ]
    return MemoryScienceOrchestrator.get_review_plan(item_states)


@router.get("/memory-science/aid")
async def memory_science_aid(
    concept: str = "光合作用",
    domain: str = "science",
    user: User = Depends(get_current_user),
):
    """为单个知识点生成记忆辅助（具体例子+记忆术+巩固建议）"""
    return MemoryScienceOrchestrator.generate_memory_aid(concept, domain)


@router.get("/memory-science/consolidation")
async def memory_science_consolidation(
    user: User = Depends(get_current_user),
):
    """记忆巩固建议：睡眠与运动"""
    return {
        "sleep": MemoryConsolidationEngine.get_sleep_recommendation(),
        "exercise": MemoryConsolidationEngine.get_exercise_recommendation(),
        "plan": MemoryConsolidationEngine.consolidation_plan(["最近学的知识点1", "最近学的知识点2"]),
    }


@router.get("/memory-science/mnemonic")
async def memory_science_mnemonic(
    method: str = "acronym",
    items: str = "分数,方程,函数",
    user: User = Depends(get_current_user),
):
    """记忆术工具：acronym / peg"""
    item_list = [i.strip() for i in items.split(",") if i.strip()]
    if method == "peg":
        return MnemonicEngine.peg_system(item_list)
    return MnemonicEngine.acronym(item_list)


@router.get("/memory-science/example")
async def memory_science_example(
    concept: str = "函数",
    domain: str = "math",
    user: User = Depends(get_current_user),
):
    """为抽象概念生成具体例子"""
    return ConcreteExamplesEngine.generate_example(concept, domain)


@router.get("/memory-science/recommend")
async def memory_science_recommend(
    mastery: float = 0.5,
    days_since_review: float = 1.0,
    streak: int = 0,
    error_rate: float = 0.2,
    user: User = Depends(get_current_user),
):
    """根据掌握度和遗忘曲线推荐学习方法"""
    return DesirableDifficultiesOrchestrator.recommend_methods(
        mastery, days_since_review, streak, error_rate
    )


# ─── 习惯化/成瘾新引擎 ───────────────────────────

@router.get("/habit-formation/plan")
async def habit_formation_plan(
    user: User = Depends(get_current_user),
):
    """生成个人习惯培养方案（习惯叠加、诱惑捆绑、执行意图等）"""
    return HabitAddictionOrchestrator.build_personal_habit_plan({
        "topic_options": ["数学", "英语", "科学"],
    })


# ─── LAI 学习成瘾化指数仪表盘（论文第十章优化清单第6项）───

class LAIAssessmentRequest(BaseModel):
    daily_minutes: float = 0.0
    session_minutes: float = 0.0
    night_ratio: float = 0.0
    content_attention_ratio: float = 1.0
    leaderboard_views: int = 0
    planned_stop_failures: int = 0
    intrinsic_motivation_ratio: float = 0.7
    external_reward_dependency: float = 0.3
    time_perception_bias: float = 0.0
    sleep_impact: float = 0.0
    social_impact: float = 0.0
    age_group: str = "secondary"


@router.post("/lai/assess")
async def assess_lai(
    req: LAIAssessmentRequest,
    user: User = Depends(get_current_user),
):
    """计算学习成瘾化指数（LAI）综合评估

    基于论文第十一章11.1节五维度测量框架：
    时间投入(30%) + 动机结构(25%) + 行为控制(25%) + 认知(10%) + 功能影响(10%)
    返回0-100分（越高越健康）和风险等级L1-L4。
    """
    assessment = lai_engine.assess(
        daily_minutes=req.daily_minutes,
        session_minutes=req.session_minutes,
        night_ratio=req.night_ratio,
        content_attention_ratio=req.content_attention_ratio,
        leaderboard_views=req.leaderboard_views,
        planned_stop_failures=req.planned_stop_failures,
        intrinsic_motivation_ratio=req.intrinsic_motivation_ratio,
        external_reward_dependency=req.external_reward_dependency,
        time_perception_bias=req.time_perception_bias,
        sleep_impact=req.sleep_impact,
        social_impact=req.social_impact,
        age_group=req.age_group,
    )
    return assessment.to_dict()


@router.get("/lai/dashboard")
async def lai_dashboard(
    user: User = Depends(get_current_user),
):
    """LAI 仪表盘 - 获取当前用户的学习成瘾化指数概览

    当LAI风险等级≥L2时，系统自动：
    1. 降低游戏化强度（变比率奖励频率↓）
    2. 增强自主性支持引擎（选择透明度↑）
    3. L3+级别通知家长
    """
    # 从数据库获取最近7天的行为数据（简化版：使用默认值）
    # 实际实现应从 Attempt 表和日志中聚合
    assessment = lai_engine.assess(
        daily_minutes=45,  # 默认值，实际从日志聚合
        session_minutes=25,
        night_ratio=0.05,
        age_group="secondary",
    )
    result = assessment.to_dict()
    result["gamification_adjustments"] = {
        "variable_ratio_probability": 0.15 if assessment.should_reduce_gamification else 0.25,
        "leaderboard_visible": not assessment.should_reduce_gamification,
        "autonomy_support_boosted": assessment.autonomy_support_boost,
        "forced_break_minutes": 10 if assessment.should_force_break else 0,
    }
    return result


# ─── A/B 测试框架（论文第九章9.5节）──────────────────

class CreateExperimentRequest(BaseModel):
    name: str
    description: str
    parameter_name: str
    control_value: str
    treatment_value: str


@router.post("/ab-test/create")
async def create_ab_experiment(
    req: CreateExperimentRequest,
    user: User = Depends(get_current_user),
):
    """创建 A/B 测试实验（初始为影子模式）

    遵循最小可干预单元原则：每次实验只改变一个参数。
    """
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(403, "仅教师和管理员可创建实验")
    exp = ab_test_framework.create_experiment(
        name=req.name,
        description=req.description,
        parameter_name=req.parameter_name,
        control_value=req.control_value,
        treatment_value=req.treatment_value,
    )
    return exp.to_dict()


@router.get("/ab-test/list")
async def list_ab_experiments(
    user: User = Depends(get_current_user),
):
    """列出所有 A/B 测试实验"""
    return ab_test_framework.list_experiments()


@router.get("/ab-test/{experiment_id}/summary")
async def ab_experiment_summary(
    experiment_id: str,
    user: User = Depends(get_current_user),
):
    """获取实验摘要统计（含健康一票否决判定）"""
    summary = ab_test_framework.get_experiment_summary(experiment_id)
    if not summary:
        raise HTTPException(404, "实验不存在")
    return summary


@router.post("/ab-test/{experiment_id}/advance")
async def advance_ab_experiment(
    experiment_id: str,
    force: bool = False,
    user: User = Depends(get_current_user),
):
    """推进实验阶段：影子模式 → 小流量 → 放量 → 全量

    需教师/管理员权限。全量上线前需经伦理委员会审查。
    """
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(403, "仅教师和管理员可推进实验阶段")
    new_phase = ab_test_framework.advance_phase(experiment_id, force=force)
    return {"experiment_id": experiment_id, "new_phase": new_phase.value}


@router.get("/ab-test/{experiment_id}/parameter")
async def get_ab_parameter(
    experiment_id: str,
    default_value: str = "",
    user: User = Depends(get_current_user),
):
    """获取当前用户在指定实验中应使用的参数值

    影子模式：所有用户使用默认值
    小流量/全量：实验组用户使用treatment_value
    """
    return {
        "parameter_value": ab_test_framework.get_parameter_value(experiment_id, user.id, default_value),
        "experiment_id": experiment_id,
    }


# ─── 算法透明度 API（论文第十章优化清单第7项）──────────

@router.get("/transparency/explain")
async def explain_algorithm(
    algorithm: str = "difficulty",
    user: User = Depends(get_current_user),
):
    """算法透明度接口 - 向用户解释算法决策逻辑

    支持的算法：
    - difficulty: 自适应难度推荐依据
    - reward: 奖励触发条件
    - risk: 风险评分计算方法
    - lai: 学习成瘾化指数构成
    """
    explanations = {
        "difficulty": {
            "algorithm": "Thompson Sampling (多臂老虎机)",
            "description": "系统将不同难度级别的题目视为不同的'臂'，每次推荐选择预期'学习收益'最大的题目。",
            "key_parameters": {
                "zpd_window": "60%-75% 正确率（最近发展区）",
                "beta_distribution": "Beta(α, β) 参数随答题结果更新",
                "fatigue_detection": "反应时间延长+错误率上升时自动降难",
            },
            "user_controls": "您可在设置中调整'挑战偏好'（保守/标准/激进）",
        },
        "reward": {
            "algorithm": "变比率强化 (Variable Ratio Reinforcement)",
            "description": "每次答题后有15%-25%概率触发额外奖励，奖励与知识掌握关联。",
            "key_parameters": {
                "trigger_probability": "15%-25%（根据LAI动态调整）",
                "reward_types": "基础积分(70%) + 彩蛋积分(30%)",
                "cooldown": "连续触发后进入冷却期，防止多巴胺耐受",
            },
            "user_controls": "您可在设置中关闭'惊喜奖励'功能",
        },
        "risk": {
            "algorithm": "RRMS 四层风险模型",
            "description": "系统从时间、认知、行为、社交四维度评估成瘾风险。",
            "key_parameters": {
                "thresholds": "动态阈值，根据年龄和学科压力周期调整",
                "update_frequency": "每24小时更新一次",
                "human_review": "L3+级别需人工审核确认",
            },
            "user_controls": "您可对风险评级提出申诉",
        },
        "lai": {
            "algorithm": "学习成瘾化指数 (LAI)",
            "description": "LAI从五维度评估学习健康度：时间(30%)+动机(25%)+控制(25%)+认知(10%)+功能(10%)。",
            "key_parameters": {
                "score_range": "0-100（越高越健康）",
                "risk_tiers": "L1正常(80-100) / L2关注(50-79) / L3深度(20-49) / L4病理(0-19)",
                "adaptive_adjustment": "LAI降低时自动降低游戏化强度、增强自主性支持",
            },
            "user_controls": "您可在仪表盘查看各维度得分和改进建议",
        },
    }
    return explanations.get(algorithm, {"error": f"未知算法: {algorithm}"})
