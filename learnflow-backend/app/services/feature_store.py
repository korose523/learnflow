"""实时特征存储 —— 把 LearningEvent(或等效 dict)流聚合为固定维特征向量。

纯 Python, 内存实现; 生产可替换为 Redis。这是 AI 实时分析层的摄入入口,
把离散行为事件转化为机器学习模型可消费的特征。时序动态由**滚动窗口聚合**
承载 (近期行为决定特征), 因此模型无需显式递归即可感知趋势。
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

# 规范特征向量维度 (顺序即索引, 与 ml_risk_model 严格对应)
FEATURE_KEYS = [
    "correct_rate",    # 正确率
    "hint_rate",       # 提示依赖率
    "skip_rate",       # 跳过率
    "wrong_streak",    # 当前连续错 (归一)
    "thinking_norm",   # 平均思考时长 (归一)
    "night_ratio",     # 夜间(22-7)事件占比
    "intensity_10m",   # 近10分钟强度
    "variability",     # 事件间隔变异性 (可变比率暴露代理)
    "difficulty_mean", # 平均难度 (decision_snapshot.fused_d)
    "immersive_ratio", # 沉浸/心流区占比
    "session_switch",  # 会话切换率
    "recency_gap",     # 距上次事件间隔
    "duration_norm",   # 窗口时长
    "engagement",      # 参与强度
]
F = len(FEATURE_KEYS)

WINDOW_EVENTS = 200
WINDOW_SEC = 2 * 3600


def _norm(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


class FeatureStore:
    def __init__(self, window_events: int = WINDOW_EVENTS, window_sec: int = WINDOW_SEC):
        self.window_events = window_events
        self.window_sec = window_sec
        self._buf: Dict[str, Deque[dict]] = {}

    def ingest(self, event: dict) -> None:
        uid = event.get("user_id")
        if not uid:
            return
        e = dict(event)
        ts = e.get("created_at")
        if isinstance(ts, (int, float)):
            e["_ts"] = float(ts)
        else:
            e["_ts"] = time.time()
        dq = self._buf.setdefault(uid, deque(maxlen=self.window_events))
        dq.append(e)

    def _window(self, uid: str) -> List[dict]:
        now = time.time()
        dq = self._buf.get(uid)
        if not dq:
            return []
        return [e for e in dq if now - e.get("_ts", now) <= self.window_sec]

    def sequence(self, uid: str, k: int = 10) -> List[dict]:
        return self._window(uid)[-k:]

    def feature_vector(self, uid: str) -> List[float]:
        return self._aggregate(self._window(uid))

    def _aggregate(self, w: List[dict]) -> List[float]:
        if not w:
            return [0.0] * F
        n = len(w)
        now = time.time()
        correct = sum(1 for e in w if e.get("is_correct") is True)
        hints = sum(int(e.get("hints_used") or 0) for e in w)
        skipped = sum(1 for e in w if e.get("skipped"))
        thinking = [int(e.get("thinking_ms") or 0) for e in w]
        avg_think = sum(thinking) / n if thinking else 0.0

        wrong_streak = cur = 0
        for e in w:
            if e.get("is_correct") is False:
                cur += 1
                wrong_streak = max(wrong_streak, cur)
            else:
                cur = 0

        night = 0
        for e in w:
            h = time.localtime(e.get("_ts", now)).tm_hour
            if h >= 22 or h < 7:
                night += 1

        intensity = sum(1 for e in w if now - e.get("_ts", now) <= 600)

        ts_list = sorted(e.get("_ts", now) for e in w)
        gaps = [ts_list[i + 1] - ts_list[i] for i in range(len(ts_list) - 1)]
        variability = (
            (sum((g - (sum(gaps) / len(gaps))) ** 2 for g in gaps)
             / max(1, len(gaps) - 1)) ** 0.5
            if len(gaps) > 1 else 0.0
        )

        diffs = []
        imm = 0
        for e in w:
            snap = e.get("decision_snapshot") or {}
            d = snap.get("fused_d")
            if d is not None:
                diffs.append(float(d))
            if snap.get("zone") in ("immersive", "deep", "flow"):
                imm += 1
        diff_mean = (sum(diffs) / len(diffs)) if diffs else 0.0

        sessions = set(e.get("session_id") for e in w)
        session_switch = len(sessions) / n
        recency_gap = (now - ts_list[-1]) if ts_list else self.window_sec
        duration = (ts_list[-1] - ts_list[0]) if len(ts_list) > 1 else 0.0

        return [
            _norm(correct, 0, n),
            _norm(hints, 0, n),
            _norm(skipped, 0, n),
            _norm(wrong_streak, 0, 10),
            _norm(avg_think, 0, 60000),
            _norm(night, 0, n),
            _norm(intensity, 0, 20),
            _norm(variability, 0, 3600),
            _norm(diff_mean, 0, 1000),
            _norm(imm, 0, n),
            _norm(session_switch, 0, 1),
            _norm(recency_gap, 0, self.window_sec),
            _norm(duration, 0, 7200),
            _norm(n, 0, 200),
        ]

    def users(self) -> List[str]:
        return list(self._buf.keys())

    def clear(self) -> None:
        self._buf.clear()
