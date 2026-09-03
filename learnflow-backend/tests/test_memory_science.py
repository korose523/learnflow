"""记忆科学引擎测试"""
import pytest
from datetime import datetime, timedelta, UTC
from app.services.memory_science_engine import (
    FSRSMemoryState,
    FSRSSpacedRepetitionEngine,
    MemoryConsolidationEngine,
    MnemonicEngine,
    ConcreteExamplesEngine,
    DesirableDifficultiesOrchestrator,
    MemoryScienceOrchestrator,
)


class TestFSRS:
    def test_retrievability_formula(self):
        r = FSRSSpacedRepetitionEngine.retrievability(1.0, 1.0)
        assert 0.49 < r < 0.51  # 2^-1 = 0.5

    def test_recommended_interval_basic(self):
        interval = FSRSSpacedRepetitionEngine.recommended_interval(3.0, 5.0)
        assert interval > 0

    def test_update_after_review_easy(self):
        state = FSRSMemoryState(difficulty=5.0, stability=2.0)
        new_state = FSRSSpacedRepetitionEngine.update_after_review(state, 4)
        assert new_state.stability > state.stability
        assert new_state.difficulty < state.difficulty

    def test_update_after_review_again(self):
        state = FSRSMemoryState(difficulty=5.0, stability=10.0)
        new_state = FSRSSpacedRepetitionEngine.update_after_review(state, 1)
        assert new_state.stability < state.stability

    def test_schedule_next(self):
        state = FSRSMemoryState(difficulty=5.0, stability=1.0)
        plan = FSRSSpacedRepetitionEngine.schedule_next(state, 3)
        assert "next_review_date" in plan
        assert "next_interval_days" in plan


class TestMemoryConsolidation:
    def test_sleep_recommendation(self):
        advice = MemoryConsolidationEngine.get_sleep_recommendation()
        assert "睡眠" in advice["message"]
        assert advice["priority"] in ["high", "normal"]

    def test_exercise_recommendation(self):
        advice = MemoryConsolidationEngine.get_exercise_recommendation()
        assert "运动" in advice["message"]

    def test_consolidation_plan(self):
        plan = MemoryConsolidationEngine.consolidation_plan(["分数", "几何"])
        assert len(plan["plan"]) == 3
        assert plan["topics"] == ["分数", "几何"]


class TestMnemonic:
    def test_acronym(self):
        result = MnemonicEngine.acronym(["中国共产党", "人民共和国"])
        assert "acronym" in result

    def test_keyword_method(self):
        result = MnemonicEngine.keyword_method("apple", "苹果")
        assert "keyword" in result
        assert result["method"] == "关键词法"

    def test_peg_system(self):
        result = MnemonicEngine.peg_system(["牛顿", "爱因斯坦", "居里夫人"])
        assert len(result["associations"]) == 3


class TestConcreteExamples:
    def test_generate_example(self):
        result = ConcreteExamplesEngine.generate_example("函数", "math")
        assert result["concept"] == "函数"
        assert "example" in result

    def test_general_domain(self):
        result = ConcreteExamplesEngine.generate_example("正义", "general")
        assert result["domain"] == "general"


class TestDesirableDifficulties:
    def test_recommend_methods_low_mastery(self):
        result = DesirableDifficultiesOrchestrator.recommend_methods(
            mastery=0.2, days_since_last_review=2, correct_streak=0, error_rate=0.5
        )
        assert len(result["recommended"]) > 0

    def test_recommend_methods_high_mastery(self):
        result = DesirableDifficultiesOrchestrator.recommend_methods(
            mastery=0.9, days_since_last_review=1, correct_streak=6, error_rate=0.1
        )
        assert any("生成" in m["method"] or "间隔" in m["method"] for m in result["recommended"])

    def test_forgetting_curve_alert(self):
        alert = DesirableDifficultiesOrchestrator.forgetting_curve_alert(10.0, 1.0)
        assert alert["level"] == "strong"
        alert2 = DesirableDifficultiesOrchestrator.forgetting_curve_alert(1.0, 7.0)
        assert alert2["level"] == "weak"


class TestMemoryScienceOrchestrator:
    def test_get_review_plan(self):
        now = datetime.now(UTC)
        item_states = [
            {"id": "1", "concept": "分数", "difficulty": 5.0, "stability": 1.0, "review_count": 0, "last_review": now - timedelta(days=2)},
            {"id": "2", "concept": "几何", "difficulty": 4.0, "stability": 10.0, "review_count": 2, "last_review": now - timedelta(days=1)},
        ]
        plan = MemoryScienceOrchestrator.get_review_plan(item_states)
        assert "due_items" in plan
        assert "strong_items" in plan

    def test_generate_memory_aid(self):
        aid = MemoryScienceOrchestrator.generate_memory_aid("光合作用", "science")
        assert aid["concept"] == "光合作用"
        assert "concrete_example" in aid
        assert "mnemonic_acronym" in aid
