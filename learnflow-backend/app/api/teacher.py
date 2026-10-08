"""教师端 API：班级仪表盘、任务管理、AI建议、风险告警"""
from datetime import datetime, timedelta, UTC
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.task import Task, Attempt, StudentSkillProfile
from app.models.pet import PetProfile
from app.models.consent import Alert
from app.services.teacher_ai_assistant import TeacherAIAssistant
from app.services.assignment_versions import latest_versions, new_version, progress
from app.models.curriculum import Class, Assignment, AssignmentResponse, AssignmentVersion, AssignmentVersionResponse, CurriculumNode

router = APIRouter(prefix="/api/v1/teacher", tags=["教师端"])

# K12 增量路由（Spec §4 精确路径，与既有 /api/v1/teacher 共存）
k12_router = APIRouter(prefix="/api/v1/teacher", tags=["教师 K12"])


async def require_teacher(user: User = Depends(get_current_user)) -> User:
    """确保当前用户是教师或管理员"""
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可访问")
    return user


class CreateTaskRequest(BaseModel):
    title: str | None = None
    content: str
    topic: str
    difficulty: int = Field(default=5, ge=1, le=10)
    correct_answer: str
    explanation: str | None = None
    hint_levels: list[str] | None = None
    time_estimate: int = Field(default=120, ge=1, le=86400)

    @field_validator("content", "topic", "correct_answer")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value


class AdjustDifficultyRequest(BaseModel):
    student_id: str
    new_difficulty: int = Field(ge=1, le=10)


class BatchAdjustRequest(BaseModel):
    student_ids: List[str]
    difficulty_delta: int = 0


def student_scope(user: User):
    conditions = [User.role == UserRole.STUDENT, User.is_active == True]
    if user.role != UserRole.ADMIN:
        conditions.append(User.class_id.in_(select(Class.id).where(Class.teacher_id == user.id)))
    return conditions


async def owned_student(student_id: str, user: User, db: AsyncSession) -> User:
    student = (await db.execute(select(User).where(User.id == student_id, *student_scope(user)))).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在或不属于当前教师")
    return student


async def owned_class(class_id: str, user: User, db: AsyncSession) -> Class:
    conditions = [Class.id == class_id]
    if user.role != UserRole.ADMIN:
        conditions.append(Class.teacher_id == user.id)
    klass = (await db.execute(select(Class).where(*conditions))).scalar_one_or_none()
    if klass is None:
        raise HTTPException(status_code=404, detail="班级不存在或不属于当前教师")
    return klass


# ─── 班级仪表盘 ───────────────────────────────

@router.get("/classroom")
async def get_classroom(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """教师班级仪表盘数据"""
    classes = (await db.execute(select(Class).where(
        *([] if user.role == UserRole.ADMIN else [Class.teacher_id == user.id])
    ).order_by(Class.name, Class.id))).scalars().all()
    students_query = await db.execute(
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True,
                           User.class_id.in_([klass.id for klass in classes]))
    )
    students = students_query.scalars().all()
    student_ids = [s.id for s in students]

    skills_query = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id.in_(student_ids))
    )
    all_skills = skills_query.scalars().all()
    skills_by_student: dict = {}
    for s in all_skills:
        skills_by_student.setdefault(str(s.user_id), []).append(s)

    alerts_query = await db.execute(
        select(Alert)
        .where(Alert.user_id.in_(student_ids), Alert.is_resolved == False)
        .order_by(Alert.severity.desc(), Alert.created_at.desc())
    )
    all_alerts = alerts_query.scalars().all()
    alerts_by_student: dict = {}
    for a in all_alerts:
        alerts_by_student.setdefault(str(a.user_id), []).append(a)

    student_data = []
    alerts_list = []

    for student in students:
        skills = skills_by_student.get(str(student.id), [])
        alerts = alerts_by_student.get(str(student.id), [])
        recent_alerts = alerts[:3]

        for a in recent_alerts:
            alerts_list.append({
                "student_id": str(student.id),
                "student_name": student.name,
                "type": a.alert_type.value,
                "severity": a.severity.value,
                "title": a.title,
                "created_at": a.created_at.isoformat(),
            })

        avg_score = sum(s.score for s in skills) / max(len(skills), 1)

        student_data.append({
            "id": str(student.id),
            "name": student.name,
            "grade": student.grade,
            "avg_score": round(avg_score, 1),
            "skill_count": len(skills),
            "has_alerts": len(recent_alerts) > 0,
        })

    return {
        "classes": [{"id": klass.id, "name": klass.name, "grade_id": klass.grade_id} for klass in classes],
        "total_students": len(students),
        "class_avg_score": round(
            sum(s["avg_score"] for s in student_data) / max(len(student_data), 1), 1
        ),
        "students": student_data,
        "alerts": alerts_list,
    }


