# -*- coding: utf-8 -*-
"""test_placement_api.py
================================================================================
入学水平测试 API 契约测试：用真实 FastAPI app + httpx ASGITransport 打满
``app/api/placement.py`` 的 start / answer 端点，验证「后端响应结构 == 引擎输出」，
并覆盖错误路径（未知 session_id → 404）与会话 TTL 清理逻辑。

复用 test_class_pet_api_integration.py 的夹具风格：
· 模块级 app 单例，显式调用一次 _register_routers；
· 覆盖 get_current_user，注入一个学生身份（端点要求登录，但不依赖 DB）；
· 不依赖外部数据库。
================================================================================
"""
import time

import pytest

from httpx import AsyncClient, ASGITransport

from app.api.auth import get_current_user
from app.api import placement as placement_module
from app.main import app, _register_routers
from app.models.user import User, UserRole

_ROUTES_READY = False  # 路由注册守卫（app 为模块级单例）


async def _ensure_routes():
    global _ROUTES_READY
    if _ROUTES_READY:
        return
    if any(getattr(r, "path", None) == "/api/v1/placement/start" for r in app.routes):
        _ROUTES_READY = True
        return
    await _register_routers(app)
    _ROUTES_READY = True


@pytest.fixture
async def client():
    await _ensure_routes()

    def _override_user():
        return User(
            id="U_PLC", email="plc@lf.com", hashed_password="x",
            name="测试生", role=UserRole.STUDENT,
        )

    app.dependency_overrides[get_current_user] = lambda: _override_user()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── 正向 ────────────────────────────────────────────────
async def test_start_returns_session_and_question(client):
    r = await client.post("/api/v1/placement/start")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["session_id"], str) and len(body["session_id"]) == 32  # uuid4().hex
    assert body["started"]["test_started"] is True
    q = body["question"]
    assert q["test_complete"] is False
    assert q["question_number"] == 1
    assert q["difficulty"] == 5


async def test_answer_unknown_session_404(client):
    r = await client.post(
        "/api/v1/placement/answer",
        json={"session_id": "deadbeef" * 4, "is_correct": True},
    )
    assert r.status_code == 404, r.text
    assert "会话" in r.json()["detail"]


async def test_full_flow_converges(client):
    """交替作答直到收敛；引擎在 6 题左右（最近 3 题 2/3 正确）应判定收敛。"""
    r = await client.post("/api/v1/placement/start")
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    converged = False
    for i in range(12):
        resp = await client.post(
            "/api/v1/placement/answer",
            json={"session_id": session_id, "is_correct": (i % 2 == 0)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body["converged"]:
            converged = True
            assert "result" in body
            assert body["result"]["test_completed"] is True
            assert "estimated_level" in body["result"]
            break
        else:
            assert "question" in body
    assert converged, "12 题内应已收敛"


async def test_ttl_purge_removes_expired_session(client):
    """注入一个已过期的会话，start 时惰性清理应将其移除。"""
    expired_id = "x" * 32
    placement_module._SESSIONS[expired_id] = {
        "state": None,
        "created_at": time.monotonic() - (placement_module._TTL_SECONDS + 10),
    }
    r = await client.post("/api/v1/placement/start")
    assert r.status_code == 200, r.text
    # 过期会话应已被清理
    assert expired_id not in placement_module._SESSIONS
