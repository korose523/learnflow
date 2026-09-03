"""能力估计持久化 + 决策审计日志

按 Spec §5 / P0 / P2 实现：
- AbilityEstimate: 学生能力 (theta/sigma) 落库，next-task 优先读库、过期才重算
- AuditLog: 所有难度/奖励/风险决策写审计（未成年人保护硬约束）
"""
import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Float, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class AuditKind(str, Enum):
    DIFFICULTY = "difficulty"
    REWARD = "reward"
    RISK = "risk"


class AbilityEstimate(Base):
    """学生能力估计（Elo 风格 theta/sigma），与 User 1:1"""
    __tablename__ = "ability_estimates"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    theta = Column(Float, nullable=False, default=1500.0)   # 能力分
    sigma = Column(Float, nullable=False, default=350.0)    # 不确定性 (Glicko RD)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))

    user = relationship("User")


class AuditLog(Base):
    """决策审计日志：所有难度/奖励/风险决策必须落库"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    kind = Column(SAEnum(AuditKind), nullable=False, index=True)
    input_json = Column(JSON, default=dict)     # 决策输入
    output_json = Column(JSON, default=dict)    # 决策输出
    subject = Column(String(50), nullable=True)  # 学科
    age_band = Column(String(10), nullable=True)  # 学段 (小学/初中/高中)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)

    user = relationship("User")
