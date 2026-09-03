"""第二波新功能测试: 防沉迷合规 + 峰终/蔡格尼克/宜家/社会认同/自主"""
import pytest
from datetime import datetime, UTC, timedelta


# ─── 防沉迷合规 ───────────────────────────────────

class TestMinorProtectionEngine:
    def test_age_groups(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, AgeGroup
        assert MinorProtectionEngine.get_age_group(5) == AgeGroup.CHILD
        assert MinorProtectionEngine.get_age_group(10) == AgeGroup.PRE_TEEN
        assert MinorProtectionEngine.get_age_group(14) == AgeGroup.TEEN
        assert MinorProtectionEngine.get_age_group(17) == AgeGroup.LATE_TEEN
        assert MinorProtectionEngine.get_age_group(25) == AgeGroup.ADULT

    def test_daily_limits_by_age(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, AgeGroup
        assert MinorProtectionEngine.get_daily_limit(AgeGroup.CHILD) == 30
        assert MinorProtectionEngine.get_daily_limit(AgeGroup.PRE_TEEN) == 60
        assert MinorProtectionEngine.get_daily_limit(AgeGroup.TEEN) == 90
        assert MinorProtectionEngine.get_daily_limit(AgeGroup.LATE_TEEN) == 120

    def test_consecutive_limits_by_age(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, AgeGroup
        assert MinorProtectionEngine.get_consecutive_limit(AgeGroup.CHILD) == 20
        assert MinorProtectionEngine.get_consecutive_limit(AgeGroup.ADULT) == 90

    def test_is_minor(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, AgeGroup
        assert MinorProtectionEngine.is_minor(AgeGroup.CHILD)
        assert MinorProtectionEngine.is_minor(AgeGroup.TEEN)
        assert not MinorProtectionEngine.is_minor(AgeGroup.ADULT)

    def test_session_active(self):
        from app.services.anti_addiction_compliance import (
            MinorProtectionEngine, UsageQuota, AgeGroup, SessionStatus
        )
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.ADULT)
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        quota.today_date = day_time.strftime("%Y-%m-%d")
        # Monkey-patch _is_night_time
        orig = MinorProtectionEngine._is_night_time
        MinorProtectionEngine._is_night_time = lambda cfg, current_time=None: False
        try:
            result = MinorProtectionEngine.check_session(quota, current_time=day_time)
            assert result["status"] == SessionStatus.ACTIVE
        finally:
            MinorProtectionEngine._is_night_time = orig

    def test_daily_limit_reached(self):
        from app.services.anti_addiction_compliance import (
            MinorProtectionEngine, UsageQuota, AgeGroup, SessionStatus
        )
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.CHILD)
        quota.today_date = datetime(2026, 6, 20, 10, 0, tzinfo=UTC).strftime("%Y-%m-%d")
        quota.daily_minutes_used = 30
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        orig = MinorProtectionEngine._is_night_time
        MinorProtectionEngine._is_night_time = lambda cfg, current_time=None: False
        try:
            result = MinorProtectionEngine.check_session(quota, current_time=day_time)
            assert result["status"] == SessionStatus.DAILY_LIMIT_REACHED
        finally:
            MinorProtectionEngine._is_night_time = orig

    def test_rest_required(self):
        from app.services.anti_addiction_compliance import (
            MinorProtectionEngine, UsageQuota, AgeGroup, SessionStatus
        )
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.CHILD)
        quota.today_date = datetime(2026, 6, 20, 10, 0, tzinfo=UTC).strftime("%Y-%m-%d")
        quota.consecutive_minutes = 25  # > 20 for child
        day_time = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
        orig = MinorProtectionEngine._is_night_time
        MinorProtectionEngine._is_night_time = lambda cfg, current_time=None: False
        try:
            result = MinorProtectionEngine.check_session(quota, current_time=day_time)
            assert result["status"] == SessionStatus.REST_REQUIRED
            assert result["rest_minutes"] > 0
        finally:
            MinorProtectionEngine._is_night_time = orig

    def test_record_rest_resets_consecutive(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, UsageQuota, AgeGroup
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.CHILD)
        quota.consecutive_minutes = 25
        MinorProtectionEngine.record_rest(quota, 15)
        assert quota.consecutive_minutes == 0.0
        assert quota.total_rest_today == 15

    def test_record_usage_minute(self):
        from app.services.anti_addiction_compliance import MinorProtectionEngine, UsageQuota, AgeGroup
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.TEEN)
        MinorProtectionEngine.record_usage_minute(quota)
        assert quota.daily_minutes_used == 1.0
        assert quota.consecutive_minutes == 1.0

    def test_parent_custom_limit(self):
        from app.services.anti_addiction_compliance import (
            MinorProtectionEngine, MinorProtectionConfig, AgeGroup
        )
        config = MinorProtectionConfig(parent_managed=True, parent_custom_daily_limit=45)
        assert MinorProtectionEngine.get_daily_limit(AgeGroup.TEEN, config) == 45

    def test_parent_report(self):
        from app.services.anti_addiction_compliance import (
            MinorProtectionEngine, UsageQuota, AgeGroup
        )
        quota = UsageQuota(user_id="u1", age_group=AgeGroup.TEEN)
        quota.daily_minutes_used = 50
        quota.total_rest_today = 10
        report = MinorProtectionEngine.generate_parent_report(quota)
        assert report["daily_minutes_used"] == 50
        assert report["is_minor"] == True
        assert "recommendation" in report


