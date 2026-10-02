"""班级宠物园 API：积分养宠系统的班级聚合与师/班干部操作 (LF-M54)

真实「班级电子养宠」里，**宠物是每个学生专属的**，由学生本人认领、用行为积分
喂养；**班级宠物园**是聚合视图，由老师（或班干部）统一加减分、查看排行榜与
每周「喂养时间」仪式。本模块据此设计：

- ``GET /{class_id}/garden``      班级宠物园视图（学生/老师可见）：排行榜、形态
                                  分布、凝聚力、连接质量。
- ``GET /{class_id}/my-pet``     当前学生的专属宠物 + 形态阶段 + 是否「饿肚子」。
- ``POST /{class_id}/award``     老师给某学生加减分（行为积分 → 喂养其宠物）。
- ``POST /{class_id}/ritual``    老师触发/开关每周「喂养时间」仪式。
- ``GET /{class_id}/teacher``    老师视图：完整班级宠物园 + 逐生明细。

机制标识与路由挂载由 lead 在 main.py / mechanism_registry.py 统一接线。
"""
import logging
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User, UserRole
from app.models.class_pet import ClassPetGarden
from app.models.pet import PetProfile, PetMood
from app.services.class_pet_service import (
    ClassPetService,
    BehaviorPointEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/class-pet", tags=["班级宠物园"])


# ── 请求体 ───────────────────────────────────────────────
class AwardRequest(BaseModel):
    student_id: str
    points: float                     # 正=加分喂养，负=扣分饥饿
    behavior: str = "general"         # homework/participation/help/creativity/general
    reason: str = ""


class RitualRequest(BaseModel):
    enabled: Optional[bool] = True    # 是否开启每周仪式


# ── 内部 helper ─────────────────────────────────────────
async def _get_or_create_garden(db: AsyncSession, class_id: str) -> ClassPetGarden:
    res = await db.execute(select(ClassPetGarden).where(ClassPetGarden.class_id == class_id))
    garden = res.scalar_one_or_none()
    if garden is None:
        garden = ClassPetGarden(class_id=class_id)
        db.add(garden)
        await db.commit()
        await db.refresh(garden)
    return garden


async def _get_or_create_pet(db: AsyncSession, student_id: str) -> PetProfile:
    res = await db.execute(select(PetProfile).where(PetProfile.user_id == student_id))
    pet = res.scalar_one_or_none()
    if pet is None:
        pet = PetProfile(user_id=student_id)
        db.add(pet)
        await db.commit()
        await db.refresh(pet)
    return pet


async def _class_pets(db: AsyncSession, class_id: str) -> list:
    res = await db.execute(
        select(PetProfile)
        .join(User, PetProfile.user_id == User.id)
        .where(User.class_id == class_id)
    )
    return list(res.scalars().all())


def _cohesion_of(pets: list) -> float:
    if not pets:
        return 50.0
    return sum(p.collaboration for p in pets) / len(pets)


def _pet_summary(pet: PetProfile) -> dict:
    return {
        "pet_id": pet.id,
        "user_id": pet.user_id,
        "name": pet.name,
        "breed": pet.breed.value if pet.breed else None,
        "level": pet.level,
        "morphology_stage": ClassPetService.morphology_stage(pet.level),
        "morphology_label": ClassPetService.morphology_label(pet.level),
        "total_score": round(pet.total_score, 1),
        "dimensions": {
            "understanding": round(pet.understanding, 1),
            "persistence": round(pet.persistence, 1),
            "creativity": round(pet.creativity, 1),
            "collaboration": round(pet.collaboration, 1),
        },
        "mood": pet.mood.value,
        "starving": ClassPetService.starvation_risk(pet),
    }


# ── 路由 ────────────────────────────────────────────────
@router.get("/{class_id}/garden")
async def get_class_garden(
    class_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """班级宠物园视图：排行榜、形态分布、凝聚力、连接质量。"""
    garden = await _get_or_create_garden(db, class_id)
    pets = await _class_pets(db, class_id)
    cohesion = _cohesion_of(pets)
    return ClassPetService.build_garden_view(pets, class_id, cohesion)


@router.get("/{class_id}/my-pet")
async def get_my_pet(
    class_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """当前学生的专属宠物 + 形态阶段 + 是否「饿肚子」。"""
    pet = await _get_or_create_pet(db, user.id)
    summary = _pet_summary(pet)
    summary["class_id"] = class_id
    return summary


@router.post("/{class_id}/award")
async def award_points(
    class_id: str,
    body: AwardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """老师/班干部给某学生加减分（行为积分 → 喂养其专属宠物）。

    真实规则示例：背课文+10口粮、发言+5能量、助人+2、拾金不昧+5；违纪扣分。
    正分喂养升级进化，负分使宠物「饿肚子」（属性微降、情绪 tired）。
    """
    if user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可加减分")
    if body.points == 0:
        raise HTTPException(status_code=400, detail="points 不能为 0")

    pet = await _get_or_create_pet(db, body.student_id)
    event = BehaviorPointEvent(
        student_id=body.student_id,
        points=body.points,
        behavior=body.behavior,
        reason=body.reason,
        awarded_by=user.id,
    )
    ClassPetService.feed_pet_with_points(pet, event.points, event.behavior)
    await db.commit()
    await db.refresh(pet)
    summary = _pet_summary(pet)
    summary["award"] = {"points": body.points, "behavior": body.behavior, "reason": body.reason}
    return summary


@router.post("/{class_id}/ritual")
async def trigger_ritual(
    class_id: str,
    body: RitualRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """老师触发/开关每周「喂养时间」仪式。"""
    if user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可操作仪式")
    garden = await _get_or_create_garden(db, class_id)
    garden.weekly_ritual_enabled = body.enabled
    if body.enabled:
        garden.last_ritual_at = datetime.now(UTC)
    garden.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(garden)

    pets = await _class_pets(db, class_id)
    cohesion = _cohesion_of(pets)
    report = ClassPetService.class_weekly_report(pets, class_id, cohesion, garden.ritual_due)
    report["ritual_enabled"] = garden.weekly_ritual_enabled
    report["last_ritual_at"] = garden.last_ritual_at.isoformat() if garden.last_ritual_at else None
    return report


@router.get("/{class_id}/teacher")
async def get_class_garden_teacher(
    class_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """老师视图：完整班级宠物园 + 逐生宠物明细。"""
    if user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可访问")
    garden = await _get_or_create_garden(db, class_id)
    pets = await _class_pets(db, class_id)
    cohesion = _cohesion_of(pets)
    view = ClassPetService.build_garden_view(pets, class_id, cohesion)
    view["per_student"] = [_pet_summary(p) for p in pets]
    view["ritual_enabled"] = garden.weekly_ritual_enabled
    view["last_ritual_at"] = garden.last_ritual_at.isoformat() if garden.last_ritual_at else None
    view["ritual_due"] = garden.ritual_due
    return view
