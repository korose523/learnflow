"""时序成瘾风险模型 (纯 Python, 可训练)。

架构: 1 隐藏层 MLP (tanh) + logistic 输出; 在线维护每用户隐藏态。
时序动态由 ``FeatureStore`` 的滚动窗口聚合承载 — 特征本身编码了近期行为趋势,
因此模型以特征向量为输入即可感知「成瘾进度」。可训练:
``train_batch`` 用 SGD + logistic 损失; 支持以本项目 LAI 引擎生成 **proxy 标签**
做自监督预训练, 再辅以少量真人成瘾量表标注做微调。
"""
from __future__ import annotations

import json
import math
import random
from typing import Dict, List, Optional

from app.services._ml_utils import dot, sigmoid, tanh, auc
from app.services.feature_store import FeatureStore, FEATURE_KEYS, F

DEFAULT_H = 16
LR = 0.05
EPOCHS = 40
L2 = 1e-3


class TemporalRiskModel:
    def __init__(self, hidden: int = DEFAULT_H, lr: float = LR,
                 epochs: int = EPOCHS, l2: float = L2, seed: int = 20260906):
        self.H = hidden
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2
        rng = random.Random(seed)
        scale = (1.0 / (F ** 0.5)) ** 0.5
        self.W1 = [[rng.uniform(-scale, scale) for _ in range(F)] for _ in range(hidden)]
        self.b1 = [0.0] * hidden
        self.W2 = [rng.uniform(-scale, scale) for _ in range(hidden)]
        self.b2 = 0.0
        self._hidden: Dict[str, List[float]] = {}
        self.store = FeatureStore()

    # ---- forward ----
    def _hidden_act(self, x: List[float]) -> List[float]:
        return [tanh(dot(self.W1[i], x) + self.b1[i]) for i in range(self.H)]

    def _forward(self, x: List[float]):
        h = self._hidden_act(x)
        return sigmoid(dot(self.W2, h) + self.b2), h

    # ---- online ----
    def online_update(self, event: dict) -> float:
        """摄入一个事件, 返回该用户当前风险概率 (0-1)。"""
        uid = event.get("user_id", "")
        self.store.ingest(event)
        x = self.store.feature_vector(uid)
        h = self._hidden_act(x)
        self._hidden[uid] = h
        return sigmoid(dot(self.W2, h) + self.b2)

    def predict(self, user_id: str) -> float:
        x = self.store.feature_vector(user_id)
        p, _ = self._forward(x)
        return p

    @staticmethod
    def risk_tier(p: float) -> int:
        if p < 0.15:
            return 0
        if p < 0.35:
            return 1
        if p < 0.6:
            return 2
        return 3

    # ---- train ----
    def train_batch(self, X: List[List[float]], y: List[float],
                    lr: Optional[float] = None, epochs: Optional[int] = None) -> List[float]:
        lr = lr or self.lr
        epochs = epochs or self.epochs
        n = len(X)
        if n == 0:
            return []
        losses = []
        for ep in range(epochs):
            order = list(range(n))
            random.Random(ep).shuffle(order)
            total = 0.0
            for i in order:
                xi, yi = X[i], y[i]
                h = self._hidden_act(xi)
                z = dot(self.W2, h) + self.b2
                p = sigmoid(z)
                d_out = (p - yi)
                for j in range(self.H):
                    self.W2[j] -= lr * d_out * h[j]
                self.b2 -= lr * d_out
                dh = [d_out * self.W2[j] * (1 - h[j] * h[j]) for j in range(self.H)]
                for j in range(self.H):
                    for k in range(F):
                        self.W1[j][k] -= lr * dh[j] * xi[k]
                    self.b1[j] -= lr * dh[j]
                total += -(yi * math.log(p + 1e-12) + (1 - yi) * math.log(1 - p + 1e-12))
            losses.append(total / n)
        return losses

    def evaluate(self, X: List[List[float]], y: List[float]) -> Dict[str, float]:
        scores = [self._forward(x)[0] for x in X]
        preds = [1 if s >= 0.5 else 0 for s in scores]
        acc = sum(1 for a, b in zip(preds, y) if a == b) / len(y) if y else 0.0
        try:
            a = auc(y, scores)
        except Exception:
            a = 0.5
        pos_rate = sum(y) / len(y) if y else 0.0
        return {"auroc": a, "accuracy": acc, "n": len(y), "pos_rate": pos_rate}

    # ---- persistence ----
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"H": self.H, "W1": self.W1, "b1": self.b1,
                       "W2": self.W2, "b2": self.b2,
                       "feature_keys": FEATURE_KEYS}, f)

    @classmethod
    def load(cls, path: str) -> "TemporalRiskModel":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        m = cls(hidden=d["H"])
        m.W1, m.b1, m.W2, m.b2 = d["W1"], d["b1"], d["W2"], d["b2"]
        return m
