"""家长端 API：学习摘要、同意管理、数据导出"""
from datetime import datetime, UTC, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.task import Attempt, StudentSkillProfile
from app.models.pet import PetProfile
from app.models.consent import ConsentRecord, ConsentType, Alert

router = APIRouter(prefix="/api/v1/parent", tags=["家长端"])

# K12 增量路由（Spec §4 精确路径）
k12_router = APIRouter(prefix="/api/v1/parent", tags=["家长 K12"])


async def require_parent(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="仅家长可访问")
    return user


def _is_demo_child(parent_email: str, child_email: str) -> bool:
    """判断是否为演示绑定关系：
    - parent_student@learnflow.com ↔ student@learnflow.com
    - parent@learnflow.com 作为通用演示家长，可查看 student@learnflow.com
    """
    local = parent_email.split("@")[0]
    if local.startswith("parent_"):
        expected_child = f"{local.replace('parent_', '')}@learnflow.com"
        return child_email == expected_child
    # 通用演示家长账号可查看默认演示学生
    if parent_email == "parent@learnflow.com" and child_email == "student@learnflow.com":
        return True
    return False


class ConsentRequest(BaseModel):
    child_id: str
    consent_type: str
    granted: bool


class DailyLimitRequest(BaseModel):
    daily_limit_minutes: int | None = None  # None 表示清除上限


# ─── 孩子学习摘要 ─────────────────────────────

@router.get("/child/{child_id}/summary")
async def get_child_summary(
    child_id: str,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """查看孩子的学习摘要"""
    child_query = await db.execute(select(User).where(User.id == child_id))
    child = child_query.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="未找到该孩子")

    # 验证亲子关系：真实 parent_id 匹配 或 演示绑定
    is_authorized = (
        child.parent_id == user.id
        or _is_demo_child(user.email, child.email)
    )
    if not is_authorized:
        raise HTTPException(status_code=404, detail="未找到该孩子或无权查看")

    week_ago = datetime.now(UTC) - timedelta(days=7)
    week_attempts = await db.execute(
        select(
            func.count(Attempt.id),
            func.sum(case((Attempt.is_correct == True, 1), else_=0)),
        )
        .where(
            Attempt.user_id == child.id,
            Attempt.created_at >= week_ago,
        )
    )
    total_week, correct_week = week_attempts.first()

    skills = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == child.id)
    )
    skill_list = skills.scalars().all()

    pet = await db.execute(select(PetProfile).where(PetProfile.user_id == child.id))
    pet_data = pet.scalar_one_or_none()

    alerts = await db.execute(
        select(Alert)
        .where(Alert.user_id == child.id, Alert.is_resolved == False)
        .order_by(Alert.created_at.desc())
        .limit(5)
    )
    alert_list = alerts.scalars().all()

    return {
        "child": {"id": str(child.id), "name": child.name, "grade": child.grade},
        "weekly": {
            "total_attempts": total_week or 0,
            "correct_attempts": correct_week or 0,
            "accuracy": round((correct_week or 0) / max(total_week or 1, 1) * 100, 1),
        },
        "skills": [
            {"skill": s.skill_dim, "score": round(s.score, 1), "mastery": round(s.mastery, 3) if s.mastery else 0.0}
            for s in skill_list
        ],
        "pet": {
            "name": pet_data.name,
            "level": pet_data.level,
            "mood": pet_data.mood.value,
            "total_score": round(pet_data.total_score, 1),
        } if pet_data else None,
        "alerts": [
            {"type": a.alert_type.value, "severity": a.severity.value, "title": a.title}
            for a in alert_list
        ],
        "risk_level": "red" if alert_list else "green",
    }


# ─── 同意管理 ─────────────────────────────────

@router.get("/consent-settings/{child_id}")
async def get_consent_settings(
    child_id: str,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """查看孩子的同意设置"""
    child_query = await db.execute(select(User).where(User.id == child_id))
    child = child_query.scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权查看")

    consents = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == child.id).order_by(
            ConsentRecord.consented_at.desc()
        )
    )
    records = consents.scalars().all()

    return {
        "consents": child.consents or {},
        "history": [
            {
                "type": r.consent_type.value,
                "granted": r.revoked_at is None,
                "granted_at": r.consented_at.isoformat(),
                "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
            }
            for r in records
        ],
    }


@router.post("/consent")
async def update_child_consent(
    req: ConsentRequest,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """家长为孩子管理同意"""
    child_query = await db.execute(select(User).where(User.id == req.child_id))
    child = child_query.scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权操作")

    if not child.consents:
        child.consents = {}

    if req.granted:
        child.consents[req.consent_type] = True
        try:
            record = ConsentRecord(
                user_id=child.id,
                consent_type=ConsentType(req.consent_type),
                granted_by=user.id,
            )
            db.add(record)
        except ValueError:
            pass
    else:
        child.consents[req.consent_type] = False
        revoke = await db.execute(
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == child.id,
                ConsentRecord.consent_type == ConsentType(req.consent_type),
                ConsentRecord.revoked_at.is_(None),
            )
            .order_by(ConsentRecord.consented_at.desc())
            .limit(1)
        )
        record = revoke.scalar_one_or_none()
        if record:
            record.revoked_at = datetime.now(UTC)

    await db.flush()

    return {
        "message": f"{req.consent_type} 已{'开启' if req.granted else '关闭'}",
        "consent_type": req.consent_type,
        "granted": req.granted,
    }


# ─── 数据导出 ─────────────────────────────────

