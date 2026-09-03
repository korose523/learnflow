"""测试新增游戏化成瘾引擎 v3 和学习方法引擎 v3"""
import pytest
from app.services.addiction_engine_v3 import (
    LossAversionEngine, FreshStartEngine, ZeigarnikEngine,
    PeakEndRuleEngine, SurpriseDelightEngine,
)
from app.services.learning_methods_engine_v3 import (
    MindMappingEngine, DualCodingEngine, InterleavingEngine,
    ElaborationEngine, GenerationEffectEngine, LearningMethodOrchestratorV3,
)


class TestLossAversionEngine:
    def test_streak_shield_basic(self):
        result = LossAversionEngine.get_streak_shield({"streak": 7})
        assert result["shields_available"] == 1
        assert result["streak"] == 7

    def test_streak_shield_zero(self):
        result = LossAversionEngine.get_streak_shield({"streak": 3})
        assert result["shields_available"] == 0
        assert result["loss_if_broken"]["xp_loss"] == 30

    def test_streak_shield_multiple(self):
        result = LossAversionEngine.get_streak_shield({"streak": 21})
        assert result["shields_available"] == 3

    def test_sunk_cost_reminder(self):
        result = LossAversionEngine.get_sunk_cost_reminder(300, 15)
        assert result["total_time_invested"]["hours"] == 5.0
        assert result["total_time_invested"]["days"] == 15
        assert "milestone" in result


class TestFreshStartEngine:
    def test_fresh_start_check(self):
        result = FreshStartEngine.check_fresh_start()
        assert "is_fresh_start" in result
        assert "bonus_xp" in result

    def test_weekly_reset(self):
        result = FreshStartEngine.get_weekly_reset({"tasks": 15, "streak": True})
        assert result["this_week_goals"]["tasks_target"] == 20


class TestZeigarnikEngine:
    def test_incomplete_reminder(self):
        result = ZeigarnikEngine.get_incomplete_reminder(
            [{"id": "t1", "title": "未完成题目"}],
            [{"id": "c1", "title": "未完成章节"}]
        )
        assert result["incomplete_tasks_count"] == 1
        assert result["closure_bonus"] == 5

    def test_progress_bar_mid(self):
        result = ZeigarnikEngine.get_progress_bar(5, 10)
        assert result["percentage"] == 50.0

    def test_progress_bar_near_complete(self):
        result = ZeigarnikEngine.get_progress_bar(8, 10)
        assert result["percentage"] == 80.0
        assert result["completion_bonus"] > 0

    def test_progress_bar_empty(self):
        result = ZeigarnikEngine.get_progress_bar(0, 0)
        assert result["percentage"] == 0


class TestPeakEndRuleEngine:
    def test_session_end_summary(self):
        result = PeakEndRuleEngine.generate_session_end_summary({
            "fastest_answer_seconds": 15,
            "max_correct_streak": 6,
            "xp_earned": 120,
        })
        assert "peak_moments" in result
        assert "end_message" in result
        assert result["peak_xp_bonus"] > 0


class TestSurpriseDelightEngine:
    def test_roll_surprise(self):
        results = [SurpriseDelightEngine.roll_surprise() for _ in range(100)]
        triggered = [r for r in results if r["triggered"]]
        # 5% 概率，100次应有接近5次
        assert 0 <= len(triggered) <= 20

    def test_check_achievements_none(self):
        result = SurpriseDelightEngine.check_achievements({"current_streak": 3})
        assert isinstance(result, list)


class TestMindMappingEngine:
    def test_generate_knowledge_map(self):
        result = MindMappingEngine.generate_knowledge_map("数学", ["代数", "几何"])
        assert result["method"] == "思维导图"
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2

    def test_concept_bridge(self):
        result = MindMappingEngine.generate_concept_bridge("加法", "乘法")
        assert "加法" in result["prompt"]
        assert "乘法" in result["prompt"]


class TestDualCodingEngine:
    def test_visual_prompt(self):
        result = DualCodingEngine.get_visual_prompt("质数", "math")
        assert result["method"] == "双重编码"
        assert "visual_suggestion" in result

    def test_visual_card(self):
        result = DualCodingEngine.generate_visual_card("牛顿第二定律")
        assert "sketch_prompt" in result


class TestInterleavingEngine:
    def test_interleaved_plan(self):
        result = InterleavingEngine.generate_interleaved_plan(["代数", "几何", "三角"], 2)
        assert len(result["schedule"]) == 6

    def test_adaptive_interleave(self):
        result = InterleavingEngine.get_adaptive_interleave({"代数": 0.3, "几何": 0.8, "三角": 0.5})
        assert len(result["plan"]) > 0


class TestElaborationEngine:
    def test_elaboration_prompt(self):
        result = ElaborationEngine.get_elaboration_prompt("光合作用", 5)
        assert len(result["prompts"]) >= 2

    def test_generate_analogy(self):
        result = ElaborationEngine.generate_analogy("DNA")
        assert "analogy" in result


class TestGenerationEffectEngine:
    def test_fill_blank(self):
        result = GenerationEffectEngine.generate_fill_blank("牛顿发现了万有引力", ["牛顿", "万有引力"])
        assert "____" in result["masked"]

    def test_free_recall(self):
        result = GenerationEffectEngine.free_recall_prompt("细胞结构")
        assert "prompt" in result


class TestLearningMethodOrchestratorV3:
    def test_recommend_low_mastery(self):
        result = LearningMethodOrchestratorV3.recommend_for_mastery_level(0.2, "微积分", ["导数", "积分"])
        assert len(result["recommended_methods"]) > 0

    def test_recommend_high_mastery(self):
        result = LearningMethodOrchestratorV3.recommend_for_mastery_level(0.9, "微积分", ["导数", "积分"])
        assert len(result["recommended_methods"]) > 0

    def test_loading_tip(self):
        tip = LearningMethodOrchestratorV3.get_loading_tip()
        assert len(tip) > 10
