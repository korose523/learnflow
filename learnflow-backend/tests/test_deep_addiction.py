"""第四波: 深度行为上瘾引擎测试"""
import pytest


class TestCuriosityEngine:
    def test_generate_teaser_math(self):
        from app.services.deep_addiction_engine import CuriosityEngine
        result = CuriosityEngine.generate_teaser("math")
        assert "teaser" in result
        assert result["mechanism"] == "information_gap"

    def test_generate_teaser_general(self):
        from app.services.deep_addiction_engine import CuriosityEngine
        result = CuriosityEngine.generate_teaser("unknown_topic")
        assert "teaser" in result

    def test_generate_mystery_unlock(self):
        from app.services.deep_addiction_engine import CuriosityEngine
        result = CuriosityEngine.generate_mystery_unlock(["math"], ["science", "physics"])
        assert result["has_mystery"]

    def test_generate_mystery_no_locked(self):
        from app.services.deep_addiction_engine import CuriosityEngine
        result = CuriosityEngine.generate_mystery_unlock(["math", "science"], [])
        assert not result["has_mystery"]

    def test_generate_cliffhanger(self):
        from app.services.deep_addiction_engine import CuriosityEngine
        result = CuriosityEngine.generate_cliffhanger("代数", 5)
        assert "cliffhanger" in result
        assert result["urgency"] == "optional_but_curious"


class TestCollectionEngine:
    def test_first_badge(self):
        from app.services.deep_addiction_engine import CollectionEngine, CollectionState
        state = CollectionState()
        earned = CollectionEngine.check_and_award(state, "answer", {"total_attempts": 1})
        assert len(earned) >= 1
        assert earned[0]["id"] == "first_blood"

    def test_streak_badge(self):
        from app.services.deep_addiction_engine import CollectionEngine, CollectionState
        state = CollectionState()
        earned = CollectionEngine.check_and_award(state, "login", {"current_streak": 7})
        assert any(b["id"] == "streak_7" for b in earned)

    def test_no_duplicate_badges(self):
        from app.services.deep_addiction_engine import CollectionEngine, CollectionState
        state = CollectionState()
        CollectionEngine.check_and_award(state, "answer", {"total_attempts": 1})
        earned = CollectionEngine.check_and_award(state, "answer", {"total_attempts": 1})
        assert len(earned) == 0

    def test_collection_summary(self):
        from app.services.deep_addiction_engine import CollectionEngine, CollectionState
        state = CollectionState()
        state.badges_collected = ["first_blood"]
        summary = CollectionEngine.generate_collection_summary(state)
        assert summary["collected"] == 1
        assert summary["missing"] > 0
        assert len(summary["collection_nudge"]) > 0


class TestFOMOEngine:
    def test_get_active_challenges(self):
        from app.services.deep_addiction_engine import FOMOEngine
        challenges = FOMOEngine.get_active_challenges()
        # 至少应该有 daily challenge
        assert len(challenges) >= 1

    def test_fomo_nudge(self):
        from app.services.deep_addiction_engine import FOMOEngine
        from app.services.mechanism_registry import Effect, EffectType
        challenges = [{"name": "周末勇士", "desc": "双倍经验", "time_remaining": "本周末结束", "id": "w1"}]
        nudge = FOMOEngine.generate_fomo_nudge(challenges)
        assert isinstance(nudge, Effect)
        assert nudge.mechanism_id == "LF-M44"
        assert nudge.effect_type == EffectType.NUDGE
        assert nudge.direction == "approach"
        assert nudge.health_critical is False
        assert nudge.cost == 1.5
        assert nudge.payload["type"] == "fomo"
        assert nudge.payload["challenge_id"] == challenges[0]["id"]
        assert "周末勇士" in nudge.payload["message"]

    def test_no_fomo_when_empty(self):
        from app.services.deep_addiction_engine import FOMOEngine
        nudge = FOMOEngine.generate_fomo_nudge([])
        assert nudge is None

    def test_peer_progress_nudge(self):
        from app.services.deep_addiction_engine import FOMOEngine
        result = FOMOEngine.generate_peer_progress_nudge(
            {"peers_completed_today": 10, "user_completed_today": 5})
        assert "同学" in result["message"] or result["fomo_score"] == 0.0


