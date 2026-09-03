"""任务与答题模型"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class Task(Base):
    """学习任务 / 题目"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=_new_id)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)          # 题目内容 (Markdown)
    content_type = Column(String(20), default="text")  # text, image, formula
    topic = Column(String(100), nullable=False, index=True)  # 知识点
    difficulty = Column(Integer, nullable=False, default=5)   # 1-10
    correct_answer = Column(Text, nullable=False)   # 正确答案
    explanation = Column(Text, nullable=True)        # 解析
    hint_levels = Column(JSON, nullable=True)        # 分层提示 ["提示1", "提示2", "提示3"]
    time_estimate = Column(Integer, default=120)     # 预计耗时 (秒)
    source = Column(String(100), default="system")   # system / teacher_upload
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_approved = Column(Boolean, default=False)
    curriculum_node_id = Column(String(36), ForeignKey("curriculum_nodes.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # 关系
    attempts = relationship("Attempt", back_populates="task")


class Attempt(Base):
    """答题记录"""
    __tablename__ = "attempts"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_spent = Column(Integer, nullable=True)  # 秒
    hints_used = Column(Integer, default=0)      # 使用了几层提示
    difficulty_at_time = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # 关系
    task = relationship("Task", back_populates="attempts")


class SpacedReview(Base):
    """间隔复习记录"""
    __tablename__ = "spaced_reviews"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    review_number = Column(Integer, default=1)       # 第几次复习
    scheduled_date = Column(DateTime, nullable=False) # 计划复习日期
    completed_date = Column(DateTime, nullable=True)  # 实际完成日期
    result = Column(Boolean, nullable=True)           # 复习结果
    next_interval_days = Column(Float, nullable=True)  # 下次间隔天数
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class StudentSkillProfile(Base):
    """学生能力画像"""
    __tablename__ = "student_skill_profiles"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    skill_dim = Column(String(100), nullable=False)   # 技能维度/知识点
    curriculum_node_id = Column(String(36), ForeignKey("curriculum_nodes.id"), nullable=True, index=True)  # 关联课标知识点
    score = Column(Float, default=50.0)               # 0-100
    confidence = Column(Float, default=0.5)           # 置信度 0-1
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    mastery = Column(Float, default=0.5)                # BKT 掌握概率 0-1
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # 关系
    user = relationship("User", back_populates="skill_profile")

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.correct_attempts / self.total_attempts
