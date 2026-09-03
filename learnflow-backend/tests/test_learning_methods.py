"""学习方法论引擎测试"""
import pytest


class TestLearningMethodEngine:
    def test_loading_tip(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        tip = LearningMethodEngine.get_loading_tip("分数运算")
        assert "title" in tip
        assert "detail" in tip
        assert "分数运算" in tip["detail"]

    def test_post_question_correct(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        tip = LearningMethodEngine.get_post_question_tip("几何", True)
        assert "title" in tip
        assert tip["scene"] == "post_question"

    def test_post_question_incorrect(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        tip = LearningMethodEngine.get_post_question_tip("几何", False)
        assert "title" in tip
        assert tip["trigger"] == "incorrect"

    def test_reflection_trigger(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        result = LearningMethodEngine.get_reflection_trigger(5, "代数")
        assert result is not None
        assert len(result["questions"]) == 4

    def test_reflection_not_ready(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        result = LearningMethodEngine.get_reflection_trigger(2, "代数")
        assert result is None

    def test_daily_method_challenge(self):
        from app.services.learning_methods_engine import LearningMethodEngine
        challenge = LearningMethodEngine.get_daily_method_challenge("u1")
        assert "challenge_type" in challenge
        assert "title" in challenge
        assert challenge["xp_reward"] == 10


class TestMemoryPalaceEngine:
    def test_create_palace(self):
        from app.services.learning_methods_engine import MemoryPalaceEngine
        palace = MemoryPalaceEngine.create_palace("u1", 0)
        assert palace.name == "我的卧室"
        assert len(palace.locations) == 6

    def test_place_knowledge(self):
        from app.services.learning_methods_engine import MemoryPalaceEngine
        MemoryPalaceEngine.create_palace("u2", 0)
        result = MemoryPalaceEngine.place_knowledge("u2", "分数运算", "想象一个披萨被切成几块")
        assert result["placed"]
        assert "门口" in result["location"] or "书桌" in result["location"]

    def test_recall_walkthrough(self):
        from app.services.learning_methods_engine import MemoryPalaceEngine
        MemoryPalaceEngine.create_palace("u3", 0)
        MemoryPalaceEngine.place_knowledge("u3", "几何", "正方形和长方形的区别")
        result = MemoryPalaceEngine.recall_walkthrough("u3")
        assert result["has_palace"]
        assert result["total_knowledge_stored"] >= 1

    def test_no_palace(self):
        from app.services.learning_methods_engine import MemoryPalaceEngine
        result = MemoryPalaceEngine.recall_walkthrough("ghost_user")
        assert not result["has_palace"]


class TestMetacognitionDashboard:
    def test_learning_profile(self):
        from app.services.learning_methods_engine import MetacognitionDashboard
        profile = MetacognitionDashboard.generate_learning_profile({
            "best_time": "9:00",
            "avg_focus": 25,
            "pref_difficulty": 5,
            "methods_tried": ["active_recall", "feynman"],
            "method_performance": {"active_recall": 85, "feynman": 70},
        })
        assert profile["strongest_method"] == "active_recall"
        assert len(profile["methods_to_try"]) >= 1


class TestMethodQuizEngine:
    def test_generate_quiz(self):
        from app.services.learning_methods_engine import MethodQuizEngine
        quiz = MethodQuizEngine.generate_quiz("memory_palace")
        assert quiz is not None
        assert "question" in quiz

    def test_check_correct(self):
        from app.services.learning_methods_engine import MethodQuizEngine
        result = MethodQuizEngine.check_answer("memory_palace", 0)
        assert result["correct"]

    def test_check_incorrect(self):
        from app.services.learning_methods_engine import MethodQuizEngine
        result = MethodQuizEngine.check_answer("memory_palace", 1)
        assert not result["correct"]
