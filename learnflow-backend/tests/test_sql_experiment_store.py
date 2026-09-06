"""SQLExperimentStore 测试套件（博士论文实验基础设施复核用）

覆盖：字段往返保真（嵌套 dataclass / Enum / JSON 不退化）、跨实例持久化、
分组写入与主键覆盖、删除清除孤儿分组、工厂路由、以及 MySQL 方言可生成性
（专门防止回归到 Postgres 专有类型）。
"""
from datetime import datetime, UTC

import pytest
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.schema import CreateTable

from app.services.ab_test_framework import (
    Experiment,
    ExperimentMetric,
    ExperimentResult,
    ExperimentPhase,
    MetricCategory,
    MemoryExperimentStore,
    JSONFileExperimentStore,
    SQLExperimentStore,
    default_experiment_store,
    experiments as experiments_table,
)


def _make_experiment(exp_id: str = "exp_x1") -> Experiment:
    """构造一个字段尽量全的实验，用于往返保真测试。"""
    return Experiment(
        id=exp_id,
        name="消融实验A",
        description="用于 SQL 落库复核的测试实验",
        parameter_name="spaced_repetition_enabled",
        control_value="off",
        treatment_value="on",
        mechanism_toggles={"LF-M44": False, "LF-M23": True},
        primary_metric="knowledge_mastery_growth",
        secondary_metrics=["exam_score", "flow_frequency"],
        alpha_alloc=0.05,
        gate_level=2,
        mde=0.3,
        required_n_per_group=120,
        icc_assumed=0.05,
        cluster_randomized=True,
        deff=2.45,
        phase=ExperimentPhase.CANARY,
        traffic_percentage=0.25,
        metrics=[
            ExperimentMetric(
                "knowledge_mastery_growth", MetricCategory.LEARNING, "increase",
                safety_threshold=None, current_value=0.5,
            ),
            ExperimentMetric(
                "risk_score", MetricCategory.HEALTH, "decrease",
                safety_threshold=70.0, current_value=30.0,
            ),
        ],
        results=[],
        registry_fingerprint="fp-abc123deadbeef",
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        started_at=datetime(2026, 1, 3, tzinfo=UTC),
        completed_at=None,
        min_sample_per_group=100,
        tracking_days=90,
    )


# ---------------------------------------------------------------------------
# 1. 字段逐一往返保真
# ---------------------------------------------------------------------------
def test_roundtrip_all_fields(tmp_path):
    url = f"sqlite:///{tmp_path / 'a.db'}"
    store = SQLExperimentStore(url)
    exp = _make_experiment()
    store.save_experiment(exp)
    loaded = store.load_experiment(exp.id)
    store.close()

    assert loaded is not None
    assert loaded.id == exp.id
    assert loaded.name == exp.name
    assert loaded.description == exp.description
    assert loaded.parameter_name == exp.parameter_name
    # 兼容旧字段原样保留（JSON 列，类型不丢）
    assert loaded.control_value == "off"
    assert loaded.treatment_value == "on"
    # mechanism_toggles 必须是 dict（不是字符串）
    assert loaded.mechanism_toggles == {"LF-M44": False, "LF-M23": True}
    assert loaded.primary_metric == exp.primary_metric
    assert loaded.secondary_metrics == ["exam_score", "flow_frequency"]
    assert loaded.alpha_alloc == 0.05
    assert loaded.gate_level == 2
    assert loaded.mde == 0.3
    assert loaded.required_n_per_group == 120
    assert loaded.icc_assumed == 0.05
    assert loaded.cluster_randomized is True
    assert loaded.deff == 2.45
    assert loaded.phase == ExperimentPhase.CANARY
    assert loaded.traffic_percentage == 0.25
    assert loaded.min_sample_per_group == 100
    assert loaded.tracking_days == 90
    # 可复现性锚点必须保留
    assert loaded.registry_fingerprint == "fp-abc123deadbeef"
    # 时间戳往返（tz-aware 一致）
    assert loaded.created_at == exp.created_at
    assert loaded.started_at == exp.started_at
    assert loaded.completed_at is None

    # 嵌套 metrics 必须还原成 ExperimentMetric 实例（不是 dict）
    assert len(loaded.metrics) == 2
    assert all(isinstance(m, ExperimentMetric) for m in loaded.metrics)
    assert loaded.metrics[0].category == MetricCategory.LEARNING
    assert loaded.metrics[0].target_direction == "increase"
    assert loaded.metrics[1].category == MetricCategory.HEALTH
    assert loaded.metrics[1].safety_threshold == 70.0
    assert loaded.metrics[1].current_value == 30.0
    assert loaded.results == []


# ---------------------------------------------------------------------------
# 2. 跨实例持久化（"真落库"判据）
# ---------------------------------------------------------------------------
def test_cross_instance_persistence(tmp_path):
    url = f"sqlite:///{tmp_path / 'b.db'}"
    s1 = SQLExperimentStore(url)
    exp = _make_experiment("exp_cross")
    s1.save_experiment(exp)
    s1.close()  # 关闭引擎（dispose）

    # 用同一个文件新开一个 store，应仍能读回
    s2 = SQLExperimentStore(url)
    loaded = s2.load_experiment("exp_cross")
    s2.close()

    assert loaded is not None
    assert loaded.name == exp.name
    assert loaded.registry_fingerprint == "fp-abc123deadbeef"
    assert loaded.mechanism_toggles == {"LF-M44": False, "LF-M23": True}
    assert loaded.metrics[0].category == MetricCategory.LEARNING