@router.get("/child/{child_id}/export")
async def export_child_data(
    child_id: str,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """导出孩子的全部学习数据（JSON格式）"""
    child_query = await db.execute(select(User).where(User.id == child_id))
    child = child_query.scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权操作")

    attempts = await db.execute(
        select(Attempt).where(Attempt.user_id == child.id).order_by(Attempt.created_at)
    )
    all_attempts = attempts.scalars().all()

    skills = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == child.id)
    )
    all_skills = skills.scalars().all()

    return {
        "export_date": datetime.now(UTC).isoformat(),
        "child": {"id": str(child.id), "name": child.name, "grade": child.grade},
        "attempts": [
            {
                "task_id": str(a.task_id),
                "is_correct": a.is_correct,
                "difficulty": a.difficulty_at_time,
                "time_spent": a.time_spent,
                "date": a.created_at.isoformat(),
            }
            for a in all_attempts
        ],
        "skills": [
            {"skill": s.skill_dim, "score": round(s.score, 1), "total_attempts": s.total_attempts}
            for s in all_skills
        ],
        "total_records": len(all_attempts),
    }


# ═══════════════════════════════════════════════════════
# K12 家长周报（Spec §4）—— 非分数导向：时长 / 难度曲线 / 掌握度 / 风险
# ═════════════════════════════════════════════════════

@k12_router.get("/weekly-report")
async def weekly_report(
    student_id: str,
    week: str | None = None,  # 周起始日 ISO date，默认最近 7 天
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """家长周报：时长 / 难度曲线 / 掌握度 / 风险等级（去分数焦虑）"""
    child = (await db.execute(select(User).where(User.id == student_id))).scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权查看")

    now = datetime.now(UTC)
    if week:
        try:
            week_start = datetime.fromisoformat(week).replace(tzinfo=UTC)
        except ValueError:
            week_start = now - timedelta(days=7)
    else:
        week_start = now - timedelta(days=7)
    week_end = week_start + timedelta(days=7)

    week_attempts_q = await db.execute(
        select(Attempt)
        .options(selectinload(Attempt.task))
        .where(
            Attempt.user_id == child.id,
            Attempt.created_at >= week_start,
            Attempt.created_at < week_end,
        )
        .order_by(Attempt.created_at.asc())
    )
    week_attempts = list(week_attempts_q.scalars().all())

    # 时长（按每次约 3 分钟估算，去分数焦虑，只给时长）
    duration_minutes = len(week_attempts) * 3

    # 难度曲线：按天聚合平均难度
    from collections import defaultdict
    by_day = defaultdict(list)
    for a in week_attempts:
        day = a.created_at.strftime("%Y-%m-%d") if a.created_at else None
        if day:
            by_day[day].append(a.difficulty_at_time or 5)
    difficulty_curve = [
        {"date": d, "avg_difficulty": round(sum(v) / len(v), 1)}
        for d, v in sorted(by_day.items())
    ]

    # 掌握度：技能画像均值
    skills_q = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == child.id)
    )
    skills = skills_q.scalars().all()
    avg_score = round(sum(s.score for s in skills) / max(len(skills), 1), 1) if skills else 0.0

    # 风险等级：基于未解决告警
    alerts_q = await db.execute(
        select(Alert)
        .where(Alert.user_id == child.id, Alert.is_resolved == False)
        .order_by(Alert.severity.desc())
        .limit(1)
    )
    top_alert = alerts_q.scalar_one_or_none()
    risk_level = top_alert.severity.value if top_alert else "green"

    return {
        "student_id": str(child.id),
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "duration": {"minutes": duration_minutes, "sessions": len(week_attempts)},
        "difficulty_curve": difficulty_curve,
        "mastery": {
            "avg_score": avg_score,
            "skills": [
                {"skill": s.skill_dim, "score": round(s.score, 1), "mastery": round(s.mastery, 3) if s.mastery else 0.0}
                for s in skills
            ],
        },
        "risk_level": risk_level,
    }


@router.get("/children")
async def list_children(
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """列出当前家长绑定的孩子（供前端解析 child_id）"""
    rows = (
        await db.execute(
            select(User).where(User.parent_id == user.id, User.is_active == True)
        )
    ).scalars().all()
    return {"children": [{"id": c.id, "name": c.name, "grade": c.grade} for c in rows]}


# ─── 每日学习时长上限（家长设定的真实持久化） ────────────

@router.get("/child/{child_id}/daily-limit")
async def get_child_daily_limit(
    child_id: str,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """查看孩子的每日学习时长上限（分钟）；未设置时为 null"""
    child_query = await db.execute(select(User).where(User.id == child_id))
    child = child_query.scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权查看")

    return {
        "child_id": str(child.id),
        "daily_limit_minutes": child.daily_limit_minutes,
    }


@router.put("/child/{child_id}/daily-limit")
async def set_child_daily_limit(
    child_id: str,
    req: DailyLimitRequest,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """设定/清除孩子的每日学习时长上限（分钟）

    - 20..180 为合法区间；越界返回 400
    - 传 null 表示清除上限
    """
    child_query = await db.execute(select(User).where(User.id == child_id))
    child = child_query.scalar_one_or_none()
    if not child or (child.parent_id != user.id and not _is_demo_child(user.email, child.email)):
        raise HTTPException(status_code=404, detail="未找到该孩子或无权操作")

    value = req.daily_limit_minutes
    if value is not None and not (20 <= value <= 180):
        raise HTTPException(
            status_code=400,
            detail="daily_limit_minutes 必须在 20..180 分钟之间，或为 null 以清除",
        )

    child.daily_limit_minutes = value
    await db.flush()

    return {
        "child_id": str(child.id),
        "daily_limit_minutes": child.daily_limit_minutes,
    }
