"""多邻国式学习成瘾系统测试"""
import pytest
from datetime import datetime, UTC


class TestXPEngine:
    def test_award_xp_basic(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState, XPEventType
        state = XPState()
        result = XPEngine.award_xp(state, XPEventType.LESSON_COMPLETE, streak=0)
        assert result["xp_earned"] >= 10
        assert state.total_xp > 0

    def test_award_xp_with_streak(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState, XPEventType
        state = XPState()
        result = XPEngine.award_xp(state, XPEventType.LESSON_COMPLETE, streak=12)
        assert result["xp_earned"] >= 14

    def test_xp_boost(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState, XPEventType
        state = XPState()
        XPEngine.activate_boost(state, 15)
        result = XPEngine.award_xp(state, XPEventType.LESSON_COMPLETE, streak=0)
        assert result["xp_earned"] >= 20

    def test_level_up(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState, XPEventType
        state = XPState()
        state.total_xp = 95
        result = XPEngine.award_xp(state, XPEventType.LESSON_COMPLETE, streak=0)
        assert result["leveled_up"]

    def test_boost_tick(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState
        state = XPState(boost_remaining_minutes=1, current_boost_multiplier=2.0)
        XPEngine.tick_boost(state)
        assert state.boost_remaining_minutes == 0
        assert state.current_boost_multiplier == 1.0

    def test_no_boosts_left(self):
        from app.services.duolingo_addiction_engine import XPEngine, XPState
        state = XPState(boosts_available=0)
        result = XPEngine.activate_boost(state)
        assert not result["activated"]


class TestLeagueEngine:
    def test_standings(self):
        from app.services.duolingo_addiction_engine import LeagueEngine
        users = [("u1", "小明", 500), ("u2", "小红", 600), ("u3", "u3", 300), ("u4", "u4", 200)]
        result = LeagueEngine.get_league_standings("u1", 500, users)
        assert result["user_rank"] == 2

    def test_promotion(self):
        from app.services.duolingo_addiction_engine import LeagueEngine, LeagueState, LeagueTier
        state = LeagueState(current_tier=LeagueTier.BRONZE)
        result = LeagueEngine.process_weekly_promotion(state, 1, 10)
        assert result["promoted"]

    def test_no_promotion_mid_rank(self):
        from app.services.duolingo_addiction_engine import LeagueEngine, LeagueState, LeagueTier
        state = LeagueState(current_tier=LeagueTier.BRONZE)
        result = LeagueEngine.process_weekly_promotion(state, 5, 10)
        assert not result["promoted"]


class TestDuolingoStreakEngine:
    def test_check_in_first_time(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState
        state = DuolingoStreakState()
        result = DuolingoStreakEngine.check_in(state)
        assert result["streak"] == 1
        assert result["streak_updated"]

    def test_streak_freeze_used(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState
        from datetime import timedelta
        yesterday = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
        state = DuolingoStreakState(current_streak=7, streak_freezes_available=2,
                                     last_lesson_date=yesterday)
        result = DuolingoStreakEngine.check_in(state)
        assert result["streak"] == 8
        assert result["action"] == "frozen"
        assert not result.get("streak_frozen") is None

    def test_reminder_generation(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState
        state = DuolingoStreakState()
        reminder = DuolingoStreakEngine.generate_reminder(state)
        assert reminder is not None
        assert "消息" not in reminder.get("message", "")  # Not empty

    def test_fire_level(self):
        from app.services.duolingo_addiction_engine import DuolingoStreakEngine, DuolingoStreakState
        state = DuolingoStreakState(current_streak=19)  # 19→check_in→20
        state.last_lesson_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        result = DuolingoStreakEngine.check_in(state)
        assert result["fire_level"] == 3  # 20//10+1=3


class TestFriendQuestEngine:
    def test_create_quest(self):
        from app.services.duolingo_addiction_engine import FriendQuestEngine
        quest = FriendQuestEngine.create_quest("u1", "u2")
        assert len(quest.participants) == 2
        assert quest.goal_xp > 0

    def test_contribute_xp(self):
        from app.services.duolingo_addiction_engine import FriendQuestEngine, FriendQuest
        quest = FriendQuest(id="fq_test", participants=["u1", "u2"],
                             goal_xp=100, start_date="", end_date="")
        FriendQuestEngine.ACTIVE_QUESTS["fq_test"] = quest
        result = FriendQuestEngine.contribute_xp("fq_test", "u1", 50)
        assert result["contributed"]
        assert quest.current_xp == 50

    def test_quest_completion(self):
        from app.services.duolingo_addiction_engine import FriendQuestEngine, FriendQuest
        quest = FriendQuest(id="fq_comp", participants=["u1", "u2"],
                             goal_xp=50, start_date="", end_date="")
        FriendQuestEngine.ACTIVE_QUESTS["fq_comp"] = quest
        result = FriendQuestEngine.contribute_xp("fq_comp", "u1", 60)
        assert result["completed"]


class TestTimeBasedBonus:
    def test_returns_dict(self):
        from app.services.duolingo_addiction_engine import TimeBasedBonusEngine
        result = TimeBasedBonusEngine.check_time_bonus()
        assert "bonus_active" in result


class TestMonthlyChallenge:
    def test_get_challenge(self):
        from app.services.duolingo_addiction_engine import MonthlyChallengeEngine
        result = MonthlyChallengeEngine.get_current_challenge()
        assert "challenge" in result
        assert "days_left" in result

    def test_completion_check(self):
        from app.services.duolingo_addiction_engine import MonthlyChallengeEngine
        result = MonthlyChallengeEngine.check_completion("mc_xp", 5000)
        assert result["completed"]

    def test_incomplete(self):
        from app.services.duolingo_addiction_engine import MonthlyChallengeEngine
        result = MonthlyChallengeEngine.check_completion("mc_quests", 5)
        assert not result["completed"]
        assert result["remaining"] == 15


class TestNotificationEngine:
    def test_generate(self):
        from app.services.duolingo_addiction_engine import DuolingoNotificationEngine
        notif = DuolingoNotificationEngine.generate_notification("streak_reminder")
        assert notif is not None
        assert "title" in notif


class TestDailyXPGoal:
    def test_set_goal(self):
        from app.services.duolingo_addiction_engine import DailyXPGoalEngine
        result = DailyXPGoalEngine.set_goal("u1", 50)
        assert result["goal_set"]

    def test_completion(self):
        from app.services.duolingo_addiction_engine import DailyXPGoalEngine
        result = DailyXPGoalEngine.check_goal_completion(120, 100)
        assert result["completed"]

    def test_not_complete(self):
        from app.services.duolingo_addiction_engine import DailyXPGoalEngine
        result = DailyXPGoalEngine.check_goal_completion(30, 100)
        assert not result["completed"]
        assert result["remaining_xp"] == 70


from datetime import timedelta
