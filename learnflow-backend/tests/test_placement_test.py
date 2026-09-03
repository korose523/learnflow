"""自适应水平测试系统测试"""
import pytest


class TestAdaptivePlacementEngine:
    def test_start_test(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        result = AdaptivePlacementEngine.start_test("u1")
        assert result["test_started"]
        assert result["total_questions"] == 10

    def test_get_next_question(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1")
        result = AdaptivePlacementEngine.get_next_question(state)
        assert not result["test_complete"]
        assert result["difficulty"] == 5
        assert result["question_number"] == 1

    def test_submit_correct_increases_difficulty(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1")
        result = AdaptivePlacementEngine.submit_answer(state, True)
        assert result["new_difficulty"] > 5

    def test_submit_incorrect_decreases_difficulty(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1")
        result = AdaptivePlacementEngine.submit_answer(state, False)
        assert result["new_difficulty"] < 5

    def test_convergence_detected(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1")
        # Submit 6 answers to pass MIN_QUESTIONS threshold + create alternating pattern
        AdaptivePlacementEngine.submit_answer(state, True)
        AdaptivePlacementEngine.submit_answer(state, False)
        AdaptivePlacementEngine.submit_answer(state, True)
        AdaptivePlacementEngine.submit_answer(state, False)
        AdaptivePlacementEngine.submit_answer(state, True)
        # After 5 submits: last_three=[True, False, True], q_idx=5
        # 6th submit to check convergence (q_idx becomes 6 >= MIN_QUESTIONS=6)
        result = AdaptivePlacementEngine.submit_answer(state, False)
        # last_three after: [True, False, True] → 67%, should converge
        assert state.converged

    def test_generate_result(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1")
        for _ in range(10):
            AdaptivePlacementEngine.submit_answer(state, True)
        result = AdaptivePlacementEngine.generate_result(state)
        assert result["test_completed"]
        assert "estimated_level" in result
        assert "topic_suggestions" in result

    def test_difficulty_bounds(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1", current_difficulty=10)
        # 答对应该保持10 (不变)
        result = AdaptivePlacementEngine.submit_answer(state, True)
        assert result["new_difficulty"] == 10

    def test_difficulty_bounds_low(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1", current_difficulty=1)
        result = AdaptivePlacementEngine.submit_answer(state, False)
        assert result["new_difficulty"] == 1

    def test_max_questions_enforced(self):
        from app.services.placement_test_engine import AdaptivePlacementEngine, PlacementState
        state = PlacementState(user_id="u1", current_question_index=12)
        result = AdaptivePlacementEngine.get_next_question(state)
        assert result["test_complete"]


class TestAdaptiveQuestionSelector:
    def test_select_initial_questions(self):
        from app.services.placement_test_engine import AdaptiveQuestionSelector
        placement = {
            "estimated_level": 6,
            "topic_suggestions": {
                "运算基础": 5, "逻辑推理": 6, "应用理解": 5, "数学思维": 7
            }
        }
        result = AdaptiveQuestionSelector.select_initial_questions(placement, 12)
        assert result["placement_level"] == 6
        assert result["dda_enabled"]


class TestPlacementTestGuide:
    def test_guide_step(self):
        from app.services.placement_test_engine import PlacementTestGuide
        step = PlacementTestGuide.get_placement_guide_step()
        assert step["step_id"] == "placement_test"
        assert "skip_option" in step
