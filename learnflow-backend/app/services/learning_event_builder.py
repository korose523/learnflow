"""学习事件构建器 —— 纯函数, 可单元测试, 无任何 I/O

把一次答题提交拆解为若干「埋点事件」(telemetry points)。每个事件是一个
kwargs 字典, 可直接用于 ``record_learning_event(db, **event)`` (除了 db 本身)。

设计目标 (论文可复现性):
  把难度/奖励/风险等「机制决策」与对应的「结果」冻结成决策快照
  (decision_snapshot), 第三方可独立重跑估计并比对报告值, 用于因果归因。
"""
from typing import Dict, List, Optional


def build_submission_events(
    user_id: str,
    session_id: str,
    task_id: str,
    is_correct: bool,
    *,
    risk_level: Optional[str] = None,
    xp_suppressed: bool = False,
    success_streak: int = 0,
    failure_streak: int = 0,
    method_skill: Optional[str] = None,
    decision_snapshot: Optional[dict] = None,
) -> List[Dict]:
    """构建一次提交对应的全部埋点事件。

    返回的事件列表 (telemetry points):
      - ``"attempt"``        总是返回, 携带 is_correct;
      - ``"risk_assessment"`` 仅当 risk_level 不为 None, 快照含 risk_level + xp_suppressed;
      - ``"xp_award"``       总是返回, 快照含 xp_suppressed + success_streak + failure_streak;
      - ``"method_xp"``      仅当 method_skill 不为 None。

    每个事件字典均含 ``user_id`` / ``session_id`` / ``task_id`` / ``event_type`` /
    ``decision_snapshot``, 且可直接解包给 ``record_learning_event`` (除 db 外)。

    该函数不触碰数据库、不打印, 纯可测试。
    """
    events: List[Dict] = []

    # 1. attempt —— 总是记录作答正确性
    events.append(
        {
            "event_type": "attempt",
            "user_id": user_id,
            "session_id": session_id,
            "task_id": task_id,
            "is_correct": is_correct,
            "decision_snapshot": decision_snapshot,
        }
    )

    # 2. risk_assessment —— 仅当存在风险等级 (每次提交都会评估, 但由调用方决定
    #    是否传入; None 表示未触发风险事件流)
    if risk_level is not None:
        events.append(
            {
                "event_type": "risk_assessment",
                "user_id": user_id,
                "session_id": session_id,
                "task_id": task_id,
                "decision_snapshot": {
                    "risk_level": risk_level,
                    "xp_suppressed": xp_suppressed,
                },
            }
        )

    # 3. xp_award —— 总是记录奖励发放与连胜 (用于因果归因: 奖励是否被抑制)
    events.append(
        {
            "event_type": "xp_award",
            "user_id": user_id,
            "session_id": session_id,
            "task_id": task_id,
            "decision_snapshot": {
                "xp_suppressed": xp_suppressed,
                "success_streak": success_streak,
                "failure_streak": failure_streak,
            },
        }
    )

    # 4. method_xp —— 仅当使用了某个学习方法技能
    if method_skill is not None:
        events.append(
            {
                "event_type": "method_xp",
                "user_id": user_id,
                "session_id": session_id,
                "task_id": task_id,
                "decision_snapshot": {
                    "method_skill": method_skill,
                },
            }
        )

    return events
