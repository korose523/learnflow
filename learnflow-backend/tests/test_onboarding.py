"""新手引导系统测试"""
import pytest


class TestOnboardingEngine:
    def test_student_onboarding_has_12_steps(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_onboarding("student")
        assert result["total_steps"] == 12

    def test_teacher_onboarding_has_10_steps(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_onboarding("teacher")
        assert result["total_steps"] == 10

    def test_parent_onboarding_has_8_steps(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_onboarding("parent")
        assert result["total_steps"] == 8

    def test_first_step_for_new_user(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_current_step("student", [])
        assert result["has_next"]
        assert result["step_id"] == "stu_welcome"
        assert result["order"] == 1

    def test_second_step_after_first_done(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_current_step("student", ["stu_welcome"])
        assert result["step_id"] == "stu_first_question"

    def test_complete_onboarding(self):
        from app.services.onboarding_engine import OnboardingEngine
        all_steps = ["stu_welcome", "stu_first_question", "stu_pet_birth",
                      "stu_feedback", "stu_streak", "stu_xp_and_level",
                      "stu_daily_goal", "stu_skills", "stu_league",
                      "stu_team", "stu_social", "stu_complete"]
        result = OnboardingEngine.get_current_step("student", all_steps)
        assert not result["has_next"]

    def test_complete_step_gives_reward(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.complete_step("student", "stu_first_question")
        assert result["completed"]
        assert result["xp_reward"] > 0

    def test_skip_onboarding(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.skip_onboarding("student")
        assert result["skipped"]

    def test_unknown_role_defaults_student(self):
        from app.services.onboarding_engine import OnboardingEngine
        result = OnboardingEngine.get_onboarding("unknown_role")
        assert result["total_steps"] == 12  # defaults to student


class TestContextualHelpEngine:
    def test_first_error_help(self):
        from app.services.onboarding_engine import ContextualHelpEngine
        help_info = ContextualHelpEngine.get_help_for_trigger("first_error")
        assert help_info is not None
        assert "讲解" in help_info["message"]

    def test_idle_help(self):
        from app.services.onboarding_engine import ContextualHelpEngine
        help_info = ContextualHelpEngine.get_help_for_trigger("idle_30s")
        assert help_info is not None
        assert help_info["icon"] == "🤔"


class TestFeatureDiscoveryEngine:
    def test_student_session_1(self):
        from app.services.onboarding_engine import FeatureDiscoveryEngine
        features = FeatureDiscoveryEngine.check_new_features("student", 1)
        assert any(f["feature"] == "pet_system" for f in features)

    def test_student_session_7(self):
        from app.services.onboarding_engine import FeatureDiscoveryEngine
        features = FeatureDiscoveryEngine.check_new_features("student", 7)
        assert any(f["feature"] == "league" for f in features)

    def test_teacher_session_2(self):
        from app.services.onboarding_engine import FeatureDiscoveryEngine
        features = FeatureDiscoveryEngine.check_new_features("teacher", 2)
        assert any(f["feature"] == "ai_analysis" for f in features)

    def test_no_features_at_wrong_count(self):
        from app.services.onboarding_engine import FeatureDiscoveryEngine
        features = FeatureDiscoveryEngine.check_new_features("student", 4)
        assert len(features) == 0
