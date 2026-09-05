"""学习节奏管理模块 — Quality > Quantity

基于中国《未成年人网络保护条例》并结合正向学习成瘾研究。
设计哲学: 所有限制用认知科学解释——休息是学习的一部分。
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Optional, Dict


class AgeGroup(str, Enum):
    CHILD = "child"             # 0-8岁
    PRE_TEEN = "pre_teen"       # 8-12岁
    TEEN = "teen"               # 13-15岁
    LATE_TEEN = "late_teen"     # 16-17岁
    ADULT = "adult"             # 18+


class SessionStatus(str, Enum):
    ACTIVE = "active"
    REST_REQUIRED = "rest_required"
    DAILY_LIMIT_REACHED = "daily_limit_reached"
    WEEKLY_LIMIT_REACHED = "weekly_limit_reached"
    NIGHT_BLOCKED = "night_blocked"


@dataclass
class MinorProtectionConfig:
    """未成年人保护配置——按年龄段差异化"""

    # 每日学习上限（分钟）
    daily_limit_child: int = 30       # 0-8岁: 30分钟
    daily_limit_pre_teen: int = 60    # 8-12岁: 60分钟
    daily_limit_teen: int = 90        # 13-15岁: 90分钟
    daily_limit_late_teen: int = 120  # 16-17岁: 120分钟
    daily_limit_adult: int = 210      # 18+: 3.5小时

    # 连续学习后强制休息（分钟）
    consecutive_limit_child: int = 20
    consecutive_limit_pre_teen: int = 30
    consecutive_limit_teen: int = 45
    consecutive_limit_late_teen: int = 60
    consecutive_limit_adult: int = 90

    # 强制休息时长（分钟）
    rest_duration_child: int = 15
    rest_duration_pre_teen: int = 10
    rest_duration_teen: int = 10
    rest_duration_late_teen: int = 5
    rest_duration_adult: int = 5

    # 夜间禁用时段
    #
    # 注意：这两个钟点是**本地时间**（《未成年人网络保护条例》语境下的北京时间），
    # 不是 UTC。换算由 night_timezone_offset 控制，见
    # MinorProtectionEngine._is_night_time。
    night_start: int = 22
    night_end: int = 6

    # 夜间时段判定的时区偏移（小时）。
    #
    # 默认 +8 即北京时间。服务内部时刻统一以 UTC 流转（datetime.now(UTC)），
    # 判定夜间前需先按此偏移换算到本地钟点，否则政策会被整体错位。
    night_timezone_offset: int = 8

    # 家长管控开关
    parent_managed: bool = False
    parent_custom_daily_limit: Optional[int] = None
    parent_custom_night_start: Optional[int] = None


@dataclass
class UsageQuota:
    """用户使用配额状态"""
    user_id: str
    age_group: AgeGroup
    today_date: str = ""
    daily_minutes_used: float = 0.0
    daily_limit: int = 0
    consecutive_minutes: float = 0.0
    consecutive_limit: int = 0
    last_rest_at: Optional[datetime] = None
    total_rest_today: int = 0
    session_status: SessionStatus = SessionStatus.ACTIVE


class MinorProtectionEngine:
    """未成年人保护引擎

    核心功能：
    1. 根据年龄自动调整限制参数
    2. 实时检查使用配额
    3. 提供家长管控接口
    """

    DEFAULT_CONFIG = MinorProtectionConfig()

    @classmethod
    def get_age_group(cls, age: int) -> AgeGroup:
        """根据年龄返回年龄段"""
        if age < 8:
            return AgeGroup.CHILD
        elif age < 13:
            return AgeGroup.PRE_TEEN
        elif age < 16:
            return AgeGroup.TEEN
        elif age < 18:
            return AgeGroup.LATE_TEEN
        return AgeGroup.ADULT

    @classmethod
    def get_daily_limit(cls, age_group: AgeGroup,
                         config: Optional[MinorProtectionConfig] = None) -> int:
        """获取每日学习上限"""
        cfg = config or cls.DEFAULT_CONFIG
        limits = {
            AgeGroup.CHILD: cfg.daily_limit_child,
            AgeGroup.PRE_TEEN: cfg.daily_limit_pre_teen,
            AgeGroup.TEEN: cfg.daily_limit_teen,
            AgeGroup.LATE_TEEN: cfg.daily_limit_late_teen,
            AgeGroup.ADULT: cfg.daily_limit_adult,
        }
        limit = limits.get(age_group, 210)
        if cfg.parent_managed and cfg.parent_custom_daily_limit:
            return cfg.parent_custom_daily_limit
        return limit

    @classmethod
    def get_consecutive_limit(cls, age_group: AgeGroup,
                               config: Optional[MinorProtectionConfig] = None) -> int:
        """获取连续学习上限"""
        cfg = config or cls.DEFAULT_CONFIG
        limits = {
            AgeGroup.CHILD: cfg.consecutive_limit_child,
            AgeGroup.PRE_TEEN: cfg.consecutive_limit_pre_teen,
            AgeGroup.TEEN: cfg.consecutive_limit_teen,
            AgeGroup.LATE_TEEN: cfg.consecutive_limit_late_teen,
            AgeGroup.ADULT: cfg.consecutive_limit_adult,
        }
        return limits.get(age_group, 90)

    @classmethod
    def get_rest_duration(cls, age_group: AgeGroup,
                           config: Optional[MinorProtectionConfig] = None) -> int:
        """获取强制休息时长"""
        cfg = config or cls.DEFAULT_CONFIG
        durations = {
            AgeGroup.CHILD: cfg.rest_duration_child,
            AgeGroup.PRE_TEEN: cfg.rest_duration_pre_teen,
            AgeGroup.TEEN: cfg.rest_duration_teen,
            AgeGroup.LATE_TEEN: cfg.rest_duration_late_teen,
            AgeGroup.ADULT: cfg.rest_duration_adult,
        }
        return durations.get(age_group, 5)

    @classmethod
    def check_session(cls, quota: UsageQuota,
                       config: Optional[MinorProtectionConfig] = None,
                       current_time: Optional[datetime] = None) -> dict:
        """实时检查会话状态

        Returns:
            dict with status, message, should_block, rest_minutes
        """
        cfg = config or cls.DEFAULT_CONFIG
        now = current_time or datetime.now(UTC)

        # 检查日期变化
        today = now.strftime("%Y-%m-%d")
        if quota.today_date != today:
            quota.today_date = today
            quota.daily_minutes_used = 0.0
            quota.total_rest_today = 0

        # 1. 夜间禁用检查
        #
        # 缺陷修复：原实现对本引擎的**全部**年龄段（含 ADULT）在 22:00-06:00
        # 一律返回 should_block=True。与本类的定位（《未成年人网络保护条例》、
        # 类名 MinorProtectionEngine、其余限额均按年龄段分档）不符，属越权阻断：
        # 成年学习者在夜间会被完全禁止学习。
        #
        # 现改为仅对未成年保护对象生效；成年人仍会在返回值中收到
        # night_time 标记，可供上层做温和提示（当前不阻断）。
        is_minor = cls.is_minor(quota.age_group)
        is_night = cls._is_night_time(cfg, now)
        if is_night and is_minor:
            return {
                "status": SessionStatus.NIGHT_BLOCKED,
                "message": "现在是休息时间（22:00-06:00）。明天再来学习吧，好的睡眠能帮你更好地记住知识！",
                "should_block": True,
                "rest_minutes": 0,
                "night_time": is_night,
                "is_minor": is_minor,
            }

        # 2. 每日上限检查
        daily_limit = cls.get_daily_limit(quota.age_group, cfg)
        quota.daily_limit = daily_limit
        if quota.daily_minutes_used >= daily_limit:
            quota.daily_minutes_used = daily_limit
            return {
                "status": SessionStatus.DAILY_LIMIT_REACHED,
                "message": f"今天的建议学习时间已用完（{daily_limit}分钟）。明天再来继续你的学习之旅！",
                "should_block": True,
                "rest_minutes": 0,
                "daily_remaining": 0,
                "daily_remaining_pct": 0,
                "night_time": is_night,
                "is_minor": is_minor,
            }

        # 3. 连续使用检查
        consecutive_limit = cls.get_consecutive_limit(quota.age_group, cfg)
        quota.consecutive_limit = consecutive_limit
        if quota.consecutive_minutes >= consecutive_limit:
            rest_minutes = cls.get_rest_duration(quota.age_group, cfg)
            return {
                "status": SessionStatus.REST_REQUIRED,
                "message": f"你已经连续学习了{int(quota.consecutive_minutes)}分钟。休息{rest_minutes}分钟吧，眼睛和大脑都需要放松！",
                "should_block": True,
                "rest_minutes": rest_minutes,
                "rest_activities": cls._get_rest_activities(),
                "night_time": is_night,
                "is_minor": is_minor,
            }

        return {
            "status": SessionStatus.ACTIVE,
            "message": "",
            "should_block": False,
            "rest_minutes": 0,
            "night_time": is_night,
            "is_minor": is_minor,
            "daily_remaining": daily_limit - quota.daily_minutes_used,
            "daily_remaining_pct": round((1 - quota.daily_minutes_used / daily_limit) * 100),
        }

    @classmethod
    def record_rest(cls, quota: UsageQuota, rest_minutes: int):
        """记录休息"""
        quota.consecutive_minutes = 0.0
        quota.last_rest_at = datetime.now(UTC)
        quota.total_rest_today += rest_minutes

    @classmethod
    def record_usage_minute(cls, quota: UsageQuota):
        """每学习1分钟调用一次"""
        quota.daily_minutes_used += 1.0
        quota.consecutive_minutes += 1.0

    @classmethod
    def is_minor(cls, age_group: AgeGroup) -> bool:
        """判断是否为未成年人"""
        return age_group != AgeGroup.ADULT

    @classmethod
    def _is_night_time(cls, config: MinorProtectionConfig, current_time: Optional[datetime] = None) -> bool:
        """夜间时段判定。

        缺陷修复 —— 原实现直接以 ``now.hour`` 与 ``night_start/night_end`` 比较，
        而 ``now`` 默认来自 ``datetime.now(UTC)``，即 **UTC 小时**；但
        ``night_start=22 / night_end=6`` 是《未成年人网络保护条例》语境下的
        **本地（北京时间）** 钟点。对 UTC+8 的中国用户，原实现的实际效果是：

            阻断 06:00–14:00（北京时间，上午/中午的正常学习时段），
            却在真正的深夜 22:00–06:00 放行。

        即政策被整体错位 8 小时，方向完全相反。这是本模块最严重的正确性缺陷。

        现按 ``config.night_timezone_offset`` 把 UTC 换算为本地小时后再比较。

        时刻约定：
            - ``current_time`` 为 timezone-aware → 先归一到 UTC，再施加偏移；
            - ``current_time`` 为 naive → 视为调用方已给本地时刻，直接使用其小时
              （向后兼容既有调用与测试）。
        """
        now = current_time or datetime.now(UTC)
        if now.tzinfo is not None:
            hour = (now.astimezone(UTC).hour + config.night_timezone_offset) % 24
        else:
            hour = now.hour
        start = config.parent_custom_night_start or config.night_start
        return hour >= start or hour < config.night_end

    @classmethod
    def _get_rest_activities(cls) -> list:
        """休息活动建议"""
        return [
            {"icon": "👀", "title": "远眺放松", "description": "看远处20秒以上"},
            {"icon": "🧘", "title": "深呼吸", "description": "吸气4秒、屏息4秒、呼气6秒"},
            {"icon": "🚶", "title": "站起来走走", "description": "活动一下身体"},
            {"icon": "💧", "title": "喝水", "description": "补充水分"},
        ]

    @classmethod
    def generate_parent_report(cls, quota: UsageQuota) -> dict:
        """生成家长报告"""
        return {
            "date": quota.today_date,
            "age_group": quota.age_group.value,
            "daily_minutes_used": quota.daily_minutes_used,
            "daily_limit": quota.daily_limit,
            "daily_remaining": max(0, quota.daily_limit - quota.daily_minutes_used),
            "total_rest_today": quota.total_rest_today,
            "is_minor": cls.is_minor(quota.age_group),
            "recommendation": cls._get_parent_recommendation(quota),
        }

    @classmethod
    def _get_parent_recommendation(cls, quota: UsageQuota) -> str:
        if quota.daily_minutes_used > quota.daily_limit * 0.8:
            return "今日学习已接近上限，建议明天继续"
        if quota.total_rest_today < 10 and quota.daily_minutes_used > 30:
            return "休息次数偏少，建议提醒孩子每学习一段就休息"
        return "使用状态良好"
