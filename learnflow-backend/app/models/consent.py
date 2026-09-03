"""同意记录与告警模型"""
import uuid
from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SAEnum, JSON, Text, Boolean

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class ConsentType(str, Enum):
    RELAXATION_GUIDE = "relaxation_guide"
    EEG_INTEGRATION = "eeg_integration"
    DATA_RESEARCH = "data_research"
    PARENT_BINDING = "parent_binding"


class ConsentRecord(Base):
    """同意记录"""
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    consent_type = Column(SAEnum(ConsentType), nullable=False)
    consented_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    revoked_at = Column(DateTime, nullable=True)
    granted_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # 家长授权
    ip_address = Column(String(45), nullable=True)
    extra_data = Column(JSON, default=dict)


class AlertType(str, Enum):
    USAGE_EXCESS = "usage_excess"           # 使用超时
    NIGHT_USAGE = "night_usage"             # 夜间使用
    PERFORMANCE_DROP = "performance_drop"   # 表现下降
    CONSECUTIVE_FAILURE = "consecutive_failure"  # 连续失败
    DISENGAGEMENT = "disengagement"         # 参与度下降


class AlertSeverity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class Alert(Base):
    """风险告警"""
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    alert_type = Column(SAEnum(AlertType), nullable=False)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.YELLOW)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    data_snapshot = Column(JSON, default=dict)  # 触发时的数据快照
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notified_teacher = Column(Boolean, default=False)
    notified_parent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class FeedbackScript(Base):
    """微反馈文案库"""
    __tablename__ = "feedback_scripts"

    id = Column(String(36), primary_key=True, default=_new_id)
    category = Column(String(50), nullable=False, index=True)  # correct, incorrect, encouragement, flow, rest, identity
    sub_category = Column(String(50), nullable=True)
    text = Column(Text, nullable=False)
    author = Column(String(100), default="system")
    reviewer = Column(String(100), nullable=True)
    review_status = Column(String(20), default="approved")  # draft, pending_review, approved, rejected
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    ab_test_group = Column(String(20), nullable=True)  # 用于 A/B 测试
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
