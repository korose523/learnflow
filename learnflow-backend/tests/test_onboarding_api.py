# -*- coding: utf-8 -*-
"""test_onboarding_api.py
================================================================================
新手引导 API 契约测试：用真实 FastAPI app + httpx ASGITransport 打满
``app/api/onboarding.py`` 全部 6 个端点，验证「后端响应结构 == 引擎输出」。

复用 test_class_pet_api_integration.py 的夹具风格：
· 模块级 app 单例，显式调用一次 _register_routers（ASGITransport 不触发 lifespan）；
· 覆盖 get_current_user，注入一个学生身份（端点要求登录，但不依赖 DB）；
· 不依赖外部数据库（端点本身不碰 DB）。
================================================================================
"""
import pytest

from httpx import AsyncClient, ASGITransport

from app.api.auth import get_current_user
from app.main import app, _register_routers
from app.models.user import User, UserRole

_ROUTES_READY = False  # 路由注册守卫（app 为模块级单例）


async def _ensure_routes():
    global _ROUTES_READY
    if _ROUTES_READY:
        return
    # 若其它测试模块已注册过，避免重复注册导致重复路由
    if any(getattr(r, "path", None) == "/api/v1/onboarding/steps" for r in app.routes):
        _ROUTES_READY = True
        return
    await _register_routers(app)
    _ROUTES_READY = True


@pytest.fixture
async def client():
    await _ensure_routes()

    def _override_user():
        return User(
            id="U_ONB", email="onb@lf.com", hashed_password="x",
            name="引导测试生", role=UserRole.STUDENT,
        )

    app.dependency_overrides[get_current_user] = lambda: _override_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── 正向 ────────────────────────────────────────────────
