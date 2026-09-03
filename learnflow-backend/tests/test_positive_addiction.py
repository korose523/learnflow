"""正向学习成瘾引擎测试 — Hook/习惯/身份/承诺/社交/即时满足/成长可视化"""
import pytest
from datetime import datetime, UTC, timedelta


class TestHookEngine:
    def test_trigger_external_pet(self):
        from app.services.positive_addiction_engine import HookEngine, HookState, TriggerType
        state = HookState(user_id="u1")
        result = HookEngine.trigger(state, TriggerType.EXTERNAL_PET)
        assert "小豆" in result["message"]
        assert state.current_phase == "triggered"
        assert state.trigger_count == 1

    def test_trigger_social_peer(self):
        from app.services.positive_addiction_engine import HookEngine, HookState, TriggerType
        state = HookState(user_id="u1")
        result = HookEngine.trigger(state, TriggerType.SOCIAL_PEER, {"peer_count": 5})
        assert "5位" in result["message"] or "同学" in result["message"]

    def test_action_reduces_friction(self):
        from app.services.positive_addiction_engine import HookEngine, HookState
        state = HookState(user_id="u1")
        result = HookEngine.action(state)
        assert result["action_taken"]
        assert "friction_reduction" in result

    def test_reward_correct_with_streak(self):
        from app.services.positive_addiction_engine import HookEngine, HookState
        state = HookState(user_id="u1")
        result = HookEngine.reward(state, True, 5, "小豆")
        assert "reward" in result
        assert result["dopamine_peak"] > 0.5

    def test_reward_incorrect_still_has_reward(self):
        from app.services.positive_addiction_engine import HookEngine, HookState
        state = HookState(user_id="u1")
        result = HookEngine.reward(state, False, 0, "小豆")
        assert "reward" in result

    def test_investment_builds_sunk_cost(self):
        from app.services.positive_addiction_engine import HookEngine, HookState
        state = HookState(user_id="u1")
        result = HookEngine.investment(state, "set_goal", {"goal": 10, "minutes": 5})
        assert len(result["investments"]) >= 1
        assert result["total_time_invested"] > 0

    def test_investment_streak_protection(self):
        from app.services.positive_addiction_engine import HookEngine, HookState
        state = HookState(user_id="u1")
        result = HookEngine.investment(state, "build_streak", {"streak": 10})
        assert result["investments"][0]["type"] == "streak_sunk_cost"

    def test_full_hook_cycle(self):
        from app.services.positive_addiction_engine import HookEngine, HookState, TriggerType
        state = HookState(user_id="u1")
        HookEngine.trigger(state, TriggerType.EXTERNAL_PET)
        assert state.current_phase == "triggered"
        HookEngine.action(state)
        assert state.current_phase == "acting"
        HookEngine.reward(state, True, 3, "小豆")
        assert state.current_phase == "rewarded"
        HookEngine.investment(state, "build_streak", {"streak": 3, "minutes": 15})
        assert state.total_loops_completed == 1


class TestHabitLoopEngine:
    def test_set_time_cue(self):
        from app.services.positive_addiction_engine import HabitLoopEngine, HabitState
        state = HabitState()
        result = HabitLoopEngine.set_habit_cue(state, "time", "19:00")
        assert "19:00" in result["implementation_intention"]

    def test_set_after_event_cue(self):
        from app.services.positive_addiction_engine import HabitLoopEngine, HabitState
        state = HabitState()
        result = HabitLoopEngine.set_habit_cue(state, "after_event", "吃完晚饭")
        assert "吃完晚饭" in result["implementation_intention"]

    def test_record_session_strengthens_habit(self):
        from app.services.positive_addiction_engine import HabitLoopEngine, HabitState
        state = HabitState()
        result = HabitLoopEngine.record_session(state)
        assert result["habit_strength"] > 0
        assert "phase" in result
        assert result["days_to_automation"] <= 66

    def test_habit_phases(self):
        from app.services.positive_addiction_engine import HabitLoopEngine, HabitState
        state = HabitState()
        state.total_days_learned = 70
        result = HabitLoopEngine.record_session(state)
        assert result["phase"] == "automated"


class TestIdentityEngine:
    def test_no_identity_yet(self):
        from app.services.positive_addiction_engine import IdentityEngine
        result = IdentityEngine.assess_identity({})
        assert "初学者" in result["identity"]

    def test_persistent_identity(self):
        from app.services.positive_addiction_engine import IdentityEngine
        result = IdentityEngine.assess_identity({"current_streak": 5})
        assert "坚持者" in result["identity"]

    def test_multiple_identities(self):
        from app.services.positive_addiction_engine import IdentityEngine
        result = IdentityEngine.assess_identity({
            "current_streak": 5, "topics_explored": 4,
            "failure_recovery": 6, "total_attempts": 60
        })
        assert result["identity_count"] >= 3

    def test_growth_mindset_nudge(self):
        from app.services.positive_addiction_engine import IdentityEngine
        result = IdentityEngine.assess_identity({"current_streak": 2})
        assert "growth_mindset_nudge" in result


