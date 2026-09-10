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

# 冷启动保护: 某个风险档下, 单个 arm 至少被观测到这么多次, 才允许 RL 在该档位
# 接管「选哪个 approach 机制」的决策。
#
# 为什么必须有这个阈值: RL 一旦基于极少量观测接管决策, 单次噪声就会被放大成
# 长期偏好 (Q 的初值 0 + 增量更新 alpha=0.1, 一次偶然高奖励就能让某个 arm 长期
# 霸榜)。在未成年人场景里, 这等于让噪声决定给脆弱状态的学生下发什么干预 ——
# 不可接受。故: 学习可以立刻开始, 接管必须等学够了。
#
# 注意区分两个门 (此前二者被混为一谈, 造成冷启动死锁):
#   * 学习门 (observe): 无条件。只要拿到有效信号就学, 否则 Q 永远起不来。
#   * 决策门 (ready): 需要 MIN_OBS_FOR_DECISION 次观测, 保守放行。
MIN_OBS_FOR_DECISION = 5


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
        """是否已有任何学习发生 (Q 表非空)。

        语义: 「学到过东西」, 而非「学够了可以接管决策」。后者见 :meth:`ready`。
        """
        return any(self.Q.values())

    def ready(self, bucket: str) -> bool:
        """该风险档是否已学够、可以让 RL 接管决策 (保守)。

        判据: 该 bucket 下**至少有一个** arm 的观测次数 ≥ MIN_OBS_FOR_DECISION。
        与 :meth:`trained` 的区别至关重要 —— ``trained()`` 只要 update 过一次就为真,
        若拿它当决策门, 单次观测的噪声就会主导后续的机制选择。
        """
        counts = self.counts.get(bucket)
        if not counts:
            return False
        return any(c >= MIN_OBS_FOR_DECISION for c in counts.values())

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
        """从候选 approach 机制中选一个 (RL 决策); 该档位未学够则回退 None (用规则)。

        决策门用 :meth:`BanditPolicy.ready` 而非 ``trained()``: 前者要求该风险档下
        已有 arm 被观测 MIN_OBS_FOR_DECISION 次, 避免让单次噪声主导机制选择。
        """
        if not self.bandit.ready(_ctx_bucket(risk_tier)):
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

    def ready(self, risk_tier: int) -> bool:
        """该风险档是否学够了、可以让 RL 接管决策。"""
        return self.bandit.ready(_ctx_bucket(risk_tier))
