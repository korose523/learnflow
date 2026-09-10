"""用户模型：学生、教师、家长、管理员"""
import uuid
from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    grade = Column(String(20), nullable=True)  # 年级，如 "五年级"
    school_id = Column(String(50), nullable=True)
    class_id = Column(String(36), ForeignKey("classes.id"), nullable=True, index=True)  # 所属班级（班级宠物园聚合用）
    parent_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    consents = Column(JSON, default=lambda: dict())  # {"relaxation_guide": true, "eeg": false, ...}
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # 关系
    parent = relationship("User", remote_side=[id], backref="children")
    pet = relationship("PetProfile", back_populates="user", uselist=False)
    skill_profile = relationship("StudentSkillProfile", back_populates="user")

    def __init__(self, **kwargs):
        """确保 consents 默认值为空 dict"""
        kwargs.setdefault("consents", dict())
        super().__init__(**kwargs)

    def is_demo_parent_bound(self, candidate_email: str) -> bool:
        """判断候选邮箱是否为本账号的演示绑定家长/孩子"""
        # 学生 ↔ parent_student 邮箱
        if self.role == UserRole.STUDENT and candidate_email == f"parent_{self.email.split('@')[0]}@learnflow.com":
            return True
        # 反向：家长邮箱 parent_student 对应学生 student
        if self.role == UserRole.PARENT:
            local = self.email.split("@")[0]
            if local.startswith("parent_"):
                student_email = f"{local.replace('parent_', '')}@learnflow.com"
                if candidate_email == student_email:
                    return True
        return False

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"
