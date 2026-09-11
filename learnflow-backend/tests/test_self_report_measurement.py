# -*- coding: utf-8 -*-
"""
test_self_report_measurement.py
================================================================================
回归测试：自陈测量基础设施 + LAI 结构偏差修复。

要防的是什么
------------
修复前，LAI 五维中的 ``control``(25%) 与 ``function``(10%) 由**硬编码常量**
驱动（``planned_stop_failures=0`` / ``sleep_impact=0`` / ``social_impact=0``），
这两维因此恒为「健康」，索引结构性偏向「不成瘾」——35% 的权重永远满分。

本套用例的核心断言是**对旧代码必败**：
· 旧代码：``assess()`` 无 ``measured_dimensions`` 参数，任何输入下 control/function
  都以满分计入综合分；
· 新代码：未声明为「已测」的维度 ``measured=False``、``weighted_score=0``，
  且 ``coverage`` 明确报告缺哪些维度与缺哪份量表。

harness 沿用 tests/test_data_integrity_fixes.py（内存 sqlite + StaticPool，
get_db 镜像真实 commit 语义，路由需显式注册）。

运行
----
  cd /e/learnflow/learnflow-backend && \\
    ./.venv/Scripts/python.exe -m pytest tests/test_self_report_measurement.py -q
================================================================================
"""
from datetime import datetime, timedelta, UTC

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.main import app
from app.models.user import User, UserRole
from app.models.instrument import SelfReportResponse
from app.services import instrument_catalog
from app.services.learning_addiction_index import LearningAddictionIndex
from app.services.self_report_service import (
    MAX_AGE_DAYS,
    coverage_report,
    latest_self_report_inputs,
    lai_inputs_from_self_report,
    measured_dimensions,
)

CURRENT_USER = None
_ROUTES_READY = False


async def _ensure_routes():
    global _ROUTES_READY
    if _ROUTES_READY:
        return
    sentinel = "/api/v1/instruments/me/coverage"
    if any(getattr(r, "path", None) == sentinel for r in app.routes):
        _ROUTES_READY = True
        return
    from app.main import _register_routers
    await _register_routers(app)
    _ROUTES_READY = True


@pytest.fixture
async def harness():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # 别名导入：直接 `import app.models` 会把本函数内的名字 app 绑定到包，
    # 遮蔽模块级 FastAPI 实例，导致 dependency_overrides 报 AttributeError。
    import app.models as _app_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        # 镜像真实 get_db：成功 commit、异常 rollback
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


@pytest.fixture
async def as_student(harness):
    """把当前登录用户设为学生并返回 (client, sessionmaker, user)。

    必须是 async 夹具 —— 它依赖同样 async 的 ``harness``；写成同步夹具
    会让 pytest-asyncio 无法解析依赖（报 TypeError）。
    """
    ac, sm = harness
    user = User(
        id="U_SR", email="sr@lf.com", hashed_password="x",
        name="自陈测试生", role=UserRole.STUDENT,
    )
    global CURRENT_USER
    CURRENT_USER = user
    return ac, sm, user


async def _seed_user(sm, **kw):
    u = User(**kw)
    async with sm() as s:
        s.add(u)
        await s.commit()
        await s.refresh(u)
    return u


# ══════════════════════════════════════════════════════════════════════
# 一、量表目录与计分
# ══════════════════════════════════════════════════════════════════════

def test_catalog_has_four_instruments_covering_gap_dimensions():
    """目录必须覆盖「行为日志不可观测」的三个输入键。"""
    specs = instrument_catalog.all_instruments()
    assert len(specs) == 4
    inputs = {s.lai_input for s in specs}
    assert inputs == {
        "planned_stop_failures", "sleep_impact", "social_impact", "time_perception_bias",
    }
    # 恰好补上 control / function / cognition 的三处空白
    assert {"control", "function", "cognition"} <= {s.dimension for s in specs}


def test_catalog_fingerprint_is_stable_and_12_hex():
    fp1 = instrument_catalog.catalog_fingerprint()
    fp2 = instrument_catalog.catalog_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 12 and all(c in "0123456789abcdef" for c in fp1)


def test_score_count_instrument_sums():
    """计数题：三题求和，直接作为 LAI 输入（语义 = 本周失败次数）。"""
    out = instrument_catalog.score("SRL-STOP", [3, 2, 4])
    assert out["raw_total"] == 9
    assert out["lai_input"] == "planned_stop_failures"
    assert out["lai_value"] == 9.0


