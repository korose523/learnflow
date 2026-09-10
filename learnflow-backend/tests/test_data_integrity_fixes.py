# -*- coding: utf-8 -*-
"""
test_data_integrity_fixes.py
================================================================================
回归测试：修复「完整性审计」发现的 3 处编造/硬编码数据缺口（be-fix-core）。

设计（沿用 tests/test_class_pet_api_integration.py 的成熟 harness）
------------------------------------------------------------------
· 用内存 sqlite（StaticPool）覆盖 get_db；覆盖 get_current_user 注入身份；
· 路由需显式 _ensure_routes()（ASGITransport 不触发 lifespan，而 FastAPI
  路由正是注册在 lifespan 里）；用 sentinel 守卫避免跨测试模块重复注册；
· 播种受控数据后逐端点断言，每个用例都必须对「旧的错误代码」判红，
  即：不是“对新代码能过”，而是“对老代码必败”。

覆盖
----
1. teacher.py  /ai/classroom-analysis  —— 真实的 most_active_hour / weekend_ratio
   / difficulty_distribution（旧代码硬编码 "19:00" / 0.3 / {}）。
2. student.py  /challenge             —— subject 取自最近作答的 Task.topic；
   reset_recommended 取自真正的反成瘾判定；low/high 设计带宽保留并断言。
3. parent.py   /child/{id}/daily-limit —— GET/PUT 真实落库（旧代码仅前端
   localStorage，后端无对应端点，故旧代码下这些用例全部 404）。

运行
----
  cd /e/learnflow/learnflow-backend && ./.venv/Scripts/python.exe -m pytest tests/test_data_integrity_fixes.py -q
================================================================================
"""
import pytest
from collections import Counter
from datetime import datetime, timedelta, UTC

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.main import app
from app.models.user import User, UserRole
from app.models.task import Task, Attempt


# ─── 身份占位（被 get_current_user override 返回） ────────────────────────────
CURRENT_USER = None
_ROUTES_READY = False  # 跨用例只注册一次路由


async def _ensure_routes():
    """真实启动经由 lifespan 注册路由；ASGITransport 不触发 lifespan，
    故显式调用一次 _register_routers。用 sentinel 路径判定是否已注册，
    避免与其他测试模块重复 include_router 产生重复路由。"""
    global _ROUTES_READY
    if _ROUTES_READY:
        return
    sentinel = "/api/v1/parent/child/{child_id}/daily-limit"
    if any(
        getattr(r, "path", None) == sentinel
        and getattr(r, "methods", None)
        and "PUT" in r.methods
        for r in app.routes
    ):
        _ROUTES_READY = True
        return
    from app.main import _register_routers
    await _register_routers(app)
    _ROUTES_READY = True


def _set_user(user):
    global CURRENT_USER
    CURRENT_USER = user


@pytest.fixture
async def harness():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # 注意：这里必须用别名导入。写成 `import app.models` 会在本函数作用域内
    # 把名字 `app` 重新绑定到顶层包，从而遮蔽模块级 `from app.main import app`
    # 得到的 FastAPI 实例，导致 `app.dependency_overrides` 报
    # AttributeError: module 'app' has no attribute 'dependency_overrides'。
    import app.models as _app_models  # noqa: F401 —— 仅为确保 Base.metadata 注册全部表（含 daily_limit_minutes）

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        # 必须镜像 app.core.database.get_db 的真实语义：成功时 commit、异常时
        # rollback。真实 get_db 在 yield 之后会 `await session.commit()`，因此端点
        # 内部只需 flush()；若这里省掉 commit，会话关闭时会回滚，任何写端点的
        # 「持久化」断言都会假失败（曾导致 daily-limit roundtrip 用例误判）。
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        return CURRENT_USER

    await _ensure_routes()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sessionmaker

    app.dependency_overrides.clear()


# ─── 播种辅助 ────────────────────────────────────────────────────────────────

async def _seed_user(sm, **kw):
    u = User(**kw)
    async with sm() as s:
        s.add(u)
        await s.commit()
        await s.refresh(u)
    return u


