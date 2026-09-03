"""学生端 API：仪表盘、学习任务流、宠物、DDA、反馈、复习"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.pet import PetProfile
from app.models.task import Task, Attempt, SpacedReview, StudentSkillProfile
from app.models.analytics import AbilityEstimate
from app.services.pet_service import PetService
from app.services.feedback_service import FeedbackService
from app.services.risk_monitor import RiskMonitor
from app.services.learning_orchestrator import LearningOrchestrator
from app.services import cache as cache_service

router = APIRouter(prefix="/api/v1/student", tags=["学生端"])


class TaskSubmitRequest(BaseModel):
    task_id: str
    answer: str
    time_spent: int | None = None  # 秒
    hints_used: int = 0
    is_retry: bool = False
    is_creative: bool = False


class RecoveryChoice(BaseModel):
    task_id: str
    choice: str  # "watch_tutorial" | "retry" | "skip"


class ConsentUpdate(BaseModel):
    consent_type: str  # "relaxation_guide" | "eeg_integration" | "data_research"
    granted: bool


# ─── 仪表盘 ───────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学生仪表盘数据（Redis 缓存包裹 5 条聚合查询，Spec P0 / AC3）"""
    cached = await cache_service.get_dashboard(user.id)
    if cached is not None:
        return cached

    result = await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))
    pet = result.scalar_one_or_none()

    today_attempts = await db.execute(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == user.id,
            func.date(Attempt.created_at) == func.current_date(),
        )
    )
    today_total = today_attempts.scalar() or 0

    today_correct = await db.execute(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == user.id,
            Attempt.is_correct == True,
            func.date(Attempt.created_at) == func.current_date(),
        )
    )
    _correct_count = today_correct.scalar() or 0

    due_reviews = await db.execute(
        select(func.count(SpacedReview.id)).where(
            SpacedReview.user_id == user.id,
            SpacedReview.scheduled_date <= func.now(),
            SpacedReview.completed_date.is_(None),
        )
    )
    _due_count = due_reviews.scalar() or 0

    skill_profiles = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == user.id)
    )
    profiles = skill_profiles.scalars().all()

    payload = {
        "pet": PetService.get_weekly_summary(pet) if pet else None,
        "has_pet": pet is not None,
        "today": {
            "total_attempts": today_total,
            "correct_attempts": _correct_count,
            "accuracy": round(_correct_count / max(today_total, 1) * 100, 1),
        },
        "pending_reviews": _due_count,
        "skill_profiles": [
            {
                "skill": p.skill_dim,
                "score": round(p.score, 1),
                "mastery": round(p.mastery, 3) if p.mastery else 0.0,
                "success_rate": round(p.success_rate * 100, 1),
            }
            for p in profiles
        ],
        "daily_goal": {
            "recommended_tasks": min(5, max(1, 10 - today_total)),
            "estimated_minutes": min(30, max(3, (10 - today_total) * 3)),
        },
    }
    await cache_service.cache_dashboard(user.id, payload)
    return payload


# ─── 任务流与算法编排 ─────────────────────────