# ---------------------------------------------------------------------------
# 3. 分组写入 + 读回
# ---------------------------------------------------------------------------
def test_assignment_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'c.db'}"
    store = SQLExperimentStore(url)
    store.save_experiment(_make_experiment("exp_assign"))
    store.save_assignment("exp_assign", "u1", "treatment", cluster_id="cls1")
    store.save_assignment("exp_assign", "u2", "control")

    out = store.load_assignments("exp_assign")
    store.close()

    assert out == {
        "u1": {"group": "treatment", "cluster_id": "cls1"},
        "u2": {"group": "control", "cluster_id": ""},
    }


# ---------------------------------------------------------------------------
# 4. 主键冲突：重复写入应覆盖，不产生重复行
# ---------------------------------------------------------------------------
def test_assignment_overwrite_on_duplicate(tmp_path):
    url = f"sqlite:///{tmp_path / 'd.db'}"
    store = SQLExperimentStore(url)
    store.save_experiment(_make_experiment("exp_dup"))
    store.save_assignment("exp_dup", "u1", "control", cluster_id="c1")
    store.save_assignment("exp_dup", "u1", "treatment", cluster_id="c2")  # 覆盖

    out = store.load_assignments("exp_dup")
    store.close()

    # 被试只能属于一个组，且为最新值
    assert out["u1"] == {"group": "treatment", "cluster_id": "c2"}
    assert len(out) == 1  # 不产生重复行


# ---------------------------------------------------------------------------
# 5. 删除实验同时清除其分组（不留孤儿分组）
# ---------------------------------------------------------------------------
def test_delete_clears_assignments(tmp_path):
    url = f"sqlite:///{tmp_path / 'e.db'}"
    store = SQLExperimentStore(url)
    store.save_experiment(_make_experiment("exp_del"))
    store.save_assignment("exp_del", "u1", "control")
    store.delete_experiment("exp_del")

    assert store.load_experiment("exp_del") is None
    assert store.load_assignments("exp_del") == {}
    store.close()


# ---------------------------------------------------------------------------
# 6. list_experiments 返回全部
# ---------------------------------------------------------------------------
def test_list_experiments(tmp_path):
    url = f"sqlite:///{tmp_path / 'f.db'}"
    store = SQLExperimentStore(url)
    store.save_experiment(_make_experiment("e1"))
    store.save_experiment(_make_experiment("e2"))
    all_exp = store.list_experiments()
    store.close()

    assert len(all_exp) == 2
    ids = {e.id for e in all_exp}
    assert ids == {"e1", "e2"}


# ---------------------------------------------------------------------------
# 7. 幂等建表：同库连续 new 两个 store 不报错
# ---------------------------------------------------------------------------
def test_idempotent_create_all(tmp_path):
    url = f"sqlite:///{tmp_path / 'g.db'}"
    s1 = SQLExperimentStore(url)
    s1.close()
    s2 = SQLExperimentStore(url)  # 重复建表应被 checkfirst 忽略
    s2.save_experiment(_make_experiment("e_idem"))
    assert s2.load_experiment("e_idem") is not None
    s2.close()


# ---------------------------------------------------------------------------
# 8. 工厂路由
# ---------------------------------------------------------------------------
def test_factory_default_is_memory(monkeypatch):
    monkeypatch.delenv("LEARNFLOW_EXPERIMENT_BACKEND", raising=False)
    store = default_experiment_store()
    try:
        assert isinstance(store, MemoryExperimentStore)
    finally:
        store.close()


def test_factory_memory(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_EXPERIMENT_BACKEND", "memory")
    store = default_experiment_store()
    try:
        assert isinstance(store, MemoryExperimentStore)
    finally:
        store.close()


def test_factory_json(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_EXPERIMENT_BACKEND", "json")
    store = default_experiment_store()
    try:
        assert isinstance(store, JSONFileExperimentStore)
    finally:
        store.close()


def test_factory_sql(monkeypatch, tmp_path):
    db = tmp_path / "factory.db"
    monkeypatch.setenv("LEARNFLOW_EXPERIMENT_BACKEND", "sql")
    monkeypatch.setenv("LEARNFLOW_EXPERIMENT_DB_URL", f"sqlite:///{db}")
    store = default_experiment_store()
    try:
        assert isinstance(store, SQLExperimentStore)
    finally:
        store.close()


def test_factory_unknown_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_EXPERIMENT_BACKEND", "bogus-value")
    store = default_experiment_store()
    try:
        assert isinstance(store, MemoryExperimentStore)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 9. MySQL 方言可生成，且不含 Postgres 专有类型（防回归）
# ---------------------------------------------------------------------------
def test_mysql_ddl_no_postgres_types():
    ddl = str(CreateTable(experiments_table).compile(dialect=mysql.dialect()))
    assert "JSONB" not in ddl
    assert "TIMESTAMPTZ" not in ddl
    assert "BIGSERIAL" not in ddl
    # 方言无关类型生效：MySQL 下 JSON 列应编译成 JSON
    assert "JSON" in ddl


def test_sqlite_ddl_no_postgres_types():
    ddl = str(CreateTable(experiments_table).compile(dialect=sqlite.dialect()))
    assert "JSONB" not in ddl
    assert "TIMESTAMPTZ" not in ddl
    assert "BIGSERIAL" not in ddl