async def _seed_task(sm, task_id, topic):
    t = Task(
        id=task_id,
        title=f"题-{topic}",
        content="x",
        topic=topic,
        difficulty=5,
        correct_answer="42",
    )
    async with sm() as s:
        s.add(t)
        await s.commit()
    return t


async def _seed_attempt(sm, user_id, task_id, created_at, difficulty, is_correct=True):
    a = Attempt(
        user_id=user_id,
        task_id=task_id,
        answer="42",
        is_correct=is_correct,
        created_at=created_at,
        difficulty_at_time=difficulty,
    )
    async with sm() as s:
        s.add(a)
        await s.commit()


# ═══════════════════════════════════════════════════════════════════════════
# FIX 1 —— teacher /ai/classroom-analysis 真实统计
# ═══════════════════════════════════════════════════════════════════════════

# 受控作答：8 条，小时众数=14，周末(weekday>=5)=3 条 → 真实占比 3/8=0.375
_ATTEMPTS_SPEC = [
    ("STU1", datetime(2024, 3, 13, 14, 0, 0, tzinfo=UTC), 3),  # 周三 14 点
    ("STU1", datetime(2024, 3, 13, 14, 0, 0, tzinfo=UTC), 3),
    ("STU1", datetime(2024, 3, 13, 14, 0, 0, tzinfo=UTC), 5),
    ("STU1", datetime(2024, 3, 13, 14, 0, 0, tzinfo=UTC), 5),
    ("STU1", datetime(2024, 3, 13, 14, 0, 0, tzinfo=UTC), 7),
    ("STU2", datetime(2024, 3, 16, 14, 0, 0, tzinfo=UTC), 7),  # 周六 14 点
    ("STU2", datetime(2024, 3, 16, 14, 0, 0, tzinfo=UTC), 9),  # 周六 14 点
    ("STU2", datetime(2024, 3, 10, 10, 0, 0, tzinfo=UTC), 9),  # 周日 10 点
]


async def test_classroom_analysis_real_stats(harness):
    """众数小时 / 周末占比 / 难度分布必须从真实 all_attempts 算出（非 "19:00"/0.3/{}）。

    旧代码：most_active_hour="19:00", weekend_ratio=0.3, difficulty_distribution={}
    → 本用例对旧代码判红。"""
    ac, sm = harness

    await _seed_user(sm, id="STU1", email="s1@lf.com", hashed_password="x", name="学1", role=UserRole.STUDENT)
    await _seed_user(sm, id="STU2", email="s2@lf.com", hashed_password="x", name="学2", role=UserRole.STUDENT)
    # attempts.task_id 是 NOT NULL，必须先播种一道题再挂作答
    seeded_task = await _seed_task(sm, "TASK-CA-1", "math")
    for uid, dt, diff in _ATTEMPTS_SPEC:
        await _seed_attempt(sm, uid, seeded_task.id, dt, diff)

    # 计算与种子一致的真值
    hour_counts = Counter(dt.hour for (_, dt, _) in _ATTEMPTS_SPEC)
    modal_hour = max(hour_counts, key=hour_counts.get)
    expected_hour = f"{modal_hour:02d}:00"
    weekend = sum(1 for (_, dt, _) in _ATTEMPTS_SPEC if dt.weekday() >= 5)
    expected_ratio = round(weekend / len(_ATTEMPTS_SPEC), 2)
    expected_dist = {str(d): c for d, c in Counter(d for (_, _, d) in _ATTEMPTS_SPEC).items()}

    _set_user(User(id="T1", email="t@lf.com", hashed_password="x", name="师", role=UserRole.TEACHER))
    r = await ac.get("/api/v1/teacher/ai/classroom-analysis")
    assert r.status_code == 200, r.text
    body = r.json()

    # 关键：结果必须匹配真实数据，且不等于旧的占位常量
    assert body["most_active_hour"] == expected_hour, body
    assert body["most_active_hour"] != "19:00", "most_active_hour 不应是旧占位常量"
    assert body["weekend_vs_weekday_ratio"] == expected_ratio, body
    assert body["weekend_vs_weekday_ratio"] != 0.3, "weekend_ratio 不应是旧占位常量"
    assert body["difficulty_distribution"] == expected_dist, body
    assert body["difficulty_distribution"] != {}, "difficulty_distribution 不应是空占位"


