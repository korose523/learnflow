"""研究知情同意判定与标记测试（博士论文伦理合规）

覆盖：
  1. 成年人本人授权 → True / self_granted
  2. 未成年人自授 → False / minor_without_guardian_consent        （★ 核心规则）
  3. 未成年人由家长授权 → True / guardian_granted                 （★ 核心规则）
  4. granted_by 为空的未成年人 → False
  5. 无同意记录 → None / no_record
  6. 已撤销（revoked_at 非 NULL）→ 视为无效（None / revoked）
  7. 多条记录时取最新的一条
  8. 事件写入后 research_consented 字段值正确
  9. ★ 不阻断：consented=False 的被试提交答题，事件仍然写入
 10. 容错：db 抛异常时返回 None 且不冒泡

使用 tmp_path + SQLite，不污染仓库。learning_events 复合主键在 SQLite 下无法
由 create_all 建表（既有已知问题），故集成测试通过桩替换 record_learning_event
走真实编排器注入路径。
"""
import pytest
import pytest_asyncio
from datetime import datetime, UTC, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
import app.models  # noqa: F401  注册全部表
from app.models.user import User, UserRole
from app.models.consent import ConsentRecord, ConsentType
from app.models.task import Task
from app.services.research_consent import (
    judge_research_consent,
    resolve_research_consent,
    ResearchConsentStatus,
)


# ─── 构造辅助（纯函数测试无需 db）─────────────────────────────
NOW = datetime.now(UTC)


def _rec(user_id: str, granted_by=None, revoked: bool = False, when=None):
    return ConsentRecord(
        user_id=user_id,
        consent_type=ConsentType.DATA_RESEARCH,
        consented_at=when or NOW,
        granted_by=granted_by,
        revoked_at=(when or NOW) if revoked else None,
    )


_STUDENT = User(id="s", role=UserRole.STUDENT)
_PARENT = User(id="p", role=UserRole.PARENT)
_OTHER = User(id="o", role=UserRole.TEACHER)


# ─── 纯函数（同步）分支覆盖 ──────────────────────────────────
def test_adult_self_granted():
    st = judge_research_consent(_rec("a", granted_by=None), is_minor=False)
    assert st == ResearchConsentStatus(True, "self_granted", None)


def test_adult_granted_by_other():
    st = judge_research_consent(_rec("a", granted_by="o"), is_minor=False, granted_by_user=_OTHER)
    assert st == ResearchConsentStatus(True, "granted_by_other", "o")


def test_minor_self_granted_is_invalid():
    # ★ 核心规则：未成年人自授一律无效
    st = judge_research_consent(_rec("s", granted_by="s"), is_minor=True, granted_by_user=_STUDENT)
    assert st == ResearchConsentStatus(False, "minor_without_guardian_consent", "s")


def test_minor_guardian_granted():
    # ★ 核心规则：未成年人由家长授权有效
    st = judge_research_consent(_rec("s", granted_by="p"), is_minor=True, granted_by_user=_PARENT)
    assert st == ResearchConsentStatus(True, "guardian_granted", "p")


def test_minor_granted_by_empty():
    st = judge_research_consent(_rec("s", granted_by=None), is_minor=True, granted_by_user=None)
    assert st == ResearchConsentStatus(False, "minor_without_guardian_consent", None)


def test_minor_granted_by_non_parent():
    # 授权人不是 PARENT → 无效
    st = judge_research_consent(_rec("s", granted_by="o"), is_minor=True, granted_by_user=_OTHER)
    assert st == ResearchConsentStatus(False, "minor_without_guardian_consent", "o")


def test_no_record_is_none():
    # 「没问过」与「问了没同意」必须区分 → None 而非 False
    st = judge_research_consent(None, is_minor=False)
    assert st == ResearchConsentStatus(None, "no_record", None)


def test_revoked_is_invalid_none():
    # 已撤销视为无效 → None / revoked
    st = judge_research_consent(_rec("a", revoked=True), is_minor=False)
    assert st == ResearchConsentStatus(None, "revoked", None)


# ─── 异步 resolve（db 支撑）──────────────────────────────────
@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'consent.db'}", pool_pre_ping=True
    )
    tables = [t for t in Base.metadata.sorted_tables if t.name != "learning_events"]
    async with engine.begin() as conn:
        await conn.run_sync(lambda s: Base.metadata.create_all(s, tables=tables))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed(session, *users, consents=()):
    for u in users:
        session.add(u)
    for c in consents:
        session.add(c)
    await session.commit()


async def test_resolve_adult_self_granted(session_factory):
    async with session_factory() as db:
        adult = User(id="adult", email="a@x.com", name="A", role=UserRole.STUDENT, hashed_password="x")
        # grade 为空 → OTHER → 成年
        await _seed(db, adult, consents=[_rec("adult", granted_by="adult")])
        st = await resolve_research_consent(db, adult)
        assert st.consented is True
        assert st.reason == "self_granted"


async def test_resolve_minor_self_granted_invalid(session_factory):
    async with session_factory() as db:
        minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="五年级")
        await _seed(db, minor, consents=[_rec("minor", granted_by="minor")])
        st = await resolve_research_consent(db, minor)
        assert st.consented is False
        assert st.reason == "minor_without_guardian_consent"


