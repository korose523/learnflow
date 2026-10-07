"""Counterbalanced allocation and grading for an unvalidated research apparatus.

No ordinary orchestrator, reward, risk, health or AI feedback is invoked here.
The Elo model is an engineering specification, not validated learning evidence.
"""
import hashlib
import random
from datetime import datetime, UTC
from fastapi import HTTPException
from sqlalchemy import select, update
from app.models.research import ResearchStudy, ResearchParticipant, ResearchAllocation, ResearchSession, ResearchTrial

PHASES = ('pretest', 'practice', 'posttest', 'delayed')


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def now():
    return datetime.now(UTC)


def expected_success(ability, difficulty):
    exponent = max(-15., min(15., (difficulty - ability) / 400.))
    return 1. / (1. + 10. ** exponent)


def allocated_targets(seed, ordinal, n_topics, targets):
    """Each block of four participants balances every topic across four targets.

    Topic order is frozen in the protocol. Cyclic shifts balance within-subject
    conditions for four topics. The shuffle is local and reproducible.
    """
    n = len(targets)
    block, row = divmod(ordinal, n)
    rng = random.Random(hashlib.sha256(f'{seed}:{block}'.encode()).hexdigest())
    values = list(targets)
    rng.shuffle(values)
    row_order = list(range(n))
    rng.shuffle(row_order)
    return [values[(row_order[row] + topic) % n] for topic in range(n_topics)]


async def participant_for(db, study_id, user_id):
    study = await db.get(ResearchStudy, study_id)
    if study is None:
        raise HTTPException(404, '研究不存在')
    if study.status != 'active':
        raise HTTPException(409, '研究尚未开放')
    participant = (await db.execute(select(ResearchParticipant).where(
        ResearchParticipant.study_id == study_id,
        ResearchParticipant.user_id == user_id,
    ))).scalar_one_or_none()
    if participant is None or participant.withdrawn_at is not None:
        raise HTTPException(403, '需要有效的研究同意与参与记录')
    return study, participant


async def allocation_for(db, participant_id, topic):
    allocation = (await db.execute(select(ResearchAllocation).where(
        ResearchAllocation.participant_id == participant_id,
        ResearchAllocation.topic == topic,
    ))).scalar_one_or_none()
    if allocation is None:
        raise HTTPException(404, '主题未分配')
    return allocation


async def owned_session(db, session_id, user_id):
    # A write lock serializes issue/submit transactions on this session, including SQLite.
    await db.execute(update(ResearchSession).where(ResearchSession.id == session_id).values(revision=ResearchSession.revision + 1))
    session = await db.get(ResearchSession, session_id, populate_existing=True)
    if session is None:
        raise HTTPException(404, '会话不存在')
    participant = await db.get(ResearchParticipant, session.participant_id)
    if participant.user_id != user_id:
        raise HTTPException(403, '不可访问其他参与者的会话')
    study, participant = await participant_for(db, participant.study_id, user_id)
    return study, participant, session


async def session_progress(db, session):
    trials = (await db.execute(select(ResearchTrial).where(
        ResearchTrial.session_id == session.id
    ).order_by(ResearchTrial.issued_at, ResearchTrial.id))).scalars().all()
    answered = [t for t in trials if t.submitted_at is not None]
    return trials, answered
