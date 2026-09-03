"""宠物四维模型：反映学生学习维度的可视化画像

四个维度：
- understanding (理解力): 对概念的掌握深度
- persistence (坚持力): 面对困难的投入
- creativity (创造力): 能否提出独特解法
- collaboration (协作力): 与他人互助的能力
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from enum import Enum

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class PetBreed(str, Enum):
    """宠物品种"""
    CAT = "cat"
    DOG = "dog"
    RABBIT = "rabbit"
    OWL = "owl"
    DRAGON = "dragon"


class PetMood(str, Enum):
    """宠物情绪状态"""
    HAPPY = "happy"
    FOCUSED = "focused"
    TIRED = "tired"
    ENCOURAGING = "encouraging"
    CONFIDENT = "confident"
    CURIOUS = "curious"


class PetProfile(Base):
    """宠物画像 —— 学习维度的可视化镜像"""
    __tablename__ = "pet_profiles"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(50), default="小豆")
    breed = Column(SAEnum(PetBreed), nullable=False, default=PetBreed.CAT)
    level = Column(Integer, default=1)  # 1-10 级
    mood = Column(SAEnum(PetMood), default=PetMood.HAPPY)

    # 四维属性 (0-100)
    understanding = Column(Float, default=50.0)   # 理解力
    persistence = Column(Float, default=50.0)      # 坚持力
    creativity = Column(Float, default=50.0)        # 创造力
    collaboration = Column(Float, default=50.0)     # 协作力

    # 视觉状态 (JSON: 皮肤、装饰、特效等)
    visuals_state = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # 关系
    user = relationship("User", back_populates="pet")

    def __init__(self, **kwargs):
        """确保 Python 层也有合理的默认值（SQLAlchemy Column default 只在 INSERT 时生效）"""
        kwargs.setdefault("level", 1)
        kwargs.setdefault("mood", PetMood.HAPPY)
        super().__init__(**kwargs)

    @property
    def total_score(self) -> float:
        """综合评分"""
        return (self.understanding + self.persistence + self.creativity + self.collaboration) / 4

    @property
    def dominant_trait(self) -> str:
        """主导特质"""
        traits = {
            "understanding": self.understanding,
            "persistence": self.persistence,
            "creativity": self.creativity,
            "collaboration": self.collaboration,
        }
        return max(traits, key=traits.get)

    def get_level_progress(self) -> float:
        """当前等级进度百分比 (0-100)"""
        return (self.total_score % 10) * 10

    def __repr__(self):
        return f"<Pet {self.name} Lv.{self.level} ({self.breed})>"
