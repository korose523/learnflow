"""learning_event_builder 单元测试 —— 纯函数, 无 I/O 依赖"""
from app.services.learning_event_builder import build_submission_events


def test_build_submission_events_returns_four_points():
    """risk_level 与 method_skill 均提供 → 返回 4 个埋点 (attempt/risk_assessment/xp_award/method_xp)"""
    events = build_submission_events(
        user_id="u1",
        session_id="s1",
        task_id="t1",
        is_correct=True,
        risk_level="WARNING",
        xp_suppressed=False,
        success_streak=3,
        failure_streak=0,
        method_skill="retrieval_practice",
    )

    assert len(events) == 4
    types = {e["event_type"] for e in events}
    assert types == {"attempt", "risk_assessment", "xp_award", "method_xp"}

    for e in events:
        assert e["user_id"] == "u1"
        assert e["session_id"] == "s1"
        assert e["task_id"] == "t1"

    xp_award = [e for e in events if e["event_type"] == "xp_award"][0]
    assert xp_award["decision_snapshot"]["xp_suppressed"] is False


def test_build_submission_events_pure():
    """纯函数: 两次调用结果相等, 且不含任何 I/O 副作用 (仅校验结构)"""
    kwargs = dict(
        user_id="u1",
        session_id="s1",
        task_id="t1",
        is_correct=True,
        risk_level="WARNING",
        xp_suppressed=False,
        success_streak=2,
        failure_streak=1,
        method_skill="feynman",
        decision_snapshot={"is_correct": True, "risk_level": "WARNING"},
    )
    first = build_submission_events(**kwargs)
    second = build_submission_events(**kwargs)

    assert first == second
    # 结构完整性 (无 I/O 行为, 仅校验字段存在)
    assert all("event_type" in e and "user_id" in e for e in first)
    assert all("decision_snapshot" in e for e in first)


def test_build_submission_events_omits_optional():
    """risk_level=None 且 method_skill=None → 仅返回 attempt 与 xp_award 两个事件"""
    events = build_submission_events(
        user_id="u1",
        session_id="s1",
        task_id="t1",
        is_correct=False,
        risk_level=None,
        method_skill=None,
    )

    types = [e["event_type"] for e in events]
    assert types == ["attempt", "xp_award"]
