"""AI 实时分析层单元测试 —— 覆盖数值工具/特征/风险模型/RL/LLM护栏/因果/API。"""
from __future__ import annotations

import math
import time

import pytest

from app.services._ml_utils import matmul, ols, auc, dot, sigmoid, tanh
from app.services.feature_store import FeatureStore, FEATURE_KEYS, F
from app.services.ml_risk_model import TemporalRiskModel
from app.services.rl_arbitrator import RLArbitrator, BanditPolicy
from app.services.mechanism_arbitrator import MechanismArbitrator, MechanismContext
from app.services.mechanism_registry import Effect, EffectType
from app.services.llm_intervention import generate_intervention, _SAFE_TEMPLATE
from app.services.ollama_client import get_ollama, MockOllama
from app.services.causal_effects import estimate_mechanism_effect


# ── 1. 数值工具 ───────────────────────────────────────────────
def test_matmul_identity():
    I = [[1.0, 0.0], [0.0, 1.0]]
    v = [3.0, 4.0]
    assert matmul(I, [v])[0] == pytest.approx(v)


def test_ols_exact():
    # y = 2*x1 + 3*x2 + 1  -> 含截距, 末位应为 1
    X = [[1.0, 2.0], [2.0, 1.0], [0.0, 1.0], [3.0, 3.0]]
    y = [2 * a + 3 * b + 1 for a, b in X]
    w = ols(X, y, l2=0.0)
    assert w[0] == pytest.approx(2.0, abs=1e-6)
    assert w[1] == pytest.approx(3.0, abs=1e-6)
    assert w[2] == pytest.approx(1.0, abs=1e-6)  # 截距


def test_auc_perfect():
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    assert auc(y, s) == pytest.approx(1.0)


def test_activations():
    assert sigmoid(0) == pytest.approx(0.5)
    assert tanh(0) == pytest.approx(0.0)
    assert 0.0 < sigmoid(5) < 1.0


# ── 2. 特征存储 ──────────────────────────────────────────────
def _ts_with_hour(hour: int) -> float:
    """生成本地时区下指定小时的 epoch (绕开 UTC 偏移)。"""
    t = time.localtime()
    st = time.struct_time((t.tm_year, t.tm_mon, t.tm_mday, hour, 0, 0,
                           0, 0, t.tm_isdst))
    return time.mktime(st)


def _event(uid, is_correct=True, night=False, hints=0, ts=None):
    ts_event = ts if ts is not None else _ts_with_hour(23 if night else 10)
    return {"user_id": uid, "event_type": "ANSWERED", "is_correct": is_correct,
            "hints_used": hints, "thinking_ms": 30000, "skipped": False,
            "created_at": ts_event,
            "session_id": "S1",
            "decision_snapshot": {"fused_d": 500, "zone": "normal"}}


def test_feature_vector_length_and_night():
    fs = FeatureStore()
    for _ in range(10):
        fs.ingest(_event("u1", is_correct=True, night=False))
    for _ in range(10):
        fs.ingest(_event("u2", is_correct=False, night=True))
    v1 = fs.feature_vector("u1")
    v2 = fs.feature_vector("u2")
    assert len(v1) == F == len(FEATURE_KEYS)
    night_idx = FEATURE_KEYS.index("night_ratio")
    assert v2[night_idx] > v1[night_idx]  # 夜间事件越多, 夜间比例越高


# ── 3. 时序风险模型 ──────────────────────────────────────────
def _make_xy(n=120, seed=1):
    import random
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        # 标签由 night_ratio 主导, 其余加噪
        night = rng.random()
        row = [rng.random() for _ in range(F)]
        row[FEATURE_KEYS.index("night_ratio")] = night
        X.append(row)
        y.append(1 if night > 0.5 else 0)
    return X, y


def test_ml_risk_train_auc():
    X, y = _make_xy()
    m = TemporalRiskModel(seed=7)
    m.train_batch(X, y, epochs=30)
    ev = m.evaluate(X, y)
    assert ev["auroc"] > 0.5  # 应能学会 night_ratio→label
    # 预测值在 [0,1]
    p = m.predict("nope")  # 空用户 -> 全 0 特征
    assert 0.0 <= p <= 1.0
    # 风险档映射
    assert m.risk_tier(0.7) == 3
    assert m.risk_tier(0.1) == 0


def test_online_update_range():
    m = TemporalRiskModel(seed=3)
    r = m.online_update(_event("u9", is_correct=True))
    assert 0.0 <= r <= 1.0


def test_save_load_roundtrip(tmp_path):
    m = TemporalRiskModel(seed=5)
    X, y = _make_xy(60)
    m.train_batch(X, y, epochs=10)
    p = str(tmp_path / "m.json")
    m.save(p)
    m2 = TemporalRiskModel.load(p)
    assert m2.W2 == m.W2
    assert m2.predict("x") == m.predict("x")