async def test_classroom_analysis_no_attempts_returns_none(harness):
    """无作答数据时，三项返回 None / {}——宁可空缺也不编造。

    旧代码：most_active_hour="19:00", weekend_ratio=0.3, difficulty_distribution={}
    → 本用例对旧代码判红（断言 None / None）。"""
    ac, sm = harness
    await _seed_user(sm, id="STU1", email="s1@lf.com", hashed_password="x", name="学1", role=UserRole.STUDENT)
    # 注意：不播种任何 Attempt

    _set_user(User(id="T1", email="t@lf.com", hashed_password="x", name="师", role=UserRole.TEACHER))
    r = await ac.get("/api/v1/teacher/ai/classroom-analysis")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["most_active_hour"] is None
    assert body["weekend_vs_weekday_ratio"] is None
    assert body["difficulty_distribution"] == {}


# ═══════════════════════════════════════════════════════════════════════════
# FIX 2 —— student /challenge subject / reset_recommended
# ═══════════════════════════════════════════════════════════════════════════

async def test_challenge_subject_and_reset_true(harness):
    """subject 取自最近作答 Task.topic；连续学习时长≥25min 时 reset_recommended=True。

    · subject：旧代码恒为 None → 判红。
    · reset_recommended：旧代码恒为 False；本用例当日 10 次作答×3min=30min≥25 → 应为 True → 判红。"""
    ac, sm = harness
    stu = await _seed_user(
        sm, id="STU", email="stu@lf.com", hashed_password="x", name="生",
        role=UserRole.STUDENT, grade="六年级",
    )
    await _seed_task(sm, "TK", "分数加减法")

    now = datetime.now(UTC)
    # 10 次当日作答，最近一次(最后插入)的 topic 即 "分数加减法"
    for i in range(10):
        await _seed_attempt(sm, "STU", "TK", now - timedelta(minutes=i), 5)

    _set_user(User(id="STU", email="stu@lf.com", hashed_password="x", name="生", role=UserRole.STUDENT, grade="六年级"))
    r = await ac.get("/api/v1/student/challenge")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["subject"] == "分数加减法", "subject 应来自最近作答的 Task.topic"
    assert body["reset_recommended"] is True, "当日 30 分钟会话应触发难度重置"
    # 设计带宽常量保留并显式断言（这是有意为之的固定设计值，不是编造数据）
    assert body["low"] == 75
    assert body["high"] == 85


async def test_challenge_reset_false_and_subject_none_without_history(harness):
    """无作答历史：subject=None；当日 0 分钟 → reset_recommended=False。

    该用例主要作为“不会误报重置 / 不会臆造 subject”的正向守门（旧代码此处恰为
    False/None，故不是鉴别旧代码的用例；真正的鉴别由 True 用例承担）。"""
    ac, sm = harness
    await _seed_user(
        sm, id="STU", email="stu@lf.com", hashed_password="x", name="生",
        role=UserRole.STUDENT, grade="六年级",
    )
    _set_user(User(id="STU", email="stu@lf.com", hashed_password="x", name="生", role=UserRole.STUDENT, grade="六年级"))
    r = await ac.get("/api/v1/student/challenge")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subject"] is None
    assert body["reset_recommended"] is False
    assert body["low"] == 75 and body["high"] == 85


# ═══════════════════════════════════════════════════════════════════════════
# FIX 3 —— parent /child/{id}/daily-limit 真实持久化
# ═══════════════════════════════════════════════════════════════════════════

async def _seed_parent_child(sm):
    parent = await _seed_user(
        sm, id="PA", email="pa@lf.com", hashed_password="x", name="父", role=UserRole.PARENT,
    )
    child = await _seed_user(
        sm, id="CH", email="ch@lf.com", hashed_password="x", name="娃",
        role=UserRole.STUDENT, parent_id="PA",
    )
    return parent, child


