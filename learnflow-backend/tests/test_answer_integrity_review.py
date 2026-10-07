import pytest
from pydantic import ValidationError
from app.api.student import AttemptRequest
from app.services.learning_orchestrator import LearningOrchestrator

@pytest.mark.parametrize('answer,expected,correct', [
    ('x = 7','7',True), ('７','7',True), ('7.0','7',True),
    ('1/2','0.5',True), ('-1/2','-0.5',True),
    ('7.0001','7',False), ('1/0','7',False), ('','',False),
    ('2+5','7',False), ('__import__("os")','7',False),
])
def test_server_answer_comparison(answer, expected, correct):
    assert LearningOrchestrator._compare_answer(answer, expected) is correct

def test_client_correctness_without_answer_is_rejected():
    with pytest.raises(ValidationError):
        AttemptRequest(task_id='item', correct=True, rt_ms=1000)

@pytest.mark.parametrize('target', [0.65, 0.75, 0.85, 0.95])
def test_target_success_is_a_parameter(target):
    from app.services.optimal_difficulty import FlowChannel, EloRating
    d = FlowChannel.optimal_difficulty_elo(1500, target_success=target)
    assert EloRating().expected_score(1500, d) == pytest.approx(target)

@pytest.mark.parametrize('target', [0, 1, -0.1, float('nan')])
def test_invalid_target_is_rejected(target):
    from app.services.optimal_difficulty import OptimalDifficultyEngine
    with pytest.raises(ValueError):
        OptimalDifficultyEngine(target_success=target)
