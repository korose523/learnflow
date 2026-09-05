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


# ══════════════════════════════════════════════════════════════
# 未成年保护合规引擎委托 (LF-M52)
#
# 历史缺陷（治理审计发现）：
#   机制注册表 mechanism_registry 把 LF-M52「未成年保护」的 impl_ref 指向
#   anti_addiction_compliance.MinorProtectionEngine，但生产代码中该引擎
#   **零调用方**——编排器只使用了本模块上方的粗粒度规则（25 分钟会话重置 +
#   未成年奖励冷却），导致：
#     (a) 注册表宣称 LF-M52 已落地，实际实现从未运行（审计可被证伪）；
#     (b) 运行中的实现缺少「每日时长上限」与「夜间禁用」两项合规硬要求。
#
# 修复方式：把本模块确立为未成年保护的**唯一对外门面**，对外暴露统一的
# minor_protection_decision()，内部委托 MinorProtectionEngine 执行配额校验。
# 本模块原有的粗粒度规则（变比率概率、奖励冷却）继续保留，与合规校验互补
# 而非重复——前者约束"奖励强度"，后者约束"使用时长"。
#
# 依赖项 anti_addiction_compliance 仅依赖标准库，不存在循环导入风险。
# ══════════════════════════════════════════════════════════════

from app.services.anti_addiction_compliance import (
    AgeGroup,
    MinorProtectionEngine,
    UsageQuota,
)

# 学段 → 合规年龄段。
# 依据：中国学制入学年龄与年级的常规对应关系。小学跨越 6–12 岁（同时覆盖
# AgeGroup.CHILD 的 <8 与 PRE_TEEN 的 8–13），此处按学段主体人群归入
# PRE_TEEN，其每日/连续上限已足够保守（见 MinorProtectionConfig）。
_GRADE_BAND_TO_AGE_GROUP = {
    GradeBand.PRIMARY.value: AgeGroup.PRE_TEEN,
    GradeBand.JUNIOR.value: AgeGroup.TEEN,
    GradeBand.SENIOR.value: AgeGroup.LATE_TEEN,
    GradeBand.OTHER.value: AgeGroup.ADULT,
}


def to_age_group(age_band: str) -> AgeGroup:
    """学段 → 合规年龄段。

    未知学段（OTHER / 空值）按 **成人** 处理，即不施加未成年限制。
    这是一个**保守方向的取舍**：宁可漏限，不可误限成年用户的正常使用。
    若未来 User 模型补充出生日期字段，应改用真实年龄而非学段推断。
    """
    return _GRADE_BAND_TO_AGE_GROUP.get(age_band, AgeGroup.ADULT)


def minor_protection_decision(
    user_id: str,
    age_band: str,
    daily_minutes: float = 0.0,
    consecutive_minutes: Optional[float] = None,
    now: Optional[datetime] = None,
) -> dict:
    """LF-M52 未成年保护合规决策——编排器访问未成年保护的唯一入口。

    委托 MinorProtectionEngine.check_session 执行三级检查：
      1. 夜间禁用（22:00–06:00）
      2. 每日时长上限（按年龄段分档）
      3. 连续学习上限（按年龄段分档，超限则要求强制休息）

    Args:
        user_id: 用户标识（用于构造 UsageQuota）
        age_band: 学段，取值见 GradeBand（由 infer_age_band 产出）
        daily_minutes: 当日已用学习分钟数
        consecutive_minutes: 连续学习分钟数。为 None 时以 daily_minutes 兜底
            —— 见下方「已知限制」。
        now: 当前时刻，可注入以便测试夜间时段（生产为 None → 取系统时间）

    Returns:
        {
            "age_band": str,          # 输入学段
            "age_group": str,         # 映射后的合规年龄段
            "is_minor": bool,         # 是否未成年保护对象
            "status": str,            # SessionStatus 值
            "should_block": bool,     # 是否应阻断后续投入型反馈
            "message": str,           # 面向用户的解释性文案（阻断时非空）
            "rest_minutes": int,      # 要求的休息时长
            "daily_limit": int,       # 该年龄段每日上限
            "consecutive_limit": int, # 该年龄段连续上限
            "daily_minutes_used": float,
            "consecutive_minutes_used": float,
        }

    已知限制（必须如实记录，不得在论文中隐去）：
        UsageQuota.consecutive_minutes 当前**没有真实的会话时钟**支撑。
        编排器的 risk_snapshot.total_minutes 是「当日累计估算」（当日答题数 × 3
        分钟/题），并非「自上次休息以来的连续时长」。因此当调用方不显式传入
        consecutive_minutes 时，此处以当日累计值兜底，会把「早读 20 分钟 + 晚读
        20 分钟」误判为「连续 40 分钟」，产生**假阳性**的强制休息要求。
        该偏差方向是保守的（宁可多要求休息），但不精确；引入真实会话时钟
        （记录 last_rest_at 并按会话计时）前，论文中不得声称已精确测量连续时长。
    """
    age_group = to_age_group(age_band)
    consecutive = float(
        consecutive_minutes if consecutive_minutes is not None else daily_minutes or 0.0
    )
    quota = UsageQuota(
        user_id=str(user_id),
        age_group=age_group,
        daily_minutes_used=float(daily_minutes or 0.0),
        consecutive_minutes=consecutive,
    )

    verdict = MinorProtectionEngine.check_session(quota, None, now)

    status = verdict.get("status")
    return {
        "age_band": age_band,
        "age_group": age_group.value,
        "is_minor": bool(MinorProtectionEngine.is_minor(age_group)),
        "status": status.value if hasattr(status, "value") else str(status),
        "should_block": bool(verdict.get("should_block", False)),
        "message": verdict.get("message", "") or "",
        "rest_minutes": int(verdict.get("rest_minutes", 0) or 0),
            "daily_limit": int(quota.daily_limit or 0),
            "consecutive_limit": int(quota.consecutive_limit or 0),
            "daily_minutes_used": round(float(daily_minutes or 0.0), 1),
            "consecutive_minutes_used": round(consecutive, 1),
            # 夜间时段标记：成年人不会被阻断，但上层可据此做温和提示
            "night_time": bool(verdict.get("night_time", False)),
            "daily_remaining": verdict.get("daily_remaining"),
    }