# ── 4. RL 仲裁器 ─────────────────────────────────────────────
def test_bandit_learn():
    b = BanditPolicy(seed=1)
    assert not b.trained()
    ctx = "t2"
    # arm A 给高奖励, arm B 给低奖励
    for _ in range(40):
        a = b.choose(ctx, ["A", "B"])
        b.update(ctx, a, 1.0 if a == "A" else 0.0)
    assert b.trained()
    # 学完后更可能选 A
    picks = [b.choose(ctx, ["A", "B"]) for _ in range(50)]
    assert picks.count("A") > picks.count("B")


def test_rl_arbitrator_fallback_when_untrained():
    arb = RLArbitrator()
    effects = [Effect("LF-M44", EffectType.NUDGE, {}, priority=70),
               Effect("LF-M33", EffectType.REMINDER, {}, priority=60)]
    # 未训练 -> 回退 None (交由规则仲裁器)
    assert arb.select_mechanism(MechanismContext("u"), effects, risk_tier=2) is None


def test_rl_arbitrator_choose_after_training():
    arb = RLArbitrator()
    effects = [Effect("LF-M44", EffectType.NUDGE, {}, priority=70),
               Effect("LF-M33", EffectType.REMINDER, {}, priority=60)]
    # 手动训练 bandit: t2 下 A 优于 B
    for _ in range(40):
        a = arb.bandit.choose("t2", ["LF-M44", "LF-M33"])
        arb.bandit.update("t2", a, 1.0 if a == "LF-M44" else 0.0)
    chosen = arb.select_mechanism(MechanismContext("u"), effects, risk_tier=2)
    assert chosen in ("LF-M44", "LF-M33")


# ── 5. LLM 干预 + 暗黑模式护栏 ───────────────────────────────
def test_ollama_fallback_safe():
    o = get_ollama()
    assert hasattr(o, "generate")
    # 无本地服务时返回 MockOllama, 文本非空
    assert isinstance(o, MockOllama) or o.available()


def test_llm_guardrail_strips_dark_pattern(monkeypatch):
    class Evil:
        def generate(self, prompt, system=None):
            return "你已经连胜 30 天了，不赶紧学就落后同学了！"
    monkeypatch.setattr("app.services.llm_intervention.get_ollama", lambda: Evil())
    out = generate_intervention({"name": "小明"}, risk=0.7)
    assert out["safe"] is True
    assert out["message"] == _SAFE_TEMPLATE
    assert out["mechanism_id"] == "LF-M53"  # 高风险 -> 健康推开


def test_llm_safe_output_passthrough(monkeypatch):
    class Good:
        def generate(self, prompt, system=None):
            return "你今天很专注，记得喝口水休息一下哦。"
    monkeypatch.setattr("app.services.llm_intervention.get_ollama", lambda: Good())
    out = generate_intervention({"name": "小红"}, risk=0.2)
    assert out["safe"] is True
    assert "休息" in out["message"]


# ── 6. DML 因果效应 ──────────────────────────────────────────
def test_dml_ate_recovers_effect():
    # 处理 T 正向影响结局 Y, 混淆 C 同时影响 T 与 Y
    import random
    rng = random.Random(42)
    rows = []
    for _ in range(400):
        c = rng.uniform(0, 1)
        t = 1 if rng.random() < (0.3 + 0.4 * c) else 0
        y = 2.5 * t + 1.0 * c + rng.gauss(0, 0.3)
        rows.append({"treatment": t, "outcome": y, "covariates": [c]})
    res = estimate_mechanism_effect(rows)
    assert res["ate"] == pytest.approx(2.5, abs=0.5)
    assert res["n"] == 400


# ── 7. 实时分析 API ─────────────────────────────────────────
def test_analytics_endpoints():
    import asyncio
    from fastapi.testclient import TestClient
    from app.main import app
    import app.main as main_mod

    # 路由在 lifespan 注册, TestClient 默认不触发 -> 显式注册
    asyncio.run(main_mod._register_routers(app))

    client = TestClient(app)

    now = time.time()
    evs = [_event("astu1", is_correct=False, night=True, ts=now) for _ in range(15)]
    r = client.post("/api/v1/analytics/ingest", json={"events": evs})
    assert r.status_code == 200
    assert r.json()["ingested"] == 15

    r = client.get("/api/v1/analytics/student/astu1/risk")
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["ml_risk"] <= 1.0
    assert "top_factors" in body

    r = client.get("/api/v1/analytics/class/C1/risk", params={"user_ids": ["astu1"]})
    assert r.status_code == 200
    assert r.json()["students"] == 1

    r = client.get("/api/v1/analytics/class/C1/early-warning",
                   params={"user_ids": ["astu1"], "threshold": 0.0})
    assert r.status_code == 200
    assert r.json()["count"] >= 1


