"""管理端 API：内容审核、文案管理、风险告警配置"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.task import Task, Attempt
from app.models.consent import FeedbackScript, Alert

router = APIRouter(prefix="/api/v1/admin", tags=["管理端"])


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return user


class ReviewTaskRequest(BaseModel):
    task_id: str
    approved: bool
    review_notes: str | None = None


class FeedbackScriptRequest(BaseModel):
    category: str
    sub_category: str | None = None
    text: str
    author: str = "system"
    ab_test_group: str | None = None


class AlertRuleRequest(BaseModel):
    rule_name: str
    trigger_condition: str
    action: str
    severity: str = "yellow"
    description: str | None = None


# ─── 内容审核 ─────────────────────────────────

@router.get("/pending-tasks")
async def get_pending_tasks(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
):
    """获取待审核的题目"""
    result = await db.execute(
        select(Task)
        .where(Task.is_approved == False)
        .order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tasks = result.scalars().all()

    total = await db.execute(
        select(func.count(Task.id)).where(Task.is_approved == False)
    )

    return {
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "topic": t.topic,
                "difficulty": t.difficulty,
                "content": t.content[:200] + "..." if len(t.content) > 200 else t.content,
                "source": t.source,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
        "total": total.scalar(),
        "page": page,
        "page_size": page_size,
    }


@router.post("/review-task")
async def review_task(
    req: ReviewTaskRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """审核题目（批准/拒绝）"""
    result = await db.execute(select(Task).where(Task.id == req.task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="题目不存在")

    task.is_approved = req.approved
    await db.flush()

    return {
        "task_id": str(task.id),
        "approved": req.approved,
        "message": "题目已审核通过" if req.approved else "题目已被拒绝",
    }


# ─── 文案管理 ─────────────────────────────────

@router.get("/feedback-scripts")
async def list_feedback_scripts(
    category: str | None = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """列出所有微反馈文案"""
    query = select(FeedbackScript)
    if category:
        query = query.where(FeedbackScript.category == category)
    query = query.order_by(FeedbackScript.category, FeedbackScript.created_at.desc())

    result = await db.execute(query)
    scripts = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "category": s.category,
            "sub_category": s.sub_category,
            "text": s.text,
            "author": s.author,
            "reviewer": s.reviewer,
            "review_status": s.review_status,
            "version": s.version,
            "is_active": s.is_active,
            "ab_test_group": s.ab_test_group,
        }
        for s in scripts
    ]


@router.post("/feedback-scripts")
async def create_feedback_script(
    req: FeedbackScriptRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建新文案"""
    script = FeedbackScript(
        category=req.category,
        sub_category=req.sub_category,
        text=req.text,
        author=req.author,
        ab_test_group=req.ab_test_group,
        review_status="draft",
    )
    db.add(script)
    await db.flush()
    await db.refresh(script)

    return {"id": str(script.id), "message": "文案已创建，等待审核"}


# ─── 告警规则配置 ─────────────────────────────

@router.get("/alert-rules")
async def get_alert_rules(
    user: User = Depends(require_admin),
):
    """获取告警规则配置"""
    return {
        "rules": [
            {
                "name": "daily_usage",
                "trigger": "if daily_usage_hours > 3.5",
                "action": "notify_teacher + notify_parent",
                "severity": "yellow",
                "description": "学生日均使用超3.5小时",
            },
            {
                "name": "consecutive_usage",
                "trigger": "if session_minutes > 120",
                "action": "force_rest + notify_teacher",
                "severity": "red",
                "description": "连续使用超120分钟",
            },
            {
                "name": "night_usage",
                "trigger": "if night_usage_ratio > 0.2",
                "action": "notify_parent",
                "severity": "red",
                "description": "夜间使用占比超20%",
            },
            {
                "name": "performance_drop",
                "trigger": "if 3_day_streak_decline",
                "action": "notify_teacher",
                "severity": "yellow",
                "description": "连续3天掌握度下降",
            },
        ]
    }


# ─── 系统统计 ─────────────────────────────────

@router.get("/stats")
async def get_system_stats(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统整体统计"""
    total_users = await db.execute(select(func.count(User.id)))
    total_tasks = await db.execute(select(func.count(Task.id)))
    total_attempts = await db.execute(select(func.count(Attempt.id)))

    return {
        "total_users": total_users.scalar(),
        "total_tasks": total_tasks.scalar(),
        "total_attempts": total_attempts.scalar(),
    }
