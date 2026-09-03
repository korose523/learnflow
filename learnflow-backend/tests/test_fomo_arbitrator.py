"""FOMO 引擎迁移回归测试 — 验证 LF-M44 经 MechanismArbitrator 三层漏斗下发,
以及 LF-M52 (未成年保护) 命中时 Layer1 健康一票否决丢弃 FOMO (治理 §3.4.2)。
"""
from app.services.mechanism_arbitrator import MechanismArbitrator
from app.services.mechanism_registry import (
    Effect,
    EffectType,
    MechanismContext,
)
from app.services.deep_addiction_engine import FOMOEngine


class TestFOMOArbitration:
    def _fomo_effect(self):
        return FOMOEngine.generate_fomo_nudge([{
            "id": "weekend_warrior",
            "name": "周末勇士",
            "desc": "x",
            "window": "weekend",
            "time_remaining": "本周末结束",
        }])

    def test_fomo_alone_delivered(self):
        arb = MechanismArbitrator()
        delivered = arb.arbitrate(MechanismContext(user_id="u1"), [self._fomo_effect()])
        ids = [e.mechanism_id for e in delivered]
        assert "LF-M44" in ids

    def test_fomo_dropped_when_minor_protection(self):
        arb = MechanismArbitrator()
        fomo_effect = self._fomo_effect()
        minor_veto = Effect(
            mechanism_id="LF-M52",
            effect_type=EffectType.NOTIFICATION,
            payload={"reason": "minor_protection_veto"},
            priority=100,
            cost=0.0,
            user_visible=False,
            health_critical=True,
            direction="withdraw",
        )
        delivered = arb.arbitrate(MechanismContext(user_id="u2"), [fomo_effect, minor_veto])
        ids = {e.mechanism_id for e in delivered}
        # Layer1 健康一票否决: 丢弃全部 approach (含 FOMO), 保留 LF-M52
        assert "LF-M44" not in ids
        assert "LF-M52" in ids

    def test_direction_map(self):
        # 直接校验仲裁器语义方向表
        assert MechanismArbitrator._DIRECTION["LF-M44"] == "approach"
        assert MechanismArbitrator._DIRECTION["LF-M52"] == "withdraw"