def test_score_likert_normalizes_to_unit_interval():
    """Likert 题：均值线性归一化到 [0,1]；(mean-1)/4。"""
    assert instrument_catalog.score("SLEEP-IMPACT", [1, 1, 1, 1])["lai_value"] == 0.0
    assert instrument_catalog.score("SLEEP-IMPACT", [5, 5, 5, 5])["lai_value"] == 1.0
    mid = instrument_catalog.score("SLEEP-IMPACT", [3, 3, 3, 3])["lai_value"]
    assert mid == pytest.approx(0.5)


def test_score_rejects_wrong_count_and_out_of_range():
    with pytest.raises(ValueError):
        instrument_catalog.score("SRL-STOP", [1, 1])            # 题数不符
    with pytest.raises(ValueError):
        instrument_catalog.score("SRL-STOP", [8, 1, 1])         # 计数题超 7
    with pytest.raises(ValueError):
        instrument_catalog.score("SLEEP-IMPACT", [0, 1, 1, 1])  # Likert 不允许 0
    with pytest.raises(KeyError):
        instrument_catalog.score("NO-SUCH", [1])


# ══════════════════════════════════════════════════════════════════════
# 二、LAI 结构偏差修复（本套测试的核心）
# ══════════════════════════════════════════════════════════════════════

def test_lai_default_remains_backward_compatible():
    """不传 measured_dimensions 时行为与修复前完全一致（保护既有 800+ 用例）。"""
    a = LearningAddictionIndex.assess(
        daily_minutes=100, session_minutes=50, night_ratio=0.2,
        planned_stop_failures=5, sleep_impact=0.5, social_impact=0.5,
    )
    expected = sum(
        a.dimensions[d].raw_score * 100 * LearningAddictionIndex.WEIGHTS[d]
        for d in LearningAddictionIndex.WEIGHTS
    )
    assert a.overall_score == pytest.approx(expected, abs=1e-6)
    assert all(d.measured for d in a.dimensions.values())
    assert a.coverage["complete"] is True
    assert a.coverage["explicit"] is False


def test_unmeasured_dimensions_do_not_count_as_healthy():
    """★ 回归核心：未测维度不得以「默认常量所得的满分」计入综合分。

    旧代码下：control / function 用默认常量 0 算出满分并占 35% 权重 →
    overall 被系统性抬高。新代码下这两维 weighted_score 必须为 0。
    """
    measured = {"time", "motivation", "cognition"}
    a = LearningAddictionIndex.assess(
        daily_minutes=100, session_minutes=50, night_ratio=0.2,
        content_attention_ratio=0.8,
        # 这两个是占位常量：行为日志观测不到
        sleep_impact=0.0, social_impact=0.0,
        measured_dimensions=measured,
    )
    assert a.dimensions["control"].measured is False
    assert a.dimensions["control"].weighted_score == 0.0
    assert a.dimensions["function"].measured is False
    assert a.dimensions["function"].weighted_score == 0.0
    assert a.dimensions["function"].risk_flag is False  # 未测不得报风险
    assert a.coverage["unmeasured"] == ["control", "function"]
    assert a.coverage["complete"] is False
    assert a.coverage["weight_basis"] == pytest.approx(0.65)

    # 只由已测维度构成，权重归一化后仍在 0-100 量纲
    expected = sum(
        a.dimensions[d].raw_score * 100 * (LearningAddictionIndex.WEIGHTS[d] / 0.65)
        for d in measured
    )
    assert a.overall_score == pytest.approx(expected, abs=1e-6)
    assert 0.0 <= a.overall_score <= 100.0


def test_untreated_placeholder_cannot_mask_addiction():
    """只要 control 未测，无论占位常量取什么值都不会抬高综合分。"""
    base = dict(daily_minutes=150, session_minutes=90, night_ratio=0.5,
                content_attention_ratio=0.3)
    a0 = LearningAddictionIndex.assess(
        **base, planned_stop_failures=0, measured_dimensions={"time", "motivation", "cognition"})
    a9 = LearningAddictionIndex.assess(
        **base, planned_stop_failures=999, measured_dimensions={"time", "motivation", "cognition"})
    # control 未测 → 其输入值完全不影响结果
    assert a0.overall_score == pytest.approx(a9.overall_score, abs=1e-9)


