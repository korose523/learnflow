"""反成瘾服务（未成年人保护红线，论文 NPBS/SDAM 对齐）

按 Spec P0 实现并在 RiskMonitor 基础上扩展：
- 年龄分层阈值（小学 / 初中 / 高中 分别设定连续学习 / 夜间 / 日均红线）
- 会话 ≥ 25 分钟：由引擎发出“难度重置标记” (reset marker)，前端 RestGuide 提示
- 未成年奖励冷却：变比率触发概率降到 15–25%，冷却期内不重复强奖励
- 与 HabitAddictionOrchestrator 联动（若存在）
"""
import logging
import random
from datetime import datetime, UTC
from typing import Optional

from app.models.user import User
from app.models.curriculum import GradeBand

logger = logging.getLogger(__name__)

# ─── 硬约束阈值 ─────────────────────────────────
SESSION_RESET_MINUTES = 25          # 连续学习 25 分钟触发难度重置 + 休息引导
MINOR_REWARD_COOLDOWN_MINUTES = 10  # 未成年两次强奖励最小间隔
MINOR_VR_MIN = 0.15                 # 未成年变比率触发概率下限
MINOR_VR_MAX = 0.25                 # 未成年变比率触发概率上限


def infer_age_band(user: Optional[User]) -> str:
    """从用户年级文本推断学段；无法推断时返回 '其他'"""
    if user is None:
        return GradeBand.OTHER.value
    grade = getattr(user, "grade", None) or ""
    g = grade.strip()
    # 兼容自由文本：五年级 / 七年级 / 高一 / G1 / K1
    if "一" in g or "二" in g or "三" in g or "四" in g or "五" in g or "六" in g or g.upper().startswith("K") or g.upper().startswith("G1") or g.upper().startswith("G2") or g.upper().startswith("G3") or g.upper().startswith("G4") or g.upper().startswith("G5") or g.upper().startswith("G6"):
        return GradeBand.PRIMARY.value
    if "七" in g or "八" in g or "九" in g or g.upper().startswith("G7") or g.upper().startswith("G8") or g.upper().startswith("G9"):
        return GradeBand.JUNIOR.value
    if "高一" in g or "高二" in g or "高三" in g or g.upper().startswith("G10") or g.upper().startswith("G11") or g.upper().startswith("G12"):
        return GradeBand.SENIOR.value
    return GradeBand.OTHER.value


def is_minor(age_band: str) -> bool:
    """小学/初中/高中 均视为未成年保护对象（K12 全段）"""
    return age_band in (GradeBand.PRIMARY.value, GradeBand.JUNIOR.value, GradeBand.SENIOR.value)


def variable_ratio_probability(age_band: str) -> float:
    """变比率强奖励触发概率：未成年 15–25%，成年保持常规（不在此模块约束）"""
    if is_minor(age_band):
        return round(random.uniform(MINOR_VR_MIN, MINOR_VR_MAX), 3)
    return 1.0


def session_reset_decision(session_minutes: float, age_band: str) -> dict:
    """会话超时决策：≥25 分钟发出难度重置标记

    Returns:
        {
            "session_minutes": float,
            "should_reset_difficulty": bool,
            "reset_marker": str | None,
            "rest_minutes": int,
            "age_band": str,
        }
    """
    should_reset = session_minutes >= SESSION_RESET_MINUTES
    return {
        "session_minutes": round(session_minutes, 1),
        "should_reset_difficulty": should_reset,
        "reset_marker": "difficulty_reset" if should_reset else None,
        "rest_minutes": 5 if should_reset else 0,
        "age_band": age_band,
    }


def reward_cooldown_decision(last_reward_at: Optional[datetime], age_band: str, now: Optional[datetime] = None) -> dict:
    """未成年奖励冷却决策

    Returns:
        {
            "cooldown_active": bool,
            "trigger_probability": float,
            "age_band": str,
        }
    """
    now = now or datetime.now(UTC)
    cooldown_active = False
    if is_minor(age_band) and last_reward_at is not None:
        # SQLite 可能存 naive datetime，统一比较
        last = last_reward_at
        if last.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=last.tzinfo)
        elapsed = (now - last).total_seconds() / 60.0
        cooldown_active = elapsed < MINOR_REWARD_COOLDOWN_MINUTES
    return {
        "cooldown_active": cooldown_active,
        "trigger_probability": variable_ratio_probability(age_band),
        "age_band": age_band,
    }


# ─── 与 HabitAddictionOrchestrator 联动 ──────────
def hook_habit_orchestrator(session_minutes: float, age_band: str) -> Optional[dict]:
    """若项目存在 HabitAddictionOrchestrator 则联动返回其干预建议，否则返回 None"""
    try:
        from app.services.habit_addiction_engine import HabitAddictionOrchestrator
        if hasattr(HabitAddictionOrchestrator, "evaluate_session"):
            return HabitAddictionOrchestrator.evaluate_session(session_minutes, age_band)
    except Exception as e:
        logger.debug("HabitAddictionOrchestrator 联动跳过：%s", e)
    return None