class TestStreakSanctification:
    def test_milestone_day_7(self):
        from app.services.deep_addiction_engine import StreakSanctificationEngine
        result = StreakSanctificationEngine.get_daily_ritual(7)
        assert result["is_milestone"]
        assert "一周" in result["message"]

    def test_non_milestone_day(self):
        from app.services.deep_addiction_engine import StreakSanctificationEngine
        result = StreakSanctificationEngine.get_daily_ritual(5)
        assert not result["is_milestone"]

    def test_worship_message(self):
        from app.services.deep_addiction_engine import StreakSanctificationEngine
        msg = StreakSanctificationEngine.generate_streak_worship_message(100)
        assert "一部分" in msg


class TestAppointmentEngine:
    def test_create_appointment(self):
        from app.services.deep_addiction_engine import AppointmentEngine, AppointmentState
        state = AppointmentState()
        result = AppointmentEngine.create_appointment(state, "u1", "19:00", "代数", 30)
        assert "19:00" in result["message"]
        assert len(state.scheduled_sessions) == 1

    def test_get_upcoming(self):
        from app.services.deep_addiction_engine import AppointmentEngine, AppointmentState
        state = AppointmentState()
        AppointmentEngine.create_appointment(state, "u1", "20:00", "几何")
        upcoming = AppointmentEngine.get_upcoming_appointments(state)
        assert len(upcoming) == 1

    def test_mark_completed(self):
        from app.services.deep_addiction_engine import AppointmentEngine, AppointmentState
        state = AppointmentState()
        AppointmentEngine.create_appointment(state, "u1", "19:00", "代数")
        result = AppointmentEngine.mark_completed(state, "apt_1")
        assert "守信" in result["message"]

    def test_appointment_nudge(self):
        from app.services.deep_addiction_engine import AppointmentEngine, AppointmentState
        state = AppointmentState()
        AppointmentEngine.create_appointment(state, "u1", "20:00")
        nudge = AppointmentEngine.get_appointment_nudge(state)
        assert nudge is not None
        assert nudge["should_nudge"]


class TestScarcityEngine:
    def test_golden_question_unlock(self):
        from app.services.deep_addiction_engine import ScarcityEngine
        result = ScarcityEngine.check_unlock("golden_question", {"current_streak": 6})
        assert result["unlocked"]
        assert "黄金题目" in result["message"]

    def test_diamond_challenge_locked(self):
        from app.services.deep_addiction_engine import ScarcityEngine
        result = ScarcityEngine.check_unlock("diamond_challenge", {"mastery_pct": 50})
        assert not result["unlocked"]

    def test_daily_rarity_drop(self):
        from app.services.deep_addiction_engine import ScarcityEngine
        # 跑多次确保不崩溃
        for _ in range(20):
            result = ScarcityEngine.generate_daily_rarity_drop()
            assert "has_drop" in result


class TestSerendipityEngine:
    def test_roll_returns_dict(self):
        from app.services.deep_addiction_engine import SerendipityEngine
        result = SerendipityEngine.roll_serendipity()
        assert "triggered" in result

    def test_most_rolls_no_event(self):
        import random
        from app.services.deep_addiction_engine import SerendipityEngine
        random.seed(42)
        triggered = 0
        total = 50
        for _ in range(total):
            if SerendipityEngine.roll_serendipity()["triggered"]:
                triggered += 1
        random.seed()
        # ~6.5% chance total, 50 rolls → ~3 expected, within reason
        assert triggered <= 25  # should not trigger too often (statistical safety)
