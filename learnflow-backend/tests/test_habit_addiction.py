"""习惯化成瘾引擎测试"""
import pytest
from app.services.habit_addiction_engine import (
    HabitStackingEngine,
    TemptationBundlingEngine,
    ImplementationIntentionsEngine,
    AutonomySupportEngine,
    SelfRegulationEngine,
    HabitAddictionOrchestrator,
)


class TestHabitStacking:
    def test_suggest_stack(self):
        result = HabitStackingEngine.suggest_stack({"preferred_anchor": "早餐后"})
        assert result["anchor"] == "早餐后"
        assert "stack_plan" in result

    def test_build_routine_chain(self):
        result = HabitStackingEngine.build_routine_chain(["早餐后", "晚饭后"])
        assert len(result["chain"]) == 2


class TestTemptationBundling:
    def test_suggest_bundle(self):
        result = TemptationBundlingEngine.suggest_bundle({})
        assert "reward" in result
        assert "rule" in result

    def test_custom_reward(self):
        result = TemptationBundlingEngine.suggest_bundle({"favorite_reward": "喝一杯奶茶"})
        assert "奶茶" in result["reward"]


class TestImplementationIntentions:
    def test_generate_if_then(self):
        result = ImplementationIntentionsEngine.generate_if_then()
        assert "if" in result
        assert "then" in result
        assert "plan" in result

    def test_custom_plan(self):
        result = ImplementationIntentionsEngine.generate_if_then(
            situation="感到不想学习时",
            response="我会先做 3 道题",
        )
        assert "感到不想学习时" in result["plan"]

    def test_setback_recovery(self):
        result = ImplementationIntentionsEngine.generate_setback_recovery_plan(
            trigger="忘记学习", fallback_action="立即完成 1 个微会话"
        )
        assert "忘记学习" in result["plan"]


class TestAutonomySupport:
    def test_provide_choice(self):
        result = AutonomySupportEngine.provide_choice(["数学", "英语", "物理"])
        assert len(result["choices"]) <= 3
        assert "数学" in result["choices"]

    def test_explain_rationale(self):
        result = AutonomySupportEngine.explain_rationale("复习", "巩固记忆")
        assert "巩固记忆" in result["reason"]

    def test_acknowledge_feelings(self):
        result = AutonomySupportEngine.acknowledge_feelings("焦虑")
        assert "焦虑" in result["message"]


class TestSelfRegulation:
    def test_set_goal(self):
        result = SelfRegulationEngine.set_goal("u1", "g1", "每天完成 10 道题", 10, "题", 7)
        assert result["goal"]["description"] == "每天完成 10 道题"

    def test_monitor_progress(self):
        SelfRegulationEngine.set_goal("u2", "g2", "完成 5 个微会话", 5, "个", 7)
        result = SelfRegulationEngine.monitor_progress("u2", "g2", 3)
        assert result["progress_pct"] == 60.0

    def test_monitor_progress_not_found(self):
        result = SelfRegulationEngine.monitor_progress("u999", "g999", 1)
        assert "error" in result

    def test_reflect_on_session(self):
        result = SelfRegulationEngine.reflect_on_session("u1", {"duration_min": 25, "questions_done": 10, "accuracy": 80})
        assert len(result["questions"]) == 4


class TestHabitAddictionOrchestrator:
    def test_build_personal_habit_plan(self):
        plan = HabitAddictionOrchestrator.build_personal_habit_plan({
            "topic_options": ["数学", "英语"]
        })
        assert "stack" in plan
        assert "bundle" in plan
        assert "if_then" in plan
        assert "recovery" in plan
