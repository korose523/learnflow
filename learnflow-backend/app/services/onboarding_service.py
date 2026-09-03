"""用户注册/初始化统一服务

为新注册或演示账号自动创建：
- 默认宠物（小豆 / 猫 / 四维 50）
- 默认技能画像（初始理解力/坚持力/创造力/协作力 50）
- 默认同意设置（relaxation_guide 为 True）
- 演示家长绑定（若适用）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.pet import PetProfile, PetBreed, PetMood
from app.models.task import StudentSkillProfile
from app.models.consent import ConsentRecord, ConsentType


class OnboardingService:
    """统一 onboarding 服务"""

    DEFAULT_PET_NAME = "小豆"
    DEFAULT_PET_BREED = PetBreed.CAT
    DEFAULT_DIMENSIONS = {
        "understanding": 50.0,
        "persistence": 50.0,
        "creativity": 50.0,
        "collaboration": 50.0,
    }

    DEFAULT_SKILLS = [
        "understanding", "persistence", "creativity", "collaboration",
        "主动回忆", "间隔重复", "精细复述", "生长型思维", "检索练习",
    ]

    @classmethod
    async def ensure_default_pet(cls, user: User, db: AsyncSession) -> PetProfile:
        """确保用户拥有默认宠物"""
        result = await db.execute(select(PetProfile).where(PetProfile.user_id == user.id))
        pet = result.scalar_one_or_none()
        if pet:
            return pet

        pet = PetProfile(
            user_id=user.id,
            name=cls.DEFAULT_PET_NAME,
            breed=cls.DEFAULT_PET_BREED,
            level=1,
            mood=PetMood.HAPPY,
            understanding=cls.DEFAULT_DIMENSIONS["understanding"],
            persistence=cls.DEFAULT_DIMENSIONS["persistence"],
            creativity=cls.DEFAULT_DIMENSIONS["creativity"],
            collaboration=cls.DEFAULT_DIMENSIONS["collaboration"],
            visuals_state={},
        )
        db.add(pet)
        await db.flush()
        await db.refresh(pet)
        return pet

    @classmethod
    async def ensure_default_skill_profile(cls, user: User, db: AsyncSession) -> None:
        """确保用户拥有默认技能画像"""
        for skill_dim in cls.DEFAULT_SKILLS:
            result = await db.execute(
                select(StudentSkillProfile).where(
                    StudentSkillProfile.user_id == user.id,
                    StudentSkillProfile.skill_dim == skill_dim,
                )
            )
            if result.scalar_one_or_none() is None:
                profile = StudentSkillProfile(
                    user_id=user.id,
                    skill_dim=skill_dim,
                    score=50.0,
                    confidence=0.5,
                    total_attempts=0,
                    correct_attempts=0,
                )
                db.add(profile)
        await db.flush()

    @classmethod
    async def ensure_default_consents(cls, user: User, db: AsyncSession) -> None:
        """确保用户拥有默认同意设置"""
        if not user.consents or not isinstance(user.consents, dict):
            user.consents = {}

        defaults = {
            "relaxation_guide": True,
            "eeg_integration": False,
            "data_research": False,
            "parent_binding": True,
        }
        changed = False
        for key, value in defaults.items():
            if key not in user.consents:
                user.consents[key] = value
                changed = True
                # 创建同意记录
                try:
                    record = ConsentRecord(
                        user_id=user.id,
                        consent_type=ConsentType(key),
                        granted_by=user.id,
                    )
                    db.add(record)
                except ValueError:
                    # 非枚举 key 忽略
                    pass

        if changed:
            await db.flush()

    @classmethod
    async def bind_demo_parent(cls, user: User, db: AsyncSession) -> User | None:
        """为演示账号绑定对应的默认家长账号（若存在）"""
        if user.role != UserRole.STUDENT:
            return None

        # 演示学生：student@learnflow.com -> parent_student@learnflow.com
        local = user.email.split("@")[0]
        parent_email = f"parent_{local}@learnflow.com"

        result = await db.execute(select(User).where(User.email == parent_email))
        parent = result.scalar_one_or_none()
        if parent is None:
            # 创建默认家长
            from app.core.security import hash_password
            parent = User(
                email=parent_email,
                hashed_password=hash_password("Parent123!"),
                name=f"{user.name}的家长",
                role=UserRole.PARENT,
                is_active=True,
            )
            db.add(parent)
            await db.flush()
            await db.refresh(parent)

        if user.parent_id != parent.id:
            user.parent_id = parent.id
            await db.flush()

        return parent

    @classmethod
    async def onboard(cls, user: User, db: AsyncSession) -> dict:
        """完整 onboarding 流程"""
        await cls.ensure_default_pet(user, db)
        await cls.ensure_default_skill_profile(user, db)
        await cls.ensure_default_consents(user, db)
        parent = await cls.bind_demo_parent(user, db)

        return {
            "user_id": str(user.id),
            "has_pet": True,
            "has_skill_profile": True,
            "has_default_consents": True,
            "parent_bound": parent is not None,
            "parent_id": str(parent.id) if parent else None,
        }