# ─── 学生详情 ─────────────────────────────────

@router.get("/student/{student_id}")
async def get_student_detail(
    student_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """单个学生详情"""
    student = await owned_student(student_id, user, db)

    pet_query = await db.execute(select(PetProfile).where(PetProfile.user_id == student.id))
    pet = pet_query.scalar_one_or_none()

    attempts_query = await db.execute(
        select(Attempt)
        .options(selectinload(Attempt.task))
        .where(Attempt.user_id == student.id)
        .order_by(Attempt.created_at.desc())
        .limit(50)
    )
    attempts = attempts_query.scalars().all()

    skills_query = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == student.id)
    )
    skills = skills_query.scalars().all()

    return {
        "student": {
            "id": str(student.id),
            "name": student.name,
            "grade": student.grade,
            "consents": student.consents,
        },
        "pet": {
            "name": pet.name,
            "level": pet.level,
            "mood": pet.mood.value,
            "total_score": round(pet.total_score, 1),
        } if pet else None,
        "recent_activity": [
            {
                "task_topic": a.task.topic if a.task else "未知",
                "is_correct": a.is_correct,
                "difficulty": a.difficulty_at_time,
                "time_spent": a.time_spent,
                "created_at": a.created_at.isoformat(),
            }
            for a in attempts[:20]
        ],
        "skills": [
            {
                "skill": s.skill_dim,
                "score": round(s.score, 1),
                "mastery": round(s.mastery, 3) if s.mastery else 0.0,
                "success_rate": round(s.success_rate * 100, 1),
            }
            for s in skills
        ],
    }


# ─── 任务管理 ─────────────────────────────────

