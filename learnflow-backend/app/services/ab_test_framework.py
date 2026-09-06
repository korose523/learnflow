"""A/B 测试与持续优化框架

基于论文第九章 9.5 节：A/B 测试与持续优化框架
- 最小可干预单元：每次实验只改变一个参数（或一类机制）
- 分层随机化：按年级、学科、学习风格分层
- 伦理优先：安全停止规则（健康一票否决）
- 长期追踪：30 天、90 天效果追踪
- 健康一票否决：牺牲健康安全的方案拒绝上线

实验流程：影子模式 → 小流量(1-5%) → 全量上线（经伦理委员会审查）

本文件在 §3.4.2 (与 A/B 框架对接改造) 基础上的增量:
- ``Experiment`` 增加 ``mechanism_toggles``（机制级开关）与统计治理字段
  (``gate_level``/``mde``/``required_n_per_group``/``icc_assumed``/
  ``cluster_randomized``/``registry_fingerprint``），实现真正的「单机制/类别消融」
- 新增 ``get_mechanism_toggles`` / ``is_mechanism_enabled`` 单点开关查询
- 修正统计缺陷：``cohens_d`` 用正确 pooled SD；新增 ``required_n_per_group``
  （含整群随机设计效应 DEFF）与 ``design_effect`` —— 样本量由功效分析写入，
  不再硬编码 ``min_sample_per_group``（仅保留为 deprecated 兼容字段）
- 数据落库：``ExperimentStore`` 可插拔后端（默认内存，生产可换 JSON/SQL），
  解决 ``_experiments``/``_user_assignments`` 内存态进程重启即丢的问题（§4.2.3）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, Any, Dict, List, Tuple
from collections import defaultdict
from statistics import NormalDist
from math import ceil, sqrt
import random
import hashlib
import json
import os
import logging

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    Numeric,
    DateTime,
    JSON,
    MetaData,
    Table,
    insert,
    select,
    update,
    delete,
    create_engine,
)
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 类别级消融预设 (GAP-1): 8 个治理字母 A–H → 5 个注册表类别
# ---------------------------------------------------------------------------
# 治理文档把 53 个机制分成 8 组 (A–H)。本映射把每个字母解析到**单一**注册表类别，
# 供 ``toggles_for_category`` 一次性关闭整类机制（消融实验用）。
#   A 行为主义·强化与奖励        → retention
#   B 承诺·损失与目标梯度        → retention
#   C 自我决定论 (自主/胜任/关联) → selfreg
#   D 社会影响与社会学习          → retention (社会类跨 retention/motivation，取多数)
#   E 习惯形成与自我调节          → retention
#   F 情绪与动机触发              → motivation
#   G UX 微交互与认知负荷         → cognition
#   H 健康护栏与伦理              → health (消融中单臂永不关闭：伦理硬约束)
# 注意：映射到的类别返回该类别**全部**机制 (by_category)，不止该字母的子集；
#       这是 GAP 规格要求的「关掉一整类」语义。H 类在消融中保持开启。
_GOVERNANCE_LETTER_TO_CATEGORY = {
    "A": "retention",
    "B": "retention",
    "C": "selfreg",
    "D": "retention",
    "E": "retention",
    "F": "motivation",
    "G": "cognition",
    "H": "health",
}


class ExperimentPhase(str, Enum):
    """实验阶段"""
    SHADOW = "shadow"        # 影子模式：计算但不执行
    CANARY = "canary"        # 小流量：1-5%用户
    RAMPING = "ramping"      # 逐步放量
    FULL = "full"            # 全量上线
    STOPPED = "stopped"      # 已停止（安全规则触发）
    COMPLETED = "completed"  # 已完成


class MetricCategory(str, Enum):
    """指标类别（论文'学习效果-动机质量-健康安全'三维）"""
    LEARNING = "learning"      # 学习效果
    MOTIVATION = "motivation"  # 动机质量
    HEALTH = "health"          # 健康安全


@dataclass
class ExperimentMetric:
    """实验指标定义"""
    name: str
    category: MetricCategory
    target_direction: str  # "increase" or "decrease"
    safety_threshold: Optional[float] = None  # 健康安全阈值（超过则停止实验）
    current_value: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "target_direction": self.target_direction,
            "safety_threshold": self.safety_threshold,
            "current_value": self.current_value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExperimentMetric":
        return cls(
            name=d["name"],
            category=MetricCategory(d["category"]),
            target_direction=d["target_direction"],
            safety_threshold=d.get("safety_threshold"),
            current_value=d.get("current_value", 0.0),
        )


@dataclass
class ExperimentResult:
    """实验结果记录"""
    experiment_id: str
    user_id: str
    group: str  # "control" or "treatment"
    metrics: dict  # {metric_name: value}
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "user_id": self.user_id,
            "group": self.group,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExperimentResult":
        return cls(
            experiment_id=d["experiment_id"],
            user_id=d["user_id"],
            group=d["group"],
            metrics=d["metrics"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
        )


@dataclass
class Experiment:
    """A/B 测试实验定义"""
    id: str
    name: str
    description: str

    # --- 保留旧字段以兼容存量实验 ---
    parameter_name: str = ""
    control_value: Any = None
    treatment_value: Any = None

    # --- 新增: 机制级开关（消融实验的核心） ---
    mechanism_toggles: Dict[str, bool] = field(default_factory=dict)
    # 例: {"LF-M44": False}                      单机制消融
    #     {"LF-M23": False, "LF-M24": False}     类别消融（推荐）

    # --- 新增: 统计治理 ---
    primary_metric: str = "knowledge_mastery_growth"
    secondary_metrics: List[str] = field(default_factory=list)
    alpha_alloc: float = 0.05          # 该实验在检验序中分到的 α
    gate_level: int = 1                # 0=omnibus, 1=category, 2=mechanism
    mde: float = 0.3                   # 最小可检测效应 (Cohen's d)
    required_n_per_group: int = 0      # 由功效分析写入，非硬编码
    icc_assumed: float = 0.05          # 假设的组内相关系数
    cluster_randomized: bool = True    # 是否整群随机（班级级）
    deff: float = 1.0                  # 设计效应 (1 + (m-1)*ICC)，由功效分析写入

    phase: ExperimentPhase = ExperimentPhase.SHADOW
    traffic_percentage: float = 0.0  # 实验流量占比
    metrics: list = field(default_factory=list)  # [ExperimentMetric]
    results: list = field(default_factory=list)  # [ExperimentResult]
    safety_stop_triggered: bool = False
    safety_stop_reason: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    min_sample_per_group: int = 100     #  deprecated: 由 required_n_per_group 取代
    tracking_days: int = 90
    registry_fingerprint: str = ""      # 新增: 注册表版本指纹，保证可复现

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameter_name": self.parameter_name,
            "control_value": str(self.control_value),
            "treatment_value": str(self.treatment_value),
            "mechanism_toggles": dict(self.mechanism_toggles),
            "primary_metric": self.primary_metric,
            "secondary_metrics": list(self.secondary_metrics),
            "alpha_alloc": self.alpha_alloc,
            "gate_level": self.gate_level,
            "mde": self.mde,
            "required_n_per_group": self.required_n_per_group,
            "icc_assumed": self.icc_assumed,
            "cluster_randomized": self.cluster_randomized,
            "deff": self.deff,
            "phase": self.phase.value,
            "traffic_percentage": self.traffic_percentage,
            "safety_stop_triggered": self.safety_stop_triggered,
            "safety_stop_reason": self.safety_stop_reason,
            "total_results": len(self.results),
            "created_at": self.created_at.isoformat(),
            "registry_fingerprint": self.registry_fingerprint,
        }

    def to_json(self) -> dict:
        """完整可序列化形态（含 results），供落库后端使用。"""
        d = self.to_dict()
        d["metrics"] = [m.to_dict() for m in self.metrics]
        d["results"] = [r.to_dict() for r in self.results]
        d["started_at"] = self.started_at.isoformat() if self.started_at else None
        d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Experiment":
        exp = cls(
            id=d["id"],
            name=d["name"],
            description=d["description"],
            parameter_name=d.get("parameter_name", ""),
            control_value=d.get("control_value"),
            treatment_value=d.get("treatment_value"),
            mechanism_toggles=d.get("mechanism_toggles", {}) or {},
            primary_metric=d.get("primary_metric", "knowledge_mastery_growth"),
            secondary_metrics=d.get("secondary_metrics", []) or [],
            alpha_alloc=d.get("alpha_alloc", 0.05),
            gate_level=d.get("gate_level", 1),
            mde=d.get("mde", 0.3),
            required_n_per_group=d.get("required_n_per_group", 0),
            icc_assumed=d.get("icc_assumed", 0.05),
            cluster_randomized=d.get("cluster_randomized", True),
            deff=d.get("deff", 1.0),
            phase=ExperimentPhase(d["phase"]),
            traffic_percentage=d.get("traffic_percentage", 0.0),
            metrics=[ExperimentMetric.from_dict(m) for m in d.get("metrics", [])],
            results=[ExperimentResult.from_dict(r) for r in d.get("results", [])],
            safety_stop_triggered=d.get("safety_stop_triggered", False),
            safety_stop_reason=d.get("safety_stop_reason", ""),
            created_at=datetime.fromisoformat(d["created_at"]),
            started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
            min_sample_per_group=d.get("min_sample_per_group", 100),
            tracking_days=d.get("tracking_days", 90),
            registry_fingerprint=d.get("registry_fingerprint", ""),
        )
        return exp


# ---------------------------------------------------------------------------
# 可插拔落库后端 (§4.2.3)
# ---------------------------------------------------------------------------

class ExperimentStore(ABC):
    """实验数据持久化后端抽象。默认内存实现与既有行为一致；可换 JSON 文件或 SQL。"""

    @abstractmethod
    def save_experiment(self, exp: Experiment) -> None: ...

    @abstractmethod
    def load_experiment(self, exp_id: str) -> Optional[Experiment]: ...

    @abstractmethod
    def list_experiments(self) -> List[Experiment]: ...

    @abstractmethod
    def delete_experiment(self, exp_id: str) -> None: ...

    @abstractmethod
    def save_assignment(self, exp_id: str, user_id: str,
                        group: str, cluster_id: Optional[str] = None) -> None: ...

    @abstractmethod
    def load_assignments(self, exp_id: str) -> Dict[str, Dict[str, str]]:
        """返回 {user_id: {"group": ..., "cluster_id": ...}}"""
        ...

    @abstractmethod
    def close(self) -> None: ...


class MemoryExperimentStore(ExperimentStore):
    """内存后端 —— 与改造前的行为完全一致（进程重启即丢）。"""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)

    def save_experiment(self, exp: Experiment) -> None:
        self._experiments[exp.id] = exp

    def load_experiment(self, exp_id: str) -> Optional[Experiment]:
        return self._experiments.get(exp_id)

    def list_experiments(self) -> List[Experiment]:
        return list(self._experiments.values())

    def delete_experiment(self, exp_id: str) -> None:
        self._experiments.pop(exp_id, None)
        self._assignments.pop(exp_id, None)

    def save_assignment(self, exp_id: str, user_id: str,
                        group: str, cluster_id: Optional[str] = None) -> None:
        self._assignments[exp_id][user_id] = {
            "group": group,
            "cluster_id": cluster_id or "",
        }

    def load_assignments(self, exp_id: str) -> Dict[str, Dict[str, str]]:
        return dict(self._assignments.get(exp_id, {}))

    def close(self) -> None:
        return None


class JSONFileExperimentStore(ExperimentStore):
    """JSON 文件后端 —— 真正落库，进程重启不丢，满足 90 天追踪与可复现性。

    生产可替换为 SQLExperimentStore（可执行建表见
    scripts/schema_core_assets.mysql.sql 与 scripts/schema_core_assets.sqlite.sql，
    分别面向 MySQL 8.0 与 SQLite 3 环境；原 scripts/schema_core_assets.sql 为
    Postgres 方言，在 MySQL/SQLite 环境下不可直接执行，仅作论文附录归档）。
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(self._dir, exist_ok=True)
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for ej in blob.get("experiments", []):
            try:
                self._experiments[ej["id"]] = Experiment.from_json(ej)
            except (KeyError, ValueError):
                continue
        for exp_id, users in blob.get("assignments", {}).items():
            self._assignments[exp_id] = {u: a for u, a in users.items()}

    def _flush(self) -> None:
        blob = {
            "experiments": [e.to_json() for e in self._experiments.values()],
            "assignments": {eid: dict(users) for eid, users in self._assignments.items()},
        }
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(blob, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def save_experiment(self, exp: Experiment) -> None:
        self._experiments[exp.id] = exp
        self._flush()

    def load_experiment(self, exp_id: str) -> Optional[Experiment]:
        return self._experiments.get(exp_id)

    def list_experiments(self) -> List[Experiment]:
        return list(self._experiments.values())

    def delete_experiment(self, exp_id: str) -> None:
        self._experiments.pop(exp_id, None)
        self._assignments.pop(exp_id, None)
        self._flush()

    def save_assignment(self, exp_id: str, user_id: str,
                        group: str, cluster_id: Optional[str] = None) -> None:
        self._assignments[exp_id][user_id] = {
            "group": group,
            "cluster_id": cluster_id or "",
        }
        self._flush()

    def load_assignments(self, exp_id: str) -> Dict[str, Dict[str, str]]:
        return dict(self._assignments.get(exp_id, {}))

    def close(self) -> None:
        self._flush()


# ---------------------------------------------------------------------------
# SQL 落库后端（§4.2.3，生产可替换 JSONFileExperimentStore）
# ---------------------------------------------------------------------------

# 模块级 MetaData：所有 SQLExperimentStore 实例共享同一份表定义，
# 由 create_all(checkfirst=True) 保证幂等（重复建表不报错）。
# 统一用 SQLAlchemy Core 的方言无关类型（JSON / DateTime / Numeric ...），
# 由 SQLAlchemy 按运行时的数据库方言生成对应 DDL——
#   MySQL   → JSON / DATETIME / DECIMAL
#   SQLite  → TEXT / DATETIME / NUMERIC
# 这样一套代码同时支持生产 MySQL 与测试 SQLite，不写死 Postgres 专有类型
# （JSONB / TIMESTAMPTZ / BIGSERIAL）。字段语义对齐
# scripts/schema_core_assets.sql 的 experiments / experiment_assignments，
# 复杂字段（mechanism_toggles、metrics、results 等）以 JSON 列序列化落库，
# 读回时还原成 Experiment 实例（嵌套 dataclass / Enum 不退化）。
metadata = MetaData()

experiments = Table(
    "experiments", metadata,
    Column("id", String(255), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("parameter_name", String(255), nullable=False, default=""),
    # control_value / treatment_value 为兼容旧字段，类型任意，用 JSON 列原样保留
    Column("control_value", JSON, nullable=True),
    Column("treatment_value", JSON, nullable=True),
    Column("mechanism_toggles", JSON, nullable=False),
    Column("primary_metric", String(255), nullable=False,
           default="knowledge_mastery_growth"),
    Column("secondary_metrics", JSON, nullable=False),
    Column("alpha_alloc", Numeric(18, 8), nullable=False, default=0.05),
    Column("gate_level", Integer, nullable=False, default=1),
    Column("mde", Numeric(18, 8), nullable=False, default=0.3),
    Column("required_n_per_group", Integer, nullable=False, default=0),
    Column("icc_assumed", Numeric(18, 8), nullable=False, default=0.05),
    Column("cluster_randomized", Boolean, nullable=False, default=True),
    Column("deff", Numeric(18, 8), nullable=False, default=1.0),
    Column("phase", String(31), nullable=False, default="shadow"),
    Column("traffic_percentage", Numeric(18, 8), nullable=False, default=0.0),
    Column("metrics", JSON, nullable=False),
    Column("results", JSON, nullable=False),
    Column("safety_stop_triggered", Boolean, nullable=False, default=False),
    Column("safety_stop_reason", Text, nullable=False, default=""),
    Column("created_at", DateTime, nullable=False),
    Column("started_at", DateTime, nullable=True),
    Column("completed_at", DateTime, nullable=True),
    Column("min_sample_per_group", Integer, nullable=False, default=100),
    Column("tracking_days", Integer, nullable=False, default=90),
    # registry_fingerprint 是可复现性锚点，务必保留
    Column("registry_fingerprint", String(255), nullable=False, default=""),
)

experiment_assignments = Table(
    "experiment_assignments", metadata,
    Column("experiment_id", String(255), primary_key=True),
    Column("user_id", String(255), primary_key=True),
    Column("cluster_id", String(255), nullable=True),
    # 用 group_name 而非 group，规避 group 是 SQL 保留字
    Column("group_name", String(63), nullable=False),
    Column("assigned_at", DateTime, nullable=False),
)


def _strip_tz(value: Optional[datetime]) -> Optional[datetime]:
    """写库前把时区信息去掉，统一以 naive UTC 存储，规避 SQLite/MySQL 时区往返差异。"""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    """读回的时间戳统一补齐 UTC 时区（SQLite 可能返回 naive）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _create_engine(url: str):
    """构造同步引擎。

    - 配置里的 DATABASE_URL 默认是 mysql+aiomysql（异步驱动），同步落库需换成
      pymysql；若未安装 pymysql 则在此不报错，仅在真正连接时暴露（测试走 SQLite 不受影响）。
    - SQLite 加 timeout，缓解多连接/多实例并发下的 'database is locked'。
    """
    if url.startswith("mysql+aiomysql"):
        url = "mysql+pymysql" + url[len("mysql+aiomysql"):]
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["timeout"] = 30
    return create_engine(url, future=True, connect_args=connect_args)


class SQLExperimentStore(ExperimentStore):
    """SQL 落库后端 —— 真正持久化，跨进程/跨重启不丢，支撑 90 天追踪与可复现性。

    用 SQLAlchemy Core 定义表结构，方言无关：生产 MySQL、测试 SQLite 同一套代码。
    复杂字段（嵌套 dataclass 的 metrics/results、Enum 的 phase、JSON 的
    mechanism_toggles）以 JSON 列序列化；读回时还原，不退化成 dict/字符串。

    容错策略（与项目既有风格一致）：
    - 非关键读取/写入失败：记 warning，降级返回（不让调用方崩溃）；
    - ``save_assignment`` 失败：记 **error** 并**重新抛出**——分组若静默丢失，
      被试会被重复随机分组，污染实验内部效度，属不可逆损伤，必须让调用方感知。
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine = _create_engine(database_url)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            metadata.create_all(self._engine, checkfirst=True)
        except Exception:
            logger.warning(
                "SQLExperimentStore 建表失败（可能数据库不可用）url=%s",
                self._database_url, exc_info=True,
            )

    # ---- 序列化：Experiment <-> 行 ----
    def _to_row(self, exp: Experiment) -> dict:
        return {
            "id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "parameter_name": exp.parameter_name,
            "control_value": exp.control_value,
            "treatment_value": exp.treatment_value,
            "mechanism_toggles": dict(exp.mechanism_toggles),
            "primary_metric": exp.primary_metric,
            "secondary_metrics": list(exp.secondary_metrics),
            "alpha_alloc": exp.alpha_alloc,
            "gate_level": exp.gate_level,
            "mde": exp.mde,
            "required_n_per_group": exp.required_n_per_group,
            "icc_assumed": exp.icc_assumed,
            "cluster_randomized": exp.cluster_randomized,
            "deff": exp.deff,
            "phase": exp.phase.value,
            "traffic_percentage": exp.traffic_percentage,
            # 嵌套 dataclass 先转 dict 再交 JSON 列序列化还原
            "metrics": [m.to_dict() for m in exp.metrics],
            "results": [r.to_dict() for r in exp.results],
            "safety_stop_triggered": exp.safety_stop_triggered,
            "safety_stop_reason": exp.safety_stop_reason,
            "created_at": _strip_tz(exp.created_at),
            "started_at": _strip_tz(exp.started_at),
            "completed_at": _strip_tz(exp.completed_at),
            "min_sample_per_group": exp.min_sample_per_group,
            "tracking_days": exp.tracking_days,
            "registry_fingerprint": exp.registry_fingerprint,
        }

    def _to_experiment(self, row) -> Experiment:
        return Experiment(
            id=row.id,
            name=row.name,
            description=row.description,
            parameter_name=row.parameter_name or "",
            control_value=row.control_value,
            treatment_value=row.treatment_value,
            mechanism_toggles=dict(row.mechanism_toggles or {}),
            primary_metric=row.primary_metric,
            secondary_metrics=list(row.secondary_metrics or []),
            alpha_alloc=float(row.alpha_alloc) if row.alpha_alloc is not None else 0.05,
            gate_level=int(row.gate_level),
            mde=float(row.mde) if row.mde is not None else 0.3,
            required_n_per_group=int(row.required_n_per_group),
            icc_assumed=float(row.icc_assumed) if row.icc_assumed is not None else 0.05,
            cluster_randomized=bool(row.cluster_randomized),
            deff=float(row.deff) if row.deff is not None else 1.0,
            phase=ExperimentPhase(row.phase),
            traffic_percentage=float(row.traffic_percentage)
            if row.traffic_percentage is not None else 0.0,
            metrics=[ExperimentMetric.from_dict(m) for m in (row.metrics or [])],
            results=[ExperimentResult.from_dict(r) for r in (row.results or [])],
            safety_stop_triggered=bool(row.safety_stop_triggered),
            safety_stop_reason=row.safety_stop_reason or "",
            created_at=_normalize_dt(row.created_at),
            started_at=_normalize_dt(row.started_at),
            completed_at=_normalize_dt(row.completed_at),
            min_sample_per_group=int(row.min_sample_per_group),
            tracking_days=int(row.tracking_days),
            registry_fingerprint=row.registry_fingerprint or "",
        )

    # ---- ExperimentStore 接口 ----
    def save_experiment(self, exp: Experiment) -> None:
        values = self._to_row(exp)
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(experiments).values(**values))
        except IntegrityError:
            # 同 id 已存在：覆盖更新（实验配置被修订时）
            try:
                with self._engine.begin() as conn:
                    conn.execute(
                        update(experiments)
                        .where(experiments.c.id == exp.id)
                        .values(**values)
                    )
            except Exception:
                logger.warning(
                    "SQLExperimentStore.save_experiment 更新失败 exp_id=%s", exp.id,
                    exc_info=True,
                )
                return
        except Exception:
            logger.warning(
                "SQLExperimentStore.save_experiment 落库失败 exp_id=%s", exp.id,
                exc_info=True,
            )
            return

    def load_experiment(self, exp_id: str) -> Optional[Experiment]:
        try:
            with self._engine.connect() as conn:
                row = conn.execute(
                    select(experiments).where(experiments.c.id == exp_id)
                ).mappings().first()
            if row is None:
                return None
            return self._to_experiment(row)
        except Exception:
            logger.warning(
                "SQLExperimentStore.load_experiment 读取失败 exp_id=%s", exp_id,
                exc_info=True,
            )
            return None

    def list_experiments(self) -> List[Experiment]:
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(select(experiments)).mappings().all()
            return [self._to_experiment(r) for r in rows]
        except Exception:
            logger.warning(
                "SQLExperimentStore.list_experiments 读取失败", exc_info=True
            )
            return []

    def delete_experiment(self, exp_id: str) -> None:
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    experiments.delete().where(experiments.c.id == exp_id)
                )
                # 同时清除该实验的分组，避免留下孤儿分组污染后续组间对比
                conn.execute(
                    experiment_assignments.delete().where(
                        experiment_assignments.c.experiment_id == exp_id
                    )
                )
        except Exception:
            logger.warning(
                "SQLExperimentStore.delete_experiment 删除失败 exp_id=%s", exp_id,
                exc_info=True,
            )

    def save_assignment(self, exp_id: str, user_id: str,
                        group: str, cluster_id: Optional[str] = None) -> None:
        values = {
            "experiment_id": exp_id,
            "user_id": user_id,
            "cluster_id": cluster_id,
            "group_name": group,
            "assigned_at": _strip_tz(datetime.now(UTC)),
        }
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(experiment_assignments).values(**values))
        except IntegrityError:
            # 同一 (experiment_id, user_id) 重复写入：覆盖，被试只能属于一个组
            try:
                with self._engine.begin() as conn:
                    conn.execute(
                        update(experiment_assignments)
                        .where(
                            (experiment_assignments.c.experiment_id == exp_id)
                            & (experiment_assignments.c.user_id == user_id)
                        )
                        .values(
                            cluster_id=cluster_id,
                            group_name=group,
                            assigned_at=values["assigned_at"],
                        )
                    )
            except Exception:
                logger.error(
                    "SQLExperimentStore.save_assignment 覆盖写入失败 "
                    "exp_id=%s user_id=%s",
                    exp_id, user_id, exc_info=True,
                )
                raise
        except Exception:
            # 分组是唯一不可静默吞掉的写入：丢失会导致被试被重复随机分组，
            # 直接破坏实验内部效度，必须让调用方知道。
            logger.error(
                "SQLExperimentStore.save_assignment 分组写入失败，被试可能未被正确记录 "
                "exp_id=%s user_id=%s",
                exp_id, user_id, exc_info=True,
            )
            raise

    def load_assignments(self, exp_id: str) -> Dict[str, Dict[str, str]]:
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    select(experiment_assignments).where(
                        experiment_assignments.c.experiment_id == exp_id
                    )
                ).mappings().all()
            return {
                r["user_id"]: {
                    "group": r["group_name"],
                    "cluster_id": r["cluster_id"] or "",
                }
                for r in rows
            }
        except Exception:
            logger.warning(
                "SQLExperimentStore.load_assignments 读取失败 exp_id=%s", exp_id,
                exc_info=True,
            )
            return {}

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception:
            logger.warning(
                "SQLExperimentStore.close 释放引擎失败", exc_info=True
            )