def test_lai_rejects_empty_and_unknown_measured_dimensions():
    with pytest.raises(ValueError):
        LearningAddictionIndex.assess(measured_dimensions=set())
    with pytest.raises(ValueError):
        LearningAddictionIndex.assess(measured_dimensions={"time", "nope"})


def test_lai_to_dict_exposes_measurement_provenance():
    a = LearningAddictionIndex.assess(measured_dimensions={"time", "motivation"})
    d = a.to_dict()
    assert d["dimensions"]["control"]["measured"] is False
    assert d["coverage"]["complete"] is False
    assert d["coverage"]["unmeasured"] == ["cognition", "control", "function"]


# ══════════════════════════════════════════════════════════════════════
# 三、聚合服务：新鲜度、覆盖度推导
# ══════════════════════════════════════════════════════════════════════

async def test_coverage_without_any_self_report_is_honest(harness):
    """零自陈数据时：只承认行为代理支撑的 time/motivation，且披露它们是代理。"""
    _, sm = harness
    await _seed_user(sm, id="U_NONE", email="n@lf.com", hashed_password="x",
                     name="无数据", role=UserRole.STUDENT)
    async with sm() as s:
        rep = await coverage_report(s, "U_NONE")
    assert rep["measured"] == ["motivation", "time"]
    assert rep["unmeasured"] == ["cognition", "control", "function"]
    assert rep["complete"] is False
    assert rep["weight_basis"] == pytest.approx(0.55)
    assert set(rep["proxy_dimensions"]) == {"time", "motivation"}
    # 必须明确告知缺哪份量表，而不是只报一个残缺分数
    assert {"SRL-STOP", "SLEEP-IMPACT", "SOCIAL-IMPACT", "TIME-BIAS"} == {
        m["code"] for m in rep["missing_instruments"]
    }


async def test_submitting_self_report_extends_coverage(harness):
    _, sm = harness
    async with sm() as s:
        s.add(SelfReportResponse(
            user_id="U_C", instrument_code="SRL-STOP", answers=[2, 1, 3],
            raw_total=6, normalized=0.2857, lai_input="planned_stop_failures",
            lai_value=6.0, catalog_fingerprint=instrument_catalog.catalog_fingerprint(),
        ))
        await s.commit()
    async with sm() as s:
        rep = await coverage_report(s, "U_C")
        inputs = await lai_inputs_from_self_report(s, "U_C")
    assert "control" in rep["measured"]
    assert rep["weight_basis"] == pytest.approx(0.80)
    assert inputs == {"planned_stop_failures": 6.0}


async def test_stale_self_report_is_ignored(harness):
    """超过有效期的作答不得继续支撑当前评分。"""
    _, sm = harness
    old = datetime.now(UTC) - timedelta(days=MAX_AGE_DAYS + 1)
    async with sm() as s:
        s.add(SelfReportResponse(
            user_id="U_OLD", instrument_code="SRL-STOP", answers=[1, 1, 1],
            raw_total=3, normalized=0.1429, lai_input="planned_stop_failures",
            lai_value=3.0, submitted_at=old,
        ))
        await s.commit()
    async with sm() as s:
        assert await latest_self_report_inputs(s, "U_OLD") == {}
        assert "control" not in await measured_dimensions(s, "U_OLD")


async def test_partial_function_coverage_requires_both_instruments(harness):
    """function 维需要睡眠与社交两份量表齐备才算已测（缺失即未测）。"""
    _, sm = harness
    async with sm() as s:
        s.add(SelfReportResponse(
            user_id="U_F", instrument_code="SLEEP-IMPACT", answers=[4, 4, 4, 4],
            raw_total=16, normalized=0.75, lai_input="sleep_impact", lai_value=0.75,
        ))
        await s.commit()
    async with sm() as s:
        assert "function" not in await measured_dimensions(s, "U_F")
    async with sm() as s:
        s.add(SelfReportResponse(
            user_id="U_F", instrument_code="SOCIAL-IMPACT", answers=[2, 2, 2, 2],
            raw_total=8, normalized=0.25, lai_input="social_impact", lai_value=0.25,
        ))
        await s.commit()
    async with sm() as s:
        assert "function" in await measured_dimensions(s, "U_F")


