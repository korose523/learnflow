"""RL 仲裁器 —— contextual bandit 在线学习「何时下发哪个干预机制」。

冷启动 / 未训练时**回退到规则 MechanismArbitrator** (安全兜底, 保守偏置不变)。
训练后, 它在规则仲裁器之上做「在候选 approach 机制中, 当前风险档下下发哪一个
收益最高」的决策, 用真实 LAI 改善/风险下降作为奖励信号做在线学习。
"""
from __future__ import annotations

import json
import random
from typing import Dict, List, Optional

from app.services.mechanism_arbitrator import MechanismArbitrator, MechanismContext
from app.services.mechanism_registry import Effect

EPSILON = 0.15
ALPHA = 0.1


def _ctx_bucket(risk_tier: int) -> str:
    return f"t{risk_tier}"


class BanditPolicy:
    def __init__(self, epsilon: float = EPSILON, alpha: float = ALPHA, seed: int = 20260906):
        self.epsilon = epsilon
        self.alpha = alpha
        self.rng = random.Random(seed)
        self.Q: Dict[str, Dict[str, float]] = {}
        self.counts: Dict[str, Dict[str, int]] = {}

    def _ensure(self, bucket: str, arm: str) -> None:
        self.Q.setdefault(bucket, {})
        self.Q[bucket].setdefault(arm, 0.0)
        self.counts.setdefault(bucket, {})
        self.counts[bucket].setdefault(arm, 0)

    def choose(self, bucket: str, arms: List[str]) -> Optional[str]:
        if not arms:
            return None
        for a in arms:
            self._ensure(bucket, a)
        if self.rng.random() < self.epsilon:
            return self.rng.choice(arms)
        return max(arms, key=lambda a: self.Q[bucket][a])

    def update(self, bucket: str, arm: str, reward: float) -> None:
        self._ensure(bucket, arm)
        q = self.Q[bucket][arm]
        self.Q[bucket][arm] = q + self.alpha * (reward - q)
        self.counts[bucket][arm] += 1

    def trained(self) -> bool:
        return any(self.Q.values())

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"Q": self.Q, "counts": self.counts,
                       "epsilon": self.epsilon, "alpha": self.alpha}, f)

    @classmethod
    def load(cls, path: str) -> "BanditPolicy":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        p = cls(epsilon=d.get("epsilon", EPSILON), alpha=d.get("alpha", ALPHA))
        p.Q, p.counts = d["Q"], d["counts"]
        return p


class RLArbitrator:
    """包装 BanditPolicy: 在规则仲裁器之上做送达决策的学习。"""

    def __init__(self, rule_arbitrator: Optional[MechanismArbitrator] = None):
        self.rule = rule_arbitrator or MechanismArbitrator()
        self.bandit = BanditPolicy()

    def select_mechanism(self, ctx: MechanismContext, effects: List[Effect],
                         risk_tier: int) -> Optional[str]:
        """从候选 approach 机制中选一个 (RL 决策); 未训练则回退 None (用规则)。"""
        if not self.bandit.trained():
            return None
        approach = [e.mechanism_id for e in effects
                    if self.rule._DIRECTION.get(e.mechanism_id) == "approach"]
        if not approach:
            return None
        return self.bandit.choose(_ctx_bucket(risk_tier), approach)

    def observe(self, risk_tier: int, chosen_id: str, reward: float) -> None:
        self.bandit.update(_ctx_bucket(risk_tier), chosen_id, reward)

    def trained(self) -> bool:
        return self.bandit.trained()
