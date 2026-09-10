"""教师端 API：班级仪表盘、任务管理、AI建议、风险告警"""
from datetime import datetime, UTC
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.task import Task, Attempt, StudentSkillProfile
from app.models.pet import PetProfile
from app.models.consent import Alert
from app.services.teacher_ai_assistant import TeacherAIAssistant
from app.models.curriculum import Class, Assignment, CurriculumNode

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
    difficulty: int = 5
    correct_answer: str
    explanation: str | None = None
    hint_levels: list[str] | None = None
    time_estimate: int = 120


class AdjustDifficultyRequest(BaseModel):
    student_id: str
    new_difficulty: int


class BatchAdjustRequest(BaseModel):
    student_ids: List[str]
    difficulty_delta: int = 0


# ─── 班级仪表盘 ───────────────────────────────

@router.get("/classroom")
async def get_classroom(
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """教师班级仪表盘数据"""
    students_query = await db.execute(
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True)
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
    student_query = await db.execute(select(User).where(User.id == student_id))
    student = student_query.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

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
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True)
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
        .where(Alert.is_resolved == False)
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
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
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
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True)
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
        "active_today": sum(1 for a in all_attempts if a.created_at.strftime("%Y-%m-%d") == today),
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
    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

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

    stats = {
        "avg_mastery": avg_mastery,
        "skill_scores": skill_scores,
        "recent_accuracy": recent_accuracy_list,
        "current_streak": current_streak,
        "weekly_attempts": len(attempts),
        "avg_difficulty": sum(a.difficulty_at_time or 5 for a in attempts) / max(len(attempts), 1),
        "skip_ratio": 0.1,
        "help_others": 0,
        "hook_loops": len(attempts),
        "total_attempts": len(attempts),
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
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True)
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
    result = await db.execute(select(User).where(User.id == req.student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

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
        select(User).where(User.role == UserRole.STUDENT, User.is_active == True)
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
    node_ids: List[str]
    due_at: str | None = None  # ISO datetime


@k12_router.post("/assignments")
async def create_assignments(
    req: CreateAssignmentRequest,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """教师布置作业（班级 + 若干课标知识点 + 截止时间）"""
    klass = (await db.execute(select(Class).where(Class.id == req.class_id))).scalar_one_or_none()
    if not klass:
        raise HTTPException(status_code=404, detail="班级不存在")

    due_at = None
    if req.due_at:
        try:
            due_at = datetime.fromisoformat(req.due_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="due_at 格式应为 ISO datetime")

    created_ids = []
    for node_id in req.node_ids:
        node = (await db.execute(select(CurriculumNode).where(CurriculumNode.id == node_id))).scalar_one_or_none()
        if not node:
            continue
        assignment = Assignment(class_id=req.class_id, node_id=node_id, due_at=due_at)
        db.add(assignment)
        await db.flush()
        await db.refresh(assignment)
        created_ids.append(str(assignment.id))

    await db.flush()
    return {"assignment_id": created_ids[0] if created_ids else None, "created": len(created_ids)}


@k12_router.get("/assignments")
async def list_assignments(
    class_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """班级作业列表"""
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
                "due_at": a.due_at.isoformat() if a.due_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in assignments
        ]
    }


@k12_router.get("/class-mastery")
async def class_mastery(
    class_id: str,
    user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """班级掌握热力图（按知识点，基于该知识点下题目的答题正确率）"""
    klass = (await db.execute(select(Class).where(Class.id == class_id))).scalar_one_or_none()
    if not klass:
        raise HTTPException(status_code=404, detail="班级不存在")

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
            mastery_out.append({"id": str(node.id), "title": node.title, "mastery": 0.0})
            continue
        agg = (await db.execute(
            select(
                func.count(Attempt.id),
                func.sum(case((Attempt.is_correct == True, 1), else_=0)),
            ).where(Attempt.task_id.in_(node_tasks))
        )).first()
        total, correct = agg
        pct = round((correct or 0) / max(total or 1, 1) * 100, 1)
        mastery_out.append({"id": str(node.id), "title": node.title, "mastery": pct})

    return {"nodes": mastery_out}
