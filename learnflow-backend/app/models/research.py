"""Persisted research records, independent of gamification and ordinary attempts."""
import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, JSON, Boolean, UniqueConstraint
from app.core.database import Base


def new_id():
    return str(uuid.uuid4())


def now():
    return datetime.now(UTC)


class ResearchStudy(Base):
    __tablename__ = 'research_studies'
    id = Column(String(36), primary_key=True, default=new_id)
    title = Column(String(200), nullable=False)
    protocol_version = Column(String(80), nullable=False)
    protocol_hash = Column(String(64), nullable=False)
    consent_version = Column(String(80), nullable=False)
    consent_text = Column(Text, nullable=False)
    mode = Column(String(20), nullable=False, default='dry_run')
    status = Column(String(20), nullable=False, default='draft')
    approval_reference = Column(String(200), nullable=True)
    topics = Column(JSON, nullable=False)
    targets = Column(JSON, nullable=False)
    phase_counts = Column(JSON, nullable=False)
    practice_seconds = Column(Integer, nullable=False, default=600)
    delay_days = Column(Integer, nullable=False, default=7)
    allocation_seed = Column(String(64), nullable=False)
    allocation_cursor = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=now)


class ResearchItem(Base):
    __tablename__ = 'research_items'
    __table_args__ = (UniqueConstraint('study_id', 'task_id', name='uq_research_item_phase'),)
    id = Column(String(36), primary_key=True, default=new_id)
    study_id = Column(String(36), ForeignKey('research_studies.id'), nullable=False)
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    topic = Column(String(100), nullable=False)
    phase = Column(String(20), nullable=False)
    difficulty_elo = Column(Float, nullable=False)
    expert_reviewed = Column(Boolean, nullable=False, default=False)
    calibration_source = Column(String(200), nullable=True)


class ResearchParticipant(Base):
    __tablename__ = 'research_participants'
    __table_args__ = (UniqueConstraint('study_id', 'user_id', name='uq_research_participant'), UniqueConstraint('study_id', 'ordinal', name='uq_research_ordinal'))
    id = Column(String(36), primary_key=True, default=new_id)
    study_id = Column(String(36), ForeignKey('research_studies.id'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    ordinal = Column(Integer, nullable=False)
    consent_version = Column(String(80), nullable=False)
    consented_at = Column(DateTime, nullable=False, default=now)
    withdrawn_at = Column(DateTime, nullable=True)


class ResearchAllocation(Base):
    __tablename__ = 'research_allocations'
    __table_args__ = (UniqueConstraint('participant_id', 'topic', name='uq_research_allocation'),)
    id = Column(String(36), primary_key=True, default=new_id)
    participant_id = Column(String(36), ForeignKey('research_participants.id'), nullable=False)
    topic = Column(String(100), nullable=False)
    target_success = Column(Float, nullable=False)
    ability_elo = Column(Float, nullable=False, default=1500.)


class ResearchSession(Base):
    __tablename__ = 'research_sessions'
    __table_args__ = (UniqueConstraint('participant_id', 'topic', 'phase', name='uq_research_session'),)
    id = Column(String(36), primary_key=True, default=new_id)
    participant_id = Column(String(36), ForeignKey('research_participants.id'), nullable=False)
    topic = Column(String(100), nullable=False)
    phase = Column(String(20), nullable=False)
    revision = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False, default=now)
    completed_at = Column(DateTime, nullable=True)


class ResearchTrial(Base):
    __tablename__ = 'research_trials'
    __table_args__ = (UniqueConstraint('session_id', 'task_id', name='uq_research_trial'), UniqueConstraint('session_id', 'sequence', name='uq_research_sequence'))
    id = Column(String(36), primary_key=True, default=new_id)
    session_id = Column(String(36), ForeignKey('research_sessions.id'), nullable=False)
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    sequence = Column(Integer, nullable=False)
    predicted_success = Column(Float, nullable=False)
    ability_before = Column(Float, nullable=False)
    item_difficulty_elo = Column(Float, nullable=False)
    issued_at = Column(DateTime, nullable=False, default=now)
    submitted_at = Column(DateTime, nullable=True)
    answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    response_ms = Column(Integer, nullable=True)
    server_elapsed_ms = Column(Integer, nullable=True)