class TestCommitmentEscalator:
    def test_first_commitment_offer(self):
        from app.services.positive_addiction_engine import CommitmentEscalator, CommitmentState
        state = CommitmentState()
        result = CommitmentEscalator.offer_next_commitment(state)
        assert result["has_next"]
        assert result["next_level"] == 1

    def test_accept_commitment(self):
        from app.services.positive_addiction_engine import CommitmentEscalator, CommitmentState
        state = CommitmentState()
        result = CommitmentEscalator.accept_commitment(state, 1, "daily_one", "每天1题")
        assert result["accepted"]
        assert state.commitment_level == 1
        assert "公开承诺" in result["public_commitment_message"]

    def test_celebrate_fulfillment(self):
        from app.services.positive_addiction_engine import CommitmentEscalator, CommitmentState
        state = CommitmentState()
        state.promises_made = ["每天1题"]
        result = CommitmentEscalator.celebrate_fulfillment(state)
        assert result["celebrated"]
        assert state.promises_kept == 1

    def test_full_ladder(self):
        from app.services.positive_addiction_engine import CommitmentEscalator, CommitmentState
        state = CommitmentState()
        for level in range(1, 6):
            result = CommitmentEscalator.offer_next_commitment(state)
            assert result["has_next"]
            state.commitment_level = level
        result = CommitmentEscalator.offer_next_commitment(state)
        assert not result["has_next"]


class TestSocialContagionEngine:
    def test_social_proof_moment(self):
        from app.services.positive_addiction_engine import SocialContagionEngine
        result = SocialContagionEngine.get_social_proof_moment(
            {"most_active_hour": "19:00", "most_improved_topic": "分数运算"}
        )
        assert result["has_social_context"]

    def test_friendly_competition_nudge_no_ranking(self):
        from app.services.positive_addiction_engine import SocialContagionEngine
        result = SocialContagionEngine.get_friendly_competition_nudge(
            {"streak": 3, "weekly_accuracy": 65},
            {"max_streak": 7, "class_avg_accuracy": 70, "active_peers": 8}
        )
        assert "growth_not_ranking" in result["focus"]

    def test_ripple_effect(self):
        from app.services.positive_addiction_engine import SocialContagionEngine
        result = SocialContagionEngine.get_ripple_effect_message(3)
        assert result["show"]
        assert "3" in result["message"]

    def test_ripple_effect_zero(self):
        from app.services.positive_addiction_engine import SocialContagionEngine
        result = SocialContagionEngine.get_ripple_effect_message(0)
        assert not result["show"]


class TestInstantGratificationEngine:
    def test_correct_instant_feedback(self):
        from app.services.positive_addiction_engine import InstantGratificationEngine
        result = InstantGratificationEngine.generate_instant_feedback(
            True, "分数运算", "小豆", streak=0, session_progress=0.5)
        assert len(result["phases"]) >= 3

    def test_correct_long_streak_feedback(self):
        from app.services.positive_addiction_engine import InstantGratificationEngine
        result = InstantGratificationEngine.generate_instant_feedback(
            True, "分数运算", "小豆", streak=7, session_progress=0.3)
        # 长连对应该有火苗动画
        has_fire = any(
            dim.get("icon") == "🔥"
            for phase in result["phases"]
            for dim in phase.get("dimensions", [])
        )
        assert has_fire

    def test_incorrect_gentle_feedback(self):
        from app.services.positive_addiction_engine import InstantGratificationEngine
        result = InstantGratificationEngine.generate_instant_feedback(
            False, "分数运算", "小豆", streak=0, session_progress=0.5)
        assert "gentle" in str(result["phases"][0]["animation"])

    def test_progress_pulse(self):
        from app.services.positive_addiction_engine import InstantGratificationEngine
        result = InstantGratificationEngine.generate_instant_feedback(
            True, "分数运算", "小豆", streak=0, session_progress=0.9)
        assert result.get("progress_pulse")


class TestProgressVisualizationEngine:
    def test_weekly_growth_report(self):
        from app.services.positive_addiction_engine import ProgressVisualizationEngine
        result = ProgressVisualizationEngine.generate_weekly_growth_report({
            "new_skills": 2, "weekly_questions": 35,
            "accuracy_trend": "up", "accuracy_improved": True,
            "new_topic_mastered": "几何", "hardest_solved": True,
            "hardest_difficulty": 9,
        })
        assert "identity_anchor" in result
        assert len(result["growth_moments"]) >= 2

    def test_knowledge_map(self):
        from app.services.positive_addiction_engine import ProgressVisualizationEngine
        result = ProgressVisualizationEngine.generate_knowledge_map({
            "分数运算": 0.9, "几何": 0.3, "代数": 0.5
        })
        assert result["total_skills"] == 3
        assert result["mastered"] >= 1