# ── 8. RL 接入 MechanismArbitrator 在线决策闭环 ──────────────────
def _trained_rl(prefer: str = "LF-M44") -> RLArbitrator:
    """造一个已训练的 RL 仲裁器: 在 t2 风险档下 prefer 机制优于另一 approach。"""
    rl = RLArbitrator(rule_arbitrator=MechanismArbitrator())
    others = ["LF-M33", "LF-M08", "LF-M07"]  # 任选一个非 prefer 的作对照组
    other = next(o for o in others if o != prefer)
    for _ in range(40):
        a = rl.bandit.choose("t2", [prefer, other])
        rl.bandit.update("t2", a, 1.0 if a == prefer else 0.0)
    rl.bandit.epsilon = 0.0  # 测试确定性: 永远选 Q 最大者
    assert rl.trained()
    return rl


def test_mechanism_arbitrator_rl_selects_single_approach():
    arb = MechanismArbitrator()
    rl = _trained_rl(prefer="LF-M44")
    arb.rl_arbitrator = rl

    effects = [
        Effect("LF-M44", EffectType.NUDGE, {}, priority=70),       # approach, RL 偏好
        Effect("LF-M33", EffectType.REMINDER, {}, priority=60),    # approach, 应被丢弃
        Effect("LF-M19", EffectType.BADGE, {}, priority=50),      # neutral, 不受影响
    ]
    # lai_risk=0.4 -> 风险档 t2 (与 _trained_rl 训练桶一致), 且不触发 LAI 冷却
    # (0.9*0.4=0.36 < 0.4), 从而隔离出纯 RL 选择行为。
    ctx = MechanismContext("u_loop", session_id="s1")
    out = arb.arbitrate(ctx, effects, lai_risk=0.4)
    delivered = [e.mechanism_id for e in out]

    # RL 在 t2 选中 LF-M44 -> 其余 approach (LF-M33) 被丢弃, neutral (LF-M19) 保留
    assert "LF-M44" in delivered
    assert "LF-M33" not in delivered
    assert "LF-M19" in delivered
    approach_delivered = [m for m in delivered
                          if arb._DIRECTION.get(m) == "approach"]
    assert approach_delivered == ["LF-M44"]
    # 反馈目标已记录
    assert arb._rl_pending[("u_loop", "s1")]["chosen_id"] == "LF-M44"


def test_mechanism_arbitrator_rl_untrained_is_noop():
    """未注入/未训练的 RL -> 行为完全不变 (向后兼容)。"""
    # 不注入 rl_arbitrator, 且不传 lai_risk (避免 LAI 冷却干扰, 单独隔离 RL 行为)
    arb = MechanismArbitrator()
    effects = [
        Effect("LF-M44", EffectType.NUDGE, {}, priority=70),
        Effect("LF-M33", EffectType.REMINDER, {}, priority=60),
    ]
    out = arb.arbitrate(MechanismContext("u"), effects)
    delivered = [e.mechanism_id for e in out]
    assert "LF-M44" in delivered and "LF-M33" in delivered
    assert arb.report_lai_feedback("u", 50.0, 70.0) is None  # 无反馈目标


def test_report_lai_feedback_updates_bandit():
    """LAI 改善应作为正奖励回灌到 bandit 的 (风险档, 机制) 状态-动作对。"""
    arb = MechanismArbitrator()
    rl = _trained_rl(prefer="LF-M44")
    arb.rl_arbitrator = rl

    effects = [Effect("LF-M44", EffectType.NUDGE, {}, priority=70),
               Effect("LF-M33", EffectType.REMINDER, {}, priority=60)]
    ctx = MechanismContext("u_fb", session_id="s_fb")
    arb.arbitrate(ctx, effects, lai_risk=0.4)  # t2, 不触发冷却

    bucket = "t2"
    before = rl.bandit.counts[bucket]["LF-M44"]
    reward = arb.report_lai_feedback("u_fb", lai_before=50.0, lai_after=72.0,
                                     session_id="s_fb")
    assert reward == pytest.approx(0.22)  # (72-50)/100
    assert rl.bandit.counts[bucket]["LF-M44"] == before + 1
    assert rl.bandit.Q[bucket]["LF-M44"] > 0.0  # Q 朝正奖励方向移动


def test_report_lai_feedback_negative_on_deterioration():
    """LAI 恶化 -> 负奖励; 未注入 RL 时安全返回 None。"""
    arb = MechanismArbitrator()
    rl = _trained_rl(prefer="LF-M44")
    arb.rl_arbitrator = rl
    effects = [Effect("LF-M44", EffectType.NUDGE, {}, priority=70),
               Effect("LF-M33", EffectType.REMINDER, {}, priority=60)]
    arb.arbitrate(MechanismContext("u_neg", session_id="s_neg"), effects, lai_risk=0.4)
    reward = arb.report_lai_feedback("u_neg", lai_before=80.0, lai_after=60.0,
                                     session_id="s_neg")
    assert reward == pytest.approx(-0.20)  # (60-80)/100
    # 未注入 RL 的仲裁器调用应安全跳过
    plain = MechanismArbitrator()
    assert plain.report_lai_feedback("x", 50.0, 70.0) is None