async def test_get_steps_200(client):
    r = await client.get("/api/v1/onboarding/steps", params={"role": "student"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "student"
    assert body["total_steps"] == 12
    assert isinstance(body["steps"], list) and len(body["steps"]) == 12


async def test_get_current_first_step(client):
    r = await client.get("/api/v1/onboarding/current", params={"role": "student"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_next"] is True
    assert body["step_id"] == "stu_welcome"
    assert "progress_pct" in body


async def test_get_current_after_one_done(client):
    r = await client.get(
        "/api/v1/onboarding/current",
        params={"role": "student", "completed": "stu_welcome"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["step_id"] == "stu_first_question"


async def test_get_current_empty_completed_param(client):
    # completed 省略 → 视作 [] → 回到第一步
    r = await client.get("/api/v1/onboarding/current", params={"role": "student", "completed": ""})
    assert r.status_code == 200, r.text
    assert r.json()["step_id"] == "stu_welcome"


async def test_complete_step_reward(client):
    r = await client.post(
        "/api/v1/onboarding/complete",
        json={"role": "student", "step_id": "stu_first_question"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["completed"] is True
    assert body["step_id"] == "stu_first_question"
    assert body["xp_reward"] > 0


async def test_skip_onboarding(client):
    r = await client.post("/api/v1/onboarding/skip", json={"role": "student"})
    assert r.status_code == 200, r.text
    assert r.json()["skipped"] is True


async def test_help_known_trigger(client):
    r = await client.get("/api/v1/onboarding/help", params={"trigger": "first_error"})
    assert r.status_code == 200, r.text
    assert r.json()["trigger"] == "first_error"


async def test_help_context_template_substitution(client):
    r = await client.get(
        "/api/v1/onboarding/help",
        params={"trigger": "feature_unused", "context": "feature_name=技能树,benefit=提升效率"},
    )
    assert r.status_code == 200, r.text
    # feature_name 应被替换进 message
    assert "技能树" in r.json()["message"]


async def test_features_at_session_1(client):
    r = await client.get(
        "/api/v1/onboarding/features",
        params={"role": "student", "sessions_completed": 1},
    )
    assert r.status_code == 200, r.text
    features = r.json()
    assert isinstance(features, list)
    assert any(f["feature"] == "pet_system" for f in features)


# ── 负向 ────────────────────────────────────────────────
async def test_help_unknown_trigger_404(client):
    r = await client.get("/api/v1/onboarding/help", params={"trigger": "no_such_trigger"})
    assert r.status_code == 404, r.text


async def test_help_missing_trigger_404(client):
    r = await client.get("/api/v1/onboarding/help")
    assert r.status_code == 404, r.text


async def test_help_malformed_context_400(client):
    r = await client.get(
        "/api/v1/onboarding/help",
        params={"trigger": "first_error", "context": "badformat_no_equals"},
    )
    assert r.status_code == 400, r.text


async def test_features_negative_sessions_422(client):
    r = await client.get(
        "/api/v1/onboarding/features",
        params={"role": "student", "sessions_completed": -1},
    )
    assert r.status_code == 422, r.text


# ═══════════════════════════════════════════════════════════════════════════
# PUT /profile —— 引导向导学习档案的真实落库（本组端点需要 DB，故单独夹具）
#
# 背景：POST /complete 只做无状态奖励查询、不写库；引导向导（grade → subjects
# → consent）此前只写 localStorage，后端无落库路径。PUT /profile 补上该路径，
# 本组用例验证数据真的进了 users 表（而非只回显）。
# ═══════════════════════════════════════════════════════════════════════════
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db


@pytest.fixture
async def db_client():
    await _ensure_routes()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # 用别名导入：写成 `import app.models` 会把局部名 app 绑定到包，遮蔽 app 单例
    import app.models as _app_models  # noqa: F401 —— 注册全部表（含新增 subjects 列）

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _session():
        # 镜像真实 get_db：成功 commit、异常 rollback。少了 commit，写端点
        # 的持久化断言会假失败（会话关闭即回滚）。
        async with sm() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _session
    app.dependency_overrides[get_current_user] = lambda: User(
        id="U_PROF", email="prof@lf.com", hashed_password="x",
        name="档案生", role=UserRole.STUDENT,
    )

    async with sm() as s:
        s.add(User(id="U_PROF", email="prof@lf.com", hashed_password="x",
                   name="档案生", role=UserRole.STUDENT))
        await s.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sm
    app.dependency_overrides.clear()


async def _read_user(sm):
    async with sm() as s:
        return (await s.execute(
            sa_select(User).where(User.id == "U_PROF")
        )).scalar_one()


async def test_profile_persists_grade_and_subjects(db_client):
    """核心断言：PUT 之后**重新查库**能读到值（而非只回显请求体）。

    旧行为：向导只写 localStorage，后端无端点 → 本用例 404/405 判红。"""
    ac, sm = db_client
    r = await ac.put("/api/v1/onboarding/profile", json={
        "grade": "G5", "subjects": ["math", "chinese"], "consent_agreed": False,
    })
    assert r.status_code == 200, r.text

    u = await _read_user(sm)          # 从库里重读，证明真的落库了
    assert u.grade == "G5"
    assert u.subjects == ["math", "chinese"]


async def test_profile_consent_writes_record(db_client):
    """同意勾选必须写入 consents 记录（含姓名与时间戳）。"""
    ac, sm = db_client
    r = await ac.put("/api/v1/onboarding/profile", json={
        "grade": "G6", "subjects": ["english"],
        "consent_name": "张监护", "consent_agreed": True,
    })
    assert r.status_code == 200, r.text

    u = await _read_user(sm)
    assert u.consents.get("parental_consent") is True
    assert u.consents.get("parental_consent_name") == "张监护"
    assert u.consents.get("parental_consent_at"), "应写入同意时间戳"


async def test_profile_partial_update_does_not_clear(db_client):
    """省略字段 = 不改动；不能把已存的 grade 清成 None。"""
    ac, sm = db_client
    await ac.put("/api/v1/onboarding/profile", json={
        "grade": "G7", "subjects": ["math"],
    })
    r = await ac.put("/api/v1/onboarding/profile", json={"subjects": ["science"]})
    assert r.status_code == 200, r.text

    u = await _read_user(sm)
    assert u.grade == "G7", "未提供的 grade 不应被清空"
    assert u.subjects == ["science"]
