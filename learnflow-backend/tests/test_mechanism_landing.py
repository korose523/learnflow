"""机制落地审计矩阵 + xp_leveling 消融门控测试

* test_scan_produces_53_rows   —— 审计矩阵必须是 53 行且 ID 连续 LF-M01..LF-M53
* test_xp_leveling_gate_suppresses
    —— process_submission 在 xp_leveling (LF-M19) 关闭时 xp_earned 必须为 0
    （GAP-6 修复；默认开启时行为不变，授予 XP）
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


def _load_script(filename: str):
    """从 scripts/ 加载指定脚本为模块（不依赖 conftest / 包结构）。"""
    script = BACKEND_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(
        "lf_script_" + Path(filename).stem, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_scan_module():
    """加载 scan_mechanism_landing 模块。"""
    return _load_script("scan_mechanism_landing.py")


def test_scan_produces_53_rows():
    mod = _load_scan_module()
    rows = mod.build_landing_rows(BACKEND_ROOT)
    assert len(rows) == 53, f"期望 53 行机制, 实际 {len(rows)}"

    ids = [r["id"] for r in rows]
    expected = [f"LF-M{i:02d}" for i in range(1, 54)]
    assert ids == expected, f"机制 ID 不连续: {ids[:3]}..{ids[-3:]}"

    # 每行必须含审计所需字段
    for r in rows:
        for field in (
            "id", "key", "name_zh", "category", "disposition", "maturity",
            "impl_ref", "impl_ref_file_exists", "external_ref",
            "orchestrator_wired", "landed",
        ):
            assert field in r, f"{r.get('id')} 缺少字段 {field}"


@pytest.mark.asyncio
async def test_xp_leveling_gate_suppresses():
    """xp_leveling (LF-M19) 关闭时, 编排器步骤 9 必须跳过 award_xp → xp_earned == 0。"""
    from app.services.learning_orchestrator import LearningOrchestrator
    from app.services import mechanism_registry

    # 轻量内存 SQLite（StaticPool 保证单连接共享同一内存库）
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        # learning_events 含复合主键 + autoincrement (seq)，SQLite 不支持该组合建表；
        # 该表由 record_learning_event 仅追加写入，与 xp_leveling 门控无关，
        # 故排除其建表并以 no-op 桩替换写入（隔离本测试关注的门控逻辑）。
        tables = [t for t in Base.metadata.sorted_tables if t.name != "learning_events"]
        await conn.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))

    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as db:
        user = User(
            id="lf-xp-test-user",
            email="lf_xp_test@example.com",
            name="XPTester",
            role=UserRole.STUDENT,
            hashed_password="x",
            grade=None,  # 成年/其他学段 → 非未成年, reward 不被冷却, 隔离变量
        )
        task = Task(
            id="lf-xp-test-task",
            content="1+1=?",
            topic="math",
            difficulty=3,
            correct_answer="2",
            explanation="两个一相加",
        )
        db.add(user)
        db.add(task)
        await db.commit()

        user = await db.get(User, "lf-xp-test-user")
        task = await db.get(Task, "lf-xp-test-task")

        # 桩掉与 xp_leveling 门控无关的下游写入：
        #   * record_learning_event —— learning_events 表 SQLite 复合主键不兼容建表。
        #
        # 注：此处原还有一处 SkillTreeEngine.get_skill_tree 桩，用于规避
        # 「引擎视图结构 vs _skilltree_repo_format 期望扁平结构」不兼容导致的
        # AttributeError（P0，凡 db 非 None 的提交必崩）。该缺陷已修复，桩随之
        # 移除 —— 本测试因此同时覆盖技能树真实落库路径。
        with patch(
            "app.services.learning_orchestrator.record_learning_event",
            new=AsyncMock(),
        ):
            # 1) 默认开启 → 应当授予 XP
            enabled_resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "2", "hints_used": 0}, db
            )
            assert enabled_resp["xp_update"]["xp_earned"] > 0, (
                "xp_leveling 开启时应当授予 XP, 实际 xp_earned="
                f"{enabled_resp['xp_update']['xp_earned']}"
            )

            # 2) 关闭 LF-M19 → xp_earned 必须为 0（消融门控）
            mechanism_registry.set_enabled("xp_leveling", False)
            try:
                disabled_resp = await LearningOrchestrator.process_submission(
                    user, task, {"answer": "2", "hints_used": 0}, db
                )
                assert disabled_resp["xp_update"]["xp_earned"] == 0, (
                    "xp_leveling 关闭时 xp_earned 必须为 0（消融门控失效）, 实际 "
                    f"{disabled_resp['xp_update']['xp_earned']}"
                )
                assert disabled_resp["xp_update"]["message"] == "（机制已关闭）实验对照"
            finally:
                # 还原全局开关, 避免污染其它测试
                mechanism_registry.set_enabled("xp_leveling", True)

    await engine.dispose()


def test_impl_ref_has_no_hard_errors():
    """impl_ref 引用完整性：不得存在文件缺失 / 行号越界 / 形态非法。

    ``scripts/check_impl_ref.py`` 把「行号静默漂移」这一失效模式变成可复算的
    红灯。软警告（BLANK，行号落在空行）不判失败——既有条目中一部分锚定在
    分隔注释行上，需人工确认后再批量修正。
    """
    mod = _load_script("check_impl_ref.py")
    services_dir = BACKEND_ROOT / "app" / "services"

    from app.services.mechanism_registry import all_mechanisms
    rows = [mod.check_one(m.id, m.impl_ref, services_dir) for m in all_mechanisms()]

    assert len(rows) == 53
    hard = [r for r in rows if r["status"] in ("MISSING", "OUT_OF_RANGE", "UNPARSEABLE")]
    assert hard == [], "存在硬错误的 impl_ref: " + "; ".join(
        f"{r['id']} {r['impl_ref']} ({r['detail']})" for r in hard
    )