async def test_daily_limit_get_default_none(harness):
    """新孩子默认未设上限 → GET 返回 daily_limit_minutes=None。

    旧代码：后端无此端点 → 404。→ 对旧代码判红。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    _set_user(User(id="PA", email="pa@lf.com", hashed_password="x", name="父", role=UserRole.PARENT))
    r = await ac.get("/api/v1/parent/child/CH/daily-limit")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"child_id": "CH", "daily_limit_minutes": None}


async def test_daily_limit_put_get_roundtrip(harness):
    """PUT 60 落库，随后 GET 读到 60（证明写入真实 DB，而非 localStorage）。

    旧代码：后端无此端点 → 404。→ 对旧代码判红。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    _set_user(User(id="PA", email="pa@lf.com", hashed_password="x", name="父", role=UserRole.PARENT))

    r1 = await ac.put("/api/v1/parent/child/CH/daily-limit", json={"daily_limit_minutes": 60})
    assert r1.status_code == 200, r1.text
    assert r1.json()["daily_limit_minutes"] == 60

    r2 = await ac.get("/api/v1/parent/child/CH/daily-limit")
    assert r2.status_code == 200, r2.text
    assert r2.json()["daily_limit_minutes"] == 60, "GET 应读回刚 PUT 的持久化值"


async def test_daily_limit_put_null_clears(harness):
    """PUT null 清除上限 → GET 回到 None。旧代码：404 → 判红。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    _set_user(User(id="PA", email="pa@lf.com", hashed_password="x", name="父", role=UserRole.PARENT))

    await ac.put("/api/v1/parent/child/CH/daily-limit", json={"daily_limit_minutes": 90})
    r = await ac.put("/api/v1/parent/child/CH/daily-limit", json={"daily_limit_minutes": None})
    assert r.status_code == 200, r.text
    assert r.json()["daily_limit_minutes"] is None

    r2 = await ac.get("/api/v1/parent/child/CH/daily-limit")
    assert r2.json()["daily_limit_minutes"] is None


async def test_daily_limit_put_out_of_range_returns_400(harness):
    """越界值（10 / 500）必须返回 400（与实现一致，非 422）。旧代码：404 → 判红。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    _set_user(User(id="PA", email="pa@lf.com", hashed_password="x", name="父", role=UserRole.PARENT))

    for bad in (10, 500):
        r = await ac.put("/api/v1/parent/child/CH/daily-limit", json={"daily_limit_minutes": bad})
        assert r.status_code == 400, f"值 {bad} 应被 400 拒绝: {r.text}"
        # 越界不得落库
        g = await ac.get("/api/v1/parent/child/CH/daily-limit")
        assert g.json()["daily_limit_minutes"] is None


async def test_daily_limit_wrong_parent_forbidden(harness):
    """非绑定家长访问他人孩子 → 404（与 /summary 一致）。旧代码：404 但原因不同
    （端点不存在）→ 仍判红，因为新代码中这是“无权限”语义。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    # 另一个家长，与 CH 无绑定、也不满足演示绑定规则
    await _seed_user(
        sm, id="PB", email="pb@lf.com", hashed_password="x", name="外父", role=UserRole.PARENT,
    )
    _set_user(User(id="PB", email="pb@lf.com", hashed_password="x", name="外父", role=UserRole.PARENT))
    r = await ac.get("/api/v1/parent/child/CH/daily-limit")
    assert r.status_code == 404, r.text


async def test_daily_limit_requires_parent_role(harness):
    """非家长角色（此处为学生）调用 → require_parent 返回 403。旧代码：404 → 判红。"""
    ac, sm = harness
    await _seed_parent_child(sm)
    await _seed_user(
        sm, id="STRANGER", email="st@lf.com", hashed_password="x", name="路人", role=UserRole.STUDENT,
    )
    _set_user(User(id="STRANGER", email="st@lf.com", hashed_password="x", name="路人", role=UserRole.STUDENT))
    r = await ac.get("/api/v1/parent/child/CH/daily-limit")
    assert r.status_code == 403, r.text
