"""K12 课标 API：学科/年级枚举、课标知识点树

按 Spec §4 实现：
- GET /k12/subjects
- GET /k12/curriculum?subject=&grade=
所有难度/奖励/风险决策写 AuditLog（此处为只读查询，不写审计）。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.curriculum import Subject, GradeLevel, CurriculumNode

router = APIRouter(prefix="/api/v1/k12", tags=["K12 课标"])


@router.get("/subjects")
async def list_subjects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学科 + 年级枚举（含学段 band）"""
    subjects = (await db.execute(select(Subject).order_by(Subject.code))).scalars().all()
    grades = (await db.execute(select(GradeLevel).order_by(GradeLevel.code))).scalars().all()

    return {
        "subjects": [
            {"id": str(s.id), "code": s.code, "name": s.name, "color": s.color}
            for s in subjects
        ],
        "grades": [
            {"id": str(g.id), "code": g.code, "label": g.label, "band": g.band}
            for g in grades
        ],
    }


@router.get("/curriculum")
async def get_curriculum(
    subject: str | None = Query(None, description="学科 code，如 math"),
    grade: str | None = Query(None, description="年级 code，如 G7"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """课标知识点树（含前备依赖 prerequisites）"""
    query = (
        select(CurriculumNode)
        .join(Subject, CurriculumNode.subject_id == Subject.id)
        .join(GradeLevel, CurriculumNode.grade_id == GradeLevel.id)
    )
    if subject:
        query = query.where(Subject.code == subject)
    if grade:
        query = query.where(GradeLevel.code == grade)
    query = query.order_by(GradeLevel.code, Subject.code, CurriculumNode.chapter, CurriculumNode.title)

    nodes = (await db.execute(query)).scalars().all()

    subjects_index = {
        str(s.id): s for s in (await db.execute(select(Subject))).scalars().all()
    }
    grades_index = {
        str(g.id): g for g in (await db.execute(select(GradeLevel))).scalars().all()
    }

    node_list = []
    for n in nodes:
        subj = subjects_index.get(str(n.subject_id))
        g = grades_index.get(str(n.grade_id))
        node_list.append({
            "id": str(n.id),
            "subject": {"code": subj.code, "name": subj.name, "color": subj.color} if subj else None,
            "grade": {"code": g.code, "label": g.label, "band": g.band} if g else None,
            "chapter": n.chapter,
            "title": n.title,
            "prerequisites": n.prerequisite_ids,
        })

    return {
        "subjects": [
            {"id": str(s.id), "code": s.code, "name": s.name, "color": s.color}
            for s in subjects_index.values()
        ],
        "nodes": node_list,
    }