def default_experiment_store() -> ExperimentStore:
    """按环境变量 ``LEARNFLOW_EXPERIMENT_BACKEND`` 选择实验落库后端。

    - ``memory``（默认）：``MemoryExperimentStore()``，与改造前行为完全一致；
    - ``json``：``JSONFileExperimentStore(path=<后端根>/artifacts/experiments.json)``；
    - ``sql``：``SQLExperimentStore(database_url=...)``，URL 优先取
      ``LEARNFLOW_EXPERIMENT_DB_URL``，没有则回落到配置 ``DATABASE_URL``；
    - 未知取值：记 warning 并回退 ``MemoryExperimentStore()``。

    **默认必须是 memory**，保证 761 个既有测试行为完全不变。将来切换后端只改此一处。
    """
    backend = os.environ.get("LEARNFLOW_EXPERIMENT_BACKEND", "memory").strip().lower()
    if backend == "memory":
        return MemoryExperimentStore()
    if backend == "json":
        backend_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        path = os.path.join(backend_root, "artifacts", "experiments.json")
        return JSONFileExperimentStore(path=path)
    if backend == "sql":
        from app.core.config import settings  # 延迟导入，避免模块加载副作用

        url = os.environ.get("LEARNFLOW_EXPERIMENT_DB_URL") or settings.DATABASE_URL
        return SQLExperimentStore(database_url=url)
    logger.warning(
        "未知的 LEARNFLOW_EXPERIMENT_BACKEND=%r，回退 MemoryExperimentStore", backend
    )
    return MemoryExperimentStore()