@router.post("/tasks")
async def create_task(
    req: CreateTaskRequest,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """创建新任务/题目（需管理员审核）"""
    task = Task(
        title=req.title,
        content=req.content,
        topic=req.topic,
        difficulty=req.difficulty,
        correct_answer=req.correct_answer,
        explanation=req.explanation,
        hint_levels=req.hint_levels,
        time_estimate=req.time_estimate,
        source="teacher_upload",
        created_by=user.id,
        is_approved=False,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    return {
        "id": str(task.id),
        "title": task.title,
        "topic": task.topic,
        "difficulty": task.difficulty,
        "status": "pending_review",
    }


@router.get("/tasks")
async def list_tasks(
    topic: str | None = None,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """获取教师创建的题目列表"""
    query = select(Task).where(Task.created_by == user.id)
    if topic:
        query = query.where(Task.topic == topic)
    query = query.order_by(Task.created_at.desc()).limit(50)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "title": t.title,
            "topic": t.topic,
            "difficulty": t.difficulty,
            "is_approved": t.is_approved,
            "review_status": "approved" if t.is_approved else "rejected" if t.reviewed_at else "pending_review",
            "review_notes": t.review_notes,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


# ─── AI 建议 ──────────────────────────────────

@router.get("/suggestions")
async def get_suggestions(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """AI 教学建议"""
    students_query = await db.execute(
        select(User).where(*student_scope(user))
    )
    students = students_query.scalars().all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return {"suggestions": [], "total": 0}

    all_attempts_query = await db.execute(
        select(Attempt)
        .where(Attempt.user_id.in_(student_ids))
        .order_by(Attempt.created_at.desc())
    )
    all_attempts = all_attempts_query.scalars().all()

    attempts_by_student: dict = {}
    for a in all_attempts:
        key = str(a.user_id)
        lst = attempts_by_student.setdefault(key, [])
        if len(lst) < 20:
            lst.append(a)

    suggestions = []
    for student in students:
        recent = attempts_by_student.get(str(student.id), [])
        if not recent:
            continue

        success_rate = sum(1 for a in recent if a.is_correct) / len(recent)

        if success_rate > 0.85 and len(recent) >= 5:
            suggestions.append({
                "type": "difficulty_upgrade",
                "student_id": str(student.id),
                "student_name": student.name,
                "reason": f"最近{len(recent)}题成功率{success_rate:.0%}，建议升级难度",
                "severity": "green",
            })
        elif success_rate < 0.45 and len(recent) >= 5:
            suggestions.append({
                "type": "intervention_needed",
                "student_id": str(student.id),
                "student_name": student.name,
                "reason": f"最近{len(recent)}题成功率仅{success_rate:.0%}，可能需要额外辅导",
                "severity": "red",
            })

    return {"suggestions": suggestions, "total": len(suggestions)}


# ─── 告警管理 ─────────────────────────────────

@router.get("/alerts")
async def get_alerts(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """获取所有未解决告警"""
    result = await db.execute(
        select(Alert)
        .where(Alert.is_resolved == False, Alert.user_id.in_(select(User.id).where(*student_scope(user))))
        .order_by(Alert.severity.desc(), Alert.created_at.desc())
        .limit(50)
    )
    alerts = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "student_id": str(a.user_id),
            "type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
            "description": a.description,
            "notified_parent": a.notified_parent,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """解决告警"""
    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.user_id.in_(select(User.id).where(*student_scope(user)))))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    alert.is_resolved = True
    alert.resolved_by = user.id
    alert.resolved_at = datetime.now(UTC)
    await db.flush()

    return {"message": "告警已解决", "alert_id": str(alert.id)}


# ═══════════════════════════════════════════════════════
# AI 教师助手 — 智能分析与建议
# ═══════════════════════════════════════════════════════

@router.get("/ai/classroom-analysis")
async def get_ai_classroom_analysis(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """AI 班级全景分析"""
    students_query = await db.execute(
        select(User).where(*student_scope(user))
    )
    students = students_query.scalars().all()
    student_ids = [str(s.id) for s in students]

    skills_query = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id.in_(student_ids))
    )
    all_skills = skills_query.scalars().all()

    topic_mastery: dict = {}
    topic_difficulty: dict = {}
    for sk in all_skills:
        topic_mastery[sk.skill_dim] = max(topic_mastery.get(sk.skill_dim, 0), sk.score / 100)

    attempts_query = await db.execute(
        select(Attempt).where(Attempt.user_id.in_(student_ids))
        .order_by(Attempt.created_at.desc()).limit(500)
    )
    all_attempts = attempts_query.scalars().all()

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    active_today = (await db.execute(select(func.count(func.distinct(Attempt.user_id))).where(
        Attempt.user_id.in_(student_ids), Attempt.created_at >= day_start,
        Attempt.created_at < day_start + timedelta(days=1)
    ))).scalar_one()

    student_summaries = []
    for student in students:
        sid = str(student.id)
        skills = [s for s in all_skills if str(s.user_id) == sid]
        s_attempts = [a for a in all_attempts if str(a.user_id) == sid]

        avg_mastery = sum(s.score for s in skills) / max(len(skills), 1) / 100
        recent_20 = s_attempts[:20]
        recent_accuracy = [a.is_correct for a in recent_20]
        trend_score = sum(1 for a in recent_20 if a.is_correct) / max(len(recent_20), 1)
        current_streak = 0
        for is_correct in recent_accuracy:
            if is_correct:
                current_streak += 1
            else:
                break

        student_summaries.append({
            "id": sid,
            "name": student.name,
            "overall_mastery": avg_mastery,
            "trend_score": trend_score,
            "current_streak": current_streak,
            "hook_loops": len(s_attempts),
            "total_attempts": len(s_attempts),
        })

    # 真实统计：全部基于已加载的 all_attempts 计算，杜绝硬编码假数据
    if not all_attempts:
        difficulty_distribution = {}
        most_active_hour = None
        weekend_ratio = None
    else:
        hour_counts: dict = {}
        weekend_count = 0
        dist_counts: dict = {}
        for a in all_attempts:
            ts = a.created_at
            if ts is not None:
                hour_counts[ts.hour] = hour_counts.get(ts.hour, 0) + 1
                if ts.weekday() >= 5:
                    weekend_count += 1
            diff = a.difficulty_at_time if a.difficulty_at_time is not None else 5
            key = str(diff)
            dist_counts[key] = dist_counts.get(key, 0) + 1
        # 模态小时；若无任何有效时间戳则保留 None（不臆造）
        most_active_hour = (
            f"{max(hour_counts, key=hour_counts.get):02d}:00" if hour_counts else None
        )
        weekend_ratio = round(weekend_count / len(all_attempts), 2)
        # 注意：本分支必须显式回填 difficulty_distribution，否则非空作答时
        # class_stats 引用到未绑定的局部名 → UnboundLocalError（500）。
        difficulty_distribution = dist_counts

    class_stats = {
        "total_students": len(students),
        "active_today": active_today,
        "class_avg_mastery": sum(s["overall_mastery"] for s in student_summaries) / max(len(student_summaries), 1),
        "topic_mastery": topic_mastery,
        "topic_difficulty": topic_difficulty,
        "difficulty_distribution": difficulty_distribution,
        "most_active_hour": most_active_hour,
        "weekend_ratio": weekend_ratio,
    }

    report = TeacherAIAssistant.analyze_classroom(student_summaries, class_stats)
    return report.__dict__ if hasattr(report, '__dict__') else report


@router.get("/ai/student-analysis/{student_id}")
async def get_ai_student_analysis(
    student_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """AI 单个学生深度分析"""
    student = await owned_student(student_id, user, db)

    skills_q = await db.execute(
        select(StudentSkillProfile).where(StudentSkillProfile.user_id == student_id)
    )
    skills = skills_q.scalars().all()

    attempts_q = await db.execute(
        select(Attempt).where(Attempt.user_id == student_id)
        .order_by(Attempt.created_at.desc()).limit(100)
    )
    attempts = attempts_q.scalars().all()

    recent = attempts[:20]
    skill_scores = {s.skill_dim: s.score / 100 for s in skills}
    avg_mastery = sum(skill_scores.values()) / max(len(skill_scores), 1)
    recent_acc = [a.is_correct for a in recent]
    recent_accuracy_list = [1.0 if a else 0.0 for a in recent_acc]

    current_streak = 0
    for is_correct in recent_acc:
        if is_correct:
            current_streak += 1
        else:
            break

    window_end = datetime.now(UTC)
    weekly_count = (await db.execute(select(func.count(Attempt.id)).where(
        Attempt.user_id == student_id, Attempt.created_at >= window_end - timedelta(days=7),
        Attempt.created_at <= window_end
    ))).scalar_one()
    total_count = (await db.execute(select(func.count(Attempt.id)).where(Attempt.user_id == student_id))).scalar_one()

    stats = {
        "avg_mastery": avg_mastery,
        "skill_scores": skill_scores,
        "recent_accuracy": recent_accuracy_list,
        "current_streak": current_streak,
        "weekly_attempts": weekly_count,
        "avg_difficulty": sum(a.difficulty_at_time or 5 for a in attempts) / max(len(attempts), 1),
        "skip_ratio": None,
        "help_others": 0,
        "hook_loops": len(attempts),
        "total_attempts": total_count,
        "consecutive_failures": TeacherAIAssistant._count_consecutive_fails(recent_acc) if recent_acc else 0,
        "identity_labels": [],
        "identity_count": 0,
    }

    report = TeacherAIAssistant.analyze_student(
        {"id": str(student.id), "name": student.name, "grade": student.grade or ""}, stats)
    return report.__dict__ if hasattr(report, '__dict__') else report


@router.get("/ai/difficulty-suggestions")
async def get_difficulty_suggestions(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """获取全班难度调整建议"""
    students_q = await db.execute(
        select(User).where(*student_scope(user))
    )
    students = students_q.scalars().all()

    suggestions = []
    for s in students:
        attempts_q = await db.execute(
            select(Attempt).where(Attempt.user_id == s.id)
            .order_by(Attempt.created_at.desc()).limit(20)
        )
        s_attempts = attempts_q.scalars().all()
        recent_acc = sum(1 for a in s_attempts if a.is_correct) / max(len(s_attempts), 1)

        suggestion = TeacherAIAssistant.suggest_difficulty_adjustment(
            str(s.id),
            s_attempts[0].difficulty_at_time if s_attempts else 5,
            recent_acc,
            recent_acc,
        )
        suggestion["student_name"] = s.name
        suggestions.append(suggestion)

    return {"suggestions": suggestions, "total": len(suggestions)}


@router.post("/ai/adjust-difficulty")
async def adjust_student_difficulty(
    req: AdjustDifficultyRequest,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """手动/自动调整学生难度（保存到最近答题难度偏置）"""
    student = await owned_student(req.student_id, user, db)

    student.difficulty_bias = float(max(-4, min(4, req.new_difficulty - 5)))  # 以 5 为中性基线
    await db.commit()

    return {
        "message": "已保存难度偏置",
        "student_id": req.student_id,
        "requested_difficulty": req.new_difficulty,
        "difficulty_bias": student.difficulty_bias,
        "applied_to": "dda_bias",
        "applied_by": str(user.id),
        "persisted": True,
    }


@router.get("/ai/intervention-plan")
async def get_intervention_plan(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """获取教学干预计划"""
    students_q = await db.execute(
        select(User).where(*student_scope(user))
    )
    students = students_q.scalars().all()

    plan = {"urgent": [], "monitor": [], "challenge": [], "summary": ""}

    for s in students:
        attempts_q = await db.execute(
            select(Attempt).where(Attempt.user_id == s.id)
            .order_by(Attempt.created_at.desc()).limit(20)
        )
        attempts = attempts_q.scalars().all()
        acc = sum(1 for a in attempts if a.is_correct) / max(len(attempts), 1)

        if len(attempts) < 3:
            plan["monitor"].append({
                "student_id": str(s.id), "name": s.name,
                "reason": "数据不足，需要更多学习记录",
                "action": "鼓励学生开始使用系统",
            })
        elif acc < 0.4:
            plan["urgent"].append({
                "student_id": str(s.id), "name": s.name,
                "reason": f"最近正确率仅{acc:.0%}",
                "action": "建议降难度2级 + 安排讲解",
            })
        elif acc > 0.9 and len(attempts) >= 10:
            plan["challenge"].append({
                "student_id": str(s.id), "name": s.name,
                "reason": f"最近正确率{acc:.0%}，可以挑战",
                "action": "建议升难度 + 给予挑战题",
            })

    plan["summary"] = (
        f"紧急: {len(plan['urgent'])}人 | "
        f"观察: {len(plan['monitor'])}人 | "
        f"可挑战: {len(plan['challenge'])}人"
    )

    return plan


# ═══════════════════════════════════════════════════════
# K12 作业布置 / 班级掌握（Spec §4）
# ═════════════════════════════════════════════════════

class CreateAssignmentRequest(BaseModel):
    class_id: str
    node_ids: List[str] = Field(min_length=1, max_length=200)
    due_at: str | None = None  # ISO datetime with explicit timezone
    new_version: bool = False


@k12_router.post("/assignments")
async def create_assignments(
    req: CreateAssignmentRequest,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """教师布置作业（班级 + 若干课标知识点 + 截止时间）"""
    async def flush_or_conflict():
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=409,detail="作业版本发生并发修改，请重新读取后重试") from exc

    klass = await owned_class(req.class_id, user, db)

    due_at = None
    if req.due_at:
        try:
            parsed = datetime.fromisoformat(req.due_at)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError('timezone required')
            due_at = parsed.astimezone(UTC).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="due_at 必须是包含时区的 ISO datetime")

    node_ids = list(dict.fromkeys(req.node_ids))
    nodes = (await db.execute(select(CurriculumNode).where(CurriculumNode.id.in_(node_ids)))).scalars().all()
    if len(nodes) != len(node_ids):
        raise HTTPException(status_code=400, detail="包含不存在的知识点，未布置作业")
    if klass.grade_id and any(node.grade_id != klass.grade_id for node in nodes):
        raise HTTPException(status_code=400, detail="知识点年级与班级不匹配")
    existing = {row.node_id: row for row in (await db.execute(
        select(Assignment).where(Assignment.class_id == klass.id, Assignment.node_id.in_(node_ids))
    )).scalars().all()}
    versions = await latest_versions(db, [a.id for a in existing.values()])
    tasks_by_node = {}
    for node_id in node_ids:
        old = existing.get(node_id)
        if old is None or old.id not in versions or req.new_version:
            tasks = (await db.execute(select(Task).where(Task.curriculum_node_id == node_id,
                Task.is_approved == True).order_by(Task.id))).scalars().all()
            if not tasks:
                raise HTTPException(status_code=400, detail="知识点没有已审核题目，未布置作业")
            tasks_by_node[node_id] = tasks
    created_ids = []
    new_count = 0
    for node_id in node_ids:
        assignment = existing.get(node_id)
        if assignment is None:
            assignment = Assignment(class_id=klass.id, node_id=node_id, due_at=due_at)
            db.add(assignment)
            new_count += 1
        else:
            assignment.due_at = due_at
        await flush_or_conflict()
        if node_id in tasks_by_node:
            previous = versions.get(assignment.id)
            db.add(new_version(assignment.id, previous.number + 1 if previous else 1, tasks_by_node[node_id]))
        created_ids.append(str(assignment.id))

    await flush_or_conflict()
    return {"assignment_id": created_ids[0] if created_ids else None, "created": new_count, "updated": len(created_ids) - new_count}


@k12_router.get("/assignments")
async def list_assignments(
    class_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """班级作业列表"""
    await owned_class(class_id, user, db)
    result = await db.execute(
        select(Assignment)
        .where(Assignment.class_id == class_id)
        .order_by(Assignment.created_at.desc())
    )
    assignments = result.scalars().all()
    nodes_index = {
        str(n.id): n for n in (await db.execute(select(CurriculumNode))).scalars().all()
    }
    return {
        "assignments": [
            {
                "id": str(a.id),
                "class_id": str(a.class_id),
                "node_id": str(a.node_id),
                "node_title": nodes_index.get(str(a.node_id)).title if nodes_index.get(str(a.node_id)) else None,
                "due_at": a.due_at.replace(tzinfo=UTC).isoformat() if a.due_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in assignments
        ]
    }


@k12_router.get("/assignments/{assignment_id}/versions")
async def assignment_versions(assignment_id: str, user: User = Depends(require_teacher), db: AsyncSession = Depends(get_db)):
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404,detail="作业不存在")
    await owned_class(assignment.class_id,user,db)
    versions = (await db.execute(select(AssignmentVersion).where(AssignmentVersion.assignment_id == assignment.id)
        .order_by(AssignmentVersion.number.desc()))).scalars().all()
    return {'versions':[{'id':v.id,'number':v.number,'task_count':len(v.tasks),'sha256':v.sha256,
        'created_at':v.created_at.replace(tzinfo=UTC).isoformat()} for v in versions]}


@k12_router.get("/assignments/{assignment_id}/results")
async def assignment_results(
    assignment_id: str,
    version_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    await owned_class(assignment.class_id, user, db)
    conditions = [User.class_id == assignment.class_id, User.role == UserRole.STUDENT, User.is_active == True]
    total = (await db.execute(select(func.count(User.id)).where(*conditions))).scalar_one()
    students = (await db.execute(select(User).where(*conditions).order_by(User.name, User.id)
        .offset(offset).limit(limit))).scalars().all()
    if version_id:
        version = (await db.execute(select(AssignmentVersion).where(AssignmentVersion.id == version_id,
            AssignmentVersion.assignment_id == assignment.id))).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=404,detail="作业版本不存在")
    else:
        version = (await latest_versions(db, [assignment.id])).get(assignment.id)
    response_model = AssignmentVersionResponse if version else AssignmentResponse
    scope = response_model.version_id == version.id if version else response_model.assignment_id == assignment.id
    rows = (await db.execute(select(response_model.user_id,
        func.count(Attempt.id), func.sum(case((Attempt.is_correct == True, 1), else_=0)),
        func.max(response_model.created_at))
        .join(Attempt, Attempt.id == response_model.attempt_id)
        .where(scope, response_model.user_id.in_([student.id for student in students]))
        .group_by(response_model.user_id))).all()
    version_submissions = {}
    if version:
        for uid, tid in (await db.execute(select(response_model.user_id,response_model.task_id).where(
            scope,response_model.attempt_id.is_not(None),response_model.user_id.in_([student.id for student in students])))).all():
            version_submissions.setdefault(uid,set()).add(tid)
    approved_ids = set((await db.execute(select(Task.id).where(Task.is_approved == True,Task.id.in_([item['id'] for item in version.tasks] if version else [])))).scalars().all())
    stats = {row[0]: row[1:] for row in rows}
    available = (await db.execute(select(func.count(Task.id)).where(
        Task.curriculum_node_id == assignment.node_id, Task.is_approved == True))).scalar_one()
    output = []
    for student in students:
        count, correct, last = stats.get(student.id, (0, 0, None))
        output.append({'student_id': student.id, 'student_name': student.name,
            'submitted_count': count, 'correct_count': int(correct),
            'accuracy_percent': round(100 * correct / count, 1) if count else None,
            'last_submitted_at': last.replace(tzinfo=UTC).isoformat() if last else None,
            **(progress(version, version_submissions.get(student.id,set()), approved_ids) if version else {'submission_state':'legacy_unversioned'})})
    return {'assignment_id': assignment.id, 'version_id':version.id if version else None,
        'version_number':version.number if version else None, 'task_count':len(version.tasks) if version else None,
        'available_task_count': available,
        'students': output, 'total_students': total, 'has_more': offset + len(students) < total}


@k12_router.get("/class-mastery")
async def class_mastery(
    class_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """班级掌握热力图（按知识点，基于该知识点下题目的答题正确率）"""
    klass = await owned_class(class_id, user, db)

    grade_id = klass.grade_id
    if grade_id:
        nodes = (await db.execute(
            select(CurriculumNode).where(CurriculumNode.grade_id == grade_id)
        )).scalars().all()
    else:
        nodes = (await db.execute(select(CurriculumNode))).scalars().all()

    nodes_index = {str(n.id): n for n in nodes}
    task_rows = (await db.execute(
        select(Task.id, Task.curriculum_node_id).where(Task.curriculum_node_id.in_(list(nodes_index.keys())))
    )).all()
    task_to_node = {str(tid): str(nid) for tid, nid in task_rows}

    mastery_out = []
    for node in nodes:
        node_tasks = [tid for tid, nid in task_to_node.items() if nid == str(node.id)]
        if not node_tasks:
            mastery_out.append({"id": str(node.id), "title": node.title, "mastery": None, "attempt_count": 0})
            continue
        agg = (await db.execute(
            select(
                func.count(Attempt.id),
                func.sum(case((Attempt.is_correct == True, 1), else_=0)),
            ).where(Attempt.task_id.in_(node_tasks), Attempt.user_id.in_(
                select(User.id).where(User.class_id == klass.id, User.role == UserRole.STUDENT, User.is_active == True)
            ))
        )).first()
        total, correct = agg
        pct = round((correct or 0) / max(total or 1, 1) * 100, 1)
        mastery_out.append({"id": str(node.id), "title": node.title, "mastery": pct if total else None, "attempt_count": total or 0})

    return {"nodes": mastery_out}
