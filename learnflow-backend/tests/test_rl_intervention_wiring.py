"""AI 行为管控链路接线测试 —— RL 在线学习 / 容错 / LLM 规则兜底。

覆盖任务要求:
  * RL 接线后: 给定可观测前后信号, observe 被调用、Q 值更新
  * 容错: RL 抛异常时主流程 (答题提交) 不受影响
  * LLM 不可用时回退规则话术; LLM 可用时个性化生效
"""
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
import app.models  # noqa: F401  (注册全部表)
from app.models.user import User, UserRole
from app.models.task import Task

from app.services.mechanism_arbitrator import MechanismArbitrator
from app.services.mechanism_registry import Effect, EffectType
from app.services.rl_arbitrator import RLArbitrator
from app.services.ollama_client import MockOllama
from app.services.anti_addiction_compliance import MinorProtectionEngine
from app.services.risk_monitor import RiskMonitor, RiskAssessment, RiskLevel

import app.services.learning_orchestrator as orchestrator
from app.services.learning_orchestrator import LearningOrchestrator


def _trained_rl(bucket: str = "t0", prefer: str = "LF-M44") -> RLArbitrator:
    """造一个已训练的 RL 仲裁器: 在指定风险桶下 prefer 机制优于对照组。"""
    rl = RLArbitrator(rule_arbitrator=MechanismArbitrator())
    others = ["LF-M33", "LF-M08", "LF-M07"]
    other = next(o for o in others if o != prefer)
    for _ in range(40):
        a = rl.bandit.choose(bucket, [prefer, other])
        rl.bandit.update(bucket, a, 1.0 if a == prefer else 0.0)
    rl.bandit.epsilon = 0.0  # 确定性: 永远选 Q 最大者
    return rl


def _fomo_effect():
    return Effect(
        mechanism_id="LF-M44",
        effect_type=EffectType.NUDGE,
        payload={"message": "规则文案", "type": "fomo"},
        priority=70,
        cost=1.5,
        user_visible=True,
        health_critical=False,
        direction="approach",
    )


async def _make_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables
                  if t.name != "learning_events"]
        await conn.run_sync(lambda s: Base.metadata.create_all(s, tables=tables))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def test_rl_observe_called_and_q_updated(monkeypatch):
    """RL 接线后: 可观测信号下, observe 被调用、Q 值朝正奖励移动。"""
    engine, factory = await _make_db()
    async with factory() as db:
        db.add(User(id="rl-u", email="rl_u@x.com", name="RL",
                    role=UserRole.STUDENT, hashed_password="x", grade="五年级"))
        db.add(Task(id="rl-t", content="2+3=?", topic="math",
                    difficulty=3, correct_answer="5", explanation="相加"))
        await db.commit()
        user = await db.get(User, "rl-u")
        task = await db.get(Task, "rl-t")

        rl = _trained_rl("t0")
        arb = MechanismArbitrator(rl_arbitrator=rl)
        monkeypatch.setattr(orchestrator, "_FOMO_ARBITRATOR", arb)
        monkeypatch.setattr(
            orchestrator.FOMOEngine, "generate_fomo_nudge",
            staticmethod(lambda challenges: _fomo_effect()),
        )
        _before = rl.bandit.counts["t0"]["LF-M44"]

        with patch("app.services.learning_orchestrator.record_learning_event",
                   new=AsyncMock()), \
             patch.object(MinorProtectionEngine, "_is_night_time",
                          classmethod(lambda cls, cfg, t=None: False)), \
             patch.object(RiskMonitor, "assess",
                          classmethod(lambda cls, snapshots: RiskAssessment(level=RiskLevel.NORMAL))), \
             patch("app.services.learning_orchestrator.random.random", new=lambda: 0.05):
            resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "5", "hints_used": 0}, db)

        assert resp["is_correct"] is True
        assert resp["fomo_nudge"] is not None
        # Q 表已更新: t0 桶下 LF-M44 被观测一次, 且掌握度提升 -> Q 为正
        assert rl.bandit.counts["t0"]["LF-M44"] == _before + 1
        assert rl.bandit.Q["t0"]["LF-M44"] > 0.0

    await engine.dispose()


