# -*- coding: utf-8 -*-
"""
test_class_pet_api_integration.py
================================================================================
班级宠物园（LF-M54）前后端「联调」测试：用真实 FastAPI app + httpx ASGITransport
打满全部 5 个端点，验证「后端响应结构 == 前端 classPetApi 期望」的契约一致性。

设计
----
· 用内存 sqlite（StaticPool）覆盖 get_db，避免依赖外部数据库；
· 覆盖 get_current_user，分别注入「学生」与「教师」身份，覆盖角色权限；
· 播种一个班级 + 5 名学生（带专属宠物）+ 1 名教师，再逐端点断言 200 与字段；
· 同时验证「学生越权调用教师端点 → 403」的负向契约。

运行（本机 venv 已损坏，用 .venv_new + PYTHONPATH 分号分隔）
  PYTHONPATH="E:/learnflow/learnflow-backend/.venv/Lib/site-packages;E:/learnflow/learnflow-backend" \
    E:/learnflow/learnflow-backend/.venv_new/Scripts/python.exe -m pytest \
    tests/test_class_pet_api_integration.py -q
================================================================================
"""
import pytest

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.main import app
from app.models.user import User, UserRole
from app.models.pet import PetProfile
from app.models.class_pet import ClassPetGarden


CLASS_ID = "C_TEST"
CURRENT_USER = None  # 模块级身份占位，由 override 返回
_ROUTES_READY = False  # 路由注册守卫（app 为模块级单例，避免重复注册）


async def _ensure_routes():
    """真实启动经由 lifespan 注册路由；ASGITransport 不触发 lifespan，
    故测试里显式调用一次 _register_routers（等价启动行为，不碰数据库）。"""
    global _ROUTES_READY
    if not _ROUTES_READY:
        from app.main import _register_routers
        await _register_routers(app)
        _ROUTES_READY = True


@pytest.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # —— 播种班级 + 学生（带宠物）+ 教师 ——
    async with sessionmaker() as s:
        students = []
        for i in range(5):
            u = User(
                id=f"S{i}", email=f"s{i}@lf.com", hashed_password="x",
                name=f"学{i}", role=UserRole.STUDENT, class_id=CLASS_ID,
            )
            s.add(u)
            students.append(u)
            pet = PetProfile(
                user_id=f"S{i}", level=i + 1,
                understanding=50.0 + i * 3, persistence=50.0,
                creativity=50.0, collaboration=50.0 + i * 2,
            )
            s.add(pet)
        teacher = User(
            id="T1", email="t@lf.com", hashed_password="x",
            name="师", role=UserRole.TEACHER, class_id=CLASS_ID,
        )
        s.add(teacher)
        s.add(ClassPetGarden(class_id=CLASS_ID))
        await s.commit()

    async def override_get_db():
        async with sessionmaker() as session:
            yield session

    async def override_get_current_user():
        return CURRENT_USER

    await _ensure_routes()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _student(idx=0):
    global CURRENT_USER
    CURRENT_USER = User(
        id=f"S{idx}", email=f"s{idx}@lf.com", hashed_password="x",
        name=f"学{idx}", role=UserRole.STUDENT, class_id=CLASS_ID,
    )


def _teacher():
    global CURRENT_USER
    CURRENT_USER = User(
        id="T1", email="t@lf.com", hashed_password="x",
        name="师", role=UserRole.TEACHER, class_id=CLASS_ID,
    )


BASE = f"/api/v1/class-pet/{CLASS_ID}"


async def test_student_garden_view(client):
    _student(0)
    r = await client.get(f"{BASE}/garden")
    assert r.status_code == 200, r.text
    body = r.json()
    # 前端 classPetApi.garden() 期望的字段
    for key in ("leaderboard", "morphology_distribution", "cohesion",
                "connection_quality", "total_pets", "class_id"):
        assert key in body, f"garden 缺少字段 {key}"
    assert body["total_pets"] == 5
    assert isinstance(body["leaderboard"], list) and len(body["leaderboard"]) == 5
    assert 0.0 <= body["connection_quality"] <= 1.0


async def test_student_my_pet(client):
    _student(2)
    r = await client.get(f"{BASE}/my-pet")
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("pet_id", "name", "level", "morphology_stage", "morphology_label",
                "total_score", "dimensions", "mood", "starving", "class_id"):
        assert key in body, f"my-pet 缺少字段 {key}"
    assert isinstance(body["dimensions"], dict)
    assert {"understanding", "persistence", "creativity", "collaboration"} <= set(body["dimensions"])
    assert isinstance(body["morphology_stage"], int) and body["morphology_stage"] >= 1


async def test_teacher_award_feeds_pet(client):
    _teacher()
    r = await client.post(f"{BASE}/award", json={
        "student_id": "S1", "points": 10, "behavior": "homework", "reason": "背课文",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["award"]["points"] == 10
    assert body["award"]["behavior"] == "homework"
    # 正分喂养应抬升 persistence（homework→坚持力）
    assert body["dimensions"]["persistence"] >= 50.0


async def test_student_cannot_award(client):
    _student(0)
    r = await client.post(f"{BASE}/award", json={
        "student_id": "S3", "points": 10, "behavior": "homework",
    })
    assert r.status_code == 403, "学生越权加减分应被拒"


async def test_teacher_ritual_toggle(client):
    _teacher()
    r = await client.post(f"{BASE}/ritual", json={"enabled": True})
    assert r.status_code == 200, r.text
    assert r.json().get("ritual_enabled") is True


async def test_teacher_full_view(client):
    _teacher()
    r = await client.get(f"{BASE}/teacher")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "per_student" in body and len(body["per_student"]) == 5
    for p in body["per_student"]:
        for key in ("pet_id", "user_id", "level", "morphology_stage", "starving"):
            assert key in p, f"per_student 缺 {key}"
