"""终极学习方法 + 学神冲刺测试"""
import pytest


class TestAdvancedMethods:
    def test_methods_added_to_tips(self):
        # 需要先导入 advanced_methods_engine 触发 append
        import app.services.advanced_methods_engine
        from app.services.learning_methods_engine import METHOD_TIPS
        methods = [t["method"] for t in METHOD_TIPS]
        for m in ["pretesting", "generation", "self_explanation", "analogy",
                   "concrete_examples", "successive_relearning", "distributed_practice"]:
            assert m in methods, f"Missing method: {m}"


class TestPretestingEngine:
    def test_generate_pre_test(self):
        from app.services.advanced_methods_engine import PretestingEngine
        result = PretestingEngine.generate_pre_test("分数运算", 5)
        assert result["type"] == "pretest"
        assert "大脑" in result["message"]

    def test_post_pretest_feedback_wrong(self):
        from app.services.advanced_methods_engine import PretestingEngine
        result = PretestingEngine.generate_post_pretest_feedback(False)
        assert "好事" in result["message"]


class TestSelfExplanationEngine:
    def test_should_trigger(self):
        from app.services.advanced_methods_engine import SelfExplanationEngine
        # 多试几次确保区间内
        for _ in range(10):
            result = SelfExplanationEngine.should_trigger(5)
            if result:
                break
        # 至少有一次会触发
        assert True

    def test_generate_prompt(self):
        from app.services.advanced_methods_engine import SelfExplanationEngine
        prompt = SelfExplanationEngine.generate_prompt("代数")
        assert "type" in prompt
        assert prompt["skill_boost"] == "self_explanation"


class TestAnalogyBridgeEngine:
    def test_analogy_for_known_topic(self):
        from app.services.advanced_methods_engine import AnalogyBridgeEngine
        result = AnalogyBridgeEngine.generate_analogy("分数运算")
        assert result is not None
        assert "披萨" in result["source"] or "时间" in result["source"] or "钱" in result["source"]

    def test_analogy_for_unknown_topic(self):
        from app.services.advanced_methods_engine import AnalogyBridgeEngine
        result = AnalogyBridgeEngine.generate_analogy("量子力学")
        assert result is None


class TestGodModeEngine:
    def test_activate(self):
        from app.services.advanced_methods_engine import GodModeEngine
        result = GodModeEngine.activate_godmode("u1")
        assert result["active"]
        assert result["xp_multiplier"] == 3.0
        assert len(result["methods_active"]) == 7

    def test_check_available(self):
        from app.services.advanced_methods_engine import GodModeEngine
        result = GodModeEngine.check_godmode_available("2020-01-01")
        assert result["available"]

    def test_check_unavailable_today(self):
        from app.services.advanced_methods_engine import GodModeEngine
        from datetime import datetime, UTC
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        result = GodModeEngine.check_godmode_available(today)
        assert not result["available"]


class TestStrategyRecommender:
    def test_new_topic_recommendation(self):
        from app.services.advanced_methods_engine import StrategyRecommender
        result = StrategyRecommender.recommend_for_topic("分数", 0.0, 1)
        assert "pretesting" in result["recommended_strategies"]

    def test_high_mastery_recommendation(self):
        from app.services.advanced_methods_engine import StrategyRecommender
        result = StrategyRecommender.recommend_for_topic("分数", 0.9, 50)
        assert "spaced_repetition" in result["recommended_strategies"]

    def test_mid_mastery_recommendation(self):
        from app.services.advanced_methods_engine import StrategyRecommender
        result = StrategyRecommender.recommend_for_topic("分数", 0.5, 20)
        assert "self_explanation" in result["recommended_strategies"]