async def test_resolve_minor_guardian_granted(session_factory):
    async with session_factory() as db:
        minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="初一")
        parent = User(id="parent", email="p@x.com", name="P", role=UserRole.PARENT, hashed_password="x")
        await _seed(db, minor, parent, consents=[_rec("minor", granted_by="parent")])
        st = await resolve_research_consent(db, minor)
        assert st.consented is True
        assert st.reason == "guardian_granted"


async def test_resolve_no_record(session_factory):
    async with session_factory() as db:
        minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="五年级")
        await _seed(db, minor)
        st = await resolve_research_consent(db, minor)
        assert st.consented is None
        assert st.reason == "no_record"


async def test_resolve_revoked(session_factory):
    async with session_factory() as db:
        adult = User(id="adult", email="a@x.com", name="A", role=UserRole.STUDENT, hashed_password="x")
        await _seed(db, adult, consents=[_rec("adult", granted_by="adult", revoked=True)])
        st = await resolve_research_consent(db, adult)
        assert st.consented is None
        assert st.reason == "revoked"


async def test_resolve_multi_record_takes_latest(session_factory):
    # 两条记录：旧的未成年人自授（无效）+ 新的家长授权（有效）
    # 取最新一条 → 应判定为家长授权有效
    async with session_factory() as db:
        minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="五年级")
        parent = User(id="parent", email="p@x.com", name="P", role=UserRole.PARENT, hashed_password="x")
        older = _rec("minor", granted_by="minor", when=NOW - timedelta(days=1))
        newer = _rec("minor", granted_by="parent", when=NOW)
        await _seed(db, minor, parent, consents=[older, newer])
        st = await resolve_research_consent(db, minor)
        assert st.consented is True
        assert st.reason == "guardian_granted"


async def test_resolve_db_error_returns_none(session_factory):
    # 容错：db.execute 抛异常 → None + error，且不冒泡
    class BoomDB:
        async def execute(self, *a, **k):
            raise RuntimeError("db boom")

    minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="五年级")
    st = await resolve_research_consent(BoomDB(), minor)
    assert st.consented is None
    assert st.reason == "error"


async def test_resolve_none_db_or_user():
    minor = User(id="minor", email="m@x.com", name="M", role=UserRole.STUDENT, hashed_password="x", grade="五年级")
    assert (await resolve_research_consent(None, minor)).reason == "error"
    assert (await resolve_research_consent("not-a-db", None)).reason == "error"


# ─── 集成：事件写入 + 不阻断（走真实编排器注入路径）─────────────
async def test_orchestrator_marks_and_does_not_block():
    """★ 不阻断：未取得有效同意的被试提交，事件仍写入且标记为 False/None。"""
    from unittest.mock import patch
    from sqlalchemy.pool import StaticPool
    from app.services.learning_orchestrator import LearningOrchestrator
    from app.services.anti_addiction_compliance import MinorProtectionEngine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name != "learning_events"]
        await conn.run_sync(lambda s: Base.metadata.create_all(s, tables=tables))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add(User(id="minor-self", email="ms@x.com", name="MS", role=UserRole.STUDENT, hashed_password="x", grade="五年级"))
        db.add(User(id="parent", email="p@x.com", name="P", role=UserRole.PARENT, hashed_password="x"))
        db.add(User(id="minor-ok", email="mo@x.com", name="MO", role=UserRole.STUDENT, hashed_password="x", grade="初一"))
        db.add(User(id="minor-none", email="mn@x.com", name="MN", role=UserRole.STUDENT, hashed_password="x", grade="高二"))
        # 学生自授
        db.add(_rec("minor-self", granted_by="minor-self"))
        # 家长授权
        db.add(_rec("minor-ok", granted_by="parent"))
        # minor-none 无同意记录
        db.add(Task(id="t1", content="2+3=?", topic="math", difficulty=3, correct_answer="5", explanation="x"))
        await db.commit()

        captured = []

        async def fake_record(db_session, **kwargs):
            captured.append(kwargs)
            return None

        with patch(
            "app.services.learning_orchestrator.record_learning_event", new=fake_record
        ), patch.object(
            MinorProtectionEngine, "_is_night_time", classmethod(lambda cls, cfg, t=None: False)
        ), patch(
            "app.services.learning_orchestrator.random.random", new=lambda: 0.05
        ):
            task = await db.get(Task, "t1")

            # 9a) 自授未成年人：必须成功且事件写入，标记 False
            minor_self = await db.get(User, "minor-self")
            resp = await LearningOrchestrator.process_submission(
                minor_self, task, {"answer": "5", "hints_used": 0}, db
            )
            assert resp["is_correct"] is True
            assert len(captured) > 0, "事件应写入（不阻断）"
            for ev in captured:
                assert ev["research_consented"] is False

            # 9b) 家长授权未成年人：标记 True
            captured.clear()
            minor_ok = await db.get(User, "minor-ok")
            await LearningOrchestrator.process_submission(
                minor_ok, task, {"answer": "5", "hints_used": 0}, db
            )
            assert len(captured) > 0
            for ev in captured:
                assert ev["research_consented"] is True

            # 9c) 无记录未成年人：事件仍写入，标记 None（未知，不阻断）
            captured.clear()
            minor_none = await db.get(User, "minor-none")
            await LearningOrchestrator.process_submission(
                minor_none, task, {"answer": "5", "hints_used": 0}, db
            )
            assert len(captured) > 0, "未知同意状态的事件仍应写入（不阻断）"
            for ev in captured:
                assert ev["research_consented"] is None

    await engine.dispose()
