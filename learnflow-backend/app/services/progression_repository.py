"""成长系统仓储层 —— 把驻留内存的引擎状态接入数据库

修复两处伪持久化：
  1. XP / 等级 / 连胜：原先 `learning_orchestrator.py:409` 每次请求
     `XPState()` 从零构造，结果只写响应体，请求结束即归零。
  2. 元学习技能树：原先存于 `meta_learning_skilltree.PLAYER_SKILLS`
     进程内字典，重启即丢失。

同时提供研究事件流的写入接口（``record_learning_event``）。
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progression import UserXPState, SkillTreeState, LearningEvent
from app.services.duolingo_addiction_engine import XPState

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# XP / 等级状态
# ────────────────────────────────────────────────────────────

def _start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(now: datetime) -> datetime:
    """ISO 周：周一为一周之始"""
    sod = _start_of_day(now)
    return sod - timedelta(days=sod.weekday())


async def load_xp_state(db: AsyncSession, user_id: str) -> UserXPState:
    """读取用户 XP 状态；不存在则创建。

    同时处理跨天 / 跨周重置——这是 v1 从未实现的逻辑，
    因为状态根本不落库，也就无从判断"上次活跃是哪天"。
    """
    result = await db.execute(
        select(UserXPState).where(UserXPState.user_id == user_id)
    )
    row = result.scalar_one_or_none()

    if row is None:
        now = datetime.now(UTC)
        row = UserXPState(
            user_id=user_id,
            total_xp=0,
            weekly_xp=0,
            today_xp=0,
            current_boost_multiplier=1.0,
            boost_remaining_minutes=0,
            boosts_available=3,
            xp_level=1,
            xp_to_next_level=100,
            current_streak=0,
            longest_streak=0,
            last_active_date=now,
            week_start_date=_start_of_week(now),
        )
        db.add(row)
        await db.flush()
        return row

    # 跨天 / 跨周滚动重置
    now = datetime.now(UTC)
    sod, sow = _start_of_day(now), _start_of_week(now)

    if row.last_active_date is not None:
        last = row.last_active_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if last < sod:
            row.today_xp = 0
            logger.debug("XP daily reset for user %s", user_id)

    if row.week_start_date is not None:
        ws = row.week_start_date
        if ws.tzinfo is None:
            ws = ws.replace(tzinfo=UTC)
        if ws < sow:
            row.weekly_xp = 0
            row.week_start_date = sow
            logger.debug("XP weekly reset for user %s", user_id)

    row.last_active_date = now
    return row


def to_xp_state(row: UserXPState) -> XPState:
    """ORM 行 → 引擎所需的 XPState dataclass"""
    return XPState(
        total_xp=row.total_xp,
        weekly_xp=row.weekly_xp,
        today_xp=row.today_xp,
        current_boost_multiplier=row.current_boost_multiplier,
        boost_remaining_minutes=row.boost_remaining_minutes,
        boosts_available=row.boosts_available,
        xp_level=row.xp_level,
        xp_to_next_level=row.xp_to_next_level,
    )


async def save_xp_state(db: AsyncSession, row: UserXPState, xp: XPState) -> None:
    """把引擎计算后的 XPState 回写 ORM 行"""
    row.total_xp = xp.total_xp
    row.weekly_xp = xp.weekly_xp
    row.today_xp = xp.today_xp
    row.current_boost_multiplier = xp.current_boost_multiplier
    row.boost_remaining_minutes = xp.boost_remaining_minutes
    row.boosts_available = xp.boosts_available
    row.xp_level = xp.xp_level
    row.xp_to_next_level = xp.xp_to_next_level
    db.add(row)


# ────────────────────────────────────────────────────────────
# 元学习技能树
# ────────────────────────────────────────────────────────────

async def load_skill_tree(db: AsyncSession, user_id: str) -> Dict[str, Dict[str, Any]]:
    """读取用户技能树，返回 {skill_id: {proficiency, level, total_uses}}"""
    result = await db.execute(
        select(SkillTreeState).where(SkillTreeState.user_id == user_id)
    )
    return {
        row.skill_id: {
            "proficiency": row.proficiency,
            "level": row.level,
            "total_uses": row.total_uses,
        }
        for row in result.scalars().all()
    }


async def save_skill_tree(
    db: AsyncSession, user_id: str, skills: Dict[str, Dict[str, Any]]
) -> None:
    """增量回写技能树（upsert 语义）"""
    existing = await db.execute(
        select(SkillTreeState).where(SkillTreeState.user_id == user_id)
    )
    by_skill = {row.skill_id: row for row in existing.scalars().all()}

    for skill_id, data in skills.items():
        row = by_skill.get(skill_id)
        if row is None:
            row = SkillTreeState(user_id=user_id, skill_id=skill_id)
            db.add(row)
        row.proficiency = float(data.get("proficiency", 0.0))
        row.level = int(data.get("level", 1))
        row.total_uses = int(data.get("total_uses", 0))


# ────────────────────────────────────────────────────────────
# 研究事件流
# ────────────────────────────────────────────────────────────

async def record_learning_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: str,
    session_id: str,
    task_id: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    presented_at: Optional[datetime] = None,
    answered_at: Optional[datetime] = None,
    is_correct: Optional[bool] = None,
    answer_payload: Optional[dict] = None,
    hints_used: Optional[int] = None,
    skipped: bool = False,
    decision_snapshot: Optional[dict] = None,
    client_ctx: Optional[dict] = None,
) -> LearningEvent:
    """写入一条学习事件。

    ``decision_snapshot`` 应包含本次难度决策的完整输入，例如：:

        {
          "theta": 1523.4, "sigma": 88.2,
          "bkt_d": 6, "dda_d": 5, "optimal_d": 5.7, "fused_d": 6,
          "zone": "FLOW", "expected_success": 0.82,
          "mechanism_toggles": {"LF-M12": true},
          "experiment_arm": "control", "model_version": "v2.0-draft"
        }

    冻结这些输入后，第三方可独立重跑估计并比对报告值。
    """
    thinking_ms = None
    if presented_at is not None and answered_at is not None:
        delta = (answered_at - presented_at).total_seconds() * 1000
        thinking_ms = int(max(0, delta))

    event = LearningEvent(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        knowledge_point=knowledge_point,
        presented_at=presented_at,
        answered_at=answered_at,
        thinking_ms=thinking_ms,
        is_correct=is_correct,
        answer_payload=answer_payload,
        hints_used=hints_used,
        skipped=skipped,
        decision_snapshot=decision_snapshot,
        client_ctx=client_ctx,
    )
    db.add(event)
    return event


async def load_recent_events(
    db: AsyncSession, user_id: str, limit: int = 200
) -> List[LearningEvent]:
    """按时间倒序读取用户最近事件（离线分析用）"""
    result = await db.execute(
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id)
        .order_by(LearningEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