# ─── 峰终定律 ─────────────────────────────────────

class TestPeakEndEngine:
    def test_empty_session(self):
        from app.services.gamification_service import PeakEndEngine
        result = PeakEndEngine.end_session("no_session")
        assert not result["has_session"]

    def test_full_session(self):
        from app.services.gamification_service import PeakEndEngine
        PeakEndEngine.start_session("u1")
        PeakEndEngine.record_answer("u1", True, "数学", 8, 6, "小豆")
        PeakEndEngine.record_answer("u1", False, "数学", 5, 0, "小豆")
        result = PeakEndEngine.end_session("u1", "小豆")
        assert result["has_session"]
        assert result["total_attempts"] == 2
        assert result["total_correct"] == 1
        assert "peak_moment" in result
        assert "accuracy" in result

    def test_peak_detection(self):
        from app.services.gamification_service import PeakEndEngine
        PeakEndEngine.start_session("u2")
        # 高难度答对但连对不高，应该记录难度峰值
        PeakEndEngine.record_answer("u2", True, "物理", 9, 2, "小豆")
        result = PeakEndEngine.end_session("u2")
        assert result["peak_score"] > 0
        # 弱断言: 至少有peak_moment
        assert len(result.get("peak_moment", "")) > 0


# ─── 蔡格尼克效应 ──────────────────────────────────

class TestZeigarnikEngine:
    def test_save_and_retrieve(self):
        from app.services.gamification_service import ZeigarnikEngine
        ZeigarnikEngine.save_unfinished("u1", "task_001", "分数运算", 5)
        reminder = ZeigarnikEngine.get_reminder("u1")
        assert reminder is not None
        assert reminder["has_unfinished"]
        assert "分数运算" in reminder["message"]

    def test_max_3_reminders(self):
        from app.services.gamification_service import ZeigarnikEngine, UnfinishedTask
        from datetime import datetime, timedelta, UTC
        task = UnfinishedTask(task_id="t1", topic="测试", difficulty=3,
                               started_at=datetime.now(UTC),
                               reminder_count=3,
                               last_reminded_at=datetime.now(UTC) - timedelta(hours=10))
        ZeigarnikEngine._unfinished.set("u_max", task)
        reminder = ZeigarnikEngine.get_reminder("u_max")
        assert reminder is None

    def test_clear_after_completion(self):
        from app.services.gamification_service import ZeigarnikEngine
        ZeigarnikEngine.save_unfinished("u_clr", "t_clear", "几何", 4)
        ZeigarnikEngine.clear_unfinished("u_clr", "t_clear")
        assert ZeigarnikEngine.get_reminder("u_clr") is None


# ─── 宜家效应 ─────────────────────────────────────

class TestIKEAEngine:
    def test_customize_pet_name(self):
        from app.services.gamification_service import IKEAEngine
        result = IKEAEngine.customize_pet_name("小豆", "闪电")
        assert "闪电" in result["message"]
        assert result["ownership_bonus"]

    def test_set_personal_goal(self):
        from app.services.gamification_service import IKEAEngine
        result = IKEAEngine.set_personal_goal(15)
        assert result["daily_target"] == 15
        assert "40%" in result["commitment_nudge"]

    def test_ownership_summary(self):
        from app.services.gamification_service import IKEAEngine, CustomizationState
        state = CustomizationState(pet_name_customized=True, learning_goal_set=True,
                                    daily_target_custom=20, custom_paths_created=2)
        summary = IKEAEngine.get_ownership_summary(state)
        assert summary["ownership_score"] >= 80
        assert "creator" in summary["level"]


# ─── 社会认同 ─────────────────────────────────────

class TestSocialProofEngine:
    def test_class_mastery_nudge_encourage(self):
        from app.services.gamification_service import SocialProofEngine
        result = SocialProofEngine.get_class_mastery_nudge("分数", 75, 50)
        assert result["type"] == "encourage"

    def test_class_mastery_nudge_pride(self):
        from app.services.gamification_service import SocialProofEngine
        result = SocialProofEngine.get_class_mastery_nudge("分数", 50, 75)
        assert result["type"] == "pride"

    def test_active_learners(self):
        from app.services.gamification_service import SocialProofEngine
        result = SocialProofEngine.get_active_learners_nudge(8)
        assert result["show"]

    def test_help_prompt(self):
        from app.services.gamification_service import SocialProofEngine
        result = SocialProofEngine.get_help_prompt("几何", 0)
        assert result["action"] == "offer_help"


# ─── 自主支持 ─────────────────────────────────────

class TestAutonomyEngine:
    def test_offer_choice_difficulty(self):
        from app.services.gamification_service import AutonomyEngine
        result = AutonomyEngine.offer_choice("difficulty")
        assert len(result["options"]) == 3
        assert "40%" in result["autonomy_msg"]

    def test_offer_choice_session(self):
        from app.services.gamification_service import AutonomyEngine
        result = AutonomyEngine.offer_choice("session_goal")
        assert len(result["options"]) == 4

    def test_provide_rationale_rest(self):
        from app.services.gamification_service import AutonomyEngine
        rationale = AutonomyEngine.provide_rationale("rest")
        assert "休息" in rationale

    def test_provide_rationale_unknown(self):
        from app.services.gamification_service import AutonomyEngine
        rationale = AutonomyEngine.provide_rationale("unknown_req")
        assert "更好" in rationale
