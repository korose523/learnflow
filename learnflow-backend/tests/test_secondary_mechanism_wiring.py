"""步骤 13 孤儿机制评估钩子测试 (28 机制接编排器)

* test_scan_all_53_mechanisms_landed
    —— 审计矩阵必须 53/53 全落地 (orphan=0), 这是接线的验收指标
* test_evaluation_returns_all_28_with_real_outputs
    —— 评估钩子默认全开时返回 28 个键, 每个都是真实引擎输出且无 error
* test_gate_suppresses_evaluation
    —— is_enabled(False) 关闭后该机制跳过评估 (output=None), 消融对照成立
* test_process_submission_includes_evaluations
    —— 集成: process_submission 响应携带 mechanism_evaluations (28 键),
      且 XP/主流程行为不受影响
"""
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
import app.models  # noqa: F401  (确保全部表注册到 Base.metadata)
from app.models.user import User, UserRole
from app.models.task import Task

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _load_scan_module():
    """从脚本文件加载 scan_mechanism_landing 模块（不依赖 conftest / 包结构）。"""
    script = BACKEND_ROOT / "scripts" / "scan_mechanism_landing.py"
    spec = importlib.util.spec_from_file_location("scan_mechanism_landing", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_scan_all_53_mechanisms_landed():
    """接线验收: 审计矩阵 53/53 全部落地, orphan=0。"""
    mod = _load_scan_module()
    rows = mod.build_landing_rows(BACKEND_ROOT)
    assert len(rows) == 54, f"期望 54 行机制, 实际 {len(rows)}"

    orphans = [r["id"] for r in rows if not r["landed"]]
    assert orphans == [], f"仍存在未落地机制: {orphans}"

    # 28 个原孤儿必须全部是「编排器接线」(而非仅外部引用)
    secondary = [
        "LF-M01", "LF-M04", "LF-M05", "LF-M06", "LF-M08",
        "LF-M12", "LF-M13", "LF-M14", "LF-M15", "LF-M16", "LF-M18",
        "LF-M20", "LF-M21", "LF-M24", "LF-M29", "LF-M32",
        "LF-M33", "LF-M34", "LF-M35", "LF-M37", "LF-M38", "LF-M39",
        "LF-M41", "LF-M43", "LF-M46", "LF-M48", "LF-M49", "LF-M50",
    ]
    by_id = {r["id"]: r for r in rows}
    for mid in secondary:
        assert by_id[mid]["orchestrator_wired"], f"{mid} 未被编排器接线"


def test_evaluation_returns_all_28_with_real_outputs():
    """评估钩子默认全开: 28 键齐全, 输出为真实引擎结果且无 error。"""
    from app.services.learning_orchestrator import (
        _evaluate_secondary_mechanisms,
        _EvalContext,
        PIPELINE_MECHANISM_MAP,
    )

    ctx = _EvalContext(
        user_id="u-eval-test",
        user_name="EvalTester",
        topic="math",
        difficulty=5,
        is_correct=True,
        success_streak=6,
        failure_streak=0,
        day_streak=3,
        attempts_today=7,
        xp_earned=25,
        pet_name="小豆",
    )
    ev = _evaluate_secondary_mechanisms(ctx)

    expected_keys = set(PIPELINE_MECHANISM_MAP[13])
    assert set(ev.keys()) == expected_keys, (
        f"评估键集与 PIPELINE_MECHANISM_MAP[13] 不一致: "
        f"缺 {expected_keys - set(ev)}, 多 {set(ev) - expected_keys}"
    )
    assert len(ev) == 28, f"期望 28 个机制评估, 实际 {len(ev)}"

    for key, record in ev.items():
        assert record["enabled"] is True, f"{key} 默认应开启"
        out = record["output"]
        assert not (isinstance(out, dict) and "error" in out), (
            f"{key} 引擎调用报错: {out}"
        )

    # 抽查若干真实输出形状 (来自引擎真实计算, 非伪造)
    assert "bonus_active" in ev["time_based_bonus"]["output"]
    assert "challenge" in ev["daily_challenge"]["output"]
    assert "percentage" in ev["zeigarnik"]["output"]
    assert ev["color_psychology"]["output"]["primary"] == "#4CAF50"  # success 主题
    assert ev["scarcity"]["output"]["unlocked"] is True  # streak=6 ≥ 5 解锁黄金题目
    assert "identity" in ev["identity_motivation"]["output"]


def test_gate_suppresses_evaluation():
    """is_enabled(False) 关闭 → 该机制跳过评估 (enabled=False, output=None)。"""
    from app.services.learning_orchestrator import (
        _evaluate_secondary_mechanisms,
        _EvalContext,
    )
    from app.services import mechanism_registry

    ctx = _EvalContext(
        user_id="u-gate-test", user_name="GateTester", topic="math",
        difficulty=3, is_correct=True, success_streak=1, failure_streak=0,
        day_streak=1, attempts_today=2, xp_earned=10, pet_name="小豆",
    )
    mechanism_registry.set_enabled("surprise_delight", False)
    try:
        ev = _evaluate_secondary_mechanisms(ctx)
        assert ev["surprise_delight"] == {"enabled": False, "output": None}, (
            "关闭的机制必须跳过评估且无任何输出"
        )
        # 其余机制不受影响
        assert ev["daily_challenge"]["enabled"] is True
    finally:
        mechanism_registry.set_enabled("surprise_delight", True)


@pytest.mark.asyncio
async def test_process_submission_includes_evaluations():
    """集成: process_submission 响应携带 28 键 mechanism_evaluations, XP 主流程不变。"""
    from app.services.learning_orchestrator import LearningOrchestrator

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        # learning_events 复合主键 SQLite 建表不兼容 (既有已知问题), 排除并以桩替换
        tables = [t for t in Base.metadata.sorted_tables if t.name != "learning_events"]
        await conn.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))

    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as db:
        user = User(
            id="lf-sec-test-user",
            email="lf_sec_test@example.com",
            name="SecTester",
            role=UserRole.STUDENT,
            hashed_password="x",
            grade=None,
        )
        task = Task(
            id="lf-sec-test-task",
            content="2+3=?",
            topic="math",
            difficulty=3,
            correct_answer="5",
            explanation="两数相加",
        )
        db.add(user)
        db.add(task)
        await db.commit()

        user = await db.get(User, "lf-sec-test-user")
        task = await db.get(Task, "lf-sec-test-task")

        with patch(
            "app.services.learning_orchestrator.record_learning_event",
            new=AsyncMock(),
        ), patch(
            "app.services.learning_orchestrator.SkillTreeEngine.get_skill_tree",
            new=lambda uid: {},
        ):
            resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "5", "hints_used": 0}, db
            )

        # 步骤 13 评估记录随响应返回, 28 键全开
        evals = resp["mechanism_evaluations"]
        assert len(evals) == 28, f"期望 28 个机制评估, 实际 {len(evals)}"
        assert all(rec["enabled"] for rec in evals.values())

        # 主流程行为不受影响: 正确作答仍授予 XP
        assert resp["xp_update"]["xp_earned"] > 0
        assert resp["is_correct"] is True

    await engine.dispose()
