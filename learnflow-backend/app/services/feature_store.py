"""实时特征存储 —— 把 LearningEvent(或等效 dict)流聚合为固定维特征向量。

纯 Python, 内存实现; 生产可替换为 Redis。这是 AI 实时分析层的摄入入口,
把离散行为事件转化为机器学习模型可消费的特征。时序动态由**滚动窗口聚合**
承载 (近期行为决定特征), 因此模型无需显式递归即可感知趋势。
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

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


#: 夜间时段定义（22:00–07:00），与 ``_aggregate`` 中的判定保持一致。
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 7


def hour_of(ts: float, tz_offset_hours: Optional[float] = None) -> int:
    """返回时间戳 ``ts`` 所对应的小时数（0–23）。

    ``tz_offset_hours`` 为 ``None`` 时按**运行机器本地时区**解释（生产语义：
    夜间应相对于学习者所在地判断）；给定数值时按该固定 UTC 偏移（小时）计算，
    使结果与运行机器时区无关，供离线评估复现之用。
    """
    if tz_offset_hours is None:
        return time.localtime(ts).tm_hour
    return int(((float(ts) + tz_offset_hours * 3600.0) // 3600) % 24)


def is_night_hour(h: int) -> bool:
    """小时数是否落入夜间时段（22:00–07:00）。"""
    return h >= NIGHT_START_HOUR or h < NIGHT_END_HOUR


def _norm(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


class FeatureStore:
    def __init__(self, window_events: int = WINDOW_EVENTS, window_sec: int = WINDOW_SEC,
                 now_fn: Optional[Callable[[], float]] = None,
                 tz_offset_hours: Optional[float] = None):
        self.window_events = window_events
        self.window_sec = window_sec
        self._buf: Dict[str, Deque[dict]] = {}
        #: 可注入的时间源。默认为 ``time.time``，即生产环境的实时语义
        #: （滚动窗口与近端强度均相对"当下"计算）。离线评估可注入常量
        #: 函数，以消除墙钟依赖、使特征逐位可复现。注入不影响 ``ingest``
        #: 对事件自带 ``created_at`` 的取值。
        self._now_fn: Callable[[], float] = now_fn or time.time
        #: 夜间判定的时区偏移（小时）。``None`` 表示按运行机器本地时区
        #: （生产语义）；给定数值时按该固定 UTC 偏移，使夜间占比与运行
        #: 机器无关，供离线评估复现。
        self._tz_offset_hours: Optional[float] = tz_offset_hours

    def _now(self) -> float:
        return self._now_fn()

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
        now = self._now()
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
        now = self._now()
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
            h = hour_of(e.get("_ts", now), self._tz_offset_hours)
            if is_night_hour(h):
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