class ABTestFramework:
    """A/B 测试框架

    管理 LearnFlow 所有游戏化引擎参数的 A/B 测试生命周期。
    遵循'健康一票否决'原则：任何牺牲健康安全的方案拒绝上线。
    """

    def __init__(self, store: Optional[ExperimentStore] = None):
        self._store = store or MemoryExperimentStore()

    # ----- 实验 CRUD -----
    def create_experiment(
        self,
        name: str,
        description: str,
        parameter_name: str = "",
        control_value: Any = None,
        treatment_value: Any = None,
        metrics: Optional[list] = None,
        mechanism_toggles: Optional[Dict[str, bool]] = None,
        primary_metric: str = "knowledge_mastery_growth",
        secondary_metrics: Optional[List[str]] = None,
        alpha_alloc: float = 0.05,
        gate_level: int = 1,
        mde: float = 0.3,
        icc_assumed: float = 0.05,
        cluster_randomized: bool = True,
        registry_fingerprint: str = "",
    ) -> Experiment:
        """创建新实验（初始为影子模式）"""
        exp_id = self._generate_id(name)
        exp = Experiment(
            id=exp_id,
            name=name,
            description=description,
            parameter_name=parameter_name,
            control_value=control_value,
            treatment_value=treatment_value,
            metrics=metrics or self._default_metrics(),
            mechanism_toggles=mechanism_toggles or {},
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            alpha_alloc=alpha_alloc,
            gate_level=gate_level,
            mde=mde,
            icc_assumed=icc_assumed,
            cluster_randomized=cluster_randomized,
            registry_fingerprint=registry_fingerprint,
        )
        self._store.save_experiment(exp)
        return exp

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._store.load_experiment(experiment_id)

    def assign_user(self, experiment_id: str, user_id: str,
                    strata: Optional[dict] = None) -> str:
        """将用户分配到对照组或实验组

        使用基于 user_id 的确定性哈希，确保同一用户始终分到同一组。
        支持分层随机化（strata 参数用于后续分层分析）。
        """
        exp = self._store.load_experiment(experiment_id)
        if not exp:
            return "control"

        assignments = self._store.load_assignments(experiment_id)
        if user_id in assignments:
            return assignments[user_id]["group"]

        # 影子模式：所有用户都是对照组（不执行新策略）
        if exp.phase == ExperimentPhase.SHADOW:
            group = "control"
        else:
            # 确定性哈希分配
            hash_input = f"{experiment_id}:{user_id}"
            hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            bucket = (hash_val % 100) / 100.0

            if bucket < exp.traffic_percentage:
                group = "treatment"
            else:
                group = "control"

        cluster_id = (str(strata.get("class_id")) if strata and strata.get("class_id")
                      else None)
        self._store.save_assignment(experiment_id, user_id, group, cluster_id)
        return group

    def get_parameter_value(self, experiment_id: str, user_id: str,
                            default_value: Any) -> Any:
        """获取用户应使用的参数值（核心方法）

        在影子模式下，所有用户使用 default_value；
        在小流量/全量阶段，实验组用户使用 treatment_value。
        """
        exp = self._store.load_experiment(experiment_id)
        if not exp or exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return default_value

        group = self.assign_user(experiment_id, user_id)
        if group == "treatment" and exp.phase != ExperimentPhase.SHADOW:
            return exp.treatment_value
        return exp.control_value if exp.phase != ExperimentPhase.SHADOW else default_value

    def record_result(self, experiment_id: str, user_id: str, metrics: dict):
        """记录实验结果"""
        exp = self._store.load_experiment(experiment_id)
        if not exp:
            return

        group = self.assign_user(experiment_id, user_id)
        result = ExperimentResult(
            experiment_id=experiment_id,
            user_id=user_id,
            group=group,
            metrics=metrics,
        )
        exp.results.append(result)
        self._store.save_experiment(exp)

        # 检查安全停止规则
        self._check_safety_rules(exp)

    # ------------------------------------------------------------------
    # 改造 2: 机制开关查询
    # ------------------------------------------------------------------
    def get_mechanism_toggles(self, user_id: str) -> Dict[str, bool]:
        """返回该用户的完整机制开关向量（合并所有生效中实验的 toggles）。

        数据流:
          Experiment.mechanism_toggles  --(按分组)-->  {mechanism_id: enabled}
          合并规则: 实验覆盖 > 基线; 健康临界机制恒为 True（由仲裁器保证）
        """
        toggles: Dict[str, bool] = {}
        for exp in self._store.list_experiments():
            if exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
                continue
            group = self.assign_user(exp.id, user_id)
            if group != "treatment" or exp.phase == ExperimentPhase.SHADOW:
                continue
            toggles.update(exp.mechanism_toggles)
        return toggles

    def is_mechanism_enabled(self, experiment_id: str, user_id: str,
                             mechanism_id: str, health_critical: bool = False) -> bool:
        """单点查询。health_critical 机制永不被关闭。"""
        if health_critical:
            return True
        exp = self._store.load_experiment(experiment_id)
        if not exp or exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return True
        if self.assign_user(experiment_id, user_id) != "treatment":
            return True
        return exp.mechanism_toggles.get(mechanism_id, True)

    def toggles_for_category(self, category_letter: str) -> Dict[str, bool]:
        """类别级消融预设：返回「关闭整类机制」的 toggle 字典 (GAP-1)。

        接受两种输入：
          - 注册表类别名: retention / motivation / selfreg / cognition / health
          - 治理字母 A–H（按 ``_GOVERNANCE_LETTER_TO_CATEGORY`` 映射到类别）
        返回形如 ``{lf_id: False for 该类别每个机制}``，可直接并入
        ``Experiment.mechanism_toggles``，实现「一次性关掉一整类」的消融。

        Example:
            off_B = fw.toggles_for_category("B")   # 全部 承诺/损失/梯度 机制 = False
        """
        from app.services import mechanism_registry
        key = (category_letter or "").strip().lower()
        if key in mechanism_registry.CATEGORIES:
            cat = key
        elif key.upper() in _GOVERNANCE_LETTER_TO_CATEGORY:
            cat = _GOVERNANCE_LETTER_TO_CATEGORY[key.upper()]
        else:
            raise ValueError(
                f"非法类别/字母: {category_letter!r}；可选注册表类别 "
                f"{mechanism_registry.CATEGORIES} 或字母 A–H"
            )
        return {spec.id: False for spec in mechanism_registry.by_category(cat)}

    def set_required_n(self, experiment_id: str, n: int, deff: float = 1.0) -> None:
        """由功效分析回填样本量（§3.4.2 改造 1）。"""
        exp = self._store.load_experiment(experiment_id)
        if not exp:
            return
        exp.required_n_per_group = n
        exp.deff = deff
        self._store.save_experiment(exp)

    # ------------------------------------------------------------------
    # 安全停止 / 阶段推进（保留既有逻辑）
    # ------------------------------------------------------------------
    def _check_safety_rules(self, exp: Experiment):
        """检查安全停止规则——健康一票否决"""
        if exp.phase in (ExperimentPhase.STOPPED, ExperimentPhase.COMPLETED):
            return

        treatment_health = [r.metrics for r in exp.results if r.group == "treatment"]
        if len(treatment_health) < 10:  # 样本不足时不检查
            return

        # 计算实验组的健康指标均值
        health_metrics = ["risk_score", "anxiety_score", "depression_score", "addiction_index"]
        for metric_name in health_metrics:
            values = [m.get(metric_name) for m in treatment_health
                      if m.get(metric_name) is not None]
            if not values:
                continue
            avg = sum(values) / len(values)

            if metric_name == "risk_score" and avg > 70:  # LAI风险评分>70（即健康分<30）
                self._trigger_safety_stop(exp, f"实验组风险评分均值 {avg:.1f} 超过安全阈值 70")
                return
            if metric_name == "addiction_index" and avg > 0.6:  # 成瘾指数>0.6
                self._trigger_safety_stop(exp, f"实验组成瘾指数均值 {avg:.2f} 超过安全阈值 0.6")
                return

    def _trigger_safety_stop(self, exp: Experiment, reason: str):
        """触发安全停止"""
        exp.phase = ExperimentPhase.STOPPED
        exp.safety_stop_triggered = True
        exp.safety_stop_reason = reason
        exp.completed_at = datetime.now(UTC)
        self._store.save_experiment(exp)

    def advance_phase(self, experiment_id: str, force: bool = False) -> ExperimentPhase:
        """推进实验阶段：shadow → canary → ramping → full"""
        exp = self._store.load_experiment(experiment_id)
        if not exp:
            return ExperimentPhase.STOPPED

        if exp.phase == ExperimentPhase.SHADOW:
            exp.phase = ExperimentPhase.CANARY
            exp.traffic_percentage = 0.05  # 5%
            exp.started_at = datetime.now(UTC)
        elif exp.phase == ExperimentPhase.CANARY:
            treatment_count = sum(1 for r in exp.results if r.group == "treatment")
            # GAP-7: 真实门槛 = 功效分析写入的 required_n_per_group；
            # 仅当该字段为 0/None（未做功效分析）时，才退回 deprecated 的
            # min_sample_per_group 兼容值。
            threshold = (exp.required_n_per_group
                         if (exp.required_n_per_group or 0) > 0
                         else exp.min_sample_per_group)
            if not force and treatment_count < threshold:
                return exp.phase  # 样本不足，暂不推进
            exp.phase = ExperimentPhase.RAMPING
            exp.traffic_percentage = 0.25  # 25%
        elif exp.phase == ExperimentPhase.RAMPING:
            exp.phase = ExperimentPhase.FULL
            exp.traffic_percentage = 1.0  # 100%
        elif exp.phase == ExperimentPhase.FULL:
            exp.phase = ExperimentPhase.COMPLETED
            exp.completed_at = datetime.now(UTC)

        self._store.save_experiment(exp)
        return exp.phase

    def get_experiment_summary(self, experiment_id: str) -> dict:
        """获取实验摘要统计"""
        exp = self._store.load_experiment(experiment_id)
        if not exp:
            return {}

        control_results = [r for r in exp.results if r.group == "control"]
        treatment_results = [r for r in exp.results if r.group == "treatment"]

        summary = {
            "experiment": exp.to_dict(),
            "control_count": len(control_results),
            "treatment_count": len(treatment_results),
            "metric_comparisons": {},
            "required_n_per_group": exp.required_n_per_group,
            "deff": exp.deff,
            "cluster_randomized": exp.cluster_randomized,
        }

        all_metric_names = set()
        for r in exp.results:
            all_metric_names.update(r.metrics.keys())

        for metric_name in all_metric_names:
            control_vals = [r.metrics[metric_name] for r in control_results
                            if metric_name in r.metrics and r.metrics[metric_name] is not None]
            treatment_vals = [r.metrics[metric_name] for r in treatment_results
                              if metric_name in r.metrics and r.metrics[metric_name] is not None]

            if not control_vals or not treatment_vals:
                continue

            control_mean = sum(control_vals) / len(control_vals)
            treatment_mean = sum(treatment_vals) / len(treatment_vals)

            # 修正: 用正确的 pooled SD 计算 Cohen's d (§3.4.2 改造 5)
            effect_size = ABTestFramework.cohens_d(control_vals, treatment_vals)

            summary["metric_comparisons"][metric_name] = {
                "control_mean": round(control_mean, 4),
                "treatment_mean": round(treatment_mean, 4),
                "difference": round(treatment_mean - control_mean, 4),
                "effect_size": round(effect_size, 3),
                "favor_treatment": treatment_mean > control_mean,
            }

        # 健康一票否决判定
        health_metrics = ["risk_score", "addiction_index", "anxiety_score"]
        health_ok = True
        for hm in health_metrics:
            if hm in summary["metric_comparisons"]:
                comp = summary["metric_comparisons"][hm]
                if comp["favor_treatment"] and hm in health_metrics:
                    health_ok = False

        summary["health_veto"] = not health_ok
        summary["recommendation"] = (
            "reject" if not health_ok else
            ("approve" if all(v.get("favor_treatment", False)
                              for k, v in summary["metric_comparisons"].items()
                              if k not in health_metrics) else "inconclusive")
        )

        return summary

    def list_experiments(self) -> list:
        """列出所有实验"""
        return [exp.to_dict() for exp in self._store.list_experiments()]

    def _default_metrics(self) -> list:
        """默认指标集（三维指标体系）"""
        return [
            ExperimentMetric("knowledge_mastery_growth", MetricCategory.LEARNING, "increase"),
            ExperimentMetric("exam_score", MetricCategory.LEARNING, "increase"),
            ExperimentMetric("intrinsic_motivation_ratio", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("flow_frequency", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("autonomy_score", MetricCategory.MOTIVATION, "increase"),
            ExperimentMetric("lai_score", MetricCategory.HEALTH, "increase", safety_threshold=50.0),
            ExperimentMetric("risk_score", MetricCategory.HEALTH, "decrease", safety_threshold=70.0),
            ExperimentMetric("drop_rate", MetricCategory.HEALTH, "decrease", safety_threshold=0.15),
        ]

    @staticmethod
    def _generate_id(name: str) -> str:
        """根据名称生成确定性ID"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"exp_{timestamp}_{name_hash}"

    # ------------------------------------------------------------------
    # 改造 5: 统计函数修正
    # ------------------------------------------------------------------
    @staticmethod
    def cohens_d(control: List[float], treatment: List[float]) -> float:
        """正确 pooled SD 的 Cohen's d，而非用控制组 SD 近似（§3.4.2）。"""
        n1, n2 = len(control), len(treatment)
        if n1 < 2 or n2 < 2:
            return 0.0
        m1, m2 = sum(control) / n1, sum(treatment) / n2
        s1 = sum((x - m1) ** 2 for x in control) / (n1 - 1)
        s2 = sum((x - m2) ** 2 for x in treatment) / (n2 - 1)
        pooled = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
        if pooled <= 0:
            return 0.0
        return (m2 - m1) / (pooled ** 0.5)

    @staticmethod
    def design_effect(cluster_size: int, icc: float) -> float:
        """整群随机设计效应 DEFF = 1 + (m-1)*ρ。

        m=30, ρ=0.05 → DEFF=2.45，即样本量需 ×2.45（原框架完全缺失，最隐蔽的统计错误）。
        """
        if cluster_size < 1:
            return 1.0
        return 1.0 + (cluster_size - 1) * max(0.0, icc)

    @staticmethod
    def required_n_per_group(d: float, alpha: float = 0.05,
                             power: float = 0.80, deff: float = 1.0) -> int:
        """样本量计算。deff 为整群随机设计效应。

        来源: n = 2*(z_{1-a/2} + z_{1-b})^2 / d^2  (two-sided, equal n)
        """
        if d <= 0:
            return 0
        nd = NormalDist()
        z_a = nd.inv_cdf(1 - alpha / 2)
        z_b = nd.inv_cdf(power)
        return ceil(2 * (z_a + z_b) ** 2 / (d * d) * deff)


# 全局单例（内存后端，保持既有测试/运行行为不变）
ab_test_framework = ABTestFramework()