async def test_rl_fault_tolerance_does_not_break_submission(monkeypatch):
    """容错: RL observe 抛异常时, 答题提交仍成功返回 (不 500)。"""
    engine, factory = await _make_db()
    async with factory() as db:
        db.add(User(id="rl-f", email="rl_f@x.com", name="RLF",
                    role=UserRole.STUDENT, hashed_password="x", grade="五年级"))
        db.add(Task(id="rl-ft", content="2+3=?", topic="math",
                    difficulty=3, correct_answer="5", explanation="相加"))
        await db.commit()
        user = await db.get(User, "rl-f")
        task = await db.get(Task, "rl-ft")

        rl = _trained_rl("t0")
        _before = rl.bandit.counts["t0"]["LF-M44"]
        # 让 observe 必然抛异常
        def _boom(*args, **kwargs):
            raise RuntimeError("simulated RL failure")
        monkeypatch.setattr(rl, "observe", _boom)
        arb = MechanismArbitrator(rl_arbitrator=rl)
        monkeypatch.setattr(orchestrator, "_FOMO_ARBITRATOR", arb)
        monkeypatch.setattr(
            orchestrator.FOMOEngine, "generate_fomo_nudge",
            staticmethod(lambda challenges: _fomo_effect()),
        )

        with patch("app.services.learning_orchestrator.record_learning_event",
                   new=AsyncMock()), \
             patch.object(MinorProtectionEngine, "_is_night_time",
                          classmethod(lambda cls, cfg, t=None: False)), \
             patch.object(RiskMonitor, "assess",
                          classmethod(lambda cls, snapshots: RiskAssessment(level=RiskLevel.NORMAL))), \
             patch("app.services.learning_orchestrator.random.random", new=lambda: 0.05):
            # 不应抛出
            resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "5", "hints_used": 0}, db)

        assert resp["is_correct"] is True
        # observe 抛异常被容错捕获 -> Q 计数未变 (未被污染), 但主流程完好
        assert rl.bandit.counts["t0"]["LF-M44"] == _before

    await engine.dispose()


async def test_llm_unavailable_falls_back_to_rule_message(monkeypatch):
    """LLM 不可用 (ollama 未启动) 时, 回退到既有规则话术。"""
    engine, factory = await _make_db()
    async with factory() as db:
        db.add(User(id="llm-u", email="llm_u@x.com", name="LLM",
                    role=UserRole.STUDENT, hashed_password="x", grade="五年级"))
        db.add(Task(id="llm-t", content="2+3=?", topic="math",
                    difficulty=3, correct_answer="5", explanation="相加"))
        await db.commit()
        user = await db.get(User, "llm-u")
        task = await db.get(Task, "llm-t")

        # ollama 不可用 -> MockOllama (available()==False) -> 回退规则话术
        import app.services.llm_intervention as llm_mod
        monkeypatch.setattr(llm_mod, "get_ollama", lambda: MockOllama())
        monkeypatch.setattr(
            orchestrator.FOMOEngine, "generate_fomo_nudge",
            staticmethod(lambda challenges: _fomo_effect()),
        )

        with patch("app.services.learning_orchestrator.record_learning_event",
                   new=AsyncMock()), \
             patch.object(MinorProtectionEngine, "_is_night_time",
                          classmethod(lambda cls, cfg, t=None: False)), \
             patch.object(RiskMonitor, "assess",
                          classmethod(lambda cls, snapshots: RiskAssessment(level=RiskLevel.NORMAL))), \
             patch("app.services.learning_orchestrator.random.random", new=lambda: 0.05):
            resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "5", "hints_used": 0}, db)

        assert resp["fomo_nudge"] is not None
        assert resp["fomo_nudge"]["message"] == "规则文案"

    await engine.dispose()


async def test_llm_available_personalizes_message(monkeypatch):
    """LLM 可用时, 个性化话术生效 (且通过暗黑模式护栏)。"""
    engine, factory = await _make_db()
    async with factory() as db:
        db.add(User(id="llm-p", email="llm_p@x.com", name="LLMP",
                    role=UserRole.STUDENT, hashed_password="x", grade="五年级"))
        db.add(Task(id="llm-pt", content="2+3=?", topic="math",
                    difficulty=3, correct_answer="5", explanation="相加"))
        await db.commit()
        user = await db.get(User, "llm-p")
        task = await db.get(Task, "llm-pt")

        class FakeOllama:
            def available(self):
                return True
            def generate(self, prompt, system=None):
                return "你今天很专注，记得喝口水休息一下哦。"

        import app.services.llm_intervention as llm_mod
        monkeypatch.setattr(llm_mod, "get_ollama", lambda: FakeOllama())
        monkeypatch.setattr(
            orchestrator.FOMOEngine, "generate_fomo_nudge",
            staticmethod(lambda challenges: _fomo_effect()),
        )

        with patch("app.services.learning_orchestrator.record_learning_event",
                   new=AsyncMock()), \
             patch.object(MinorProtectionEngine, "_is_night_time",
                          classmethod(lambda cls, cfg, t=None: False)), \
             patch.object(RiskMonitor, "assess",
                          classmethod(lambda cls, snapshots: RiskAssessment(level=RiskLevel.NORMAL))), \
             patch("app.services.learning_orchestrator.random.random", new=lambda: 0.05):
            resp = await LearningOrchestrator.process_submission(
                user, task, {"answer": "5", "hints_used": 0}, db)

        assert resp["fomo_nudge"] is not None
        assert resp["fomo_nudge"]["message"] == "你今天很专注，记得喝口水休息一下哦。"

    await engine.dispose()
