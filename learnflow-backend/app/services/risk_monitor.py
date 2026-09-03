"""风险监控服务 — 三级防护体系

🔴 红区 (INTERVENTION): 强制限锁/禁用 — 连续90min锁屏、日超3.5h禁用、夜间禁用
🟡 黄区 (WARNING): 提示式干预 — 重复知识点衰减、连错5题降速、跳过率>30%告警
🟢 绿区 (GUIDE): 健康引导 — 休息是学习的一部分、成就回顾淡化题数
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import List, Optional, Dict


class RiskLevel(int, Enum):
    NORMAL = 0
    WATCH = 1
    WARNING = 2
    INTERVENTION = 3


class ZoneLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class UsageSnapshot:
    user_id: str
    date: datetime
    total_minutes: float = 0.0
    relaxation_minutes: float = 0.0
    standard_minutes: float = 0.0
    night_minutes: float = 0.0
    total_attempts: int = 0
    correct_attempts: int = 0
    hard_task_ratio: float = 0.0
    skip_ratio: float = 0.0
    retry_ratio: float = 0.0
    help_others_count: int = 0
    repeated_skill_attempts: Dict[str, int] = field(default_factory=dict)
    consecutive_failures: int = 0
    self_reported_mood: Optional[float] = None


@dataclass
class RiskAssessment:
    level: RiskLevel
    zone: ZoneLevel = ZoneLevel.GREEN
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    needs_intervention: bool = False
    should_force_rest: bool = False
    should_switch_topic: bool = False
    should_reduce_difficulty: bool = False
    rest_minutes: int = 0


class RiskMonitor:
    DAILY_HOURS_YELLOW = 2.5
    DAILY_HOURS_RED = 3.5
    CONSECUTIVE_MINUTES_YELLOW = 60
    CONSECUTIVE_MINUTES_RED = 90
    NIGHT_USAGE_RATIO_YELLOW = 0.10
    NIGHT_USAGE_RATIO_RED = 0.20
    LOW_CHALLENGE_RATIO = 0.30
    SKIP_RATIO_YELLOW = 0.30
    SKIP_RATIO_RED = 0.50
    PERFORMANCE_DROP_DAYS = 3
    REPEATED_SKILL_LIMIT = 20
    CONSECUTIVE_FAILURE_LIMIT = 5
    NIGHT_HOURS_START = 22
    NIGHT_HOURS_END = 6

    @classmethod
    def assess(cls, snapshots: List[UsageSnapshot]) -> RiskAssessment:
        if not snapshots:
            return RiskAssessment(level=RiskLevel.NORMAL)

        assessment = RiskAssessment(level=RiskLevel.NORMAL)
        latest = snapshots[-1]

        # 红区: 日均使用超时
        recent = snapshots[-7:] if len(snapshots) >= 7 else snapshots
        avg_hours = sum(s.total_minutes for s in recent) / len(recent) / 60

        if avg_hours > cls.DAILY_HOURS_RED:
            assessment.level = RiskLevel.INTERVENTION
            assessment.zone = ZoneLevel.RED
            assessment.should_force_rest = True
            assessment.alerts.append(f"日均使用 {avg_hours:.1f}h，超过 {cls.DAILY_HOURS_RED}h 红线")
        elif avg_hours > cls.DAILY_HOURS_YELLOW:
            assessment.level = max(assessment.level, RiskLevel.WARNING)
            assessment.zone = ZoneLevel.YELLOW
            assessment.alerts.append(f"日均使用 {avg_hours:.1f}h，接近警戒线")

        # 红区: 夜间使用（基于最新快照的日期时间）
        if cls.is_night_time(latest.date) and not assessment.should_force_rest:
            assessment.level = max(assessment.level, RiskLevel.INTERVENTION)
            assessment.zone = ZoneLevel.RED
            assessment.should_force_rest = True
            assessment.alerts.append("当前为夜间时段 (22:00-06:00)")

        # 夜间使用占比
        night_ratio = latest.night_minutes / max(latest.total_minutes, 1)
        if night_ratio > cls.NIGHT_USAGE_RATIO_RED:
            assessment.level = max(assessment.level, RiskLevel.INTERVENTION)
            assessment.zone = ZoneLevel.RED
            assessment.alerts.append(f"夜间占比 {night_ratio:.0%}")
        elif night_ratio > cls.NIGHT_USAGE_RATIO_YELLOW:
            assessment.level = max(assessment.level, RiskLevel.WARNING)
            assessment.zone = max(assessment.zone, ZoneLevel.YELLOW)

        # 黄区: 重复知识点
        if latest.repeated_skill_attempts:
            max_repeat = max(latest.repeated_skill_attempts.values())
            if max_repeat >= cls.REPEATED_SKILL_LIMIT:
                assessment.should_switch_topic = True
                most = max(latest.repeated_skill_attempts, key=latest.repeated_skill_attempts.get)
                assessment.alerts.append(f"'{most}' 已练习 {max_repeat} 题，建议切换主题")

        # 黄区: 连错降速
        if latest.consecutive_failures >= cls.CONSECUTIVE_FAILURE_LIMIT:
            assessment.should_reduce_difficulty = True
            assessment.alerts.append(f"连续错误 {latest.consecutive_failures} 题，已自动降低难度")

        # 黄区: 挑战回避
        if latest.hard_task_ratio < cls.LOW_CHALLENGE_RATIO and latest.total_attempts > 10:
            assessment.alerts.append("高难度题选择率偏低，可能存在挑战回避")

        # 黄区: 跳过率
        if latest.skip_ratio > cls.SKIP_RATIO_RED:
            assessment.level = max(assessment.level, RiskLevel.WARNING)
            assessment.zone = max(assessment.zone, ZoneLevel.YELLOW)
            assessment.alerts.append(f"跳过率 {latest.skip_ratio:.0%}")
        elif latest.skip_ratio > cls.SKIP_RATIO_YELLOW:
            assessment.alerts.append(f"跳过率 {latest.skip_ratio:.0%}")

        if assessment.level >= RiskLevel.WARNING:
            assessment.needs_intervention = True

        return assessment

    @classmethod
    def check_consecutive_usage(cls, session_minutes: int) -> dict:
        if session_minutes >= cls.CONSECUTIVE_MINUTES_RED:
            return {"should_force_rest": True, "zone": "red", "message": f"已连续学习{session_minutes}分钟，需要休息", "rest_minutes": 10, "pet_message": "我累了，你也需要休息！"}
        elif session_minutes >= cls.CONSECUTIVE_MINUTES_YELLOW:
            return {"should_force_rest": False, "zone": "yellow", "message": f"已学{session_minutes}分钟，建议休息", "rest_minutes": 5, "pet_message": "休息5分钟？"}
        return {"should_force_rest": False, "zone": "green", "message": "", "rest_minutes": 0, "pet_message": ""}

    @classmethod
    def check_repeated_skill(cls, skill_attempts: Dict[str, int]) -> dict:
        if not skill_attempts:
            return {"should_switch": False, "most_repeated": "", "count": 0, "message": ""}
        most = max(skill_attempts, key=skill_attempts.get)
        count = skill_attempts[most]
        if count >= cls.REPEATED_SKILL_LIMIT:
            return {"should_switch": True, "most_repeated": most, "count": count, "message": f"'{most}' 已练{count}题，试试新知识？"}
        return {"should_switch": False, "most_repeated": most, "count": count, "message": ""}

    @classmethod
    def check_consecutive_failure(cls, failure_count: int) -> dict:
        if failure_count >= cls.CONSECUTIVE_FAILURE_LIMIT:
            return {"should_intervene": True, "should_reduce_difficulty": True, "message": f"连续错了{failure_count}题，看看讲解？", "pet_message": "错误是最好的老师，从基础巩固开始。"}
        return {"should_intervene": False, "should_reduce_difficulty": False, "message": ""}

    @classmethod
    def is_night_time(cls, now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now(UTC)
        return now.hour >= cls.NIGHT_HOURS_START or now.hour < cls.NIGHT_HOURS_END