async def test_latest_wins_per_input(harness):
    _, sm = harness
    for val in (1, 9):
        async with sm() as s:
            s.add(SelfReportResponse(
                user_id="U_L", instrument_code="SRL-STOP", answers=[val, val, val],
                raw_total=val * 3, normalized=val / 7, lai_input="planned_stop_failures",
                lai_value=float(val * 3),
                submitted_at=datetime.now(UTC) - timedelta(minutes=(10 if val == 1 else 0)),
            ))
            await s.commit()
    async with sm() as s:
        got = await lai_inputs_from_self_report(s, "U_L")
    assert got == {"planned_stop_failures": 27.0}


# ══════════════════════════════════════════════════════════════════════
# 四、API 契约
# ══════════════════════════════════════════════════════════════════════

async def test_list_and_catalog(as_student):
    ac, _, _ = as_student
    r = await ac.get("/api/v1/instruments")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 4
    assert len(body["instruments"][0]["items"]) >= 3

    r = await ac.get("/api/v1/instruments/catalog")
    assert r.status_code == 200, r.text
    assert r.json()["fingerprint"] == instrument_catalog.catalog_fingerprint()
    assert "未经独立信效度检验" in r.json()["provenance_notice"]

    r = await ac.get("/api/v1/instruments", params={"dimension": "function"})
    assert r.status_code == 200
    assert {i["code"] for i in r.json()["instruments"]} == {"SLEEP-IMPACT", "SOCIAL-IMPACT"}


async def test_list_rejects_unknown_dimension(as_student):
    ac, _, _ = as_student
    r = await ac.get("/api/v1/instruments", params={"dimension": "nope"})
    assert r.status_code == 400, r.text


async def test_get_single_instrument_and_404(as_student):
    ac, _, _ = as_student
    r = await ac.get("/api/v1/instruments/SRL-STOP")
    assert r.status_code == 200, r.text
    assert r.json()["item_count"] == 3
    assert r.json()["scoring_method"] == "sum_count"

    r = await ac.get("/api/v1/instruments/NO-SUCH")
    assert r.status_code == 404, r.text


async def test_coverage_endpoint_reflects_missing_instruments(as_student):
    ac, _, _ = as_student
    r = await ac.get("/api/v1/instruments/me/coverage")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["complete"] is False
    assert body["weight_basis"] == pytest.approx(0.55)
    assert len(body["missing_instruments"]) == 4
    assert body["lai_inputs"] == {}


async def test_submit_persists_and_extends_coverage(as_student):
    ac, sm, user = as_student
    r = await ac.post("/api/v1/instruments/SRL-STOP/responses",
                      json={"answers": [3, 2, 4], "context": {"phase": "weekly_checkin"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] is True
    assert body["lai_input"] == "planned_stop_failures"
    assert body["lai_value"] == 9.0
    assert "control" in body["coverage"]["measured"]
    # 计分口径被冻结在记录上（可复现性锚点）
    assert body["response"]["catalog_fingerprint"] == instrument_catalog.catalog_fingerprint()
    # 同意状态被标记（不阻断提交）
    assert "research_consent" in body["response"]["context"]

    # 真落库（非仅内存态）
    async with sm() as s:
        rows = (await s.execute(
            SelfReportResponse.__table__.select().where(
                SelfReportResponse.user_id == user.id)
        )).fetchall()
    assert len(rows) == 1

    r = await ac.get("/api/v1/instruments/me/responses")
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = await ac.get("/api/v1/instruments/me/coverage")
    assert r.json()["weight_basis"] == pytest.approx(0.80)


async def test_submit_validation_errors(as_student):
    ac, _, _ = as_student
    r = await ac.post("/api/v1/instruments/SRL-STOP/responses", json={"answers": [1, 1]})
    assert r.status_code == 400, r.text
    r = await ac.post("/api/v1/instruments/SRL-STOP/responses", json={"answers": [9, 1, 1]})
    assert r.status_code == 400, r.text
    r = await ac.post("/api/v1/instruments/NO-SUCH/responses", json={"answers": [1]})
    assert r.status_code == 404, r.text


async def test_responses_are_scoped_to_the_logged_in_user(as_student):
    """不得读到他人作答（user_id 取自登录态，不接受外部传入）。"""
    ac, sm, _ = as_student
    async with sm() as s:
        s.add(SelfReportResponse(
            user_id="SOMEONE_ELSE", instrument_code="SRL-STOP", answers=[1, 1, 1],
            raw_total=3, normalized=0.1429, lai_input="planned_stop_failures", lai_value=3.0,
        ))
        await s.commit()
    r = await ac.get("/api/v1/instruments/me/responses")
    assert r.status_code == 200
    assert r.json()["count"] == 0