@router.get("/next-task")
async def get_next_task(
    topic: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取下一道题目（融合 BKT / DDA / 85% 规则 / 风险监控 / 学习方法）"""
    try:
        result = await LearningOrchestrator.build_next_task(user, topic, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e) or "暂无匹配难度的题目")


@router.post("/submit-answer")
async def submit_answer(
    req: TaskSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交答案 → 即时反馈 + 宠物更新 + 间隔复习 + XP + 风险告警"""
    task_query = await db.execute(select(Task).where(Task.id == req.task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="题目不存在")

    result = await LearningOrchestrator.process_submission(
        user, task, req.model_dump(), db
    )
    return result


class AttemptRequest(BaseModel):
    task_id: str
    correct: bool
    rt_ms: int = 0


@router.post("/attempt")
async def attempt(
    req: AttemptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交作答（兼容前端 LearnPage 的 {task_id,correct,rt_ms} 契约）

    内部复用 LearningOrchestrator.process_submission：写奖励/风险审计、失效 dashboard+ability 缓存。
    """
    task_query = await db.execute(select(Task).where(Task.id == req.task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 前端只给正确性，不直接给答案文本：按 correct 合成答案供 process_submission 判定
    synthesized_answer = task.correct_answer if req.correct else "__incorrect__"
    result = await LearningOrchestrator.process_submission(
        user, task,
        {
            "answer": synthesized_answer,
            "time_spent": max(1, req.rt_ms // 1000) if req.rt_ms else None,
            "hints_used": 0,
            "is_retry": False,
            "is_creative": False,
        },
        db,
    )
    fb = result.get("feedback")
    feedback_text = fb.get("feedback_text") if isinstance(fb, dict) else (str(fb) if fb else "")
    return {"feedback": feedback_text, "next": None}


@router.get("/challenge")
async def get_challenge(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """当前难度通道（ChallengeBar 数据源）：由 AbilityEstimate.theta 映射到 0–100

    通道区间 low=75 / high=85 对应 85% 规则的心流带。
    """
    row = (await db.execute(
        select(AbilityEstimate).where(AbilityEstimate.user_id == user.id)
    )).scalar_one_or_none()

    if row is not None:
        # theta ∈ [800, 2200] → 掌握度 ∈ [0,1] → 0–100
        current = int(max(0, min(100, round((row.theta - 800) / 1400 * 100))))
    else:
        current = 50  # 未评估时的中性起点

    return {
        "current": current,
        "low": 75,
        "high": 85,
        "reset_recommended": False,
        "subject": None,
    }


@router.post("/recovery-choice")
async def recovery_choice(
    req: RecoveryChoice,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """答错后的恢复路径选择"""
    task_query = await db.execute(select(Task).where(Task.id == req.task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="题目不存在")

    pet_query = await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))
    pet = pet_query.scalar_one_or_none()

    if pet:
        pet_event = PetService.calculate_wrong_answer(
            difficulty=task.difficulty,
            chosen_recovery=req.choice,
        )
        PetService.apply_update(pet, pet_event)

    result = {"choice": req.choice, "pet_mood": pet.mood.value if pet else "happy"}

    if req.choice == "watch_tutorial":
        result["tutorial"] = task.explanation or "暂无讲解内容"
        result["message"] = "从错误中学习是最有效的进步方式！"
    elif req.choice == "retry":
        result["message"] = "勇于再试！这是坚持力在成长。"
        similar_query = await db.execute(
            select(Task)
            .where(
                Task.topic == task.topic,
                Task.difficulty == task.difficulty,
                Task.id != task.id,
                Task.is_approved == True,
            )
            .limit(1)
        )
        similar = similar_query.scalar_one_or_none()
        if similar:
            result["similar_task"] = {
                "id": str(similar.id),
                "content": similar.content,
                "difficulty": similar.difficulty,
            }
    elif req.choice == "skip":
        result["message"] = "已标记为待突破，周末复习时再挑战！"

    return result


@router.get("/due-reviews")
async def get_due_reviews(
    cursor: str | None = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取到期复习列表（SQL 下推 + 游标分页，Spec P0 / AC4）

    - WHERE user_id=? AND completed_date IS NULL AND scheduled_date<=now()
    - 游标分页：cursor 为上一页最后一条的 scheduled_date(ISO)，返回 next_cursor
    """
    from datetime import datetime, timezone
    from app.services.spaced_repetition import SpacedRepetitionService

    limit = max(1, min(limit, 100))

    query = (
        select(SpacedReview)
        .where(
            SpacedReview.user_id == user.id,
            SpacedReview.completed_date.is_(None),
            SpacedReview.scheduled_date <= func.now(),
        )
        .order_by(SpacedReview.scheduled_date.asc(), SpacedReview.id.asc())
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            if cursor_dt.tzinfo is None:
                cursor_dt = cursor_dt.replace(tzinfo=timezone.utc)
            query = query.where(SpacedReview.scheduled_date > cursor_dt)
        except ValueError:
            pass

    query = query.limit(limit + 1)  # 多取一条判断是否有下一页
    reviews = (await db.execute(query)).scalars().all()

    has_next = len(reviews) > limit
    page = reviews[:limit]

    due = SpacedRepetitionService.get_due_reviews(list(page))

    next_cursor = None
    if has_next and page:
        last = page[-1]
        next_cursor = last.scheduled_date.isoformat() if last.scheduled_date else None

    return {
        "due_reviews": [
            {
                "id": str(r.id),
                "task_id": str(r.task_id),
                "review_number": r.review_number,
                "scheduled_date": r.scheduled_date.isoformat(),
                "next_interval_days": r.next_interval_days,
            }
            for r in due
        ],
        "total_due": len(due),
        "next_cursor": next_cursor,
        "limit": limit,
    }


# ─── 宠物 ──────────────────────────────────────

@router.get("/pet")
async def get_pet(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取宠物详情"""
    result = await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))
    pet = result.scalar_one_or_none()

    if not pet:
        return {"has_pet": False, "message": "还没有宠物，去创建一只吧！"}

    return {
        "has_pet": True,
        "pet": {
            "id": str(pet.id),
            "name": pet.name,
            "breed": pet.breed.value,
            "level": pet.level,
            "mood": pet.mood.value,
            "dimensions": {
                "understanding": round(pet.understanding, 1),
                "persistence": round(pet.persistence, 1),
                "creativity": round(pet.creativity, 1),
                "collaboration": round(pet.collaboration, 1),
            },
            "total_score": round(pet.total_score, 1),
            "dominant_trait": pet.dominant_trait,
            "level_progress": round(pet.get_level_progress(), 1),
            "visuals_state": pet.visuals_state,
        },
    }


# ─── 放松引导 ─────────────────────────────────

@router.get("/relaxation-guide")
async def get_relaxation_guide(
    user: User = Depends(get_current_user),
):
    """获取放松引导文案（需已同意）"""
    if not user.consents or not user.consents.get("relaxation_guide"):
        raise HTTPException(status_code=403, detail="未同意放松引导功能。请在设置中开启。")

    return {
        "guide_text": FeedbackService.generate_relaxation_guide(),
        "duration_seconds": 30,
        "can_skip": True,
        "disclaimer": "这是放松与专注引导，由系统提供。您可随时在设置中关闭此功能。",
    }


# ─── 同意管理 ─────────────────────────────────

@router.post("/consent")
async def update_consent(
    req: ConsentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新功能同意状态"""
    if not user.consents:
        user.consents = {}
    user.consents[req.consent_type] = req.granted
    await db.flush()

    return {
        "consent_type": req.consent_type,
        "granted": req.granted,
        "message": "同意状态已更新",
    }


# ─── 健康检查 ─────────────────────────────────

@router.get("/health-check")
async def health_check(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学习健康状态检查（基于 RiskMonitor）"""
    from app.services.learning_orchestrator import LearningOrchestrator

    snapshot = await LearningOrchestrator._build_risk_snapshot(user, db)
    assessment = RiskMonitor.assess([snapshot])
    consecutive = RiskMonitor.check_consecutive_usage(snapshot.total_minutes)

    return {
        "should_rest": assessment.should_force_rest or consecutive.get("should_force_rest", False),
        "risk_level": assessment.zone.value,
        "message": (
            "目前状态良好，继续加油！" if assessment.level.value == 0
            else "; ".join(assessment.alerts) or "请注意学习节奏"
        ),
        "consecutive_minutes": int(snapshot.total_minutes),
        "alerts": assessment.alerts,
    }
