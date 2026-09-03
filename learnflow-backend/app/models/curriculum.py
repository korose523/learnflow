"""K12 课程模型：学科、年级、课标知识点、班级、作业

按 Spec §5 实现：subjects / grade_levels / curriculum_nodes / classes / assignments
- prerequisites 用 JSON 字段存储前备知识点依赖（self 引用 node id 列表）
- Class.teacher_id 关联 users.id（N:1）
"""
import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Text, Integer, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class GradeBand(str, Enum):
    """学段"""
    PRIMARY = "小学"      # 小学 (G1–G6)
    JUNIOR = "初中"       # 初中 (G7–G9)
    SENIOR = "高中"       # 高中 (G10–G12)
    OTHER = "其他"


class Subject(Base):
    """学科（数学/语文/英语/科学...）"""
    __tablename__ = "subjects"

    id = Column(String(36), primary_key=True, default=_new_id)
    name = Column(String(50), nullable=False)
    code = Column(String(20), nullable=False, unique=True, index=True)  # math/zh/en/science
    color = Column(String(20), nullable=True)   # 学科主题色 (#4F5BD5 等)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    nodes = relationship("CurriculumNode", back_populates="subject")


class GradeLevel(Base):
    """年级（K1–G12 结构化）"""
    __tablename__ = "grade_levels"

    id = Column(String(36), primary_key=True, default=_new_id)
    code = Column(String(10), nullable=False, unique=True, index=True)  # G1..G12
    label = Column(String(50), nullable=False)    # 一年级 / 七年级 / 高一
    band = Column(String(10), nullable=False, default=GradeBand.OTHER.value)  # 小学/初中/高中
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    nodes = relationship("CurriculumNode", back_populates="grade")
    classes = relationship("Class", back_populates="grade")


class CurriculumNode(Base):
    """课标知识点（含前备依赖）"""
    __tablename__ = "curriculum_nodes"

    id = Column(String(36), primary_key=True, default=_new_id)
    subject_id = Column(String(36), ForeignKey("subjects.id"), nullable=False, index=True)
    grade_id = Column(String(36), ForeignKey("grade_levels.id"), nullable=False, index=True)
    chapter = Column(String(100), nullable=True)   # 章节
    title = Column(String(200), nullable=False)    # 知识点标题
    prerequisites = Column(JSON, default=list)     # 前备知识点 node id 列表
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    subject = relationship("Subject", back_populates="nodes")
    grade = relationship("GradeLevel", back_populates="nodes")
    classes = relationship("Assignment", back_populates="node")

    @property
    def prerequisite_ids(self) -> List[str]:
        if not self.prerequisites:
            return []
        return [str(p) for p in self.prerequisites]


class Class(Base):
    """班级"""
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=_new_id)
    name = Column(String(100), nullable=False)
    grade_id = Column(String(36), ForeignKey("grade_levels.id"), nullable=True, index=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    grade = relationship("GradeLevel", back_populates="classes")
    assignments = relationship("Assignment", back_populates="klass")


class Assignment(Base):
    """教师布置的作业（关联到课标知识点）"""
    __tablename__ = "assignments"

    id = Column(String(36), primary_key=True, default=_new_id)
    class_id = Column(String(36), ForeignKey("classes.id"), nullable=False, index=True)
    node_id = Column(String(36), ForeignKey("curriculum_nodes.id"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    klass = relationship("Class", back_populates="assignments")
    node = relationship("CurriculumNode", back_populates="classes")

    __table_args__ = (
        UniqueConstraint("class_id", "node_id", name="uq_class_node"),
    )
