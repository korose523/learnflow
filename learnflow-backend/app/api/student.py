"""学生端 API：仪表盘、学习任务流、宠物、DDA、反馈、复习"""
import logging
import json
from typing import Literal
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.pet import PetProfile
from app.models.task import Task, Attempt, SpacedReview, StudentSkillProfile
from app.models.analytics import AbilityEstimate
from app.services.pet_service import PetService
from app.services.feedback_service import FeedbackService
from app.services.risk_monitor import RiskMonitor
from app.services.learning_orchestrator import LearningOrchestrator
from app.services import cache as cache_service
from app.services.anti_addiction import session_reset_decision, infer_age_band

logger = logging.getLogger(__name__)

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
    choice: Literal["watch_tutorial", "retry", "skip"]


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
        select(func.count(SpacedReview.id)).join(Task, Task.id == SpacedReview.task_id).where(
            Task.is_approved == True,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("next-task 生成失败 (user=%s, topic=%r)", user.id, topic, exc_info=True)
        raise HTTPException(status_code=500, detail="题目服务暂时不可用，请稍后重试") from e


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
    if not task.is_approved:
        raise HTTPException(status_code=409, detail="题目尚未通过审核，暂不可作答")

    result = await LearningOrchestrator.process_submission(
        user, task, req.model_dump(), db
    )
    return result


class AttemptRequest(BaseModel):
    task_id: str
    answer: str
    rt_ms: int = 0


@router.post("/attempt")
async def attempt(
    req: AttemptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兼容作答接口：接收答案，正确性只由服务器判定。"""
    task_query = await db.execute(select(Task).where(Task.id == req.task_id))
    task = task_query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="题目不存在")
    if not task.is_approved:
        raise HTTPException(status_code=409, detail="题目尚未通过审核，暂不可作答")
    return await LearningOrchestrator.process_submission(
        user, task,
        {"answer": req.answer, "time_spent": max(1, req.rt_ms // 1000),
         "hints_used": 0, "is_retry": False, "is_creative": False}, db,
    )


@router.get("/challenge")
async def get_challenge(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """当前难度通道（ChallengeBar 数据源）：由 AbilityEstimate.theta 映射到 0–100

    通道区间 low=75 / high=85 为 85% 规则的心流带【设计带宽】，非实测数据。
    """
    row = (await db.execute(
        select(AbilityEstimate).where(AbilityEstimate.user_id == user.id)
    )).scalar_one_or_none()

    if row is not None:
        # theta ∈ [800, 2200] → 掌握度 ∈ [0,1] → 0–100
        current = int(max(0, min(100, round((row.theta - 800) / 1400 * 100))))
    else:
        current = 50  # 未评估时的中性起点

    # subject：取用户最近一次作答关联 Task.topic；无任何作答历史则为 None
    recent_attempt = (await db.execute(
        select(Attempt)
        .options(selectinload(Attempt.task))
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )).scalars().first()
    subject = recent_attempt.task.topic if (recent_attempt and recent_attempt.task) else None

    # reset_recommended：复用反成瘾服务的权威判定（连续学习 ≥25 分钟触发难度重置）。
    # 本会话时长以「当日作答数 × 3 分钟/题」估算（与周报一致的保守启发，非真实会话时钟）；
    # 当日无作答时 session_minutes=0，不误报重置（保守默认值）。
    today_count = (await db.execute(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == user.id,
            func.date(Attempt.created_at) == func.current_date(),
        )
    )).scalar() or 0
    session_minutes = today_count * 3
    age_band = infer_age_band(user)
    reset_decision = session_reset_decision(session_minutes, age_band)
    reset_recommended = reset_decision["should_reset_difficulty"]

    # low/high 为 85% 心流带设计带宽（非实测数据），保持不变
    return {
        "current": current,
        "low": 75,
        "high": 85,
        "reset_recommended": reset_recommended,
        "subject": subject,
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

    if not task.is_approved:
        raise HTTPException(status_code=409, detail="题目尚未通过审核，暂不可使用恢复流程")
    latest = (await db.execute(
        select(Attempt).where(Attempt.user_id == user.id, Attempt.task_id == task.id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(1)
    )).scalar_one_or_none()
    if latest is None or latest.is_correct:
        raise HTTPException(status_code=409, detail="请先完成本题作答；恢复流程仅用于最近一次答错的题目")

    # Submission owns pet updates. Opening/retrying recovery must not award points.
    pet = (await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))).scalar_one_or_none()

    result = {"choice": req.choice, "pet_mood": pet.mood.value if pet else "happy"}

    if req.choice == "watch_tutorial":
        result["tutorial"] = task.explanation or "暂无讲解内容"
        result["message"] = "可以先阅读讲解，再尝试作答。"
    elif req.choice == "retry":
        result["message"] = "可以再试一次，检查刚才的解题步骤。"
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
        result["message"] = "可以继续下一题，之后再回来练习。"

    return result


@router.get("/due-reviews")
async def get_due_reviews(cursor: str | None = None, limit: int = 20, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Approved, owned due reviews with a time-and-ID cursor."""
    limit = max(1, min(limit, 100))
    conditions = [SpacedReview.user_id == user.id, SpacedReview.completed_date.is_(None), SpacedReview.scheduled_date <= datetime.now(UTC), Task.is_approved == True]
    total = (await db.execute(select(func.count(SpacedReview.id)).join(Task, Task.id == SpacedReview.task_id).where(*conditions))).scalar_one()
    query = select(SpacedReview, Task).join(Task, Task.id == SpacedReview.task_id).where(*conditions)
    if cursor:
        try:
            stamp, row_id = json.loads(cursor)
            cursor_dt = datetime.fromisoformat(stamp)
            if not isinstance(row_id, str) or not row_id: raise ValueError('Invalid ID')
        except (ValueError, TypeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="复习分页标记无效")
        query = query.where(or_(SpacedReview.scheduled_date > cursor_dt, and_(SpacedReview.scheduled_date == cursor_dt, SpacedReview.id > row_id)))
    rows = (await db.execute(query.order_by(SpacedReview.scheduled_date, SpacedReview.id).limit(limit + 1))).all()
    page = rows[:limit]
    next_cursor = json.dumps([page[-1][0].scheduled_date.isoformat(), page[-1][0].id]) if len(rows) > limit and page else None
    return {"due_reviews": [{"id":r.id,"task_id":t.id,"content":t.content,"topic":t.topic,"difficulty":t.difficulty,"review_number":r.review_number,"scheduled_date":r.scheduled_date.isoformat(),"next_interval_days":r.next_interval_days} for r,t in page], "total_due":total,"page_count":len(page),"next_cursor":next_cursor,"limit":limit}


class ReviewAnswerRequest(BaseModel):
    answer: str = Field(min_length=1)
    time_spent: int = Field(default=1, ge=1)

    @field_validator('answer')
    @classmethod
    def nonblank_answer(cls, value: str) -> str:
        if not value.strip(): raise ValueError('答案不能为空')
        return value.strip()


@router.post("/reviews/{review_id}/answer")
async def answer_review(review_id: str, req: ReviewAnswerRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="仅学生可提交复习")
    row = (await db.execute(select(SpacedReview).where(SpacedReview.id == review_id, SpacedReview.user_id == user.id))).scalar_one_or_none()
    if row is None: raise HTTPException(status_code=404, detail="复习记录不存在")
    now = datetime.now(UTC)
    scheduled = row.scheduled_date.replace(tzinfo=UTC) if row.scheduled_date.tzinfo is None else row.scheduled_date
    if row.completed_date is not None or scheduled > now:
        raise HTTPException(status_code=409, detail="该复习已完成或尚未到期")
    task = await db.get(Task, row.task_id)
    if task is None or not task.is_approved: raise HTTPException(status_code=409, detail="题目当前不可用于复习")
    claimed = await db.execute(update(SpacedReview).where(SpacedReview.id == row.id, SpacedReview.user_id == user.id, SpacedReview.completed_date.is_(None), SpacedReview.scheduled_date <= now).values(completed_date=now).execution_options(synchronize_session=False))
    if claimed.rowcount != 1: raise HTTPException(status_code=409, detail="该复习已被提交")
    row.completed_date = now
    result = await LearningOrchestrator.process_submission(user, task, {"answer":req.answer,"time_spent":req.time_spent}, db)
    row.result = result['is_correct']
    await db.flush()
    result['review_id'] = row.id
    result['review_explanation'] = task.explanation
    return result


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
