"""成长系统与事件流模型

本模块修复三处「有引擎逻辑但状态不落库」的架构缺陷：

1. ``UserXPState``  — 修复 `learning_orchestrator.py` 中 XP / 等级 / 连胜
   每次请求从零构造、只写响应体从不落库的伪持久化缺陷。
2. ``SkillTreeState`` — 替代 `meta_learning_skilltree.PLAYER_SKILLS`
   进程内字典，16 项元学习技能熟练度重启即丢失。
3. ``LearningEvent`` — 研究用事件流。相比 `Attempt` 表补齐了会话 ID、
   展示/作答时间戳分离、跳过标记，并冻结每次难度决策的完整输入
   （``decision_snapshot``），使离线回放与因果归因成为可能。

字段命名与既有模型保持一致：主键为 36 位 UUID 字符串，
时间戳使用 UTC 且带索引。
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Float, Text, JSON, Boolean, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class UserXPState(Base):
    """用户 XP / 等级状态（修复 XP 伪持久化）

    字段与 ``duolingo_addiction_engine.XPState`` 一一对应，
    以便直接 ``XPState(**row)`` 构造与回写。
    """
    __tablename__ = "user_xp_state"

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False,
        unique=True, index=True,
    )
    total_xp = Column(Integer, nullable=False, default=0)
    weekly_xp = Column(Integer, nullable=False, default=0)
    today_xp = Column(Integer, nullable=False, default=0)
    current_boost_multiplier = Column(Float, nullable=False, default=1.0)
    boost_remaining_minutes = Column(Integer, nullable=False, default=0)
    boosts_available = Column(Integer, nullable=False, default=3)
    xp_level = Column(Integer, nullable=False, default=1)
    xp_to_next_level = Column(Integer, nullable=False, default=100)

    # 跨天/跨周重置依据与连胜（v1 中连胜为临时计算，同样不落库）
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(DateTime, nullable=True)   # 用于跨天重置 today_xp
    week_start_date = Column(DateTime, nullable=True)    # 用于跨周重置 weekly_xp

    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User")


class SkillTreeState(Base):
    """元学习技能树状态（替代内存字典 PLAYER_SKILLS）

    每个用户 × 每个技能一行，`meta_learning_skilltree.py`
    当前用 ``PLAYER_SKILLS: Dict[str, Dict[str, LearningSkill]]``
    驻留进程内存，进程重启即丢失全部熟练度与等级。
    """
    __tablename__ = "user_skill_tree"
    __table_args__ = (
        Index("ix_skill_tree_user_skill", "user_id", "skill_id", unique=True),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(String(64), nullable=False)      # 16 个技能之一
    proficiency = Column(Float, nullable=False, default=0.0)  # 0-100
    level = Column(Integer, nullable=False, default=1)
    total_uses = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class LearningEvent(Base):
    """学习事件流（研究核心表，只增不改）

    与 ``Attempt`` 的区别：
      - Attempt 是面向业务的窄表，由事件流投影而来；
      - LearningEvent 是只追加的原始事件流，承载研究所需全量上下文。

    ``decision_snapshot`` 是本表的关键设计：把每次难度决策的完整输入
    （θ、σ、各源难度、融合权重、所属 zone、机制开关、实验分组）冻结下来。
    没有它，任何离线回放、离策略评估与因果归因都无法进行——
    这是全部论文可复现性的地基。
    """
    __tablename__ = "learning_events"

    id = Column(String(36), primary_key=True, default=_new_id)
    # BIGSERIAL 在 SQLite/MySQL 下均可用自增整数替代，此处沿用项目 UUID 约定
    seq = Column(Integer, primary_key=True, autoincrement=True)

    event_type = Column(String(48), nullable=False, index=True)
    # TASK_PRESENTED / ANSWERED / SKIPPED / HINT_REQUESTED / SESSION_START / SESSION_END
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
    knowledge_point = Column(String(100), nullable=True, index=True)

    # —— 时间三元组（v1 完全缺失，学习分析必需）——
    presented_at = Column(DateTime, nullable=True)      # 题目展示时刻
    answered_at = Column(DateTime, nullable=True)       # 提交作答时刻
    thinking_ms = Column(Integer, nullable=True)        # 冗余存储，避免高频差值计算
    created_at = Column(DateTime, default=_now, nullable=False, index=True)

    # —— 作答结果 ——
    is_correct = Column(Boolean, nullable=True)
    answer_payload = Column(JSON, nullable=True)
    hints_used = Column(Integer, nullable=True)
    skipped = Column(Boolean, nullable=False, default=False)

    # —— 难度决策快照（可复现性关键）——
    # {theta, sigma, bkt_d, dda_d, optimal_d, fused_d, zone,
    #  mechanism_toggles, experiment_arm, model_version}
    decision_snapshot = Column(JSON, nullable=True)

    # —— 上下文 ——
    client_ctx = Column(JSON, nullable=True)            # 设备 / 时区 / 网络

    user = relationship("User")
    task = relationship("Task")
